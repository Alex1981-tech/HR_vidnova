import { useEffect, useState, type ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';
import { ChevronLeft, Filter, MoreHorizontal } from 'lucide-react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ComposedChart,
  LabelList,
  Legend,
  Line,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

const TOOLTIP_STYLE = {
  background: 'var(--panel)',
  border: '1px solid var(--line)',
  borderRadius: 8,
  fontSize: 12,
  color: 'var(--text)',
} as const;

const AXIS_TICK = { fontSize: 11, fill: 'var(--muted)' } as const;
const VALUE_LABEL = { fontSize: 10, fill: 'var(--text-muted)' } as const;

// ---- data fetching ----
export type LoadState = 'loading' | 'ready' | 'error';

export function useReportData<T>(path: string): { data: T | null; state: LoadState } {
  const [data, setData] = useState<T | null>(null);
  const [state, setState] = useState<LoadState>('loading');
  useEffect(() => {
    let alive = true;
    setState('loading');
    fetch(path, { credentials: 'include', headers: { Accept: 'application/json' } })
      .then((response) => {
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return response.json();
      })
      .then((json) => {
        if (!alive) return;
        setData(json as T);
        setState('ready');
      })
      .catch(() => {
        if (alive) setState('error');
      });
    return () => {
      alive = false;
    };
  }, [path]);
  return { data, state };
}

// ---- colours ----
export const CHART = {
  hired: '#16a37b',
  terminated: '#ec7a45',
  line: '#4b73e8',
  bar: '#5b8def',
};

// distribution pie palette (matches PeopleForce blues/violets)
export const PIE_PALETTE = ['#5b8def', '#3f6fd6', '#8b80e6', '#6f63d6', '#5ec2e0', '#a79cf7', '#3fa9c9', '#c0788f'];

// ---- layout ----
export function ReportLayout({
  title,
  subtitle,
  children,
  filterCount,
}: {
  title: string;
  subtitle?: string;
  children: ReactNode;
  filterCount?: number;
}) {
  const navigate = useNavigate();
  return (
    <main className="workspace report-page">
      <button type="button" className="report-back" onClick={() => navigate('/reports')}>
        <ChevronLeft size={16} />
        <span>Назад</span>
      </button>

      <header className="report-head">
        <div>
          <h1>{title}</h1>
          {subtitle ? <p>{subtitle}</p> : null}
        </div>
        <button type="button" className="icon-button report-menu" aria-label="Дії">
          <MoreHorizontal size={18} />
        </button>
      </header>

      <div className="report-toolbar">
        <button type="button" className="secondary-action">
          <Filter size={15} />
          <span>Фільтр{filterCount ? ` (${filterCount})` : ''}</span>
        </button>
      </div>

      {children}
    </main>
  );
}

export function ReportCard({
  title,
  className,
  children,
}: {
  title?: string;
  className?: string;
  children: ReactNode;
}) {
  return (
    <section className={`report-card${className ? ` ${className}` : ''}`}>
      {title ? <h2 className="report-card-title">{title}</h2> : null}
      {children}
    </section>
  );
}

export function MetricStat({ value, label }: { value: string; label: string }) {
  return (
    <div className="report-metric">
      <strong>{value}</strong>
      <span>{label}</span>
    </div>
  );
}

// ---- charts ----
type MonthlyRow = { label: string; hired: number; terminated: number; total: number };

export function HiringComboChart({ data }: { data: MonthlyRow[] }) {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <ComposedChart data={data} margin={{ top: 16, right: 8, bottom: 0, left: -8 }}>
        <CartesianGrid stroke="var(--line)" vertical={false} />
        <XAxis dataKey="label" tick={{ fontSize: 11, fill: 'var(--muted)' }} tickLine={false} axisLine={{ stroke: 'var(--line)' }} />
        <YAxis yAxisId="bars" tick={{ fontSize: 11, fill: 'var(--muted)' }} tickLine={false} axisLine={false} allowDecimals={false} />
        <YAxis yAxisId="line" orientation="right" tick={{ fontSize: 11, fill: 'var(--muted)' }} tickLine={false} axisLine={false} allowDecimals={false} />
        <Tooltip
          contentStyle={{
            background: 'var(--panel)',
            border: '1px solid var(--line)',
            borderRadius: 8,
            fontSize: 12,
            color: 'var(--text)',
          }}
        />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Bar yAxisId="bars" dataKey="hired" name="Найнято" fill={CHART.hired} radius={[3, 3, 0, 0]} maxBarSize={18}>
          <LabelList dataKey="hired" position="top" style={VALUE_LABEL} />
        </Bar>
        <Bar yAxisId="bars" dataKey="terminated" name="Звільнені" fill={CHART.terminated} radius={[3, 3, 0, 0]} maxBarSize={18}>
          <LabelList dataKey="terminated" position="top" style={VALUE_LABEL} />
        </Bar>
        <Line yAxisId="line" type="monotone" dataKey="total" name="Загалом" stroke={CHART.line} strokeWidth={2} dot={{ r: 3, fill: CHART.line }}>
          <LabelList dataKey="total" position="top" style={VALUE_LABEL} />
        </Line>
      </ComposedChart>
    </ResponsiveContainer>
  );
}

type TerminationRow = { label: string; terminated: number; cumulative: number };

export function TerminationComboChart({ data }: { data: TerminationRow[] }) {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <ComposedChart data={data} margin={{ top: 16, right: 8, bottom: 0, left: -8 }}>
        <CartesianGrid stroke="var(--line)" vertical={false} />
        <XAxis dataKey="label" tick={AXIS_TICK} tickLine={false} axisLine={{ stroke: 'var(--line)' }} />
        <YAxis yAxisId="bars" tick={AXIS_TICK} tickLine={false} axisLine={false} allowDecimals={false} />
        <YAxis yAxisId="line" orientation="right" tick={AXIS_TICK} tickLine={false} axisLine={false} allowDecimals={false} />
        <Tooltip contentStyle={TOOLTIP_STYLE} />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Bar yAxisId="bars" dataKey="terminated" name="Звільнення" fill="#8b80e6" radius={[3, 3, 0, 0]} maxBarSize={18}>
          <LabelList dataKey="terminated" position="top" style={VALUE_LABEL} />
        </Bar>
        <Line yAxisId="line" type="monotone" dataKey="cumulative" name="Накопичено" stroke="#6f63d6" strokeWidth={2} dot={{ r: 3, fill: '#6f63d6' }}>
          <LabelList dataKey="cumulative" position="top" style={VALUE_LABEL} />
        </Line>
      </ComposedChart>
    </ResponsiveContainer>
  );
}

type LabelCount = { label: string; count: number };

export function SimpleBarChart({ data, color = CHART.bar, height = 300 }: { data: LabelCount[]; color?: string; height?: number }) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 16, right: 8, bottom: 0, left: -8 }}>
        <CartesianGrid stroke="var(--line)" vertical={false} />
        <XAxis dataKey="label" tick={AXIS_TICK} tickLine={false} axisLine={{ stroke: 'var(--line)' }} interval={0} />
        <YAxis tick={AXIS_TICK} tickLine={false} axisLine={false} allowDecimals={false} />
        <Tooltip contentStyle={TOOLTIP_STYLE} cursor={{ fill: 'var(--panel-soft)' }} />
        <Bar dataKey="count" name="Кількість" fill={color} radius={[3, 3, 0, 0]} maxBarSize={48}>
          <LabelList dataKey="count" position="top" style={VALUE_LABEL} />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

type NameYears = { name: string; years: number };

export function HorizontalBarChart({ data }: { data: NameYears[] }) {
  return (
    <ResponsiveContainer width="100%" height={Math.max(160, data.length * 38 + 24)}>
      <BarChart data={data} layout="vertical" margin={{ top: 4, right: 16, bottom: 4, left: 8 }}>
        <CartesianGrid stroke="var(--line)" horizontal={false} />
        <XAxis type="number" tick={AXIS_TICK} tickLine={false} axisLine={{ stroke: 'var(--line)' }} />
        <YAxis type="category" dataKey="name" tick={AXIS_TICK} tickLine={false} axisLine={false} width={150} />
        <Tooltip contentStyle={TOOLTIP_STYLE} cursor={{ fill: 'var(--panel-soft)' }} formatter={(value) => [`${value} р.`, 'Середній стаж']} />
        <Bar dataKey="years" fill={CHART.bar} radius={[0, 3, 3, 0]} maxBarSize={22} />
      </BarChart>
    </ResponsiveContainer>
  );
}

type DistRow = { name: string; count: number; pct: number };

export function DistributionPie({ data }: { data: DistRow[] }) {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <PieChart>
        <Tooltip
          formatter={(value, _name, entry) => {
            const row = (entry as { payload?: DistRow }).payload;
            return [`${value} (${row?.pct ?? 0}%)`, row?.name ?? ''];
          }}
          contentStyle={{
            background: 'var(--panel)',
            border: '1px solid var(--line)',
            borderRadius: 8,
            fontSize: 12,
            color: 'var(--text)',
          }}
        />
        <Legend wrapperStyle={{ fontSize: 11 }} />
        <Pie data={data} dataKey="count" nameKey="name" cx="50%" cy="50%" outerRadius={100} innerRadius={0}>
          {data.map((_, index) => (
            <Cell key={index} fill={PIE_PALETTE[index % PIE_PALETTE.length]} />
          ))}
        </Pie>
      </PieChart>
    </ResponsiveContainer>
  );
}
