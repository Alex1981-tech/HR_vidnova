import type {
  Announcement,
  AnnouncementAudiencePreview,
  AnnouncementComment,
  AnnouncementCondition,
  AnnouncementMediaUpload,
  AnnouncementPayload,
  AnnouncementPollResult,
  AnnouncementReactionSummary,
  ApiList,
  AuthCodeResponse,
  AuthLoginResponse,
  AuthStatus,
  CompanyLink,
  CompanyAttendanceSummary,
  DashboardOverview,
  DepartmentLevelOption,
  DepartmentOption,
  DivisionOption,
  EmployeeAttendanceDetail,
  EmployeeAttendancePeriod,
  EmployeeDocument,
  EmployeeDocumentFolder,
  EmployeeDocumentFolderPayload,
  EmergencyContact,
  Dependent,
  EmployeeEducation,
  EmployeeCertificate,
  SkillCategory,
  SkillCatalogItem,
  EmployeeSkill,
  EmployeeNote,
  EmployeeFormTemplate,
  EmployeeFormTemplateSummary,
  EmployeeFormType,
  EmployeeListItem,
  EmployeeProfile,
  GenderOption,
  HolidayOption,
  HolidayPolicyOption,
  JobLevel,
  ClinicLocation,
  KnowledgeCategory,
  KnowledgeDocument,
  LeaveBalance,
  LeaveRequest,
  LeaveType,
  LeaveTypePayload,
  PositionOption,
  ProbationPolicyOption,
  Project,
  ProjectPayload,
  TimeEntry,
  SelfAttendance,
  SelfKnowledge,
  SelfLeave,
  TeamOption,
  TerminationReasonOption,
  TerminationTypeOption,
  TimeCorrectionRequest,
  UserPreferences,
  SkillOption,
  WorkType,
  WorkingPatternOption,
  WorkDaySummary,
  CmmsAsset,
  CmmsAssetOptions,
} from '../types/api';

const API_BASE = import.meta.env.VITE_API_BASE ?? '';
const CSRF_COOKIE_NAMES = [import.meta.env.VITE_CSRF_COOKIE_NAME ?? 'hr_csrftoken', 'csrftoken'];
let csrfPrimePromise: Promise<void> | null = null;

type QueryValue = string | number | boolean | null | undefined;

export class ApiError extends Error {
  status: number;
  data: unknown;

  constructor(status: number, message: string, data: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

export type ListResult<T> = {
  items: T[];
  total: number;
  next: string | number | null;
  previous: string | number | null;
};

export type KnowledgeCategoryPayload = {
  name: string;
  description?: string;
  icon_emoji?: string;
  visibility_mode?: string;
  audience_employee_ids?: number[];
  audience_filters?: Record<string, unknown>;
  conditions?: AnnouncementCondition[];
  parent?: number | null;
  position?: number;
  is_active?: boolean;
};

export type KnowledgeDocumentPayload = {
  category: number;
  title: string;
  summary?: string;
  cover_url?: string;
  body?: string;
  body_html?: string;
  status?: string;
  tags?: string[];
};

export type JobLevelPayload = {
  name: string;
  external_peopleforce_id?: string;
  sort_order?: number;
  is_active?: boolean;
};

export type GenderPayload = {
  name: string;
  code?: string;
  external_peopleforce_id?: string;
  is_active?: boolean;
};

export type TerminationReasonPayload = {
  name: string;
  external_peopleforce_id?: string;
  is_active?: boolean;
};

export type TerminationTypePayload = {
  name: string;
  external_peopleforce_id?: string;
  is_active?: boolean;
};

export type WorkTypePayload = {
  name: string;
  external_peopleforce_id?: string;
  is_active?: boolean;
};

export type EmployeeFormTemplatePayload = {
  form_type: EmployeeFormType;
  name: string;
  description?: string;
  allow_employee_access?: boolean;
  workflow_name?: string;
  allow_requester_disable_workflow?: boolean;
  preboarding_form?: number | null;
  absence_policy_names?: string[];
  sections?: unknown[];
  is_active?: boolean;
};

export type ProbationPolicyPayload = {
  name: string;
  external_peopleforce_id?: string;
  duration_months?: number;
  is_active?: boolean;
};

export type HolidayPolicyPayload = {
  name: string;
  external_peopleforce_id?: string;
  country_code?: string;
  is_active?: boolean;
};

export type HolidayPayload = {
  policy: number;
  name: string;
  legacy_peopleforce_id?: string;
  occurs_on: string;
  starts_on?: string | null;
  ends_on?: string | null;
  working?: boolean;
  compensated_on?: string | null;
  observed_on?: string | null;
  recurrence?: string;
  is_active?: boolean;
};

export type CompanyLinkPayload = {
  title: string;
  url: string;
  icon_url?: string;
  order?: number;
  is_active?: boolean;
  audience_type?: 'all' | 'conditions';
  conditions?: AnnouncementCondition[];
};

export type WorkingPatternPayload = {
  name: string;
  external_peopleforce_id?: string;
  monday_hours?: number;
  tuesday_hours?: number;
  wednesday_hours?: number;
  thursday_hours?: number;
  friday_hours?: number;
  saturday_hours?: number;
  sunday_hours?: number;
  uses_time_range?: boolean;
  is_default?: boolean;
  schedule?: Record<string, unknown>;
  is_active?: boolean;
};

export type AttendancePeriodPayload = {
  date: string;
  start_time: string;
  end_time: string;
  comment?: string;
};

export type PositionPayload = {
  name: string;
  external_peopleforce_id?: string;
  is_active?: boolean;
};

export type DivisionPayload = {
  name: string;
  external_peopleforce_id?: string;
  is_active?: boolean;
};

export type SkillPayload = {
  name: string;
  external_fotopacients_id?: string;
  external_peopleforce_id?: string;
  is_active?: boolean;
};

export type ClinicLocationPayload = {
  name: string;
  code?: string;
  external_peopleforce_id?: string;
  country_code?: string;
  address?: string;
  holiday_policy_id?: string;
  holiday_policy_name?: string;
  time_zone?: string;
  is_active?: boolean;
};

export type DepartmentPayload = {
  name: string;
  clinic?: number | null;
  parent?: number | null;
  manager?: number | null;
  level?: number | null;
  code?: string;
  external_peopleforce_id?: string;
  is_active?: boolean;
};

export type DepartmentLevelPayload = {
  name: string;
  color?: string;
  external_peopleforce_id?: string;
  is_active?: boolean;
};

export type TeamPayload = {
  name: string;
  external_peopleforce_id?: string;
  description?: string;
  lead?: number | null;
  member_ids?: number[];
  is_active?: boolean;
};

export type TableRow = {
  row_id: string;
  created_at?: string;
  updated_at?: string;
  [key: string]: unknown;
};

export type EmployeeHirePayload = {
  first_name: string;
  last_name: string;
  middle_name?: string;
  email?: string;
  personal_email?: string;
  phone?: string;
  phone2?: string;
  birth_date?: string | null;
  gender?: string;
  status?: string;
  hired_on?: string | null;
  notes?: string;
  clinic?: number | null;
  department?: number | null;
  position?: number | null;
  division?: number | null;
  employment_type?: number | null;
  job_level?: number | null;
  medical_specialties?: number[];
  manager?: number | null;
  working_pattern?: number | null;
  probation_policy?: number | null;
};

function buildQuery(params: Record<string, QueryValue>): string {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') return;
    search.set(key, String(value));
  });
  const query = search.toString();
  return query ? `?${query}` : '';
}

function normalizeList<T>(response: ApiList<T> | T[]): ListResult<T> {
  if (Array.isArray(response)) {
    return {
      items: response,
      total: response.length,
      next: null,
      previous: null,
    };
  }
  return {
    items: response.results,
    total: response.count,
    next: response.next,
    previous: response.previous,
  };
}

function getCookie(name: string): string {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length !== 2) return '';
  return parts.pop()?.split(';').shift() ?? '';
}

async function ensureCsrfCookie(path: string): Promise<string> {
  const existingToken = CSRF_COOKIE_NAMES.map(getCookie).find(Boolean) ?? '';
  if (existingToken || path === '/api/auth/status/') {
    return existingToken;
  }
  csrfPrimePromise ??= fetch(`${API_BASE}/api/auth/status/`, {
    credentials: 'include',
    headers: { Accept: 'application/json' },
  })
    .then(() => undefined)
    .finally(() => {
      csrfPrimePromise = null;
    });
  await csrfPrimePromise;
  return CSRF_COOKIE_NAMES.map(getCookie).find(Boolean) ?? '';
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const bodyIsFormData = typeof FormData !== 'undefined' && init.body instanceof FormData;
  const method = (init.method || 'GET').toUpperCase();
  const needsCsrf = !['GET', 'HEAD', 'OPTIONS', 'TRACE'].includes(method);
  const csrfToken = needsCsrf ? await ensureCsrfCookie(path) : '';
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    credentials: 'include',
    headers: {
      Accept: 'application/json',
      ...(init.body && !bodyIsFormData ? { 'Content-Type': 'application/json' } : {}),
      ...(needsCsrf && csrfToken ? { 'X-CSRFToken': csrfToken } : {}),
      ...(init.headers ?? {}),
    },
  });

  if (!response.ok) {
    let payload: unknown = null;
    try {
      payload = await response.json();
    } catch {
      payload = await response.text().catch(() => '');
    }
    const detail =
      payload && typeof payload === 'object' && 'detail' in payload
        ? String((payload as { detail?: unknown }).detail)
        : `HTTP ${response.status}`;
    throw new ApiError(response.status, detail, payload);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const text = await response.text();
  if (!text) {
    return undefined as T;
  }
  return JSON.parse(text) as T;
}

export const api = {
  authStatus: () => request<AuthStatus>('/api/auth/status/'),
  assets: (
    params: {
      page?: number;
      page_size?: number;
      search?: string;
      status?: string;
      location_ids?: number[];
      department_ids?: number[];
      responsible_ids?: number[];
      hr_employee_id?: number;
    } = {},
  ) => {
    const sp = new URLSearchParams();
    if (params.page) sp.set('page', String(params.page));
    if (params.page_size) sp.set('page_size', String(params.page_size));
    if (params.search) sp.set('search', params.search);
    if (params.status && params.status !== 'all') sp.set('status', params.status);
    if (params.hr_employee_id) sp.set('hr_employee_id', String(params.hr_employee_id));
    for (const id of params.location_ids ?? []) sp.append('location_ids', String(id));
    for (const id of params.department_ids ?? []) sp.append('department_ids', String(id));
    for (const id of params.responsible_ids ?? []) sp.append('responsible_ids', String(id));
    const query = sp.toString();
    return request<{ total: number; items: CmmsAsset[] }>(`/api/assets/${query ? `?${query}` : ''}`);
  },
  assetOptions: () => request<CmmsAssetOptions>('/api/assets/options/'),
  assignAssetResponsible: (assetId: number, employeeId: number | null) =>
    request<{ asset_id: number; responsible_person_id: number | null; responsible_person_name: string | null }>(
      `/api/assets/${assetId}/responsible/`,
      { method: 'POST', body: JSON.stringify({ employee_id: employeeId }) },
    ),
  requestLoginCode: (phone: string) =>
    request<AuthCodeResponse>('/api/auth/request-code/', {
      method: 'POST',
      body: JSON.stringify({ phone }),
    }),
  verifyLoginCode: (phone: string, code: string) =>
    request<AuthLoginResponse>('/api/auth/verify-code/', {
      method: 'POST',
      body: JSON.stringify({ phone, code }),
    }),
  logout: () =>
    request<{ status: string }>('/api/auth/logout/', {
      method: 'POST',
      body: JSON.stringify({}),
    }),
  overview: () => request<DashboardOverview>('/api/dashboard/overview/'),
  employees: (
    params: {
      q?: string;
      status?: string;
      clinic?: number | string;
      department?: number | string;
      department_level?: number | string;
      division?: number | string;
      team?: number | string;
      medical_specialty?: number | string;
      gender?: string;
      job_level?: number | string;
      employment_type?: number | string;
      probation_policy?: number | string;
      position?: number | string;
      compact?: boolean;
      page?: number;
      page_size?: number;
    } = {},
  ) =>
    request<ApiList<EmployeeListItem> | EmployeeListItem[]>(`/api/employees/employees/${buildQuery(params)}`).then(
      normalizeList,
    ),
  employee: (id: number) => request<EmployeeListItem>(`/api/employees/employees/${id}/`),
  updateEmployee: (id: number, payload: Partial<EmployeeListItem>) =>
    request<EmployeeListItem>(`/api/employees/employees/${id}/`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),
  updateEmployeeProfileBlock: (
    id: number,
    payload: Partial<EmployeeListItem> & { custom_fields_delta?: Record<string, unknown> },
  ) =>
    request<EmployeeListItem>(`/api/employees/employees/${id}/profile-block/`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),
  hireEmployee: (payload: EmployeeHirePayload) =>
    request<EmployeeListItem>('/api/employees/employees/hire/', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  // Atomic row-level API для повторюваних таблиць профілю
  tableRows: (employeeId: number, tableId: number) =>
    request<TableRow[]>(`/api/employees/employees/${employeeId}/table-rows/?table=${tableId}`),
  createTableRow: (employeeId: number, tableId: number, values: Record<string, unknown>) =>
    request<TableRow>(`/api/employees/employees/${employeeId}/table-rows/?table=${tableId}`, {
      method: 'POST',
      body: JSON.stringify({ values }),
    }),
  updateTableRow: (employeeId: number, tableId: number, rowId: string, values: Record<string, unknown>) =>
    request<TableRow>(`/api/employees/employees/${employeeId}/table-rows/${rowId}/?table=${tableId}`, {
      method: 'PATCH',
      body: JSON.stringify({ values }),
    }),
  deleteTableRow: (employeeId: number, tableId: number, rowId: string) =>
    request<void>(`/api/employees/employees/${employeeId}/table-rows/${rowId}/?table=${tableId}`, {
      method: 'DELETE',
    }),
  jobLevels: (params: { q?: string; is_active?: boolean; page?: number; page_size?: number } = {}) =>
    request<ApiList<JobLevel> | JobLevel[]>(`/api/employees/job-levels/${buildQuery(params)}`).then(normalizeList),
  createJobLevel: (payload: JobLevelPayload) =>
    request<JobLevel>('/api/employees/job-levels/', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  updateJobLevel: (id: number, payload: Partial<JobLevelPayload>) =>
    request<JobLevel>(`/api/employees/job-levels/${id}/`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),
  deleteJobLevel: (id: number) =>
    request<void>(`/api/employees/job-levels/${id}/`, {
      method: 'DELETE',
    }),
  reorderJobLevels: (ids: number[]) =>
    request<JobLevel[]>('/api/employees/job-levels/reorder/', {
      method: 'POST',
      body: JSON.stringify({ ids }),
    }),
  genders: (params: { q?: string; is_active?: boolean; page?: number; page_size?: number } = {}) =>
    request<ApiList<GenderOption> | GenderOption[]>(`/api/employees/genders/${buildQuery(params)}`).then(normalizeList),
  createGender: (payload: GenderPayload) =>
    request<GenderOption>('/api/employees/genders/', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  updateGender: (id: number, payload: Partial<GenderPayload>) =>
    request<GenderOption>(`/api/employees/genders/${id}/`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),
  deleteGender: (id: number) =>
    request<void>(`/api/employees/genders/${id}/`, {
      method: 'DELETE',
    }),
  terminationReasons: (params: { q?: string; is_active?: boolean; page?: number; page_size?: number } = {}) =>
    request<ApiList<TerminationReasonOption> | TerminationReasonOption[]>(
      `/api/employees/termination-reasons/${buildQuery(params)}`,
    ).then(normalizeList),
  createTerminationReason: (payload: TerminationReasonPayload) =>
    request<TerminationReasonOption>('/api/employees/termination-reasons/', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  updateTerminationReason: (id: number, payload: Partial<TerminationReasonPayload>) =>
    request<TerminationReasonOption>(`/api/employees/termination-reasons/${id}/`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),
  deleteTerminationReason: (id: number) =>
    request<void>(`/api/employees/termination-reasons/${id}/`, {
      method: 'DELETE',
    }),
  terminationTypes: (params: { q?: string; is_active?: boolean; page?: number; page_size?: number } = {}) =>
    request<ApiList<TerminationTypeOption> | TerminationTypeOption[]>(
      `/api/employees/termination-types/${buildQuery(params)}`,
    ).then(normalizeList),
  createTerminationType: (payload: TerminationTypePayload) =>
    request<TerminationTypeOption>('/api/employees/termination-types/', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  updateTerminationType: (id: number, payload: Partial<TerminationTypePayload>) =>
    request<TerminationTypeOption>(`/api/employees/termination-types/${id}/`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),
  deleteTerminationType: (id: number) =>
    request<void>(`/api/employees/termination-types/${id}/`, {
      method: 'DELETE',
    }),
  workTypes: (params: { q?: string; is_active?: boolean; page?: number; page_size?: number } = {}) =>
    request<ApiList<WorkType> | WorkType[]>(`/api/employees/employment-types/${buildQuery(params)}`).then(normalizeList),
  createWorkType: (payload: WorkTypePayload) =>
    request<WorkType>('/api/employees/employment-types/', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  updateWorkType: (id: number, payload: Partial<WorkTypePayload>) =>
    request<WorkType>(`/api/employees/employment-types/${id}/`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),
  deleteWorkType: (id: number) =>
    request<void>(`/api/employees/employment-types/${id}/`, {
      method: 'DELETE',
    }),
  formTemplates: (
    params: { q?: string; form_type?: EmployeeFormType; is_active?: boolean; page?: number; page_size?: number } = {},
  ) => request<ApiList<EmployeeFormTemplate> | EmployeeFormTemplate[]>(`/api/employees/form-templates/${buildQuery(params)}`).then(normalizeList),
  formTemplateSummary: (params: { is_active?: boolean } = {}) =>
    request<EmployeeFormTemplateSummary[]>(`/api/employees/form-templates/summary/${buildQuery(params)}`),
  createFormTemplate: (payload: EmployeeFormTemplatePayload) =>
    request<EmployeeFormTemplate>('/api/employees/form-templates/', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  probationPolicies: (params: { q?: string; is_active?: boolean; page?: number; page_size?: number } = {}) =>
    request<ApiList<ProbationPolicyOption> | ProbationPolicyOption[]>(
      `/api/employees/probation-policies/${buildQuery(params)}`,
    ).then(normalizeList),
  createProbationPolicy: (payload: ProbationPolicyPayload) =>
    request<ProbationPolicyOption>('/api/employees/probation-policies/', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  updateProbationPolicy: (id: number, payload: Partial<ProbationPolicyPayload>) =>
    request<ProbationPolicyOption>(`/api/employees/probation-policies/${id}/`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),
  deleteProbationPolicy: (id: number) =>
    request<void>(`/api/employees/probation-policies/${id}/`, {
      method: 'DELETE',
    }),
  holidayPolicies: (params: { q?: string; is_active?: boolean; page?: number; page_size?: number } = {}) =>
    request<ApiList<HolidayPolicyOption> | HolidayPolicyOption[]>(
      `/api/employees/holiday-policies/${buildQuery(params)}`,
    ).then(normalizeList),
  createHolidayPolicy: (payload: HolidayPolicyPayload) =>
    request<HolidayPolicyOption>('/api/employees/holiday-policies/', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  updateHolidayPolicy: (id: number, payload: Partial<HolidayPolicyPayload>) =>
    request<HolidayPolicyOption>(`/api/employees/holiday-policies/${id}/`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),
  deleteHolidayPolicy: (id: number) =>
    request<void>(`/api/employees/holiday-policies/${id}/`, {
      method: 'DELETE',
    }),
  holidays: (
    params: {
      policy?: number;
      year?: number;
      starts_on?: string;
      ends_on?: string;
      q?: string;
      is_active?: boolean;
      page?: number;
      page_size?: number;
    } = {},
  ) => request<ApiList<HolidayOption> | HolidayOption[]>(`/api/employees/holidays/${buildQuery(params)}`).then(normalizeList),
  companyLinks: (params: { q?: string; is_active?: boolean; for_me?: boolean; page?: number; page_size?: number } = {}) =>
    request<ApiList<CompanyLink> | CompanyLink[]>(`/api/employees/company-links/${buildQuery(params)}`).then(normalizeList),
  companyLinkAudiencePreview: (payload: { audience_type: 'all' | 'conditions'; conditions: AnnouncementCondition[] }) =>
    request<AnnouncementAudiencePreview>('/api/employees/company-links/audience-preview/', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  createCompanyLink: (payload: CompanyLinkPayload) =>
    request<CompanyLink>('/api/employees/company-links/', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  updateCompanyLink: (id: number, payload: Partial<CompanyLinkPayload>) =>
    request<CompanyLink>(`/api/employees/company-links/${id}/`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),
  deleteCompanyLink: (id: number) =>
    request<void>(`/api/employees/company-links/${id}/`, {
      method: 'DELETE',
    }),
  reorderCompanyLinks: (ids: number[]) =>
    request<CompanyLink[]>('/api/employees/company-links/reorder/', {
      method: 'POST',
      body: JSON.stringify({ ids }),
    }),
  createHoliday: (payload: HolidayPayload) =>
    request<HolidayOption>('/api/employees/holidays/', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  updateHoliday: (id: number, payload: Partial<HolidayPayload>) =>
    request<HolidayOption>(`/api/employees/holidays/${id}/`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),
  deleteHoliday: (id: number) =>
    request<void>(`/api/employees/holidays/${id}/`, {
      method: 'DELETE',
    }),
  workingPatterns: (params: { q?: string; is_active?: boolean; page?: number; page_size?: number } = {}) =>
    request<ApiList<WorkingPatternOption> | WorkingPatternOption[]>(
      `/api/employees/working-patterns/${buildQuery(params)}`,
    ).then(normalizeList),
  createWorkingPattern: (payload: WorkingPatternPayload) =>
    request<WorkingPatternOption>('/api/employees/working-patterns/', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  updateWorkingPattern: (id: number, payload: Partial<WorkingPatternPayload>) =>
    request<WorkingPatternOption>(`/api/employees/working-patterns/${id}/`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),
  deleteWorkingPattern: (id: number) =>
    request<void>(`/api/employees/working-patterns/${id}/`, {
      method: 'DELETE',
    }),
  positions: (params: { q?: string; is_active?: boolean; page?: number; page_size?: number } = {}) =>
    request<ApiList<PositionOption> | PositionOption[]>(`/api/employees/positions/${buildQuery(params)}`).then(normalizeList),
  createPosition: (payload: PositionPayload) =>
    request<PositionOption>('/api/employees/positions/', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  updatePosition: (id: number, payload: Partial<PositionPayload>) =>
    request<PositionOption>(`/api/employees/positions/${id}/`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),
  deletePosition: (id: number) =>
    request<void>(`/api/employees/positions/${id}/`, {
      method: 'DELETE',
    }),
  divisions: (params: { q?: string; is_active?: boolean; page?: number; page_size?: number } = {}) =>
    request<ApiList<DivisionOption> | DivisionOption[]>(`/api/employees/divisions/${buildQuery(params)}`).then(normalizeList),
  createDivision: (payload: DivisionPayload) =>
    request<DivisionOption>('/api/employees/divisions/', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  updateDivision: (id: number, payload: Partial<DivisionPayload>) =>
    request<DivisionOption>(`/api/employees/divisions/${id}/`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),
  deleteDivision: (id: number) =>
    request<void>(`/api/employees/divisions/${id}/`, {
      method: 'DELETE',
    }),
  skills: (params: { q?: string; is_active?: boolean; page?: number; page_size?: number } = {}) =>
    request<ApiList<SkillOption> | SkillOption[]>(`/api/employees/medical-specialties/${buildQuery(params)}`).then(normalizeList),
  createSkill: (payload: SkillPayload) =>
    request<SkillOption>('/api/employees/medical-specialties/', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  updateSkill: (id: number, payload: Partial<SkillPayload>) =>
    request<SkillOption>(`/api/employees/medical-specialties/${id}/`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),
  deleteSkill: (id: number) =>
    request<void>(`/api/employees/medical-specialties/${id}/`, {
      method: 'DELETE',
    }),
  locations: (params: { q?: string; is_active?: boolean; page?: number; page_size?: number } = {}) =>
    request<ApiList<ClinicLocation> | ClinicLocation[]>(`/api/employees/clinics/${buildQuery(params)}`).then(normalizeList),
  createLocation: (payload: ClinicLocationPayload) =>
    request<ClinicLocation>('/api/employees/clinics/', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  updateLocation: (id: number, payload: Partial<ClinicLocationPayload>) =>
    request<ClinicLocation>(`/api/employees/clinics/${id}/`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),
  deleteLocation: (id: number) =>
    request<void>(`/api/employees/clinics/${id}/`, {
      method: 'DELETE',
    }),
  departments: (params: { q?: string; is_active?: boolean; page?: number; page_size?: number } = {}) =>
    request<ApiList<DepartmentOption> | DepartmentOption[]>(`/api/employees/departments/${buildQuery(params)}`).then(normalizeList),
  createDepartment: (payload: DepartmentPayload) =>
    request<DepartmentOption>('/api/employees/departments/', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  updateDepartment: (id: number, payload: Partial<DepartmentPayload>) =>
    request<DepartmentOption>(`/api/employees/departments/${id}/`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),
  deleteDepartment: (id: number) =>
    request<void>(`/api/employees/departments/${id}/`, {
      method: 'DELETE',
    }),
  departmentLevels: (params: { q?: string; is_active?: boolean; page?: number; page_size?: number } = {}) =>
    request<ApiList<DepartmentLevelOption> | DepartmentLevelOption[]>(
      `/api/employees/department-levels/${buildQuery(params)}`,
    ).then(normalizeList),
  createDepartmentLevel: (payload: DepartmentLevelPayload) =>
    request<DepartmentLevelOption>('/api/employees/department-levels/', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  updateDepartmentLevel: (id: number, payload: Partial<DepartmentLevelPayload>) =>
    request<DepartmentLevelOption>(`/api/employees/department-levels/${id}/`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),
  deleteDepartmentLevel: (id: number) =>
    request<void>(`/api/employees/department-levels/${id}/`, {
      method: 'DELETE',
    }),
  teams: (params: { q?: string; is_active?: boolean; page?: number; page_size?: number } = {}) =>
    request<ApiList<TeamOption> | TeamOption[]>(`/api/employees/teams/${buildQuery(params)}`).then(normalizeList),
  createTeam: (payload: TeamPayload) =>
    request<TeamOption>('/api/employees/teams/', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  updateTeam: (id: number, payload: Partial<TeamPayload>) =>
    request<TeamOption>(`/api/employees/teams/${id}/`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),
  deleteTeam: (id: number) =>
    request<void>(`/api/employees/teams/${id}/`, {
      method: 'DELETE',
    }),
  companyAttendance: (
    params: { from?: string; to?: string; q?: string; employee_status?: string; page?: number; page_size?: number } = {},
  ) =>
    request<ApiList<CompanyAttendanceSummary> | CompanyAttendanceSummary[]>(
      `/api/skud/company-attendance/${buildQuery(params)}`,
    ).then(normalizeList),
  employeeAttendance: (employeeId: number, params: { from?: string; to?: string } = {}) =>
    request<EmployeeAttendanceDetail>(`/api/skud/employee-attendance/${employeeId}/${buildQuery(params)}`),
  createEmployeeAttendancePeriod: (employeeId: number, payload: AttendancePeriodPayload) =>
    request<EmployeeAttendancePeriod>(`/api/skud/employee-attendance/${employeeId}/periods/`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  updateEmployeeAttendancePeriod: (employeeId: number, periodId: number, payload: AttendancePeriodPayload) =>
    request<EmployeeAttendancePeriod>(`/api/skud/employee-attendance/${employeeId}/periods/${periodId}/`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),
  deleteEmployeeAttendancePeriod: (employeeId: number, periodId: number) =>
    request<void>(`/api/skud/employee-attendance/${employeeId}/periods/${periodId}/`, {
      method: 'DELETE',
    }),
  workdays: (params: { from?: string; to?: string; employee?: number; status?: string; page?: number } = {}) =>
    request<ApiList<WorkDaySummary> | WorkDaySummary[]>(`/api/skud/workdays/${buildQuery(params)}`).then(normalizeList),
  leaveTypes: (params: { page?: number; page_size?: number } = {}) =>
    request<ApiList<LeaveType> | LeaveType[]>(`/api/leave/types/${buildQuery(params)}`).then(normalizeList),
  createLeaveType: (payload: LeaveTypePayload) =>
    request<LeaveType>('/api/leave/types/', { method: 'POST', body: JSON.stringify(payload) }),
  updateLeaveType: (id: number, payload: Partial<LeaveTypePayload>) =>
    request<LeaveType>(`/api/leave/types/${id}/`, { method: 'PATCH', body: JSON.stringify(payload) }),
  deleteLeaveType: (id: number) => request<void>(`/api/leave/types/${id}/`, { method: 'DELETE' }),
  reorderLeaveTypes: (ids: number[]) =>
    request<LeaveType[]>('/api/leave/types/reorder/', { method: 'POST', body: JSON.stringify({ ids }) }),
  projects: (params: { archived?: boolean; q?: string; page?: number; page_size?: number } = {}) =>
    request<ApiList<Project> | Project[]>(`/api/projects/${buildQuery(params)}`).then(normalizeList),
  project: (id: number) => request<Project>(`/api/projects/${id}/`),
  createProject: (payload: ProjectPayload) =>
    request<Project>('/api/projects/', { method: 'POST', body: JSON.stringify(payload) }),
  updateProject: (id: number, payload: Partial<ProjectPayload>) =>
    request<Project>(`/api/projects/${id}/`, { method: 'PATCH', body: JSON.stringify(payload) }),
  deleteProject: (id: number) => request<void>(`/api/projects/${id}/`, { method: 'DELETE' }),
  archiveProject: (id: number) => request<Project>(`/api/projects/${id}/archive/`, { method: 'POST' }),
  unarchiveProject: (id: number) => request<Project>(`/api/projects/${id}/unarchive/`, { method: 'POST' }),
  addProjectMembers: (id: number, employee_ids: number[]) =>
    request<Project>(`/api/projects/${id}/add-members/`, { method: 'POST', body: JSON.stringify({ employee_ids }) }),
  removeProjectMembers: (id: number, employee_ids: number[]) =>
    request<Project>(`/api/projects/${id}/remove-members/`, { method: 'POST', body: JSON.stringify({ employee_ids }) }),
  timeEntries: (params: { date?: string; page_size?: number } = {}) =>
    request<ApiList<TimeEntry> | TimeEntry[]>(`/api/projects/time-entries/${buildQuery(params)}`).then(normalizeList),
  activeTimeEntry: () => request<TimeEntry | null>('/api/projects/time-entries/active/'),
  startTimeEntry: (payload: { project?: number | null; comment?: string }) =>
    request<TimeEntry>('/api/projects/time-entries/start/', { method: 'POST', body: JSON.stringify(payload) }),
  stopTimeEntry: (id: number) => request<TimeEntry>(`/api/projects/time-entries/${id}/stop/`, { method: 'POST' }),
  documentFolders: (params: { q?: string; page?: number; page_size?: number } = {}) =>
    request<ApiList<EmployeeDocumentFolder> | EmployeeDocumentFolder[]>(
      `/api/employees/document-folders/${buildQuery(params)}`,
    ).then(normalizeList),
  createDocumentFolder: (payload: EmployeeDocumentFolderPayload) =>
    request<EmployeeDocumentFolder>('/api/employees/document-folders/', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  updateDocumentFolder: (id: number, payload: Partial<EmployeeDocumentFolderPayload>) =>
    request<EmployeeDocumentFolder>(`/api/employees/document-folders/${id}/`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),
  deleteDocumentFolder: (id: number) =>
    request<void>(`/api/employees/document-folders/${id}/`, { method: 'DELETE' }),
  employeeDocuments: (params: { employee?: number; folder?: number; type?: string; page_size?: number } = {}) =>
    request<ApiList<EmployeeDocument> | EmployeeDocument[]>(`/api/employees/documents/${buildQuery(params)}`).then(
      normalizeList,
    ),
  uploadEmployeeDocuments: (employee: number, folder: number | null, files: File[]) => {
    const form = new FormData();
    form.append('employee', String(employee));
    if (folder != null) form.append('folder', String(folder));
    files.forEach((file) => form.append('files', file));
    return request<{ created: EmployeeDocument[]; errors: Array<{ name: string; error: string }> }>(
      '/api/employees/documents/upload/',
      { method: 'POST', body: form },
    );
  },
  deleteEmployeeDocument: (id: number) =>
    request<void>(`/api/employees/documents/${id}/`, { method: 'DELETE' }),
  employeeDocumentDownloadUrl: (id: number) => `/api/employees/documents/${id}/download/`,
  employeeDocumentPreviewUrl: (id: number) => `/api/employees/documents/${id}/preview/`,
  emergencyContacts: (employee: number) =>
    request<ApiList<EmergencyContact> | EmergencyContact[]>(
      `/api/employees/emergency-contacts/${buildQuery({ employee, page_size: 200 })}`,
    ).then(normalizeList),
  saveEmergencyContact: (payload: Partial<EmergencyContact> & { employee: number }) =>
    payload.id
      ? request<EmergencyContact>(`/api/employees/emergency-contacts/${payload.id}/`, {
          method: 'PATCH',
          body: JSON.stringify(payload),
        })
      : request<EmergencyContact>('/api/employees/emergency-contacts/', { method: 'POST', body: JSON.stringify(payload) }),
  deleteEmergencyContact: (id: number) =>
    request<void>(`/api/employees/emergency-contacts/${id}/`, { method: 'DELETE' }),
  dependents: (employee: number) =>
    request<ApiList<Dependent> | Dependent[]>(`/api/employees/dependents/${buildQuery({ employee, page_size: 200 })}`).then(
      normalizeList,
    ),
  saveDependent: (payload: Partial<Dependent> & { employee: number }) =>
    payload.id
      ? request<Dependent>(`/api/employees/dependents/${payload.id}/`, { method: 'PATCH', body: JSON.stringify(payload) })
      : request<Dependent>('/api/employees/dependents/', { method: 'POST', body: JSON.stringify(payload) }),
  deleteDependent: (id: number) => request<void>(`/api/employees/dependents/${id}/`, { method: 'DELETE' }),
  educations: (employee: number) =>
    request<ApiList<EmployeeEducation> | EmployeeEducation[]>(
      `/api/employees/educations/${buildQuery({ employee, page_size: 200 })}`,
    ).then(normalizeList),
  saveEducation: (payload: Partial<EmployeeEducation> & { employee: number }) =>
    payload.id
      ? request<EmployeeEducation>(`/api/employees/educations/${payload.id}/`, { method: 'PATCH', body: JSON.stringify(payload) })
      : request<EmployeeEducation>('/api/employees/educations/', { method: 'POST', body: JSON.stringify(payload) }),
  deleteEducation: (id: number) => request<void>(`/api/employees/educations/${id}/`, { method: 'DELETE' }),
  certificates: (employee: number) =>
    request<ApiList<EmployeeCertificate> | EmployeeCertificate[]>(
      `/api/employees/certificates/${buildQuery({ employee, page_size: 200 })}`,
    ).then(normalizeList),
  saveCertificate: (payload: Partial<EmployeeCertificate> & { employee: number }) =>
    payload.id
      ? request<EmployeeCertificate>(`/api/employees/certificates/${payload.id}/`, { method: 'PATCH', body: JSON.stringify(payload) })
      : request<EmployeeCertificate>('/api/employees/certificates/', { method: 'POST', body: JSON.stringify(payload) }),
  deleteCertificate: (id: number) => request<void>(`/api/employees/certificates/${id}/`, { method: 'DELETE' }),
  skillCategories: () =>
    request<ApiList<SkillCategory> | SkillCategory[]>(
      `/api/employees/skill-categories/${buildQuery({ is_active: true, page_size: 500 })}`,
    ).then(normalizeList),
  createSkillCategory: (name: string) =>
    request<SkillCategory>('/api/employees/skill-categories/', { method: 'POST', body: JSON.stringify({ name }) }),
  updateSkillCategory: (id: number, name: string) =>
    request<SkillCategory>(`/api/employees/skill-categories/${id}/`, { method: 'PATCH', body: JSON.stringify({ name }) }),
  deleteSkillCategory: (id: number) =>
    request<void>(`/api/employees/skill-categories/${id}/`, { method: 'DELETE' }),
  updateCatalogSkill: (id: number, name: string) =>
    request<SkillCatalogItem>(`/api/employees/skills-catalog/${id}/`, { method: 'PATCH', body: JSON.stringify({ name }) }),
  deleteCatalogSkill: (id: number) =>
    request<void>(`/api/employees/skills-catalog/${id}/`, { method: 'DELETE' }),
  skillsCatalog: (category: number) =>
    request<ApiList<SkillCatalogItem> | SkillCatalogItem[]>(
      `/api/employees/skills-catalog/${buildQuery({ category, is_active: true, page_size: 500 })}`,
    ).then(normalizeList),
  createCatalogSkill: (category: number, name: string) =>
    request<SkillCatalogItem>('/api/employees/skills-catalog/', { method: 'POST', body: JSON.stringify({ category, name }) }),
  employeeSkills: (employee: number) =>
    request<ApiList<EmployeeSkill> | EmployeeSkill[]>(
      `/api/employees/employee-skills/${buildQuery({ employee, page_size: 200 })}`,
    ).then(normalizeList),
  saveEmployeeSkill: (payload: { id?: number; employee: number; skill: number; level: string }) =>
    payload.id
      ? request<EmployeeSkill>(`/api/employees/employee-skills/${payload.id}/`, { method: 'PATCH', body: JSON.stringify(payload) })
      : request<EmployeeSkill>('/api/employees/employee-skills/', { method: 'POST', body: JSON.stringify(payload) }),
  deleteEmployeeSkill: (id: number) => request<void>(`/api/employees/employee-skills/${id}/`, { method: 'DELETE' }),
  employeeNotes: (employee: number) =>
    request<ApiList<EmployeeNote> | EmployeeNote[]>(
      `/api/employees/employee-notes/${buildQuery({ employee, page_size: 200 })}`,
    ).then(normalizeList),
  saveEmployeeNote: (payload: Partial<EmployeeNote> & { employee: number }) =>
    payload.id
      ? request<EmployeeNote>(`/api/employees/employee-notes/${payload.id}/`, {
          method: 'PATCH',
          body: JSON.stringify(payload),
        })
      : request<EmployeeNote>('/api/employees/employee-notes/', { method: 'POST', body: JSON.stringify(payload) }),
  deleteEmployeeNote: (id: number) => request<void>(`/api/employees/employee-notes/${id}/`, { method: 'DELETE' }),
  leaveRequests: (params: { status?: string; employee?: number; date_from?: string; date_to?: string; page?: number; page_size?: number } = {}) =>
    request<ApiList<LeaveRequest> | LeaveRequest[]>(`/api/leave/requests/${buildQuery(params)}`).then(normalizeList),
  leaveBalances: (params: { employee?: number; leave_type?: number; page?: number; page_size?: number } = {}) =>
    request<ApiList<LeaveBalance> | LeaveBalance[]>(`/api/leave/balances/${buildQuery(params)}`).then(normalizeList),
  knowledgeCategories: (params: { page?: number; page_size?: number } = {}) =>
    request<ApiList<KnowledgeCategory> | KnowledgeCategory[]>(`/api/knowledge/categories/${buildQuery(params)}`).then(
      normalizeList,
    ),
  knowledgeDocuments: (params: { q?: string; status?: string; category?: number; page?: number; page_size?: number } = {}) =>
    request<ApiList<KnowledgeDocument> | KnowledgeDocument[]>(`/api/knowledge/documents/${buildQuery(params)}`).then(
      normalizeList,
    ),
  createKnowledgeCategory: (payload: KnowledgeCategoryPayload) =>
    request<KnowledgeCategory>('/api/knowledge/categories/', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  updateKnowledgeCategory: (id: number, payload: Partial<KnowledgeCategoryPayload>) =>
    request<KnowledgeCategory>(`/api/knowledge/categories/${id}/`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),
  createKnowledgeDocument: (payload: KnowledgeDocumentPayload) =>
    request<KnowledgeDocument>('/api/knowledge/documents/', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  updateKnowledgeDocument: (id: number, payload: Partial<KnowledgeDocumentPayload>) =>
    request<KnowledgeDocument>(`/api/knowledge/documents/${id}/`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),
  uploadKnowledgeCover: (file: File) => {
    const form = new FormData();
    form.append('file', file);
    return request<{ url: string }>('/api/knowledge/documents/cover-upload/', {
      method: 'POST',
      body: form,
    });
  },
  uploadKnowledgeMedia: (file: File) => {
    const form = new FormData();
    form.append('file', file);
    return request<{ url: string; kind: string; content_type: string }>('/api/knowledge/documents/media-upload/', {
      method: 'POST',
      body: form,
    });
  },
  selfProfile: () => request<EmployeeProfile>('/api/me/profile/'),
  selfPreferences: () => request<UserPreferences>('/api/me/preferences/'),
  updateSelfPreferences: (payload: Partial<UserPreferences>) =>
    request<UserPreferences>('/api/me/preferences/', {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),
  selfAttendance: () => request<SelfAttendance>('/api/me/attendance/'),
  createTimeCorrection: (payload: {
    date: string;
    requested_start_at?: string;
    requested_end_at?: string;
    reason: string;
  }) =>
    request<TimeCorrectionRequest>('/api/me/time-corrections/', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  selfLeave: () => request<SelfLeave>('/api/me/leave/'),
  createLeaveRequest: (payload: { leave_type: number; date_from: string; date_to: string; reason: string }) =>
    request<LeaveRequest>('/api/me/leave/', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  selfKnowledge: () => request<SelfKnowledge>('/api/me/knowledge/'),

  // --- Оголошення ---
  announcements: (params: { page?: number; page_size?: number } = {}) =>
    request<ApiList<Announcement> | Announcement[]>(`/api/announcements/announcements/${buildQuery(params)}`).then(
      normalizeList,
    ),
  createAnnouncement: (payload: AnnouncementPayload) =>
    request<Announcement>('/api/announcements/announcements/', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  updateAnnouncement: (id: number, payload: Partial<AnnouncementPayload>) =>
    request<Announcement>(`/api/announcements/announcements/${id}/`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),
  deleteAnnouncement: (id: number) =>
    request<void>(`/api/announcements/announcements/${id}/`, { method: 'DELETE' }),
  announcementAudiencePreview: (payload: { audience_type: string; conditions: AnnouncementCondition[] }) =>
    request<AnnouncementAudiencePreview>('/api/announcements/announcements/audience-preview/', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  uploadAnnouncementMedia: (file: File) => {
    const form = new FormData();
    form.append('file', file);
    return request<AnnouncementMediaUpload>('/api/announcements/announcements/media-upload/', {
      method: 'POST',
      body: form,
    });
  },
  reactAnnouncement: (id: number, emoji: string) =>
    request<{ reactions: AnnouncementReactionSummary[] }>(`/api/announcements/announcements/${id}/react/`, {
      method: 'POST',
      body: JSON.stringify({ emoji }),
    }),
  addAnnouncementComment: (id: number, body: string) =>
    request<AnnouncementComment>(`/api/announcements/announcements/${id}/comments/`, {
      method: 'POST',
      body: JSON.stringify({ body }),
    }),
  voteAnnouncementPoll: (id: number, optionIndex: number) =>
    request<{ poll_results: AnnouncementPollResult[]; user_vote: number | null }>(
      `/api/announcements/announcements/${id}/vote/`,
      {
        method: 'POST',
        body: JSON.stringify({ option_index: optionIndex }),
      },
    ),
};
