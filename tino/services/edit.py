'''Exact-string replacement on text documents, used by the MCP ``edit_file`` tool.'''

import re
from dataclasses import dataclass

from ..models import FileEdit


class EditError(ValueError):
    '''An edit could not be applied (no match, ambiguous match, or a no-op).'''


@dataclass(frozen=True)
class Splice:
    '''Replace ``text[start:end]`` with ``insert`` (character offsets).'''
    start: int
    end: int
    insert: str


def apply_edits(text: str, edits: list[FileEdit]) -> tuple[str, list[Splice]]:
    '''Apply *edits* in order and return the new text plus the splices made.

    Every edit applies to the result of the previous one. Its ``old_string``
    must occur exactly once unless ``replace_all`` is set. The function is pure,
    so a failing edit raises :class:`EditError` before anything is changed.

    The splices are expressed against the text as it is when each one applies,
    so replaying them in order on *text* reproduces the result. This lets a
    caller apply the same change incrementally (e.g. to a live Yjs document)
    instead of replacing the whole document.
    '''
    splices: list[Splice] = []

    for number, edit in enumerate(edits, start=1):
        _validate(text, edit, number)
        text, made = _replace(text, edit)
        splices.extend(made)

    return text, splices


def _validate(text: str, edit: FileEdit, number: int) -> None:
    '''Raise :class:`EditError` if *edit* cannot be applied unambiguously to *text*.'''
    prefix = f'Edit {number}'

    if not edit.old_string:
        raise EditError(f'{prefix}: old_string must not be empty')

    if edit.old_string == edit.new_string:
        raise EditError(f'{prefix}: old_string and new_string are identical')

    count = text.count(edit.old_string)

    if count == 0:
        raise EditError(f'{prefix}: old_string not found in the file')

    if count > 1 and not edit.replace_all:
        raise EditError(
            f'{prefix}: old_string matches {count} times; add surrounding context '
            f'to make it unique, or set replace_all',
        )


def _replace(text: str, edit: FileEdit) -> tuple[str, list[Splice]]:
    '''Replace the first (or every) occurrence, returning the text and its splices.'''
    old, new  = edit.old_string, edit.new_string
    positions = [match.start() for match in re.finditer(re.escape(old), text)]

    if not edit.replace_all:
        positions = positions[:1]

    growth  = len(new) - len(old)
    splices = [
        Splice(pos + index * growth, pos + index * growth + len(old), new)
        for index, pos in enumerate(positions)
    ]

    count = -1 if edit.replace_all else 1
    return text.replace(old, new, count), splices
