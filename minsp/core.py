
import struct, bitstruct
from enum import Enum

class PacketType(int, Enum):
    TM = 0b0
    TC = 0b1

class SpacePacket:
    """
    Class to represent a Space Packet.

    Attributes:
    - version (int): packet version (3 bits)
    - type (PacketType): type of packet (PacketType enum: TM or TC) (1 bit)
    - sec_hdr_flag (int): secondary header flag (1 bit)
    - apid (int): application process identifier (11 bits)
    - sequence_flags (int): sequence flags (2 bits)
    - sequence_count (int): Sequence Count (14 bits)
    - data_length (int): data length (16 bits)
    - sec_hdr (bytes): secondary header
    - payload (bytes): packet payload
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
        Generate a space packet from a byte stream.

        Returns:
        - (SpacePacket): a new space packet.
        """
        primary_header = byte_stream[:6]

        version, type, sec_hdr_flag, apid, sequence_flags, sequence_count, data_length = bitstruct.unpack('>u3u1u1u11u2u14u16', primary_header)

        if sec_hdr_flag == 1:
            sec_hdr = byte_stream[5:5+sec_hdr_len]  # FIXME
            payload = byte_stream[5+sec_hdr_len:]   # FIXME
        else:
            sec_hdr = b''
            payload = byte_stream[6:]

        return cls(version=version, type=PacketType(type), sec_hdr_flag=sec_hdr_flag, apid=apid, sequence_flags=sequence_flags, sequence_count=sequence_count, data_length=data_length, sec_hdr=sec_hdr, payload=payload)

    def generate_primary_header(self):
        """
        Generate the primary header of the packet.

        Returns:
        - (bytes): packet primary header (6 bytes).
        """
        return bitstruct.pack('>u3u1u1u11u2u14u16', self.version, self.type.value, self.sec_hdr_flag, self.apid, self.sequence_flags, self.sequence_count, self.data_length)

    def byte_stream(self):
        """
        Generate a full space packet as byte stream.

        Returns:
        - (bytes): a full space packet in bytes.
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

        Args:
        - payload (bytes): The new payload data.
        """
        self.payload = payload

        # TODO: verify data length calculation
        self.data_length = len(self.sec_hdr) + len(self.payload) - 1

    def __repr__(self):
        """
        String representation of the SpacePacket class.
        """
        return f"SpacePacket(version={bin(self.version)}, type={self.type}, sec_hdr_flag={bin(self.sec_hdr_flag)}, " \
               f"apid={self.apid}, sequence_flags={bin(self.sequence_flags)}, " \
               f"sequence_count={self.sequence_count}, data_length={self.data_length})"

