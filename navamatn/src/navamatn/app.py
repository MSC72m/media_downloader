from openai import OpenAI

from navamatn.core.config import get_settings
from navamatn.modules.summarize import OpenAISummarizer
from navamatn.modules.transcribe import OpenAITranscriber
from navamatn.pipeline.run_pipeline import run_pipeline


def run_app_pipeline(audio_path: str, language_hint: str | None = None):
    settings = get_settings()
    client = OpenAI(api_key=settings.openai_api_key)

    transcriber = OpenAITranscriber(client=client, model=settings.transcription_model)
    summarizer = OpenAISummarizer(client=client, model=settings.summary_model)

    return run_pipeline(
        audio_path=audio_path,
        transcriber=transcriber,
        summarizer=summarizer,
        language_hint=language_hint,
    )
