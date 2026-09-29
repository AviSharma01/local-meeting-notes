# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses [Semantic Versioning](https://semver.org/).

## [1.0.0] - 2026-09-29

First release.

### Added

- Debrief mode (`--mode debrief --company`) for short voice-memo debriefs after interviews and networking calls. It extracts questions asked, weak spots, people mentioned, commitments, and open questions.
- Meeting mode, the default. It extracts decisions, action items, follow-ups, risks, open questions, and items needing review.
- Structured extraction through a local Ollama model: validated JSON, exactly one retry on invalid output, and deterministic Markdown rendering with counts computed in code.
- Direct audio input to `summarize` (`.m4a`, `.mp3`, `.wav`, `.aac`, `.flac`). The transcript is saved to `transcripts/` inside the output folder.
- `transcribe` and `preview` commands for working with transcripts on their own.
- Local transcription with faster-whisper on CPU (`--whisper-model tiny|base|small|medium`). Models load offline only, and a missing model prints a one-time download command.
- Dated note filenames (`YYYY-MM-DD-<slug>.md`), `--date` for earlier recordings, and `--force` to overwrite an existing note.
- An `Action Items.md` tracker. Each note appends its section once, and `--force` leaves it untouched.
- `--link-related` to link related notes from the same folder, with same-company notes ranked first. It never recurses, follows symlinks, or links a note to itself.
- A length check before calling the model. Over-length transcripts fail with a clear error instead of being truncated.
- `OLLAMA_HOST` restricted to loopback addresses.
- An eval set of 5 public cases, a scoring runner (`python -m evals.run`), and recorded results in `evals/results.md`.
- GitHub Actions CI running the test suite on push and pull request, with no model downloads and no Ollama.
- `qwen2.5:14b` as the default Ollama model. It scored 0.94 total recall on the public evals, compared with 0.76 for `qwen2.5:7b`.
