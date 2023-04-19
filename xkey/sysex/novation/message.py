"""Novation specific data models used by xKey."""

import struct
from typing import Dict

from xkey.sysex import constant


class Message:
    """Expresses a Novation SysEx message."""

    name: str = str()
    fields: Dict[str, str] = {}
    identifier: bytes = bytes()

    def size(self) -> int:
        """Returns the size of the message, in bytes."""
        return struct.calcsize("".join(self.fields.values()))

    def to_bytes(self) -> bytearray:
        """Returns this SysEx message as bytes."""
        buffer = bytearray()

        # Construct the header.
        buffer.append(constant.MIDI_SYSEX_SOX)
        buffer.append(0x0)
        buffer.extend(constant.MIDI_SYSEX_MANUFACTURER_IDS["Novation"])

        # Add the message payload / body.
        for field in self.fields.keys():
            buffer.extend(bytearray(getattr(self, field)))

        # Trailer.
        buffer.append(constant.MIDI_SYSEX_EOX)

        return buffer

    def from_bytes(self, buffer: bytearray):
        """Hydrates an object representing this SysEx message from bytes."""

        if len(buffer) < 8 or buffer[0] != constant.MIDI_SYSEX_SOX:
            raise ValueError("Buffer does not appear to contain a SysEx message.")

        if buffer[1] != 0x0:
            raise ValueError("Buffer contains an unsupported SysEx message.")

        if buffer[2:4] != constant.MIDI_SYSEX_MANUFACTURER_IDS["Novation"]:
            raise ValueError("Buffer does not contain a Novation SysEx message.")

        if buffer[4:6] != self.identifier:
            raise ValueError("Identifier in buffer is invalid for this message type.")

        # We need the names of fields specified, in addition to the specification of
        # the fields themselves, to allow unpacking into the correct field.
        fields = list(self.fields.keys())
        format_ = "".join(self.fields.values())

        for index, value in enumerate(struct.unpack(format_, buffer[6:-1])):
            setattr(self, fields[index], value)


class Start(Message):
    """Expresses a Novation 'Start' SysEx message."""

    name: str = "START"
    identifier: bytes = bytearray([0x00, 0x71])

    # A mapping of the field name to its format string. These MUST be in the order.
    fields: Dict[str, str] = {
        "manufacturer": "c",
        "model": "c",
        "build": "6s",
    }


class Metadata(Message):
    """Expresses a Novation 'Metadata' SysEx message."""

    name: str = "METADATA"
    identifier: bytes = bytearray([0x00, 0x7C])

    # A mapping of the field name to its format string. These MUST be in the order.
    fields: Dict[str, str] = {
        "unknown0": "c",
        "build": "6s",
        "chunk": "16s",
    }


class Data(Message):
    """Expresses a Novation 'Data' SysEx message."""

    name: str = "DATA"
    identifier: bytes = bytearray([0x00, 0x72])

    # A mapping of the field name to its format string. These MUST be in the order.
    fields: Dict[str, str] = {
        "chunk": "37s",
    }


class End(Message):
    """Expresses a Novation 'End' SysEx message."""

    name: str = "END"
    identifier: bytes = bytearray([0x00, 0x73])

    # A mapping of the field name to its format string. These MUST be in the order.
    fields: Dict[str, str] = {
        "chunk": "37s",
    }
