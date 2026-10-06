from datetime import UTC, datetime, timedelta

import pytest

from appointment.domain.model.availability import Availability


def _at(hours: int) -> datetime:
    return datetime(2026, 12, 1, 8, 0, tzinfo=UTC) + timedelta(hours=hours)


def test_rejects_end_before_start() -> None:
    with pytest.raises(ValueError):
        Availability(professional_id=1, start=_at(2), end=_at(1))


def test_rejects_non_positive_professional() -> None:
    with pytest.raises(ValueError):
        Availability(professional_id=0, start=_at(1), end=_at(2))


def test_overlap_detects_intersection() -> None:
    a = Availability(professional_id=1, start=_at(1), end=_at(3))
    assert a.overlaps_with(_at(2), _at(4)) is True
    assert a.overlaps_with(_at(0), _at(2)) is True


def test_overlap_returns_false_when_disjoint() -> None:
    a = Availability(professional_id=1, start=_at(1), end=_at(3))
    assert a.overlaps_with(_at(3), _at(4)) is False
    assert a.overlaps_with(_at(0), _at(1)) is False
