# API 명세

실행 중인 서버의 `/docs`가 최신 OpenAPI 명세입니다. 아래는 현재 `server/main.py`에 구현된 주요 경로입니다.

| 메서드 | 경로 | 인증 | 설명 |
| --- | --- | --- | --- |
| `POST` | `/analyze` | 없음 | 이미지 OCR·QR·통합 분석 |
| `POST` | `/analyze-text` | 없음 | 텍스트 및 포함 URL 분석 |
| `POST` | `/analysis/cancel/{analysis_id}` | 없음 | 분석 취소 요청 |
| `POST` | `/feedback` | 없음 | 등급 피드백과 선택적 이미지 저장 |
| `GET` | `/top-urls?limit=5` | 없음 | URL 랭킹 조회(1–50) |
| `GET` | `/admin/logs` | Bearer `ADMIN_TOKEN` | 관리자 분석 로그 HTML |

## 공통 요청 헤더

분석 클라이언트는 선택적으로 `X-Analysis-ID`를 전달합니다. 동일한 ID로 `/analysis/cancel/{analysis_id}`를 호출하면 실행 중인 분석에 취소 이벤트를 전달합니다.

## 텍스트 요청

```http
POST /analyze-text
Content-Type: application/json
X-Analysis-ID: demo-001

{"text":"[택배] 주소 확인이 필요합니다. https://example.com"}
```

## 이미지 요청

```bash
curl -X POST "http://127.0.0.1:8000/analyze" \
  -H "X-Analysis-ID: demo-image-001" \
  -F "file=@./sample-message.png"
```

## 주요 응답 키

`extracted_text`, `text_urls`, `qr_urls`, `category`, `nlp_analysis`, `url_analysis`, `gemini_text_analysis`, `vlm_analysis`, `scores`, `result`, `rank`를 사용합니다. 일부 보조 분석이 실패하면 관련 점수가 `null`이 되거나 실패 정보가 포함될 수 있습니다.

## 오류와 제한

- 잘못된 입력: `400`
- 크기·길이 제한 초과: `413`
- 요청 제한 초과: `429`
- 관리자 토큰 오류: `401`, 미설정: `503`
- 분석 취소: `499`
- 분석을 수행할 수 없는 서버 상태: `500` 또는 `503`
