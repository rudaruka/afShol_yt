import pandas as pd
import streamlit as st

from ai_utils import ask_gemini
from youtube_utils import extract_video_id, get_top_comments, get_transcript, get_video_info

st.set_page_config(page_title="유튜브 영상 비교 분석", page_icon="🎬", layout="wide")
st.title("🎬 유튜브 영상 비교 분석")

YT_KEY = st.secrets.get("YOUTUBE_API_KEY", "")
GEMINI_KEY = st.secrets.get("GEMINI_API_KEY", "")
if not YT_KEY or not GEMINI_KEY:
    st.error("`.streamlit/secrets.toml`(또는 Streamlit Cloud Secrets)에 YOUTUBE_API_KEY, GEMINI_API_KEY를 등록해주세요.")
    st.stop()

st.session_state.setdefault("videos", [])
st.session_state.setdefault("messages", [])

# ---------- 사이드바 ----------
with st.sidebar:
    st.header("영상 입력")
    urls = [st.text_input(f"영상 {i} URL", key=f"url{i}") for i in (1, 2, 3)]
    model = st.text_input("Gemini 모델", value="gemini-2.5-flash",
                          help="사용 가능한 모델명은 Google AI Studio에서 확인하세요.")
    if st.button("불러오기", type="primary", use_container_width=True):
        videos = []
        with st.spinner("영상 데이터를 가져오는 중..."):
            for u in filter(None, (x.strip() for x in urls)):
                vid = extract_video_id(u)
                if not vid:
                    st.warning(f"URL을 인식하지 못했어요: {u}")
                    continue
                info = get_video_info(vid, YT_KEY)
                if not info:
                    st.warning(f"영상을 찾지 못했어요: {u}")
                    continue
                info["transcript"] = get_transcript(vid)
                info["top_comments"] = get_top_comments(vid, YT_KEY)
                videos.append(info)
        if len(videos) < 1:
            st.error("불러온 영상이 없어요.")
        else:
            st.session_state.videos = videos
            st.session_state.messages = []  # 새 영상이면 대화 초기화
            st.success(f"{len(videos)}개 영상을 불러왔어요.")

    if st.session_state.messages and st.button("대화 초기화", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

videos = st.session_state.videos
if not videos:
    st.info("왼쪽에 유튜브 URL을 1~3개 입력하고 **불러오기**를 눌러주세요.")
    st.stop()

# ---------- 탭 ----------
tab_compare, tab_chat = st.tabs(["📊 비교", "💬 AI와 대화"])

with tab_compare:
    cols = st.columns(len(videos))
    for col, v in zip(cols, videos):
        with col:
            if v["thumbnail"]:
                st.image(v["thumbnail"], use_container_width=True)
            st.markdown(f"**{v['title']}**")
            st.caption(f"{v['channel']} · {v['published']}")
            if not v["transcript"]:
                st.caption("⚠️ 자막을 가져오지 못했어요 (설명·댓글 기반으로만 분석)")

    df = pd.DataFrame(
        {
            "제목": [v["title"][:30] for v in videos],
            "조회수": [v["views"] for v in videos],
            "좋아요": [v["likes"] for v in videos],
            "댓글수": [v["comments"] for v in videos],
            "길이(분)": [round(v["duration_sec"] / 60, 1) for v in videos],
        }
    )
    df["좋아요율(%)"] = (df["좋아요"] / df["조회수"].replace(0, pd.NA) * 100).round(2)
    df["댓글율(%)"] = (df["댓글수"] / df["조회수"].replace(0, pd.NA) * 100).round(3)
    st.dataframe(df, use_container_width=True, hide_index=True)

    c1, c2 = st.columns(2)
    with c1:
        st.caption("조회수 / 좋아요 / 댓글수")
        st.bar_chart(df.set_index("제목")[["조회수", "좋아요", "댓글수"]])
    with c2:
        st.caption("좋아요율 / 댓글율 (%)")
        st.bar_chart(df.set_index("제목")[["좋아요율(%)", "댓글율(%)"]])

SUGGESTIONS = [
    "각 영상을 3줄로 요약해줘",
    "영상들의 공통점과 차이점을 비교해줘",
    "댓글 반응(긍정/부정)을 비교해줘",
    "어떤 영상이 더 초보자에게 적합해?",
]

with tab_chat:
    # 대화 기록 표시
    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    # 추천 질문 (대화가 비어 있을 때만)
    clicked = None
    if not st.session_state.messages:
        st.caption("이런 걸 물어볼 수 있어요")
        qcols = st.columns(2)
        for i, q in enumerate(SUGGESTIONS):
            if qcols[i % 2].button(q, key=f"sug{i}", use_container_width=True):
                clicked = q

    question = st.chat_input("영상에 대해 무엇이든 물어보세요") or clicked
    if question:
        with st.chat_message("user"):
            st.markdown(question)
        with st.chat_message("assistant"):
            with st.spinner("생각 중..."):
                try:
                    answer = ask_gemini(
                        GEMINI_KEY, model, videos, st.session_state.messages, question
                    )
                except Exception as e:
                    answer = f"⚠️ AI 호출 중 오류가 났어요: {e}"
            st.markdown(answer)
        st.session_state.messages += [
            {"role": "user", "content": question},
            {"role": "assistant", "content": answer},
        ]
