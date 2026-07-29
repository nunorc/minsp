
from datetime import datetime, timedelta, timezone

import pytest

from minspp.utils import (CRC16_SEED, CUC_COARSE_LENGTH, CUC_EPOCH, CUC_FINE_LENGTH,
                          CUC_TIME_LENGTH, MAL_STRING_LENGTH_SIZE, crc16_ccitt,
                          cuc_as_datetime, cuc_time_now, mal_decode_string, mal_encode_string)

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

def test_cuc_epoch_default_is_the_unix_epoch():
    assert CUC_EPOCH == datetime(1970, 1, 1, tzinfo=timezone.utc)

def test_cuc_as_datetime_custom_epoch():
    # the CCSDS agency-standard epoch, 1958-01-01
    epoch = datetime(1958, 1, 1, tzinfo=timezone.utc)
    cuc_time = b'\x00\x00\x00\x01\x80\x00\x00'

    assert cuc_as_datetime(cuc_time, epoch=epoch) == \
        datetime(1958, 1, 1, 0, 0, 1, 500000, tzinfo=timezone.utc)

    # the same octets against the default epoch are a different instant
    assert cuc_as_datetime(cuc_time) != cuc_as_datetime(cuc_time, epoch=epoch)

def test_cuc_time_now_custom_epoch_round_trip():
    epoch = datetime(2000, 1, 1, tzinfo=timezone.utc)

    now = datetime.now(timezone.utc)
    value = cuc_as_datetime(cuc_time_now(epoch=epoch), epoch=epoch)

    assert abs((value - now).total_seconds()) < 2

def test_cuc_time_now_custom_epoch_counts_from_it():
    epoch = datetime(2000, 1, 1, tzinfo=timezone.utc)
    offset = (epoch - CUC_EPOCH).total_seconds()

    seconds = int.from_bytes(cuc_time_now(epoch=epoch)[:CUC_COARSE_LENGTH], byteorder='big')
    default = int.from_bytes(cuc_time_now()[:CUC_COARSE_LENGTH], byteorder='big')

    # a later epoch yields a smaller count, by exactly the distance between epochs
    assert abs((default - seconds) - offset) < 2

def test_cuc_time_now_mission_elapsed_time():
    # a mission elapsed time epoch, i.e. a count from launch
    epoch = datetime.now(timezone.utc) - timedelta(days=1)
    seconds = int.from_bytes(cuc_time_now(epoch=epoch)[:CUC_COARSE_LENGTH], byteorder='big')

    assert abs(seconds - 86400) < 2

def test_cuc_time_now_rounds_the_fine_time():
    # an epoch 999 milliseconds past a whole second, so a coarse only time rounds up
    epoch = datetime.now(timezone.utc) - timedelta(seconds=10, milliseconds=999)

    cuc_time = cuc_time_now(fine_length=0, epoch=epoch)

    assert len(cuc_time) == CUC_COARSE_LENGTH
    # truncating the sub-second part instead of rounding it would give 10
    assert int.from_bytes(cuc_time, byteorder='big') == 11

def test_cuc_time_now_fine_time_carries_into_the_coarse_time():
    # a fine time that rounds up to a whole second must not overflow its field
    epoch = datetime.now(timezone.utc) - timedelta(seconds=10, microseconds=999999)

    cuc_time = cuc_time_now(fine_length=1, epoch=epoch)

    assert len(cuc_time) == CUC_COARSE_LENGTH + 1
    assert int.from_bytes(cuc_time[:CUC_COARSE_LENGTH], byteorder='big') == 11
    assert cuc_time[CUC_COARSE_LENGTH] <= 1

def test_cuc_time_now_fine_time_resolution():
    # every fine time length keeps the round trip within one unit of its resolution
    for fine_length in range(1, 5):
        now = datetime.now(timezone.utc)
        value = cuc_as_datetime(cuc_time_now(fine_length=fine_length))

        assert abs((value - now).total_seconds()) < 1 + 1 / (1 << (8 * fine_length))

def test_mal_string_round_trip():
    for value in ['', 'a', 'space packet', 'ãéï non ascii', 'x' * 300]:
        encoded = mal_encode_string(value)

        assert len(encoded) == MAL_STRING_LENGTH_SIZE + len(value.encode('utf-8'))
        assert mal_decode_string(encoded, 0) == (value, len(encoded))

def test_mal_string_round_trip_with_offset():
    prefix = b'\xde\xad\xbe\xef'
    encoded = prefix + mal_encode_string('domain') + mal_encode_string('zone')

    value, offset = mal_decode_string(encoded, len(prefix))
    assert value == 'domain'

    value, offset = mal_decode_string(encoded, offset)
    assert value == 'zone'
    assert offset == len(encoded)

def test_mal_encode_string_known_value():
    assert mal_encode_string('ab') == b'\x00\x02ab'

def test_mal_encode_string_too_long():
    with pytest.raises(ValueError):
        mal_encode_string('x' * (0xFFFF + 1))

def test_mal_decode_string_insufficient_data():
    with pytest.raises(ValueError):
        mal_decode_string(b'\x00', 0)

    with pytest.raises(ValueError):
        mal_decode_string(b'\x00\x04ab', 0)

def test_crc16_ccitt_check_value():
    # the CRC-16/CCITT-FALSE check value for the ASCII string "123456789"
    assert crc16_ccitt(b'123456789') == 0x29B1

def test_crc16_ccitt_empty_data():
    assert crc16_ccitt(b'') == CRC16_SEED

def test_crc16_ccitt_over_own_crc_is_zero():
    data = b'\x00\x0b\xc0\x00\x00\x06hello'
    crc = crc16_ccitt(data)

    # appending the CRC to the data makes the CRC of the whole stream zero
    assert crc16_ccitt(data + crc.to_bytes(2, byteorder='big')) == 0

def test_crc16_ccitt_detects_a_flipped_bit():
    data = bytearray(b'\x00\x0b\xc0\x00\x00\x06hello')
    crc = crc16_ccitt(data)

    data[-1] ^= 0x01
    assert crc16_ccitt(data) != crc
