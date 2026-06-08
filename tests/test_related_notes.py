from pathlib import Path

from src.related_notes import (
    MeetingNote,
    RelatedNoteMatch,
    find_related_notes,
    format_related_meetings_section,
    format_wiki_link,
    load_meeting_notes,
)


def make_note(
    title,
    filename,
    content="",
    tags=None,
    summary="",
    date=None,
):
    return MeetingNote(
        title=title,
        filename=filename,
        path=Path(filename),
        content=content,
        tags=tags or [],
        summary=summary,
        date=date,
    )


def test_load_meeting_notes_loads_direct_markdown_notes(tmp_path):
    note_path = tmp_path / "sprint-planning.md"
    content = "# Meeting Notes: Sprint Planning\n\n## Summary\n\nDiscussed sprint scope."
    note_path.write_text(content, encoding="utf-8")

    notes = load_meeting_notes(tmp_path)

    assert notes == [
        MeetingNote(
            title="Meeting Notes: Sprint Planning",
            filename="sprint-planning.md",
            path=note_path,
            content=content,
            tags=[],
            summary="Discussed sprint scope.",
            date=None,
        )
    ]


def test_load_meeting_notes_ignores_action_items_file(tmp_path):
    (tmp_path / "Action Items.md").write_text("# Action Items", encoding="utf-8")
    (tmp_path / "meeting.md").write_text("# Meeting", encoding="utf-8")

    notes = load_meeting_notes(tmp_path)

    assert [note.filename for note in notes] == ["meeting.md"]


def test_load_meeting_notes_ignores_non_markdown_files(tmp_path):
    (tmp_path / "meeting.md").write_text("# Meeting", encoding="utf-8")
    (tmp_path / "transcript.txt").write_text("# Not Markdown", encoding="utf-8")

    notes = load_meeting_notes(tmp_path)

    assert [note.filename for note in notes] == ["meeting.md"]


def test_load_meeting_notes_does_not_recurse_into_subfolders(tmp_path):
    subfolder = tmp_path / "archive"
    subfolder.mkdir()
    (subfolder / "old-meeting.md").write_text("# Old Meeting", encoding="utf-8")

    assert load_meeting_notes(tmp_path) == []


def test_load_meeting_notes_does_not_follow_symlinks(tmp_path):
    real_note = tmp_path / "real-meeting.md"
    real_note.write_text("# Real Meeting", encoding="utf-8")
    symlink_note = tmp_path / "linked-meeting.md"
    symlink_note.symlink_to(real_note)

    notes = load_meeting_notes(tmp_path)

    assert [note.filename for note in notes] == ["real-meeting.md"]


def test_load_meeting_notes_returns_empty_list_for_missing_folder(tmp_path):
    assert load_meeting_notes(tmp_path / "missing") == []


def test_load_meeting_notes_extracts_title_from_first_h1_heading(tmp_path):
    (tmp_path / "meeting.md").write_text(
        "Intro text\n# Meeting Notes: Launch Sync\n# Later H1",
        encoding="utf-8",
    )

    notes = load_meeting_notes(tmp_path)

    assert notes[0].title == "Meeting Notes: Launch Sync"


def test_load_meeting_notes_falls_back_to_filename_stem_without_h1(tmp_path):
    (tmp_path / "launch-sync.md").write_text(
        "## Summary\n\nNo H1 heading.",
        encoding="utf-8",
    )

    notes = load_meeting_notes(tmp_path)

    assert notes[0].title == "launch-sync"


def test_load_meeting_notes_sorts_results_by_filename(tmp_path):
    (tmp_path / "beta.md").write_text("# Beta", encoding="utf-8")
    (tmp_path / "Alpha.md").write_text("# Alpha", encoding="utf-8")
    (tmp_path / "charlie.md").write_text("# Charlie", encoding="utf-8")

    notes = load_meeting_notes(tmp_path)

    assert [note.filename for note in notes] == ["Alpha.md", "beta.md", "charlie.md"]


def test_load_meeting_notes_extracts_tags_from_yaml_list_format(tmp_path):
    (tmp_path / "meeting.md").write_text(
        """---
tags:
  - meeting-notes
  - sprint
---

# Meeting
""",
        encoding="utf-8",
    )

    notes = load_meeting_notes(tmp_path)

    assert notes[0].tags == ["meeting-notes", "sprint"]


def test_load_meeting_notes_extracts_tags_from_inline_yaml_format(tmp_path):
    (tmp_path / "meeting.md").write_text(
        """---
tags: [meeting-notes, sprint]
---

# Meeting
""",
        encoding="utf-8",
    )

    notes = load_meeting_notes(tmp_path)

    assert notes[0].tags == ["meeting-notes", "sprint"]


def test_load_meeting_notes_returns_empty_tags_when_missing(tmp_path):
    (tmp_path / "meeting.md").write_text("# Meeting", encoding="utf-8")

    notes = load_meeting_notes(tmp_path)

    assert notes[0].tags == []


def test_load_meeting_notes_extracts_date_from_frontmatter(tmp_path):
    (tmp_path / "meeting.md").write_text(
        """---
date: 2026-06-07
---

# Meeting
""",
        encoding="utf-8",
    )

    notes = load_meeting_notes(tmp_path)

    assert notes[0].date == "2026-06-07"


def test_load_meeting_notes_returns_none_when_date_missing(tmp_path):
    (tmp_path / "meeting.md").write_text("# Meeting", encoding="utf-8")

    notes = load_meeting_notes(tmp_path)

    assert notes[0].date is None


def test_load_meeting_notes_extracts_summary_text(tmp_path):
    (tmp_path / "meeting.md").write_text(
        """# Meeting

## Summary

Discussed launch scope.
Confirmed beta timeline.
""",
        encoding="utf-8",
    )

    notes = load_meeting_notes(tmp_path)

    assert notes[0].summary == "Discussed launch scope.\nConfirmed beta timeline."


def test_load_meeting_notes_stops_summary_at_next_heading(tmp_path):
    (tmp_path / "meeting.md").write_text(
        """# Meeting

## Summary

Discussed launch scope.

## Action Items

- [ ] Send notes — Owner: Avi — Due: Friday
""",
        encoding="utf-8",
    )

    notes = load_meeting_notes(tmp_path)

    assert notes[0].summary == "Discussed launch scope."


def test_load_meeting_notes_returns_empty_summary_when_missing(tmp_path):
    (tmp_path / "meeting.md").write_text("# Meeting\n\n## Notes", encoding="utf-8")

    notes = load_meeting_notes(tmp_path)

    assert notes[0].summary == ""


def test_find_related_notes_returns_empty_list_with_no_candidates():
    assert find_related_notes("Sprint Planning", "Discussed beta launch.", []) == []


def test_find_related_notes_returns_empty_list_when_no_signals_match():
    candidates = [
        make_note(
            "Budget Review",
            "budget.md",
            content="Discussed finance forecasts.",
            tags=["finance"],
            summary="Reviewed budget.",
        )
    ]

    assert find_related_notes("Sprint Planning", "Discussed beta launch.", candidates) == []


def test_find_related_notes_scores_shared_title_words_once():
    note = make_note("Sprint Retro", "sprint-retro.md")

    matches = find_related_notes("Sprint Planning", "Discussed roadmap.", [note])

    assert matches[0].score == 3
    assert matches[0].reasons == ["Shared title keyword: sprint"]


def test_find_related_notes_scores_candidate_tags_in_current_title_or_content():
    note = make_note("Roadmap", "roadmap.md", tags=["launch", "qa"])

    matches = find_related_notes(
        "Sprint Planning",
        "The team discussed launch readiness and QA ownership.",
        [note],
    )

    assert matches[0].score == 4
    assert matches[0].reasons == ["Shared tag: launch", "Shared tag: qa"]


def test_find_related_notes_does_not_score_generic_tags():
    note = make_note("Roadmap", "roadmap.md", tags=["meeting-notes"])

    assert find_related_notes(
        "Meeting Notes",
        "These meeting notes mention planning.",
        [note],
    ) == []


def test_find_related_notes_scores_shared_content_keywords_with_cap():
    note = make_note(
        "Roadmap",
        "roadmap.md",
        content="alpha beta gamma delta epsilon zeta eta theta",
    )

    matches = find_related_notes(
        "Planning",
        "alpha beta gamma delta epsilon zeta eta theta",
        [note],
    )

    assert matches[0].score == 5
    assert matches[0].reasons == [
        "Shared content keywords: alpha, beta, delta, epsilon, eta"
    ]


def test_find_related_notes_limits_results():
    candidates = [
        make_note("Sprint A", "a.md"),
        make_note("Sprint B", "b.md"),
        make_note("Sprint C", "c.md"),
    ]

    matches = find_related_notes("Sprint Planning", "", candidates, limit=2)

    assert [match.note.filename for match in matches] == ["a.md", "b.md"]


def test_find_related_notes_sorts_by_score_descending():
    low_score = make_note("Sprint Retro", "low.md")
    high_score = make_note(
        "Sprint Launch",
        "high.md",
        tags=["launch"],
        content="beta",
    )

    matches = find_related_notes(
        "Sprint Planning",
        "Discussed launch beta.",
        [low_score, high_score],
    )

    assert [match.note.filename for match in matches] == ["high.md", "low.md"]
    assert matches[0].score > matches[1].score


def test_find_related_notes_uses_filename_as_tie_breaker():
    candidates = [
        make_note("Sprint Beta", "b.md"),
        make_note("Sprint Alpha", "a.md"),
    ]

    matches = find_related_notes("Sprint Planning", "", candidates)

    assert [match.note.filename for match in matches] == ["a.md", "b.md"]


def test_find_related_notes_excludes_exact_same_title():
    candidates = [
        make_note("Sprint Planning", "same.md", tags=["sprint"], content="planning")
    ]

    assert find_related_notes("Sprint Planning", "sprint planning", candidates) == []


def test_find_related_notes_includes_useful_reasons():
    note = make_note(
        "Sprint Launch",
        "sprint-launch.md",
        content="beta rollout",
        tags=["qa"],
    )

    matches = find_related_notes(
        "Sprint Planning",
        "QA reviewed beta rollout.",
        [note],
    )

    assert "Shared title keyword: sprint" in matches[0].reasons
    assert "Shared tag: qa" in matches[0].reasons
    assert "Shared content keywords: beta, rollout" in matches[0].reasons


def test_find_related_notes_filters_noisy_shared_content_keywords():
    note = make_note(
        "Prior Launch",
        "prior-launch.md",
        content="Alex said but blockers were just more about process.",
    )

    matches = find_related_notes(
        "Current Launch",
        "Alex said but blockers were just more about process.",
        [note],
    )

    content_reason = next(
        reason
        for reason in matches[0].reasons
        if reason.startswith("Shared content keywords:")
    )
    assert "alex" not in content_reason
    assert "but" not in content_reason
    assert "blockers" not in content_reason


def test_find_related_notes_filters_generated_note_boilerplate_keywords():
    note = make_note(
        "Prior Launch",
        "prior-launch.md",
        content=(
            "created date dates explicitly mentioned none unknown "
            "made missing found related score reason reasons section sections "
            "content generated final note launch"
        ),
    )

    matches = find_related_notes(
        "Current Launch",
        (
            "created date dates explicitly mentioned none unknown "
            "made missing found related score reason reasons section sections "
            "content generated final note launch"
        ),
        [note],
    )

    content_reason = next(
        reason
        for reason in matches[0].reasons
        if reason.startswith("Shared content keywords:")
    )
    assert content_reason == "Shared content keywords: launch"


def test_find_related_notes_keeps_meaningful_shared_content_keywords():
    note = make_note(
        "Product Review",
        "product-review.md",
        content="beta qa dashboard metrics",
    )

    matches = find_related_notes(
        "Product Planning",
        "beta qa dashboard metrics",
        [note],
    )

    assert "Shared content keywords: beta, dashboard, metrics" in matches[0].reasons


def test_find_related_notes_uses_summary_section_keywords():
    note = make_note(
        "Prior Planning",
        "prior-planning.md",
        content="""# Prior Planning

## Summary

Launch beta dashboard metrics were reviewed.
""",
    )

    matches = find_related_notes(
        "Current Planning",
        """# Current Planning

## Summary

Launch beta dashboard metrics stayed on track.
""",
        [note],
    )

    assert "Shared content keywords: beta, dashboard, launch, metrics" in matches[0].reasons


def test_find_related_notes_uses_key_decisions_section_keywords():
    note = make_note(
        "Prior Decision",
        "prior-decision.md",
        content="""# Prior Decision

## Key Decisions

- Decision: Keep the beta launch dashboard scope.
""",
    )

    matches = find_related_notes(
        "Current Decision",
        """# Current Decision

## Key Decisions

- Decision: Keep beta launch dashboard scope.
""",
        [note],
    )

    assert (
        "Shared content keywords: beta, dashboard, keep, launch, scope"
        in matches[0].reasons
    )


def test_find_related_notes_ignores_meeting_health_only_keywords():
    note = make_note(
        "Prior Status",
        "prior-health.md",
        content="""# Prior Health

## Meeting Health

- Decisions made: 1
- Action items created: 2
- Open questions: 3
""",
    )

    matches = find_related_notes(
        "Current Report",
        """# Current Health

## Meeting Health

- Decisions made: 1
- Action items created: 2
- Open questions: 3
""",
        [note],
    )

    assert matches == []


def test_find_related_notes_ignores_related_meetings_only_keywords():
    note = make_note(
        "Prior Connections",
        "prior-links.md",
        content="""# Prior Links

## Related Meetings

- [[dashboard-beta-launch]] — Score: 8
  - Reason: Shared content keywords: dashboard, beta, launch
""",
    )

    matches = find_related_notes(
        "Current References",
        """# Current Links

## Related Meetings

- [[dashboard-beta-launch]] — Score: 8
  - Reason: Shared content keywords: dashboard, beta, launch
""",
        [note],
    )

    assert matches == []


def test_format_wiki_link_uses_filename_stem():
    note = make_note("Sprint Planning", "sprint-planning.md")

    assert format_wiki_link(note) == "[[sprint-planning]]"


def test_format_wiki_link_excludes_markdown_extension():
    note = make_note("Sprint Planning", "sprint-planning.md")

    assert ".md" not in format_wiki_link(note)


def test_format_related_meetings_section_returns_empty_string_for_no_matches():
    assert format_related_meetings_section([]) == ""


def test_format_related_meetings_section_includes_heading_wiki_links_scores_and_reasons():
    note = make_note("Sprint Planning", "sprint-planning.md")
    match = RelatedNoteMatch(
        note=note,
        score=6,
        reasons=[
            "Shared title keyword: sprint",
            "Shared content keywords: beta, qa",
        ],
    )

    section = format_related_meetings_section([match])

    assert section.startswith("## Related Meetings\n\n")
    assert "- [[sprint-planning]] — Score: 6" in section
    assert "  - Reason: Shared title keyword: sprint" in section
    assert "  - Reason: Shared content keywords: beta, qa" in section


def test_format_related_meetings_section_preserves_match_order():
    first = RelatedNoteMatch(make_note("Beta", "beta.md"), score=2, reasons=[])
    second = RelatedNoteMatch(make_note("Alpha", "alpha.md"), score=9, reasons=[])

    section = format_related_meetings_section([first, second])

    assert section.index("[[beta]]") < section.index("[[alpha]]")


def test_format_related_meetings_section_renders_match_with_no_reasons():
    match = RelatedNoteMatch(make_note("Sprint Planning", "sprint-planning.md"), 3, [])

    section = format_related_meetings_section([match])

    assert "- [[sprint-planning]] — Score: 3" in section
    assert "Reason:" not in section
