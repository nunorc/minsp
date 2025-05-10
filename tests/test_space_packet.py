
from minsp import SpacePacket, PacketType, SequenceFlag

def test_new_space_packet():
    packet = SpacePacket()

    assert packet.version == 0b000
    assert packet.type == PacketType.TM
    assert packet.secondary_header_flag == 0
    assert packet.apid == 0
    assert packet.sequence_flags == SequenceFlag.UNSEGMENTED
    assert packet.sequence_count == 0
    assert packet.data_length == -1
    assert packet.secondary_header == b''
    assert packet.data_field == b''

def test_new_space_packet_data_length():
    pld = b'1234567890123456'

    packet = SpacePacket(data_field=pld)
    assert packet.data_length == 15

def test_space_packet_byte_stream():
    packet = SpacePacket(data_field=b'testing')

    byte_stream = packet.as_bytes()
    assert len(byte_stream) > 0

    new_packet = SpacePacket.from_bytes(byte_stream)
    assert packet.data_field == new_packet.data_field

def test_space_packet_byte_stream_sec_hdr():
    hdr = b'1212121212'
    pld = b'14141414141414141414'

    packet = SpacePacket(secondary_header=hdr, data_field=pld)
    assert packet.secondary_header_flag == 1
    assert len(packet.secondary_header) > 0
    assert len(packet.data_field) > 0

    byte_stream = packet.as_bytes()
    assert len(byte_stream) > 0

    new_packet = SpacePacket.from_bytes(byte_stream, secondary_header_length=len(hdr))
    assert hdr == new_packet.secondary_header
    assert pld == new_packet.data_field
