# 데이터베이스 구조

DB 연결 정보는 `.env`로 주입하며 `server/db_config.py`가 PyMySQL 연결을 생성합니다. DB가 설정되지 않은 로컬 환경에서도 기본 분석 서버는 시작할 수 있지만, 아래 저장 기능은 사용할 수 없습니다.

## 테이블

### `url_counts`

위험하거나 위협 피드에 등재된 URL의 누적 노출 횟수와 재검사 기준 정보를 저장합니다.

주요 필드: `url`, `category`, `count`, `original_feed_hit`, `original_vt_positive`, `resolve_error`, `first_seen`

### `analysis_log`

분석 입력 유형, 결과 등급·점수, 카테고리, 텍스트·URL·Gemini·Vision 근거를 저장합니다.

주요 필드: `input_type`, `extracted_text`, `grade`, `category`, `category_confidence`, `score`, `p_nlp`, `p_url`, `p_gemini`, `p_vlm`, `urls`, `url_details`, `risk_keywords`, `text_reasons`, `url_reasons`, `gemini_reason`, `vlm_signals`, `vlm_reason`, `created_at`

### `feedback`

사용자가 제공한 판정 정정과 사유를 저장합니다.

주요 필드: `given_grade`, `correct_grade`, `reason`, `text_content`, `image_path`, `created_at`

### `app_meta`

주간 URL 재검사 완료 시각 등 애플리케이션 메타 값을 키·숫자 값으로 저장합니다.

## 초기화 방식

서버 시작 시 필요한 테이블을 `CREATE TABLE IF NOT EXISTS`로 생성하고, 이후 추가된 컬럼은 `ALTER TABLE`을 시도합니다. 스키마 변경을 별도 migration 도구로 관리하는 구조는 현재 저장소에 포함되어 있지 않습니다.

## 민감 정보

분석 로그와 피드백에는 문자 본문·URL·첨부 이미지가 포함될 수 있습니다. 운영 DB 접근 통제, 보존 기간, 삭제 절차는 배포 환경에서 별도로 정해야 합니다.
