# beginner crash course

## what each part does

- `modules/ingest.py` checks the file.
- `modules/transcribe.py` turns audio into text.
- `modules/summarize.py` makes a short summary.
- `modules/enrich.py` extracts keywords and action items.
- `pipeline/run_pipeline.py` calls modules in order.
- `ui/streamlit_app.py` is the screen.
- `cli.py` is the terminal command.

## pydantic in one minute

- Pydantic models keep data shape clear.
- If fields are missing or wrong, you get a clear error.
- This helps juniors debug faster.

## openai client in one minute

- Create one `OpenAI` client once.
- Pass that client to transcriber and summarizer.
- Keep API calls inside modules, not inside UI code.

## unslop rules in short

- Use short sentences.
- Use plain words.
- Skip filler lines.
- State one idea per line.
- Do not add style words that do not add facts.

## first tasks for apprentice

1. Add a new allowed audio extension.
2. Add one more test for missing file path.
3. Show transcript word count in UI.
4. Add one config value in `core/config.py` and use it.
5. Add one new enrichment rule and test it.
