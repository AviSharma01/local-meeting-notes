# local-meeting-notes

A local-first CLI for turning meeting transcripts into structured notes.

## Quick start

Install dependencies:

```bash
pip install -r requirements.txt
```

Preview a local transcript:

```bash
python main.py preview tests/fixtures/sample_meeting_short.txt
```

Phase 1 is intentionally small. The current CLI reads a manually supplied
`.txt` transcript path and prints it with Rich. It does not call Ollama or write
Obsidian notes yet.
