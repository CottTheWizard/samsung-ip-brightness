import unittest
from windows_tray import accumulate_wheel


class WheelTests(unittest.TestCase):
    def test_notches_both_directions(self):
        self.assertEqual(accumulate_wheel(120), (1, 0))
        self.assertEqual(accumulate_wheel(-120), (-1, 0))
        self.assertEqual(accumulate_wheel(360), (3, 0))

    def test_high_resolution_accumulates(self):
        steps, remainder = accumulate_wheel(40)
        self.assertEqual((steps, remainder), (0, 40))
        self.assertEqual(accumulate_wheel(80, remainder), (1, 0))
        self.assertEqual(accumulate_wheel(-150), (-1, -30))

    def test_reverse_direction_cancels_partial_notch(self):
        self.assertEqual(accumulate_wheel(-60, 60), (0, 0))
        self.assertEqual(accumulate_wheel(-180, 60), (-1, 0))
