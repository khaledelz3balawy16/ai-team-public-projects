import csv
import re
from datetime import datetime
from io import StringIO
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from psycho.models import SelfAssessmentQuestion


OPTION_RE = re.compile(r"^\s*([A-E])\)\s*(.*?)\s*\((\d+)\)\s*$")


def parse_datetime(value):
    raw = (value or "").strip()
    if not raw:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return timezone.make_aware(datetime.strptime(raw, fmt), timezone.get_current_timezone())
        except ValueError:
            continue
    return None


def parse_options(row):
    options = []
    raw_options = (row.get("Options") or "").strip()
    if raw_options:
        for order, part in enumerate(raw_options.split("|"), start=1):
            match = OPTION_RE.match(part.strip())
            if match:
                key, label, score = match.groups()
                options.append({"key": key, "label": label.strip(), "score": int(score), "order": order})
            elif part.strip():
                options.append({"key": chr(64 + order), "label": part.strip(), "score": order, "order": order})
    return options


class Command(BaseCommand):
    help = "Import self-assessment questions from wp_self_assessment_qb.csv."

    def add_arguments(self, parser):
        parser.add_argument("csv_path")
        parser.add_argument("--deactivate-missing", action="store_true")

    def handle(self, *args, **options):
        csv_path = options["csv_path"]
        raw_text = None
        last_error = None

        for encoding in ("utf-8-sig", "cp1252", "latin-1"):
            try:
                raw_text = Path(csv_path).read_text(encoding=encoding)
                break
            except (OSError, UnicodeDecodeError) as exc:
                last_error = exc

        if raw_text is None:
            raise CommandError(f"Could not read CSV file: {last_error}") from last_error

        now = timezone.now()
        seen_keys = set()
        objects = []

        with StringIO(raw_text) as csv_file:
            reader = csv.DictReader(csv_file, delimiter=";")
            required = {"QuestionId", "Question", "assessment_type"}
            missing = required - set(reader.fieldnames or [])
            if missing:
                raise CommandError(f"CSV missing required columns: {', '.join(sorted(missing))}")

            for row in reader:
                question_id = (row.get("QuestionId") or "").strip()
                assessment_type = (row.get("assessment_type") or "").strip()
                question_text = (row.get("Question") or row.get("text") or "").strip()
                if not question_id or not assessment_type or not question_text:
                    continue

                key = (assessment_type.lower(), question_id)
                if key in seen_keys:
                    continue
                seen_keys.add(key)

                objects.append(SelfAssessmentQuestion(
                    question_id=question_id,
                    label=(row.get("Label") or "").strip() or None,
                    assessment_type=assessment_type,
                    question_text=question_text,
                    options=parse_options(row),
                    answer=(row.get("Answer") or "").strip() or None,
                    source_created_at=parse_datetime(row.get("created_at")),
                    is_active=True,
                    created_at=now,
                    updated_at=now,
                ))

        if objects:
            SelfAssessmentQuestion.objects.bulk_create(
                objects,
                batch_size=500,
                update_conflicts=True,
                unique_fields=["assessment_type", "question_id"],
                update_fields=[
                    "label",
                    "question_text",
                    "options",
                    "answer",
                    "source_created_at",
                    "is_active",
                    "updated_at",
                ],
            )

        deactivated = 0
        if options["deactivate_missing"]:
            question_ids = {question_id for _, question_id in seen_keys}
            deactivated = SelfAssessmentQuestion.objects.exclude(question_id__in=question_ids).update(is_active=False)

        self.stdout.write(
            self.style.SUCCESS(
                f"Imported self-assessment questions: {len(objects)} rows processed, {deactivated} deactivated."
            )
        )
