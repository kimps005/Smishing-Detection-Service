import os
import random
import qrcode
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, timedelta

# 데이터셋 생성에 사용하는 경로와 고정 리소스
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BG_DIR = os.path.join(BASE_DIR, "backgrounds")
FONT_DIR = os.path.join(BASE_DIR, "fonts")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

font_paths = [os.path.join(FONT_DIR, f) for f in os.listdir(FONT_DIR) if f.endswith('.ttf')]
if not font_paths:
    raise FileNotFoundError("fonts 폴더에 .ttf 폰트 파일을 넣어주세요.")

bg_configs = {"bg_Galaxy.png": (40, 50, 580), "bg_iPhone.png": (55, 45, 580), "bg_Kakao.png": (45, 40, 580)}

# 이전 생성기 블록에서 사용하는 레거시 헬퍼
def generate_malicious_url(brand_keyword=""):
    patterns = [
        f"http://{brand_keyword.lower()}-safe-{random.randint(10,99)}.cc",
        f"http://{random.randint(100,255)}.{random.randint(10,255)}.{random.randint(10,99)}.{random.randint(1,99)}/info",
        f"http://bit.ly/{random.choice(['app', 'update', 'chk'])}{random.randint(100,999)}.apk",
        f"http://vo.la/kr_{random.randint(1000,9999)}"
    ]
    return random.choice(patterns)

def apply_spam_noise(text):
    if random.random() < 0.5:
        idx = random.randint(0, len(text) - 1)
        noise_char = random.choice([" ", ".", "/", "_"])
        text = text[:idx+1] + noise_char + text[idx+1:]
    if "[Web발신]" in text and random.random() < 0.4:
        noise_web = random.choice(["[Web 발 신]", "(Web발신)", "[웹발신]", "[W.e.b발신]"])
        text = text.replace("[Web발신]", noise_web)
    if random.random() < 0.3:
        text += random.choice([" .", " -", " _", " ..", " /"])
    return text

CATEGORIES = {
    0: "PERSONAL",
    1: "FINANCE",
    2: "DELIVERY",
    3: "GOVERNMENT",
    4: "PROMOTION",
    5: "AUTH",
    6: "WORK",
}


# 확장 엔진 아래에 남겨둔 레거시 카테고리 생성기
def _gen_personal():
    now = datetime.now()
    date_short = now.strftime('%m/%d')
    amt = f"{random.randint(5, 500) * 10000:,}원"
    url = generate_malicious_url("scam")

    def get_random_header(prob=0.5, type="web"):
        if random.random() > prob: return ""
        if type == "web": return random.choice(["[Web발신]\n", "[국제발신]\n", ""])
        return ""

    family = ['엄마', '아빠', '형', '누나', '오빠', '언니', '할머니', '할아버지']
    friends = ['민수', '지수', '지연', '현우', '성민', '다은', '준호', '서윤', '철수', '영희',
              '승호', '지영', '태희', '소영', '동준', '혜진', '석준', '예진', '정우', '유진',
              '준영', '경준', '소현', '승우', '민정', '희진', '휘진', '호민', '진아', '수진',
              '대권', '기준', '준철', '재훈', '준석', '지훈', '병훈', '상윤', '준범', '영길']
    places = ['강남역 11번 출구', '학교 앞 스타벅스', '중앙도서관 3층', '우리 집 앞 편의점', '코엑스 몰', '홍대 입구']
    activities = ['영화 보기로 한 거', '전공 과제', '캡스톤 회의', '점심 식사', '운동', '스터디 모임']
    times = ['오늘 저녁 7시', '이번 주말', '내일 수업 끝나고', '다다음주 월요일', '이따가 밤에']
    items = ['선물', '기프티콘', '교안 복사본', '우산', '충전기', '노트북']
    food = ['치킨', '삼겹살', '마라탕', '떡볶이', '파스타', '국밥', '돈까스', '커피', '초밥']

    sub_cat = random.choice(["DAILY", "OBITUARY", "WEDDING", "FAMILY_SCAM"])

    if sub_cat == "DAILY":
        personal_templates = [
            f"{random.choice(family)}, 저 오늘 {random.choice(activities)} 때문에 좀 늦을 것 같아요. 저녁 먼저 드세요!",
            f"{random.choice(family)}! 아까 말한 {random.choice(items)} 식탁 위에 올려놨으니까 확인해 보세요.",
            f"방금 {random.choice(family)} 계좌로 용돈 보냈어요. 확인해보시고 맛있는 거 사 드세요!",
            f"{random.choice(family)}, 비 온다는데 우산 챙기셨어요? 나갈 때 옷 따뜻하게 입으세요.",
            f"{random.choice(family)}, 요즘 미세먼지 심한데 나갈 때 마스크 꼭 쓰고 나가세요!",
            f"오늘 일기예보 보니까 밤에 기온 뚝 떨어진대요. {random.choice(family)} 퇴근할 때 춥지 않게 조심하세요.",
            f"{random.choice(family)}! 아까 택배 온 거 제가 거실 안쪽에 들여놨어요. 이따 확인해 보세요.",
            f"{random.choice(family)}, 아까 거실 보니까 핸드폰 충전기 꽂혀 있던데 제가 방에 가져다 둘까요?",
            f"집에 오는 길에 {random.choice(food)} 좀 사 갈까요? {random.choice(family)} 드시고 싶은 거 있으면 말해주세요!",
            f"{random.choice(family)}! 아까 택배 온 거 제가 거실 안쪽에 들여놨어요. 이따 확인해 보세요.",
            f"{random.choice(family)}! 지금 어디에 있어요?",
            f"{random.choice(friends)}야, {random.choice(times)}에 {random.choice(places)}에서 {random.choice(activities)} 하는 거 맞지?",
            f"미안! 지하철이 연체돼서 {random.choice(places)}까지 한 15분 정도 늦을 것 같아. 먼저 들어가 있어!",
            f"{random.choice(times)}에 시간 돼? 오랜만에 애들이랑 {random.choice(places)}에서 얼굴 좀 보자.",
            f"{random.choice(friends)}님, {random.choice(activities)} 관련해서 물어볼 게 있는데 {random.choice(times)}에 통화 가능해?",
            f"나 지금 {random.choice(places)}인데 너 어디야? {random.choice(activities)} 같이 하자 ㅋㅋㅋ",
            f"야, 이번 {random.choice(activities)} 제출 기한 {random.choice(times)}까지로 연장됐대! 대박이지.",
            f"방금 {random.choice(activities)} 자료 단톡방에 올렸어. {random.choice(friends)} 너만 확인하면 될 듯!",
            f"수업 끝나고 {random.choice(places)}에서 밥 먹을 사람? 오늘 메뉴 {random.choice(food)}인데 고?",
            f"{random.choice(friends)}야, 이번 {random.choice(activities)} 진짜 어려운데 너는 어떻게 했어? 나 좀 도와줘 ㅠㅠ",
            f"아까 {random.choice(activities)} 비용 N빵 해서 {amt}원 보냈어! 확인해봐~",
            f"{random.choice(friends)}야, 저번에 빌린 {amt}원 지금 입금했어. 깜빡해서 미안해!",
            f"모임 회비 안 낸 사람 나한테 말해줘. {random.choice(times)}까지 입금 부탁해!",
            f"생일 축하해 {random.choice(friends)}야! {random.choice(items)} 카톡으로 보냈으니까 이따가 꼭 확인해봐.",
            f"벌써 종강이네! 이번 학기 고생 많았고 {random.choice(times)}에 다 같이 파티 한 번 하자.",
            f"합격 축하해! 드디어 고생한 보람이 있네 ㅠㅠ 이따가 {random.choice(places)}에서 내가 쏠게!",
            f"나 배터리가 없어서 곧 꺼질 것 같아. 도착하면 {random.choice(family)}한테 전화할게!",
            f"방금 집에 잘 도착했어. {random.choice(friends)} 너도 조심히 들어가고 내일 보자.",
            f"야 너 괜찮아? 아까 보니까 표정 안 좋던데 무슨 일 있는 건 아니지?",
            f"너 오늘 무슨 일 있냐?",
            f"{random.choice(friends)}야, 미안한데 나 지금 {random.choice(places)}인데 {random.choice(items)} 좀 가져다줄 수 있어?",
            f"혹시 {random.choice(activities)} 교안 찍어서 보내줄 수 있는 사람? 나 오늘 몸이 안 좋아서 못 갔어 ㅠㅠ",
        ]
        text = random.choice(personal_templates)
        return text.strip(), "N/A", sub_cat

    elif sub_cat == "OBITUARY":
        relation = random.choice(["부친", "모친", "조부", "조모", "빙부", "빙모"])
        loc = random.choice(["서울아산병원", "삼성서울병원", "연세세브란스", "강남성모병원", "시화병원"])
        target_url = url
        text = random.choice([
            f"[부고] 저희 {relation}께서 별세하셨기에 삼가 알려드립니다. 장례식장: {loc}\n오시는 길 및 부의금 전달 안내: {url}",
            f"{get_random_header()}[부고] 저희 {relation}상에 베풀어 주신 위로에 감사드립니다. 고인의 마지막 가시는 길, 모바일 부고장에서 확인 바랍니다: {url}",
            f"[부고] {relation}님께서 금일 별세하셨습니다. 장지 안내 및 모바일 부고장 확인 후 조문 부탁드립니다: {url}",
            f"{get_random_header()}[알림] {random.choice(['박*호', '이*준', '김*수'])}님의 {relation} 별세. 장례식장 정보가 변경되었습니다. 최종 장소 확인: {url}",
        ])
        text = apply_spam_noise(text)
        return text.strip(), target_url, sub_cat

    elif sub_cat == "WEDDING":
        name1 = random.choice(["민준", "도윤", "서준", "예준", "시우", "하준", "주원", "지호", "준서", "건우"])
        name2 = random.choice(["서연", "서윤", "지우", "하윤", "지유", "수아", "하은", "지은", "예은", "유진"])
        target_url = url
        text = random.choice([
            f"[모바일청첩장] 저희 결혼합니다! 한 분 한 분 직접 찾아뵙지 못해 모바일 청첩장으로 대신합니다! 링크 확인 부탁드립니다!: {url}",
            f"{get_random_header()}저희 두 사람, 긴 기다림 끝에 하나가 됩니다. 바쁘시더라도 꼭 오셔서 축복해주세요. 청첩장 보기: {url}",
            f"[초대장] {name1} & {name2}의 소중한 날에 초대합니다. 모바일 청첩장을 클릭하여 식장 위치를 확인하세요: {url}",
            f"{get_random_header()}결혼식 사진이 업데이트되었습니다! 저희 행복한 모습 미리 구경 오세요. 사진보기: {url}",
            f"[돌잔치] 저희 아이의 첫 번째 생일 파티에 초대합니다! 모바일 초대장 확인 후 참석 여부 체크 부탁드려요: {url}",
        ])
        text = apply_spam_noise(text)
        return text.strip(), target_url, sub_cat

    elif sub_cat == "FAMILY_SCAM":
        person = random.choice(["엄마", "아빠", "할머니", "할아버지"])
        target_url = url
        text = random.choice([
            f"{person} 나 폰 액정 깨져서 수리 맡겼어 ㅠㅠ 지금 컴퓨터로 문자 보내는 중인데 확인하면 링크 클릭해서 톡 줘! {url}",
            f"{get_random_header()}{person}! 나 지금 급하게 편의점 기프트카드 사야 하는데 폰이 안 돼서 그래.. 아래 링크로 들어와서 대신 좀 사줘: {url}",
            f"{person} 나 지금 휴대폰 본인인증이 안 돼서 결제를 못 하고 있어. 이 링크 눌러서 대신 인증 좀 해주면 안 돼? 급해! {url}",
            f"[{person}님] 자녀분이 교통사고로 병원에 이송되었습니다. 수술 동의 및 병원비 입금 안내 확인: {url}",
            f"{get_random_header()}{person} 나 지금 임시폰이야! 카톡 아이디 새로 만들었으니까 이 링크로 친구추가 해줘. 물어볼 거 있어: {url}",
        ])
        text = apply_spam_noise(text)
        return text.strip(), target_url, sub_cat


def _gen_finance():
    now = datetime.now()
    date_str = now.strftime('%Y-%m-%d')
    date_short = now.strftime('%m/%d')
    time_str = now.strftime('%H:%M')
    url = generate_malicious_url("scam")

    def get_random_header(prob=0.5, type="web"):
        if random.random() > prob: return ""
        if type == "web": return random.choice(["[Web발신]\n", "[국제발신]\n", ""])
        elif type == "ad": return random.choice(["(광고) ", ""])
        return ""

    banks = ['KB국민은행', '신한은행', '우리은행', 'NH농협', 'IBK기업', '카카오뱅크', '토스뱅크', '하나은행']
    cards = ['삼성카드', '현대카드', '롯데카드', '신한카드', '국민카드', '비씨카드']
    portals = ['네이버페이', '카카오페이', '다날', 'Apple', 'Amazon', '해외직구']
    agencies = ['국세청', '정부24', '서민금융진흥원', '소상공인시장진흥공단', '기획재정부', '금융감독원']
    amounts = [f'{random.randint(1, 100) * 50000:,}' for _ in range(6)]
    items_fin = ['아이패드 프로', '해외결제 승인', '구글 기프트카드', '원격지원 앱', '보안 승급']
    fake_url = random.choice(['http://bit.ly/auth-kr', 'http://kb-safe.xyz', 'http://v-gov.net', 'http://sh-card.top', 'http://cj-v.link'])

    sub_cat = random.choice(["NORMAL_BANK", "NORMAL_CARD", "NORMAL_INVEST", "NORMAL_PAY",
                              "SCAM_PAYMENT", "SCAM_LOAN", "SCAM_INVEST"])

    if sub_cat == "NORMAL_BANK":
        brand = random.choice(banks)
        amt_val = random.randint(1, 200) * 10000
        balance = random.randint(50, 5000) * 10000
        acc_num = f"{random.randint(100, 999)}-{random.randint(10, 99)}-****"
        scenarios = [
            f"[{brand}] 입금알림\n{amt_val:,}원\n{date_short} {time_str}\n잔액: {balance:,}원\n보낸이: {random.choice(['홍*동', '주식회사대박', '쿠팡(주)', '근로복지공단'])}",
            f"[{brand}] 출금알림\n{amt_val:,}원\n{date_short} {time_str}\n잔액: {balance:,}원\n받는이: {random.choice(['임대료', '보험료납부', '관리비', '체크카드결제'])}",
            f"[{brand}] 대출이자 출금안내\n금액: {random.randint(5, 50)*10000:,}원\n출금계좌: {acc_num}\n잔액부족 시 연체료가 발생할 수 있습니다.",
            f"[{brand}] 오픈뱅킹 등록 안내\n타행 계좌 {random.randint(1, 3)}건이 성공적으로 연결되었습니다. 이제 {brand} 앱에서 한 번에 관리하세요.",
        ]
        text = random.choice(scenarios)
        return text.strip(), "N/A", sub_cat

    elif sub_cat == "NORMAL_CARD":
        brand = random.choice(cards)
        amt_val = random.randint(1, 200) * 10000
        store = random.choice(['쿠팡', '배달의민족', '스타벅스코리아', 'SK에너지', '네이버파이낸셜', 'G마켓'])
        scenarios = [
            f"[{brand}] 승인안내\n{amt_val:,}원 {random.choice(['일시불', '2개월 할부'])}\n{date_short} {time_str}\n이용처: {store}\n누적: {random.randint(100, 500)*10000:,}원",
            f"[{brand}] 승인취소\n-{amt_val:,}원\n{date_short} {time_str}\n이용처: {store}\n정상 취소 처리되었습니다.",
            f"[{brand}] 해외승인 알림\n$ {random.randint(10, 500)}.{random.randint(10, 99)}\n{date_short} {time_str}\n이용처: {random.choice(['AMAZON.COM', 'APPLE.COM/BILL', 'PAYPAL', 'AGODA'])}",
            f"[{brand}] 카드 대금 명세서\n이번 달 결제 예정금액: {random.randint(50, 300)*10000:,}원\n결제일: {random.randint(1, 25)}일\n명세서는 앱에서 확인 가능합니다.",
        ]
        text = random.choice(scenarios)
        return text.strip(), "N/A", sub_cat

    elif sub_cat == "NORMAL_INVEST":
        brand = random.choice(["미래에셋증권", "키움증권"])
        stock = random.choice(['삼성전자', 'SK하이닉스', '애플', '엔비디아', '테슬라'])
        acc_num = f"{random.randint(100, 999)}-{random.randint(10, 99)}-****"
        scenarios = [
            f"[{brand}] 주식 체결 안내\n{stock}\n{random.randint(1, 50)}주 매수 완료\n체결가: {random.randint(50, 1000)*1000:,}원",
            f"[{brand}] 배당금 입금\n종목: {stock}\n세후 입금액: {random.randint(1, 10)*10000:,}원\n계좌: {acc_num}",
        ]
        text = random.choice(scenarios)
        return text.strip(), "N/A", sub_cat

    elif sub_cat == "NORMAL_PAY":
        amt_val = random.randint(1, 200) * 10000
        scenarios = [
            f"[카카오페이] 결제 완료\n{amt_val:,}원\n{date_short} {time_str}\n포인트 {random.randint(10, 1000)}원 적립 예정",
            f"[토스] 송금 완료\n{random.choice(['김*철', '이*희'])}님께 {amt_val:,}원을 보냈습니다.\n즐거운 하루 되세요!",
        ]
        text = random.choice(scenarios)
        return text.strip(), "N/A", sub_cat

    elif sub_cat == "SCAM_PAYMENT":
        payment_templates = [
            f"[Web발신][{random.choice(portals)}] {random.choice(amounts)}원 승인완료. 본인 아닐 시 즉시 소비자원 신고: {fake_url}",
            f"[{random.choice(cards)}] 고객님, 해외 IP에서 거액의 결제가 시도되었습니다. 본인 확인 필수: {fake_url}",
            f"[해외발송] Amazon 결제 승인 ${random.randint(400, 999)}.00. 주문 내역 확인 및 취소 요청: {fake_url}",
            f"[{random.choice(portals)}] 비정상적인 로그인이 감지되었습니다. 지금 즉시 원격 차단 및 보안 승급: {fake_url}",
            f"[{random.choice(cards)}] 03/27 결제예정금액 {random.choice(amounts)}원. 한도 초과 및 연체 방지를 위해 즉시 확인: {fake_url}",
            f"[{random.choice(banks)}] 타인 명의로 계좌 개설이 시도되었습니다. 본인 아닐 시 즉시 중지: {fake_url}",
            f"[다날] {random.choice(amounts)}원 휴대폰 결제 완료. 콘텐츠 이용료 바로 확인: {fake_url}",
            f"[Apple] 귀하의 계정이 새로운 기기에서 로그인되었습니다. 본인이 아니면 암호 즉시 재설정: {fake_url}",
            f"[{random.choice(cards)}] 카드 발급 신청이 접수되었습니다. 본인 미신청 시 즉시 차단: {fake_url}",
            f"[Web발신] 주문하신 상품 {random.choice(items_fin)} 배송 예정. 즉시 확인 바랍니다.: {fake_url}",
            f"[{random.choice(banks)}] 보안카드 3회 오류로 인해 인터넷 뱅킹이 정지되었습니다. 즉시 해제 요청: {fake_url}",
            f"[{random.choice(banks)}] 비정상적인 IP에서 로그인이 감지되어 이체가 제한됩니다. 지금 즉시 확인 및 보안 설정 요망: {fake_url}",
        ]
        text = apply_spam_noise(random.choice(payment_templates))
        return text.strip(), fake_url, sub_cat

    elif sub_cat == "SCAM_LOAN":
        loan_templates = [
            f"(광고)[{random.choice(banks)}] 정부지원 대환대출 안내. 연 2.1%~ 고정금리, 최대 1억 한도 확정, 금일 마감: {fake_url}",
            f"[{random.choice(agencies)}] 2026년 소상공인 특별 손실보상금 신청 대상자입니다. 오늘 마감: {fake_url}",
            f"[민생지원] 귀하는 긴급 생활안정자금 {random.choice(amounts)}원 지급 대상입니다. 즉시 수령: {fake_url}",
            f"[{random.choice(banks)}] 비대면 특례보증 대출 승인 완료. 서류 없이 즉시 입금 가능: {fake_url}",
            f"(광고)[기획재정부] 근로장려금 및 자녀장려금 미신청 건 발생. 지금 바로 신청하세요: {fake_url}",
            f"[서민금융] 저금리 전환대출 혜택 안내. 기존 고금리 채무를 {random.choice(banks)} 저금리로 대환 (지금 즉시 확인): {fake_url}",
            f"[{random.choice(banks)}] 고객님, 장기 미사용 계좌 포인트가 {random.choice(amounts)}원 있습니다. 지금 바로 현금 전환: {fake_url}",
            f"[정책자금] 고용유지 지원금 신청 안내. 법인/개인 사업자 대상 특별 우대 (지금 즉시 확인하세요): {fake_url}",
            f"(광고)[{random.choice(banks)}] 마이너스 통장 한도 증액 이벤트. 비대면 간편 신청(오늘 마감): {fake_url}",
            f"[{random.choice(agencies)}] 국민건강보험 환급금 {random.choice(amounts)}원 미수령 상태입니다. 즉시 환급: {fake_url}",
        ]
        text = apply_spam_noise(random.choice(loan_templates))
        return text.strip(), fake_url, sub_cat

    elif sub_cat == "SCAM_INVEST":
        invest_templates = [
            f"[Web발신][VIP투자] 내일 상한가 확정 종목 무료 공개. 신속히 정보 확인: {fake_url}",
            f"(광고)[수익인증] 주식투자 300% 수익 달성! 비법 공유방 입장하기 (금일 마감): {fake_url}",
            f"[{random.choice(banks)}] 연계 증권사 계좌 개설 이벤트. 가상화폐 선착순 증정: {fake_url}",
            f"[해외선물] 소액으로 시작하는 고수익 재테크. 전문가 실시간 리딩 참여 바로 가기: {fake_url}",
            f"(광고)공모주 {random.choice(items_fin)} 관련 사전 청약 안내. 100% 당첨 보장 (지금 즉시 확인): {fake_url}",
            f"[금금융] 금 시세 급등 대비 자산 배분 전략 보고서 배포. 선착순 50명 (지금 바로 확인): {fake_url}",
            f"[{random.choice(portals)}] 선착순 가상자산 에어드랍 이벤트. {random.choice(amounts)}원 상당의 코인 지급: {fake_url}",
            f"[VIP정보] 대기업 M&A 내부 정보 유출. 단기 폭등주 지금 바로 확인하기: {fake_url}",
            f"(광고)부동산 소액 투자로 월 200만원 수익 가능. 사업 설명회 초대장: {fake_url}",
            f"[{random.choice(banks)}] 비상장 주식 상장 확정 안내. 사전 매수 기회 확인: {fake_url}",
        ]
        text = apply_spam_noise(random.choice(invest_templates))
        return text.strip(), fake_url, sub_cat


def _gen_delivery():
    now = datetime.now()
    date_short = now.strftime('%m/%d')
    time_str = now.strftime('%H:%M')
    url = generate_malicious_url("scam")

    def get_random_header(prob=0.5, type="web"):
        if random.random() > prob: return ""
        if type == "web": return random.choice(["[Web발신]\n", "[국제발신]\n", ""])
        return ""

    logistic_brands = ["CJ대한통운", "우체국택배", "로젠택배", "한진택배", "롯데택배"]
    customs_brands = ["관세청", "통관지원센터", "인천공항세관", "해외배송팀"]
    platform_brands = ["CU편의점택배", "GS25포스트박스", "세븐일레븐택배"]
    fresh_brands = ["쿠팡프레시", "마켓컬리", "오아시스마켓"]

    sub_cat = random.choice(["NORMAL_SHOP", "SCAM_LOGISTIC", "SCAM_CUSTOMS", "SCAM_PLATFORM", "SCAM_FRESH"])

    if sub_cat == "NORMAL_SHOP":
        brand = random.choice(["쿠팡", "11번가", "무신사"])
        order_no = f"{random.randint(100000000, 999999999)}"
        amount = f'{random.randint(1, 100) * 50000:,}'
        scenarios = [
            f"[{brand}] 주문하신 상품이 출고되었습니다.\n송장번호: {random.randint(1000,9999)}-{random.randint(1000,9999)}\n배송조회: https://m.{brand.lower()}.com",
            f"[{brand}] 배송완료 안내\n고객님의 소중한 상품이 '문 앞'에 배송되었습니다.\n https://{brand.lower()}.com/order/status",
            f"[{brand}] 반품 접수가 완료되었습니다. 영업일 1~3일 내 기사님이 방문하실 예정입니다."
            f"[{brand}] 결제완료 안내\n주문번호: {order_no}\n금액: {amount}원\n상품명 외 1건\n상세보기: https://{brand.lower()}.com/my/order",
            f"[{brand}] 죄송합니다. 주문하신 상품이 주문 폭주로 인해 품절되었습니다. 결제하신 {amount}원은 자동 환불 처리됩니다. 양해 부탁드립니다.",
            f"[{brand}] 상품 출고 안내\n송장번호: {random.choice(['CJ','한진','롯데'])}{random.randint(1000000000, 9999999999)}\n기분 좋은 만남이 되도록 안전하게 배송하겠습니다.",
            f"[{brand}] 배송완료\n택배함(또는 경비실)에 물품을 보관하였습니다. 소중한 상품을 확인해주세요.\n구매확정: https://{brand.lower()}.com/confirm",
            f"[{brand}] 상품은 만족스러우신가요?\n지금 리뷰를 작성하시면 최대 5,000포인트를 드립니다! 다른 구매자에게도 큰 도움이 됩니다.",
            f"[{brand}] 반품 수거 예정 안내\n오늘 오후 기사님이 방문하실 예정입니다. 상품을 문 앞에 내놓아 주시기 바랍니다. (운송장:{random.randint(1000,9999)})",
            f"[{brand}] 정기결제 완료\n와우/유니버스 멤버십 이용료 {random.choice(['4,990', '9,900'])}원이 결제되었습니다. 이번 달 혜택을 확인해보세요.",
            f"[{brand}] 선물이 도착했습니다!\n{random.choice(['김*수', '이*지'])}님이 보내신 선물을 확인해보세요! {date_short}까지 배송지 입력 요망",
            f"[{brand}] 기다리시던 '재입고' 소식!\n찜하신 상품이 드디어 입고되었습니다. https://{brand.lower()}.com/item/view",
            f"[{brand}] 배송 중 안내\n{random.choice(['CJ','한진','롯데','우체국'])}택배를 통해 배송 중입니다.\n현재 위치: {random.choice(['분류센터', '배송센터', '출발지'])}\n송장번호: {random.randint(1000000000, 9999999999)}",
            f"[{brand}] 배송 예정일 변경\n예정일이 {random.choice(['내일', '모레', '2일 뒤'])}로 변경되었습니다.\n상품을 기다리고 계시는 동안 기타 혜택을 확인해보세요.",
            f"[{brand}] 배송 지연 안내\n죄송합니다. 배송 물량 증가로 인해 배송이 {random.randint(1, 3)}일 정도 지연될 예정입니다.\n빠른 배송을 위해 노력하겠습니다.",
            f"[{brand}] 배송지 주소 변경 요청\n배송 전 주소를 변경하실 수 있습니다.\n변경 시간: {time_str}까지\n변경하기: https://m.{brand.lower()}.com/order/change-address",
            f"[{brand}] 배송 수령 불가 안내\n고객님이 계신 장소에 도착했으나 수령이 불가하여 반환될 예정입니다.\n다시 배송받으시려면 고객센터(1644-1234)로 연락주세요.",
            f"[{brand}] 환불 처리 중\n반품/교환 상품을 회수 중입니다.\n환불은 상품 수령 후 영업일 기준 3~5일 내에 완료됩니다.",
            f"[{brand}] 환불완료 안내\n반품하신 상품이 확인되어 환불 처리가 완료되었습니다.\n환불액: {random.randint(10, 100)*10000:,}원\n계좌: 농협 ****-****-****",
            f"[{brand}] 교환상품 배송 시작\n새로운 상품이 출고되었습니다.\n송장번호: {random.randint(1000000000, 9999999999)}\n교환 배송일: {date_short}",
            f"[{brand}] 부분배송 안내\n주문하신 상품 중 일부({random.randint(1, 3)}개)가 먼저 배송됩니다.\n나머지 상품: {random.randint(1, 5)}일 후 배송 예정",
            f"[{brand}] 배송 수령 확인 요청\n배송이 완료된 후 {random.randint(1, 7)}일 이내에 수령 확인을 부탁드립니다.\n확인 기한: {date_short}\n미확인 시 자동 구매확정됩니다.",
            f"[{brand}] 배송 상태: 배송 준비 중\n곧 배송을 시작할 예정입니다.\n배송 시작: {date_short} 예정\n실시간 배송 추적: https://m.{brand.lower()}.com/tracking",
        ]
        text = random.choice(scenarios)
        return text.strip(), "N/A", sub_cat

    elif sub_cat == "SCAM_LOGISTIC":
        brand = random.choice(logistic_brands)
        target_url = url
        text = random.choice([
            f"{get_random_header()}[{brand}] 주소지 오류로 물품 배송이 중단되었습니다. 금일 내 수정되지 않으면 자동 반송됩니다. ■수정하기: {url}",
            f"[{brand}] 부재중으로 미수령된 등기 소포가 본인확인 미비로 폐기 예정입니다. 즉시 재배송 신청: {url}",
            f"{get_random_header()}[{brand}] 배송 중 수하물 파손으로 인한 보상금이 산정되었습니다. 아래 링크에서 계좌 등록하고 수령하세요. ■등록: {url}",
            f"[{brand}] 송장번호[{random.randint(1000,9999)}***] 물품이 인근 대리점에 장기 보관 중입니다. 보관료 발생 전 수령 위치 지정: {url}",
            f"{get_random_header()}[{brand}] 택배 분류 중 송장 오염으로 주소 식별 불가. 미확인 시 배송 불가합니다. ■주소재입력: {url}",
            f"[{brand}] 기사 사고로 인해 배송 지연 및 파손 확인이 필요합니다. 피해 물품 사진을 앱에서 확인하세요. ■앱설치: {url}",
            f"{get_random_header()}[{brand}] 물품 대리 수령 완료. 본인이 아닐 경우 타인 수령 및 도난 방지를 위해 즉시 위치 확인: {url}",
            f"[{brand}] 수하물 무게 초과로 인한 추가 결제가 필요합니다. 미결제 시 배송이 무기한 중단됩니다. ■결제하기: {url}",
        ])
        text = apply_spam_noise(text)
        return text.strip(), target_url, sub_cat

    elif sub_cat == "SCAM_CUSTOMS":
        brand = random.choice(customs_brands)
        target_url = url
        text = random.choice([
            f"{get_random_header()}[{brand}] 해외직구 물품 통관번호 불일치로 검사가 지연중입니다. 금일 마감 전 번호 재입력 필요. ■재입력: {url}",
            f"[{brand}] 수하물[{random.randint(100,999)}E] 관세 미납으로 반입 제한. 세액 납부 완료 후 통관 진행 가능합니다. ■세액납부: {url}",
            f"{get_random_header()}[{brand}] 해외 발송 물품이 검역 대상으로 분류되어 압류 예정입니다. 상세 사유 확인 및 소명 자료 제출: {url}",
            f"[{brand}] 해외직구 물품 과세가격 결정 통지서 발급. 전자고지서 확인 후 기한 내 미납 시 가산세 부과. ■고지서확인: {url}",
            f"{get_random_header()}[{brand}] 고객님의 직구 물품이 인천항에 도착했으나 수입 요건 미비로 통관 거부되었습니다. 재승인 절차 확인: {url}",
            f"[{brand}] 반입 금지 성분 포함 의심으로 수하물이 개장 검사 대기 중입니다. 검사 동의서에 서명하세요. ■서명하기: {url}"
            f"[{brand}] 해외 발송 수하물 내 금지 품목(의약품) 포함 의심. 미확인 시 폐기 및 과태료 부과 대상입니다. ■소명하기: {url}",
            f"{get_random_header()}[{brand}] 직구 물품 통관 완료. 배송료 미결제로 출고 보류 중입니다. 운임료 결제 후 수령: {url}",
            f"[{brand}] 해외 직구용 개인통관고유부호가 도용된 것으로 의심되어 사용 정지되었습니다. 본인확인 후 해제: {url}",
            f"{get_random_header()}[{brand}] 관세청 알림: 고객님 성함으로 고가의 물품이 입항되었습니다. 본인 주문이 아닐 경우 즉시 신고: {url}",
            f"[{brand}] 통관 지원금 환급 대상자로 선정되었습니다. 누적된 관세 포인트 64,000점 소멸 전 현금 전환: {url}",
        ])
        text = apply_spam_noise(text)
        return text.strip(), target_url, sub_cat

    elif sub_cat == "SCAM_PLATFORM":
        brand = random.choice(platform_brands)
        target_url = url
        text = random.choice([
            f"[{brand}] 예약하신 택배가 규격 초과로 접수 거부되었습니다. 환불을 위해 앱 설치 후 본인인증을 진행하세요. ■환불접수: {url}",
            f"{get_random_header()}[{brand}] 편의점 보관함(BOX)에 물품이 장기 방치되어 보안 경고가 발생했습니다. 즉시 인증번호 확인 후 수령: {url}",
            f"[{brand}] 점포 택배 수령 대기 중. {date_short}까지 미수령 시 본사 반송 및 추가 비용 청구됩니다. ■상세보기: {url}",
            f"{get_random_header()}[{brand}] 택배 예약 결제 오류로 접수가 자동 취소되었습니다. 환불 내역 확인 및 재결제: {url}",
            f"[{brand}] 편의점 택배 예약 시스템 점검으로 인해 기존 예약건이 초기화되었습니다. 재등록 및 쿠폰 받기: {url}",
            f"[{brand}] 제3의 기기에서 택배 예약 정보 조회가 감지되었습니다. 본인이 아닐 경우 즉시 차단: {url}",
            f"{get_random_header()}[{brand}] 편의점 보관함 비밀번호가 3회 오류로 잠금 처리되었습니다. 앱에서 잠금 해제 후 수령: {url}",
            f"[{brand}] 시스템 고도화에 따른 통합 회원 전환 안내. 미전환 시 기존 배송 데이터가 삭제됩니다. ■전환하기: {url}",
        ])
        text = apply_spam_noise(text)
        return text.strip(), target_url, sub_cat

    elif sub_cat == "SCAM_FRESH":
        brand = random.choice(fresh_brands)
        target_url = url
        text = random.choice([
            f"[{brand}] 새벽 배송지 오설정으로 타 가구에 오배송되었습니다. 분실 처리 전 즉시 배송지 정보를 수정하세요. ■수정: {url}",
            f"{get_random_header()}[{brand}] 고객님, 공동현관 비밀번호 불일치로 신선식품 배송 불가. 상품 부패 위험이 있으니 즉시 비번 입력: {url}",
            f"[{brand}] 주문 상품 품절로 인한 보상 쿠폰 3만원권이 발급되었습니다. 지금 즉시 등록하고 사용하세요. ■쿠폰등록: {url}",
            f"{get_random_header()}[{brand}] 프레시백 미반납 회수 지연 경고. {date_short}까지 미반납 시 지연 과태료가 자동 결제됩니다. ■장소지정: {url}",
            f"[{brand}] 결제 수단 정보 만료로 정기 결제가 실패했습니다. 멤버십 혜택 유지를 위해 지금 즉시 정보를 갱신하세요. ■정보갱신: {url}"
            f"[{brand}] 신선식품 배송 완료. 하절기 온도 상승으로 변질 우려가 있으니 즉시 수령 장소를 확인하세요: {url}",
            f"{get_random_header()}[{brand}] 프레시 멤버십 1년 구독권 당첨! 무료 체험 후 자동 결제 전 해지 가능합니다. ■신청하기: {url}",
            f"[{brand}] 주문하신 상품이 파손되어 환불 처리되었습니다. 환불 금액 계좌 입금 확인: {url}",
            f"{get_random_header()}[{brand}] 배송 기사 긴급 연락: 등록된 연락처가 연결되지 않아 배송이 중단되었습니다. 실시간 위치 확인: {url}",
        ])
        text = apply_spam_noise(text)
        return text.strip(), target_url, sub_cat


def _gen_government():
    now = datetime.now()
    date_str = now.strftime('%Y-%m-%d')
    time_str = now.strftime('%H:%M')
    url = generate_malicious_url("scam")

    def get_random_header(prob=0.5, type="web"):
        if random.random() > prob: return ""
        if type == "web": return random.choice(["[Web발신]\n", "[국제발신]\n", ""])
        return ""

    police_orgs = ["경찰청교통민원", "검찰청", "사이버수사대"]
    tax_orgs = ["국세청", "민원24", "정부24", "행정안전부"]
    health_orgs = ["국민건강보험", "질병관리청", "근로복지공단"]
    legal_orgs = ["대한법률구조공단", "지방법원", "병무청"]

    sub_cat = random.choice(["NORMAL_GOV", "SCAM_POLICE", "SCAM_TAX", "SCAM_HEALTH", "SCAM_LEGAL"])

    if sub_cat == "NORMAL_GOV":
        scenarios = [
            f"[민원24] 신청하신 서류 발급이 완료되었습니다. 홈페이지에서 출력 가능합니다.",
            f"[기상청] 금일 {random.randint(14, 20)}시부로 수도권 지역 한파주의보 발효. 건강관리에 유의하시기 바랍니다.",
            f"[대한적십자사] 헌혈에 참여해주셔서 감사합니다. 증서 번호: {random.randint(10, 99)}-{random.randint(10, 99)}-{random.randint(100000, 999999)}",
            f"[정부24] 간편인증 완료 안내\n이용업무: 민원신청/조회\n일시: {date_str} {time_str}",
            f"[국세청] 전자문서 도착 안내\n본인인증 후 내용을 확인하시기 바랍니다.\n확인하기: https://hometax.go.kr",
            f"[경찰청] 교통범칙금 281,000원 납부 안내. 이의신청: efine.go.kr",
        ]
        text = random.choice(scenarios)
        return text.strip(), "N/A", sub_cat

    elif sub_cat == "SCAM_POLICE":
        brand = random.choice(police_orgs)
        target_url = url
        text = random.choice([
            f"{get_random_header()}[{brand}] 교통법규 위반 과태료 고지서 발송. 미납 시 차량 압류 절차가 진행됩니다. 상세내역 확인 및 납부: {url}",
            f"[{brand}] 귀하께서는 [폐기물관리법] 위반 쓰레기 무단투기로 단속되었습니다. 현장 사진 및 위반 장소 확인: {url}",
            f"{get_random_header()}[{brand}] 사건번호 2026-고단{random.randint(1000,9999)} 관련 명예훼손 피고소인 출석요구서 발부. 미출석 시 불이익이 발생할 수 있습니다. 조회: {url}",
            f"[{brand}] 정보통신망법 위반(불법 촬영물 유포) 혐의로 조사 대상에 포함되었습니다. 관련 증거 자료 확인 및 소명: {url}",
            f"{get_random_header()}[{brand}] 긴급 연락. 보이스피싱 범죄에 귀하의 명의가 도용되었습니다. 계좌 보호를 위해 즉시 보안 앱을 설치하세요. ■앱설치: {url}",
            f"[법원] 귀하는 명의도용 사건의 피의자로 신고되었습니다. 불출석 시 구속영장 발부 예정. 진술서 확인: {url}",
            f"[검찰청] 귀하의 계좌가 범죄 자금 세탁에 연루되었습니다. 긴급 소명 절차 안내: {url}",
            f"[경찰청] 교통 위반 과태료 고지서가 발송되었습니다. 미납 시 가산금 부과: {url}",
            f"[법원] 민사 소송 피고 소환장 전달 안내. 전자 소송 사이트에서 확인: {url}",
        ])
        text = apply_spam_noise(text)
        return text.strip(), target_url, sub_cat

    elif sub_cat == "SCAM_TAX":
        brand = random.choice(tax_orgs)
        target_url = url
        text = random.choice([
            f"{get_random_header()}[{brand}] 2026년 상반기 종합소득세 누락분 환급 안내. 오늘까지 신청하지 않으면 국고로 귀속됩니다. ■즉시신청: {url}",
            f"[{brand}] 지방세 미납으로 인한 자산 압류 통지서가 전자 문서로 발송되었습니다. 압류 예정일 확인 및 소명: {url}",
            f"{get_random_header()}[{brand}] 근로장려금 지급 대상자 선정 안내. 본인인증 후 수령 계좌를 등록하십시오. 미등록 시 지급 제외. ■등록: {url}",
            f"[{brand}] 주민등록증 발급 및 갱신 미이행에 따른 과태료 부과 예정 통지서. 상세 내용 확인 후 이의신청 바랍니다: {url}",
            f"{get_random_header()}[{brand}] 연말정산 간소화 서비스 오류로 인한 추가 공제 환급금 발생. 본인확인 후 즉시 수령하세요: {url}",
            f"[국세청] 종부세 및 양도소득세 미납 고지서 발부. 체납 시 압류 예정. 즉시 확인하세요: {url}",
            f"[행정안전부] 정부지원 민생회복지원금 미수령 대상자입니다. 신청 확인: {url}",
        ])
        text = apply_spam_noise(text)
        return text.strip(), target_url, sub_cat

    elif sub_cat == "SCAM_HEALTH":
        brand = random.choice(health_orgs)
        target_url = url
        text = random.choice([
            f"{get_random_header()}[{brand}] 정기 건강검진 결과 암 의심 소견이 발견되었습니다. 정밀 검사 대상자 명단을 확인하십시오. ■결과조회: {url}",
            f"[{brand}] 2026년도 건강보험료 과오납금 환급금 신청 안내. 본인 확인 절차 후 즉시 입금됩니다. ■신청하기: {url}",
            f"{get_random_header()}[{brand}] 생활지원비 지급 대상자로 선정되셨습니다. 신청 기한이 얼마 남지 않았으니 서둘러 등록하세요. ■내용확인: {url}",
            f"[{brand}] 실업급여 수급 자격 인정 통지서 발급. 실업인정일 및 지급액 확인을 위해 보안 문서를 열람하세요: {url}",
            f"{get_random_header()}[{brand}] 산재보험 가입 증명서 발급 오류 안내. 미조치 시 급여 지급이 중단될 수 있습니다. ■확인: {url}",
            f"[{random.choice(health_orgs + ['금융감독원'])}] 건강검진 보고서 결과 미확인 건이 발생했습니다. 즉시 조회: {url}",
        ])
        text = apply_spam_noise(text)
        return text.strip(), target_url, sub_cat

    elif sub_cat == "SCAM_LEGAL":
        brand = random.choice(legal_orgs)
        target_url = url
        text = random.choice([
            f"{get_random_header()}[{brand}] 2026년도 병력판정검사 통지서 발송 완료. 기일 내 미확인 시 병역법 위반으로 고발 조치됩니다. ■상세: {url}",
            f"[{brand}] 민사 소송 관련 소장 부본이 송달되었습니다. 전자 소송 시스템을 통해 지금 즉시 내용을 확인하고 답변서를 제출하세요: {url}",
            f"{get_random_header()}[{brand}] 국민참여재판 배심원 후보 선정 안내. 선정 여부 확인 및 불출석 사유서 작성(미작성 시 불이익을 챔임지지 않습니다.): {url}",
            f"[{brand}] 채무 불이행에 따른 재산 명시 명령서 발부. 재산 목록 작성 및 제출 기일 지금 즉시 확인 바랍니다. ■조회: {url}",
            f"[병무청] 예비군/민방위 소집 통지 최종 통고. 미참석 시 고발 조치 및 벌금형에 처해질 수 있습니다: {url}",
        ])
        text = apply_spam_noise(text)
        return text.strip(), target_url, sub_cat


def _gen_promotion():
    now = datetime.now()
    date_short = now.strftime('%m/%d')

    ad_brands = {
        "스타벅스": ["신메뉴", "별 적립", "사이렌오더", "보고쿠폰"],
        "올리브영": ["오늘드림", "올영세일", "뷰티어워즈", "샘플링"],
        "무신사": ["래플", "브랜드데크", "코디맵", "적립금"],
        "CGV": ["VIP선정", "포토플레이", "팝콘할인", "시사회"],
        "다이소": ["멤버십", "신상탐험대", "재입고", "포인트"],
        "배달의민족": ["처음주문", "더귀한분", "배민클럽", "포장할인"],
        "야놀자": ["숙박쿠폰", "얼리버드", "무한대실", "포인트소멸"],
    }

    brand = random.choice(list(ad_brands.keys()))
    opt_out = f"080-{random.randint(100, 999)}-{random.randint(1000, 9999)}"

    scenarios = []
    if brand == "스타벅스":
        scenarios = [
            f"(광고) [{brand}]\nWinter 시즌 음료 출시! 사이렌 오더로 주문 시 별 3개 추가 적립 혜택을 드립니다.\n대상: {brand} 리워드 회원\n기간: ~{date_short}\n무료수신거부 {opt_out}",
            f"(광고) [{brand}]\n고객님께만 드리는 BOGO(1+1) 쿠폰이 도착했습니다. 지금 바로 앱에서 확인하고 시원한 여름을 즐기세요!\n무료수신거부 {opt_out}",
        ]
    elif brand == "올리브영":
        scenarios = [
            f"(광고) [{brand}]\n[올영세일] 최대 70% 할인 + 선착순 쿠폰 팩 증정.\n지금 가까운 매장이나 앱으로 만나보세요.\n무료수신거부 {opt_out}",
            f"(광고) [{brand}]\n고객님, 장바구니에 담아두신 상품이 세일 중입니다. 품절되기 전에 확인하세요!\n무료수신거부 {opt_out}",
        ]
    elif brand == "CGV":
        scenarios = [
            f"(광고) [{brand}]\n기다리던 기대작 '블록버스터' 개봉! 지금 예매하고 포토플레이 소장 기회를 놓치지 마세요.\n상영시간표: https://cgv.kr/search\n무료수신거부 {opt_out}",
            f"(광고) [{brand}]\n[생일축하] 고객님의 생일을 축하하며 매점 콤보 50% 할인권을 드립니다. 행복한 영화 관람 되세요!\n무료수신거부 {opt_out}",
        ]
    elif brand == "배달의민족":
        scenarios = [
            f"(광고) [{brand}]\n비오는 날엔 역시 파전? 지금 바로 쓸 수 있는 {random.randint(3, 5)}천원 쿠폰이 도착했습니다.\n배민클럽 회원이라면 배달팁 무제한 무료!\n무료수신거부 {opt_out}",
            f"(광고) [{brand}]\n고객님, '더귀한분' 등급 유지를 위해 주문 1회가 부족해요! 이 달의 혜택을 놓치지 마세요.\n무료수신거부 {opt_out}",
        ]
    elif brand == "야놀자":
        scenarios = [
            f"(광고) [{brand}]\n[여름휴가 얼리버드] 국내 숙소 최대 50,000원 할인권 발급!\n지금 예약하면 8월 휴가비가 절반으로!\n무료수신거부 {opt_out}",
            f"(광고) [{brand}]\n고객님의 포인트 {random.randint(1000, 5000)}P가 3일 뒤 소멸 예정입니다. 사라지기 전에 여행 계획 세워보세요!\n무료수신거부 {opt_out}",
        ]
    elif brand == "무신사":
        scenarios = [
            f"(광고) [{brand}]\n이번 시즌 핫한 신상 대방출! 래플 참여하고 한정판 아이템을 손에 넣으세요.\n무료수신거부 {opt_out}",
            f"(광고) [{brand}]\n고객님, 찜하신 상품이 품절 임박입니다. 지금 바로 확인하고 코디맵에서 스타일링 팁도 받아보세요!\n무료수신거부 {opt_out}"
            f"(광고) [{brand}]\n[브랜드데크]에서 좋아하는 브랜드의 최신 컬렉션을 만나보세요. 지금 가입하면 첫 구매에 사용 가능한 10% 할인 쿠폰을 드립니다!\n무료수신거부 {opt_out}"
            f"(광고) [{brand}]\n안녕하세요. 무신사 스토어입니다.\n회원님의 15%할인 쿠폰이 곧 소멸될 예정입니다."
            f"[상품 출고 안내]\n주문하신 상품이 발송되었습니다.\n배송 조회까지 평일 기준 1~2일 정도 소요될 수 있습니다.\n상품 수령까지 조금만 기다려주세요!",
        ]
    else:
        scenarios = [
            f"(광고) [{brand}]\n신규 컬렉션 런칭! 오직 {brand}에서만 만날 수 있는 단독 할인 혜택을 확인하세요.\n혜택: 전 상품 {random.randint(10, 20)}% 쿠폰 제공\n무료수신거부 {opt_out}",
            f"(광고) [{brand}]\n[품절임박] 고객님이 찜하신 상품의 재고가 얼마 남지 않았습니다. 서둘러 확인하세요!\n무료수신거부 {opt_out}"
            f"(광고)카카오페이\n롯데월드에 찾아온 메이플스토리\n최대 39%할인받고, 롯데월드로 놀러 가요",
        ]

    shop_promo = [
        f"(광고) [쿠팡] 장바구니에 담아둔 상품을 잊으셨나요? 지금 구매하시면 사용 가능한 {random.randint(5, 15)}% 할인 쿠폰이 있습니다. 무료수신거부: 080-000-0000",
        f"[네이버쇼핑] 관심상품 가격 인하 알림. 지금 구매하세요. shopping.naver.com",
    ]

    text = random.choice(scenarios + shop_promo)
    return text.strip(), "N/A", ""


def _gen_auth():
    now = datetime.now()
    date_str = now.strftime('%Y-%m-%d')
    time_str = now.strftime('%H:%M')
    auth_num = random.randint(100000, 999999)
    ip_addr = f"{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}"
    device = random.choice(['iPhone 15', 'Windows 10', 'MacBook Pro', 'Galaxy S24', 'Chrome 브라우저'])

    sub_cat = random.choice(["PORTAL", "KAKAO", "CRYPTO", "GOV_AUTH", "GAME", "MARKET"])

    if sub_cat == "PORTAL":
        brand = random.choice(["네이버", "구글", "인스타그램", "애플"])
        scenarios = [
            f"[{brand}] 새로운 기기에서 로그인이 감지되었습니다.\n일시: {date_str} {time_str}\n기기: {device}\n위치: 서울(KR)\n본인이 아니라면 즉시 비밀번호를 변경하세요.",
            f"[{brand}] 계정 복구 코드는 [{auth_num}]입니다. 코드를 공유하지 마세요.",
            f"[{brand}] 비밀번호가 성공적으로 변경되었습니다. 보안 유지를 위해 정기적인 변경을 권장합니다.",
            f"[{brand}] 인증번호 {auth_num}입니다. 타인에게 공유하지 마세요.",
        ]
        text = random.choice(scenarios)
        return text.strip(), "N/A", sub_cat

    elif sub_cat == "KAKAO":
        scenarios = [
            f"[카카오톡] 기기로그인 알림\n일시: {date_str} {time_str}\nPC버전 카카오톡에 로그인하였습니다.\n본인이 아니라면 [기기 연결 해제]를 클릭하세요.",
            f"[카카오톡] 인증번호 [{auth_num}]를 입력해 주세요. (타인 노출 금지)",
        ]
        text = random.choice(scenarios)
        return text.strip(), "N/A", sub_cat

    elif sub_cat == "CRYPTO":
        scenarios = [
            f"[Upbit] 출금 신청 안내\n신청금액: {random.randint(1, 100)/100:.4f} BTC\n주소: {random.choice(['bc1q...', '3J98t...'])}\n본인 요청이 아닐 경우 즉시 고객센터로 연락 바랍니다.",
            f"[Upbit] 회원가입을 위한 인증번호는 [{auth_num}]입니다.",
        ]
        text = random.choice(scenarios)
        return text.strip(), "N/A", sub_cat

    elif sub_cat == "GOV_AUTH":
        scenarios = [
            f"[국세청] 연말정산 간편제출 서비스 이용을 위해 인증번호 [{auth_num}]를 입력하세요.",
            f"[Web발신] 본인확인 인증번호 [{auth_num}]입니다. 요청하신 화면에 입력해 주세요.",
            f"[KB국민은행] OTP 인증번호: {auth_num}. 타인에게 절대 알려주지 마세요.",
        ]
        text = random.choice(scenarios)
        return text.strip(), "N/A", sub_cat

    elif sub_cat == "GAME":
        scenarios = [
            f"[NEXON] OTP 인증번호 [{random.randint(10000000, 99999999)}]를 입력해주세요.",
            f"[NEXON] 해외 IP 로그인 차단 알림\n차단된 IP: {ip_addr}\n비정상적인 접근이 시도되어 차단되었습니다.",
        ]
        text = random.choice(scenarios)
        return text.strip(), "N/A", sub_cat

    elif sub_cat == "MARKET":
        scenarios = [
            f"[당근] 당근마켓 인증번호 [{auth_num}]입니다.",
            f"[당근] 타지방 로그인 알림\n최근 접속 위치가 평소와 다릅니다: {random.choice(['부산', '광주', '제주'])}",
        ]
        text = random.choice(scenarios)
        return text.strip(), "N/A", sub_cat


def _gen_work():
    names = ['김철수', '이영희', '박지민', '최현우', '정다은', '강민석', '조세희', '한준영']
    ranks = ['사원', '주임', '대리', '과장', '차장', '팀장', '부장', '본부장']
    depts = ['인사팀', 'IT전략부', '마케팅팀', '글로벌영업부', '재무회계과', '품질관리팀', '법무지원실']
    projects = ['캡스톤 디자인', '상반기 성과지표', '신규 플랫폼 런칭', '차세대 보안 솔루션', '고객 만족도 조사', '클라우드 전환']
    places = ['제1회의실', '중회의실', '커뮤니티 라운지', '4층 탕비실 옆', '비대면 화상회의', '외부 미팅 장소']
    times = ['오전 10시 30분', '오후 2시', '점심시간 직후', '오늘 퇴근 전까지', '내일 오전 중', '이번 주 금요일']
    work_urls = [
        'http://intra.company.com/notice/129',
        'https://gw.workplace.co.kr/main',
        'https://docs.google.com/spreadsheets/d/work123',
        'http://it-support.internal/ticket',
        'https://zoom.us/j/987654321',
    ]

    work_templates = [
        f"[{random.choice(depts)}] 금일 {random.choice(times)}부터 {random.choice(places)} 이용이 제한됩니다. 양해 부탁드립니다.",
        f"[{random.choice(depts)}] 사내 네트워크 안정화 작업 안내. {random.choice(times)}에 점검 예정입니다.",
        f"[{random.choice(depts)}] 금주 {random.choice(times)}까지 전 사원 보안 점검 리스트 제출 바랍니다. : {random.choice(work_urls)}",
        f"{random.choice(names)} {random.choice(ranks)}님, 요청하신 {random.choice(projects)} 관련 분석 보고서 메일 발송했습니다.",
        f"{random.choice(ranks)}님, {random.choice(projects)} 건으로 잠시 대화 가능할까요? {random.choice(times)}에 찾아뵙겠습니다.",
        f"{random.choice(names)} 씨, 아까 공유해준 {random.choice(projects)} 파일 수정사항 반영해서 다시 전달 부탁해요.",
        f"팀장님, {random.choice(times)}로 예정된 {random.choice(projects)} 미팅 장소를 {random.choice(places)}로 변경했습니다.",
        f"이번 {random.choice(projects)} TF 팀원분들 주목! {random.choice(times)}에 킥오프 미팅 진행합니다. {random.choice(work_urls)}",
        f"다들 고생 많으셨습니다. 이번 {random.choice(projects)} 성공 기념으로 {random.choice(times)}에 부서 회식 진행하겠습니다.",
        f"과장님, 금일 갑작스러운 개인 사정으로 {random.choice(times)}부터 반차 사용하고자 합니다. 결재 부탁드립니다.",
        f"오늘 오전 외부 미팅으로 인해 {random.choice(times)}에 사무실 복귀 예정입니다. 급한 건은 전화 주세요.",
        f"{random.choice(names)} 님, 이번 주 목요일 연차 신청 인트라넷에 상신했습니다. {random.choice(projects)} 인계해두었습니다.",
        f"[인사팀] {random.choice(times)}까지 법정 의무 교육 미이수자는 수강 완료 바랍니다. 링크: {random.choice(work_urls)}",
        f"[{random.choice(depts)}] 이번 상반기 인사이동 및 조직 개편 확정 공지입니다. 그룹웨어 게시판을 확인하세요.",
        f"[IT지원] PC 보안 프로그램 업데이트가 필요합니다. {random.choice(times)} 전까지 재부팅 부탁드립니다.",
        f"[보안] 외부 메일 수신 시 첨부파일 실행에 주의 바랍니다. 의심 메일 신고 안내: {random.choice(work_urls)}",
        f"교수님, {random.choice(projects)} 조장 {random.choice(names)}입니다. 이번 주 {random.choice(times)}에 상담 가능하신가요?",
        f"{random.choice(names)}야, 우리 {random.choice(projects)} 발표 자료 구글 드라이브에 올려놨어. 확인해봐. {random.choice(work_urls)}",
        f"🚨 {random.choice(projects)} 서버에 오류가 발생했습니다. 담당자분들은 지금 바로 {random.choice(work_urls)} 접속 바랍니다.",
        f"{random.choice(names)} 대리님, 아까 말씀하신 {random.choice(projects)} 예산안 오타 수정해서 다시 보냈습니다.",
    ]

    text = random.choice(work_templates)
    return text.strip(), "N/A", ""


def _gen_reservation():
    """예약/교통 관련 알림 (old NOTICE 중 예약/항공/기차 관련)"""
    now = datetime.now()
    date_short = now.strftime('%m/%d')
    time_str = now.strftime('%H:%M')

    sub_cat = random.choice(["MOVIE", "FLIGHT", "TRAIN"])

    if sub_cat == "MOVIE":
        brand = random.choice(["CGV", "롯데시네마", "메가박스"])
        movie_name = random.choice(["파묘", "범죄도시4", "인사이드 아웃 2", "듄: 파트2"])
        scenarios = [
            f"[{brand}] 예매완료 안내\n{date_short} {time_str}\n영화: {movie_name}\n인원: 성인 {random.randint(1, 2)}명\n상영관: {random.randint(1, 8)}관\n즐거운 관람 되세요.",
            f"[{brand}] 티켓 발권이 완료되었습니다.\n상영시간 10분 전 입장을 권장합니다.\n매점 쿠폰 확인: https://m.{brand.lower()}.co.kr/event",
        ]
        text = random.choice(scenarios)
        return text.strip(), "N/A", sub_cat

    elif sub_cat == "FLIGHT":
        brand = random.choice(["대한항공", "아시아나항공", "제주항공"])
        route = random.choice(["인천(ICN)->나리타(NRT)", "김포(GMP)->제주(CJU)", "인천(ICN)->방콕(BKK)"])
        scenarios = [
            f"[{brand}] 항공권 예매 완료\n예약번호: {random.choice(['ABC12D', 'XYZ98P'])}\n노선: {route}\n일시: {date_short} {time_str}\n출발 3시간 전 카운터 방문 바랍니다.",
            f"[{brand}] 모바일 체크인 안내\n고객님, 위탁 수하물 규정을 확인하시고 모바일 탑승권을 발급받으세요.\n상세: https://{brand.lower()}.com/checkin",
        ]
        text = random.choice(scenarios)
        return text.strip(), "N/A", sub_cat

    elif sub_cat == "TRAIN":
        brand = random.choice(["KORAIL", "SRT"])
        train_type = "KTX" if brand == "KORAIL" else "SRT"
        scenarios = [
            f"[{brand}] 승차권 예매 안내\n{date_short} {time_str}\n{random.choice(['서울->부산', '용산->광주송정', '수서->동대구'])}\n열차: {train_type} {random.randint(100, 999)}호\n좌석: {random.randint(1, 15)}{random.choice(['A', 'B', 'C', 'D'])}",
            f"[{brand}] 열차 출발 안내\n잠시 후 열차가 출발합니다. 승차권의 호차와 좌석번호를 다시 확인해 주세요.",
        ]
        text = random.choice(scenarios)
        return text.strip(), "N/A", sub_cat


def generate_dynamic_text(category_idx):
    if category_idx == 0:
        return _gen_personal()
    elif category_idx == 1:
        return _gen_finance()
    elif category_idx == 2:
        if random.random() < 0.15:
            return _gen_reservation()
        return _gen_delivery()
    elif category_idx == 3:
        return _gen_government()
    elif category_idx == 4:
        return _gen_promotion()
    elif category_idx == 5:
        return _gen_auth()
    elif category_idx == 6:
        return _gen_work()
    else:
        return _gen_personal()


# 최종 이미지 합성 루프에서 사용하는 렌더링 헬퍼
def get_wrapped_text(text, font, max_width):
    import re as _re
    lines = []
    token_re = _re.compile(r'https?://\S+')
    for paragraph in text.split('\n'):
        # URL은 줄바꿈 중간에 끊기지 않도록 한 덩어리로 유지
        tokens = []
        last = 0
        for m in token_re.finditer(paragraph):
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

# 최종 확장 템플릿 풀 이전 단계의 중간 전문 생성기
SAFE_DOMAINS = [
    "ex.test", "m.test", "kr.test", "go.test", "pay.test", "auth.test",
]

SUBCATEGORY_POOLS = {
    0: ["DAILY_FAMILY", "DAILY_FRIEND", "EVENT_INVITE", "MONEY_REQUEST", "OBITUARY", "WEDDING", "FAMILY_IMPERSONATION"],
    1: ["BANK_NOTICE", "CARD_PAYMENT", "PAY_TRANSFER", "INVEST_NOTICE", "LOAN_AD", "PAYMENT_SCAM", "ACCOUNT_SCAM"],
    2: ["SHOPPING_ORDER", "COURIER_NORMAL", "DELIVERY_DELAY", "CUSTOMS_SCAM", "ADDRESS_SCAM", "RESERVATION_TICKET"],
    3: ["GOV_NOTICE", "TAX_NOTICE", "HEALTH_NOTICE", "POLICE_SCAM", "COURT_SCAM", "SUBSIDY_SCAM"],
    4: ["STORE_COUPON", "BRAND_SALE", "MEMBERSHIP", "EVENT_WIN", "PRICE_ALERT", "LOCAL_AD"],
    5: ["OTP_CODE", "LOGIN_ALERT", "PASSWORD_CHANGE", "DEVICE_LINK", "ACCOUNT_RECOVERY", "SECURITY_SCAM"],
    6: ["MEETING", "HR_NOTICE", "IT_NOTICE", "APPROVAL", "PROJECT", "URGENT_WORK_SCAM"],
}

_subcat_cursor = {cat: 0 for cat in SUBCATEGORY_POOLS}


def pick_subcategory(category_idx):
    pool = SUBCATEGORY_POOLS[category_idx]
    cursor = _subcat_cursor[category_idx]
    _subcat_cursor[category_idx] += 1
    return pool[cursor % len(pool)]


def fake_url(keyword="notice"):
    domain = random.choice(SAFE_DOMAINS)
    code = random.randint(1000, 999999)
    return f"https://{keyword}{code}.{domain}"


def maybe_header(kind="web"):
    headers = {
        "web": ["[Web발신]\n", "[국외발신]\n", ""],
        "ad": ["(광고) ", "[광고] ", ""],
        "none": [""],
    }
    return random.choice(headers.get(kind, [""]))


def money(min_man=1, max_man=300):
    return f"{random.randint(min_man, max_man) * 10000:,}원"


def order_no(prefix=""):
    letters = "".join(random.choice("ABCDEFGHJKLMNPQRSTUVWXYZ") for _ in range(2))
    return f"{prefix}{letters}{random.randint(100000, 999999)}"


def realistic_noise(text):
    if random.random() < 0.12:
        text = text.replace("확인", random.choice(["확 인", "확인.", "확인요청"]), 1)
    if random.random() < 0.10:
        text = text.replace("드립니다", random.choice(["드립니다.", "드림니다", "드립니다"]), 1)
    if random.random() < 0.10:
        text += random.choice(["\n무료수신거부 080-000-0000", " /", " .", ""])
    return text


def gen_personal_professional(sub_cat):
    now = datetime.now()
    date_short = now.strftime("%m/%d")
    family = ["엄마", "아빠", "누나", "형", "동생", "이모", "삼촌", "할머니"]
    names = ["민수", "지훈", "서연", "유진", "현우", "지아", "도윤", "수빈", "예린", "준호"]
    places = ["강남역 11번 출구", "홍대입구", "회사 앞", "학교 정문", "병원 로비", "스터디룸", "카페"]
    activities = ["저녁 먹기", "과제 제출", "회의 준비", "생일 모임", "동창회", "영화 예매", "짐 찾기"]
    url = fake_url("family")
    templates = {
        "DAILY_FAMILY": [
            f"{random.choice(family)}, 오늘 늦게 들어갈 것 같아. 저녁은 먼저 드세요.",
            f"{random.choice(family)} 지금 어디야? 우산 안 가져왔으면 역 앞에서 같이 가자.",
            f"{random.choice(family)}, 택배 문 앞에 왔다고 해서 혹시 보이면 안으로 넣어줘.",
            f"{random.choice(family)} 병원 예약 {date_short} 오후로 잡아뒀어. 시간 괜찮은지 확인해줘.",
        ],
        "DAILY_FRIEND": [
            f"{random.choice(names)}야 오늘 {random.choice(places)}에서 {random.choice(activities)} 하는 거 맞지?",
            "나 15분 정도 늦을 것 같아. 먼저 들어가 있어.",
            "아까 말한 자료 단톡방에 올렸어. 확인하고 빠진 부분 있으면 알려줘.",
            f"오늘 메뉴 {random.choice(['김치찌개', '마라탕', '초밥', '파스타', '치킨'])} 어때?",
        ],
        "EVENT_INVITE": [
            f"{random.choice(names)} 생일 모임 장소가 {random.choice(places)}로 변경됐어. 시간은 그대로야.",
            "이번 주말 집들이 하려고 해. 가능하면 저녁 7시쯤 와줘.",
            "동기 모임 참석자 확인 중이야. 참석 가능하면 오늘 안에 답장 부탁해.",
        ],
        "MONEY_REQUEST": [
            f"{random.choice(names)}야 아까 계산한 회비 {money(1, 8)} 보내줘. 계좌는 단톡에 올릴게.",
            f"지난번 빌린 {money(3, 30)} 오늘 입금했어. 늦어서 미안해.",
            f"모임 예약금 먼저 냈어. 1인당 {money(1, 5)}씩 보내주면 돼.",
        ],
        "OBITUARY": [
            f"{maybe_header()}[부고] {random.choice(names)}님의 부친께서 별세하셨기에 삼가 알려드립니다. 빈소: 서울중앙병원 장례식장\n모바일 부고장: {url}",
            f"[부고알림] 고인의 마지막 길에 따뜻한 위로 부탁드립니다. 빈소 및 장례 일정 확인: {url}",
            f"{maybe_header()}부고 안내드립니다. 장례식장 위치와 조문 계좌는 아래 모바일 안내장에서 확인 부탁드립니다.\n{url}",
        ],
        "WEDDING": [
            f"[모바일청첩장] {random.choice(names)} & {random.choice(names)} 결혼식에 초대합니다. 일시/장소 확인: {url}",
            f"{maybe_header()}소중한 분들을 결혼식에 모시고자 합니다. 모바일 청첩장: {url}",
            f"결혼식 참석 여부 확인 부탁드립니다. 식장 위치와 주차 안내: {url}",
        ],
        "FAMILY_IMPERSONATION": [
            f"{random.choice(family)} 나 휴대폰 액정이 나가서 임시폰으로 문자해. 본인확인 좀 도와줘 {url}",
            f"{random.choice(family)} 급하게 결제해야 하는데 인증이 안 돼. 링크 들어가서 확인만 해줘 {url}",
            f"{random.choice(family)} 지금 통화가 안 돼서 문자 남겨. 상품권 구매가 필요한데 잠깐 확인 부탁해 {url}",
        ],
    }
    text = random.choice(templates[sub_cat])
    return realistic_noise(text), url if sub_cat in ["OBITUARY", "WEDDING", "FAMILY_IMPERSONATION"] else "N/A", sub_cat


def gen_finance_professional(sub_cat):
    now = datetime.now()
    date_short = now.strftime("%m/%d")
    time_str = now.strftime("%H:%M")
    banks = ["KB국민은행", "신한은행", "우리은행", "하나은행", "NH농협", "IBK기업은행", "카카오뱅크", "토스뱅크"]
    cards = ["삼성카드", "현대카드", "신한카드", "KB국민카드", "롯데카드", "BC카드"]
    stores = ["쿠팡", "배달의민족", "스타벅스", "네이버페이", "GS칼텍스", "이마트", "APPLE.COM/BILL"]
    url = fake_url("finance")
    templates = {
        "BANK_NOTICE": [
            f"[{random.choice(banks)}] 입금 {money(1, 200)}\n{date_short} {time_str}\n잔액 {money(50, 5000)}",
            f"[{random.choice(banks)}] 출금 {money(1, 150)}\n{date_short} {time_str}\n받는분 {random.choice(['관리비', '보험료', '카드대금', '자동이체'])}",
            f"[{random.choice(banks)}] 자동이체 예정 안내\n{date_short} {time_str} {money(5, 80)} 출금 예정입니다.",
        ],
        "CARD_PAYMENT": [
            f"[{random.choice(cards)}] 승인 {money(1, 200)}\n{date_short} {time_str}\n가맹점 {random.choice(stores)}",
            f"[{random.choice(cards)}] 승인취소 -{money(1, 100)}\n{date_short} {time_str}\n처리 완료",
            f"[{random.choice(cards)}] 해외승인 USD {random.randint(5, 900)}.{random.randint(10,99)}\n가맹점 {random.choice(['AMAZON', 'PAYPAL', 'AGODA', 'APPLE'])}",
        ],
        "PAY_TRANSFER": [
            f"[카카오페이] {money(1, 80)} 결제 완료\n{date_short} {time_str}\n가맹점 {random.choice(stores)}",
            f"[토스] {random.choice(['김*수', '박*영', '최*진'])}님에게 {money(1, 50)} 송금 완료",
            f"[네이버페이] 포인트 {random.randint(100, 9000):,}원 적립 예정입니다.",
        ],
        "INVEST_NOTICE": [
            f"[미래에셋증권] {random.choice(['삼성전자', 'NAVER', '현대차', 'KODEX 200'])} {random.randint(1, 30)}주 체결 완료",
            f"[한국투자증권] 배당금 {money(1, 20)} 입금 예정\n종목 {random.choice(['삼성전자', 'SK하이닉스', '현대차'])}",
            "[토스증권] 예약주문이 접수되었습니다. 체결 여부는 장 시작 후 확인 가능합니다.",
        ],
        "LOAN_AD": [
            f"{maybe_header('ad')}[{random.choice(banks)}] 비대면 신용대출 한도 조회 가능. 예상한도 최대 {money(500, 5000)}\n상담: {url}",
            f"{maybe_header('ad')}정부지원 서민대출 대상자 확인 안내. 금리 연 {random.randint(3, 8)}%대 가능\n{url}",
            f"{maybe_header('ad')}기존 대출 대환 안내. 중도상환수수료 조건 확인: {url}",
        ],
        "PAYMENT_SCAM": [
            f"{maybe_header()}[{random.choice(cards)}] 본인 미사용 결제 {money(40, 300)} 발생. 취소 요청: {url}",
            f"{maybe_header()}해외 IP에서 결제가 시도되었습니다. 본인 확인 후 차단 진행: {url}",
            f"[{random.choice(banks)}] 계좌 신규 개설 시도 감지. 본인이 아니면 즉시 확인: {url}",
        ],
        "ACCOUNT_SCAM": [
            f"{maybe_header()}[{random.choice(banks)}] 보안등급 만료 예정. 미갱신 시 일부 거래 제한\n갱신: {url}",
            f"{maybe_header()}전자금융 이상거래 탐지로 계좌가 임시 제한되었습니다. 해제 신청: {url}",
            f"[금융보안센터] 고객님 명의 계좌에서 비정상 접근이 확인되었습니다. 확인: {url}",
        ],
    }
    scam = sub_cat in ["LOAN_AD", "PAYMENT_SCAM", "ACCOUNT_SCAM"]
    return realistic_noise(random.choice(templates[sub_cat])), url if scam else "N/A", sub_cat


def gen_delivery_professional(sub_cat):
    now = datetime.now()
    date_short = now.strftime("%m/%d")
    carriers = ["CJ대한통운", "롯데택배", "한진택배", "우체국택배", "로젠택배", "쿠팡"]
    shops = ["쿠팡", "네이버쇼핑", "11번가", "G마켓", "마켓컬리", "오늘의집"]
    products = ["생활용품", "건강식품", "무선이어폰", "도서", "의류", "반려용품", "주방용품"]
    url = fake_url("delivery")
    templates = {
        "SHOPPING_ORDER": [
            f"[{random.choice(shops)}] 주문이 완료되었습니다.\n주문번호 {order_no('O')}\n상품: {random.choice(products)}",
            f"[{random.choice(shops)}] 결제 완료 {money(1, 80)}\n배송 준비가 시작되었습니다.",
            "[마켓컬리] 교환 접수가 완료되었습니다. 회수 일정은 별도 안내드립니다.",
        ],
        "COURIER_NORMAL": [
            f"[{random.choice(carriers)}] 고객님의 택배가 배송 출발했습니다.\n운송장 {random.randint(1000000000, 9999999999)}",
            f"[{random.choice(carriers)}] 배송 완료\n문 앞에 두었습니다. 이용해 주셔서 감사합니다.",
            f"[{random.choice(carriers)}] 택배가 집하 처리되었습니다. 배송조회는 잠시 후 가능합니다.",
        ],
        "DELIVERY_DELAY": [
            f"[{random.choice(carriers)}] 물량 증가로 배송이 지연되고 있습니다. 예상 도착일 {date_short}",
            f"[{random.choice(shops)}] 일부 상품 입고 지연으로 배송 일정이 변경되었습니다.",
            f"[{random.choice(carriers)}] 부재중으로 배송하지 못했습니다. 재방문 예정입니다.",
        ],
        "CUSTOMS_SCAM": [
            f"{maybe_header()}[관세청] 해외배송 물품 통관 보류. 개인통관고유부호 확인 필요: {url}",
            f"[국제배송] 수취인 정보 오류로 통관이 지연 중입니다. 정보 수정: {url}",
            f"{maybe_header()}수입신고 물품 관세 미납 안내. 납부 확인 후 배송 진행: {url}",
        ],
        "ADDRESS_SCAM": [
            f"{maybe_header()}[{random.choice(carriers)}] 주소 일부 누락으로 배송 보류. 주소 재확인: {url}",
            f"[택배알림] 수취인 연락처 오류로 배송 실패. 재배송 신청: {url}",
            f"{maybe_header()}배송지 확인이 필요합니다. 오늘 안에 확인하지 않으면 반송될 수 있습니다: {url}",
        ],
        "RESERVATION_TICKET": [
            f"[KORAIL] 승차권 예매 완료\n열차 {random.choice(['KTX', 'ITX', '무궁화'])} {random.randint(100,999)}\n좌석 {random.randint(1,15)}{random.choice(['A','B','C','D'])}",
            f"[CGV] 예매 완료\n상영일 {date_short}\n좌석 {random.choice(['E열 7번', 'F열 10번', 'H열 5번'])}",
            f"[대한항공] 모바일 체크인 안내\n예약번호 {order_no()}\n출발 3시간 전 공항 도착 권장",
        ],
    }
    scam = sub_cat in ["CUSTOMS_SCAM", "ADDRESS_SCAM"]
    return realistic_noise(random.choice(templates[sub_cat])), url if scam else "N/A", sub_cat


def gen_government_professional(sub_cat):
    url = fake_url("gov")
    templates = {
        "GOV_NOTICE": [
            "[정부24] 신청하신 민원서류 발급이 완료되었습니다. 정부24 앱에서 확인 가능합니다.",
            "[행정안전부] 주민등록 사실조사 참여 안내. 세대별 확인에 협조 부탁드립니다.",
            "[국민비서] 생활정보 알림이 도착했습니다. 자세한 내용은 국민비서에서 확인하세요.",
        ],
        "TAX_NOTICE": [
            "[국세청] 종합소득세 신고 안내. 신고기한 내 홈택스에서 확인 바랍니다.",
            "[국세청] 환급금 지급 예정 안내. 지급 계좌 등록 여부를 확인해 주세요.",
            "[지방세] 자동차세 납부기한이 도래했습니다. 위택스 또는 은행 앱에서 납부 가능합니다.",
        ],
        "HEALTH_NOTICE": [
            "[국민건강보험] 건강검진 대상자 안내. 검진기관 예약 후 방문 바랍니다.",
            "[질병관리청] 예방접종 예약 변경 안내. 예약 내역을 확인해 주세요.",
            "[건강보험공단] 보험료 고지서가 발송되었습니다. 납부기한을 확인 바랍니다.",
        ],
        "POLICE_SCAM": [
            f"{maybe_header()}[경찰청] 사건번호 {random.randint(20240000, 20269999)} 관련 출석요구서 확인: {url}",
            f"[사이버수사대] 귀하 명의 계좌가 범죄에 연루되어 확인이 필요합니다: {url}",
            f"{maybe_header()}수사협조 요청. 미확인 시 불이익이 발생할 수 있습니다. 확인: {url}",
        ],
        "COURT_SCAM": [
            f"{maybe_header()}[법원] 등기 우편 반송으로 전자문서 송달 안내: {url}",
            f"[대한민국법원] 지급명령 관련 문서가 도착했습니다. 열람: {url}",
            f"{maybe_header()}민사소송 통지서 확인 요청. 본인 인증 후 열람 가능합니다: {url}",
        ],
        "SUBSIDY_SCAM": [
            f"{maybe_header()}[복지지원센터] 긴급생활지원금 대상자로 선정되었습니다. 신청: {url}",
            f"[정부지원금] 미수령 환급금이 있습니다. 지급계좌 확인: {url}",
            f"{maybe_header()}소상공인 지원금 추가 접수 안내. 마감 전 신청: {url}",
        ],
    }
    scam = sub_cat in ["POLICE_SCAM", "COURT_SCAM", "SUBSIDY_SCAM"]
    return realistic_noise(random.choice(templates[sub_cat])), url if scam else "N/A", sub_cat


def gen_promotion_professional(sub_cat):
    brands = ["올리브영", "이마트", "스타벅스", "무신사", "배달의민족", "롯데온", "GS25", "CJ ONE"]
    url = fake_url("event")
    templates = {
        "STORE_COUPON": [
            f"{maybe_header('ad')}[{random.choice(brands)}] 오늘만 사용 가능한 {random.randint(10, 40)}% 할인쿠폰이 도착했습니다.\n{url}",
            f"{maybe_header('ad')}장바구니 상품 재입고 안내. 지금 구매 시 쿠폰 적용 가능\n{url}",
            f"{maybe_header('ad')}첫 구매 고객 무료배송 쿠폰 지급 완료. 확인: {url}",
        ],
        "BRAND_SALE": [
            f"{maybe_header('ad')}[{random.choice(brands)}] 시즌오프 최대 {random.randint(30, 80)}% 할인 시작\n{url}",
            f"{maybe_header('ad')}단 하루 특가 공개. 인기상품 한정 수량 판매\n{url}",
            f"{maybe_header('ad')}멤버십 고객 전용 사전 세일 오픈\n{url}",
        ],
        "MEMBERSHIP": [
            f"[{random.choice(brands)}] 고객님의 멤버십 포인트 {random.randint(500, 50000):,}P가 곧 소멸됩니다.",
            f"{maybe_header('ad')}등급 유지 혜택 안내. 이번 달 구매 실적을 확인해 주세요.\n{url}",
            "[CJ ONE] 포인트 적립 완료. 앱에서 상세 내역을 확인하세요.",
        ],
        "EVENT_WIN": [
            f"{maybe_header('ad')}이벤트 당첨 안내. 경품 수령을 위해 배송 정보를 입력해 주세요: {url}",
            f"[{random.choice(brands)}] 리뷰 이벤트 당첨 축하드립니다. 쿠폰이 지급되었습니다.",
            f"{maybe_header('ad')}설문 참여 고객 추첨 결과 확인. 당첨 여부 조회: {url}",
        ],
        "PRICE_ALERT": [
            f"[가격알림] 관심상품 가격이 {random.randint(5, 30)}% 하락했습니다. 지금 확인해 보세요.",
            "[쇼핑알림] 찜한 상품의 재고가 얼마 남지 않았습니다.",
            "[특가알림] 최근 본 상품이 오늘 한정가로 변경되었습니다.",
        ],
        "LOCAL_AD": [
            f"{maybe_header('ad')}우리동네 신규 매장 오픈 이벤트. 방문 고객 음료 증정\n{url}",
            f"{maybe_header('ad')}근처 매장에서 사용 가능한 쿠폰이 도착했습니다.\n{url}",
            f"{maybe_header('ad')}주말 예약 고객 할인 안내. 잔여 시간 확인: {url}",
        ],
    }
    with_url = sub_cat in ["STORE_COUPON", "BRAND_SALE", "EVENT_WIN", "LOCAL_AD"]
    return realistic_noise(random.choice(templates[sub_cat])), url if with_url else "N/A", sub_cat


def gen_auth_professional(sub_cat):
    code = random.randint(100000, 999999)
    ip = f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}"
    services = ["네이버", "카카오", "Google", "Apple", "쿠팡", "토스", "Upbit", "Steam"]
    devices = ["iPhone", "Galaxy", "Windows PC", "MacBook", "Chrome 브라우저"]
    url = fake_url("auth")
    templates = {
        "OTP_CODE": [
            f"[{random.choice(services)}] 인증번호 [{code}]를 입력해 주세요. 타인에게 알려주지 마세요.",
            f"[본인확인] 인증번호 {code} 입니다. 3분 이내 입력 바랍니다.",
            f"[간편인증] 요청하신 인증번호는 {code}입니다.",
        ],
        "LOGIN_ALERT": [
            f"[{random.choice(services)}] 새로운 기기에서 로그인되었습니다.\n기기: {random.choice(devices)}\nIP: {ip}",
            f"[카카오톡] PC버전 로그인 알림. 본인이 아니면 즉시 비밀번호를 변경해 주세요.",
            f"[네이버] 해외 로그인 차단 설정으로 접근이 차단되었습니다. IP {ip}",
        ],
        "PASSWORD_CHANGE": [
            f"[{random.choice(services)}] 비밀번호가 변경되었습니다. 본인이 아니라면 고객센터로 문의하세요.",
            "[보안알림] 계정 복구 이메일이 변경되었습니다.",
            f"[{random.choice(services)}] 2단계 인증 설정이 완료되었습니다.",
        ],
        "DEVICE_LINK": [
            f"[카카오] 새 기기 연결 요청이 있습니다. 연결코드 {code}",
            f"[Apple] Apple ID가 {random.choice(devices)}에서 사용되었습니다.",
            "[Google] 보안 키 등록 요청이 감지되었습니다.",
        ],
        "ACCOUNT_RECOVERY": [
            f"[{random.choice(services)}] 계정 복구 코드 [{code}]입니다. 요청하지 않았다면 무시하세요.",
            "[고객센터] 아이디 찾기 결과가 발송되었습니다.",
            f"[{random.choice(services)}] 휴면 계정 해제 인증번호 {code}",
        ],
        "SECURITY_SCAM": [
            f"{maybe_header()}[{random.choice(services)}] 계정이 임시 제한되었습니다. 본인확인: {url}",
            f"{maybe_header()}비정상 로그인으로 보안 점검이 필요합니다. 즉시 확인: {url}",
            f"[보안센터] 인증 만료 예정. 서비스 이용 제한 전 갱신하세요: {url}",
        ],
    }
    return realistic_noise(random.choice(templates[sub_cat])), url if sub_cat == "SECURITY_SCAM" else "N/A", sub_cat


def gen_work_professional(sub_cat):
    names = ["김민수", "박지영", "이서연", "최현우", "정다은", "강준호", "오유진", "한지훈"]
    ranks = ["사원", "주임", "대리", "과장", "차장", "팀장", "부장"]
    depts = ["인사팀", "재무팀", "IT지원팀", "영업기획팀", "마케팅팀", "법무팀", "총무팀"]
    projects = ["분기 실적 보고", "신규 캠페인", "보안 점검", "고객 만족도 조사", "서버 이전", "계약 검토"]
    url = fake_url("work")
    templates = {
        "MEETING": [
            f"[{random.choice(depts)}] 금일 회의 시간이 오후 {random.randint(2,5)}시로 변경되었습니다.",
            f"{random.choice(names)} {random.choice(ranks)}님, {random.choice(projects)} 관련해서 10분만 미팅 가능하실까요?",
            "내일 오전 회의 자료는 공유드라이브에 업로드 부탁드립니다.",
        ],
        "HR_NOTICE": [
            "[인사팀] 법정의무교육 수강 기한이 이번 주 금요일까지입니다.",
            "[인사팀] 연차 사용 계획 제출 요청드립니다. 오늘 중 회신 부탁드립니다.",
            "[총무팀] 사원증 재발급 신청이 접수되었습니다.",
        ],
        "IT_NOTICE": [
            "[IT지원팀] 사내 VPN 점검 예정입니다. 작업 시간 중 접속이 불안정할 수 있습니다.",
            "[보안] 외부 메일 첨부파일 실행 주의 안내드립니다.",
            "[IT지원팀] PC 보안 프로그램 업데이트를 오늘 퇴근 전 진행해 주세요.",
        ],
        "APPROVAL": [
            f"{random.choice(names)} {random.choice(ranks)}님, 지출결의서 결재 요청 올렸습니다. 확인 부탁드립니다.",
            f"[전자결재] 신규 결재 문서가 도착했습니다. 제목: {random.choice(projects)}",
            "계약서 검토본 반영했습니다. 법무팀 확인 후 재상신하겠습니다.",
        ],
        "PROJECT": [
            f"{random.choice(projects)} 일정표 최신본 공유했습니다. 변경 사항 확인 부탁드립니다.",
            "클라이언트 피드백 반영본을 메일로 전달했습니다.",
            "이번 주 업무 진행률 업데이트 부탁드립니다. 누락 항목은 오늘 안에 정리해 주세요.",
        ],
        "URGENT_WORK_SCAM": [
            f"{maybe_header()}대표님 지시사항입니다. 긴급 송금 승인 필요하니 보안문서 확인: {url}",
            f"{maybe_header()}급여명세서 오류 정정 안내. 본인확인 후 재발급: {url}",
            f"[사내공지] 임직원 개인정보 최신화 요청. 미제출 시 시스템 이용 제한: {url}",
        ],
    }
    return realistic_noise(random.choice(templates[sub_cat])), url if sub_cat == "URGENT_WORK_SCAM" else "N/A", sub_cat


def generate_dynamic_text(category_idx):
    sub_cat = pick_subcategory(category_idx)
    generators = {
        0: gen_personal_professional,
        1: gen_finance_professional,
        2: gen_delivery_professional,
        3: gen_government_professional,
        4: gen_promotion_professional,
        5: gen_auth_professional,
        6: gen_work_professional,
    }
    return generators.get(category_idx, gen_personal_professional)(sub_cat)




# 대량 생성용 확장 엔진 헬퍼와 템플릿 풀
class SafeFormatDict(dict):
    def __missing__(self, key):
        return "{" + key + "}"


def expanded_values(category_idx, sub_cat, url):
    now = datetime.now()
    next_day = now + timedelta(days=random.randint(1, 5))
    values = {
        "url": url,
        "date": now.strftime("%m/%d"),
        "date_full": now.strftime("%Y-%m-%d"),
        "next_date": next_day.strftime("%m/%d"),
        "time": now.strftime("%H:%M"),
        "time_slot": random.choice(["오전 9시", "오전 10시 30분", "오후 1시", "오후 2시", "오후 3시 30분", "오후 6시", "저녁 7시"]),
        "deadline": random.choice(["오늘 18시", "오늘 자정", "이번 주 금요일", "내일 오전", "금일 업무 종료 전", "24시간 이내"]),
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
        "agency": random.choice(["정부24", "국세청", "국민건강보험", "고용노동부", "국민연금", "행정안전부", "질병관리청"]),
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
            "{family} 병원 예약 {next_date} {time_slot}로 잡아뒀어. 시간 괜찮은지 확인해줘.",
        ],
        "DAILY_FRIEND": [
            "{friend}야 오늘 {place}에서 {activity} 하는 거 맞지?",
            "나 15분 정도 늦을 것 같아. 먼저 들어가 있어.",
            "아까 말한 자료 단톡방에 올렸어. 빠진 부분 있으면 알려줘.",
            "오늘 메뉴 {food} 어때? 괜찮으면 내가 예약해둘게.",
        ],
        "APPOINTMENT": [
            "{date} {time_slot} 예약 확인드립니다. 방문이 어려우시면 사전에 연락 부탁드립니다.",
            "예약 시간이 {time_slot}로 변경되었습니다. 장소는 {place} 그대로입니다.",
            "{friend}님 예약 대기 순번이 앞당겨졌습니다. 가능하시면 {deadline}까지 회신 주세요.",
            "오늘 상담 예약이 있습니다. 도착 10분 전까지 접수 부탁드립니다.",
        ],
        "STUDY_SCHOOL": [
            "[{school}] {class_name} 과제 제출 기한은 {deadline}입니다.",
            "{teacher}입니다. 내일 준비물은 {item}입니다. 학생에게 전달 부탁드립니다.",
            "[{school}] 출결 확인 요청드립니다. 결석 사유가 있으면 회신 부탁드립니다.",
            "스터디 자료를 공유했습니다. {deadline}까지 문제 풀이 완료해 주세요.",
        ],
        "EVENT_INVITE": [
            "{friend} 생일 모임 장소가 {place}로 변경됐어. 시간은 그대로야.",
            "이번 주말 집들이 하려고 해. 가능하면 {time_slot}쯤 와줘.",
            "동기 모임 참석자 확인 중이야. 참석 가능하면 {deadline}까지 답장 부탁해.",
            "{activity} 일정 잡으려고 해. {next_date} 괜찮은지 알려줘.",
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
            "기프티콘 보냈어. 문자함 확인해봐.",
            "{food} 쿠폰 하나 남아서 보냈어. 오늘 안에 써도 돼.",
        ],
        "HEALTH_FAMILY": [
            "{family}, 약은 식후에 챙겨 드세요. 물 많이 마시고.",
            "{hospital} 검사 결과는 다음 주에 나온대. 문자 오면 알려줘.",
            "오늘 미세먼지 심하니까 외출할 때 마스크 챙겨.",
            "{family} 병원 접수번호 받으면 나한테도 보내줘.",
        ],
        "OBITUARY": [
            "{header}[부고] {friend}님의 {relation}께서 별세하셨기에 삼가 알려드립니다. 빈소: {hospital} 장례식장\n모바일 부고장: {url}",
            "[부고알림] 고인의 마지막 길에 따뜻한 위로 부탁드립니다. 빈소 및 장례 일정 확인: {url}",
            "{header}부고 안내드립니다. 장례식장 위치와 조문 계좌는 모바일 안내장에서 확인 부탁드립니다.\n{url}",
            "[訃告] {masked_name}님의 {relation}상. 발인 일정 및 빈소 안내: {url}",
        ],
        "WEDDING": [
            "[모바일청첩장] {friend} & {name2} 결혼식에 초대합니다. 일시/장소 확인: {url}",
            "{header}소중한 분들을 결혼식에 모시고자 합니다. 모바일 청첩장: {url}",
            "결혼식 참석 여부 확인 부탁드립니다. 식장 위치와 주차 안내: {url}",
            "[청첩장] {next_date} {hall}에서 뵙겠습니다. 참석 회신: {url}",
        ],
        "CHILD_SCHOOL": [
            "[{school}] 학부모 상담 일정 안내드립니다. 희망 시간 회신 부탁드립니다.",
            "[{school}] 급식비 납부 내역이 확인되었습니다.",
            "[{school}] 현장학습 동의서 제출 기한은 {deadline}입니다.",
            "[{school}] 학생 건강상태 확인 문자가 발송되었습니다. 담임에게 회신 바랍니다.",
        ],
        "MOVE_HELP": [
            "{friend}야 {next_date} 이사하는데 시간 되면 1시간만 도와줄 수 있어?",
            "짐이 생각보다 많아서 {item} 챙겨와 주면 고마울 것 같아.",
            "{place} 근처에서 짐 내릴 예정이야. 도착하면 연락할게.",
            "이사 차량 예약했어. {time_slot} 전에 내려와 줘.",
        ],
        "FAMILY_IMPERSONATION": [
            "{family} 나 휴대폰 액정이 나가서 임시폰으로 문자해. 본인확인 좀 도와줘 {url}",
            "{family} 급하게 결제해야 하는데 인증이 안 돼. 링크 들어가서 확인만 해줘 {url}",
            "{family} 지금 통화가 안 돼서 문자 남겨. 상품권 구매가 필요한데 잠깐 확인 부탁해 {url}",
            "{family} 계정 잠겨서 연락처 인증이 필요해. 내가 보낸 화면에서 확인해줘 {url}",
        ],
        "LOST_PHONE_SCAM": [
            "나 {friend}인데 폰을 잃어버려서 임시번호로 보내. 급한 확인만 부탁해 {url}",
            "{family} 지금 다른 사람 폰으로 문자해. 인증번호 받으면 알려줘 {url}",
            "휴대폰 고장나서 은행 인증이 안 돼. 잠깐만 도와줘 {url}",
            "카톡 로그인이 안 돼서 문자 남겨. 친구 추가 전에 확인해줘 {url}",
        ],
        "UTILITY_HOME": [
            "{family}, {utility} 고지서 나왔대. 내가 저녁에 확인할게.",
            "{family} 관리사무소에서 {utility} 납부 안내 왔다고 하네. 종이 있으면 사진만 보내줘.",
            "{utility} 자동이체 등록 확인 문자 왔어. 내가 집 가서 다시 볼게.",
            "{family}, 이번 달 {utility} 납부일이 {next_date}래. 깜빡할까봐 미리 보냄.",
        ],
        "PET_CARE": [
            "{family}, {pet} 사료 거의 다 떨어졌대. 오는 길에 주문할게.",
            "{friend}야 오늘 집 비울 것 같아서 {pet} 밥 좀 한번만 봐줄 수 있어?",
            "{pet} 병원 예약이 {next_date} {time_slot}로 잡혔어. 시간 되면 같이 가자.",
            "{family}, {pet} 산책은 내가 늦으면 먼저 부탁해.",
        ],
        "PARENT_GROUP": [
            "[학부모방] 준비물은 {item}이며 등교 전 확인 부탁드립니다.",
            "[학부모알림] 현장체험학습 귀가 시간이 {time_slot} 전후로 예정되어 있습니다.",
            "[반대표] 이번 주 간식비는 1인당 {small_amount}입니다. 가능하시면 오늘 중 부탁드립니다.",
            "[학교공지] 학부모 총회 참석 여부를 {deadline}까지 회신 부탁드립니다.",
        ],
    },
    1: {
        "BANK_DEPOSIT": [
            "[{bank}] 입금 {amount}\n{date} {time}\n잔액 {large_amount}",
            "[{bank}] {masked_name}님으로부터 {amount} 입금되었습니다.",
            "[{bank}] 급여 입금 알림\n금액 {large_amount}\n계좌 {account}",
            "[{bank}] 이체 입금 완료. 상세 내역은 앱에서 확인 가능합니다.",
        ],
        "BANK_WITHDRAWAL": [
            "[{bank}] 출금 {amount}\n{date} {time}\n받는분 {bill}",
            "[{bank}] ATM 출금 {amount}\n위치 {location}\n본인 거래가 아니면 고객센터로 문의하세요.",
            "[{bank}] 예약이체가 실행되었습니다. 금액 {amount}",
            "[{bank}] 계좌 {account}에서 {bill} 자동납부 처리되었습니다.",
        ],
        "AUTO_TRANSFER": [
            "[{bank}] {bill} 자동이체 예정 안내\n{next_date} {amount} 출금 예정입니다.",
            "[{bank}] 자동이체 실패\n잔액 부족으로 {bill} 납부가 처리되지 않았습니다.",
            "[{bank}] 자동이체 신청이 완료되었습니다. 출금일은 매월 {random_day}일입니다.",
            "[{bank}] 납부 예약 내역이 변경되었습니다. 앱에서 상세 확인 가능합니다.",
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
            "[{card}] 해외 온라인 결제 승인\nKRW {amount}\n본인 이용이 아니면 즉시 신고 바랍니다.",
            "[{card}] 해외 원화결제 차단 설정이 적용되었습니다.",
            "[{card}] 해외 이용 알림. 국가 {country}, 금액 {amount}",
        ],
        "PAY_TRANSFER": [
            "[{pay_app}] {amount} 결제 완료\n{date} {time}\n가맹점 {store}",
            "[{pay_app}] {masked_name}님에게 {small_amount} 송금 완료",
            "[{pay_app}] 포인트 {points} 적립 예정입니다.",
            "[{pay_app}] 송금 받기가 도착했습니다. 앱에서 확인하세요.",
        ],
        "SECURITIES_TRADE": [
            "[{securities}] {stock} {share_count}주 체결 완료",
            "[{securities}] 예약주문 접수 완료. 체결 여부는 장 시작 후 확인 가능합니다.",
            "[{securities}] 미수금 발생 안내. {deadline}까지 확인 바랍니다.",
            "[{securities}] 공모주 청약 배정 결과가 등록되었습니다.",
        ],
        "STOCK_DIVIDEND": [
            "[{securities}] 배당금 {small_amount} 입금 예정\n종목 {stock}",
            "[{securities}] 배당소득세 원천징수 내역이 등록되었습니다.",
            "[{securities}] 외화 배당금 입금 알림. 상세 내역은 앱에서 확인하세요.",
            "[{securities}] 주식 입고 처리 완료. 종목 {stock}",
        ],
        "INSURANCE_BILL": [
            "[{insurance}] 보험료 {amount} 출금 예정입니다. 출금일 {next_date}",
            "[{insurance}] 보험금 청구 서류가 접수되었습니다.",
            "[{insurance}] 자동차보험 갱신 안내. 만기 전 조건을 확인해 주세요.",
            "[{insurance}] 청구 심사가 완료되었습니다. 지급 예정 금액 {amount}",
        ],
        "LOAN_AD": [
            "{ad_header}[{bank}] 비대면 신용대출 한도 조회 가능. 예상한도 최대 {large_amount}\n상담: {url}",
            "{ad_header}정부지원 서민대출 대상자 확인 안내. 금리 연 {rate}%대 가능\n{url}",
            "{ad_header}기존 대출 대환 안내. 중도상환수수료 조건 확인: {url}",
            "{ad_header}직장인 우대 한도 사전조회. 신용점수 영향 없이 확인: {url}",
        ],
        "LIMIT_INCREASE": [
            "[{card}] 이용한도 변경 신청이 접수되었습니다.",
            "[{card}] 임시한도 상향 가능 대상입니다. 앱에서 신청 여부를 선택하세요.",
            "[{bank}] 이체한도 변경 완료. 본인이 아니면 고객센터로 문의하세요.",
            "[{card}] 해외 이용한도 설정이 변경되었습니다.",
        ],
        "PAYMENT_SCAM": [
            "{header}[{card}] 본인 미사용 결제 {amount} 발생. 취소 요청: {url}",
            "{header}해외 IP에서 결제가 시도되었습니다. 본인 확인 후 차단 진행: {url}",
            "[{bank}] 계좌 신규 개설 시도 감지. 본인이 아니면 즉시 확인: {url}",
            "[{card}] 고액 결제 대기 중. 취소하지 않으면 승인될 수 있습니다: {url}",
        ],
        "ACCOUNT_RESTRICT_SCAM": [
            "{header}[{bank}] 보안등급 만료 예정. 미갱신 시 일부 거래 제한\n갱신: {url}",
            "{header}전자금융 이상거래 탐지로 계좌가 임시 제한되었습니다. 해제 신청: {url}",
            "[금융보안센터] 고객님 명의 계좌에서 비정상 접근이 확인되었습니다. 확인: {url}",
            "[{bank}] 장기 미사용 계좌 보호조치 예정. 본인 인증: {url}",
        ],
        "INVESTMENT_SCAM": [
            "{ad_header}[투자정보] {stock} 단기 급등 예상 리포트 공개. 무료 확인: {url}",
            "{header}가상자산 출금 제한 해제를 위해 지갑 인증이 필요합니다: {url}",
            "[리딩방초대] 금일 추천 종목과 매수가를 확인하세요: {url}",
            "{ad_header}원금보장형 투자 상품 사전 신청 마감 임박: {url}",
        ],
        "SAVINGS_MATURITY": [
            "[{bank}] 적금 만기 예정 안내. 만기일은 {next_date}입니다.",
            "[{bank}] 예금 만기 후 자동 재예치 여부를 확인해 주세요.",
            "[{bank}] 만기 해지 가능 상품이 있습니다. 앱에서 처리 가능합니다.",
            "[{bank}] 만기 이자 예상 금액은 {small_amount}입니다.",
        ],
        "LOAN_REPAYMENT": [
            "[{bank}] 대출 상환일은 {next_date}입니다. 출금 계좌 잔액을 확인해 주세요.",
            "[{bank}] 원리금 상환이 완료되었습니다. 상세 내역은 앱에서 확인하세요.",
            "[{bank}] 대출 약정 변경 신청이 접수되었습니다.",
            "[{bank}] 중도상환 가능 금액 안내가 도착했습니다.",
        ],
        "BILLING_NOTICE": [
            "[{card}] 이번 달 청구 예정금액은 {large_amount}입니다.",
            "[{card}] 결제대금 결제일은 {next_date}입니다.",
            "[{insurance}] 보험료 납부 영수증이 발행되었습니다.",
            "[{bank}] {utility} 납부 내역이 등록되었습니다.",
        ],
    },
    2: {
        "SHOPPING_ORDER": [
            "[{shop}] 주문이 완료되었습니다.\n주문번호 {order}\n상품: {product}",
            "[{shop}] 결제 완료 {amount}\n배송 준비가 시작되었습니다.",
            "[{shop}] 주문 내역이 변경되었습니다. 앱에서 상세 내용을 확인해 주세요.",
            "[{shop}] 선물하기 주문이 접수되었습니다. 수신자 입력을 확인하세요.",
        ],
        "PAYMENT_COMPLETE": [
            "[{shop}] {product} 결제 완료\n금액 {amount}",
            "[{pay_app}] {shop} 결제가 정상 처리되었습니다.",
            "[{shop}] 무통장 입금 확인 완료. 상품 준비 중입니다.",
            "[{shop}] 예약 구매가 완료되었습니다. 출고 예정일 {next_date}",
        ],
        "COURIER_PICKUP": [
            "[{carrier}] 택배가 집하 처리되었습니다.\n운송장 {invoice}",
            "[{carrier}] 반품 회수 접수 완료. 방문 예정일 {next_date}",
            "[{carrier}] 편의점 택배 접수 완료. 배송조회는 잠시 후 가능합니다.",
            "[{carrier}] 택배 인수 완료. 배송 상태는 앱에서 확인 가능합니다.",
        ],
        "COURIER_OUT": [
            "[{carrier}] 고객님의 택배가 배송 출발했습니다.\n운송장 {invoice}",
            "[{carrier}] 금일 {time_slot} 전후 배송 예정입니다.",
            "[{carrier}] 배송기사 방문 예정. 부재 시 {pickup_place} 보관될 수 있습니다.",
            "[{carrier}] 배송 중입니다. 수령 장소: {pickup_place}",
        ],
        "DELIVERY_DONE": [
            "[{carrier}] 배송 완료\n{pickup_place}에 두었습니다. 이용해 주셔서 감사합니다.",
            "[{shop}] 주문하신 상품이 배송 완료되었습니다.",
            "[{carrier}] 수령 확인이 완료되었습니다. 문의 사항은 고객센터로 연락 바랍니다.",
            "[{shop}] 구매확정 전 상품 상태를 확인해 주세요.",
        ],
        "DELIVERY_DELAY": [
            "[{carrier}] 물량 증가로 배송이 지연되고 있습니다. 예상 도착일 {next_date}",
            "[{shop}] 일부 상품 입고 지연으로 배송 일정이 변경되었습니다.",
            "[{carrier}] 기상 악화로 배송이 지연될 수 있습니다.",
            "[{carrier}] 주소 확인 중으로 배송이 보류되었습니다. 고객센터 문의 바랍니다.",
        ],
        "RETURN_EXCHANGE": [
            "[{shop}] 교환 접수가 완료되었습니다. 회수 일정은 별도 안내드립니다.",
            "[{carrier}] 반품 상품 회수 예정입니다. 상품을 포장해 주세요.",
            "[{shop}] 환불이 접수되었습니다. 결제수단 반영까지 시간이 소요됩니다.",
            "[{shop}] 교환 상품이 출고되었습니다. 운송장 {invoice}",
        ],
        "FRESH_DELIVERY": [
            "[{shop}] 새벽배송이 시작되었습니다. 도착 전 알림을 보내드립니다.",
            "[{shop}] 냉장 상품이 {pickup_place}에 배송 완료되었습니다.",
            "[{shop}] 신선식품 품절로 일부 상품이 환불 처리됩니다.",
            "[{shop}] 오늘 도착 예정 상품이 포장 완료되었습니다.",
        ],
        "CUSTOMS_NORMAL": [
            "[관세청] 수입신고가 정상 처리되었습니다. 배송사 인계 예정입니다.",
            "[국제우편] 통관이 완료되어 국내 배송이 시작됩니다.",
            "[관세청] 개인통관고유부호 확인이 완료되었습니다.",
            "[해외배송] 통관 심사가 진행 중입니다. 추가 요청 시 별도 안내됩니다.",
        ],
        "CUSTOMS_SCAM": [
            "{header}[관세청] 해외배송 물품 통관 보류. 개인통관고유부호 확인 필요: {url}",
            "[국제배송] 수취인 정보 오류로 통관이 지연 중입니다. 정보 수정: {url}",
            "{header}수입신고 물품 관세 미납 안내. 납부 확인 후 배송 진행: {url}",
            "[해외직구] 세관 반송 예정. 오늘 안에 통관정보를 수정해 주세요: {url}",
        ],
        "ADDRESS_SCAM": [
            "{header}[{carrier}] 주소 일부 누락으로 배송 보류. 주소 재확인: {url}",
            "[택배알림] 수취인 연락처 오류로 배송 실패. 재배송 신청: {url}",
            "{header}배송지 확인이 필요합니다. 오늘 안에 확인하지 않으면 반송될 수 있습니다: {url}",
            "[{carrier}] 부재중 배송비 결제 후 재방문 신청 가능합니다: {url}",
        ],
        "MISSED_DELIVERY_SCAM": [
            "{header}부재중 택배 보관 중. 보관료 발생 전 수령 신청: {url}",
            "[택배센터] 미수령 상품 반송 예정. 수령지 변경: {url}",
            "[{carrier}] 배송 실패 2회. 최종 배송 일정 확인: {url}",
            "고객님의 택배가 지점에 보관 중입니다. 보관 위치 확인: {url}",
        ],
        "RESERVATION_TICKET": [
            "[KORAIL] 승차권 예매 완료\n{route}\n좌석 {seat}",
            "[CGV] 예매 완료\n영화: {movie}\n상영일 {next_date}\n좌석 {seat}",
            "[SRT] 열차 출발 안내. 승차권의 열차번호와 좌석을 다시 확인해 주세요.",
            "[공연예매] 티켓 예매가 완료되었습니다. 입장 전 모바일 티켓을 준비해 주세요.",
        ],
        "TRAVEL_CHECKIN": [
            "[{airline}] 모바일 체크인 안내\n편명 {flight}\n출발 3시간 전 공항 도착 권장",
            "[{airline}] 항공권 결제 완료\n노선 {route}\n예약번호 {order}",
            "[{airline}] 탑승구 변경 안내. 공항 전광판을 확인해 주세요.",
            "[숙박예약] 체크인 안내가 도착했습니다. 예약번호 {order}",
        ],
        "PICKUP_LOCKER": [
            "[{carrier}] 무인택배함에 보관되었습니다. 보관 위치를 확인해 주세요.",
            "[{carrier}] 픽업코드가 발급되었습니다. 코드로 상품을 수령하세요.",
            "[{carrier}] 편의점 택배 도착 안내. {deadline}까지 수령 가능합니다.",
            "[{shop}] 주문 상품이 수령 대기 상태입니다. 보관 장소: {pickup_place}",
        ],
        "MARKETPLACE_TRADE": [
            "[중고거래] 안전결제 요청이 접수되었습니다. 거래 내역을 확인해 주세요.",
            "[중고거래] 구매자가 입금 완료했습니다. 배송 준비 부탁드립니다.",
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
            "[정부24] 신청하신 {document} 발급이 완료되었습니다. 정부24 앱에서 확인 가능합니다.",
            "[정부24] 민원 신청이 접수되었습니다. 처리 결과는 문자로 안내됩니다.",
            "[정부24] 보완 요청이 있습니다. 신청 내역을 확인해 주세요.",
            "[정부24] 전자문서지갑에 새 문서가 도착했습니다.",
        ],
        "RESIDENT_SURVEY": [
            "[행정안전부] 주민등록 사실조사 참여 안내. 세대별 확인에 협조 부탁드립니다.",
            "[주민센터] 전입신고 처리 결과가 등록되었습니다.",
            "[행정복지센터] 민원 예약 시간이 {time_slot}로 확정되었습니다.",
            "[국민비서] 생활정보 알림이 도착했습니다. 자세한 내용은 국민비서에서 확인하세요.",
        ],
        "TAX_NOTICE": [
            "[국세청] {tax} 신고 안내. 신고기한 내 홈택스에서 확인 바랍니다.",
            "[국세청] 전자고지 신청이 완료되었습니다.",
            "[국세청] 신고 도움자료가 제공되었습니다. 홈택스에서 확인 가능합니다.",
            "[세무서] 납부기한이 도래했습니다. 기한 내 납부 바랍니다.",
        ],
        "TAX_REFUND": [
            "[국세청] 환급금 지급 예정 안내. 지급 계좌 등록 여부를 확인해 주세요.",
            "[국세청] {tax} 환급 검토가 완료되었습니다.",
            "[국세청] 환급금 지급일은 {next_date} 예정입니다.",
            "[홈택스] 환급 신청서가 접수되었습니다. 처리 결과를 기다려 주세요.",
        ],
        "LOCAL_TAX": [
            "[지방세] {tax} 납부기한이 도래했습니다. 위택스 또는 은행 앱에서 납부 가능합니다.",
            "[시청] {fine} 고지서가 발송되었습니다.",
            "[위택스] 전자납부번호가 등록되었습니다. 기한 내 납부 바랍니다.",
            "[구청] 지방세 자동납부 신청이 완료되었습니다.",
        ],
        "HEALTH_CHECKUP": [
            "[국민건강보험] 건강검진 대상자 안내. 검진기관 예약 후 방문 바랍니다.",
            "[건강보험공단] 보험료 고지서가 발송되었습니다. 납부기한을 확인 바랍니다.",
            "[국민건강보험] 자격 변동 내역이 있습니다. 공단 앱에서 확인해 주세요.",
            "[건강검진센터] 예약 시간이 {time_slot}로 확정되었습니다.",
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
            "{header}[경찰청] 사건번호 {case_no} 관련 출석요구서 확인: {url}",
            "[사이버수사대] 귀하 명의 계좌가 범죄에 연루되어 확인이 필요합니다: {url}",
            "{header}수사협조 요청. 미확인 시 불이익이 발생할 수 있습니다. 확인: {url}",
            "[경찰민원] 전자문서가 도착했습니다. 본인 인증 후 열람: {url}",
        ],
        "COURT_SCAM": [
            "{header}[법원] 등기 우편 반송으로 전자문서 송달 안내: {url}",
            "[대한민국법원] 지급명령 관련 문서가 도착했습니다. 열람: {url}",
            "{header}민사소송 통지서 확인 요청. 본인 인증 후 열람 가능합니다: {url}",
            "[법원행정처] 미열람 문서가 있습니다. 기한 내 확인: {url}",
        ],
        "SUBSIDY_SCAM": [
            "{header}[복지지원센터] {benefit} 대상자로 선정되었습니다. 신청: {url}",
            "[정부지원금] 미수령 환급금이 있습니다. 지급계좌 확인: {url}",
            "{header}소상공인 지원금 추가 접수 안내. 마감 전 신청: {url}",
            "[민생지원] 본인 부담금 없이 지원 신청 가능합니다: {url}",
        ],
        "FINE_SCAM": [
            "{header}[교통민원] {fine} 미납 내역 확인 및 납부: {url}",
            "[전자고지] 미납 과태료가 있습니다. 납부기한 전 확인: {url}",
            "[구청] 불법주정차 과태료 고지서 열람: {url}",
            "[민원24] 미처리 고지서가 있습니다. 본인 확인 후 열람: {url}",
        ],
        "CIVIL_DEFENSE": [
            "[민방위] 교육 일정 안내가 도착했습니다. 교육일은 {next_date}입니다.",
            "[민방위] 사이버 교육 이수 기한은 {deadline}입니다.",
            "[민방위] 전자통지서가 발송되었습니다. 교육 장소를 확인해 주세요.",
            "[민방위] 교육 이수 처리 결과가 등록되었습니다.",
        ],
        "DISASTER_ALERT": [
            "[재난문자] {location} 지역 안전 안내. 재난 단계는 {alert_level}입니다.",
            "[안전안내문자] 기상 악화로 외출 시 주의 바랍니다.",
            "[재난안전] 폭염 대비 행동요령을 확인해 주세요.",
            "[재난문자] 강풍 예보로 시설물 점검을 권고합니다.",
        ],
        "WELFARE_NOTICE": [
            "[복지로] 신청하신 복지 서비스 처리 결과가 등록되었습니다.",
            "[복지로] 자격 확인을 위한 추가 서류 제출이 필요합니다.",
            "[고용복지센터] 상담 일정은 {next_date} {time_slot}입니다.",
            "[복지알림] 지원금 지급 예정일은 {next_date}입니다.",
        ],
    },
    4: {
        "STORE_COUPON": [
            "{ad_header}[{brand}] 오늘만 사용 가능한 {percent}% 할인쿠폰이 도착했습니다.\n{url}",
            "{ad_header}장바구니 상품 재입고 안내. 지금 구매 시 {coupon} 적용 가능\n{url}",
            "{ad_header}첫 구매 고객 {benefit_text} 혜택 지급 완료. 확인: {url}",
            "[{brand}] 앱 전용 쿠폰이 발급되었습니다. 마이페이지에서 확인하세요.",
        ],
        "BRAND_SALE": [
            "{ad_header}[{brand}] 시즌오프 최대 {percent}% 할인 시작\n{url}",
            "{ad_header}단 하루 특가 공개. 인기상품 한정 수량 판매\n{url}",
            "{ad_header}멤버십 고객 전용 사전 세일 오픈\n{url}",
            "{ad_header}[{brand}] 신상품 출시 기념 특별 혜택 안내",
        ],
        "MEMBERSHIP_POINT": [
            "[{brand}] 고객님의 멤버십 포인트 {points}가 적립되었습니다.",
            "[{brand}] 등급 유지 조건까지 {amount} 남았습니다.",
            "[CJ ONE] 포인트 적립 완료. 앱에서 상세 내역을 확인하세요.",
            "[{brand}] 이번 달 멤버십 혜택이 업데이트되었습니다.",
        ],
        "POINT_EXPIRY": [
            "[{brand}] 고객님의 포인트 {points}가 곧 소멸됩니다.",
            "{ad_header}소멸 예정 포인트로 교환 가능한 쿠폰 확인: {url}",
            "[{brand}] 이번 달 말 소멸 포인트가 있습니다.",
            "{ad_header}포인트 사용처가 추가되었습니다. 자세히 보기: {url}",
        ],
        "EVENT_ENTRY": [
            "{ad_header}[{brand}] 구매 고객 대상 이벤트 응모가 완료되었습니다.",
            "{ad_header}리뷰 작성 시 {points} 지급 이벤트 진행 중\n{url}",
            "[{brand}] 출석체크 이벤트 참여가 완료되었습니다.",
            "{ad_header}친구 초대 이벤트 혜택을 확인해 보세요: {url}",
        ],
        "EVENT_WIN": [
            "{ad_header}이벤트 당첨 안내. 경품 수령을 위해 배송 정보를 입력해 주세요: {url}",
            "[{brand}] 리뷰 이벤트 당첨 축하드립니다. 쿠폰이 지급되었습니다.",
            "{ad_header}설문 참여 고객 추첨 결과 확인. 당첨 여부 조회: {url}",
            "[{brand}] 당첨 경품 발송 예정입니다. 주소 확인 부탁드립니다.",
        ],
        "PRICE_ALERT": [
            "[가격알림] 관심상품 가격이 {percent}% 하락했습니다. 지금 확인해 보세요.",
            "[쇼핑알림] 찜한 상품의 재고가 얼마 남지 않았습니다.",
            "[특가알림] 최근 본 상품이 오늘 한정가로 변경되었습니다.",
            "[{brand}] 관심 브랜드의 신상품이 입고되었습니다.",
        ],
        "RESTOCK": [
            "[{brand}] 품절 상품이 재입고되었습니다.",
            "[재입고알림] 요청하신 {product} 상품이 입고되었습니다.",
            "{ad_header}재입고 수량 한정 판매 중입니다. 확인: {url}",
            "[{brand}] 알림 신청 상품이 구매 가능 상태로 변경되었습니다.",
        ],
        "FOOD_DELIVERY_COUPON": [
            "{ad_header}[배달쿠폰] 오늘 {menu} 주문 시 {small_amount} 할인\n{url}",
            "[배달의민족] 바로 사용 가능한 쿠폰이 도착했습니다.",
            "{ad_header}우리동네 인기 가게 {percent}% 할인 중\n{url}",
            "[요기요] 포장 주문 할인 혜택이 적용 가능합니다.",
        ],
        "LOCAL_STORE": [
            "{ad_header}우리동네 신규 {local_store} 오픈 이벤트. 방문 고객 {benefit_text}\n{url}",
            "{ad_header}근처 매장에서 사용 가능한 쿠폰이 도착했습니다.\n{url}",
            "{ad_header}주말 예약 고객 할인 안내. 잔여 시간 확인: {url}",
            "[지역알림] {local_store} 예약 시간이 확정되었습니다.",
        ],
        "SUBSCRIPTION": [
            "[{subscription}] 정기결제 예정일은 {next_date}입니다.",
            "{ad_header}[{subscription}] 첫 달 무료 체험 혜택 안내\n{url}",
            "[{subscription}] 이용권이 곧 만료됩니다.",
            "{ad_header}프리미엄 전환 시 {percent}% 할인 혜택 제공\n{url}",
        ],
        "BEAUTY": [
            "{ad_header}[{brand}] 뷰티데이 최대 {percent}% 할인\n{url}",
            "[{brand}] 예약하신 피부 상담 시간이 {time_slot}입니다.",
            "{ad_header}오늘의 뷰티 특가 상품이 공개되었습니다.\n{url}",
            "[{brand}] 구매하신 화장품 리뷰 작성 시 포인트 지급",
        ],
        "TRAVEL_PROMO": [
            "{ad_header}[여행특가] {route} 항공권 특가 오픈\n{url}",
            "{ad_header}숙박 예약 고객 대상 쿠폰 지급\n{url}",
            "[여행알림] 관심 지역 숙소 가격이 하락했습니다.",
            "{ad_header}연휴 렌터카 예약 할인 마감 임박: {url}",
        ],
        "SURVEY_REWARD": [
            "{ad_header}설문 참여 시 {points} 지급. 참여하기: {url}",
            "[{brand}] 고객 만족도 조사 참여 부탁드립니다.",
            "{ad_header}1분 설문 완료 후 쿠폰 즉시 지급\n{url}",
            "[리서치] 참여하신 설문 보상이 지급되었습니다.",
        ],
        "APP_PUSH": [
            "[{brand}] 앱 푸시 수신 동의 고객 전용 혜택이 도착했습니다.",
            "{ad_header}[{brand}] 앱에서만 사용 가능한 {coupon} 지급\n{url}",
            "[{brand}] 앱 첫 접속 고객 대상 {benefit_text} 이벤트 진행 중입니다.",
            "{ad_header}{campaign} 기념 앱 전용 특가를 확인해 보세요.\n{url}",
        ],
        "SEASONAL_PROMO": [
            "{ad_header}[{brand}] 시즌 한정 {percent}% 할인 행사 시작\n{url}",
            "{ad_header}연휴 맞이 특가 상품이 공개되었습니다.\n{url}",
            "[{brand}] 월말 결산 세일이 진행 중입니다.",
            "{ad_header}주말 한정 쿠폰이 발급되었습니다. 사용기한 확인: {url}",
        ],
        "RESERVATION_PROMO": [
            "{ad_header}[{local_store}] 예약 고객 대상 추가 할인 안내\n{url}",
            "[{local_store}] 예약 확정 시 음료 쿠폰이 제공됩니다.",
            "{ad_header}예약 가능한 시간대가 열렸습니다. 빠르게 확인해 보세요.\n{url}",
            "[{local_store}] 재방문 고객 전용 예약 혜택이 적용 가능합니다.",
        ],
    },
    5: {
        "OTP_CODE": [
            "[{service}] 인증번호 [{code}]를 입력해 주세요. 타인에게 알려주지 마세요.",
            "[본인확인] 인증번호 {code} 입니다. 3분 이내 입력 바랍니다.",
            "[간편인증] 요청하신 인증번호는 {code}입니다.",
            "[{service}] 로그인 인증코드 {code8}입니다.",
        ],
        "SIMPLE_AUTH": [
            "[{service}] 간편인증 요청이 도착했습니다. 앱에서 승인해 주세요.",
            "[PASS] 본인확인 요청이 있습니다. 요청 기관을 확인 후 진행하세요.",
            "[{bank}] 공동인증서 인증 요청이 접수되었습니다.",
            "[{service}] QR 로그인 승인을 요청했습니다.",
        ],
        "LOGIN_ALERT": [
            "[{service}] 새로운 기기에서 로그인되었습니다.\n기기: {device}\nIP: {ip}",
            "[카카오톡] PC버전 로그인 알림. 본인이 아니면 즉시 비밀번호를 변경해 주세요.",
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
            "[{service}] 계정 복구 코드 [{code}]입니다. 요청하지 않았다면 무시하세요.",
            "[고객센터] 아이디 찾기 결과가 발송되었습니다.",
            "[{service}] 휴면 계정 해제 인증번호 {code}",
            "[{service}] 계정 복구 신청이 접수되었습니다.",
        ],
        "DEVICE_LINK": [
            "[카카오] 새 기기 연결 요청이 있습니다. 연결코드 {code}",
            "[{service}] 연결된 기기 목록이 변경되었습니다.",
            "[{service}] 기기 연결 해제가 완료되었습니다.",
            "[{service}] 앱 연동 승인 요청이 있습니다.",
        ],
        "PAYMENT_AUTH": [
            "[{pay_app}] 결제 인증번호 {code}입니다. 결제를 요청한 경우에만 입력하세요.",
            "[{card}] 온라인 결제 본인확인 요청이 있습니다.",
            "[{bank}] 이체 인증번호 {code}. 타인에게 알려주지 마세요.",
            "[{service}] 구매 인증이 요청되었습니다. 금액 {amount}",
        ],
        "CRYPTO_WITHDRAW": [
            "[Upbit] 출금 요청 인증번호 {code}입니다.",
            "[Upbit] 가상자산 출금 신청이 접수되었습니다. 본인이 아니면 즉시 문의하세요.",
            "[Bithumb] 새 지갑주소가 등록되었습니다.",
            "[{service}] 보안등급 변경 요청이 있습니다.",
        ],
        "GAME_OTP": [
            "[NEXON] OTP 인증번호 [{code8}]를 입력해 주세요.",
            "[Steam] 새 기기 로그인 코드 {code}입니다.",
            "[게임보안] 해외 IP 접속 시도가 차단되었습니다. IP {ip}",
            "[{service}] 계정 보호를 위해 비밀번호 변경을 권장합니다.",
        ],
        "CLOUD_SECURITY": [
            "[Microsoft] 계정 보안 정보가 업데이트되었습니다.",
            "[Google] 드라이브 공유 설정이 변경되었습니다.",
            "[iCloud] 저장공간 결제 인증이 필요합니다.",
            "[{service}] 클라우드 백업이 완료되었습니다.",
        ],
        "EMAIL_CHANGE": [
            "[{service}] 로그인 이메일이 변경되었습니다.",
            "[{service}] 복구 전화번호가 010-****-{phone_suffix}로 변경되었습니다.",
            "[{service}] 알림 수신 이메일이 추가되었습니다.",
            "[{service}] 계정 정보 변경 확인 메일이 발송되었습니다.",
        ],
        "SECURITY_SCAM": [
            "{header}[{service}] 계정이 임시 제한되었습니다. 본인확인: {url}",
            "{header}비정상 로그인으로 보안 점검이 필요합니다. 즉시 확인: {url}",
            "[보안센터] 인증 만료 예정. 서비스 이용 제한 전 갱신하세요: {url}",
            "[{service}] 계정 보호조치 해제를 위해 인증을 완료해 주세요: {url}",
        ],
        "VERIFICATION_EXPIRE_SCAM": [
            "{header}[본인인증] 인증 유효기간이 만료됩니다. 재인증: {url}",
            "[{service}] 장기 미접속 계정 삭제 예정. 유지 신청: {url}",
            "{header}보안약관 변경으로 재동의가 필요합니다: {url}",
            "[인증센터] 미완료 인증 요청이 있습니다. 확인: {url}",
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
            "[{dept}] 금일 회의 시간이 {time_slot}로 변경되었습니다.",
            "{employee} {rank}님, {project} 관련해서 10분만 미팅 가능하실까요?",
            "내일 오전 회의 자료는 {tool}에 업로드 부탁드립니다.",
            "[회의알림] {meeting_room} 예약이 확정되었습니다.",
        ],
        "HR_EDUCATION": [
            "[인사팀] 법정의무교육 수강 기한이 {deadline}까지입니다.",
            "[인사팀] 신규 입사자 교육 일정이 확정되었습니다.",
            "[교육알림] 개인정보보호 교육 미수강자 확인 바랍니다.",
            "[인사팀] 교육 이수증 제출 부탁드립니다.",
        ],
        "HR_ATTENDANCE": [
            "[인사팀] 연차 사용 계획 제출 요청드립니다. {deadline}까지 회신 부탁드립니다.",
            "[근태알림] 금일 지각 처리 내역이 있습니다. 확인 바랍니다.",
            "[총무팀] 출장 신청서가 접수되었습니다.",
            "[인사팀] 재택근무 신청 결과가 승인되었습니다.",
        ],
        "PAYROLL": [
            "[급여] {date} 급여명세서가 등록되었습니다.",
            "[인사팀] 원천징수영수증 발급 신청이 완료되었습니다.",
            "[급여] 계좌 변경 신청이 접수되었습니다.",
            "[재무팀] 경비 지급 예정일은 {next_date}입니다.",
        ],
        "IT_MAINTENANCE": [
            "[IT지원팀] 사내 VPN 점검 예정입니다. 작업 시간 중 접속이 불안정할 수 있습니다.",
            "[IT지원팀] PC 보안 프로그램 업데이트를 오늘 퇴근 전 진행해 주세요.",
            "[IT공지] {tool} 점검으로 {time_slot}부터 일부 기능이 제한됩니다.",
            "[IT지원팀] 비밀번호 변경 주기가 도래했습니다.",
        ],
        "SECURITY_NOTICE": [
            "[보안] 외부 메일 첨부파일 실행 주의 안내드립니다.",
            "[보안팀] 의심 메일 신고 훈련이 진행됩니다.",
            "[보안] 사내망 접속 기록 점검 예정입니다.",
            "[보안팀] 개인정보 파일 암호화 여부를 확인해 주세요.",
        ],
        "APPROVAL": [
            "{employee} {rank}님, {doc} 결재 요청 올렸습니다. 확인 부탁드립니다.",
            "[전자결재] 신규 결재 문서가 도착했습니다. 제목: {project}",
            "[{tool}] 결재 반려 문서가 있습니다. 수정 후 재상신 부탁드립니다.",
            "[전자결재] 승인 대기 문서가 {share_count}건 있습니다.",
        ],
        "EXPENSE": [
            "[재무팀] 법인카드 영수증 제출 기한은 {deadline}입니다.",
            "{employee}님, {amount} 경비 정산 내역 확인 부탁드립니다.",
            "[재무팀] 세금계산서 발행 요청이 접수되었습니다.",
            "[경비정산] 증빙 누락 건이 있습니다. 보완 바랍니다.",
        ],
        "PROJECT_UPDATE": [
            "{project} 일정표 최신본 공유했습니다. 변경 사항 확인 부탁드립니다.",
            "클라이언트 피드백 반영본을 메일로 전달했습니다.",
            "이번 주 업무 진행률 업데이트 부탁드립니다. 누락 항목은 오늘 안에 정리해 주세요.",
            "[{tool}] {project} 티켓 상태가 변경되었습니다.",
        ],
        "CLIENT_MEETING": [
            "{client} 미팅 시간이 {time_slot}로 확정되었습니다.",
            "{client} 전달용 제안서 최종본 확인 부탁드립니다.",
            "{manager}님, {client} 회의록 공유드립니다.",
            "[영업팀] 고객사 방문 일정이 {next_date}로 변경되었습니다.",
        ],
        "DOCUMENT_SHARE": [
            "{doc} 파일을 {tool}에 공유했습니다. 권한 확인 부탁드립니다.",
            "공유드라이브에 최신 {doc} 업로드했습니다.",
            "[{tool}] {employee}님이 문서를 공유했습니다.",
            "{doc} 수정본 확인 후 코멘트 남겨주세요.",
        ],
        "CONTRACT_REVIEW": [
            "[법무팀] {client} 계약서 검토 의견을 전달드립니다.",
            "계약서 검토본 반영했습니다. 법무팀 확인 후 재상신하겠습니다.",
            "[법무팀] 날인본 수령 후 스캔본 업로드 부탁드립니다.",
            "{client} 계약 일정이 변경되었습니다. 담당자 확인 바랍니다.",
        ],
        "URGENT_WORK_SCAM": [
            "{header}대표님 지시사항입니다. 긴급 송금 승인 필요하니 보안문서 확인: {url}",
            "{header}급여명세서 오류 정정 안내. 본인확인 후 재발급: {url}",
            "[사내공지] 임직원 개인정보 최신화 요청. 미제출 시 시스템 이용 제한: {url}",
            "{header}{manager} 요청입니다. 외부 공유 문서 확인 후 회신 바랍니다: {url}",
        ],
        "HR_SCAM": [
            "{header}[인사팀] 퇴직연금 정보 변경 요청. 본인 확인: {url}",
            "[급여] 계좌 오류로 지급 보류. 재확인 필요: {url}",
            "{header}[복리후생] 임직원 지원금 신청 대상 확인: {url}",
            "[사내복지] 미사용 포인트 소멸 예정. 신청서 확인: {url}",
        ],
        "FACILITY_NOTICE": [
            "[총무팀] {office_notice} 관련 안내가 등록되었습니다.",
            "[총무팀] {meeting_room} 사용 가능 시간이 변경되었습니다.",
            "[사내안내] 냉난방 점검으로 일부 구역 사용이 제한됩니다.",
            "[시설공지] 출입 시스템 점검은 {next_date} {time_slot} 예정입니다.",
        ],
        "ASSET_RETURN": [
            "[총무팀] 퇴실 전 {asset} 반납 여부를 확인해 주세요.",
            "[자산관리] 대여 중인 {asset} 반납 예정일은 {next_date}입니다.",
            "[IT지원팀] 교체 대상 장비는 {asset}입니다. 회수 일정 안내 예정입니다.",
            "[자산관리] 반납 확인 후 인수증이 발급됩니다.",
        ],
        "TEAM_EVENT": [
            "[{dept}] 팀 점심 일정이 {next_date} {time_slot}로 확정되었습니다.",
            "[{dept}] 워크숍 참석 여부를 {deadline}까지 회신 부탁드립니다.",
            "[사내행사] 분기 타운홀 미팅 장소는 {meeting_room}입니다.",
            "[{dept}] 송년회 참석 인원 확인 중입니다. 가능 여부만 답장 부탁드립니다.",
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


def render_expanded_template(category_idx, sub_cat):
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
    values = expanded_values(category_idx, sub_cat, url)
    values.update({
        "header": maybe_header("web"),
        "ad_header": maybe_header("ad"),
        "name2": random.choice(["서연", "지아", "유진", "하린", "수빈", "민지"]),
        "random_day": random.randint(1, 28),
        "usd": f"{random.randint(5, 900)}.{random.randint(10, 99)}",
        "overseas_store": random.choice(["AMAZON", "PAYPAL", "AGODA", "APPLE", "GOOGLE", "AIRBNB"]),
        "country": random.choice(["US", "JP", "CN", "VN", "TH", "KR"]),
        "rate": random.randint(3, 9),
        "share_count": random.randint(1, 30),
    })
    template = random.choice(EXPANDED_SCENARIO_TEMPLATES[category_idx][sub_cat])
    text = template.format_map(SafeFormatDict(values))
    text = apply_expanded_noise(text, category_idx)
    return text, url if url in text else "N/A", sub_cat


def generate_dynamic_text(category_idx):
    if category_idx not in EXPANDED_SCENARIO_TEMPLATES:
        return gen_personal_professional("DAILY_FAMILY")
    sub_cat = pick_expanded_subcategory(category_idx)
    return render_expanded_template(category_idx, sub_cat)


# 메인 데이터셋 생성 루프
TOTAL_COUNT = int(os.getenv("TOTAL_COUNT", "10000"))
metadata = []
available_bgs = [f for f in os.listdir(BG_DIR) if f in bg_configs]
if not available_bgs:
    raise FileNotFoundError("backgrounds 폴더에 이미지가 없습니다.")

num_categories = len(CATEGORIES)
SAMPLES_PER_CATEGORY = TOTAL_COUNT // num_categories

print(f"총 {TOTAL_COUNT}개의 데이터 생성을 시작합니다. (카테고리당 {SAMPLES_PER_CATEGORY}개)")

category_counters = {category_name: 0 for category_name in CATEGORIES.values()}
category_indices = []
for cat_idx in range(num_categories):
    for sample_idx in range(SAMPLES_PER_CATEGORY):
        category_indices.append(cat_idx)

while len(category_indices) < TOTAL_COUNT:
    category_indices.append(random.randint(0, num_categories - 1))

random.shuffle(category_indices)
print(f"✅ 데이터 순서 섞음 완료\n")

for i in range(TOTAL_COUNT):
    label_int = category_indices[i]

    text, target_url, sub_cat = generate_dynamic_text(label_int)

    bg_file = random.choice(available_bgs)
    start_x, start_y, max_width = bg_configs[bg_file]

    img = Image.open(os.path.join(BG_DIR, bg_file)).convert("RGB")
    draw = ImageDraw.Draw(img)

    f_size = random.randint(24, 31)
    font = ImageFont.truetype(random.choice(font_paths), f_size)
    line_spacing = f_size + random.randint(7, 11)

    lines = get_wrapped_text(text, font, max_width)
    y = start_y

    text_color = (random.randint(10, 40), random.randint(10, 40), random.randint(10, 40))

    for line in lines:
        draw.text((start_x, y), line, fill=text_color, font=font)
        y += line_spacing

    qr_applied = False
    if target_url != "N/A" and random.random() < 0.4:
        safe_y = min(y + 20, img.height - 150)
        img.paste(create_qr_code(target_url), (start_x, safe_y))
        qr_applied = True

    category_name = CATEGORIES[label_int]
    category_counters[category_name] += 1
    file_name = f"{category_name}_{category_counters[category_name]:04d}.png"
    img.save(os.path.join(OUTPUT_DIR, file_name))

    metadata.append({
        "file_name": file_name,
        "label_idx": label_int,
        "category": category_name,
        "sub_category": sub_cat,
        "has_qr": qr_applied,
        "url": target_url,
        "text": text.replace('\n', ' ')
    })

    if (i+1) % 100 == 0:
        print(f"{i+1}/{TOTAL_COUNT} 생성 완료 ({(i+1)/TOTAL_COUNT*100:.1f}%)")

df = pd.DataFrame(metadata)
column_order = [
    "file_name", "label_idx", "category",
    "sub_category", "has_qr", "url", "text"
]
df = df[column_order]

csv_path = os.path.join(OUTPUT_DIR, "metadata.csv")
df.to_csv(csv_path, index=False, encoding='utf-8-sig')

print(f"\n✅ 생성 완료!")
print(f"📂 이미지: {OUTPUT_DIR} (총 {TOTAL_COUNT}개)")
print(f"📋 메타데이터: {csv_path}")
print(f"📊 카테고리 분포:")
for cat, count in df['category'].value_counts().sort_index().items():
    print(f"   - {cat}: {count}개")
