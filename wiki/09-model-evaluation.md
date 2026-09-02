# 모델 및 평가

## 분류 모델

| 항목 | 내용 |
| --- | --- |
| 기반 모델 | `klue/bert-base` |
| 작업 | 한국어 SMS 7개 카테고리 분류 |
| 입력 | 최대 128 토큰(서비스에서 URL 제거·정규화) |
| 배포 | PyTorch INT8 동적 양자화 `state_dict` |
| 저장소 | [kimps005/sms-category-model](https://huggingface.co/kimps005/sms-category-model) |

분류 모델은 카테고리 신호를 제공하며, 독립적인 스미싱 판정 모델이 아닙니다. 최종 등급은 NLP·URL·Gemini·Vision 신호와 함께 계산됩니다.

## 양자화 벤치마크

프로젝트에 기록된 로컬 진단 결과는 다음과 같습니다.

| 지표 | FP32 | INT8 동적 양자화 | 변화 |
| --- | ---: | ---: | ---: |
| 체크포인트 크기 | 426.58 MiB | 178.56 MiB | 약 −58.14% |
| 정확도 | 98.68% | 98.57% | −0.11%p |
| Macro F1 | 98.68% | 98.57% | −0.11%p |
| 단일 메시지 p50 | 370.97 ms | 196.40 ms | 약 −47.1% |
| 단일 메시지 p95 | 449.58 ms | 220.32 ms | 약 −51.0% |

벤치마크는 7개 카테고리별 400건씩 생성한 한국어 SMS 2,800건과 특정 로컬 실행 환경을 사용합니다. 따라서 실제 통신사 문자나 실시간 스미싱 탐지율을 대표하지 않습니다.

## 재현 명령

```powershell
python benchmark_quantization.py --variant fp32
python benchmark_quantization.py --variant int8_dynamic
```

모델 학습 설정은 `smishing_colab.ipynb`, Hugging Face 모델의 상세한 제한과 책임 있는 사용 안내는 모델 저장소 문서를 기준으로 합니다.
