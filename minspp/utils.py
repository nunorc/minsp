"""
The `minspp.utils` module provides different auxiliary functions.
"""

import struct
from datetime import datetime, timezone, timedelta

epoch: datetime = datetime(1970, 1, 1, tzinfo=timezone.utc)

CUC_COARSE_LENGTH: int = 4
"""Default number of octets of the CUC coarse time (seconds) field."""

CUC_FINE_LENGTH: int = 3
"""Default number of octets of the CUC fine time (sub-seconds) field."""

CUC_TIME_LENGTH: int = CUC_COARSE_LENGTH + CUC_FINE_LENGTH
"""Default total length in octets of a CUC time field."""

def cuc_time_now(coarse_length: int = CUC_COARSE_LENGTH,
                 fine_length: int = CUC_FINE_LENGTH) -> bytes:
    """
    Generates a CUC time from the current UTC time.

    The result is `coarse_length` octets of seconds since the epoch followed by
    `fine_length` octets of sub-seconds, i.e. `coarse_length + fine_length` octets
    in total (7 by default).

    :param coarse_length: Number of octets of the coarse time field, default is `4`.
    :type coarse_length: int
    :param fine_length: Number of octets of the fine time field, default is `3`.
    :type fine_length: int

    :raises ValueError: Invalid CUC coarse or fine time length.
    :raises OverflowError: Current time does not fit in the coarse time field.

    :return: CUC time bytes.
    :rtype: bytes
    """
    if coarse_length < 1 or fine_length < 0:
        raise ValueError("Invalid CUC time length, "
                         "coarse length must be positive and fine length non-negative.")

    now = datetime.now(timezone.utc)
    delta = (now - epoch).total_seconds()
    seconds = int(delta)
    fractional = int((delta - seconds) * 2**(8 * fine_length))

    return seconds.to_bytes(coarse_length, byteorder='big') \
        + fractional.to_bytes(fine_length, byteorder='big')

def cuc_as_datetime(cuc_time: bytes, coarse_length: int = CUC_COARSE_LENGTH) -> datetime:
    """
    Converts a CUC time to a UTC datetime.

    The fine time length is taken from the remaining octets, so any CUC length
    produced by `cuc_time_now` is decoded with the matching resolution.

    :param cuc_time: The CUC time bytes.
    :type cuc_time: bytes
    :param coarse_length: Number of octets of the coarse time field, default is `4`.
    :type coarse_length: int

    :raises ValueError: Insufficient data for the CUC coarse time field.

    :return: The corresponding UTC datetime.
    :rtype: datetime
    """
    if coarse_length < 1 or len(cuc_time) < coarse_length:
        raise ValueError("Insufficient data for CUC coarse time field.")

    seconds = int.from_bytes(cuc_time[:coarse_length], byteorder='big')
    fine = cuc_time[coarse_length:]

    frac_seconds = 0.0
    if fine:
        frac_seconds = int.from_bytes(fine, byteorder='big') / (1 << (8 * len(fine)))

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
