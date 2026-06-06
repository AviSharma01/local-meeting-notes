def clean_transcript(text: str) -> str:
    """Normalize transcript whitespace while preserving line order."""
    cleaned_lines = []

    for line in text.splitlines():
        stripped_line = line.strip()
        if not stripped_line:
            continue

        cleaned_lines.append(" ".join(stripped_line.split()))

    return "\n".join(cleaned_lines)
