from pathlib import Path

from pydantic import BaseModel, Field


class AudioInput(BaseModel):
    path: Path
    language_hint: str | None = None


class Transcript(BaseModel):
    text: str = Field(min_length=1)
    language: str | None = None
    duration_seconds: float | None = None


class SummaryResult(BaseModel):
    short_summary: str = Field(min_length=1)
    bullet_points: list[str] = Field(default_factory=list)


class EnrichmentResult(BaseModel):
    keywords: list[str] = Field(default_factory=list)
    action_items: list[str] = Field(default_factory=list)


class PipelineResult(BaseModel):
    transcript: Transcript
    summary: SummaryResult
    enrichment: EnrichmentResult
