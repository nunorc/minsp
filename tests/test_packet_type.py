
from minsp import PacketType

def test_new_packet_type():
    tm = PacketType.TM
    tc = PacketType.TC

    assert tm.name == 'TM'
    assert tm.value == 0
    assert tc.name == 'TC'
    assert tc.value == 1

def test_new_packet_type_from_int():
    tm = PacketType(0)
    tc = PacketType(1)

    assert tm.name == 'TM'
    assert tm.value == 0
    assert tc.name == 'TC'
    assert tc.value == 1
