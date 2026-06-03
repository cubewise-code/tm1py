"""Module C — v12 ``Metrics()`` ``$filter`` builder (pure).

Turns ``(cube, metrics, timestamp)`` into the relative OData URL the v12 path
GETs. Extracted from PR #1396's inline ``MetricService.get()`` logic so the
filter string can be unit-tested without a live server.
"""

from datetime import datetime
from typing import List, Optional

from TM1py.Utils.Utils import build_url_friendly_object_name, datetime_to_iso


def build_metrics_url(
    cube_name: str = None,
    metrics: Optional[List[str]] = None,
    timestamp: datetime = None,
) -> str:
    """Build the relative ``/Metrics()`` URL, optionally with a ``$filter``.

    :param cube_name: restrict to a single cube (``CubeName eq '<cube>'``).
    :param metrics: restrict to these canonical metric names
        (``Name eq 'm1' or Name eq 'm2' ...``).
    :param timestamp: only metrics newer than this (``Timestamp gt <iso>``).
    :return: ``"/Metrics()"`` or ``"/Metrics()?$filter=..."``.
    """
    clauses: List[str] = []

    if cube_name:
        clauses.append(f"CubeName eq '{build_url_friendly_object_name(cube_name)}'")

    if metrics:
        clauses.append(" or ".join(f"Name eq '{build_url_friendly_object_name(m)}'" for m in metrics))

    if timestamp:
        clauses.append(f"Timestamp gt {datetime_to_iso(timestamp)}")

    if not clauses:
        return "/Metrics()"

    filter_string = " and ".join(f"({clause})" for clause in clauses)
    return f"/Metrics()?$filter={filter_string}"
