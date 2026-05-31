import streamlit as st
import requests
import re
from collections import defaultdict

API_URL = "http://127.0.0.1:8000"

def extract_domain(url: str) -> str:
    url = re.sub(r'^https?://', '', url)
    return url.split('/')[0].split('?')[0].lower()

CATEGORY_NAMES = {
    "PERSONAL":   "일반 문자",
    "FINANCE":    "금융 사기",
    "DELIVERY":   "배송 사기",
    "GOVERNMENT": "공공기관 사칭",
    "PROMOTION":  "홍보/투자 유도",
    "AUTH":       "계정 탈취",
    "WORK":       "지인 사칭",
}
CATEGORY_COLORS = {
    "PERSONAL":   "#64748b",
    "FINANCE":    "#dc2626",
    "DELIVERY":   "#f59e0b",
    "GOVERNMENT": "#7c3aed",
    "PROMOTION":  "#0891b2",
    "AUTH":       "#ea580c",
    "WORK":       "#2563eb",
}

st.markdown("<h2 style='font-weight:800; color:#18181b;'>📋 위험 문자 탐지 순위</h2>", unsafe_allow_html=True)
st.caption("위험으로 판정된 URL의 누적 탐지 현황입니다. 의심되는 URL을 검색해 신고 이력을 확인하세요.")

if "ranking_data" not in st.session_state:
    try:
        resp = requests.get(f"{API_URL}/top-urls?limit=50", timeout=5)
        st.session_state.ranking_data = resp.json().get("top_urls", [])
    except Exception:
        st.session_state.ranking_data = None

data = st.session_state.ranking_data

st.markdown("---")

# 검색 + 카테고리 필터
if "filter_clear_count" not in st.session_state:
    st.session_state.filter_clear_count = 0

col1, col2, col3 = st.columns([1.1, 3, 0.7])
with col1:
    selected_category = st.selectbox(
        "카테고리",
        options=[k for k in CATEGORY_NAMES.keys() if k != "PERSONAL"],
        format_func=lambda x: CATEGORY_NAMES.get(x, x),
        index=None,
        placeholder="카테고리 선택",
        key=f"category_{st.session_state.filter_clear_count}",
        label_visibility="collapsed"
    )
with col2:
    search_query = st.text_input("URL 검색", placeholder="🔍  예: amazon, trust4, .top",
                                  key=f"search_query_{st.session_state.filter_clear_count}",
                                  label_visibility="collapsed")
with col3:
    if st.button("새로고침", use_container_width=True):
        st.session_state.filter_clear_count += 1
        st.rerun()

if data is None:
    st.error("서버에 연결할 수 없습니다.")
elif len(data) == 0:
    st.markdown("""
    <div style='text-align:center; padding:4rem; color:#94a3b8;'>
        <div style='font-size:4rem;'>🛡️</div>
        <p style='font-size:1.1rem; font-weight:bold; margin-top:1rem;'>탐지된 위험 문자가 없습니다</p>
        <p style='font-size:0.9rem;'>위험으로 판단된 문자가 누적되면 여기에 표시됩니다.</p>
    </div>
    """, unsafe_allow_html=True)
else:
    # 카테고리 분포
    cat_totals = defaultdict(int)
    for item in data:
        cat = item.get('category', '')
        cat_totals[cat] += item.get('count', 0)
    total_count = sum(cat_totals.values())

    if total_count > 0:
        sorted_cats = sorted(cat_totals.items(), key=lambda x: x[1], reverse=True)
        bars_html = ""
        for cat, cnt in sorted_cats:
            if cnt == 0 or cat == 'PERSONAL':
                continue
            pct = cnt / total_count * 100
            color = CATEGORY_COLORS.get(cat, "#64748b")
            name = CATEGORY_NAMES.get(cat, cat)
            bars_html += f"""
            <div style='display:flex; align-items:center; gap:10px; margin-bottom:6px;'>
                <div style='width:90px; font-size:12px; color:#374151; text-align:right; flex-shrink:0;'>{name}</div>
                <div style='flex:1; background:#f1f5f9; border-radius:4px; height:12px;'>
                    <div style='width:{pct:.1f}%; background:{color}; border-radius:4px; height:12px;'></div>
                </div>
                <div style='width:40px; font-size:12px; color:#64748b; flex-shrink:0; text-align:right;'>{pct:.0f}%</div>
            </div>
            """
        if bars_html:
            st.markdown(f"""
            <div style='background:white; border:1px solid #e2e8f0; border-radius:12px;
                 padding:1rem 1.25rem; margin-bottom:1rem;'>
                <div style='font-size:13px; color:#64748b; font-weight:600; margin-bottom:10px;'>탐지된 스미싱 유형 분포</div>
                {bars_html}
            </div>
            """, unsafe_allow_html=True)

    # 필터링
    filtered = data
    if search_query.strip():
        filtered = [item for item in filtered if search_query.strip().lower() in item.get("url", "").lower()]
    if selected_category:
        filtered = [item for item in filtered if item.get("category") == selected_category]

    if not filtered:
        st.markdown("<div style='text-align:center; padding:2rem; color:#94a3b8;'>검색 결과가 없습니다.</div>", unsafe_allow_html=True)

    MEDALS = ["🥇", "🥈", "🥉"]

    for i, item in enumerate(filtered):
        rank    = i + 1
        url     = item.get("url", "")
        category = item.get("category", "")
        count   = item.get("count", 0)
        color   = CATEGORY_COLORS.get(category, "#dc2626")
        cat_name = CATEGORY_NAMES.get(category, category)
        medal   = MEDALS[i] if i < 3 else f"**{rank}위**"
        rank_display = MEDALS[i] if i < 3 else f"{rank}위"

        if i < 3:
            bg = "#fff7ed" if i == 0 else "white"
            border = f"2px solid {color}"
            rank_style = f"font-size:1.5rem; min-width:40px; text-align:center;"
        else:
            bg = "#f8fafc"
            border = "1px solid #e2e8f0"
            rank_style = f"font-size:1rem; font-weight:800; color:#374151; min-width:40px; text-align:center;"

        st.markdown(f"""
        <div style='display:flex; align-items:center; gap:16px; background:{bg};
             border:{border}; border-radius:12px; padding:1rem 1.25rem; margin-bottom:8px;'>
            <div style='{rank_style}'>{rank_display}</div>
            <div style='flex:1; min-width:0;'>
                <div style='font-size:13px; color:#18181b; font-weight:600;
                     overflow:hidden; text-overflow:ellipsis; white-space:nowrap;'
                     title='{url}'>{url}</div>
            </div>
            <span style='background:{color}22; color:{color}; border:1px solid {color}44;
                  padding:3px 10px; border-radius:6px; font-size:12px; font-weight:bold;
                  white-space:nowrap;'>{cat_name}</span>
            <div style='font-size:13px; color:#64748b; white-space:nowrap; min-width:60px; text-align:right;'>
                탐지 <b>{count}</b>회
            </div>
        </div>
        """, unsafe_allow_html=True)
