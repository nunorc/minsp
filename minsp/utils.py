"""
The `minsp.utils` module provides different auxiliary functions.
"""

import struct
from datetime import datetime, timezone, timedelta

epoch: datetime = datetime(1970, 1, 1, tzinfo=timezone.utc)

def cuc_time_now() -> bytes:
    """ Generates a 7-byte CUC time from the current UTC time. """
    now = datetime.now(timezone.utc)
    delta = (now - epoch).total_seconds()
    seconds = int(delta)
    fractional = int((delta - seconds) * 2**24)

    return seconds.to_bytes(4, byteorder='big') + fractional.to_bytes(3, byteorder='big')

def cuc_as_datetime(cuc_time) -> datetime:
    """Converts a CUC time to a UTC datetime."""
    seconds = int.from_bytes(cuc_time[:4], byteorder='big')
    fractional = int.from_bytes(cuc_time[4:], byteorder='big')
    frac_seconds = fractional / (1 << 24)  # 2^24 resolution

    return epoch + timedelta(seconds=seconds + frac_seconds)

def mal_encode_string(s: str) -> bytes:
    """Encode a string to pack header."""
    encoded = s.encode('utf-8')

    return struct.pack("B", len(encoded)) + encoded

def mal_decode_string(data: bytes, offset: int) -> tuple[str, int]:
    """Decode a string from a packed header."""
    length = struct.unpack(">H", data[offset:offset+2])[0]
    value = data[offset + 2:offset + 2 + length].decode('utf-8')

    return value, offset + 1 + length
