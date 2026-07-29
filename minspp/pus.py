"""
The `minspp.pus` module provides PUS header related classes.
"""

import struct
from dataclasses import dataclass, field

from .utils import CUC_COARSE_LENGTH, CUC_TIME_LENGTH, cuc_time_now

@dataclass
class PUSHeader:
    """
    Represents a Packet Utilization Standard (PUS) secondary header as used in
    CCSDS space packets.

    The PUS secondary header adds standardized metadata to a CCSDS space packet,
    including service type, service subtype, source ID, and an optional timestamp
    in CUC format.

    :param version: PUS version number (4 bits).
    :type version: int
    :param ack: Acknowledgment flags, only for telecommands (4 bits).
    :type ack: int
    :param service_type: PUS service type (1 byte).
    :type service_type: int
    :param service_subtype: PUS service subtype (1 byte).
    :type service_subtype: int
    :param source_id: Identifier of the source application or subsystem (1 byte).
    :type source_id: int
    :param has_time: Sequence count, default is `0` (14 bits).
    :type has_time: bool
    :param cuc_time: Optional CUC-formatted timestamp (`cuc_time_length` bytes).
    :param cuc_time: bytes.
    :param cuc_time_length: Length in bytes of the CUC timestamp, default is `7`.
    Ignored when `cuc_time` is given, in which case it is derived from it.
    :type cuc_time_length: int
    """
    version: int = 1
    ack: int = 0
    service_type: int = 1
    service_subtype: int = 1
    source_id: int = 0
    has_time: bool = False
    cuc_time: bytes = b''
    cuc_time_length: int = field(default=CUC_TIME_LENGTH, repr=False)

    def __post_init__(self):
        if self.cuc_time:
            self.cuc_time_length = len(self.cuc_time)
        elif self.has_time:
            self.cuc_time = cuc_time_now(fine_length=self.fine_time_length())

    def fine_time_length(self) -> int:
        """
        Number of bytes of the fine time (sub-seconds) part of the CUC timestamp.

        :raises ValueError: Invalid CUC time length.

        :return: The fine time length.
        :rtype: int
        """
        if self.cuc_time_length < CUC_COARSE_LENGTH:
            raise ValueError(f"Invalid CUC time length, must be at least {CUC_COARSE_LENGTH}.")

        return self.cuc_time_length - CUC_COARSE_LENGTH

    def as_bytes(self) -> bytes:
        """
        Packs the PUS header as a byte stream.

        :return: PUS header bytes.
        :rtype: bytes
        """
        first_byte = ((self.version & 0x0F) << 4) | (self.ack & 0x0F)
        header = struct.pack(">BBBB",
                            first_byte, self.service_type, self.service_subtype, self.source_id)

        if not self.has_time:
            return header

        cuc_time = self.cuc_time or cuc_time_now(fine_length=self.fine_time_length())

        return header + cuc_time

    @classmethod
    def from_bytes(cls, data: bytes, has_time: bool = False,
                   cuc_time_length: int = CUC_TIME_LENGTH) -> "PUSHeader":
        """
        Unpacks a byte stream into a `PUSHeader` instance.

        :param data: The byte stream.
        :type data: bytes
        :param has_time: Includes a CUC time in header.
        :type has_time: bool
        :param cuc_time_length: Length in bytes of the CUC time, default is `7`.
        :type cuc_time_length: int

        :raises ValueError: Insufficient data for PUS header.
        :raises ValueError: Invalid CUC time length.
        :raises ValueError: Insufficient data for PUS header with CUC time.

        :return: A new `PUSHeader`.
        :rtype: PUSHeader
        """
        if len(data) < 4:
            raise ValueError("Insufficient data for PUS header.")

        first_byte, service_type, service_subtype, source_id = struct.unpack(">BBBB", data[:4])
        version = (first_byte >> 4) & 0x0F
        ack = first_byte & 0x0F

        cuc_time = b''
        if has_time:
            if cuc_time_length < CUC_COARSE_LENGTH:
                raise ValueError(f"Invalid CUC time length, must be at least {CUC_COARSE_LENGTH}.")
            if len(data) < 4 + cuc_time_length:
                raise ValueError("Insufficient data for PUS header with CUC time.")
            cuc_time = data[4:4+cuc_time_length]

        return cls(
            version=version,
            ack=ack,
            service_type=service_type,
            service_subtype=service_subtype,
            source_id=source_id,
            has_time=has_time,
            cuc_time=cuc_time,
            cuc_time_length=cuc_time_length
        )
