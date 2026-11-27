'Regression (#13): the coach timetable must not drop in-window live sessions.\n\n``collect_live_session_events`` defaults to ``include_past=False`` so the\nwindowless, forward-looking coach timetable only shows today+future lectures.\nBut when a caller supplies an CHANGE_ME date window (the all-coaches week grid,\nor any narrowed range), that window is the intended bound -- the extra\n"before today" guard silently hides sessions already delivered earlier in the\nrequested range. ``collect_generated_timetable`` must therefore forward\n``include_past=True`` only when a window is supplied, and keep the\nforward-looking default otherwise.\n\nPure unit test: every database-backed dependency of\n``collect_generated_timetable`` is patched out, so this runs under the no-DB\nSimpleTestCase suite.\n'
from datetime import date
from unittest.mock import patch

from django.test import SimpleTestCase

from coach_api import views


EMPTY_RESOLVED = {
    "events": [],
    "reviewGenerationIssues": [],
    "aptemProfileIds": set(),
    "sourceCounts": {
        "progressReviewRows": 0, "mcrRows": 0, "reviewRows": 0,
        "learnersWithDates": 0, "reviewAnchorSkipped": 0,
        "reviewAnchorSkipReasons": {}, "aptemReviewRows": 0,
        "curriculumReviewRows": 0, "aptemLearners": 0, "curriculumLearners": 0,
    },
}


class TimetableLiveSessionWindowTests(SimpleTestCase):
    @patch("coach_api.views.build_timetable_summary", return_value={"sourceCounts": {}})
    @patch("coach_api.views.assign_timetable_slots", side_effect=lambda events: events)
    @patch("coach_api.views.curriculum_review_instances.reconcile_review_event_keys", return_value={})
    @patch("coach_api.views.fetch_calendar_event_records", return_value={})
    @patch("coach_api.views.fetch_standalone_event_records", return_value=[])
    @patch("coach_api.views.resolve_coach_review_events", return_value=EMPTY_RESOLVED)
    @patch("coach_api.views.fetch_caseload_timetable_profiles", return_value=[])
    @patch("coach_api.views.fetch_owner_active_learner_profiles", return_value=[])
    @patch("coach_api.views.coach_staff_display_name", return_value="Coach")
    @patch("coach_api.views.collect_live_session_events", return_value=[])
    def test_windowed_call_includes_past_live_sessions(self, live_sessions, *_mocks):
        views.collect_generated_timetable(
            "coach@example.invalid",
            start_date=date(2026, 9, 1),
            end_date=date(2026, 9, 30),
            include_scheduler_queues=False,
        )
        self.assertTrue(live_sessions.called)
        self.assertIs(live_sessions.call_args.kwargs.get("include_past"), True)

    @patch("coach_api.views.build_timetable_summary", return_value={"sourceCounts": {}})
    @patch("coach_api.views.assign_timetable_slots", side_effect=lambda events: events)
    @patch("coach_api.views.curriculum_review_instances.reconcile_review_event_keys", return_value={})
    @patch("coach_api.views.fetch_calendar_event_records", return_value={})
    @patch("coach_api.views.fetch_standalone_event_records", return_value=[])
    @patch("coach_api.views.resolve_coach_review_events", return_value=EMPTY_RESOLVED)
    @patch("coach_api.views.fetch_caseload_timetable_profiles", return_value=[])
    @patch("coach_api.views.fetch_owner_active_learner_profiles", return_value=[])
    @patch("coach_api.views.coach_staff_display_name", return_value="Coach")
    @patch("coach_api.views.collect_live_session_events", return_value=[])
    def test_windowless_call_stays_forward_looking(self, live_sessions, *_mocks):
        views.collect_generated_timetable(
            "coach@example.invalid",
            include_scheduler_queues=False,
        )
        self.assertTrue(live_sessions.called)
        self.assertIsNot(live_sessions.call_args.kwargs.get("include_past"), True)
