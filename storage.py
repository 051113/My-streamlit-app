import datetime
import json
import pathlib


DATA_PATH = pathlib.Path("data")
FEEDBACK_FILE = DATA_PATH / "feedback.json"


def read_feedback():
    if not FEEDBACK_FILE.exists():
        return []
    try:
        return json.loads(FEEDBACK_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []


def save_feedback(tmdb_id, mood_text, time_available, energy, result, genre_ids=None):
    DATA_PATH.mkdir(parents=True, exist_ok=True)
    feedback = read_feedback()
    feedback.append(
        {
            "date": _today(),
            "tmdb_id": tmdb_id,
            "mood_text": mood_text,
            "time_available": time_available,
            "energy": energy,
            "result": result,
            "genre_ids": genre_ids or [],
        }
    )
    FEEDBACK_FILE.write_text(json.dumps(feedback, indent=2), encoding="utf-8")


def _today():
    return datetime.date.today().isoformat()
