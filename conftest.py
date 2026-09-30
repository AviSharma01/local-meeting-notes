# Root conftest: lets bare `pytest` import `main` and `src` from the project root.
import socket
import sys
import types

import pytest


def refuse_network(*args, **kwargs):
    raise AssertionError("Tests must not open real network connections; use a fake.")


def refuse_whisper(*args, **kwargs):
    raise AssertionError("Tests must not load or download a real whisper model; use a fake.")


@pytest.fixture(autouse=True)
def block_network_and_whisper(monkeypatch):
    """Fail any test that makes a real connection or loads a real whisper model."""
    monkeypatch.setattr(socket.socket, "connect", refuse_network)
    fake_whisper = types.ModuleType("faster_whisper")
    fake_whisper.WhisperModel = refuse_whisper
    fake_whisper.download_model = refuse_whisper
    monkeypatch.setitem(sys.modules, "faster_whisper", fake_whisper)
