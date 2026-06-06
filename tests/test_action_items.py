from src.action_items import append_action_items, extract_action_items


def test_extract_action_items_extracts_single_checkbox_item():
    markdown = """## Action Items

- [ ] Send launch notes — Owner: Avi — Due: Friday

## Follow-ups
"""

    assert extract_action_items(markdown) == [
        "- [ ] Send launch notes — Owner: Avi — Due: Friday"
    ]


def test_extract_action_items_extracts_multiple_checkbox_items_in_order():
    markdown = """## Action Items

- [ ] Send notes — Owner: Avi — Due: Friday
- [ ] Review QA plan — Owner: Sam — Due: Monday
"""

    assert extract_action_items(markdown) == [
        "- [ ] Send notes — Owner: Avi — Due: Friday",
        "- [ ] Review QA plan — Owner: Sam — Due: Monday",
    ]


def test_extract_action_items_includes_indented_evidence_lines():
    markdown = """## Action Items

- [ ] Review QA plan — Owner: Sam — Due: Monday
  - Evidence: Sam said he can own QA.
  - Due: Monday
- Follow-up note
"""

    assert extract_action_items(markdown) == [
        "- [ ] Review QA plan — Owner: Sam — Due: Monday\n"
        "  - Evidence: Sam said he can own QA.\n"
        "  - Due: Monday"
    ]


def test_extract_action_items_stops_before_heading_or_top_level_bullet():
    markdown = """- [ ] Review QA plan — Owner: Sam — Due: Monday
  - Evidence: Sam said he can own QA.
## Follow-ups
- Not a checkbox item
- [ ] Confirm release notes — Owner: Unknown — Due: Unknown
- Another bullet
"""

    assert extract_action_items(markdown) == [
        "- [ ] Review QA plan — Owner: Sam — Due: Monday\n"
        "  - Evidence: Sam said he can own QA.",
        "- [ ] Confirm release notes — Owner: Unknown — Due: Unknown",
    ]


def test_extract_action_items_returns_empty_list_when_none_exist():
    markdown = """## Summary

No action items were identified.
"""

    assert extract_action_items(markdown) == []


def test_append_action_items_creates_action_items_file(tmp_path):
    markdown = "- [ ] Send notes — Owner: Avi — Due: Friday"

    action_items_path = append_action_items(str(tmp_path), "Sample Meeting", markdown)

    assert action_items_path == tmp_path / "Action Items.md"
    assert action_items_path.exists()


def test_append_action_items_preserves_existing_content(tmp_path):
    action_items_path = tmp_path / "Action Items.md"
    existing_content = "# Action Items\n\nExisting content."
    action_items_path.write_text(existing_content, encoding="utf-8")

    append_action_items(
        str(tmp_path),
        "Sample Meeting",
        "- [ ] Send notes — Owner: Avi — Due: Friday",
    )

    content = action_items_path.read_text(encoding="utf-8")
    assert content.startswith(existing_content)
    assert "- [ ] Send notes" in content


def test_append_action_items_returns_none_and_creates_no_file_when_none_exist(tmp_path):
    result = append_action_items(str(tmp_path), "Sample Meeting", "## Summary\n\nNo actions.")

    assert result is None
    assert not (tmp_path / "Action Items.md").exists()


def test_append_action_items_adds_source_line(tmp_path):
    append_action_items(
        str(tmp_path),
        "Sample Meeting",
        "- [ ] Send notes — Owner: Avi — Due: Friday",
    )

    content = (tmp_path / "Action Items.md").read_text(encoding="utf-8")
    assert "  - Source: [[Sample Meeting]]" in content


def test_append_action_items_does_not_add_duplicate_source_line(tmp_path):
    markdown = """- [ ] Send notes — Owner: Avi — Due: Friday
  - Evidence: Avi agreed.
  - Source: [[Sample Meeting]]
"""

    append_action_items(str(tmp_path), "Sample Meeting", markdown)

    content = (tmp_path / "Action Items.md").read_text(encoding="utf-8")
    assert content.count("Source: [[Sample Meeting]]") == 1
