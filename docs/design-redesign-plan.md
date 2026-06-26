# HR Vidnova — План редизайну фронтенду

> Ціль: щільний, легкий, сучасний UI з якісною мобільною адаптацією. Правила/токени — у `design-system.md`. Цей файл — як туди дійти без ризику зламати прод.
> Легенда статусів: ⬜ todo · 🚧 in-progress · ✅ done.

## Контекст / діагноз (аудит 2026-06-26)

`frontend/src/styles/index.css` = **~12 900 рядків**, виросло органічно. `App.tsx` = **~14 600 рядків** (моноліт, усі сторінки інлайн). Конкретні болі:

- **Типографіка:** 27+ різних `font-size` (8…56px, включно з 12.5/13.5/11.5px). Нестандартні ваги **650/550/750**, надлишок 600/700/800 → «важкий» вигляд.
- **Відступи:** ad-hoc 7/9/11/13/18/22px — без шкали.
- **Дублі:** `.primary-action`×3, `.secondary-action`×4, `.icon-button`×3, `.panel`×3, `.nav-button`×2 — у різних місцях файлу, незрозуміла каскадність.
- **Темна тема:** **203 `!important`**, розкидані 946–1160 та 11430–12084.
- **Page header роздутий:** min-height 66 + h1 24px + margin-bottom 18 = багато повітря.
- **Mobile:** лише 3 брейкпойнти (1280/980/620); порожній планшетний діапазон 768–1024; таблиці — тільки горизонт-скрол, без stacked-cards.
- **Токени:** є 74 (майже всі — кольори); **немає** шкал spacing/type/weight/radius/shadow/z-index.

Ключові локації: sidebar 1592–1703 · topbar 1794–1805 · page-header 2004–2031 · таблиці 3080–3240 · кнопки 1833–1851/1869–1878/10815–10834 · dark 946–1160/11430–12084 · @media 10911/10932/11264/11297.

---

## Стратегія

**Token-first, incremental.** Не переписуємо 13k рядків за раз. Вводимо шар токенів, потім **звужуємо** ad-hoc значення до токенів find-replace'ом найгірших офендерів. 80% ефекту «щільніше/легше» дають типографіка + page-header + ваги.

Деплой як звично: git push → CI → GHCR → watchtower (прод 172.16.33.14). Кожна фаза — окремий коміт, перевірка візуально, тоді наступна. **Без eager-push** — пушимо коли Alex скаже.

---

## Поточний стан (2026-06-26)

- ✅ Фази 0–3 виконані і задеплоєні за журналом нижче: `tokens.css`, типографіка/ваги, кнопки/панелі, desktop-щільність таблиць.
- 🚧 Фаза 4 виконана частково: sidebar/topbar стали щільніші, але потрібен контрольний прохід по z-index, sticky/topbar/drawer шарах і активних станах.
- 🚧 Фаза 5 виконана частково як mobile-polish: інпути 16px на телефоні, частина touch targets, частина існуючих drawer/grid патернів. Не закрито: attendance stacked-cards, filters bottom-sheet, modal/full-screen sheets.
- ⬜ Фаза 6 не почата: dark theme досі має baseline **203 `!important`**.
- ⬜ Фаза 7 не почата: `App.tsx` і `index.css` залишаються монолітами.
- Поточний CSS-аудит: `!important` = 203; raw `font-size` офендери ще є; `font-weight > 600` лишився в inline CSS всередині `App.tsx`.

## Stop / Go перед наступними фазами

- Перед новими mobile/dark змінами зробити clean checkpoint: attendance/skud зміни окремо зафіксувати або явно відокремити від редизайну. Не змішувати `apps/skud/*`, attendance-detail і mobile-redesign в один коміт.
- Перед Phase 5.2+ перевірити `git status --short` і список файлів у коміті. У коміт фази дизайну мають входити тільки пов'язані frontend/docs файли.
- Якщо треба чіпати `App.tsx`, спочатку визначити ownership блоку: attendance, people, filters, shell або modal. Не редагувати сусідні unrelated секції.
- Якщо в фазі збільшується кількість `!important`, raw hex або `font-weight > 600`, це має бути явно пояснено в журналі.

## Критерії приймання для кожної UI-фази

Команди:
- `npm run build` у `frontend/`.
- Якщо зачеплено backend/API: `python3 manage.py check` + вузькі тести відповідного app.
- Якщо зачеплено auth/session/API-client: smoke `/api/auth/status/` і сценарій авторизованого користувача.

Візуальна матриця:
- Routes: `/people`, `/attendance`, `/attendance/employees/:id`, `/knowledge`, `/settings`, `/dashboard`, `/login`.
- Viewports: 1440 desktop, 1280 desktop, 1024 tablet, 768 tablet, 390 mobile, 360 mobile.
- Теми: light + dark для сторінок, які зачепила фаза.
- Для production deploy: зафіксувати commit SHA, GitHub Actions run, факт оновлення watchtower/контейнера, smoke `https://hr.vidnova.app/` і 1–2 ключових routes.

UX/a11y:
- Немає випадкового horizontal scroll на 360px, крім явно задокументованого table-scroll fallback.
- Drawer/sheet/modal: Esc закриває, scrim закриває, focus не губиться, body scroll lock працює.
- Кожен interactive має видимий focus і touch target ≥44px на mobile.
- Loading/empty/error/disabled стани не ламають висоту таблиць, тулбарів і карток.
- Кирилиця читається при browser zoom 125%; цифри у табличних числових колонках рівні (`tnum`).

CSS-аудит:
- `rg -c "!important" frontend/src/styles/index.css` не збільшується; Phase 6 target `<20`.
- `rg -n "font-weight:\\s*(7|8|9|650|550|750)" frontend/src/styles/index.css frontend/src/App.tsx` має повертати 0 або лише задокументовані legacy винятки.
- `rg -n "font-size:\\s*(56|42|34|30|28|26|25|24|23|22|19|18|17|15|13\\.5|12\\.5|11\\.5)px" frontend/src/styles/index.css frontend/src/App.tsx` має зменшуватись або не рости.
- Новий CSS для компонентів: tokens only для кольорів, spacing, radius, font-size, shadow. Raw px допустимі тільки для 1px hairline, intrinsic icon size або тимчасового legacy fallback з коментарем.

## Технічні рішення перед mobile/dark

- Breakpoint tokens у CSS custom properties не можна напряму використовувати в `@media`. Поки не додано PostCSS custom-media, використовуємо literal `@media (max-width: 640px)` з коментарем `/* --bp-sm */`.
- Додати z-index шкалу в tokens/design-system перед drawer/modal роботами: sticky, topbar, dropdown, drawer, modal, toast. Без цього drawer/filter/modal будуть перетинатися випадково.
- Dark theme не залишати тільки на фінал: кожна нова mobile/sheet/modal правка одразу має light/dark перевірку. Phase 6 — cleanup старого dark override шару.

## Фази

### Фаза 0 — Токени (фундамент) ✅
- Створити `frontend/src/styles/tokens.css` з усіма токенами з `design-system.md` (`:root` + `[data-theme="dark"]`). Імпортувати **першим** перед `index.css`.
- Поки що нічого не ламає — лише додає змінні. Перевірити, що збірка проходить (`tsc -b`, vite build).
- **Виграш:** база для всього далі. Ризик: нульовий.

### Фаза 1 — Типографіка + ваги (найбільший візуальний виграш) ✅
- Find-replace найгірших офендерів на токени:
  - `56/42/34/30/28/26px` → `--font-display`/`--font-h1` (auth-hero окремо).
  - `24/23/22/20px` (заголовки) → `--font-h1` (20).
  - `18/17/16px` → `--font-h2`.
  - `15/14px` body → `--font-body` (13) або `--font-h3` за контекстом.
  - `13.5/12.5/11.5px` → найближчий токен.
- Ваги: `650→600`, `550→500`, `750/800/900→600`. **Прибрати всі 700+** (крім явного винятку).
- **Page header:** h1 24→20, min-height 66→56, margin-bottom 18→12 (економить ~60–90px/сторінку).
- Перевірити People / Attendance / Assets / Org / Dashboard візуально.
- Legacy cleanup: старі raw font-size прибирати при дотику до фічі; нові компоненти тільки через tokens.

### Фаза 2 — Консолідація кнопок/панелей ✅
- Звести `.primary-action`/`.secondary-action`/`.icon-button`/`.toolbar-button` у **один** блок кожен (видалити дублі з 10774–10934). Привести до spec §4 (h32/sm28, padding-токени, ваги 500/600).
- `.panel`/картки → radius-md, shadow-xs, padding `--space-5`, бордер `--border`.
- Прибрати «прозорі кнопки» системно (фікс controls-row був точковим — тепер через токени).

### Фаза 3 — Таблиці + щільність ✅
- Ввести `[data-density]` на обгортку таблиць, default `compact` (row 40, header 38, cell 8×12).
- Заголовки колонок → 11/500 uppercase muted. Числові колонки → праворуч + `tnum`.
- (Опц.) user-toggle щільності з persist у localStorage.
- Mobile stacked-cards не входить у цю фазу; це Phase 5.2.

### Фаза 4 — Sidebar / Topbar 🚧
- Sidebar → spec §4 (240/rail56, nav-item h36/13px, group-labels). Topbar h52, search h32, avatar 28.
- Узгодити активний стан (`--primary-soft`).
- Додати z-index шкалу і перевірити накладання: topbar, sticky header, dropdown, drawer, modal.
- Приймання: sidebar collapsed/expanded, topbar actions, active nav, search, avatar; desktop 1440/1024 + mobile 390.

### Фаза 5 — Мобільна адаптація 🚧
Розбити на окремі коміти, не робити одним великим diff.

#### Phase 5.1 — Mobile polish base ✅
- Інпути 16px <640 (анти-iOS-zoom).
- Touch targets кнопок на телефоні.
- Перевірити існуючі drawer/grid патерни.

#### Phase 5.2 — Attendance mobile ⬜
- `/attendance` company table → stacked cards <640 або явно контрольований horizontal-scroll fallback.
- `/attendance/employees/:id` calendar/list/day drawer: без горизонтального overflow на 360, drawer поверх контенту, actions доступні пальцем.
- Приймання: click row → detail, click day → drawer, create/edit/delete record, custom delete modal, keyboard focus.

#### Phase 5.3 — People / shared tables mobile ⬜
- People table/card fallback <640: avatar+name header, position/department/location як label/value, row actions через `⋯`.
- Зберегти search, filters, pagination, selected/hover/focus стани.

#### Phase 5.4 — Filters bottom-sheet ⬜
- Фільтри <768 → bottom sheet: drag handle, max-h 85vh, sticky footer Reset/Apply, scroll lock, Esc/scrim close.
- Не ламати desktop right drawer для фільтрів.

#### Phase 5.5 — Modal/form sheets ⬜
- Модалки <640 → full-screen або bottom sheet залежно від контенту.
- Forms: sticky action-bar, safe-area, labels/helper/error readable, inputs 16px.

#### Phase 5.6 — Responsive QA ⬜
- Повна матриця viewports/routes з критеріїв приймання.
- Зафіксувати screenshots before/after для People + Attendance + Login.

### Фаза 6 — Темна тема (прибрати !important-спам) ⬜
- Винести dark у `dark-theme.css` через токени (`[data-theme="dark"]` перевизначає змінні, а не кожне правило). Ціль: <20 `!important` замість 203.
- Робити як cleanup phase з baseline counters: до/після `!important`, hardcoded dark colors, contrast spot-check.
- Не переносити light semantic soft tokens у dark напряму; кожен semantic soft має dark variant.

### Фаза 7 — Розбити моноліти ⬜
- `App.tsx` (14k) → фіче-модулі (People/Attendance/Assets/Org/Calendar/Knowledge) з локальним скоупом стилів.
- `index.css` → партіали по фічах + спільні tokens/base/components.
- Не блокувало перші фази, але перед великими JSX mobile змінами бажано винести хоча б `Attendance`, `People`, shared `Shell`, `Table`, `Modal/Drawer` helpers.

---

## Порядок виконання (рекомендований)
Закрито: Фаза 0 → 1 → 2 → 3 → частково 5.1.

Далі: clean checkpoint attendance/skud → Фаза 4 контрольний прохід → Phase 5.2 Attendance mobile → Phase 5.3 People/shared tables → Phase 5.4 Filters → Phase 5.5 Modal/form sheets → Phase 5.6 QA → Phase 6 dark cleanup. Phase 7 — поступово, але не відкладати після початку великих mobile JSX змін.

## Інваріанти
- Кожна нова сторінка/компонент від цього моменту — **тільки через токени** (`design-system.md` §6). Старі сторінки мігруємо при дотику.
- Бренд-колір зберігаємо (`#7f74df`/`#a79cf7`).
- Паралельна робота Alex (Telegram-auth, attendance-detail) — не зачіпати.

## Журнал
- **2026-06-26 (1):** аудит (2 агенти) + `design-system.md` + цей план створено. Точковий фікс «прозорих кнопок».
- **2026-06-26 (2):** ✅ **Фаза 0** (tokens.css адитивно) + ✅ **Фаза 1** (ваги→400/500/600, 700+ прибрано; page-header 24→20, відступи; oddball sizes) — задеплоєно.
- **2026-06-26 (3):** ✅ depth-тіні (sidebar/topbar/cards), ✅ **Фаза 2** (кнопки h38→32, токени) — задеплоєно.
- **2026-06-26 (4):** ✅ **Фаза 3** (заголовки колонок caption-style uppercase muted; attendance 46→40px; токени відступів — people/attendance/leave) — задеплоєно. + nav-button 38→36 токени.
- **2026-06-26 (5):** ✅ **Фаза 5 mobile-polish** (інпути 16px <640 анти-iOS-zoom; тач-таргети кнопок →40px на телефоні; CTA full-width) — задеплоєно. Виявлено: drawer/bottom-nav/People-картки/адаптивні-грід уже існували — база була непогана.
- **2026-06-26 (6):** ✅ План оновлено після незалежного review: додано current state, Stop/Go, критерії приймання, CSS-аудити, z-index/breakpoint рішення, Phase 5 розбито на підфази.
- **Лишилось / наступні роботи:**
  - ⬜ Phase 5.2: attendance-table → stacked-cards на телефоні (зараз горизонт-скрол) — потребує JSX-зміни в App.tsx, не лише CSS.
  - ⬜ Phase 5.4: фільтри→bottom-sheet — потребує JSX і перевірки scroll lock/focus.
  - ⬜ Повна міграція брейкпойнтів на 640/768/1024/1280 (зараз мікс 620/980 + новий 640).
  - ⬜ **Фаза 6** — dark тема без 203 `!important` (винести в окремий файл через токени).
  - ⬜ **Фаза 7** — розбити `App.tsx` (14k) та `index.css` (12.9k) на модулі.
  - ⬜ Поступова міграція старих ad-hoc font-size (15/14px тощо) на токени при дотику до кожної фічі.
