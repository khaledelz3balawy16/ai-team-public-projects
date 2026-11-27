from django.test import SimpleTestCase, override_settings

from .coach_booking import COACH_BOOKINGS, booking_url


class CoachBookingTests(SimpleTestCase):
    @override_settings(OLD_OTJH_COACH_BOOKING_URLS={})
    def test_bundled_links_work_without_deployment_configuration(self):
        self.assertEqual(len(COACH_BOOKINGS), 13)
        self.assertEqual(len({coach['email'] for coach in COACH_BOOKINGS}), 13)
        for coach in COACH_BOOKINGS:
            with self.subTest(coach=coach['slug']):
                self.assertEqual(booking_url(f" {coach['email'].upper()} "), coach['booking_page_url'])
        self.assertEqual(booking_url('contact+72398d95e84c@example.com'),
                         'https://kentbusinesscollege.com/coach-adey/')
        self.assertEqual(booking_url('contact+8982bc9dfbfe@example.com'),
                         'https://kentbusinesscollege.com/coach-omar-badr/')
        self.assertEqual(booking_url('contact+d9c4db65fc4f@example.com'),
                         'https://kentbusinesscollege.com/coach-omar-elshafey/')
        self.assertIsNone(booking_url('contact+9a587b4d99d6@example.com'))

    @override_settings(OLD_OTJH_COACH_BOOKING_URLS={
        'contact+b23cce919b15@example.com': 'https://example.org/new-booking',
        'contact+22b187d97ef2@example.com': None,
    })
    def test_override_can_replace_or_disable_one_link_without_affecting_others(self):
        self.assertEqual(booking_url('contact+b23cce919b15@example.com'), 'https://example.org/new-booking')
        self.assertIsNone(booking_url('contact+22b187d97ef2@example.com'))
        self.assertEqual(booking_url('contact+37c9538dcddd@example.com'),
                         'https://kentbusinesscollege.com/coach-afaan/')

    @override_settings(OLD_OTJH_COACH_BOOKING_URLS='{" Coach@Example.org ": "https://example.org/book/coach"}')
    def test_matches_only_assigned_email_ignoring_case_and_whitespace(self):
        self.assertEqual(booking_url(' COACH@example.org '), 'https://example.org/book/coach')
        self.assertIsNone(booking_url('other@example.org'))
        self.assertIsNone(booking_url(None))

    def test_invalid_configuration_keeps_contact_fallback_available(self):
        for configuration in ['invalid JSON', '[]', 'null', {}, {'coach@example.org': 42}]:
            with self.subTest(configuration=configuration), override_settings(OLD_OTJH_COACH_BOOKING_URLS=configuration):
                self.assertIsNone(booking_url('coach@example.org'))

    def test_rejects_unsafe_or_malformed_urls(self):
        for url in ['javascript:alert(1)', '//example.org/book', '/book',
                    'https://CHANGE_ME@example.org', 'https://',
                    'https://example.org:invalid', 'https://example.org/\nbook',
                    'https://example.org\\@other.example.org']:
            with self.subTest(url=url), override_settings(OLD_OTJH_COACH_BOOKING_URLS={'coach@example.org': url}):
                self.assertIsNone(booking_url('coach@example.org'))

    @override_settings(OLD_OTJH_COACH_BOOKING_URLS={
        'coach@example.org': 'https://example.org/first',
        ' COACH@example.org ': 'https://example.org/second',
    })
    def test_ambiguous_assignment_never_picks_an_arbitrary_link(self):
        self.assertIsNone(booking_url('coach@example.org'))
