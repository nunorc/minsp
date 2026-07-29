"""
The `minspp.core` module provides the package core functions and classes.
"""

from dataclasses import dataclass
from enum import Enum
import struct

from .pus import (PUS_TC_SOURCE_ID_LENGTH, PUS_TM_DESTINATION_ID_LENGTH,
                  PUSTCHeader, PUSTMHeader)
from .mo import MALHeader
from .utils import CUC_COARSE_LENGTH, CUC_TIME_LENGTH, crc16_ccitt

PACKET_ERROR_CONTROL_LENGTH: int = 2
"""Number of octets of the packet error control (CRC-16) field."""

class PacketType(int, Enum):
    """
    Enum to represent a space packet type: telemetry (TM) or telecommand (TC).

    Attributes:
        TM = 0
        TC = 1
    """
    TM = 0b0
    TC = 0b1

class SequenceFlags(int, Enum):
    """
    Enum to represent the sequece flags of a space packet.

    Attributes:
        CONTINUATION = 0
        FIRST = 1
        LAST = 2
        UNSEGMENTED = 3
    """
    CONTINUATION = 0b00
    FIRST = 0b01
    LAST = 0b10
    UNSEGMENTED = 0b11

@dataclass
class SpacePacket:
    """
    Represents a CCSDS Space Packet (including primary header, optional secondary
    header, and data field).

    According to the CCSDS standard:
    * The primary header is 6 bytes long and contains version, packet type, APID,
    sequence info, and length.
    * The secondary header can be an custom stream of bytes, an instance of `PUSTCHeader`
    (telecommand), an instance of `PUSTMHeader` (PUS-C telemetry) or an instance
    of `MALHeader`.
    * The data length field (data_length) defines the number of bytes after the primary
    header minus one.
    * This class allows serialization to and from byte streams.

    :param version: Packet version, default is `0` (3 bits).
    :type version: int
    :param type: Packet type, default is `PacketType.TM` (1 bit).
    :type type: PacketType
    :param secondary_header_flag: Secondary header flag, default is `0` (1 bit).
    :type secondary_header_flag: int
    :param apid: Application process identifier, default is `0` (11 bits).
    :type apid: int
    :param sequence_flags: Sequence flags, default is `SequenceFlag.UNSEGMENTED` (2 bits).
    :type sequence_flags: SequenceFlag
    :param sequence_count: Sequence count, default is `0` (14 bits).
    :type sequence_count: int
    :param data_length: Packet data field length of the data following
    the primary header minus one, defaults is `0` (16 bits).
    :param secondary_header: Secondary header.
    :type secondary_header: bytes|`PUSTCHeader`|`PUSTMHeader`|`MALHeader`
    :param data_field: Packet data.
    :type data_field: bytes
    """
    version: int = 0
    type: PacketType = PacketType.TM
    secondary_header_flag: int = 0
    apid: int = 0
    sequence_flags: SequenceFlags = SequenceFlags.UNSEGMENTED
    sequence_count: int = 0
    data_length: int = 0

    secondary_header: bytes|PUSTCHeader|PUSTMHeader|MALHeader = b''
    data_field: bytes = b''

    def __post_init__(self):

        # update data length
        size = 0
        if isinstance(self.secondary_header, (PUSTCHeader, PUSTMHeader, MALHeader)):
            size += len(self.secondary_header.as_bytes())
        else:
            size += len(self.secondary_header)

        self.data_length = size + len(self.data_field) - 1

        # update secondary header flag
        if self.secondary_header:
            self.secondary_header_flag = 1

    def as_bytes(self, packet_error_control: bool = False) -> bytes:
        """
        Packs the space packet into a byte stream, including:
        - Primary header (6 bytes)
        - Optional secondary header
        - Data field
        - Optional packet error control (2 bytes)

        The packet error control field is the CRC-16-CCITT of every preceding octet
        of the packet, and is itself part of the packet data field, so the data
        length written to the primary header accounts for it. The `data_length`
        attribute does not, it always describes the secondary header plus the data
        field.

        :param packet_error_control: Append a packet error control field,
        default is `False`.
        :type packet_error_control: bool

        :raises ValueError: Empty packet data field, at least one octet is required.

        :return: Space packet bytes.
        :rtype: bytes
        """
        if isinstance(self.secondary_header, bytes):
            sec_hdr = self.secondary_header
        elif isinstance(self.secondary_header, PUSTCHeader):
            sec_hdr = self.secondary_header.as_bytes()
        elif isinstance(self.secondary_header, PUSTMHeader):
            sec_hdr = self.secondary_header.as_bytes()
        elif isinstance(self.secondary_header, MALHeader):
            sec_hdr = self.secondary_header.as_bytes()
        else:
            sec_hdr = b''

        payload = sec_hdr + self.data_field
        self.data_length = len(payload) - 1

        data_length = self.data_length
        if packet_error_control:
            data_length += PACKET_ERROR_CONTROL_LENGTH

        # the packet data field holds at least one octet, i.e. a data length of 0
        if data_length < 0:
            raise ValueError("Can't generate packet as bytes, packet data field is empty.")

        first_word = ((self.version & 0x07) << 13) | \
                     ((self.type & 0x01) << 12) | \
                     ((self.secondary_header_flag & 0x01) << 11) | \
                     (self.apid & 0x07FF)
        second_word = ((self.sequence_flags & 0x03) << 14) | (self.sequence_count & 0x3FFF)

        header = struct.pack(">HHH", first_word, second_word, data_length)
        packet = header + payload

        if packet_error_control:
            packet += struct.pack(">H", crc16_ccitt(packet))

        return packet

    @staticmethod
    def _strip_packet_error_control(data: bytes) -> bytes:
        """
        Verifies the packet error control field of a packet and strips it.

        :param data: The bytes of a single packet, error control field included.
        :type data: bytes

        :raises ValueError: Insufficient data for the packet error control field.
        :raises ValueError: Packet error control mismatch.

        :return: The packet bytes without the packet error control field.
        :rtype: bytes
        """
        if len(data) < 6 + PACKET_ERROR_CONTROL_LENGTH:
            raise ValueError("Insufficient data for the packet error control field.")

        crc = struct.unpack(">H", data[-PACKET_ERROR_CONTROL_LENGTH:])[0]
        if crc != crc16_ccitt(data[:-PACKET_ERROR_CONTROL_LENGTH]):
            raise ValueError("Packet error control mismatch.")

        return data[:-PACKET_ERROR_CONTROL_LENGTH]

    # pylint: disable=R1720,R0914
    @classmethod
    def from_bytes(cls, data: bytes, secondary_header_length: int = 0, \
        pus_tc: bool = False, mal: bool = False, pus_has_time: bool = False, \
        pus_cuc_time_length: int = CUC_TIME_LENGTH, pus_tm: bool = False, \
        pus_source_id_length: int = PUS_TC_SOURCE_ID_LENGTH, \
        packet_error_control: bool = False, \
        pus_destination_id_length: int = PUS_TM_DESTINATION_ID_LENGTH, \
        pus_cuc_coarse_length: int = CUC_COARSE_LENGTH) -> "SpacePacket":
        """
        Unpacks a byte stream into a `SpacePacket` instance.

        Only the octets declared by the packet data length field are consumed, any
        trailing octets in the byte stream are ignored.

        :param data: The byte stream.
        :type data: bytes
        :param secondary_header_length: Secondary header length if present, default is `0`.
        :type secondary_header_length: int
        :param pus_tc: Secondary header is a `PUSTCHeader`.
        :type pus_tc: bool
        :param mal: Secondary header is a `MALHeader`.
        :type mal: bool
        :param pus_has_time: PUS secondary header includes a CUC time.
        :type pus_has_time: bool
        :param pus_cuc_time_length: Length in bytes of the PUS CUC time, default is `7`.
        :type pus_cuc_time_length: int
        :param pus_tm: Secondary header is a `PUSTMHeader`.
        :type pus_tm: bool
        :param pus_source_id_length: Length in bytes of the source ID of a PUS TC
        secondary header, default is `1`. The standard makes this width mission defined.
        :type pus_source_id_length: int
        :param packet_error_control: The packet data field ends with a packet error
        control field, which is verified and stripped, default is `False`.
        :type packet_error_control: bool
        :param pus_destination_id_length: Length in bytes of the destination ID of a
        PUS TM secondary header, default is `2`. The standard makes this width mission
        defined.
        :type pus_destination_id_length: int
        :param pus_cuc_coarse_length: Length in bytes of the coarse time part of the
        PUS CUC time, default is `4`. The standard makes this split mission defined.
        :type pus_cuc_coarse_length: int

        :raises ValueError: Insufficient data for space packet primary header.
        :raises ValueError: Both `pus_tc` and `pus_tm` are set.
        :raises ValueError: Insufficient data for the declared packet data length.
        :raises ValueError: Insufficient data for the packet error control field.
        :raises ValueError: Packet error control mismatch.
        :raises ValueError: Secondary header flag bit is set to 1, but secondary header length is 0.

        :return: A new `SpacePacket`.
        :rtype: SpacePacket
        """
        if len(data) < 6:
            raise ValueError("Insufficient data for space packet primary header.")

        if pus_tc and pus_tm:
            raise ValueError("Secondary header can't be both a PUS TC and a PUS TM header.")

        header = cls.header_from_bytes(data[:6])

        # the packet data field holds data_length+1 octets, anything past it
        # belongs to the next packet (or is trailing garbage) and is dropped
        packet_length = 6 + header["data_length"] + 1
        if len(data) < packet_length:
            raise ValueError("Insufficient data for the declared packet data length.")
        data = data[:packet_length]

        if packet_error_control:
            data = cls._strip_packet_error_control(data)

        if header["secondary_header_flag"] == 1:
            if pus_tc:
                secondary_header = PUSTCHeader.from_bytes(data[6:], has_time=pus_has_time,
                                                          cuc_time_length=pus_cuc_time_length,
                                                          source_id_length=pus_source_id_length,
                                                          cuc_coarse_length=pus_cuc_coarse_length)
                data_field = data[6+len(secondary_header.as_bytes()):]
            elif pus_tm:
                secondary_header = PUSTMHeader.from_bytes(
                    data[6:], has_time=pus_has_time,
                    cuc_time_length=pus_cuc_time_length,
                    destination_id_length=pus_destination_id_length,
                    cuc_coarse_length=pus_cuc_coarse_length)
                data_field = data[6+len(secondary_header.as_bytes()):]
            elif mal:
                secondary_header = MALHeader.from_bytes(data[6:])
                data_field =data[6+len(secondary_header.as_bytes()):]
            else:
                if secondary_header_length == 0:
                    raise ValueError("Secondary header flag bit is set to 1, \
                                     but secondary header length is 0.")
                else:
                    secondary_header = data[6:6+secondary_header_length]
                    data_field = data[6+secondary_header_length:]
        else:
            secondary_header = b''
            data_field = data[6:]

        return cls(
            version=header["version"],
            type=PacketType(header["type"]),
            secondary_header_flag=header["secondary_header_flag"],
            apid=header["apid"],
            sequence_flags=SequenceFlags(header["sequence_flags"]),
            sequence_count=header["sequence_count"],
            secondary_header=secondary_header,
            data_length=header["data_length"],
            data_field=data_field
        )

    @classmethod
    def iter_packets(cls, data: bytes, secondary_header_length: int = 0, \
        pus_tc: bool = False, mal: bool = False, pus_has_time: bool = False, \
        pus_cuc_time_length: int = CUC_TIME_LENGTH, pus_tm: bool = False, \
        pus_source_id_length: int = PUS_TC_SOURCE_ID_LENGTH, \
        packet_error_control: bool = False, \
        pus_destination_id_length: int = PUS_TM_DESTINATION_ID_LENGTH, \
        pus_cuc_coarse_length: int = CUC_COARSE_LENGTH):
        """
        Unpacks a byte stream of back to back space packets, yielding one
        `SpacePacket` per packet found. Every packet in the stream must share the
        same secondary header shape, described by the arguments of this method,
        which have the same meaning as in `from_bytes`.

        :param data: The byte stream.
        :type data: bytes
        :param secondary_header_length: Secondary header length if present, default is `0`.
        :type secondary_header_length: int
        :param pus_tc: Secondary header is a `PUSTCHeader`.
        :type pus_tc: bool
        :param mal: Secondary header is a `MALHeader`.
        :type mal: bool
        :param pus_has_time: PUS secondary header includes a CUC time.
        :type pus_has_time: bool
        :param pus_cuc_time_length: Length in bytes of the PUS CUC time, default is `7`.
        :type pus_cuc_time_length: int
        :param pus_tm: Secondary header is a `PUSTMHeader`.
        :type pus_tm: bool
        :param pus_source_id_length: Length in bytes of the source ID of a PUS TC
        secondary header, default is `1`. The standard makes this width mission defined.
        :type pus_source_id_length: int
        :param packet_error_control: The packet data field ends with a packet error
        control field, which is verified and stripped, default is `False`.
        :type packet_error_control: bool
        :param pus_destination_id_length: Length in bytes of the destination ID of a
        PUS TM secondary header, default is `2`. The standard makes this width mission
        defined.
        :type pus_destination_id_length: int
        :param pus_cuc_coarse_length: Length in bytes of the coarse time part of the
        PUS CUC time, default is `4`. The standard makes this split mission defined.
        :type pus_cuc_coarse_length: int

        :raises ValueError: Insufficient data for space packet primary header.
        :raises ValueError: Insufficient data for the declared packet data length.
        :raises ValueError: Packet error control mismatch.

        :return: A generator of `SpacePacket`.
        :rtype: Iterator[SpacePacket]
        """
        offset = 0

        while offset < len(data):
            header = cls.header_from_bytes(data[offset:offset+6])
            packet_length = 6 + header["data_length"] + 1

            yield cls.from_bytes(data[offset:offset+packet_length],
                                 secondary_header_length=secondary_header_length,
                                 pus_tc=pus_tc, mal=mal, pus_has_time=pus_has_time,
                                 pus_cuc_time_length=pus_cuc_time_length, pus_tm=pus_tm,
                                 pus_source_id_length=pus_source_id_length,
                                 packet_error_control=packet_error_control,
                                 pus_destination_id_length=pus_destination_id_length,
                                 pus_cuc_coarse_length=pus_cuc_coarse_length)

            offset += packet_length

    @classmethod
    def header_from_bytes(cls, data: bytes) -> dict:
        """
        Unpacks a space packt header from a byte.

        :param data: The byte stream.
        :type data: bytes

        :raises ValueError: Insufficient data for space packet primary header.

        :return: A new `dict`.
        :rtype: dict
        """
        if len(data) < 6:
            raise ValueError("Insufficient data for space packet primary header.")

        first_word, second_word, pkt_length = struct.unpack(">HHH", data[:6])

        header = {}
        header["version"] = (first_word >> 13) & 0x07
        header["type"] = (first_word >> 12) & 0x01
        header["secondary_header_flag"] = (first_word >> 11) & 0x01
        header["apid"] = first_word & 0x07FF
        header["sequence_flags"] = (second_word >> 14) & 0x03
        header["sequence_count"] = second_word & 0x3FFF
        header["data_length"] = pkt_length

        return header


class SpacePacketAssembler:
    """
    Assembles the payload from segmented space packets.
    """
    def __init__(self):
        self.buffer = bytearray()
        self.reassembling = False

    def process_packet(self, packet:SpacePacket) -> bytes | None:
        """
        Process a individual space packet.

        :raises RuntimeError: Continuation received without first segment.
        :raises RuntimeError: Last segment received without segment.

        :return: Optional payload found.
        :rtype: bytes | None
        """
        payload = None

        if packet.sequence_flags == SequenceFlags.UNSEGMENTED:
            payload = packet.data_field

        elif packet.sequence_flags == SequenceFlags.FIRST:
            self.buffer = bytearray(packet.data_field)
            self.reassembling = True
            payload = None

        elif packet.sequence_flags == SequenceFlags.CONTINUATION:
            if not self.reassembling:
                raise RuntimeError("Continuation received without first segment.")
            self.buffer.extend(packet.data_field)
            payload = None

        elif packet.sequence_flags == SequenceFlags.LAST:
            if not self.reassembling:
                raise RuntimeError("Last segment received without segment.")
            self.buffer.extend(packet.data_field)
            payload = bytes(self.buffer)
            self.buffer.clear()
            self.reassembling = False

        return payload

    @classmethod
    def from_packets(cls, packets:list[SpacePacket]) -> bytes | None:
        """
        Assembles the payload from segmented space packets.

        :param packets: A list of `SpacePacket`.
        :type packets: list[SpacePacket]

        :return: The payload.
        :rtype: bytes | None
        """
        spa = cls()

        for packet in packets:
            payload = spa.process_packet(packet)
            if payload:
                return payload

        return None
