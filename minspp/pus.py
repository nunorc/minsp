"""
The `minspp.pus` module provides PUS header related classes.

Telemetry (TM) and telecommand (TC) packets use different secondary header
layouts, one class each: `PUSTCHeader` implements the TC layout and
`PUSTMHeader` the PUS-C TM layout.
"""

import struct
from dataclasses import dataclass, field

from .utils import CUC_COARSE_LENGTH, CUC_TIME_LENGTH, cuc_time_now

PUS_TC_SOURCE_ID_LENGTH: int = 1
"""Default length in octets of the TC source ID, the standard makes it mission defined."""

PUS_TC_HEADER_LENGTH: int = 4
"""Length in octets of a TC secondary header with a default source ID, excluding the
optional CUC time."""

PUS_TM_DESTINATION_ID_LENGTH: int = 2
"""Default length in octets of the TM destination ID, the standard makes it mission defined."""

PUS_TM_HEADER_LENGTH: int = 7
"""Length in octets of a PUS-C TM secondary header with a default destination ID,
excluding the optional CUC time."""

def tc_header_length(source_id_length: int = PUS_TC_SOURCE_ID_LENGTH) -> int:
    """
    Length in octets of a TC secondary header, excluding the optional CUC time.

    :param source_id_length: Length in octets of the source ID.
    :type source_id_length: int

    :raises ValueError: Invalid source ID length.

    :return: The TC secondary header length.
    :rtype: int
    """
    if source_id_length < 0:
        raise ValueError("Invalid source ID length, must not be negative.")

    return PUS_TC_HEADER_LENGTH - PUS_TC_SOURCE_ID_LENGTH + source_id_length

def tm_header_length(destination_id_length: int = PUS_TM_DESTINATION_ID_LENGTH) -> int:
    """
    Length in octets of a PUS-C TM secondary header, excluding the optional CUC time.

    :param destination_id_length: Length in octets of the destination ID.
    :type destination_id_length: int

    :raises ValueError: Invalid destination ID length.

    :return: The TM secondary header length.
    :rtype: int
    """
    if destination_id_length < 0:
        raise ValueError("Invalid destination ID length, must not be negative.")

    return PUS_TM_HEADER_LENGTH - PUS_TM_DESTINATION_ID_LENGTH + destination_id_length

def fine_time_length(cuc_time_length: int, coarse_length: int = CUC_COARSE_LENGTH) -> int:
    """
    Number of octets of the fine time (sub-seconds) part of a CUC timestamp.

    The CCSDS unsegmented time code splits into a coarse time (seconds) and a fine
    time (sub-seconds) field, and the mission defines how the total length is split
    between the two, so only `cuc_time_length - coarse_length` octets are left for
    the fine time.

    :param cuc_time_length: Total length in octets of the CUC timestamp.
    :type cuc_time_length: int
    :param coarse_length: Number of octets of the coarse time field, default is `4`.
    :type coarse_length: int

    :raises ValueError: Invalid CUC coarse time length.
    :raises ValueError: Invalid CUC time length.

    :return: The fine time length.
    :rtype: int
    """
    if coarse_length < 1:
        raise ValueError("Invalid CUC coarse time length, must be positive.")

    if cuc_time_length < coarse_length:
        raise ValueError(f"Invalid CUC time length, must be at least {coarse_length}.")

    return cuc_time_length - coarse_length

@dataclass
class PUSTCHeader:
    """
    Represents a Packet Utilization Standard (PUS) telecommand (TC) secondary
    header as used in CCSDS space packets.

    The PUS secondary header adds standardized metadata to a CCSDS space packet,
    including service type, service subtype, source ID, and an optional timestamp
    in CUC format. Use `PUSTMHeader` for telemetry packets, which use a different
    field layout.

    :param version: PUS version number, `2` for PUS-C (4 bits).
    :type version: int
    :param ack: Acknowledgment flags (4 bits).
    :type ack: int
    :param service_type: PUS service type (1 byte).
    :type service_type: int
    :param service_subtype: PUS service subtype (1 byte).
    :type service_subtype: int
    :param source_id: Identifier of the source application or subsystem
    (`source_id_length` bytes).
    :type source_id: int
    :param has_time: Includes a CUC time in the header, default is `False`.
    :type has_time: bool
    :param cuc_time: Optional CUC-formatted timestamp (`cuc_time_length` bytes).
    :type cuc_time: bytes
    :param cuc_time_length: Length in bytes of the CUC timestamp, default is `7`.
    Ignored when `cuc_time` is given, in which case it is derived from it.
    :type cuc_time_length: int
    :param source_id_length: Length in bytes of the source ID, default is `1`. The
    standard makes this width mission defined, `0` means the field is absent.
    :type source_id_length: int
    :param cuc_coarse_length: Length in bytes of the coarse time (seconds) part of
    the CUC timestamp, default is `4`. The standard makes this split mission defined,
    the remaining `cuc_time_length - cuc_coarse_length` bytes hold the fine time.
    :type cuc_coarse_length: int
    """
    version: int = 2
    ack: int = 0
    service_type: int = 1
    service_subtype: int = 1
    source_id: int = 0
    has_time: bool = False
    cuc_time: bytes = b''
    cuc_time_length: int = field(default=CUC_TIME_LENGTH, repr=False)
    source_id_length: int = field(default=PUS_TC_SOURCE_ID_LENGTH, repr=False)
    cuc_coarse_length: int = field(default=CUC_COARSE_LENGTH, repr=False)

    def __post_init__(self):
        if self.cuc_time:
            self.cuc_time_length = len(self.cuc_time)
        elif self.has_time:
            self.cuc_time = cuc_time_now(coarse_length=self.cuc_coarse_length,
                                         fine_length=self.fine_time_length())

    def header_length(self) -> int:
        """
        Length in bytes of the header, excluding the optional CUC time.

        :raises ValueError: Invalid source ID length.

        :return: The header length.
        :rtype: int
        """
        return tc_header_length(self.source_id_length)

    def fine_time_length(self) -> int:
        """
        Number of bytes of the fine time (sub-seconds) part of the CUC timestamp.

        :raises ValueError: Invalid CUC coarse time length.
        :raises ValueError: Invalid CUC time length.

        :return: The fine time length.
        :rtype: int
        """
        return fine_time_length(self.cuc_time_length, self.cuc_coarse_length)

    def as_bytes(self) -> bytes:
        """
        Packs the PUS TC header as a byte stream.

        :raises ValueError: Invalid source ID length.

        :return: PUS TC header bytes.
        :rtype: bytes
        """
        source_id_length = self.source_id_length
        if source_id_length < 0:
            raise ValueError("Invalid source ID length, must not be negative.")
        source_id_mask = (1 << (8 * source_id_length)) - 1

        first_byte = ((self.version & 0x0F) << 4) | (self.ack & 0x0F)
        header = struct.pack(">BBB", first_byte, self.service_type, self.service_subtype) + \
                 (self.source_id & source_id_mask).to_bytes(source_id_length, "big")

        if not self.has_time:
            return header

        cuc_time = self.cuc_time or cuc_time_now(coarse_length=self.cuc_coarse_length,
                                                 fine_length=self.fine_time_length())

        return header + cuc_time

    @classmethod
    def from_bytes(cls, data: bytes, has_time: bool = False,
                   cuc_time_length: int = CUC_TIME_LENGTH,
                   source_id_length: int = PUS_TC_SOURCE_ID_LENGTH,
                   cuc_coarse_length: int = CUC_COARSE_LENGTH) -> "PUSTCHeader":
        """
        Unpacks a byte stream into a `PUSTCHeader` instance.

        :param data: The byte stream.
        :type data: bytes
        :param has_time: Includes a CUC time in header.
        :type has_time: bool
        :param cuc_time_length: Length in bytes of the CUC time, default is `7`.
        :type cuc_time_length: int
        :param source_id_length: Length in bytes of the source ID, default is `1`.
        :type source_id_length: int
        :param cuc_coarse_length: Length in bytes of the coarse time part of the CUC
        time, default is `4`.
        :type cuc_coarse_length: int

        :raises ValueError: Invalid source ID length.
        :raises ValueError: Insufficient data for PUS TC header.
        :raises ValueError: Invalid CUC coarse time length.
        :raises ValueError: Invalid CUC time length.
        :raises ValueError: Insufficient data for PUS TC header with CUC time.

        :return: A new `PUSTCHeader`.
        :rtype: PUSTCHeader
        """
        header_length = tc_header_length(source_id_length)

        if len(data) < header_length:
            raise ValueError("Insufficient data for PUS TC header.")

        first_byte, service_type, service_subtype = struct.unpack(">BBB", data[:3])
        source_id = int.from_bytes(data[3:header_length], "big")
        version = (first_byte >> 4) & 0x0F
        ack = first_byte & 0x0F

        cuc_time = b''
        if has_time:
            # validates the coarse and fine time split
            fine_time_length(cuc_time_length, cuc_coarse_length)
            if len(data) < header_length + cuc_time_length:
                raise ValueError("Insufficient data for PUS TC header with CUC time.")
            cuc_time = data[header_length:header_length+cuc_time_length]

        return cls(
            version=version,
            ack=ack,
            service_type=service_type,
            service_subtype=service_subtype,
            source_id=source_id,
            has_time=has_time,
            cuc_time=cuc_time,
            cuc_time_length=cuc_time_length,
            source_id_length=source_id_length,
            cuc_coarse_length=cuc_coarse_length
        )

@dataclass
class PUSTMHeader:
    """
    Represents a PUS-C (ECSS-E-ST-70-41C) telemetry (TM) secondary header as used
    in CCSDS space packets.

    The TM secondary header layout differs from the telecommand one (`PUSTCHeader`):
    the acknowledgment flags are replaced by the spacecraft time reference status,
    and the source ID is replaced by a message type counter and a destination ID,
    giving a 7 octet header followed by an optional CUC timestamp.

    :param version: PUS version number, `2` for PUS-C (4 bits).
    :type version: int
    :param time_reference_status: Spacecraft time reference status, a mission
    defined value reporting the synchronization status of the time field (4 bits).
    :type time_reference_status: int
    :param service_type: PUS service type (1 byte).
    :type service_type: int
    :param service_subtype: PUS message subtype (1 byte).
    :type service_subtype: int
    :param message_type_counter: Count of messages of this service type and
    subtype generated by the application process (2 bytes).
    :type message_type_counter: int
    :param destination_id: Identifier of the destination application or
    subsystem (`destination_id_length` bytes).
    :type destination_id: int
    :param has_time: Includes a CUC time in the header, default is `False`.
    :type has_time: bool
    :param cuc_time: Optional CUC-formatted timestamp (`cuc_time_length` bytes).
    :type cuc_time: bytes
    :param cuc_time_length: Length in bytes of the CUC timestamp, default is `7`.
    Ignored when `cuc_time` is given, in which case it is derived from it.
    :type cuc_time_length: int
    :param destination_id_length: Length in bytes of the destination ID, default is
    `2`. The standard makes this width mission defined, `0` means the field is absent.
    :type destination_id_length: int
    :param cuc_coarse_length: Length in bytes of the coarse time (seconds) part of
    the CUC timestamp, default is `4`. The standard makes this split mission defined,
    the remaining `cuc_time_length - cuc_coarse_length` bytes hold the fine time.
    :type cuc_coarse_length: int
    """
    version: int = 2
    time_reference_status: int = 0
    service_type: int = 1
    service_subtype: int = 1
    message_type_counter: int = 0
    destination_id: int = 0
    has_time: bool = False
    cuc_time: bytes = b''
    cuc_time_length: int = field(default=CUC_TIME_LENGTH, repr=False)
    destination_id_length: int = field(default=PUS_TM_DESTINATION_ID_LENGTH, repr=False)
    cuc_coarse_length: int = field(default=CUC_COARSE_LENGTH, repr=False)

    def __post_init__(self):
        if self.cuc_time:
            self.cuc_time_length = len(self.cuc_time)
        elif self.has_time:
            self.cuc_time = cuc_time_now(coarse_length=self.cuc_coarse_length,
                                         fine_length=self.fine_time_length())

    def header_length(self) -> int:
        """
        Length in bytes of the header, excluding the optional CUC time.

        :raises ValueError: Invalid destination ID length.

        :return: The header length.
        :rtype: int
        """
        return tm_header_length(self.destination_id_length)

    def fine_time_length(self) -> int:
        """
        Number of bytes of the fine time (sub-seconds) part of the CUC timestamp.

        :raises ValueError: Invalid CUC coarse time length.
        :raises ValueError: Invalid CUC time length.

        :return: The fine time length.
        :rtype: int
        """
        return fine_time_length(self.cuc_time_length, self.cuc_coarse_length)

    def as_bytes(self) -> bytes:
        """
        Packs the PUS-C TM header as a byte stream.

        :raises ValueError: Invalid destination ID length.

        :return: PUS-C TM header bytes.
        :rtype: bytes
        """
        destination_id_length = self.destination_id_length
        if destination_id_length < 0:
            raise ValueError("Invalid destination ID length, must not be negative.")
        destination_id_mask = (1 << (8 * destination_id_length)) - 1

        first_byte = ((self.version & 0x0F) << 4) | (self.time_reference_status & 0x0F)
        header = struct.pack(">BBBH",
                             first_byte, self.service_type, self.service_subtype,
                             self.message_type_counter) + \
                 (self.destination_id & destination_id_mask).to_bytes(destination_id_length, "big")

        if not self.has_time:
            return header

        cuc_time = self.cuc_time or cuc_time_now(coarse_length=self.cuc_coarse_length,
                                                 fine_length=self.fine_time_length())

        return header + cuc_time

    @classmethod
    def from_bytes(cls, data: bytes, has_time: bool = False,
                   cuc_time_length: int = CUC_TIME_LENGTH,
                   destination_id_length: int = PUS_TM_DESTINATION_ID_LENGTH,
                   cuc_coarse_length: int = CUC_COARSE_LENGTH) -> "PUSTMHeader":
        """
        Unpacks a byte stream into a `PUSTMHeader` instance.

        :param data: The byte stream.
        :type data: bytes
        :param has_time: Includes a CUC time in header.
        :type has_time: bool
        :param cuc_time_length: Length in bytes of the CUC time, default is `7`.
        :type cuc_time_length: int
        :param destination_id_length: Length in bytes of the destination ID, default is `2`.
        :type destination_id_length: int
        :param cuc_coarse_length: Length in bytes of the coarse time part of the CUC
        time, default is `4`.
        :type cuc_coarse_length: int

        :raises ValueError: Invalid destination ID length.
        :raises ValueError: Insufficient data for PUS TM header.
        :raises ValueError: Invalid CUC coarse time length.
        :raises ValueError: Invalid CUC time length.
        :raises ValueError: Insufficient data for PUS TM header with CUC time.

        :return: A new `PUSTMHeader`.
        :rtype: PUSTMHeader
        """
        header_length = tm_header_length(destination_id_length)

        if len(data) < header_length:
            raise ValueError("Insufficient data for PUS TM header.")

        first_byte, service_type, service_subtype, message_type_counter = \
            struct.unpack(">BBBH", data[:5])
        destination_id = int.from_bytes(data[5:header_length], "big")
        version = (first_byte >> 4) & 0x0F
        time_reference_status = first_byte & 0x0F

        cuc_time = b''
        if has_time:
            # validates the coarse and fine time split
            fine_time_length(cuc_time_length, cuc_coarse_length)
            if len(data) < header_length + cuc_time_length:
                raise ValueError("Insufficient data for PUS TM header with CUC time.")
            cuc_time = data[header_length:header_length+cuc_time_length]

        return cls(
            version=version,
            time_reference_status=time_reference_status,
            service_type=service_type,
            service_subtype=service_subtype,
            message_type_counter=message_type_counter,
            destination_id=destination_id,
            has_time=has_time,
            cuc_time=cuc_time,
            cuc_time_length=cuc_time_length,
            destination_id_length=destination_id_length,
            cuc_coarse_length=cuc_coarse_length
        )
