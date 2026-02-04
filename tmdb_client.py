import requests
import streamlit as st


BASE_URL = "https://api.themoviedb.org/3"
IMAGE_BASE = "https://image.tmdb.org/t/p/w500"


def _get(url, params):
    response = requests.get(url, params=params, timeout=10)
    if response.status_code != 200:
        raise RuntimeError(f"TMDB request failed: {response.status_code}")
    return response.json()


@st.cache_data(show_spinner=False, ttl=3600)
def get_genre_map(api_key, language):
    url = f"{BASE_URL}/genre/movie/list"
    data = _get(url, {"api_key": api_key, "language": language})
    name_to_id = {genre["name"]: genre["id"] for genre in data.get("genres", [])}
    id_to_name = {genre["id"]: genre["name"] for genre in data.get("genres", [])}
    return {"name_to_id": name_to_id, "id_to_name": id_to_name}


@st.cache_data(show_spinner=False, ttl=1800)
def discover_movies(api_key, language, params):
    url = f"{BASE_URL}/discover/movie"
    payload = {
        "api_key": api_key,
        "language": language,
        "include_adult": False,
        "sort_by": "popularity.desc",
        "vote_count.gte": 200,
    }
    payload.update(params)
    data = _get(url, payload)
    return data.get("results", [])


@st.cache_data(show_spinner=False, ttl=1800)
def get_movie_details(api_key, movie_id, language):
    url = f"{BASE_URL}/movie/{movie_id}"
    data = _get(url, {"api_key": api_key, "language": language})
    return {
        "id": data["id"],
        "title": data["title"],
        "release_date": data.get("release_date", ""),
        "runtime": data.get("runtime"),
        "overview": data.get("overview", ""),
        "poster_path": data.get("poster_path"),
        "genres": [genre["name"] for genre in data.get("genres", [])],
        "genre_ids": [genre["id"] for genre in data.get("genres", [])],
        "vote_average": data.get("vote_average", 0),
        "vote_count": data.get("vote_count", 0),
        "popularity": data.get("popularity", 0),
    }


@st.cache_data(show_spinner=False, ttl=1800)
def get_movie_videos(api_key, movie_id, language):
    url = f"{BASE_URL}/movie/{movie_id}/videos"
    data = _get(url, {"api_key": api_key, "language": language})
    return data.get("results", [])


def get_trailer_url(api_key, movie_id, language):
    try:
        videos = get_movie_videos(api_key, movie_id, language)
    except RuntimeError:
        return None

    youtube_trailers = [
        video
        for video in videos
        if video.get("site") == "YouTube" and video.get("type") == "Trailer"
    ]
    if not youtube_trailers:
        return None

    youtube_trailers.sort(
        key=lambda v: "official" in v.get("name", "").lower(), reverse=True
    )
    key = youtube_trailers[0].get("key")
    if not key:
        return None
    return f"https://www.youtube.com/watch?v={key}"


def get_poster_url(poster_path):
    if not poster_path:
        return None
    return f"{IMAGE_BASE}{poster_path}"
