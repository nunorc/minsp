
from datetime import datetime, timezone

from minspp import SpacePacket
from minspp.pus import PUSHeader
from minspp.utils import CUC_TIME_LENGTH, cuc_as_datetime, cuc_time_now

def test_new_pus_header():
    pus_header = PUSHeader()

    assert pus_header.version == 1
    assert pus_header.ack == 0
    assert pus_header.service_type == 1
    assert pus_header.service_subtype == 1
    assert pus_header.source_id == 0
    assert pus_header.has_time is False
    assert pus_header.cuc_time == b''
    assert pus_header.cuc_time_length == CUC_TIME_LENGTH

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

def test_pus_header_time_bytes():
    h1 = PUSHeader(has_time=True)
    bytes1 = h1.as_bytes()

    assert len(h1.cuc_time) == CUC_TIME_LENGTH
    assert len(bytes1) == 4 + CUC_TIME_LENGTH

    h2 = PUSHeader.from_bytes(bytes1, has_time=True)

    assert h1 == h2
    assert h2.cuc_time == h1.cuc_time
    assert h2.as_bytes() == bytes1

def test_pus_header_time_bytes_custom_length():
    for length in [4, 5, 6, 7, 8]:
        h1 = PUSHeader(has_time=True, cuc_time_length=length)
        bytes1 = h1.as_bytes()

        assert len(h1.cuc_time) == length
        assert len(bytes1) == 4 + length

        h2 = PUSHeader.from_bytes(bytes1, has_time=True, cuc_time_length=length)

        assert h1 == h2
        assert h2.as_bytes() == bytes1

def test_pus_header_time_explicit_cuc_time():
    cuc_time = cuc_time_now(fine_length=2)
    h1 = PUSHeader(has_time=True, cuc_time=cuc_time)

    assert h1.cuc_time_length == 6

    h2 = PUSHeader.from_bytes(h1.as_bytes(), has_time=True, cuc_time_length=6)

    assert h1 == h2

def test_pus_header_time_as_datetime():
    now = datetime.now(timezone.utc)
    header = PUSHeader.from_bytes(PUSHeader(has_time=True).as_bytes(), has_time=True)

    assert abs((cuc_as_datetime(header.cuc_time) - now).total_seconds()) < 60

def test_space_packet_pus_time_bytes():
    space_packet = SpacePacket(secondary_header=PUSHeader(has_time=True), data_field=b'\x01\x02')

    bytes1 = space_packet.as_bytes()
    packet2 = SpacePacket.from_bytes(bytes1, pus=True, pus_has_time=True)

    assert packet2.secondary_header == space_packet.secondary_header
    assert packet2.data_field == b'\x01\x02'
    assert packet2.as_bytes() == bytes1
