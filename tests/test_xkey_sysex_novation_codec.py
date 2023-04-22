"""Implements tests for Novation SysEx codecs."""

import unittest

from xkey.sysex.novation import codec


class xKeySysExNovationCodecTestCase(unittest.TestCase):
    """Implements tests for Novation SysEx codecs."""

    def setUp(self):
        """Operations to perform before a test case is run."""
        pass

    def tearDown(self):
        """Operations to perform after a test case has run."""

    def test_bytes_to_nibbles(self):
        """Ensure bytes are properly encoded to "split nibbles"."""
        candidate = bytearray([0x00, 0x01, 0x7A, 0x14])
        expected = bytearray([0x00, 0x00, 0x00, 0x01, 0x07, 0x0A, 0x01, 0x04])

        self.assertEqual(codec.bytes_to_nibbles(candidate), expected)

    def test_nibbles_to_bytes(self):
        """Ensures "split nibbles" are properly decoded into bytes."""
        candidate = bytearray([0x00, 0x00, 0x00, 0x01, 0x07, 0x0A, 0x01, 0x04])
        expected = bytearray([0x00, 0x01, 0x7A, 0x14])

        self.assertEqual(codec.nibbles_to_bytes(candidate), expected)
