export type EmployeeStatusCount = {
  status: string;
  count: number;
};

export type ApiList<T> = {
  count: number;
  next: string | number | null;
  previous: string | number | null;
  results: T[];
};

export type IntegrationRun = {
  system: string;
  job: string;
  status: string;
  started_at: string;
  rows_inserted: number;
};

export type DashboardOverview = {
  employees_by_status: EmployeeStatusCount[];
  workday_exceptions: number;
  pending_leave_requests: number;
  last_integration_runs: IntegrationRun[];
};

export type AuthStatus = {
  authenticated: boolean;
  user: null | {
    id: number;
    username: string;
    is_staff: boolean;
    is_superuser: boolean;
  };
  employee: null | {
    id: number;
    full_name: string;
    status: string;
  };
  preferences: UserPreferences | null;
};

export type AuthCodeResponse = {
  status: 'code_sent' | string;
};

export type AuthLoginResponse = {
  status: 'ok' | string;
  user: NonNullable<AuthStatus['user']>;
  employee: NonNullable<AuthStatus['employee']>;
};

export type UserPreferences = {
  language: 'en' | 'uk' | 'pl';
  theme: 'light' | 'dark' | 'auto';
  time_zone: string;
};

export type EmployeeProfile = {
  id: number;
  full_name: string;
  avatar_local_url?: string;
  avatar_url?: string;
  first_name: string;
  last_name: string;
  middle_name: string;
  email: string;
  phone: string;
  phone2: string;
  clinic_name: string;
  department_name: string;
  position_name: string;
  status: string;
  hired_on: string | null;
};

export type EmployeeDocument = {
  id: number;
  employee: number;
  employee_name: string;
  folder: number | null;
  folder_name: string;
  legacy_peopleforce_id: string;
  name: string;
  document_type: string;
  source_url: string;
  expires_at: string | null;
  local_file: string;
  file_url: string;
  file_downloaded_at: string | null;
  file_download_error: string;
};

export type EmployeeDocumentFolder = {
  id: number;
  legacy_peopleforce_id: string;
  name: string;
  description: string;
  parent: number | null;
  parent_name: string;
  document_count: number;
  is_active: boolean;
};

export type EmployeeDocumentFolderPayload = {
  name: string;
  description?: string;
  parent?: number | null;
  is_active?: boolean;
};

export type EmergencyContact = {
  id: number;
  employee: number;
  name: string;
  relationship: string;
  work_phone: string;
  home_phone: string;
  mobile_phone: string;
  address: string;
  order: number;
};

export type Dependent = {
  id: number;
  employee: number;
  name: string;
  birth_date: string | null;
  gender: string;
  description: string;
  order: number;
};

export type EmployeeEducation = {
  id: number;
  employee: number;
  institution: string;
  degree: string;
  start_year: number | null;
  end_year: number | null;
  gpa: string;
  order: number;
};

export type EmployeeCertificate = {
  id: number;
  employee: number;
  name: string;
  issuer: string;
  url: string;
  issued_on: string | null;
  expires_on: string | null;
  attachment_url: string;
  thumbnail_url: string;
  attachment_name: string;
  order: number;
};

export type SkillCategory = {
  id: number;
  name: string;
  order: number;
  is_active: boolean;
  employee_count: number;
};

export type SkillCatalogItem = {
  id: number;
  category: number;
  category_name: string;
  name: string;
  is_active: boolean;
  employee_count: number;
};

export type EmployeeSkill = {
  id: number;
  employee: number;
  skill: number;
  skill_name: string;
  category: number;
  category_name: string;
  level: string;
  level_display: string;
  order: number;
  employee_detail?: EmployeeListItem;
};

export type EmployeeNote = {
  id: number;
  employee: number;
  body_html: string;
  author: number | null;
  author_name: string;
  created_at: string;
  updated_at: string;
};

export type JobLevel = {
  id: number;
  name: string;
  external_peopleforce_id: string;
  sort_order: number;
  is_active: boolean;
  employee_count: number;
};

export type GenderOption = {
  id: number;
  code: string;
  name: string;
  external_peopleforce_id: string;
  is_active: boolean;
  employee_count: number;
};

export type TerminationReasonOption = {
  id: number;
  name: string;
  external_peopleforce_id: string;
  is_active: boolean;
  employee_count: number;
};

export type TerminationTypeOption = {
  id: number;
  name: string;
  external_peopleforce_id: string;
  is_active: boolean;
  employee_count: number;
};

export type WorkType = {
  id: number;
  name: string;
  external_peopleforce_id: string;
  is_active: boolean;
  employee_count: number;
};

export type EmployeeFormType =
  | 'new_hire'
  | 'preboarding'
  | 'people_data_change'
  | 'self_service'
  | 'custom_request'
  | 'termination';

export type EmployeeFormField = {
  id: string;
  name: string;
  field_type?: string;
  required?: boolean;
};

export type EmployeeFormSection = {
  id: string;
  name: string;
  fields: EmployeeFormField[];
};

export type EmployeeFormTemplate = {
  id: number;
  form_type: EmployeeFormType;
  form_type_label: string;
  name: string;
  description: string;
  allow_employee_access: boolean;
  workflow_name: string;
  allow_requester_disable_workflow: boolean;
  preboarding_form: number | null;
  preboarding_form_name: string;
  absence_policy_names: string[];
  sections: EmployeeFormSection[];
  section_count: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type EmployeeFormTemplateSummary = {
  form_type: EmployeeFormType;
  count: number;
};

export type ProbationPolicyOption = {
  id: number;
  name: string;
  external_peopleforce_id: string;
  duration_months: number;
  is_active: boolean;
  employee_count: number;
};

export type HolidayPolicyOption = {
  id: number;
  name: string;
  external_peopleforce_id: string;
  country_code: string;
  country_name: string;
  is_active: boolean;
  location_count: number;
  holiday_count: number;
};

export type HolidayOption = {
  id: number;
  policy: number;
  policy_name: string;
  legacy_peopleforce_id: string;
  name: string;
  occurs_on: string;
  starts_on: string | null;
  ends_on: string | null;
  working: boolean;
  compensated_on: string | null;
  observed_on: string | null;
  recurrence: 'none' | 'yearly' | string;
  is_active: boolean;
};

export type CompanyLink = {
  id: number;
  title: string;
  url: string;
  icon_url: string;
  order: number;
  is_active: boolean;
  audience_type: 'all' | 'conditions';
  conditions: AnnouncementCondition[];
  created_at: string;
  updated_at: string;
};

export type WorkingPatternScheduleDay = {
  key: string;
  label?: string;
  time_range?: string;
  break_hours?: number;
  hours?: number;
};

export type WorkingPatternSchedule = {
  source?: string;
  days?: WorkingPatternScheduleDay[];
  raw?: Record<string, unknown>;
};

export type WorkingPatternOption = {
  id: number;
  name: string;
  external_peopleforce_id: string;
  monday_hours: string | number;
  tuesday_hours: string | number;
  wednesday_hours: string | number;
  thursday_hours: string | number;
  friday_hours: string | number;
  saturday_hours: string | number;
  sunday_hours: string | number;
  uses_time_range: boolean;
  is_default: boolean;
  schedule: WorkingPatternSchedule;
  is_active: boolean;
};

export type PositionOption = {
  id: number;
  name: string;
  external_peopleforce_id: string;
  is_active: boolean;
  employee_count: number;
};

export type DivisionOption = {
  id: number;
  name: string;
  external_peopleforce_id: string;
  is_active: boolean;
  employee_count: number;
};

export type SkillOption = {
  id: number;
  name: string;
  external_fotopacients_id: string;
  external_peopleforce_id: string;
  is_active: boolean;
  employee_count: number;
};

export type ClinicLocation = {
  id: number;
  name: string;
  code: string;
  external_peopleforce_id: string;
  country_code: string;
  country_name: string;
  address: string;
  holiday_policy_id: string;
  holiday_policy_name: string;
  holiday_policy_ref: number | null;
  holiday_policy_ref_name: string;
  time_zone: string;
  is_active: boolean;
  employee_count: number;
};

export type DepartmentLevelOption = {
  id: number;
  name: string;
  color: string;
  external_peopleforce_id: string;
  is_active: boolean;
  department_count: number;
};

export type DepartmentOption = {
  id: number;
  clinic: number | null;
  clinic_name: string;
  parent: number | null;
  parent_name: string;
  manager: number | null;
  manager_name: string;
  level: number | null;
  level_name: string;
  level_color: string;
  name: string;
  code: string;
  external_peopleforce_id: string;
  is_active: boolean;
  employee_count: number;
  children_count: number;
};

export type EmployeeListItem = EmployeeProfile & {
  user: number | null;
  external_baf_id: string;
  external_fotopacients_id: string;
  legacy_peopleforce_id: string;
  employee_number: string;
  personal_email: string;
  telegram_id: string;
  facebook_url: string;
  instagram_url: string;
  birth_date: string | null;
  gender: string;
  avatar_url: string;
  avatar_local_url: string;
  avatar_downloaded_at: string | null;
  avatar_download_error: string;
  peopleforce_status: string;
  peopleforce_fields: Record<string, unknown>;
  custom_fields: Record<string, unknown>;
  clinic: number | null;
  department: number | null;
  position: number | null;
  division: number | null;
  division_name: string;
  employment_type: number | null;
  employment_type_name: string;
  job_level: number | null;
  job_level_name: string;
  medical_specialties: number[];
  medical_specialty_names: string[];
  manager_name: string;
  manager_profile: EmployeeListItem | null;
  direct_reports_count: number;
  direct_reports?: EmployeeListItem[];
  teams?: Array<{ id: number; name: string; role: 'lead' | 'member' }>;
  dismissed_on: string | null;
  notes: string;
  documents: EmployeeDocument[];
};

export type TeamOption = {
  id: number;
  name: string;
  external_peopleforce_id: string;
  description: string;
  lead: number | null;
  lead_name: string;
  lead_profile: EmployeeListItem | null;
  member_count: number;
  members: EmployeeListItem[];
  is_active: boolean;
};

export type WorkDaySummary = {
  id: number;
  employee: number;
  employee_name: string;
  date: string;
  planned_minutes: number;
  actual_minutes: number;
  first_entry_at: string | null;
  last_exit_at: string | null;
  status: string;
  exception_count: number;
  calculated_at: string | null;
  locked_at: string | null;
};

export type CompanyAttendanceSummary = {
  id: number;
  employee: number;
  employee_name: string;
  position_name: string;
  department_name: string;
  clinic_name: string;
  planned_minutes: number;
  actual_minutes: number;
  overtime_minutes: number;
  break_minutes: number;
  paid_absence_minutes: number;
  unpaid_absence_minutes: number;
  total_absence_minutes: number;
  difference_minutes: number;
  first_entry_at: string | null;
  last_exit_at: string | null;
  exception_count: number;
  summary_count: number;
};

export type EmployeeAttendancePeriod = {
  id: number;
  start_at: string;
  end_at: string;
  duration_minutes: number;
  period_type: string;
  comment: string;
};

export type EmployeeAttendanceDay = {
  date: string;
  planned_minutes: number;
  actual_minutes: number;
  overtime_minutes: number;
  break_minutes: number;
  paid_absence_minutes: number;
  unpaid_absence_minutes: number;
  total_absence_minutes: number;
  difference_minutes: number;
  first_entry_at: string | null;
  last_exit_at: string | null;
  status: string;
  exception_count: number;
  working_pattern_names: string[];
  periods: EmployeeAttendancePeriod[];
};

export type EmployeeAttendanceDetail = {
  employee: {
    id: number;
    full_name: string;
    position_name: string;
    department_name: string;
    clinic_name: string;
    avatar_url: string;
    avatar_local_url: string;
  };
  range: {
    from: string;
    to: string;
  };
  summary: {
    planned_minutes: number;
    actual_minutes: number;
    overtime_minutes: number;
    break_minutes: number;
    paid_absence_minutes: number;
    unpaid_absence_minutes: number;
    total_absence_minutes: number;
    difference_minutes: number;
  };
  days: EmployeeAttendanceDay[];
};

export type AccessEvent = {
  id: number;
  device_name: string;
  occurred_at: string;
  direction: string;
  quality: string;
};

export type TimeCorrectionRequest = {
  id: number;
  date: string;
  requested_start_at: string | null;
  requested_end_at: string | null;
  reason: string;
  status: string;
  submitted_at: string | null;
  decided_at: string | null;
  decision_comment: string;
  created_at: string;
};

export type SelfAttendance = {
  employee: EmployeeProfile;
  range: {
    from: string;
    to: string;
  };
  workdays: WorkDaySummary[];
  events: AccessEvent[];
  correction_requests: TimeCorrectionRequest[];
};

export type LeaveType = {
  id: number;
  name: string;
  code: string;
  unit: string;
  icon: string;
  color: string;
  order: number;
  requires_hr_approval: boolean;
  is_active: boolean;
  balance?: number | null;
};

export type LeaveTypePayload = {
  name: string;
  unit?: string;
  icon?: string;
  color?: string;
  requires_hr_approval?: boolean;
  is_active?: boolean;
};

export type LeavePolicyAccrualRule = {
  id: number;
  enabled: boolean;
  start_delay_amount: number;
  start_delay_unit: string;
  start_balance: string;
  annual_allowance: string;
  period_amount: string;
  frequency: string;
  accrual_timing: string;
  first_accrual: string;
  max_balance: string | null;
  carryover_mode: string;
  carryover_limit: string | null;
  carryover_expire_months: number;
  carryover_day: number;
  carryover_month: number;
  seniority_bonus_enabled: boolean;
  seniority_bonus_levels: unknown[];
};

export type LeavePolicy = {
  id: number;
  leave_type: number;
  leave_type_name: string;
  name: string;
  legacy_peopleforce_id?: string;
  policy_type: string;
  type?: string;
  activity_type: string;
  counted_as: string;
  visibility: string;
  instructions_html: string;
  deduct_non_working_holidays: boolean;
  allow_on_demand_absence: boolean;
  on_demand_limit: string | null;
  prevent_overlapping_requests: boolean;
  forbid_probation_requests: boolean;
  forbid_breakdown_edit: boolean;
  restrict_adjustments_for_employees: boolean;
  direct_reports_only: boolean;
  min_daily_amount: string | null;
  min_total_amount: string | null;
  max_total_amount: string | null;
  min_notice_days: number | null;
  max_notice_days: number | null;
  approval_enabled: boolean;
  skip_unassigned_approvers: boolean;
  allow_substitute_approvers: boolean;
  approver_steps: unknown[];
  allow_negative_balance: boolean;
  limit_negative_balance: boolean;
  max_negative_balance: string | null;
  rounding_method: string;
  rounding_precision: string;
  allow_withdraw: boolean;
  mandatory_comment: boolean;
  allow_attachments: boolean;
  notify_approver: boolean;
  is_active: boolean;
  employee_count: number;
  accrual_rule?: LeavePolicyAccrualRule | null;
  created_at?: string;
  updated_at?: string;
};

export type LeavePolicyPayload = Partial<Omit<LeavePolicy, 'id' | 'leave_type_name' | 'employee_count' | 'created_at' | 'updated_at' | 'type'>> & {
  leave_type: number;
  name: string;
};

export type LeaveTypeWithPolicies = LeaveType & {
  policies: LeavePolicy[];
};

export type EmployeeLeavePolicyAssignment = {
  id: number;
  employee: number;
  employee_name: string;
  employee_avatar_url: string;
  employee_avatar_local_url: string;
  employee_position_name: string;
  leave_type: number;
  leave_type_name: string;
  policy: number;
  policy_name: string;
  policy_type: string;
  effective_on: string;
  ends_on: string | null;
  initial_balance: string;
  balance: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type LeaveRequest = {
  id: number;
  employee?: number;
  employee_name?: string;
  employee_avatar_url?: string;
  employee_avatar_local_url?: string;
  employee_position_name?: string;
  legacy_peopleforce_id?: string;
  leave_type: number;
  leave_type_name: string;
  date_from: string;
  date_to: string;
  reason: string;
  amount?: string;
  tracking_time_in?: string;
  status: string;
  submitted_at: string | null;
  decided_at: string | null;
  decided_by?: number | null;
  created_at: string;
  approval_steps?: LeaveApprovalStep[];
};

export type LeaveApprovalStep = {
  id: number;
  approver: number;
  approver_name: string;
  order: number;
  status: string;
  decided_at: string | null;
  comment: string;
};

export type LeaveBalance = {
  id: number;
  employee: number;
  employee_name: string;
  leave_type: number;
  leave_type_name: string;
  legacy_peopleforce_id: string;
  effective_on: string | null;
  balance: string;
  policy_name: string;
  policy_activity_type: string;
  policy_counted_as: string;
};

export type LeaveLedgerEntry = {
  id: number;
  employee: number;
  employee_name: string;
  leave_type: number;
  leave_type_name: string;
  policy: number | null;
  policy_name: string;
  assignment: number | null;
  kind: string;
  occurred_on: string;
  amount: string;
  balance_after: string;
  description: string;
  source_model: string;
  source_id: string;
  created_at: string;
};

export type SelfLeave = {
  leave_types: LeaveType[];
  requests: LeaveRequest[];
};

export type KnowledgeCategory = {
  id: number;
  name: string;
  slug: string;
  legacy_peopleforce_id: string;
  description: string;
  icon_emoji: string;
  visibility_mode: string;
  audience_employee_ids: number[];
  audience_filters: Record<string, unknown>;
  conditions: AnnouncementCondition[];
  position: number;
  parent: number | null;
  is_active: boolean;
};

export type KnowledgeAttachment = {
  id: number;
  legacy_peopleforce_id: string;
  file: string;
  original_name: string;
  content_type: string;
  size_bytes: number;
  source_url: string;
  created_at: string;
};

export type KnowledgeDocument = {
  id: number;
  category: number;
  category_name: string;
  owner_name?: string;
  view_count: number;
  legacy_peopleforce_id: string;
  title: string;
  slug: string;
  summary: string;
  cover_url: string;
  body: string;
  body_html: string;
  status: string;
  tags: string[];
  published_at: string | null;
  attachments: KnowledgeAttachment[];
  created_at: string;
  updated_at: string;
};

export type SelfKnowledge = {
  categories: KnowledgeCategory[];
  documents: KnowledgeDocument[];
};

export type CmmsAsset = {
  id: number;
  inventory_number: string;
  name: string;
  status: string;
  manufacturer?: string | null;
  asset_type_id: number | null;
  category_id: number | null;
  location_id?: number | null;
  location_path?: string[] | null;
  location_name?: string | null;
  department_id?: number | null;
  department_name?: string | null;
  responsible_person_id: number | null;
  responsible_person_name: string | null;
  engineer_id?: number | null;
  engineer_name?: string | null;
  photo_url?: string | null;
};

export type CmmsAssetPhoto = {
  id: number | null;
  url: string | null;
  thumbnail_url: string | null;
  is_primary?: boolean;
  content_type?: string;
  is_video?: boolean;
};

export type AssetPerson = {
  id: number;
  full_name: string;
  position: string;
  avatar_url: string | null;
};

export type SecurityLogEvent = {
  id: number;
  event: string;
  event_label: string;
  result: string;
  ip_address: string | null;
  user_agent: string;
  created_at: string;
};

export type EntrustedGroup = {
  employee: AssetPerson;
  assets: CmmsAsset[];
};

export type CmmsAssetDetail = CmmsAsset & {
  description?: string | null;
  photos?: CmmsAssetPhoto[];
  responsible?: AssetPerson | null;
  engineer?: AssetPerson | null;
};

export type AssetZone = {
  id: number;
  name: string;
  scope_type: 'location' | 'department';
  location_id: number | null;
  location_name: string;
  department_id: number | null;
  department_name: string;
  engineer_user_id: number | null;
  engineer_name: string;
  last_applied_at: string | null;
  last_applied_count: number | null;
};

export type PhysicalNode = {
  id: number;
  name: string;
  kind: 'city' | 'clinic' | 'floor' | 'cabinet';
  parent_id: number | null;
  order: number;
  asset_count: number;
  engineer_id: number | null;
  engineer_name: string | null;
  children: PhysicalNode[];
};

export type AssetZoneOptions = {
  locations: CmmsLocation[];
  departments: Array<{ id: number; name: string }>;
  engineers: Array<{ id: number; full_name: string }>;
};

export type CmmsOwnershipRow = {
  date: string | null;
  city: string | null;
  clinic: string | null;
  cabinet: string | null;
  responsible_name: string | null;
  engineer_name: string | null;
  handed_over: string | null;
  is_creation?: boolean;
};

export type CmmsLocation = {
  id: number;
  name: string;
  parent_id: number | null;
  level: number;
  sublocations?: CmmsLocation[];
};

export type CmmsAssetOptions = {
  statuses: string[];
  asset_types: Array<{ id: number; name: string }>;
  categories: Array<{ id: number; name: string; parent_id?: number | null }>;
  locations: CmmsLocation[];
  departments: Array<{ id: number; name: string }>;
  employees: Array<{ id: number; full_name: string }>;
};

export type AnnouncementCondition = {
  field: string;
  operator: '' | 'is' | 'is_not' | 'is_empty' | 'is_not_empty';
  value: number[];
};

export type AnnouncementReactionSummary = {
  emoji: string;
  count: number;
  reacted: boolean;
  users: string[];
};

export type AnnouncementComment = {
  id: number;
  announcement: number;
  author: number | null;
  author_name: string;
  author_avatar: string;
  employee: number | null;
  body: string;
  created_at: string;
};

export type AnnouncementPollResult = {
  index: number;
  text: string;
  votes: number;
  percentage: number;
  total_votes: number;
};

export type Announcement = {
  id: number;
  title: string;
  kind: 'announcement' | 'poll';
  body_html: string;
  poll_options: string[];
  author: number | null;
  author_name: string;
  author_avatar: string;
  author_role: string;
  audience_type: 'all' | 'conditions';
  conditions: AnnouncementCondition[];
  notify_telegram: boolean;
  notify_email: boolean;
  notify_web: boolean;
  allow_comments: boolean;
  scheduled_at: string | null;
  status: 'draft' | 'scheduled' | 'published';
  published_at: string | null;
  recipients_count: number;
  tg_sent_count: number;
  tg_failed_count: number;
  tg_dispatched_at: string | null;
  comments_count: number;
  comments: AnnouncementComment[];
  reactions: AnnouncementReactionSummary[];
  poll_results: AnnouncementPollResult[];
  user_vote: number | null;
  created_at: string;
  updated_at: string;
};

export type AnnouncementPayload = {
  kind?: 'announcement' | 'poll';
  title: string;
  body_html: string;
  poll_options?: string[];
  audience_type: 'all' | 'conditions';
  conditions: AnnouncementCondition[];
  notify_telegram: boolean;
  notify_email?: boolean;
  notify_web: boolean;
  allow_comments: boolean;
  scheduled_at?: string | null;
};

export type AnnouncementAudiencePreview = {
  count: number;
  sample: Array<{ id: number; full_name: string; avatar_url: string }>;
};

export type AnnouncementMediaUpload = {
  url: string;
  kind: 'image' | 'video';
  content_type: string;
  name: string;
  size: number;
};

export type ProjectMember = {
  id: number;
  full_name: string;
  position_name?: string;
  avatar_url: string;
  avatar_local_url: string;
};

export type Project = {
  id: number;
  name: string;
  emoji: string;
  is_archived: boolean;
  order: number;
  member_count: number;
  members?: ProjectMember[];
  created_at?: string;
  updated_at?: string;
};

export type ProjectPayload = {
  name: string;
  emoji?: string;
  is_archived?: boolean;
};

export type TimeEntry = {
  id: number;
  project: number | null;
  project_name: string;
  project_emoji: string;
  comment: string;
  started_at: string;
  ended_at: string | null;
  duration_seconds: number;
  is_running: boolean;
};
