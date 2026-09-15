from pathlib import Path

from navamatn.core.models import AudioInput

ALLOWED_EXTENSIONS = {".wav", ".mp3", ".m4a", ".flac"}
MAX_SIZE_BYTES = 50 * 1024 * 1024


class AudioValidationError(ValueError):
    pass


def validate_audio_input(path: str | Path, language_hint: str | None = None) -> AudioInput:
    audio_path = Path(path)

    if not audio_path.exists():
        raise AudioValidationError(f"Audio file not found: {audio_path}")

    if audio_path.suffix.lower() not in ALLOWED_EXTENSIONS:
        raise AudioValidationError(
            f"Unsupported file type '{audio_path.suffix}'. Allowed: {sorted(ALLOWED_EXTENSIONS)}"
        )

    if audio_path.stat().st_size > MAX_SIZE_BYTES:
        raise AudioValidationError("Audio file is larger than 50MB")

    return AudioInput(path=audio_path, language_hint=language_hint)
