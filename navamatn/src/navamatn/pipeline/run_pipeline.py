from pathlib import Path

from navamatn.core.models import PipelineResult
from navamatn.modules.enrich import enrich_transcript
from navamatn.modules.ingest import validate_audio_input
from navamatn.modules.summarize import Summarizer
from navamatn.modules.transcribe import Transcriber


def run_pipeline(
    audio_path: str | Path,
    transcriber: Transcriber,
    summarizer: Summarizer,
    language_hint: str | None = None,
) -> PipelineResult:
    audio_input = validate_audio_input(audio_path, language_hint=language_hint)
    transcript = transcriber.transcribe(audio_input)
    summary = summarizer.summarize(transcript)
    enrichment = enrich_transcript(transcript)
    return PipelineResult(transcript=transcript, summary=summary, enrichment=enrichment)
