from __future__ import annotations

import threading
from pathlib import Path

from docx_handle.word_service import (
    SingleWorkerDocxService,
    clean_document,
    is_cross_reference_field,
    remove_hidden_text_from_ranges,
    unlink_cross_reference_fields,
)


class FakeCode:
    def __init__(self, text: str):
        self.Text = text


class FakeField:
    def __init__(self, text: str, field_type: int = 0):
        self.Code = FakeCode(text)
        self.Type = field_type
        self.unlinked = False

    def Unlink(self) -> None:
        self.unlinked = True


class FakeReplacement:
    def __init__(self):
        self.Text = None
        self.Font = type("Font", (), {"Hidden": None})()

    def ClearFormatting(self) -> None:
        self.cleared = True


class FakeFind:
    def __init__(self):
        self.Replacement = FakeReplacement()
        self.Font = type("Font", (), {"Hidden": None})()
        self.executed = False

    def ClearFormatting(self) -> None:
        self.clear_calls = getattr(self, "clear_calls", 0) + 1

    def Execute(self, **kwargs) -> None:  # noqa: N802
        self.executed = True
        self.execute_kwargs = kwargs


class FakeRange:
    def __init__(self):
        self.Find = FakeFind()
        self.NextStoryRange = None


class FakeDocument:
    def __init__(self, fields, ranges):
        self.Fields = fields
        self.StoryRanges = ranges
        self.Content = ranges[0] if ranges else None


class HiddenCrossRefState:
    def __init__(self):
        self.hidden_text_present = True
        self.hidden_formatting_preserved = True


class HiddenCrossRefField(FakeField):
    def __init__(self, state: HiddenCrossRefState):
        super().__init__("REF bookmark")
        self._state = state

    def Unlink(self) -> None:
        super().Unlink()
        self._state.hidden_formatting_preserved = False


class HiddenCrossRefFind(FakeFind):
    def __init__(self, state: HiddenCrossRefState):
        super().__init__()
        self._state = state

    def Execute(self, **kwargs) -> None:  # noqa: N802
        super().Execute(**kwargs)
        if self._state.hidden_formatting_preserved:
            self._state.hidden_text_present = False


class HiddenCrossRefRange(FakeRange):
    def __init__(self, state: HiddenCrossRefState):
        self.Find = HiddenCrossRefFind(state)
        self.NextStoryRange = None


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


def test_remove_hidden_text_configures_find_replace():
    cleanup_range = FakeRange()
    cleaned = remove_hidden_text_from_ranges([cleanup_range])

    assert cleaned == 1
    assert cleanup_range.Find.executed is True
    assert cleanup_range.Find.Font.Hidden is True
    assert cleanup_range.Find.Replacement.Text == ""
    assert cleanup_range.Find.Replacement.Font.Hidden is False


def test_clean_document_applies_both_transformations():
    field = FakeField("REF bookmark")
    cleanup_range = FakeRange()
    document = FakeDocument([field], [cleanup_range])

    result = clean_document(document)

    assert field.unlinked is True
    assert cleanup_range.Find.executed is True
    assert result["cross_reference_fields_unlinked"] == 1
    assert result["ranges_scanned_for_hidden_text"] == 1


def test_clean_document_removes_hidden_crossref_text_before_unlink():
    state = HiddenCrossRefState()
    field = HiddenCrossRefField(state)
    cleanup_range = HiddenCrossRefRange(state)
    document = FakeDocument([field], [cleanup_range])

    clean_document(document)

    assert state.hidden_text_present is False
    assert field.unlinked is True


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
