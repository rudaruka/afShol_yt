from google import genai
from google.genai import types

MAX_TRANSCRIPT_CHARS = 40_000  # 영상당 자막 최대 길이


def build_context(videos: list[dict]) -> str:
    parts = []
    for i, v in enumerate(videos, 1):
        transcript = v["transcript"][:MAX_TRANSCRIPT_CHARS] or "(자막 없음)"
        comments = "\n".join(f"- {c[:200]}" for c in v["top_comments"][:30]) or "(댓글 없음)"
        parts.append(
            f"=== 영상 {i} ===\n"
            f"제목: {v['title']}\n채널: {v['channel']}\n업로드: {v['published']}\n"
            f"조회수: {v['views']:,} / 좋아요: {v['likes']:,} / 댓글수: {v['comments']:,}\n"
            f"길이: {v['duration_sec'] // 60}분 {v['duration_sec'] % 60}초\n"
            f"[설명]\n{v['description'][:1500]}\n"
            f"[자막]\n{transcript}\n"
            f"[인기 댓글]\n{comments}\n"
        )
    return "\n".join(parts)


def ask_gemini(api_key: str, model: str, videos: list[dict], history: list[dict], question: str) -> str:
    """history: [{'role': 'user'|'assistant', 'content': str}, ...]"""
    client = genai.Client(api_key=api_key)

    system = (
        "너는 유튜브 영상 분석 도우미야. 아래 영상 데이터(메타데이터, 자막, 댓글)만 근거로 답해.\n"
        "자료에 없는 내용은 모른다고 말하고, 영상을 언급할 땐 '영상 1', '영상 2'처럼 번호나 제목으로 구분해.\n"
        "사용자가 쓰는 언어(기본 한국어)로 답해.\n\n" + build_context(videos)
    )

    contents = [
        types.Content(
            role="model" if m["role"] == "assistant" else "user",
            parts=[types.Part(text=m["content"])],
        )
        for m in history
    ]
    contents.append(types.Content(role="user", parts=[types.Part(text=question)]))

    resp = client.models.generate_content(
        model=model,
        contents=contents,
        config=types.GenerateContentConfig(system_instruction=system, temperature=0.4),
    )
    return resp.text or "(응답이 비어 있어요)"
