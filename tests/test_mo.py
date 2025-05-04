
from minsp.mo import MALHeader

def test_new_mal_header():
    header = MALHeader()

    assert header.version == 0
    assert header.sdu_type == 0
    assert header.service_area == 0
    assert header.service == 0
    assert header.operation == 0
    assert header.area_version == 0
    assert header.is_error == 0
    assert header.qos_level == 0
    assert header.session == 0
    assert header.secondary_apid == 0
    assert header.secondary_apid_qualifier == 0
    assert header.transaction_id == 0
    assert header.source_id_flag == 0
    assert header.destination_id_flag == 0
    assert header.priority_flag == 0
    assert header.timestamp_flag == 0
    assert header.network_zone_flag == 0
    assert header.session_name_flag == 0
    assert header.domain_flag == 0
    assert header.authentication_id_flag == 0

def test_mal_header_bytes():
    h1 = MALHeader()
    h2 = MALHeader.from_bytes(MALHeader().as_bytes())
    
    assert h1 == h2

    bytes1 = MALHeader().as_bytes()
    bytes2 = MALHeader.from_bytes(bytes1).as_bytes()
    
    assert bytes1 == bytes2
