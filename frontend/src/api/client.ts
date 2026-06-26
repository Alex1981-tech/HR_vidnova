import type {
  ApiList,
  AuthCodeResponse,
  AuthLoginResponse,
  AuthStatus,
  CompanyAttendanceSummary,
  DashboardOverview,
  DepartmentLevelOption,
  DepartmentOption,
  DivisionOption,
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
  PositionOption,
  ProbationPolicyOption,
  SelfAttendance,
  SelfKnowledge,
  SelfLeave,
  TeamOption,
  TerminationReasonOption,
  TerminationTypeOption,
  TimeCorrectionRequest,
  SkillOption,
  WorkType,
  WorkingPatternOption,
  WorkDaySummary,
  CmmsAsset,
} from '../types/api';

const API_BASE = import.meta.env.VITE_API_BASE ?? '';
const CSRF_COOKIE_NAMES = [import.meta.env.VITE_CSRF_COOKIE_NAME ?? 'hr_csrftoken', 'csrftoken'];

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

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const csrfToken = CSRF_COOKIE_NAMES.map(getCookie).find(Boolean) ?? '';
  const bodyIsFormData = typeof FormData !== 'undefined' && init.body instanceof FormData;
  const response = await fetch(`${API_BASE}${path}`, {
    credentials: 'include',
    headers: {
      Accept: 'application/json',
      ...(init.body && !bodyIsFormData ? { 'Content-Type': 'application/json' } : {}),
      ...(init.body && csrfToken ? { 'X-CSRFToken': csrfToken } : {}),
      ...(init.headers ?? {}),
    },
    ...init,
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
  assets: (params: { page?: number; page_size?: number; search?: string } = {}) =>
    request<{ total: number; items: CmmsAsset[] }>(`/api/assets/${buildQuery(params)}`),
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
  workdays: (params: { from?: string; to?: string; employee?: number; status?: string; page?: number } = {}) =>
    request<ApiList<WorkDaySummary> | WorkDaySummary[]>(`/api/skud/workdays/${buildQuery(params)}`).then(normalizeList),
  leaveTypes: (params: { page?: number; page_size?: number } = {}) =>
    request<ApiList<LeaveType> | LeaveType[]>(`/api/leave/types/${buildQuery(params)}`).then(normalizeList),
  leaveRequests: (params: { status?: string; employee?: number; page?: number; page_size?: number } = {}) =>
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
};
