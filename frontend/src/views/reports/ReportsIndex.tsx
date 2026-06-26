import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

type ReportItem = { key: string; title: string; desc: string };
type ReportGroup = { title: string; items: ReportItem[] };

const COMPANY_REPORT_GROUPS: ReportGroup[] = [
  {
    title: 'Основні',
    items: [
      { key: 'tasks', title: 'Завдання', desc: 'Хід виконання завдань у компанії' },
      { key: 'security-audit', title: 'Аудит безпеки', desc: 'Аудит безпеки співробітників та платформи' },
      { key: 'system-log', title: 'Системний журнал', desc: 'Список подій безпеки у вашому акаунті' },
    ],
  },
  {
    title: 'CoreHR',
    items: [
      { key: 'age', title: 'Вік співробітників', desc: 'Звіт про вікові профілі компанії' },
      { key: 'gender', title: 'Гендерне розподілення', desc: 'Звіт про гендерну різноманітність компанії' },
      { key: 'headcount', title: 'Кількість персоналу', desc: 'Чисельність співробітників у компанії' },
      { key: 'turnover', title: 'Плинність співробітників', desc: 'Звіт про плинність співробітників у компанії' },
      { key: 'tenure', title: 'Стаж', desc: 'Термін працевлаштування працівників у компанії' },
      { key: 'children', title: 'Діти', desc: 'Звіт про дітей працівників компанії' },
      { key: 'emergency-contacts', title: 'Екстрені контакти', desc: 'Екстрені контакти співробітників і ті, у кого їх немає' },
      { key: 'employment-status-history', title: 'Історія статусу роботи', desc: 'Історія змін статусу зайнятості працівників' },
      { key: 'career-history', title: "Історія кар'єрних змін", desc: "Рух співробітників по кар'єрних сходах" },
      { key: 'monthly-salary', title: 'Щомісячна заробітна плата', desc: 'Щомісячний звіт про заробітну плату співробітників' },
      { key: 'compensation-history', title: 'Історія компенсацій', desc: 'Історія змін зарплати працівників' },
      { key: 'working-hours', title: 'Робочі години', desc: 'Фактичний робочий час та відсутності кожного працівника' },
      { key: 'absence-history', title: 'Історія відсутностей', desc: 'Використані дні відпустки, лікарняні та інші відсутності' },
      { key: 'leave-requests', title: 'Запити на відсутність', desc: 'Історія запитів на відсутність у працівників' },
      { key: 'leave-balance', title: 'Баланс відсутностей', desc: 'Поточні залишки відсутності у працівників' },
      { key: 'leave-policies', title: 'Політики відсутностей', desc: 'Політики відсутностей, які застосовуються до працівників' },
      { key: 'assets-registry', title: 'Реєстр активів', desc: 'Активи компанії та кому вони призначені' },
      { key: 'celebrations', title: 'Святкування', desc: 'Дні народження та річниці співробітників' },
    ],
  },
];

export function ReportsIndex() {
  const navigate = useNavigate();
  const [tab, setTab] = useState<'company' | 'custom'>('company');

  return (
    <main className="workspace reports-page">
      <header className="page-header">
        <div>
          <h1>Звіти</h1>
        </div>
      </header>

      <div className="section-tabs reports-tabs">
        <button type="button" className={tab === 'company' ? 'active' : ''} onClick={() => setTab('company')}>
          Компанія
        </button>
        <button type="button" className={tab === 'custom' ? 'active' : ''} onClick={() => setTab('custom')}>
          Кастомний
        </button>
      </div>

      {tab === 'company' ? (
        <div className="reports-groups">
          {COMPANY_REPORT_GROUPS.map((group) => (
            <section className="reports-group" key={group.title}>
              <h2 className="reports-group-title">{group.title}</h2>
              <div className="reports-list">
                {group.items.map((item) => (
                  <button
                    type="button"
                    key={item.key}
                    className="reports-row"
                    onClick={() => navigate(`/reports/${item.key}`)}
                  >
                    <span className="reports-row-title">{item.title}</span>
                    <span className="reports-row-desc">{item.desc}</span>
                  </button>
                ))}
              </div>
            </section>
          ))}
        </div>
      ) : (
        <section className="panel reports-empty">
          <p>Кастомні звіти з'являться тут. Поки що доступні стандартні звіти у вкладці «Компанія».</p>
        </section>
      )}
    </main>
  );
}
