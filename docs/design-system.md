# HR Vidnova — Дизайн-система (єдине джерело правди)

> Мета: щільний, легкий, сучасний інтерфейс (як PeopleForce / Linear), без крупних жирних шрифтів і «гуляючого» повітря. Світла тема — основна; темна існує.
> **Правило №1:** якщо значення не є токеном — це баг. Жодних raw-px для типографіки/відступів/радіусів/кольорів у компонентах.

Статус впровадження див. `design-redesign-plan.md`. Бренд: `--primary #7f74df` (дія) + `#a79cf7` (акцент).

---

## 0. Філософія
- **Щільність > повітря.** Найтісніше комфортне значення за замовчуванням; повітря додаємо лише там, де ламається скан.
- **Тиха ієрархія.** Ієрархія з ваги + кольору, а **не** з гігантських розмірів. Заголовок сторінки — 20px, не 30–56px.
- **~7 токенів типографіки, ~8 токенів відступів.** Замінюють 30+ ad-hoc розмірів, що є зараз.
- **Майже плоскі поверхні.** 1px бордери роблять основну роботу; тіні — ледь помітні.

---

## 1. Типографіка

**Базовий розмір body = 13px** (data-dense таблиці; стандарт Linear/Stripe/GitHub dense). На мобільному (<640px) базу піднімаємо до 14px, **інпути 16px** (проти iOS-zoom).

| Токен | px | lh | вага | Де |
|---|---|---|---|---|
| `--font-display` | 24 | 30 | 600 | dashboard hero / логін / empty-state |
| `--font-h1` | **20** | 26 | 600 | заголовок сторінки (було 24–56) |
| `--font-h2` | 16 | 22 | 600 | заголовки секцій/карток |
| `--font-h3` | 14 | 20 | 600 | під-секції, заголовки груп таблиць, модалки |
| `--font-body` | 13 | 18 | 400 | body, клітинки таблиць, інпути, кнопки |
| `--font-sm` | 12 | 16 | 400 | вторинний текст, helper |
| `--font-caption` | 11 | 14 | 500 | лейбли, бейджі, **заголовки колонок таблиць** |
| `--font-micro` | 10 | 14 | 500 | таймстемпи, лічильники (рідко) |

```css
--font-display:24px; --lh-display:30px;
--font-h1:20px;      --lh-h1:26px;
--font-h2:16px;      --lh-h2:22px;
--font-h3:14px;      --lh-h3:20px;
--font-body:13px;    --lh-body:18px;
--font-sm:12px;      --lh-sm:16px;
--font-caption:11px; --lh-caption:14px;
--font-micro:10px;   --lh-micro:14px;
```

**Шрифт:** system stack (нуль network-cost, відмінна кирилиця). Опційний апгрейд — self-host Inter (не CDN). Не змішувати.
```css
--font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans", sans-serif;
--font-mono: "SF Mono", "JetBrains Mono", Menlo, Consolas, monospace;
```
Числові колонки (зарплата/відвідуваність): `font-feature-settings: "tnum" 1;` — щоб цифри вирівнювались.

**Ваги — лише три: 400 / 500 / 600.**
- **400** — увесь body, клітинки, значення інпутів.
- **500** — лейбли, заголовки колонок, бейджі, активний пункт навігації, secondary-кнопки.
- **600** — усі заголовки, текст primary-кнопки, KPI-числа.
- **700+ заборонено.** Саме 700 на великих розмірах дає «важкий» вигляд.

---

## 2. Відступи (база 4px)
```css
--space-0:0; --space-1:4px; --space-2:8px; --space-3:12px;
--space-4:16px; --space-5:20px; --space-6:24px; --space-7:32px; --space-8:48px;
```
Усе (padding/margin/gap) лягає на цю шкалу. **Жодних 10/15/18/25px.** (Виняток: 6px лейбл→інпут.)

| Контекст | Токен |
|---|---|
| Падінг сторінки (desktop / mobile) | 24 / 16 |
| Падінг картки (звич / компакт) | 20 / 16 |
| Відступ між блоками | 24 |
| Клітинка таблиці (compact, default) | 8×12 |
| Кнопка md / sm | 0 16 / 0 12 |
| Інпут | 0 12 |
| Icon→text inline | 8 |

**Щільність таблиць** — один атрибут перемикає все, default = `compact`:
```css
[data-density="comfortable"]{ --row-h:44px; --cell-py:10px; --cell-px:16px; }
[data-density="compact"]    { --row-h:40px; --cell-py:8px;  --cell-px:12px; } /* default */
[data-density="condensed"]  { --row-h:32px; --cell-py:6px;  --cell-px:8px;  }
```

---

## 3. Радіус / тіні / бордери
```css
--radius-xs:4px; --radius-sm:6px; --radius-md:8px; --radius-lg:12px; --radius-full:9999px;
/* ≥16px не використовувати — читається як consumer-app, не dense SaaS */

--shadow-xs:0 1px 2px rgba(16,24,40,.04);
--shadow-sm:0 1px 3px rgba(16,24,40,.06),0 1px 2px rgba(16,24,40,.04);
--shadow-md:0 4px 8px -2px rgba(16,24,40,.08),0 2px 4px -2px rgba(16,24,40,.04);
--shadow-lg:0 12px 24px -6px rgba(16,24,40,.12),0 4px 8px -4px rgba(16,24,40,.06);
--shadow-focus:0 0 0 3px rgba(127,116,223,.30);

--border:#e7eaf0; --border-strong:#d4d9e3; --border-subtle:#f0f2f6; --border-focus:#7f74df;
```
xs=картки в спокої, sm=hover/sticky-header, md=дропдауни/тултіпи, lg=модалки/drawer, focus=клавіатурний фокус. Бордери 1px скрізь; 2px ніколи (фокус — через box-shadow).

---

## 4. Компоненти (точні px)

**Sidebar:** width 240 (collapsed rail 56); nav-item h36, padding 0 12, icon-text gap 10; шрифт 13/400 (активний 500); іконка 18; group-label 11/500 uppercase ls .04em muted; активний фон `--primary-soft`.

**Topbar:** h52; padding 0 16 (desktop 0 24); search h32; avatar 28; icon-кнопки 32×32 (icon 18); 1px bottom border.

**Page header (компактний — головний виграш по висоті):** title **20/600**; subtitle 12 muted; padding 16 top / 12 bottom; title→content gap 16; екшени праворуч на baseline. (Економить ~60–90px вертикалі на сторінку.)

**Таблиця:** row h40 (condensed 32); header h38; cell 8×12; cell 13/400; **header 11/500 uppercase ls .03em muted**; row-border 1px `--border-subtle`; hover `--bg-hover`; selected `--primary-soft`; sticky header bg elevated + shadow-sm; числові — праворуч + tnum; avatar-in-cell 24.

**Кнопки:**
| Розмір | h | padding | шрифт | radius |
|---|---|---|---|---|
| sm | 28 | 0 12 | 12/500 | 6 |
| md (default) | 32 | 0 16 | 13/500 | 6 |
| lg (mobile CTA) | 40 | 0 20 | 14/500 | 8 |
| icon sm/md | 28/32 кв. | — | icon 16/18 | 6 |

Варіанти: `primary` (бренд-фон, білий текст, 600), `secondary` (поверхня+1px бордер), `ghost` (прозорий, hover-фон), `danger` (червоний). На mobile primary-CTA → 44px. Icon→text gap у кнопці 6px.

**Інпути:** h32 (sm28, mobile40/тап44); padding 0 12; 13/400 (**mobile 16**); 1px `--border-strong`, focus→`--border-focus`+`--shadow-focus`; radius6; label 12/500 (6px нижче); helper/error 11; placeholder `--muted-2`.

**Бейджі/чипи:** h20; padding 0 8; 11/500; radius4 (status-pill → full); dot 6px; стиль — м'який тонований фон + кольоровий текст, **не суцільна заливка**.

**Аватари:** xs20 / sm24 / md32 (default) / lg40 / xl64; radius-full; ініціали 600; status-dot 8px з 2px білим кільцем; стек -8px overlap + 2px кільце.

---

## 4b. Кольори

**Бренд (ролі флипнуто — `#7f74df` тепер дія, проходить AA на білому):**
```css
--primary:#7f74df; --primary-hover:#6e62d4; --primary-active:#5d51c4;
--primary-light:#a79cf7; --primary-soft:#eeebfb; --primary-contrast:#fff;
```
**Нейтралі (light):**
```css
--bg:#f7f8fa; --bg-subtle:#f0f2f6; --bg-elevated:#fff; --bg-hover:#f2f3f7;
--text:#18243a; --text-muted:#5b6b80; --muted-2:#9aaabc;
```
**Семантика (м'який фон + сильний текст):**
```css
--success:#0f9d6c; --success-soft:#e7f6ef;  /* approved/present */
--warning:#c98a00; --warning-soft:#fdf4e3;  /* pending/expiring */
--danger:#dc4b56;  --danger-soft:#fdecee;   /* rejected/absent/delete */
--info:#3b82c4;    --info-soft:#e8f1fb;     /* notes/neutral */
```
**Dark:**
```css
[data-theme="dark"]{
  --bg:#11151f; --bg-subtle:#161b27; --bg-elevated:#1a202e; --bg-hover:#222a3a;
  --text:#e5edf7; --text-muted:#9aa8bd; --muted-2:#6b7a90;
  --border:#283042; --border-strong:#36405a; --border-subtle:#1e2533;
  --primary:#8b80e6; --primary-hover:#9a90ec; --primary-soft:#262247;
  --success:#34c08a; --success-soft:#13251f; --warning:#e0a93b; --warning-soft:#2a2114;
  --danger:#e9636d; --danger-soft:#2a1619; --info:#5aa0e0; --info-soft:#13202e;
}
```
Семантичні soft-фони — окремі per-theme; **ніколи** не використовувати light-soft на dark (світитиметься). Контраст: body ≥4.5:1, secondary/large ≥3:1 (WCAG AA).

---

## 5. Мобільна адаптація

```css
--bp-sm:640px; --bp-md:768px; --bp-lg:1024px; --bp-xl:1280px;
```
Mobile-first: базові стилі = телефон, далі `min-width` вгору.

| Брейкпойнт | Що змінюється |
|---|---|
| **<640 (телефон)** | Sidebar→off-canvas **drawer** (бургер у topbar). База 14px, інпути 16px. Падінг 16. Таблиці→**stacked cards**. Фільтри→**bottom sheet**. CTA full-width 44px. Один стовпець. |
| **640–767** | Те саме + 2-up KPI-картки. |
| **768–1023 (планшет)** | Sidebar = drawer або rail 56. Таблиці: горизонт-скрол зі sticky 1-ю колонкою. 2-колонкові форми. Падінг 20. |
| **≥1024** | Постійний sidebar (240, складається до 56). Повні таблиці. Падінг 24. Фільтри інлайн. |
| **≥1280** | Multi-column дашборди, контент max ~1440 центр. |

**Патерни:**
- **Drawer (<1024):** 280px, зліва, shadow-lg, scrim rgba(16,24,40,.45); закриття: scrim/тап-пункт/swipe/Esc; translateX 200ms.
- **Таблиця→картки (<640):** рядок=картка (padding12–16, radius8, shadow-xs, gap8); ім'я+avatar=шапка (14/600); решта колонок=пари label(11 muted)/value(13); екшени→«⋯».
- **Тач-таргет ≥44×44**, ≥8px між сусідніми.
- **Фільтри→bottom sheet (<768):** drag-handle 32×4, max-h85vh, sticky-footer Reset(ghost)+Apply(primary full-44).
- **Модалки <640** → full-screen sheet (slide up). Sticky bottom action-bar з `env(safe-area-inset-bottom)`. Поважати `prefers-reduced-motion`.

---

## 6. Правила governance (для майбутніх сторінок)

1. **Лише токени.** Жодних raw-px для типу/відступу/радіуса/кольору. `var(--…)`. Raw-px лише для разової геометрії (1px hairline, intrinsic-розмір іконки).
2. **Шкала типу з 7 токенів — закрита.** Потрібен новий розмір? Бери найближчий токен.
3. **Відступи лягають на 4px-шкалу.** Жодних 10/15/18/25px (виняток 6px лейбл-gap).
4. **Макс 2 видимі ваги на екран** (600 заголовок + 400 body + опц. 500 акцент). **700+ заборонено.**
5. **Заголовки сторінок = 20px.** Виняток — dashboard `--font-display` 24.
6. **Таблиці default `compact`** (40px рядки). Comfortable/condensed — user-toggle, не хардкод.
7. **Тіні лише зі шкали** (xs/sm/md/lg/focus). Жодних bespoke box-shadow-літералів.
8. **Кольори через семантичні токени**, не hex у компонентах. Обидві теми визначають кожен токен.
9. **Кожен інтерактив** має видимий фокус (`--shadow-focus`) і ≥44px тач-таргет на mobile.
10. **Контраст:** body ≥4.5:1, secondary/large ≥3:1, в обох темах.
11. **Mobile не опційний.** Кожен новий екран проходить на 360px: drawer-nav, stacked-таблиці, bottom-sheet фільтри, без горизонт-скролу (крім навмисного таблиці).
12. **Одне джерело правди.** Усі токени в `tokens.css` (`:root` + `[data-theme="dark"]`). Компоненти не імпортують інших значень. (Ціль: stylelint-правило проти hardcoded hex/px.)
