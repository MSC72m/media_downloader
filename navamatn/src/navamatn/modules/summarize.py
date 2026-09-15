from typing import Protocol

from openai import OpenAI

from navamatn.core.models import SummaryResult, Transcript


class Summarizer(Protocol):
    def summarize(self, transcript: Transcript) -> SummaryResult:
        ...


class OpenAISummarizer:
    def __init__(self, client: OpenAI, model: str) -> None:
        self._client = client
        self._model = model

    def summarize(self, transcript: Transcript) -> SummaryResult:
        prompt = (
            "Summarize this transcript in plain language. "
            "Return JSON with keys short_summary and bullet_points.\n\n"
            f"Transcript:\n{transcript.text}"
        )
        response = self._client.responses.create(
            model=self._model,
            input=prompt,
            response_format={"type": "json_object"},
        )
        text = response.output_text

        short_summary = ""
        bullet_points: list[str] = []

        try:
            import json

            payload = json.loads(text)
            short_summary = str(payload.get("short_summary", "")).strip()
            raw_bullets = payload.get("bullet_points", [])
            if isinstance(raw_bullets, list):
                bullet_points = [str(item).strip() for item in raw_bullets if str(item).strip()]
        except Exception:  # noqa: BLE001
            short_summary = text.strip()

        if not short_summary:
            short_summary = "Summary not available"

        return SummaryResult(short_summary=short_summary, bullet_points=bullet_points)
