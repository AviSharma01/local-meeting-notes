from pathlib import Path

import requests


OLLAMA_GENERATE_URL = "http://localhost:11434/api/generate"
PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "meeting_summary_prompt.md"


def generate_meeting_notes(transcript: str, model: str = "qwen2.5:7b") -> str:
    """Generate Markdown meeting notes using a local Ollama model."""
    if not transcript.strip():
        raise ValueError("Transcript cannot be empty.")

    prompt_template = PROMPT_PATH.read_text(encoding="utf-8")
    prompt = prompt_template.replace("{{ transcript }}", transcript)

    try:
        response = requests.post(
            OLLAMA_GENERATE_URL,
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=60,
        )
        response.raise_for_status()
    except requests.RequestException as error:
        raise RuntimeError("Ollama request failed. Is Ollama running locally?") from error

    try:
        response_data = response.json()
        generated_text = response_data["response"]
    except (ValueError, KeyError, TypeError) as error:
        raise RuntimeError("Ollama returned an invalid response.") from error

    return generated_text
