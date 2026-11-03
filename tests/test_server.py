"""The routes with fake models: no weights, and they run anywhere ffmpeg does."""

import numpy as np
import pytest
from fastapi.testclient import TestClient

from wocal import server


class FakeTTS:
    sample_rate = 24000

    def get_state_for_audio_prompt(self, voice):
        return voice

    def generate_audio(self, state, text):
        class Audio:
            def numpy(self):
                return np.zeros(2400, dtype=np.float32)

        return Audio()


class FakeSTT:
    def generate(self, path, chunk_duration):
        class Result:
            text = " hello from the lodge "

        return Result()


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(server, "load_tts", FakeTTS)
    monkeypatch.setattr(server, "load_stt", FakeSTT)
    server.voice_states.clear()
    with TestClient(server.app, base_url="http://127.0.0.1") as test_client:
        yield test_client


def speak(client, **body):
    return client.post("/v1/audio/speech", json={"input": "hello"} | body)


@pytest.mark.parametrize("fmt,content_type", [("wav", "audio/wav"), ("mp3", "audio/mpeg"), ("opus", "audio/ogg")])
def test_speech_formats(client, fmt, content_type):
    response = speak(client, response_format=fmt)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith(content_type)
    assert response.content


@pytest.mark.parametrize("body", [{"input": " "}, {"input": "x" * 4097}, {"voice": "http://x"}, {"response_format": "flac"}])
def test_speech_refuses_bad_requests(client, body):
    assert speak(client, **body).status_code == 400


def test_transcription_round_trip(client):
    audio = speak(client, response_format="opus").content
    response = client.post("/v1/audio/transcriptions", files={"file": ("note.bin", audio)},
                           data={"model": "anything", "response_format": "json"})
    assert response.status_code == 200
    assert response.json() == {"text": "hello from the lodge"}


def test_transcription_refuses_non_audio(client):
    response = client.post("/v1/audio/transcriptions", files={"file": ("note.bin", b"not audio")})
    assert response.status_code == 400


def test_a_failed_model_is_a_clear_error(monkeypatch):
    def broken():
        raise RuntimeError("no weights")

    monkeypatch.setattr(server, "load_tts", broken)
    monkeypatch.setattr(server, "load_stt", FakeSTT)
    with TestClient(server.app, base_url="http://127.0.0.1") as client:
        assert speak(client).status_code == 503
        assert client.get("/health").json()["speech"] == "failed"


def test_foreign_hosts_are_refused(client):
    assert client.get("/health", headers={"host": "evil.example"}).status_code == 400
    assert client.get("/health", headers={"host": "wocal.localhost:7777"}).status_code == 200
