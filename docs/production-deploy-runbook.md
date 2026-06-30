# Production deploy runbook

HR Vidnova: `https://hr.vidnova.app` — хост **vidnova.app (172.16.33.14)**, compose
`/root/hr_vidnova` (GHCR-образы + watchtower + my-tunnel). Django-сервис в проде
называется `web`.

## Пайплайн

`git push` → GitHub Actions собирает образ → пушит в GHCR → watchtower на проде
автоматически подтягивает новый образ. Ручной деплой:
`docker compose -f docker-compose.prod.ghcr.yml pull web && ... up -d web`.

## Production safety gate (P0)

При `ENVIRONMENT=production` приложение **не стартует** (`ImproperlyConfigured`),
если конфигурация небезопасна. Логика — `config/safety.py`
(`production_safety_problems`), проверка — в конце `config/settings.py`.

Гейт блокирует старт, если:

- `DEBUG=True`
- `SECRET_KEY` пустой или равен dev-fallback (`dev-insecure-change-me`)
- `HR_PUBLIC_READ_API=1`
- `HR_PUBLIC_WRITE_API=1`

В dev (`ENVIRONMENT=development`, по умолчанию) гейт неактивен — небезопасные
значения допустимы для удобства разработки.

## Обязательные env в production (значения НЕ хранить здесь — только в проде)

| Переменная | Production-значение | Зачем |
|---|---|---|
| `ENVIRONMENT` | `production` | Включает safety gate |
| `DEBUG` | `0` (или пусто) | Без отладки/трейсбеков |
| `SECRET_KEY` | длинный случайный секрет | Подпись сессий/CSRF |
| `HR_PUBLIC_READ_API` | `0` | Закрыть анонимное чтение API |
| `HR_PUBLIC_WRITE_API` | `0` | Закрыть анонимную запись |
| `ALLOWED_HOSTS` | `hr.vidnova.app` (+ нужные) | Host header |
| `CSRF_TRUSTED_ORIGINS` | `https://hr.vidnova.app` | CSRF за TLS-прокси |
| `CORS_ALLOWED_ORIGINS` | `https://hr.vidnova.app` | CORS |
| `SESSION_COOKIE_SECURE` / `CSRF_COOKIE_SECURE` | по умолчанию `not DEBUG` → `1` | Cookies только по https |
| `USE_X_FORWARDED_PROTO` | по умолчанию `not DEBUG` → `1` | За nginx/Cloudflare tunnel |
| `DB_*`, `REDIS_URL`, `CELERY_*` | прод-значения | БД/брокер |
| `PEOPLEFORCE_WEBHOOK_ENFORCE` | `true` | Проверка подписи вебхука PF |
| `PEOPLEFORCE_WEBHOOK_SECRET` | секрет PF | HMAC вебхука |

Секреты (`SECRET_KEY`, `DB_PASSWORD`, `PEOPLEFORCE_*`, `HR_BOT_API_SECRET`,
`TELEGRAM_BOT_TOKEN`, `CMMS_API_PASSWORD`) задаются только в `.env` на проде, в git
не коммитятся.

## Активация safety gate на существующем проде

1. Задеплоить код с гейтом (этот релиз).
2. Убедиться, что прод уже сконфигурирован безопасно
   (`DEBUG=False`, `HR_PUBLIC_READ_API/WRITE_API=False` — проверено 2026-06-30).
3. Добавить `ENVIRONMENT=production` в прод `.env`.
4. Перезапустить `web`. Если конфиг небезопасен — контейнер упадёт на старте с
   понятным сообщением (это и есть цель): исправить env и повторить.

## Проверка

```bash
# анонимный запрос к API должен быть 401/403
curl -s -o /dev/null -w '%{http_code}\n' https://hr.vidnova.app/api/employees/
```

Юнит-тесты гейта и permission-класса: `python manage.py test config`
(`DB_ENGINE=sqlite`, 10 тестов).
