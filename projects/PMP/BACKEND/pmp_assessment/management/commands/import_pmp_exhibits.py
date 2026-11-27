import hashlib
import posixpath
import re
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from pmp_assessment.bank import PERFORMANCE_DOMAINS, infer_performance_domain, normalize_text
from pmp_assessment.models import PMPDomain, PMPExhibit, PMPQuestion, PMPQuestionExhibit, PMPQuestionOption, PMPTopic

NS = {
    "m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "pr": "http://schemas.openxmlformats.org/package/2006/relationships",
    "xdr": "http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
}


@dataclass
class WorkbookQuestion:
    row_number: int
    question_number: int
    qid: str
    question_text: str
    exhibit_label: str = ""
    visual_filename: str = ""
    options: dict = field(default_factory=dict)
    correct_answer: str = ""
    explanation: str = ""
    performance_domain: str = ""
    methodology: str = ""
    source_note: str = ""


@dataclass
class WorkbookImage:
    row_number: int
    col_number: int
    media_path: str
    data: bytes
    ext: str
    checksum: str


@dataclass
class ImportReport:
    files: int = 0
    questions_checked: int = 0
    questions_matched: int = 0
    case_studies_detected: int = 0
    image_refs_detected: int = 0
    images_extracted: int = 0
    exhibits_created: int = 0
    exhibits_updated: int = 0
    links_created: int = 0
    links_existing: int = 0
    questions_created: int = 0
    questions_existing: int = 0
    missing_question_matches: list = field(default_factory=list)
    ambiguous_question_matches: list = field(default_factory=list)
    missing_images: list = field(default_factory=list)
    link_preview: list = field(default_factory=list)


def xml_root(archive, name):
    return ET.fromstring(archive.read(name))


def normal_path(base, target):
    return posixpath.normpath(posixpath.join(posixpath.dirname(base), target)).lstrip("/")


def cell_text(cell, shared):
    cell_type = cell.attrib.get("t")
    if cell_type == "inlineStr":
        return "".join(t.text or "" for t in cell.findall(".//m:t", NS)).strip()
    value = cell.find("m:v", NS)
    if value is None:
        return ""
    raw = value.text or ""
    if cell_type == "s":
        try:
            return shared[int(raw)].strip()
        except (ValueError, IndexError):
            return raw.strip()
    return raw.strip()


def cell_column(ref):
    letters = re.sub(r"\d+", "", ref or "")
    number = 0
    for char in letters:
        number = number * 26 + ord(char.upper()) - 64
    return number


def cell_row(ref):
    match = re.search(r"\d+", ref or "")
    return int(match.group()) if match else 0


def safe_slug(value):
    slug = re.sub(r"[^a-z0-9]+", "-", str(value or "").lower()).strip("-")
    return slug or "exhibit"


def strip_arabic_translation(value):
    text = str(value or "").strip()
    if not re.search(r"[\u0600-\u06FF]", text):
        return text
    english_parenthetical = re.findall(r"\(([A-Za-z][A-Za-z0-9 /&,+-]+)\)", text)
    if english_parenthetical:
        phrase = english_parenthetical[-1].strip()
        return f"{phrase} Life Cycle" if phrase.lower() == "hybrid" else phrase
    return re.sub(r"[\u0600-\u06FF]+", "", text).strip()


def infer_exam_key(path):
    match = re.search(r"Mock_Exam_(\d+)", path.name, re.IGNORECASE)
    return f"exam{int(match.group(1)):02d}" if match else safe_slug(path.stem)


def infer_exhibit_type(filename, label):
    text = f"{filename} {label}".lower()
    if "case" in text:
        return "case_study"
    if "table" in text or "matrix" in text or "traceability" in text or "source_selection" in text:
        return "table"
    if "chart" in text or "curve" in text or "histogram" in text or "flow" in text or "burndown" in text or "s_curve" in text:
        return "chart"
    if "diagram" in text or "map" in text or "tree" in text or "grid" in text:
        return "diagram"
    return "image"


class XlsxWorkbook:
    def __init__(self, path):
        self.path = Path(path)
        self.archive = zipfile.ZipFile(self.path)
        self.names = set(self.archive.namelist())
        self.shared = self._shared_strings()
        self.sheets = self._sheet_paths()

    def close(self):
        self.archive.close()

    def _shared_strings(self):
        if "xl/sharedStrings.xml" not in self.names:
            return []
        root = xml_root(self.archive, "xl/sharedStrings.xml")
        return ["".join(t.text or "" for t in item.findall(".//m:t", NS)) for item in root.findall("m:si", NS)]

    def _sheet_paths(self):
        workbook = xml_root(self.archive, "xl/workbook.xml")
        rels_root = xml_root(self.archive, "xl/_rels/workbook.xml.rels")
        rels = {rel.attrib["Id"]: rel.attrib["Target"] for rel in rels_root.findall("pr:Relationship", NS)}
        paths = {}
        for sheet in workbook.findall("m:sheets/m:sheet", NS):
            rel_id = sheet.attrib[f"{{{NS['r']}}}id"]
            paths[sheet.attrib["name"]] = normal_path("xl/workbook.xml", rels[rel_id])
        return paths

    def rows(self, sheet_name):
        sheet_path = self.sheets.get(sheet_name)
        if not sheet_path:
            return []
        sheet = xml_root(self.archive, sheet_path)
        rows = []
        for row in sheet.findall("m:sheetData/m:row", NS):
            values = {}
            for cell in row.findall("m:c", NS):
                value = cell_text(cell, self.shared)
                if value:
                    values[cell.attrib.get("r", "")] = value
            if values:
                rows.append(values)
        return rows

    def drawing_images(self, sheet_name):
        sheet_path = self.sheets.get(sheet_name)
        if not sheet_path:
            return []
        rel_path = posixpath.join(posixpath.dirname(sheet_path), "_rels", posixpath.basename(sheet_path) + ".rels")
        drawings = []
        if rel_path in self.names:
            rels_root = xml_root(self.archive, rel_path)
            for rel in rels_root.findall("pr:Relationship", NS):
                if "drawing" in rel.attrib.get("Type", ""):
                    drawings.append(normal_path(sheet_path, rel.attrib["Target"]))

        images = []
        for drawing in drawings:
            if drawing not in self.names:
                continue
            drawing_root = xml_root(self.archive, drawing)
            drawing_rels_path = posixpath.join(posixpath.dirname(drawing), "_rels", posixpath.basename(drawing) + ".rels")
            rels = {}
            if drawing_rels_path in self.names:
                rels_root = xml_root(self.archive, drawing_rels_path)
                rels = {rel.attrib["Id"]: rel.attrib["Target"] for rel in rels_root.findall("pr:Relationship", NS)}
            anchors = list(drawing_root.findall("xdr:twoCellAnchor", NS)) + list(drawing_root.findall("xdr:oneCellAnchor", NS))
            for anchor in anchors:
                start = anchor.find("xdr:from", NS)
                pic = anchor.find("xdr:pic", NS)
                if start is None or pic is None:
                    continue
                row = int(start.find("xdr:row", NS).text) + 1
                col = int(start.find("xdr:col", NS).text) + 1
                blip = pic.find("xdr:blipFill/a:blip", NS)
                rel_id = blip.attrib.get(f"{{{NS['r']}}}embed") if blip is not None else ""
                media_path = normal_path(drawing, rels.get(rel_id, ""))
                if media_path not in self.names:
                    continue
                data = self.archive.read(media_path)
                ext = Path(media_path).suffix.lower() or ".png"
                images.append(WorkbookImage(row, col, media_path, data, ext, hashlib.sha256(data).hexdigest()))
        return images


class Command(BaseCommand):
    help = "Import PMP exhibit metadata and assets from mock-exam workbooks without duplicating questions."

    def add_arguments(self, parser):
        parser.add_argument("files", nargs="+", type=Path)
        parser.add_argument("--dry-run", action="store_true", help="Inspect and report only. No files or database rows are changed.")
        parser.add_argument("--create-missing-questions", action="store_true", help="Create workbook questions that do not already exist after duplicate checks.")
        parser.add_argument("--output-dir", default="pmp-question-assets")

    def handle(self, *args, **options):
        self.build_question_index()
        report = ImportReport()
        for path in options["files"]:
            if not path.exists():
                raise CommandError(f"File not found: {path}")
            self.process_file(path, options, report)
        self.print_report(report, options["dry_run"])

    def build_question_index(self):
        self.qid_index = {}
        self.text_index = {}
        self.text_rows = []
        questions = PMPQuestion.objects.filter(is_active=True, duplicate_of__isnull=True).only("id", "question_id", "source_item_id", "question_text")
        for question in questions:
            self.add_question_to_index(question)

    def process_file(self, path, options, report):
        workbook = XlsxWorkbook(path)
        try:
            exam_key = infer_exam_key(path)
            report.files += 1
            questions = self.read_questions(workbook)
            self.enrich_questions(workbook, questions)
            visuals = self.read_blueprint_visuals(workbook)
            for question in questions:
                question.visual_filename = visuals.get(question.qid, "")
            if options["create_missing_questions"]:
                for question in questions:
                    self.ensure_question(question, f"{exam_key}.xlsx", options, report)
            question_images = workbook.drawing_images("Questions")
            exhibit_images = workbook.drawing_images("Exhibits")
            images_by_question_row = {image.row_number: image for image in question_images}
            images_by_exhibit_index = {index + 1: image for index, image in enumerate(sorted(exhibit_images, key=lambda x: x.row_number))}

            case_title, case_content = self.read_case_study(workbook)
            case_questions = [q for q in questions[:5] if "case study" in q.question_text.lower()]
            if case_content and case_questions:
                report.case_studies_detected += 1
                self.import_case_study(exam_key, case_title, case_content, case_questions, options, report)

            visual_questions = [q for q in questions if q.exhibit_label]
            report.image_refs_detected += len(visual_questions)
            for index, question in enumerate(visual_questions, start=1):
                image = images_by_question_row.get(question.row_number) or images_by_exhibit_index.get(index)
                if not image:
                    report.missing_images.append(f"{exam_key} {question.qid or question.question_number}: {question.exhibit_label}")
                    continue
                self.import_image_exhibit(exam_key, question, image, options, report)
        finally:
            workbook.close()

    def read_questions(self, workbook):
        sheet_name = "Questions" if "Questions" in workbook.sheets else "Questions & Answers"
        rows = workbook.rows(sheet_name)
        if not rows:
            return []
        header = {cell_column(ref): value.strip() for ref, value in rows[0].items()}
        result = []
        for row in rows[1:]:
            by_header = {header.get(cell_column(ref), ""): value for ref, value in row.items()}
            no = by_header.get("No.") or by_header.get("No") or ""
            question_number = int(float(no)) if str(no).strip() else 0
            qid = by_header.get("QID") or by_header.get("Question ID") or ""
            text = by_header.get("Question") or by_header.get("Stem and Question") or ""
            exhibit = by_header.get("Exhibit") or ""
            if question_number and text:
                row_number = max(cell_row(ref) for ref in row)
                result.append(WorkbookQuestion(
                    row_number=row_number,
                    question_number=question_number,
                    qid=qid.strip(),
                    question_text=text.strip(),
                    exhibit_label=exhibit.strip(),
                    options={label: strip_arabic_translation(by_header.get(label, "")) for label in "ABCDE" if by_header.get(label, "").strip()},
                    correct_answer=(by_header.get("Correct Answer") or "").strip().upper(),
                    explanation=(by_header.get("Explanation") or "").strip(),
                    performance_domain=(by_header.get("Domain / Classification") or by_header.get("Performance Domain") or "").strip(),
                    methodology=(by_header.get("Approach") or "").strip(),
                    source_note=(by_header.get("Source-Fit / Item Note") or "").strip(),
                ))
        return result

    def enrich_questions(self, workbook, questions):
        by_qid = {q.qid: q for q in questions if q.qid}
        by_number = {q.question_number: q for q in questions}
        for row in workbook.rows("Answer Key")[1:]:
            refs = {re.sub(r"\d+", "", ref): value for ref, value in row.items()}
            number = int(float(refs.get("A", "0"))) if refs.get("A") else 0
            question = by_qid.get(refs.get("B", "").strip()) or by_number.get(number)
            if question:
                question.correct_answer = question.correct_answer or (refs.get("C") or "").strip().upper()
                question.explanation = question.explanation or (refs.get("E") or "").strip()
        rows = workbook.rows("Blueprint")
        if not rows:
            return
        header = {cell_column(ref): value.strip() for ref, value in rows[0].items()}
        for row in rows[1:]:
            by_header = {header.get(cell_column(ref), ""): value for ref, value in row.items()}
            question = by_qid.get((by_header.get("QID") or "").strip())
            if question:
                question.performance_domain = question.performance_domain or (by_header.get("Performance Domain") or "").strip()
                question.methodology = question.methodology or (by_header.get("Approach") or "").strip()
                question.source_note = question.source_note or (by_header.get("Appendix / Cross-Cutting Coverage") or by_header.get("Seed Item ID") or "").strip()

    def read_blueprint_visuals(self, workbook):
        rows = workbook.rows("Blueprint")
        if not rows:
            return {}
        header = {cell_column(ref): value.strip() for ref, value in rows[0].items()}
        visual_map = {}
        for row in rows[1:]:
            by_header = {header.get(cell_column(ref), ""): value for ref, value in row.items()}
            qid = (by_header.get("QID") or "").strip()
            visual = (by_header.get("Visual Exhibit") or "").strip()
            if qid and visual and "." in visual:
                visual_map[qid] = visual
        return visual_map

    def read_case_study(self, workbook):
        rows = workbook.rows("Case Study")
        values = []
        for row in rows:
            for ref, value in sorted(row.items(), key=lambda item: (cell_row(item[0]), cell_column(item[0]))):
                if value.strip():
                    values.append(value.strip())
        if not values:
            return "", ""
        return values[0], "\n\n".join(values)

    def matching_questions(self, workbook_question):
        qid = workbook_question.qid.strip()
        if qid:
            matches = list({question.id: question for question in self.qid_index.get(qid.lower(), [])}.values())
            return matches
        normalized_source = normalize_text(workbook_question.question_text)
        if not normalized_source:
            return []
        exact = self.text_index.get(normalized_source, [])
        if exact:
            return exact
        return [question for normalized_target, question in self.text_rows if normalized_source in normalized_target or normalized_target in normalized_source]

    def resolve_question(self, workbook_question, report):
        report.questions_checked += 1
        matches = self.matching_questions(workbook_question)
        label = workbook_question.qid or f"Q{workbook_question.question_number}"
        if len(matches) == 1:
            report.questions_matched += 1
            report.questions_existing += 1
            return matches[0]
        if not matches:
            report.missing_question_matches.append(label)
        else:
            report.ambiguous_question_matches.append(f"{label}: {[q.id for q in matches[:10]]}")
        return None

    def ensure_question(self, workbook_question, source_file, options, report):
        if not options["create_missing_questions"]:
            return self.resolve_question(workbook_question, report)
        report.questions_checked += 1
        matches = self.matching_questions(workbook_question)
        label = workbook_question.qid or f"Q{workbook_question.question_number}"
        if len(matches) == 1:
            report.questions_matched += 1
            report.questions_existing += 1
            return matches[0]
        if len(matches) > 1:
            report.ambiguous_question_matches.append(f"{label}: {[q.id for q in matches[:10]]}")
            return None
        if not workbook_question.options or workbook_question.correct_answer not in workbook_question.options:
            report.missing_question_matches.append(f"{workbook_question.qid or workbook_question.question_number}: cannot create without valid answer key")
            return None
        if options["dry_run"]:
            report.questions_created += 1
            report.questions_matched += 1
            return True
        domain_name = self.domain_for(workbook_question)
        domain, _ = PMPDomain.objects.get_or_create(name=domain_name)
        topic, _ = PMPTopic.objects.get_or_create(domain=domain, name=f"{source_file} Mock Exam")
        question = PMPQuestion.objects.create(
            question_id=workbook_question.qid,
            source_item_id=workbook_question.qid,
            question_text=workbook_question.question_text,
            domain=domain,
            topic=topic,
            performance_domain=domain_name,
            eco_domain=self.eco_for(domain_name),
            eco_task=workbook_question.source_note,
            task=workbook_question.source_note,
            methodology=self.methodology_for(workbook_question),
            question_type="Single Response",
            difficulty="Medium",
            correct_answer_explanation=workbook_question.explanation,
            wrong_answer_explanation=workbook_question.explanation,
            pmp_reference=f"Imported from {source_file}",
            source_file=source_file,
            source_sheet="Questions",
            source_year=2026,
            is_active=True,
            import_status="ready",
        )
        PMPQuestionOption.objects.bulk_create([
            PMPQuestionOption(question=question, option_label=label, option_text=text, is_correct=label == workbook_question.correct_answer)
            for label, text in workbook_question.options.items()
        ])
        self.add_question_to_index(question)
        report.questions_created += 1
        report.questions_matched += 1
        return question

    def add_question_to_index(self, question):
        seen_keys = set()
        for value in (question.question_id, question.source_item_id):
            key = str(value or "").strip().lower()
            if key and key not in seen_keys:
                self.qid_index.setdefault(key, []).append(question)
                seen_keys.add(key)
        normalized = normalize_text(question.question_text)
        if normalized:
            self.text_index.setdefault(normalized, []).append(question)
            self.text_rows.append((normalized, question))

    def domain_for(self, workbook_question):
        raw = workbook_question.performance_domain
        for domain in PERFORMANCE_DOMAINS:
            if domain.lower() in raw.lower():
                return domain
        inferred = infer_performance_domain(workbook_question.question_text, raw, workbook_question.source_note)
        return inferred if inferred in PERFORMANCE_DOMAINS else "Governance"

    def eco_for(self, domain):
        if domain in {"Stakeholders", "Resources"}:
            return "People"
        if domain == "Governance":
            return "Business Environment"
        return "Process"

    def methodology_for(self, workbook_question):
        raw = f"{workbook_question.methodology} {workbook_question.question_text}".lower()
        if "hybrid" in raw:
            return "Hybrid"
        if "agile" in raw or "sprint" in raw or "backlog" in raw or "product owner" in raw:
            return "Agile"
        if "predictive" in raw or "waterfall" in raw or "baseline" in raw:
            return "Predictive"
        return "General"

    @transaction.atomic
    def import_case_study(self, exam_key, title, content, questions, options, report):
        matched = []
        for question in questions:
            db_question = self.ensure_question(question, f"{exam_key}.xlsx", options, report)
            if db_question:
                matched.append((question, db_question))
        if not matched:
            return
        checksum = hashlib.sha256(content.encode("utf-8")).hexdigest()
        if options["dry_run"]:
            for source_question, _ in matched:
                report.link_preview.append(f"{source_question.qid} -> {title}")
            return
        exhibit, created = PMPExhibit.objects.update_or_create(
            source_exam=exam_key,
            source_label="case-study",
            checksum=checksum,
            defaults={"title": title or f"{exam_key} Case Study", "exhibit_type": "case_study", "storage_backend": "none", "content": content, "caption": title},
        )
        report.exhibits_created += int(created)
        report.exhibits_updated += int(not created)
        for order, (source_question, db_question) in enumerate(matched, start=1):
            _, link_created = PMPQuestionExhibit.objects.get_or_create(question=db_question, exhibit=exhibit, defaults={"display_order": 1})
            report.links_created += int(link_created)
            report.links_existing += int(not link_created)
            report.link_preview.append(f"{source_question.qid} -> {title}")

    @transaction.atomic
    def import_image_exhibit(self, exam_key, question, image, options, report):
        db_question = self.ensure_question(question, f"{exam_key}.xlsx", options, report)
        if not db_question:
            return
        filename = question.visual_filename or f"{exam_key}_question_{question.question_number:03d}{image.ext}"
        if not filename.lower().endswith(image.ext):
            filename = f"{Path(filename).stem}{image.ext}"
        storage_path = f"mock-exams/{exam_key}/{safe_slug(Path(filename).stem)}{image.ext}"
        title = question.exhibit_label or Path(filename).stem.replace("_", " ").title()
        exhibit_type = infer_exhibit_type(filename, question.exhibit_label)
        report.link_preview.append(f"{question.qid or question.question_number} -> {storage_path}")
        if options["dry_run"]:
            return
        target = Path(options["output_dir"]) / storage_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(image.data)
        report.images_extracted += 1
        exhibit, created = PMPExhibit.objects.update_or_create(
            source_exam=exam_key,
            source_label=question.exhibit_label or f"question-{question.question_number}",
            checksum=image.checksum,
            defaults={
                "title": title,
                "exhibit_type": exhibit_type,
                "storage_backend": "local",
                "storage_path": storage_path,
                "caption": title,
                "source_question_number": question.question_number,
                "metadata": {"qid": question.qid, "filename": filename, "excel_media_path": image.media_path},
            },
        )
        report.exhibits_created += int(created)
        report.exhibits_updated += int(not created)
        _, link_created = PMPQuestionExhibit.objects.get_or_create(question=db_question, exhibit=exhibit, defaults={"display_order": 1})
        report.links_created += int(link_created)
        report.links_existing += int(not link_created)

    def print_report(self, report, dry_run):
        self.stdout.write("")
        self.stdout.write("PMP Exhibit Import Report")
        self.stdout.write(f"Files checked: {report.files}")
        self.stdout.write(f"Questions checked for links: {report.questions_checked}")
        self.stdout.write(f"Questions matched: {report.questions_matched}")
        self.stdout.write(f"Case studies detected: {report.case_studies_detected}")
        self.stdout.write(f"Image exhibit refs detected: {report.image_refs_detected}")
        self.stdout.write(f"Images extracted: {report.images_extracted}")
        self.stdout.write(f"Exhibits created: {report.exhibits_created}")
        self.stdout.write(f"Exhibits updated: {report.exhibits_updated}")
        self.stdout.write(f"Questions created: {report.questions_created}")
        self.stdout.write(f"Existing questions reused: {report.questions_existing}")
        self.stdout.write(f"Links created: {report.links_created}")
        self.stdout.write(f"Links already existed: {report.links_existing}")
        changes = report.exhibits_created + report.exhibits_updated + report.links_created + report.questions_created
        self.stdout.write(f"Database changes: {'0 (dry-run)' if dry_run else changes}")
        if report.link_preview:
            self.stdout.write("")
            self.stdout.write("Question-Exhibit links:")
            for row in report.link_preview[:200]:
                self.stdout.write(row)
        if report.missing_question_matches:
            self.stdout.write(self.style.WARNING("Missing question matches: " + ", ".join(report.missing_question_matches[:100])))
        if report.ambiguous_question_matches:
            self.stdout.write(self.style.WARNING("Ambiguous question matches: " + "; ".join(report.ambiguous_question_matches[:50])))
        if report.missing_images:
            self.stdout.write(self.style.WARNING("Missing images: " + "; ".join(report.missing_images[:50])))
        self.stdout.write(self.style.SUCCESS("DRY RUN COMPLETE" if dry_run else "IMPORT COMPLETE"))
