import math


MOOD_GENRES = {
    "Comfort": ["Comedy", "Family"],
    "Laugh": ["Comedy"],
    "Thrill": ["Thriller", "Action"],
    "Cry": ["Drama", "Romance"],
    "Weird": ["Mystery", "Science Fiction"],
}


def build_discover_params(mood_text, energy, time_available, tighten_runtime, genre_map):
    name_to_id = genre_map["name_to_id"]
    mood_key = _detect_mood_key(mood_text)
    mood_genres = MOOD_GENRES.get(mood_key, [])
    genre_ids = [name_to_id.get(genre) for genre in mood_genres]
    genre_ids = [genre_id for genre_id in genre_ids if genre_id]

    runtime_limit = time_available + 10
    if energy == "Dead" or tighten_runtime:
        runtime_limit = min(runtime_limit, time_available)

    params = {"with_runtime.lte": runtime_limit}

    if genre_ids:
        params["with_genres"] = ",".join(str(genre_id) for genre_id in genre_ids)

    if energy == "Dead":
        horror_id = name_to_id.get("Horror")
        if horror_id:
            params["without_genres"] = str(horror_id)
    return params


def _detect_mood_key(mood_text):
    if not mood_text:
        return None
    lowered = mood_text.lower()
    for mood in MOOD_GENRES:
        if mood.lower() in lowered:
            return mood
    return None


def score_candidates(candidates, user_state, feedback):
    target_runtime = user_state["time_available"]
    penalties = _feedback_penalties(feedback, user_state)
    scored = []
    for movie in candidates:
        runtime = movie.get("runtime") or target_runtime
        runtime_score = 1 - min(abs(runtime - target_runtime) / target_runtime, 1)
        popularity = math.log1p(movie.get("popularity", 0))
        rating = movie.get("vote_average", 0) / 10
        score = 0.4 * runtime_score + 0.3 * rating + 0.3 * popularity
        for genre_id in movie.get("genre_ids", []):
            score -= penalties.get(genre_id, 0)
        scored.append((score, movie))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [movie for _, movie in scored]


def pick_top_three(candidates, user_state, feedback):
    ranked = score_candidates(candidates, user_state, feedback)
    picks = []
    used_genres = set()
    for movie in ranked:
        movie_genres = set(movie.get("genre_ids", []))
        if used_genres and movie_genres.issubset(used_genres):
            continue
        picks.append(movie)
        used_genres.update(movie_genres)
        if len(picks) == 3:
            break
    if len(picks) < 3:
        picks = ranked[:3]
    return picks


def template_reasons(movies, user_state):
    mood = user_state["mood_text"] or "your"
    reasons = {}
    for movie in movies:
        genre = movie.get("genres", ["good"])[0]
        runtime = movie.get("runtime") or user_state["time_available"]
        reason = f"{genre} pick that fits {mood} in about {runtime} min."
        reasons[movie["id"]] = reason[:140]
    return reasons


def _feedback_penalties(feedback, user_state):
    penalties = {}
    mood_words = set(user_state["mood_text"].lower().split())
    for entry in feedback[-20:]:
        if entry.get("result") != "no":
            continue
        if entry.get("energy") != user_state["energy"]:
            continue
        entry_words = set(entry.get("mood_text", "").lower().split())
        if mood_words and not (mood_words & entry_words):
            continue
        for genre_id in entry.get("genre_ids", []):
            penalties[genre_id] = penalties.get(genre_id, 0) + 0.15
    return penalties
