# AGENTS.example.md

## Project Goal

Build a local-first meeting notes agent.

The app lets a user manually upload a `.txt` meeting transcript, generate structured notes using a local Ollama model, and save the result as Markdown in a user-selected Obsidian meetings folder.

The project should stay simple, local-first, and privacy-conscious.

## Phase 1 Scope

Implement:

1. Manual `.txt` transcript upload.
2. Transcript cleaning.
3. Chunking for long transcripts.
4. Local summary generation through Ollama.
5. Obsidian-friendly Markdown note generation.
6. Save generated notes to a user-selected folder.
7. Append extracted action items to `Action Items.md`.
8. Basic tests for core utilities.

## Expected Note Sections

Generated notes should include:

* Summary
* Key decisions
* Action items
* Follow-ups
* Risks / blockers
* Open questions
* Needs review
* Meeting health metrics
* Evidence / timestamps where available

Action items should use this format:

```markdown
- [ ] Task — Owner: Name or Unknown — Due: Date or Unknown
  - Evidence:
```

## Out of Scope for Phase 1

Do not implement:

* Audio transcription
* Speaker diarization
* Gmail, Slack, Notion, or calendar integration
* Obsidian vault-wide scanning
* RAG over previous notes
* Embeddings or vector databases
* Background folder watching
* User accounts
* Cloud storage
* Paid API model providers

## Privacy Boundaries

The app should only read:

* The transcript manually uploaded by the user
* Prompt files inside this repository
* The selected output folder path for saving generated Markdown

The app should not:

* Search the user's filesystem
* Read unrelated files
* Scan the full Obsidian vault
* Upload transcript content to external APIs
* Run background watchers

## Preferred Stack

Use:

* Python
* Streamlit
* Ollama
* pytest

Avoid additional frameworks unless they are clearly needed.

## Testing Expectations

Include tests for:

* Transcript cleaning
* Chunking
* Safe filename generation
* Markdown writing
* Action item appending
* Preserving existing `Action Items.md` content

## Future Direction

A future Phase 2 may optionally read only `.md` files inside a user-selected Obsidian meetings folder to connect new notes to prior meetings or sprint notes.

Do not implement Phase 2 in the MVP.
