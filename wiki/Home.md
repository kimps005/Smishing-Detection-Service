# CatchSmishing Wiki

> CatchSmishing의 현재 구현·설정·검증 정보를 한 곳에서 확인하는 프로젝트 위키입니다.

이 위키는 저장소의 FastAPI 서버, Flutter 클라이언트, Streamlit 운영 UI, 모델·평가 도구를 기준으로 작성했습니다. 저장소에서 확인할 수 없는 조직 정책이나 운영 수치는 추정하지 않습니다.

## 바로가기

| 구분 | 문서 |
| --- | --- |
| 프로젝트 | [[프로젝트 개요]] · [[요구사항 및 제약]] · [[전체 아키텍처]] |
| 기획 | [[문제 정의 및 사용 흐름]] |
| 기술 | [[AI 분석 파이프라인]] · [[URL 보안 분석]] · [[API 명세]] · [[데이터베이스 구조]] |
| 모델·검증 | [[모델 및 평가]] · [[검증 프로세스]] |
| 운영 | [[실행 및 운영]] · [[보안 및 개인정보]] · [[피드백 개선]] |

## 서비스 한눈에 보기

```text
문자 텍스트 / 캡처 이미지 / QR
              │
              ▼
OCR·QR 디코딩·URL 추출·정규화
              │
              ├─ KLUE/BERT 7종 분류
              ├─ 규칙 기반 텍스트 위험 신호
              ├─ URL 평판·도메인·APK 분석
              └─ Gemini 문맥·Vision 분석
              │
              ▼
      점수(0–10) · 등급 · 근거 · 대응 안내
```

## 외부 링크

- 서비스: [catchsmishing.com](https://catchsmishing.com)
- API: [api.catchsmishing.com](https://api.catchsmishing.com)
- 분류 모델: [kimps005/sms-category-model](https://huggingface.co/kimps005/sms-category-model)
- 저장소: [Smishing-Detection-Service](https://github.com/kimps005/Smishing-Detection-Service)

## 문서 기준

위키 내용이 코드와 달라질 경우 `server/main.py`, `server/url_analyzer.py`, `server/predictor.py`, `.env.example`, `requirements.txt`, `pubspec.yaml`을 우선 기준으로 삼습니다. 기능이 변경되면 관련 위키 페이지도 함께 수정합니다.
