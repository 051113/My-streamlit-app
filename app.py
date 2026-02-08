import datetime

import streamlit as st

import openai_picker
import recommender
import storage
import tmdb_client


st.set_page_config(page_title="3 Picks Tonight", page_icon="?占쏙옙", layout="centered")

TMDB_API_KEY = st.secrets.get("TMDB_API_KEY")
OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY")

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
    "title": {"en": "3 Movie Picks", "ko": "영화 3편 추천"},
    "caption": {"en": "Exactly three choices. Zero scrolling.", "ko": "딱 3편. 스크롤 없이 끝."},
    "tmdb_missing": {
        "en": "TMDB API key is missing. Add it in Streamlit Community Cloud Settings Secrets.",
        "ko": "TMDB API 키가 없습니다. Streamlit Community Cloud 설정의 Secrets에 추가해 주세요.",
    },
    "openai_missing": {
        "en": "OpenAI key not found. Using heuristic picks instead of AI reasons.",
        "ko": "OpenAI 키가 없습니다. AI 이유 대신 휴리스틱 추천을 사용합니다.",
    },
    "mood_comfort": {"en": "Comfort", "ko": "편안함"},
    "mood_laugh": {"en": "Laugh", "ko": "웃음"},
    "mood_thrill": {"en": "Thrill", "ko": "스릴"},
    "mood_cry": {"en": "Cry", "ko": "눈물"},
    "mood_weird": {"en": "Weird", "ko": "이상함"},
    "mood_comfort_desc": {
        "en": "Something cozy, gentle, and reassuring.",
        "ko": "포근하고 부드럽고 안심되는 영화.",
    },
    "mood_laugh_desc": {
        "en": "I want something light, funny, and easy to enjoy.",
        "ko": "가볍고 재미있고 편하게 볼 수 있는 영화.",
    },
    "mood_thrill_desc": {
        "en": "I want a tense, exciting story with some adrenaline.",
        "ko": "긴장감 있고 짜릿한 이야기.",
    },
    "mood_cry_desc": {
        "en": "I want an emotional, heartfelt movie that can move me.",
        "ko": "감동적이고 울림이 있는 영화.",
    },
    "mood_weird_desc": {
        "en": "I want something unusual, offbeat, and a little strange.",
        "ko": "색다르고 독특하고 조금 이상한 영화.",
    },
    "input_prompt": {
        "en": "In one sentence, what do you want tonight?",
        "ko": "오늘 어떤 영화를 보고 싶은지 한 문장으로 적어주세요.",
    },
    "input_placeholder": {"en": "Something cozy and uplifting.", "ko": "포근하고 uplifting한 영화."},
    "time_available": {"en": "Time available (minutes)", "ko": "가능한 시간 (분)"},
    "energy": {"en": "Energy", "ko": "에너지"},
    "energy_dead": {"en": "Dead", "ko": "방전"},
    "energy_okay": {"en": "Okay", "ko": "보통"},
    "energy_ready": {"en": "Ready", "ko": "충전됨"},
    "language": {"en": "Language", "ko": "언어"},
    "tighten_runtime": {"en": "Tighten to shorter runtime", "ko": "더 짧은 러닝타임으로"},
    "get_picks": {"en": "Get 3 picks", "ko": "3편 추천받기"},
    "login_required": {
        "en": "Please log in to get personalized picks.",
        "ko": "개인화 추천을 보려면 로그인해 주세요.",
    },
    "daily_limit": {
        "en": "Daily refresh limit reached. Try again tomorrow.",
        "ko": "하루 새로고침 한도에 도달했습니다. 내일 다시 시도해 주세요.",
    },
    "tmdb_unreachable": {
        "en": "Could not reach TMDB. Please try again.",
        "ko": "TMDB에 연결할 수 없습니다. 다시 시도해 주세요.",
    },
    "not_enough_movies": {
        "en": "Not enough movies matched your filters. Try adjusting them.",
        "ko": "필터에 맞는 영화가 충분하지 않습니다. 조건을 조정해 보세요.",
    },
    "refresh_picks": {"en": "Refresh 3 Picks", "ko": "3편 다시 고르기"},
    "runtime_caption": {"en": "Runtime: {runtime} min", "ko": "러닝타임: {runtime}분"},
    "genres_caption": {"en": "Genres: {genres}", "ko": "장르: {genres}"},
    "default_reason": {"en": "A solid pick.", "ko": "괜찮은 선택입니다."},
    "rating_caption": {
        "en": "TMDB rating: {rating}/10 ({votes} votes)",
        "ko": "TMDB 평점: {rating}/10 ({votes}명 투표)",
    },
    "trailer_unavailable": {"en": "Trailer not available.", "ko": "예고편이 없습니다."},
    "pick_this": {"en": "Pick this", "ko": "이 영화 선택"},
    "fit_mood": {"en": "Did this fit your mood tonight?", "ko": "오늘의 기분에 맞았나요?"},
    "yes": {"en": "Yes", "ko": "네"},
    "no": {"en": "No", "ko": "아니오"},
    "save_feedback": {"en": "Save feedback", "ko": "피드백 저장"},
    "thanks_feedback": {"en": "Thanks for the feedback!", "ko": "피드백 감사합니다!"},
    "account": {"en": "Account", "ko": "계정"},
    "logged_in_as": {"en": "Logged in as {email}", "ko": "{email}로 로그인됨"},
    "logout": {"en": "Logout", "ko": "로그아웃"},
    "login_tab": {"en": "Login", "ko": "로그인"},
    "register_tab": {"en": "Register", "ko": "회원가입"},
    "email": {"en": "Email", "ko": "이메일"},
    "password": {"en": "Password", "ko": "비밀번호"},
    "login": {"en": "Login", "ko": "로그인"},
    "create_account": {"en": "Create account", "ko": "계정 만들기"},
    "login_failed": {
        "en": "Login failed. Check your email and password.",
        "ko": "로그인 실패. 이메일과 비밀번호를 확인해 주세요.",
    },
    "register_failed": {
        "en": "Registration failed. Email may already exist.",
        "ko": "회원가입 실패. 이미 존재하는 이메일일 수 있습니다.",
    },
    "history": {"en": "My history", "ko": "내 기록"},
    "no_history": {"en": "No history yet.", "ko": "아직 기록이 없습니다."},
    "clear_history": {"en": "Clear my history", "ko": "내 기록 지우기"},
    "diagnostics": {"en": "Diagnostics", "ko": "진단"},
    "tmdb_loaded": {"en": "TMDB key loaded:", "ko": "TMDB 키 로드됨:"},
    "openai_loaded": {"en": "OpenAI key loaded:", "ko": "OpenAI 키 로드됨:"},
    "picker_source": {"en": "Picker source:", "ko": "추천 소스:"},
    "refresh_count": {"en": "Refresh count today:", "ko": "오늘 새로고침 횟수:"},
    "candidates": {"en": "Candidates fetched:", "ko": "가져온 후보 수:"},
    "seen_ids": {"en": "Seen ids count:", "ko": "이미 본 ID 수:"},
    "ui_toggle": {"en": "Translate page / 페이지 번역", "ko": "페이지 번역 / Translate page"},
    "login_notice": {
        "en": "Please use the sidebar to log in and set the language.",
        "ko": "사이드바에서 로그인과 언어설정을 해 주십시오.",
    },
    "event_search": {"en": "search", "ko": "검색"},
    "event_pick": {"en": "pick", "ko": "선택"},
    "event_feedback": {"en": "feedback", "ko": "피드백"},
}


def t(key):
    lang = "ko" if st.session_state.get("ui_korean") else "en"
    return UI_TEXT[key][lang]


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
    st.error(t("tmdb_missing"))
    st.stop()

if not OPENAI_API_KEY:
    st.warning(t("openai_missing"))


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
        borderradius: 12px;
        padding: 12px;
        marginbottom: 16px;
    }
    .moviecard.recommended {
        bordercolor: #ff4b4b;
        boxshadow: 0 0 0 2px rgba(255, 75, 75, 0.2);
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
                st.image(poster_url, width="stretch")
            else:
                st.image(
                    "https://via.placeholder.com/500x750?text=NoPoster",
                    width="stretch",
                )

            title = movie["title"]
            year = movie.get("release_date", "")[:4]
            st.subheader(f"{title} ({year})")
            runtime = movie.get("runtime") or "??"
            st.caption(t("runtime_caption").format(runtime=runtime))
            genres = ", ".join(movie.get("genres", [])) or "??"
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
                st.write(
                    f"{translate_event_type(entry['event_type'])} · {entry['created_at']}"
                )
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
