import zipfile
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from PIL import Image, ImageStat, UnidentifiedImageError

EXCEL_IMAGE_TO_BLOB = {
    "Finance_Performance_Domain_Question_Bank.xlsx": [
        ("xl/media/image1.png", "finance/ch1-q39.png", "CH1-Q39"),
        ("xl/media/image2.png", "finance/be-041.png", "BE-041"),
    ],
    "Risk_Performance_Domain_Question_Bank.xlsx": [
        ("xl/media/image1.png", "risk/rsk-011.png", "RSK-011"),
    ],
    "Schedule_Performance_Domain_Question_Bank.xlsx": [
        ("xl/media/image1.png", "schedule/ag-001.png", "AG-001"),
        ("xl/media/image2.png", "schedule/ag-014.png", "AG-014"),
        ("xl/media/image3.png", "schedule/ag-042.png", "AG-042"),
        ("xl/media/image4.png", "schedule/sch-003.png", "SCH-003"),
        # image5 is SCH-004. It is intentionally skipped because SCH-004 duplicates SC-027.
        ("xl/media/image6.png", "schedule/sch-009.png", "SCH-009"),
        ("xl/media/image7.png", "schedule/sch-045.png", "SCH-045"),
    ],
    "Scope_Performance_Domain_Question_Bank.xlsx": [
        ("xl/media/image1.png", "scope/sc-027.png", "SC-027"),
    ],
}

SKIPPED_DUPLICATES = {"SCH-004": "scope/sc-027.png"}


def validate_png(path):
    try:
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            if image.width <= 0 or image.height <= 0:
                raise CommandError(f"Invalid image dimensions: {path}")
            extrema = ImageStat.Stat(image.convert("L")).extrema[0]
            if extrema[0] == extrema[1]:
                raise CommandError(f"Image appears blank: {path}")
            return image.width, image.height
    except (UnidentifiedImageError, OSError) as exc:
        raise CommandError(f"Image is corrupted or not readable: {path}") from exc


class Command(BaseCommand):
    help = "Extract original embedded PMP exhibit PNGs from the Excel question banks."

    def add_arguments(self, parser):
        parser.add_argument("--excel-dir", default="pmp_sources")
        parser.add_argument("--output-dir", default="pmp-question-assets")

    def handle(self, *args, **options):
        excel_dir = Path(options["excel_dir"])
        output_dir = Path(options["output_dir"])
        missing = [name for name in EXCEL_IMAGE_TO_BLOB if not (excel_dir / name).exists()]
        if missing:
            raise CommandError("Missing source Excel files: " + ", ".join(missing))

        extracted = []
        for filename, mappings in EXCEL_IMAGE_TO_BLOB.items():
            workbook = excel_dir / filename
            with zipfile.ZipFile(workbook) as archive:
                names = set(archive.namelist())
                for media_path, blob_name, exhibit_id in mappings:
                    if media_path not in names:
                        raise CommandError(f"Missing {media_path} for {exhibit_id} in {filename}")
                    target = output_dir / blob_name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(archive.read(media_path))
                    width, height = validate_png(target)
                    extracted.append((exhibit_id, blob_name, width, height))

        self.stdout.write(self.style.SUCCESS(f"Extracted {len(extracted)} unique PMP exhibit assets."))
        for exhibit_id, blob_name, width, height in extracted:
            self.stdout.write(f"{exhibit_id} -> {blob_name} ({width}x{height})")
        self.stdout.write("Skipped duplicate visual IDs: " + ", ".join(sorted(SKIPPED_DUPLICATES)))
