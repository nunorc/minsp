
import pytest

from minspp import SpacePacket, PacketType, SequenceFlags
from minspp.core import PACKET_ERROR_CONTROL_LENGTH
from minspp.utils import crc16_ccitt

def test_new_space_packet():
    packet = SpacePacket()

    assert packet.version == 0b000
    assert packet.type == PacketType.TM
    assert packet.secondary_header_flag == 0
    assert packet.apid == 0
    assert packet.sequence_flags == SequenceFlags.UNSEGMENTED
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

def test_space_packet_single_octet_data_field():
    packet = SpacePacket(apid=11, data_field=b'\x01')
    assert packet.data_length == 0

    byte_stream = packet.as_bytes()
    assert byte_stream == b'\x00\x0b\xc0\x00\x00\x00\x01'

    new_packet = SpacePacket.from_bytes(byte_stream)
    assert new_packet.data_length == 0
    assert new_packet.data_field == b'\x01'

def test_space_packet_empty_data_field():
    with pytest.raises(ValueError):
        SpacePacket().as_bytes()

def test_space_packet_from_bytes_bounded_by_data_length():
    packet = SpacePacket(data_field=b'testing')

    new_packet = SpacePacket.from_bytes(packet.as_bytes() + b'\xAA\xBB')
    assert new_packet.data_field == b'testing'
    assert new_packet.data_length == packet.data_length

def test_space_packet_from_bytes_bounded_by_data_length_sec_hdr():
    hdr = b'1212121212'

    packet = SpacePacket(secondary_header=hdr, data_field=b'testing')

    new_packet = SpacePacket.from_bytes(packet.as_bytes() + b'\xAA\xBB',
                                        secondary_header_length=len(hdr))
    assert new_packet.secondary_header == hdr
    assert new_packet.data_field == b'testing'

def test_space_packet_from_bytes_truncated():
    byte_stream = SpacePacket(data_field=b'testing').as_bytes()

    with pytest.raises(ValueError):
        SpacePacket.from_bytes(byte_stream[:-1])

def test_space_packet_iter_packets():
    first = SpacePacket(apid=1, data_field=b'testing')
    second = SpacePacket(apid=2, data_field=b'more testing')

    packets = list(SpacePacket.iter_packets(first.as_bytes() + second.as_bytes()))

    assert len(packets) == 2
    assert [p.apid for p in packets] == [1, 2]
    assert packets[0].data_field == b'testing'
    assert packets[1].data_field == b'more testing'

def test_space_packet_iter_packets_empty():
    assert not list(SpacePacket.iter_packets(b''))

def test_space_packet_iter_packets_truncated():
    byte_stream = SpacePacket(data_field=b'testing').as_bytes()

    with pytest.raises(ValueError):
        list(SpacePacket.iter_packets(byte_stream + byte_stream[:-1]))

def test_space_packet_error_control_bytes():
    packet = SpacePacket(apid=11, data_field=b'hello')

    plain = packet.as_bytes()
    byte_stream = packet.as_bytes(packet_error_control=True)

    assert len(byte_stream) == len(plain) + PACKET_ERROR_CONTROL_LENGTH
    assert byte_stream[:6] != plain[:6]   # the data length accounts for the CRC
    assert byte_stream[6:-PACKET_ERROR_CONTROL_LENGTH] == plain[6:]
    assert byte_stream[4:6] == (packet.data_length + PACKET_ERROR_CONTROL_LENGTH).to_bytes(2, 'big')
    assert byte_stream[-PACKET_ERROR_CONTROL_LENGTH:] == \
        crc16_ccitt(byte_stream[:-PACKET_ERROR_CONTROL_LENGTH]).to_bytes(2, 'big')

def test_space_packet_error_control_round_trip():
    packet = SpacePacket(apid=11, data_field=b'hello')
    byte_stream = packet.as_bytes(packet_error_control=True)

    new_packet = SpacePacket.from_bytes(byte_stream, packet_error_control=True)

    assert new_packet.data_field == b'hello'
    assert new_packet.data_length == packet.data_length
    assert new_packet.as_bytes(packet_error_control=True) == byte_stream

def test_space_packet_error_control_sec_hdr_round_trip():
    hdr = b'1212121212'
    packet = SpacePacket(secondary_header=hdr, data_field=b'hello')
    byte_stream = packet.as_bytes(packet_error_control=True)

    new_packet = SpacePacket.from_bytes(byte_stream, secondary_header_length=len(hdr),
                                        packet_error_control=True)

    assert new_packet.secondary_header == hdr
    assert new_packet.data_field == b'hello'

def test_space_packet_error_control_mismatch():
    byte_stream = bytearray(SpacePacket(data_field=b'hello').as_bytes(packet_error_control=True))
    byte_stream[-1] ^= 0x01

    with pytest.raises(ValueError):
        SpacePacket.from_bytes(bytes(byte_stream), packet_error_control=True)

def test_space_packet_error_control_not_stripped_when_not_requested():
    byte_stream = SpacePacket(data_field=b'hello').as_bytes(packet_error_control=True)

    new_packet = SpacePacket.from_bytes(byte_stream)

    assert len(new_packet.data_field) == len(b'hello') + PACKET_ERROR_CONTROL_LENGTH

def test_space_packet_error_control_iter_packets():
    first = SpacePacket(apid=1, data_field=b'hello').as_bytes(packet_error_control=True)
    second = SpacePacket(apid=2, data_field=b'world').as_bytes(packet_error_control=True)

    packets = list(SpacePacket.iter_packets(first + second, packet_error_control=True))

    assert [(p.apid, p.data_field) for p in packets] == [(1, b'hello'), (2, b'world')]
