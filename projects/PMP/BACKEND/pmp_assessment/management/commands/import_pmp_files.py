import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from pmp_assessment.bank import PERFORMANCE_DOMAINS, infer_performance_domain, question_signature, unique_exam_questions
from pmp_assessment.models import PMPDomain, PMPQuestion, PMPQuestionOption, PMPTopic

DOMAIN_BY_ECO = {"1": "People", "2": "Process", "3": "Business Environment"}

def clean(value): return str(value or "").strip()
def eco_domain_for(eco): return DOMAIN_BY_ECO.get(clean(eco).split(".")[0], "")
def methodology_for(text):
    value = text.lower()
    if "hybrid" in value: return "Hybrid"
    if any(word in value for word in ("agile", "sprint", "scrum", "product owner", "backlog")): return "Agile"
    if any(word in value for word in ("predictive", "waterfall", "baseline", "change control")): return "Predictive"
    return "General"

class Command(BaseCommand):
    help = "Import single- and multiple-answer PMP questions from XLSX/CSV while preserving source metadata."
    def add_arguments(self, parser): parser.add_argument("files", nargs="+", type=Path)
    def handle(self, *args, **options):
        totals = {"created": 0, "duplicates": 0, "needs_domain_mapping": 0, "invalid": 0}
        seen_files = set()
        existing = {question_signature(q): q for q in unique_exam_questions(PMPQuestion.objects.all())}
        for path in options["files"]:
            if not path.exists(): raise CommandError(f"File not found: {path}")
            digest = __import__("hashlib").sha256(path.read_bytes()).hexdigest()
            if digest in seen_files:
                self.stdout.write(self.style.WARNING(f"Skipped identical file: {path.name}")); continue
            seen_files.add(digest)
            rows = self.read_xlsx(path) if path.suffix.lower() == ".xlsx" else self.read_csv(path)
            for row in rows:
                result, question = self.import_row(row, path.name)
                if question:
                    signature = question_signature(question)
                    canonical = existing.get(signature)
                    if canonical:
                        question.duplicate_of = canonical; question.is_active = False; question.save(update_fields=["duplicate_of", "is_active", "updated_at"])
                        result = "duplicates"
                    else:
                        existing[signature] = question
                totals[result] += 1
        self.stdout.write(self.style.SUCCESS(
            "Import complete - created: {created}, duplicates: {duplicates}, needs domain mapping: {needs_domain_mapping}, invalid skipped: {invalid}".format(**totals)
        ))
    def read_xlsx(self, path):
        from openpyxl import load_workbook
        workbook = load_workbook(path, read_only=True, data_only=True)
        for sheet in workbook.worksheets:
            rows = sheet.iter_rows(values_only=True)
            try: headers = [clean(value) for value in next(rows)]
            except StopIteration: continue
            for values in rows:
                raw = dict(zip(headers, values))
                case = clean(raw.get("Case or Graphic"))
                stem = clean(raw.get("Stem and Question") or raw.get("Question"))
                yield {"question_id": clean(raw.get("Original Question ID") or raw.get("Question ID") or raw.get("ID")),
                       "question": f"{case}\n\n{stem}" if case else stem, "case": case, "key": clean(raw.get("Key") or raw.get("Correct Answer")),
                       "eco": clean(raw.get("ECO match") or raw.get("ECO")), "performance_domain": clean(raw.get("Performance Domain")),
                       "methodology": clean(raw.get("Methodology")), "question_type": clean(raw.get("Question Type")),
                       "rationale": clean(raw.get("Feedback and Rationale") or raw.get("Rationale")), "source_sheet": sheet.title,
                       "options": {label: clean(raw.get(f"Option {label}") or raw.get(f"Answer {label}")) for label in "ABCDE"}}
    def read_csv(self, path):
        with path.open(encoding="cp1252", newline="") as stream:
            for raw in csv.DictReader(stream):
                yield {"question_id": clean(raw.get("Original Question ID") or raw.get("Question ID") or raw.get("ID")),
                       "question": clean(raw.get("Stem and Question") or raw.get("Question")), "case": clean(raw.get("Case or Graphic")),
                       "key": clean(raw.get("Key") or raw.get("Correct Answer")), "eco": clean(raw.get("ECO match") or raw.get("ECO")),
                       "performance_domain": clean(raw.get("Performance Domain")), "methodology": clean(raw.get("Methodology")),
                       "question_type": clean(raw.get("Question Type")), "rationale": clean(raw.get("Feedback and Rationale") or raw.get("Rationale")),
                       "source_sheet": clean(raw.get("Source Sheet")), "options": {label: clean(raw.get(f"Option {label}") or raw.get(f"Answer {label}")) for label in "ABCDE"}}
    @transaction.atomic
    def import_row(self, row, source):
        keys = [item.strip().upper() for item in row["key"].replace(";", ",").split(",") if item.strip()]
        options = {label: text for label, text in row["options"].items() if text}
        if not row["question"] or len(options) < 2 or not keys or any(key not in options for key in keys): return "invalid", None
        performance_domain = row["performance_domain"] if row["performance_domain"] in PERFORMANCE_DOMAINS else infer_performance_domain(row["question"], row["eco"])
        needs_mapping = performance_domain not in PERFORMANCE_DOMAINS
        domain, _ = PMPDomain.objects.get_or_create(name=performance_domain if not needs_mapping else "Unmapped")
        topic_name = f"ECO {row['eco']}" if row["eco"] else "General PMP Practice"
        topic, _ = PMPTopic.objects.get_or_create(domain=domain, name=topic_name)
        qtype = row["question_type"] or ("Multiple Response" if len(keys) > 1 else "Case Study" if row["case"] else "Single Response")
        question = PMPQuestion.objects.create(
            question_id=row["question_id"], question_text=row["question"], domain=domain, topic=topic,
            performance_domain="" if needs_mapping else performance_domain, eco_domain=eco_domain_for(row["eco"]), eco_task=row["eco"], task=row["eco"],
            methodology=row["methodology"] or methodology_for(row["question"]), question_type=qtype, difficulty="Medium",
            correct_answer_explanation=row["rationale"], wrong_answer_explanation=row["rationale"],
            pmp_reference=f"Imported from {source}", source_file=source, source_sheet=row["source_sheet"],
            import_status="needs_domain_mapping" if needs_mapping else "ready", is_active=not needs_mapping,
        )
        PMPQuestionOption.objects.bulk_create([PMPQuestionOption(question=question, option_label=label, option_text=text, is_correct=label in keys) for label, text in options.items()])
        return ("needs_domain_mapping" if needs_mapping else "created"), question
