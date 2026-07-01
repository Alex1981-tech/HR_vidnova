# HR Vidnova ↔ CMMS — план інтеграції

> Живий документ. Статуси: ✅ done · 🚧 in progress · ⏳ todo · ⏸ paused.
> Створено 2026-07-01. Останнє оновлення: 2026-07-01.

## Контекст систем

- **HR Vidnova** — Django+React, `/home/serv/hr_vidnova`, прод `https://hr.vidnova.app` (host 172.16.33.14, compose `/root/hr_vidnova`). HR — **майстер даних про людей/структуру**. Живиться з PeopleForce (PF-вебхуки + sunc_v4).
- **CMMS** — FastAPI+React, репо `github.com/Alex1981-tech/CMMS` (branch `master`), прод на host 172.16.33.14 (`/root/CMMS`), backend `:8002→8001` (`ghcr.io/alex1981-tech/cmms/backend`), frontend `:5177`, домен `https://cmms.vidnova.app`. Postgres `:5433`.
  - CI: `.github/workflows/deploy.yml` (GHCR build+deploy), `rollback.yml`.
  - Dev-середовище: `docker-compose.dev.yml` (є! тестувати тут перед прод).
  - Схема БД: **без alembic** — зміни через ad-hoc `update_*_schema.py` скрипти.
  - **Зараз CMMS сам тягне PeopleForce** через APScheduler-крон (`app/services/peopleforce_scheduler.py`, щодня). Employees/departments мають `source` + `peopleforce_id`.
- **HR→CMMS сьогодні**: `apps/assets/cmms_client.py` — тільки читання + `resolve_employee_id` (find-or-create employee по `peopleforce_id`/email при призначенні відповідального).

## Рішення (зафіксовані з Alex 2026-07-01)

1. **Ланцюг істини: PeopleForce → HR → CMMS.** HR — єдиний писач у CMMS. Прямий PF-крон у CMMS **вимкнути**. Ключ join = `peopleforce_id` (є в обох).
2. **Авто-провізіонинг у CMMS**: співробітники, департаменти, локації, посади, підрозділи. Нові/змінені/деактивовані в HR → з'являються/оновлюються в CMMS автоматично.
3. **Історія володіння активу**: новий запис при **будь-якій зміні** відповідального АБО інженера АБО локації. Снапшот стану на момент зміни. «Сдано» = дата наступного запису (авто).

## ⚠️ Безпека (окремо, поза цим планом)

- git-remote CMMS на проді містить **GitHub PAT у відкритому вигляді** в URL. Відкликати токен, перевести remote на SSH/credential helper. НЕ комітити токени.

---

## Phase A — Історія володіння активу (CMMS + HR) — ✅ ЖИВЕ В ПРОДІ (2026-07-01)

CMMS-ендпоінт задеплоєно (2 коміти в `master`: `6adeaf1` базовий + `6143293` creation-row). HR-таблиця підключена й показує реальні дані. Найраніший рядок = «Додано в систему» (зелений бейдж, дата=created_at).

**ВАЖЛИВЕ ВІДКРИТТЯ:** CMMS уже веде окремі history-таблиці — нова модель/write-path НЕ потрібні:
- `asset_location_history` (`location_id` + `location_path` TEXT, роздільник `" / "`, root-first: `Місто / Клініка / Поверх / Кабінет`)
- `asset_responsibility_history` (`responsible_person_id` → **employees**.full_name)
- `asset_engineer_history` (`engineer_id` → **users**.full_name — інженер = CMMS user, НЕ employee!)
- `asset_department_history` (ігноруємо для таблиці)
Історія пишеться в `app/routers/assets.py` (при create ~1100, при update ~1287). Тобто таблицю ЗБИРАЄМО агрегацією.

- ✅ **A3. CMMS endpoint** `GET /api/assets/{id}/ownership-history` — реалізовано в `app/routers/assets.py` (схема `OwnershipHistoryRow` + `get_asset_ownership_history`). Логіка: 3 SELECT-и (location/responsibility/engineer) → злиття подій за `changed_at` → carry-forward → рядок на кожну унікальну мітку часу; `handed_over`=дата наступного рядка; DESC. **Застейджено на хості `/root/CMMS/backend`, НЕ закомічено, НЕ задеплоєно.** Валідовано read-only на активі 907 (3 зміни). Бекап `/tmp/assets.py.bak`.
- ✅ **A4a. HR proxy** `GET /api/assets/{id}/ownership-history/` (`AssetOwnershipHistoryView` + `cmms_client.get_asset_ownership_history`). Graceful: якщо CMMS-ендпоінт ще не живий → 200 `{items:[]}`.
- ✅ **A4b. HR frontend** — таблиця «Історія володіння» внизу сторінки активу (дата·місто·клініка·кабінет·відповідальний·інженер·сдано). Порожній стан «Історія відсутня».
- ✅ **A3-deploy.** Задеплоєно через CI (self-hosted runner, push→master→GHCR→zero-downtime). Смоук ок: 907=3 рядки, 555=2 рядки. `is_creation` на найранішому рядку.
- ✅ **A4c. Creation-row у фронті**: клас `.asset-history-creation` (зелена підсвітка) + бейдж «Додано в систему» в комірці дати.
- ✅ **A5. Backfill** — НЕ потрібен: історія вже пишеться CMMS при кожній зміні; для активів без змін показуємо синтетичний creation-рядок з поточного стану.

**Механіка деплою CMMS (на майбутнє):** репо `Alex1981-tech/CMMS`, гілка `master`. Правки на хості `/root/CMMS`, `git add <file>` (НЕ додавати `backups/` — CI-шум), commit, `git push origin master` → self-hosted runner (`actions.runner.Alex1981-tech-CMMS`) автоматично білдить+пушить GHCR+zero-downtime deploy+healthcheck. Бекапи `/tmp/assets.py.bak*` на хості.

### Борг/нотатки Phase A
- 🐞 HR detail-поле «Відповідальний інженер» (`AssetDetailApiView`/`_enrich_asset`) резолвить `engineer_id` через **employees**, а треба через **users** (інженер=user). Зараз усі engineer_id=null тому непомітно. Виправити при деплої CMMS (додати users-мапу в HR або віддавати engineer_name з CMMS detail).

## Phase A2 — Зони відповідальності (Settings → Основні → «Активи») — ✅ ГОТОВО (2026-07-01)

Рішення Alex (пивот від per-asset до зон): істина щодо відповідального/локації/інженера — у HR; керуємо на рівні **зон**. Зона = скоуп (локація будь-якого рівня: клініка/поверх/кабінет **або** департамент) + **один інженер** (CMMS user). «Застосувати» — кнопкою, bulk-проставляє engineer_id усім активам скоупу (тригерить CMMS engineer-history → видно в таблиці історії володіння).

- ✅ HR модель `AssetResponsibilityZone` (`apps/assets/models.py`, table `asset_responsibility_zones`, міграція 0001) — скоуп location/department + engineer (CMMS user id) + last_applied_at/count.
- ✅ HR API під `/api/assets/zones/`: list/create, `<id>/` put/delete, `options/` (locations tree + departments + engineers=CMMS users), `<id>/apply/` (+`?preview=1` для підрахунку без запису). Scope-збірка: субдерево локації (recursive) або department_ids, пагінація list_assets.
- ✅ Фронт: Settings→Основні→«Активи» (`AssetZonesSettingsView`) — редактор (скоуп-segmented, каскад локації, департамент, інженер) + список зон + «Застосувати» (preview→confirm→apply).
- ✅ `set_asset_engineer` у cmms_client (PUT engineer_id).
- Перевірено: scope кабінет=29 активів, клініка-8=359; UI рендериться. **Реальний apply (запис у прод CMMS) ще не робив** — Alex зробить кнопкою.
- 🔜 Розширення (Alex «потом»): кілька відповідальних на зону; «відповідальний» окрім інженера; у CMMS — юзер бачить свої активи.

### Стан build
- `npm run build` проходить після виправлення типів `TBlockId` в орг-схемі. Попередній stale-warning про падіння `tsc -b` більше не актуальний.

## Phase A3 — Фізична структура (HR-owned) + об'єднання із зонами — 🚧 В РОБОТІ (2026-07-01)

Рішення Alex: HR **володіє** деревом фізичної структури (клініка→поверхи→кабінети), синк → CMMS locations. Об'єднати в одній сторінці «Активи»: будувати структуру + привʼязувати департаменти + призначати інженера (зона) + «Застосувати». Спочатку бекфіл існуючих CMMS-локацій у HR.

- ✅ **Модель** `PhysicalLocation` (`apps/assets/models.py`, table `asset_physical_locations`, міграція 0002): tree (self-parent), `kind` city/clinic/floor/cabinet (+level мапа на CMMS 0-3), `cmms_location_id` (лінк синку), M2M `departments`→employees.Department, `engineer_user_id`/`engineer_name` (CMMS user), order/is_active.
- ✅ **Бекфіл** `python manage.py import_cmms_locations` — імпортовано 115 вузлів (6 city / 3 clinic / 12 floor / 94 cabinet), cmms_location_id проставлено, дерево збережено. Ідемпотентно (матч по cmms_location_id).
- ⏳ **API** CRUD дерева (`/api/assets/physical-locations/`): list(tree)/create/update/delete + attach departments + set engineer.
- ⏳ **HR→CMMS синк вузла**: при create/update PhysicalLocation → створити/оновити CMMS location (POST/PUT `/api/locations/`), зберегти cmms_location_id.
- ⏳ **UI** — переробити сторінку Settings→«Активи»: tree-builder (клініка→поверхи→кабінети, +додати/переймен./видалити), привʼязка департаментів до вузла, вибір інженера, кнопка «Застосувати» (engineer_id на активи субдерева — переніс логіки з `_assets_in_scope`, тепер по cmms_location_id вузла).
- ⏳ **Депрекейт** окремої `AssetResponsibilityZone` (Phase A2) — відповідальність тепер живе на вузлі дерева. Таблиця лишається порожня; UI зон замінюється tree-builder-ом.

### Департамент-баг (2026-07-01) — ✅ FIX
POST `/api/employees/departments/` давав 400 «clinic обов'язкове» коли фронт **опускав** clinic (DRF UniqueTogether робить поле required при omit). Фронт тепер шле `clinic: null` (бекенд дефолтить на активну клініку). `frontend/src/App.tsx` ~payload департаменту.

## Phase B — HR→CMMS майстер-синк (людей/структури) — ⏸ ВІДКЛАДЕНО

Alex переключив пріоритет на зони (Phase A2). Bulk-синк співробітників/департаментів/локацій/посад лишається на потім.

- ⏳ **B1.** Вимкнути PeopleForce-крон у CMMS (`peopleforce_scheduler`), щоб уникнути двох писачів.
- ⏳ **B2. HR push-сервіс**: Django signals на create/update/deactivate `Employee`/`Department`/`Location`/`Position`/`Subdivision` → Celery-таск upsert у CMMS по `peopleforce_id`.
- ⏳ **B3. CMMS upsert-ендпоінти**: employees/departments/locations вже є (POST/PUT). Додати positions/subdivisions за потреби. Ідемпотентний upsert по `peopleforce_id`/external key.
- ⏳ **B4. Reconcile-джоба**: періодичний повний прохід HR→CMMS (ловити пропущені події).
- ⏳ **B5. Backfill**: початковий повний push HR→CMMS + звірка кількостей.
- ⏳ **B6. Cutover + моніторинг** (лічильники, алерти на розсинхрон).

## Зроблено (2026-07-01, до цього плану)

- ✅ Сторінка активу `/assets/:id` (HR): фото-картка + таблиця (інв.№/локація/відповідальний/інженер/опис), галерея-лайтбокс, кнопка «Перейти в CMMS».
- ✅ Detail-ендпоінт HR `GET /api/assets/{id}/` (`AssetDetailApiView`) + збагачення локацією/інженером/департаментом.
- ✅ Обмеження ширини сторінки активів (центрована колонка ~1090px).

## Відкриті питання

- Чи HR веде **локації** (місто/клініка/кабінет) як джерело, чи вони живуть у CMMS? (від цього залежить напрям синку локацій у B2). Уточнити.
- «Підрозділи» (подразделения) — окрема сутність від департаментів у HR? Змапити.
- Політика видалень: hard-delete vs deactivate при звільненні/розформуванні.
