import {
  DistributionPie,
  MetricStat,
  ReportCard,
  ReportLayout,
  TerminationComboChart,
  useReportData,
} from './shared';

type TurnoverReport = {
  monthly: Array<{ label: string; terminated: number; cumulative: number }>;
  metrics: { turnover_count: number; turnover_pct: number; monthly_pct: number; avg_tenure_months: number };
  by_department: Array<{ name: string; count: number; pct: number }>;
  by_clinic: Array<{ name: string; count: number; pct: number }>;
};

export function TurnoverReportView() {
  const { data, state } = useReportData<TurnoverReport>('/api/reports/turnover/');

  return (
    <ReportLayout
      title="Плинність співробітників"
      subtitle="Звіт про плинність співробітників у компанії"
      filterCount={1}
    >
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
            <ReportCard title="Плинність за місяцем">
              <TerminationComboChart data={data.monthly} />
            </ReportCard>
            <ReportCard className="report-metrics-card">
              <MetricStat
                value={`${data.metrics.turnover_pct}% ${data.metrics.turnover_count} осіб`}
                label="Плинність персоналу"
              />
              <MetricStat value={`${data.metrics.monthly_pct}%`} label="Плинність співробітників (середній за місяць)" />
              <MetricStat value={`${data.metrics.avg_tenure_months} місяців`} label="Середній стаж роботи" />
            </ReportCard>
          </div>

          <div className="report-grid-pies">
            <ReportCard title="Звільнення за підрозділом">
              <DistributionPie data={data.by_department} />
            </ReportCard>
            <ReportCard title="Звільнення за локацією">
              <DistributionPie data={data.by_clinic} />
            </ReportCard>
          </div>
        </>
      )}
    </ReportLayout>
  );
}
