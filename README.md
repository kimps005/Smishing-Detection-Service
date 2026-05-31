# 지능형 스미싱/큐싱 탐지 솔루션

> 멀티모달 AI 기반 스미싱·큐싱 탐지 시스템 — 문자 캡처 이미지 또는 텍스트를 분석해 위험도를 판정합니다.

🌐 웹: [catchsmishing.com](https://catchsmishing.com)  
⚙️ API: [api.catchsmishing.com](https://api.catchsmishing.com)

---

## 시스템 아키텍처

```
[입력: 이미지 / 텍스트 / QR]
        ↓
  ① OCR (PaddleOCR) — 이미지에서 텍스트 및 QR URL 추출
        ↓
  ② 카테고리 분류 (KLUE/bert-base)
     + 텍스트 위험 패턴 분석 → P_NLP 산출
  ③ URL 보안 분석 (피싱 피드, VirusTotal 등) → P_URL 산출
  ④ Gemini Vision — 이미지 시각 위협 신호 분석 → P_VLM 산출
  ⑤ Gemini Text — 문자 맥락 스미싱 판단 → P_Gemini 산출
        ↓
  ⑥ 최종 위험도 S 산출 (calculate_final_score_v2)
        ↓
[출력: 등급 + 카테고리 + 탐지 근거 + 행동 가이드]
```

---

## 위험도 등급

| 등급 | 점수 범위 |
|------|---------|
| 위험 (Danger) | 7.0 ~ 10.0 |
| 주의 (Warning) | 3.5 ~ 6.9 |
| 안전 (Safe) | 0.0 ~ 3.4 |

---

## 최종 위험도 공식

입력 유형(이미지/텍스트/QR), URL 분석 결과, Gemini 분석 결과, 시각 분석 결과에 따라 가중치가 자동 결정됩니다.

**우선순위: URL > P_Gemini > P_VLM > P_NLP**

### 점수 구성

| 점수 | 설명 |
|------|------|
| P_NLP | 카테고리 분류 결과와 긴급성·위협·행동 유도·카테고리별 위험 키워드를 기반으로 산출한 텍스트 위험 점수 |
| P_URL | 피싱 피드, VirusTotal, URL 특징, WHOIS, APK 다운로드 유도 여부를 종합한 URL 위험 점수 |
| P_Gemini | Gemini가 문자 맥락을 분석해 산출한 스미싱 의심 점수 |
| P_VLM | Gemini Vision이 이미지 레이아웃, 로고, QR, 경고 UI 등 시각적 위협 신호를 분석한 점수 |

### 대표 가중치

| 상황 | 공식 |
|------|------|
| 강한 URL 위험 신호 + Gemini + VLM | `P_URL×0.75 + P_Gemini×0.15 + P_VLM×0.05 + P_NLP×0.05` |
| 중간 URL 위험 신호 + Gemini + VLM | `P_URL×0.45 + P_Gemini×0.30 + P_VLM×0.15 + P_NLP×0.10` |
| URL 안전 확인 + Gemini + VLM | `P_Gemini×0.45 + P_VLM×0.15 + P_NLP×0.20 + P_URL×0.20` |
| URL 없음 + Gemini + VLM | `P_Gemini×0.50 + P_VLM×0.30 + P_NLP×0.20` |
| URL 없음 + Gemini만 | `P_Gemini×0.70 + P_NLP×0.30` |
| URL 없음, 신호 없음 | `P_NLP×1.0` |

VirusTotal에서 악성 또는 의심 탐지가 있고 Gemini도 의심 판단을 내린 경우, 최종 등급이 위험(Danger)으로 보정될 수 있습니다.

---

## 분류 카테고리 (7종)

| 카테고리 | 설명 |
|----------|------|
| PERSONAL | 일반 문자 |
| FINANCE | 금융 사기 |
| DELIVERY | 배송 사기 |
| GOVERNMENT | 공공기관 사칭 |
| PROMOTION | 홍보/투자 유도 |
| AUTH | 계정 탈취 |
| WORK | 지인 사칭 |

---

## 기술 스택

### 서버
- **Framework:** FastAPI
- **OCR:** PaddleOCR (한국어/영어)
- **카테고리 분류:** KLUE/bert-base fine-tuned 모델
- **텍스트 위험 분석:** 긴급성, 위협 표현, 행동 유도, 카테고리별 위험 키워드 기반 점수화
- **멀티모달 분석:** Google Gemini API (이미지 시각 분석 + 텍스트 문맥 분석)
- **URL 분석:** 피싱 피드 DB, VirusTotal, 도메인 나이/리다이렉트 추적
- **DB:** MySQL (Aiven 클라우드) — URL 탐지 이력, 피드백 저장
- **배포:** Cloudflare Tunnel

### 앱
- **Framework:** Flutter (Android)
- **언어:** Dart
- **주요 패키지:** image_picker, http, share_handler, mobile_scanner, share_plus

### 웹 UI
- **Framework:** Streamlit

---

## 주요 기능

- **이미지 분석:** 문자 캡처 이미지 업로드 → OCR + QR 추출 → AI 멀티모달 위험도 판정
- **텍스트 분석:** 문자 내용 직접 입력 또는 공유하기 연동
- **QR 스캔:** 웹 카메라 / 앱 카메라로 QR 코드 스캔 후 분석
- **Gemini 시각 분석:** 이미지 레이아웃·색상·로고 등 시각적 위협 신호 탐지
- **Gemini 문맥 분석:** 문자 내용의 스미싱 맥락 판단
- **탐지 순위:** 위험 URL 누적 탐지 횟수 Top 50 + 카테고리 분포 차트
- **오탐 피드백:** 잘못된 판정 신고 (텍스트/이미지 첨부)
- **행동 가이드:** 등급별 대응 방법 안내

---

## 실행 방법

### 환경 설정

**가상환경 사용 시 (Windows)**
```bash
cd Smishing_Project
venv\Scripts\activate
```

**패키지 설치**
```bash
pip install fastapi uvicorn paddleocr pymysql transformers huggingface_hub sentencepiece google-genai pillow
```

### 서버
```bash
cd server
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 웹 UI
```bash
cd server
streamlit run app.py
```

### 앱
```bash
cd smishing_app
flutter run
```

> **주의:** `server/sms_category_model.pt`는 git에 포함되지 않습니다. 별도로 복사해주세요.

---

## API 주요 엔드포인트

| 메서드 | URL | 설명 |
|--------|-----|------|
| POST | `/analyze` | 이미지 분석 (multipart/form-data) |
| POST | `/analyze-text` | 텍스트 분석 (JSON) |
| GET | `/top-urls?limit=50` | 위험 URL 탐지 순위 |
| POST | `/feedback` | 오탐 피드백 제출 |
