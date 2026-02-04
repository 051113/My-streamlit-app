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
        raw_text = _call_openai(candidates, user_state, openai_api_key)
        selected_ids, reasons = _validate_response(raw_text, candidates)
        picks = [movie for movie in candidates if movie["id"] in selected_ids]
        picks.sort(key=lambda movie: selected_ids.index(movie["id"]))
        return picks, reasons, selected_ids[0]
    except Exception:
        # broad fallback to guarantee we always return a 3-tuple
        picks = recommender.pick_top_three(candidates, user_state, feedback)
        reasons = recommender.template_reasons(picks, user_state)
        return picks, reasons, picks[0]["id"]


def _call_openai(candidates, user_state, openai_api_key):
    client = OpenAI(api_key=openai_api_key)

    system_message = (
        "You are a movie curator who minimizes decision fatigue.\n"
        "Select exactly 3 movies from the provided candidate list.\n"
        "Never invent titles or IDs.\n"
        "Return ONLY valid JSON with this shape:\n"
        '{ "selected_ids": [<int>, <int>, <int>], "reasons": { "<id>": "<=140 chars>", ... } }\n'
        "Rules:\n"
        "- selected_ids must contain exactly 3 unique integers.\n"
        "- reasons must include a reason for each selected id.\n"
        "- Each reason must be ONE sentence and <= 140 characters.\n"
        "- Do not include any extra keys."
    )

    user_message = {
        "user_state": user_state,
        "candidates": [
            {
                "tmdb_id": movie["id"],
                "title": movie["title"],
                "year": (movie.get("release_date") or "")[:4],
                "runtime": movie.get("runtime"),
                "genres": movie.get("genres", []),
                "overview": (movie.get("overview") or "")[:240],
                "popularity": movie.get("popularity", 0),
                "vote_average": movie.get("vote_average", 0),
                "vote_count": movie.get("vote_count", 0),
            }
            for movie in candidates
        ],
    }

    response = client.responses.create(
        model=MODEL_NAME,
        input=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": json.dumps(user_message, ensure_ascii=False)},
        ],
        text={"format": {"type": "json_object"}},
    )

    return response.output_text


def _validate_response(raw_text, candidates):
    payload = json.loads(raw_text)

    selected_ids = payload.get("selected_ids", [])
    reasons_obj = payload.get("reasons", {})

    candidate_ids = {movie["id"] for movie in candidates}

    # Validate selected_ids
    if not isinstance(selected_ids, list):
        raise ValueError("selected_ids must be a list")
    if len(selected_ids) != 3 or len(set(selected_ids)) != 3:
        raise ValueError("Invalid selection length")
    if not all(isinstance(mid, int) for mid in selected_ids):
        raise ValueError("selected_ids must contain integers")
    if not all(mid in candidate_ids for mid in selected_ids):
        raise ValueError("Unknown movie id")

    # Validate and normalize reasons
    if not isinstance(reasons_obj, dict):
        raise ValueError("reasons must be an object/dict")

    normalized = {}
    for mid in selected_ids:
        # reasons may come back with string keys
        reason = reasons_obj.get(str(mid)) or reasons_obj.get(mid)
        if not reason or not isinstance(reason, str):
            raise ValueError("Reason missing")
        reason = reason.strip()
        if len(reason) > 140:
            raise ValueError("Reason too long")
        normalized[mid] = reason

    return selected_ids, normalized
