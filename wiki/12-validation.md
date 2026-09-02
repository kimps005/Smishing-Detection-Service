# 검증 프로세스

## 구현 수준 확인

현재 저장소에는 다음 검증 도구가 포함되어 있습니다.

| 도구 | 목적 |
| --- | --- |
| `benchmark_quantization.py` | FP32와 INT8 동적 양자화 모델의 크기·정확도·F1·지연시간·메모리 비교 |
| `eval_hybrid.py` | OCR과 통합 분석 조합 평가 |
| `eval_paddle_only.py` | PaddleOCR 중심 평가 |
| `evaluate_paddle.py` | PaddleOCR 평가 보조 실행 |
| `test_normal_dataset.py` | `meal-bbang/Korean_message` 정상 문자 샘플의 오탐 확인 |
| `test_my_messages.py` | 사용자가 제공한 HTML 문자 묶음의 API 분석 결과 확인 |

## 실행 전제

- API 서버가 `http://127.0.0.1:8000`에서 실행 중이어야 하는 스크립트가 있습니다.
- `test_normal_dataset.py`는 `datasets` 패키지와 외부 데이터셋 접근이 필요합니다.
- Gemini 무료 요금제 호출 한도를 고려해 일부 스크립트는 요청 사이에 지연을 둡니다.
- 개인 문자 파일을 사용할 때는 민감 정보 노출과 결과 파일 생성에 주의합니다.

## 해석 기준

정량 평가는 모델·OCR·통합 파이프라인의 특정 조건을 비교하는 용도입니다. 생성 데이터나 특정 샘플의 결과를 실사용 성능, 실시간 악성 URL 차단율, 안전 보증으로 확대 해석하지 않습니다.

현재 저장소에서 별도 CI 파이프라인이나 자동 배포 검증 설정은 확인되지 않으므로, 변경 후에는 해당 기능에 맞는 로컬 검증을 수행합니다.
