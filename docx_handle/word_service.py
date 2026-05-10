from __future__ import annotations

import os
import queue
import logging
import sys
import threading
import tempfile
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Protocol

from .errors import DocumentProcessingError, WordAutomationUnavailableError

logger = logging.getLogger(__name__)

WD_FIND_STOP = 0
MAX_HIDDEN_DELETES_PER_RANGE = 1000

KNOWN_CROSS_REFERENCE_CODES = {"REF", "PAGEREF", "NOTEREF"}
KNOWN_CROSS_REFERENCE_TYPES = {3, 37, 72}

# Hidden runs that start with these prefixes in cross-reference results should be
# made visible rather than deleted.  The trailing space is intentional.
CROSS_REFERENCE_VISIBLE_PREFIXES = ("Таблица ", "Рисунок ")


class DocumentEngine(Protocol):
    def process(self, input_path: Path, output_path: Path) -> None:
        ...


class WordFieldLike(Protocol):
    Type: int
    Code: Any


class WordRangeLike(Protocol):
    Find: Any


def _field_code_token(field: Any) -> str:
    code = getattr(getattr(field, "Code", None), "Text", "")
    if not isinstance(code, str):
        return ""
    token = code.strip().split(maxsplit=1)
    return token[0].upper() if token else ""


def is_cross_reference_field(field: Any) -> bool:
    token = _field_code_token(field)
    if token in KNOWN_CROSS_REFERENCE_CODES:
        return True
    field_type = getattr(field, "Type", None)
    return field_type in KNOWN_CROSS_REFERENCE_TYPES


def _safe_call(obj: Any, method: str, *args: Any, **kwargs: Any) -> None:
    fn = getattr(obj, method, None)
    if callable(fn):
        fn(*args, **kwargs)


def _safe_set(obj: Any, attr: str, value: Any) -> None:
    if hasattr(obj, attr):
        try:
            setattr(obj, attr, value)
        except Exception:
            pass


def _safe_get_text_retrieval_mode(word_range: Any) -> Any | None:
    return getattr(word_range, "TextRetrievalMode", None)


def _set_include_hidden_text(word_range: Any, include: bool) -> None:
    text_retrieval_mode = _safe_get_text_retrieval_mode(word_range)
    if text_retrieval_mode is not None:
        _safe_set(text_retrieval_mode, "IncludeHiddenText", include)


def remove_hidden_text_from_ranges(ranges: Iterable[Any]) -> int:
    cleaned = 0
    for word_range in ranges:
        search_range = getattr(word_range, "Duplicate", word_range)
        _set_include_hidden_text(search_range, True)
        find = getattr(search_range, "Find", None)
        if find is None:
            continue

        _safe_call(find, "ClearFormatting")
        _safe_set(find, "Text", "")
        _safe_set(find, "Forward", True)
        _safe_set(find, "Wrap", WD_FIND_STOP)
        _safe_set(find, "Format", True)
        _safe_set(find, "MatchCase", False)
        _safe_set(find, "MatchWholeWord", False)
        _safe_set(find, "MatchWildcards", False)
        _safe_set(find, "MatchSoundsLike", False)
        _safe_set(find, "MatchAllWordForms", False)

        font = getattr(find, "Font", None)
        if font is not None:
            _safe_set(font, "Hidden", True)

        replacement = getattr(find, "Replacement", None)
        if replacement is not None:
            _safe_call(replacement, "ClearFormatting")
            replacement_font = getattr(replacement, "Font", None)
            if replacement_font is not None:
                _safe_set(replacement_font, "Hidden", False)

        deletes = 0
        while deletes < MAX_HIDDEN_DELETES_PER_RANGE:
            found = getattr(find, "Execute", lambda **kwargs: False)()
            if not found:
                break
            delete = getattr(search_range, "Delete", None)
            removed = delete() if callable(delete) else 0
            if removed == 0:
                break
            deletes += 1
        cleaned += deletes
    return cleaned


def _unhide_prefix_in_range(word_range: Any, prefix: str) -> int:
    """Find hidden runs of *prefix* in *word_range* and clear their hidden formatting.

    Uses the same Find-loop pattern as :func:`remove_hidden_text_from_ranges` but
    sets ``Font.Hidden = False`` on each match instead of deleting it.
    """
    search_range = getattr(word_range, "Duplicate", word_range)
    _set_include_hidden_text(search_range, True)
    find = getattr(search_range, "Find", None)
    if find is None:
        return 0

    _safe_call(find, "ClearFormatting")
    _safe_set(find, "Text", prefix)
    _safe_set(find, "Forward", True)
    _safe_set(find, "Wrap", WD_FIND_STOP)
    _safe_set(find, "Format", True)
    _safe_set(find, "MatchCase", True)
    _safe_set(find, "MatchWholeWord", False)
    _safe_set(find, "MatchWildcards", False)
    _safe_set(find, "MatchSoundsLike", False)
    _safe_set(find, "MatchAllWordForms", False)

    font = getattr(find, "Font", None)
    if font is not None:
        _safe_set(font, "Hidden", True)

    count = 0
    execute_fn = getattr(find, "Execute", None)
    if not callable(execute_fn):
        return 0
    while count < MAX_HIDDEN_DELETES_PER_RANGE:
        if not execute_fn():
            break
        found_font = getattr(search_range, "Font", None)
        if found_font is not None:
            _safe_set(found_font, "Hidden", False)
        count += 1
    return count


def unhide_table_figure_prefixes_in_cross_reference_results(document: Any) -> int:
    """Unhide hidden 'Таблица ' and 'Рисунок ' prefixes in cross-reference field results.

    For every cross-reference field in every story, if the result range contains
    a run whose text matches one of :data:`CROSS_REFERENCE_VISIBLE_PREFIXES` and
    that run carries ``Font.Hidden = True``, the hidden formatting is removed so
    the prefix becomes visible in the rendered document.
    """
    total = 0
    for fields in iter_story_field_collections(document):
        count = getattr(fields, "Count", 0)
        if not isinstance(count, int):
            continue
        for index in range(count, 0, -1):
            field = fields[index]
            if not is_cross_reference_field(field):
                continue
            result_range = getattr(field, "Result", None)
            if result_range is None:
                continue
            for prefix in CROSS_REFERENCE_VISIBLE_PREFIXES:
                total += _unhide_prefix_in_range(result_range, prefix)
    return total


def iter_cross_reference_fields(fields: Iterable[Any]) -> Iterable[Any]:
    for field in fields:
        if is_cross_reference_field(field):
            yield field


def iter_story_field_collections(document: Any) -> Iterable[Any]:
    seen: set[int] = set()
    for story_range in iter_word_cleanup_ranges(document):
        story_fields = getattr(story_range, "Fields", None)
        if story_fields is None:
            continue
        marker = id(story_fields)
        if marker in seen:
            continue
        seen.add(marker)
        yield story_fields


def remove_hidden_text_from_cross_reference_results(document: Any) -> int:
    scanned = 0
    for fields in iter_story_field_collections(document):
        count = getattr(fields, "Count", 0)
        if not isinstance(count, int):
            continue
        for index in range(count, 0, -1):
            field = fields[index]
            if not is_cross_reference_field(field):
                continue
            result_range = getattr(field, "Result", None)
            if result_range is None:
                continue
            scanned += 1
            remove_hidden_text_from_ranges([result_range])
    return scanned


def iter_word_cleanup_ranges(document: Any) -> Iterable[Any]:
    seen: set[int] = set()
    story_ranges = getattr(document, "StoryRanges", None)
    if story_ranges is not None:
        try:
            for story in story_ranges:
                current = story
                while current is not None:
                    marker = id(current)
                    if marker in seen:
                        break
                    seen.add(marker)
                    yield current
                    current = getattr(current, "NextStoryRange", None)
        except TypeError:
            pass

    content = getattr(document, "Content", None)
    if content is not None:
        marker = id(content)
        if marker not in seen:
            yield content


def clean_document(document: Any) -> dict[str, int]:
    # Unhide "Таблица " / "Рисунок " prefixes first so the subsequent delete pass
    # leaves them intact.
    unhide_count = unhide_table_figure_prefixes_in_cross_reference_results(document)
    cross_reference_hidden_text_count = remove_hidden_text_from_cross_reference_results(document)
    hidden_text_count = remove_hidden_text_from_ranges(iter_word_cleanup_ranges(document))
    return {
        "cross_reference_fields_unlinked": 0,
        "cross_reference_prefixes_unhidden": unhide_count,
        "cross_reference_results_scanned_for_hidden_text": cross_reference_hidden_text_count,
        "cross_reference_results_rewritten": 0,
        "ranges_scanned_for_hidden_text": hidden_text_count,
    }


class SingleWorkerDocxService:
    def __init__(self, engine_factory: Callable[[], DocumentEngine]):
        self._engine_factory = engine_factory
        self._jobs: queue.Queue[_Job] = queue.Queue()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._started = False
        self._start_lock = threading.Lock()
        self._ready = threading.Event()
        self._startup_error: BaseException | None = None

    def start(self) -> None:
        with self._start_lock:
            if self._started:
                return
            self._thread = threading.Thread(target=self._worker_loop, name="docx-handle-worker", daemon=True)
            self._thread.start()
            self._started = True
        self._ready.wait()
        if self._startup_error is not None:
            raise WordAutomationUnavailableError("Unable to start the Word automation engine.") from self._startup_error

    def close(self) -> None:
        self._stop.set()
        self._jobs.put(_Job.sentinel())
        if self._thread is not None:
            self._thread.join(timeout=10)

    def process_bytes(self, filename: str, content: bytes) -> bytes:
        self.start()
        suffix = _safe_suffix(filename)
        logger.info("queue: accepted %s (%d bytes)", filename, len(content))
        with tempfile.TemporaryDirectory(prefix="docx-handle-") as temp_dir:
            temp_root = Path(temp_dir)
            input_path = temp_root / f"input{suffix}"
            output_path = temp_root / "output.docx"
            input_path.write_bytes(content)
            job = _Job(input_path=input_path, output_path=output_path)
            logger.info("queue: waiting for worker on %s", input_path.name)
            self._jobs.put(job)
            job.done.wait()
            if job.error is not None:
                raise job.error
            logger.info("queue: finished %s", filename)
            return output_path.read_bytes()

    def _worker_loop(self) -> None:
        try:
            engine = self._engine_factory()
        except Exception as exc:
            self._startup_error = exc
            traceback.print_exception(exc, file=sys.stderr)
            self._ready.set()
            self._stop.set()
            return

        self._ready.set()

        while not self._stop.is_set():
            job = self._jobs.get()
            try:
                if job.is_sentinel:
                    return
                logger.info("worker: starting %s -> %s", job.input_path.name, job.output_path.name)
                engine.process(job.input_path, job.output_path)
                logger.info("worker: completed %s", job.output_path.name)
            except BaseException as exc:  # noqa: BLE001 - propagate any failure to the caller
                job.error = exc
                traceback.print_exception(exc, file=sys.stderr)
            finally:
                job.done.set()


@dataclass
class _Job:
    input_path: Path | None = None
    output_path: Path | None = None
    done: threading.Event = field(default_factory=threading.Event)
    error: BaseException | None = None
    is_sentinel: bool = False

    @classmethod
    def sentinel(cls) -> "_Job":
        return cls(is_sentinel=True)


def _safe_suffix(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    return suffix if suffix == ".docx" else ".docx"


def default_engine_factory() -> DocumentEngine:
    if os.name == "nt":
        scripts_dir = Path(sys.executable).resolve().parent
        if scripts_dir.exists():
            if str(scripts_dir) not in sys.path:
                sys.path.insert(0, str(scripts_dir))
            add_dll_directory = getattr(os, "add_dll_directory", None)
            if callable(add_dll_directory):
                try:
                    add_dll_directory(str(scripts_dir))
                except OSError:
                    pass

    try:
        import pythoncom  # type: ignore
        import win32com.client  # type: ignore
    except Exception as exc:  # pragma: no cover - depends on host platform
        raise WordAutomationUnavailableError(
            "pywin32 is required on Windows hosts with Microsoft Word installed."
        ) from exc

    class _ComWordEngine:
        def process(self, input_path: Path, output_path: Path) -> None:
            pythoncom.CoInitialize()
            app = None
            document = None
            saved = False
            try:
                logger.info("word: creating Word.Application")
                for creator in (
                    getattr(win32com.client, "GetActiveObject", None),
                    getattr(win32com.client, "Dispatch", None),
                    getattr(win32com.client, "DispatchEx", None),
                ):
                    if callable(creator):
                        try:
                            app = creator("Word.Application")
                            break
                        except Exception:
                            continue
                if app is None:
                    raise RuntimeError("Unable to create a Word.Application COM object.")
                app.Visible = False
                app.DisplayAlerts = 0
                try:
                    app.ScreenUpdating = False
                except Exception:
                    pass
                try:
                    app.Options.SaveNormalPrompt = False
                except Exception:
                    pass

                logger.info("word: opening %s", input_path)
                document = app.Documents.Open(
                    FileName=str(input_path),
                    ReadOnly=False,
                    AddToRecentFiles=False,
                    ConfirmConversions=False,
                )
                cleanup_stats = clean_document(document)
                logger.info(
                    "word: cleanup complete cross_refs=%d hidden_ranges=%d cross_ref_ranges=%d",
                    cleanup_stats["cross_reference_fields_unlinked"],
                    cleanup_stats["ranges_scanned_for_hidden_text"],
                    cleanup_stats["cross_reference_results_scanned_for_hidden_text"],
                )
                logger.info("word: saving to %s", output_path)
                document.SaveAs2(FileName=str(output_path), FileFormat=16)
                saved = True
            except Exception as exc:  # pragma: no cover - exercised on Windows host
                raise DocumentProcessingError("Word failed while processing the document.") from exc
            finally:
                if document is not None:
                    try:
                        document.Close(SaveChanges=False)
                    except Exception:
                        pass
                if app is not None:
                    try:
                        app.Quit()
                    except Exception:
                        pass
                pythoncom.CoUninitialize()

    return _ComWordEngine()


def build_processor() -> SingleWorkerDocxService:
    return SingleWorkerDocxService(default_engine_factory)
