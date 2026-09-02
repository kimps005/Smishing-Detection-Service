# 실행 및 운영

## 로컬 실행

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env

cd server
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

별도 터미널에서 운영 UI를 실행합니다.

```powershell
cd server
streamlit run app.py
```

Flutter 앱은 프로젝트 루트에서 다음을 실행합니다.

```powershell
flutter pub get
flutter run
```

## 시작 시 동작

- 분류 모델의 로컬 파일을 확인하고 없으면 Hugging Face에서 필요한 파일을 내려받습니다.
- DB 설정이 있으면 테이블과 URL 카운터를 초기화합니다.
- 위협 피드 갱신과 주간 URL 재검사 작업을 시작합니다.

## 환경 설정 체크

운영 배포 전 다음 값을 확인합니다.

- `GEMINI_API_KEY`, `VIRUSTOTAL_API_KEY`를 Secret으로 주입
- Aiven 등 TLS DB 사용 시 `DB_SSL_CA` 설정 및 `DB_SSL_VERIFY=1` 유지
- `/admin/logs`를 사용할 경우 충분히 긴 `ADMIN_TOKEN` 설정
- Streamlit의 `API_URL`이 실제 FastAPI 주소를 가리키는지 확인
- 실기기 테스트 시 Flutter의 `serverUrl`이 기기에서 접근 가능한 주소인지 확인

## 현재 확인 가능한 운영 화면

- FastAPI 문서: `/docs`
- 기본 웹 화면: `/`
- 분석 화면: `/analyze-page`
- 피드백 화면: `/feedback-page`
- 관리자 로그: 인증 헤더가 있는 `/admin/logs`

백업 주기, 장애 대응 담당자, 배포 자동화와 같은 조직 운영 정책은 저장소에 정의되어 있지 않으므로 이 위키에서 임의로 정하지 않습니다.
