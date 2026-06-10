## What this project does

A local-first CLI that turns meeting transcripts or local audio files into Obsidian-ready meeting notes, action items, and links to prior meetings.

The tool generates structured summaries, decisions, evidence-linked action items, meeting health metrics, and an `Action Items.md` tracker. It can also transcribe user-provided audio files locally into timestamped `.txt` transcripts before summarization.

The project is designed to avoid cloud dependencies: transcripts are processed locally with Ollama, audio transcription runs locally with faster-whisper, notes are written directly to a user-selected folder, and no calendar, email, Slack, Notion, or full Obsidian vault access is required.

## Interesting design decision

The related-meeting feature is intentionally folder-scoped. When `--link-related` is enabled, the tool reads only Markdown files directly inside the selected `--out` folder, ignores `Action Items.md`, avoids recursion and symlinks, and uses deterministic local matching to add Obsidian wiki-links to related prior meetings.

Matching uses token-overlap scoring with fixed local rules, section-aware keyword extraction, boilerplate filtering, speaker-label filtering, and a small allowlist for short domain terms like `QA`, `UI`, `UX`, `AI`, and `ML`.

This keeps the project useful without turning it into a full-vault RAG system, semantic index, or background file watcher.

## Autonomy level

This is a controlled local workflow, not an autonomous agent.

The classification is deliberate: the steps are fixed, and there is no runtime decision-making about what to do next. The user provides the transcript or audio file, chooses the output folder, and explicitly enables related-note linking when desired.

## Current phase and next work

Phase 1 implemented transcript-to-note generation, Obsidian Markdown export, and action-item tracking.

Phase 2 added optional related-meeting linking from a selected folder.

Phase 3 improved related-note quality through section-aware matching, boilerplate filtering, speaker-label filtering, and short-domain keyword handling.

Phase 4 added local audio transcription using faster-whisper, so meetings can start from an audio file instead of a prepared transcript.

Phase 5 will focus on speaker-aware transcript quality, mainly diarization or speaker labeling for multi-speaker meetings.

## Local notes

Audio files, generated transcripts, and real meeting notes should stay local and should not be committed to GitHub.

The project expects local tools such as Ollama for summarization and faster-whisper for transcription. For common audio formats, ffmpeg may also be required.

The recommended workflow is intentionally two-step: transcribe audio into a .txt file first, then summarize that transcript into an Obsidian-ready meeting note.