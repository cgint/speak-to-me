from __future__ import annotations

import base64
from types import SimpleNamespace
import wave


def test_synthesize_writes_official_multispeaker_request_and_pcm_wav(tmp_path) -> None:
    from experiments import multispeaker_emotion_tts

    pcm = b"\x00\x00\x01\x00"
    calls: dict[str, object] = {}

    class FakeInteractions:
        def create(self, **kwargs):
            calls.update(kwargs)
            return SimpleNamespace(
                output_audio=SimpleNamespace(data=base64.b64encode(pcm).decode("ascii"))
            )

    client = SimpleNamespace(interactions=FakeInteractions())
    output = tmp_path / "dialogue.wav"

    multispeaker_emotion_tts.synthesize_to_wav(client=client, output_wav=output)

    assert calls == {
        "model": "gemini-3.1-flash-tts-preview",
        "input": multispeaker_emotion_tts.PROMPT,
        "response_format": {"type": "audio"},
        "generation_config": {
            "speech_config": [
                {"speaker": "Speaker1", "voice": "Enceladus"},
                {"speaker": "Speaker2", "voice": "Puck"},
            ]
        },
    }
    with wave.open(str(output), "rb") as audio:
        assert audio.getnchannels() == 1
        assert audio.getsampwidth() == 2
        assert audio.getframerate() == 24000
        assert audio.readframes(audio.getnframes()) == pcm
