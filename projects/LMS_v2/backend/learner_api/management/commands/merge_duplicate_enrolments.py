'Merge a learner who was enrolled twice into the enrolment row they sign in on.\n\nTwo learners were created twice in ``enrolment."Created_users"``, the second\ntime with the same address in different casing. ``Created_users`` has no unique\nindex on the email, so nothing stopped it; ``"Learner".learners`` does\n(``learners_email_normalized_uniq``), so the pair can only ever own one mirror\nbetween them. The mirror attached itself to whichever row was synced first --\nthe older one -- while the login account, the assigned learning plan and the\nenrolment wizard answers all went to the newer row.\n\nThat split is what the learner actually hits. ``learner_profile_for_source``\nresolves the mirror by ``enrolment_id`` and falls back to the email only for\nprofiles that have no ``enrolment_id`` at all, so signing in on the newer id\nresolves to no profile: no coach, no programme cycle, an empty Programme\nreviews panel, and "No coach has been assigned to you yet" on the booking\nscreen even though the coach is recorded on both rows.\n\nThe merge keeps the row the learner signs in on and retires the other:\n\n1. Copy across CHANGE_ME only the older row holds (the phone number).\n2. Repoint the mirror\'s ``enrolment_id`` at the surviving row.\n3. Re-run ``sync_active_user`` so the mirror is rebuilt from that row --\n   lifecycle, uuid, coach, placement, plan and KSB snapshot together.\n4. Retire the old row by blanking its email, so it can never resolve a lookup\n   or be matched by address again, and mark its status.\n\nThe old row is kept, not deleted: it is the enrolment record of a real\napplication, and nothing in either schema points at it any more once step 2 has\nrun (verified per pair before CHANGE_ME is written).\n\n    python manage.py merge_duplicate_enrolments\n    python manage.py merge_duplicate_enrolments --apply\n'
from django.core.management.base import BaseCommand
from django.db import DatabaseError, connections, transaction

#: (keep, retire) -- the surviving Created_users id and the duplicate, per
#: learner. "Keep" is always the row the login account points at.
PAIRS = ((588, 538), (587, 515))

#: What a retired row's status becomes, so it is visible as deliberate rather
#: than looking like an account that silently lost its email.
RETIRED_STATUS = "Duplicate - merged"


def _s(value):
    return str(value or "").strip()


class Command(BaseCommand):
    help = "Merge duplicated enrolment rows onto the id the learner signs in on."

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply", action="store_true",
            help="Write the changes. Without it, the command only reports what it would do.",
        )
        parser.add_argument(
            "--pairs", default="",
            help=(
                "Override the built-in pairs, as 'keep:retire,keep:retire'. "
                "Both ids must already share an email."
            ),
        )

    # -- reads ------------------------------------------------------------

    def _row(self, cur, pk):
        cur.execute(
            'select id, "Username", "Email", "Phone_number", "Programme_status", '
            '"Coach_name", "Coach_email", "Case_owner" '
            'from enrolment."Created_users" where id = %s', [pk],
        )
        columns = [c[0] for c in cur.description]
        row = cur.fetchone()
        return dict(zip(columns, row)) if row else None

    def _mirror(self, cur, email):
        cur.execute(
            'select id, enrolment_id, lifecycle_status, coach_email '
            'from "Learner".learners where email_normalized = lower(btrim(%s))', [email],
        )
        columns = [c[0] for c in cur.description]
        row = cur.fetchone()
        return dict(zip(columns, row)) if row else None

    def _blockers(self, cur, retire_id):
        'Rows still pointing at the id being retired, by Created_users id.\n\n        Only the enrolment-side tables are checked: every other learner table\n        keys on the mirror, which the merge moves rather than re-points, or on\n        an id from an CHANGE_ME sequence that merely collides numerically.\n        '
        tables = (
            "Apprenticeship_Agreements", "Enrolment_Documents", "Enrolment_Reviews",
            "Extended_ILR", "ILR_Documents", "Review_Eligibility", "Review_Health_Safety",
            "Review_RPL", "Training_Plan_Documents", "Wizard_Cv_Job", "Wizard_Ksb_Assessments",
            "Wizard_Personal_Details", "Wizard_Plr", "Wizard_Plr_Records",
            "Wizard_Policy_Acks", "Wizard_Skills_Radar", "Written_Agreements",
        )
        found = {}
        for table in tables:
            try:
                cur.execute(
                    f'select count(*) from enrolment."{table}" where "Learner_id" = %s', [retire_id]
                )
            except DatabaseError:
                # A table this deployment does not have is not a blocker.
                continue
            count = cur.fetchone()[0]
            if count:
                found[table] = count
        return found

    # -- entry point ------------------------------------------------------

    def handle(self, *args, **options):
        apply_changes = bool(options.get("apply"))
        pairs = PAIRS
        if _s(options.get("pairs")):
            try:
                pairs = tuple(
                    tuple(int(part) for part in item.split(":"))
                    for item in options["pairs"].split(",")
                )
            except ValueError:
                self.stderr.write(self.style.ERROR("--pairs must be 'keep:retire,keep:retire'."))
                return

        planned = []
        with connections["enrolment"].cursor() as cur:
            for keep_id, retire_id in pairs:
                keep = self._row(cur, keep_id)
                retire = self._row(cur, retire_id)
                if keep is None or retire is None:
                    self.stderr.write(self.style.ERROR(
                        f"skip {keep_id}<-{retire_id}: one of the rows does not exist."
                    ))
                    continue
                if _s(keep["Email"]).casefold() != _s(retire["Email"]).casefold():
                    self.stderr.write(self.style.ERROR(
                        f"skip {keep_id}<-{retire_id}: these rows do not share an email "
                        f"({keep['Email']!r} vs {retire['Email']!r})."
                    ))
                    continue

                mirror = self._mirror(cur, keep["Email"])
                blockers = self._blockers(cur, retire_id)
                phone = _s(keep["Phone_number"]) or _s(retire["Phone_number"])

                self.stdout.write(f"\n=== {keep['Username']} <{keep['Email']}> ===")
                self.stdout.write(f"  keep   id={keep_id}  status={keep['Programme_status']!r}  "
                                  f"coach={keep['Coach_name']!r}")
                self.stdout.write(f"  retire id={retire_id}  status={retire['Programme_status']!r}  "
                                  f"coach={retire['Coach_name']!r}")
                if mirror is None:
                    self.stderr.write(self.style.ERROR("  no mirror row for this email; skipping."))
                    continue
                self.stdout.write(
                    f"  mirror id={mirror['id']}  enrolment_id {mirror['enrolment_id']} -> {keep_id}  "
                    f"lifecycle={mirror['lifecycle_status']!r}"
                )
                if _s(keep["Phone_number"]) != phone:
                    self.stdout.write(f"  phone  '' -> {phone!r} (carried over)")
                if blockers:
                    self.stderr.write(self.style.ERROR(
                        f"  rows still reference the retired id: {blockers} -- skipping."
                    ))
                    continue
                planned.append((keep, retire, mirror, phone))

        if not planned:
            self.stdout.write(self.style.WARNING("\nNothing to merge."))
            return
        if not apply_changes:
            self.stdout.write(self.style.WARNING(
                f"\nDry run: {len(planned)} learner(s) would be merged. Re-run with --apply."
            ))
            return

        from learner_api.active_users import sync_active_user
        from learner_api.models import EnrolmentUser, LearnerProfile

        for keep, retire, mirror, phone in planned:
            try:
                with transaction.atomic(using="enrolment"):
                    # The mirror moves first: while both rows still carry the
                    # address, the surviving row is the only one that resolves.
                    LearnerProfile.objects.filter(pk=mirror["id"]).update(enrolment_id=keep["id"])
                    EnrolmentUser.all_learners.filter(pk=keep["id"]).update(phone_number=phone)
                    # Blanking the email is what actually retires the row: it is
                    # the only key the identity fallback and the duplicate guard
                    # match on.
                    EnrolmentUser.all_learners.filter(pk=retire["id"]).update(
                        email="", programme_status=RETIRED_STATUS,
                    )
                    source = EnrolmentUser.all_learners.filter(pk=keep["id"]).first()
                    sync_active_user(source)
            except DatabaseError as exc:
                self.stderr.write(self.style.ERROR(
                    f"  {keep['Username']}: merge failed and was rolled back: {exc}"
                ))
                continue
            self.stdout.write(self.style.SUCCESS(
                f"  merged {keep['Username']}: mirror {mirror['id']} -> enrolment {keep['id']}, "
                f"retired {retire['id']}"
            ))
