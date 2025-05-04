"""
The `minsp.mo` module provides MAL header related classes.
"""

from dataclasses import dataclass
import struct
from datetime import datetime, timezone

from .utils import mal_encode_string, mal_decode_string

@dataclass
class MALHeader:
    """
    Represents a MAL (Message Abstraction Layer) secondary header as defined by CCSDS 524.1-B-1.

    This header is used in CCSDS Space Packet Protocols to provide structured metadata about
    messages, including addressing, quality of service, and transport-level information.

    :param version: MAL version (3 bits, usually 1).
    :type version: int
    :param sdu_type: SDU type (5 bits), e.g., 1 for message, 2 for acknowledgment.
    :type sdu_type: int
    :param service_area: Numeric identifier of the service area (16 bits).
    :type service_area: int
    :param service: Specific service within the area (16 bits).
    :type service: int
    :param operation: Operation identifier (8 bits).
    :type operation: int
    :param area_version: Version of the service area (8 bits).
    :type area_version: int
    :param is_error: Error flag (1 bit): 0 = normal, 1 = error.
    :type is_error: int
    :param qos_level: Quality of Service level (2 bits).
    :type qos_level: int
    :param session: Session type (2 bits), e.g., P2P, PUB/SUB.
    :type session: int
    :param secondary_apid: 11-bit field representing the secondary Application Process ID.
    :type secondary_apid: int
    :param secondary_apid_qualifier: Qualifier for secondary APID (16 bits).
    :type secondary_apid_qualifier: int
    :param transaction_id: Unique transaction ID (64 bits).
    :type transaction_id: int
    :param source_id_flag: If set, `source_id` field is present (1 bit).
    :type source_id_flag: int
    :param destination_id_flag: If set, `destination_id` field is present (1 bit).
    :type destination_id_flag: int
    :param priority_flag: If set, `priority` field is present (1 bit).
    :type priority_flag: int
    :param timestamp_flag: If set, `timestamp` field is present (1 bit).
    :type timestamp_flag: int
    :param network_zone_flag: If set, `network_zone` field is present (1 bit).
    :type network_zone_flag: int
    :param session_name_flag: If set, `session_name` field is present (1 bit).
    :type session_name_flag: int
    :param domain_flag: If set, `domain` field is present (1 bit).
    :type domain_flag: int
    :param authentication_id_flag: If set, `authentication_id` field is present (1 bit).
    :type authentication_id_flag: int
    :param source_id: Optional source identifier (8 bits).
    :type source_id: int
    :param destination_id: Optional destination identifier (8 bits).
    :type destination_id: int
    :param segment_counter: Optional segment counter for sequencing (32 bits).
    :type segment_counter: int
    :param priority: Optional message priority (32 bits).
    :type priority: int
    :param timestamp: Optional UTC timestamp (CUC 7-byte format).
    :type timestamp: datetime
    :param network_zone: Optional network zone string (UTF-8, length-prefixed).
    :type network_zone: str
    :param session_name: Optional session name string (UTF-8, length-prefixed).
    :type session_name: str
    :param domain: Optional domain string (UTF-8, length-prefixed).
    :type domain: str
    :param authentication_id: Optional authentication ID string (UTF-8, length-prefixed).
    :type sdu_type: str
    """
    version: int = 0
    sdu_type: int = 0
    service_area: int = 0
    service: int = 0
    operation: int = 0
    area_version: int = 0
    is_error: int = 0
    qos_level: int = 0
    session: int = 0
    secondary_apid: int = 0
    secondary_apid_qualifier: int = 0
    transaction_id: int = 0

    source_id_flag: int = 0
    destination_id_flag: int = 0
    priority_flag: int = 0
    timestamp_flag: int = 0
    network_zone_flag: int = 0
    session_name_flag: int = 0
    domain_flag: int = 0
    authentication_id_flag: int = 0

    source_id: int = 0
    destination_id: int = 0
    segment_counter: int = 0
    priority: int = 0
    timestamp: datetime|None = None
    network_zone: str = ''
    session_name: str = ''
    domain: str = ''
    authentication_id: str = ''

    def as_bytes(self, sequence_flag=3) -> bytes:
        """
        Packs the MAL header as a byte stream.

        :raises ValueError: Timestamp flag set but no valid timestamp provided

        :return: MAL header bytes.
        :rtype: bytes
        """
        ver_and_sdu = ((self.version & 0x7) << 5) | (self.sdu_type & 0x1F)
        error_qos_session_sec_apid = (
            ((self.is_error & 0x1) << 15) |
            ((self.qos_level & 0x3) << 13) |
            ((self.session & 0x3) << 11) |
            (self.secondary_apid & 0x7FF)
        )
        flags = (
            ((self.source_id_flag & 0x1) << 7) |
            ((self.destination_id_flag & 0x1) << 6) |
            ((self.priority_flag & 0x1) << 5) |
            ((self.timestamp_flag & 0x1) << 4) |
            ((self.network_zone_flag & 0x1) << 3) |
            ((self.session_name_flag & 0x1) << 2) |
            ((self.domain_flag & 0x1) << 1) |
            (self.authentication_id_flag & 0x1)
        )

        header = struct.pack(
            ">B 3H B 2H q B",
            ver_and_sdu,
            self.service_area,
            self.service,
            self.operation,
            self.area_version,
            error_qos_session_sec_apid,
            self.secondary_apid_qualifier,
            self.transaction_id,
            flags
        )

        parts = [header]

        # optional fixed length fields
        if self.source_id_flag:
            parts.append(struct.pack(">B", self.source_id))
        if self.destination_id_flag:
            parts.append(struct.pack(">B", self.destination_id))
        if sequence_flag != 3:
            parts.append(struct.pack(">L", self.segment_counter))
        if self.priority_flag:
            parts.append(struct.pack(">L", self.priority))
        if self.timestamp_flag:
            if not isinstance(self.timestamp, datetime):
                raise ValueError("Timestamp flag set but no valid timestamp provided.")
            epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
            delta = (self.timestamp - epoch).total_seconds()
            seconds = int(delta)
            fraction = int((delta - seconds) * (1 << 24))
            parts.append(struct.pack(">I", seconds) + fraction.to_bytes(3, 'big'))

        # optional variable length fields
        if self.network_zone_flag:
            parts.append(mal_encode_string(self.network_zone or ""))
        if self.session_name_flag:
            parts.append(mal_encode_string(self.session_name or ""))
        if self.domain_flag:
            parts.append(mal_encode_string(self.domain or ""))
        if self.authentication_id_flag:
            parts.append(mal_encode_string(self.authentication_id or ""))

        return b"".join(parts)


    # pylint: disable=R0914,R0912,R0915
    @classmethod
    def from_bytes(cls, data:bytes, sequence_flag:int = 3):
        """
        Unpacks a byte stream into a `MALHeader` instance.

        :param data: The byte stream.
        :type data: bytes
        :param sequence_flag: The packet sequence flag, defaults to 3.
        :type sequence_flag: int

        :raises ValueError: MAL header too short.

        :return: A new `MALHeader`.
        :rtype: MALHeader
        """
        if len(data) < 20:
            raise ValueError("MAL header too short.")

        # CCSDS 524.1-B-1 page 3-4
        ver_and_sdu, service_area, service, operation, area_version, error_qos_session_sec_apid, \
            secondary_apid_qualifier, transaction_id, flags \
                = struct.unpack(">B 3H B 2H q B", data[:21])

        version = ver_and_sdu >> 5 & 0x7
        sdu_type = ver_and_sdu & 0x1F
        is_error = error_qos_session_sec_apid >> 15 & 0x1
        qos_level = error_qos_session_sec_apid >> 13 & 0x3
        session = error_qos_session_sec_apid >> 11 & 0x3
        secondary_apid = error_qos_session_sec_apid & 0x7FF
        source_id_flag = flags >> 7 & 0x1
        destination_id_flag = flags >> 6 & 0x1
        priority_flag = flags >> 5 & 0x1
        timestamp_flag = flags >> 4 & 0x1
        network_zone_flag = flags >> 3 & 0x1
        session_name_flag = flags >> 2 & 0x1
        domain_flag = flags >> 1 & 0x1
        authentication_id_flag = flags >> 0 & 0x1

        offset = 21
        if source_id_flag:
            source_id = struct.unpack(">B", data[offset:offset+1])[0]
            offset += 1
        else:
            source_id = 0
        if destination_id_flag:
            destination_id = struct.unpack(">B", data[offset:offset+1])[0]
            offset += 1
        else:
            destination_id = 0
        if sequence_flag != 3:
            segment_counter = struct.unpack(">L", data[offset:offset+4])[0]
            offset += 4
        else:
            segment_counter = 0
        if priority_flag:
            priority = struct.unpack(">L", data[offset:offset+4])[0]
            offset += 4
        else:
            priority = 0
        if timestamp_flag:
            timestamp_buf = data[offset:offset+7]
            seconds = struct.unpack(">I", timestamp_buf[0:4])[0]
            fractions = timestamp_buf[4] << 16 | timestamp_buf[5] << 8 | timestamp_buf[6]
            timestamp = datetime.fromtimestamp(seconds + (fractions/0xFFFFFF), timezone.utc)
            offset += 7
        else:
            timestamp = None
        if network_zone_flag:
            network_zone, offset = mal_decode_string(data, offset)
        else:
            network_zone = ''
        if session_name_flag:
            session_name, offset = mal_decode_string(data, offset)
        else:
            session_name = ''
        if domain_flag:
            domain, offset = mal_decode_string(data, offset)
        else:
            domain = ''
        if authentication_id_flag:
            authentication_id, offset = mal_decode_string(data, offset)
        else:
            authentication_id = ''

        return cls(
            version=version,
            sdu_type=sdu_type,
            service_area=service_area,
            service=service,
            operation=operation,
            area_version=area_version,
            is_error=is_error,
            qos_level=qos_level,
            session=session,
            secondary_apid=secondary_apid,
            secondary_apid_qualifier=secondary_apid_qualifier,
            transaction_id=transaction_id,
            source_id_flag=source_id_flag,
            destination_id_flag=destination_id_flag,
            priority_flag=priority_flag,
            timestamp_flag=timestamp_flag,
            network_zone_flag=network_zone_flag,
            session_name_flag=session_name_flag,
            domain_flag=domain_flag,
            authentication_id_flag=authentication_id_flag,
            source_id=source_id,
            destination_id=destination_id,
            segment_counter=segment_counter,
            priority=priority,
            timestamp=timestamp,
            network_zone=network_zone,
            session_name=session_name,
            domain=domain,
            authentication_id=authentication_id
        )
