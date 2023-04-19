"""SysEx specific constants."""

# Per Table VII of "The Complete MIDI 1.0 Detailed Specification" v96.1 (third edition).
MIDI_SYSEX_SOX = 0xF0
MIDI_SYSEX_EOX = 0xF7

# Well known manufacturer identifiers.
MIDI_SYSEX_MANUFACTURER_IDS = {
    "Novation": bytearray([0x20, 0x29]),
}
