
Getting Started
-------------------------------------

Import the :code:`SpacePacket` class from the package:

.. code-block:: python

   >>> from minspp import SpacePacket

For example, to create a new space packet for APID 11 and an arbitrary data field:

.. code-block:: python

   >>> space_packet = SpacePacket(apid=11, data_field=b'hello')
   >>> space_packet
   SpacePacket(version=0, type=<PacketType.TM: 0>, secondary_header_flag=0, apid=11, sequence_flags=<SequenceFlags.UNSEGMENTED: 3>, sequence_count=0, data_length=4, secondary_header=b'', data_field=b'hello')

To get the bytes representation of the packet:

.. code-block:: python

   >>> byte_stream = space_packet.as_bytes()
   >>> byte_stream
   b'\x00\x0b\xc0\x00\x00\x04hello'

Packets can also be created from a byte stream:

.. code-block:: python

   >>> new_packet = SpacePacket.from_bytes(byte_stream)
   >>> new_packet
   SpacePacket(version=0, type=<PacketType.TM: 0>, secondary_header_flag=0, apid=11, sequence_flags=<SequenceFlags.UNSEGMENTED: 3>, sequence_count=0, data_length=4, secondary_header=b'', data_field=b'hello')
   >>> new_packet.data_field
   b'hello'

The packet data length field delimits the packet, so any octets past the end of
the packet are ignored. To walk a buffer holding several back to back packets use
:code:`iter_packets`, which takes the same secondary header arguments as
:code:`from_bytes`:

.. code-block:: python

   >>> stream = b'\x00\x0b\xc0\x00\x00\x04hello\x00\x0c\xc0\x00\x00\x04world'
   >>> [(p.apid, p.data_field) for p in SpacePacket.iter_packets(stream)]
   [(11, b'hello'), (12, b'world')]

The packet data field can end with a packet error control field, the CRC-16-CCITT
of every preceding octet of the packet, which most missions mandate for
telecommands. It is opt-in on both sides, and the data length written to the
primary header accounts for the two extra octets:

.. code-block:: python

   >>> byte_stream = space_packet.as_bytes(packet_error_control=True)
   >>> byte_stream
   b'\x00\x0b\xc0\x00\x00\x06hello\x81c'
   >>> SpacePacket.from_bytes(byte_stream, packet_error_control=True).data_field
   b'hello'

Decoding verifies the field and strips it, a mismatch raises a :code:`ValueError`.

Secondary header can have a custom data definition, or to use PUS. Telemetry
packets use the PUS-C (ECSS-E-ST-70-41C) TM secondary header:

.. code-block:: python

   >>> from minspp.pus import PUSTMHeader
   >>> pus_header = PUSTMHeader()
   >>> pus_header
   PUSTMHeader(version=2, time_reference_status=0, service_type=1, service_subtype=1, message_type_counter=0, destination_id=0, has_time=False, cuc_time=b'')

And create a new packet with the PUS header:

.. code-block:: python

   >>> space_packet = SpacePacket(secondary_header=pus_header)
   >>> space_packet
   SpacePacket(version=0, type=<PacketType.TM: 0>, secondary_header_flag=1, apid=0, sequence_flags=<SequenceFlags.UNSEGMENTED: 3>, sequence_count=0, data_length=6, secondary_header=PUSTMHeader(version=2, time_reference_status=0, service_type=1, service_subtype=1, message_type_counter=0, destination_id=0, has_time=False, cuc_time=b''), data_field=b'')

For example a housekeeping parameter report (service 3, subtype 25) for
destination 42:

.. code-block:: python

   >>> tm_header = PUSTMHeader(service_type=3, service_subtype=25, message_type_counter=7, destination_id=42)
   >>> tm_header.as_bytes()
   b' \x03\x19\x00\x07\x00*'

The width of the TM destination ID is mission defined, use
:code:`destination_id_length` to set it in bytes (defaults to :code:`2`, and
:code:`0` means the field is absent):

.. code-block:: python

   >>> PUSTMHeader(service_type=3, service_subtype=25, message_type_counter=7, destination_id=42, destination_id_length=1).as_bytes()
   b' \x03\x19\x00\x07*'

The split of the CUC time between the coarse (seconds) and the fine (sub-seconds)
field is mission defined too, use :code:`cuc_coarse_length` to set the coarse part,
the remaining octets of :code:`cuc_time_length` hold the fine part:

.. code-block:: python

   >>> header = PUSTMHeader(has_time=True, cuc_time_length=7, cuc_coarse_length=5)
   >>> header.fine_time_length()
   2

So is the epoch the coarse time counts from, which defaults to the Unix epoch, use
:code:`cuc_epoch` for a mission that counts from another one (the CCSDS
agency-standard epoch is 1958-01-01, and mission elapsed time counts from launch):

.. code-block:: python

   >>> from datetime import datetime, timezone
   >>> from minspp.utils import cuc_as_datetime
   >>> epoch = datetime(1958, 1, 1, tzinfo=timezone.utc)
   >>> header = PUSTMHeader(has_time=True, cuc_epoch=epoch)
   >>> cuc_as_datetime(header.cuc_time, epoch=epoch)   # the current time
   datetime.datetime(2026, 7, 29, 20, 17, 2, 120716, tzinfo=datetime.timezone.utc)

These values must be given again when decoding, as
:code:`pus_destination_id_length`, :code:`pus_cuc_coarse_length` and
:code:`pus_cuc_epoch` of :code:`SpacePacket.from_bytes`, otherwise the data field
is misaligned or the timestamp is read at the wrong resolution or epoch.

The CUC field carries none of them, they are declared out-of-band, and there is no
P-field (preamble) support. All the arithmetic is done on UTC datetimes: a mission
whose CUC counts a continuous time scale (TAI, GPS) is off by the leap seconds
accumulated since its epoch, this package does not convert time scales.

Telecommand packets use a different secondary header layout, implemented by the
:code:`PUSTCHeader` class:

.. code-block:: python

   >>> from minspp.pus import PUSTCHeader
   >>> PUSTCHeader()
   PUSTCHeader(version=2, ack=0, service_type=1, service_subtype=1, source_id=0, has_time=False, cuc_time=b'')

The width of the TC source ID is mission defined, use :code:`source_id_length` to
set it in bytes (defaults to :code:`1`, and :code:`0` means the field is absent):

.. code-block:: python

   >>> PUSTCHeader(service_type=8, service_subtype=1, source_id=0x0102, source_id_length=2).as_bytes()
   b' \x08\x01\x01\x02'

Field values are checked when a packet or a header is packed, not when it is built.
An out of range value raises a :code:`ValueError` instead of being silently masked
or surfacing as a :code:`struct.error`, and the standard reserves service type and
message subtype :code:`0`:

.. code-block:: python

   >>> PUSTCHeader(service_type=300).as_bytes()
   Traceback (most recent call last):
     ...
   ValueError: Invalid service type 300, must be between 1 and 255.

Decoding stays permissive, so a malformed packet can still be inspected. Use
:code:`strict` (or :code:`pus_strict` on :code:`SpacePacket.from_bytes`) to reject a
secondary header that is not valid PUS-C, i.e. one whose version is not :code:`2` or
whose service type or subtype is the reserved :code:`0`:

.. code-block:: python

   >>> PUSTCHeader.from_bytes(b'\x10\x08\x01\x00').version   # a PUS-A header
   1
   >>> PUSTCHeader.from_bytes(b'\x10\x08\x01\x00', strict=True)
   Traceback (most recent call last):
     ...
   ValueError: Invalid PUS version 1, must be 2 for PUS-C.

Note that ECSS-E-ST-70-41C defines no time field for the TC secondary header,
timestamps belong to telemetry. The :code:`has_time` and :code:`cuc_time` arguments
of :code:`PUSTCHeader` are a mission specific extension for missions that extend the
header, they are off by default and leaving them off keeps the header standard
conformant.

Similar approach for a MAL secondary header:

.. code-block:: python

   >>> from minspp.mo import MALHeader
   >>> mal_header = MALHeader()
   >>> mal_header
   MALHeader(version=0, sdu_type=0, service_area=0, service=0, operation=0, area_version=0, is_error=0, qos_level=0, session=0, secondary_apid=0, secondary_apid_qualifier=0, transaction_id=0, source_id_flag=0, destination_id_flag=0, priority_flag=0, timestamp_flag=0, network_zone_flag=0, session_name_flag=0, domain_flag=0, authentication_id_flag=0, source_id=0, destination_id=0, segment_counter=0, priority=0, timestamp=None, network_zone='', session_name='', domain='', authentication_id='')

And to create a new packet with the MAL header:

.. code-block:: python

   >>> space_packet = SpacePacket(secondary_header=mal_header)
   >>> space_packet
   SpacePacket(version=0, type=<PacketType.TM: 0>, secondary_header_flag=1, apid=0, sequence_flags=<SequenceFlags.UNSEGMENTED: 3>, sequence_count=0, data_length=20, secondary_header=MALHeader(version=0, sdu_type=0, service_area=0, service=0, operation=0, area_version=0, is_error=0, qos_level=0, session=0, secondary_apid=0, secondary_apid_qualifier=0, transaction_id=0, source_id_flag=0, destination_id_flag=0, priority_flag=0, timestamp_flag=0, network_zone_flag=0, session_name_flag=0, domain_flag=0, authentication_id_flag=0, source_id=0, destination_id=0, segment_counter=0, priority=0, timestamp=None, network_zone='', session_name='', domain='', authentication_id=''), data_field=b'')

To create a space packet from a byte stream including a PUS header, use
:code:`pus_tm=True` for a TM header, or :code:`pus_tc=True` for a TC one:

.. code-block:: python

   >>> data = SpacePacket(secondary_header=pus_header).as_bytes()
   >>> SpacePacket.from_bytes(data, pus_tm=True)
   SpacePacket(version=0, type=<PacketType.TM: 0>, secondary_header_flag=1, apid=0, sequence_flags=<SequenceFlags.UNSEGMENTED: 3>, sequence_count=0, data_length=6, secondary_header=PUSTMHeader(version=2, time_reference_status=0, service_type=1, service_subtype=1, message_type_counter=0, destination_id=0, has_time=False, cuc_time=b''), data_field=b'')

A TC header with a non default source ID width must be decoded with the same
width, otherwise the data field is misaligned, use :code:`pus_source_id_length`:

.. code-block:: python

   >>> tc_header = PUSTCHeader(service_type=8, service_subtype=1, source_id=0x0102, source_id_length=2)
   >>> data = SpacePacket(secondary_header=tc_header, data_field=b'\xAB\x2A').as_bytes()
   >>> SpacePacket.from_bytes(data, pus_tc=True, pus_source_id_length=2).data_field
   b'\xab*'

The same holds for the other mission defined values, use
:code:`pus_destination_id_length` for a TM header, :code:`pus_cuc_coarse_length`
for the coarse and fine time split, and :code:`pus_cuc_epoch` for the epoch:

.. code-block:: python

   >>> tm_header = PUSTMHeader(service_type=3, service_subtype=25, destination_id=42, destination_id_length=1)
   >>> data = SpacePacket(secondary_header=tm_header, data_field=b'\x01\x02').as_bytes()
   >>> SpacePacket.from_bytes(data, pus_tm=True, pus_destination_id_length=1).data_field
   b'\x01\x02'

Or from a byte stream including a MAL header:

.. code-block:: python

   >>> data = SpacePacket(secondary_header=mal_header).as_bytes()
   >>> SpacePacket.from_bytes(data, mal=True)
   SpacePacket(version=0, type=<PacketType.TM: 0>, secondary_header_flag=1, apid=0, sequence_flags=<SequenceFlags.UNSEGMENTED: 3>, sequence_count=0, data_length=20, secondary_header=MALHeader(version=0, sdu_type=0, service_area=0, service=0, operation=0, area_version=0, is_error=0, qos_level=0, session=0, secondary_apid=0, secondary_apid_qualifier=0, transaction_id=0, source_id_flag=0, destination_id_flag=0, priority_flag=0, timestamp_flag=0, network_zone_flag=0, session_name_flag=0, domain_flag=0, authentication_id_flag=0, source_id=0, destination_id=0, segment_counter=0, priority=0, timestamp=None, network_zone='', session_name='', domain='', authentication_id=''), data_field=b'')

Use :code:`SpacePacketAssembler` to recover the data from a list
of fragmented packets, for example consider the following packets:

.. code-block:: python

   >>> from minspp import SpacePacket, SequenceFlags
   >>> sp1 = SpacePacket(sequence_flags=SequenceFlags.FIRST, data_field=b"123")
   >>> sp2 = SpacePacket(sequence_flags=SequenceFlags.CONTINUATION, data_field=b"456")
   >>> sp3 = SpacePacket(sequence_flags=SequenceFlags.LAST, data_field=b"789")

To recover the fragmented payload by processing the individual packets:

.. code-block:: python

   >>> from minspp import SpacePacketAssembler
   >>> spa = SpacePacketAssembler()
   >>> spa.process_packet(sp1)
   >>> spa.process_packet(sp2)
   >>> spa.process_packet(sp3)
   b'123456789'


Or directly using the :code:`from_packets` method:

.. code-block:: python

   >>> SpacePacketAssembler.from_packets([sp1, sp2, sp3])
   b'123456789'

