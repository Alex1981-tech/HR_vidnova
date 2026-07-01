"""Міграція активів з CMMS у HR (консолідація).

Мапить локацію (PhysicalLocation.cmms_location_id), департамент/відповідального
(через peopleforce_id → HR), інженера (CMMS user → HR Employee за email/ПІБ),
категорію/тип. Фото — завантажує з CMMS /uploads у HR media (--no-photos щоб пропустити).
Ідемпотентно за cmms_asset_id.
"""

from decimal import Decimal, InvalidOperation

import httpx
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand

from apps.assets.cmms_client import CmmsError, cmms_client
from apps.assets.models import Asset, AssetCategory, AssetPhoto, AssetType, PhysicalLocation
from apps.employees.models import Department, Employee


def _dec(value):
    try:
        return Decimal(str(value)) if value not in (None, "") else None
    except (InvalidOperation, ValueError):
        return None


class Command(BaseCommand):
    help = "Мігрує активи (+категорії/типи/фото) з CMMS у HR."

    def add_arguments(self, parser):
        parser.add_argument("--no-photos", action="store_true", help="Не завантажувати фото.")
        parser.add_argument("--limit", type=int, default=0, help="Обмежити кількість активів (тест).")

    def handle(self, *args, **options):
        try:
            self._import_lookups()
            self._build_maps()
        except CmmsError as exc:
            self.stderr.write(f"CMMS error: {exc}")
            return

        no_photos = options["no_photos"]
        limit = options["limit"]
        created = updated = photos_saved = 0
        skip = 0
        page_size = 200
        while True:
            try:
                page = cmms_client.list_assets({"skip": skip, "limit": page_size})
            except CmmsError as exc:
                self.stderr.write(f"CMMS list error at skip={skip}: {exc}")
                break
            items = page.get("items", []) if isinstance(page, dict) else (page or [])
            for item in items:
                asset, was_created = self._upsert_asset(item)
                created += int(was_created)
                updated += int(not was_created)
                if not no_photos:
                    photos_saved += self._sync_photos(asset, item.get("photos") or [])
                if limit and (created + updated) >= limit:
                    break
            if limit and (created + updated) >= limit:
                break
            if len(items) < page_size:
                break
            skip += page_size

        self.stdout.write(self.style.SUCCESS(
            f"Готово: активів створено {created}, оновлено {updated}, фото {photos_saved}."
        ))

    # -- lookups ------------------------------------------------------------
    def _import_lookups(self):
        # Категорії — дерево (subcategories), тому обходимо рекурсивно з побудовою parent+path.
        def walk_cats(nodes, parent_obj, path_prefix):
            for node in nodes or []:
                name = node.get("name") or ""
                path = f"{path_prefix} → {name}" if path_prefix else name
                obj, _ = AssetCategory.objects.update_or_create(
                    cmms_category_id=node["id"],
                    defaults={"name": name, "path": path, "parent": parent_obj},
                )
                walk_cats(node.get("subcategories") or [], obj, path)

        walk_cats(cmms_client.list_categories(), None, "")
        for t in cmms_client.list_asset_types():
            AssetType.objects.update_or_create(
                cmms_asset_type_id=t["id"], defaults={"name": t.get("name") or ""}
            )

    def _build_maps(self):
        self.loc_by_cmms = {p.cmms_location_id: p for p in PhysicalLocation.objects.exclude(cmms_location_id=None)}
        self.cat_by_cmms = {c.cmms_category_id: c for c in AssetCategory.objects.exclude(cmms_category_id=None)}
        self.type_by_cmms = {t.cmms_asset_type_id: t for t in AssetType.objects.exclude(cmms_asset_type_id=None)}

        # Департаменти: cmms dept id → peopleforce_id → HR Department.
        hr_dept_by_pf = {
            str(d.external_peopleforce_id): d
            for d in Department.objects.all() if d.external_peopleforce_id
        }
        self.dept_by_cmms = {}
        for d in cmms_client.list_departments():
            pf = d.get("peopleforce_id")
            if pf is not None and str(pf) in hr_dept_by_pf:
                self.dept_by_cmms[d["id"]] = hr_dept_by_pf[str(pf)]

        # Співробітники (responsible): cmms employee id → peopleforce_id → HR Employee.
        hr_emp_by_pf = {
            str(e.legacy_peopleforce_id): e
            for e in Employee.objects.all() if e.legacy_peopleforce_id
        }
        hr_emp_by_email = {}
        for e in Employee.objects.all():
            for em in (getattr(e, "email", ""), getattr(e, "personal_email", "")):
                if em:
                    hr_emp_by_email.setdefault(em.strip().lower(), e)
        self.resp_by_cmms = {}
        for e in cmms_client.list_employees():
            pf = e.get("peopleforce_id")
            hit = hr_emp_by_pf.get(str(pf)) if pf is not None else None
            if not hit:
                em = (e.get("email") or "").strip().lower()
                hit = hr_emp_by_email.get(em)
            if hit:
                self.resp_by_cmms[e["id"]] = hit

        # Інженери (engineer): cmms user id → HR Employee за email/ПІБ.
        hr_emp_by_name = {(e.full_name or "").strip().lower(): e for e in Employee.objects.all()}
        self.eng_by_cmms = {}
        for u in cmms_client.list_users():
            em = (u.get("email") or "").strip().lower()
            hit = hr_emp_by_email.get(em) if em else None
            if not hit:
                hit = hr_emp_by_name.get((u.get("full_name") or "").strip().lower())
            if hit:
                self.eng_by_cmms[u["id"]] = hit

    # -- asset --------------------------------------------------------------
    def _upsert_asset(self, item):
        defaults = {
            "inventory_number": item.get("inventory_number") or "",
            "name": item.get("name") or "",
            "status": item.get("status") or "",
            "manufacturer": item.get("manufacturer") or "",
            "description": (item.get("description") or "").strip(),
            "tags": item.get("tags") or "",
            "purchase_date": item.get("purchase_date") or None,
            "initial_cost": _dec(item.get("initial_cost")),
            "currency": item.get("currency") or "",
            "category": self.cat_by_cmms.get(item.get("category_id")),
            "asset_type": self.type_by_cmms.get(item.get("asset_type_id")),
            "location": self.loc_by_cmms.get(item.get("location_id")),
            "department": self.dept_by_cmms.get(item.get("department_id")),
            "responsible": self.resp_by_cmms.get(item.get("responsible_person_id")),
            "engineer": self.eng_by_cmms.get(item.get("engineer_id")),
        }
        asset, created = Asset.objects.update_or_create(cmms_asset_id=item["id"], defaults=defaults)
        return asset, created

    def _sync_photos(self, asset, photos):
        saved = 0
        base = cmms_client.base
        for order, photo in enumerate(photos):
            cmms_photo_id = photo.get("id")
            if cmms_photo_id and asset.photos.filter(cmms_photo_id=cmms_photo_id).exists():
                continue
            url = photo.get("url") or photo.get("thumbnail_url")
            if not url:
                continue
            try:
                resp = httpx.get(f"{base}{url}", timeout=30)
                if resp.status_code != 200:
                    continue
                ext = "jpg"
                ct = resp.headers.get("content-type", "")
                if "png" in ct:
                    ext = "png"
                elif "webp" in ct:
                    ext = "webp"
                obj = AssetPhoto(
                    asset=asset,
                    is_primary=bool(photo.get("is_primary")),
                    order=order,
                    cmms_photo_id=cmms_photo_id,
                )
                obj.image.save(f"cmms_{cmms_photo_id or order}.{ext}", ContentFile(resp.content), save=True)
                saved += 1
            except httpx.HTTPError:
                continue
        return saved
