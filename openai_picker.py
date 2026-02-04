import json

from openai import OpenAI

import recommender


MODEL_NAME = "gpt-4.1-mini"


def pick_movies(candidates, user_state, openai_api_key, feedback):
    if not candidates:
        return [], {}, None

    if not openai_api_key:
        picks = recommender.pick_top_three(candidates, user_state, feedback)
        reasons = recommender.template_reasons(picks, user_state)
        return picks, reasons, picks[0]["id"]

    try:
        response = _call_openai(candidates, user_state, openai_api_key)
        selected_ids, reasons = _validate_response(response, candidates)
        picks = [movie for movie in candidates if movie["id"] in selected_ids]
        picks.sort(key=lambda movie: selected_ids.index(movie["id"]))
        return picks, reasons, selected_ids[0]
    except (ValueError, RuntimeError, json.JSONDecodeError):
        picks = recommender.pick_top_three(candidates, user_state, feedback)
        reasons = recommender.template_reasons(picks, user_state)
        return picks, reasons, picks[0]["id"]


def _call_openai(candidates, user_state, openai_api_key):
    client = OpenAI(api_key=openai_api_key)
    system_message = (
        "You are a movie curator. Select exactly 3 movies from the provided "
        "candidate list. Never invent titles or IDs. Respond ONLY with JSON."
    )
    user_message = {
        "user_state": user_state,
        "candidates": [
            {
                "tmdb_id": movie["id"],
                "title": movie["title"],
                "year": movie.get("release_date", "")[:4],
                "runtime": movie.get("runtime"),
                "genres": movie.get("genres", []),
                "overview": movie.get("overview", "")[:240],
                "popularity": movie.get("popularity", 0),
                "vote_average": movie.get("vote_average", 0),
                "vote_count": movie.get("vote_count", 0),
            }
            for movie in candidates
        ],
    }
    response = client.responses.create(
        model=MODEL_NAME,
        response_format={"type": "json_object"},
        input=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": json.dumps(user_message)},
        ],
    )
    return response.output_text


def _validate_response(raw_text, candidates):
    payload = json.loads(raw_text)
    selected_ids = payload.get("selected_ids", [])
    reasons = payload.get("reasons", {})
    candidate_ids = {movie["id"] for movie in candidates}
    if len(selected_ids) != 3 or len(set(selected_ids)) != 3:
        raise ValueError("Invalid selection length")
    if not all(movie_id in candidate_ids for movie_id in selected_ids):
        raise ValueError("Unknown movie id")
    for movie_id in selected_ids:
        reason = reasons.get(str(movie_id)) or reasons.get(movie_id)
        if not reason or len(reason) > 140:
            raise ValueError("Reason missing or too long")
        reasons[movie_id] = reason
    return selected_ids, reasons
