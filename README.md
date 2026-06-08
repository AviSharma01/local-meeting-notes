## What this project does

A local-first CLI that turns meeting transcripts into Obsidian-ready notes, action items, and links to prior meetings, with no cloud and no vault-wide scanning.

This is a local-first meeting intelligence CLI that converts user-provided meeting transcripts into Obsidian-ready Markdown notes. It generates structured summaries, decisions, evidence-linked action items, meeting health metrics, and an `Action Items.md` tracker.

The tool is designed to avoid cloud dependencies: transcripts are processed locally with Ollama, notes are written directly to a user-selected folder, and no calendar, email, Slack, Notion, or full Obsidian vault access is required.

## Interesting design decision

The related-meeting feature is intentionally folder-scoped. When `--link-related` is enabled, the tool reads only Markdown files directly inside the selected `--out` folder, ignores `Action Items.md`, avoids recursion and symlinks, and uses deterministic local matching to add Obsidian wiki-links to related prior meetings.

Matching uses token-overlap scoring with fixed local rules, with no model in the loop, so the same inputs always produce the same links.

This keeps the project useful without turning it into a full-vault RAG system or background indexing tool.

## Autonomy level

This is a controlled local workflow, not an autonomous agent. The classification is deliberate: the steps are fixed, and there is no runtime decision-making about what to do next. The user provides the transcript, chooses the output folder, and explicitly enables related-note linking when desired.

## Current phase and next work

Phase 1 implemented transcript-to-note generation, Obsidian Markdown export, and action-item tracking. Phase 2 added optional related-meeting linking from a selected folder.

Phase 3 improves related-note quality through section-aware matching, speaker-name filtering, and better handling of short domain terms like `QA`, `UI`, `UX`, `AI`, and `ML`.

Later phases add local audio transcription, so meetings can start from an audio file instead of a prepared transcript, and speaker-aware quality via diarization for multi-speaker meetings.