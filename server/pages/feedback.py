import streamlit as st
import requests
import re
from collections import defaultdict

API_URL = "http://127.0.0.1:8000"

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

st.markdown("""
<div style='margin-bottom:1.5rem;'>
    <div style='font-size:1.4rem; font-weight:800; color:#0f172a; margin-bottom:4px;'>💬 피드백</div>
    <div style='font-size:13px; color:#94a3b8;'>탐지 결과 개선에 도움을 주세요</div>
</div>
""", unsafe_allow_html=True)

tab_submit, tab_usage = st.tabs(["📝 피드백하기", "📊 피드백 활용"])

# ── 피드백하기 ─────────────────────────────────────────────
with tab_submit:
    st.caption("스미싱 탐지 결과가 잘못됐거나 개선이 필요하다면 알려주세요.")

    grade_labels = {"Danger": "🚨 위험", "Warning": "⚠️ 주의", "Safe": "✅ 안전"}

    input_mode = st.radio("입력 방식", ["📝 텍스트", "🖼️ 이미지"], horizontal=True, label_visibility="collapsed")

    with st.form("standalone_feedback_form"):
        if input_mode == "📝 텍스트":
            text_content = st.text_area(
                "문자 내용",
                placeholder="분석된 문자 내용을 입력해주세요.",
                height=120,
            )
            uploaded_img = None
        else:
            uploaded_img = st.file_uploader(
                "문자 캡처 이미지",
                type=["png", "jpg", "jpeg"],
            )
            if uploaded_img is not None:
                st.image(uploaded_img, caption="첨부 이미지", use_container_width=True)
            text_content = ""

        col1, col2 = st.columns(2)
        with col1:
            given = st.selectbox(
                "시스템 판정 (AI가 내린 결과)",
                options=["Danger", "Warning", "Safe"],
                format_func=lambda x: grade_labels[x],
            )
        with col2:
            correct = st.selectbox(
                "실제 판정 (올바른 결과)",
                options=["Safe", "Warning", "Danger"],
                format_func=lambda x: grade_labels[x],
            )
        reason = st.text_area(
            "이유 (선택)",
            placeholder="예: 실제로 제가 주문한 택배 안내 문자입니다.",
        )
        submitted = st.form_submit_button("피드백 제출", use_container_width=True, type="primary")

    if submitted:
        has_text  = text_content.strip()
        has_image = uploaded_img is not None

        if not has_text and not has_image:
            st.warning("문자 내용 또는 이미지를 입력해주세요.")
        else:
            final_text = text_content.strip() if has_text else "[이미지 첨부 피드백]"
            try:
                if has_image:
                    uploaded_img.seek(0)
                    requests.post(
                        f"{API_URL}/feedback",
                        data={"given_grade": given, "correct_grade": correct,
                              "reason": reason, "text_content": final_text},
                        files={"image": (uploaded_img.name, uploaded_img.read(), uploaded_img.type)},
                        timeout=5,
                    )
                else:
                    requests.post(
                        f"{API_URL}/feedback",
                        data={"given_grade": given, "correct_grade": correct,
                              "reason": reason, "text_content": final_text},
                        timeout=5,
                    )
                st.success("피드백이 제출됐습니다. 감사합니다!")
            except Exception:
                st.error("제출에 실패했습니다. 서버 연결을 확인해주세요.")

# ── 피드백 활용 ────────────────────────────────────────────
with tab_usage:
    st.markdown("#### 📋 수집된 위험 URL 현황")
    st.caption("위험으로 판정된 URL의 누적 탐지 현황입니다.")

    if "ranking_data" not in st.session_state:
        try:
            resp = requests.get(f"{API_URL}/top-urls?limit=50", timeout=5)
            st.session_state.ranking_data = resp.json().get("top_urls", [])
        except Exception:
            st.session_state.ranking_data = None

    data = st.session_state.ranking_data

    if data is None:
        st.error("서버에 연결할 수 없습니다.")
    elif len(data) == 0:
        st.markdown("""
        <div style='text-align:center; padding:2rem; color:#94a3b8;'>
            <div style='font-size:3rem;'>🛡️</div>
            <p style='font-size:1rem; font-weight:bold; margin-top:0.8rem;'>탐지된 위험 문자가 없습니다</p>
        </div>
        """, unsafe_allow_html=True)
    else:
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
                bars_html += (
                    f"<div style='display:flex; align-items:center; gap:10px; margin-bottom:6px;'>"
                    f"<div style='width:90px; font-size:12px; color:#374151; text-align:right; flex-shrink:0;'>{name}</div>"
                    f"<div style='flex:1; background:#f1f5f9; border-radius:4px; height:12px;'>"
                    f"<div style='width:{pct:.1f}%; background:{color}; border-radius:4px; height:12px;'></div></div>"
                    f"<div style='width:40px; font-size:12px; color:#64748b; flex-shrink:0; text-align:right;'>{pct:.0f}%</div>"
                    f"</div>"
                )
            if bars_html:
                st.markdown(
                    f"<div style='background:white; border:1px solid #e2e8f0; border-radius:12px;"
                    f"padding:1rem 1.25rem; margin-bottom:1rem;'>"
                    f"<div style='font-size:13px; color:#64748b; font-weight:600; margin-bottom:10px;'>탐지된 스미싱 유형 분포</div>"
                    f"{bars_html}</div>",
                    unsafe_allow_html=True
                )

        if "ru_filter_key" not in st.session_state:
            st.session_state.ru_filter_key = 0

        col1, col2, col3 = st.columns([1.1, 3, 0.7])
        with col1:
            selected_category = st.selectbox(
                "카테고리",
                options=[k for k in CATEGORY_NAMES.keys() if k != "PERSONAL"],
                format_func=lambda x: CATEGORY_NAMES.get(x, x),
                index=None,
                placeholder="카테고리 선택",
                key=f"ru_cat_{st.session_state.ru_filter_key}",
                label_visibility="collapsed",
            )
        with col2:
            search_query = st.text_input(
                "URL 검색", placeholder="🔍  예: amazon, trust4, .top",
                key=f"ru_search_{st.session_state.ru_filter_key}",
                label_visibility="collapsed",
            )
        with col3:
            if st.button("새로고침", use_container_width=True, key="ru_refresh"):
                st.session_state.pop("ranking_data", None)
                st.session_state.ru_filter_key += 1
                st.rerun()

        filtered = data
        if search_query.strip():
            filtered = [item for item in filtered if search_query.strip().lower() in item.get("url", "").lower()]
        if selected_category:
            filtered = [item for item in filtered if item.get("category") == selected_category]

        if not filtered:
            st.markdown("<div style='text-align:center; padding:1.5rem; color:#94a3b8;'>검색 결과가 없습니다.</div>", unsafe_allow_html=True)

        MEDALS = ["🥇", "🥈", "🥉"]
        for i, item in enumerate(filtered):
            rank     = i + 1
            url      = item.get("url", "")
            category = item.get("category", "")
            count    = item.get("count", 0)
            color    = CATEGORY_COLORS.get(category, "#dc2626")
            cat_name = CATEGORY_NAMES.get(category, category)
            rank_display = MEDALS[i] if i < 3 else f"{rank}위"

            if i < 3:
                bg = "#fff7ed" if i == 0 else "white"
                border = f"2px solid {color}"
                rank_style = "font-size:1.5rem; min-width:40px; text-align:center;"
            else:
                bg = "#f8fafc"
                border = "1px solid #e2e8f0"
                rank_style = "font-size:1rem; font-weight:800; color:#374151; min-width:40px; text-align:center;"

            st.markdown(
                f"<div style='display:flex; align-items:center; gap:16px; background:{bg};"
                f"border:{border}; border-radius:12px; padding:1rem 1.25rem; margin-bottom:8px;'>"
                f"<div style='{rank_style}'>{rank_display}</div>"
                f"<div style='flex:1; min-width:0;'>"
                f"<div style='font-size:13px; color:#18181b; font-weight:600;"
                f"overflow:hidden; text-overflow:ellipsis; white-space:nowrap;' title='{url}'>{url}</div></div>"
                f"<span style='background:{color}22; color:{color}; border:1px solid {color}44;"
                f"padding:3px 10px; border-radius:6px; font-size:12px; font-weight:bold;"
                f"white-space:nowrap;'>{cat_name}</span>"
                f"<div style='font-size:13px; color:#64748b; white-space:nowrap; min-width:60px; text-align:right;'>"
                f"탐지 <b>{count}</b>회</div></div>",
                unsafe_allow_html=True
            )

    st.markdown("<div style='margin-top:2rem;'></div>", unsafe_allow_html=True)
    st.markdown("#### 🔄 수집된 피드백, 어떻게 활용되나요?")

    for title, desc in [
        ("📌 키워드 가중치 조정", "피드백에서 오탐·미탐 패턴을 분석해 NLP 위험 키워드의 가중치를 수동으로 조정합니다."),
        ("📌 Gemini 프롬프트 개선", "오탐·미탐 사례를 분석해 AI 문맥 분석(Gemini) 프롬프트의 판단 기준을 지속적으로 개선합니다."),
        ("📌 위험 URL 데이터베이스 갱신", "이미지 피드백에서 URL이 포함된 경우 위험 URL 목록에 추가해 향후 동일 URL 탐지 정확도를 높입니다."),
    ]:
        st.markdown(
            f"<div style='background:white; border:1px solid #e2e8f0; border-radius:12px;"
            f"padding:1rem 1.2rem; margin-bottom:8px;'>"
            f"<div style='font-size:14px; font-weight:700; color:#18181b; margin-bottom:6px;'>{title}</div>"
            f"<div style='font-size:13px; color:#374151; line-height:1.7;'>{desc}</div></div>",
            unsafe_allow_html=True
        )

    st.markdown("<div style='margin-top:1.5rem;'></div>", unsafe_allow_html=True)
    st.markdown("#### 🧠 모델 개선 방향")
    st.markdown("""
    <div style='background:#f0fdf4; border:1px solid #86efac; border-radius:12px; padding:1.2rem 1.4rem;'>
        <div style='font-size:13px; color:#166534; line-height:1.8;'>
            ✅ <strong>KoBERT 카테고리 분류 모델</strong> — 현재 정확도 96%, 학습 데이터 1만 건 기반<br>
            ✅ <strong>Gemini AI 문맥 분석</strong> — 프롬프트 지속 개선으로 정상/스미싱 판단 정확도 향상<br>
            ✅ <strong>URL 보안 분석</strong> — VirusTotal + OpenPhish + URLhaus 피드 주간 갱신
        </div>
    </div>
    """, unsafe_allow_html=True)
