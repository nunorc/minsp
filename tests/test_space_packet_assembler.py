
from minsp import SpacePacket, SequenceFlag, SpacePacketAssembler

space_packet_1 = SpacePacket(sequence_flags=SequenceFlag.FIRST, data_field=b"123")
space_packet_2 = SpacePacket(sequence_flags=SequenceFlag.CONTINUATION, data_field=b"456")
space_packet_3 = SpacePacket(sequence_flags=SequenceFlag.LAST, data_field=b"789")

def test_new_space_packet_assembler():
    space_packet_assembler = SpacePacketAssembler()

    assert space_packet_assembler.buffer == b''
    assert space_packet_assembler.reassembling == False

def test_space_packet_assembler_process():
    space_packet_assembler = SpacePacketAssembler()

    r = space_packet_assembler.process_packet(space_packet_1)
    assert r is None

    r = space_packet_assembler.process_packet(space_packet_2)
    assert r is None

    r = space_packet_assembler.process_packet(space_packet_3)
    assert r == b'123456789'

def test_space_packet_assembler_from_packets():
    r = SpacePacketAssembler.from_packets([
        space_packet_1,
        space_packet_2,
        space_packet_3,
    ])

    assert r == b'123456789'
