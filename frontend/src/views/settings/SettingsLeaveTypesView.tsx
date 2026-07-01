import { useEffect, useMemo, useState } from 'react';
import {
  Bold,
  CheckCircle2,
  ChevronDown,
  ChevronLeft,
  ClipboardList,
  Copy,
  GripVertical,
  Italic,
  Link,
  List,
  Minus,
  MoreHorizontal,
  Pencil,
  Plus,
  Search,
  Smile,
  Trash2,
  Underline,
  Users,
  X,
} from 'lucide-react';
import { api } from '../../api/client';
import type {
  EmployeeLeavePolicyAssignment,
  EmployeeListItem,
  LeavePolicy,
  LeavePolicyPayload,
  LeaveType,
  LeaveTypePayload,
  LeaveTypeWithPolicies,
} from '../../types/api';
import { LEAVE_ICON_OPTIONS, LeaveTypeIcon } from '../../lib/leaveIcons';

const UNIT_OPTIONS: Array<{ value: string; label: string }> = [
  { value: 'days', label: 'Днях' },
  { value: 'hours', label: 'Годинах' },
];

const DEFAULT_ICON = 'plane';
const DEFAULT_COLOR = '#000000';

const POLICY_ACTIVITY_OPTIONS = [
  { value: 'not_working_paid', label: 'Неробочі, оплачувані' },
  { value: 'not_working_unpaid', label: 'Неробочі, неоплачувані' },
  { value: 'working_paid', label: 'Робочі, оплачувані' },
];

const POLICY_TYPE_OPTIONS = [
  { value: 'accrual', label: 'З нарахуванням' },
  { value: 'manual', label: 'Без нарахування' },
  { value: 'external', label: 'Зовнішній баланс' },
];

const POLICY_COUNTED_OPTIONS = [
  { value: 'working_days', label: 'Робочі дні' },
  { value: 'calendar_days', label: 'Календарні дні' },
];

const ACCRUAL_FREQUENCY_OPTIONS = [
  { value: 'monthly', label: 'Щомісяця' },
  { value: 'yearly', label: 'Щороку' },
  { value: 'weekly', label: 'Щотижня' },
  { value: 'none', label: 'Немає' },
];

const ACCRUAL_TIMING_OPTIONS = [
  { value: 'period_start', label: 'Початок періоду' },
  { value: 'period_end', label: 'Кінець періоду' },
];

const FIRST_ACCRUAL_OPTIONS = [
  { value: 'proportional', label: 'Пропорційна' },
  { value: 'full', label: 'Повна' },
  { value: 'none', label: 'Не нараховувати' },
];

const CARRYOVER_MODE_OPTIONS = [
  { value: 'none', label: 'Немає' },
  { value: 'all', label: 'Усе' },
  { value: 'limited', label: 'Обмежено' },
];

const DELAY_UNIT_OPTIONS = [
  { value: 'days', label: 'Дні' },
  { value: 'months', label: 'Місяці' },
  { value: 'years', label: 'Роки' },
];

const CARRYOVER_DAY_OPTIONS = Array.from({ length: 31 }, (_, index) => ({
  value: String(index + 1),
  label: String(index + 1),
}));

const MONTH_OPTIONS = [
  'Січень',
  'Лютий',
  'Березень',
  'Квітень',
  'Травень',
  'Червень',
  'Липень',
  'Серпень',
  'Вересень',
  'Жовтень',
  'Листопад',
  'Грудень',
].map((label, index) => ({ value: String(index + 1), label }));

function unitSubtitle(unit: string): string {
  return unit === 'hours' ? 'Відстеження у годинах' : 'Відстеження у днях';
}

function activityLabel(value: string): string {
  const raw = (value || '').toLowerCase();
  if (raw.includes('not_working') || raw.includes('non_working') || raw.includes('неробоч')) {
    return raw.includes('unpaid') || raw.includes('неоплач') ? 'Неробочі, неоплачувані' : 'Неробочі, оплачувані';
  }
  if (raw.includes('unpaid') || raw.includes('неоплач')) return 'Неробочі, неоплачувані';
  if (raw.includes('working') || raw.includes('робоч')) return 'Робочі, оплачувані';
  return 'Неробочі, оплачувані';
}

function countedAsLabel(value: string): string {
  const raw = (value || '').toLowerCase();
  if (raw.includes('calendar') || raw.includes('календар')) return 'Календарні дні';
  return 'Робочі дні';
}

function policyTypeLabel(value: string): string {
  const option = POLICY_TYPE_OPTIONS.find((item) => item.value === value);
  return option?.label ?? 'Без нарахування';
}

function employeesCountLabel(count: number): string {
  const mod10 = count % 10;
  const mod100 = count % 100;
  if (mod10 === 1 && mod100 !== 11) return `${count} співробітник`;
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return `${count} співробітники`;
  return `${count} співробітників`;
}

type ModalState = { mode: 'create' } | { mode: 'edit'; type: LeaveType } | null;

type PolicyWizardRequest = {
  leaveType: LeaveType;
  policyType?: string;
  policy?: LeavePolicy;
};

type PolicyPeoplePanelState = {
  policy: LeavePolicy;
  type: LeaveType;
} | null;

type PolicyPersonRow = {
  employeeId: number;
  fullName: string;
  position: string;
  avatarUrl: string;
  effectiveOn: string | null;
};

function dateLabel(value: string | null | undefined): string {
  if (!value) return '-';
  const date = new Date(`${value}T00:00:00`);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString('uk-UA');
}

function employeeInitials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join('')
    .toUpperCase() || 'HR';
}

function employeeAvatar(employee: EmployeeListItem | undefined): string {
  if (!employee) return '';
  if (employee.avatar_local_url) return employee.avatar_local_url;
  if (employee.avatar_url && !employee.avatar_url.includes('default_employee')) return employee.avatar_url;
  return '';
}

function peopleForPolicy(
  policy: LeavePolicy,
  assignments: EmployeeLeavePolicyAssignment[],
  employeesById: Map<number, EmployeeListItem>,
): PolicyPersonRow[] {
  return assignments
    .filter((assignment) => assignment.policy === policy.id)
    .map((assignment) => {
      const employee = employeesById.get(assignment.employee);
      return {
        employeeId: assignment.employee,
        fullName: employee?.full_name || assignment.employee_name || `ID ${assignment.employee}`,
        position: employee?.position_name || assignment.employee_position_name || employee?.department_name || '',
        avatarUrl: employeeAvatar(employee),
        effectiveOn: assignment.effective_on,
      };
    })
    .sort((first, second) => first.fullName.localeCompare(second.fullName, 'uk'));
}

function buildPoliciesByType(types: LeaveTypeWithPolicies[]): Map<number, LeavePolicy[]> {
  const result = new Map<number, LeavePolicy[]>();
  types.forEach((type) => {
    result.set(
      type.id,
      [...(type.policies ?? [])].sort((first, second) => first.name.localeCompare(second.name, 'uk')),
    );
  });
  return result;
}

function LeaveTypeModal({
  initial,
  onClose,
  onSave,
}: {
  initial: LeaveType | null;
  onClose: () => void;
  onSave: (payload: LeaveTypePayload) => Promise<void>;
}) {
  const [name, setName] = useState(initial?.name ?? '');
  const [unit, setUnit] = useState(initial?.unit || 'days');
  const [icon, setIcon] = useState(initial?.icon || DEFAULT_ICON);
  const [color, setColor] = useState(initial?.color || DEFAULT_COLOR);
  const [iconPickerOpen, setIconPickerOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const activeIcon = LEAVE_ICON_OPTIONS.find((opt) => opt.key === icon) ?? LEAVE_ICON_OPTIONS[0];

  async function submit() {
    if (!name.trim()) {
      setError('Введіть ім’я типу');
      return;
    }
    setSaving(true);
    setError('');
    try {
      await onSave({ name: name.trim(), unit, icon, color });
    } catch {
      setError('Не вдалося зберегти. Спробуйте ще раз.');
      setSaving(false);
    }
  }

  return (
    <div
      className="people-data-modal-layer leave-type-modal-layer"
      role="dialog"
      aria-modal="true"
      aria-label={initial ? 'Редагувати тип відсутності' : 'Додати тип відсутності'}
    >
      <button type="button" className="people-data-modal-backdrop" aria-label="Закрити" onClick={onClose} />
      <div className="people-data-modal leave-type-modal">
        <div className="people-data-modal-head leave-type-modal-head">
          <h2>{initial ? 'Редагувати тип відсутності' : 'Додати тип відсутності'}</h2>
          <button type="button" className="icon-button" onClick={onClose} aria-label="Закрити">
            <X size={20} />
          </button>
        </div>
        <div className="people-data-modal-body leave-type-modal-body">
          <label className="leave-type-modal-field">
            <span>Ім’я</span>
            <input className="people-data-input leave-type-input" value={name} onChange={(e) => setName(e.target.value)} autoFocus />
          </label>
          <label className="leave-type-modal-field">
            <span>Одиниця відстеження часу</span>
            <select className="people-data-input leave-type-input leave-type-select" value={unit} onChange={(e) => setUnit(e.target.value)}>
              {UNIT_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </label>
          <div className="leave-type-style-row">
            <div className="leave-icon-picker">
              <button
                type="button"
                className="leave-icon-trigger"
                aria-label={`Іконка: ${activeIcon.label}`}
                aria-haspopup="menu"
                aria-expanded={iconPickerOpen}
                onClick={() => setIconPickerOpen((open) => !open)}
                style={{ color }}
              >
                <LeaveTypeIcon iconKey={icon} size={20} />
                <ChevronDown size={15} />
              </button>
              {iconPickerOpen ? (
                <div className="leave-icon-menu" role="menu">
                  {LEAVE_ICON_OPTIONS.map((opt) => (
                    <button
                      type="button"
                      key={opt.key}
                      className={icon === opt.key ? 'active' : ''}
                      title={opt.label}
                      role="menuitem"
                      onClick={() => {
                        setIcon(opt.key);
                        setIconPickerOpen(false);
                      }}
                      style={icon === opt.key ? { color } : undefined}
                    >
                      <opt.Icon size={18} />
                    </button>
                  ))}
                </div>
              ) : null}
            </div>
            <span className="leave-color-copy">з кольором</span>
            <label className="leave-color-button" aria-label="Колір типу відсутності">
              <span className="leave-color-swatch" style={{ backgroundColor: color }} />
              <ChevronDown size={14} />
              <input type="color" value={color} onChange={(e) => setColor(e.target.value)} />
            </label>
          </div>
          {error ? <p className="people-data-modal-error">{error}</p> : null}
        </div>
        <div className="people-data-modal-foot leave-type-modal-foot">
          <button type="button" className="primary-action leave-type-save" onClick={submit} disabled={saving}>
            {saving ? 'Збереження…' : 'Зберегти'}
          </button>
        </div>
      </div>
    </div>
  );
}

function ToolbarStub() {
  return (
    <div className="leave-policy-editor-toolbar" aria-hidden>
      <Bold size={15} />
      <Italic size={15} />
      <Underline size={15} />
      <List size={15} />
      <Link size={15} />
      <Smile size={15} />
    </div>
  );
}

function valueOrNull(value: string): string | null {
  const normalized = value.trim().replace(',', '.');
  return normalized ? normalized : null;
}

function valueOrZero(value: string): string {
  return valueOrNull(value) ?? '0';
}

function numberOrNull(value: string): number | null {
  const normalized = value.trim();
  if (!normalized) return null;
  const parsed = Number.parseInt(normalized, 10);
  return Number.isFinite(parsed) ? parsed : null;
}

type ApprovalOptionKind =
  | 'manager'
  | 'manager_manager'
  | 'manager_level_3'
  | 'team_manager'
  | 'person_reference'
  | 'department_manager'
  | 'specific_employee';

type ApprovalStepDraft = {
  uiId: string;
  type: ApprovalOptionKind;
  employeeId: number | null;
  employeeName: string;
};

type SubstituteDraft = {
  sourceType: ApprovalOptionKind;
  targetType: string;
  employeeId: number | null;
};

type SeniorityLevelDraft = {
  uiId: string;
  id: string;
  seniorityYears: string;
  periodAmount: string;
  frequency: string;
  accrualTiming: string;
  maxBalance: string;
  carryoverMode: string;
  carryoverExpireMonths: string;
};

type SelectOption = {
  value: string;
  label: string;
  group?: string;
  subtitle?: string;
};

const APPROVER_OPTIONS: SelectOption[] = [
  { value: 'manager', label: 'Менеджер', group: 'Особиста' },
  { value: 'manager_manager', label: 'Менеджер менеджера', group: 'Особиста' },
  { value: 'manager_level_3', label: 'Менеджер 3-го рівня', group: 'Особиста' },
  { value: 'team_manager', label: 'Менеджер команди', group: 'Особиста' },
  { value: 'person_reference', label: 'Посилання на особу', group: 'Особиста' },
  { value: 'department_manager', label: 'Менеджер департаменту', group: 'Департамент' },
  { value: 'specific_employee', label: 'Конкретна людина', group: 'Конкретна людина' },
];

const SUBSTITUTE_SOURCE_OPTIONS: SelectOption[] = [
  { value: 'manager', label: 'Менеджер' },
  { value: 'manager_manager', label: 'Менеджер менеджера' },
  { value: 'manager_level_3', label: 'Менеджер 3-го рівня' },
  { value: 'specific_employee', label: 'Конкретна людина' },
  { value: 'person_reference', label: 'Посилання на особу' },
];

const SUBSTITUTE_TARGET_OPTIONS: SelectOption[] = [
  { value: 'current_responsible', label: 'Відповідальний на момент відсутності' },
  { value: 'hire_responsible', label: 'Відповідальний за найм нового співробітника' },
  { value: 'extra_manager_zaporizhzhia', label: 'Додатковий керівник Запоріжжя' },
  { value: 'extra_manager_lviv', label: 'Додатковий керівник Львів' },
  { value: 'department_operations_director', label: 'Операційний директор відділення' },
];

function createApprovalStep(type: ApprovalOptionKind = 'manager'): ApprovalStepDraft {
  return {
    uiId: `approver-${Date.now()}-${Math.random().toString(36).slice(2)}`,
    type,
    employeeId: null,
    employeeName: '',
  };
}

function createSeniorityLevel(): SeniorityLevelDraft {
  const id = `seniority-${Date.now()}-${Math.random().toString(36).slice(2)}`;
  return {
    uiId: id,
    id,
    seniorityYears: '1',
    periodAmount: '1',
    frequency: 'monthly',
    accrualTiming: 'period_start',
    maxBalance: '',
    carryoverMode: 'none',
    carryoverExpireMonths: '0',
  };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
}

function normalizeApprovalKind(value: unknown): ApprovalOptionKind {
  const raw = typeof value === 'string' ? value : '';
  if (APPROVER_OPTIONS.some((option) => option.value === raw)) return raw as ApprovalOptionKind;
  if (['employee', 'person', 'specific_person', 'specific_user'].includes(raw)) return 'specific_employee';
  if (raw === 'department') return 'department_manager';
  return 'manager';
}

function optionLabel(options: SelectOption[], value: string): string {
  return options.find((option) => option.value === value)?.label ?? 'Менеджер';
}

function normalizeApproverSteps(rawSteps: unknown): ApprovalStepDraft[] {
  const raw = Array.isArray(rawSteps) ? rawSteps : [];
  const steps = raw
    .filter(isRecord)
    .filter((item) => item.type !== '_substitute_config' && item.kind !== 'substitute_config')
    .map((item, index) => {
      const employeeIdRaw = item.employee_id ?? item.employee ?? null;
      const employeeId = typeof employeeIdRaw === 'number' ? employeeIdRaw : Number.parseInt(String(employeeIdRaw ?? ''), 10);
      return {
        uiId: `approver-existing-${index}-${Math.random().toString(36).slice(2)}`,
        type: normalizeApprovalKind(item.type ?? item.kind),
        employeeId: Number.isFinite(employeeId) ? employeeId : null,
        employeeName: typeof item.employee_name === 'string' ? item.employee_name : '',
      };
    });
  return steps.length ? steps : [createApprovalStep()];
}

function normalizeSubstituteDraft(rawSteps: unknown): SubstituteDraft {
  const raw = Array.isArray(rawSteps) ? rawSteps : [];
  const config =
    raw.filter(isRecord).find((item) => item.type === '_substitute_config' || item.kind === 'substitute_config') ??
    raw.filter(isRecord).find((item) => isRecord(item.substitute_approver))?.substitute_approver;
  if (!isRecord(config)) {
    return { sourceType: 'person_reference', targetType: 'current_responsible', employeeId: null };
  }
  const employeeIdRaw = config.employee_id ?? config.employee ?? null;
  const employeeId = typeof employeeIdRaw === 'number' ? employeeIdRaw : Number.parseInt(String(employeeIdRaw ?? ''), 10);
  const targetType = typeof config.target_type === 'string' ? config.target_type : 'current_responsible';
  return {
    sourceType: normalizeApprovalKind(config.source_type ?? config.type),
    targetType: SUBSTITUTE_TARGET_OPTIONS.some((option) => option.value === targetType) ? targetType : 'current_responsible',
    employeeId: Number.isFinite(employeeId) ? employeeId : null,
  };
}

function normalizeSeniorityLevels(rawLevels: unknown): SeniorityLevelDraft[] {
  const raw = Array.isArray(rawLevels) ? rawLevels : [];
  return raw.filter(isRecord).map((level, index) => {
    const id = typeof level.id === 'string' && level.id ? level.id : `seniority-existing-${index}`;
    return {
      uiId: `${id}-${Math.random().toString(36).slice(2)}`,
      id,
      seniorityYears: String(level.seniority_years ?? level.years ?? '1'),
      periodAmount: String(level.period_amount ?? level.bonus_amount ?? '1'),
      frequency: typeof level.frequency === 'string' ? level.frequency : 'monthly',
      accrualTiming: typeof level.accrual_timing === 'string' ? level.accrual_timing : 'period_start',
      maxBalance: level.max_balance == null ? '' : String(level.max_balance),
      carryoverMode: typeof level.carryover_mode === 'string' ? level.carryover_mode : 'none',
      carryoverExpireMonths: String(level.carryover_expire_months ?? '0'),
    };
  });
}

function filterOptions(options: SelectOption[], query: string): SelectOption[] {
  const normalized = query.trim().toLowerCase();
  if (!normalized) return options;
  return options.filter((option) => `${option.label} ${option.subtitle ?? ''} ${option.group ?? ''}`.toLowerCase().includes(normalized));
}

function PolicySelectMenu({
  value,
  options,
  disabled = false,
  open,
  searchable = false,
  query = '',
  placeholder = '-- Виберіть --',
  onQueryChange,
  onToggle,
  onChange,
}: {
  value: string;
  options: SelectOption[];
  disabled?: boolean;
  open: boolean;
  searchable?: boolean;
  query?: string;
  placeholder?: string;
  onQueryChange?: (query: string) => void;
  onToggle: () => void;
  onChange: (value: string) => void;
}) {
  const selected = options.find((option) => option.value === value);
  const visibleOptions = filterOptions(options, query);
  let currentGroup = '';
  return (
    <div className="policy-select-menu">
      <button type="button" className="policy-select-trigger" disabled={disabled} onClick={onToggle}>
        <span>{selected?.label ?? placeholder}</span>
        <ChevronDown size={17} />
      </button>
      {open && !disabled ? (
        <div className="policy-select-popover" role="listbox">
          {searchable ? (
            <label className="policy-select-search">
              <Search size={17} />
              <input value={query} onChange={(event) => onQueryChange?.(event.target.value)} placeholder="Пошук..." autoFocus />
            </label>
          ) : null}
          {visibleOptions.map((option) => {
            const showGroup = option.group && option.group !== currentGroup;
            if (option.group) currentGroup = option.group;
            return (
              <div key={option.value}>
                {showGroup ? <div className="policy-select-group">{option.group}</div> : null}
                <button type="button" className="policy-select-option" onClick={() => onChange(option.value)} role="option">
                  <span>{option.label}</span>
                  {option.subtitle ? <em>{option.subtitle}</em> : null}
                </button>
              </div>
            );
          })}
          {!visibleOptions.length ? <div className="policy-select-empty">Нічого не знайдено</div> : null}
        </div>
      ) : null}
    </div>
  );
}

function PolicyEmployeePicker({
  employees,
  value,
  disabled = false,
  open,
  query,
  onQueryChange,
  onToggle,
  onChange,
}: {
  employees: EmployeeListItem[];
  value: number | null;
  disabled?: boolean;
  open: boolean;
  query: string;
  onQueryChange: (query: string) => void;
  onToggle: () => void;
  onChange: (employeeId: number) => void;
}) {
  const selected = employees.find((employee) => employee.id === value);
  const normalizedQuery = query.trim().toLowerCase();
  const visibleEmployees = employees
    .filter((employee) => {
      if (!normalizedQuery) return true;
      return `${employee.full_name} ${employee.position_name ?? ''} ${employee.department_name ?? ''}`.toLowerCase().includes(normalizedQuery);
    })
    .slice(0, 30);

  return (
    <div className="policy-select-menu">
      <button type="button" className="policy-select-trigger" disabled={disabled} onClick={onToggle}>
        <span>{selected?.full_name ?? '-- Виберіть --'}</span>
        <ChevronDown size={17} />
      </button>
      {open && !disabled ? (
        <div className="policy-select-popover policy-employee-popover" role="listbox">
          <label className="policy-select-search">
            <Search size={17} />
            <input value={query} onChange={(event) => onQueryChange(event.target.value)} placeholder="Пошук..." autoFocus />
          </label>
          {visibleEmployees.map((employee) => {
            const avatarUrl = employeeAvatar(employee);
            return (
              <button type="button" className="policy-employee-option" key={employee.id} onClick={() => onChange(employee.id)} role="option">
                {avatarUrl ? <img src={avatarUrl} alt="" /> : <em>{employeeInitials(employee.full_name)}</em>}
                <span>
                  <strong>{employee.full_name}</strong>
                  <small>{employee.position_name || employee.department_name || 'Співробітник'}</small>
                </span>
              </button>
            );
          })}
          {!visibleEmployees.length ? <div className="policy-select-empty">Нічого не знайдено</div> : null}
        </div>
      ) : null}
    </div>
  );
}

function LeavePolicyWizard({
  initial,
  employees,
  onBack,
  onFinish,
}: {
  initial: PolicyWizardRequest;
  employees: EmployeeListItem[];
  onBack: () => void;
  onFinish: (payload: LeavePolicyPayload) => Promise<void>;
}) {
  type PolicyStep = 'details' | 'accruals' | 'approval' | 'settings';
  const policy = initial.policy;
  const rule = policy?.accrual_rule;
  const [step, setStep] = useState<PolicyStep>('details');
  const [name, setName] = useState(policy?.name ?? initial.leaveType.name);
  const [policyType, setPolicyType] = useState(policy?.policy_type ?? initial.policyType ?? 'manual');
  const [activityType, setActivityType] = useState(policy?.activity_type ?? POLICY_ACTIVITY_OPTIONS[0].value);
  const [countedAs, setCountedAs] = useState(policy?.counted_as ?? 'working_days');
  const [visibility, setVisibility] = useState(policy?.visibility ?? 'everyone');
  const [instructionsHtml, setInstructionsHtml] = useState(policy?.instructions_html ?? '');
  const [deductNonWorkingHolidays, setDeductNonWorkingHolidays] = useState(policy?.deduct_non_working_holidays ?? false);
  const [allowOnDemandAbsence, setAllowOnDemandAbsence] = useState(policy?.allow_on_demand_absence ?? false);
  const [onDemandLimit, setOnDemandLimit] = useState(policy?.on_demand_limit ?? '');
  const [preventOverlapping, setPreventOverlapping] = useState(policy?.prevent_overlapping_requests ?? true);
  const [forbidProbation, setForbidProbation] = useState(policy?.forbid_probation_requests ?? false);
  const [forbidBreakdown, setForbidBreakdown] = useState(policy?.forbid_breakdown_edit ?? false);
  const [restrictAdjustments, setRestrictAdjustments] = useState(policy?.restrict_adjustments_for_employees ?? false);
  const [directReportsOnly, setDirectReportsOnly] = useState(policy?.direct_reports_only ?? false);
  const [minDailyAmount, setMinDailyAmount] = useState(policy?.min_daily_amount ?? '');
  const [minTotalAmount, setMinTotalAmount] = useState(policy?.min_total_amount ?? '');
  const [maxTotalAmount, setMaxTotalAmount] = useState(policy?.max_total_amount ?? '');
  const [minNoticeDays, setMinNoticeDays] = useState(policy?.min_notice_days == null ? '' : String(policy.min_notice_days));
  const [maxNoticeDays, setMaxNoticeDays] = useState(policy?.max_notice_days == null ? '' : String(policy.max_notice_days));
  const [approvalEnabled, setApprovalEnabled] = useState(policy?.approval_enabled ?? true);
  const [approverSteps, setApproverSteps] = useState<ApprovalStepDraft[]>(() => normalizeApproverSteps(policy?.approver_steps));
  const [skipUnassigned, setSkipUnassigned] = useState(policy?.skip_unassigned_approvers ?? false);
  const [allowSubstitute, setAllowSubstitute] = useState(policy?.allow_substitute_approvers ?? false);
  const [allowNegativeBalance, setAllowNegativeBalance] = useState(policy?.allow_negative_balance ?? true);
  const [limitNegativeBalance, setLimitNegativeBalance] = useState(policy?.limit_negative_balance ?? false);
  const [maxNegativeBalance, setMaxNegativeBalance] = useState(policy?.max_negative_balance ?? '');
  const [substituteDraft, setSubstituteDraft] = useState<SubstituteDraft>(() => normalizeSubstituteDraft(policy?.approver_steps));
  const [openApproverMenu, setOpenApproverMenu] = useState<string | null>(null);
  const [openEmployeeMenu, setOpenEmployeeMenu] = useState<string | null>(null);
  const [openSubstituteMenu, setOpenSubstituteMenu] = useState<string | null>(null);
  const [employeeQuery, setEmployeeQuery] = useState('');
  const [substituteQuery, setSubstituteQuery] = useState('');
  const [roundingMethod, setRoundingMethod] = useState(policy?.rounding_method ?? 'nearest');
  const [roundingPrecision, setRoundingPrecision] = useState(policy?.rounding_precision ?? 'two_decimals');
  const [allowWithdraw, setAllowWithdraw] = useState(policy?.allow_withdraw ?? true);
  const [mandatoryComment, setMandatoryComment] = useState(policy?.mandatory_comment ?? false);
  const [allowAttachments, setAllowAttachments] = useState(policy?.allow_attachments ?? false);
  const [notifyApprover, setNotifyApprover] = useState(policy?.notify_approver ?? true);
  const [startDelayAmount, setStartDelayAmount] = useState(String(rule?.start_delay_amount ?? 0));
  const [startDelayUnit, setStartDelayUnit] = useState(rule?.start_delay_unit ?? 'months');
  const [startBalance, setStartBalance] = useState(rule?.start_balance ?? '0.00');
  const [annualAllowance, setAnnualAllowance] = useState(rule?.annual_allowance ?? '24.00');
  const [periodAmount, setPeriodAmount] = useState(rule?.period_amount ?? '2.00');
  const [frequency, setFrequency] = useState(rule?.frequency ?? 'monthly');
  const [accrualTiming, setAccrualTiming] = useState(rule?.accrual_timing ?? 'period_start');
  const [firstAccrual, setFirstAccrual] = useState(rule?.first_accrual ?? 'proportional');
  const [maxBalance, setMaxBalance] = useState(rule?.max_balance ?? '24.00');
  const [carryoverMode, setCarryoverMode] = useState(rule?.carryover_mode ?? 'none');
  const [carryoverLimit, setCarryoverLimit] = useState(rule?.carryover_limit ?? '');
  const [carryoverExpireMonths, setCarryoverExpireMonths] = useState(String(rule?.carryover_expire_months ?? 0));
  const [carryoverDay, setCarryoverDay] = useState(String(rule?.carryover_day ?? 1));
  const [carryoverMonth, setCarryoverMonth] = useState(String(rule?.carryover_month ?? 1));
  const [seniorityBonusEnabled, setSeniorityBonusEnabled] = useState(rule?.seniority_bonus_enabled ?? false);
  const [seniorityLevels, setSeniorityLevels] = useState<SeniorityLevelDraft[]>(() => normalizeSeniorityLevels(rule?.seniority_bonus_levels));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const steps = [
    { key: 'details', label: 'Деталі' },
    { key: 'accruals', label: 'Нарахування та перенесення' },
    { key: 'approval', label: 'Схвалення' },
    { key: 'settings', label: 'Налаштування' },
  ] as const;
  const activeIndex = steps.findIndex((item) => item.key === step);

  function stepEmployeeName(stepDraft: ApprovalStepDraft): string {
    return employees.find((employee) => employee.id === stepDraft.employeeId)?.full_name ?? stepDraft.employeeName;
  }

  function serializedApproverSteps(): unknown[] {
    const stepsPayload = approverSteps.map((item, index) => ({
      type: item.type,
      label: optionLabel(APPROVER_OPTIONS, item.type),
      order: index + 1,
      employee_id: item.type === 'specific_employee' ? item.employeeId : null,
      employee_name: item.type === 'specific_employee' ? stepEmployeeName(item) : '',
    }));
    if (!allowSubstitute) return stepsPayload;
    return [
      ...stepsPayload,
      {
        type: '_substitute_config',
        kind: 'substitute_config',
        source_type: substituteDraft.sourceType,
        source_label: optionLabel(SUBSTITUTE_SOURCE_OPTIONS, substituteDraft.sourceType),
        target_type: substituteDraft.sourceType === 'specific_employee' ? 'specific_employee' : substituteDraft.targetType,
        target_label:
          substituteDraft.sourceType === 'specific_employee'
            ? employees.find((employee) => employee.id === substituteDraft.employeeId)?.full_name ?? ''
            : optionLabel(SUBSTITUTE_TARGET_OPTIONS, substituteDraft.targetType),
        employee_id: substituteDraft.sourceType === 'specific_employee' ? substituteDraft.employeeId : null,
      },
    ];
  }

  function toggleApprovalEnabled(enabled: boolean) {
    setApprovalEnabled(enabled);
    if (enabled) {
      setApproverSteps((current) => (current.length ? current : [createApprovalStep()]));
    }
  }

  function updateApproverStep(uiId: string, patch: Partial<ApprovalStepDraft>) {
    setApproverSteps((current) =>
      current.map((item) =>
        item.uiId === uiId
          ? {
              ...item,
              ...patch,
              employeeId: patch.type && patch.type !== 'specific_employee' ? null : patch.employeeId ?? item.employeeId,
              employeeName: patch.type && patch.type !== 'specific_employee' ? '' : patch.employeeName ?? item.employeeName,
            }
          : item,
      ),
    );
  }

  function adjustLimit(value: string, setter: (next: string) => void, delta: number) {
    const parsed = Number.parseFloat(value.replace(',', '.'));
    const next = Math.max(0, (Number.isFinite(parsed) ? parsed : 0) + delta);
    setter(Number.isInteger(next) ? String(next) : next.toFixed(2));
  }

  function updateSeniorityLevel(uiId: string, patch: Partial<SeniorityLevelDraft>) {
    setSeniorityLevels((current) => current.map((level) => (level.uiId === uiId ? { ...level, ...patch } : level)));
  }

  function addSeniorityLevel() {
    setSeniorityBonusEnabled(true);
    setSeniorityLevels((current) => [...current, createSeniorityLevel()]);
  }

  function serializedSeniorityLevels() {
    if (!seniorityBonusEnabled) return [];
    return seniorityLevels.map((level) => ({
      id: level.id,
      seniority_years: Math.max(0, numberOrNull(level.seniorityYears) ?? 0),
      period_amount: valueOrZero(level.periodAmount),
      frequency: level.frequency,
      accrual_timing: level.accrualTiming,
      max_balance: valueOrNull(level.maxBalance),
      carryover_mode: level.carryoverMode,
      carryover_expire_months: Math.max(0, numberOrNull(level.carryoverExpireMonths) ?? 0),
    }));
  }

  function buildPayload(): LeavePolicyPayload {
    return {
      leave_type: initial.leaveType.id,
      name: name.trim() || initial.leaveType.name,
      policy_type: policyType,
      activity_type: activityType,
      counted_as: countedAs,
      visibility,
      instructions_html: instructionsHtml,
      deduct_non_working_holidays: deductNonWorkingHolidays,
      allow_on_demand_absence: allowOnDemandAbsence,
      on_demand_limit: allowOnDemandAbsence ? valueOrNull(onDemandLimit) : null,
      prevent_overlapping_requests: preventOverlapping,
      forbid_probation_requests: forbidProbation,
      forbid_breakdown_edit: forbidBreakdown,
      restrict_adjustments_for_employees: restrictAdjustments,
      direct_reports_only: directReportsOnly,
      min_daily_amount: valueOrNull(minDailyAmount),
      min_total_amount: valueOrNull(minTotalAmount),
      max_total_amount: valueOrNull(maxTotalAmount),
      min_notice_days: numberOrNull(minNoticeDays),
      max_notice_days: numberOrNull(maxNoticeDays),
      approval_enabled: approvalEnabled,
      skip_unassigned_approvers: skipUnassigned,
      allow_substitute_approvers: allowSubstitute,
      approver_steps: approvalEnabled ? serializedApproverSteps() : [],
      allow_negative_balance: allowNegativeBalance,
      limit_negative_balance: allowNegativeBalance ? limitNegativeBalance : false,
      max_negative_balance: allowNegativeBalance && limitNegativeBalance ? valueOrNull(maxNegativeBalance) : null,
      rounding_method: roundingMethod,
      rounding_precision: roundingPrecision,
      allow_withdraw: allowWithdraw,
      mandatory_comment: mandatoryComment,
      allow_attachments: allowAttachments,
      notify_approver: notifyApprover,
      is_active: true,
      accrual_rule: {
        id: rule?.id ?? 0,
        enabled: policyType === 'accrual',
        start_delay_amount: Math.max(0, numberOrNull(startDelayAmount) ?? 0),
        start_delay_unit: startDelayUnit,
        start_balance: valueOrZero(startBalance),
        annual_allowance: valueOrZero(annualAllowance),
        period_amount: valueOrZero(periodAmount),
        frequency,
        accrual_timing: accrualTiming,
        first_accrual: firstAccrual,
        max_balance: valueOrNull(maxBalance),
        carryover_mode: carryoverMode,
        carryover_limit: valueOrNull(carryoverLimit),
        carryover_expire_months: Math.max(0, numberOrNull(carryoverExpireMonths) ?? 0),
        carryover_day: Math.min(31, Math.max(1, numberOrNull(carryoverDay) ?? 1)),
        carryover_month: Math.min(12, Math.max(1, numberOrNull(carryoverMonth) ?? 1)),
        seniority_bonus_enabled: seniorityBonusEnabled,
        seniority_bonus_levels: serializedSeniorityLevels(),
      },
    };
  }

  async function submit() {
    if (!name.trim()) {
      setError('Введіть ім’я політики.');
      return;
    }
    setSaving(true);
    setError('');
    try {
      await onFinish(buildPayload());
    } catch {
      setError('Не вдалося зберегти політику. Перевірте поля та спробуйте ще раз.');
      setSaving(false);
    }
  }

  function goNext() {
    if (activeIndex < steps.length - 1) {
      setStep(steps[activeIndex + 1].key);
      return;
    }
    void submit();
  }

  function goPrevious() {
    if (step === 'details') {
      onBack();
      return;
    }
    setStep(steps[Math.max(0, activeIndex - 1)].key);
  }

  return (
    <main className="settings-page leave-policy-page">
      <button type="button" className="report-back leave-policy-back" onClick={onBack}>
        <ChevronLeft size={16} />
        <span>Назад</span>
      </button>
      <h1>{policy ? 'Редагувати політику відсутності' : 'Нова політика відсутності'}</h1>

      <div className="leave-policy-tabs" role="tablist" aria-label="Кроки політики">
        {steps.map((item, index) => {
          const isDone = index < activeIndex;
          const isActive = item.key === step;
          return (
            <button
              type="button"
              key={item.key}
              role="tab"
              className={`${isActive ? 'active' : ''} ${isDone ? 'done' : ''}`}
              onClick={() => setStep(item.key)}
            >
              {isDone ? <CheckCircle2 size={15} /> : null}
              <span>{item.label}</span>
            </button>
          );
        })}
      </div>

      {step === 'details' ? (
        <section className="leave-policy-card">
          <div className="leave-policy-section">
            <h2>Деталі</h2>
            <label className="leave-policy-field">
              <span>Ім’я</span>
              <input value={name} onChange={(event) => setName(event.target.value)} autoFocus />
            </label>
            <label className="leave-policy-field">
              <span>Тип активності</span>
              <select value={activityType} onChange={(event) => setActivityType(event.target.value)}>
                {POLICY_ACTIVITY_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
              <small>Визначає, чи відсутність є робочою, оплачуваною або неоплачуваною.</small>
            </label>
            <label className="leave-policy-field">
              <span>Тип політики</span>
              <select value={policyType} onChange={(event) => setPolicyType(event.target.value)}>
                {POLICY_TYPE_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
              <small>Нарахування створює баланс автоматично, ручна політика змінюється заявками або коригуваннями.</small>
            </label>
            <label className="leave-policy-field">
              <span>Враховується як</span>
              <select value={countedAs} onChange={(event) => setCountedAs(event.target.value)}>
                {POLICY_COUNTED_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
              <small>Визначає, рахувати тривалість за робочими чи календарними днями.</small>
            </label>
            <label className="leave-policy-check">
              <input
                type="checkbox"
                checked={deductNonWorkingHolidays}
                onChange={(event) => setDeductNonWorkingHolidays(event.target.checked)}
              />
              <span>
                <strong>Вираховувати неробочі святкові дні із залишку відпустки</strong>
                <em>Якщо ввімкнено, неробочі святкові дні включатимуться до розбивки як використані дні та списуватимуться з балансу.</em>
              </span>
            </label>
            <label className="leave-policy-field">
              <span>Інструкції</span>
              <div className="leave-policy-editor">
                <ToolbarStub />
                <textarea value={instructionsHtml} onChange={(event) => setInstructionsHtml(event.target.value)} />
              </div>
            </label>
            <label className="leave-policy-check">
              <input
                type="checkbox"
                checked={allowOnDemandAbsence}
                onChange={(event) => setAllowOnDemandAbsence(event.target.checked)}
              />
              <span>
                <strong>Увімкнути відсутність на вимогу</strong>
                <em>Якщо ввімкнено, укажіть суму відсутності на вимогу, яку працівники можуть взяти в межах свого балансу.</em>
              </span>
            </label>
            {allowOnDemandAbsence ? (
              <label className="leave-policy-field leave-policy-number-control">
                <span>Кількість відсутностей на вимогу</span>
                <div>
                  <input value={onDemandLimit} onChange={(event) => setOnDemandLimit(event.target.value)} placeholder="0,0" inputMode="decimal" />
                  <button type="button" aria-label="Зменшити" onClick={() => adjustLimit(onDemandLimit, setOnDemandLimit, -1)}>
                    <Minus size={15} />
                  </button>
                  <button type="button" aria-label="Збільшити" onClick={() => adjustLimit(onDemandLimit, setOnDemandLimit, 1)}>
                    <Plus size={15} />
                  </button>
                  <em>днів</em>
                </div>
              </label>
            ) : null}
          </div>
          <div className="leave-policy-section">
            <h2>Обмеження</h2>
            <label className="leave-policy-check">
              <input type="checkbox" checked={allowNegativeBalance} onChange={(event) => setAllowNegativeBalance(event.target.checked)} />
              <span>
                <strong>Дозволити запити з негативним балансом</strong>
                <em>Якщо вимкнено, працівники не зможуть залишати запити, якщо це призведе до негативного балансу.</em>
              </span>
            </label>
            {allowNegativeBalance ? (
              <div className="leave-policy-nested">
                <label className="leave-policy-check">
                  <input
                    type="checkbox"
                    checked={limitNegativeBalance}
                    onChange={(event) => setLimitNegativeBalance(event.target.checked)}
                  />
                  <span>
                    <strong>Встановіть максимальний негативний баланс при якому можна запросити відсутність</strong>
                  </span>
                </label>
                {limitNegativeBalance ? (
                  <label className="leave-policy-field leave-policy-number-control">
                    <span>Максимальний негативний баланс</span>
                    <div>
                      <input value={maxNegativeBalance} onChange={(event) => setMaxNegativeBalance(event.target.value)} placeholder="Макс" inputMode="decimal" />
                      <button type="button" aria-label="Зменшити" onClick={() => adjustLimit(maxNegativeBalance, setMaxNegativeBalance, -1)}>
                        <Minus size={15} />
                      </button>
                      <button type="button" aria-label="Збільшити" onClick={() => adjustLimit(maxNegativeBalance, setMaxNegativeBalance, 1)}>
                        <Plus size={15} />
                      </button>
                      <em>днів</em>
                    </div>
                  </label>
                ) : null}
              </div>
            ) : null}
            <label className="leave-policy-check">
              <input type="checkbox" checked={preventOverlapping} onChange={(event) => setPreventOverlapping(event.target.checked)} />
              <span>
                <strong>Обмежити запити, які збігаються</strong>
                <em>Якщо ввімкнено, співробітники не зможуть подавати запити, які збігаються з іншими відсутностями.</em>
              </span>
            </label>
            <label className="leave-policy-check">
              <input type="checkbox" checked={forbidProbation} onChange={(event) => setForbidProbation(event.target.checked)} />
              <span>
                <strong>Заборонити запити під час випр. терміну</strong>
                <em>Працівники на випробувальному терміні не зможуть подати запит за цією політикою.</em>
              </span>
            </label>
            <label className="leave-policy-check">
              <input type="checkbox" checked={forbidBreakdown} onChange={(event) => setForbidBreakdown(event.target.checked)} />
              <span>
                <strong>Заборонити редагування розбивки</strong>
                <em>Сума днів у заявці буде рахуватися політикою без ручного редагування співробітником.</em>
              </span>
            </label>
            <label className="leave-policy-check">
              <input type="checkbox" checked={restrictAdjustments} onChange={(event) => setRestrictAdjustments(event.target.checked)} />
              <span>
                <strong>Коригування обмежені</strong>
                <em>Зміни балансу вручну доступні тільки адміністраторам політик.</em>
              </span>
            </label>
            <label className="leave-policy-check">
              <input type="checkbox" checked={directReportsOnly} onChange={(event) => setDirectReportsOnly(event.target.checked)} />
              <span>
                <strong>Обмежити надсилання запитів безпосередньо людьми</strong>
                <em>Менеджери працюють тільки із запитами своїх прямих підлеглих.</em>
              </span>
            </label>
            <p className="leave-policy-note">Нижче ви можете налаштувати мінімальні та максимальні обмеження для запитів на відсутність.</p>
            <div className="leave-policy-limits">
              {[
                { label: 'Мінімальна щоденна сума', value: minDailyAmount, setter: setMinDailyAmount, wide: true },
                { label: 'Мінімальна загальна сума', value: minTotalAmount, setter: setMinTotalAmount, wide: false },
                { label: 'Максимальна загальна сума', value: maxTotalAmount, setter: setMaxTotalAmount, wide: false },
                { label: 'Мінімальний термін повідомлення', value: minNoticeDays, setter: setMinNoticeDays, wide: false },
                { label: 'Максимальний термін повідомлення', value: maxNoticeDays, setter: setMaxNoticeDays, wide: false },
              ].map((field) => (
                <label className={field.wide ? 'wide' : ''} key={field.label}>
                  <span>{field.label}</span>
                  <div>
                    <input
                      value={field.value}
                      onChange={(event) => field.setter(event.target.value)}
                      placeholder={field.label.includes('Максим') ? 'Макс' : 'Мін'}
                      inputMode="decimal"
                    />
                    <button type="button" aria-label="Зменшити" onClick={() => adjustLimit(field.value, field.setter, -1)}>
                      <Minus size={15} />
                    </button>
                    <button type="button" aria-label="Збільшити" onClick={() => adjustLimit(field.value, field.setter, 1)}>
                      <Plus size={15} />
                    </button>
                    <em>днях</em>
                  </div>
                </label>
              ))}
            </div>
          </div>
        </section>
      ) : null}

      {step === 'accruals' ? (
        <section className="leave-policy-card leave-policy-accrual-card">
          <div className="leave-policy-section compact">
            <h2>Нарахування та перенесення</h2>
            <label className="leave-policy-check inline">
              <input
                type="checkbox"
                checked={policyType === 'accrual'}
                onChange={(event) => setPolicyType(event.target.checked ? 'accrual' : 'manual')}
              />
              <strong>Автоматично нараховувати баланс</strong>
            </label>
            <fieldset className="leave-policy-accrual-panel" disabled={policyType !== 'accrual'}>
              <strong className="leave-policy-accrual-title">Нарахування</strong>
              <div className="leave-policy-accrual-line start">
                <span>Починається через</span>
                <input value={startDelayAmount} onChange={(event) => setStartDelayAmount(event.target.value)} inputMode="numeric" />
                <select value={startDelayUnit} onChange={(event) => setStartDelayUnit(event.target.value)}>
                  {DELAY_UNIT_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
                <span>після дати прийому, з початковим залишком</span>
                <input value={startBalance} onChange={(event) => setStartBalance(event.target.value)} inputMode="decimal" />
                <span>днів</span>
              </div>
              <div className="leave-policy-accrual-line earn">
                <span>Нарахування</span>
                <input value={periodAmount} onChange={(event) => setPeriodAmount(event.target.value)} inputMode="decimal" />
                <span>днів</span>
                <select value={frequency} onChange={(event) => setFrequency(event.target.value)}>
                  {ACCRUAL_FREQUENCY_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
                <span>на</span>
                <select value={accrualTiming} onChange={(event) => setAccrualTiming(event.target.value)}>
                  {ACCRUAL_TIMING_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </div>
              <label className="leave-policy-accrual-stack">
                <span>Максимальний баланс</span>
                <div className="leave-policy-number-control compact">
                  <input value={maxBalance} onChange={(event) => setMaxBalance(event.target.value)} inputMode="decimal" />
                  <button type="button" aria-label="Зменшити" onClick={() => adjustLimit(maxBalance, setMaxBalance, -1)}>
                    <Minus size={15} />
                  </button>
                  <button type="button" aria-label="Збільшити" onClick={() => adjustLimit(maxBalance, setMaxBalance, 1)}>
                    <Plus size={15} />
                  </button>
                  <em>днів</em>
                </div>
                <small>Максимальна кількість днів, яку можна нарахувати.</small>
              </label>
              <div className="leave-policy-accrual-line carry">
                <span>Сума перенесення</span>
                <select value={carryoverMode} onChange={(event) => setCarryoverMode(event.target.value)}>
                  {CARRYOVER_MODE_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
                <span>Використайте нараховані дні або втратите у дату перенесення</span>
                <input value={carryoverExpireMonths} onChange={(event) => setCarryoverExpireMonths(event.target.value)} inputMode="numeric" />
                <span>місяці</span>
              </div>
              {carryoverMode === 'limited' ? (
                <label className="leave-policy-accrual-stack compact-limit">
                  <span>Ліміт перенесення</span>
                  <input value={carryoverLimit} onChange={(event) => setCarryoverLimit(event.target.value)} inputMode="decimal" />
                </label>
              ) : null}
              <label className="leave-policy-check">
                <input
                  type="checkbox"
                  checked={seniorityBonusEnabled}
                  onChange={(event) => {
                    const enabled = event.target.checked;
                    setSeniorityBonusEnabled(enabled);
                    if (enabled && !seniorityLevels.length) {
                      setSeniorityLevels([createSeniorityLevel()]);
                    }
                  }}
                  disabled={policyType !== 'accrual'}
                />
                <span>
                  <strong>Надати додаткову відпустку з урахуванням загального досвіду роботи</strong>
                </span>
              </label>
              {seniorityBonusEnabled ? (
                <div className="leave-policy-seniority-levels">
                  {seniorityLevels.map((level, index) => (
                    <div className="leave-policy-seniority-level" key={level.uiId}>
                      <div className="leave-policy-seniority-head">
                        <strong>Рівень {index + 1}</strong>
                        <button
                          type="button"
                          className="secondary-action"
                          onClick={() => setSeniorityLevels((current) => current.filter((item) => item.uiId !== level.uiId))}
                        >
                          <Trash2 size={15} />
                          Видалити рівень
                        </button>
                      </div>
                      <div className="leave-policy-seniority-grid">
                        <label className="leave-policy-field">
                          <span>Загальний досвід роботи</span>
                          <div className="leave-policy-unit-input">
                            <input
                              value={level.seniorityYears}
                              onChange={(event) => updateSeniorityLevel(level.uiId, { seniorityYears: event.target.value })}
                              inputMode="numeric"
                            />
                            <em>роки</em>
                          </div>
                        </label>
                        <label className="leave-policy-field">
                          <span>Нарахування додаткової відпустки</span>
                          <div className="leave-policy-unit-input">
                            <input
                              value={level.periodAmount}
                              onChange={(event) => updateSeniorityLevel(level.uiId, { periodAmount: event.target.value })}
                              inputMode="decimal"
                            />
                            <em>днів</em>
                          </div>
                        </label>
                        <label className="leave-policy-field">
                          <span>Частота</span>
                          <select value={level.frequency} onChange={(event) => updateSeniorityLevel(level.uiId, { frequency: event.target.value })}>
                            {ACCRUAL_FREQUENCY_OPTIONS.map((option) => (
                              <option key={option.value} value={option.value}>
                                {option.label}
                              </option>
                            ))}
                          </select>
                        </label>
                        <label className="leave-policy-field">
                          <span>Коли нараховувати</span>
                          <select value={level.accrualTiming} onChange={(event) => updateSeniorityLevel(level.uiId, { accrualTiming: event.target.value })}>
                            {ACCRUAL_TIMING_OPTIONS.map((option) => (
                              <option key={option.value} value={option.value}>
                                {option.label}
                              </option>
                            ))}
                          </select>
                        </label>
                        <label className="leave-policy-field">
                          <span>Максимальний баланс</span>
                          <input
                            value={level.maxBalance}
                            onChange={(event) => updateSeniorityLevel(level.uiId, { maxBalance: event.target.value })}
                            inputMode="decimal"
                          />
                        </label>
                        <label className="leave-policy-field">
                          <span>Сума перенесення</span>
                          <select value={level.carryoverMode} onChange={(event) => updateSeniorityLevel(level.uiId, { carryoverMode: event.target.value })}>
                            {CARRYOVER_MODE_OPTIONS.map((option) => (
                              <option key={option.value} value={option.value}>
                                {option.label}
                              </option>
                            ))}
                          </select>
                        </label>
                      </div>
                    </div>
                  ))}
                </div>
              ) : null}
            </fieldset>
            <button type="button" className="secondary-action leave-policy-add-level" disabled={policyType !== 'accrual'} onClick={addSeniorityLevel}>
              <Plus size={15} />
              Додати рівень
            </button>
          </div>
          <div className="leave-policy-section compact">
            <h2>Перенесення</h2>
            <fieldset className="leave-policy-carryover-date" disabled={policyType !== 'accrual'}>
              <label className="leave-policy-field">
                <span>Дата перенесення</span>
                <select value="specific" disabled>
                  <option value="specific">Конкретна дата</option>
                </select>
              </label>
              <label className="leave-policy-field">
                <span>День</span>
                <select value={carryoverDay} onChange={(event) => setCarryoverDay(event.target.value)}>
                  {CARRYOVER_DAY_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="leave-policy-field">
                <span>Місяць</span>
                <select value={carryoverMonth} onChange={(event) => setCarryoverMonth(event.target.value)}>
                  {MONTH_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
            </fieldset>
          </div>
          <div className="leave-policy-section compact">
            <h2>Налаштування нарахувань</h2>
            <fieldset className="leave-policy-two-cols compact" disabled={policyType !== 'accrual'}>
              <label className="leave-policy-field">
                <span>Перше нарахування</span>
                <select value={firstAccrual} onChange={(event) => setFirstAccrual(event.target.value)}>
                  {FIRST_ACCRUAL_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="leave-policy-field">
                <span>Нарахування трапляються</span>
                <select value={accrualTiming} onChange={(event) => setAccrualTiming(event.target.value)}>
                  {ACCRUAL_TIMING_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="leave-policy-field">
                <span>Річний ліміт</span>
                <input value={annualAllowance} onChange={(event) => setAnnualAllowance(event.target.value)} inputMode="decimal" />
              </label>
            </fieldset>
          </div>
        </section>
      ) : null}

      {step === 'approval' ? (
        <section className="leave-policy-card leave-policy-approval-card">
          <div className="leave-policy-section">
            <h2>Схвалення</h2>
            <label className="leave-policy-check inline">
              <input type="checkbox" checked={approvalEnabled} onChange={(event) => toggleApprovalEnabled(event.target.checked)} />
              <strong>Увімкнути схвалення</strong>
            </label>
            <div className="leave-policy-approver-list">
              {approverSteps.map((item) => (
                <div className={`leave-policy-approver-row ${item.type === 'specific_employee' ? '' : 'single'}`} key={item.uiId}>
                  <PolicySelectMenu
                    value={item.type}
                    options={APPROVER_OPTIONS}
                    disabled={!approvalEnabled}
                    open={openApproverMenu === item.uiId}
                    onToggle={() => {
                      setEmployeeQuery('');
                      setOpenEmployeeMenu(null);
                      setOpenApproverMenu((current) => (current === item.uiId ? null : item.uiId));
                    }}
                    onChange={(value) => {
                      updateApproverStep(item.uiId, { type: value as ApprovalOptionKind });
                      setOpenApproverMenu(null);
                    }}
                  />
                  {item.type === 'specific_employee' ? (
                    <PolicyEmployeePicker
                      employees={employees}
                      value={item.employeeId}
                      disabled={!approvalEnabled}
                      open={openEmployeeMenu === item.uiId}
                      query={employeeQuery}
                      onQueryChange={setEmployeeQuery}
                      onToggle={() => {
                        setEmployeeQuery('');
                        setOpenApproverMenu(null);
                        setOpenEmployeeMenu((current) => (current === item.uiId ? null : item.uiId));
                      }}
                      onChange={(employeeId) => {
                        updateApproverStep(item.uiId, { employeeId, employeeName: employees.find((employee) => employee.id === employeeId)?.full_name ?? '' });
                        setOpenEmployeeMenu(null);
                      }}
                    />
                  ) : (
                    <span aria-hidden="true" />
                  )}
                  <button
                    type="button"
                    className="icon-button"
                    aria-label="Видалити схвалювача"
                    disabled={!approvalEnabled}
                    onClick={() => setApproverSteps((current) => current.filter((stepItem) => stepItem.uiId !== item.uiId))}
                  >
                    <X size={18} />
                  </button>
                </div>
              ))}
            </div>
            <button
              type="button"
              className="secondary-action leave-policy-add-approver"
              disabled={!approvalEnabled}
              onClick={() => setApproverSteps((current) => [...current, createApprovalStep()])}
            >
              <Plus size={15} />
              Додати схвалювача
            </button>
            <label className="leave-policy-check">
              <input type="checkbox" checked={skipUnassigned} onChange={(event) => setSkipUnassigned(event.target.checked)} />
              <span>
                <strong>Пропустити непризначені схвалення</strong>
                <em>Запити, в яких відсутні відповідальні особи, будуть автоматично схвалені.</em>
              </span>
            </label>
            <label className="leave-policy-check">
              <input type="checkbox" checked={allowSubstitute} onChange={(event) => setAllowSubstitute(event.target.checked)} />
              <span>
                <strong>Дозволити схвалювати заступникам</strong>
                <em>Запити будуть перенаправлені вибраному заступнику, якщо схвалювач недоступний.</em>
              </span>
            </label>
            {allowSubstitute ? (
              <div className="leave-policy-substitute-row">
                <PolicySelectMenu
                  value={substituteDraft.sourceType}
                  options={SUBSTITUTE_SOURCE_OPTIONS}
                  disabled={!approvalEnabled}
                  open={openSubstituteMenu === 'source'}
                  onToggle={() => {
                    setSubstituteQuery('');
                    setOpenSubstituteMenu((current) => (current === 'source' ? null : 'source'));
                  }}
                  onChange={(value) => {
                    setSubstituteDraft((current) => ({ ...current, sourceType: value as ApprovalOptionKind }));
                    setOpenSubstituteMenu(null);
                  }}
                />
                {substituteDraft.sourceType === 'specific_employee' ? (
                  <PolicyEmployeePicker
                    employees={employees}
                    value={substituteDraft.employeeId}
                    disabled={!approvalEnabled}
                    open={openSubstituteMenu === 'employee'}
                    query={substituteQuery}
                    onQueryChange={setSubstituteQuery}
                    onToggle={() => {
                      setSubstituteQuery('');
                      setOpenSubstituteMenu((current) => (current === 'employee' ? null : 'employee'));
                    }}
                    onChange={(employeeId) => {
                      setSubstituteDraft((current) => ({ ...current, employeeId }));
                      setOpenSubstituteMenu(null);
                    }}
                  />
                ) : (
                  <PolicySelectMenu
                    value={substituteDraft.targetType}
                    options={SUBSTITUTE_TARGET_OPTIONS}
                    disabled={!approvalEnabled}
                    searchable
                    query={substituteQuery}
                    onQueryChange={setSubstituteQuery}
                    open={openSubstituteMenu === 'target'}
                    onToggle={() => {
                      setSubstituteQuery('');
                      setOpenSubstituteMenu((current) => (current === 'target' ? null : 'target'));
                    }}
                    onChange={(value) => {
                      setSubstituteDraft((current) => ({ ...current, targetType: value }));
                      setOpenSubstituteMenu(null);
                    }}
                  />
                )}
              </div>
            ) : null}
          </div>
        </section>
      ) : null}

      {step === 'settings' ? (
        <section className="leave-policy-card">
          <div className="leave-policy-section">
            <h2>Округлення балансу</h2>
            <p>Як відображається баланс відсутності працівникам.</p>
            <div className="leave-policy-two-cols">
              <label className="leave-policy-field">
                <span>Метод округлення</span>
                <select value={roundingMethod} onChange={(event) => setRoundingMethod(event.target.value)}>
                  <option value="nearest">До найближчого</option>
                  <option value="down">Вниз</option>
                  <option value="up">Вгору</option>
                </select>
              </label>
              <label className="leave-policy-field">
                <span>Точність округлення</span>
                <select value={roundingPrecision} onChange={(event) => setRoundingPrecision(event.target.value)}>
                  <option value="two_decimals">Два знаки після коми</option>
                  <option value="one_decimal">Один знак після коми</option>
                  <option value="integer">Ціле число</option>
                </select>
              </label>
            </div>
          </div>
          <div className="leave-policy-section">
            <h2>Видимість</h2>
            <p>Показувати ім’я типу відсутності в календарях і на домашній сторінці.</p>
            <label className="leave-policy-radio">
              <input
                type="radio"
                name="visibility"
                checked={visibility === 'everyone'}
                onChange={() => setVisibility('everyone')}
              />
              <span>Для всіх</span>
            </label>
            <label className="leave-policy-radio">
              <input
                type="radio"
                name="visibility"
                checked={visibility === 'self_only'}
                onChange={() => setVisibility('self_only')}
              />
              <span>Для мене</span>
            </label>
          </div>
          <div className="leave-policy-section">
            <h2>Налаштування</h2>
            <label className="leave-policy-check">
              <input type="checkbox" checked={allowWithdraw} onChange={(event) => setAllowWithdraw(event.target.checked)} />
              <span>
                <strong>Дозволити відкликати запити</strong>
                <em>Співробітники зможуть відкликати запит поки не настав перший день відпустки.</em>
              </span>
            </label>
            <label className="leave-policy-check">
              <input type="checkbox" checked={mandatoryComment} onChange={(event) => setMandatoryComment(event.target.checked)} />
              <span>
                <strong>Обов’язковий коментар</strong>
                <em>Щоб надіслати запит, співробітник має написати нотатку.</em>
              </span>
            </label>
            <label className="leave-policy-check">
              <input type="checkbox" checked={allowAttachments} onChange={(event) => setAllowAttachments(event.target.checked)} />
              <span>
                <strong>Дозволити вкладення</strong>
                <em>Співробітник зможе завантажити файл до своїх запитів.</em>
              </span>
            </label>
            <label className="leave-policy-check">
              <input type="checkbox" checked={notifyApprover} onChange={(event) => setNotifyApprover(event.target.checked)} />
              <span>
                <strong>Увімкнути сповіщення про схвалення</strong>
                <em>Повідомлення для листа про схвалений запит.</em>
              </span>
            </label>
            <div className="leave-policy-editor">
              <ToolbarStub />
              <textarea value={instructionsHtml} onChange={(event) => setInstructionsHtml(event.target.value)} />
            </div>
          </div>
        </section>
      ) : null}

      <footer className="leave-policy-footer">
        <button type="button" className="secondary-action" onClick={goPrevious}>
          <ChevronLeft size={16} />
                {step === 'details' ? 'Скасувати' : 'Назад'}
        </button>
        {error ? <span className="leave-policy-footer-error">{error}</span> : null}
        <button type="button" className="primary-action" onClick={goNext} disabled={saving}>
          {step === 'settings' ? (saving ? 'Збереження…' : 'Завершити') : 'Далі'}
          {step === 'settings' ? <CheckCircle2 size={16} /> : <ChevronDown className="next-icon" size={16} />}
        </button>
      </footer>
    </main>
  );
}

function LeavePolicyPeopleDrawer({
  policy,
  type,
  rows,
  onClose,
}: {
  policy: LeavePolicy;
  type: LeaveType;
  rows: PolicyPersonRow[];
  onClose: () => void;
}) {
  const pageSize = 10;
  const [page, setPage] = useState(1);
  const pageCount = Math.max(1, Math.ceil(rows.length / pageSize));
  const safePage = Math.min(page, pageCount);
  const visibleRows = rows.slice((safePage - 1) * pageSize, safePage * pageSize);

  function go(nextPage: number) {
    setPage(Math.min(Math.max(nextPage, 1), pageCount));
  }

  return (
    <aside className="leave-people-drawer" aria-label={`Призначення ${policy.name}`}>
      <div className="leave-people-drawer-head">
        <h2>Призначення</h2>
        <button type="button" className="icon-button" onClick={onClose} aria-label="Закрити">
          <X size={20} />
        </button>
      </div>
      <div className="leave-people-drawer-meta">
        <span>
          Відображено {visibleRows.length ? (safePage - 1) * pageSize + 1 : 0} - {Math.min(safePage * pageSize, rows.length)} з {rows.length}
        </span>
        <div className="leave-people-pager compact">
          <button type="button" onClick={() => go(safePage - 1)} disabled={safePage <= 1} aria-label="Попередня сторінка">
            <ChevronLeft size={16} />
          </button>
          {[1, 2, 3, 4, 5].filter((item) => item <= pageCount).map((item) => (
            <button key={item} type="button" className={safePage === item ? 'active' : ''} onClick={() => go(item)}>
              {item}
            </button>
          ))}
          {pageCount > 6 ? <span>...</span> : null}
          {pageCount > 5 ? (
            <button type="button" className={safePage === pageCount ? 'active' : ''} onClick={() => go(pageCount)}>
              {pageCount}
            </button>
          ) : null}
          <button type="button" onClick={() => go(safePage + 1)} disabled={safePage >= pageCount} aria-label="Наступна сторінка">
            <ChevronDown className="next-icon" size={16} />
          </button>
        </div>
      </div>
      <div className="leave-people-table-shell">
        <table className="leave-people-table">
          <thead>
            <tr>
              <th>Повне ім'я</th>
              <th>Дата початку</th>
              <th>Діє з</th>
            </tr>
          </thead>
          <tbody>
            {visibleRows.length ? (
              visibleRows.map((row) => (
                <tr key={row.employeeId}>
                  <td>
                    <span className="leave-person-cell">
                      {row.avatarUrl ? <img src={row.avatarUrl} alt="" /> : <em>{employeeInitials(row.fullName)}</em>}
                      <span>
                        <strong>{row.fullName}</strong>
                        <small>{row.position || type.name}</small>
                      </span>
                    </span>
                  </td>
                  <td>{dateLabel(row.effectiveOn)}</td>
                  <td>{dateLabel(row.effectiveOn)}</td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={3} className="leave-people-empty">
                  Людей не знайдено
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <div className="leave-people-pager">
        <button type="button" onClick={() => go(safePage - 1)} disabled={safePage <= 1} aria-label="Попередня сторінка">
          <ChevronLeft size={16} />
        </button>
        {Array.from({ length: Math.min(pageCount, 5) }, (_, index) => index + 1).map((item) => (
          <button key={item} type="button" className={safePage === item ? 'active' : ''} onClick={() => go(item)}>
            {item}
          </button>
        ))}
        {pageCount > 6 ? <span>...</span> : null}
        {pageCount > 5 ? (
          <button type="button" className={safePage === pageCount ? 'active' : ''} onClick={() => go(pageCount)}>
            {pageCount}
          </button>
        ) : null}
        <button type="button" onClick={() => go(safePage + 1)} disabled={safePage >= pageCount} aria-label="Наступна сторінка">
          <ChevronDown className="next-icon" size={16} />
        </button>
      </div>
    </aside>
  );
}

function LeaveAssignmentsView({
  employees,
  types,
  policiesByType,
  onChanged,
  onBack,
}: {
  employees: EmployeeListItem[];
  types: LeaveTypeWithPolicies[];
  policiesByType: Map<number, LeavePolicy[]>;
  onChanged: () => Promise<void>;
  onBack: () => void;
}) {
  const [query, setQuery] = useState('');
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [action, setAction] = useState<'assign' | 'recalculate' | 'remove'>('assign');
  const [leaveTypeId, setLeaveTypeId] = useState('');
  const [policyId, setPolicyId] = useState('');
  const [effectiveOn, setEffectiveOn] = useState(new Date().toISOString().slice(0, 10));
  const [initialBalance, setInitialBalance] = useState('0.00');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const selectedEmployees = employees.filter((employee) => selectedIds.has(employee.id));
  const typePolicies = leaveTypeId ? policiesByType.get(Number(leaveTypeId)) ?? [] : [];
  const availableEmployees = employees.filter((employee) => {
    if (selectedIds.has(employee.id)) return false;
    const needle = query.trim().toLowerCase();
    if (!needle) return true;
    return [employee.full_name, employee.position_name, employee.department_name]
      .filter(Boolean)
      .join(' ')
      .toLowerCase()
      .includes(needle);
  });

  useEffect(() => {
    if (!leaveTypeId) {
      setPolicyId('');
      return;
    }
    const firstPolicy = policiesByType.get(Number(leaveTypeId))?.[0];
    setPolicyId(firstPolicy ? String(firstPolicy.id) : '');
  }, [leaveTypeId, policiesByType]);

  function toggleEmployee(id: number) {
    setSelectedIds((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function selectAllVisible() {
    setSelectedIds((current) => {
      const next = new Set(current);
      availableEmployees.forEach((employee) => next.add(employee.id));
      return next;
    });
  }

  async function submitAction() {
    const selectedPolicy = Number(policyId);
    if (!selectedPolicy) {
      setError('Виберіть політику відсутності.');
      return;
    }
    if (action !== 'recalculate' && !selectedEmployees.length) {
      setError('Виберіть хоча б одного співробітника.');
      return;
    }
    setSaving(true);
    setError('');
    try {
      if (action === 'recalculate') {
        await api.recalculateLeavePolicy(selectedPolicy);
      } else if (action === 'remove') {
        await api.bulkRemoveLeavePolicy({
          policy: selectedPolicy,
          employee_ids: selectedEmployees.map((employee) => employee.id),
          effective_on: effectiveOn,
        });
      } else {
        await api.bulkAssignLeavePolicy({
          policy: selectedPolicy,
          employee_ids: selectedEmployees.map((employee) => employee.id),
          effective_on: effectiveOn,
          initial_balance: valueOrZero(initialBalance),
        });
      }
      await onChanged();
      onBack();
    } catch {
      setError('Не вдалося виконати дію. Перевірте політику та спробуйте ще раз.');
      setSaving(false);
    }
  }

  return (
    <main className="settings-page leave-assignments-page">
      <button type="button" className="report-back" onClick={onBack}>
        <ChevronLeft size={16} />
        <span>Назад</span>
      </button>
      <h1>Типи відсутностей</h1>
      <div className="leave-assignment-tabs">
        <button type="button" className="active">
          Подробиці
        </button>
        <button type="button">Перегляд</button>
      </div>
      <div className="leave-assignment-toolbar">
        <label>
          <Search size={18} />
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Пошук..." />
        </label>
        <button type="button" className="secondary-action">
          Фільтр
          <ChevronDown className="next-icon" size={16} />
        </button>
      </div>

      <section className="leave-assignment-card leave-assignment-people-card">
        <div className="leave-assignment-card-head">
          <h2>Вибрати людей</h2>
          <p>Виберіть людей, яких потрібно масово перемістити. Їх буде переведено до вибраної політики.</p>
        </div>
        <div className="leave-assignment-columns-head">
          <span>
            Доступні люди <em>{employees.length}</em>
          </span>
          <button type="button" onClick={selectAllVisible}>
            Вибрати всіх
          </button>
          <span>
            Вибрано для перенесення <em>{selectedEmployees.length}</em>
          </span>
          <button type="button" onClick={() => setSelectedIds(new Set())}>
            Скинути все
          </button>
        </div>
        <div className="leave-assignment-columns">
          <div className="leave-assignment-list">
            <label className="leave-assignment-search">
              <Search size={17} />
              <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Пошук..." />
            </label>
            <div className="leave-assignment-scroll">
              {availableEmployees.map((employee) => (
                <button type="button" key={employee.id} onClick={() => toggleEmployee(employee.id)}>
                  {employee.full_name}
                </button>
              ))}
            </div>
          </div>
          <div className="leave-assignment-list selected">
            <label className="leave-assignment-search">
              <Search size={17} />
              <input placeholder="Пошук..." readOnly />
            </label>
            {selectedEmployees.length ? (
              <div className="leave-assignment-scroll">
                {selectedEmployees.map((employee) => (
                  <button type="button" key={employee.id} onClick={() => toggleEmployee(employee.id)}>
                    {employee.full_name}
                  </button>
                ))}
              </div>
            ) : (
              <div className="leave-assignment-empty">
                <ClipboardList size={54} />
                <span>Людей не вибрано</span>
              </div>
            )}
          </div>
        </div>
      </section>

      <section className="leave-assignment-card leave-assignment-action-card">
        <h2>Виконати дію</h2>
        <p>Керуйте політиками відсутностей для вибраних співробітників</p>
        <div className="leave-assignment-actions">
          <button type="button" className={action === 'assign' ? 'active' : ''} onClick={() => setAction('assign')}>
            <Users size={18} />
            <span>
              <strong>Призначити політику відсутності</strong>
              <em>Налаштуйте політику відсутності для вибраних співробітників</em>
            </span>
          </button>
          <button type="button" className={action === 'recalculate' ? 'active' : ''} onClick={() => setAction('recalculate')}>
            <ClipboardList size={18} />
            <span>
              <strong>Перерахувати політику відсутності</strong>
              <em>Застосувати зміни заднім числом до наявних балансів</em>
            </span>
          </button>
          <button type="button" className={action === 'remove' ? 'active' : ''} onClick={() => setAction('remove')}>
            <Trash2 size={18} />
            <span>
              <strong>Прибрати політику відсутності</strong>
              <em>Архівувати активні призначення без очищення історії балансу</em>
            </span>
          </button>
        </div>
        <label className="leave-assignment-type-field">
          <span>Тип відсутності</span>
          <select value={leaveTypeId} onChange={(event) => setLeaveTypeId(event.target.value)}>
            <option value="" />
            {types.map((type) => (
              <option key={type.id} value={type.id}>
                {type.name}
              </option>
            ))}
          </select>
        </label>
        <label className="leave-assignment-type-field">
          <span>Політика відсутності</span>
          <select value={policyId} onChange={(event) => setPolicyId(event.target.value)} disabled={!typePolicies.length}>
            <option value="" />
            {typePolicies.map((policy) => (
              <option key={policy.id} value={policy.id}>
                {policy.name} · {policyTypeLabel(policy.policy_type)}
              </option>
            ))}
          </select>
        </label>
        <div className="leave-assignment-form-row">
          <label className="leave-assignment-type-field">
            <span>Діє з</span>
            <input value={effectiveOn} onChange={(event) => setEffectiveOn(event.target.value)} type="date" />
          </label>
          <label className="leave-assignment-type-field">
            <span>Початковий баланс</span>
            <input value={initialBalance} onChange={(event) => setInitialBalance(event.target.value)} />
          </label>
        </div>
        {error ? <p className="leave-assignment-error">{error}</p> : null}
      </section>
      <div className="leave-assignment-footer">
        <button
          type="button"
          className="primary-action"
          disabled={saving || !policyId || (action !== 'recalculate' && !selectedEmployees.length)}
          onClick={() => void submitAction()}
        >
          {saving ? 'Застосування…' : 'Далі'}
        </button>
      </div>
    </main>
  );
}

export function SettingsLeaveTypesView({ onBack }: { onBack: () => void }) {
  const [types, setTypes] = useState<LeaveTypeWithPolicies[]>([]);
  const [assignments, setAssignments] = useState<EmployeeLeavePolicyAssignment[]>([]);
  const [employees, setEmployees] = useState<EmployeeListItem[]>([]);
  const [state, setState] = useState<'loading' | 'ok' | 'error'>('loading');
  const [modal, setModal] = useState<ModalState>(null);
  const [menuFor, setMenuFor] = useState<number | null>(null);
  const [addPolicyMenuFor, setAddPolicyMenuFor] = useState<number | null>(null);
  const [policyMenuFor, setPolicyMenuFor] = useState<number | null>(null);
  const [peoplePanel, setPeoplePanel] = useState<PolicyPeoplePanelState>(null);
  const [assignmentsOpen, setAssignmentsOpen] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState<LeaveType | null>(null);
  const [dragId, setDragId] = useState<number | null>(null);
  const [expandedIds, setExpandedIds] = useState<Set<number>>(new Set());
  const [policyWizard, setPolicyWizard] = useState<PolicyWizardRequest | null>(null);
  const policiesByType = useMemo(() => buildPoliciesByType(types), [types]);
  const employeesById = useMemo(() => new Map(employees.map((employee) => [employee.id, employee])), [employees]);

  async function load() {
    setState('loading');
    try {
      const [res, assignmentsRes, employeesRes] = await Promise.all([
        api.leaveTypesWithPolicies(),
        api.leavePolicyAssignments({ is_active: true, page_size: 1000 }).catch(() => ({ items: [], total: 0, next: null, previous: null })),
        api.employees({ status: 'active', compact: true, page_size: 1000 }).catch(() => ({ items: [], total: 0, next: null, previous: null })),
      ]);
      setTypes(res);
      setAssignments(assignmentsRes.items);
      setEmployees(employeesRes.items);
      setExpandedIds((current) => {
        const validIds = new Set(res.map((type) => type.id));
        return new Set([...current].filter((id) => validIds.has(id)));
      });
      setState('ok');
    } catch {
      setState('error');
    }
  }
  useEffect(() => {
    void load();
  }, []);

  async function handleSave(payload: LeaveTypePayload) {
    if (modal?.mode === 'edit') {
      await api.updateLeaveType(modal.type.id, payload);
    } else {
      await api.createLeaveType(payload);
    }
    setModal(null);
    await load();
  }

  async function handleDelete(type: LeaveType) {
    await api.deleteLeaveType(type.id);
    setConfirmDelete(null);
    await load();
  }

  function handleDrop(targetId: number) {
    if (dragId == null || dragId === targetId) {
      setDragId(null);
      return;
    }
    const ids = types.map((t) => t.id);
    const from = ids.indexOf(dragId);
    const to = ids.indexOf(targetId);
    if (from < 0 || to < 0) {
      setDragId(null);
      return;
    }
    ids.splice(to, 0, ids.splice(from, 1)[0]);
    const reordered = ids.map((id) => types.find((t) => t.id === id)!).filter(Boolean);
    setTypes(reordered);
    setDragId(null);
    void api.reorderLeaveTypes(ids).catch(() => load());
  }

  function toggleExpanded(typeId: number) {
    setPolicyMenuFor(null);
    setExpandedIds((current) => {
      const next = new Set(current);
      if (next.has(typeId)) {
        next.delete(typeId);
      } else {
        next.add(typeId);
      }
      return next;
    });
  }

  function openPolicyWizard(type: LeaveType, policyType: string) {
    setAddPolicyMenuFor(null);
    setMenuFor(null);
    setPolicyMenuFor(null);
    setPolicyWizard({ leaveType: type, policyType });
  }

  function editPolicy(type: LeaveType, policy: LeavePolicy) {
    setPolicyMenuFor(null);
    setPolicyWizard({ leaveType: type, policy });
  }

  async function copyPolicy(policy: LeavePolicy) {
    const created = await api.copyLeavePolicy(policy.id);
    setExpandedIds((current) => new Set(current).add(created.leave_type));
    setPolicyMenuFor(null);
    await load();
  }

  async function deletePolicy(policy: LeavePolicy) {
    await api.deleteLeavePolicy(policy.id);
    setPolicyMenuFor(null);
    await load();
  }

  function openPeoplePanel(type: LeaveType, policy: LeavePolicy) {
    setMenuFor(null);
    setAddPolicyMenuFor(null);
    setPolicyMenuFor(null);
    setPeoplePanel({ type, policy });
  }

  if (assignmentsOpen) {
    return (
      <LeaveAssignmentsView
        employees={employees}
        types={types}
        policiesByType={policiesByType}
        onChanged={load}
        onBack={() => setAssignmentsOpen(false)}
      />
    );
  }

  if (policyWizard) {
    return (
      <LeavePolicyWizard
        initial={policyWizard}
        employees={employees}
        onBack={() => setPolicyWizard(null)}
        onFinish={async (payload) => {
          const saved = policyWizard.policy
            ? await api.updateLeavePolicy(policyWizard.policy.id, payload)
            : await api.createLeavePolicy(payload);
          setExpandedIds((current) => new Set(current).add(saved.leave_type));
          setPolicyWizard(null);
          await load();
        }}
      />
    );
  }

  return (
    <main className="settings-page leave-types-page">
      <button type="button" className="report-back" onClick={onBack}>
        <ChevronLeft size={16} />
        <span>Назад</span>
      </button>

      <header className="people-data-head">
        <div>
          <h1>Типи відсутностей</h1>
        </div>
        <div className="people-data-head-actions">
          <button type="button" className="secondary-action" onClick={() => setAssignmentsOpen(true)}>
            <ClipboardList size={15} />
            <span>Призначення</span>
          </button>
          <button type="button" className="primary-action" onClick={() => setModal({ mode: 'create' })}>
            <Plus size={15} />
            <span>Додати тип відсутності</span>
          </button>
        </div>
      </header>

      {state === 'loading' ? (
        <p className="people-data-empty">Завантаження…</p>
      ) : state === 'error' ? (
        <p className="people-data-empty">Не вдалося завантажити типи відсутностей.</p>
      ) : types.length === 0 ? (
        <p className="people-data-empty">Типів ще немає. Додайте перший.</p>
      ) : (
        <div className="leave-types-list">
          {types.map((type) => (
            <div
              key={type.id}
              className={`leave-type-card${dragId === type.id ? ' dragging' : ''}`}
              draggable
              onDragStart={() => setDragId(type.id)}
              onDragOver={(e) => e.preventDefault()}
              onDrop={() => handleDrop(type.id)}
            >
              <div className="leave-type-row leave-type-row-head">
                <span className="leave-type-grip">
                  <GripVertical size={16} />
                </span>
                <span className="leave-type-icon" style={type.color ? { color: type.color } : undefined}>
                  <LeaveTypeIcon iconKey={type.icon} size={18} />
                </span>
                <div className="leave-type-info">
                  <strong>{type.name}</strong>
                  <span>{unitSubtitle(type.unit)}</span>
                </div>
                <div className="leave-type-actions">
                  <button
                    type="button"
                    className={`leave-type-caret-action ${expandedIds.has(type.id) ? 'expanded' : ''}`}
                    aria-label={`${expandedIds.has(type.id) ? 'Згорнути' : 'Розгорнути'} ${type.name}`}
                    onClick={() => toggleExpanded(type.id)}
                  >
                    <ChevronDown size={19} />
                  </button>
                  <button
                    type="button"
                    className="icon-button leave-type-add-action"
                    aria-label={`Додати політику для ${type.name}`}
                    title="Додати"
                    onClick={() => {
                      setMenuFor(null);
                      setPolicyMenuFor(null);
                      setAddPolicyMenuFor(addPolicyMenuFor === type.id ? null : type.id);
                    }}
                  >
                    <Plus size={18} />
                  </button>
                  <button
                    type="button"
                    className="icon-button leave-type-more-action"
                    aria-label="Дії"
                    onClick={() => {
                      setAddPolicyMenuFor(null);
                      setPolicyMenuFor(null);
                      setMenuFor(menuFor === type.id ? null : type.id);
                    }}
                  >
                    <MoreHorizontal size={16} />
                  </button>
                  {addPolicyMenuFor === type.id ? (
                    <>
                      <button
                        type="button"
                        className="leave-menu-backdrop"
                        aria-hidden
                        tabIndex={-1}
                        onClick={() => setAddPolicyMenuFor(null)}
                      />
                      <div className="leave-policy-add-menu" role="menu">
                        {POLICY_TYPE_OPTIONS.map((option) => (
                          <button key={option.value} type="button" onClick={() => openPolicyWizard(type, option.value)}>
                            {option.label}
                          </button>
                        ))}
                      </div>
                    </>
                  ) : null}
                  {menuFor === type.id ? (
                    <>
                      <button
                        type="button"
                        className="leave-menu-backdrop"
                        aria-hidden
                        tabIndex={-1}
                        onClick={() => setMenuFor(null)}
                      />
                      <div className="leave-row-menu" role="menu">
                        <button
                          type="button"
                          onClick={() => {
                            setModal({ mode: 'edit', type });
                            setMenuFor(null);
                          }}
                        >
                          <Pencil size={14} />
                          Редагувати
                        </button>
                        <button
                          type="button"
                          className="danger"
                          onClick={() => {
                            setConfirmDelete(type);
                            setMenuFor(null);
                          }}
                        >
                          <Trash2 size={14} />
                          Видалити
                        </button>
                      </div>
                    </>
                  ) : null}
                </div>
              </div>
              {expandedIds.has(type.id) ? (
                <div className="leave-policy-list">
                  {(policiesByType.get(type.id) ?? []).map((policy) => (
                    <div className="leave-policy-row" key={policy.id}>
                      <div>
                        <strong>{policy.name}</strong>
                        <span>
                          {activityLabel(policy.activity_type)} · {policyTypeLabel(policy.policy_type)} · {countedAsLabel(policy.counted_as)} ·{' '}
                          {employeesCountLabel(policy.employee_count)}
                        </span>
                      </div>
                      <div className="leave-policy-row-actions">
                        <button
                          type="button"
                          className="leave-policy-more"
                          aria-label={`Дії політики ${policy.name}`}
                          onClick={() => {
                            setMenuFor(null);
                            setAddPolicyMenuFor(null);
                            setPolicyMenuFor(policyMenuFor === policy.id ? null : policy.id);
                          }}
                        >
                          <MoreHorizontal size={16} />
                        </button>
                        {policyMenuFor === policy.id ? (
                          <>
                            <button
                              type="button"
                              className="leave-menu-backdrop"
                              aria-hidden
                              tabIndex={-1}
                              onClick={() => setPolicyMenuFor(null)}
                            />
                            <div className="leave-policy-row-menu" role="menu">
                              <button type="button" onClick={() => editPolicy(type, policy)}>
                                <Pencil size={14} />
                                Редагувати
                              </button>
                              <button type="button" onClick={() => void copyPolicy(policy)}>
                                <Copy size={14} />
                                Зробити копію
                              </button>
                              <button type="button" onClick={() => openPeoplePanel(type, policy)}>
                                <Users size={14} />
                                Переглянути людей
                              </button>
                              <button type="button" className="danger" onClick={() => void deletePolicy(policy)}>
                                <Trash2 size={14} />
                                Видалити
                              </button>
                            </div>
                          </>
                        ) : null}
                      </div>
                    </div>
                  ))}
                </div>
              ) : null}
            </div>
          ))}
        </div>
      )}

      {modal ? (
        <LeaveTypeModal initial={modal.mode === 'edit' ? modal.type : null} onClose={() => setModal(null)} onSave={handleSave} />
      ) : null}

      {peoplePanel ? (
        <LeavePolicyPeopleDrawer
          type={peoplePanel.type}
          policy={peoplePanel.policy}
          rows={peopleForPolicy(peoplePanel.policy, assignments, employeesById)}
          onClose={() => setPeoplePanel(null)}
        />
      ) : null}

      {confirmDelete ? (
        <div className="people-data-modal-layer leave-type-modal-layer" role="dialog" aria-modal="true" aria-label="Видалити тип відсутності">
          <button type="button" className="people-data-modal-backdrop" aria-label="Скасувати" onClick={() => setConfirmDelete(null)} />
          <div className="people-data-modal people-data-modal-sm leave-type-confirm-modal">
            <div className="people-data-modal-head">
              <h2>Видалити тип?</h2>
              <button type="button" className="icon-button" onClick={() => setConfirmDelete(null)} aria-label="Закрити">
                <X size={18} />
              </button>
            </div>
            <div className="people-data-modal-body">
              <p>
                Видалити «{confirmDelete.name}»? Якщо є пов’язані запити/баланси, тип буде архівовано разом з активними
                політиками й призначеннями.
              </p>
            </div>
            <div className="people-data-modal-foot">
              <button type="button" className="secondary-action" onClick={() => setConfirmDelete(null)}>
                Скасувати
              </button>
              <button type="button" className="primary-action danger" onClick={() => void handleDelete(confirmDelete)}>
                <Trash2 size={15} />
                Видалити
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </main>
  );
}
