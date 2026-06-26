from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db.models import Q

from apps.knowledge.models import KnowledgeDocument
from apps.knowledge.peopleforce_attachments import RICH_ATTACHMENT_MARKER, extract_peopleforce_attachment_refs, sync_peopleforce_document_attachments


class Command(BaseCommand):
    help = "Download PeopleForce rich-text knowledge attachments into local media and rewrite document links."

    def add_arguments(self, parser):
        parser.add_argument("--document-id", type=int, default=None, help="Process only one KnowledgeDocument ID.")
        parser.add_argument("--limit", type=int, default=None, help="Stop after N documents with PeopleForce attachment URLs.")
        parser.add_argument("--force", action="store_true", help="Re-download files even if a local KnowledgeAttachment already exists.")
        parser.add_argument("--dry-run", action="store_true", help="Only report matching documents and attachment URLs.")

    def handle(self, *args, **options):
        qs = KnowledgeDocument.objects.filter(
            Q(body__contains=RICH_ATTACHMENT_MARKER) | Q(body_html__contains=RICH_ATTACHMENT_MARKER),
        ).order_by("id")
        if options["document_id"]:
            qs = qs.filter(id=options["document_id"])
        if options["limit"]:
            qs = qs[: options["limit"]]

        scanned = 0
        docs_with_refs = 0
        downloaded = 0
        reused = 0
        failed = 0
        rewritten = 0

        for document in qs:
            scanned += 1
            refs = extract_peopleforce_attachment_refs(document.body_html, document.body)
            if not refs:
                continue
            docs_with_refs += 1
            if options["dry_run"]:
                self.stdout.write(f"#{document.id} {document.title}: {len(refs)} attachment(s)")
                for ref in refs:
                    self.stdout.write(f"  - {ref.name}: {ref.url}")
                continue

            result = sync_peopleforce_document_attachments(document, force=options["force"])
            downloaded += result.downloaded
            reused += result.reused
            failed += result.failed
            rewritten += result.rewritten
            self.stdout.write(
                f"#{document.id} {document.title}: downloaded={result.downloaded}, reused={result.reused}, "
                f"failed={result.failed}, rewritten={result.rewritten}"
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Done: scanned={scanned}, docs_with_refs={docs_with_refs}, downloaded={downloaded}, "
                f"reused={reused}, failed={failed}, rewritten={rewritten}"
            )
        )
