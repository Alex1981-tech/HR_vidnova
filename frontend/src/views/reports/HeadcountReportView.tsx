import {
  DistributionPie,
  HiringComboChart,
  MetricStat,
  ReportCard,
  ReportLayout,
  useReportData,
} from './shared';

type HeadcountReport = {
  monthly: Array<{ label: string; hired: number; terminated: number; total: number }>;
  metrics: { growth_count: number; growth_pct: number; turnover_count: number; turnover_pct: number };
  by_department: Array<{ name: string; count: number; pct: number }>;
  by_clinic: Array<{ name: string; count: number; pct: number }>;
};

function pluralOsib(n: number): string {
  const mod10 = n % 10;
  const mod100 = n % 100;
  if (mod10 === 1 && mod100 !== 11) return 'особа';
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 10 || mod100 >= 20)) return 'особи';
  return 'осіб';
}

export function HeadcountReportView() {
  const { data, state } = useReportData<HeadcountReport>('/api/reports/headcount/');

  return (
    <ReportLayout title="Кількість персоналу" subtitle="Чисельність співробітників у компанії" filterCount={1}>
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
            <ReportCard title="Яка чисельність у моїй компанії?">
              <HiringComboChart data={data.monthly} />
            </ReportCard>
            <ReportCard className="report-metrics-card">
              <MetricStat
                value={`${data.metrics.growth_pct}% ${data.metrics.growth_count} ${pluralOsib(data.metrics.growth_count)}`}
                label="Середній приріст"
              />
              <MetricStat
                value={`${data.metrics.turnover_pct}% ${data.metrics.turnover_count} ${pluralOsib(data.metrics.turnover_count)}`}
                label="Середня плинність"
              />
            </ReportCard>
          </div>

          <div className="report-grid-pies">
            <ReportCard title="Чисельність за підрозділами">
              <DistributionPie data={data.by_department} />
            </ReportCard>
            <ReportCard title="Чисельність за локацією">
              <DistributionPie data={data.by_clinic} />
            </ReportCard>
          </div>
        </>
      )}
    </ReportLayout>
  );
}
