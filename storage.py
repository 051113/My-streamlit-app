import datetime
import json
import pathlib
import sqlite3
from contextlib import contextmanager

import bcrypt


DATA_PATH = pathlib.Path("data")
DB_PATH = DATA_PATH / "app.db"


def init_db(db_path=None):
    path = _resolve_db_path(db_path)
    DATA_PATH.mkdir(parents=True, exist_ok=True)
    with _get_conn(path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )


def create_user(email, password, db_path=None):
    if not email or not password:
        return None
    password_hash = _hash_password(password)
    path = _resolve_db_path(db_path)
    with _get_conn(path) as conn:
        try:
            cursor = conn.execute(
                "INSERT INTO users (email, password_hash, created_at) VALUES (?, ?, ?)",
                (email.strip().lower(), password_hash, _now()),
            )
        except sqlite3.IntegrityError:
            return None
        return {"id": cursor.lastrowid, "email": email.strip().lower(), "created_at": _now()}


def authenticate_user(email, password, db_path=None):
    if not email or not password:
        return None
    path = _resolve_db_path(db_path)
    with _get_conn(path) as conn:
        row = conn.execute(
            "SELECT id, email, password_hash, created_at FROM users WHERE email = ?",
            (email.strip().lower(),),
        ).fetchone()
    if not row:
        return None
    if not _verify_password(password, row["password_hash"]):
        return None
    return {"id": row["id"], "email": row["email"], "created_at": row["created_at"]}


def log_event(user_id, event_type, payload, db_path=None):
    path = _resolve_db_path(db_path)
    with _get_conn(path) as conn:
        conn.execute(
            """
            INSERT INTO user_events (user_id, event_type, payload_json, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, event_type, json.dumps(payload), _now()),
        )


def get_user_history(user_id, limit=200, db_path=None):
    path = _resolve_db_path(db_path)
    with _get_conn(path) as conn:
        rows = conn.execute(
            """
            SELECT id, user_id, event_type, payload_json, created_at
            FROM user_events
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
    history = []
    for row in rows:
        try:
            payload = json.loads(row["payload_json"])
        except json.JSONDecodeError:
            payload = {}
        history.append(
            {
                "id": row["id"],
                "user_id": row["user_id"],
                "event_type": row["event_type"],
                "payload": payload,
                "created_at": row["created_at"],
            }
        )
    return history


def get_user_feedback(user_id, db_path=None):
    history = get_user_history(user_id, limit=500, db_path=db_path)
    feedback = []
    for entry in history:
        if entry["event_type"] != "feedback":
            continue
        payload = entry["payload"]
        feedback.append(
            {
                "date": entry["created_at"][:10],
                "tmdb_id": payload.get("tmdb_id"),
                "mood_text": payload.get("mood_text", ""),
                "time_available": payload.get("time_available", 0),
                "energy": payload.get("energy", ""),
                "result": payload.get("result", ""),
                "genre_ids": payload.get("genre_ids", []),
            }
        )
    feedback.reverse()
    return feedback


def get_user_watched_ids(user_id, db_path=None):
    history = get_user_history(user_id, limit=1000, db_path=db_path)
    watched = set()
    for entry in history:
        if entry["event_type"] not in {"pick", "feedback"}:
            continue
        tmdb_id = entry["payload"].get("tmdb_id")
        if tmdb_id:
            watched.add(tmdb_id)
    return watched


def clear_user_history(user_id, db_path=None):
    path = _resolve_db_path(db_path)
    with _get_conn(path) as conn:
        conn.execute("DELETE FROM user_events WHERE user_id = ?", (user_id,))


def read_feedback():
    return []


def save_feedback(*_args, **_kwargs):
    return None


def _resolve_db_path(db_path):
    return pathlib.Path(db_path) if db_path else DB_PATH


def _connect(path):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def _get_conn(path):
    conn = _connect(path)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _hash_password(password):
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_password(password, password_hash):
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def _now():
    return datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds")
