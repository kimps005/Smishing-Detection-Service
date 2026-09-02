# CatchSmishing

> **이미지·문자·QR 코드에 숨은 스미싱 신호를 다층적으로 분석하는 AI 기반 탐지 서비스**

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](#빠른-시작) [![Flutter](https://img.shields.io/badge/Flutter-3.29%2B-02569B?logo=flutter&logoColor=white)](#flutter-클라이언트-실행) [![FastAPI](https://img.shields.io/badge/API-FastAPI-009688?logo=fastapi&logoColor=white)](#api-명세) [![Hugging%20Face](https://img.shields.io/badge/Model-Hugging%20Face-FFD21E?logo=huggingface&logoColor=black)](https://huggingface.co/kimps005/sms-category-model)

**CatchSmishing**은 수신 문자, 캡처 이미지, QR 코드의 URL을 입력받아 OCR, URL 위협 인텔리전스, 한국어 문자 분류 모델, Gemini 기반 문맥·시각 분석을 결합해 스미싱 위험도와 판단 근거를 제공합니다.

- 서비스: [catchsmishing.com](https://catchsmishing.com)
- API: [api.catchsmishing.com](https://api.catchsmishing.com)
- 모델: [kimps005/sms-category-model](https://huggingface.co/kimps005/sms-category-model)
- 프로젝트 위키: [wiki/Home.md](wiki/Home.md)

> 이 서비스의 결과는 사용자의 확인을 돕는 **보조 신호**입니다. `Safe` 결과도 발신자·링크·기관의 진위를 보증하지 않으며, 금전·개인정보와 관련된 요청은 반드시 해당 기관의 공식 앱 또는 공식 번호로 별도 확인해야 합니다.

## 목차

- [핵심 기능](#핵심-기능)
- [분석 아키텍처](#분석-아키텍처)
- [위험도와 분류 체계](#위험도와-분류-체계)
- [기술 구성](#기술-구성)
- [프로젝트 구조](#프로젝트-구조)
- [빠른 시작](#빠른-시작)
- [API 명세](#api-명세)
- [모델과 평가](#모델과-평가)
- [보안·개인정보·운영 유의사항](#보안개인정보운영-유의사항)

## 핵심 기능

| 영역 | 제공 기능 |
| --- | --- |
| 이미지 분석 | 문자 캡처본에서 PaddleOCR로 텍스트를 추출하고, QR 코드와 본문 URL을 함께 분석합니다. |
| 텍스트 분석 | 복사·공유된 문자에서 위험 키워드, 카테고리, URL, 문맥 신호를 종합합니다. |
| QR 분석 | 카메라·이미지에서 추출한 QR URL의 최종 도착지와 위험 신호를 확인합니다. |
| URL 위협 분석 | 리다이렉트 추적, Phishing.Database·URLhaus 대조, VirusTotal, WHOIS 도메인 연령, APK 설치 유도, URL 구조 특징을 점검합니다. |
| AI 문맥·시각 분석 | Gemini가 사칭, 긴박감, 행동 유도 등 문맥을 분석하며 이미지 입력에서는 시각적 단서도 함께 평가합니다. |
| 설명 가능한 결과 | 최종 등급·점수·카테고리뿐 아니라 위험 키워드, URL 근거, AI 분석 사유를 반환합니다. |
| 운영·개선 | 위험 URL 랭킹, 사용자 피드백, 인증된 관리자 분석 로그를 지원합니다. |

## 분석 아키텍처

```text
┌──────────────────────── 입력 ────────────────────────┐
│  문자 텍스트  ·  문자 캡처 이미지  ·  QR 코드 URL       │
└─────────────────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────── 전처리 ──────────────────────────┐
│ OCR · QR 디코딩 · URL 정규화 · URL 추출 · 입력 검증     │
└─────────────────────────────────────────────────────┘
                         │
          ┌──────────────┼───────────────┐
          ▼              ▼               ▼
┌────────────────┐ ┌────────────────┐ ┌────────────────────┐
│ 문자 분류 모델  │ │ 규칙 기반 NLP  │ │ URL 보안 분석       │
│ KLUE/BERT 7종   │ │ 긴박·위협·유도 │ │ 피드·VT·WHOIS·APK  │
└────────────────┘ └────────────────┘ └────────────────────┘
          │              │               │
          └──────────────┼───────────────┘
                         ▼
          ┌──────────────────────────────┐
          │ Gemini 문맥 분석 / Vision 분석 │
          └──────────────────────────────┘
                         │
                         ▼
┌──────────────────── 결과 생성 ───────────────────────┐
│ 위험 점수(0–10) · 등급 · 유형 · 탐지 근거 · 대응 안내  │
└─────────────────────────────────────────────────────┘
```

분석 신호의 가용성에 따라 점수 결합 방식이 달라집니다. 예를 들어 URL 위험 신호가 강하면 URL의 비중을 높이고, Gemini 호출을 사용할 수 없는 경우에도 OCR·규칙·URL 분석 결과만으로 응답을 반환합니다.

### URL 분석 흐름

1. HTTP(S) URL만 허용하고 `localhost`, 사설·링크-로컬 IP, 사용자 인증정보가 포함된 URL을 차단합니다.
2. 최대 5회 리다이렉트를 따라 최종 목적지를 확인합니다.
3. 원본·최종 URL을 Phishing.Database 및 URLhaus 피드와 대조합니다.
4. 최종 도메인을 VirusTotal 및 WHOIS로 확인하고, URL 구조·단축 URL·의심 TLD·APK 설치 유도를 점검합니다.
5. 가장 위험한 URL 신호와 문자 유형 가중치를 반영해 `P_URL`을 계산합니다.

## 위험도와 분류 체계

### 위험 등급

| 등급 | 점수 | 의미 | 권장 대응 |
| --- | ---: | --- | --- |
| `Danger` | 7.0–10.0 | 스미싱 위험 신호가 강하게 확인됨 | 링크를 열지 말고 발신자를 차단한 뒤 신고·확인합니다. |
| `Warning` | 3.5–6.9 | 의심스러운 패턴 또는 링크 신호 감지 | 문자 링크 대신 해당 기관의 공식 앱·웹사이트에 직접 접속합니다. |
| `Safe` | 0.0–3.4 | 현재 수집된 신호에서 강한 위험을 찾지 못함 | 민감 정보 요청은 여전히 공식 경로로 재확인합니다. |
| `Unknown` | — | OCR 등 입력 인식에 실패함 | 더 선명한 캡처 이미지 또는 원문 텍스트로 재시도합니다. |

### 문자 카테고리

| 코드 | 분류 | 예시 범위 |
| --- | --- | --- |
| `PERSONAL` | 일반 문자 | 가족·지인·일상 대화 |
| `FINANCE` | 금융 | 은행, 카드, 결제, 대출 |
| `DELIVERY` | 배송 | 택배, 수령, 반품, 배송 상태 |
| `GOVERNMENT` | 공공기관 | 정부·지자체·공공기관 안내 |
| `PROMOTION` | 홍보·투자 | 광고, 쿠폰, 이벤트, 투자 유도 |
| `AUTH` | 계정 인증 | 로그인, OTP, 비밀번호, 보안 알림 |
| `WORK` | 업무·지인 사칭 | 조직·업무 공지, 지인 사칭 패턴 |

카테고리는 스미싱 여부 그 자체가 아닙니다. 예를 들어 금융·배송 문자는 정상일 수도 있으므로 URL, 요청 내용, 발신자 확인 결과와 함께 해석해야 합니다.

## 기술 구성

| 구분 | 기술 |
| --- | --- |
| API 서버 | FastAPI, Uvicorn, Python |
| 문자·이미지 분석 | PaddleOCR, OpenCV, pyzbar, Pillow |
| 분류 모델 | PyTorch, Transformers, `klue/bert-base`, Hugging Face Hub |
| 생성형 AI | Google Gemini API (텍스트 문맥·이미지 시각 분석) |
| URL 보안 | requests, python-whois, Phishing.Database, URLhaus, VirusTotal |
| 데이터·운영 | MySQL/Aiven, PyMySQL, Streamlit |
| 모바일 | Flutter, Dart, `image_picker`, `mobile_scanner`, `share_handler`, `share_plus` |

정확한 Python 의존성은 [requirements.txt](requirements.txt), Flutter 패키지 버전은 [pubspec.yaml](pubspec.yaml)을 기준으로 합니다.

## 프로젝트 구조

```text
.
├── lib/
│   └── main.dart                  # Flutter 모바일 클라이언트
├── server/
│   ├── main.py                    # FastAPI 엔드포인트·통합 분석 파이프라인
│   ├── predictor.py               # KLUE/BERT 카테고리 분류 및 모델 로딩
│   ├── url_analyzer.py            # URL 리다이렉트·평판·WHOIS·APK 분석
│   ├── db_config.py               # MySQL TLS 연결 설정
│   ├── app.py                     # Streamlit 운영 UI 진입점
│   ├── pages/                     # 운영 UI 화면
│   ├── templates/, static/        # FastAPI 웹 페이지 리소스
│   └── admin_feedback.py          # 피드백 조회 보조 도구
├── models/                        # 로컬 캐시 모델 경로 (Git 제외)
├── requirements.txt               # Python 의존성
├── pubspec.yaml                   # Flutter 의존성
├── .env.example                   # 환경 변수 템플릿
├── benchmark_quantization.py      # FP32 ↔ INT8 모델 벤치마크
├── eval_hybrid.py                 # OCR 하이브리드 평가 도구
└── smishing_colab.ipynb           # 모델 학습 실험 노트북
```

## 빠른 시작

### 1. 사전 요구사항

- Python 3.11 이상 및 `pip`
- Flutter 3.29 이상 — 모바일 앱 실행 시
- MySQL 호환 데이터베이스 — 피드백·위험 URL 랭킹·관리자 로그 사용 시
- Gemini API 키 — Gemini 문맥·Vision 분석 사용 시
- VirusTotal API 키 — VirusTotal 평판 조회 사용 시
- `pyzbar`가 사용하는 ZBar 런타임 — Windows에서 QR 디코딩 오류가 난 경우 별도 설치가 필요할 수 있습니다.

### 2. 설치 및 환경 변수 설정

저장소를 내려받은 뒤 가상 환경을 만들고 의존성을 설치합니다. 아래 명령은 PowerShell 기준입니다.

```powershell
git clone https://github.com/kimps005/Smishing-Detection-Service.git
cd Smishing-Detection-Service

python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt

Copy-Item .env.example .env
```

`.env`에 필요한 값을 입력합니다. `.env`는 Git으로 추적하지 않으므로 API 키와 DB 비밀번호를 저장소에 커밋하지 마세요.

| 변수 | 필수 여부 | 용도 |
| --- | --- | --- |
| `GEMINI_API_KEY` | 선택 | Gemini 텍스트·이미지 분석. 미설정 시 해당 신호 없이 분석합니다. |
| `VIRUSTOTAL_API_KEY` | 선택 | VirusTotal 도메인 평판 조회. |
| `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` | 선택 | 피드백, URL 랭킹, 분석 로그 저장. 미설정이어도 기본 분석 API는 실행됩니다. |
| `DB_SSL_CA` | 운영 DB 사용 시 권장 | Aiven 등 TLS DB의 CA 인증서 경로. 운영 환경에서는 `DB_SSL_VERIFY=1`을 유지합니다. |
| `ADMIN_TOKEN` | 관리자 로그 사용 시 필수 | `/admin/logs` 접근용 Bearer 토큰. 충분히 긴 무작위 값으로 설정합니다. |
| `API_URL` | Streamlit 사용 시 선택 | Streamlit이 호출할 FastAPI 주소. 기본값은 `http://127.0.0.1:8000`입니다. |

기본 방어 한도도 `.env`에서 조정할 수 있습니다.

| 변수 | 기본값 | 설명 |
| --- | ---: | --- |
| `MAX_IMAGE_BYTES` | 10 MiB | 분석 이미지의 최대 크기 |
| `MAX_FEEDBACK_IMAGE_BYTES` | 5 MiB | 피드백 첨부 이미지의 최대 크기 |
| `MAX_IMAGE_PIXELS` | 25,000,000 | 이미지 최대 픽셀 수 |
| `MAX_TEXT_LENGTH` | 20,000 | 텍스트 최대 글자 수 |
| `ANALYSIS_WORKERS` | 4 | 분석용 백그라운드 작업자 수(1–4) |
| `MAX_URLS_PER_ANALYSIS` | 10 | 한 요청에서 검사할 최대 URL 수 |

### 3. 분류 모델 준비

서버를 처음 시작하면 `models/`에 로컬 파일이 있는지 먼저 확인합니다. 없을 경우 공개 Hugging Face 저장소에서 **INT8 양자화 가중치**와 모델 구성·토크나이저 파일만 자동으로 내려받아 캐시합니다. 이후 요청에서는 재다운로드하지 않습니다.

```env
SMS_MODEL_QUANTIZED=1
SMS_CATEGORY_MODEL_PATH=
SMS_BASE_MODEL_PATH=
SMS_HF_REPO_ID=kimps005/sms-category-model
SMS_HF_MODEL_FILENAME=sms_category_model_int8_dynamic_state_dict.pt
SMS_HF_REVISION=b0267b3befd229165127de5cf402414d427863fa
```

기본 경로는 `models/sms_category_model_int8_dynamic_state_dict.pt` 및 `models/klue-bert-base/`입니다. 사내 아티팩트 저장소나 다른 디렉터리를 사용할 때만 `SMS_CATEGORY_MODEL_PATH`, `SMS_BASE_MODEL_PATH`를 지정하세요. 큰 모델 가중치는 저장소에서 제외되며, 실제 파일은 Hugging Face에서 제공합니다.

### 4. 서버와 운영 UI 실행

API 서버는 첫 실행 시 모델을 준비하고, DB가 설정되어 있으면 URL 카운터를 초기화합니다.

```powershell
cd server
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

실행 후 다음 주소를 사용할 수 있습니다.

- API 문서: `http://127.0.0.1:8000/docs`
- 기본 웹 화면: `http://127.0.0.1:8000/`
- 분석 화면: `http://127.0.0.1:8000/analyze-page`
- 피드백 화면: `http://127.0.0.1:8000/feedback-page`

별도 터미널에서 Streamlit 운영 UI를 실행합니다.

```powershell
cd server
streamlit run app.py
```

### Flutter 클라이언트 실행

```powershell
flutter pub get
flutter run
```

개발용 API를 사용할 경우 [lib/main.dart](lib/main.dart)의 `_localDev`를 `true`로 전환하고, 같은 네트워크에서 기기가 접근 가능한 서버 IP로 `serverUrl`을 설정합니다. 실기기에서는 `localhost`가 개발 PC가 아니라 기기 자신을 가리키는 점에 유의하세요.

## API 명세

개발 중에는 FastAPI의 자동 문서(`/docs`)를 가장 최신 명세로 사용하세요. 주요 엔드포인트는 다음과 같습니다.

| 메서드 | 경로 | 요청 | 설명 |
| --- | --- | --- | --- |
| `POST` | `/analyze` | `multipart/form-data`의 `file` | 이미지 OCR·QR·Vision을 포함한 통합 분석 |
| `POST` | `/analyze-text` | JSON `{"text": "..."}` | 문자 본문과 포함 URL 분석 |
| `POST` | `/analysis/cancel/{analysis_id}` | — | `X-Analysis-ID`로 시작한 분석의 협력 취소 요청 |
| `GET` | `/top-urls?limit=5` | 쿼리 `limit` 1–50 | 누적 위험 URL 랭킹 조회 |
| `POST` | `/feedback` | 폼 데이터, 선택적 이미지 | 오탐·미탐 피드백 저장 |
| `GET` | `/admin/logs` | `Authorization: Bearer <ADMIN_TOKEN>` | 관리자 분석 로그 HTML 화면 |

### 텍스트 분석 예시

```bash
curl -X POST "http://127.0.0.1:8000/analyze-text" \
  -H "Content-Type: application/json" \
  -H "X-Analysis-ID: demo-001" \
  -d "{\"text\": \"[택배] 주소 확인이 필요합니다. https://example.com\"}"
```

### 이미지 분석 예시

```bash
curl -X POST "http://127.0.0.1:8000/analyze" \
  -H "X-Analysis-ID: demo-image-001" \
  -F "file=@./sample-message.png"
```

응답에는 다음 정보를 포함합니다. Gemini 호출 실패나 DB 미설정은 분석 전체를 실패시키지 않으며, 해당 보조 기능의 결과만 비어 있거나 실패 상태로 반환될 수 있습니다.

```json
{
  "extracted_text": "OCR 또는 입력 텍스트",
  "text_urls": ["https://example.com"],
  "category": {
    "category": "DELIVERY",
    "category_confidence": 0.91
  },
  "scores": {
    "p_nlp": 4.2,
    "p_url": 6.8,
    "p_gemini": 7.0,
    "p_vlm": null,
    "final": 6.9
  },
  "result": {
    "grade": "Warning",
    "message": "의심스러운 패턴이 감지되었습니다. 주의가 필요합니다."
  }
}
```

## 모델과 평가

### 카테고리 분류 모델

- 기반 모델: [`klue/bert-base`](https://huggingface.co/klue/bert-base)
- 분류 대상: 한국어 SMS 7개 카테고리
- 배포 형식: PyTorch INT8 동적 양자화 `state_dict`
- 입력 길이: 최대 128 토큰
- 배포 모델: [kimps005/sms-category-model](https://huggingface.co/kimps005/sms-category-model)

양자화 체크포인트는 CPU 추론을 목표로 합니다. 프로젝트의 벤치마크에서는 FP32 체크포인트 대비 파일 크기를 약 **58%** 줄이고, 단일 문자 p50 지연 시간을 약 **47%** 낮추는 결과를 확인했습니다. 해당 수치는 생성형 SMS 2,800건을 사용한 로컬 진단 벤치마크 결과이며, 실제 스미싱 탐지율 또는 독립적인 실사용 성능을 의미하지 않습니다.

원본 FP32 체크포인트의 경로를 `SMS_CATEGORY_MODEL_PATH`로 지정한 뒤 양자화 성능을 비교할 수 있습니다.

```powershell
python benchmark_quantization.py --variant fp32
python benchmark_quantization.py --variant int8_dynamic
```

`smishing_colab.ipynb`에는 분류 모델 실험 워크플로가, `eval_hybrid.py`와 `eval_paddle_only.py`에는 OCR 평가 도구가 포함되어 있습니다. 외부 데이터셋·개인 문자 테스트는 API 키 사용량과 개인정보 보호 요건을 먼저 확인한 뒤 실행하세요.

## 보안·개인정보·운영 유의사항

### 기본 방어 설계

- 공개 API의 비용이 큰 경로에는 IP·경로 단위의 메모리 기반 요청 제한이 적용됩니다. 기본값은 이미지 분석 분당 10회, 텍스트 분석 분당 30회, 피드백 분당 20회입니다.
- 이미지 크기·픽셀 수, 텍스트 길이, URL 개수를 제한하고 분석은 최대 4개의 백그라운드 작업자로 처리합니다.
- URL을 실제로 요청하기 전 및 리다이렉트 단계마다 사설망·로컬·예약 IP를 검사해 SSRF 위험을 줄입니다.
- 관리자 로그는 `ADMIN_TOKEN`을 설정한 경우에만 Bearer 토큰 인증으로 접근할 수 있습니다.
- DB 연결은 CA 인증서를 통한 TLS 검증을 기본으로 합니다. 운영 환경에서는 `DB_SSL_VERIFY=0`을 사용하지 마세요.

### 개인정보 처리 원칙

문자에는 전화번호, 계좌 정보, 인증번호, 이름 등 민감한 개인정보가 포함될 수 있습니다. 운영 시에는 다음을 권장합니다.

- 필요 최소한의 로그만 저장하고 보존 기간을 정의합니다.
- 사용자 동의와 접근 통제를 갖춘 환경에서만 외부 AI·평판 API로 데이터를 전송합니다.
- API 키·DB 자격 증명·관리자 토큰은 비밀 관리 도구 또는 배포 플랫폼의 Secret으로 관리합니다.
- 피드백 첨부 이미지는 운영 정책에 따라 접근 권한·보존·삭제 절차를 마련합니다.

### 한계와 책임 있는 사용

- 스미싱 기법과 악성 도메인은 빠르게 변하므로 피드·모델·규칙은 지속적으로 검토해야 합니다.
- 카테고리 분류의 확률은 스미싱 확률이나 URL 안전 확률로 해석할 수 없습니다.
- VirusTotal 또는 위협 피드에 결과가 없더라도 안전을 보장하지 않습니다.
- 이 결과만으로 계정 차단, 결제 중단, 법적 판단 같은 자동 조치를 수행하지 마세요.

의심 문자로 실제 피해가 발생했거나 긴급 대응이 필요하다면 KISA 불법스팸대응센터 **118** 또는 관계 기관의 공식 신고 채널을 이용하세요.

## 라이선스 및 기여

현재 저장소의 라이선스 파일이 제공되지 않았습니다. 재배포·상업적 사용·모델 재사용 전에는 저장소 및 기반 모델의 이용 조건을 확인해 주세요. 개선 제안이나 버그 제보는 GitHub Issues 또는 Pull Request로 남겨주시면 됩니다.
