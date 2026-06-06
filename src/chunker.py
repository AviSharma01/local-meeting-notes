def chunk_transcript(text: str, max_chars: int = 6000) -> list[str]:
    """Split transcript text into ordered chunks under max_chars."""
    if max_chars < 1:
        raise ValueError("max_chars must be positive.")

    if text == "":
        return []

    if len(text) <= max_chars:
        return [text]

    chunks = []
    current_lines = []

    def flush_current_lines() -> None:
        if current_lines:
            chunks.append("\n".join(current_lines))
            current_lines.clear()

    for line in text.splitlines():
        if len(line) > max_chars:
            flush_current_lines()
            for index in range(0, len(line), max_chars):
                chunks.append(line[index : index + max_chars])
            continue

        candidate_lines = current_lines + [line]
        candidate = "\n".join(candidate_lines)

        if len(candidate) <= max_chars:
            current_lines.append(line)
        else:
            flush_current_lines()
            current_lines.append(line)

    flush_current_lines()

    return [chunk for chunk in chunks if chunk]
