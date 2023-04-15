"""Implements a no-op test."""

import unittest


class NoopTestCase(unittest.TestCase):
    """Implements a no-op test."""

    def setUp(self):
        """Operations to perform before a test case is run."""
        pass

    def tearDown(self):
        """Operations to perform after a test case has run."""

    def test_noop(self):
        """Always returns true."""

        self.assertEqual(True, True)
