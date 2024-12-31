"""
The `minsp.core` module provides the package core functions and classes.
"""

from enum import Enum
import bitstruct

class PacketType(int, Enum):
    """
    Enum to represent a space packet type: telemetry (TM) or telecommand (TC).

    Attributes:
        TM = 0
        TC = 1
    """
    TM = 0b0
    TC = 0b1

class SpacePacket:
    """
    Class to represent a Space Packet.

    :param version: Packet version, default is `0` (3 bits).
    :type version: int
    :param type: Packet type, default is `PacketType.TM` (1 bit).
    :type type: PacketType
    :param sec_hdr_flag: Secondary header flag, default is `0` (1 bit).
    :type sec_hdr_flag: int
    :param apid: Application process identifier, default is `0` (11 bits).
    :type apid: int
    :param sequence_flags: Sequence flags, default is `0b11` (2 bits).
    :type sequence_flags: int
    :param sequence_count: Sequence count, default is `0` (14 bits).
    :type sequence_count: int
    :param data_length: Payload data lenght, defauls is `0` (16 bits).
    :param sec_hdr: Secondary header.
    :type sec_hdr: bytes
    :param payload: Packet payload.
    :type payload: bytes

    :raises ValueError: If `type` is not an instance of `PacketType`.
    """
    def __init__(self,
                 version: int = 0b00,
                 type: PacketType = PacketType.TM,
                 sec_hdr_flag: int = 0,
                 apid: int = 0,
                 sequence_flags: int = 0b11,
                 sequence_count: int = 0,
                 data_length: int = 0,

                 sec_hdr: bytes = b'',
                 payload: bytes = b'',
            ) -> None:

        if not isinstance(type, PacketType):
            raise ValueError("Invalid packet type, must be an instance of PacketType Enum")

        self.version = version
        self.type = type
        self.sec_hdr_flag = sec_hdr_flag
        self.apid = apid
        self.sequence_flags = sequence_flags
        self.sequence_count = sequence_count
        self.data_length = data_length

        self.sec_hdr = sec_hdr
        self.payload = payload

        # TODO: verify data length calculation
        if self.sec_hdr:
            self.sec_hdr_flag = 1
        if len(self.sec_hdr) > 0 or len(self.payload) > 0:
            self.data_length = len(self.sec_hdr) + len(self.payload) - 1

    @classmethod
    def from_byte_stream(cls, byte_stream, sec_hdr_len=0):
        """
        Initialize a new `SpacePacket` object from a byte stream.

        :param byte_stream: byte stream
        :type byte_stream: bytes
        :param sec_hdr_len: secondary header lenght if present, default is `0`
        :type sec_hdr_len: int

        :return: a new `SpacePacket`
        :rtype: SpacePacket
        """
        primary_header = byte_stream[:6]

        version, type, sec_hdr_flag, apid, sequence_flags, \
            sequence_count, data_length = bitstruct.unpack('>u3u1u1u11u2u14u16', primary_header)

        if sec_hdr_flag == 1:
            sec_hdr = byte_stream[5:5+sec_hdr_len]  # FIXME
            payload = byte_stream[5+sec_hdr_len:]   # FIXME
        else:
            sec_hdr = b''
            payload = byte_stream[6:]

        return cls(version = version,
                   type = PacketType(type),
                   sec_hdr_flag = sec_hdr_flag,
                   apid = apid,
                   sequence_flags = sequence_flags,
                   sequence_count = sequence_count,
                   data_length = data_length,
                   sec_hdr = sec_hdr,
                   payload = payload)

    def generate_primary_header(self):
        """
        Generate the primary header of a spacke packet.

        :return: Space packet primary header.
        :rtype: bytes
        """
        return bitstruct.pack('>u3u1u1u11u2u14u16',
                              self.version,
                              self.type.value,
                              self.sec_hdr_flag,
                              self.apid,
                              self.sequence_flags,
                              self.sequence_count,
                              self.data_length)

    def byte_stream(self):
        """
        Generate a space packet as byte stream.

        :return: Space packet bytes.
        :rtype: bytes
        """
        primary_header = self.generate_primary_header()

        if self.sec_hdr_flag == 1:
            packet = primary_header + self.sec_hdr + self.payload
        else:
            packet = primary_header + self.payload

        return packet

    def set_payload(self, payload):
        """
        Set the payload of the packet.

        :param payload: Payload.
        :type payload: bytes
        """
        self.payload = payload

        # TODO: verify data length calculation
        self.data_length = len(self.sec_hdr) + len(self.payload) - 1

    def __repr__(self):
        """
        String representation of the SpacePacket class.

        :return: String representation.
        :rtype: str
        """
        return f"SpacePacket(version={bin(self.version)}, type={self.type}, " \
               f"sec_hdr_flag={bin(self.sec_hdr_flag)}, " \
               f"apid={self.apid}, sequence_flags={bin(self.sequence_flags)}, " \
               f"sequence_count={self.sequence_count}, data_length={self.data_length})"
