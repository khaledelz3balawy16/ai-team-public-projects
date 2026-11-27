import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from PIL import Image, ImageStat, UnidentifiedImageError

from pmp_assessment.models import PMPExhibit
from pmp_assessment.services.exhibit_storage import (
    DUPLICATE_VISUAL_IDS,
    EXPECTED_EXHIBIT_BLOBS,
    SOURCE_EXCEL_FILES,
    content_type_for_path,
    local_exhibit_path,
    normalize_blob_name,
    normalize_storage_path,
)

VISUAL_ID_BY_BLOB = {
    "scope/sc-027.png": "SC-027",
    "schedule/ag-001.png": "AG-001",
    "schedule/ag-014.png": "AG-014",
    "schedule/ag-042.png": "AG-042",
    "schedule/sch-003.png": "SCH-003",
    "schedule/sch-009.png": "SCH-009",
    "schedule/sch-045.png": "SCH-045",
    "risk/rsk-011.png": "RSK-011",
    "finance/ch1-q39.png": "CH1-Q39",
    "finance/be-041.png": "BE-041",
}


def container_sas():
    token = os.getenv("AZURE_PMP_CONTAINER_SAS", "").strip()
    if token.startswith("http://") or token.startswith("https://"):
        token = urlparse(token).query
    return token[1:] if token.startswith("?") else token


def blob_url(blob_name, sas_token):
    name = normalize_blob_name(blob_name)
    return f"{settings.AZURE_PMP_BLOB_BASE_URL}/{quote(name, safe='/')}?{sas_token}"


def asset_url(storage_path, sas_token):
    name = normalize_storage_path(storage_path)
    return f"{settings.AZURE_PMP_BLOB_BASE_URL}/{quote(name, safe='/')}?{sas_token}"


def find_asset(source_dir, blob_name):
    root = Path(source_dir)
    visual_id = VISUAL_ID_BY_BLOB[blob_name]
    candidates = [
        root / blob_name,
        root / Path(blob_name).name,
        root / f"{visual_id}.png",
        root / f"{visual_id.lower()}.png",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def validate_png(path):
    try:
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            if image.width <= 0 or image.height <= 0:
                raise CommandError(f"Invalid image dimensions: {path}")
            stat = ImageStat.Stat(image.convert("L"))
            extrema = stat.extrema[0]
            if extrema[0] == extrema[1]:
                raise CommandError(f"Image appears blank: {path}")
            return image.width, image.height
    except (UnidentifiedImageError, OSError) as exc:
        raise CommandError(f"Image is corrupted or not readable: {path}") from exc


def validate_image(path):
    try:
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            if image.width <= 0 or image.height <= 0:
                raise CommandError(f"Invalid image dimensions: {path}")
            stat = ImageStat.Stat(image.convert("L"))
            extrema = stat.extrema[0]
            if extrema[0] == extrema[1]:
                raise CommandError(f"Image appears blank: {path}")
            return image.width, image.height
    except (UnidentifiedImageError, OSError) as exc:
        raise CommandError(f"Image is corrupted or not readable: {path}") from exc


def put_asset(storage_path, path, sas_token):
    with open(path, "rb") as handle:
        data = handle.read()
    request = Request(asset_url(storage_path, sas_token), data=data, method="PUT", headers={
        "x-ms-blob-type": "BlockBlob",
        "Content-Type": content_type_for_path(path),
    })
    try:
        with urlopen(request, timeout=60) as response:
            if response.status not in (200, 201):
                raise CommandError(f"Azure upload failed for {storage_path}: HTTP {response.status}")
    except (HTTPError, URLError) as exc:
        raise CommandError(f"Azure upload failed for {storage_path}: {exc}") from exc


def put_blob(blob_name, path, sas_token):
    with open(path, "rb") as handle:
        data = handle.read()
    request = Request(blob_url(blob_name, sas_token), data=data, method="PUT", headers={
        "x-ms-blob-type": "BlockBlob",
        "Content-Type": "image/png",
    })
    try:
        with urlopen(request, timeout=60) as response:
            if response.status not in (200, 201):
                raise CommandError(f"Azure upload failed for {blob_name}: HTTP {response.status}")
    except (HTTPError, URLError) as exc:
        raise CommandError(f"Azure upload failed for {blob_name}: {exc}") from exc


def verify_blob(blob_name, sas_token):
    request = Request(blob_url(blob_name, sas_token), method="HEAD")
    try:
        with urlopen(request, timeout=30) as response:
            return response.status in (200, 201)
    except (HTTPError, URLError) as exc:
        raise CommandError(f"Azure verification failed for {blob_name}: {exc}") from exc


def verify_asset(storage_path, sas_token):
    request = Request(asset_url(storage_path, sas_token), method="HEAD")
    try:
        with urlopen(request, timeout=30) as response:
            return response.status in (200, 201)
    except (HTTPError, URLError) as exc:
        raise CommandError(f"Azure verification failed for {storage_path}: {exc}") from exc


class Command(BaseCommand):
    help = "Validate and upload PMP visual-question exhibit PNG assets to the private Azure container."

    def add_arguments(self, parser):
        parser.add_argument("--source-dir", default="pmp-question-assets", help="Directory containing the 10 verified PNG assets.")
        parser.add_argument("--excel-dir", default=".", help="Directory containing the original Excel question banks for availability checks.")
        parser.add_argument("--check-excel", action="store_true", help="Fail if any expected source Excel file is missing.")
        parser.add_argument("--dry-run", action="store_true", help="Validate local files without uploading to Azure.")
        parser.add_argument("--all-db-local", action="store_true", help="Upload every local PMPExhibit asset from the database and mark it as azure after verification.")

    def handle(self, *args, **options):
        if options["all_db_local"]:
            self.upload_database_local_assets(options["dry_run"])
            return

        if options["check_excel"]:
            excel_dir = Path(options["excel_dir"])
            missing = [name for name in SOURCE_EXCEL_FILES if not (excel_dir / name).exists()]
            if missing:
                raise CommandError("Missing source Excel files: " + ", ".join(missing))

        source_dir = Path(options["source_dir"])
        missing_assets = []
        resolved = []
        for blob_name in EXPECTED_EXHIBIT_BLOBS:
            path = find_asset(source_dir, blob_name)
            if not path:
                missing_assets.append(blob_name)
                continue
            width, height = validate_png(path)
            resolved.append((blob_name, path, width, height))

        if missing_assets:
            raise CommandError("Missing local exhibit PNG assets: " + ", ".join(missing_assets))

        if "SCH-004" in VISUAL_ID_BY_BLOB.values() or len(EXPECTED_EXHIBIT_BLOBS) != 10:
            raise CommandError("Duplicate SCH-004 must not be uploaded as an eleventh active asset.")

        if options["dry_run"]:
            self.stdout.write(self.style.SUCCESS(f"Validated {len(resolved)} unique PMP exhibit assets. No upload performed."))
            self.stdout.write("Duplicate visual IDs skipped: " + ", ".join(sorted(DUPLICATE_VISUAL_IDS)))
            return

        sas_token = container_sas()
        if not sas_token:
            raise CommandError("AZURE_PMP_CONTAINER_SAS is required for upload and verification.")

        for blob_name, path, _, _ in resolved:
            put_blob(blob_name, path, sas_token)
            verify_blob(blob_name, sas_token)
            self.stdout.write(f"Uploaded and verified {blob_name}")

        self.stdout.write(self.style.SUCCESS(f"Uploaded and verified {len(resolved)} unique PMP exhibit assets."))

    def upload_database_local_assets(self, dry_run):
        exhibits = PMPExhibit.objects.filter(storage_backend="local").exclude(storage_path="")
        resolved = []
        missing = []
        for exhibit in exhibits.order_by("id"):
            path = local_exhibit_path(exhibit.storage_path)
            if not path.exists():
                missing.append(f"{exhibit.id}:{exhibit.storage_path}")
                continue
            validate_image(path)
            resolved.append((exhibit, path))

        if missing:
            raise CommandError("Missing local exhibit assets: " + ", ".join(missing))

        if dry_run:
            self.stdout.write(self.style.SUCCESS(f"Validated {len(resolved)} local database exhibit assets. No upload performed."))
            return

        sas_token = container_sas()
        if not sas_token:
            raise CommandError("AZURE_PMP_CONTAINER_SAS is required for upload and verification.")

        uploaded = 0
        for exhibit, path in resolved:
            put_asset(exhibit.storage_path, path, sas_token)
            verify_asset(exhibit.storage_path, sas_token)
            exhibit.storage_backend = "azure"
            exhibit.save(update_fields=["storage_backend", "updated_at"])
            uploaded += 1
            self.stdout.write(f"Uploaded and verified exhibit {exhibit.id}: {exhibit.storage_path}")

        self.stdout.write(self.style.SUCCESS(f"Uploaded, verified, and marked {uploaded} database exhibit assets as azure."))
