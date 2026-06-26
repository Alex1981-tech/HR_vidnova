// HR Vidnova version history.
// Схема версій: 1.0.XX (патч 00..99) → коли дійде 1.0.99, наступна 1.1.00 і т.д.
// На кожен реліз: додай запис ЗВЕРХУ + онови патч.

export type ChangelogEntry = {
  version: string;
  date: string; // dd.mm.yyyy
  changes: string[];
};

export const changelog: ChangelogEntry[] = [
  {
    version: '1.0.01',
    date: '26.06.2026',
    changes: [
      'Активи (CMMS): сторінка обладнання з фото-картками та призначенням відповідальної особи.',
      'HR — майстер співробітників для активів; PeopleForce відключено від CMMS.',
      'Історія версій (цей розділ) під кнопкою «Налаштування».',
      'Оновлений компактний стиль бокового меню.',
    ],
  },
  {
    version: '1.0.00',
    date: '26.06.2026',
    changes: [
      'Перший реліз HR Vidnova у продакшні (hr.vidnova.app).',
      'Співробітники, команди, оргструктура (граф), відпустки, база знань.',
      'Авторизація співробітників через Telegram.',
      'Автоматичний деплой: GitHub Actions → GHCR → watchtower.',
    ],
  },
];

export const APP_VERSION = changelog[0].version;
export const APP_VERSION_DATE = changelog[0].date;
