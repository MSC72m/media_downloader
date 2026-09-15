import argparse
import json

from navamatn.app import run_app_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="Audio to text with summary")
    parser.add_argument("audio_path", help="Path to audio file")
    parser.add_argument("--language", default=None, help="Language hint, like en")

    args = parser.parse_args()

    result = run_app_pipeline(audio_path=args.audio_path, language_hint=args.language)

    output = {
        "transcript": result.transcript.text,
        "short_summary": result.summary.short_summary,
        "bullet_points": result.summary.bullet_points,
        "keywords": result.enrichment.keywords,
        "action_items": result.enrichment.action_items,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))
