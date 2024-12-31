
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

**Note**: `minsp` depends on the `bitstruct` package that may require a C
compiler to install.

## Quick Start

Import the `SpacePacket` class from the package:

```python
>>> from minsp import SpacePacket
```

For example, to create a new space packet for APID 11 and an arbitrary payload:

```python
>>> space_packet = SpacePacket(apid=11, payload=b'hello')
>>> space_packet
SpacePacket(version=0b0, type=PacketType.TM, sec_hdr_flag=0b0, apid=11,
sequence_flags=0b11, sequence_count=0, data_length=4)
```

To get the bytes representation of the packet:

```python
>>> byte_stream = space_packet.byte_stream()
>>> byte_stream
b'\x00\x0b\xc0\x00\x00\x04hello'
```

Packets can also be created from a byte stream:

```python
>>> new_packet = SpacePacket.from_byte_stream(byte_stream)
>>> new_packet
SpacePacket(version=0b0, type=PacketType.TM, sec_hdr_flag=0b0, apid=11,
sequence_flags=0b11, sequence_count=0, data_length=4)
>>> new_packet.payload
b'hello'
```
