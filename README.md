# CatchSmishing

> 이미지, 텍스트, QR 코드를 기반으로 스미싱 여부를 분석하고 위험도를 판정하는 AI 기반 스미싱 탐지 서비스입니다.

- 서비스 주소: [catchsmishing.com](https://catchsmishing.com)
- API 주소: [api.catchsmishing.com](https://api.catchsmishing.com)

---

## 1. 프로젝트 소개

CatchSmishing은 사용자가 수신한 문자 메시지를 텍스트, 캡처 이미지, QR 코드 등 다양한 형태로 입력하면 AI 기반 복합 분석을 통해 스미싱 위험도를 판단해주는 서비스입니다.

단순 키워드 탐지가 아니라 다음 요소를 함께 반영합니다.

- OCR 기반 텍스트 추출
- 문자 카테고리 분류
- 위험 키워드 및 행동 유도 패턴 분석
- URL 보안 분석
- Gemini 기반 문맥 분석
- Gemini Vision 기반 시각 분석

---

## 2. 시스템 흐름

```text
[입력: 이미지 / 텍스트 / QR]
        ↓
OCR(PaddleOCR)로 이미지 내 텍스트 및 QR URL 추출
        ↓
문자 카테고리 분류(KLUE/bert-base fine-tuned)
        ↓
텍스트 위험 신호 분석(P_NLP)
        ↓
URL 보안 분석(P_URL)
 - 단축 URL 추적
 - 악성 피드 대조
 - VirusTotal 조회
 - WHOIS 생성일 확인
 - APK 설치 유도 여부 확인
        ↓
Gemini 문맥 분석(P_Gemini)
Gemini Vision 시각 분석(P_VLM)
        ↓
최종 위험 점수 계산
        ↓
[출력: 등급 + 카테고리 + 탐지 근거 + 대응 가이드]
```

---

## 3. 위험 등급

| 등급 | 점수 범위 |
|------|----------|
| Danger | 7.0 ~ 10.0 |
| Warning | 3.5 ~ 6.9 |
| Safe | 0.0 ~ 3.4 |

---

## 4. 주요 카테고리

| 카테고리 | 설명 |
|----------|------|
| PERSONAL | 일반 문자 |
| FINANCE | 금융 사기 |
| DELIVERY | 배송 사기 |
| GOVERNMENT | 공공기관 사칭 |
| PROMOTION | 홍보/투자 유도 |
| AUTH | 계정 인증/탈취 |
| WORK | 업무/지인 사칭 |

---

## 5. 주요 기능

- 이미지 분석: 문자 캡처 이미지 업로드 후 OCR, QR, 문맥, 시각 분석 수행
- 텍스트 분석: 문자 내용을 직접 입력하거나 공유해 분석 수행
- QR 분석: 카메라로 QR 코드를 읽고 연결 URL 위험도 판정
- URL 보안 분석: 악성 피드, VirusTotal, WHOIS, APK 유도 여부 종합 점검
- 탐지 근거 제공: 위험 키워드, URL 근거, AI 분석 이유 제공
- 위험 URL 랭킹: 반복 탐지된 위험 URL 상위 목록 제공
- 피드백 수집: 오탐/미탐 사례 제출 및 개선 데이터 확보
- 관리자 로그 조회: 분석 이력과 점수 정보를 웹에서 확인 가능

---

## 6. 기술 스택

### Backend / AI

- FastAPI
- Uvicorn
- PaddleOCR
- PyTorch
- Hugging Face Transformers
- Google Gemini API
- OpenCV
- pyzbar
- requests
- python-whois
- PyMySQL

### Mobile App

- Flutter
- Dart
- `image_picker`
- `http`
- `share_handler`
- `mobile_scanner`
- `share_plus`

### Admin / Operation

- Streamlit
- MySQL (Aiven Cloud)

---

## 7. 실행 방법

### Python 환경

```bash
cd Project
venv\Scripts\activate
```

### 패키지 설치

```bash
pip install -r requirements.txt
```

운영 DB는 Aiven에서 제공하는 CA 인증서 경로를 `DB_SSL_CA`에 지정하고 `DB_SSL_VERIFY=1`을 유지해야 합니다. 인증서 검증을 끄는 `DB_SSL_VERIFY=0`은 로컬 테스트에서만 사용하세요.

### 모델 배포

분류 모델은 서버를 처음 시작할 때 로컬 경로를 먼저 확인합니다. 모델 파일이 이미 있으면 그대로 사용하고, 없으면 공개 Hugging Face 저장소에서 양자화 가중치와 BERT 설정·토크나이저 파일만 자동으로 내려받아 로컬 경로에 저장합니다. 이후 요청에서는 다시 다운로드하지 않습니다.

```env
SMS_MODEL_QUANTIZED=1
SMS_CATEGORY_MODEL_PATH=
SMS_BASE_MODEL_PATH=
SMS_HF_REPO_ID=kimps005/sms-category-model
SMS_HF_MODEL_FILENAME=sms_category_model_int8_dynamic_state_dict.pt
SMS_HF_REVISION=b0267b3befd229165127de5cf402414d427863fa
```

분류 모델 Hugging Face 주소: [kimps005/sms-category-model](https://huggingface.co/kimps005/sms-category-model)

기본 경로는 프로젝트의 `models/sms_category_model_int8_dynamic_state_dict.pt`와 `models/klue-bert-base/`입니다. 경로를 직접 지정하고 싶을 때만 `SMS_CATEGORY_MODEL_PATH`와 `SMS_BASE_MODEL_PATH`를 설정하면 됩니다. 공개 저장소이므로 별도 Hugging Face 토큰은 필요하지 않습니다. 전체 `klue/bert-base` 가중치는 받지 않고, 모델 구조를 만드는 데 필요한 설정·토크나이저 파일만 받습니다.

### API 서버 실행

```bash
cd server
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Streamlit 운영 UI 실행

```bash
cd server
streamlit run app.py
```

### Flutter 앱 실행

```bash
flutter run
```

> 참고: 원본 FP32 모델은 약 427MB, 양자화 모델도 약 179MB이므로 GitHub에는 Git LFS 포인터만 저장하고 실제 파일은 Hugging Face에서 배포합니다.

### 양자화 벤치마크

`benchmark_quantization.py`는 동일한 데이터셋에서 FP32와 INT8 동적 양자화 모델의 정확도, F1, 메모리, 추론 지연시간을 비교합니다. 원본 FP32 체크포인트를 `SMS_CATEGORY_MODEL_PATH`로 지정한 뒤 실행합니다.

```bash
python benchmark_quantization.py --variant fp32
python benchmark_quantization.py --variant int8_dynamic
```

양자화 체크포인트는 기본적으로 `models/sms_category_model_int8_dynamic_state_dict.pt`에 저장됩니다.

---

## 8. 주요 API

| 메서드 | URL | 설명 |
|--------|-----|------|
| POST | `/analyze` | 이미지 분석 |
| POST | `/analyze-text` | 텍스트 분석 |
| GET | `/top-urls?limit=50` | 위험 URL 랭킹 조회 |
| POST | `/feedback` | 사용자 피드백 제출 |
| GET | `/admin/logs` | 관리자 분석 로그 조회 (`Authorization: Bearer <ADMIN_TOKEN>` 필요) |

---

## 9. 라이브러리 버전

아래 버전은 2026-06-03 기준 로컬 개발 환경에서 `pip show`로 확인한 값입니다.

| 라이브러리 | 버전 | 용도 |
|-----------|------|------|
| FastAPI | 0.135.1 | API 서버 |
| Uvicorn | 0.42.0 | ASGI 서버 |
| PaddleOCR | 2.7.3 | OCR 텍스트 추출 |
| PyMySQL | 1.1.3 | MySQL 연동 |
| transformers | 5.3.0 | BERT 기반 분류 모델 |
| google-genai | 2.4.0 | Gemini 연동 |
| Pillow | 11.0.0 | 이미지 처리 |
| numpy | 1.26.4 | 수치 연산 |
| opencv-python | 4.6.0.66 | 이미지 전처리 |
| pyzbar | 0.1.9 | QR 코드 추출 |
| requests | 2.32.4 | 외부 보안 API 호출 |
| python-whois | 0.9.6 | 도메인 생성일 조회 |
| streamlit | 1.50.0 | 운영 UI |
| torch | 2.5.1+cu121 | 분류 모델 추론 |

### 참고 사항

- `sentencepiece`는 현재 로컬 환경에서 설치 여부가 확인되지 않았습니다.
- Flutter 패키지의 정확한 버전 관리는 `pubspec.yaml` 기준으로 추가 정리하는 것을 권장합니다.

---

## 10. 현재 서비스 구조 메모

- 현재 버전은 사용자 로그인 없이 즉시 분석 가능한 비회원형 구조입니다.
- 관리자 분석 로그는 `/admin/logs` 페이지를 통해 조회할 수 있습니다.
- 향후 사용자 로그인, 개인 분석 이력 저장, 관리자 권한 분리 기능으로 확장 가능합니다.
