import streamlit as st

CATEGORY_COLORS = {
    "FINANCE":    "#dc2626",
    "DELIVERY":   "#f59e0b",
    "GOVERNMENT": "#7c3aed",
    "PROMOTION":  "#0891b2",
    "AUTH":       "#ea580c",
    "WORK":       "#2563eb",
}

SMISHING_TYPES = [
    {
        "cat": "DELIVERY",
        "icon": "📦",
        "title": "배송 사기",
        "desc": "택배 미수령·주소 오류를 빙자해 개인정보 또는 소액 결제를 유도합니다.",
        "example": "[CJ대한통운] 주소지 불일치로 배송이 보류되었습니다. 확인 → bit.ly/...",
    },
    {
        "cat": "FINANCE",
        "icon": "💳",
        "title": "금융 사기",
        "desc": "은행·카드사를 사칭해 계좌 인증, 미승인 거래 확인을 명목으로 접속을 유도합니다.",
        "example": "[신한카드] 비정상 거래가 감지되었습니다. 본인 확인 → http://...",
    },
    {
        "cat": "GOVERNMENT",
        "icon": "🏛️",
        "title": "공공기관 사칭",
        "desc": "경찰청·검찰·건강보험공단 등을 사칭해 과태료·소환 통보로 링크를 클릭하게 합니다.",
        "example": "[교통민원24] 미납 과태료가 있습니다. 납부 기한 내 처리 → http://...",
    },
    {
        "cat": "AUTH",
        "icon": "🔐",
        "title": "계정 탈취",
        "desc": "포털·SNS 계정 해킹·정지를 빙자해 비밀번호를 탈취합니다.",
        "example": "[카카오] 비정상 로그인이 감지되었습니다. 재인증 필요 → http://...",
    },
    {
        "cat": "PROMOTION",
        "icon": "📈",
        "title": "투자·홍보 유도",
        "desc": "고수익 투자 리딩방, 공모주 당첨 등을 미끼로 개인정보나 투자금을 탈취합니다.",
        "example": "[주식알림] 금일 공모주 청약 마감! 지금 확인하세요 → http://...",
    },
    {
        "cat": "WORK",
        "icon": "👤",
        "title": "지인 사칭",
        "desc": "지인·가족을 사칭해 청첩장·부고를 보내며 APK 설치나 송금을 유도합니다.",
        "example": "엄마, 저 폰 고장났어. 이 링크에서 청첩장 확인해줘 → http://...",
    },
]

# ── 히어로 배너 ──────────────────────────────────────────────
st.markdown("""
<div style='background:white; border:1px solid #e2e8f0; border-radius:20px;
     padding:2.5rem 3rem; margin-bottom:1.4rem; position:relative; overflow:hidden;
     box-shadow:0 1px 6px rgba(0,0,0,0.05);'>
    <div style='position:absolute; right:-80px; top:-80px; width:340px; height:340px;
         background:radial-gradient(circle, #dbeafe 0%, #ede9fe 55%, transparent 75%);
         opacity:0.55; pointer-events:none;'></div>
    <div style='position:absolute; right:60px; bottom:-30px; width:160px; height:160px;
         background:radial-gradient(circle, #bfdbfe 0%, transparent 70%);
         opacity:0.4; pointer-events:none;'></div>
    <div style='position:relative; z-index:1;'>
        <div style='display:inline-block; background:#eff6ff; color:#2563eb;
             font-size:11.5px; font-weight:700; letter-spacing:0.8px; text-transform:uppercase;
             padding:5px 14px; border-radius:20px; margin-bottom:1.2rem;
             border:1px solid #bfdbfe;'>
            AI POWERED · KISA 기반
        </div>
        <div style='font-size:2.3rem; font-weight:800; color:#0f172a; line-height:1.2; margin-bottom:0.9rem;'>
            🛡️ 스미싱/큐싱<br>탐지 시스템
        </div>
        <div style='font-size:0.93rem; color:#64748b; line-height:1.8; max-width:480px;'>
            이미지·텍스트·QR 코드를 AI로 즉시 분석합니다.<br>
            Gemini Vision + NLP + URL 보안 분석 통합 엔진
        </div>
        <div style='font-size:12px; color:#94a3b8; margin-top:1.1rem;'>↓ 아래 버튼으로 바로 시작하세요</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ── CTA 버튼 ────────────────────────────────────────────────
col_a, col_b = st.columns(2, gap="medium")
with col_a:
    if st.button("🔍  문자 분석하기", use_container_width=True, type="primary"):
        st.switch_page("pages/analysis.py")
with col_b:
    if st.button("💬  피드백 / 탐지 현황", use_container_width=True):
        st.switch_page("pages/feedback.py")

# ── 통계 카드 ────────────────────────────────────────────────
st.markdown("<div style='margin-top:1.2rem;'></div>", unsafe_allow_html=True)
s1, s2, s3 = st.columns(3, gap="medium")
for col, val, label, color in [
    (s1, "96%", "카테고리 분류 정확도", "#2563eb"),
    (s2, "3종",  "AI 분석 엔진 통합",   "#6366f1"),
    (s3, "6종",  "스미싱 유형 탐지",    "#dc2626"),
]:
    with col:
        st.markdown(f"""
        <div style='background:white; border:1px solid #e2e8f0; border-radius:14px;
             padding:1.2rem 1rem; text-align:center;
             box-shadow:0 1px 4px rgba(0,0,0,0.04);'>
            <div style='font-size:2rem; font-weight:800; color:{color}; line-height:1;'>{val}</div>
            <div style='font-size:12px; color:#64748b; margin-top:6px; font-weight:500;'>{label}</div>
        </div>
        """, unsafe_allow_html=True)

# ── 스미싱 유형 섹션 제목 ────────────────────────────────────
st.markdown("""
<div style='display:flex; align-items:center; gap:10px; margin:1.8rem 0 1rem;'>
    <div style='width:4px; height:18px; background:#2563eb; border-radius:2px; flex-shrink:0;'></div>
    <span style='font-size:15px; font-weight:700; color:#0f172a;'>요즘 유행하는 스미싱 유형</span>
    <span style='font-size:12px; color:#94a3b8;'>KISA 2024 통계 기반</span>
</div>
""", unsafe_allow_html=True)

# ── 스미싱 유형 3열 카드 ─────────────────────────────────────
cols = st.columns(3, gap="medium")
for i, item in enumerate(SMISHING_TYPES):
    color = CATEGORY_COLORS.get(item["cat"], "#64748b")
    with cols[i % 3]:
        st.markdown(f"""
        <div style='background:white; border:1px solid #e2e8f0;
             border-top:3px solid {color}; border-radius:0 0 14px 14px;
             padding:1.2rem 1.2rem 1.1rem;
             box-shadow:0 1px 4px rgba(0,0,0,0.05); margin-bottom:10px;'>
            <div style='display:flex; align-items:center; gap:8px; margin-bottom:8px;'>
                <span style='font-size:1.25rem;'>{item['icon']}</span>
                <span style='font-size:14px; font-weight:700; color:#1e293b;'>{item['title']}</span>
            </div>
            <div style='font-size:12.5px; color:#64748b; line-height:1.65; margin-bottom:10px;'>{item['desc']}</div>
            <div style='background:#f8fafc; border-left:3px solid {color}55;
                 border-radius:0 8px 8px 0; padding:7px 10px;
                 font-size:11.5px; color:#94a3b8; font-style:italic; line-height:1.5;'>
                {item['example']}
            </div>
        </div>
        """, unsafe_allow_html=True)

# ── 예방 수칙 섹션 제목 ──────────────────────────────────────
st.markdown("""
<div style='display:flex; align-items:center; gap:10px; margin:0.8rem 0 1rem;'>
    <div style='width:4px; height:18px; background:#6366f1; border-radius:2px; flex-shrink:0;'></div>
    <span style='font-size:15px; font-weight:700; color:#0f172a;'>스미싱 피해 예방 수칙</span>
</div>
""", unsafe_allow_html=True)

tips = [
    ("🚫", "출처 불명 링크 클릭 금지",  "문자·SNS의 단축 URL은 클릭 전 이 서비스로 반드시 확인하세요."),
    ("🏦", "공식 앱/웹사이트 직접 접속", "택배·은행·정부기관은 공식 앱이나 검색을 통해 직접 접속하세요."),
    ("🔒", "개인정보·비밀번호 입력 주의", "문자 링크를 통한 개인정보 입력 요구는 100% 의심하세요."),
    ("📞", "의심 문자 신고",              "KISA 불법스팸대응센터 118 또는 문자 전달로 신고 가능합니다."),
]
t1, t2 = st.columns(2, gap="medium")
for i, (icon, title, desc) in enumerate(tips):
    with (t1 if i % 2 == 0 else t2):
        st.markdown(f"""
        <div style='display:flex; gap:12px; background:white; border:1px solid #e2e8f0;
             border-radius:12px; padding:1rem 1.1rem; margin-bottom:8px;
             box-shadow:0 1px 3px rgba(0,0,0,0.04);'>
            <div style='background:#eff6ff; border-radius:10px; padding:8px 10px;
                 font-size:1.1rem; flex-shrink:0; align-self:flex-start;'>{icon}</div>
            <div>
                <div style='font-size:13.5px; font-weight:700; color:#1e293b; margin-bottom:3px;'>{title}</div>
                <div style='font-size:12.5px; color:#64748b; line-height:1.6;'>{desc}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

# ── 하단 신고 안내 ───────────────────────────────────────────
st.markdown("""
<div style='background:#eff6ff; border:1px solid #bfdbfe; border-radius:12px;
     padding:1rem 1.5rem; text-align:center; font-size:13px; color:#1d4ed8;
     margin-top:0.5rem;'>
    📞 피해 발생 시: <strong>KISA 불법스팸대응센터 118</strong>
    &nbsp;|&nbsp; 경찰청 사이버수사국 <strong>182</strong>
</div>
""", unsafe_allow_html=True)
