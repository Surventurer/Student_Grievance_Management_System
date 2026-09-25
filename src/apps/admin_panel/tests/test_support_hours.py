from django.test import TestCase
from datetime import datetime
from apps.admin_panel.support_hours import is_within_support_hours


class SupportHoursTest(TestCase):
    def test_24_7_keywords(self):
        # 24/7 should always be active regardless of day/time
        dt = datetime(2026, 9, 27, 3, 30)  # Sunday 3:30 AM
        for kw in ['24/7', 'always', '24x7', 'Anytime', 'All Day']:
            active, msg = is_within_support_hours(kw, dt)
            self.assertTrue(active)
            self.assertIn("24/7", msg)

    def test_empty_string_defaults_to_24_7(self):
        dt = datetime(2026, 9, 27, 3, 30)
        active, msg = is_within_support_hours("", dt)
        self.assertTrue(active)

    def test_standard_weekday_schedule_during_hours(self):
        schedule = "Mon-Fri, 9:00 AM - 5:00 PM"
        # Wednesday at 2:00 PM
        wed_2pm = datetime(2026, 9, 23, 14, 0)
        active, msg = is_within_support_hours(schedule, wed_2pm)
        self.assertTrue(active)
        self.assertEqual(msg, "Within support hours.")

    def test_standard_weekday_schedule_outside_hours(self):
        schedule = "Mon-Fri, 9:00 AM - 5:00 PM"
        # Wednesday at 8:00 PM
        wed_8pm = datetime(2026, 9, 23, 20, 0)
        active, msg = is_within_support_hours(schedule, wed_8pm)
        self.assertFalse(active)
        self.assertIn("Support hours are currently closed", msg)

    def test_standard_weekday_schedule_on_weekend(self):
        schedule = "Mon-Fri, 9:00 AM - 5:00 PM"
        # Saturday at 11:00 AM
        sat_11am = datetime(2026, 9, 26, 11, 0)
        active, msg = is_within_support_hours(schedule, sat_11am)
        self.assertFalse(active)
        self.assertIn("Support is inactive on Saturday", msg)

    def test_overnight_schedule(self):
        schedule = "Mon-Fri, 10:00 PM - 6:00 AM"
        # Tuesday 11:00 PM (active)
        tue_11pm = datetime(2026, 9, 22, 23, 0)
        active, _ = is_within_support_hours(schedule, tue_11pm)
        self.assertTrue(active)

        # Tuesday 3:00 AM (active)
        tue_3am = datetime(2026, 9, 22, 3, 0)
        active, _ = is_within_support_hours(schedule, tue_3am)
        self.assertTrue(active)

        # Tuesday 12:00 PM noon (closed)
        tue_noon = datetime(2026, 9, 22, 12, 0)
        active, msg = is_within_support_hours(schedule, tue_noon)
        self.assertFalse(active)
