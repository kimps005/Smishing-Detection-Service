from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse
from typing import Optional
import os
import tempfile
import traceback
os.environ['FLAGS_enable_pir_api'] = '0'
from paddleocr import PaddleOCR
import numpy as np
import cv2
from pyzbar.pyzbar import decode
import re
from urllib.parse import urlparse
from google import genai as google_genai
import PIL.Image

from predictor import predict
import url_analyzer
from url_analyzer import analyze_urls, resolve_url, check_threat_feeds, check_virustotal
from collections import Counter
import requests
from db_config import get_db_conn
import zipfile
import io
import threading
import asyncio
import time
from contextlib import asynccontextmanager

# uvicorn main:app --reload
# http://127.0.0.1:8000/docs


@asynccontextmanager
async def lifespan(app: FastAPI):
    threading.Thread(target=_update_feeds, daemon=True).start()

    async def _periodic_refresh():
        while True:
            await asyncio.sleep(6 * 3600)
            threading.Thread(target=_update_feeds, daemon=True).start()

    async def _weekly_recheck():
        _week = 7 * 24 * 3600
        while True:
            elapsed = time.time() - _get_last_recheck()
            wait = max(_week - elapsed, 0)
            await asyncio.sleep(wait)
            threading.Thread(target=_run_recheck_and_mark, daemon=True).start()
            await asyncio.sleep(_week)

    task1 = asyncio.create_task(_periodic_refresh())
    task2 = asyncio.create_task(_weekly_recheck())
    yield
    task1.cancel()
    task2.cancel()


app = FastAPI(lifespan=lifespan)

# ── 정적 파일 / 프론트엔드 페이지 서빙 ───────────────────────
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse as _FileResponse

_BASE = os.path.dirname(__file__)
app.mount("/static", StaticFiles(directory=os.path.join(_BASE, "static")), name="static")

@app.get("/", include_in_schema=False)
async def _page_home():
    return _FileResponse(os.path.join(_BASE, "templates", "index.html"))

@app.get("/analyze-page", include_in_schema=False)
async def _page_analyze():
    return _FileResponse(os.path.join(_BASE, "templates", "analyze.html"))

@app.get("/feedback-page", include_in_schema=False)
async def _page_feedback():
    return _FileResponse(os.path.join(_BASE, "templates", "feedback.html"))

def _init_db():
    os.makedirs(os.path.join(os.path.dirname(__file__), "feedback_images"), exist_ok=True)
    con = get_db_conn()
    cursor = con.cursor()
    cursor.execute("""CREATE TABLE IF NOT EXISTS url_counts (
        url VARCHAR(512) PRIMARY KEY,
        category VARCHAR(64),
        count INT NOT NULL DEFAULT 0,
        original_feed_hit TINYINT(1) DEFAULT 0,
        original_vt_positive INT DEFAULT 0,
        resolve_error TINYINT(1) DEFAULT 0,
        first_seen DOUBLE DEFAULT 0
    )""")
    for col, definition in [
        ("original_feed_hit", "TINYINT(1) DEFAULT 0"),
        ("original_vt_positive", "INT DEFAULT 0"),
        ("resolve_error", "TINYINT(1) DEFAULT 0"),
        ("first_seen", "DOUBLE DEFAULT 0"),
    ]:
        try:
            cursor.execute(f"ALTER TABLE url_counts ADD COLUMN {col} {definition}")
        except Exception:
            pass
    cursor.execute("""CREATE TABLE IF NOT EXISTS app_meta (
        `key` VARCHAR(64) PRIMARY KEY,
        value DOUBLE NOT NULL DEFAULT 0
    )""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS feedback (
        id INT PRIMARY KEY AUTO_INCREMENT,
        given_grade VARCHAR(32),
        correct_grade VARCHAR(32),
        reason TEXT,
        text_content TEXT,
        image_path VARCHAR(512),
        created_at DOUBLE
    )""")
    try:
        cursor.execute("ALTER TABLE feedback ADD COLUMN image_path VARCHAR(512)")
    except Exception:
        pass
    cursor.execute("""CREATE TABLE IF NOT EXISTS analysis_log (
        id INT PRIMARY KEY AUTO_INCREMENT,
        input_type VARCHAR(16),
        extracted_text TEXT,
        grade VARCHAR(16),
        category VARCHAR(32),
        score FLOAT,
        p_nlp FLOAT DEFAULT 0,
        p_url FLOAT DEFAULT 0,
        p_gemini FLOAT,
        p_vlm FLOAT,
        urls TEXT,
        url_details TEXT,
        risk_keywords TEXT,
        text_reasons TEXT,
        url_reasons TEXT,
        gemini_reason TEXT,
        vlm_signals TEXT,
        vlm_reason TEXT,
        created_at DOUBLE
    )""")
    for col, definition in [
        ("category_confidence", "FLOAT DEFAULT 0"),
        ("p_url_raw", "FLOAT DEFAULT 0"),
        ("p_nlp", "FLOAT DEFAULT 0"),
        ("p_url", "FLOAT DEFAULT 0"),
        ("p_gemini", "FLOAT"),
        ("p_vlm", "FLOAT"),
        ("url_details", "TEXT"),
        ("text_reasons", "TEXT"),
        ("url_reasons", "TEXT"),
        ("vlm_signals", "TEXT"),
        ("vlm_reason", "TEXT"),
        ("gemini_reason", "TEXT"),
    ]:
        try:
            cursor.execute(f"ALTER TABLE analysis_log ADD COLUMN {col} {definition}")
        except Exception:
            pass
    con.commit()
    cursor.close()
    con.close()

def _log_analysis(input_type: str, extracted_text: str, analysis: dict, grade: str,
                   score: float, urls: list, p_gemini, p_vlm,
                   gemini_result: dict, vlm_result: dict):
    import json as _json
    try:
        cat = analysis.get('category', {})
        nlp = analysis.get('nlp_analysis', {})
        url_an = analysis.get('url_analysis', {})
        scores = analysis.get('scores', {})

        url_details = []
        for u in url_an.get('analyzed_urls', []):
            d = u.get('details', {})
            resolve = d.get('resolve', {})
            vt = d.get('virustotal', {})
            whois = d.get('whois', {})
            features = d.get('features', {})
            feed = d.get('feed_result', {})
            url_details.append({
                'original_url': d.get('original_url', ''),
                'final_url': d.get('final_url', ''),
                'resolve_error': resolve.get('error'),
                'redirect_fail_reason': resolve.get('redirect_fail_reason'),
                'feed_hit': feed.get('is_feed_hit', False),
                'feed_source': feed.get('source', ''),
                'feed_score': d.get('feed_score', 0),
                'vt_positive': vt.get('positive_count', 0),
                'vt_harmless': vt.get('harmless_count', 0),
                'vt_total': vt.get('total_count', 0),
                'vt_score': d.get('virustotal_score', 0),
                'features_score': d.get('features_score', 0),
                'features': features,
                'whois_age_days': whois.get('age_days', -1),
                'whois_score': d.get('whois_score', 0),
                'apk_score': d.get('apk_score', 0),
                'weighted_avg': d.get('weighted_avg', 0),
                'max_score': d.get('max_score', 0),
                'p_url': u.get('p_url', 0),
            })

        con = get_db_conn()
        cursor = con.cursor()
        cursor.execute(
            """INSERT INTO analysis_log
               (input_type, extracted_text, grade, category, category_confidence,
                score, p_nlp, p_url, p_url_raw, p_gemini, p_vlm,
                urls, url_details, risk_keywords, text_reasons, url_reasons,
                gemini_reason, vlm_signals, vlm_reason, created_at)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (
                input_type,
                (extracted_text or '')[:2000],
                grade,
                cat.get('category', ''),
                cat.get('category_confidence', 0.0),
                score,
                scores.get('p_nlp', 0.0),
                scores.get('p_url', 0.0),
                scores.get('p_url_raw', 0.0),
                p_gemini,
                p_vlm,
                _json.dumps(urls, ensure_ascii=False),
                _json.dumps(url_details, ensure_ascii=False),
                _json.dumps(nlp.get('risk_keywords', []), ensure_ascii=False),
                _json.dumps(analysis.get('text_reasons', []), ensure_ascii=False),
                _json.dumps(analysis.get('url_reasons', []), ensure_ascii=False),
                (gemini_result.get('reason', '') if gemini_result else ''),
                _json.dumps(vlm_result.get('visual_signals', []) if vlm_result else [], ensure_ascii=False),
                (vlm_result.get('reason', '') if vlm_result else ''),
                time.time(),
            )
        )
        con.commit()
        cursor.close()
        con.close()
    except Exception as e:
        print(f"[DB] 분석 로그 저장 실패: {e}")


def _get_last_recheck() -> float:
    try:
        con = get_db_conn()
        cursor = con.cursor()
        cursor.execute("SELECT value FROM app_meta WHERE `key` = 'last_recheck'")
        row = cursor.fetchone()
        cursor.close()
        con.close()
        return row[0] if row else 0.0
    except Exception:
        return 0.0


def _mark_recheck_done():
    try:
        con = get_db_conn()
        cursor = con.cursor()
        cursor.execute(
            "REPLACE INTO app_meta (`key`, value) VALUES ('last_recheck', %s)",
            (time.time(),)
        )
        con.commit()
        cursor.close()
        con.close()
    except Exception as e:
        print(f"[Recheck] last_recheck 저장 실패: {e}")


def _load_url_counter() -> Counter:
    _init_db()
    con = get_db_conn()
    cursor = con.cursor()
    cursor.execute("SELECT url, count FROM url_counts")
    rows = cursor.fetchall()
    cursor.close()
    con.close()
    return Counter({url: count for url, count in rows})

def _normalize_url_key(url: str) -> str:
    """프로토콜 제거 + 끝 슬래시 제거 → DB 키 정규화"""
    return re.sub(r'^https?://', '', url).rstrip('/')

def _record_url_to_db(url: str, category: str, original_feed_hit: bool = False,
                      original_vt_positive: int = 0, resolve_error: bool = False):
    key = _normalize_url_key(url)
    con = get_db_conn()
    cursor = con.cursor()
    cursor.execute(
        """INSERT INTO url_counts (url, category, count, original_feed_hit, original_vt_positive, resolve_error, first_seen)
           VALUES (%s, %s, 1, %s, %s, %s, %s)
           ON DUPLICATE KEY UPDATE count=count+1, category=VALUES(category)""",
        (key, category, int(original_feed_hit), original_vt_positive, int(resolve_error), time.time())
    )
    con.commit()
    cursor.close()
    con.close()

url_counter = _load_url_counter()


# =============================================================
# 피드 갱신 (OpenPhish + URLhaus)
# =============================================================

def _fetch_and_store_phishingdb():
    try:
        resp = requests.get(
            "https://raw.githubusercontent.com/mitchellkrogza/Phishing.Database/master/phishing-links-ACTIVE.txt",
            timeout=30
        )
        resp.raise_for_status()
        urls = {line.strip() for line in resp.text.splitlines()
                if line.strip().startswith("http")}
        url_analyzer.phishingdb_urls = urls
        print(f"[Feed] Phishing.Database 갱신 완료 ({len(urls)}개)")
    except Exception as e:
        print(f"[Feed] Phishing.Database 갱신 실패: {e}")


def _fetch_and_store_urlhaus():
    try:
        resp = requests.get("https://urlhaus.abuse.ch/downloads/csv_recent/", timeout=30)
        resp.raise_for_status()

        content_type = resp.headers.get("Content-Type", "")
        raw = resp.content

        if "zip" in content_type or raw[:2] == b'PK':
            zf = zipfile.ZipFile(io.BytesIO(raw))
            content = zf.read(zf.namelist()[0]).decode("utf-8", errors="ignore")
        else:
            content = raw.decode("utf-8", errors="ignore")

        if content.strip().startswith("<"):
            print("[Feed] URLhaus 갱신 실패: 서버가 HTML 응답 반환 (rate limit 또는 접근 차단)")
            return

        new_urls = set()
        new_domains = set()
        for line in content.splitlines():
            if line.startswith("#") or not line.strip():
                continue
            parts = line.split('","')
            if len(parts) < 3:
                continue
            url = parts[2].strip('"')
            if not url.startswith("http"):
                continue
            new_urls.add(url)
            try:
                domain = urlparse(url).netloc.lower()
                if domain.startswith("www."):
                    domain = domain[4:]
                if domain:
                    new_domains.add(domain)
            except Exception:
                pass

        if not new_urls:
            print("[Feed] URLhaus 갱신 실패: 파싱된 URL이 없음 (응답 형식 확인 필요)")
            return

        url_analyzer.urlhaus_urls = new_urls
        url_analyzer.urlhaus_domains = new_domains
        print(f"[Feed] URLhaus 갱신 완료 ({len(new_urls)}개)")
    except Exception as e:
        print(f"[Feed] URLhaus 갱신 실패: {e}")


def _update_feeds():
    _fetch_and_store_phishingdb()
    _fetch_and_store_urlhaus()


paddle_reader = PaddleOCR(
    use_angle_cls=True, lang='korean',
    det_db_thresh=0.2, det_db_box_thresh=0.5,
)

# OCR 오인식 패턴 포함한 URL 추출 정규식
URL_RE = re.compile(
    r"http[s]?://\S+"
    r"|http[s]?:ll\S+"
    r"|http[s]?:[/\\]{1,2}\S+"
    r"|(?<!\w)[a-zA-Z0-9][-a-zA-Z0-9.]*\.(?:com|net|org|kr|ly|me|io|app|link|cc)(?:/\S*)?"
)

INVALID_DOMAINS = {"www", "http", "https", "ftp"}


# =============================================================
# NLP 위험도 스코어링 (팀원 코드 통합)
# KISA 2024 통계 + ASEC 2024 Q2 + 김창형 외(2025) 논문 기반
# =============================================================

# [논문] Urgency — 긴박감 조성 표현 (김창형 외, 2025 심리적 압박 키워드)
_URGENCY = {
    "즉시": 3, "긴급": 3, "당장": 3, "지금 바로": 3, "지금당장": 3,
    "빨리": 2, "서두르": 2, "24시간": 2, "오늘까지": 2, "금일": 2,
}

# [논문] Threat — 부정적 결과 위협 표현 (김창형 외, 2025)
_THREAT = {
    "정지": 3, "차단": 3, "삭제": 3, "압류": 3, "체납": 3,
    "계좌 정지": 3, "서비스 중단": 3, "비정상": 2,
    "만료": 2, "소멸": 2, "해지": 2, "제한": 2,
}

# [논문] Call to Action — 행동 유도 표현, 악성 앱 설치 유도 최고 가중치 (김창형 외, 2025)
_ACTION = {
    "확인 바람": 2, "확인하세요": 2, "클릭": 2, "접속하": 2,
    "재인증": 2, "인증 필요": 2, "다운로드": 2, "설치": 2,
    "로그인": 1, "인증": 1, "링크": 1, "눌러": 1, "조회": 1,
}

# [KISA 유형별 통계] 카테고리별 스미싱 공식 패턴
# DELIVERY: 65~85% (KISA 2024)
# GOVERNMENT: 53.4%, 전년 대비 1,874% 급증 (KISA 2023→2024)
# FINANCE: 16.8%, 신한카드 사칭 최다 (ASEC 2024 Q2)
_CATEGORY_KEYWORDS = {
    "FINANCE": {
        "계좌 인증": 3, "미승인 거래": 3, "카드 발급": 3,
        "신용 조회": 2, "이체": 2, "출금": 2, "비밀번호": 2, "보안카드": 2, "대출": 2,
    },
    "DELIVERY": {
        "주소지 불명": 3, "배송 불가": 3, "수령 확인": 3,
        "배송 지연": 2, "재배송": 2, "미수령": 2, "반송": 2, "배송 조회": 2, "주소 오류": 2, "주소 변경": 2,
    },
    "GOVERNMENT": {
        "과태료": 3, "범칙금": 3, "세금 환급": 3, "소환": 3,
        "고지서": 2, "벌금": 2, "경찰청": 2, "검찰": 2, "세무청": 2, "환경부": 2, "건강보험공단": 2, "교통민원24": 2, "국민건강보험공단": 2,
    },
    "PROMOTION": {
        "공모주": 3, "IPO": 3, "고수익": 3, "수익률": 3,
        "당첨": 2, "무료": 2, "단기 알바": 2, "취업": 2, "투자": 2,
    },
    "AUTH": {
        "계정 위반": 3, "계정 정지 예정": 3, "비밀번호 변경": 3,
        "재인증": 2, "보안 확인": 2, "인증번호": 2, "OTP": 2, "해킹": 2,
    },
    "WORK": {
        "청첩장": 3, "부음": 3, "장례식": 3,
        "계약서": 2, "첨부파일": 2, "파일": 1,
    },
    "PERSONAL": {},
}
_MAX_SCORE = 12


# =============================================================
# Gemini Vision (VLM 시각 분석)
# =============================================================

GEMINI_API_KEY = "AIzaSyCSJgF1kz_O7jiQjnqwaxQuY4OtzGGRn2g"
_gemini_client = None


def _get_gemini():
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = google_genai.Client(api_key=GEMINI_API_KEY)
    return _gemini_client


def _gemini_generate(contents: list, retries: int = 2) -> str | None:
    import time as _time
    client = _get_gemini()
    for attempt in range(retries + 1):
        try:
            response = client.models.generate_content(
                model="gemini-3.1-flash-lite",
                contents=contents,
            )
            return response.text
        except Exception as e:
            msg = str(e)
            if "503" in msg and attempt < retries:
                _time.sleep(3)
                continue
            print(f"[Gemini] 분석 실패 (시도 {attempt+1}): {e}")
            return None


async def _gemini_generate_async(contents: list, retries: int = 2) -> str | None:
    return await asyncio.to_thread(_gemini_generate, contents, retries)


def _build_url_context(analyzed_urls: list) -> str:
    """URL 분석 결과를 Gemini 프롬프트용 문자열로 변환"""
    from urllib.parse import unquote
    lines = []
    for result in analyzed_urls:
        d = result.get('details', {})
        orig = d.get('original_url', '')
        final = d.get('final_url', orig)
        resolve = d.get('resolve', {})
        vt = d.get('virustotal', {})
        whois = d.get('whois', {})

        final_decoded = unquote(final) if final else final

        line = f"- {orig}"
        if final_decoded and final_decoded != orig:
            line += f" → {final_decoded}"
        if resolve.get('error'):
            line += f" (연결 실패)"
        else:
            line += " (연결 정상)"
        if vt.get('is_malicious'):
            line += f" [보안 엔진 {vt['positive_count']}개 악성 탐지]"
        age = whois.get('age_days', -1)
        if age >= 0:
            years = age // 365
            months = (age % 365) // 30
            age_str = f"{years}년 {months}개월" if years > 0 else f"{months}개월"
            line += f" [도메인 생성 {age_str}]"
        lines.append(line)
    return "\n".join(lines)


async def analyze_text_vlm(text: str, url_context: str = "") -> dict:
    import json as _json, re as _re
    result = {"gemini_smishing_score": 0.0, "reason": "", "success": False}
    if not text or not text.strip():
        return result
    try:
        url_part = f"\n\n[추출된 URL 정보]\n{url_context}" if url_context else ""
        resp = await _gemini_generate_async([
            "아래는 한국 휴대폰 문자 메시지입니다. 스미싱(SMS 피싱) 여부를 0.0~1.0으로 판단하세요.\n"
            "스미싱(높은 점수 0.7~1.0): 금전·계좌·개인정보 직접 요구, APK 설치 유도, "
            "기관사칭+비공식URL, 투자 유인 문구, 배송·결제 사칭+비공식 단축URL\n"
            "정상(낮은 점수 0.0~0.3): 공식 기업 쿠폰·포인트·구독 만료 안내, 배송 현황, "
            "공공기관 공지, 정부기관+go.kr 도메인\n"
            "핵심: 발신자 이름이 아닌 무엇을 요구하는가로 판단\n"
            "영어 문자도 동일 기준 적용: 계정 인증 요구·개인정보 입력 유도·상품 당첨 사칭 등은 스미싱으로 판단\n"
            "URL 판단 기준: bit.ly·onelink.me·me2.kr 등 단축URL·앱링크 서비스는 중간 도메인 자체로 신뢰도를 판단하지 마세요. "
            "[추출된 URL 정보]에 '→'로 표시된 최종 도착지가 공식 기업 사이트(예: musinsa.com, coupang.com 등)라면 안전한 링크로 판단하세요. "
            "reason에는 중간 도메인이 아닌 최종 도착지 기준으로 설명하세요. "
            "최종 도착지가 naver.com·google.com 등 검색엔진인 경우, reason에 어떤 검색어로 연결되는지 구체적으로 언급하세요 (예: '네이버에서 \"에뛰드데이 1월\"을 검색하는 링크로 안전합니다').\n"
            "안전 판단(smishing_score 0.3 이하) 시 reason 규칙: '사칭'이라는 단어를 절대 사용하지 마세요. '~로 보이는 문자', '~에서 보낸 것으로 판단되는 문자' 등 중립적 표현만 사용하세요. "
            "단, 학교·대학·교육기관에서 보낸 것으로 판단되는 문자에 한해서만 발신 번호가 해당 기관의 공식 번호인지 확인해볼 것을 권장하는 문구를 추가하세요.\n"
            "네이버 밴드·카카오톡 오픈채팅·카페·커뮤니티 초대 링크처럼 지인이 보낸 것으로 보이는 문자에 한해, reason 마지막에 '발신자가 아는 사람인지 확인해보세요'를 추가하세요.\n"
            "JSON만 반환 (설명 없이): {\"smishing_score\": 0.0~1.0, \"reason\": \"한 줄 요약\"}\n\n"
            f"문자 내용:\n{text}"
            + url_part
        ])
        if resp:
            m = _re.search(r'\{.*\}', resp, _re.DOTALL)
            if m:
                data = _json.loads(m.group())
                result["gemini_smishing_score"] = round(float(data.get("smishing_score", 0.0)), 4)
                result["reason"] = data.get("reason", "")
                result["success"] = True
    except Exception as e:
        print(f"[Gemini Text] 분석 실패: {e}")
    return result


async def analyze_image_and_text_combined(img_bytes: bytes, text: str) -> dict:
    """이미지 VLM 분석 + 텍스트 스미싱 판단을 한 번의 Gemini 호출로 처리"""
    import json as _json, re as _re
    result = {
        "vlm":  {"vlm_smishing_score": 0.0, "visual_signals": [], "reason": "", "success": False},
        "text": {"gemini_smishing_score": 0.0, "reason": "", "success": False},
    }
    try:
        image = PIL.Image.open(io.BytesIO(img_bytes))
        has_text = bool(text and text.strip())
        text_part = f"\n\n추출된 문자 내용:\n{text}" if has_text else "\n\n(인식된 텍스트 없음)"
        resp = await _gemini_generate_async([
            image,
            "이 이미지는 스미싱/큐싱 탐지를 위한 휴대폰 문자 또는 QR코드 스크린샷입니다.\n"
            "아래 두 가지를 동시에 분석해 JSON만 반환하세요 (설명 없이):\n"
            "1. 이미지 시각적 위협 신호 (레이아웃, 색상, 로고, QR 등)\n"
            "2. 추출된 텍스트의 스미싱 여부\n"
            "스미싱(높은 점수 0.7~1.0): 금전·계좌·개인정보 직접 요구, APK 설치 유도, "
            "기관사칭+비공식URL, 투자 유인 문구, 배송·결제 사칭+비공식 단축URL\n"
            "정상(낮은 점수 0.0~0.3): 공식 기업 쿠폰·포인트·구독 만료 안내, 배송 현황, "
            "공공기관 공지, 정부기관+go.kr 도메인\n"
            "핵심: 발신자 이름이 아닌 무엇을 요구하는가로 판단\n"
            "영어 문자도 동일 기준 적용: 계정 인증 요구·개인정보 입력 유도·상품 당첨 사칭 등은 스미싱으로 판단\n"
            "URL 판단 기준: bit.ly·onelink.me·me2.kr 등 단축URL·앱링크 서비스는 중간 도메인 자체로 신뢰도를 판단하지 마세요. "
            "추출된 URL 정보에서 '→'로 표시된 최종 도착지가 공식 기업 사이트라면 안전한 링크로 판단하세요. "
            "reason에는 중간 도메인이 아닌 최종 도착지 기준으로 설명하세요. "
            "최종 도착지가 naver.com·google.com 등 검색엔진인 경우, reason에 어떤 검색어로 연결되는지 구체적으로 언급하세요 (예: '네이버에서 \"에뛰드데이 1월\"을 검색하는 링크로 안전합니다').\n"
            "안전 판단(text_smishing_score 0.3 이하) 시 text_reason 규칙: '사칭'이라는 단어를 절대 사용하지 마세요. '~로 보이는 문자', '~에서 보낸 것으로 판단되는 문자' 등 중립적 표현만 사용하세요. "
            "단, 학교·대학·교육기관에서 보낸 것으로 판단되는 문자에 한해서만 발신 번호가 해당 기관의 공식 번호인지 확인해볼 것을 권장하는 문구를 추가하세요.\n"
            "네이버 밴드·카카오톡 오픈채팅·카페·커뮤니티 초대 링크처럼 지인이 보낸 것으로 보이는 문자에 한해, text_reason 마지막에 '발신자가 아는 사람인지 확인해보세요'를 추가하세요.\n\n"
            '{"vlm_smishing_score": 0.0~1.0, "visual_signals": ["신호1"], "vlm_reason": "시각 분석 요약", '
            '"text_smishing_score": 0.0~1.0, "text_reason": "텍스트 분석 요약"}\n\n'
            "시각적 위협 신호 예시: 긴박감 조성 색상(빨강/경고), 공공기관·은행 사칭 로고, 의심 QR코드, 링크·버튼 클릭 유도 레이아웃"
            + text_part
        ])
        if resp:
            m = _re.search(r'\{.*\}', resp, _re.DOTALL)
            if m:
                data = _json.loads(m.group())
                result["vlm"]["vlm_smishing_score"] = round(float(data.get("vlm_smishing_score", 0.0)), 4)
                result["vlm"]["visual_signals"] = data.get("visual_signals", [])
                result["vlm"]["reason"] = data.get("vlm_reason", "")
                result["vlm"]["success"] = True
                if has_text:
                    result["text"]["gemini_smishing_score"] = round(float(data.get("text_smishing_score", 0.0)), 4)
                    result["text"]["reason"] = data.get("text_reason", "")
                    result["text"]["success"] = True
    except Exception as e:
        print(f"[Gemini Combined] 분석 실패: {e}")
    return result


def score_text(text: str, category: str) -> dict:
    """KISA 2024 + ASEC 2024 Q2 + 김창형 외(2025) 논문 기반 텍스트 위험도 스코어링"""
    matched = []
    total = 0

    normalized = re.sub(r'[^\w\s가-힣]', '', text, flags=re.UNICODE)

    def check(kw_dict: dict, label: str):
        nonlocal total
        for kw, weight in kw_dict.items():
            if kw in text or kw in normalized:
                matched.append({"keyword": kw, "type": label, "weight": weight})
                total += weight

    check(_URGENCY, "urgency")
    check(_THREAT, "threat")
    check(_ACTION, "action")
    check(_CATEGORY_KEYWORDS.get(category, {}), "category_pattern")

    return {
        "text_risk_score": round(min(total / _MAX_SCORE, 1.0), 4),
        "risk_keywords": matched,
    }


def calculate_p_nlp(text_risk_score: float) -> float:
    """
    P_NLP 계산

    공식: P_NLP = text_risk_score × 10
    """
    return round(text_risk_score * 10, 4)


# =============================================================
# 최종 위험도 계산 (S = P_NLP × 0.4 + P_URL × 0.6)
# =============================================================


def calculate_final_score_v2(
    p_nlp: float, p_url: float, has_url: bool,
    p_gemini: float | None = None,
    p_vlm: float | None = None,
    is_image: bool = False,
    is_qr: bool = False,
    vt_confirmed_safe: bool = False,
    vt_found: bool = False,
    p_url_raw: float | None = None,
) -> dict:
    """
    최종 위험도 S 계산
    1차 분기: 신호 강도 (URL 강함 → 중간 → VT 안전 확인 → 신호 없음)
    2차 분기: Gemini/VLM 가용 여부
    """
    g = p_gemini is not None
    v = p_vlm is not None

    # 분기 결정은 raw 점수 기준 (카테고리 가중치 영향 제거)
    _br = p_url_raw if p_url_raw is not None else p_url

    # VT 미등록 도메인 p_url 소폭 상향 (unknown = 약한 위험 신호)
    if has_url and not vt_found and p_url < 4.0:
        p_url = min(p_url + 0.5, 10.0)

    if is_qr:
        s = (p_url*0.65 + p_vlm*0.35) if v else p_url

    # ── [2] URL 강함 (raw ≥ 4.0): URL 압도적 주도 ───────────────
    elif has_url and _br >= 4.0:
        if g and v: s = p_url*0.75 + p_gemini*0.15 + p_vlm*0.05 + p_nlp*0.05
        elif g:     s = p_url*0.80 + p_gemini*0.10 + p_nlp*0.10
        elif v:     s = p_url*0.80 + p_vlm*0.10    + p_nlp*0.10
        else:       s = p_url*0.60 + p_nlp*0.40

    # ── [3] URL 중간 (1.5 ≤ raw < 4.0, VT 미확인): URL + Gemini 종합
    elif has_url and _br >= 1.5 and not vt_confirmed_safe:
        if g and v: s = p_url*0.45 + p_gemini*0.30 + p_vlm*0.15 + p_nlp*0.10
        elif g:     s = p_url*0.45 + p_gemini*0.40 + p_nlp*0.15
        elif v:     s = p_url*0.50 + p_vlm*0.30    + p_nlp*0.20
        else:       s = p_url*0.55 + p_nlp*0.45

    # ── [4] VT 안전 확인 URL (raw < 1.5) ────────────────────────
    elif has_url and _br < 1.5 and vt_confirmed_safe:
        _g_high = g and (p_gemini or 0) >= 7.0
        if _g_high:  # [4b] Gemini가 URL 비공식 등 강하게 의심 → Gemini 비중 높임
            if g and v: s = p_gemini*0.40 + p_vlm*0.20 + p_nlp*0.30 + p_url*0.10
            elif g:     s = p_gemini*0.45 + p_nlp*0.40 + p_url*0.15
            elif v:     s = p_vlm*0.40    + p_nlp*0.45 + p_url*0.15
            else:       s = p_nlp*0.70    + p_url*0.30
        else:        # [4a] VT 안전, Gemini 텍스트 주도, NLP 보조 (Gemini 실패 시 NLP 폴백)
            if g and v: s = p_gemini*0.45 + p_vlm*0.15 + p_nlp*0.20 + p_url*0.20
            elif g:     s = p_gemini*0.50 + p_nlp*0.25 + p_url*0.25
            elif v:     s = p_vlm*0.25    + p_nlp*0.50 + p_url*0.25
            else:       s = p_nlp*0.70    + p_url*0.30
            if (p_url_raw or 0.0) == 0.0 and p_nlp < 6.0:
                s = min(s, 3.9)

    # ── [5] URL 없음 / p_url=0 / VT 미확인 ──────────────────────
    else:
        if has_url:
            if g and v: s = p_gemini*0.35 + p_vlm*0.25 + p_nlp*0.30 + p_url*0.10
            elif g:     s = p_gemini*0.35 + p_nlp*0.45 + p_url*0.20
            elif v:     s = p_vlm*0.40    + p_nlp*0.45 + p_url*0.15
            else:       s = p_nlp*0.60    + p_url*0.40
        else:
            if g and v: s = p_gemini*0.50 + p_vlm*0.30 + p_nlp*0.20
            elif g:     s = p_gemini*0.70 + p_nlp*0.30
            elif v:     s = p_vlm*0.60    + p_nlp*0.40
            else:       s = p_nlp

    s = round(min(max(s, 0.0), 10.0), 4)

    if has_url and not is_qr:
        if p_url >= 6.0:
            s = max(s, 7.0)
        elif p_url >= 3.5:
            s = max(s, 4.0)
        # VT 악성 탐지 확인 + Gemini 의심 → Danger 보장
        if vt_found and not vt_confirmed_safe and g and (p_gemini or 0) >= 5.0:
            s = max(s, 7.0)

    if s >= 7.0:
        grade, message = "Danger", "스미싱 강력 의심. 링크를 절대 클릭하지 마세요."
    elif s >= 3.5:
        grade, message = "Warning", "의심스러운 패턴이 감지되었습니다. 주의가 필요합니다."
    else:
        grade, message = "Safe", "정상 문자로 판단됩니다."

    return {'score': round(s, 2), 'grade': grade, 'message': message}


# =============================================================
# OCR / URL 처리 함수들
# =============================================================

def normalize_url(url: str) -> str:
    """OCR 오인식된 URL 정규화"""
    url = re.sub(r'^(http[s]?):ll', r'\1://', url)
    url = re.sub(r'^(http[s]?):[/\\]{1,2}', r'\1://', url)
    url = re.sub(r'^(http[s]?):[Il1\[]{1,2}', r'\1://', url)
    url = re.sub(r'^(http[s]?):([Il1])/', r'\1://', url)
    url = re.sub(r'(https?://)([Il1])(/)', r'\1/\3', url)
    url = re.sub(r'(\w)\[(\w)', r'\1.\2', url)
    url = re.sub(r'(\w)\](\w)', r'\1.\2', url)
    url = re.sub(r'(https?://)www([a-zA-Z])', r'\1www.\2', url)
    url = re.sub(r'([a-zA-Z])(cor)(/|$)', r'\1.com\3', url)
    url = re.sub(r'([a-zA-Z])(com|net|org|kr)(/|$)', r'\1.\2\3', url)
    url = re.sub(r'/([a-z]{2})l$', r'/\1/', url)
    url = re.sub(r'[)\]},;\'\"]+$', '', url)
    url = re.sub(r'[가-힣]+$', '', url)
    return url


def is_valid_url(url: str) -> bool:
    try:
        parsed = urlparse(url if url.startswith("http") else "http://" + url)
        netloc = parsed.netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        elif netloc.startswith("m."):
            netloc = netloc[2:]
        if not netloc or netloc in INVALID_DOMAINS:
            return False
        if "." not in netloc and len(netloc) < 4:
            return False
        return True
    except Exception:
        return False


def _join_multiline_url(text: str) -> str:
    """OCR이 줄바꿈으로 분리한 URL 조각을 재결합 (최대 8회 반복)"""
    for _ in range(8):
        prev = text
        # http://xxx .domain/path → http://xxx.domain/path
        text = re.sub(r'(https?://\S+)\s+\.([a-zA-Z0-9]\S*)', r'\1.\2', text)
        # http://xxx /path → http://xxx/path
        text = re.sub(r'(https?://\S+)\s+(/\S+)', r'\1\2', text)
        # http://xxx/path alphanumeric{6+}/rest → 줄바꿈으로 나뉜 경로 이어붙이기
        text = re.sub(r'(https?://[^\s]+[a-zA-Z0-9])\s+([a-zA-Z0-9][a-zA-Z0-9_\-]{5,}/\S+)', r'\1\2', text)
        # http://xxx. + domain.tld/path → URL이 점으로 끝나고 다음 토큰이 도메인인 경우
        text = re.sub(r'(https?://[^\s]+\.)\s+([a-zA-Z][a-zA-Z0-9\-]+\.[a-zA-Z]{2,}\S*)', r'\1\2', text)
        # http://xxx/f + 7RKswWpz1b → 단일문자 경로 뒤 연속 토큰 이어붙이기
        text = re.sub(r'(https?://[^\s]+/[a-zA-Z0-9]{1})\s+([a-zA-Z0-9]{5,})(\s|$)', r'\1\2\3', text)
        # http://xxx/ + path → URL이 /로 끝나고 다음 토큰이 경로 조각인 경우
        text = re.sub(r'(https?://[^\s]+/)\s+([a-zA-Z][a-zA-Z0-9_\-\.]*(?:[/?]\S*)?)', r'\1\2', text)
        # http://xxx& + query → URL이 &나 ?로 끝나고 다음 토큰이 쿼리 파라미터인 경우
        text = re.sub(r'(https?://\S+[&?])\s+([a-zA-Z][a-zA-Z0-9_=&%]+)', r'\1\2', text)
        # http://xxx= + value → = 뒤 공백으로 분리된 쿼리값 이어붙이기 (예: ?list= PLRz...)
        text = re.sub(r'(https?://\S+=)\s+([a-zA-Z0-9_\-]{3,})', r'\1\2', text)
        # http://xxx- + path → - 뒤 공백으로 분리된 경로 이어붙이기 (예: 26-05-06-AI- 33e4b...)
        text = re.sub(r'(https?://\S+-)\s+([a-zA-Z0-9]{4,})(\s|$)', r'\1\2\3', text)
        # http://xxx[alphanum] + token_with_& → 쿼리 파라미터 조각이 &= 포함하며 이어지는 경우
        text = re.sub(r'(https?://\S+[a-zA-Z0-9])\s+([a-zA-Z0-9_\-]{4,}[&=]\S*)', r'\1\2', text)
        # http://xxx .ext (끝 확장자)
        text = re.sub(r'(https?://\S+)\s+(\.[a-zA-Z]{2,6})(\s|$)', lambda m: m.group(1) + m.group(2) + m.group(3), text)
        # bare domain (xxx.kr/path) + space + 슬래시 포함 경로 조각 (예: airport.kr/ap + ko/1027/subview.)
        text = re.sub(
            r'((?<!\w)[a-zA-Z0-9][-a-zA-Z0-9.]*\.(?:com|net|org|kr)/\S*[a-zA-Z0-9])\s+([a-zA-Z0-9][a-zA-Z0-9_\-]*(?:/\S*)+)',
            r'\1\2', text
        )
        # bare domain path 끝 마침표 + space + 확장자 (예: subview. do → subview.do)
        text = re.sub(
            r'((?<!\w)[a-zA-Z0-9][-a-zA-Z0-9.]*\.(?:com|net|org|kr)\S*\.)\s+([a-zA-Z]{2,6})(\s|$)',
            lambda m: m.group(1) + m.group(2) + m.group(3), text
        )
        if text == prev:
            break
    return text


def correct_text(text):
    text = re.sub(r'https?:l\s+', 'https://', text)
    text = re.sub(r'https?://\s+', 'https://', text)
    text = re.sub(r'https?l[I1l]\s*', 'https://', text)
    text = re.sub(r'https?:[I1l]{2}\s*', 'https://', text)
    text = re.sub(r'ht\s+tp(s?)://', r'http\1://', text)
    text = re.sub(r'https?\s*:\s*//\s*', 'https://', text)
    text = re.sub(r'https?:/\s+/', 'https://', text)
    text = re.sub(r'(https?:)[Il1\[]{1,2}', r'\1//', text)
    text = re.sub(r'(https?://)([Il1])(/)', r'\1/\3', text)
    text = re.sub(r'(https?://[^\s]*\w)\[(\w)', r'\1.\2', text)
    text = re.sub(r'(https?://[^\s]*\w)\](\w)', r'\1.\2', text)
    text = re.sub(r'([a-zA-Z])(com|net|org|kr)(\s|/|$)', r'\1.\2\3', text)
    text = re.sub(r'([a-zA-Z])(cor)(\s|/|$)', r'\1.com\3', text)
    text = re.sub(r'\bwww([a-zA-Z])', r'www.\1', text)
    # www. + 줄바꿈 + 도메인 이어붙이기 (예: www. lotteglogisplus.com → www.lotteglogisplus.com)
    text = re.sub(r'\bwww\.\s+([a-zA-Z0-9])', r'www.\1', text)
    # ► / ▶ 기호가 직접 인식된 경우
    text = re.sub(r'[►▶]\s*https?://', 'https://', text)
    # ► 가 ) + h 로 오인식된 경우 (예: )htps://, )https://)
    text = re.sub(r'\)htps://', 'https://', text)
    text = re.sub(r'\)https?://', 'https://', text)
    # htps:// (t 하나 누락)
    text = re.sub(r'\bhtps://', 'https://', text)
    # nttps:// (h → n 오인식)
    text = re.sub(r'\bnttps?://', 'https://', text)
    # https:!| or https:|| (// → !| or || 오인식)
    text = re.sub(r'\bhttps?:[!|]{1,2}', 'https://', text)
    text = _join_multiline_url(text)
    # 메시지 앱 시스템 UI 문구 제거 (OCR 오탐 방지)
    text = re.sub(r'저장되지 않은 번호에서 온 메시지입니다\.?\s*', '', text)
    text = re.sub(r'스미싱이나 피싱에 유의하세요\.?\s*', '', text)
    text = re.sub(r'수신 차단\s*', '', text)
    return text


def _ocr_single(img):
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
        tmp_path = tmp.name
        cv2.imwrite(tmp_path, img)
    try:
        result = paddle_reader.predict(tmp_path)
    finally:
        os.remove(tmp_path)

    lines = []
    if result:
        for page in result:
            if not page:
                continue
            if isinstance(page, dict):
                texts = page.get('rec_texts') or page.get('text', [])
                polys = page.get('rec_polys') or page.get('dt_boxes', [])
                for i, text in enumerate(texts):
                    y = polys[i][0][1] if i < len(polys) else i
                    lines.append((y, text))
            else:
                for line in page:
                    try:
                        if isinstance(line[1], (list, tuple)):
                            lines.append((line[0][0][1], line[1][0]))
                        else:
                            lines.append((line[0][0][1], str(line[1])))
                    except Exception:
                        continue
    lines.sort(key=lambda x: x[0])
    return " ".join(text for _, text in lines)


def _has_color_text(img) -> bool:
    """이미지에 채도 높은 컬러 텍스트(파란 링크 등)가 있는지 감지"""
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    saturation = hsv[:, :, 1]
    colored_ratio = np.sum(saturation > 60) / saturation.size
    return colored_ratio > 0.01


def run_paddleocr(img):
    text = _ocr_single(img)
    if _has_color_text(img):
        # 흑백 이진화
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        binary_3ch = cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)
        binary_text = _ocr_single(binary_3ch)

        # R채널 (파란색 텍스트 특화)
        r_channel = img[:, :, 2]
        r_3ch = cv2.cvtColor(r_channel, cv2.COLOR_GRAY2BGR)
        r_text = _ocr_single(r_3ch)

        text = max(text, binary_text, r_text, key=len)
    return text


def is_ocr_garbage(text: str) -> bool:
    """OCR 결과가 판단 불가 수준인지 감지

    공백 기준 토큰 중 한글 2~6자 단어 비율이 30% 미만이면 깨진 것으로 판단
    """
    tokens = [t for t in text.split() if t]
    if not tokens:
        return True
    valid = 0
    for t in tokens:
        korean_chars = re.findall(r'[가-힣]', t)
        if 2 <= len(korean_chars) <= 6:
            valid += 1
    return (valid / len(tokens)) < 0.3


def _clean_and_extract_urls(clean_text: str):
    clean_text = re.sub(
        r'(https?://\S+)\s+(com|net|org|co\.kr|kr|me|io|app|cc|top|site|link)(\s|/|$)',
        r'\1.\2\3', clean_text
    )
    clean_text = re.sub(
        r'(https?://\S+\.(com|net|org|co\.kr|kr|me|io|app|cc|top|site|link))\s+(\[?[A-Za-z0-9_\-]+)',
        lambda m: m.group(1) + '/' + m.group(3).lstrip('['), clean_text
    )
    clean_text = re.sub(
        r'(https?://\S+)\s+\.(me|com|net|org|kr|io|app|cc|top|site|link)(/\S*)?',
        lambda m: m.group(1) + '.' + m.group(2) + (m.group(3) or ''), clean_text
    )

    raw_urls = URL_RE.findall(clean_text)
    text_urls = [
        normalize_url(u) for u in raw_urls
        if is_valid_url(normalize_url(u))
    ]
    clean_text_no_url = URL_RE.sub("", clean_text).strip()
    return text_urls, clean_text_no_url


# =============================================================
# 통합 분석 함수
# =============================================================

# 정부·공공기관 사칭 오버라이드 트리거 키워드 (확실한 기관명만)
# 이 키워드가 있을 때만 GOVERNMENT + URL → 무조건 Danger 처리
# 집행형 정부 키워드 — 이 키워드가 있을 때만 GOVERNMENT + URL → Danger 처리
# 안내형(채용박람회, 건강검진, 공공행사 등)은 URL을 포함해도 정상이므로 제외
ENFORCEMENT_GOVERNMENT_KEYWORDS = [
    "과태료", "범칙금", "체납", "미납", "벌금", "압류", "징수",
    "소환", "출석", "고지서", "세금 환급", "처분",
    "계좌 정지", "압수", "강제",
]


def analyze_full(text: str, urls: list) -> dict:
    """
    텍스트 + URL을 분석해서 P_NLP, P_URL 및 각종 분석 결과 반환
    최종 점수/등급은 엔드포인트에서 calculate_final_score_v2()로 결정

    Args:
        text: URL 제거된 순수 텍스트
        urls: 분석할 URL 리스트

    Returns:
        dict: 카테고리, P_NLP, P_URL, 키워드 등 분석 데이터 (최종 등급 제외)
    """
    # ===== NLP 분석 =====
    category_result = predict(text)
    category = category_result["category"]

    scoring = score_text(text, category)
    text_risk_score = scoring["text_risk_score"]
    p_nlp = calculate_p_nlp(text_risk_score)

    # ===== URL 분석 =====
    url_result = analyze_urls(urls, category, text)
    p_url = url_result["p_url"]
    p_url_raw = url_result.get("p_url_raw", p_url)
    # text_reasons 생성 (risk_keywords 타입 기반)
    TYPE_TO_REASON = {
        'urgency':          '긴박감을 조성하는 표현을 포함하고 있습니다',
        'threat':           '위협적인 표현을 포함하고 있습니다',
        'action':           '링크 클릭 또는 앱 설치를 유도하는 표현이 있습니다',
        'category_pattern': '스미싱에서 자주 쓰이는 표현 패턴이 감지되었습니다',
    }
    seen_types = set()
    text_reasons = []
    for kw in scoring["risk_keywords"]:
        t = kw.get("type", "")
        if t in TYPE_TO_REASON and t not in seen_types:
            text_reasons.append(TYPE_TO_REASON[t])
            seen_types.add(t)
    if not text_reasons:
        text_reasons.append("문자 내용에서 위험 키워드가 감지되지 않았습니다")

    # government_override 플래그 (엔드포인트에서 처리)
    has_enforcement_keyword = any(kw in text for kw in ENFORCEMENT_GOVERNMENT_KEYWORDS)
    government_override = url_result.get('government_url_override', False) and has_enforcement_keyword

    return {
        "category": category_result,
        "nlp_analysis": {
            "text_risk_score": text_risk_score,
            "risk_keywords": scoring["risk_keywords"],
        },
        "url_analysis": url_result,
        "scores": {
            "p_nlp": p_nlp,
            "p_url": p_url,
            "p_url_raw": p_url_raw,
            "final": 0.0,
        },
        "result": {"grade": "", "message": ""},
        "feed_hit": url_result.get("feed_hit", False),
        "text_reasons": text_reasons,
        "url_reasons": list(url_result.get("url_reasons", [])),
        "government_override": government_override,
        "low_confidence_warning": False,
        "safe_reason": None,
    }


def _print_analysis_detail(header: str, analysis: dict, final_result: dict,
                            p_nlp: float, p_url: float, p_gemini, p_vlm=None,
                            urls: list = None, qr_urls: list = None,
                            extracted_text: str = None):
    cat = analysis['category']
    nlp = analysis['nlp_analysis']
    url_analysis = analysis.get('url_analysis', {})
    text_risk = nlp.get('text_risk_score', 0)
    keywords = nlp.get('risk_keywords', [])
    grade = final_result['grade']

    print(f"\n{'='*55}")
    print(f"{header}")
    if extracted_text:
        print(f"  OCR 추출   : {extracted_text.replace(chr(10), ' ')}")
    print(f"  카테고리   : {cat.get('category', '-')} (신뢰도 {cat.get('category_confidence', 0):.4f})")

    # P_NLP
    print(f"\n  [P_NLP = {p_nlp}]")
    print(f"    text_risk_score     : {text_risk:.4f}  × 10 = {text_risk * 10:.4f}")
    if keywords:
        for k in keywords:
            print(f"    키워드 : {k['keyword']} ({k['type']}, +{k['weight']})")
    else:
        print(f"    키워드 : 없음")

    # P_URL
    print(f"\n  [P_URL = {p_url}]")
    analyzed_urls = url_analysis.get('analyzed_urls', [])
    if analyzed_urls:
        for u_res in analyzed_urls:
            details = u_res.get('details', {})
            resolve = details.get('resolve', {})
            orig = details.get('original_url', '-')
            final = resolve.get('final_url', orig)
            print(f"    원본 URL  : {orig}")
            if final != orig:
                print(f"    최종 URL  : {final}")
            elif resolve.get('redirect_fail_reason'):
                reason_map = {
                    'bot_blocked': '봇 차단 (403/429)',
                    'cloudflare': 'Cloudflare 봇 차단',
                    'js_redirect': 'JS 리다이렉트 (requests 추적 불가)',
                    'unknown': '리다이렉트 실패 (원인 불명)',
                }
                print(f"    리다이렉트: 실패 — {reason_map.get(resolve['redirect_fail_reason'], resolve['redirect_fail_reason'])}")
            feed = details.get('feed_result', {})
            print(f"    피드      : {details.get('feed_score', 0):.1f}{'  ← ' + feed.get('source','') if feed.get('is_feed_hit') else ''}")
            vt = details.get('virustotal', {})
            vt_pos = vt.get('positive_count', 0)
            vt_harm = vt.get('harmless_count', 0)
            vt_undet = vt.get('total_count', 0) - vt_pos - vt_harm
            vt_detail = f"악성(m+s)={vt_pos}  harmless={vt_harm}  undetected={vt_undet}"
            print(f"    VT        : {details.get('virustotal_score', 0):.1f}  ({vt_detail})")
            features = details.get('features', {})
            feat_notes = []
            if features.get('is_shortener'):         feat_notes.append('단축URL(+2.0)')
            if features.get('has_suspicious_tld'):   feat_notes.append('의심TLD(+2.0)')
            if features.get('has_ip'):               feat_notes.append('IP직접사용(+2.0)')
            if features.get('has_suspicious_keyword'): feat_notes.append('의심키워드(+1.5)')
            ul = features.get('url_length', 0)
            if ul > 75:    feat_notes.append(f'URL길이{ul}(+1.5)')
            elif ul > 50:  feat_notes.append(f'URL길이{ul}(+0.8)')
            sc = features.get('subdomain_count', 0)
            if sc >= 4:    feat_notes.append(f'서브도메인{sc}(+1.5)')
            elif sc == 3:  feat_notes.append(f'서브도메인{sc}(+0.8)')
            dr = features.get('digit_ratio', 0)
            if dr > 0.3:   feat_notes.append(f'숫자비율{dr:.2f}(+1.2)')
            elif dr > 0.15: feat_notes.append(f'숫자비율{dr:.2f}(+0.6)')
            print(f"    특징      : {details.get('features_score', 0):.1f}  {', '.join(feat_notes) if feat_notes else '해당없음'}")
            whois = details.get('whois', {})
            age = whois.get('age_days', -1)
            print(f"    WHOIS     : {details.get('whois_score', 0):.1f}  ({age}일)" if age >= 0 else f"    WHOIS     : {details.get('whois_score', 0):.1f}  (조회실패)")
            print(f"    APK       : {details.get('apk_score', 0):.1f}")
            print(f"    가중평균  : {details.get('weighted_avg', 0):.2f}  / 최고점: {details.get('max_score', 0):.2f}")
            print(f"    p_url_raw : {u_res.get('p_url', 0):.2f}")
        print(f"    카테고리 가중치 × {url_analysis.get('category_weight', 1.0)}  →  p_url = {p_url}")
    else:
        print(f"    URL 없음")

    print(f"\n  P_Gemini   : {p_gemini}")
    if p_vlm is not None:
        print(f"  P_VLM      : {p_vlm}")
    print(f"  최종 점수  : {final_result['score']}  →  {grade}")
    if qr_urls:
        print(f"  QR URL     : {', '.join(qr_urls)}")
    if urls:
        print(f"  추출 URL   : {', '.join(urls)}")
    print(f"{'='*55}\n")


def _apply_grade_logic(analysis: dict, grade: str, text: str, has_url: bool, p_nlp: float, p_url: float):
    """최종 등급이 결정된 후 등급 의존 로직 적용 (url_reasons, low_confidence_warning, safe_reason)"""
    government_override = analysis.pop("government_override", False)

    url_reasons = analysis["url_reasons"]
    if grade == "Safe":
        url_reasons += analysis.get("url_analysis", {}).get("url_safe_reasons", [])
    if grade in ("Warning", "Danger") and has_url:
        vt_found = analysis.get("url_analysis", {}).get("vt_found", False)
        if not vt_found:
            url_reasons.append("보안 엔진에 등록되지 않은 URL로 주의가 필요합니다")
    if government_override:
        url_reasons.append("정부·공공기관은 공식 문자에 URL을 포함하지 않습니다")
        HEALTH_INSURANCE_KEYWORDS = ["건강보험공단", "국민건강보험", "건강검진"]
        if any(kw in text for kw in HEALTH_INSURANCE_KEYWORDS):
            url_reasons.append("건강검진 안내 문자메시지에는 공단 대표 전화번호만 표시되고, 인터넷 주소는 포함돼 있지 않습니다. 낯선 주소가 있다면 의심해 봐야 합니다.")

    analysis["low_confidence_warning"] = (
        len(analysis["nlp_analysis"]["risk_keywords"]) == 0
        and has_url and p_url < 1.0
        and grade != "Danger"
    )

    safe_reason = None
    if grade == "Safe":
        reasons = []
        if not has_url:
            reasons.append("URL 없음")
        elif p_url < 2.0:
            reasons.append("위험 URL 아님")
        if len(analysis["nlp_analysis"]["risk_keywords"]) == 0:
            reasons.append("위험 패턴 없음")
        elif p_nlp < 2.0:
            reasons.append("위험 패턴 미약")
        safe_reason = " · ".join(reasons) if reasons else "위험 패턴 없음"
    analysis["safe_reason"] = safe_reason

    return government_override


# =============================================================
# 엔드포인트
# =============================================================

@app.post("/analyze")
async def analyze_image(file: UploadFile = File(...)):
    if file.content_type and not file.content_type.startswith("image/") \
            and file.content_type != "application/octet-stream":
        raise HTTPException(
            status_code=400,
            detail="이미지 파일만 업로드 가능합니다."
        )

    try:
        contents = await file.read()
        nparr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            raise HTTPException(
                status_code=400,
                detail="이미지를 읽을 수 없습니다. 파일이 손상되었는지 확인해주세요."
            )

        # ① QR 코드 추출
        qr_results = []
        decoded_objects = decode(img)
        for obj in decoded_objects:
            qr_results.append(normalize_url(obj.data.decode("utf-8")))

        # ② OCR 텍스트 추출
        raw_text = run_paddleocr(img)
        clean_text = correct_text(raw_text)

        # URL 추출
        text_urls, clean_text_no_url = _clean_and_extract_urls(clean_text)

        # QR + 텍스트 URL 통합
        if qr_results and text_urls:
            qr_domains = {normalize_url(u).lower().rstrip("/") for u in qr_results}
            txt_domains = {normalize_url(u).lower().rstrip("/") for u in text_urls}
            all_urls = qr_results if qr_domains == txt_domains else qr_results + text_urls
        elif qr_results:
            all_urls = qr_results
        else:
            all_urls = text_urls

        # OCR 결과 신뢰도 확인
        ocr_failed = is_ocr_garbage(clean_text_no_url) and not all_urls

        # Gemini 통합 분석 (VLM + 텍스트 스미싱 판단 1회 호출, URL 있으면 표시)
        _gemini_text = clean_text_no_url + ("\n추출된 URL: " + ", ".join(all_urls) if all_urls else "")
        _combined = await analyze_image_and_text_combined(contents, _gemini_text)
        vlm_result = _combined["vlm"]

        if ocr_failed:
            return {
                "filename": file.filename,
                "qr_urls": qr_results,
                "text_urls": text_urls,
                "extracted_text": clean_text_no_url,
                "rank": None,
                "ocr_failed": True,
                "vlm_analysis": vlm_result,
                "category": {
                    "category": "UNKNOWN",
                    "category_confidence": 0.0,
                    "smishing_confidence": 0.0,
                },
                "nlp_analysis": {"text_risk_score": 0.0, "risk_keywords": []},
                "url_analysis": {},
                "scores": {"p_nlp": 0.0, "p_url": 0.0, "final": 0.0},
                "result": {"grade": "Unknown", "message": "이미지에서 텍스트를 인식할 수 없습니다. 선명한 이미지로 다시 시도해주세요."},
            }

        # 통합 분석
        analysis = analyze_full(clean_text_no_url, all_urls)

        gemini_text_result = _combined["text"]
        p_gemini = round(gemini_text_result["gemini_smishing_score"] * 10, 4) if gemini_text_result["success"] else None
        p_vlm = round(vlm_result["vlm_smishing_score"] * 10, 4) if vlm_result["success"] else None
        if gemini_text_result["success"] and (
            gemini_text_result["gemini_smishing_score"] < 0.3
            or gemini_text_result["gemini_smishing_score"] >= 0.5
        ):
            analysis["low_confidence_warning"] = False

        # QR 판단: 텍스트 없고 URL 있으면
        is_qr = not clean_text_no_url.strip() and bool(all_urls)
        p_nlp = analysis["scores"]["p_nlp"]
        p_url = analysis["scores"]["p_url"]
        has_url = bool(all_urls)
        vt_confirmed_safe = analysis.get("url_analysis", {}).get("vt_confirmed_safe", False)
        vt_found = analysis.get("url_analysis", {}).get("vt_found", False)
        p_url_raw = analysis["scores"].get("p_url_raw", p_url)

        final_result = calculate_final_score_v2(
            p_nlp=p_nlp, p_url=p_url, has_url=has_url,
            p_gemini=p_gemini, p_vlm=p_vlm,
            is_qr=is_qr,
            vt_confirmed_safe=vt_confirmed_safe, vt_found=vt_found,
            p_url_raw=p_url_raw,
        )
        grade = final_result["grade"]
        analysis["result"] = {"grade": grade, "message": final_result["message"]}
        analysis["scores"]["final"] = final_result["score"]
        _print_analysis_detail(
            header=f"[이미지 분석] {file.filename}",
            analysis=analysis, final_result=final_result,
            p_nlp=p_nlp, p_url=p_url, p_gemini=p_gemini, p_vlm=p_vlm,
            urls=all_urls, qr_urls=qr_results,
            extracted_text=clean_text_no_url,
        )
        government_override = _apply_grade_logic(analysis, grade, clean_text_no_url, has_url, p_nlp, p_url)
        if government_override:
            grade = "Danger"
            analysis["result"] = {"grade": "Danger", "message": "정부기관 사칭 스미싱 의심. 정부·공공기관 공식 문자에는 URL이 포함되지 않습니다."}
            analysis["scores"]["final"] = 10.0
        if gemini_text_result["success"] and (
            gemini_text_result["gemini_smishing_score"] < 0.3
            or gemini_text_result["gemini_smishing_score"] >= 0.5
        ):
            analysis["low_confidence_warning"] = False

        is_dangerous = grade == "Danger"
        category_name = analysis["category"].get("category", "")
        feed_hit = analysis.get("feed_hit", False)
        analyzed_urls = analysis.get("url_analysis", {}).get("analyzed_urls", [])
        _log_analysis(
            input_type='qr' if is_qr else 'image',
            extracted_text=clean_text_no_url,
            analysis=analysis,
            grade=grade,
            score=analysis["scores"]["final"],
            urls=all_urls,
            p_gemini=p_gemini,
            p_vlm=p_vlm,
            gemini_result=gemini_text_result,
            vlm_result=vlm_result,
        )
        rank = _record_urls_and_get_rank(all_urls, is_dangerous, category_name, feed_hit, analyzed_urls)

        return {
            "filename": file.filename,
            "qr_urls": qr_results,
            "text_urls": text_urls,
            "extracted_text": clean_text_no_url,
            "rank": rank,
            "vlm_analysis": vlm_result,
            "gemini_text_analysis": gemini_text_result,
            **analysis,
        }

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"이미지 분석 중 오류가 발생했습니다: {str(e)}"
        )


def _record_urls_and_get_rank(urls: list, is_dangerous: bool, category: str = "",
                               feed_hit: bool = False, analyzed_urls: list = None) -> int | None:
    """위험하거나 피드에 등재된 URL을 DB에 기록하고 Top 5 내 순위 반환 (없으면 None)"""
    if (not is_dangerous and not feed_hit) or not urls:
        return None

    url_data = {}
    if analyzed_urls:
        for result in analyzed_urls:
            orig_url = result.get('details', {}).get('original_url', '')
            if orig_url:
                url_data[orig_url] = {
                    'feed_hit': result.get('feed_hit', False),
                    'vt_positive': result.get('details', {}).get('virustotal', {}).get('positive_count', 0),
                    'resolve_error': result.get('details', {}).get('resolve', {}).get('error') is not None,
                }

    for url in urls:
        key = _normalize_url_key(url)
        url_counter[key] += 1
        data = url_data.get(url, {})
        _record_url_to_db(
            url, category,
            original_feed_hit=data.get('feed_hit', False),
            original_vt_positive=data.get('vt_positive', 0),
            resolve_error=data.get('resolve_error', False),
        )
    top5 = [url for url, _ in url_counter.most_common(5)]
    for url in urls:
        key = _normalize_url_key(url)
        if key in top5:
            return top5.index(key) + 1
    return None


def _recheck_and_clean_rankings():
    """상위 50개 URL 재검사 후 더 이상 위험하지 않은 URL 제거"""
    print("[Recheck] 주간 랭킹 재검사 시작")
    try:
        con = get_db_conn()
        cursor = con.cursor()
        cursor.execute(
            "SELECT url, original_feed_hit, original_vt_positive FROM url_counts ORDER BY count DESC LIMIT 50"
        )
        rows = cursor.fetchall()
        cursor.close()
        con.close()
    except Exception as e:
        print(f"[Recheck] DB 조회 실패: {e}")
        return

    to_remove = []
    for url, orig_feed_hit, orig_vt_positive in rows:
        full_url = "https://" + url
        try:
            resolved = resolve_url(full_url)
            now_resolve_error = resolved['error'] is not None

            feed_result = check_threat_feeds(full_url, resolved['final_url'], resolved['final_domain'])
            now_feed_hit = feed_result['is_feed_hit']

            vt_result = check_virustotal(resolved['final_domain'])
            now_vt_positive = vt_result['positive_count']

            feed_improved = bool(orig_feed_hit) and not now_feed_hit
            vt_improved = now_vt_positive < (orig_vt_positive or 0)

            should_remove = (
                (now_resolve_error and (feed_improved or vt_improved))
                or
                (not now_resolve_error and feed_improved and vt_improved)
            )

            if should_remove:
                to_remove.append(url)
                print(f"[Recheck] 제거 대상: {url}")

        except Exception as e:
            print(f"[Recheck] {url} 검사 실패: {e}")

        time.sleep(15)  # VT 분당 4건 제한 대응

    if to_remove:
        try:
            con = get_db_conn()
            cursor = con.cursor()
            for url in to_remove:
                cursor.execute("DELETE FROM url_counts WHERE url = %s", (url,))
                url_counter.pop(url, None)
            con.commit()
            cursor.close()
            con.close()
            print(f"[Recheck] 총 {len(to_remove)}개 URL 제거 완료")
        except Exception as e:
            print(f"[Recheck] DB 삭제 실패: {e}")
    else:
        print("[Recheck] 제거할 URL 없음")


def _run_recheck_and_mark():
    _recheck_and_clean_rankings()
    _mark_recheck_done()


@app.post("/feedback")
async def submit_feedback(
    given_grade: str = Form(...),
    correct_grade: str = Form(...),
    reason: str = Form(""),
    text_content: str = Form(""),
    image: Optional[UploadFile] = File(None),
):
    image_path = None
    if image and image.filename:
        ext = os.path.splitext(image.filename)[-1] or ".png"
        filename = f"feedback_{int(time.time() * 1000)}{ext}"
        save_dir = os.path.join(os.path.dirname(__file__), "feedback_images")
        save_path = os.path.join(save_dir, filename)
        with open(save_path, "wb") as f:
            f.write(await image.read())
        image_path = filename

    con = get_db_conn()
    cursor = con.cursor()
    cursor.execute(
        "INSERT INTO feedback (given_grade, correct_grade, reason, text_content, image_path, created_at) VALUES (%s, %s, %s, %s, %s, %s)",
        (given_grade, correct_grade, reason, text_content, image_path, time.time())
    )
    con.commit()
    cursor.close()
    con.close()
    return {"status": "ok"}


@app.get("/top-urls")
async def top_urls(limit: int = 5):
    con = get_db_conn()
    cursor = con.cursor()
    cursor.execute("SELECT url, category, count FROM url_counts ORDER BY count DESC LIMIT %s", (limit,))
    rows = cursor.fetchall()
    cursor.close()
    con.close()
    return {"top_urls": [{"url": url, "category": category, "count": count} for url, category, count in rows]}


@app.post("/analyze-text")
async def analyze_text(data: dict):
    text = data.get("text", "")
    if not text.strip():
        raise HTTPException(status_code=400, detail="텍스트를 입력해주세요.")

    try:
        clean_text = correct_text(text)
        text_urls, clean_text_no_url = _clean_and_extract_urls(clean_text)

        # 통합 분석
        analysis = analyze_full(clean_text_no_url, text_urls)

        # Gemini 텍스트 스미싱 판단 (팀원2의 _build_url_context 방식 사용)
        url_context = _build_url_context(analysis.get('url_analysis', {}).get('analyzed_urls', []))
        gemini_text_result = await analyze_text_vlm(clean_text_no_url, url_context)
        p_gemini = round(gemini_text_result["gemini_smishing_score"] * 10, 4) if gemini_text_result["success"] else None
        if gemini_text_result["success"] and (
            gemini_text_result["gemini_smishing_score"] < 0.3
            or gemini_text_result["gemini_smishing_score"] >= 0.5
        ):
            analysis["low_confidence_warning"] = False
        p_nlp = analysis["scores"]["p_nlp"]
        p_url = analysis["scores"]["p_url"]
        has_url = bool(text_urls)
        vt_confirmed_safe = analysis.get("url_analysis", {}).get("vt_confirmed_safe", False)
        vt_found = analysis.get("url_analysis", {}).get("vt_found", False)
        p_url_raw = analysis["scores"].get("p_url_raw", p_url)
        final_result = calculate_final_score_v2(
            p_nlp=p_nlp, p_url=p_url, has_url=has_url,
            p_gemini=p_gemini,
            vt_confirmed_safe=vt_confirmed_safe, vt_found=vt_found,
            p_url_raw=p_url_raw,
        )
        grade = final_result["grade"]
        analysis["result"] = {"grade": grade, "message": final_result["message"]}
        analysis["scores"]["final"] = final_result["score"]
        _print_analysis_detail(
            header="[텍스트 분석]",
            analysis=analysis, final_result=final_result,
            p_nlp=p_nlp, p_url=p_url, p_gemini=p_gemini,
            urls=text_urls,
            extracted_text=clean_text_no_url,
        )
        government_override = _apply_grade_logic(analysis, grade, clean_text_no_url, has_url, p_nlp, p_url)
        if government_override:
            grade = "Danger"
            analysis["result"] = {"grade": "Danger", "message": "정부기관 사칭 스미싱 의심. 정부·공공기관 공식 문자에는 URL이 포함되지 않습니다."}
            analysis["scores"]["final"] = 10.0
        if gemini_text_result["success"] and (
            gemini_text_result["gemini_smishing_score"] < 0.3
            or gemini_text_result["gemini_smishing_score"] >= 0.5
        ):
            analysis["low_confidence_warning"] = False

        is_dangerous = grade == "Danger"
        category_name = analysis["category"].get("category", "")
        feed_hit = analysis.get("feed_hit", False)
        analyzed_urls = analysis.get("url_analysis", {}).get("analyzed_urls", [])
        _log_analysis(
            input_type='text',
            extracted_text=clean_text_no_url,
            analysis=analysis,
            grade=grade,
            score=analysis["scores"]["final"],
            urls=text_urls,
            p_gemini=p_gemini,
            p_vlm=None,
            gemini_result=gemini_text_result,
            vlm_result=None,
        )
        rank = _record_urls_and_get_rank(text_urls, is_dangerous, category_name, feed_hit, analyzed_urls)

        return {
            "qr_urls": [],
            "text_urls": text_urls,
            "extracted_text": clean_text_no_url,
            "rank": rank,
            "gemini_text_analysis": gemini_text_result,
            **analysis,
        }

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"텍스트 분석 중 오류가 발생했습니다: {str(e)}"
        )


@app.get("/admin/logs", response_class=HTMLResponse, include_in_schema=False)
async def admin_logs(page: int = 1, grade: str = ""):
    import json as _json
    per_page = 50
    offset = (page - 1) * per_page
    try:
        con = get_db_conn()
        cursor = con.cursor()
        where = "WHERE grade = %s" if grade else ""
        params_count = (grade,) if grade else ()
        cursor.execute(f"SELECT COUNT(*) FROM analysis_log {where}", params_count)
        total = cursor.fetchone()[0]
        params = (grade, per_page, offset) if grade else (per_page, offset)
        cursor.execute(
            f"SELECT id, created_at, input_type, grade, score, category, category_confidence, "
            f"p_nlp, p_url, p_gemini, p_vlm, extracted_text, urls, gemini_reason, risk_keywords "
            f"FROM analysis_log {where} ORDER BY id DESC LIMIT %s OFFSET %s",
            params
        )
        rows = cursor.fetchall()
        cursor.close()
        con.close()
    except Exception as e:
        return HTMLResponse(f"<pre>DB 오류: {e}</pre>", status_code=500)

    total_pages = max(1, (total + per_page - 1) // per_page)

    grade_colors = {"Danger": "#ff4444", "Warning": "#ff9900", "Safe": "#00aa44", "": "#888"}
    type_labels = {"image": "이미지", "qr": "QR", "text": "텍스트"}

    def fmt_time(ts):
        import datetime
        try:
            return datetime.datetime.fromtimestamp(float(ts)).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            return "-"

    def safe_json(s):
        try:
            return _json.loads(s) if s else []
        except Exception:
            return []

    def _fmt(v):
        return f"{v:.2f}" if v is not None else "-"

    rows_html = ""
    for row in rows:
        rid, created_at, input_type, g, score, cat, cat_conf, p_nlp, p_url, p_gemini, p_vlm, text, urls_json, gemini_reason, kw_json = row
        g = g or ""
        color = grade_colors.get(g, "#888")
        urls = safe_json(urls_json)
        keywords = safe_json(kw_json)
        kw_text = "있음" if keywords else "-"
        url_text = "<br>".join(f'<span style="font-size:11px;color:#aaa">{u}</span>' for u in urls) if urls else "-"
        text_preview = (text or "")[:80].replace("<", "&lt;").replace(">", "&gt;")
        if len(text or "") > 80:
            text_preview += "…"
        gemini_short = (gemini_reason or "")[:60].replace("<", "&lt;").replace(">", "&gt;")
        s_score = _fmt(score)
        s_conf = f"{cat_conf:.2f}" if cat_conf else "0.00"
        s_nlp = _fmt(p_nlp)
        s_url = _fmt(p_url)
        s_gem = _fmt(p_gemini)
        s_vlm = _fmt(p_vlm)
        rows_html += f"""
        <tr>
          <td style="color:#888;font-size:11px">{rid}</td>
          <td style="font-size:11px;white-space:nowrap">{fmt_time(created_at)}</td>
          <td style="text-align:center">{type_labels.get(input_type, input_type or "-")}</td>
          <td style="text-align:center;font-weight:bold;color:{color}">{g or "-"}</td>
          <td style="text-align:center">{s_score}</td>
          <td style="font-size:11px">{cat or "-"} <span style="color:#888">({s_conf})</span></td>
          <td style="font-size:11px;text-align:center">{s_nlp}</td>
          <td style="font-size:11px;text-align:center">{s_url}</td>
          <td style="font-size:11px;text-align:center">{s_gem}</td>
          <td style="font-size:11px;text-align:center">{s_vlm}</td>
          <td style="font-size:12px;max-width:200px">{text_preview or "-"}</td>
          <td style="font-size:11px;max-width:160px">{url_text}</td>
          <td style="font-size:11px;color:#aaa;max-width:180px">{kw_text}</td>
          <td style="font-size:11px;color:#ccc;max-width:180px">{gemini_short or "-"}</td>
        </tr>"""

    pager = ""
    for p in range(1, total_pages + 1):
        active = "background:#333;border-radius:4px;" if p == page else ""
        pager += f'<a href="/admin/logs?page={p}&grade={grade}" style="color:#ccc;padding:4px 8px;text-decoration:none;{active}">{p}</a> '

    grade_filter = "".join(
        f'<a href="/admin/logs?page=1&grade={g}" style="color:{grade_colors[g]};margin-right:12px;text-decoration:{"underline" if grade==g else "none"}">{g or "전체"}</a>'
        for g in ["", "Danger", "Warning", "Safe"]
    )

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<title>분석 로그</title>
<style>
  body {{ background:#1a1a1a; color:#ddd; font-family:monospace; padding:20px; }}
  h2 {{ color:#fff; margin-bottom:8px; }}
  .meta {{ color:#888; font-size:12px; margin-bottom:16px; }}
  table {{ border-collapse:collapse; width:100%; font-size:12px; }}
  th {{ background:#2a2a2a; color:#aaa; padding:8px 10px; text-align:left; border-bottom:1px solid #333; white-space:nowrap; }}
  td {{ padding:7px 10px; border-bottom:1px solid #222; vertical-align:top; }}
  tr:hover td {{ background:#222; }}
</style>
</head>
<body>
<h2>분석 로그</h2>
<div class="meta">총 {total}건 · 페이지 {page}/{total_pages} &nbsp;|&nbsp; {grade_filter}</div>
<table>
<thead>
<tr>
  <th>#</th><th>시각</th><th>유형</th><th>등급</th><th>점수</th>
  <th>카테고리</th><th>P_NLP</th><th>P_URL</th><th>P_Gemini</th><th>P_VLM</th>
  <th>추출 텍스트</th><th>URL</th><th>위험 키워드</th><th>Gemini 판단</th>
</tr>
</thead>
<tbody>{rows_html}</tbody>
</table>
<div style="margin-top:16px">{pager}</div>
</body>
</html>"""
    return HTMLResponse(html)
