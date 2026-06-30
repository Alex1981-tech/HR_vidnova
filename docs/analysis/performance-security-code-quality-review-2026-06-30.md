# Анализ быстродействия, безопасности и чистоты кода

Дата: 2026-06-30  
Проект: `/home/serv/hr_vidnova`  
Стек: Django/DRF/PostgreSQL/Celery/Redis + React/Vite/TypeScript  
Область: read-only аудит приложения, без изменения бизнес-кода.

## Методика

- Прочитаны workspace memory, `README.md`, `docs/*`, настройки Django, Docker/CI, backend/frontend entrypoints, serializers, permissions, uploads, integrations.
- Использованы skills: `security-best-practices`, `backend`, `frontend`, `code-review`, `tech-debt`, `documentation`.
- Запущены три read-only sub-agent среза: backend security/performance, frontend security/performance, tech-debt/CI/production readiness.
- Выполнены проверки:
  - `python3 manage.py check --deploy` -> 6 security warnings.
  - `npm run build` -> успешный build, но Vite предупреждает о крупном JS chunk.
  - `env DB_ENGINE=sqlite python3 manage.py test -v 1` -> 111 tests, 1 failure.
- Проверен официальный статус Django: текущий pinned `Django==4.2.18`, а Django 4.2 LTS больше не получает security updates после 2026-04-07. На 2026-06-30 поддерживаются Django 5.2 LTS и 6.0 по официальной странице: https://www.djangoproject.com/download/.

## Executive Summary

Проект выглядит как активно развиваемый MVP с уже неплохой доменной декомпозицией backend и большим объемом реализованных HR-функций. Для production с HR/PII данными приложение пока нельзя считать готовым без hardening-фазы.

Главные риски:

1. Dev/public access flags и небезопасные defaults могут открыть HR API без авторизации.
2. Нет role/object-level authorization: обычный authenticated employee потенциально получает слишком широкий доступ к HR API.
3. HR/PeopleForce документы и media сейчас архитектурно близки к публичной раздаче через `/media/`.
4. Raw HTML сохраняется и рендерится через `dangerouslySetInnerHTML`, что дает stored-XSS поверхность.
5. Интеграции хранят и передают слишком много чувствительных payload/header данных.
6. CI сейчас публикует images без обязательных test/security gates.
7. Frontend монолитный: `App.tsx` 22k+ LOC, main JS bundle около 2.0 MB minified.

## Critical Findings

### C1. Production safety gate отсутствует

Evidence:

- `config/settings.py:21-23`: fallback `SECRET_KEY`, `DEBUG` default `True`.
- `config/settings.py:143-156`: secure cookie defaults зависят от `DEBUG`, public read default завязан на `DEBUG`.
- `config/permissions.py:8-13`: `HR_PUBLIC_READ_API` и `HR_PUBLIC_WRITE_API` могут разрешать anonymous read/write.
- `.env.example:1-7`: пример окружения содержит `DEBUG=1`, `HR_PUBLIC_READ_API=1`, `HR_PUBLIC_WRITE_API=1`.
- `python3 manage.py check --deploy`: warnings `security.W009`, `W012`, `W016`, `W018`, `W004`, `W008`.

Impact:

Если такие значения попадут в production или staging с реальными данными, anonymous пользователь сможет читать и изменять HR-ресурсы.

Recommended fix:

- Fail-closed defaults: `DEBUG=False` без явного env override.
- Отдельный `ENVIRONMENT=production`/`DJANGO_ENV=production`.
- Django system check или startup guard: в production приложение не стартует при fallback `SECRET_KEY`, `DEBUG=True`, `HR_PUBLIC_READ_API=True`, `HR_PUBLIC_WRITE_API=True`.
- `.env.example` разделить на `.env.example.dev` и `.env.example.prod`, либо явно пометить dev-only значения.

## High Findings

### H1. Нет role/object-level authorization для HR API

Evidence:

- `config/permissions.py:11-13`: любой authenticated user проходит.
- `apps/employees/views.py:179-180`: общий `EmployeeApiViewSet` использует этот permission.
- `apps/employees/views.py:886-970`: employee-scoped child records фильтруются по query param `employee`, а не по role/object scope.
- `apps/skud/views.py:42-47`, `apps/knowledge/views.py:23-24`, `apps/leave/views.py:12-13`: похожая coarse permission модель.

Impact:

После Telegram login обычный сотрудник может получить доступ к административным HR endpoints, если frontend не скрывает URL достаточно надежно. UI gating не является защитой.

Recommended fix:

- Ввести роли: `hr_admin`, `hr_manager`, `manager`, `employee`, возможно отдельные `compensation_admin`, `documents_admin`.
- Разделить admin APIs и self-service APIs.
- В queryset фильтровать scope до сериализации.
- Добавить negative API tests: self не читает чужие документы/контакты/заметки; manager видит только подчиненных; HR role required для справочников и массовых действий.

### H2. HR документы/media раздаются как public static media

Evidence:

- `frontend/nginx.conf:45-49`: `/media/` alias без auth, `expires 7d`.
- `apps/employees/serializers.py:510-518`: `EmployeeDocumentSerializer.get_file_url()` возвращает прямой `local_file.url`.
- `apps/employees/models.py:525-530`: employee documents хранятся в `peopleforce_employee_documents/%Y/%m/`.

Impact:

Документы из PeopleForce/HR с PII доступны любому, кто получил URL; URL может попасть в логи, историю браузера, chat, external referrer.

Recommended fix:

- Разделить public media и private HR media.
- Для employee documents не отдавать raw file URL в serializer.
- Download/preview только через authenticated endpoint с object-level permission.
- В nginx использовать `internal` location + `X-Accel-Redirect` или отдавать stream из Django для MVP.

### H3. Upload policy слишком широкая

Evidence:

- `apps/employees/views.py:790-792`: комментарий говорит "будь-які типи".
- `apps/employees/views.py:813-825`: до 10 файлов по 200 MB сохраняются как документы.
- `apps/employees/views.py:847-862`: preview может inline-отдавать image/video/audio/text.
- `apps/employees/views.py:26-49`: previewable text extensions включают `html`, `js`, `php`, `sql`, `tsx`, etc. Они отдаются как `text/plain`, что лучше HTML, но политика все равно слишком широкая для HR docs.

Impact:

Риск disk DoS, malware storage, unsafe content previews, дальнейшего leakage через public `/media/`.

Recommended fix:

- Allowlist MIME/extensions по типам HR-документов.
- Magic-byte/content sniffing.
- Quarantine/AV scan или хотя бы async validation.
- Меньшие лимиты по умолчанию; большие файлы через отдельный flow.
- Inline preview только для PDF/images после проверки; остальное download attachment.

### H4. Stored HTML/XSS boundary не централизован

Evidence:

- `apps/announcements/serializers.py:55-68`: `body_html` writable.
- `apps/employees/serializers.py:1025-1031`: employee note `body_html` writable.
- `apps/knowledge/serializers.py:160`: knowledge `body_html` writable.
- `frontend/src/App.tsx:2608`, `frontend/src/App.tsx:8473`, `frontend/src/App.tsx:13646`: render через `dangerouslySetInnerHTML`.
- `frontend/src/App.tsx:2264-2315`: `prepareAnnouncementHtml()` парсит HTML через `template.innerHTML`.

Compensating controls:

- В `App.tsx:850-875` есть локальный sanitizer для части knowledge HTML, но он не является общим backend boundary.

Impact:

Stored XSS против HR пользователей. Для session-auth приложения с PII это high impact.

Recommended fix:

- Backend sanitizer на serializer/model boundary для announcements, notes, knowledge.
- Frontend sanitizer как defense-in-depth, но не основной trust boundary.
- URL allowlist: `https:`, `mailto:`, `tel:` и безопасные relative `/media/` только там, где это допустимо.
- Regression tests на `<script>`, `onerror`, `style`, `iframe`, SVG, `javascript:`.
- CSP в report-only, затем enforce.

### H5. PeopleForce attachment downloader может утечь credentials / SSRF

Evidence:

- `apps/knowledge/peopleforce_attachments.py:79-84`: `X-API-KEY` и `Cookie` добавляются в headers общего `httpx.Client`.
- `apps/knowledge/peopleforce_attachments.py:95-99`: `client.get(ref.url)` ходит по URL из imported rich text.
- `apps/knowledge/peopleforce_attachments.py:151-165`: regex принимает любые `https?://.../rich_text/attachments/...`.

Impact:

Если imported/edited rich text содержит внешний URL с похожим path, backend отправит PeopleForce credentials на чужой host. Также возможны SSRF-попытки.

Recommended fix:

- Exact host allowlist: только ожидаемый PeopleForce origin.
- Credentials добавлять только после проверки host/scheme.
- Блокировать private/link-local IP, redirects на чужой origin.
- Stream download с max bytes до чтения всего тела.
- Tests: malicious host не получает credentials; redirect на private IP fail closed.

## Medium Findings

### M1. PeopleForce webhook fail-open по умолчанию

Evidence:

- `apps/integrations/webhook_views.py:60-62`: no DRF auth.
- `apps/integrations/webhook_views.py:84-93`: invalid signature отклоняется только если `PEOPLEFORCE_WEBHOOK_ENFORCE=True`.
- `config/settings.py:199-200`: enforce default `false`.

Impact:

Внешний отправитель может триггерить light sync и засорять audit/logs.

Recommended fix:

- В production fail-closed: secret required, invalid signature -> 401/403.
- Throttle by IP/source; alert на invalid signatures.
- Не хранить лишние headers/payload без redaction.

### M2. Integration logs становятся вторичным PII/secrets хранилищем

Evidence:

- `apps/integrations/models.py:104-107`: request/response payload JSON fields.
- `apps/integrations/peopleforce_compat.py:227-247`: request log сохраняет query/body/response payload.
- `apps/integrations/webhook_views.py:74-80`: webhook payload и headers сохраняются почти полностью, кроме cookie.

Impact:

Даже если основные таблицы защищены, log tables могут содержать PII, auth-like headers, employee emails/phones/birth dates.

Recommended fix:

- Хранить ids, counters, status, hashes вместо raw payloads.
- Redact headers: `authorization`, `x-api-key`, `cookie`, `set-cookie`, proxy auth.
- TTL cleanup management command + scheduled Celery beat.

### M3. Rate limit доверяет spoofable `X-Forwarded-For`

Evidence:

- `apps/access/views.py:30-34`: берет первый `HTTP_X_FORWARDED_FOR`.
- `frontend/nginx.conf:23-25`: nginx append-ит `$proxy_add_x_forwarded_for`.
- `apps/access/views.py:90-100`: rate limit key строится из phone + client IP.

Impact:

Атакующий может подставлять XFF, обходя per-IP throttle и загрязняя audit IP.

Recommended fix:

- На edge strip inbound XFF.
- В Django использовать trusted proxy parsing либо `REMOTE_ADDR`.
- Добавить verify-code throttle по phone, employee/user, real IP.

### M4. BasicAuthentication включен глобально

Evidence:

- `config/settings.py:164-168`: `SessionAuthentication` + `BasicAuthentication` в DRF default.
- `config/urls.py:20`: `AuthStatusView` тоже принимает Basic.

Impact:

Password-based path расширяет brute-force surface и может обходить ожидаемый Telegram/session UX.

Recommended fix:

- Disable BasicAuth в production.
- Если нужен internal/debug доступ, включать только явно для internal endpoints и только при `DEBUG`.

### M5. Hot paths без достаточных bounds/DB aggregation

Evidence:

- `apps/skud/views.py:87-93`: company attendance принимает range без max cap.
- `apps/skud/views.py:131-156`: periods грузятся и merge-ятся в Python для выбранной страницы.
- `apps/dashboard/views.py:85-120`, `167-205`, `258-315`: reports грузят employee rows в Python и считают месяцы циклом.
- `apps/projects/views.py:123-132`: `started_at__date` фильтр в time entries.

Impact:

При росте истории и сотрудников API-индуцированная нагрузка будет расти нелинейно; `__date` может обходить индексы.

Recommended fix:

- Range validation: default 1 month, max 62/92 days.
- DB aggregates/materialized summaries для reports.
- Для datetime использовать `[from_start, to_end)` вместо `__date`.
- Добавить indexes на hot filters: `(employee, date, start_at)`, time entry `(employee, started_at)`, `(project, started_at)`.

### M6. Full PeopleForce import в одной transaction

Evidence:

- `apps/integrations/peopleforce/importer.py:131-136`: `_run()` wrapped in `transaction.atomic()` for non-dry-run.
- `apps/integrations/tasks.py:67-78`: full sync включает documents, knowledge, timesheet, downloads.
- `apps/integrations/peopleforce/importer.py:1176-1188`: document file download выполняется во время importer flow.

Impact:

Долгие transactions, lock contention, rollback amplification, DB bloat. По memory full timesheet import уже занимал около 40 минут.

Recommended fix:

- Fetch/cache outside global transaction.
- Commit per entity/batch.
- Idempotent checkpoints и resume.
- Downloads в отдельные Celery jobs.

## Frontend Findings

### F1. Frontend монолит и крупный bundle

Evidence:

- `frontend/src/App.tsx`: 22,550 LOC.
- `frontend/src/styles/index.css`: 20,141 LOC.
- `npm run build`: `dist/assets/index-*.js` 2,007.89 kB minified / 569.86 kB gzip; Vite warning `Some chunks are larger than 500 kB`.

Impact:

Медленный cold start, сложный code review, высокая вероятность регрессий при изменениях в одном файле.

Recommended fix:

- Route-level `React.lazy`.
- Выделить domains: people, knowledge, attendance/skud, leave, announcements, settings, reports, projects.
- Lazy-load TipTap, Recharts/reports, org graph.
- В CI добавить bundle budget.

### F2. Raw/duplicated fetch bypasses shared API client

Evidence:

- `frontend/src/api/client.ts:366-380`: основной client делает CSRF priming и `credentials: include`.
- `frontend/src/views/settings/PeopleDataSettingsView.tsx:92-100`, `frontend/src/views/reports/shared.tsx:41`, `frontend/src/App.tsx:5913`: отдельные raw fetch paths.

Impact:

Несогласованные CSRF, error handling, auth redirect, API base behavior.

Recommended fix:

- Export shared `request()` или typed hooks из `api/client.ts`.
- CI check: protected `fetch(` outside client запрещен, кроме явно allowlisted public cases.

### F3. Optimistic/fallback UI может показывать ложный успех

Evidence from sub-agent:

- `frontend/src/App.tsx` paths around leave/time-correction submit and reactions/comments swallow errors or create local submitted state.

Impact:

Сотрудник может считать request отправленным, хотя backend отверг/потерял его.

Recommended fix:

- No fabricated success on catch.
- Inline/toast error states.
- Re-fetch after confirmed success.

## CI, Tests, Dependencies

### T1. CI публикует images без quality gates

Evidence:

- `.github/workflows/build.yml:33-55`: build & push backend/frontend images.
- Нет steps для `manage.py check`, migrations check, tests, frontend build before publish beyond Docker build, dependency audit.

Impact:

Broken tests или missing migrations могут попасть в GHCR/prod.

Recommended fix:

- До publish: backend check, `makemigrations --check --dry-run`, tests, frontend `npm ci`, `npm run build`.
- Отдельный deploy job после зеленых checks.
- Использовать SHA tags для deploy, не только `latest`.

### T2. Tests currently fail

Command:

```bash
env DB_ENGINE=sqlite python3 manage.py test -v 1
```

Result:

- 111 tests run.
- Failure: `apps.projects.tests.ProjectApiTests.test_filter_q`.
- Assertion expected `{"Маркетинг"}`, got no matching row.

Likely cause:

- `apps/projects/views.py:38-40` uses `name__icontains=q`; SQLite collation/LIKE behavior for Cyrillic lowercase may not match as expected.

Recommended fix:

- Normalize search or use DB-specific tested behavior; add regression for Cyrillic case-insensitive search on intended production DB.

### T3. Dependency posture

Evidence:

- `requirements.txt:1`: `Django==4.2.18`.
- Official Django download page lists 4.2 LTS under unsupported previous releases after 2026-04-07.
- `frontend/package.json` has no `lint`, `test`, or audit scripts.

Recommended fix:

- Upgrade to supported LTS, preferably Django 5.2 LTS for conservative path.
- Add Dependabot/Renovate.
- Add `pip-audit`/`npm audit` as scheduled or CI advisory gate.

## Code Cleanliness / Maintainability

### K1. Large files

- `frontend/src/App.tsx`: 22,550 LOC.
- `frontend/src/styles/index.css`: 20,141 LOC.
- `apps/integrations/peopleforce/importer.py`: 1,655 LOC.
- `apps/employees/views.py`: 1,275 LOC.
- `apps/employees/serializers.py`: 1,105 LOC.

Recommended direction:

- Split by domain modules before adding more features.
- Keep serializers/viewsets thin; move domain rules to services.
- Add typed API layer and route-local components.

### K2. Tracked backup/generated artifacts

Evidence:

- `frontend/src/styles/index.css.bak-2026-06-25` is tracked.
- Local ignored artifacts exist: `frontend/dist`, `db.sqlite3`, `.playwright-cli`, `frontend/node_modules`.

Recommended fix:

- Remove tracked backup after review or move to docs/patches if intentionally preserved.
- Keep generated artifacts ignored.

### K3. Docs drift

Evidence:

- `README.md:55+` still says to generate first migrations, although migrations are committed.
- Production auth runbook exists under ignored `docs/авторизация/`.

Recommended fix:

- Update onboarding docs to `python manage.py migrate`.
- Move sanitized runbooks into tracked docs path that excludes PII.

## Positive Notes

- `CsrfViewMiddleware`, `SecurityMiddleware`, `XFrameOptionsMiddleware` are present.
- Main frontend API client does CSRF cookie priming and sends `X-CSRFToken`.
- Access/Telegram auth has hashed login codes, expiry, attempt limits, audit events, transaction locks.
- Many backend models already have indexes/unique constraints for SKUD and integration entities.
- `.gitignore` protects `.env`, local DB, dist, media, staticfiles, Playwright logs, and external PII docs.

## Verification Log

```text
git status --short
 M apps/employees/models.py
 M apps/employees/serializers.py
 M apps/employees/views.py
 M frontend/src/types/api.ts
?? apps/employees/migrations/0034_employeecertificate_attachment_name_and_more.py
```

These were pre-existing/user changes at report write time and were not modified by this analysis.

```text
python3 manage.py check --deploy
System check identified 6 issues (0 silenced):
security.W004, W008, W009, W012, W016, W018
```

```text
npm run build
success, with Vite large chunk warning:
JS 2,007.89 kB minified / 569.86 kB gzip
CSS 370.07 kB minified / 58.64 kB gzip
```

```text
env DB_ENGINE=sqlite python3 manage.py test -v 1
111 tests, 1 failure:
apps.projects.tests.ProjectApiTests.test_filter_q
```

### Production verification (2026-06-30, дополнение)

Проверены реальные значения на проде `hr.vidnova.app` (172.16.33.14), чтобы отделить активные дыры от теоретических defaults:

```text
prod .env (значения булевых флагов, не secrets):
  DEBUG=False
  HR_PUBLIC_READ_API=False
  HR_PUBLIC_WRITE_API=False
  PEOPLEFORCE_WEBHOOK_ENFORCE=true

curl анонимно:
  GET /api/employees/employees/   -> HTTP 403   (HR API закрыт)
  GET /media/employee_avatars/... -> HTTP 200   (media отдается без auth)
```

Корректировки к выводам:

- **C1 (safety gate) и M1 (webhook fail-open):** на проде уже сконфигурированы безопасно. Это не активная утечка, а отсутствие fail-closed defaults / startup guard. Executive summary («могут открыть HR API без авторизации») описывает риск мисконфига, а не текущее состояние.
- **H2 (public media):** подтверждена как **активная** утечка — любой `/media/...` (включая employee documents и вложения сертификатов) отдается анонимно с 200. Это приоритет №1 после safety gate.
- **T2 (failing test):** `test_filter_q` падает из-за SQLite (нет Unicode case-folding для кириллицы в `LIKE`/`icontains`); на Postgres-проде корректно. Не прод-баг, а несоответствие тест-БД.

См. обновленные приоритеты в `refactoring-and-structure-improvement-plan-2026-06-30.md`.

