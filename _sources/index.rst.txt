
minsp
=====================================

Minimalistic implementation of the Space Packet specification from the CCSDS Space Packet Protocol standard.

`Repository <https://github.com/nunorc/minsp>`_ | `Documentation <https://nunorc.github.io/minsp>`_

Installation
-------------------------------------

Install package from the git repository:

.. code-block:: bash

    $ pip install git+https://github.com/nunorc/minsp@master

Quick Start
-------------------------------------

Import the :code:`SpacePacket` class from the package:

.. code-block:: python

   >>> from minsp import SpacePacket

For example, to create a new space packet for APID 11 and an arbitrary payload:

.. code-block:: python

   >>> space_packet = SpacePacket(apid=11, payload=b'hello')
   >>> space_packet
   SpacePacket(version=0b0, type=PacketType.TM, sec_hdr_flag=0b0, apid=11,
   sequence_flags=0b11, sequence_count=0, data_length=4)

To get the bytes representation of the packet:

.. code-block:: python

   >>> byte_stream = space_packet.byte_stream()
   >>> byte_stream
   b'\x00\x0b\xc0\x00\x00\x04hello'

Packets can also be created from a byte stream:

.. code-block:: python

   >>> new_packet = SpacePacket.from_byte_stream(byte_stream)
   >>> new_packet
   SpacePacket(version=0b0, type=PacketType.TM, sec_hdr_flag=0b0, apid=11,
   sequence_flags=0b11, sequence_count=0, data_length=4)
   >>> new_packet.payload
   b'hello'


.. automodule:: minsp.core
    :members:

.. toctree::
   :maxdepth: 2
   :caption: Contents:

