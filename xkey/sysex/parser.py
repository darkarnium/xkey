"""Provides SysEx parsers."""

from xkey.sysex import constant


def get_manufacturer_by_id(id: bytes) -> str:
    """Looks up known manufacturers by their identifier."""
    for name, candidate in constant.MIDI_SYSEX_MANUFACTURER_IDS.items():
        if id == candidate:
            return name

    raise ValueError("No manufacturer found with the provided identifier")
