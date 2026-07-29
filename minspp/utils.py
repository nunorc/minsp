"""
The `minspp.utils` module provides different auxiliary functions.

The CUC (CCSDS unsegmented time code) helpers handle the time field only, there is
no P-field (preamble) support: PUS-C carries a CUC time whose format is declared
out-of-band, so the coarse and fine lengths and the epoch are arguments of these
functions rather than values read from the byte stream.

All the arithmetic is done on UTC datetimes and is therefore leap second naive. A
mission whose CUC counts a continuous time scale (TAI, GPS, mission elapsed time)
is off by the leap second offset accumulated since its epoch, this package does not
convert between time scales.
"""

import struct
from datetime import datetime, timezone, timedelta

CUC_EPOCH: datetime = datetime(1970, 1, 1, tzinfo=timezone.utc)
"""Default epoch of a CUC time, the Unix epoch. The standard makes the epoch mission
defined, the CCSDS agency-standard epoch being 1958-01-01 TAI."""

CUC_COARSE_LENGTH: int = 4
"""Default number of octets of the CUC coarse time (seconds) field."""

CUC_FINE_LENGTH: int = 3
"""Default number of octets of the CUC fine time (sub-seconds) field."""

CUC_TIME_LENGTH: int = CUC_COARSE_LENGTH + CUC_FINE_LENGTH
"""Default total length in octets of a CUC time field."""

def cuc_time_now(coarse_length: int = CUC_COARSE_LENGTH,
                 fine_length: int = CUC_FINE_LENGTH,
                 epoch: datetime = CUC_EPOCH) -> bytes:
    """
    Generates a CUC time from the current UTC time.

    The result is `coarse_length` octets of seconds since the epoch followed by
    `fine_length` octets of sub-seconds, i.e. `coarse_length + fine_length` octets
    in total (7 by default). The fine time is rounded to the nearest unit, and a
    value that rounds up to a whole second carries into the coarse time.

    :param coarse_length: Number of octets of the coarse time field, default is `4`.
    :type coarse_length: int
    :param fine_length: Number of octets of the fine time field, default is `3`.
    :type fine_length: int
    :param epoch: Epoch the coarse time counts from, default is the Unix epoch. The
    standard makes the epoch mission defined.
    :type epoch: datetime

    :raises ValueError: Invalid CUC coarse or fine time length.
    :raises OverflowError: Current time does not fit in the coarse time field.

    :return: CUC time bytes.
    :rtype: bytes
    """
    if coarse_length < 1 or fine_length < 0:
        raise ValueError("Invalid CUC time length, "
                         "coarse length must be positive and fine length non-negative.")

    # the delta is kept in the integer fields of the timedelta, a float number of
    # seconds loses sub-microsecond resolution for the older mission epochs
    delta = datetime.now(timezone.utc) - epoch
    seconds = delta.days * 86400 + delta.seconds
    scale = 1 << (8 * fine_length)

    # round to the nearest fine time unit instead of truncating, carrying a value
    # that rounds up to a whole second into the coarse time
    fractional = (delta.microseconds * scale + 500000) // 1000000
    if fractional >= scale:
        seconds += 1
        fractional = 0

    return seconds.to_bytes(coarse_length, byteorder='big') \
        + fractional.to_bytes(fine_length, byteorder='big')

def cuc_as_datetime(cuc_time: bytes, coarse_length: int = CUC_COARSE_LENGTH,
                    epoch: datetime = CUC_EPOCH) -> datetime:
    """
    Converts a CUC time to a UTC datetime.

    The fine time length is taken from the remaining octets, so any CUC length
    produced by `cuc_time_now` is decoded with the matching resolution. The epoch
    must be the same one used to generate the time, the CUC field itself does not
    carry it.

    :param cuc_time: The CUC time bytes.
    :type cuc_time: bytes
    :param coarse_length: Number of octets of the coarse time field, default is `4`.
    :type coarse_length: int
    :param epoch: Epoch the coarse time counts from, default is the Unix epoch. The
    standard makes the epoch mission defined.
    :type epoch: datetime

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

CRC16_POLYNOMIAL: int = 0x1021
"""Generator polynomial of the CRC-16-CCITT, i.e. `x^16 + x^12 + x^5 + 1`."""

CRC16_SEED: int = 0xFFFF
"""Initial value (seed) of the CRC-16-CCITT."""

def crc16_ccitt(data: bytes, seed: int = CRC16_SEED) -> int:
    """
    Computes the CRC-16-CCITT of a byte stream.

    Uses the generator polynomial `x^16 + x^12 + x^5 + 1` seeded with `0xFFFF`,
    without input or output reflection and without a final XOR, as used by the
    packet error control field of a space packet. Computed bit by bit, no lookup
    table involved.

    :param data: The byte stream.
    :type data: bytes
    :param seed: Initial value of the CRC, default is `0xFFFF`.
    :type seed: int

    :return: The CRC value (16 bits).
    :rtype: int
    """
    crc = seed & 0xFFFF

    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ CRC16_POLYNOMIAL) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF

    return crc

MAL_STRING_LENGTH_SIZE: int = 2
"""Number of octets of the length prefix of a MAL variable length string field."""

def mal_encode_string(s: str) -> bytes:
    """
    Encodes a string as a MAL length prefixed field.

    The result is a `MAL_STRING_LENGTH_SIZE` octet big-endian length followed by
    the UTF-8 encoded string.

    :param s: The string to encode.
    :type s: str

    :raises ValueError: Encoded string too long for the length field.

    :return: The length prefixed string bytes.
    :rtype: bytes
    """
    encoded = s.encode('utf-8')

    if len(encoded) > 0xFFFF:
        raise ValueError("Encoded string too long for the MAL length field.")

    return struct.pack(">H", len(encoded)) + encoded

def mal_decode_string(data: bytes, offset: int) -> tuple[str, int]:
    """
    Decodes a MAL length prefixed string field.

    :param data: The byte stream.
    :type data: bytes
    :param offset: Offset of the length prefix in the byte stream.
    :type offset: int

    :raises ValueError: Insufficient data for the string field.

    :return: The decoded string and the offset just after the field.
    :rtype: tuple[str, int]
    """
    if len(data) < offset + MAL_STRING_LENGTH_SIZE:
        raise ValueError("Insufficient data for MAL string length field.")

    length = struct.unpack(">H", data[offset:offset+MAL_STRING_LENGTH_SIZE])[0]
    start = offset + MAL_STRING_LENGTH_SIZE
    end = start + length

    if len(data) < end:
        raise ValueError("Insufficient data for MAL string field.")

    return data[start:end].decode('utf-8'), end
