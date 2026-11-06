import re
import requests
import streamlit as st
from youtube_transcript_api import YouTubeTranscriptApi

API = "https://www.googleapis.com/youtube/v3"


def extract_video_id(url: str):
    """다양한 형태의 유튜브 URL에서 11자리 영상 ID 추출."""
    m = re.search(r"(?:v=|youtu\.be/|shorts/|embed/|live/)([A-Za-z0-9_-]{11})", url.strip())
    return m.group(1) if m else None


def _duration_to_sec(iso: str) -> int:
    m = re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso or "")
    if not m:
        return 0
    h, mi, s = (int(x or 0) for x in m.groups())
    return h * 3600 + mi * 60 + s


@st.cache_data(show_spinner=False, ttl=3600)
def get_video_info(video_id: str, api_key: str):
    r = requests.get(
        f"{API}/videos",
        params={"part": "snippet,statistics,contentDetails", "id": video_id, "key": api_key},
        timeout=10,
    )
    r.raise_for_status()
    items = r.json().get("items", [])
    if not items:
        return None
    it = items[0]
    sn, st_, cd = it["snippet"], it.get("statistics", {}), it["contentDetails"]
    return {
        "id": video_id,
        "title": sn["title"],
        "channel": sn["channelTitle"],
        "published": sn["publishedAt"][:10],
        "thumbnail": sn["thumbnails"].get("medium", {}).get("url"),
        "description": sn.get("description", ""),
        "views": int(st_.get("viewCount", 0)),
        "likes": int(st_.get("likeCount", 0)),
        "comments": int(st_.get("commentCount", 0)),
        "duration_sec": _duration_to_sec(cd.get("duration")),
    }


@st.cache_data(show_spinner=False, ttl=3600)
def get_top_comments(video_id: str, api_key: str, limit: int = 50):
    r = requests.get(
        f"{API}/commentThreads",
        params={
            "part": "snippet", "videoId": video_id, "maxResults": limit,
            "order": "relevance", "textFormat": "plainText", "key": api_key,
        },
        timeout=10,
    )
    if r.status_code != 200:  # 댓글 비활성화 등
        return []
    return [
        i["snippet"]["topLevelComment"]["snippet"]["textDisplay"]
        for i in r.json().get("items", [])
    ]


@st.cache_data(show_spinner=False, ttl=3600)
def get_transcript(video_id: str, languages=("ko", "en")):
    """자막 텍스트 반환. 없으면 빈 문자열."""
    try:
        fetched = YouTubeTranscriptApi().fetch(video_id, languages=list(languages))
        return " ".join(s.text for s in fetched)
    except Exception:
        return ""
