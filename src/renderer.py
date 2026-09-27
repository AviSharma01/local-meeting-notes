from src.models import ActionItem, DebriefExtraction, MeetingExtraction


EMPTY_SECTION = "None explicitly mentioned."


def render_action_item(item: ActionItem) -> str:
    """Render one action item as a top-level checkbox with optional evidence."""
    line = (
        f"- [ ] {item.task} — Owner: {item.owner or 'Unknown'}"
        f" — Due: {item.due or 'Unknown'}"
    )
    if item.evidence:
        line += f"\n  - Evidence: {item.evidence}"
    return line


def render_meeting(extraction: MeetingExtraction) -> str:
    """Render a validated extraction to the Markdown note sections."""
    decisions = []
    for decision in extraction.decisions:
        line = f"- Decision: {decision.text}"
        if decision.evidence:
            line += f"\n  - Evidence: {decision.evidence}"
        decisions.append(line)

    action_items = [render_action_item(item) for item in extraction.action_items]

    health = [
        f"- Decisions made: {len(extraction.decisions)}",
        f"- Action items created: {len(extraction.action_items)}",
        f"- Items missing owners: {sum(1 for item in extraction.action_items if not item.owner)}",
        f"- Items missing due dates: {sum(1 for item in extraction.action_items if not item.due)}",
        f"- Open questions: {len(extraction.open_questions)}",
    ]

    evidence = [
        f"- {decision.text}: {decision.evidence}"
        for decision in extraction.decisions
        if decision.evidence
    ] + [
        f"- {item.task}: {item.evidence}"
        for item in extraction.action_items
        if item.evidence
    ]

    sections = [
        ("Summary", extraction.summary.strip() or EMPTY_SECTION),
        ("Key Decisions", _join(decisions)),
        ("Action Items", _join(action_items)),
        ("Follow-ups", _bullets(extraction.follow_ups)),
        ("Risks / Blockers", _bullets(extraction.risks)),
        ("Open Questions", _bullets(extraction.open_questions)),
        ("Needs Review", _bullets(extraction.needs_review)),
        ("Meeting Health", "\n".join(health)),
        ("Evidence / Timestamps", _join(evidence)),
    ]

    return "\n\n".join(f"## {heading}\n\n{body}" for heading, body in sections)


def render_debrief(extraction: DebriefExtraction) -> str:
    """Render a validated debrief extraction to the Markdown note sections."""
    people = [
        f"- {person.name} — {person.role}" if person.role else f"- {person.name}"
        for person in extraction.people_mentioned
    ]

    sections = [
        ("Summary", extraction.summary.strip() or EMPTY_SECTION),
        ("Questions Asked", _bullets(extraction.questions_asked)),
        ("Weak Spots to Prep", _bullets(extraction.weak_spots)),
        ("People Mentioned", _join(people)),
        ("Commitments", _join([render_action_item(item) for item in extraction.commitments])),
        ("Open Questions", _bullets(extraction.open_questions)),
    ]

    return "\n\n".join(f"## {heading}\n\n{body}" for heading, body in sections)


def _bullets(items: list[str]) -> str:
    return _join([f"- {item}" for item in items])


def _join(lines: list[str]) -> str:
    return "\n".join(lines) if lines else EMPTY_SECTION
