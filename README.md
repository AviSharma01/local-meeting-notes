# local-meeting-notes

A local-first CLI that turns a voice memo or transcript into a structured Obsidian note. It appends your commitments to `Action Items.md` and can link earlier notes about the same company.

It is built for the short debrief you record right after an interview or networking call: what they asked, where you struggled, who you met, what you promised, and what you still don't know. Meeting notes are supported as a second mode.

Everything runs on your Mac. Transcription uses faster-whisper, extraction uses a local Ollama model, and notes are written to a folder you choose.

## Setup

You need Python 3.13 and [Ollama](https://ollama.com), and Ollama must be running.

```bash
git clone https://github.com/AviSharma01/local-meeting-notes.git
cd local-meeting-notes
python3.13 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

You don't need a system `ffmpeg`, because faster-whisper decodes audio through PyAV, which bundles the FFmpeg libraries.

Two models are downloaded once. After that, normal runs never go online.

1. The Ollama model (about 9 GB):

   ```bash
   ollama pull qwen2.5:14b
   ```

2. The whisper model. `small` is recommended for debriefs:

   ```bash
   .venv/bin/python -c "from faster_whisper import download_model; download_model('small')"
   ```

   The default whisper model is `base`. If you use it, or `tiny` or `medium`, download it the same way with its name in place of `small`. If a model is missing, the error message prints this command for you.

## Try it without a recording

This command summarizes a sample debrief transcript that ships with the repo. It writes to `output/`, which git ignores:

```bash
.venv/bin/python main.py summarize evals/cases/debrief-northwind-technical/transcript.txt --mode debrief --company "Northwind Analytics" --date 2026-10-01 --out output/
```

The note is written to `output/2026-10-01-northwind-analytics-debrief.md`. Its commitments are appended to `output/Action Items.md`.

## Debriefs

### 1. Record on your phone

Right after the call, open Voice Memos on your iPhone and talk for a minute or two. Cover how it went, the questions they asked, where you struggled, the people you met (spell unusual names out loud), what you promised to do and by when, and anything you still don't know.

### 2. Move the memo to your Mac

In Voice Memos, tap the recording, then Share, then AirDrop to your Mac. The file lands in `~/Downloads` as an `.m4a`. If Voice Memos syncs through iCloud, you can instead drag the recording out of the Voice Memos app on your Mac.

### 3. Summarize it in one command

Replace `~/Downloads/memo.m4a` with your recording and `~/Obsidian/Debriefs` with a folder in your vault:

```bash
.venv/bin/python main.py summarize ~/Downloads/memo.m4a --mode debrief --company "Northwind Analytics" --whisper-model small --out ~/Obsidian/Debriefs --link-related
```

This one command:

1. transcribes the memo and saves it to `~/Obsidian/Debriefs/transcripts/`
2. extracts the debrief with the local model
3. writes the note to `~/Obsidian/Debriefs/`
4. appends the commitments to `~/Obsidian/Debriefs/Action Items.md`

The note is titled `<Company> debrief` unless you pass `--title`.

With `--link-related`, the note ends with a Related Meetings section. It links earlier notes in the same folder, and notes about the same company (matched on the `company:` field, ignoring case) rank first. That way the recruiter screen, the technical round, and the networking call with someone at the same company all link to each other.

### Sample output

This is the note produced by the "Try it" command above with `qwen2.5:14b` (excerpt):

```markdown
# Debrief: Northwind Analytics debrief

## Summary

The speaker had their first technical interview for the data analyst position at Northwind Analytics on October 1st. The conversation focused on SQL queries and product metrics, including a seven-day retention query and an investigation into daily active users. They also discussed a past project involving churn modeling. Weak spots included confusion with window functions in SQL and rambling during the metric investigation question.

## Questions Asked

- Write a query for seven-day retention by sign-up cohort
- How would you investigate a sudden drop in daily active users?
- Walk through a past project

## Weak Spots to Prep

- Confusion with window functions, mixing up rows and range.
- Rambled on the DAEU question.

## People Mentioned

- Priya Raman — Analytics Manager
- Tom — Data Platform Team Lead

## Commitments

- [ ] Send Priya a link to my portfolio by Friday, October 3rd. — Owner: Me — Due: Friday, October 3rd
  - Evidence: [01:05]
- [ ] Get back to me within a week about the next round. — Owner: Priya Raman — Due: within a week
  - Evidence: [01:11]

## Open Questions

- What is the salary range?
- Is the role hybrid?
- How big is the team?
```

## Meetings

Meeting mode is the default. It extracts a summary, decisions, action items, follow-ups, risks, open questions, and items that need review. `--title` is required:

```bash
.venv/bin/python main.py summarize ~/Downloads/meeting.m4a --title "Sprint Planning" --out ~/Obsidian/Meetings --link-related
```

## Dated notes and `--force`

Notes are named `YYYY-MM-DD-<slug>.md` and dated today. Pass `--date` to date a memo you recorded earlier:

```bash
.venv/bin/python main.py summarize ~/Downloads/memo.m4a --mode debrief --company "Northwind Analytics" --whisper-model small --out ~/Obsidian/Debriefs --date 2026-10-01
```

Running the same command again refuses to overwrite the existing note. Add `--force` to rewrite it:

```bash
.venv/bin/python main.py summarize ~/Downloads/memo.m4a --mode debrief --company "Northwind Analytics" --whisper-model small --out ~/Obsidian/Debriefs --date 2026-10-01 --force
```

`--force` never changes that note's section in `Action Items.md`, so boxes you have checked stay checked.

## Transcripts on their own

The input can also be a `.txt` transcript. Recognized audio extensions are `.m4a`, `.mp3`, `.wav`, `.aac`, and `.flac`.

To transcribe without summarizing (the `transcribe` command takes `--model`, not `--whisper-model`):

```bash
.venv/bin/python main.py transcribe ~/Downloads/memo.m4a --out transcripts/ --model small
```

Preview the transcript:

```bash
.venv/bin/python main.py preview transcripts/memo.txt
```

Then summarize it:

```bash
.venv/bin/python main.py summarize transcripts/memo.txt --mode debrief --company "Northwind Analytics" --title "Northwind technical round" --out ~/Obsidian/Debriefs
```

## Eval scores

These scores come from `qwen2.5:14b`, the default model, on 5 eval cases (3 debriefs, 2 meetings), mostly synthetic. Each cell is precision / recall, summed over the cases. The source is the latest `qwen2.5:14b` public row in [`evals/results.md`](evals/results.md) (2026-09-29, commit `baddc4e`).

| Field | Precision / recall |
|---|---|
| Commitments | 1.00 / 1.00 |
| Questions asked | 1.00 / 0.90 |
| People mentioned | 1.00 / 1.00 |
| Action items | 1.00 / 0.83 |
| Decisions | 0.83 / 1.00 |
| **Total recall** | **0.94** |

No case needed the JSON retry (0/5). With 5 cases, one missed item moves a score noticeably, so read these as a sanity check rather than a benchmark.

`qwen2.5:7b` (`ollama pull qwen2.5:7b`, about 4.7 GB, then pass `--model qwen2.5:7b`) is lighter but scored lower on the same cases: total recall 0.76, commitments 0.75 / 0.50, action items 0.80 / 0.67, decisions 1.00 / 0.60 (latest `qwen2.5:7b` public row, 2026-09-29).

## Limitations

* **Short inputs only.** The prompt and transcript must fit in an 8,192-token context, with 2,048 tokens kept for the response.
* **No chunking.** A transcript that is too long fails with a clear error. It is never truncated or split.
* **No diarization.** Transcripts don't mark who said what. This matters little for a solo debrief but a lot for recorded meetings.
* **Small eval set.** There are 5 mostly synthetic cases. Scores on your own recordings may differ.
* **Summaries aren't scored and are written in the third person** ("The speaker had..."). Only the list fields above are evaluated.
* **Transcription can mishear names and terms.** In the sample above, "DAU" came through as "DAEU". Spell unusual names out loud in the memo, and check the saved transcript when a name matters.
* **Notes are a starting point.** The local model can miss details or state them imprecisely, so skim each note against its transcript.

## What stays local

Audio, transcripts, notes, and related-note matching stay on your machine. Apart from the one-time model downloads, the only endpoint the tool talks to is Ollama on localhost. `OLLAMA_HOST` is rejected unless it points to `localhost`, `127.0.0.1`, or `::1`.

Related-note linking reads only Markdown files directly inside `--out`. It skips `Action Items.md`, never recurses or follows symlinks, and never scans the rest of your vault.

There are no cloud transcription or LLM APIs, no calendar, email, Slack, or Notion access, and no background watchers. This is a local CLI by design, not a web app, meeting bot, or real-time recorder.

Don't commit real audio, transcripts, or notes. The `.gitignore` already excludes common audio formats, `transcripts/`, `output/`, and `evals/private/`.
