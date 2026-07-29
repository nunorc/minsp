"""
The `minspp.pus` module provides PUS header related classes.

Telemetry (TM) and telecommand (TC) packets use different secondary header
layouts, one class each: `PUSTCHeader` implements the TC layout and
`PUSTMHeader` the PUS-C TM layout.
"""

import struct
from dataclasses import dataclass, field

from .utils import CUC_COARSE_LENGTH, CUC_TIME_LENGTH, cuc_time_now

PUS_TC_HEADER_LENGTH: int = 4
"""Length in octets of a TC secondary header, excluding the optional CUC time."""

PUS_TM_HEADER_LENGTH: int = 7
"""Length in octets of a PUS-C TM secondary header, excluding the optional CUC time."""

def fine_time_length(cuc_time_length: int) -> int:
    """
    Number of octets of the fine time (sub-seconds) part of a CUC timestamp.

    :param cuc_time_length: Total length in octets of the CUC timestamp.
    :type cuc_time_length: int

    :raises ValueError: Invalid CUC time length.

    :return: The fine time length.
    :rtype: int
    """
    if cuc_time_length < CUC_COARSE_LENGTH:
        raise ValueError(f"Invalid CUC time length, must be at least {CUC_COARSE_LENGTH}.")

    return cuc_time_length - CUC_COARSE_LENGTH

@dataclass
class PUSTCHeader:
    """
    Represents a Packet Utilization Standard (PUS) telecommand (TC) secondary
    header as used in CCSDS space packets.

    The PUS secondary header adds standardized metadata to a CCSDS space packet,
    including service type, service subtype, source ID, and an optional timestamp
    in CUC format. Use `PUSTMHeader` for telemetry packets, which use a different
    field layout.

    :param version: PUS version number (4 bits).
    :type version: int
    :param ack: Acknowledgment flags (4 bits).
    :type ack: int
    :param service_type: PUS service type (1 byte).
    :type service_type: int
    :param service_subtype: PUS service subtype (1 byte).
    :type service_subtype: int
    :param source_id: Identifier of the source application or subsystem (1 byte).
    :type source_id: int
    :param has_time: Includes a CUC time in the header, default is `False`.
    :type has_time: bool
    :param cuc_time: Optional CUC-formatted timestamp (`cuc_time_length` bytes).
    :type cuc_time: bytes
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
        return fine_time_length(self.cuc_time_length)

    def as_bytes(self) -> bytes:
        """
        Packs the PUS TC header as a byte stream.

        :return: PUS TC header bytes.
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
                   cuc_time_length: int = CUC_TIME_LENGTH) -> "PUSTCHeader":
        """
        Unpacks a byte stream into a `PUSTCHeader` instance.

        :param data: The byte stream.
        :type data: bytes
        :param has_time: Includes a CUC time in header.
        :type has_time: bool
        :param cuc_time_length: Length in bytes of the CUC time, default is `7`.
        :type cuc_time_length: int

        :raises ValueError: Insufficient data for PUS TC header.
        :raises ValueError: Invalid CUC time length.
        :raises ValueError: Insufficient data for PUS TC header with CUC time.

        :return: A new `PUSTCHeader`.
        :rtype: PUSTCHeader
        """
        if len(data) < PUS_TC_HEADER_LENGTH:
            raise ValueError("Insufficient data for PUS TC header.")

        first_byte, service_type, service_subtype, source_id = struct.unpack(">BBBB", data[:4])
        version = (first_byte >> 4) & 0x0F
        ack = first_byte & 0x0F

        cuc_time = b''
        if has_time:
            if cuc_time_length < CUC_COARSE_LENGTH:
                raise ValueError(f"Invalid CUC time length, must be at least {CUC_COARSE_LENGTH}.")
            if len(data) < PUS_TC_HEADER_LENGTH + cuc_time_length:
                raise ValueError("Insufficient data for PUS TC header with CUC time.")
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

@dataclass
class PUSTMHeader:
    """
    Represents a PUS-C (ECSS-E-ST-70-41C) telemetry (TM) secondary header as used
    in CCSDS space packets.

    The TM secondary header layout differs from the telecommand one (`PUSTCHeader`):
    the acknowledgment flags are replaced by a spare nibble, and the source ID is
    replaced by a message type counter and a destination ID, giving a 7 octet
    header followed by an optional CUC timestamp.

    :param version: PUS version number, `2` for PUS-C (4 bits).
    :type version: int
    :param spare: Spare field, only for telemetry (4 bits).
    :type spare: int
    :param service_type: PUS service type (1 byte).
    :type service_type: int
    :param service_subtype: PUS message subtype (1 byte).
    :type service_subtype: int
    :param message_type_counter: Count of messages of this service type and
    subtype generated by the application process (2 bytes).
    :type message_type_counter: int
    :param destination_id: Identifier of the destination application or
    subsystem (2 bytes).
    :type destination_id: int
    :param has_time: Includes a CUC time in the header, default is `False`.
    :type has_time: bool
    :param cuc_time: Optional CUC-formatted timestamp (`cuc_time_length` bytes).
    :type cuc_time: bytes
    :param cuc_time_length: Length in bytes of the CUC timestamp, default is `7`.
    Ignored when `cuc_time` is given, in which case it is derived from it.
    :type cuc_time_length: int
    """
    version: int = 2
    spare: int = 0
    service_type: int = 1
    service_subtype: int = 1
    message_type_counter: int = 0
    destination_id: int = 0
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
        return fine_time_length(self.cuc_time_length)

    def as_bytes(self) -> bytes:
        """
        Packs the PUS-C TM header as a byte stream.

        :return: PUS-C TM header bytes.
        :rtype: bytes
        """
        first_byte = ((self.version & 0x0F) << 4) | (self.spare & 0x0F)
        header = struct.pack(">BBBHH",
                             first_byte, self.service_type, self.service_subtype,
                             self.message_type_counter, self.destination_id)

        if not self.has_time:
            return header

        cuc_time = self.cuc_time or cuc_time_now(fine_length=self.fine_time_length())

        return header + cuc_time

    @classmethod
    def from_bytes(cls, data: bytes, has_time: bool = False,
                   cuc_time_length: int = CUC_TIME_LENGTH) -> "PUSTMHeader":
        """
        Unpacks a byte stream into a `PUSTMHeader` instance.

        :param data: The byte stream.
        :type data: bytes
        :param has_time: Includes a CUC time in header.
        :type has_time: bool
        :param cuc_time_length: Length in bytes of the CUC time, default is `7`.
        :type cuc_time_length: int

        :raises ValueError: Insufficient data for PUS TM header.
        :raises ValueError: Invalid CUC time length.
        :raises ValueError: Insufficient data for PUS TM header with CUC time.

        :return: A new `PUSTMHeader`.
        :rtype: PUSTMHeader
        """
        if len(data) < PUS_TM_HEADER_LENGTH:
            raise ValueError("Insufficient data for PUS TM header.")

        first_byte, service_type, service_subtype, message_type_counter, destination_id = \
            struct.unpack(">BBBHH", data[:PUS_TM_HEADER_LENGTH])
        version = (first_byte >> 4) & 0x0F
        spare = first_byte & 0x0F

        cuc_time = b''
        if has_time:
            if cuc_time_length < CUC_COARSE_LENGTH:
                raise ValueError(f"Invalid CUC time length, must be at least {CUC_COARSE_LENGTH}.")
            if len(data) < PUS_TM_HEADER_LENGTH + cuc_time_length:
                raise ValueError("Insufficient data for PUS TM header with CUC time.")
            cuc_time = data[PUS_TM_HEADER_LENGTH:PUS_TM_HEADER_LENGTH+cuc_time_length]

        return cls(
            version=version,
            spare=spare,
            service_type=service_type,
            service_subtype=service_subtype,
            message_type_counter=message_type_counter,
            destination_id=destination_id,
            has_time=has_time,
            cuc_time=cuc_time,
            cuc_time_length=cuc_time_length
        )
