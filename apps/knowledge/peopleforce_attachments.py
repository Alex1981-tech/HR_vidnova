from __future__ import annotations

import hashlib
import mimetypes
import posixpath
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import unquote, urlparse

import httpx
from django.conf import settings
from django.core.files.base import ContentFile
from django.utils.text import slugify

from .models import KnowledgeAttachment, KnowledgeDocument


RICH_ATTACHMENT_MARKER = "/rich_text/attachments/"
MAX_KNOWLEDGE_ATTACHMENT_BYTES = 25 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class PeopleForceAttachmentRef:
    url: str
    name: str
    size_bytes: int = 0

    @property
    def external_id(self) -> str:
        return hashlib.sha256(self.url.encode("utf-8")).hexdigest()[:32]


@dataclass(frozen=True, slots=True)
class KnowledgeAttachmentSyncResult:
    downloaded: int
    reused: int
    failed: int
    rewritten: int
    urls: dict[str, str]


class PeopleForceRichTextAttachmentParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.refs: list[PeopleForceAttachmentRef] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        attr_map = {name.lower(): value or "" for name, value in attrs}
        href = attr_map.get("href", "").strip()
        if not is_peopleforce_attachment_url(href):
            return
        name = attr_map.get("name") or posixpath.basename(urlparse(href).path) or "peopleforce-attachment"
        self.refs.append(PeopleForceAttachmentRef(url=href, name=unquote(name), size_bytes=int_or_zero(attr_map.get("size"))))


def sync_peopleforce_document_attachments(
    document: KnowledgeDocument,
    *,
    force: bool = False,
    timeout_seconds: int | None = None,
) -> KnowledgeAttachmentSyncResult:
    refs = extract_peopleforce_attachment_refs(document.body_html, document.body)
    if not refs:
        return KnowledgeAttachmentSyncResult(downloaded=0, reused=0, failed=0, rewritten=0, urls={})

    downloaded = 0
    reused = 0
    failed = 0
    replacements: dict[str, str] = {}

    timeout = timeout_seconds or getattr(settings, "PEOPLEFORCE_DOCUMENT_DOWNLOAD_TIMEOUT_SECONDS", 30)
    headers = {
        "Accept": "application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/octet-stream,*/*",
        "User-Agent": "VidnovaHR/1.0 KnowledgeAttachmentImporter",
    }
    if settings.PEOPLEFORCE_API_KEY:
        headers["X-API-KEY"] = settings.PEOPLEFORCE_API_KEY
    if getattr(settings, "PEOPLEFORCE_WEB_COOKIE", ""):
        headers["Cookie"] = settings.PEOPLEFORCE_WEB_COOKIE

    with httpx.Client(timeout=timeout, headers=headers, follow_redirects=True) as client:
        for ref in refs:
            attachment = KnowledgeAttachment.objects.filter(
                document=document,
                legacy_peopleforce_id=ref.external_id,
            ).first()
            if attachment and attachment.file and not force:
                replacements[ref.url] = attachment.file.url
                reused += 1
                continue

            try:
                response = client.get(ref.url)
                if "/users/sign_in" in str(response.url):
                    raise RuntimeError("PeopleForce redirected to sign-in; configure PEOPLEFORCE_WEB_COOKIE to download private rich-text attachments.")
                response.raise_for_status()
                content = response.content
                if len(content) > MAX_KNOWLEDGE_ATTACHMENT_BYTES:
                    raise ValueError(f"Attachment is too large: {len(content)} bytes")

                filename = knowledge_attachment_filename(
                    document=document,
                    ref=ref,
                    content_type=response.headers.get("content-type", ""),
                    content_disposition=response.headers.get("content-disposition", ""),
                )
                attachment = attachment or KnowledgeAttachment(document=document, legacy_peopleforce_id=ref.external_id)
                attachment.original_name = ref.name or filename
                attachment.content_type = trim_header(response.headers.get("content-type", ""))
                attachment.size_bytes = len(content)
                attachment.source_url = ref.url
                attachment.legacy_payload = {
                    "peopleforce_url": ref.url,
                    "peopleforce_name": ref.name,
                    "peopleforce_size_bytes": ref.size_bytes,
                }
                attachment.file.save(filename, ContentFile(content), save=False)
                attachment.save()
                replacements[ref.url] = attachment.file.url
                downloaded += 1
            except Exception as exc:  # noqa: BLE001
                failed += 1
                legacy_payload = dict(document.legacy_payload or {})
                errors = list(legacy_payload.get("peopleforce_attachment_errors") or [])
                errors.append({"url": ref.url, "name": ref.name, "error": str(exc)[:500]})
                legacy_payload["peopleforce_attachment_errors"] = errors[-20:]
                document.legacy_payload = legacy_payload

    rewritten = rewrite_document_attachment_urls(document, replacements)
    if replacements or failed:
        update_fields = ["legacy_payload", "updated_at"]
        if rewritten:
            update_fields.extend(["body", "body_html"])
        document.save(update_fields=update_fields)

    return KnowledgeAttachmentSyncResult(downloaded=downloaded, reused=reused, failed=failed, rewritten=rewritten, urls=replacements)


def extract_peopleforce_attachment_refs(*values: str) -> list[PeopleForceAttachmentRef]:
    refs: dict[str, PeopleForceAttachmentRef] = {}
    for value in values:
        if not value or RICH_ATTACHMENT_MARKER not in value:
            continue
        parser = PeopleForceRichTextAttachmentParser()
        parser.feed(value)
        for ref in parser.refs:
            refs.setdefault(ref.url, ref)
        for match in re.finditer(r"""['"]src['"]:\s*['"]([^'"]+/rich_text/attachments/[^'"]+)['"]""", value):
            url = decode_escaped(match.group(1))
            name_match = re.search(r"""['"]name['"]:\s*['"]([^'"]+)['"]""", value[match.end() : match.end() + 300])
            size_match = re.search(r"""['"]size['"]:\s*([0-9]+)""", value[match.end() : match.end() + 300])
            refs.setdefault(
                url,
                PeopleForceAttachmentRef(
                    url=url,
                    name=decode_escaped(name_match.group(1)) if name_match else posixpath.basename(urlparse(url).path),
                    size_bytes=int_or_zero(size_match.group(1) if size_match else None),
                ),
            )
        for match in re.finditer(r"""https?://[^'"\s<>]+/rich_text/attachments/[^'"\s<>]+""", value):
            url = decode_escaped(match.group(0))
            refs.setdefault(url, PeopleForceAttachmentRef(url=url, name=posixpath.basename(urlparse(url).path)))
    return list(refs.values())


def rewrite_document_attachment_urls(document: KnowledgeDocument, replacements: dict[str, str]) -> int:
    rewritten = 0
    for source_url, local_url in replacements.items():
        if source_url in document.body_html:
            document.body_html = document.body_html.replace(source_url, local_url)
            rewritten += 1
        if source_url in document.body:
            document.body = document.body.replace(source_url, local_url)
            rewritten += 1
    return rewritten


def is_peopleforce_attachment_url(url: str) -> bool:
    if not url or RICH_ATTACHMENT_MARKER not in url:
        return False
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"} and parsed.netloc.endswith("peopleforce.io")


def knowledge_attachment_filename(
    *,
    document: KnowledgeDocument,
    ref: PeopleForceAttachmentRef,
    content_type: str,
    content_disposition: str,
) -> str:
    raw_name = content_disposition_filename(content_disposition) or ref.name or posixpath.basename(urlparse(ref.url).path)
    raw_name = unquote(raw_name).split("?")[0].split("#")[0].strip() or f"peopleforce-{ref.external_id}"
    if "." in raw_name:
        stem, extension = raw_name.rsplit(".", 1)
        extension = f".{re.sub(r'[^0-9A-Za-z]+', '', extension)[:12]}"
    else:
        stem = raw_name
        extension = mimetypes.guess_extension((content_type or "").split(";")[0].strip()) or ""
    safe_stem = slugify(stem, allow_unicode=True) or f"peopleforce-{ref.external_id}"
    return f"{document.id}/{ref.external_id}-{safe_stem[:120]}{extension}"


def content_disposition_filename(value: str) -> str:
    if not value:
        return ""
    match = re.search(r"""filename\*=UTF-8''([^;]+)""", value, flags=re.I)
    if match:
        return unquote(match.group(1).strip().strip('"'))
    match = re.search(r"""filename="?([^";]+)"?""", value, flags=re.I)
    return match.group(1).strip() if match else ""


def trim_header(value: str, max_length: int = 120) -> str:
    return (value or "").split(";")[0].strip()[:max_length]


def decode_escaped(value: str) -> str:
    return value.replace("\\/", "/").replace("\\u0026", "&")


def int_or_zero(value: object) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0
