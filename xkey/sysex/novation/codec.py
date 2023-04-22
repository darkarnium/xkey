"""Encoding and decoding functions for Novation SysEx messages."""

from ctypes import c_int8, c_uint8

from xkey.sysex.novation.constant import CRC32_POLY


def crc32(buffer: bytearray, crc: int = 0xFFFFFFFF) -> int:
    """CRC32 implementation with ITU V.42 Poly.

    Adapted from Mark Adler's implementation via https://stackoverflow.com/a/69340177

    :param buffer: The input buffer to calculate the CRC for.
    :param crc: The CRC initial value (default: 0xFFFFFFFF).

    :return: The calculated CRC for the input buffer.
    """
    for byte in buffer:
        crc ^= byte << 24
        for _ in range(8):
            crc = crc << 1 if (crc & 0x80000000) == 0 else (crc << 1) ^ CRC32_POLY

    return crc


def bytes_to_nibbles(buffer: bytearray) -> bytearray:
    """Encodes bytes into "split nibbles".

    This result of this function is an output bytearray which is double the size of the
    input. This is due to the high and low nibbles of a single byte being encoded into
    TWO bytes, preventing the need for the use of bits unavailable in 7-bit bytes.

    :param buffer: The input buffer to encode into "split nibbles".

    :return: The encoded contents of the input buffer.
    """
    output = bytearray()

    for index in range(0, len(buffer)):
        hi = c_uint8(buffer[index] >> 4).value
        lo = c_uint8(buffer[index] & 0xF).value

        output.extend([hi, lo])

    return output


def nibbles_to_bytes(buffer: bytearray) -> bytearray:
    """Decodes "split nibbles" into bytes.

    This result of this function is an output bytearray which is half the size of the
    input. This is due to the high and low nibbles of a single byte being encoded into
    TWO bytes, preventing the need for the use of bits unavailable in 7-bit bytes.

    :param buffer: The input buffer to decode into bytes.

    :return: The decoded contents of the input buffer.
    """
    output = bytearray()

    # Shift the Nth byte by 4-bits to represent the high nibbles, and OR with the
    # subsequent byte to yield the full value of the byte.
    for index in range(0, len(buffer), 2):
        hi = c_uint8(buffer[index] << 4).value
        lo = c_uint8(buffer[index + 1]).value
        byte = hi | lo

        output.append(byte)

    return output


def decoder(buffer: bytearray) -> bytearray:
    """Decode the input buffer from 7-bit Novation compatible SysEx.

    :param buffer: The input buffer to decode from 7-bit Novation compatible SysEx into
        regular 8-bit bytes.

    :return: The decoded contents of the input buffer.
    """
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


def encoder(buffer: bytearray) -> bytearray:
    """Encode the input buffer into 7-bit Novation compatible SysEx.

    :param buffer: The input buffer to encode into 7-bit Novation compatible SysEx from
        regular 8-bit bytes.

    :return: The encoded contents of the input buffer.
    """
    last = 0x0
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
