from src.transcript_cleaner import clean_transcript


def test_clean_transcript_removes_empty_lines():
    text = "Avi: Hello\n\n\nSam: Hi\n   \nPriya: Ready"

    assert clean_transcript(text) == "Avi: Hello\nSam: Hi\nPriya: Ready"


def test_clean_transcript_normalizes_extra_spaces():
    text = "  Avi:   We   should   start.  "

    assert clean_transcript(text) == "Avi: We should start."


def test_clean_transcript_preserves_timestamps():
    text = "  [00:12]   Avi:   Quick update.  "

    assert clean_transcript(text) == "[00:12] Avi: Quick update."


def test_clean_transcript_preserves_speaker_names():
    text = "  Avi:   I can take that.  "

    assert clean_transcript(text).startswith("Avi:")


def test_clean_transcript_handles_empty_input():
    assert clean_transcript("") == ""
    assert clean_transcript(" \n \t\n") == ""
