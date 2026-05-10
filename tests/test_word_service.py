from __future__ import annotations

import threading
from pathlib import Path

from docx_handle.word_service import (
    SingleWorkerDocxService,
    clean_document,
    is_cross_reference_field,
    remove_hidden_text_from_cross_reference_results,
    remove_hidden_text_from_ranges,
    unhide_table_figure_prefixes_in_cross_reference_results,
)


class FakeCode:
    def __init__(self, text: str):
        self.Text = text


class FakeTextRetrievalMode:
    def __init__(self):
        self.IncludeHiddenText = True


class FakeReplacement:
    def __init__(self):
        self.Font = type("Font", (), {"Hidden": None})()

    def ClearFormatting(self) -> None:
        self.cleared = True


class FakeFont:
    def __init__(self, hidden: bool = False) -> None:
        self.Hidden = hidden


class FakeFind:
    def __init__(self, owner):
        self._owner = owner
        self.Replacement = FakeReplacement()
        self.Font = FakeFont()
        self.executed = 0
        self.Text = None
        self.Forward = None
        self.Wrap = None
        self.Format = None
        self.MatchCase = None
        self.MatchWholeWord = None
        self.MatchWildcards = None
        self.MatchSoundsLike = None
        self.MatchAllWordForms = None

    def ClearFormatting(self) -> None:
        self.clear_calls = getattr(self, "clear_calls", 0) + 1

    def Execute(self, **kwargs) -> bool:  # noqa: N802
        self.executed += 1
        self.execute_kwargs = kwargs
        # Decrement here so the loop terminates regardless of whether the
        # caller calls Delete() (delete path) or just unhides the found run.
        if self._owner.hidden_matches_remaining > 0:
            self._owner.hidden_matches_remaining -= 1
            return True
        return False


class FakeRangeView:
    def __init__(self, owner):
        self._owner = owner
        self.Find = owner.Find
        self.Font = FakeFont(hidden=True)
        self.TextRetrievalMode = FakeTextRetrievalMode()

    def Delete(self) -> int:  # noqa: N802
        return self._owner.Delete()


class FakeRange:
    def __init__(self, *, hidden_matches_remaining: int = 0, fields=None):
        self.hidden_matches_remaining = hidden_matches_remaining
        self.deleted_count = 0
        self.Find = FakeFind(self)
        self.TextRetrievalMode = FakeTextRetrievalMode()
        self.Fields = fields
        self.NextStoryRange = None

    @property
    def Duplicate(self) -> FakeRangeView:  # noqa: N802
        return FakeRangeView(self)

    def Delete(self) -> int:  # noqa: N802
        self.deleted_count += 1
        return 1


class FakeField:
    def __init__(self, text: str, field_type: int = 0, result=None):
        self.Code = FakeCode(text)
        self.Type = field_type
        self.Result = result
        self.unlinked = False

    def Unlink(self) -> None:
        self.unlinked = True


class FakeFieldsCollection:
    def __init__(self, fields):
        self._fields = list(fields)

    @property
    def Count(self) -> int:  # noqa: N802
        return len(self._fields)

    def __iter__(self):
        return iter(self._fields)

    def __getitem__(self, index: int):
        return self._fields[index - 1]


class FakeDocument:
    def __init__(self, fields, ranges):
        self.Fields = fields
        self.StoryRanges = ranges
        self.Content = ranges[0] if ranges else None


def test_cross_reference_detection_uses_field_code_or_type():
    assert is_cross_reference_field(FakeField(" REF bookmark \\h"))
    assert is_cross_reference_field(FakeField("PAGEREF bookmark", field_type=999))
    assert is_cross_reference_field(FakeField("", field_type=72))
    assert not is_cross_reference_field(FakeField("DATE"))


def test_remove_hidden_text_deletes_matches_instead_of_replace_all():
    cleanup_range = FakeRange(hidden_matches_remaining=2)

    cleaned = remove_hidden_text_from_ranges([cleanup_range])

    assert cleaned == 2
    assert cleanup_range.deleted_count == 2
    assert cleanup_range.Find.executed == 3
    assert cleanup_range.Find.Font.Hidden is True
    assert cleanup_range.Find.Replacement.Font.Hidden is False
    assert cleanup_range.Find.execute_kwargs == {}


def test_cross_reference_result_cleanup_deletes_hidden_text_without_unlinking():
    result_range = FakeRange(hidden_matches_remaining=2)
    field = FakeField("REF bookmark", result=result_range)
    story_range = FakeRange(fields=FakeFieldsCollection([field]))
    document = FakeDocument([], [story_range])

    cleaned = remove_hidden_text_from_cross_reference_results(document)

    assert cleaned == 1
    assert result_range.deleted_count == 2
    assert field.unlinked is False


def test_cross_reference_result_cleanup_ignores_non_cross_reference_fields():
    result_range = FakeRange(hidden_matches_remaining=2)
    field = FakeField("DATE", result=result_range)
    story_range = FakeRange(fields=FakeFieldsCollection([field]))
    document = FakeDocument([], [story_range])

    cleaned = remove_hidden_text_from_cross_reference_results(document)

    assert cleaned == 0
    assert result_range.deleted_count == 0


def test_cross_reference_result_cleanup_iterates_live_fields_in_reverse():
    first = FakeField("REF first", result=FakeRange(hidden_matches_remaining=1))
    second = FakeField("REF second", result=FakeRange(hidden_matches_remaining=1))
    collection = FakeFieldsCollection([first, second])
    story_range = FakeRange(fields=collection)
    document = FakeDocument([], [story_range])

    cleaned = remove_hidden_text_from_cross_reference_results(document)

    assert cleaned == 2
    assert first.Result.deleted_count == 1
    assert second.Result.deleted_count == 1


def test_clean_document_applies_story_and_cross_reference_cleanup_without_unlinking():
    field_result = FakeRange(hidden_matches_remaining=1)
    field = FakeField("REF bookmark", result=field_result)
    cleanup_range = FakeRange(hidden_matches_remaining=2, fields=FakeFieldsCollection([field]))
    document = FakeDocument([], [cleanup_range])

    result = clean_document(document)

    assert cleanup_range.deleted_count == 2
    # The one hidden match in field_result was unhidden (not deleted) by the
    # "Таблица "/"Рисунок " pass that runs before the delete pass.
    assert field_result.deleted_count == 0
    assert field.unlinked is False
    assert result["cross_reference_fields_unlinked"] == 0
    assert result["cross_reference_prefixes_unhidden"] == 1
    assert result["cross_reference_results_scanned_for_hidden_text"] == 1
    assert result["cross_reference_results_rewritten"] == 0
    assert result["ranges_scanned_for_hidden_text"] == 2


def test_unhide_table_figure_prefixes_unhides_hidden_runs_in_cross_reference_result():
    result_range = FakeRange(hidden_matches_remaining=2)
    field = FakeField("REF bookmark", result=result_range)
    story_range = FakeRange(hidden_matches_remaining=0, fields=FakeFieldsCollection([field]))
    document = FakeDocument([], [story_range])

    count = unhide_table_figure_prefixes_in_cross_reference_results(document)

    # Both matches were unhidden (first prefix consumed them both, second finds nothing).
    assert count == 2
    assert result_range.deleted_count == 0
    # Find was configured to match hidden text with case sensitivity.
    assert result_range.Find.Font.Hidden is True
    assert result_range.Find.MatchCase is True


def test_unhide_table_figure_prefixes_skips_non_cross_reference_fields():
    result_range = FakeRange(hidden_matches_remaining=2)
    field = FakeField("DATE", result=result_range)
    story_range = FakeRange(hidden_matches_remaining=0, fields=FakeFieldsCollection([field]))
    document = FakeDocument([], [story_range])

    count = unhide_table_figure_prefixes_in_cross_reference_results(document)

    assert count == 0
    assert result_range.deleted_count == 0


def test_unhide_table_figure_prefixes_does_not_delete_after_unhide():
    """Unhiding must leave the text intact; delete_count must stay zero."""
    result_range = FakeRange(hidden_matches_remaining=1)
    field = FakeField("REF tbl", result=result_range)
    story_range = FakeRange(hidden_matches_remaining=0, fields=FakeFieldsCollection([field]))
    document = FakeDocument([], [story_range])

    unhide_table_figure_prefixes_in_cross_reference_results(document)

    assert result_range.deleted_count == 0


class FakeEngine:
    def __init__(self):
        self.calls = []

    def process(self, input_path: Path, output_path: Path) -> None:
        self.calls.append(input_path.name)
        output_path.write_bytes(f"processed:{input_path.read_text()}".encode("utf-8"))


def test_single_worker_service_processes_requests_in_order():
    engine = FakeEngine()
    service = SingleWorkerDocxService(lambda: engine)
    service.start()

    first = service.process_bytes("first.docx", b"one")
    second = service.process_bytes("second.docx", b"two")
    service.close()

    assert first == b"processed:one"
    assert second == b"processed:two"
    assert engine.calls == ["input.docx", "input.docx"]
