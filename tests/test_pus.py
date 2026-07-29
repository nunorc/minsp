
from datetime import datetime, timedelta, timezone

import pytest

from minspp import PacketType, SpacePacket
from minspp.pus import (PUS_SERVICE_MINIMUM, PUS_TC_HEADER_LENGTH, PUS_TC_SOURCE_ID_LENGTH,
                        PUS_TM_DESTINATION_ID_LENGTH, PUS_TM_HEADER_LENGTH, PUS_VERSION,
                        PUSTCHeader, PUSTMHeader, check_pus_version, fine_time_length,
                        tc_header_length, tm_header_length)
from minspp.utils import (CUC_COARSE_LENGTH, CUC_EPOCH, CUC_FINE_LENGTH, CUC_TIME_LENGTH,
                          cuc_as_datetime, cuc_time_now)

def test_new_pus_tc_header():
    pus_header = PUSTCHeader()

    assert pus_header.version == 2
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
    assert space_packet.secondary_header.version == 2

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
    header = PUSTCHeader(service_type=8, service_subtype=1, source_id=0, source_id_length=0)

    assert header.as_bytes() == b'\x20\x08\x01'
    assert PUSTCHeader.from_bytes(header.as_bytes(), source_id_length=0).source_id == 0

    # a source ID that does not fit the absent field is an error, not silently dropped
    with pytest.raises(ValueError):
        PUSTCHeader(service_type=8, service_subtype=1, source_id=0x0102,
                    source_id_length=0).as_bytes()

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
    assert tm_header.time_reference_status == 0
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

def test_pus_tm_header_time_reference_status_nibble():
    tm_header = PUSTMHeader(version=2, time_reference_status=0x0F)

    assert tm_header.as_bytes()[0] == 0x2F
    assert PUSTMHeader.from_bytes(tm_header.as_bytes()).time_reference_status == 0x0F

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

def test_space_packet_pus_tm_trailing_bytes_are_not_absorbed():
    space_packet = SpacePacket(secondary_header=PUSTMHeader(), data_field=b'\x01\x02')

    packet2 = SpacePacket.from_bytes(space_packet.as_bytes() + b'\xAA\xBB', pus_tm=True)

    assert packet2.data_field == b'\x01\x02'
    assert packet2.data_length == space_packet.data_length

def test_space_packet_pus_tm_iter_packets():
    first = SpacePacket(apid=1, secondary_header=PUSTMHeader(service_type=3, service_subtype=25),
                        data_field=b'\x01\x02')
    second = SpacePacket(apid=2, secondary_header=PUSTMHeader(service_type=5, service_subtype=1),
                         data_field=b'\x03\x04\x05')

    packets = list(SpacePacket.iter_packets(first.as_bytes() + second.as_bytes(), pus_tm=True))

    assert len(packets) == 2
    assert packets[0].secondary_header == first.secondary_header
    assert packets[0].data_field == b'\x01\x02'
    assert packets[1].secondary_header == second.secondary_header
    assert packets[1].data_field == b'\x03\x04\x05'

def test_space_packet_pus_tc_and_pus_tm_are_exclusive():
    space_packet = SpacePacket(secondary_header=PUSTMHeader(), data_field=b'\x01\x02')

    with pytest.raises(ValueError):
        SpacePacket.from_bytes(space_packet.as_bytes(), pus_tc=True, pus_tm=True)

def test_pus_tm_header_default_destination_id_length():
    header = PUSTMHeader()

    assert header.destination_id_length == PUS_TM_DESTINATION_ID_LENGTH == 2
    assert header.header_length() == len(header.as_bytes()) == PUS_TM_HEADER_LENGTH == 7
    assert tm_header_length() == PUS_TM_HEADER_LENGTH

def test_pus_tm_header_destination_id_8bit_layout():
    # PUS-C TM (3,25) for a mission with an 8 bit destination ID
    header = PUSTMHeader(service_type=3, service_subtype=25, message_type_counter=0x0102,
                         destination_id=0x03, destination_id_length=1)
    data = header.as_bytes()

    assert header.header_length() == tm_header_length(1) == 6
    assert len(data) == 6
    assert data == b'\x20\x03\x19\x01\x02\x03'

    header2 = PUSTMHeader.from_bytes(data, destination_id_length=1)

    assert header2 == header
    assert header2.destination_id == 0x03
    assert header2.as_bytes() == data

def test_pus_tm_header_destination_id_lengths():
    for length in [0, 1, 2, 3, 4]:
        h1 = PUSTMHeader(destination_id=0, destination_id_length=length)
        bytes1 = h1.as_bytes()

        assert len(bytes1) == 5 + length

        h2 = PUSTMHeader.from_bytes(bytes1, destination_id_length=length)

        assert h1 == h2
        assert h2.as_bytes() == bytes1

def test_pus_tm_header_destination_id_length_zero_omits_field():
    header = PUSTMHeader(service_type=3, service_subtype=25, destination_id=0,
                         destination_id_length=0)

    assert header.as_bytes() == b'\x20\x03\x19\x00\x00'
    assert PUSTMHeader.from_bytes(header.as_bytes(),
                                  destination_id_length=0).destination_id == 0

    # a destination ID that does not fit the absent field is an error, not dropped
    with pytest.raises(ValueError):
        PUSTMHeader(service_type=3, service_subtype=25, destination_id=0x0304,
                    destination_id_length=0).as_bytes()

def test_pus_tm_header_destination_id_32bit_with_time():
    h1 = PUSTMHeader(destination_id=0xDEADBEEF, destination_id_length=4, has_time=True)
    bytes1 = h1.as_bytes()

    assert len(bytes1) == tm_header_length(4) + CUC_TIME_LENGTH

    h2 = PUSTMHeader.from_bytes(bytes1, has_time=True, destination_id_length=4)

    assert h1 == h2
    assert h2.destination_id == 0xDEADBEEF
    assert h2.cuc_time == h1.cuc_time
    assert h2.as_bytes() == bytes1

def test_pus_tm_header_destination_id_length_errors():
    with pytest.raises(ValueError):
        tm_header_length(-1)

    with pytest.raises(ValueError):
        PUSTMHeader(destination_id_length=-1).as_bytes()

    with pytest.raises(ValueError):
        PUSTMHeader.from_bytes(PUSTMHeader().as_bytes(), destination_id_length=-1)

    # a 7 byte stream is one byte short of a 24 bit destination ID header
    with pytest.raises(ValueError):
        PUSTMHeader.from_bytes(PUSTMHeader().as_bytes(), destination_id_length=3)

def test_pus_tm_header_destination_id_8bit_keeps_data_field_aligned():
    header = PUSTMHeader(service_type=3, service_subtype=25, destination_id=0x2A,
                         destination_id_length=1)
    space_packet = SpacePacket(apid=11, secondary_header=header, data_field=b'\xAB\x2A')

    assert space_packet.data_length == 6 + 2 - 1

    bytes1 = space_packet.as_bytes()
    packet2 = SpacePacket.from_bytes(bytes1, pus_tm=True, pus_destination_id_length=1)

    assert packet2.secondary_header == header
    assert packet2.data_field == b'\xAB\x2A'
    assert packet2.as_bytes() == bytes1

    # decoding with the default 2 byte destination ID absorbs the first data octet
    packet3 = SpacePacket.from_bytes(bytes1, pus_tm=True)

    assert packet3.data_field == b'\x2A'

def test_fine_time_length_coarse_split():
    assert fine_time_length(CUC_TIME_LENGTH) == CUC_FINE_LENGTH == 3
    assert fine_time_length(CUC_TIME_LENGTH, CUC_COARSE_LENGTH) == CUC_FINE_LENGTH
    assert fine_time_length(6, 3) == 3
    assert fine_time_length(4, 4) == 0

def test_fine_time_length_errors():
    # the fine time can't be negative, i.e. the total must cover the coarse time
    with pytest.raises(ValueError):
        fine_time_length(3, 4)

    with pytest.raises(ValueError):
        fine_time_length(CUC_TIME_LENGTH, 0)

def test_pus_tc_header_cuc_coarse_length():
    h1 = PUSTCHeader(has_time=True, cuc_time_length=7, cuc_coarse_length=5)

    assert h1.fine_time_length() == 2
    assert len(h1.cuc_time) == 7

    now = datetime.now(timezone.utc)
    assert abs((cuc_as_datetime(h1.cuc_time, coarse_length=5) - now).total_seconds()) < 60

    h2 = PUSTCHeader.from_bytes(h1.as_bytes(), has_time=True, cuc_coarse_length=5)

    assert h1 == h2
    assert h2.cuc_time == h1.cuc_time
    assert h2.as_bytes() == h1.as_bytes()

def test_pus_tm_header_cuc_coarse_length():
    h1 = PUSTMHeader(has_time=True, cuc_time_length=7, cuc_coarse_length=5)

    assert h1.fine_time_length() == 2
    assert len(h1.cuc_time) == 7

    h2 = PUSTMHeader.from_bytes(h1.as_bytes(), has_time=True, cuc_coarse_length=5)

    assert h1 == h2
    assert h2.as_bytes() == h1.as_bytes()

    # the same octets read with the default 4 byte coarse time are a different instant
    assert cuc_as_datetime(h1.cuc_time) != cuc_as_datetime(h1.cuc_time, coarse_length=5)

def test_pus_tm_header_cuc_three_coarse_three_fine():
    # a mission with 3 coarse and 3 fine octets, 1.5 seconds after its epoch
    cuc_time = b'\x00\x00\x01\x80\x00\x00'
    h1 = PUSTMHeader(has_time=True, cuc_time=cuc_time, cuc_coarse_length=3)

    assert h1.cuc_time_length == 6
    assert h1.fine_time_length() == 3
    assert cuc_as_datetime(h1.cuc_time, coarse_length=3) == \
        datetime(1970, 1, 1, 0, 0, 1, 500000, tzinfo=timezone.utc)

    h2 = PUSTMHeader.from_bytes(h1.as_bytes(), has_time=True, cuc_time_length=6,
                                cuc_coarse_length=3)

    assert h1 == h2
    assert h2.cuc_time == cuc_time

def test_pus_header_cuc_coarse_length_errors():
    # a 4 byte coarse time does not fit in a 3 byte CUC time
    with pytest.raises(ValueError):
        PUSTCHeader(has_time=True, cuc_time_length=3)

    with pytest.raises(ValueError):
        PUSTMHeader(has_time=True, cuc_time_length=5, cuc_coarse_length=6)

    with pytest.raises(ValueError):
        PUSTMHeader.from_bytes(PUSTMHeader(has_time=True).as_bytes(), has_time=True,
                               cuc_coarse_length=8)

def test_space_packet_pus_tm_cuc_coarse_length():
    header = PUSTMHeader(has_time=True, cuc_time_length=7, cuc_coarse_length=5)
    space_packet = SpacePacket(secondary_header=header, data_field=b'\x01\x02')

    bytes1 = space_packet.as_bytes()
    packet2 = SpacePacket.from_bytes(bytes1, pus_tm=True, pus_has_time=True,
                                     pus_cuc_coarse_length=5)

    assert packet2.secondary_header == header
    assert packet2.secondary_header.cuc_coarse_length == 5
    assert packet2.data_field == b'\x01\x02'
    assert packet2.as_bytes() == bytes1

def test_space_packet_pus_tc_cuc_coarse_length():
    header = PUSTCHeader(has_time=True, cuc_time_length=6, cuc_coarse_length=5)
    space_packet = SpacePacket(secondary_header=header, data_field=b'\x01\x02')

    bytes1 = space_packet.as_bytes()
    packet2 = SpacePacket.from_bytes(bytes1, pus_tc=True, pus_has_time=True,
                                     pus_cuc_time_length=6, pus_cuc_coarse_length=5)

    assert packet2.secondary_header == header
    assert packet2.data_field == b'\x01\x02'
    assert packet2.as_bytes() == bytes1

def test_pus_header_default_cuc_epoch():
    assert PUSTCHeader().cuc_epoch == PUSTMHeader().cuc_epoch == CUC_EPOCH

def test_pus_tc_header_cuc_epoch():
    # the CCSDS agency-standard epoch, 1958-01-01
    epoch = datetime(1958, 1, 1, tzinfo=timezone.utc)
    h1 = PUSTCHeader(has_time=True, cuc_epoch=epoch)

    now = datetime.now(timezone.utc)
    assert abs((cuc_as_datetime(h1.cuc_time, epoch=epoch) - now).total_seconds()) < 60

    # an earlier epoch means a larger count, so the same octets read against the
    # default epoch land twelve years in the future
    assert cuc_as_datetime(h1.cuc_time) > now + timedelta(days=365 * 11)

    h2 = PUSTCHeader.from_bytes(h1.as_bytes(), has_time=True, cuc_epoch=epoch)

    assert h1 == h2
    assert h2.cuc_epoch == epoch
    assert h2.as_bytes() == h1.as_bytes()

def test_pus_tm_header_cuc_epoch_mission_elapsed_time():
    # a mission elapsed time epoch, i.e. a count from launch
    epoch = datetime.now(timezone.utc) - timedelta(days=1)
    header = PUSTMHeader(has_time=True, cuc_epoch=epoch)

    seconds = int.from_bytes(header.cuc_time[:CUC_COARSE_LENGTH], byteorder='big')

    assert abs(seconds - 86400) < 60

def test_pus_header_cuc_epoch_differs_from_default():
    epoch = datetime(2000, 1, 1, tzinfo=timezone.utc)

    assert PUSTMHeader(has_time=True, cuc_epoch=epoch) != PUSTMHeader(has_time=True)

def test_space_packet_pus_tm_cuc_epoch():
    epoch = datetime(1958, 1, 1, tzinfo=timezone.utc)
    header = PUSTMHeader(has_time=True, cuc_epoch=epoch)
    space_packet = SpacePacket(secondary_header=header, data_field=b'\x01\x02')

    bytes1 = space_packet.as_bytes()
    packet2 = SpacePacket.from_bytes(bytes1, pus_tm=True, pus_has_time=True,
                                     pus_cuc_epoch=epoch)

    assert packet2.secondary_header == header
    assert packet2.secondary_header.cuc_epoch == epoch
    assert packet2.data_field == b'\x01\x02'
    assert packet2.as_bytes() == bytes1

def test_space_packet_pus_tc_cuc_epoch_and_coarse_length():
    # a mission with its own epoch and a 5 byte coarse time
    epoch = datetime(2000, 1, 1, tzinfo=timezone.utc)
    header = PUSTCHeader(has_time=True, cuc_time_length=7, cuc_coarse_length=5,
                         cuc_epoch=epoch)
    space_packet = SpacePacket(secondary_header=header, data_field=b'\x01\x02')

    bytes1 = space_packet.as_bytes()
    packet2 = SpacePacket.from_bytes(bytes1, pus_tc=True, pus_has_time=True,
                                     pus_cuc_coarse_length=5, pus_cuc_epoch=epoch)

    assert packet2.secondary_header == header
    assert packet2.data_field == b'\x01\x02'
    assert packet2.as_bytes() == bytes1

    now = datetime.now(timezone.utc)
    value = cuc_as_datetime(packet2.secondary_header.cuc_time, coarse_length=5, epoch=epoch)

    assert abs((value - now).total_seconds()) < 60

def test_space_packet_pus_tm_destination_id_iter_packets():
    first = SpacePacket(apid=1, secondary_header=PUSTMHeader(destination_id=0x0A,
                                                             destination_id_length=1),
                        data_field=b'\x01\x02')
    second = SpacePacket(apid=2, secondary_header=PUSTMHeader(destination_id=0x0B,
                                                              destination_id_length=1),
                         data_field=b'\x03\x04\x05')

    packets = list(SpacePacket.iter_packets(first.as_bytes() + second.as_bytes(),
                                            pus_tm=True, pus_destination_id_length=1))

    assert [p.secondary_header.destination_id for p in packets] == [0x0A, 0x0B]
    assert packets[0].data_field == b'\x01\x02'
    assert packets[1].data_field == b'\x03\x04\x05'

def test_pus_header_defaults_are_pus_c():
    assert PUSTCHeader().version == PUSTMHeader().version == PUS_VERSION == 2
    assert PUSTCHeader().service_type == PUS_SERVICE_MINIMUM == 1

def test_check_pus_version():
    assert check_pus_version(PUS_VERSION) is None

    # PUS-A, i.e. a version this package does not implement
    with pytest.raises(ValueError):
        check_pus_version(1)

def test_pus_tc_header_out_of_range_fields():
    # every out of range field raises, none is silently masked
    for header in [PUSTCHeader(version=16), PUSTCHeader(version=-1),
                   PUSTCHeader(ack=16), PUSTCHeader(service_type=256),
                   PUSTCHeader(service_subtype=256), PUSTCHeader(source_id=256)]:
        with pytest.raises(ValueError):
            header.as_bytes()

def test_pus_tm_header_out_of_range_fields():
    for header in [PUSTMHeader(version=16), PUSTMHeader(time_reference_status=16),
                   PUSTMHeader(service_type=256), PUSTMHeader(service_subtype=256),
                   PUSTMHeader(message_type_counter=65536),
                   PUSTMHeader(destination_id=65536)]:
        with pytest.raises(ValueError):
            header.as_bytes()

def test_pus_header_reserved_service_values():
    # the standard reserves service type and message subtype 0
    with pytest.raises(ValueError):
        PUSTCHeader(service_type=0).as_bytes()

    with pytest.raises(ValueError):
        PUSTCHeader(service_subtype=0).as_bytes()

    with pytest.raises(ValueError):
        PUSTMHeader(service_type=0).as_bytes()

    with pytest.raises(ValueError):
        PUSTMHeader(service_subtype=0).as_bytes()

def test_pus_header_out_of_range_raises_value_error_not_struct_error():
    # a field wider than its byte used to surface as a struct.error
    with pytest.raises(ValueError):
        PUSTCHeader(service_type=300).as_bytes()

    with pytest.raises(ValueError):
        PUSTMHeader(message_type_counter=70000).as_bytes()

def test_pus_header_boundary_values_are_valid():
    assert PUSTCHeader(version=15, ack=15, service_type=255, service_subtype=255,
                       source_id=255).as_bytes() == b'\xff\xff\xff\xff'

    assert PUSTMHeader(version=15, time_reference_status=15, service_type=255,
                       service_subtype=255, message_type_counter=65535,
                       destination_id=65535).as_bytes() == b'\xff\xff\xff\xff\xff\xff\xff'

def test_pus_tc_header_strict_version():
    # a PUS-A header, version 1 in the top nibble
    data = b'\x10\x08\x01\x00'

    assert PUSTCHeader.from_bytes(data).version == 1

    with pytest.raises(ValueError):
        PUSTCHeader.from_bytes(data, strict=True)

    assert PUSTCHeader.from_bytes(PUSTCHeader().as_bytes(), strict=True) == PUSTCHeader()

def test_pus_tm_header_strict_version():
    data = PUSTMHeader(version=1).as_bytes()

    assert PUSTMHeader.from_bytes(data).version == 1

    with pytest.raises(ValueError):
        PUSTMHeader.from_bytes(data, strict=True)

    assert PUSTMHeader.from_bytes(PUSTMHeader().as_bytes(), strict=True) == PUSTMHeader()

def test_pus_header_strict_rejects_reserved_service():
    # service type 0 is reserved, and is only rejected when strict
    data = b'\x20\x00\x01\x00'

    assert PUSTCHeader.from_bytes(data).service_type == 0

    with pytest.raises(ValueError):
        PUSTCHeader.from_bytes(data, strict=True)

def test_pus_header_decoding_stays_permissive():
    # a malformed header can be inspected, re-encoding it is what raises
    header = PUSTCHeader.from_bytes(b'\x10\x00\x01\x00')

    assert header.version == 1
    assert header.service_type == 0

    with pytest.raises(ValueError):
        header.as_bytes()

def test_space_packet_pus_strict():
    space_packet = SpacePacket(secondary_header=PUSTMHeader(version=1),
                               data_field=b'\x01\x02')
    bytes1 = space_packet.as_bytes()

    assert SpacePacket.from_bytes(bytes1, pus_tm=True).secondary_header.version == 1

    with pytest.raises(ValueError):
        SpacePacket.from_bytes(bytes1, pus_tm=True, pus_strict=True)

def test_space_packet_pus_strict_iter_packets():
    good = SpacePacket(apid=1, secondary_header=PUSTMHeader(), data_field=b'\x01')
    bad = SpacePacket(apid=2, secondary_header=PUSTMHeader(version=1), data_field=b'\x02')

    with pytest.raises(ValueError):
        list(SpacePacket.iter_packets(good.as_bytes() + bad.as_bytes(),
                                      pus_tm=True, pus_strict=True))

def test_space_packet_pus_tc_packet_error_control():
    tc_header = PUSTCHeader(service_type=8, service_subtype=1)
    space_packet = SpacePacket(type=PacketType.TC, apid=11, secondary_header=tc_header,
                               data_field=b'\x01\x02')

    bytes1 = space_packet.as_bytes(packet_error_control=True)
    assert len(bytes1) == 6 + PUS_TC_HEADER_LENGTH + 2 + 2

    packet2 = SpacePacket.from_bytes(bytes1, pus_tc=True, packet_error_control=True)

    assert packet2.secondary_header == tc_header
    assert packet2.data_field == b'\x01\x02'
    assert packet2.as_bytes(packet_error_control=True) == bytes1
