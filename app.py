import datetime

import streamlit as st

import openai_picker
import recommender
import storage
import tmdb_client


st.set_page_config(page_title="3 Movie Picks", layout="centered")

with st.sidebar:
    TMDB_API_KEY = st.text_input("TMDB API Key", type="password")
    OPENAI_API_KEY = st.text_input("OpenAI API Key (optional)", type="password")

today_key = datetime.date.today().isoformat()
st.session_state.setdefault("refresh_count", {})
st.session_state.setdefault("seen_tmdb_ids", set())
st.session_state.setdefault("current_picks", [])
st.session_state.setdefault("current_reasons", {})
st.session_state.setdefault("highlight_id", None)
st.session_state.setdefault("picker_source", "unknown")
st.session_state.setdefault("picked_id", None)
st.session_state.setdefault("mood_text", "")
st.session_state.setdefault("time_available", 120)
st.session_state.setdefault("energy", "Okay")
st.session_state.setdefault("language", "en-US")
st.session_state.setdefault("tighten_runtime", False)
st.session_state.setdefault("candidate_count", 0)
st.session_state.setdefault("authenticated", False)
st.session_state.setdefault("user_id", None)
st.session_state.setdefault("user_email", None)
st.session_state.setdefault("ui_korean", False)


UI_TEXT = {
    "title": {"en": "3 Movie Picks", "ko": "3 Movie Picks"},
    "caption": {"en": "Exactly three choices. Zero scrolling.", "ko": "Exactly three choices. Zero scrolling."},
    "tmdb_missing": {
        "en": "TMDB API key is missing. Add it in Streamlit Community Cloud Settings Secrets.",
        "ko": "TMDB API key is missing. Add it in Streamlit Community Cloud Settings Secrets.",
    },
    "openai_missing": {
        "en": "OpenAI key not found. Using heuristic picks instead of AI reasons.",
        "ko": "OpenAI key not found. Using heuristic picks instead of AI reasons.",
    },
    "mood_comfort": {"en": "Comfort", "ko": "Comfort"},
    "mood_laugh": {"en": "Laugh", "ko": "Laugh"},
    "mood_thrill": {"en": "Thrill", "ko": "Thrill"},
    "mood_cry": {"en": "Cry", "ko": "Cry"},
    "mood_weird": {"en": "Weird", "ko": "Weird"},
    "mood_comfort_desc": {
        "en": "Something cozy, gentle, and reassuring.",
        "ko": "Something cozy, gentle, and reassuring.",
    },
    "mood_laugh_desc": {
        "en": "I want something light, funny, and easy to enjoy.",
        "ko": "I want something light, funny, and easy to enjoy.",
    },
    "mood_thrill_desc": {
        "en": "I want a tense, exciting story with some adrenaline.",
        "ko": "I want a tense, exciting story with some adrenaline.",
    },
    "mood_cry_desc": {
        "en": "I want an emotional, heartfelt movie that can move me.",
        "ko": "I want an emotional, heartfelt movie that can move me.",
    },
    "mood_weird_desc": {
        "en": "I want something unusual, offbeat, and a little strange.",
        "ko": "I want something unusual, offbeat, and a little strange.",
    },
    "input_prompt": {
        "en": "In one sentence, what do you want tonight?",
        "ko": "In one sentence, what do you want tonight?",
    },
    "input_placeholder": {"en": "Something cozy and uplifting.", "ko": "Something cozy and uplifting."},
    "time_available": {"en": "Time available (minutes)", "ko": "Time available (minutes)"},
    "energy": {"en": "Energy", "ko": "Energy"},
    "energy_dead": {"en": "Dead", "ko": "Dead"},
    "energy_okay": {"en": "Okay", "ko": "Okay"},
    "energy_ready": {"en": "Ready", "ko": "Ready"},
    "language": {"en": "Language", "ko": "Language"},
    "tighten_runtime": {"en": "Tighten to shorter runtime", "ko": "Tighten to shorter runtime"},
    "get_picks": {"en": "Get 3 picks", "ko": "Get 3 picks"},
    "login_required": {"en": "Please log in to get personalized picks.", "ko": "Please log in to get personalized picks."},
    "daily_limit": {"en": "Daily refresh limit reached. Try again tomorrow.", "ko": "Daily refresh limit reached. Try again tomorrow."},
    "tmdb_unreachable": {"en": "Could not reach TMDB. Please try again.", "ko": "Could not reach TMDB. Please try again."},
    "not_enough_movies": {
        "en": "Not enough movies matched your filters. Try adjusting them.",
        "ko": "Not enough movies matched your filters. Try adjusting them.",
    },
    "refresh_picks": {"en": "Refresh 3 Picks", "ko": "Refresh 3 Picks"},
    "runtime_caption": {"en": "Runtime: {runtime} min", "ko": "Runtime: {runtime} min"},
    "genres_caption": {"en": "Genres: {genres}", "ko": "Genres: {genres}"},
    "default_reason": {"en": "A solid pick.", "ko": "A solid pick."},
    "rating_caption": {
        "en": "TMDB rating: {rating}/10 ({votes} votes)",
        "ko": "TMDB rating: {rating}/10 ({votes} votes)",
    },
    "trailer_unavailable": {"en": "Trailer not available.", "ko": "Trailer not available."},
    "pick_this": {"en": "Pick this", "ko": "Pick this"},
    "fit_mood": {"en": "Did this fit your mood tonight?", "ko": "Did this fit your mood tonight?"},
    "yes": {"en": "Yes", "ko": "Yes"},
    "no": {"en": "No", "ko": "No"},
    "save_feedback": {"en": "Save feedback", "ko": "Save feedback"},
    "thanks_feedback": {"en": "Thanks for the feedback!", "ko": "Thanks for the feedback!"},
    "account": {"en": "Account", "ko": "Account"},
    "logged_in_as": {"en": "Logged in as {email}", "ko": "Logged in as {email}"},
    "logout": {"en": "Logout", "ko": "Logout"},
    "login_tab": {"en": "Login", "ko": "Login"},
    "register_tab": {"en": "Register", "ko": "Register"},
    "email": {"en": "Email", "ko": "Email"},
    "password": {"en": "Password", "ko": "Password"},
    "login": {"en": "Login", "ko": "Login"},
    "create_account": {"en": "Create account", "ko": "Create account"},
    "login_failed": {"en": "Login failed. Check your email and password.", "ko": "Login failed. Check your email and password."},
    "register_failed": {
        "en": "Registration failed. Email may already exist.",
        "ko": "Registration failed. Email may already exist.",
    },
    "history": {"en": "My history", "ko": "My history"},
    "no_history": {"en": "No history yet.", "ko": "No history yet."},
    "clear_history": {"en": "Clear my history", "ko": "Clear my history"},
    "diagnostics": {"en": "Diagnostics", "ko": "Diagnostics"},
    "tmdb_loaded": {"en": "TMDB key loaded:", "ko": "TMDB key loaded:"},
    "openai_loaded": {"en": "OpenAI key loaded:", "ko": "OpenAI key loaded:"},
    "picker_source": {"en": "Picker source:", "ko": "Picker source:"},
    "refresh_count": {"en": "Refresh count today:", "ko": "Refresh count today:"},
    "candidates": {"en": "Candidates fetched:", "ko": "Candidates fetched:"},
    "seen_ids": {"en": "Seen ids count:", "ko": "Seen ids count:"},
    "ui_toggle": {"en": "Translate page", "ko": "Translate page"},
    "login_notice": {
        "en": "Please use the sidebar to log in and set the language.",
        "ko": "Please use the sidebar to log in and set the language.",
    },
    "event_search": {"en": "search", "ko": "search"},
    "event_pick": {"en": "pick", "ko": "pick"},
    "event_feedback": {"en": "feedback", "ko": "feedback"},
}


def t(key):
    lang = "ko" if st.session_state.get("ui_korean") else "en"
    return UI_TEXT.get(key, {}).get(lang, key)


def translate_event_type(event_type):
    mapping = {
        "search": t("event_search"),
        "pick": t("event_pick"),
        "feedback": t("event_feedback"),
    }
    return mapping.get(event_type, event_type)


st.title(t("title"))
st.caption(t("caption"))

storage.init_db()

if not TMDB_API_KEY:
    st.error("TMDB API key is missing. Enter it in the sidebar.")
    st.stop()

if not OPENAI_API_KEY:
    st.warning("OpenAI key not found. Using heuristic picks instead of AI reasons.")


def reset_user_state():
    st.session_state.seen_tmdb_ids = set()
    st.session_state.current_picks = []
    st.session_state.current_reasons = {}
    st.session_state.highlight_id = None
    st.session_state.picked_id = None
    st.session_state.refresh_count = {}


auth_required = not st.session_state.authenticated
if auth_required:
    st.warning(t("login_notice"))


def set_mood(mood):
    st.session_state.mood_text = mood


mood_cols = st.columns(5)
mood_cols[0].button(
    t("mood_comfort"),
    disabled=auth_required,
    on_click=set_mood,
    args=(t("mood_comfort_desc"),),
)
mood_cols[1].button(
    t("mood_laugh"),
    disabled=auth_required,
    on_click=set_mood,
    args=(t("mood_laugh_desc"),),
)
mood_cols[2].button(
    t("mood_thrill"),
    disabled=auth_required,
    on_click=set_mood,
    args=(t("mood_thrill_desc"),),
)
mood_cols[3].button(
    t("mood_cry"),
    disabled=auth_required,
    on_click=set_mood,
    args=(t("mood_cry_desc"),),
)
mood_cols[4].button(
    t("mood_weird"),
    disabled=auth_required,
    on_click=set_mood,
    args=(t("mood_weird_desc"),),
)

with st.form("inputs"):
    st.text_input(
        t("input_prompt"),
        key="mood_text",
        placeholder=t("input_placeholder"),
        disabled=auth_required,
    )
    st.slider(
        t("time_available"),
        min_value=60,
        max_value=240,
        step=5,
        key="time_available",
        disabled=auth_required,
    )
    energy_options = ["Dead", "Okay", "Ready"]
    energy_labels = {
        "Dead": t("energy_dead"),
        "Okay": t("energy_okay"),
        "Ready": t("energy_ready"),
    }
    st.radio(
        t("energy"),
        energy_options,
        format_func=lambda value: energy_labels.get(value, value),
        horizontal=True,
        key="energy",
        disabled=auth_required,
    )
    st.radio(
        t("language"),
        ["en-US", "ko-KR"],
        horizontal=True,
        key="language",
        disabled=auth_required,
    )
    st.toggle(
        t("tighten_runtime"),
        key="tighten_runtime",
        disabled=auth_required,
    )

    submitted = st.form_submit_button(t("get_picks"), disabled=auth_required)


def compute_picks(force_refresh=False):
    if not st.session_state.authenticated:
        st.info(t("login_required"))
        return
    tmdb_client.get_genre_map.clear()
    tmdb_client.discover_movies.clear()
    tmdb_client.get_movie_details.clear()
    refresh_count = st.session_state.refresh_count.get(today_key, 0)
    if force_refresh and refresh_count >= 3:
        st.info(t("daily_limit"))
        return

    try:
        genre_map = tmdb_client.get_genre_map(TMDB_API_KEY, st.session_state.language)
        params = recommender.build_discover_params(
            mood_text=st.session_state.mood_text,
            energy=st.session_state.energy,
            time_available=st.session_state.time_available,
            tighten_runtime=st.session_state.tighten_runtime,
            genre_map=genre_map,
        )
        popular_params = dict(params)
        popular_params.update({"sort_by": "popularity.desc", "vote_count.gte": 200})
        popular_pool = tmdb_client.discover_movies(
            TMDB_API_KEY,
            st.session_state.language,
            popular_params,
        )
        acclaimed_params = dict(params)
        acclaimed_params.update({"sort_by": "vote_average.desc", "vote_count.gte": 400})
        acclaimed_pool = tmdb_client.discover_movies(
            TMDB_API_KEY,
            st.session_state.language,
            acclaimed_params,
        )
        merged = popular_pool + acclaimed_pool
        deduped = {}
        for movie in merged:
            deduped[movie["id"]] = movie
        discover_pool = list(deduped.values())
    except RuntimeError:
        st.error(t("tmdb_unreachable"))
        return
    watched_ids = storage.get_user_watched_ids(st.session_state.user_id)
    candidates = []
    for movie in discover_pool:
        if movie["id"] in st.session_state.seen_tmdb_ids:
            continue
        if movie["id"] in watched_ids:
            continue
        try:
            details = tmdb_client.get_movie_details(
                TMDB_API_KEY, movie["id"], st.session_state.language
            )
        except RuntimeError:
            continue
        if not details:
            continue
        candidates.append(details)
        if len(candidates) >= 60:
            break

    feedback = storage.get_user_feedback(st.session_state.user_id)
    user_state = {
        "mood_text": st.session_state.mood_text,
        "time_available": st.session_state.time_available,
        "energy": st.session_state.energy,
        "language": st.session_state.language,
        "ui_language": "ko-KR" if st.session_state.get("ui_korean") else "en-US",
    }

    st.session_state.candidate_count = len(candidates)
    if len(candidates) < 3:
        st.error(t("not_enough_movies"))
        return

    picks, reasons, highlight_id, picker_source = openai_picker.pick_movies_with_source(
        candidates=candidates[:30],
        user_state=user_state,
        openai_api_key=OPENAI_API_KEY,
        feedback=feedback,
    )

    st.session_state.current_picks = picks
    st.session_state.current_reasons = reasons
    st.session_state.highlight_id = highlight_id
    st.session_state.picker_source = picker_source
    st.session_state.picked_id = None
    st.session_state.seen_tmdb_ids.update([movie["id"] for movie in picks])

    if force_refresh:
        st.session_state.refresh_count[today_key] = refresh_count + 1


if submitted:
    storage.log_event(
        st.session_state.user_id,
        "search",
        {
            "mood_text": st.session_state.mood_text,
            "time_available": st.session_state.time_available,
            "energy": st.session_state.energy,
            "language": st.session_state.language,
            "tighten_runtime": st.session_state.tighten_runtime,
        },
    )
    compute_picks(force_refresh=False)

refresh_clicked = st.button(t("refresh_picks"), disabled=auth_required)
if refresh_clicked:
    compute_picks(force_refresh=True)


st.markdown(
    """
    <style>
    .moviecard {
        border: 2px solid #e6e6e6;
        border-radius: 12px;
        padding: 12px;
        margin-bottom: 16px;
    }
    .moviecard.recommended {
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
            class_name = "moviecard recommended" if recommended else "moviecard"
            st.markdown(f'<div class="{class_name}">', unsafe_allow_html=True)
            poster_url = tmdb_client.get_poster_url(movie.get("poster_path"))
            if poster_url:
                st.image(poster_url, use_container_width=True)
            else:
                st.image(
                    "https://via.placeholder.com/500x750?text=NoPoster",
                    use_container_width=True,
                )

            title = movie["title"]
            year = movie.get("release_date", "")[:4]
            st.subheader(f"{title} ({year})")
            runtime = movie.get("runtime") or "TBD"
            st.caption(t("runtime_caption").format(runtime=runtime))
            genres = ", ".join(movie.get("genres", [])) or "TBD"
            st.caption(t("genres_caption").format(genres=genres))
            reason = st.session_state.current_reasons.get(
                movie["id"], t("default_reason")
            )
            st.write(reason)
            rating = movie.get("vote_average", 0)
            vote_count = movie.get("vote_count", 0)
            st.caption(
                t("rating_caption").format(
                    rating=f"{rating:.1f}", votes=f"{vote_count:,}"
                )
            )

            trailer_url = tmdb_client.get_trailer_url(
                TMDB_API_KEY, movie["id"], st.session_state.language
            )
            if trailer_url:
                st.video(trailer_url)
            else:
                st.info(t("trailer_unavailable"))

            if st.button(t("pick_this"), key=f"pick{movie['id']}"):
                st.session_state.picked_id = movie["id"]
                storage.log_event(
                    st.session_state.user_id,
                    "pick",
                    {"tmdb_id": movie["id"], "title": movie["title"]},
                )

            st.markdown("</div>", unsafe_allow_html=True)

    if st.session_state.picked_id:
        picked_movie = next(
            (
                m
                for m in st.session_state.current_picks
                if m["id"] == st.session_state.picked_id
            ),
            None,
        )
        if picked_movie:
            feedback_options = ["Yes", "No"]
            feedback_labels = {"Yes": t("yes"), "No": t("no")}
            feedback_choice = st.radio(
                t("fit_mood"),
                feedback_options,
                format_func=lambda value: feedback_labels.get(value, value),
                horizontal=True,
            )
            if st.button(t("save_feedback")):
                storage.log_event(
                    st.session_state.user_id,
                    "feedback",
                    {
                        "tmdb_id": picked_movie["id"],
                        "mood_text": st.session_state.mood_text,
                        "time_available": st.session_state.time_available,
                        "energy": st.session_state.energy,
                        "result": feedback_choice.lower(),
                        "genre_ids": picked_movie.get("genre_ids", []),
                    },
                )
                st.toast(t("thanks_feedback"))


with st.sidebar:
    st.toggle(t("ui_toggle"), key="ui_korean")
    st.subheader(t("account"))
    if st.session_state.authenticated:
        st.caption(t("logged_in_as").format(email=st.session_state.user_email))
        if st.button(t("logout")):
            st.session_state.authenticated = False
            st.session_state.user_id = None
            st.session_state.user_email = None
            reset_user_state()
            st.rerun()
    else:
        login_tab, register_tab = st.tabs([t("login_tab"), t("register_tab")])
        with login_tab:
            with st.form("login_form"):
                login_email = st.text_input(t("email"), key="login_email")
                login_password = st.text_input(
                    t("password"), type="password", key="login_password"
                )
                login_submit = st.form_submit_button(t("login"))
            if login_submit:
                user = storage.authenticate_user(login_email, login_password)
                if user:
                    st.session_state.authenticated = True
                    st.session_state.user_id = user["id"]
                    st.session_state.user_email = user["email"]
                    reset_user_state()
                    st.rerun()
                else:
                    st.error(t("login_failed"))
        with register_tab:
            with st.form("register_form"):
                register_email = st.text_input(t("email"), key="register_email")
                register_password = st.text_input(
                    t("password"), type="password", key="register_password"
                )
                register_submit = st.form_submit_button(t("create_account"))
            if register_submit:
                user = storage.create_user(register_email, register_password)
                if user:
                    st.session_state.authenticated = True
                    st.session_state.user_id = user["id"]
                    st.session_state.user_email = user["email"]
                    reset_user_state()
                    st.rerun()
                else:
                    st.error(t("register_failed"))

    if st.session_state.authenticated:
        with st.expander(t("history")):
            history = storage.get_user_history(st.session_state.user_id, limit=20)
            if not history:
                st.caption(t("no_history"))
            for entry in history:
                st.write(f"{translate_event_type(entry['event_type'])} - {entry['created_at']}")
                st.caption(entry["payload"])
            if st.button(t("clear_history")):
                storage.clear_user_history(st.session_state.user_id)
                reset_user_state()
                st.rerun()

    with st.expander(t("diagnostics")):
        st.write(f"{t('tmdb_loaded')} {bool(TMDB_API_KEY)}")
        st.write(f"{t('openai_loaded')} {bool(OPENAI_API_KEY)}")
        st.write(f"{t('picker_source')} {st.session_state.picker_source}")
        st.write(
            f"{t('refresh_count')} {st.session_state.refresh_count.get(today_key, 0)}"
        )
        st.write(f"{t('candidates')} {st.session_state.candidate_count}")
        st.write(f"{t('seen_ids')} {len(st.session_state.seen_tmdb_ids)}")
