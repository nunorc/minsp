
from datetime import datetime, timezone

import pytest

from minspp.utils import (CRC16_SEED, CUC_COARSE_LENGTH, CUC_FINE_LENGTH, CUC_TIME_LENGTH,
                          MAL_STRING_LENGTH_SIZE, crc16_ccitt, cuc_as_datetime, cuc_time_now,
                          mal_decode_string, mal_encode_string)

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
