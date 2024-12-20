
from minsp import SpacePacket, PacketType

def test_new_space_packet():
    packet = SpacePacket()

    assert packet.version == 0b000
    assert packet.type == PacketType.TM
    assert packet.sec_hdr_flag == 0
    assert packet.apid == 0
    assert packet.sequence_flags == 0b11
    assert packet.sequence_count == 0
    assert packet.data_length == 0
    assert packet.sec_hdr == b''
    assert packet.payload == b''

def test_space_packet_byte_stream():
    packet = SpacePacket(payload=b'testing')

    byte_stream = packet.byte_stream()
    assert len(byte_stream) > 0

    new_packet = SpacePacket.from_byte_stream(byte_stream)
    assert packet.payload == new_packet.payload

