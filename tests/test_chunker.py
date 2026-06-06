import pytest

from src.chunker import chunk_transcript


def test_short_transcript_returns_one_chunk_unchanged():
    text = "Avi: Hello\nSam: Hi"

    assert chunk_transcript(text, max_chars=100) == [text]


def test_long_transcript_returns_multiple_chunks():
    text = "\n".join(f"Line {index}" for index in range(10))

    chunks = chunk_transcript(text, max_chars=20)

    assert len(chunks) > 1


def test_no_chunk_exceeds_max_chars():
    text = "\n".join(f"Line {index}" for index in range(20))

    chunks = chunk_transcript(text, max_chars=25)

    assert all(len(chunk) <= 25 for chunk in chunks)


def test_line_order_is_preserved():
    lines = [f"Line {index}" for index in range(10)]
    text = "\n".join(lines)

    chunks = chunk_transcript(text, max_chars=20)

    assert "\n".join(chunks).splitlines() == lines


def test_empty_input_returns_empty_list():
    assert chunk_transcript("") == []


def test_very_long_single_line_is_split_safely():
    text = "a" * 25

    chunks = chunk_transcript(text, max_chars=10)

    assert chunks == ["a" * 10, "a" * 10, "a" * 5]
    assert "".join(chunks) == text
    assert all(len(chunk) <= 10 for chunk in chunks)


def test_max_chars_must_be_positive():
    with pytest.raises(ValueError):
        chunk_transcript("Avi: Hello", max_chars=0)
