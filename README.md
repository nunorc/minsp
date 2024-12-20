
# minsp

Minimalistic implementation of the Space Packet specification from the CCSDS Space Packet Protocol standard.

## Synopsis

```python
>>> from minsp import SpacePacket
>>> space_packet = SpacePacket(apid=11, payload=b'hello')
>>> space_packet
SpacePacket(version=0b0, type=PacketType.TM, sec_hdr_flag=0b0, apid=11, sequence_flags=0b11, sequence_count=0, data_length=4)
>>> byte_stream = space_packet.byte_stream()
>>> byte_stream
b'\x00\x0b\xc0\x00\x00\x04hello'
>>> new_packet = SpacePacket.from_byte_stream(byte_stream)
>>> new_packet
SpacePacket(version=0b0, type=PacketType.TM, sec_hdr_flag=0b0, apid=11, sequence_flags=0b11, sequence_count=0, data_length=4)
>>> new_packet.payload
b'hello'
```
