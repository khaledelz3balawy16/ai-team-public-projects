from django.core.management.base import BaseCommand
from django.db.models import Q

from pmp_assessment.models import PMPQuestion

EXHIBIT_QUESTION_LINKS = {
    "SC-027": ("scope/sc-027.png", "Burndown chart exhibit for scope question SC-027."),
    "AG-001": ("schedule/ag-001.png", "Agile chart exhibit for schedule question AG-001."),
    "AG-014": ("schedule/ag-014.png", "Agile chart exhibit for schedule question AG-014."),
    "AG-042": ("schedule/ag-042.png", "Agile chart exhibit for schedule question AG-042."),
    "SCH-003": ("schedule/sch-003.png", "Schedule chart exhibit for question SCH-003."),
    "SCH-009": ("schedule/sch-009.png", "Schedule chart exhibit for question SCH-009."),
    "SCH-045": ("schedule/sch-045.png", "Schedule chart exhibit for question SCH-045."),
    "RSK-011": ("risk/rsk-011.png", "Risk chart exhibit for question RSK-011."),
    "CH1-Q39": ("finance/ch1-q39.png", "Cost of change curve exhibit for finance question CH1-Q39."),
    "BE-041": ("finance/be-041.png", "Business environment chart exhibit for question BE-041."),
}

DUPLICATE_VISUAL_IDS = {"SCH-004": "SC-027"}


class Command(BaseCommand):
    help = "Link existing PMP question rows to canonical exhibit blob names by question/source item ID."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="Persist exhibit_blob_name and exhibit_alt_text updates. Default is dry-run.")

    def handle(self, *args, **options):
        apply_changes = options["apply"]
        linked = 0
        missing = []
        duplicates = []
        for item_id, (blob_name, alt_text) in EXHIBIT_QUESTION_LINKS.items():
            qs = PMPQuestion.objects.filter(Q(question_id__iexact=item_id) | Q(source_item_id__iexact=item_id)).order_by("id")
            active_unique = qs.filter(is_active=True, duplicate_of__isnull=True)
            if not active_unique.exists():
                missing.append(item_id)
                continue
            if active_unique.count() > 1:
                duplicates.append(f"{item_id}: {active_unique.count()} rows")
            for question in active_unique:
                linked += 1
                self.stdout.write(f"{'LINK' if apply_changes else 'WOULD LINK'} {item_id} -> question {question.id} -> {blob_name}")
                if apply_changes:
                    question.exhibit_blob_name = blob_name
                    question.exhibit_alt_text = question.exhibit_alt_text or alt_text
                    question.save(update_fields=["exhibit_blob_name", "exhibit_alt_text", "updated_at"])

        sch4 = PMPQuestion.objects.filter(Q(question_id__iexact="SCH-004") | Q(source_item_id__iexact="SCH-004"), is_active=True, duplicate_of__isnull=True).count()
        if sch4:
            duplicates.append(f"SCH-004 remains active ({sch4} row(s)); expected duplicate of {DUPLICATE_VISUAL_IDS['SCH-004']} and no separate asset.")

        self.stdout.write(self.style.SUCCESS(f"{'Linked' if apply_changes else 'Dry-run matched'} {linked} question row(s)."))
        if missing:
            self.stdout.write(self.style.WARNING("Missing question rows for: " + ", ".join(missing)))
        if duplicates:
            self.stdout.write(self.style.WARNING("Review duplicates: " + "; ".join(duplicates)))
