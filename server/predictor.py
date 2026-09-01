# predictor.py — 문맥 분류 모듈
# OCR로 추출한 텍스트를 받아 7개 카테고리로 분류

import os
import re
import shutil
from pathlib import Path
import numpy as np
import torch
import torch.nn as nn
from huggingface_hub import hf_hub_download, snapshot_download
from transformers import AutoConfig, AutoModel, AutoTokenizer

# ── 카테고리 정의 ──────────────────────────────────────────
CATEGORIES = {
    0: "PERSONAL",
    1: "FINANCE",
    2: "DELIVERY",
    3: "GOVERNMENT",
    4: "PROMOTION",
    5: "AUTH",
    6: "WORK",
}

# 위험 카테고리 (PERSONAL 제외) — main.py에서도 사용
DANGEROUS_CATEGORIES = {"FINANCE", "DELIVERY", "GOVERNMENT", "PROMOTION", "AUTH", "WORK"}

MODEL_NAME = "klue/bert-base"
NUM_LABELS = len(CATEGORIES)
MAX_LENGTH = 128
DROPOUT = 0.3
PROJECT_ROOT = Path(__file__).resolve().parent.parent
HF_REPO_ID = os.getenv("SMS_HF_REPO_ID", "kimps005/sms-category-model").strip()
HF_MODEL_FILENAME = os.getenv(
    "SMS_HF_MODEL_FILENAME",
    "sms_category_model_int8_dynamic_state_dict.pt",
).strip()
HF_REVISION = os.getenv(
    "SMS_HF_REVISION",
    "b0267b3befd229165127de5cf402414d427863fa",
).strip() or "b0267b3befd229165127de5cf402414d427863fa"
MODEL_QUANTIZED = os.getenv("SMS_MODEL_QUANTIZED", "1").strip().lower() in {
    "1", "true", "yes", "on"
}


def _resolve_local_path(value: str, default: Path) -> Path:
    path = Path(value) if value else default
    return path if path.is_absolute() else PROJECT_ROOT / path


_default_model_path = (
    PROJECT_ROOT / "models" / HF_MODEL_FILENAME
    if MODEL_QUANTIZED
    else PROJECT_ROOT / "server" / "sms_category_model.pt"
)
MODEL_PATH = _resolve_local_path(os.getenv("SMS_CATEGORY_MODEL_PATH", "").strip(), _default_model_path)
BASE_MODEL_PATH = _resolve_local_path(
    os.getenv("SMS_BASE_MODEL_PATH", "").strip(),
    PROJECT_ROOT / "models" / "klue-bert-base",
)
SOURCE_MODEL_PATH = _resolve_local_path(
    os.getenv("SMS_FULL_MODEL_PATH", "").strip(),
    PROJECT_ROOT / "server" / "sms_category_model.pt",
)

_BASE_MODEL_FILES = (
    "config.json",
    "tokenizer.json",
    "tokenizer_config.json",
    "special_tokens_map.json",
    "vocab.txt",
)
_models_prepared = False

URL_RE = re.compile(r"http[s]?://\S+")


def _from_pretrained(model_cls, model_name: str, **kwargs):
    model_path = Path(model_name)
    if model_path.exists():
        return model_cls.from_pretrained(model_path, local_files_only=True, **kwargs)

    if model_name == MODEL_NAME and BASE_MODEL_PATH is not None:
        if not _base_model_files_ready(BASE_MODEL_PATH):
            raise FileNotFoundError(
                f"BERT 기본 모델 경로를 찾을 수 없습니다: {BASE_MODEL_PATH}. "
                "서버 시작 시 자동 다운로드가 실패했는지 확인해주세요."
            )
        return model_cls.from_pretrained(BASE_MODEL_PATH, local_files_only=True, **kwargs)

    try:
        return model_cls.from_pretrained(model_name, local_files_only=True, **kwargs)
    except OSError as exc:
        raise FileNotFoundError(
            f"BERT 기본 모델을 로컬에서 찾을 수 없습니다: {model_name}. "
            "서버 시작 시 모델 자동 다운로드가 실패했는지 확인해주세요."
        ) from exc


def _model_file_ready(path: Path) -> bool:
    """모델 파일이 Git LFS 포인터가 아닌 실제 가중치 파일인지 확인한다."""
    try:
        return path.is_file() and path.stat().st_size > 1024 * 1024
    except OSError:
        return False


def _base_model_files_ready(path: Path) -> bool:
    return path.is_dir() and all((path / name).is_file() for name in _BASE_MODEL_FILES)


def _download_category_model() -> Path:
    if not HF_REPO_ID or not HF_MODEL_FILENAME:
        raise RuntimeError("허깅페이스 모델 저장소 설정이 비어 있습니다.")

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    downloaded_path = Path(
        hf_hub_download(
            repo_id=HF_REPO_ID,
            filename=HF_MODEL_FILENAME,
            revision=HF_REVISION,
            local_dir=str(MODEL_PATH.parent),
            force_download=True,
        )
    )
    if downloaded_path.resolve() != MODEL_PATH.resolve():
        shutil.copyfile(downloaded_path, MODEL_PATH)
    return MODEL_PATH


def _download_base_model_files() -> Path:
    if not HF_REPO_ID:
        raise RuntimeError("허깅페이스 모델 저장소 설정이 비어 있습니다.")

    BASE_MODEL_PATH.mkdir(parents=True, exist_ok=True)
    snapshot_download(
        repo_id=HF_REPO_ID,
        revision=HF_REVISION,
        local_dir=str(BASE_MODEL_PATH),
        allow_patterns=list(_BASE_MODEL_FILES),
    )
    return BASE_MODEL_PATH


def prepare_models() -> tuple[Path, Path]:
    """서버 실행 전에 모델 파일을 확인하고 없으면 공개 HF 저장소에서 받는다.

    양자화 가중치와 BERT 설정·토크나이저만 다운로드한다. BERT의 전체 가중치는
    다운로드하지 않으며, 실제 가중치는 ``MODEL_PATH``의 양자화 파일을 사용한다.
    """
    global _models_prepared
    if _models_prepared:
        return MODEL_PATH, BASE_MODEL_PATH

    if not _model_file_ready(MODEL_PATH):
        if not MODEL_QUANTIZED:
            raise FileNotFoundError(
                f"분류 모델을 찾을 수 없습니다: {MODEL_PATH}. "
                "SMS_MODEL_QUANTIZED=1로 설정하거나 전체 모델 파일을 지정해주세요."
            )
        print(f"[predictor] 분류 모델 다운로드 중: {HF_REPO_ID}/{HF_MODEL_FILENAME}", flush=True)
        _download_category_model()

    if not _base_model_files_ready(BASE_MODEL_PATH):
        print(f"[predictor] BERT 설정·토크나이저 다운로드 중: {HF_REPO_ID}", flush=True)
        _download_base_model_files()

    if not _model_file_ready(MODEL_PATH):
        raise FileNotFoundError(f"분류 모델 다운로드 후 파일을 찾을 수 없습니다: {MODEL_PATH}")
    if not _base_model_files_ready(BASE_MODEL_PATH):
        raise FileNotFoundError(f"BERT 설정·토크나이저 다운로드 후 파일을 찾을 수 없습니다: {BASE_MODEL_PATH}")

    _models_prepared = True
    return MODEL_PATH, BASE_MODEL_PATH


def resolve_model_path() -> Path:
    """현재 설정된 분류 가중치 파일 경로를 반환한다."""
    if _model_file_ready(MODEL_PATH):
        return MODEL_PATH
    return prepare_models()[0]


def resolve_source_model_path() -> Path:
    """양자화 벤치마크에 사용할 원본 FP32 가중치 경로를 반환한다."""
    if SOURCE_MODEL_PATH.is_file():
        return SOURCE_MODEL_PATH
    raise FileNotFoundError(f"원본 FP32 모델을 찾을 수 없습니다: {SOURCE_MODEL_PATH}")


def _quantize_for_inference(model: nn.Module) -> nn.Module:
    if "x86" in torch.backends.quantized.supported_engines:
        torch.backends.quantized.engine = "x86"
    elif "fbgemm" in torch.backends.quantized.supported_engines:
        torch.backends.quantized.engine = "fbgemm"
    return torch.ao.quantization.quantize_dynamic(
        model, {nn.Linear}, dtype=torch.qint8, inplace=False
    )

# ── 키워드 부스팅 (카테고리별) ────────────────────────────────
KEYWORD_BOOSTS = {
    2: {  # DELIVERY
        "keywords": ["배송", "택배", "배달", "운송", "출고", "반송", "통관",
                     "대한통운", "롯데택배", "한진택배", "CJ대한통운", "우체국택배",
                     "우체국", "로젠", "경동", "송장", "송장번호",
                     "부재중", "경비실", "재배송", "픽업", "수거"],
        "weight": 3.0,
    },
    6: {  # WORK
        "keywords": ["회의", "미팅", "보고서", "업무", "팀장", "인사팀", "부서",
                     "IT지원", "실적", "분기", "공모전", "연수", "출장", "사내 교육",
                     "인사발령", "승진", "퇴사",
                     "급여", "연차", "반차", "휴가", "결재", "공지", "스케줄", "계약"],
        "weight": 3.0,
    },
    0: {  # PERSONAL
        "keywords": ["엄마", "아빠", "오빠", "언니", "형", "누나", "동생",
                     "사랑해", "보고싶어", "청첩장", "결혼", "부고", "장례",
                     "할머니", "할아버지", "친구", "자기", "여보",
                     "미안", "고마워", "생일", "약속",
                     "학생복지", "학생복지팀", "학생처", "교학처", "학생지원"],
        "keyword_groups": [
            [  # 티켓 취소/환불 관련
                ["취소", "환불", "변경"],
                ["티켓", "공연", "예매", "페스티벌", "콘서트", "뮤지컬"],
            ],
            [  # 취창업/교육 행사 관련
                ["취창업", "취업지원팀"],
                ["특강", "세미나", "안내", "공지", "부트캠프"],
            ],
        ],
        "weight": 3.0,
    },
    1: {  # FINANCE
        "keywords": ["입금", "출금", "잔액", "승인안내", "결제", "대출",
                     "계좌 휴면", "자동이체", "환율", "이자율",
                     "카드", "신용카드", "청구", "명세", "고지서", "한도", "이상거래"],
        "weight": 2.5,
    },
    3: {  # GOVERNMENT
        "keywords": ["국세청", "경찰청", "검찰청", "행정안전부", "민원24",
                     "보조금", "운전면허", "판결", "민사소송",
                     "건강보험공단", "국민건강보험", "건강검진", "과태료",
                     "보건소", "교통안전공단", "근로복지공단", "고용노동부",
                     "재난문자", "긴급재난", "주민센터", "구청"],
        "weight": 4.0,
    },
    4: {  # PROMOTION
        "keywords": ["무료수신거부", "쿠폰", "할인권", "이벤트", "적립",
                     "광고", "특가", "선착순", "한정", "1+1", "멤버십", "할인"],
        "weight": 3.0,
    },
    5: {  # AUTH
        "keywords": ["인증번호", "OTP", "비밀번호", "기기로그인", "출금 신청", "타인",
                     "확인코드", "보안코드", "2단계인증", "만료", "유효"],
        "weight": 3.5,
    },
}


# ── 모델 구조 ──────────────────────────────────────────────
class SMSClassifier(nn.Module):
    def __init__(self, num_dropouts=5, config=None):
        super().__init__()
        if config is None:
            config = AutoConfig.from_pretrained(BASE_MODEL_PATH, local_files_only=True)
        # config만으로 구조를 만들고, 실제 가중치는 아래에서 분류 모델 파일로 로드한다.
        self.encoder = AutoModel.from_config(config)
        h = self.encoder.config.hidden_size
        self.num_dropouts = num_dropouts

        self.dropouts = nn.ModuleList([
            nn.Dropout(DROPOUT + i * 0.04) for i in range(num_dropouts)
        ])

        self.proj = nn.Sequential(
            nn.Linear(h * 2, h),
            nn.GELU(),
        )
        self.classifier = nn.Linear(h, NUM_LABELS)

    def forward(self, input_ids, attention_mask):
        out = self.encoder(input_ids=input_ids, attention_mask=attention_mask)
        last_hidden = out.last_hidden_state

        cls = last_hidden[:, 0, :]

        mask_exp = attention_mask.unsqueeze(-1).expand(last_hidden.size()).float()
        mean_pool = torch.sum(last_hidden * mask_exp, 1) / \
                    torch.clamp(mask_exp.sum(1), min=1e-9)

        h_proj = self.proj(torch.cat([cls, mean_pool], dim=-1))

        logits = sum(self.classifier(drop(h_proj)) for drop in self.dropouts) \
                 / self.num_dropouts
        return logits


# ── 싱글턴: 앱 시작 시 한 번만 로드 ──────────────────────
_model = None
_tokenizer = None
_device = None


def _load():
    global _model, _tokenizer, _device
    if _model is not None:
        return

    prepare_models()
    _device = torch.device("cpu")
    _tokenizer = _from_pretrained(AutoTokenizer, MODEL_NAME)

    model_path = resolve_model_path()
    config = AutoConfig.from_pretrained(BASE_MODEL_PATH, local_files_only=True)
    _model = SMSClassifier(config=config).to(_device)
    if MODEL_QUANTIZED:
        _model = _quantize_for_inference(_model)
    state_dict = torch.load(model_path, map_location=_device, weights_only=True)
    _model.load_state_dict(state_dict, strict=False)
    del state_dict
    _model.eval()
    print(f"[predictor] 모델 로드 완료 ({_device})")


def load_model() -> None:
    """서버 시작 시 모델을 준비하고 메모리에 한 번 로드한다."""
    _load()


# ── 전처리 ────────────────────────────────────────────────
def _clean(text: str) -> str:
    text = URL_RE.sub("", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


# ── 추론 ──────────────────────────────────────────────────
def predict(text: str) -> dict:
    """
    OCR로 추출된 텍스트를 받아 7개 카테고리 중 하나로 분류
    
    Returns:
        {
            "label":         int,    # 0~6
            "category":      str,    # 예: "FINANCE"
            "category_confidence": float,
            "smishing_confidence": float,
            "is_dangerous":  bool,   # PERSONAL이 아니면 True
            "all_probs":     dict,   # 카테고리별 확률
        }
    """
    _load()

    cleaned = _clean(text)

    enc = _tokenizer(
        cleaned,
        max_length=MAX_LENGTH,
        padding="max_length",
        truncation=True,
        return_tensors="pt",
    )

    with torch.no_grad():
        logits = _model(
            enc["input_ids"].to(_device),
            enc["attention_mask"].to(_device),
        )

    # 키워드 부스팅
    logits_np = logits.squeeze(0).cpu().float().numpy().copy()
    for cat_idx, boost_info in KEYWORD_BOOSTS.items():
        for kw in boost_info.get("keywords", []):
            if kw in text or kw in cleaned:
                logits_np[cat_idx] += boost_info["weight"]
                break
        for condition in boost_info.get("keyword_groups", []):
            if all(any(kw in text or kw in cleaned for kw in group) for group in condition):
                logits_np[cat_idx] += boost_info["weight"]
                break

    # Softmax
    exp_logits = np.exp(logits_np - logits_np.max())
    probs = exp_logits / exp_logits.sum()

    pred = int(np.argmax(probs))
    category = CATEGORIES[pred]
    category_confidence = float(probs[pred])

    return {
        "label": pred,
        "category": category,
        "category_confidence": round(category_confidence, 4),
        "smishing_confidence": 0.0,
        "is_dangerous": category in DANGEROUS_CATEGORIES,
        "all_probs": {CATEGORIES[i]: round(float(p), 4) for i, p in enumerate(probs)},
    }
