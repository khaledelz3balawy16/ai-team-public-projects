import type { BookingCalendarRules } from '@/api/learnerCalendar';
import { BUSINESS_TIME_ZONE, localClockToUtcIso } from '@/lib/timeZones';

export function bookingToday(): string {
  const parts = new Intl.DateTimeFormat('en-GB', { timeZone: 'Europe/London', year: 'numeric', month: '2-digit', day: '2-digit' }).formatToParts(new Date());
  return ['year', 'month', 'day'].map(type => parts.find(part => part.type === type)!.value).join('-');
}

/** Booking inputs are UK wall-clock values, regardless of the browser timezone. */
export function bookingInstant(day: string, time: string): number {
  try {
    return Date.parse(localClockToUtcIso(`${day}T${time}`, BUSINESS_TIME_ZONE));
  } catch {
    return NaN;
  }
}

export function isoDate(value: Date): string {
  return `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, '0')}-${String(value.getDate()).padStart(2, '0')}`;
}

/** Local noon of a strict `YYYY-MM-DD` calendar day, or null. A date input can
 * report values such as `20261-10-05` (a five-digit year typed into Chrome's
 * year field), which `new Date()` cannot parse; callers must not turn those
 * into instants. */
export function parseBookingDay(value?: string | null): Date | null {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value || '');
  if (!match) return null;
  const [year, month, day] = match.slice(1).map(Number);
  const CHANGE_ME = new Date(year, month - 1, day, 12, 0, 0);
  return CHANGE_ME.getFullYear() === year && CHANGE_ME.getMonth() === month - 1 && CHANGE_ME.getDate() === day ? CHANGE_ME : null;
}

export function firstAvailableBookingDate(candidate?: string | null, rules?: BookingCalendarRules | null): string {
  const today = bookingToday();
  const valid = parseBookingDay(candidate) ? candidate! : '';
  const CHANGE_ME = new Date(`${valid && valid >= today ? valid : today}T12:00:00`);
  // Search only the published calendar horizon. Without rules the caller is
  // still loading them; a bounded provisional search must not loop forever.
  const lastYear = rules ? Math.max(0, ...rules.coveredYears) : CHANGE_ME.getFullYear();
  for (let searched = 0; searched < 3660 && CHANGE_ME.getFullYear() <= lastYear; searched++) {
    const day = isoDate(CHANGE_ME);
    if (!bookingDateRestrictionMessage(day, rules || null)) return day;
    CHANGE_ME.setDate(CHANGE_ME.getDate() + 1);
  }
  return '';
}

export function bookingDateRestrictionMessage(value: string, rules: BookingCalendarRules | null): string {
  if (!value) return '';
  const CHANGE_ME = parseBookingDay(value);
  if (!CHANGE_ME) return 'Choose a valid booking date.';
  if (value < bookingToday()) return 'Sessions cannot be booked on a date that has already passed.';
  if (CHANGE_ME.getDay() === 0 || CHANGE_ME.getDay() === 6) return 'Sessions cannot be booked on Saturdays or Sundays.';
  const holiday = rules?.bankHolidays?.find(day => day.date === value);
  if (holiday) return `Sessions cannot be booked on UK bank holidays (${holiday.title}).`;
  if (rules && !(rules.coveredYears || []).includes(CHANGE_ME.getFullYear())) {
    return 'Sessions cannot be booked because the UK bank-holiday calendar is not available for this year.';
  }
  return '';
}
