
from datetime import datetime, timezone

import pytest

from minspp import PacketType, SpacePacket
from minspp.pus import (PUS_TC_HEADER_LENGTH, PUS_TC_SOURCE_ID_LENGTH, PUS_TM_HEADER_LENGTH,
                        PUSTCHeader, PUSTMHeader, tc_header_length)
from minspp.utils import CUC_TIME_LENGTH, cuc_as_datetime, cuc_time_now

def test_new_pus_tc_header():
    pus_header = PUSTCHeader()

    assert pus_header.version == 1
    assert pus_header.ack == 0
    assert pus_header.service_type == 1
    assert pus_header.service_subtype == 1
    assert pus_header.source_id == 0
    assert pus_header.has_time is False
    assert pus_header.cuc_time == b''
    assert pus_header.cuc_time_length == CUC_TIME_LENGTH

def test_pus_tc_header_bytes():
    h1 = PUSTCHeader()
    h2 = PUSTCHeader.from_bytes(PUSTCHeader().as_bytes())
    
    assert h1 == h2

    bytes1 = PUSTCHeader().as_bytes()
    bytes2 = PUSTCHeader.from_bytes(bytes1).as_bytes()
    
    assert bytes1 == bytes2
    
def test_space_packet_pus_tc():
    pus_header = PUSTCHeader()
    space_packet = SpacePacket(secondary_header=pus_header)
    
    assert isinstance(space_packet.secondary_header, PUSTCHeader)
    assert space_packet.secondary_header.version == 1

def test_space_packet_pus_tc_bytes():
    pus_header = PUSTCHeader()
    space_packet = SpacePacket(secondary_header=pus_header)
    
    bytes1 = space_packet.as_bytes()
    bytes2 = SpacePacket.from_bytes(space_packet.as_bytes(), pus_tc=True).as_bytes()

    assert bytes1 == bytes2

def test_pus_tc_header_time_bytes():
    h1 = PUSTCHeader(has_time=True)
    bytes1 = h1.as_bytes()

    assert len(h1.cuc_time) == CUC_TIME_LENGTH
    assert len(bytes1) == PUS_TC_HEADER_LENGTH + CUC_TIME_LENGTH

    h2 = PUSTCHeader.from_bytes(bytes1, has_time=True)

    assert h1 == h2
    assert h2.cuc_time == h1.cuc_time
    assert h2.as_bytes() == bytes1

def test_pus_tc_header_time_bytes_custom_length():
    for length in [4, 5, 6, 7, 8]:
        h1 = PUSTCHeader(has_time=True, cuc_time_length=length)
        bytes1 = h1.as_bytes()

        assert len(h1.cuc_time) == length
        assert len(bytes1) == PUS_TC_HEADER_LENGTH + length

        h2 = PUSTCHeader.from_bytes(bytes1, has_time=True, cuc_time_length=length)

        assert h1 == h2
        assert h2.as_bytes() == bytes1

def test_pus_tc_header_time_explicit_cuc_time():
    cuc_time = cuc_time_now(fine_length=2)
    h1 = PUSTCHeader(has_time=True, cuc_time=cuc_time)

    assert h1.cuc_time_length == 6

    h2 = PUSTCHeader.from_bytes(h1.as_bytes(), has_time=True, cuc_time_length=6)

    assert h1 == h2

def test_pus_tc_header_time_as_datetime():
    now = datetime.now(timezone.utc)
    header = PUSTCHeader.from_bytes(PUSTCHeader(has_time=True).as_bytes(), has_time=True)

    assert abs((cuc_as_datetime(header.cuc_time) - now).total_seconds()) < 60

def test_space_packet_pus_tc_time_bytes():
    space_packet = SpacePacket(secondary_header=PUSTCHeader(has_time=True), data_field=b'\x01\x02')

    bytes1 = space_packet.as_bytes()
    packet2 = SpacePacket.from_bytes(bytes1, pus_tc=True, pus_has_time=True)

    assert packet2.secondary_header == space_packet.secondary_header
    assert packet2.data_field == b'\x01\x02'
    assert packet2.as_bytes() == bytes1

def test_space_packet_pus_tc_time_bytes_custom_length():
    header = PUSTCHeader(has_time=True, cuc_time_length=5)
    space_packet = SpacePacket(secondary_header=header, data_field=b'\x01\x02')

    bytes1 = space_packet.as_bytes()
    packet2 = SpacePacket.from_bytes(bytes1, pus_tc=True, pus_has_time=True,
                                     pus_cuc_time_length=5)

    assert len(packet2.secondary_header.cuc_time) == 5
    assert packet2.secondary_header == header
    assert packet2.data_field == b'\x01\x02'
    assert packet2.as_bytes() == bytes1

def test_pus_tc_header_default_source_id_length():
    header = PUSTCHeader()

    assert header.source_id_length == PUS_TC_SOURCE_ID_LENGTH == 1
    assert header.header_length() == len(header.as_bytes()) == PUS_TC_HEADER_LENGTH == 4
    assert tc_header_length() == PUS_TC_HEADER_LENGTH

def test_pus_tc_header_source_id_16bit_layout():
    # TC(8,1) perform function, 16 bit source ID as defined in the mission XTCE
    header = PUSTCHeader(version=2, ack=0x9, service_type=8, service_subtype=1,
                         source_id=0x0102, source_id_length=2)
    data = header.as_bytes()

    assert header.header_length() == tc_header_length(2) == 5
    assert len(data) == 5
    assert data == b'\x29\x08\x01\x01\x02'

    header2 = PUSTCHeader.from_bytes(data, source_id_length=2)

    assert header2 == header
    assert header2.source_id == 0x0102
    assert header2.as_bytes() == data

def test_pus_tc_header_source_id_16bit_keeps_data_field_aligned():
    # the opcode and its argument follow the secondary header
    header = PUSTCHeader(service_type=8, service_subtype=1, source_id=0x0102,
                         source_id_length=2)
    space_packet = SpacePacket(type=PacketType.TC, apid=11, secondary_header=header,
                               data_field=b'\xAB\x2A')

    assert space_packet.data_length == 5 + 2 - 1

    bytes1 = space_packet.as_bytes()
    packet2 = SpacePacket.from_bytes(bytes1, pus_tc=True, pus_source_id_length=2)

    assert packet2.secondary_header == header
    assert packet2.data_field == b'\xAB\x2A'
    assert packet2.as_bytes() == bytes1

    # decoding with the default 1 byte source ID misaligns the opcode by one byte
    packet3 = SpacePacket.from_bytes(bytes1, pus_tc=True)

    assert packet3.data_field == b'\x02\xAB\x2A'

def test_pus_tc_header_source_id_lengths():
    for length in [0, 1, 2, 3, 4]:
        h1 = PUSTCHeader(source_id=0, source_id_length=length)
        bytes1 = h1.as_bytes()

        assert len(bytes1) == 3 + length

        h2 = PUSTCHeader.from_bytes(bytes1, source_id_length=length)

        assert h1 == h2
        assert h2.as_bytes() == bytes1

def test_pus_tc_header_source_id_length_zero_omits_field():
    header = PUSTCHeader(service_type=8, service_subtype=1, source_id=0x0102,
                         source_id_length=0)

    assert header.as_bytes() == b'\x10\x08\x01'
    assert PUSTCHeader.from_bytes(header.as_bytes(), source_id_length=0).source_id == 0

def test_pus_tc_header_source_id_16bit_with_time():
    h1 = PUSTCHeader(source_id=0xFFFF, source_id_length=2, has_time=True)
    bytes1 = h1.as_bytes()

    assert len(bytes1) == tc_header_length(2) + CUC_TIME_LENGTH

    h2 = PUSTCHeader.from_bytes(bytes1, has_time=True, source_id_length=2)

    assert h1 == h2
    assert h2.cuc_time == h1.cuc_time
    assert h2.as_bytes() == bytes1

def test_pus_tc_header_source_id_length_errors():
    with pytest.raises(ValueError):
        tc_header_length(-1)

    with pytest.raises(ValueError):
        PUSTCHeader(source_id_length=-1).as_bytes()

    with pytest.raises(ValueError):
        PUSTCHeader.from_bytes(PUSTCHeader().as_bytes(), source_id_length=-1)

    # a 4 byte stream is one byte short of a 16 bit source ID header
    with pytest.raises(ValueError):
        PUSTCHeader.from_bytes(PUSTCHeader().as_bytes(), source_id_length=2)

def test_new_pus_tm_header():
    tm_header = PUSTMHeader()

    assert tm_header.version == 2
    assert tm_header.spare == 0
    assert tm_header.service_type == 1
    assert tm_header.service_subtype == 1
    assert tm_header.message_type_counter == 0
    assert tm_header.destination_id == 0
    assert tm_header.has_time is False
    assert tm_header.cuc_time == b''
    assert tm_header.cuc_time_length == CUC_TIME_LENGTH

def test_pus_tm_header_layout():
    # PUS-C TM (3,25) housekeeping parameter report
    tm_header = PUSTMHeader(service_type=3, service_subtype=25,
                            message_type_counter=0x0102, destination_id=0x0304)
    data = tm_header.as_bytes()

    assert len(data) == PUS_TM_HEADER_LENGTH == 7
    assert data == b'\x20\x03\x19\x01\x02\x03\x04'

def test_pus_tm_header_spare_nibble():
    tm_header = PUSTMHeader(version=2, spare=0x0F)

    assert tm_header.as_bytes()[0] == 0x2F
    assert PUSTMHeader.from_bytes(tm_header.as_bytes()).spare == 0x0F

def test_pus_tm_header_bytes():
    h1 = PUSTMHeader(service_type=5, service_subtype=4,
                     message_type_counter=65535, destination_id=65535)
    h2 = PUSTMHeader.from_bytes(h1.as_bytes())

    assert h1 == h2
    assert h2.as_bytes() == h1.as_bytes()

def test_pus_tm_header_time_bytes():
    h1 = PUSTMHeader(has_time=True)
    bytes1 = h1.as_bytes()

    assert len(h1.cuc_time) == CUC_TIME_LENGTH
    assert len(bytes1) == PUS_TM_HEADER_LENGTH + CUC_TIME_LENGTH

    h2 = PUSTMHeader.from_bytes(bytes1, has_time=True)

    assert h1 == h2
    assert h2.cuc_time == h1.cuc_time
    assert h2.as_bytes() == bytes1

def test_pus_tm_header_time_bytes_custom_length():
    for length in [4, 5, 6, 7, 8]:
        h1 = PUSTMHeader(has_time=True, cuc_time_length=length)
        bytes1 = h1.as_bytes()

        assert len(h1.cuc_time) == length
        assert len(bytes1) == PUS_TM_HEADER_LENGTH + length

        h2 = PUSTMHeader.from_bytes(bytes1, has_time=True, cuc_time_length=length)

        assert h1 == h2
        assert h2.as_bytes() == bytes1

def test_pus_tm_header_time_explicit_cuc_time():
    cuc_time = cuc_time_now(fine_length=2)
    h1 = PUSTMHeader(has_time=True, cuc_time=cuc_time)

    assert h1.cuc_time_length == 6

    h2 = PUSTMHeader.from_bytes(h1.as_bytes(), has_time=True, cuc_time_length=6)

    assert h1 == h2

def test_pus_tm_header_time_as_datetime():
    now = datetime.now(timezone.utc)
    header = PUSTMHeader.from_bytes(PUSTMHeader(has_time=True).as_bytes(), has_time=True)

    assert abs((cuc_as_datetime(header.cuc_time) - now).total_seconds()) < 60

def test_pus_tm_header_from_bytes_errors():
    with pytest.raises(ValueError):
        PUSTMHeader.from_bytes(b'\x20\x03\x19\x01\x02\x03')

    with pytest.raises(ValueError):
        PUSTMHeader.from_bytes(PUSTMHeader(has_time=True).as_bytes(), has_time=True,
                               cuc_time_length=3)

    with pytest.raises(ValueError):
        PUSTMHeader.from_bytes(PUSTMHeader().as_bytes(), has_time=True)

def test_pus_tm_header_differs_from_tc():
    assert len(PUSTMHeader().as_bytes()) != len(PUSTCHeader().as_bytes())

def test_space_packet_pus_tm():
    tm_header = PUSTMHeader(service_type=3, service_subtype=25, message_type_counter=7,
                            destination_id=42)
    space_packet = SpacePacket(type=PacketType.TM, apid=11, secondary_header=tm_header,
                               data_field=b'\x01\x02')

    assert space_packet.secondary_header_flag == 1
    assert space_packet.data_length == PUS_TM_HEADER_LENGTH + 2 - 1

    bytes1 = space_packet.as_bytes()
    packet2 = SpacePacket.from_bytes(bytes1, pus_tm=True)

    assert isinstance(packet2.secondary_header, PUSTMHeader)
    assert packet2.secondary_header == tm_header
    assert packet2.data_field == b'\x01\x02'
    assert packet2.as_bytes() == bytes1

def test_space_packet_pus_tm_time_bytes():
    space_packet = SpacePacket(secondary_header=PUSTMHeader(has_time=True),
                               data_field=b'\x01\x02')

    bytes1 = space_packet.as_bytes()
    packet2 = SpacePacket.from_bytes(bytes1, pus_tm=True, pus_has_time=True)

    assert packet2.secondary_header == space_packet.secondary_header
    assert packet2.data_field == b'\x01\x02'
    assert packet2.as_bytes() == bytes1

def test_space_packet_pus_tm_time_bytes_custom_length():
    header = PUSTMHeader(has_time=True, cuc_time_length=5)
    space_packet = SpacePacket(secondary_header=header, data_field=b'\x01\x02')

    bytes1 = space_packet.as_bytes()
    packet2 = SpacePacket.from_bytes(bytes1, pus_tm=True, pus_has_time=True,
                                     pus_cuc_time_length=5)

    assert len(packet2.secondary_header.cuc_time) == 5
    assert packet2.secondary_header == header
    assert packet2.data_field == b'\x01\x02'
    assert packet2.as_bytes() == bytes1

def test_space_packet_pus_tm_no_time_keeps_data_field():
    header = PUSTMHeader()
    space_packet = SpacePacket(secondary_header=header, data_field=b'\x01\x02')

    packet2 = SpacePacket.from_bytes(space_packet.as_bytes(), pus_tm=True)

    assert packet2.secondary_header.cuc_time == b''
    assert packet2.data_field == b'\x01\x02'

def test_space_packet_pus_tc_and_pus_tm_are_exclusive():
    space_packet = SpacePacket(secondary_header=PUSTMHeader(), data_field=b'\x01\x02')

    with pytest.raises(ValueError):
        SpacePacket.from_bytes(space_packet.as_bytes(), pus_tc=True, pus_tm=True)
