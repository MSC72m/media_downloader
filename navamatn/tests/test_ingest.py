import pytest

from navamatn.modules.ingest import AudioValidationError, validate_audio_input


def test_validate_audio_input_accepts_supported_file(tmp_path):
    file_path = tmp_path / "sample.wav"
    file_path.write_bytes(b"abc")

    result = validate_audio_input(file_path)

    assert result.path == file_path


def test_validate_audio_input_rejects_unknown_extension(tmp_path):
    file_path = tmp_path / "sample.txt"
    file_path.write_bytes(b"abc")

    with pytest.raises(AudioValidationError):
        validate_audio_input(file_path)
