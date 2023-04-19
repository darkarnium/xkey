"""Encoding and decoding functions for Novation SysEx messages."""

from ctypes import c_int8, c_uint8


def decoder(buffer: bytearray) -> bytearray:
    """Decode the input buffer from 7-bit Novation compatible SysEx."""
    decoded = bytearray()

    for start in range(0, len(buffer) - 1, 8):
        for index in range(0, 7):
            offset = start + index

            # The final round isn't complete, so break early.
            if (offset + 1) >= len(buffer):
                break

            # Track the current and next byte for simplicity during future operations.
            byte = buffer[offset]
            next_ = buffer[offset + 1]

            # Generate shift amounts.
            byte_shift = (index % 7) + 1
            mask_shift = 6 - (index % 7)

            # Shift.
            masked = (
                c_int8(next_ >> mask_shift).value & c_uint8(0x7F >> mask_shift).value
            )
            shifted = c_int8(byte << byte_shift).value

            # Track the decoded byte.
            decoded.append(c_uint8(shifted | masked).value)

    return decoded


def encoder(buffer: bytearray, last: bytes = 0x0) -> bytearray:
    """Encode the input buffer into 7-bit Novation compatible SysEx."""
    byte = last
    encoded = bytearray()

    for offset in range(len(buffer)):
        # Track the last and current byte for simplicity during future operations.
        last = byte
        byte = buffer[offset]

        # Generate shift amounts.
        byte_shift = (offset % 7) + 1
        mask_shift = 7 - (offset % 7)

        # Shift.
        shifted = c_uint8(byte >> byte_shift).value
        masked = c_uint8(last << mask_shift).value & 0x7F

        # The 8th byte is handled a little differently, rather than OR-ing the bit
        # shifted current byte with a mask generated using the previous value, we just
        # mask off the 8th bit of the previous value and track both bytes as values.
        if offset > 0 and offset % 7 == 0:
            encoded.append(c_uint8(last).value & 0x7F)
            encoded.append(shifted)
            continue

        # For every other byte, mask.
        encoded.append(shifted ^ masked)

    # Handle the final 'carry'.
    encoded.append(c_uint8(byte << (offset % 7)).value & 0x7F)

    return encoded
