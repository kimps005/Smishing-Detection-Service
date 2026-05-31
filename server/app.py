import streamlit as st

st.set_page_config(
    page_title="스미싱/큐싱 탐지 시스템",
    page_icon="🛡️",
    layout="wide",
)

st.markdown("""
<style>
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');

*, *::before, *::after { font-family: 'Pretendard', -apple-system, sans-serif !important; }

/* ── 배경 ── */
.stApp { background: #f8fafc; }

/* ── Streamlit 기본 UI 제거 ── */
header[data-testid="stHeader"],
[data-testid="stToolbar"],
[data-testid="stDeployButton"],
[data-testid="collapsedControl"],
[data-testid="stSidebarCollapseButton"],
section[data-testid="stSidebar"] > div > div > div > button { display: none !important; }

.main .block-container {
    padding-top: 2rem !important;
    padding-bottom: 3rem !important;
}

/* ── 사이드바 ── */
section[data-testid="stSidebar"] {
    background: white !important;
    border-right: 1px solid #e2e8f0 !important;
    box-shadow: 2px 0 12px rgba(0,0,0,0.04) !important;
}
section[data-testid="stSidebar"] > div {
    padding-top: 0 !important;
    background: white !important;
}

/* 사이드바 내부 배경 전파 방지 */
section[data-testid="stSidebar"] .stMarkdown,
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] {
    background: transparent !important;
}

/* nav 링크 */
[data-testid="stSidebarNavLink"] {
    border-radius: 8px !important;
    color: #475569 !important;
    font-size: 14px !important;
    font-weight: 500 !important;
    padding: 10px 14px !important;
    transition: background 0.15s, color 0.15s !important;
}
[data-testid="stSidebarNavLink"]:hover {
    background: #f1f5f9 !important;
    color: #1e293b !important;
}
[data-testid="stSidebarNavLink"][aria-current="page"] {
    background: #eff6ff !important;
    color: #2563eb !important;
    font-weight: 700 !important;
}

/* ── 버튼 ── */
.stButton > button {
    border-radius: 10px !important;
    font-size: 14px !important;
    font-weight: 600 !important;
    transition: all 0.18s ease !important;
}
.stButton > button[kind="primary"] {
    background: #2563eb !important;
    border: none !important;
    box-shadow: 0 2px 8px rgba(37,99,235,0.25) !important;
}
.stButton > button[kind="primary"]:hover {
    background: #1d4ed8 !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 14px rgba(37,99,235,0.35) !important;
}
.stButton > button[kind="secondary"] {
    background: white !important;
    border: 1.5px solid #e2e8f0 !important;
    color: #374151 !important;
}
.stButton > button[kind="secondary"]:hover {
    border-color: #2563eb !important;
    color: #2563eb !important;
    background: #eff6ff !important;
}

/* ── 탭 ── */
[data-testid="stTabs"] [data-baseweb="tab-list"] {
    background: #f1f5f9 !important;
    border-radius: 10px !important;
    padding: 4px !important;
    gap: 2px !important;
    border-bottom: none !important;
}
[data-testid="stTabs"] [data-baseweb="tab"] {
    background: transparent !important;
    border-radius: 8px !important;
    border: none !important;
    font-size: 13.5px !important;
    font-weight: 600 !important;
    color: #64748b !important;
    padding: 8px 20px !important;
    transition: all 0.15s !important;
}
[data-testid="stTabs"] [aria-selected="true"] {
    background: white !important;
    color: #1e293b !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.08) !important;
}

/* ── 파일 업로더 ── */
div[data-testid="stFileUploader"] {
    border: 2px dashed #cbd5e1 !important;
    border-radius: 14px !important;
    background: #f8fafc !important;
    transition: border-color 0.2s !important;
}
div[data-testid="stFileUploader"]:hover {
    border-color: #2563eb !important;
}

/* ── textarea / input ── */
textarea, input[type="text"] {
    border-radius: 10px !important;
    border: 1.5px solid #e2e8f0 !important;
    font-size: 14px !important;
    transition: border-color 0.2s, box-shadow 0.2s !important;
}
textarea:focus, input[type="text"]:focus {
    border-color: #2563eb !important;
    box-shadow: 0 0 0 3px rgba(37,99,235,0.1) !important;
}

/* ── 타이포그래피 ── */
.stMarkdown h2 { font-size: 1.5rem !important; font-weight: 800 !important; color: #0f172a !important; }
.stMarkdown h3 { font-size: 1.05rem !important; font-weight: 700 !important; color: #334155 !important; }
.stMarkdown p, .stMarkdown li,
[data-testid="stText"], label, .stCaption { font-size: 14px !important; }

/* ── 구분선 ── */
hr { border-color: #e2e8f0 !important; margin: 1.2rem 0 !important; }

/* ── 컨테이너 border ── */
[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 14px !important;
    border-color: #e2e8f0 !important;
}
</style>
""", unsafe_allow_html=True)

pg = st.navigation([
    st.Page("pages/home.py",     title="홈",    icon="🏠", default=True),
    st.Page("pages/analysis.py", title="분석",  icon="🔍"),
    st.Page("pages/feedback.py", title="피드백", icon="💬"),
])

with st.sidebar:
    st.markdown("""
    <div style='padding:1.4rem 1rem 1.2rem; border-bottom:1px solid #f1f5f9; margin-bottom:6px;'>
        <div style='font-size:16px; font-weight:800; color:#0f172a; letter-spacing:-0.3px;'>🛡️ CatchSmishing</div>
        <div style='font-size:11px; color:#94a3b8; margin-top:3px; font-weight:400;'>AI 스미싱 탐지 서비스</div>
    </div>
    """, unsafe_allow_html=True)

pg.run()
