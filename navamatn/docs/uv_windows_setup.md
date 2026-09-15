# uv setup on windows

1. Install Python 3.14 from python.org.
2. Open PowerShell.
3. Run:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

4. Close and reopen PowerShell.
5. Check uv:

```powershell
uv --version
```

6. In the project folder, run:

```powershell
uv sync
```

7. Start CLI:

```powershell
uv run navamatn-cli .\samples\meeting.wav
```

8. Start UI:

```powershell
uv run streamlit run src/navamatn/ui/streamlit_app.py
```
