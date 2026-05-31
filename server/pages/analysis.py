import streamlit as st
import requests
import threading
import time
import io
from streamlit_paste_button import paste_image_button

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
CATEGORY_NAMES_SAFE = {
    "PERSONAL":   "일반 문자",
    "FINANCE":    "금융 문자",
    "DELIVERY":   "배송 문자",
    "GOVERNMENT": "공공기관 문자",
    "PROMOTION":  "홍보/투자 문자",
    "AUTH":       "계정 문자",
    "WORK":       "지인 문자",
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
GRADE_CONFIG = {
    "Danger":  {"label": "위험",  "color": "#dc2626", "bg": "#fef2f2", "icon": "🚨"},
    "Warning": {"label": "주의",  "color": "#f97316", "bg": "#fff7ed", "icon": "⚠️"},
    "Safe":    {"label": "안전",  "color": "#16a34a", "bg": "#f0fdf4", "icon": "✅"},
    "Unknown": {"label": "분석 불가", "color": "#6b7280", "bg": "#f9fafb", "icon": "❌"},
}
ACTION_GUIDE = {
    "Danger":  "링크를 절대 클릭하지 마세요. 발신자를 차단하고 KISA 불법스팸대응센터(118)에 신고하세요.",
    "Warning": "링크 클릭을 권장하지 않습니다. 공식 앱이나 웹사이트를 직접 방문해서 확인하세요.",
    "Safe":    "정상 문자로 판단됩니다. 그러나 의심스러우면 발신자에게 직접 확인하세요.",
    "Unknown": "이미지에서 텍스트 또는 QR 코드를 인식할 수 없습니다. 더 선명한 이미지로 다시 시도해주세요.",
}
KEYWORD_TYPE_LABELS = {
    "urgency":          ("긴박감",   "#dc2626"),
    "threat":           ("위협",     "#ea580c"),
    "action":           ("행동유도", "#f59e0b"),
    "category_pattern": ("유형패턴", "#7c3aed"),
}

# session_state 초기화

if "result" not in st.session_state:
    st.session_state.result = None
if "last_file" not in st.session_state:
    st.session_state.last_file = None
if "file_data" not in st.session_state:
    st.session_state.file_data = None
if "analyzing" not in st.session_state:
    st.session_state.analyzing = False
if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0
if "cancelled" not in st.session_state:
    st.session_state.cancelled = False
if "input_mode" not in st.session_state:
    st.session_state.input_mode = "image"

# ── 상단 타이틀 ──────────────────────────────────────────
st.markdown("""
<div style='margin-bottom:1.5rem;'>
    <div style='font-size:1.4rem; font-weight:800; color:#0f172a; margin-bottom:4px;'>🔍 문자 분석</div>
    <div style='font-size:13px; color:#94a3b8;'>이미지·텍스트·QR 코드를 AI로 즉시 분석합니다</div>
</div>
""", unsafe_allow_html=True)

c1, c2 = st.columns([1, 1.2], gap="large")

# ── 왼쪽: 입력 ───────────────────────────────────────────
with c1:
    st.markdown("<div style='font-size:14px; font-weight:700; color:#334155; margin-bottom:0.6rem;'>📥 데이터 입력</div>", unsafe_allow_html=True)
    tab_img, tab_txt, tab_qr = st.tabs(["🖼️ 이미지/QR 업로드", "📝 텍스트 직접 입력", "📲 QR 스캔"])

    with tab_img:
        if st.session_state.analyzing:
            st.info("🔍 분석이 진행 중입니다.")
        else:
            uploaded_file = st.file_uploader(
                "분석할 문자 캡처본 또는 QR코드를 업로드하세요",
                type=['png', 'jpg', 'jpeg'],
                key=f"uploader_{st.session_state.uploader_key}"
            )
            if uploaded_file is not None:
                fd_mode = (st.session_state.file_data or {}).get("mode")
                if st.session_state.last_file != uploaded_file.name or fd_mode != "image":
                    st.session_state.result = None
                    st.session_state.cancelled = False
                    st.session_state.last_file = uploaded_file.name
                    uploaded_file.seek(0)
                    st.session_state.file_data = {
                        "name": uploaded_file.name,
                        "data": uploaded_file.read(),
                        "type": uploaded_file.type,
                        "mode": "image",
                    }

            pasted = paste_image_button("📋 클립보드에서 붙여넣기 (Ctrl+C 후 클릭)",
                                        key=f"paste_{st.session_state.uploader_key}")
            if pasted.image_data is not None:
                buf = io.BytesIO()
                pasted.image_data.save(buf, format="PNG")
                st.session_state.result = None
                st.session_state.cancelled = False
                st.session_state.last_file = "pasted_image.png"
                st.session_state.file_data = {
                    "name": "pasted_image.png",
                    "data": buf.getvalue(),
                    "type": "image/png",
                    "mode": "image",
                }
                st.session_state.analyzing = True
                st.rerun()

    with tab_txt:
        is_text_mode = st.session_state.file_data is not None and st.session_state.file_data.get("mode") == "text"
        saved_text = st.session_state.file_data.get("text", "") if is_text_mode else ""

        input_text = st.text_area(
            "문자 내용을 붙여넣어 주세요",
            value=saved_text if st.session_state.analyzing and is_text_mode else "",
            height=200,
            placeholder="예) [Web발신] [KB국민은행] 본인 확인이 필요합니다...",
            key=f"text_input_{st.session_state.uploader_key}",
            disabled=st.session_state.analyzing,
        )

    with tab_qr:
        if "camera_on" not in st.session_state:
            st.session_state.camera_on = False

        if not st.session_state.camera_on:
            st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
            if st.button("📷 카메라 켜기", use_container_width=True,
                         key="btn_camera_on", disabled=st.session_state.analyzing):
                st.session_state.camera_on = True
                st.rerun()
        else:
            if st.button("카메라 끄기", key="btn_camera_off"):
                st.session_state.camera_on = False
                st.rerun()
            camera_photo = st.camera_input(
                "문자 화면 또는 QR코드를 촬영하세요",
                key=f"camera_{st.session_state.uploader_key}",
                disabled=st.session_state.analyzing,
            )
            if camera_photo is not None:
                st.session_state.camera_on = False
                st.session_state.result = None
                st.session_state.cancelled = False
                st.session_state.file_data = {
                    "name": "camera_capture.jpg",
                    "data": camera_photo.getvalue(),
                    "type": "image/jpeg",
                    "mode": "image",
                }
                st.session_state.analyzing = True
                st.rerun()

    img_preview = st.empty()

# ── 오른쪽: 결과 헤더 + 분석 버튼 + placeholder ──────────
with c2:
    st.markdown("<div style='font-size:14px; font-weight:700; color:#334155; margin-bottom:0.6rem;'>📊 분석 결과</div>", unsafe_allow_html=True)

    if st.button("AI 정밀 분석 실행", use_container_width=True, type="primary",
                 key="btn_analyze", disabled=st.session_state.analyzing):
        text_key = f"text_input_{st.session_state.uploader_key}"
        text_val = st.session_state.get(text_key, "")

        if text_val.strip():
            st.session_state.result = None
            st.session_state.cancelled = False
            st.session_state.file_data = {"text": text_val.strip(), "mode": "text"}
            st.session_state.analyzing = True
            st.rerun()
        elif st.session_state.file_data and st.session_state.file_data.get("mode") == "image":
            st.session_state.result = None
            st.session_state.cancelled = False
            st.session_state.analyzing = True
            st.rerun()
        else:
            st.warning("이미지를 업로드하거나 텍스트를 입력해주세요.")

    results_placeholder = st.empty()
    progress_placeholder = st.empty()

# ── 이미지 미리보기 채우기 ────────────────────────────────
_fd = st.session_state.file_data
if _fd is not None and _fd.get("mode") == "image" and st.session_state.result is None:
    if st.session_state.analyzing:
        import base64
        _b64 = base64.b64encode(_fd["data"]).decode()
        _mime = _fd.get("type", "image/png")
        img_preview.markdown(f"""
        <div style='opacity:0.45;'>
            <img src='data:{_mime};base64,{_b64}' style='width:100%; border-radius:8px;'/>
            <p style='font-size:12px; color:#64748b; text-align:center; margin-top:4px;'>업로드된 이미지</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        img_preview.image(_fd["data"], caption="업로드된 이미지", use_container_width=True)

# ── placeholder를 analyzing 여부에 따라 채움 (비블로킹) ───
if not st.session_state.analyzing:
    progress_placeholder.empty()
    if st.session_state.result is not None:
        result = st.session_state.result
        grade_key    = result.get("result", {}).get("grade", "Safe")
        keywords     = result.get("nlp_analysis", {}).get("risk_keywords", [])
        rank         = result.get("rank")
        msg          = result.get("result", {}).get("message", "")
        extracted_text = result.get("extracted_text", "")
        result_urls  = list(dict.fromkeys(result.get("qr_urls", []) + result.get("text_urls", [])))
        cat_map          = result.get("category", {})
        category         = cat_map.get("category", "-")

        if category == "UNKNOWN":
            grade_key = "Unknown"
        cfg          = GRADE_CONFIG.get(grade_key, GRADE_CONFIG["Safe"])
        name_map     = CATEGORY_NAMES_SAFE if grade_key == "Safe" else CATEGORY_NAMES
        cat_label    = "" if grade_key == "Unknown" else name_map.get(category, category)
        text_reasons = result.get("text_reasons", [])
        url_reasons  = result.get("url_reasons", [])
        low_confidence = result.get("low_confidence_warning", False)
        safe_reason  = result.get("safe_reason")
        vlm_result        = result.get("vlm_analysis", {})
        gemini_text_result = result.get("gemini_text_analysis", {})

        with results_placeholder.container():
            tab1, tab2 = st.tabs(["결과", "탐지 근거"])

            with tab1:
                safe_reason_html = ""

                st.markdown(f"""
                <div style='background:{cfg["color"]}; padding:1.5rem 2rem; border-radius:20px;
                     text-align:center; color:white; margin-bottom:1rem;'>
                    <div style='font-size:2.5rem;'>{cfg["icon"]}</div>
                    <div style='font-size:1.8rem; font-weight:800; margin-top:0.3rem;'>{cfg["label"]}</div>
                    <div style='display:inline-block; background:rgba(255,255,255,0.25); padding:2px 12px;
                         border-radius:20px; font-size:0.85rem; font-weight:600; margin-top:0.4rem;'>{cat_label}</div>
                    <div style='font-size:0.9rem; opacity:0.85; margin-top:0.2rem;'>{msg}</div>
                    {safe_reason_html}
                </div>
                """, unsafe_allow_html=True)

                if low_confidence:
                    st.markdown("""
                    <div style='background:#fefce8; border:1px solid #fbbf24; border-radius:12px;
                         padding:0.8rem 1.2rem; margin-bottom:1rem; font-size:0.88rem; color:#92400e;'>
                        ⚠️ <strong>AI 분석 신호가 미약합니다.</strong> 명확한 위험 패턴이 감지되지 않았습니다.
                        의심스럽다면 발신 번호를 검색하거나 해당 기관에 직접 문의하세요.
                    </div>
                    """, unsafe_allow_html=True)

                guide = ACTION_GUIDE.get(grade_key, "")
                st.markdown(f"""
                <div style='background:{cfg["bg"]}; border:1px solid {cfg["color"]}44; padding:0.9rem 1.2rem;
                     border-radius:12px; margin-bottom:1rem; font-size:0.9rem; color:{cfg["color"]};'>
                    <strong>행동 가이드</strong><br>{guide}
                </div>
                """, unsafe_allow_html=True)

                if grade_key == "Danger":
                    st.markdown("""
                    <a href="https://spam.kisa.or.kr" target="_blank" style="text-decoration:none;">
                        <div style='background:#fef2f2; border:1.5px solid #dc2626; border-radius:12px;
                             padding:0.9rem 1.2rem; margin-top:0.5rem;
                             display:flex; align-items:center; gap:10px;'>
                            <span style='font-size:1.3rem;'>🚨</span>
                            <div>
                                <div style='font-size:14px; font-weight:700; color:#dc2626;'>KISA 불법스팸대응센터 신고하기</div>
                                <div style='font-size:12px; color:#ef4444; margin-top:2px;'>spam.kisa.or.kr · 전화 118</div>
                            </div>
                            <span style='margin-left:auto; color:#dc2626; font-size:1rem;'>→</span>
                        </div>
                    </a>
                    """, unsafe_allow_html=True)

                st.markdown("<div style='margin-top:1rem;'></div>", unsafe_allow_html=True)

                share_lines = [f"[스미싱 탐지 결과]", f"판정: {cfg['label']} ({cat_label})"]
                if text_reasons:
                    share_lines.append("\n[탐지 근거]")
                    share_lines += [f"• {r}" for r in text_reasons]
                if url_reasons:
                    if not text_reasons:
                        share_lines.append("\n[탐지 근거]")
                    share_lines += [f"• {r}" for r in url_reasons]
                if grade_key == "Danger":
                    share_lines.append("\n의심 문자는 KISA 불법스팸대응센터(118)에 신고하세요.")
                share_lines.append("\n- 스미싱 탐지 시스템으로 분석됨")
                share_text = "\n".join(share_lines)

                import streamlit.components.v1 as components
                st.markdown("<div style='font-size:13px; color:#64748b; margin-bottom:4px;'>결과 복사</div>", unsafe_allow_html=True)
                components.html(f"""
                <div style="font-family:sans-serif;">
                    <textarea id="shareBox" readonly style="width:100%; height:110px; font-size:14px;
                        font-family:'Pretendard', 'Apple SD Gothic Neo', sans-serif; line-height:1.6;
                        border:1px solid #e2e8f0; border-radius:8px; padding:10px;
                        resize:none; background:#f8fafc; color:#374151;">{share_text}</textarea>
                    <button onclick="navigator.clipboard.writeText(document.getElementById('shareBox').value).then(()=>{{this.textContent='✅ 복사됨!'; setTimeout(()=>this.textContent='📋 복사',1500)}})"
                        style="margin-top:8px; padding:8px 20px; background:#3d9df3; color:white;
                               border:none; border-radius:8px; font-size:14px; cursor:pointer; font-weight:600;">
                        📋 복사
                    </button>
                </div>
                """, height=200)

            with tab2:
                # ── AI 종합 분석 카드 ──
                _g_ok  = gemini_text_result.get("success", False)
                _v_ok  = vlm_result.get("success", False)
                _has_k = bool(keywords)
                _has_u = bool(result_urls)
                _p_url = result.get("scores", {}).get("p_url", 0.0)
                _p_gemini = result.get("scores", {}).get("p_gemini", 0.0) or 0.0
                _has_ur = _p_url > 2.0
                _vt_safe = result.get("url_analysis", {}).get("vt_confirmed_safe", False)
                _gemini_high = _g_ok and _p_gemini >= 5.0  # Gemini가 의심 판단
                _g_noted = _g_ok and _p_gemini >= 3.0     # Safe 등급에서 Gemini가 주의 요소를 언급한 수준

                def _build_summary(grade, g, v, k, u, ur, gemini_high, vt_safe, g_noted=False):
                    if grade == "Danger":
                        if g and v and ur:   return "AI 문맥·시각 분석에서 스미싱 패턴이 감지되었고, URL이 악성으로 확인되어 위험으로 판정되었습니다."
                        if g and ur:         return "AI 문맥 분석에서 스미싱 패턴이 감지되었고, URL이 악성으로 확인되어 위험으로 판정되었습니다."
                        if v and ur:         return "이미지에서 시각적 위협 신호가 감지되었고, URL이 악성으로 확인되어 위험으로 판정되었습니다."
                        if ur:               return "URL 보안 분석에서 악성으로 확인되어 위험으로 판정되었습니다."
                        if g and v:          return "AI 문맥·시각 분석에서 스미싱 패턴이 감지되어 위험으로 판정되었습니다."
                        if g:                return "AI 문맥 분석에서 스미싱 패턴이 강하게 감지되어 위험으로 판정되었습니다."
                        return "복합적인 위험 신호가 감지되어 위험으로 판정되었습니다."

                    if grade == "Warning":
                        if g and v and ur:   return "AI 문맥·시각 분석에서 의심 요소가 발견되었고, URL에서도 위험 신호가 감지되어 주의로 판정되었습니다."
                        if g and ur:         return "AI 문맥 분석에서 의심 요소가 발견되었고, URL에서 일부 위험 신호가 감지되어 주의로 판정되었습니다."
                        if g and k:          return "AI 문맥 분석과 키워드 패턴에서 의심 요소가 발견되어 주의로 판정되었습니다."
                        if g:                return "AI 문맥 분석에서 일부 의심 요소가 발견되어 주의로 판정되었습니다."
                        if k and ur:         return "스미싱 패턴 키워드가 탐지되었고, URL에서도 의심 신호가 발견되어 주의로 판정되었습니다."
                        if ur:               return "URL 분석에서 일부 위험 신호가 감지되어 주의로 판정되었습니다."
                        if k:                return "스미싱에서 자주 사용되는 키워드 패턴이 감지되어 주의로 판정되었습니다."
                        return "복합적인 의심 신호가 감지되어 주의로 판정되었습니다."

                    if grade == "Safe":
                        if gemini_high and vt_safe:
                            return "AI 문맥 분석에서 일부 의심 요소가 감지되었으나, 다수의 보안 엔진에서 URL을 안전한 사이트로 확인하여 최종 안전으로 판정되었습니다."
                        if gemini_high and u:
                            return "AI 문맥 분석에서 의심 요소가 감지되었으나, URL이 알려진 위험 사이트가 아닌 것으로 확인되어 최종 안전으로 판정되었습니다. AI 분석 결과는 참고 수준으로 확인하세요."
                        if g_noted and k and ur: return "키워드와 URL에서 일부 의심 요소가 발견되었고 AI 문맥 분석에서도 주의 요소가 언급되었으나, URL이 알려진 위험 사이트가 아닌 것으로 확인되어 안전으로 판정되었습니다."
                        if g_noted and k:        return "일부 키워드가 탐지되고 AI 문맥 분석에서 주의 요소가 언급되었으나, 핵심 위험 패턴이 발견되지 않아 안전으로 판정되었습니다."
                        if g and u:              return "AI 문맥 분석과 URL 분석에서 위험 요소가 발견되지 않아 안전으로 판정되었습니다."
                        if g:                    return "AI 문맥 분석에서 위험 요소가 발견되지 않아 안전으로 판정되었습니다."
                        if k and not ur:         return "일부 키워드가 탐지되었으나, URL이 알려진 위험 사이트가 아니고 스미싱 핵심 패턴이 발견되지 않아 안전으로 판정되었습니다."
                        return "위험 패턴 및 악성 URL이 감지되지 않아 안전으로 판정되었습니다."

                    return ""

                _summary_sentence = _build_summary(grade_key, _g_ok, _v_ok, _has_k, _has_u, _has_ur, _gemini_high, _vt_safe, _g_noted)
                if _summary_sentence:
                    _s_color = {"Danger": "#dc2626", "Warning": "#f97316", "Safe": "#16a34a"}.get(grade_key, "#64748b")
                    _s_icon  = {"Danger": "🚨", "Warning": "⚠️", "Safe": "✅"}.get(grade_key, "")
                    st.markdown(f"""
                    <div style='background:{_s_color}0d; border:1.5px solid {_s_color}66; border-radius:14px; padding:1.2rem 1.4rem; margin-bottom:1rem;'>
                        <div style='font-size:14px; font-weight:700; color:{_s_color}; margin-bottom:0.6rem;'>{_s_icon} AI 종합 분석</div>
                        <div style='font-size:14px; color:#1e293b; line-height:1.7;'>{_summary_sentence}</div>
                    </div>
                    """, unsafe_allow_html=True)

                if not gemini_text_result.get("success") and not vlm_result.get("success"):
                    st.markdown("""
                    <div style='background:#fefce8; border:1px solid #fbbf24; border-radius:12px;
                         padding:0.8rem 1.2rem; margin-bottom:1rem; font-size:0.88rem; color:#92400e;'>
                        ⚠️ AI 문맥 분석을 일시적으로 이용할 수 없어 NLP 및 URL 분석 결과만 반영되었습니다. 잠시 후 다시 시도해주세요.
                    </div>
                    """, unsafe_allow_html=True)

                _g_color = {"Danger": "#dc2626", "Warning": "#f97316", "Safe": "#16a34a"}.get(grade_key, "#64748b")

                if gemini_text_result.get("success") and gemini_text_result.get("reason"):
                    st.markdown(f"""
                    <div style='background:white; border:1px solid {_g_color}44; border-radius:12px; padding:1rem; margin-top:0.5rem;'>
                        <div style='font-size:13px; color:#64748b; margin-bottom:8px;'>
                            AI 문맥 분석
                            <span style='font-size:11px; color:#0ea5e9; margin-left:6px;'>Gemini</span>
                        </div>
                        <div style='font-size:13px; color:#374151;'>{gemini_text_result['reason']}</div>
                    </div>
                    """, unsafe_allow_html=True)

                if vlm_result.get("success") and vlm_result.get("visual_signals"):
                    signals_html = "".join(
                        f"<span style='background:#7c3aed22; color:#7c3aed; border:1px solid #7c3aed44; "
                        f"padding:4px 10px; border-radius:8px; font-size:12px; font-weight:bold; "
                        f"margin:3px; display:inline-block;'>{s}</span>"
                        for s in vlm_result["visual_signals"]
                    )
                    reason_html = f"<div style='font-size:12px; color:#64748b; margin-top:8px;'>{vlm_result['reason']}</div>" if vlm_result.get("reason") else ""
                    st.markdown(f"""
                    <div style='background:white; border:1px solid {_g_color}44; border-radius:12px; padding:1rem; margin-top:0.5rem;'>
                        <div style='font-size:13px; color:#64748b; margin-bottom:8px;'>
                            AI 시각 분석
                            <span style='font-size:11px; color:#7c3aed; margin-left:6px;'>Gemini Vision</span>
                        </div>
                        {signals_html}
                        {reason_html}
                    </div>
                    """, unsafe_allow_html=True)

                if keywords:
                    chips_html = ""
                    for kw in keywords:
                        ktype = kw.get("type", "")
                        klabel, kcolor = KEYWORD_TYPE_LABELS.get(ktype, (ktype, "#64748b"))
                        word = kw.get("keyword", "")
                        chips_html += f"""<span style='background:{kcolor}22; color:{kcolor}; border:1px solid {kcolor}55;
                            padding:4px 10px; border-radius:8px; font-size:12px; font-weight:bold;
                            margin:3px; display:inline-block;'>{word}
                            <span style='opacity:0.7; font-size:10px;'>[{klabel}]</span></span>"""
                    st.markdown(f"""
                    <div style='background:white; border:1px solid #e2e8f0; border-radius:12px; padding:1rem; margin-top:0.5rem;'>
                        <div style='font-size:13px; color:#64748b; margin-bottom:8px;'>탐지된 위험 키워드</div>
                        {chips_html}
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown("""
                    <div style='background:white; border:1px solid #e2e8f0; border-radius:12px; padding:1rem; margin-top:0.5rem;'>
                        <div style='font-size:13px; color:#64748b; margin-bottom:4px;'>탐지된 위험 키워드</div>
                        <div style='font-size:13px; color:#94a3b8;'>감지된 키워드 없음</div>
                    </div>
                    """, unsafe_allow_html=True)

                if text_reasons:
                    reasons_html = "".join(
                        f"<div style='display:flex; align-items:flex-start; gap:8px; margin-bottom:6px;'>"
                        f"<span style='color:{cfg['color']}; font-weight:bold; flex-shrink:0;'>•</span>"
                        f"<span style='font-size:13px; color:#374151;'>{r}</span></div>"
                        for r in text_reasons
                    )
                    st.markdown(f"""
                    <div style='background:white; border:1px solid #e2e8f0; border-radius:12px; padding:1rem; margin-top:0.5rem;'>
                        <div style='font-size:13px; color:#64748b; margin-bottom:8px;'>문자 내용 탐지 근거</div>
                        {reasons_html}
                    </div>
                    """, unsafe_allow_html=True)

                if url_reasons:
                    url_reasons_html = "".join(
                        f"<div style='display:flex; align-items:flex-start; gap:8px; margin-bottom:6px;'>"
                        f"<span style='color:{cfg['color']}; font-weight:bold; flex-shrink:0;'>•</span>"
                        f"<span style='font-size:13px; color:#374151;'>{r}</span></div>"
                        for r in url_reasons
                    )
                    st.markdown(f"""
                    <div style='background:white; border:1px solid #e2e8f0; border-radius:12px; padding:1rem; margin-top:0.5rem;'>
                        <div style='font-size:13px; color:#64748b; margin-bottom:8px;'>URL 탐지 근거</div>
                        {url_reasons_html}
                    </div>
                    """, unsafe_allow_html=True)

            st.markdown("<div style='margin-top:0.5rem;'></div>", unsafe_allow_html=True)
            with st.container(border=True):
                c1, c2 = st.columns([2, 1], gap="small")
                with c1:
                    st.markdown("<div style='font-size:15px; color:#64748b; padding-top:8px;'>결과가 잘못되었다면?</div>", unsafe_allow_html=True)
                with c2:
                    if st.button("💬 피드백하러 가기", use_container_width=True):
                        st.switch_page("pages/feedback.py")
    else:
        with results_placeholder.container():
            st.markdown("""
            <div style='height: 400px; display: flex; align-items: center; justify-content: center;
                 border: 2px dashed #e2e8f0; border-radius: 20px; color: #94a3b8; background: white;'>
                이미지 또는 텍스트를 입력하고 분석 버튼을 눌러주세요.
            </div>
            """, unsafe_allow_html=True)

# ── 분석 실행 (블로킹) ────────────────────────────────────
if st.session_state.analyzing:
    file_data = st.session_state.file_data
    if file_data is None:
        st.session_state.analyzing = False
        st.rerun()

    api_result = {"data": None, "error": None, "done": False, "cancelled": False}

    def call_api():
        try:
            if file_data.get("mode") == "text":
                response = requests.post(
                    f"{API_URL}/analyze-text",
                    json={"text": file_data["text"]},
                    timeout=180
                )
            else:
                files = {"file": (file_data["name"], file_data["data"], file_data["type"])}
                response = requests.post(f"{API_URL}/analyze", files=files, timeout=180)

            if response.status_code == 200:
                api_result["data"] = response.json()
            else:
                api_result["error"] = response.json().get("detail", "알 수 없는 오류")
        except requests.exceptions.ConnectionError:
            api_result["error"] = "connection"
        except Exception as e:
            api_result["error"] = str(e)
        finally:
            api_result["done"] = True

    thread = threading.Thread(target=call_api)
    thread.start()

    LOADING_BAR_HTML = """
<style>
.smishing-loader{width:100%;height:6px;background:#e2e8f0;border-radius:3px;overflow:hidden;position:relative;margin:8px 0;}
.smishing-loader::after{content:'';position:absolute;top:0;height:100%;width:14%;background:#3b82f6;border-radius:3px;animation:slide 2.2s infinite ease-in-out;}
@keyframes slide{0%{left:-14%;}100%{left:100%;}}
</style>
<div class='smishing-loader'></div>
"""
    DONE_BAR_HTML = """
<div style='width:100%;height:6px;background:#3b82f6;border-radius:3px;margin:8px 0;'></div>
"""

    results_placeholder.empty()
    with progress_placeholder.container():
        bar_placeholder = st.empty()
        status_text = st.empty()
        stop_placeholder = st.empty()
        stop_btn = stop_placeholder.button("⛔ 분석 중단", use_container_width=True,
                                           key=f"btn_stop_{st.session_state.uploader_key}")

    bar_placeholder.markdown(LOADING_BAR_HTML, unsafe_allow_html=True)
    status_text.text("분석 중...")
    while not api_result["done"]:
        if stop_btn:
            api_result["cancelled"] = True
            break
        time.sleep(0.1)

    if api_result["cancelled"]:
        st.session_state.analyzing = False
        st.session_state.cancelled = True
        st.session_state.uploader_key += 1
        bar_placeholder.empty()
        status_text.text("분석이 중단되었습니다.")
        stop_placeholder.empty()
        st.session_state.result = None
        st.rerun()

    thread.join()
    st.session_state.analyzing = False
    stop_placeholder.empty()
    bar_placeholder.markdown(DONE_BAR_HTML, unsafe_allow_html=True)
    status_text.text("분석 완료!")

    if api_result["error"] == "connection":
        status_text.error("서버에 연결할 수 없습니다. FastAPI 서버가 실행 중인지 확인해주세요.")
        st.session_state.result = None
    elif api_result["error"]:
        status_text.error(f"서버 오류: {api_result['error']}")
        st.session_state.result = None
    else:
        st.session_state.result = api_result["data"]
        st.session_state.pop("ranking_data", None)
    st.session_state.uploader_key += 1
    st.rerun()
