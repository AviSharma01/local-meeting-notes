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
    company=None,
):
    return MeetingNote(
        title=title,
        filename=filename,
        path=Path(filename),
        content=content,
        tags=tags or [],
        summary=summary,
        date=date,
        company=company,
    )


def content_keywords_from(match):
    content_reason = next(
        reason
        for reason in match.reasons
        if reason.startswith("Shared content keywords:")
    )
    return set(content_reason.removeprefix("Shared content keywords: ").split(", "))


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


def test_find_related_notes_excludes_the_current_note_by_stem():
    candidates = [
        make_note(
            "Sprint Planning",
            "2026-01-15-sprint-planning.md",
            tags=["sprint"],
            content="planning",
        )
    ]

    assert find_related_notes(
        "Sprint Planning",
        "sprint planning",
        candidates,
        current_stem="2026-01-15-sprint-planning",
    ) == []


def test_find_related_notes_matches_the_same_title_on_a_different_date():
    candidates = [
        make_note(
            "Sprint Planning",
            "2026-01-15-sprint-planning.md",
            tags=["sprint"],
            content="planning",
        )
    ]

    matches = find_related_notes(
        "Sprint Planning",
        "sprint planning",
        candidates,
        current_stem="2026-02-01-sprint-planning",
    )

    assert [match.note.filename for match in matches] == [
        "2026-01-15-sprint-planning.md"
    ]
    assert "Shared title keyword: planning" in matches[0].reasons


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
        content="The team said but blockers were just more about process.",
    )

    matches = find_related_notes(
        "Current Launch",
        "The team said but blockers were just more about process.",
        [note],
    )

    content_keywords = content_keywords_from(matches[0])
    assert "but" not in content_keywords
    assert "blockers" not in content_keywords


def test_find_related_notes_filters_timestamped_speaker_labels_from_content_keywords():
    note = make_note(
        "Prior Record",
        "prior-record.md",
        content="[00:35] Sam: QA dashboard metrics.",
    )

    matches = find_related_notes(
        "Current Report",
        "[01:10:22] Sam: QA dashboard metrics.",
        [note],
    )

    content_keywords = content_keywords_from(matches[0])
    assert "sam" not in content_keywords
    assert {"dashboard", "metrics", "qa"}.issubset(content_keywords)


def test_find_related_notes_filters_plain_speaker_labels_from_content_keywords():
    note = make_note(
        "Prior Record",
        "prior-record.md",
        content="Priya: Launch dashboard metrics look stable.",
    )

    matches = find_related_notes(
        "Current Report",
        "Priya: Launch dashboard metrics look stable.",
        [note],
    )

    content_keywords = content_keywords_from(matches[0])
    assert "priya" not in content_keywords
    assert {"dashboard", "launch"}.issubset(content_keywords)


def test_find_related_notes_filters_each_token_from_multi_word_speaker_labels():
    note = make_note(
        "Prior Record",
        "prior-record.md",
        content="Alex Chen: Beta dashboard metrics stayed stable.",
    )

    matches = find_related_notes(
        "Current Report",
        "Alex Chen: Beta dashboard metrics stayed stable.",
        [note],
    )

    content_keywords = content_keywords_from(matches[0])
    assert "alex" not in content_keywords
    assert "chen" not in content_keywords
    assert {"beta", "dashboard", "metrics"}.issubset(content_keywords)


def test_find_related_notes_filters_generated_note_boilerplate_keywords():
    note = make_note(
        "Prior Launch",
        "prior-launch.md",
        content=(
            "meeting meetings note notes summary summarized action actions "
            "item items decision decisions follow followup followups risk risks "
            "blocker blockers question questions evidence timestamp timestamps "
            "owner due unknown explicitly mentioned none created missing related "
            "reason score launch dashboard"
        ),
    )

    matches = find_related_notes(
        "Current Launch",
        (
            "meeting meetings note notes summary summarized action actions "
            "item items decision decisions follow followup followups risk risks "
            "blocker blockers question questions evidence timestamp timestamps "
            "owner due unknown explicitly mentioned none created missing related "
            "reason score launch dashboard"
        ),
        [note],
    )

    content_reason = next(
        reason
        for reason in matches[0].reasons
        if reason.startswith("Shared content keywords:")
    )
    content_keywords = set(
        content_reason.removeprefix("Shared content keywords: ").split(", ")
    )
    boilerplate_keywords = {
        "meeting",
        "meetings",
        "note",
        "notes",
        "summary",
        "summarized",
        "action",
        "actions",
        "item",
        "items",
        "decision",
        "decisions",
        "follow",
        "followup",
        "followups",
        "risk",
        "risks",
        "blocker",
        "blockers",
        "question",
        "questions",
        "evidence",
        "timestamp",
        "timestamps",
        "owner",
        "due",
        "unknown",
        "explicitly",
        "mentioned",
        "none",
        "created",
        "missing",
        "related",
        "reason",
        "score",
    }
    assert content_keywords.isdisjoint(boilerplate_keywords)
    assert content_keywords == {"dashboard", "launch"}


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

    assert "Shared content keywords: beta, dashboard, metrics, qa" in matches[0].reasons


def test_find_related_notes_keeps_allowlisted_short_domain_keywords():
    note = make_note(
        "Product Review",
        "product-review.md",
        content="qa ui ai ml platform",
    )

    matches = find_related_notes(
        "Product Planning",
        "qa ui ai ml platform",
        [note],
    )

    assert "Shared content keywords: ai, ml, platform, qa, ui" in matches[0].reasons


def test_find_related_notes_ignores_non_allowlisted_short_keywords():
    note = make_note(
        "Product Review",
        "product-review.md",
        content="to go id platform dashboard",
    )

    matches = find_related_notes(
        "Product Planning",
        "to go id platform dashboard",
        [note],
    )

    content_keywords = content_keywords_from(matches[0])
    assert content_keywords == {"dashboard", "platform"}


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


def debrief_content(company, summary="None explicitly mentioned.", **sections):
    headings = {
        "questions_asked": "Questions Asked",
        "weak_spots": "Weak Spots to Prep",
        "people_mentioned": "People Mentioned",
        "commitments": "Commitments",
    }
    body = "\n\n".join(
        f"## {headings[key]}\n\n{sections.get(key, 'None explicitly mentioned.')}"
        for key in headings
    )
    return (
        "---\n"
        "type: debrief\n"
        f"company: {company}\n"
        "tags:\n"
        "  - debrief\n"
        "---\n\n"
        f"# Debrief: {company} debrief\n\n"
        f"## Summary\n\n{summary}\n\n"
        f"{body}\n\n"
        "## Open Questions\n\nNone explicitly mentioned."
    )


def test_load_meeting_notes_extracts_company_from_frontmatter(tmp_path):
    (tmp_path / "debrief.md").write_text(debrief_content("Northwind"), encoding="utf-8")
    (tmp_path / "meeting.md").write_text("---\ndate: 2026-01-15\n---\n\n# Sync", encoding="utf-8")

    notes = {note.filename: note for note in load_meeting_notes(tmp_path)}

    assert notes["debrief.md"].company == "Northwind"
    assert notes["meeting.md"].company is None


def test_find_related_notes_ranks_same_company_notes_above_keyword_matches():
    current = debrief_content(
        "Northwind",
        summary="Retention query, cohort analysis, dashboard metrics, and SQL windows.",
    )
    same_company_first = make_note(
        "Debrief: Northwind debrief",
        "2026-01-01-northwind-debrief.md",
        content=debrief_content("Northwind", summary="Recruiter screen about salary."),
        tags=["debrief"],
        company="Northwind",
    )
    same_company_second = make_note(
        "Debrief: Northwind onsite",
        "2026-01-08-northwind-onsite.md",
        content=debrief_content("northwind", summary="Onsite loop logistics."),
        tags=["debrief"],
        company="northwind",
    )
    other_company = make_note(
        "Debrief: Contoso debrief",
        "2026-01-05-contoso-debrief.md",
        content=debrief_content(
            "Contoso",
            summary="Retention query, cohort analysis, dashboard metrics, and SQL windows.",
        ),
        tags=["debrief"],
        company="Contoso",
    )

    matches = find_related_notes(
        "Northwind debrief",
        current,
        [other_company, same_company_second, same_company_first],
    )

    assert [match.note.filename for match in matches] == [
        "2026-01-01-northwind-debrief.md",
        "2026-01-08-northwind-onsite.md",
        "2026-01-05-contoso-debrief.md",
    ]
    assert matches[2].score > matches[0].score
    assert matches[2].score > matches[1].score
    assert "Same company: Northwind" in matches[0].reasons
    assert "Same company: northwind" in matches[1].reasons
    assert not any(reason.startswith("Same company") for reason in matches[2].reasons)


def test_find_related_notes_lists_same_company_note_without_shared_keywords():
    candidate = make_note(
        "Debrief: Acme",
        "acme.md",
        content=debrief_content("Acme", summary="Recruiter screen."),
        company="Acme",
    )

    matches = find_related_notes(
        "Round two",
        debrief_content("ACME", summary="Whiteboard exercise."),
        [candidate],
    )

    assert len(matches) == 1
    assert matches[0].reasons == ["Same company: Acme"]


def test_find_related_notes_does_not_boost_company_for_meeting_note_without_company():
    candidate = make_note(
        "Debrief: Acme",
        "acme.md",
        content=debrief_content("Acme", summary="Recruiter screen."),
        company="Acme",
    )

    matches = find_related_notes(
        "Weekly sync",
        "## Summary\n\nBudget planning.",
        [candidate],
    )

    assert matches == []


def test_find_related_notes_uses_debrief_section_keywords():
    current = debrief_content(
        "Northwind",
        questions_asked="- Write a retention query",
        weak_spots="- Windowing",
        people_mentioned="- Priya — Analytics manager",
        commitments="- [ ] Send portfolio — Owner: Me — Due: Friday",
    )
    candidate = make_note(
        "Debrief: Contoso",
        "contoso.md",
        content=debrief_content(
            "Contoso",
            questions_asked="- Explain a retention drop",
            weak_spots="- Windowing",
            people_mentioned="- Priya — Recruiter",
            commitments="- [ ] Update portfolio — Owner: Me — Due: Unknown",
        ),
    )

    matches = find_related_notes("Northwind debrief", current, [candidate])

    assert content_keywords_from(matches[0]) == {"retention", "windowing", "priya", "portfolio"}


def test_find_related_notes_keeps_names_in_debrief_keywords():
    summary = "Priya Raman: analytics manager."
    candidate = make_note(
        "Debrief: Contoso",
        "contoso.md",
        content=debrief_content("Contoso", summary=summary),
    )

    matches = find_related_notes(
        "Northwind debrief",
        debrief_content("Northwind", summary=summary),
        [candidate],
    )

    assert content_keywords_from(matches[0]) == {"priya", "raman", "analytics", "manager"}
