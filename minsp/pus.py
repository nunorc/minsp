"""
The `minsp.pus` module provides PUS header related classes.
"""

import struct
from dataclasses import dataclass

from .utils import cuc_time_now

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
    :param cuc_time: Optional CUC-formatted timestamp (7 bytes).
    :param cuc_time: bytes.
    """
    version: int = 1
    ack: int = 0
    service_type: int = 1
    service_subtype: int = 1
    source_id: int = 0
    has_time: bool = False
    cuc_time: bytes = b''

    def __post_init__(self):
        if self.has_time and len(self.cuc_time) == 0:
            self.cuc_time = cuc_time_now()

    def as_bytes(self) -> bytes:
        """
        Packs the PUS header as a byte stream.

        :return: PUS header bytes.
        :rtype: bytes
        """
        first_byte = ((self.version & 0x0F) << 4) | (self.ack & 0x0F)
        header = struct.pack(">BBBB",
                            first_byte, self.service_type, self.service_subtype, self.source_id)

        # pylint: disable=R1705
        if self.has_time:
            if self.cuc_time:
                return header + self.cuc_time
            else:
                return header + cuc_time_now()
        else:
            return header

    @classmethod
    def from_bytes(cls, data: bytes, has_time: bool = False) -> "PUSHeader":
        """
        Unpacks a byte stream into a `PUSHeader` instance.

        :param data: The byte stream.
        :type data: bytes
        :param has_time: Includes a CUC time in header.
        :type has_time: bool

        :raises ValueError: Insufficient data for PUS header.
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
            if len(data) < 8:
                raise ValueError("Insufficient data for PUS header with CUC time.")
            cuc_time = data[4:8]

        return cls(
            version=version,
            ack=ack,
            service_type=service_type,
            service_subtype=service_subtype,
            source_id=source_id,
            has_time=has_time,
            cuc_time=cuc_time
        )
