import datetime

import streamlit as st

import openai_picker
import recommender
import storage
import tmdb_client


st.set_page_config(page_title="3 Picks Tonight", page_icon="🎬", layout="centered")

TMDB_API_KEY = st.secrets.get("TMDB_API_KEY")
OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY")

st.title("🎬 3 Picks Tonight")
st.caption("Exactly three choices. Zero scrolling.")

if not TMDB_API_KEY:
    st.error(
        "TMDB API key is missing. Add it in Streamlit Community Cloud → Settings → Secrets."
    )
    st.stop()

if not OPENAI_API_KEY:
    st.warning("OpenAI key not found. Using heuristic picks instead of AI reasons.")

today_key = datetime.date.today().isoformat()
st.session_state.setdefault("refresh_count", {})
st.session_state.setdefault("seen_tmdb_ids", set())
st.session_state.setdefault("current_picks", [])
st.session_state.setdefault("current_reasons", {})
st.session_state.setdefault("highlight_id", None)
st.session_state.setdefault("picked_id", None)
st.session_state.setdefault("mood_text", "")
st.session_state.setdefault("candidate_count", 0)


def set_mood_text(text):
    st.session_state.mood_text = text


with st.form("inputs"):
    st.text_input(
        "In one sentence, what do you want tonight?",
        key="mood_text",
        placeholder="Something cozy and uplifting.",
    )
    time_available = st.slider("Time available (minutes)", 60, 240, 120, 5)
    energy = st.radio("Energy", ["Dead", "Okay", "Ready"], horizontal=True)
    language = st.radio("Language", ["en-US", "ko-KR"], horizontal=True)
    tighten_runtime = st.toggle("Tighten to shorter runtime", value=False)

    mood_cols = st.columns(5)
    mood_cols[0].button("Comfort", on_click=set_mood_text, args=("Comfort",))
    mood_cols[1].button("Laugh", on_click=set_mood_text, args=("Laugh",))
    mood_cols[2].button("Thrill", on_click=set_mood_text, args=("Thrill",))
    mood_cols[3].button("Cry", on_click=set_mood_text, args=("Cry",))
    mood_cols[4].button("Weird", on_click=set_mood_text, args=("Weird",))

    submitted = st.form_submit_button("Get 3 picks")


def compute_picks(force_refresh=False):
    refresh_count = st.session_state.refresh_count.get(today_key, 0)
    if force_refresh and refresh_count >= 3:
        st.info("Daily refresh limit reached. Try again tomorrow.")
        return

    try:
        genre_map = tmdb_client.get_genre_map(TMDB_API_KEY, language)
        params = recommender.build_discover_params(
            mood_text=st.session_state.mood_text,
            energy=energy,
            time_available=time_available,
            tighten_runtime=tighten_runtime,
            genre_map=genre_map,
        )
        discover_pool = tmdb_client.discover_movies(TMDB_API_KEY, language, params)
    except RuntimeError:
        st.error("Could not reach TMDB. Please try again.")
        return
    candidates = []
    for movie in discover_pool:
        if movie["id"] in st.session_state.seen_tmdb_ids:
            continue
        try:
            details = tmdb_client.get_movie_details(
                TMDB_API_KEY, movie["id"], language
            )
        except RuntimeError:
            continue
        if not details:
            continue
        candidates.append(details)
        if len(candidates) >= 60:
            break

    feedback = storage.read_feedback()
    user_state = {
        "mood_text": st.session_state.mood_text,
        "time_available": time_available,
        "energy": energy,
        "language": language,
    }

    st.session_state.candidate_count = len(candidates)
    if len(candidates) < 3:
        st.error("Not enough movies matched your filters. Try adjusting them.")
        return

    picks, reasons, highlight_id = openai_picker.pick_movies(
        candidates=candidates[:30],
        user_state=user_state,
        openai_api_key=OPENAI_API_KEY,
        feedback=feedback,
    )

    st.session_state.current_picks = picks
    st.session_state.current_reasons = reasons
    st.session_state.highlight_id = highlight_id
    st.session_state.picked_id = None
    st.session_state.seen_tmdb_ids.update([movie["id"] for movie in picks])

    if force_refresh:
        st.session_state.refresh_count[today_key] = refresh_count + 1


if submitted:
    compute_picks(force_refresh=False)

refresh_clicked = st.button("🔄 Refresh 3 picks")
if refresh_clicked:
    compute_picks(force_refresh=True)


st.markdown(
    """
    <style>
    .movie-card {
        border: 2px solid #e6e6e6;
        border-radius: 12px;
        padding: 12px;
        margin-bottom: 16px;
    }
    .movie-card.recommended {
        border-color: #ff4b4b;
        box-shadow: 0 0 0 2px rgba(255, 75, 75, 0.2);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

if st.session_state.current_picks:
    cols = st.columns(3)
    for col, movie in zip(cols, st.session_state.current_picks):
        with col:
            recommended = movie["id"] == st.session_state.highlight_id
            class_name = "movie-card recommended" if recommended else "movie-card"
            st.markdown(f'<div class="{class_name}">', unsafe_allow_html=True)
            poster_url = tmdb_client.get_poster_url(movie.get("poster_path"))
            if poster_url:
                st.image(poster_url, use_column_width=True)
            else:
                st.image(
                    "https://via.placeholder.com/500x750?text=No+Poster",
                    use_column_width=True,
                )

            title = movie["title"]
            year = movie.get("release_date", "")[:4]
            st.subheader(f"{title} ({year})")
            runtime = movie.get("runtime") or "—"
            st.caption(f"Runtime: {runtime} min")
            genres = ", ".join(movie.get("genres", [])) or "—"
            st.caption(f"Genres: {genres}")
            reason = st.session_state.current_reasons.get(movie["id"], "A solid pick.")
            st.write(reason)

            trailer_url = tmdb_client.get_trailer_url(
                TMDB_API_KEY, movie["id"], language
            )
            if trailer_url:
                st.video(trailer_url)
            else:
                st.info("Trailer not available.")

            if st.button("Pick this", key=f"pick-{movie['id']}"):
                st.session_state.picked_id = movie["id"]

            st.markdown("</div>", unsafe_allow_html=True)

    if st.session_state.picked_id:
        picked_movie = next(
            (m for m in st.session_state.current_picks if m["id"] == st.session_state.picked_id),
            None,
        )
        if picked_movie:
            st.success("Ready? Press play.")
            feedback_choice = st.radio(
                "Did this fit your mood tonight?", ["Yes", "No"], horizontal=True
            )
            if st.button("Save feedback"):
                storage.save_feedback(
                    tmdb_id=picked_movie["id"],
                    mood_text=st.session_state.mood_text,
                    time_available=time_available,
                    energy=energy,
                    result=feedback_choice.lower(),
                    genre_ids=picked_movie.get("genre_ids", []),
                )
                st.toast("Thanks for the feedback!")


with st.sidebar:
    with st.expander("Diagnostics"):
        st.write(f"TMDB key loaded: {bool(TMDB_API_KEY)}")
        st.write(f"OpenAI key loaded: {bool(OPENAI_API_KEY)}")
        st.write(
            f"Refresh count today: {st.session_state.refresh_count.get(today_key, 0)}"
        )
        st.write(f"Candidates fetched: {st.session_state.candidate_count}")
        st.write(f"Seen ids count: {len(st.session_state.seen_tmdb_ids)}")
