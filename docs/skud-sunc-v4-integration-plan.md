# HR Vidnova: интеграция СКУД на базе sunc_v4

Дата: 2026-06-24  
Источник кода: GitHub `Alex1981-tech/sunc_v4`, private repo, commit `62d79c4`  
Живой сервер: `172.16.33.14`, hostname `vidnova.app`  
Режим проверки: read-only. Секреты, `.env` значения и персональные строки не сохранялись.

## 1. Что сейчас делает sunc_v4

Текущий `sunc_v4` — это не просто "СКУД -> PeopleForce". Фактически это
промежуточный sync-hub:

```text
PeopleForce employees
        |
        v
Users_PUZ
        | \
        |  \ match by employee_number/email/phone
        |   \
        v    v
     UPROX  ZKTeco
        \    /
         \  /
          v
      Events_PUZ
          |
          v
Attendance calculator
          |
          v
PeopleForce timesheet
```

PeopleForce сейчас центральный источник сотрудников и конечная точка для
timesheet. При отказе от PeopleForce этот поток нужно перевернуть:

```text
BAF/Fotopacients employees
        |
        v
HR Vidnova Employee
        |
        v
AccessIdentity links
        |          \
        v           v
     UPROX         ZKTeco
        \           /
         \         /
          v       v
        Raw AccessEvent
              |
              v
      WorkDaySummary / AttendancePeriod
              |
              v
          HR Vidnova UI
```

## 2. Production inventory

На сервере `172.16.33.14` найдены:

- `/opt/sunc_v4` — production volume/config/logs;
- `/home/serv/Sunc_v4` — почти пустой каталог с `logs/monthly_check.log`;
- `/root/sunc_v4_extracted` — распакованный исходник/архив;
- Docker containers:
  - `sunc_v4_app` — `ghcr.io/alex1981-tech/sunc_v4-app:v1.0.19`, running;
  - `sunc_v4_postgres` — `postgres:15`, running/healthy;
  - `sunc_v4_pgweb` — `sosedoff/pgweb:latest`, running;
- supervisor-процессы внутри `sunc_v4_app`:
  - `zkteco_api`;
  - `sync_events`;
  - `sync_users`;
  - `daily_attendance`;
  - `telegram_command_bot`.

Важно: в repo `docker-compose.production.yml` есть отдельный service
`zkteco-api`, но на production `docker ps` его не показывает. По live-процессам
ZKTeco API сейчас запущен внутри `sunc_v4_app` через supervisor. Это drift между
repo и production, его нужно учесть перед миграцией.

## 3. Текущая БД sunc_v4

БД: PostgreSQL `sync_upb`, контейнер `sunc_v4_postgres`.

### Таблицы

`Users_PUZ`:

- `id`;
- `status_pf`;
- `fields_pf`;
- `id_pf`;
- `id_uprox`;
- `id_zkt`;
- `full_name_pf`;
- `email_pf`;
- `email2_pf`;
- `phone_pf`;
- `phone2_pf`;
- `division_pf`;
- `department_pf`;
- `position_pf`;
- `avatar_filename`;
- `date_of_birth_pf`;
- `created_at`;
- `updated_at`;
- `sync_status`;
- `last_sync_at`.

`Events_PUZ`:

- `id`;
- `uprox_token`;
- `user_id_zkt`;
- `punch_type_zkt`;
- `uprox_device_name`;
- `uprox_user_token`;
- `uprox_user_name`;
- `full_name_zkt`;
- `uprox_sender_token`;
- `uprox_sender_name`;
- `uprox_message_name`;
- `timestamp_zkt`;
- `uprox_issued`;
- `created_at`;
- `event_source`;
- `processed`;
- `processed_at`.

### Счетчики на момент проверки

- `Users_PUZ`: 180 записей;
- `Events_PUZ`: 1 245 529 записей;
- пользователи:
  - `employed`: 157;
  - `deleted`: 23;
  - с `id_uprox`: 179;
  - с `id_zkt`: 25;
  - с обоими ID: 24;
- события:
  - `UPROX`: 1 232 155;
  - `ZKT`: 12 428;
  - пустой/unknown source: 946;
- последние события:
  - UPROX: `2026-06-24 06:08:44+00`;
  - ZKT: `2026-06-24 05:56:14+00`;
- за последние 7 дней UPROX дает примерно 0.8-2.8 тыс. событий/день, ZKTeco
  меньше 30 событий/день.

Есть старые UPROX события с `1996-01-01`, поэтому при переносе истории нужен
data-quality фильтр или статус `ignored/suspicious`, а не слепой импорт в табель.

## 4. Код, который стоит переиспользовать

### UPROX event client

Файл: `app/clients/uprox_events_client.py`

Полезное:

- `UproxEventsClient` — клиент UPROX;
- `get_events_batch()` — чтение событий через `EventGetList`, batch до 1000;
- `sync_incremental_events()` — incremental sync от последнего token;
- `map_event_to_db_format()` — mapping сырого события;
- `get_all_employees()` — загрузка сотрудников UPROX.

Нужно изменить:

- не писать в `Events_PUZ`, а писать в HR `AccessEvent`;
- session/auth обернуть в нормальный adapter с метриками;
- убрать логирование payload/ответов с персональными данными;
- хранить raw event JSON отдельно от нормализованных полей.

### ZKTeco client

Файлы:

- `app/clients/zkteco_client.py`;
- `app/zkteco_api/zkteco/services/zk_service.py`;
- `app/zkteco_api/zkteco/controllers/user_controller.py`.

Полезное:

- прямое чтение терминала через pyzk;
- `get_attendance()` — чтение всех событий терминала;
- `get_users()` — чтение пользователей терминала;
- local Flask API для совместимости с текущей логикой.

Риски:

- в коде есть write-операции: create/delete user, enroll, delete template,
  clear attendance. В HR Vidnova их нельзя включать по умолчанию;
- текущий incremental ZKTeco фактически каждый раз читает весь журнал терминала
  и фильтрует по времени. При росте терминала нужно перейти на watermark/id или
  ограниченный polling, если устройство это поддерживает;
- `punch_type` считается ненадежным, текущий расчет использует чередование.

### Attendance calculator

Файл: `app/correct_attendance_calculator.py`

Полезное:

- объединение UPROX + ZKT событий;
- дедупликация событий разных источников;
- коррекция ZKTeco "заикания" в пределах 3 минут;
- обработка ночных смен;
- обработка ошибок "только вход" / "только выход";
- merge overlapping periods.

Нужно изменить:

- перестать возвращать формат PeopleForce `starts_at/ends_at`;
- возвращать доменные `AttendancePeriod` + `AttendanceException`;
- не читать напрямую `Events_PUZ`, а принимать события из HR repository/service;
- сделать правила конфигурируемыми:
  - threshold дублей;
  - minimum shift duration;
  - обработка ночной смены;
  - доверять/не доверять `punch_type_zkt`;
  - рабочие календари/смены.

### Sync services

Файлы:

- `app/sync_events.py` — hourly event ingestion;
- `app/sync_users.py` — sync employees from PeopleForce + matching UPROX/ZKT;
- `app/attendance_processor.py` — daily calculation and push to PeopleForce;
- `app/uprox_manager.py` — обновление UPROX employees из PeopleForce.

Переиспользовать аккуратно:

- из `sync_events.py`: структуру bulk/incremental ingestion;
- из `sync_users.py`: matching по email/phone/employee_number;
- из `attendance_processor.py`: schedule missed days / daily marker concept;
- из `uprox_manager.py`: только как справочник текущих UPROX operations, не как
  runtime-логику MVP.

## 5. Что нельзя переносить как есть

1. PeopleForce как обязательная зависимость.

   Сейчас `Settings._validate_required()` требует `PEOPLEFORCE_BASE_URL` и
   `PEOPLEFORCE_API_TOKEN`. Для HR Vidnova это должно исчезнуть.

2. PeopleForce как source of truth сотрудников.

   В HR Vidnova source of truth: БАФ/Fotopacients + локальные HR-настройки.
   PeopleForce ID можно импортировать только как legacy external reference.

3. Push timesheet в PeopleForce.

   Live logs показывают много ошибок в `daily_attendance_error.log`, в основном
   вокруг PeopleForce API status/422/503. Новый дизайн должен сначала сохранять
   расчет локально и показывать проблемы в UI.

4. UPROX EmployeeSet по расписанию.

   `sync_users`/`uprox_manager` сейчас меняют дополнительные поля и департаменты
   UPROX на основе PeopleForce. Для MVP HR Vidnova лучше сделать UPROX read-only.
   Запись в СКУД включать позже, отдельным feature flag и audit workflow.

5. Логирование персональных payload.

   В текущих логах есть ФИО/email/телефоны/даты рождения. В HR Vidnova logs
   должны хранить IDs/counts/statuses, а не персональные payloads.

## 6. Предлагаемая модель в HR Vidnova

### `Employee`

Основная HR-сущность. Источники: БАФ/Fotopacients, локальный UI.

Ключевые поля:

- `id`;
- `external_baf_id`;
- `external_fotopacients_id`;
- `legacy_peopleforce_id` nullable;
- ФИО;
- email/phone;
- clinic/department/position;
- status;
- hire/dismissal dates;
- manager.

### `AccessSystem`

Справочник систем СКУД:

- `uprox`;
- `zkteco`;
- позже другие.

### `AccessIdentity`

Связь сотрудника с конкретной СКУД:

- `employee_id`;
- `system`;
- `external_user_id`: UPROX token или ZKT user_id;
- `external_card_code`;
- `device_scope` / clinic optional;
- `confidence`: auto/manual/imported;
- `active`;
- `valid_from`, `valid_to`;
- `matched_by`: phone/email/employee_number/manual.

### `AccessDevice`

Справочник устройств:

- source system;
- external device token/id;
- name;
- clinic/location;
- direction hints optional.

### `AccessEventRaw`

Immutable raw event:

- `source`;
- `source_event_id` / token;
- `occurred_at`;
- `employee_identity_id` nullable;
- raw user token/name;
- raw device token/name;
- raw message code/name;
- raw payload JSON;
- `ingested_at`;
- unique constraint по `(source, source_event_id)`.

### `AccessEvent`

Нормализованное событие:

- `employee_id` nullable;
- `occurred_at`;
- `direction`: entry/exit/unknown;
- `source`;
- `device_id`;
- `raw_event_id`;
- `quality`: ok/duplicate/unknown_employee/suspicious_time/ignored.

### `AttendancePeriod`

Период присутствия:

- employee;
- date;
- start_at;
- end_at;
- duration_minutes;
- source_events;
- type: regular/night/manual/fixed/error;
- calculation_run.

### `WorkDaySummary`

Сводка дня:

- employee;
- date;
- planned_minutes;
- actual_minutes;
- first_entry_at;
- last_exit_at;
- status: ok/late/absent/missing_exit/missing_entry/manual_review;
- exception_count;
- calculated_at;
- lock state.

### `TimeAdjustment`

Ручная правка:

- employee;
- date;
- action;
- before/after summary;
- reason;
- author;
- audit log.

## 7. Интеграционный план

### Фаза A: read-only mirror текущего sunc_v4

Цель: быстро показать рабочее время в HR Vidnova без риска сломать текущий
PeopleForce процесс.

Шаги:

1. Добавить в HR Vidnova модели `AccessIdentity`, `AccessEventRaw`,
   `AccessEvent`, `AttendancePeriod`, `WorkDaySummary`.
2. Сделать management command/importer:
   - читает `Users_PUZ` и `Events_PUZ`;
   - импортирует без персональных логов;
   - сохраняет `legacy_peopleforce_id`, `id_uprox`, `id_zkt`;
   - unknown/empty source events импортирует с `source=unknown`.
3. Сопоставить `Users_PUZ` с будущими `Employee` из БАФ/Fotopacients:
   - exact phone;
   - email;
   - legacy PeopleForce ID, если поле еще есть в СКУД;
   - manual review queue для конфликтов.
4. Перенести calculator в HR как чистый service:
   - input: нормализованные events;
   - output: periods + summary + exceptions;
   - без PeopleForce API.
5. UI:
   - табель сотрудника;
   - команда руководителя;
   - список исключений;
   - raw events drill-down.

Результат: HR Vidnova уже показывает рабочее время, но текущий `sunc_v4`
продолжает жить как источник.

### Фаза B: HR Vidnova получает события напрямую

Цель: убрать зависимость от таблиц `sunc_v4`, но пока не отключать старую систему.

Шаги:

1. Вынести UPROX adapter:
   - `Authenticate`;
   - `EventGetList`;
   - incremental token watermark;
   - employee list optional.
2. Вынести ZKTeco adapter:
   - read-only `get_users`;
   - read-only `get_attendance`;
   - no create/delete/clear in MVP.
3. Добавить `IntegrationRun`:
   - source;
   - started/finished;
   - watermark before/after;
   - rows fetched/inserted/ignored;
   - error summary.
4. Запустить HR ingestion параллельно с `sunc_v4` и сравнивать:
   - количество UPROX/ZKT событий по дням;
   - max token/time;
   - расчет summary по 10-20 сотрудникам.
5. После 1-2 недель совпадения сделать HR primary для отображения табеля.

### Фаза C: отключение PeopleForce path

Цель: перестать зависеть от PeopleForce без потери истории.

Шаги:

1. Остановить только PeopleForce write path:
   - `attendance_processor.py` push to PeopleForce;
   - historical resend;
   - PeopleForce timesheet delete/create scripts.
2. Оставить временно:
   - UPROX event sync;
   - ZKT event sync;
   - read-only employee identifiers.
3. Отключить/переписать `sync_users.py`, потому что сейчас он берет сотрудников
   из PeopleForce и обновляет UPROX.
4. Перенести employee source на БАФ/Fotopacients.
5. Зафиксировать архив `sunc_v4` DB dump перед остановкой.

### Фаза D: HR Vidnova владеет СКУД-интеграцией

Цель: `sunc_v4` больше не нужен как runtime.

Шаги:

1. HR Vidnova Celery beat:
   - UPROX sync каждые 5-15 минут или 60 минут на старте;
   - ZKT sync каждые 15-60 минут;
   - daily recalculation в 01:00;
   - missed-days backfill.
2. HR Vidnova UI для:
   - статуса интеграций;
   - max event time;
   - errors;
   - manual rematch employees.
3. Остановить `sunc_v4_app` после acceptance window.
4. Оставить DB dump и readonly archive.

## 8. API/worker дизайн для HR Vidnova

### Celery tasks

- `skud.sync_uprox_events`;
- `skud.sync_zkteco_events`;
- `skud.recalculate_day(employee_id, date)`;
- `skud.recalculate_range(date_from, date_to, employee_ids=None)`;
- `skud.import_sunc_v4_snapshot`;
- `skud.match_access_identities`.

### API endpoints

- `GET /api/time/my/?from=&to=`;
- `GET /api/time/team/?from=&to=&clinic=&department=`;
- `GET /api/time/events/?employee=&date=`;
- `GET /api/time/exceptions/`;
- `POST /api/time/adjustments/`;
- `GET /api/integrations/skud/status/`;
- `POST /api/integrations/skud/sync-now/`;
- `GET /api/integrations/skud/runs/`;
- `GET /api/integrations/skud/identity-matches/`;
- `POST /api/integrations/skud/identity-matches/{id}/resolve/`.

## 9. Data-quality правила

1. Не удалять raw events.
2. Все события до разумной даты запуска клиник помечать `suspicious_time` или
   `ignored`, если они не нужны для истории.
3. `event_source` empty/null из `sunc_v4` импортировать как `unknown` и отдельно
   вывести счетчик.
4. Для ZKTeco `punch_type` считать ненадежным до проверки устройства. Использовать
   текущую логику чередования как default, но сохранить raw punch.
5. Дубликаты UPROX/ZKT в пределах 3-5 минут не удалять физически, а помечать как
   duplicate/merged в расчетном слое.
6. Если сотрудник не найден — событие сохранять с `employee_id=null` и выводить
   в очередь match review.

## 10. Наблюдаемость

Минимум для production:

- dashboard интеграций:
  - last successful run;
  - last UPROX token;
  - last UPROX event time;
  - last ZKT event time;
  - events inserted/ignored;
  - unknown employee events;
  - suspicious events;
- alert, если:
  - UPROX не обновлялся больше 2 часов в рабочее время;
  - ZKT не обновлялся больше 4 часов;
  - event count резко упал;
  - `unknown employee` больше N за день;
  - daily recalculation failed.

## 11. Security notes

- Не переносить `.env` значения в repo или документацию.
- В текущем repo есть sensitive-looking defaults в `config.py`; перед любым
  открытым использованием repo их надо убрать и проверить ротацию.
- `pgweb` на production слушает внешний порт `8081`; стоит закрыть через firewall
  или привязать к localhost/VPN.
- ZKTeco write endpoints должны быть выключены для HR MVP.
- Logs должны редактироваться: без ФИО/email/телефонов/raw payload.
- Доступ к raw events — только HR/admin, не всем руководителям.

## 12. Риски

| Риск | Что сделать |
|---|---|
| PeopleForce сейчас source of truth | Сначала импортировать employees из БАФ/Fotopacients, потом match к СКУД ID |
| UPROX Manager пишет в СКУД | Для MVP сделать UPROX read-only |
| ZKTeco читает весь журнал | Проверить поддержку watermark/limit; пока мониторить runtime |
| Старые UPROX события с 1996 | Mark ignored/suspicious, не включать в табель |
| Персональные данные в логах | Переписать logging до production |
| Production drift repo vs server | Перед миграцией сделать актуальный dump/code snapshot с сервера |
| Ошибки PeopleForce 422/503 | Не делать внешний push в новой системе, хранить расчет локально |

## 13. Ближайшие практические шаги

1. В HR Vidnova добавить backend skeleton и модели СКУД.
2. Сделать one-time importer из `sunc_v4_postgres`:
   - schema-only dry run;
   - counts validation;
   - import 7 дней;
   - import full history после проверки.
3. Перенести `CorrectAttendanceCalculator` как чистый service и покрыть тестами:
   - только вход;
   - только выход;
   - normal entry/exit;
   - night shift;
   - ZKT duplicate scans;
   - UPROX+ZKT overlapping.
4. Сделать UI "Табель" на read-only данных.
5. Сделать экран "Интеграции СКУД" для статуса и ошибок.
6. После уточнения БАФ/Fotopacients employee feed — сделать matcher сотрудников.
7. Параллельно 1-2 недели сравнить HR расчет с текущими PeopleForce timesheet
   результатами, затем отключать PeopleForce path.

## 14. Решение по архитектуре

Рекомендуемый вариант: не тащить `sunc_v4` как отдельный сервис навсегда, а
перенести его полезные части в HR Vidnova:

- UPROX adapter;
- ZKTeco read-only adapter;
- raw event ingestion;
- attendance calculator;
- missed-days scheduler.

`sunc_v4` оставить временным источником истории и контрольной системой на период
параллельной работы. Это уменьшит количество сервисов и уберет PeopleForce из
критического пути.
