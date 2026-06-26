// HR Vidnova version history. Bump APP_VERSION + add a changelog entry on each release.

export type ChangelogEntry = {
  version: string;
  date: string; // dd.mm.yyyy
  changes: string[];
};

export const changelog: ChangelogEntry[] = [
  {
    version: '1.0.0',
    date: '26.06.2026',
    changes: [
      'Перший реліз HR Vidnova у продакшні (hr.vidnova.app).',
      'Співробітники, команди, оргструктура (граф), відпустки, база знань.',
      'Активи (CMMS): сторінка обладнання з фото та призначенням відповідальної особи.',
      'Авторизація співробітників через Telegram.',
      'Автоматичний деплой: GitHub Actions → GHCR → watchtower.',
    ],
  },
];

export const APP_VERSION = changelog[0].version;
export const APP_VERSION_DATE = changelog[0].date;
