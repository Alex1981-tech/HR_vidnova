import {
  HorizontalBarChart,
  MetricStat,
  ReportCard,
  ReportLayout,
  SimpleBarChart,
  useReportData,
} from './shared';

type TenureReport = {
  buckets: Array<{ label: string; count: number }>;
  anniversaries: Array<{ label: string; count: number }>;
  metrics: { avg_years: number; longest: { years: number; name: string } };
  by_department: Array<{ name: string; years: number }>;
  by_clinic: Array<{ name: string; years: number }>;
};

export function TenureReportView() {
  const { data, state } = useReportData<TenureReport>('/api/reports/tenure/');

  return (
    <ReportLayout title="Стаж" subtitle="Термін працевлаштування працівників у компанії" filterCount={1}>
      {state === 'loading' ? (
        <ReportCard className="report-card-loading">
          <p className="report-empty-text">Завантаження…</p>
        </ReportCard>
      ) : state === 'error' || !data ? (
        <ReportCard className="report-card-loading">
          <p className="report-empty-text">Не вдалося завантажити звіт.</p>
        </ReportCard>
      ) : (
        <>
          <div className="report-grid-main">
            <ReportCard title="Стаж">
              <SimpleBarChart data={data.buckets} />
            </ReportCard>
            <ReportCard className="report-metrics-card">
              <MetricStat value={`${data.metrics.avg_years} років`} label="Середній строк роботи" />
              <MetricStat
                value={`${data.metrics.longest.years} років`}
                label={`Найдовший строк роботи${data.metrics.longest.name ? ` — ${data.metrics.longest.name}` : ''}`}
              />
            </ReportCard>
          </div>

          <ReportCard title="Розподіл річниць">
            <SimpleBarChart data={data.anniversaries} />
          </ReportCard>

          <div className="report-grid-pies">
            <ReportCard title="Середній термін роботи за підрозділом">
              <HorizontalBarChart data={data.by_department} />
            </ReportCard>
            <ReportCard title="Середній термін роботи за локацією">
              <HorizontalBarChart data={data.by_clinic} />
            </ReportCard>
          </div>
        </>
      )}
    </ReportLayout>
  );
}
