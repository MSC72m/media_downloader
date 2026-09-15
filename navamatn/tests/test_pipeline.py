from navamatn.core.models import SummaryResult, Transcript
from navamatn.pipeline.run_pipeline import run_pipeline


class FakeTranscriber:
    def transcribe(self, audio):
        _ = audio
        return Transcript(text="Todo: call Ali tomorrow about the budget")


class FakeSummarizer:
    def summarize(self, transcript):
        _ = transcript
        return SummaryResult(short_summary="Call Ali tomorrow", bullet_points=["Budget follow-up"])


def test_run_pipeline_returns_structured_output(tmp_path):
    file_path = tmp_path / "sample.wav"
    file_path.write_bytes(b"abc")

    result = run_pipeline(
        audio_path=file_path,
        transcriber=FakeTranscriber(),
        summarizer=FakeSummarizer(),
    )

    assert result.summary.short_summary == "Call Ali tomorrow"
    assert "call" in result.enrichment.keywords
    assert result.enrichment.action_items == ["Todo: call Ali tomorrow about the budget"]
