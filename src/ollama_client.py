import math
import os
from pathlib import Path
from urllib.parse import urlparse

import requests
from pydantic import BaseModel, ValidationError

from src.models import DebriefExtraction, MeetingExtraction


DEFAULT_MODEL = "qwen2.5:14b"
DEFAULT_OLLAMA_HOST = "http://localhost:11434"
DEFAULT_OLLAMA_PORT = 11434
LOOPBACK_HOSTS = {"localhost", "127.0.0.1", "::1"}
NUM_CTX = 8192
RESPONSE_TOKEN_RESERVE = 2048
REQUEST_TIMEOUT_SECONDS = 300
PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "meeting_summary_prompt.md"
DEBRIEF_PROMPT_PATH = PROMPT_PATH.parent / "debrief_prompt.md"

# Ignore proxy environment variables so no proxy can route a transcript off this machine.
SESSION = requests.Session()
SESSION.trust_env = False


def ollama_base_url() -> str:
    """Read the Ollama base URL from OLLAMA_HOST, allowing only loopback hosts."""
    host = os.environ.get("OLLAMA_HOST", "").strip() or DEFAULT_OLLAMA_HOST
    if "://" not in host:
        host = f"http://{host}"

    parsed = urlparse(host)
    if parsed.hostname not in LOOPBACK_HOSTS:
        raise ValueError(
            f"OLLAMA_HOST must point to this machine (localhost, 127.0.0.1, or ::1); got {host}."
        )

    if parsed.port is None:
        host = parsed._replace(netloc=f"{parsed.netloc}:{DEFAULT_OLLAMA_PORT}").geturl()

    return host.rstrip("/")


def estimate_tokens(text: str) -> int:
    """Roughly estimate token count at four characters per token."""
    return math.ceil(len(text) / 4)


def extract_meeting(transcript: str, model: str = DEFAULT_MODEL) -> MeetingExtraction:
    """Extract validated meeting data from a transcript using a local Ollama model."""
    return _extract(transcript, model, PROMPT_PATH, MeetingExtraction, "meeting")


def extract_debrief(transcript: str, model: str = DEFAULT_MODEL) -> DebriefExtraction:
    """Extract validated debrief data from a voice-memo transcript using a local Ollama model."""
    return _extract(transcript, model, DEBRIEF_PROMPT_PATH, DebriefExtraction, "debrief")


def _extract(
    transcript: str,
    model: str,
    prompt_path: Path,
    schema: type[BaseModel],
    label: str,
) -> BaseModel:
    if not transcript.strip():
        raise ValueError("Transcript cannot be empty.")

    prompt_template = prompt_path.read_text(encoding="utf-8")
    prompt = prompt_template.replace("{{ transcript }}", transcript)

    estimated_tokens = estimate_tokens(prompt)
    token_budget = NUM_CTX - RESPONSE_TOKEN_RESERVE
    if estimated_tokens > token_budget:
        raise ValueError(
            f"Transcript is too long: the prompt is about {estimated_tokens} tokens, "
            f"over the {token_budget}-token budget. Chunking is not implemented; "
            "split the transcript and summarize each part."
        )

    generate_url = f"{ollama_base_url()}/api/generate"

    try:
        return schema.model_validate_json(_generate(generate_url, model, prompt))
    except ValidationError as error:
        retry_prompt = (
            f"{prompt}\n\n"
            f"Your previous response was invalid:\n{error}\n\n"
            "Return only a JSON object with exactly the fields described above."
        )

    try:
        return schema.model_validate_json(_generate(generate_url, model, retry_prompt))
    except ValidationError as error:
        raise RuntimeError(
            f"Ollama returned invalid {label} JSON after one retry.\n{error}"
        ) from error


def _generate(url: str, model: str, prompt: str) -> str:
    try:
        response = SESSION.post(
            url,
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "options": {"num_ctx": NUM_CTX, "temperature": 0},
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
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
