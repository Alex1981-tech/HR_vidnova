import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ChevronLeft } from 'lucide-react';

import { api } from '../../api/client';
import type { SecurityLogEvent } from '../../types/api';

type LoadState = 'idle' | 'loading' | 'ok' | 'error';

const EVENT_LABEL: Record<string, string> = {
  login_succeeded: 'Вхід у систему',
  login_failed: 'Невдала спроба входу',
  logout: 'Вихід із системи',
  session_expired: 'Сесія завершена (тайм-аут)',
  login_code_requested: 'Запит коду входу',
  login_code_sent: 'Код входу надіслано',
  access_denied: 'Доступ заборонено',
  telegram_link_requested: 'Запит привʼязки Telegram',
  telegram_linked: 'Telegram привʼязано',
};

const EVENT_TONE: Record<string, string> = {
  login_succeeded: 'ok',
  login_failed: 'bad',
  access_denied: 'bad',
  logout: 'muted',
  session_expired: 'warn',
};

function eventLabel(e: SecurityLogEvent): string {
  return EVENT_LABEL[e.event] ?? e.event_label ?? e.event;
}

function formatDateTime(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString('uk-UA', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

// Короткий опис пристрою з user-agent (браузер + ОС).
function parseDevice(ua: string): string {
  if (!ua) return '—';
  let os = '';
  if (/Windows/i.test(ua)) os = 'Windows';
  else if (/iPhone|iPad|iOS/i.test(ua)) os = 'iOS';
  else if (/Mac OS X|Macintosh/i.test(ua)) os = 'macOS';
  else if (/Android/i.test(ua)) os = 'Android';
  else if (/Linux/i.test(ua)) os = 'Linux';
  let browser = '';
  if (/Edg\//i.test(ua)) browser = 'Edge';
  else if (/OPR\/|Opera/i.test(ua)) browser = 'Opera';
  else if (/Chrome\//i.test(ua)) browser = 'Chrome';
  else if (/Firefox\//i.test(ua)) browser = 'Firefox';
  else if (/Safari\//i.test(ua)) browser = 'Safari';
  else if (/HR\s?Bot|python|curl|okhttp/i.test(ua)) browser = 'Бот/API';
  return [browser, os].filter(Boolean).join(' · ') || 'Невідомо';
}

export function SystemLogView() {
  const navigate = useNavigate();
  const [items, setItems] = useState<SecurityLogEvent[]>([]);
  const [state, setState] = useState<LoadState>('idle');

  useEffect(() => {
    let alive = true;
    setState('loading');
    api
      .systemSecurityLog()
      .then((res) => {
        if (alive) {
          setItems(res.items);
          setState('ok');
        }
      })
      .catch(() => {
        if (alive) setState('error');
      });
    return () => {
      alive = false;
    };
  }, []);

  return (
    <main className="workspace report-page">
      <button type="button" className="report-back" onClick={() => navigate('/reports')}>
        <ChevronLeft size={16} />
        <span>Назад</span>
      </button>

      <header className="report-head">
        <div>
          <h1>Системний журнал</h1>
          <p>Події безпеки всієї системи: входи, виходи, невдалі спроби та завершення сесій із телеметрією.</p>
        </div>
      </header>

      {state === 'loading' ? (
        <div className="asset-detail-loading">Завантаження…</div>
      ) : state === 'error' ? (
        <div className="org-empty-panel">
          <p className="report-empty-text">Не вдалося завантажити журнал.</p>
        </div>
      ) : items.length === 0 ? (
        <div className="org-empty-panel">
          <p className="report-empty-text">Подій ще немає.</p>
        </div>
      ) : (
        <div className="syslog-table-wrap">
          <table className="syslog-table">
            <thead>
              <tr>
                <th>Хто</th>
                <th>Подія</th>
                <th>Дата й час</th>
                <th>IP-адреса</th>
                <th>Пристрій</th>
              </tr>
            </thead>
            <tbody>
              {items.map((e) => (
                <tr key={e.id}>
                  <td className="syslog-who">{e.who || '—'}</td>
                  <td>
                    <span className={`syslog-badge syslog-${EVENT_TONE[e.event] ?? 'muted'}`}>{eventLabel(e)}</span>
                  </td>
                  <td>{formatDateTime(e.created_at)}</td>
                  <td className="syslog-ip">{e.ip_address || '—'}</td>
                  <td className="syslog-device" title={e.user_agent}>{parseDevice(e.user_agent)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </main>
  );
}
