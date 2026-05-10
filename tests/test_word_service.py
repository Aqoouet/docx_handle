from __future__ import annotations

import threading
from pathlib import Path

from docx_handle.word_service import (
    SingleWorkerDocxService,
    clean_document,
    collect_cross_reference_fields,
    is_cross_reference_field,
    remove_hidden_text_from_ranges,
    unlink_cross_reference_fields,
)


class FakeCode:
    def __init__(self, text: str):
        self.Text = text


class FakeTextRetrievalMode:
    def __init__(self):
        self.IncludeHiddenText = True


class FakeReplacement:
    def __init__(self):
        self.Text = None
        self.Font = type("Font", (), {"Hidden": None})()

    def ClearFormatting(self) -> None:
        self.cleared = True


class FakeFind:
    def __init__(self, owner):
        self._owner = owner
        self.Replacement = FakeReplacement()
        self.Font = type("Font", (), {"Hidden": None})()
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
        return self._owner.hidden_matches_remaining > 0


class FakeRangeView:
    def __init__(self, owner):
        self._owner = owner
        self.Find = owner.Find
        self.TextRetrievalMode = FakeTextRetrievalMode()

    @property
    def Text(self) -> str:
        if self.TextRetrievalMode.IncludeHiddenText:
            return self._owner.full_text
        return self._owner.visible_text

    @Text.setter
    def Text(self, value: str) -> None:
        self._owner.full_text = value
        self._owner.visible_text = value
        self._owner.last_replaced_text = value

    def Delete(self) -> int:  # noqa: N802
        return self._owner.Delete()


class FakeRange:
    def __init__(
        self,
        *,
        visible_text: str = "",
        full_text: str | None = None,
        hidden_matches_remaining: int = 0,
        fields=None,
    ):
        self.visible_text = visible_text
        self.full_text = visible_text if full_text is None else full_text
        self.hidden_matches_remaining = hidden_matches_remaining
        self.deleted_count = 0
        self.last_replaced_text: str | None = None
        self.Find = FakeFind(self)
        self.TextRetrievalMode = FakeTextRetrievalMode()
        self.Fields = list(fields or [])
        self.NextStoryRange = None

    @property
    def Duplicate(self) -> FakeRangeView:  # noqa: N802
        return FakeRangeView(self)

    @property
    def Text(self) -> str:
        if self.TextRetrievalMode.IncludeHiddenText:
            return self.full_text
        return self.visible_text

    @Text.setter
    def Text(self, value: str) -> None:
        self.full_text = value
        self.visible_text = value
        self.last_replaced_text = value

    def Delete(self) -> int:  # noqa: N802
        if self.hidden_matches_remaining <= 0:
            return 0
        self.hidden_matches_remaining -= 1
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


def test_unlink_cross_reference_fields_only_targets_crossrefs():
    crossref = FakeField("REF bookmark")
    plain = FakeField("DATE")

    count = unlink_cross_reference_fields([crossref, plain])

    assert count == 1
    assert crossref.unlinked is True
    assert plain.unlinked is False


def test_remove_hidden_text_deletes_matches_instead_of_replace_all():
    cleanup_range = FakeRange(hidden_matches_remaining=2)

    cleaned = remove_hidden_text_from_ranges([cleanup_range])

    assert cleaned == 2
    assert cleanup_range.deleted_count == 2
    assert cleanup_range.Find.executed == 3
    assert cleanup_range.Find.Font.Hidden is True
    assert cleanup_range.Find.Replacement.Font.Hidden is False
    assert cleanup_range.Find.execute_kwargs == {}


def test_collect_cross_reference_fields_includes_story_range_fields():
    story_field = FakeField("REF bookmark", result=FakeRange(visible_text="1", full_text="Таблица 1"))
    story_range = FakeRange(fields=[story_field])
    document = FakeDocument([], [story_range])

    fields = collect_cross_reference_fields(document)

    assert fields == (story_field,)


def test_clean_document_rewrites_crossref_result_to_visible_text_before_unlink():
    result_range = FakeRange(visible_text="2-1", full_text="Таблица 2-1")
    field = FakeField("REF bookmark", result=result_range)
    cleanup_range = FakeRange()
    document = FakeDocument([field], [cleanup_range])

    result = clean_document(document)

    assert field.unlinked is True
    assert result_range.Text == "2-1"
    assert result_range.last_replaced_text == "2-1"
    assert result["cross_reference_fields_unlinked"] == 1
    assert result["cross_reference_results_scanned_for_hidden_text"] == 1
    assert result["cross_reference_results_rewritten"] == 1
    assert result["ranges_scanned_for_hidden_text"] == 0


def test_clean_document_leaves_crossref_result_unchanged_when_visible_and_full_match():
    result_range = FakeRange(visible_text="3-1", full_text="3-1")
    field = FakeField("REF bookmark", result=result_range)
    document = FakeDocument([field], [FakeRange()])

    result = clean_document(document)

    assert field.unlinked is True
    assert result_range.last_replaced_text is None
    assert result["cross_reference_results_scanned_for_hidden_text"] == 1
    assert result["cross_reference_results_rewritten"] == 0


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
