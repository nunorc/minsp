
# minsp

Minimalistic implementation of the Space Packet specification from the CCSDS Space Packet Protocol standard.

[Repository](https://github.com/nunorc/minsp) | [Documentation](https://nunorc.github.io/minsp)

## Installation

Install using pip:

```bash
$ pip install minsp
```

Install package from the git repository:

```bash
$ pip install git+https://github.com/nunorc/minsp@master
```

## Getting Started

Import the `SpacePacket` class from the package:

```python
>>> from minsp import SpacePacket
```

For example, to create a new space packet for APID 11 and an arbitrary data field:

```python
>>> space_packet = SpacePacket(apid=11, data_field=b'hello')
>>> space_packet
SpacePacket(version=0, type=<PacketType.TM: 0>, secondary_header_flag=0, apid=11, sequence_flags=3, sequence_count=0, data_length=4, secondary_header=b'', data_field=b'hello')
```

To get the bytes representation of the packet:

```python
>>> byte_stream = space_packet.as_bytes()
>>> byte_stream
b'\x00\x0b\xc0\x00\x00\x04hello'
```

Packets can also be created from a byte stream:

```python
>>> new_packet = SpacePacket.from_bytes(byte_stream)
>>> new_packet
SpacePacket(version=0, type=0, secondary_header_flag=0, apid=11, sequence_flags=3, sequence_count=0, data_length=4, secondary_header=b'', data_field=b'hello')
>>> new_packet.data_field
b'hello'
```

Secondary header can have a custom data definition, or to use PUS:

```python
>>> from minsp.pus import PUSHeader
>>> pus_header = PUSHeader()
>>> pus_header
PUSHeader(version=1, ack=0, service_type=1, service_subtype=1, source_id=0, has_time=False, cuc_time=b'')
```

And create a new packet with the PUS header:

```python
>>> space_packet = SpacePacket(secondary_header=pus_header)
>>> space_packet
SpacePacket(version=0, type=<PacketType.TM: 0>, secondary_header_flag=1, apid=0, sequence_flags=3, sequence_count=0, data_length=3, secondary_header=PUSHeader(version=1, ack=0, service_type=1, service_subtype=1, source_id=0, has_time=False, cuc_time=b''), data_field=b'')
```

Similar approach for a MAL secondary header:

```python
>>> from minsp.mo import MALHeader
>>> mal_header = MALHeader()
>>> mal_header
MALHeader(version=0, sdu_type=0, service_area=0, service=0, operation=0, area_version=0, is_error=0, qos_level=0, session=0, secondary_apid=0, secondary_apid_qualifier=0, transaction_id=0, source_id_flag=0, destination_id_flag=0, priority_flag=0, timestamp_flag=0, network_zone_flag=0, session_name_flag=0, domain_flag=0, authentication_id_flag=0, source_id=0, destination_id=0, segment_counter=0, priority=0, timestamp=None, network_zone='', session_name='', domain='', authentication_id='')
```

And to create a new packet with the MAL header:

```python
>>> space_packet = SpacePacket(secondary_header=mal_header)
>>> space_packet
SpacePacket(version=0, type=<PacketType.TM: 0>, secondary_header_flag=1, apid=0, sequence_flags=3, sequence_count=0, data_length=20, secondary_header=MALHeader(version=0, sdu_type=0, service_area=0, service=0, operation=0, area_version=0, is_error=0, qos_level=0, session=0, secondary_apid=0, secondary_apid_qualifier=0, transaction_id=0, source_id_flag=0, destination_id_flag=0, priority_flag=0, timestamp_flag=0, network_zone_flag=0, session_name_flag=0, domain_flag=0, authentication_id_flag=0, source_id=0, destination_id=0, segment_counter=0, priority=0, timestamp=None, network_zone='', session_name='', domain='', authentication_id=''), data_field=b'')
```

To create a space packet from a byte stream including a PUS header:

```python
>>> data = SpacePacket(secondary_header=pus_header).as_bytes()
>>> SpacePacket.from_bytes(data, pus=True)
SpacePacket(version=0, type=0, secondary_header_flag=1, apid=0, sequence_flags=3, sequence_count=0, data_length=3, secondary_header=PUSHeader(version=1, ack=0, service_type=1, service_subtype=1, source_id=0, has_time=False, cuc_time=b''), data_field=b'')
```

Or from a byte stream including a MAL header:

```python
>>> data = SpacePacket(secondary_header=mal_header).as_bytes()
>>> SpacePacket.from_bytes(data, mal=True)
SpacePacket(version=0, type=0, secondary_header_flag=1, apid=0, sequence_flags=3, sequence_count=0, data_length=20, secondary_header=MALHeader(version=0, sdu_type=0, service_area=0, service=0, operation=0, area_version=0, is_error=0, qos_level=0, session=0, secondary_apid=0, secondary_apid_qualifier=0, transaction_id=0, source_id_flag=0, destination_id_flag=0, priority_flag=0, timestamp_flag=0, network_zone_flag=0, session_name_flag=0, domain_flag=0, authentication_id_flag=0, source_id=0, destination_id=0, segment_counter=0, priority=0, timestamp=None, network_zone='', session_name='', domain='', authentication_id=''), data_field=b'')
```

## Acknowledgements

* Dominik Marszk for general support and MAL header baseline implementation.
