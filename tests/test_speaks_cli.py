from __future__ import annotations

from pathlib import Path

import pytest

from experiments import gemini_live_audio


def test_list_voices_prints_supported_catalog(capsys: pytest.CaptureFixture[str]) -> None:
    gemini_live_audio.speak_only_main(["--list-voices"])

    output_lines = capsys.readouterr().out.splitlines()
    assert len(gemini_live_audio.VOICE_CATALOG) == 30
    assert output_lines[0].split() == ["Voice", "Characteristic"]
    assert set(output_lines[1]) == {"-", " "}
    assert len(output_lines) == 32
    assert any(line.split() == ["Puck", "Upbeat"] for line in output_lines)
    assert any(line.split() == ["Fenrir", "Excitable"] for line in output_lines)
    assert any(line.split() == ["Zephyr", "Bright"] for line in output_lines)
    assert any(line.split() == ["Sulafat", "Warm"] for line in output_lines)


def test_help_describes_voice_listing(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit, match="0"):
        gemini_live_audio.speak_only_main(["-h"])

    output = capsys.readouterr().out
    assert "--list-voices" in output
    assert "documented Gemini prebuilt voice catalogue" in output


def test_live_text_routes_selected_voice(monkeypatch: pytest.MonkeyPatch) -> None:
    received: dict[str, object] = {}

    async def fake_live_audio_session(**kwargs: object) -> None:
        received.update(kwargs)

    monkeypatch.setattr(gemini_live_audio, "live_audio_session", fake_live_audio_session)

    gemini_live_audio.speak_only_main(["--voice", "Fenrir", "Hello", "world"])

    assert received == {
        "play_audio": True,
        "save_audio": False,
        "voice_name": "Fenrir",
        "text_to_speak_as_is": "Hello world",
    }


def test_live_text_uses_default_voice(monkeypatch: pytest.MonkeyPatch) -> None:
    received: dict[str, object] = {}

    async def fake_live_audio_session(**kwargs: object) -> None:
        received.update(kwargs)

    monkeypatch.setattr(gemini_live_audio, "live_audio_session", fake_live_audio_session)

    gemini_live_audio.speak_only_main(["Hello"])

    assert received["voice_name"] == "Puck"


def test_wav_file_routes_contents_and_voice(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    input_file = tmp_path / "notes.txt"
    input_file.write_text("File contents", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    received: dict[str, object] = {}

    def fake_client(api_version: str) -> object:
        received["api_version"] = api_version
        return object()

    def fake_synthesize(**kwargs: object) -> None:
        received.update(kwargs)

    monkeypatch.setattr(gemini_live_audio, "_client_for_api_version", fake_client)
    monkeypatch.setattr(gemini_live_audio, "synthesize_tts_to_wav", fake_synthesize)

    gemini_live_audio.speak_only_main(["--wav", "output.wav", "--voice", "Kore", input_file.name])

    assert received["voice"] == "Kore"
    assert received["text_to_speak"] == "File contents"
    assert received["output_wav"] == "output.wav"


def test_list_voices_rejects_input() -> None:
    with pytest.raises(SystemExit, match="2"):
        gemini_live_audio.speak_only_main(["--list-voices", "Hello"])


def test_missing_input_is_an_error() -> None:
    with pytest.raises(SystemExit, match="2"):
        gemini_live_audio.speak_only_main([])


def test_unreadable_file_is_an_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    input_file = tmp_path / "notes.txt"
    input_file.write_text("File contents", encoding="utf-8")

    def fail_read(self: Path, *, encoding: str) -> str:
        raise OSError("read failure")

    monkeypatch.setattr(Path, "read_text", fail_read)

    with pytest.raises(SystemExit, match="2"):
        gemini_live_audio.speak_only_main([str(input_file)])
