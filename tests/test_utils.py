
from datetime import datetime, timezone

import pytest

from minspp.utils import (CUC_COARSE_LENGTH, CUC_FINE_LENGTH, CUC_TIME_LENGTH,
                          cuc_as_datetime, cuc_time_now)

def test_cuc_time_now_default_length():
    assert CUC_TIME_LENGTH == CUC_COARSE_LENGTH + CUC_FINE_LENGTH
    assert len(cuc_time_now()) == CUC_TIME_LENGTH

def test_cuc_time_now_custom_length():
    for fine_length in range(0, 5):
        assert len(cuc_time_now(fine_length=fine_length)) == CUC_COARSE_LENGTH + fine_length

def test_cuc_as_datetime_round_trip():
    for fine_length in range(0, 5):
        now = datetime.now(timezone.utc)
        value = cuc_as_datetime(cuc_time_now(fine_length=fine_length))

        # coarse time only truncates to the second
        assert abs((value - now).total_seconds()) < 2

def test_cuc_as_datetime_known_value():
    # 1 second after the epoch, plus half a second of fine time
    cuc_time = b'\x00\x00\x00\x01\x80\x00\x00'

    assert cuc_as_datetime(cuc_time) == datetime(1970, 1, 1, 0, 0, 1, 500000, tzinfo=timezone.utc)

def test_cuc_time_now_invalid_length():
    with pytest.raises(ValueError):
        cuc_time_now(coarse_length=0)

    with pytest.raises(ValueError):
        cuc_time_now(fine_length=-1)

def test_cuc_as_datetime_insufficient_data():
    with pytest.raises(ValueError):
        cuc_as_datetime(b'\x00\x00')
