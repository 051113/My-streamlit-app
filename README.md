# 3 Picks Tonight

Minimal-decision Streamlit app that shows exactly three movie options based on your mood, time, and energy.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Auth + storage

- Users and per-user events are stored in SQLite at `data/app.db`.
- To reset local data during development, delete `data/app.db`.

## Streamlit Community Cloud secrets

This app expects keys to be stored in Streamlit Secrets.

**Settings → Secrets → paste TOML:**

```toml
TMDB_API_KEY="..."
OPENAI_API_KEY="..."
```

## Notes

- TMDB is the source of truth for movies.
- OpenAI is used to select and describe the three picks. If missing, the app falls back to a heuristic.

## Tests

```bash
python -m unittest discover -s tests
```
