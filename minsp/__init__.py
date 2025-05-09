"""
The `minsp.__init__` module imports the core functions and classes from `minsp.core`.
"""

import logging

from .core import SpacePacket, PacketType, SequenceFlags, SpacePacketAssembler

__all__ = ["SpacePacket", "PacketType", "SequenceFlags", "SpacePacketAssembler"]

logging.basicConfig(
    format="%(asctime)s | %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.WARNING,
)
