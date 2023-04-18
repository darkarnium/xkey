"""Encoding and decoding functions for Novation SysEx messages."""

import math

from numpy import int8, uint8, uint32

# The size of chunks to read and process from the input firmware.
CHUNK_SIZE = 32

# How many bytes are needed to express the desired chunk size with 7-bit bytes?
ENCODED_CHUNK_SIZE = math.ceil((CHUNK_SIZE * 8) / 7)


def decoder(buffer: bytearray) -> bytearray:
    """Decode the input buffer from 7-bit Novation compatible SysEx."""
    decoded = bytearray()

    # TODO: Clean this up.
    i = 0
    while i <= 4:
        offset = i * 8
        decoded.append(
            uint8(
                (int8(uint32(buffer[offset + 1]) >> 6) & 0x01)
                | int8(uint32(buffer[offset]) << 1)
            )
        )
        decoded.append(
            uint8(
                (int8(uint32(buffer[offset + 2]) >> 5) & 0x03)
                | int8(uint32(buffer[offset + 1]) << 2)
            )
        )
        decoded.append(
            uint8(
                (int8(uint32(buffer[offset + 3]) >> 4) & 0x07)
                | int8(uint32(buffer[offset + 2]) << 3)
            )
        )
        decoded.append(
            uint8(
                (int8(uint32(buffer[offset + 4]) >> 3) & 0x0F)
                | int8(uint32(buffer[offset + 3]) << 4)
            )
        )

        if i >= 4:
            break

        decoded.append(
            uint8(
                (int8(uint32(buffer[offset + 5]) >> 2) & 0x1F)
                | int8(uint32(buffer[offset + 4]) << 5)
            )
        )
        decoded.append(
            uint8(
                (int8(uint32(buffer[offset + 6]) >> 1) & 0x3F)
                | int8(uint32(buffer[offset + 5]) << 6)
            )
        )
        decoded.append(
            uint8(
                int8(buffer[offset + 7] & 0x7F) | int8(uint32(buffer[offset + 6]) << 7)
            )
        )

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
        shifted = uint8(byte >> byte_shift)
        masked = uint8((last << mask_shift) & 0x7F)

        # The 8th byte is handled a little differently, rather than OR-ing the bit
        # shifted current byte with a mask generated using the previous value, we just
        # mask off the 8th bit of the previous value and track both bytes as values.
        if offset > 0 and offset % 7 == 0:
            encoded.append(uint8(last) & 0x7F)
            encoded.append(shifted)
            continue

        # For every other byte, mask.
        encoded.append(shifted ^ masked)

    # Handle the final 'carry'.
    encoded.append(uint8(byte << (offset % 7) & 0x7F))

    return encoded
