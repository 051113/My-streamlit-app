
+import math
+
+
+MOOD_GENRES = {
+    "Comfort": ["Comedy", "Family"],
+    "Laugh": ["Comedy"],
+    "Thrill": ["Thriller", "Action"],
+    "Cry": ["Drama", "Romance"],
+    "Weird": ["Mystery", "Science Fiction"],
+}
+
+
+def build_discover_params(mood_text, energy, time_available, tighten_runtime, genre_map):
+    name_to_id = genre_map["name_to_id"]
+    mood_key = _detect_mood_key(mood_text)
+    mood_genres = MOOD_GENRES.get(mood_key, [])
+    genre_ids = [name_to_id.get(genre) for genre in mood_genres]
+    genre_ids = [genre_id for genre_id in genre_ids if genre_id]
+
+    runtime_limit = time_available + 10
+    if energy == "Dead" or tighten_runtime:
+        runtime_limit = min(runtime_limit, time_available)
+
+    params = {"with_runtime.lte": runtime_limit}
+
+    if genre_ids:
+        params["with_genres"] = ",".join(str(genre_id) for genre_id in genre_ids)
+
+    if energy == "Dead":
+        horror_id = name_to_id.get("Horror")
+        if horror_id:
+            params["without_genres"] = str(horror_id)
+    return params
+
+
+def _detect_mood_key(mood_text):
+    if not mood_text:
+        return None
+    lowered = mood_text.lower()
+    for mood in MOOD_GENRES:
+        if mood.lower() in lowered:
+            return mood
+    return None
+
+
+def pick_tiered_three(candidates, user_state, feedback):
+    penalties = _feedback_penalties(feedback, user_state)
+    mood_key = _detect_mood_key(user_state.get("mood_text", ""))
+
+    available = list(candidates)
+    if not available:
+        return []
+
+    popular = _pick_best(
+        available,
+        lambda movie: popular_score(movie) - _penalty_score(movie, penalties),
+    )
+    picks = [popular] if popular else []
+    available = [movie for movie in available if movie["id"] != popular["id"]] if popular else available
+
+    acclaimed = _pick_best(
+        available,
+        lambda movie: acclaimed_score(movie)
+        + diversity_score(movie, picks)
+        - _penalty_score(movie, penalties),
+    )
+    if acclaimed:
+        picks.append(acclaimed)
+        available = [movie for movie in available if movie["id"] != acclaimed["id"]]
+
+    wildcard = _pick_best(
+        available,
+        lambda movie: wildcard_score(movie, mood_key)
+        + 1.5 * diversity_score(movie, picks)
+        - _penalty_score(movie, penalties),
+    )
+    if wildcard:
+        picks.append(wildcard)
+
+    if len(picks) < 3:
+        ranked = score_candidates(candidates, user_state, feedback)
+        used = {movie["id"] for movie in picks}
+        for movie in ranked:
+            if movie["id"] in used:
+                continue
+            picks.append(movie)
+            used.add(movie["id"])
+            if len(picks) == 3:
+                break
+    return picks[:3]
+
+
+def popular_score(movie):
+    popularity = float(movie.get("popularity") or 0)
+    votes = float(movie.get("vote_count") or 0)
+    rating = float(movie.get("vote_average") or 0)
+    return 0.6 * math.log1p(popularity) + 0.25 * math.log1p(votes) + 0.15 * (rating / 10)
+
+
+def acclaimed_score(movie):
+    rating = float(movie.get("vote_average") or 0)
+    votes = float(movie.get("vote_count") or 0)
+    quality_gate = 0.8 if votes >= 300 else 0.2
+    return 0.7 * (rating / 10) + 0.3 * math.log1p(votes) + quality_gate
+
+
+def wildcard_score(movie, mood_key):
+    rating = float(movie.get("vote_average") or 0)
+    votes = float(movie.get("vote_count") or 0)
+    pop = float(movie.get("popularity") or 0)
+    if mood_key != "Weird" and (votes < 120 or rating < 5.5):
+        return -5.0
+    return 0.45 * (rating / 10) + 0.25 * math.log1p(votes) + 0.3 * (1 / (1 + math.log1p(pop)))
+
+
+def diversity_score(movie, picked):
+    if not picked:
+        return 0.0
+    movie_genres = set(movie.get("genre_ids", []))
+    movie_decade = _decade(movie.get("release_date", ""))
+    score = 0.0
+    for chosen in picked:
+        chosen_genres = set(chosen.get("genre_ids", []))
+        overlap = len(movie_genres & chosen_genres)
+        score -= 0.45 * overlap
+        if movie_decade and movie_decade == _decade(chosen.get("release_date", "")):
+            score -= 0.35
+        else:
+            score += 0.2
+    return score
+
+
+def score_candidates(candidates, user_state, feedback):
+    target_runtime = user_state["time_available"]
+    penalties = _feedback_penalties(feedback, user_state)
+    scored = []
+    for movie in candidates:
+        runtime = movie.get("runtime") or target_runtime
+        runtime_score = 1 - min(abs(runtime - target_runtime) / target_runtime, 1)
+        popularity = math.log1p(movie.get("popularity", 0))
+        rating = movie.get("vote_average", 0) / 10
+        score = 0.4 * runtime_score + 0.3 * rating + 0.3 * popularity
+        score -= _penalty_score(movie, penalties)
+        scored.append((score, movie))
+    scored.sort(key=lambda item: item[0], reverse=True)
+    return [movie for _, movie in scored]
+
+
+def pick_top_three(candidates, user_state, feedback):
+    return pick_tiered_three(candidates, user_state, feedback)
+
+
+def template_reasons(movies, user_state):
+    labels = ["Popular pick", "Critically acclaimed pick", "Wild card pick"]
+    reasons = {}
+    for idx, movie in enumerate(movies):
+        label = labels[idx] if idx < len(labels) else "Tonight's pick"
+        genre = movie.get("genres", ["good"])[0]
+        runtime = movie.get("runtime") or user_state["time_available"]
+        reason = f"{label}: {genre} choice that fits tonight in about {runtime} min."
+        reasons[movie["id"]] = reason[:140]
+    return reasons
+
+
+def is_tiered_order(selected_movies):
+    if len(selected_movies) != 3:
+        return False
+    pop, acclaimed, wildcard = selected_movies
+
+    pop_ok = popular_score(pop) >= popular_score(acclaimed) * 0.8
+    acclaimed_ok = acclaimed_score(acclaimed) >= acclaimed_score(pop) * 0.9
+    wildcard_diverse = diversity_score(wildcard, [pop, acclaimed]) >= -0.8
+    return pop_ok and acclaimed_ok and wildcard_diverse
+
+
+def _feedback_penalties(feedback, user_state):
+    penalties = {}
+    mood_words = set(user_state["mood_text"].lower().split())
+    for entry in feedback[-20:]:
+        if entry.get("result") != "no":
+            continue
+        if entry.get("energy") != user_state["energy"]:
+            continue
+        entry_words = set(entry.get("mood_text", "").lower().split())
+        if mood_words and not (mood_words & entry_words):
+            continue
+        for genre_id in entry.get("genre_ids", []):
+            penalties[genre_id] = penalties.get(genre_id, 0) + 0.15
+    return penalties
+
+
+def _pick_best(candidates, scorer):
+    if not candidates:
+        return None
+    return max(candidates, key=scorer)
+
+
+def _penalty_score(movie, penalties):
+    return sum(penalties.get(genre_id, 0) for genre_id in movie.get("genre_ids", []))
+
+
+def _decade(release_date):
+    if not release_date or len(release_date) < 4:
+        return None
+    try:
+        year = int(release_date[:4])
+    except ValueError:
+        return None
+    return year - (year % 10)
