from datetime import UTC, datetime

import pytest

from hanjan.quota import quota_day


def test_day_rolls_over_at_pacific_midnight_in_summer():
    assert str(quota_day(datetime(2026, 9, 15, 6, 59, tzinfo=UTC))) == "2026-09-14"
    assert str(quota_day(datetime(2026, 9, 15, 7, 0, tzinfo=UTC))) == "2026-09-15"  # 한국 16:00


def test_day_rolls_over_an_hour_later_in_winter():
    assert str(quota_day(datetime(2026, 12, 15, 7, 59, tzinfo=UTC))) == "2026-12-14"
    assert str(quota_day(datetime(2026, 12, 15, 8, 0, tzinfo=UTC))) == "2026-12-15"  # 한국 17:00


def test_naive_datetime_is_rejected():
    with pytest.raises(ValueError):
        quota_day(datetime(2026, 9, 15))
