
Getting Started
-------------------------------------

Import the :code:`SpacePacket` class from the package:

.. code-block:: python

   >>> from minsp import SpacePacket

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

Secondary header can have a custom data definition, or to use PUS:

.. code-block:: python

   >>> from minsp.pus import PUSHeader
   >>> pus_header = PUSHeader()
   >>> pus_header
   PUSHeader(version=1, ack=0, service_type=1, service_subtype=1, source_id=0, has_time=False, cuc_time=b'')

And create a new packet with the PUS header:

.. code-block:: python

   >>> space_packet = SpacePacket(secondary_header=pus_header)
   >>> space_packet
   SpacePacket(version=0, type=<PacketType.TM: 0>, secondary_header_flag=1, apid=0, sequence_flags=<SequenceFlags.UNSEGMENTED: 3>, sequence_count=0, data_length=3, secondary_header=PUSHeader(version=1, ack=0, service_type=1, service_subtype=1, source_id=0, has_time=False, cuc_time=b''), data_field=b'')

Similar approach for a MAL secondary header:

.. code-block:: python

   >>> from minsp.mo import MALHeader
   >>> mal_header = MALHeader()
   >>> mal_header
   MALHeader(version=0, sdu_type=0, service_area=0, service=0, operation=0, area_version=0, is_error=0, qos_level=0, session=0, secondary_apid=0, secondary_apid_qualifier=0, transaction_id=0, source_id_flag=0, destination_id_flag=0, priority_flag=0, timestamp_flag=0, network_zone_flag=0, session_name_flag=0, domain_flag=0, authentication_id_flag=0, source_id=0, destination_id=0, segment_counter=0, priority=0, timestamp=None, network_zone='', session_name='', domain='', authentication_id='')

And to create a new packet with the MAL header:

.. code-block:: python

   >>> space_packet = SpacePacket(secondary_header=mal_header)
   >>> space_packet
   SpacePacket(version=0, type=<PacketType.TM: 0>, secondary_header_flag=1, apid=0, sequence_flags=<SequenceFlags.UNSEGMENTED: 3>, sequence_count=0, data_length=20, secondary_header=MALHeader(version=0, sdu_type=0, service_area=0, service=0, operation=0, area_version=0, is_error=0, qos_level=0, session=0, secondary_apid=0, secondary_apid_qualifier=0, transaction_id=0, source_id_flag=0, destination_id_flag=0, priority_flag=0, timestamp_flag=0, network_zone_flag=0, session_name_flag=0, domain_flag=0, authentication_id_flag=0, source_id=0, destination_id=0, segment_counter=0, priority=0, timestamp=None, network_zone='', session_name='', domain='', authentication_id=''), data_field=b'')

To create a space packet from a byte stream including a PUS header:

.. code-block:: python

   >>> data = SpacePacket(secondary_header=pus_header).as_bytes()
   >>> SpacePacket.from_bytes(data, pus=True)
   SpacePacket(version=0, type=<PacketType.TM: 0>, secondary_header_flag=1, apid=0, sequence_flags=<SequenceFlags.UNSEGMENTED: 3>, sequence_count=0, data_length=3, secondary_header=PUSHeader(version=1, ack=0, service_type=1, service_subtype=1, source_id=0, has_time=False, cuc_time=b''), data_field=b'')

Or from a byte stream including a MAL header:

.. code-block:: python

   >>> data = SpacePacket(secondary_header=mal_header).as_bytes()
   >>> SpacePacket.from_bytes(data, mal=True)
   SpacePacket(version=0, type=0, secondary_header_flag=1, apid=0, sequence_flags=3, sequence_count=0, data_length=20, secondary_header=MALHeader(version=0, sdu_type=0, service_area=0, service=0, operation=0, area_version=0, is_error=0, qos_level=0, session=0, secondary_apid=0, secondary_apid_qualifier=0, transaction_id=0, source_id_flag=0, destination_id_flag=0, priority_flag=0, timestamp_flag=0, network_zone_flag=0, session_name_flag=0, domain_flag=0, authentication_id_flag=0, source_id=0, destination_id=0, segment_counter=0, priority=0, timestamp=None, network_zone='', session_name='', domain='', authentication_id=''), data_field=b'')

Use :code:`SpacePacketAssembler` to recover the data from a list
of fragmented packets, for example consider the following packets:

.. code-block:: python

   >>> from minsp import SpacePacket, SequenceFlag
   >>> sp1 = SpacePacket(sequence_flags=SequenceFlag.FIRST, data_field=b"123")
   >>> sp2 = SpacePacket(sequence_flags=SequenceFlag.CONTINUATION, data_field=b"456")
   >>> sp3 = SpacePacket(sequence_flags=SequenceFlag.LAST, data_field=b"789")

To recover the fragmented payload by processing the individual packets:

.. code-block:: python

   >>> from minsp import SpacePacketAssembler
   >>> spa = SpacePacketAssembler()
   >>> spa.process_packet(sp1)
   >>> spa.process_packet(sp2)
   >>> spa.process_packet(sp3)
   b'123456789'


Or directly using the :code:`from_packets` method:

.. code-block:: python

   >>> SpacePacketAssembler.from_packets([sp1, sp2, sp3])
   b'123456789'

