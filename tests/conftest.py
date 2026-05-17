"""Shared helpers for the mdld_parse test suite."""
from __future__ import annotations
from typing import Iterable, Optional


def find_quad(quads: Iterable, subject: str, predicate: str, object_value: Optional[str]):
    """Find the first quad matching subject, predicate, object_value."""
    for q in quads:
        if (q.subject.value == subject
                and q.predicate.value == predicate
                and (object_value is None or q.object.value == object_value)):
            return q
    return None


def has_quad(quads: Iterable, subject: str, predicate: str, object_value: Optional[str]) -> bool:
    return find_quad(quads, subject, predicate, object_value) is not None


def quad_key(q) -> str:
    dt = (q.object.datatype.value if q.object.datatype else '') if q.object.term_type == 'Literal' else ''
    lang = (q.object.language or '') if q.object.term_type == 'Literal' else ''
    return f'{q.subject.value}|{q.predicate.value}|{q.object.value}|{dt}|{lang}'
