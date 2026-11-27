from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.exceptions import SuspiciousFileOperation
from django.urls import reverse

EXPECTED_EXHIBIT_BLOBS = [
    "scope/sc-027.png",
    "schedule/ag-001.png",
    "schedule/ag-014.png",
    "schedule/ag-042.png",
    "schedule/sch-003.png",
    "schedule/sch-009.png",
    "schedule/sch-045.png",
    "risk/rsk-011.png",
    "finance/ch1-q39.png",
    "finance/be-041.png",
]

DUPLICATE_VISUAL_IDS = {"SCH-004": "scope/sc-027.png"}

SOURCE_EXCEL_FILES = [
    "Stakeholders_Performance_Domain_Question_Bank.xlsx",
    "Scope_Performance_Domain_Question_Bank.xlsx",
    "Schedule_Performance_Domain_Question_Bank.xlsx",
    "Risk_Performance_Domain_Question_Bank.xlsx",
    "Resources_Performance_Domain_Question_Bank.xlsx",
    "Governance_Performance_Domain_Question_Bank.xlsx",
    "Finance_Performance_Domain_Question_Bank.xlsx",
]


@dataclass(frozen=True)
class BlobFetchResult:
    content: bytes
    content_type: str


def normalize_blob_name(blob_name):
    value = str(blob_name or "").strip().replace("\\", "/").lower()
    if not value or value.startswith("/") or ".." in value.split("/"):
        raise SuspiciousFileOperation("Invalid exhibit blob name.")
    if not value.endswith(".png"):
        raise SuspiciousFileOperation("Only PNG question exhibits are supported.")
    return value


def normalize_storage_path(storage_path):
    value = str(storage_path or "").strip().replace("\\", "/").lower()
    if not value or value.startswith("/") or ".." in value.split("/"):
        raise SuspiciousFileOperation("Invalid exhibit storage path.")
    if Path(value).suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
        raise SuspiciousFileOperation("Only image exhibit assets are supported.")
    return value


def content_type_for_path(path):
    suffix = Path(str(path or "")).suffix.lower()
    if suffix in {".jpg", ".jpeg"}:
        return "image/jpeg"
    if suffix == ".webp":
        return "image/webp"
    return "image/png"


def exhibit_proxy_url(blob_name, request=None):
    if not blob_name:
        return None
    name = normalize_blob_name(blob_name)
    path = reverse("pmp-exhibit", kwargs={"blob_name": name})
    return request.build_absolute_uri(path) if request else path


def _sas_query():
    token = getattr(settings, "AZURE_PMP_EXHIBIT_READ_SAS", "") or ""
    token = token.strip()
    if not token:
        return ""
    if token.startswith("http://") or token.startswith("https://"):
        token = urlparse(token).query
    return token[1:] if token.startswith("?") else token


def azure_blob_url(blob_name, sas_token=None):
    name = normalize_blob_name(blob_name)
    url = f"{settings.AZURE_PMP_BLOB_BASE_URL}/{quote(name, safe='/')}"
    token = _sas_query() if sas_token is None else str(sas_token or "").lstrip("?")
    return f"{url}?{token}" if token else url


def azure_asset_url(storage_path, sas_token=None):
    name = normalize_storage_path(storage_path)
    url = f"{settings.AZURE_PMP_BLOB_BASE_URL}/{quote(name, safe='/')}"
    token = _sas_query() if sas_token is None else str(sas_token or "").lstrip("?")
    return f"{url}?{token}" if token else url


def _local_exhibit_path(blob_name):
    name = normalize_blob_name(blob_name)
    root = Path(getattr(settings, "BASE_DIR")) / "pmp-question-assets"
    path = (root / name).resolve()
    root = root.resolve()
    if root != path and root not in path.parents:
        raise SuspiciousFileOperation("Invalid exhibit path.")
    return path


def local_exhibit_path(storage_path):
    value = normalize_storage_path(storage_path)
    root = Path(getattr(settings, "BASE_DIR")) / "pmp-question-assets"
    path = (root / value).resolve()
    root = root.resolve()
    if root != path and root not in path.parents:
        raise SuspiciousFileOperation("Invalid exhibit path.")
    return path


def fetch_local_exhibit_asset(storage_path):
    path = local_exhibit_path(storage_path)
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Local exhibit asset unavailable: {storage_path}")
    return BlobFetchResult(content=path.read_bytes(), content_type=content_type_for_path(path))


def fetch_azure_exhibit_asset(storage_path):
    request = Request(azure_asset_url(storage_path), headers={"Accept": content_type_for_path(storage_path)})
    try:
        with urlopen(request, timeout=20) as response:
            content_type = response.headers.get("Content-Type") or content_type_for_path(storage_path)
            return BlobFetchResult(content=response.read(), content_type=content_type)
    except HTTPError as exc:
        if getattr(settings, "DEBUG", False):
            return fetch_local_exhibit_asset(storage_path)
        raise FileNotFoundError(f"Azure exhibit asset unavailable: {normalize_storage_path(storage_path)}") from exc
    except URLError as exc:
        if getattr(settings, "DEBUG", False):
            return fetch_local_exhibit_asset(storage_path)
        raise RuntimeError("Could not reach Azure Blob Storage for exhibit delivery.") from exc


def fetch_local_exhibit_blob(blob_name):
    path = _local_exhibit_path(blob_name)
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Local exhibit asset unavailable: {normalize_blob_name(blob_name)}")
    return BlobFetchResult(content=path.read_bytes(), content_type="image/png")


def fetch_exhibit_blob(blob_name):
    if not _sas_query():
        if getattr(settings, "DEBUG", False):
            return fetch_local_exhibit_blob(blob_name)
        raise RuntimeError("AZURE_PMP_EXHIBIT_READ_SAS is not configured.")
    request = Request(azure_blob_url(blob_name), headers={"Accept": "image/png"})
    try:
        with urlopen(request, timeout=20) as response:
            content_type = response.headers.get("Content-Type") or "image/png"
            return BlobFetchResult(content=response.read(), content_type=content_type)
    except HTTPError as exc:
        if getattr(settings, "DEBUG", False):
            return fetch_local_exhibit_blob(blob_name)
        raise FileNotFoundError(f"Azure exhibit blob unavailable: {normalize_blob_name(blob_name)}") from exc
    except URLError as exc:
        if getattr(settings, "DEBUG", False):
            return fetch_local_exhibit_blob(blob_name)
        raise RuntimeError("Could not reach Azure Blob Storage for exhibit delivery.") from exc
