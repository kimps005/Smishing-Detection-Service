import os
import re
import random
import qrcode
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, timedelta
from pathlib import Path

# 데이터셋 생성에 사용하는 경로와 고정 리소스
BASE_DIR = Path(__file__).resolve().parent
BG_DIR = BASE_DIR / "backgrounds"
FONT_DIR = BASE_DIR / "fonts"
DEFAULT_OUTPUT_DIR = BASE_DIR / "output"

BG_CONFIGS = {
    "bg_Galaxy.png": (40, 50, 580),
    "bg_iPhone.png": (55, 45, 580),
    "bg_Kakao.png": (45, 40, 580),
}

URL_TOKEN_RE = re.compile(r"https?://\S+")
HEADER_OPTIONS = {
    "web": ("[Web발신]\n", "[국외발신]\n", ""),
    "ad": ("(광고) ", "[광고] ", ""),
    "none": ("",),
}

CATEGORIES = {
    0: "PERSONAL",
    1: "FINANCE",
    2: "DELIVERY",
    3: "GOVERNMENT",
    4: "PROMOTION",
    5: "AUTH",
    6: "WORK",
}


# 최종 이미지 합성 루프에서 사용하는 렌더링 헬퍼
def get_wrapped_text(text, font, max_width):
    lines = []
    for paragraph in text.split('\n'):
        # URL은 줄바꿈 중간에 끊기지 않도록 한 덩어리로 유지
        tokens = []
        last = 0
        for m in URL_TOKEN_RE.finditer(paragraph):
            if m.start() > last:
                tokens.extend(list(paragraph[last:m.start()]))
            tokens.append(m.group())   # URL은 쪼개지 않고 통째로
            last = m.end()
        if last < len(paragraph):
            tokens.extend(list(paragraph[last:]))

        curr_line = ""
        for token in tokens:
            if font.getlength(curr_line + token) <= max_width:
                curr_line += token
            else:
                if curr_line:
                    lines.append(curr_line)
                curr_line = token
        if curr_line:
            lines.append(curr_line)
    return lines

def create_qr_code(url, size=(120, 120)):
    qr = qrcode.QRCode(version=1, border=1)
    qr.add_data(url)
    qr.make(fit=True)
    return qr.make_image(fill_color="black", back_color="white").convert('RGB').resize(size)

# 합성 데이터용 테스트 URL과 포맷 헬퍼
SAFE_DOMAINS = [
    "ex.test", "m.test", "kr.test", "go.test", "pay.test", "auth.test",
]

def fake_url(keyword="notice"):
    domain = random.choice(SAFE_DOMAINS)
    code = random.randint(1000, 999999)
    return f"https://{keyword}{code}.{domain}"


def maybe_header(kind="web"):
    return random.choice(HEADER_OPTIONS.get(kind, ("",)))


def money(min_man=1, max_man=300):
    return f"{random.randint(min_man, max_man) * 10000:,}원"


def order_no(prefix=""):
    letters = "".join(random.choice("ABCDEFGHJKLMNPQRSTUVWXYZ") for _ in range(2))
    return f"{prefix}{letters}{random.randint(100000, 999999)}"


# 대량 생성용 확장 엔진 헬퍼와 템플릿 풀
def expanded_values(url, generated_at=None):
    now = generated_at or datetime.now()
    next_day = now + timedelta(days=random.randint(1, 5))
    values = {
        "url": url,
        "date": now.strftime("%m/%d"),
        "next_date": next_day.strftime("%m/%d"),
        "time": now.strftime("%H:%M"),
        "time_slot": random.choice(["오전 9시", "오전 10시 30분", "오후 1시", "오후 2시", "오후 3시 30분", "오후 6시", "저녁 7시"]),
        "deadline": random.choice(["오늘 18시", "오늘 자정", "이번 주 금요일", "내일 오전", "오늘 업무 종료 전", "24시간 이내"]),
        "amount": money(1, 250),
        "small_amount": money(1, 20),
        "large_amount": money(300, 5000),
        "percent": random.randint(5, 80),
        "points": f"{random.randint(300, 80000):,}P",
        "code": random.randint(100000, 999999),
        "code8": random.randint(10000000, 99999999),
        "ip": f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}",
        "order": order_no("O"),
        "invoice": random.randint(1000000000, 9999999999),
        "seat": f"{random.randint(1, 15)}{random.choice(['A', 'B', 'C', 'D'])}",
        "masked_name": random.choice(["김*수", "박*영", "이*연", "최*우", "정*은", "강*호"]),
        "account": f"{random.randint(100,999)}-{random.randint(10,99)}-****",
        "phone_suffix": random.randint(1000, 9999),
        "location": random.choice(["서울", "부산", "대전", "광주", "인천", "수원", "제주", "해외"]),
        "family": random.choice(["엄마", "아빠", "누나", "형", "동생", "이모", "삼촌", "할머니", "할아버지"]),
        "friend": random.choice(["민수", "지훈", "서연", "유진", "현우", "지아", "도윤", "수빈", "예린", "준호", "하린", "태오"]),
        "relation": random.choice(["부친", "모친", "조부", "조모", "빙부", "빙모"]),
        "hospital": random.choice(["서울중앙병원", "강남성모병원", "세브란스병원", "한양대병원", "부산백병원"]),
        "hall": random.choice(["더채플앳청담", "라움", "웨스틴조선", "아펠가모", "엘타워"]),
        "place": random.choice(["강남역 11번 출구", "홍대입구", "회사 앞", "학교 정문", "병원 로비", "스터디룸", "카페", "고속터미널"]),
        "activity": random.choice(["저녁 먹기", "과제 제출", "회의 준비", "생일 모임", "동창회", "영화 예매", "짐 찾기", "운동"]),
        "food": random.choice(["김치찌개", "마라탕", "초밥", "파스타", "치킨", "분식", "샐러드", "커피"]),
        "item": random.choice(["우산", "충전기", "노트북", "지갑", "교재", "서류", "선물", "약"]),
        "pet": random.choice(["강아지", "고양이", "반려동물"]),
        "utility": random.choice(["전기요금", "가스요금", "수도요금", "관리비"]),
        "school": random.choice(["한빛초", "중앙중", "미래고", "서울대", "한국대"]),
        "class_name": random.choice(["1학년 3반", "2학년 5반", "경영학과", "컴퓨터공학과", "스터디A반"]),
        "teacher": random.choice(["담임교사", "조교", "학생지원팀", "교무처"]),
        "bank": random.choice(["KB국민은행", "신한은행", "우리은행", "하나은행", "NH농협", "IBK기업은행", "카카오뱅크", "토스뱅크"]),
        "card": random.choice(["삼성카드", "현대카드", "신한카드", "KB국민카드", "롯데카드", "BC카드", "우리카드"]),
        "store": random.choice(["쿠팡", "배달의민족", "스타벅스", "네이버페이", "GS칼텍스", "이마트", "APPLE.COM/BILL", "올리브영"]),
        "pay_app": random.choice(["카카오페이", "토스", "네이버페이", "페이코", "삼성페이"]),
        "securities": random.choice(["미래에셋증권", "한국투자증권", "NH투자증권", "키움증권", "토스증권"]),
        "stock": random.choice(["삼성전자", "NAVER", "현대차", "SK하이닉스", "KODEX 200", "카카오"]),
        "insurance": random.choice(["삼성화재", "현대해상", "DB손해보험", "KB손해보험", "교보생명"]),
        "bill": random.choice(["관리비", "보험료", "통신요금", "카드대금", "도시가스", "전기요금"]),
        "carrier": random.choice(["CJ대한통운", "롯데택배", "한진택배", "우체국택배", "로젠택배", "쿠팡"]),
        "shop": random.choice(["쿠팡", "네이버쇼핑", "11번가", "G마켓", "마켓컬리", "오늘의집", "SSG.COM"]),
        "product": random.choice(["생활용품", "건강식품", "무선이어폰", "도서", "의류", "반려용품", "주방용품", "화장품"]),
        "pickup_place": random.choice(["문 앞", "경비실", "택배함", "편의점", "관리사무소"]),
        "route": random.choice(["서울->부산", "용산->광주송정", "김포->제주", "인천->도쿄", "서울->대전"]),
        "movie": random.choice(["파묘", "범죄도시", "인사이드 아웃", "듄", "서울의 봄"]),
        "airline": random.choice(["대한항공", "아시아나항공", "제주항공", "진에어", "티웨이항공"]),
        "flight": f"{random.choice(['KE', 'OZ', '7C', 'LJ', 'TW'])}{random.randint(100,999)}",
        "document": random.choice(["주민등록등본", "가족관계증명서", "납세증명서", "건강검진 결과", "민원 처리 결과"]),
        "tax": random.choice(["종합소득세", "지방세", "자동차세", "부가가치세", "재산세"]),
        "benefit": random.choice(["근로장려금", "긴급생활지원금", "소상공인 지원금", "청년수당", "환급금"]),
        "case_no": random.randint(20240000, 20269999),
        "fine": random.choice(["과태료", "범칙금", "주정차 위반", "민원 보완", "전자고지"]),
        "alert_level": random.choice(["관심", "주의", "경계", "심각"]),
        "brand": random.choice(["올리브영", "이마트", "스타벅스", "무신사", "배달의민족", "롯데온", "GS25", "CJ ONE", "마켓컬리"]),
        "coupon": random.choice(["무료배송 쿠폰", "장바구니 쿠폰", "생일 쿠폰", "첫 구매 쿠폰", "멤버십 쿠폰"]),
        "benefit_text": random.choice(["무료배송", "1+1", "포인트 2배", "사은품 증정", "오늘만 특가"]),
        "local_store": random.choice(["헬스장", "미용실", "치과", "학원", "카페", "세탁소", "동네마트"]),
        "menu": random.choice(["아메리카노", "샐러드", "피자", "치킨", "도시락", "샌드위치"]),
        "subscription": random.choice(["음악 스트리밍", "OTT", "클라우드", "정기배송", "멤버십"]),
        "campaign": random.choice(["봄맞이 행사", "신규회원 이벤트", "주말 특가", "월말 정산전", "앱 전용 행사"]),
        "service": random.choice(["네이버", "카카오", "Google", "Apple", "쿠팡", "토스", "Upbit", "Steam", "Microsoft"]),
        "device": random.choice(["iPhone", "Galaxy", "Windows PC", "MacBook", "Chrome 브라우저", "Android 태블릿"]),
        "browser": random.choice(["Chrome", "Safari", "Edge", "Firefox", "Samsung Internet"]),
        "dept": random.choice(["인사팀", "재무팀", "IT지원팀", "영업기획팀", "마케팅팀", "법무팀", "총무팀", "보안팀"]),
        "employee": random.choice(["김민수", "박지영", "이서연", "최현우", "정다은", "강준호", "오유진", "한지훈"]),
        "manager": random.choice(["김팀장", "박부장", "이과장", "최차장", "정대표"]),
        "rank": random.choice(["사원", "주임", "대리", "과장", "차장", "팀장", "부장"]),
        "project": random.choice(["분기 실적 보고", "신규 캠페인", "보안 점검", "고객 만족도 조사", "서버 이전", "계약 검토", "앱 개편"]),
        "meeting_room": random.choice(["대회의실", "중회의실", "4층 회의실", "화상회의", "프로젝트룸"]),
        "tool": random.choice(["그룹웨어", "Slack", "Teams", "Jira", "사내포털", "전자결재"]),
        "doc": random.choice(["회의록", "견적서", "계약서", "보고서", "지출결의서", "보안서약서"]),
        "client": random.choice(["A사", "B커머스", "한빛전자", "서울유통", "파트너사"]),
        "asset": random.choice(["노트북", "출입카드", "법인폰", "보안토큰", "모니터", "충전기"]),
        "office_notice": random.choice(["사무실 출입", "회의실 사용", "주차 등록", "좌석 이동", "출입통제"]),
        "header": maybe_header("web"),
        "ad_header": maybe_header("ad"),
        "name2": random.choice(["서연", "지아", "유진", "하린", "수빈", "민지"]),
        "random_day": random.randint(1, 28),
        "usd": f"{random.randint(5, 900)}.{random.randint(10, 99)}",
        "overseas_store": random.choice(["AMAZON", "PAYPAL", "AGODA", "APPLE", "GOOGLE", "AIRBNB"]),
        "country": random.choice(["US", "JP", "CN", "VN", "TH", "KR"]),
        "rate": random.randint(3, 9),
        "share_count": random.randint(1, 30),
    }
    return values


def apply_expanded_noise(text, category_idx):
    if random.random() < 0.06:
        text = text.replace("확인", random.choice(["확 인", "확인.", "확인요청"]), 1)
    if random.random() < 0.05:
        text = text.replace("안내", random.choice(["안내.", "안 내", "알림"]), 1)
    if category_idx == 4 and random.random() < 0.35 and "무료수신거부" not in text:
        text += "\n무료수신거부 080-000-0000"
    if random.random() < 0.05:
        text += random.choice([" .", " /", ""])
    return text.strip()


# 최종 대량 생성 시나리오 풀, URL은 `.test` 도메인만 사용
EXPANDED_SCENARIO_TEMPLATES = {
    0: {
        "DAILY_FAMILY": [
            "{family}, 오늘 {time_slot}쯤 들어갈 것 같아. 저녁은 먼저 드세요.",
            "{family} 지금 어디야? {item} 안 가져왔으면 {place}에서 같이 가자.",
            "{family}, 택배가 {pickup_place}에 있다고 해서 보이면 안으로 넣어줘.",
            "{family} 병원 예약을 {next_date} {time_slot}로 잡아뒀어. 시간 괜찮은지 확인해 줘.",
        ],
        "DAILY_FRIEND": [
            "{friend}야 오늘 {place}에서 {activity} 하는 거 맞지?",
            "나 15분 정도 늦을 것 같아. 먼저 들어가 있어.",
            "아까 말한 자료 단톡방에 올렸어. 빠진 부분이 있으면 알려 줘.",
            "오늘 메뉴 {food} 어때? 괜찮으면 내가 예약해둘게.",
        ],
        "APPOINTMENT": [
            "{date} {time_slot} 예약 확인드립니다. 방문이 어려우시면 사전에 연락 부탁드립니다.",
            "예약 시간이 {time_slot}로 변경되었습니다. 장소는 {place} 그대로입니다.",
            "{friend}님, 예약 대기 순번이 앞당겨졌습니다. 가능하시면 {deadline}까지 회신해 주세요.",
            "오늘 상담 예약이 있습니다. 예약 시간 10분 전까지 접수해 주세요.",
        ],
        "STUDY_SCHOOL": [
            "[{school}] {class_name} 과제 제출 기한은 {deadline}입니다.",
            "{teacher}입니다. 내일 준비물은 {item}입니다. 학생에게 전달 부탁드립니다.",
            "[{school}] 출결 확인 요청입니다. 결석 사유가 있으면 회신해 주세요.",
            "스터디 자료를 공유했습니다. {deadline}까지 문제를 풀어 주세요.",
        ],
        "EVENT_INVITE": [
            "{friend} 생일 모임 장소가 {place}로 변경됐어. 시간은 그대로야.",
            "이번 주말 집들이 하려고 해. 가능하면 {time_slot}쯤 와줘.",
            "동기 모임 참석자를 확인하고 있어. 참석할 수 있으면 {deadline}까지 답장 부탁해.",
            "{activity} 일정을 잡으려고 해. {next_date} 괜찮은지 알려 줘.",
        ],
        "MONEY_REQUEST": [
            "{friend}야 아까 계산한 회비 {small_amount} 보내줘. 계좌는 단톡에 올릴게.",
            "지난번 빌린 {amount} 오늘 입금했어. 늦어서 미안해.",
            "모임 예약금 먼저 냈어. 1인당 {small_amount}씩 보내주면 돼.",
            "{activity} 비용 정산했어. 네 몫은 {small_amount}이야.",
        ],
        "GIFT_NOTICE": [
            "{family} 생신 선물로 {item} 주문했어. 도착하면 포장만 부탁해.",
            "{friend}한테 보낼 선물 골랐는데 {deadline} 전에 의견 줘.",
            "기프티콘 보냈어. 문자함 확인해 봐.",
            "{food} 쿠폰 하나 남아서 보냈어. 오늘 안에 써도 돼.",
        ],
        "HEALTH_FAMILY": [
            "{family}, 약은 식후에 챙겨 드시고 물도 많이 드세요.",
            "{hospital} 검사 결과는 다음 주에 나온대. 문자 오면 알려줘.",
            "오늘 미세먼지 심하니까 외출할 때 마스크 챙겨.",
            "{family} 병원 접수번호 받으면 나한테도 보내줘.",
        ],
        "OBITUARY": [
            "{header}[부고] {friend}님의 {relation}께서 별세하셨기에 삼가 알려드립니다. 빈소: {hospital} 장례식장\n모바일 부고장: {url}",
            "[부고 알림] 고인의 마지막 길에 따뜻한 위로를 부탁드립니다. 빈소와 장례 일정 확인: {url}",
            "{header}부고 소식을 안내드립니다. 장례식장 위치와 조문 계좌는 모바일 안내장에서 확인해 주세요.\n{url}",
            "[부고] {masked_name}님의 {relation}께서 별세하셨습니다. 발인 일정 및 빈소 안내: {url}",
        ],
        "WEDDING": [
            "[모바일 청첩장] {friend} & {name2}의 결혼식에 초대합니다. 일시와 장소 확인: {url}",
            "{header}소중한 분들을 결혼식에 모시고자 합니다. 모바일 청첩장: {url}",
            "결혼식 참석 여부 확인 부탁드립니다. 식장 위치와 주차 안내: {url}",
            "[청첩장] {next_date} {hall}에서 뵙겠습니다. 참석 여부 회신: {url}",
        ],
        "CHILD_SCHOOL": [
            "[{school}] 학부모 상담 일정 안내입니다. 희망 시간을 회신해 주세요.",
            "[{school}] 급식비 납부 내역이 확인되었습니다.",
            "[{school}] 현장학습 동의서 제출 기한은 {deadline}입니다.",
            "[{school}] 학생 건강 상태 확인 문자입니다. 담임 선생님께 회신해 주세요.",
        ],
        "MOVE_HELP": [
            "{friend}야 {next_date} 이사하는데 시간 되면 1시간만 도와줄 수 있어?",
            "짐이 생각보다 많아서 {item} 챙겨와 주면 고마울 것 같아.",
            "{place} 근처에서 짐 내릴 예정이야. 도착하면 연락할게.",
            "이사 차량 예약했어. {time_slot} 전에 내려와 줘.",
        ],
        "FAMILY_IMPERSONATION": [
            "{family}, 나 휴대폰 액정이 나가서 임시폰으로 문자해. 본인 확인 좀 도와줘 {url}",
            "{family}, 급하게 결제해야 하는데 인증이 안 돼. 링크 들어가서 확인만 해 줘 {url}",
            "{family}, 지금 통화가 안 돼서 문자 남겨. 상품권 구매가 필요한데 잠깐 확인 부탁해 {url}",
            "{family}, 계정이 잠겨서 연락처 확인이 필요해. 내가 보낸 화면에서 확인해 줘 {url}",
        ],
        "LOST_PHONE_SCAM": [
            "나 {friend}인데 폰을 잃어버려서 임시번호로 보내. 급한 확인만 부탁해 {url}",
            "{family}, 지금 다른 사람 폰으로 문자해. 인증번호 받으면 알려 줘 {url}",
            "휴대폰이 고장 나서 은행 인증이 안 돼. 잠깐만 도와줘 {url}",
            "카톡 로그인이 안 돼서 문자 남겨. 친구 추가 전에 확인해 줘 {url}",
        ],
        "UTILITY_HOME": [
            "{family}, {utility} 고지서 나왔대. 내가 저녁에 확인할게.",
            "{family}, 관리사무소에서 {utility} 납부 안내가 왔다고 하네. 고지서가 있으면 사진만 보내 줘.",
            "{utility} 자동이체 등록 확인 문자 왔어. 내가 집 가서 다시 볼게.",
            "{family}, 이번 달 {utility} 납부일이 {next_date}래. 잊을까 봐 미리 알려.",
        ],
        "PET_CARE": [
            "{family}, {pet} 사료 거의 다 떨어졌대. 오는 길에 주문할게.",
            "{friend}야 오늘 집 비울 것 같아서 {pet} 밥 좀 한번만 봐줄 수 있어?",
            "{pet} 병원 예약이 {next_date} {time_slot}로 잡혔어. 시간 되면 같이 가자.",
            "{family}, {pet} 산책은 내가 늦으면 먼저 부탁해.",
        ],
        "PARENT_GROUP": [
            "[학부모방] 준비물은 {item}입니다. 등교 전에 확인해 주세요.",
            "[학부모 알림] 현장체험학습 귀가 시간은 {time_slot} 전후로 예정되어 있습니다.",
            "[반대표] 이번 주 간식비는 1인당 {small_amount}입니다. 가능하시면 오늘 중으로 보내 주세요.",
            "[학교 공지] 학부모 총회 참석 여부를 {deadline}까지 회신해 주세요.",
        ],
    },
    1: {
        "BANK_DEPOSIT": [
            "[{bank}] 입금 {amount}\n{date} {time}\n잔액 {large_amount}",
            "[{bank}] {masked_name}님으로부터 {amount} 입금되었습니다.",
            "[{bank}] 급여 입금 알림\n금액 {large_amount}\n계좌 {account}",
            "[{bank}] 이체 입금이 완료되었습니다. 상세 내역은 앱에서 확인해 주세요.",
        ],
        "BANK_WITHDRAWAL": [
            "[{bank}] 출금 {amount}\n{date} {time}\n받는분 {bill}",
            "[{bank}] ATM 출금 {amount}\n위치 {location}\n본인 거래가 아니면 고객센터로 문의하세요.",
            "[{bank}] 예약이체가 실행되었습니다. 금액 {amount}",
            "[{bank}] 계좌 {account}에서 {bill} 자동 납부가 처리되었습니다.",
        ],
        "AUTO_TRANSFER": [
            "[{bank}] {bill} 자동이체 예정 안내\n{next_date}에 {amount}이 출금될 예정입니다.",
            "[{bank}] 자동이체 실패\n잔액 부족으로 {bill} 납부가 처리되지 않았습니다.",
            "[{bank}] 자동이체 신청이 완료되었습니다. 출금일은 매월 {random_day}일입니다.",
            "[{bank}] 납부 예약 내역이 변경되었습니다. 앱에서 상세 내용을 확인해 주세요.",
        ],
        "CARD_APPROVAL": [
            "[{card}] 승인 {amount}\n{date} {time}\n가맹점 {store}",
            "[{card}] 일시불 승인 {amount}\n누적 이용금액 {large_amount}",
            "[{card}] 간편결제 승인\n{pay_app} {amount}\n{store}",
            "[{card}] 교통카드 후불 이용금액 {small_amount} 청구 예정입니다.",
        ],
        "CARD_CANCEL": [
            "[{card}] 승인취소 -{amount}\n{date} {time}\n처리 완료",
            "[{card}] 부분취소 {small_amount}\n가맹점 {store}",
            "[{card}] 환불 접수 완료. 카드사 반영까지 2~5일 소요될 수 있습니다.",
            "[{card}] 결제 취소 내역이 있습니다. 앱에서 확인해 주세요.",
        ],
        "OVERSEAS_PAYMENT": [
            "[{card}] 해외승인 USD {usd}\n가맹점 {overseas_store}",
            "[{card}] 해외 온라인 결제 승인\nKRW {amount}\n본인이 이용한 내역이 아니라면 즉시 신고해 주세요.",
            "[{card}] 해외 원화결제 차단 설정이 적용되었습니다.",
            "[{card}] 해외 이용 알림. 국가 {country}, 금액 {amount}",
        ],
        "PAY_TRANSFER": [
            "[{pay_app}] {amount} 결제 완료\n{date} {time}\n가맹점 {store}",
            "[{pay_app}] {masked_name}님에게 {small_amount} 송금 완료",
            "[{pay_app}] 포인트 {points} 적립 예정입니다.",
            "[{pay_app}] 송금 받기 요청이 도착했습니다. 앱에서 확인하세요.",
        ],
        "SECURITIES_TRADE": [
            "[{securities}] {stock} {share_count}주 체결 완료",
            "[{securities}] 예약 주문이 접수되었습니다. 체결 여부는 장 시작 후 확인해 주세요.",
            "[{securities}] 미수금이 발생했습니다. {deadline}까지 확인해 주세요.",
            "[{securities}] 공모주 청약 배정 결과가 등록되었습니다.",
        ],
        "STOCK_DIVIDEND": [
            "[{securities}] 배당금 {small_amount} 입금 예정\n종목 {stock}",
            "[{securities}] 배당소득세 원천징수 내역이 등록되었습니다.",
            "[{securities}] 외화 배당금 입금 알림. 상세 내역은 앱에서 확인하세요.",
            "[{securities}] 주식 입고 처리 완료. 종목 {stock}",
        ],
        "INSURANCE_BILL": [
            "[{insurance}] 보험료 {amount} 출금 예정입니다. 출금일은 {next_date}입니다.",
            "[{insurance}] 보험금 청구 서류가 접수되었습니다.",
            "[{insurance}] 자동차보험 갱신 안내. 만기 전 조건을 확인해 주세요.",
            "[{insurance}] 청구 심사가 완료되었습니다. 지급 예정 금액 {amount}",
        ],
        "LOAN_AD": [
            "{ad_header}[{bank}] 비대면 신용대출 한도를 조회할 수 있습니다. 예상 한도는 최대 {large_amount}\n상담: {url}",
            "{ad_header}정부 지원 서민 대출 대상자 확인 안내입니다. 금리는 연 {rate}%대까지 가능합니다.\n{url}",
            "{ad_header}기존 대출 대환 안내입니다. 중도상환수수료 조건 확인: {url}",
            "{ad_header}직장인 우대 한도 사전 조회입니다. 신용점수에 영향 없이 확인: {url}",
        ],
        "LIMIT_INCREASE": [
            "[{card}] 이용한도 변경 신청이 접수되었습니다.",
            "[{card}] 임시 한도 상향 신청 대상입니다. 앱에서 신청 여부를 확인해 주세요.",
            "[{bank}] 이체한도 변경 완료. 본인이 아니면 고객센터로 문의하세요.",
            "[{card}] 해외 이용한도 설정이 변경되었습니다.",
        ],
        "PAYMENT_SCAM": [
            "{header}[{card}] 본인 미사용 결제 {amount} 발생. 취소 요청: {url}",
            "{header}해외 IP에서 결제가 시도되었습니다. 본인 확인 후 차단 진행: {url}",
            "[{bank}] 계좌 신규 개설 시도가 감지되었습니다. 본인이 아니라면 즉시 확인해 주세요: {url}",
            "[{card}] 고액 결제 대기 중. 취소하지 않으면 승인될 수 있습니다: {url}",
        ],
        "ACCOUNT_RESTRICT_SCAM": [
            "{header}[{bank}] 보안 등급이 곧 만료됩니다. 갱신하지 않으면 일부 거래가 제한됩니다.\n갱신: {url}",
            "{header}전자금융 이상 거래가 감지되어 계좌가 임시 제한되었습니다. 해제를 신청하세요: {url}",
            "[금융보안센터] 고객님 명의 계좌에 비정상 접근이 감지되었습니다. 확인해 주세요: {url}",
            "[{bank}] 장기 미사용 계좌 보호조치 예정. 본인 인증: {url}",
        ],
        "INVESTMENT_SCAM": [
            "{ad_header}[투자정보] {stock} 단기 급등 예상 리포트가 공개되었습니다. 무료로 확인해 보세요: {url}",
            "{header}가상자산 출금 제한을 해제하려면 지갑 인증이 필요합니다: {url}",
            "[리딩방 초대] 오늘의 추천 종목과 매수가를 확인하세요: {url}",
            "{ad_header}원금 보장형 투자 상품의 사전 신청 마감이 임박했습니다: {url}",
        ],
        "SAVINGS_MATURITY": [
            "[{bank}] 적금 만기 예정 안내. 만기일은 {next_date}입니다.",
            "[{bank}] 예금 만기 후 자동 재예치 여부를 확인해 주세요.",
            "[{bank}] 만기 해지가 가능한 상품이 있습니다. 앱에서 바로 처리할 수 있습니다.",
            "[{bank}] 만기 이자 예상 금액은 {small_amount}입니다.",
        ],
        "LOAN_REPAYMENT": [
            "[{bank}] 대출 상환일은 {next_date}입니다. 출금 계좌 잔액을 확인해 주세요.",
            "[{bank}] 원리금 상환이 완료되었습니다. 상세 내역은 앱에서 확인하세요.",
            "[{bank}] 대출 약정 변경 신청이 접수되었습니다.",
            "[{bank}] 중도상환 가능 금액 안내가 도착했습니다.",
        ],
        "BILLING_NOTICE": [
            "[{card}] 이번 달 청구 예정 금액은 {large_amount}입니다.",
            "[{card}] 결제대금 결제일은 {next_date}입니다.",
            "[{insurance}] 보험료 납부 영수증이 발행되었습니다.",
            "[{bank}] {utility} 납부 내역이 등록되었습니다.",
        ],
    },
    2: {
        "SHOPPING_ORDER": [
            "[{shop}] 주문이 완료되었습니다.\n주문번호 {order}\n상품: {product}",
            "[{shop}] 결제가 완료되었습니다. 금액: {amount}\n배송 준비가 시작되었습니다.",
            "[{shop}] 주문 내역이 변경되었습니다. 앱에서 상세 내용을 확인해 주세요.",
            "[{shop}] 선물하기 주문이 접수되었습니다. 수신자 정보를 확인해 주세요.",
        ],
        "PAYMENT_COMPLETE": [
            "[{shop}] {product} 결제 완료\n금액 {amount}",
            "[{pay_app}] {shop} 결제가 정상 처리되었습니다.",
            "[{shop}] 무통장 입금 확인 완료. 상품 준비 중입니다.",
            "[{shop}] 예약 구매가 완료되었습니다. 출고 예정일 {next_date}",
        ],
        "COURIER_PICKUP": [
            "[{carrier}] 택배가 집하되었습니다.\n운송장 {invoice}",
            "[{carrier}] 반품 회수 접수 완료. 방문 예정일 {next_date}",
            "[{carrier}] 편의점 택배 접수가 완료되었습니다. 배송 조회는 잠시 후 가능합니다.",
            "[{carrier}] 택배 인수가 완료되었습니다. 배송 상태는 앱에서 확인해 주세요.",
        ],
        "COURIER_OUT": [
            "[{carrier}] 고객님의 택배 배송이 시작되었습니다.\n운송장 {invoice}",
            "[{carrier}] 오늘 {time_slot} 전후에 배송될 예정입니다.",
            "[{carrier}] 배송 기사가 방문할 예정입니다. 부재 시 {pickup_place}에 보관될 수 있습니다.",
            "[{carrier}] 배송 중입니다. 수령 장소: {pickup_place}",
        ],
        "DELIVERY_DONE": [
            "[{carrier}] 배송 완료\n{pickup_place}에 두었습니다. 이용해 주셔서 감사합니다.",
            "[{shop}] 주문하신 상품이 배송 완료되었습니다.",
            "[{carrier}] 수령 확인이 완료되었습니다. 문의 사항이 있으면 고객센터로 연락해 주세요.",
            "[{shop}] 구매확정 전 상품 상태를 확인해 주세요.",
        ],
        "DELIVERY_DELAY": [
            "[{carrier}] 물량 증가로 배송이 지연되고 있습니다. 예상 도착일 {next_date}",
            "[{shop}] 일부 상품 입고 지연으로 배송 일정이 변경되었습니다.",
            "[{carrier}] 기상 악화로 배송이 지연될 수 있습니다.",
            "[{carrier}] 주소 확인이 필요해 배송이 보류되었습니다. 고객센터에 문의해 주세요.",
        ],
        "RETURN_EXCHANGE": [
            "[{shop}] 교환 접수가 완료되었습니다. 회수 일정은 별도로 안내해 드립니다.",
            "[{carrier}] 반품 상품 회수 예정입니다. 상품을 포장해 주세요.",
            "[{shop}] 환불이 접수되었습니다. 결제 수단에 반영되기까지 시간이 걸릴 수 있습니다.",
            "[{shop}] 교환 상품이 출고되었습니다. 운송장 {invoice}",
        ],
        "FRESH_DELIVERY": [
            "[{shop}] 새벽배송이 시작되었습니다. 도착 전 알림을 보내드립니다.",
            "[{shop}] 냉장 상품이 {pickup_place}에 배송되었습니다.",
            "[{shop}] 신선식품 품절로 일부 상품이 환불 처리됩니다.",
            "[{shop}] 오늘 도착 예정인 상품의 포장이 완료되었습니다.",
        ],
        "CUSTOMS_NORMAL": [
            "[관세청] 수입신고가 정상 처리되었습니다. 배송사에 인계될 예정입니다.",
            "[국제우편] 통관이 완료되어 국내 배송이 시작됩니다.",
            "[관세청] 개인통관고유부호 확인이 완료되었습니다.",
            "[해외 배송] 통관 심사가 진행 중입니다. 추가 요청이 있으면 별도로 안내해 드립니다.",
        ],
        "CUSTOMS_SCAM": [
            "{header}[관세청] 해외 배송 물품의 통관이 보류되었습니다. 개인통관고유부호 확인이 필요합니다: {url}",
            "[국제 배송] 수취인 정보에 오류가 있어 통관이 지연되고 있습니다. 정보를 수정해 주세요: {url}",
            "{header}수입신고 물품의 관세 미납 안내입니다. 납부 확인 후 배송이 진행됩니다: {url}",
            "[해외 직구] 세관 반송 예정입니다. 오늘 안에 통관 정보를 수정해 주세요: {url}",
        ],
        "ADDRESS_SCAM": [
            "{header}[{carrier}] 주소 일부가 누락되어 배송이 보류되었습니다. 주소를 다시 확인해 주세요: {url}",
            "[택배 알림] 수취인 연락처 오류로 배송에 실패했습니다. 재배송을 신청해 주세요: {url}",
            "{header}배송지 확인이 필요합니다. 오늘 안에 확인하지 않으면 반송될 수 있습니다: {url}",
            "[{carrier}] 부재중으로 배송이 완료되지 않았습니다. 배송비 결제 후 재방문을 신청할 수 있습니다: {url}",
        ],
        "MISSED_DELIVERY_SCAM": [
            "{header}부재중인 택배를 보관 중입니다. 보관료가 발생하기 전에 수령을 신청하세요: {url}",
            "[택배센터] 미수령 상품 반송 예정. 수령지 변경: {url}",
            "[{carrier}] 배송에 두 차례 실패했습니다. 최종 배송 일정을 확인해 주세요: {url}",
            "고객님의 택배가 지점에 보관 중입니다. 보관 위치를 확인해 주세요: {url}",
        ],
        "RESERVATION_TICKET": [
            "[KORAIL] 승차권 예매 완료\n{route}\n좌석 {seat}",
            "[CGV] 예매 완료\n영화: {movie}\n상영일: {next_date}\n좌석: {seat}",
            "[SRT] 열차 출발 안내입니다. 승차권의 열차 번호와 좌석을 다시 확인해 주세요.",
            "[공연예매] 티켓 예매가 완료되었습니다. 입장 전 모바일 티켓을 준비해 주세요.",
        ],
        "TRAVEL_CHECKIN": [
            "[{airline}] 모바일 체크인 안내\n편명: {flight}\n출발 3시간 전까지 공항에 도착해 주세요.",
            "[{airline}] 항공권 결제 완료\n노선 {route}\n예약번호 {order}",
            "[{airline}] 탑승구 변경 안내. 공항 전광판을 확인해 주세요.",
            "[숙박 예약] 체크인 안내가 도착했습니다. 예약 번호: {order}",
        ],
        "PICKUP_LOCKER": [
            "[{carrier}] 무인택배함에 보관되었습니다. 보관 위치를 확인해 주세요.",
            "[{carrier}] 픽업 코드가 발급되었습니다. 코드를 입력하고 상품을 수령하세요.",
            "[{carrier}] 편의점 택배 도착 안내입니다. {deadline}까지 수령할 수 있습니다.",
            "[{shop}] 주문 상품이 수령 대기 상태입니다. 보관 장소: {pickup_place}",
        ],
        "MARKETPLACE_TRADE": [
            "[중고거래] 안전결제 요청이 접수되었습니다. 거래 내역을 확인해 주세요.",
            "[중고거래] 구매자가 입금을 완료했습니다. 배송 준비를 부탁드립니다.",
            "[중고거래] 거래 예약 시간이 {time_slot}로 확정되었습니다.",
            "[중고거래] 택배 거래 운송장 등록이 완료되었습니다.",
        ],
        "SUBSCRIPTION_BOX": [
            "[정기배송] 이번 달 {product} 발송 준비가 완료되었습니다.",
            "[정기배송] 결제가 완료되어 {next_date} 출고 예정입니다.",
            "[정기배송] 상품 구성 변경 안내가 도착했습니다.",
            "[정기배송] 배송 건너뛰기 신청이 반영되었습니다.",
        ],
    },
    3: {
        "GOV24_DOC": [
            "[정부24] 신청하신 {document} 발급이 완료되었습니다. 정부24 앱에서 확인해 주세요.",
            "[정부24] 민원 신청이 접수되었습니다. 처리 결과는 문자로 안내됩니다.",
            "[정부24] 보완 요청이 있습니다. 신청 내역을 확인해 주세요.",
            "[정부24] 전자문서지갑에 새 문서가 도착했습니다.",
        ],
        "RESIDENT_SURVEY": [
            "[행정안전부] 주민등록 사실조사 참여 안내입니다. 세대 확인에 협조해 주세요.",
            "[주민센터] 전입신고 처리 결과가 등록되었습니다.",
            "[행정복지센터] 민원 예약 시간이 {time_slot}로 확정되었습니다.",
            "[국민비서] 생활정보 알림이 도착했습니다. 자세한 내용은 국민비서에서 확인해 주세요.",
        ],
        "TAX_NOTICE": [
            "[국세청] {tax} 신고 안내입니다. 신고 기한 내 홈택스에서 확인해 주세요.",
            "[국세청] 전자고지 신청이 완료되었습니다.",
            "[국세청] 신고 도움 자료가 제공되었습니다. 홈택스에서 확인해 주세요.",
            "[세무서] 납부 기한이 다가왔습니다. 기한 내 납부해 주세요.",
        ],
        "TAX_REFUND": [
            "[국세청] 환급금 지급 예정 안내. 지급 계좌 등록 여부를 확인해 주세요.",
            "[국세청] {tax} 환급 검토가 완료되었습니다.",
            "[국세청] 환급금은 {next_date}에 지급될 예정입니다.",
            "[홈택스] 환급 신청서가 접수되었습니다. 처리 결과를 기다려 주세요.",
        ],
        "LOCAL_TAX": [
            "[지방세] {tax} 납부 기한이 다가왔습니다. 위택스 또는 은행 앱에서 납부할 수 있습니다.",
            "[시청] {fine} 고지서가 발송되었습니다.",
            "[위택스] 전자 납부 번호가 등록되었습니다. 기한 내 납부해 주세요.",
            "[구청] 지방세 자동납부 신청이 완료되었습니다.",
        ],
        "HEALTH_CHECKUP": [
            "[국민건강보험] 건강검진 대상자 안내입니다. 검진 기관을 예약한 후 방문해 주세요.",
            "[건강보험공단] 보험료 고지서가 발송되었습니다. 납부 기한을 확인해 주세요.",
            "[국민건강보험] 자격 변동 내역이 있습니다. 공단 앱에서 확인해 주세요.",
            "[건강검진센터] 예약 시간이 {time_slot}로 확정되었습니다. 방문 일정을 확인해 주세요.",
        ],
        "VACCINE": [
            "[질병관리청] 예방접종 예약 변경 안내. 예약 내역을 확인해 주세요.",
            "[질병관리청] 예방접종 증명서 발급이 완료되었습니다.",
            "[보건소] 접종 예약일은 {next_date} {time_slot}입니다.",
            "[질병관리청] 이상반응 신고 안내 문자가 발송되었습니다.",
        ],
        "NATIONAL_PENSION": [
            "[국민연금] 가입내역 안내서가 발송되었습니다.",
            "[국민연금] 보험료 납부 확인서 발급이 완료되었습니다.",
            "[국민연금] 예상연금액 조회 결과가 업데이트되었습니다.",
            "[국민연금] 자격 변동 신고 처리 결과를 확인해 주세요.",
        ],
        "EMPLOYMENT_INSURANCE": [
            "[고용보험] 실업급여 신청 일정 안내. 방문 예약을 확인해 주세요.",
            "[고용노동부] 국민취업지원제도 상담 일정이 확정되었습니다.",
            "[근로복지공단] 산재 신청 서류가 접수되었습니다.",
            "[고용보험] 이직확인서 처리 상태가 변경되었습니다.",
        ],
        "SCHOOL_ADMIN": [
            "[교육청] 학부모 서비스 가입 안내가 도착했습니다.",
            "[교육청] 학교생활기록부 발급 신청이 접수되었습니다.",
            "[장학재단] 장학금 신청 서류 보완이 필요합니다.",
            "[교육청] 민원 처리 결과가 등록되었습니다.",
        ],
        "POLICE_SCAM": [
            "{header}[경찰청] 사건번호 {case_no} 관련 출석요구서가 도착했습니다. 확인해 주세요: {url}",
            "[사이버수사대] 귀하 명의 계좌가 범죄에 연루된 정황이 있어 확인이 필요합니다: {url}",
            "{header}수사 협조 요청입니다. 확인하지 않으면 불이익이 발생할 수 있습니다. 확인: {url}",
            "[경찰 민원] 전자문서가 도착했습니다. 본인 인증 후 열람해 주세요: {url}",
        ],
        "COURT_SCAM": [
            "{header}[법원] 등기 우편이 반송되어 전자문서 송달을 안내드립니다: {url}",
            "[대한민국 법원] 지급명령 관련 문서가 도착했습니다. 열람해 주세요: {url}",
            "{header}민사소송 통지서 확인 요청입니다. 본인 인증 후 열람할 수 있습니다: {url}",
            "[법원행정처] 아직 열람하지 않은 문서가 있습니다. 기한 내 확인해 주세요: {url}",
        ],
        "SUBSIDY_SCAM": [
            "{header}[복지지원센터] {benefit} 대상자로 선정되었습니다. 신청해 주세요: {url}",
            "[정부 지원금] 미수령 환급금이 있습니다. 지급 계좌를 확인해 주세요: {url}",
            "{header}소상공인 지원금 추가 접수 안내입니다. 마감 전에 신청해 주세요: {url}",
            "[민생 지원] 본인 부담금 없이 지원을 신청할 수 있습니다: {url}",
        ],
        "FINE_SCAM": [
            "{header}[교통 민원] {fine} 미납 내역을 확인하고 납부해 주세요: {url}",
            "[전자고지] 미납 과태료가 있습니다. 납부 기한 전에 확인해 주세요: {url}",
            "[구청] 불법 주정차 과태료 고지서를 확인해 주세요: {url}",
            "[민원24] 처리되지 않은 고지서가 있습니다. 본인 확인 후 열람해 주세요: {url}",
        ],
        "CIVIL_DEFENSE": [
            "[민방위] 교육 일정 안내가 도착했습니다. 교육일은 {next_date}입니다.",
            "[민방위] 사이버 교육 이수 기한은 {deadline}입니다.",
            "[민방위] 전자통지서가 발송되었습니다. 교육 장소를 확인해 주세요.",
            "[민방위] 교육 이수 처리 결과가 등록되었습니다.",
        ],
        "DISASTER_ALERT": [
            "[재난문자] {location} 지역 안전 안내. 재난 단계는 {alert_level}입니다.",
            "[안전 안내 문자] 기상 악화로 외출할 때 주의해 주세요.",
            "[재난안전] 폭염 대비 행동요령을 확인해 주세요.",
            "[재난문자] 강풍 예보로 시설물 점검을 권고합니다.",
        ],
        "WELFARE_NOTICE": [
            "[복지로] 신청하신 복지 서비스 처리 결과가 등록되었습니다.",
            "[복지로] 자격 확인을 위해 추가 서류를 제출해 주세요.",
            "[고용복지센터] 상담 일정은 {next_date} {time_slot}입니다.",
            "[복지알림] 지원금 지급 예정일은 {next_date}입니다.",
        ],
    },
    4: {
        "STORE_COUPON": [
            "{ad_header}[{brand}] 오늘만 사용 가능한 {percent}% 할인 쿠폰이 도착했습니다.\n{url}",
            "{ad_header}장바구니 상품 재입고 안내입니다. 지금 구매하면 {coupon}을 적용받을 수 있습니다.\n{url}",
            "{ad_header}첫 구매 고객님께 {benefit_text} 혜택을 드립니다. 확인해 주세요: {url}",
            "[{brand}] 앱 전용 쿠폰이 발급되었습니다. 마이페이지에서 확인해 주세요.",
        ],
        "BRAND_SALE": [
            "{ad_header}[{brand}] 시즌 오프 최대 {percent}% 할인 행사가 시작되었습니다.\n{url}",
            "{ad_header}단 하루 특가가 시작되었습니다. 인기 상품을 한정 수량으로 판매합니다.\n{url}",
            "{ad_header}멤버십 고객 전용 사전 세일이 시작되었습니다.\n{url}",
            "{ad_header}[{brand}] 신상품 출시 기념 특별 혜택을 안내드립니다.",
        ],
        "MEMBERSHIP_POINT": [
            "[{brand}] 고객님의 멤버십 포인트 {points}가 적립되었습니다.",
            "[{brand}] 등급 유지에 필요한 이용 금액이 {amount} 남았습니다.",
            "[CJ ONE] 포인트 적립 완료. 앱에서 상세 내역을 확인하세요.",
            "[{brand}] 이번 달 멤버십 혜택이 업데이트되었습니다.",
        ],
        "POINT_EXPIRY": [
            "[{brand}] 고객님의 포인트 {points}가 곧 소멸됩니다.",
            "{ad_header}소멸 예정 포인트로 교환할 수 있는 쿠폰을 확인해 보세요: {url}",
            "[{brand}] 이번 달 말 소멸 포인트가 있습니다.",
            "{ad_header}포인트 사용처가 추가되었습니다. 자세히 보기: {url}",
        ],
        "EVENT_ENTRY": [
            "{ad_header}[{brand}] 구매 고객 대상 이벤트 응모가 완료되었습니다.",
            "{ad_header}리뷰 작성 시 {points}를 드리는 이벤트가 진행 중입니다.\n{url}",
            "[{brand}] 출석 체크 이벤트 참여가 완료되었습니다.",
            "{ad_header}친구 초대 이벤트 혜택을 확인해 보세요: {url}",
        ],
        "EVENT_WIN": [
            "{ad_header}이벤트 당첨 안내. 경품 수령을 위해 배송 정보를 입력해 주세요: {url}",
            "[{brand}] 리뷰 이벤트 당첨 축하드립니다. 쿠폰이 지급되었습니다.",
            "{ad_header}설문 참여 고객 추첨 결과입니다. 당첨 여부를 확인해 보세요: {url}",
            "[{brand}] 당첨 경품을 발송할 예정입니다. 주소를 확인해 주세요.",
        ],
        "PRICE_ALERT": [
            "[가격 알림] 관심 상품 가격이 {percent}% 하락했습니다. 지금 확인해 보세요.",
            "[쇼핑 알림] 찜한 상품의 재고가 얼마 남지 않았습니다.",
            "[특가 알림] 최근 본 상품이 오늘만 적용되는 가격으로 변경되었습니다.",
            "[{brand}] 관심 브랜드의 신상품이 입고되었습니다.",
        ],
        "RESTOCK": [
            "[{brand}] 품절 상품이 재입고되었습니다.",
            "[재입고 알림] 요청하신 {product} 상품이 입고되었습니다.",
            "{ad_header}재입고 상품을 한정 수량으로 판매 중입니다. 확인해 주세요: {url}",
            "[{brand}] 알림을 신청한 상품을 지금 구매할 수 있습니다.",
        ],
        "FOOD_DELIVERY_COUPON": [
            "{ad_header}[배달 쿠폰] 오늘 {menu} 주문 시 {small_amount} 할인 혜택을 드립니다.\n{url}",
            "[배달의민족] 바로 사용 가능한 쿠폰이 도착했습니다.",
            "{ad_header}우리 동네 인기 가게에서 {percent}% 할인 행사를 진행 중입니다.\n{url}",
            "[요기요] 포장 주문 시 할인 혜택을 받을 수 있습니다.",
        ],
        "LOCAL_STORE": [
            "{ad_header}우리 동네 신규 {local_store} 오픈 이벤트입니다. 방문 고객에게 {benefit_text}을 드립니다.\n{url}",
            "{ad_header}근처 매장에서 사용할 수 있는 쿠폰이 도착했습니다.\n{url}",
            "{ad_header}주말 예약 고객 할인 안내입니다. 남은 예약 시간을 확인해 보세요: {url}",
            "[지역 알림] {local_store} 예약 시간이 확정되었습니다.",
        ],
        "SUBSCRIPTION": [
            "[{subscription}] 정기결제 예정일은 {next_date}입니다.",
            "{ad_header}[{subscription}] 첫 달 무료 체험 혜택 안내\n{url}",
            "[{subscription}] 이용권이 곧 만료됩니다.",
            "{ad_header}프리미엄으로 전환하면 {percent}% 할인 혜택을 받을 수 있습니다.\n{url}",
        ],
        "BEAUTY": [
            "{ad_header}[{brand}] 뷰티 데이 최대 {percent}% 할인\n{url}",
            "[{brand}] 예약하신 피부 상담 시간이 {time_slot}입니다.",
            "{ad_header}오늘의 뷰티 특가 상품이 공개되었습니다.\n{url}",
            "[{brand}] 구매하신 화장품의 리뷰를 작성하면 포인트가 지급됩니다.",
        ],
        "TRAVEL_PROMO": [
            "{ad_header}[여행 특가] {route} 항공권 특가가 시작되었습니다.\n{url}",
            "{ad_header}숙박 예약 고객에게 쿠폰을 드립니다.\n{url}",
            "[여행 알림] 관심 지역 숙소 가격이 하락했습니다.",
            "{ad_header}연휴 렌터카 예약 할인 혜택 마감이 임박했습니다: {url}",
        ],
        "SURVEY_REWARD": [
            "{ad_header}설문에 참여하면 {points}를 드립니다. 참여하기: {url}",
            "[{brand}] 고객 만족도 조사에 참여해 주세요.",
            "{ad_header}1분 설문을 완료하면 쿠폰을 바로 드립니다.\n{url}",
            "[리서치] 참여하신 설문 보상이 지급되었습니다.",
        ],
        "APP_PUSH": [
            "[{brand}] 앱 푸시 수신 동의 고객 전용 혜택이 도착했습니다.",
            "{ad_header}[{brand}] 앱에서만 사용할 수 있는 {coupon}을 드립니다.\n{url}",
            "[{brand}] 앱에 처음 접속한 고객에게 {benefit_text}을 드리는 이벤트가 진행 중입니다.",
            "{ad_header}{campaign} 기념 앱 전용 특가를 확인해 보세요.\n{url}",
        ],
        "SEASONAL_PROMO": [
            "{ad_header}[{brand}] 시즌 한정 {percent}% 할인 행사가 시작되었습니다.\n{url}",
            "{ad_header}연휴 맞이 특가 상품이 공개되었습니다.\n{url}",
            "[{brand}] 월말 결산 세일이 진행 중입니다.",
            "{ad_header}주말 한정 쿠폰이 발급되었습니다. 사용 기한을 확인해 주세요: {url}",
        ],
        "RESERVATION_PROMO": [
            "{ad_header}[{local_store}] 예약 고객에게 추가 할인 혜택을 안내드립니다.\n{url}",
            "[{local_store}] 예약 확정 시 음료 쿠폰이 제공됩니다.",
            "{ad_header}예약 가능한 시간대가 열렸습니다. 빠르게 확인해 보세요.\n{url}",
            "[{local_store}] 재방문 고객은 전용 예약 혜택을 받을 수 있습니다.",
        ],
    },
    5: {
        "OTP_CODE": [
            "[{service}] 인증번호 [{code}]를 입력해 주세요. 타인에게 알려주지 마세요.",
            "[본인 확인] 인증번호는 {code}입니다. 3분 이내에 입력해 주세요.",
            "[간편인증] 요청하신 인증번호는 {code}입니다.",
            "[{service}] 로그인 인증 코드는 {code8}입니다.",
        ],
        "SIMPLE_AUTH": [
            "[{service}] 간편인증 요청이 도착했습니다. 앱에서 승인해 주세요.",
            "[PASS] 본인 확인 요청이 있습니다. 요청 기관을 확인한 후 진행해 주세요.",
            "[{bank}] 공동인증서 인증 요청이 접수되었습니다.",
            "[{service}] QR 로그인 승인 요청이 도착했습니다.",
        ],
        "LOGIN_ALERT": [
            "[{service}] 새 기기에서 로그인되었습니다.\n기기: {device}\nIP: {ip}",
            "[카카오톡] PC 버전 로그인 알림입니다. 본인이 아니라면 즉시 비밀번호를 변경해 주세요.",
            "[네이버] 해외 로그인 차단 설정으로 접근이 차단되었습니다. IP {ip}",
            "[{service}] {location} 지역에서 로그인 시도가 있었습니다.",
        ],
        "NEW_DEVICE": [
            "[{service}] 새 기기가 계정에 등록되었습니다. 기기: {device}",
            "[Apple] Apple ID가 {device}에서 사용되었습니다.",
            "[Google] 보안 키 등록 요청이 감지되었습니다.",
            "[{service}] 새 브라우저 {browser}에서 접속했습니다.",
        ],
        "PASSWORD_CHANGE": [
            "[{service}] 비밀번호가 변경되었습니다. 본인이 아니라면 고객센터로 문의하세요.",
            "[보안알림] 계정 복구 이메일이 변경되었습니다.",
            "[{service}] 2단계 인증 설정이 완료되었습니다.",
            "[{service}] 비밀번호 재설정 링크가 요청되었습니다.",
        ],
        "ACCOUNT_RECOVERY": [
            "[{service}] 계정 복구 코드입니다: [{code}] 요청하지 않았다면 무시하세요.",
            "[고객센터] 아이디 찾기 결과가 발송되었습니다.",
            "[{service}] 휴면 계정 해제용 인증번호는 {code}입니다.",
            "[{service}] 계정 복구 신청이 접수되었습니다.",
        ],
        "DEVICE_LINK": [
            "[카카오] 새 기기 연결 요청이 있습니다. 연결 코드는 {code}입니다.",
            "[{service}] 연결된 기기 목록이 변경되었습니다.",
            "[{service}] 기기 연결 해제가 완료되었습니다.",
            "[{service}] 앱 연동 승인 요청이 있습니다.",
        ],
        "PAYMENT_AUTH": [
            "[{pay_app}] 결제 인증번호는 {code}입니다. 결제를 요청한 경우에만 입력하세요.",
            "[{card}] 온라인 결제 본인 확인 요청이 있습니다.",
            "[{bank}] 이체 인증번호는 {code}입니다. 타인에게 알려주지 마세요.",
            "[{service}] 구매 인증이 요청되었습니다. 결제 금액: {amount}",
        ],
        "CRYPTO_WITHDRAW": [
            "[Upbit] 출금 요청 인증번호는 {code}입니다.",
            "[Upbit] 가상자산 출금 신청이 접수되었습니다. 본인이 아니라면 즉시 문의하세요.",
            "[Bithumb] 새 지갑 주소가 등록되었습니다.",
            "[{service}] 보안 등급 변경 요청이 있습니다.",
        ],
        "GAME_OTP": [
            "[NEXON] OTP 인증번호 [{code8}]를 입력해 주세요.",
            "[Steam] 새 기기 로그인 코드 {code}입니다.",
            "[게임보안] 해외 IP 접속 시도가 차단되었습니다. IP {ip}",
            "[{service}] 계정 보호를 위해 비밀번호를 변경해 주세요.",
        ],
        "CLOUD_SECURITY": [
            "[Microsoft] 계정 보안 정보가 업데이트되었습니다.",
            "[Google] 드라이브 공유 설정이 변경되었습니다.",
            "[iCloud] 저장 공간 결제 확인이 필요합니다.",
            "[{service}] 클라우드 백업이 완료되었습니다.",
        ],
        "EMAIL_CHANGE": [
            "[{service}] 로그인 이메일이 변경되었습니다.",
            "[{service}] 복구 전화번호가 010-****-{phone_suffix}로 변경되었습니다.",
            "[{service}] 알림 수신 이메일이 추가되었습니다.",
            "[{service}] 계정 정보 변경 확인 메일이 발송되었습니다.",
        ],
        "SECURITY_SCAM": [
            "{header}[{service}] 계정이 임시 제한되었습니다. 본인 확인: {url}",
            "{header}비정상 로그인이 감지되어 보안 점검이 필요합니다. 즉시 확인해 주세요: {url}",
            "[보안센터] 인증이 곧 만료됩니다. 서비스 이용이 제한되기 전에 갱신하세요: {url}",
            "[{service}] 계정 보호조치 해제를 위해 인증을 완료해 주세요: {url}",
        ],
        "VERIFICATION_EXPIRE_SCAM": [
            "{header}[본인 인증] 인증 유효 기간이 만료됩니다. 재인증: {url}",
            "[{service}] 장기간 미접속으로 계정이 삭제될 예정입니다. 유지 신청: {url}",
            "{header}보안 약관 변경으로 재동의가 필요합니다: {url}",
            "[인증센터] 완료되지 않은 인증 요청이 있습니다. 확인해 주세요: {url}",
        ],
        "APPROVAL_PUSH": [
            "[{service}] 승인 요청이 도착했습니다. 요청한 작업이 맞으면 확인해 주세요.",
            "[{service}] 새 브라우저 인증 승인이 필요합니다.",
            "[보안승인] 로그인 시도에 대한 승인 여부를 선택해 주세요.",
            "[{service}] 기기 변경 승인 요청이 접수되었습니다.",
        ],
        "SESSION_EXPIRE": [
            "[{service}] 보안 세션이 만료되어 다시 로그인해 주세요.",
            "[{service}] 장시간 미사용으로 자동 로그아웃되었습니다.",
            "[{service}] 접속 유지 시간이 종료되었습니다. 재인증이 필요합니다.",
            "[{service}] 새 약관 적용을 위해 다시 로그인해 주세요.",
        ],
        "PRIVACY_UPDATE": [
            "[{service}] 개인정보 처리방침이 변경되었습니다.",
            "[{service}] 계정 보안 설정 점검을 권장합니다.",
            "[{service}] 마케팅 수신 설정이 변경되었습니다.",
            "[{service}] 로그인 기록 보관 정책이 업데이트되었습니다.",
        ],
    },
    6: {
        "MEETING_CHANGE": [
            "[{dept}] 오늘 회의 시간이 {time_slot}로 변경되었습니다.",
            "{employee} {rank}님, {project}와 관련해 10분 정도 미팅 가능하실까요?",
            "내일 오전 회의 자료를 {tool}에 업로드해 주세요.",
            "[회의 알림] {meeting_room} 예약이 확정되었습니다.",
        ],
        "HR_EDUCATION": [
            "[인사팀] 법정 의무 교육 수강 기한이 {deadline}까지입니다.",
            "[인사팀] 신규 입사자 교육 일정이 확정되었습니다.",
            "[교육 알림] 개인정보 보호 교육을 아직 수강하지 않은 분은 확인해 주세요.",
            "[인사팀] 교육 이수증을 제출해 주세요.",
        ],
        "HR_ATTENDANCE": [
            "[인사팀] 연차 사용 계획을 제출해 주세요. {deadline}까지 회신해 주세요.",
            "[근태 알림] 오늘 지각 처리 내역이 있습니다. 확인해 주세요.",
            "[총무팀] 출장 신청서가 접수되었습니다.",
            "[인사팀] 재택근무 신청 결과가 승인되었습니다.",
        ],
        "PAYROLL": [
            "[급여] {date} 급여명세서가 등록되었습니다.",
            "[인사팀] 원천징수 영수증 발급 신청이 완료되었습니다.",
            "[급여] 계좌 변경 신청이 접수되었습니다.",
            "[재무팀] 경비 지급 예정일은 {next_date}입니다.",
        ],
        "IT_MAINTENANCE": [
            "[IT 지원팀] 사내 VPN 점검이 예정되어 있습니다. 작업 시간에는 접속이 불안정할 수 있습니다.",
            "[IT지원팀] PC 보안 프로그램 업데이트를 오늘 퇴근 전 진행해 주세요.",
            "[IT 공지] {tool} 점검으로 {time_slot}부터 일부 기능이 제한됩니다.",
            "[IT 지원팀] 비밀번호 변경 주기가 되었습니다.",
        ],
        "SECURITY_NOTICE": [
            "[보안] 외부 메일의 첨부파일을 열 때 주의해 주세요.",
            "[보안팀] 의심스러운 메일 신고 훈련이 진행됩니다.",
            "[보안] 사내망 접속 기록 점검 예정입니다.",
            "[보안팀] 개인정보 파일 암호화 여부를 확인해 주세요.",
        ],
        "APPROVAL": [
            "{employee} {rank}님, {doc} 결재를 요청했습니다. 확인해 주세요.",
            "[전자결재] 신규 결재 문서가 도착했습니다. 제목: {project}",
            "[{tool}] 결재 반려 문서가 있습니다. 수정 후 다시 상신해 주세요.",
            "[전자결재] 승인 대기 문서가 {share_count}건 있습니다.",
        ],
        "EXPENSE": [
            "[재무팀] 법인카드 영수증 제출 기한은 {deadline}입니다.",
            "{employee}님, {amount} 경비 정산 내역을 확인해 주세요.",
            "[재무팀] 세금계산서 발행 요청이 접수되었습니다.",
            "[경비 정산] 증빙이 누락된 건이 있습니다. 보완해 주세요.",
        ],
        "PROJECT_UPDATE": [
            "{project} 일정표 최신본을 공유했습니다. 변경 사항을 확인해 주세요.",
            "클라이언트 피드백 반영본을 메일로 전달했습니다.",
            "이번 주 업무 진행률을 업데이트해 주세요. 누락 항목은 오늘 안에 정리해 주세요.",
            "[{tool}] {project} 티켓 상태가 변경되었습니다.",
        ],
        "CLIENT_MEETING": [
            "{client} 미팅 시간이 {time_slot}로 확정되었습니다.",
            "{client} 전달용 제안서 최종본을 확인해 주세요.",
            "{manager}님, {client} 회의록을 공유합니다.",
            "[영업팀] 고객사 방문 일정이 {next_date}로 변경되었습니다.",
        ],
        "DOCUMENT_SHARE": [
            "{doc} 파일을 {tool}에 공유했습니다. 권한을 확인해 주세요.",
            "공유 드라이브에 최신 {doc}을 업로드했습니다.",
            "[{tool}] {employee}님이 문서를 공유했습니다.",
            "{doc} 수정본을 확인한 후 의견을 남겨 주세요.",
        ],
        "CONTRACT_REVIEW": [
            "[법무팀] {client} 계약서 검토 의견을 전달합니다.",
            "계약서 검토본 반영했습니다. 법무팀 확인 후 재상신하겠습니다.",
            "[법무팀] 날인본을 수령한 후 스캔본을 업로드해 주세요.",
            "{client} 계약 일정이 변경되었습니다. 담당자에게 확인해 주세요.",
        ],
        "URGENT_WORK_SCAM": [
            "{header}대표님 지시사항입니다. 긴급 송금 승인이 필요하니 보안 문서를 확인해 주세요: {url}",
            "{header}급여명세서 오류 정정 안내입니다. 본인 확인 후 재발급: {url}",
            "[사내 공지] 임직원 개인정보 업데이트 요청입니다. 미제출 시 시스템 이용이 제한될 수 있습니다: {url}",
            "{header}{manager}님의 요청입니다. 외부 공유 문서를 확인한 후 회신해 주세요: {url}",
        ],
        "HR_SCAM": [
            "{header}[인사팀] 퇴직연금 정보 변경 요청이 있습니다. 본인 확인: {url}",
            "[급여] 계좌 오류로 급여 지급이 보류되었습니다. 계좌를 다시 확인해 주세요: {url}",
            "{header}[복리후생] 임직원 지원금 신청 대상 여부를 확인해 주세요: {url}",
            "[사내 복지] 미사용 포인트가 곧 소멸됩니다. 신청서를 확인해 주세요: {url}",
        ],
        "FACILITY_NOTICE": [
            "[총무팀] {office_notice} 관련 안내가 등록되었습니다. 내용을 확인해 주세요.",
            "[총무팀] {meeting_room} 사용 가능 시간이 변경되었습니다.",
            "[사내안내] 냉난방 점검으로 일부 구역 사용이 제한됩니다.",
            "[시설 공지] 출입 시스템 점검은 {next_date} {time_slot}에 진행될 예정입니다.",
        ],
        "ASSET_RETURN": [
            "[총무팀] 퇴실 전 {asset} 반납 여부를 확인해 주세요.",
            "[자산관리] 대여 중인 {asset} 반납 예정일은 {next_date}입니다.",
            "[IT 지원팀] 교체 대상 장비는 {asset}입니다. 회수 일정은 추후 안내해 드립니다.",
            "[자산관리] 반납 확인 후 인수증이 발급됩니다.",
        ],
        "TEAM_EVENT": [
            "[{dept}] 팀 점심 일정이 {next_date} {time_slot}로 확정되었습니다.",
            "[{dept}] 워크숍 참석 여부를 {deadline}까지 회신해 주세요.",
            "[사내행사] 분기 타운홀 미팅 장소는 {meeting_room}입니다.",
            "[{dept}] 송년회 참석 인원을 확인하고 있습니다. 참석 가능 여부만 답장해 주세요.",
        ],
    },
}


EXPANDED_SUBCATEGORY_POOLS = {
    category_idx: list(subcats.keys())
    for category_idx, subcats in EXPANDED_SCENARIO_TEMPLATES.items()
}
_expanded_subcat_cursor = {cat: 0 for cat in EXPANDED_SUBCATEGORY_POOLS}


def pick_expanded_subcategory(category_idx):
    pool = EXPANDED_SUBCATEGORY_POOLS[category_idx]
    cursor = _expanded_subcat_cursor[category_idx]
    _expanded_subcat_cursor[category_idx] += 1
    return pool[cursor % len(pool)]


def render_expanded_template(category_idx, sub_cat, generated_at=None):
    url_keywords = {
        0: "family",
        1: "finance",
        2: "delivery",
        3: "gov",
        4: "event",
        5: "auth",
        6: "work",
    }
    url = fake_url(url_keywords.get(category_idx, "notice"))
    values = expanded_values(url, generated_at)
    template = random.choice(EXPANDED_SCENARIO_TEMPLATES[category_idx][sub_cat])
    text = template.format(**values)
    text = apply_expanded_noise(text, category_idx)
    return text, url if url in text else "N/A", sub_cat


def generate_dynamic_text(category_idx, generated_at=None):
    if category_idx not in EXPANDED_SCENARIO_TEMPLATES:
        raise ValueError(f"지원하지 않는 카테고리 번호입니다: {category_idx}")
    sub_cat = pick_expanded_subcategory(category_idx)
    return render_expanded_template(category_idx, sub_cat, generated_at)


def build_category_indices(total_count):
    """카테고리별 개수를 균등하게 배분한 뒤 순서를 섞는다."""
    if total_count <= 0:
        raise ValueError("생성할 데이터 개수는 1개 이상이어야 합니다.")

    num_categories = len(CATEGORIES)
    samples_per_category, remainder = divmod(total_count, num_categories)
    indices = [
        category_idx
        for category_idx in CATEGORIES
        for _ in range(samples_per_category)
    ]
    indices.extend(range(remainder))
    random.shuffle(indices)
    return indices


def load_assets():
    """배경과 폰트를 한 번만 읽어 생성 루프에서 재사용한다."""
    font_paths = tuple(sorted(FONT_DIR.glob("*.ttf")))
    if not font_paths:
        raise FileNotFoundError("fonts 폴더에 .ttf 폰트 파일을 넣어주세요.")

    available_bgs = tuple(
        sorted(
            name
            for name in BG_CONFIGS
            if (BG_DIR / name).is_file()
        )
    )
    if not available_bgs:
        raise FileNotFoundError("backgrounds 폴더에 설정된 이미지가 없습니다.")

    backgrounds = {}
    for name in available_bgs:
        with Image.open(BG_DIR / name) as source:
            backgrounds[name] = source.convert("RGB")

    return font_paths, available_bgs, backgrounds


def get_cached_font(font_cache, font_path, size):
    cache_key = (font_path, size)
    if cache_key not in font_cache:
        font_cache[cache_key] = ImageFont.truetype(str(font_path), size)
    return font_cache[cache_key]


def render_image(text, target_url, bg_name, assets, font_cache):
    """문자 텍스트를 휴대폰 배경에 합성하고 QR을 추가한다."""
    font_paths, _, backgrounds = assets
    start_x, start_y, max_width = BG_CONFIGS[bg_name]

    img = backgrounds[bg_name].copy()
    draw = ImageDraw.Draw(img)

    font_size = random.randint(24, 31)
    font_path = random.choice(font_paths)
    font = get_cached_font(font_cache, font_path, font_size)
    line_spacing = font_size + random.randint(7, 11)

    lines = get_wrapped_text(text, font, max_width)
    y = start_y
    text_color = tuple(random.randint(10, 40) for _ in range(3))

    for line in lines:
        draw.text((start_x, y), line, fill=text_color, font=font)
        y += line_spacing

    qr_applied = target_url != "N/A" and random.random() < 0.4
    if qr_applied:
        safe_y = min(y + 20, img.height - 150)
        img.paste(create_qr_code(target_url), (start_x, safe_y))

    return img, qr_applied


def save_metadata(metadata, output_dir):
    column_order = [
        "file_name", "label_idx", "category",
        "sub_category", "has_qr", "url", "text",
    ]
    df = pd.DataFrame(metadata, columns=column_order)
    csv_path = output_dir / "metadata.csv"
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    return df, csv_path


def get_generation_time():
    """같은 시각을 사용해 한 번의 생성 작업 안에서 날짜/시간을 고정한다."""
    raw_value = os.getenv("GENERATED_AT", "").strip()
    if not raw_value:
        return datetime.now()

    try:
        return datetime.fromisoformat(raw_value)
    except ValueError as exc:
        raise ValueError(
            "GENERATED_AT은 ISO 형식이어야 합니다. 예: 2026-08-30T15:00:00"
        ) from exc


def main():
    total_count = int(os.getenv("TOTAL_COUNT", "10000"))
    seed = int(os.getenv("SEED", "42"))
    output_dir = Path(os.getenv("OUTPUT_DIR", str(DEFAULT_OUTPUT_DIR))).resolve()

    random.seed(seed)
    output_dir.mkdir(parents=True, exist_ok=True)
    assets = load_assets()
    _, available_bgs, _ = assets
    category_indices = build_category_indices(total_count)
    generated_at = get_generation_time()
    metadata = []
    font_cache = {}
    category_counters = {category_name: 0 for category_name in CATEGORIES.values()}

    print(f"총 {total_count}개의 데이터 생성을 시작합니다.")
    print(f"카테고리별 기본 개수: {total_count // len(CATEGORIES)}개")
    print(f"랜덤 시드: {seed}")
    print(f"기준 시각: {generated_at.isoformat(timespec='seconds')}")
    print("[OK] 데이터 순서 섞음 완료\n")

    for index, label_idx in enumerate(category_indices, start=1):
        text, target_url, sub_cat = generate_dynamic_text(label_idx, generated_at)
        bg_name = random.choice(available_bgs)
        img, qr_applied = render_image(
            text, target_url, bg_name, assets, font_cache
        )

        category_name = CATEGORIES[label_idx]
        category_counters[category_name] += 1
        file_name = f"{category_name}_{category_counters[category_name]:04d}.png"
        img.save(output_dir / file_name)

        metadata.append({
            "file_name": file_name,
            "label_idx": label_idx,
            "category": category_name,
            "sub_category": sub_cat,
            "has_qr": qr_applied,
            "url": target_url,
            "text": text.replace("\n", " "),
        })

        if index % 100 == 0 or index == total_count:
            print(f"{index}/{total_count} 생성 완료 ({index / total_count * 100:.1f}%)")

    df, csv_path = save_metadata(metadata, output_dir)

    print("\n[OK] 생성 완료!")
    print(f"[이미지] {output_dir} (총 {total_count}개)")
    print(f"[메타데이터] {csv_path}")
    print("[카테고리 분포]")
    for category, count in df["category"].value_counts().sort_index().items():
        print(f"   - {category}: {count}개")


if __name__ == "__main__":
    main()
