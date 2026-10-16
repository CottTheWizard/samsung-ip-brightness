from datetime import datetime
import unittest
from daily_schedule import parse_schedule, current_slot, ScheduleState


class ScheduleTests(unittest.TestCase):
    def setUp(self):
        self.entries = parse_schedule('20:00=15\n08:00=30\n23:00=5')

    def test_parse_sorted(self):
        self.assertEqual([e['time'] for e in self.entries], ['08:00', '20:00', '23:00'])

    def test_invalid_entries(self):
        for text in ('', '24:00=5', '08:60=5', '8:00=5', '08:00=51', '08:00=-1',
                     '08:00=20\n08:00=30', 'abc', '08:00=1.5'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_schedule(text)

    def test_midnight_uses_previous_day(self):
        key, value = current_slot(self.entries, datetime(2026, 10, 17, 1))
        self.assertEqual(key, '2026-10-16T23:00:00')
        self.assertEqual(value, 5)

    def test_exact_boundary_and_resume(self):
        self.assertEqual(current_slot(self.entries, datetime(2026, 10, 17, 20))[1], 15)
        self.assertEqual(current_slot(self.entries, datetime(2026, 10, 17, 22, 59))[1], 15)

    def test_manual_override_preserved_until_next_slot(self):
        state = ScheduleState()
        key, value = state.due(self.entries, datetime(2026, 10, 17, 10), 0)
        self.assertEqual(value, 30)
        state.finish(key, True)
        self.assertIsNone(state.due(self.entries, datetime(2026, 10, 17, 11), 5000))
        self.assertEqual(state.due(self.entries, datetime(2026, 10, 17, 20), 6000)[1], 15)

    def test_pending_and_retry(self):
        state = ScheduleState()
        now = datetime(2026, 10, 17, 10)
        key, _ = state.due(self.entries, now, 0)
        self.assertIsNone(state.due(self.entries, now, 100))
        state.finish(key, False)
        self.assertIsNone(state.due(self.entries, now, 59))
        self.assertIsNotNone(state.due(self.entries, now, 60))

    def test_next_day_and_reset(self):
        state = ScheduleState()
        key, _ = state.due(self.entries, datetime(2026, 10, 17, 10), 0)
        state.finish(key, True)
        self.assertIsNotNone(state.due(self.entries, datetime(2026, 10, 18, 10), 86400))
        state.reset()
        self.assertIsNotNone(state.due(self.entries, datetime(2026, 10, 18, 10), 86401))
