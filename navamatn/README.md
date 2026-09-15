# navamatn

Beginner friendly audio to text pipeline with summary and a simple UI.

## goals

- Keep module boundaries clear.
- Keep each file small.
- Make tasks easy to delegate to juniors.

## stack

- Python 3.14
- uv
- openai
- pydantic
- streamlit
- pytest
- ruff

## quick start

```bash
uv sync
cp .env.example .env
```

Set `NAVAMATN_OPENAI_API_KEY` in `.env`.

Run CLI:

```bash
uv run navamatn-cli ./samples/meeting.wav
```

Run UI:

```bash
uv run streamlit run src/navamatn/ui/streamlit_app.py
```

## project structure

- `src/navamatn/core`: config and data models
- `src/navamatn/modules`: ingest, transcribe, summarize, enrich
- `src/navamatn/pipeline`: orchestration
- `src/navamatn/ui`: streamlit app
- `tests`: starter tests
- `docs`: setup and crash course docs

## docs

- `docs/uv_windows_setup.md`
- `docs/beginner_crash_course.md`
