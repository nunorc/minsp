
from minsp import SpacePacket
from minsp.pus import PUSHeader

def test_new_pus_header():
    pus_header = PUSHeader()

    assert pus_header.version == 1
    assert pus_header.ack == 0
    assert pus_header.service_type == 1
    assert pus_header.service_subtype == 1
    assert pus_header.source_id == 0
    assert pus_header.has_time is False
    assert pus_header.cuc_time == b''

def test_pus_header_bytes():
    h1 = PUSHeader()
    h2 = PUSHeader.from_bytes(PUSHeader().as_bytes())
    
    assert h1 == h2

    bytes1 = PUSHeader().as_bytes()
    bytes2 = PUSHeader.from_bytes(bytes1).as_bytes()
    
    assert bytes1 == bytes2
    
def test_space_packet_pus():
    pus_header = PUSHeader()
    space_packet = SpacePacket(secondary_header=pus_header)
    
    assert isinstance(space_packet.secondary_header, PUSHeader)
    assert space_packet.secondary_header.version == 1

def test_space_packet_pus_bytes():
    pus_header = PUSHeader()
    space_packet = SpacePacket(secondary_header=pus_header)
    
    bytes1 = space_packet.as_bytes()
    bytes2 = SpacePacket.from_bytes(space_packet.as_bytes(), pus=True).as_bytes()
    
    assert bytes1 == bytes2

    