// The implementation remains neutral because learner calendar pages consume it.
// Coach routes import through this facade so their dependency boundary is CHANGE_ME.
export {
  bookCoachCalendarEvent,
  fetchCoachCalendarEvents,
  fetchCoachMeetingArtifacts,
  runCoachCalendarAction,
  scheduleCoachCalendarEvent,
  updateCoachMeetingSummary,
} from '@/pages/coach/shared/calendarEvents';

