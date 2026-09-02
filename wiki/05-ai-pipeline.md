# AI 분석 파이프라인

## 1. 이미지 전처리

`POST /analyze`는 업로드 이미지를 OpenCV로 읽고 다음을 수행합니다.

- PaddleOCR로 문자 영역의 텍스트 추출
- pyzbar로 QR 데이터 디코딩
- OCR 오인식을 고려한 URL·문자 정정 및 정규화
- 본문 URL과 QR URL 중복 제거

텍스트를 인식하지 못하고 URL도 추출되지 않으면 `Unknown` 결과와 `ocr_failed: true`를 반환합니다.

## 2. 카테고리 분류

`server/predictor.py`의 사용자 정의 분류기는 `klue/bert-base` 구조를 기반으로 다음 7개 중 하나를 예측합니다.

`PERSONAL`, `FINANCE`, `DELIVERY`, `GOVERNMENT`, `PROMOTION`, `AUTH`, `WORK`

URL은 분류 입력에서 제거하고, 최대 128토큰으로 토큰화합니다. 분류 모델의 키워드 보정은 모델 확률과 별도로 적용됩니다.

## 3. 규칙 기반 NLP

문자 본문에서는 긴박감(`urgency`), 위협(`threat`), 행동 유도(`action`), 카테고리별 패턴(`category_pattern`)을 검사합니다. 매칭 결과는 `risk_keywords`에 키워드·유형·가중치로 반환되며 `P_NLP`로 환산됩니다.

## 4. 생성형 AI

- 텍스트 입력: Gemini가 문자 문맥과 URL 분석 컨텍스트를 보고 스미싱 가능성과 사유를 반환합니다.
- 이미지 입력: Gemini 텍스트 분석과 Gemini Vision 분석을 결합해 시각적 사칭·버튼·배너 등 단서를 평가합니다.

API 키가 없거나 호출이 실패하면 해당 점수는 `null`이 될 수 있고, 서버는 사용 가능한 다른 신호로 최종 결과를 계산합니다.

## 5. 최종 등급

최종 점수는 URL 존재 여부, URL 원시 점수, VirusTotal 확인 상태, Gemini/Vision 가용성, 입력이 QR인지 여부에 따라 다른 가중치 분기를 사용합니다.

| 점수 | 등급 |
| ---: | --- |
| 7.0 이상 | `Danger` |
| 3.5 이상 7.0 미만 | `Warning` |
| 3.5 미만 | `Safe` |

URL이 강하게 의심되거나 특정 정부기관 사칭 조건을 만족하면 등급 하한을 적용하는 보정 로직도 있습니다.
