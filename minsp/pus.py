
import struct, time
from dataclasses import dataclass

@dataclass
class PUSHeader:
    version: int = 1
    ack: int = 0
    service_type: int = 1
    service_subtype: int = 1
    source_id: int = 0x42
    include_time: bool = True
    cuc_time: bytes = None

    def pack(self) -> bytes:
        first_byte = ((self.version & 0x0F) << 4) | (self.ack & 0x0F)
        header = struct.pack(">BBBB",
                            first_byte, self.service_type, self.service_subtype, self.source_id)

        if self.include_time:
            if self.cuc_time:
                return header + self.cuc_time
            else:
                return header + self.generate_cuc_time()
        else:
            return header

    def generate_cuc_time(self) -> bytes:
        """Generates a basic 4-byte CUC time from current epoch time"""
        now = int(time.time())
        coarse = (now >> 24) & 0xFF  # highest byte
        fine = now & 0xFFFFFF        # lower 3 bytes
        return struct.pack(">BI", coarse, fine)[0:4]

    @classmethod
    def from_bytes(cls, data: bytes, has_time: bool = True) -> "PUSHeader":
        if len(data) < 4:
            raise ValueError("Insufficient data for PUS header")

        first_byte, service_type, service_subtype, source_id = struct.unpack(">BBBB", data[:4])
        version = (first_byte >> 4) & 0x0F
        ack = first_byte & 0x0F

        cuc_time = None
        if has_time:
            if len(data) < 8:
                raise ValueError("Insufficient data for PUS header with CUC time")
            cuc_time = data[4:8]

        return cls(
            version=version,
            ack=ack,
            service_type=service_type,
            service_subtype=service_subtype,
            source_id=source_id,
            include_time=has_time,
            cuc_time=cuc_time
        )
