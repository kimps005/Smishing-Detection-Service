# 요구사항 및 제약

## 실행 요구사항

- Python 3.11 이상
- `requirements.txt`에 정의된 Python 패키지
- Flutter 3.29 이상 및 Dart SDK 3.7 이상(모바일 앱 사용 시)
- QR 디코딩을 위한 `pyzbar` 및 운영체제별 ZBar 런타임
- MySQL 호환 DB(피드백·랭킹·로그 저장 시)
- Gemini API 키(문맥·Vision 분석 시)
- VirusTotal API 키(VirusTotal 조회 시)

## 입력 제약 기본값

| 항목 | 기본값 | 적용 경로 |
| --- | ---: | --- |
| 분석 이미지 | 10 MiB | `MAX_IMAGE_BYTES` |
| 피드백 이미지 | 5 MiB | `MAX_FEEDBACK_IMAGE_BYTES` |
| 이미지 픽셀 수 | 25,000,000 | `MAX_IMAGE_PIXELS` |
| 텍스트 길이 | 20,000자 | `MAX_TEXT_LENGTH` |
| 요청당 URL 수 | 10개 | `MAX_URLS_PER_ANALYSIS` |
| 분석 작업자 | 4개(최대) | `ANALYSIS_WORKERS` |

값은 `.env`에서 조정할 수 있으며, 작업자 수는 코드에서 1–4 범위로 제한됩니다.

## 분석 요청 제한

현재 메모리 기반 제한은 클라이언트 IP와 경로를 기준으로 합니다.

| 경로 | 기본 제한 |
| --- | ---: |
| `/analyze` | 60초당 10회 |
| `/analyze-text` | 60초당 30회 |
| `/feedback` | 60초당 20회 |

제한을 초과하면 `429 Too Many Requests`와 `Retry-After` 헤더가 반환됩니다. 이 제한은 단일 프로세스 메모리에 저장되므로 다중 인스턴스 운영 시 별도 분산 제한 계층이 필요합니다.

## 외부 의존성에 따른 제약

- Gemini, VirusTotal, WHOIS, 위협 피드 응답은 네트워크와 외부 서비스 상태에 영향을 받습니다.
- VirusTotal 무료 요금제 등 외부 API의 호출 한도에 따라 응답 시간이 달라질 수 있습니다.
- URL 검사는 실제 네트워크 요청을 수행하므로 사설·로컬 주소는 안전 검증 단계에서 차단됩니다.
- 모델은 한국어 SMS 카테고리 분류용이며, 분류 결과만으로 스미싱 여부를 확정하지 않습니다.
