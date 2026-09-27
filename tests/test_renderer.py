from src.models import ActionItem, DebriefExtraction, Decision, MeetingExtraction, Person
from src.renderer import render_action_item, render_debrief, render_meeting


def make_extraction(**overrides):
    fields = {
        "summary": "",
        "decisions": [],
        "action_items": [],
        "follow_ups": [],
        "risks": [],
        "open_questions": [],
        "needs_review": [],
    }
    fields.update(overrides)
    return MeetingExtraction(**fields)


def test_render_meeting_matches_documented_section_format():
    extraction = make_extraction(
        summary="The team kept the beta launch date.",
        decisions=[Decision(text="Keep the beta launch date", evidence="[00:50]")],
        action_items=[
            ActionItem(task="Run the QA pass", owner="Sam", due="Friday", evidence="[00:35]"),
            ActionItem(task="Update docs"),
        ],
        follow_ups=["Confirm docs are final"],
        risks=["QA needs one more pass"],
        open_questions=["Who announces the beta?"],
        needs_review=["Launch date year is unclear"],
    )

    assert render_meeting(extraction) == (
        "## Summary\n"
        "\n"
        "The team kept the beta launch date.\n"
        "\n"
        "## Key Decisions\n"
        "\n"
        "- Decision: Keep the beta launch date\n"
        "  - Evidence: [00:50]\n"
        "\n"
        "## Action Items\n"
        "\n"
        "- [ ] Run the QA pass — Owner: Sam — Due: Friday\n"
        "  - Evidence: [00:35]\n"
        "- [ ] Update docs — Owner: Unknown — Due: Unknown\n"
        "\n"
        "## Follow-ups\n"
        "\n"
        "- Confirm docs are final\n"
        "\n"
        "## Risks / Blockers\n"
        "\n"
        "- QA needs one more pass\n"
        "\n"
        "## Open Questions\n"
        "\n"
        "- Who announces the beta?\n"
        "\n"
        "## Needs Review\n"
        "\n"
        "- Launch date year is unclear\n"
        "\n"
        "## Meeting Health\n"
        "\n"
        "- Decisions made: 1\n"
        "- Action items created: 2\n"
        "- Items missing owners: 1\n"
        "- Items missing due dates: 1\n"
        "- Open questions: 1\n"
        "\n"
        "## Evidence / Timestamps\n"
        "\n"
        "- Keep the beta launch date: [00:50]\n"
        "- Run the QA pass: [00:35]"
    )


def test_render_meeting_empty_extraction_uses_placeholder_for_every_list_section():
    rendered = render_meeting(make_extraction())

    assert rendered == (
        "## Summary\n\nNone explicitly mentioned.\n\n"
        "## Key Decisions\n\nNone explicitly mentioned.\n\n"
        "## Action Items\n\nNone explicitly mentioned.\n\n"
        "## Follow-ups\n\nNone explicitly mentioned.\n\n"
        "## Risks / Blockers\n\nNone explicitly mentioned.\n\n"
        "## Open Questions\n\nNone explicitly mentioned.\n\n"
        "## Needs Review\n\nNone explicitly mentioned.\n\n"
        "## Meeting Health\n\n"
        "- Decisions made: 0\n"
        "- Action items created: 0\n"
        "- Items missing owners: 0\n"
        "- Items missing due dates: 0\n"
        "- Open questions: 0\n\n"
        "## Evidence / Timestamps\n\nNone explicitly mentioned."
    )


def test_render_meeting_health_counts_match_extraction():
    extraction = make_extraction(
        summary="Planning.",
        decisions=[Decision(text="A"), Decision(text="B"), Decision(text="C")],
        action_items=[
            ActionItem(task="One", owner="Avi", due="Monday"),
            ActionItem(task="Two", owner="Sam"),
            ActionItem(task="Three", due="Friday"),
            ActionItem(task="Four"),
        ],
        open_questions=["Q1", "Q2"],
    )

    rendered = render_meeting(extraction)

    assert f"- Decisions made: {len(extraction.decisions)}" in rendered
    assert f"- Action items created: {len(extraction.action_items)}" in rendered
    assert "- Items missing owners: 2" in rendered
    assert "- Items missing due dates: 2" in rendered
    assert f"- Open questions: {len(extraction.open_questions)}" in rendered


def test_render_meeting_only_checkboxes_are_action_items():
    extraction = make_extraction(
        decisions=[Decision(text="Ship it")],
        action_items=[ActionItem(task="Send notes")],
        follow_ups=["Follow up"],
    )

    checkbox_lines = [
        line for line in render_meeting(extraction).splitlines() if "[ ]" in line
    ]

    assert checkbox_lines == ["- [ ] Send notes — Owner: Unknown — Due: Unknown"]


def test_render_action_item_without_evidence_has_no_evidence_line():
    assert render_action_item(ActionItem(task="Send notes", owner="Avi")) == (
        "- [ ] Send notes — Owner: Avi — Due: Unknown"
    )


DEBRIEF_SECTIONS = [
    "## Summary",
    "## Questions Asked",
    "## Weak Spots to Prep",
    "## People Mentioned",
    "## Commitments",
    "## Open Questions",
]


def test_render_debrief_renders_six_sections_in_order():
    rendered = render_debrief(
        DebriefExtraction(
            summary="First technical round.",
            questions_asked=["Write a retention query"],
            weak_spots=["Window functions"],
            people_mentioned=[
                Person(name="Priya Raman", role="Analytics manager"),
                Person(name="Tong"),
            ],
            commitments=[
                ActionItem(task="Send portfolio link", owner="Me", due="Friday", evidence="[01:05]")
            ],
            open_questions=["Salary range"],
        )
    )

    positions = [rendered.index(heading) for heading in DEBRIEF_SECTIONS]
    assert positions == sorted(positions)
    assert "- Write a retention query" in rendered
    assert "- Window functions" in rendered
    assert "- Priya Raman — Analytics manager" in rendered
    assert "- Tong\n" in rendered
    assert "- [ ] Send portfolio link — Owner: Me — Due: Friday\n  - Evidence: [01:05]" in rendered
    assert "- Salary range" in rendered


def test_render_debrief_marks_empty_sections():
    rendered = render_debrief(DebriefExtraction(summary=""))

    for heading in DEBRIEF_SECTIONS:
        assert f"{heading}\n\nNone explicitly mentioned." in rendered
