import {
  Bell,
  BookOpen,
  Bold,
  Boxes,
  BriefcaseBusiness,
  Building2,
  Calendar,
  CalendarCheck,
  Check,
  CheckSquare,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  CircleGauge,
  Clock3,
  Columns3,
  Edit3,
  ArrowUpRight,
  Eye,
  FileText,
  Filter,
  GitBranch,
  Grid3X3,
  GripVertical,
  Network,
  Home,
  Heading1,
  Heading2,
  ImagePlus,
  Italic,
  Laptop,
  LayoutList,
  Link,
  List,
  ListChecks,
  ListOrdered,
  Lock,
  LogOut,
  Mail,
  MapPin,
  Menu,
  Maximize2,
  MoreHorizontal,
  Palette,
  PanelLeftClose,
  Phone,
  Plus,
  Quote,
  Rocket,
  Save,
  Search,
  Settings,
  ShieldCheck,
  Smile,
  Sparkles,
  Star,
  Timer,
  Trash2,
  Type,
  Underline,
  Upload,
  Users,
  Video,
  X,
  Zap,
  ZoomIn,
  ZoomOut,
} from 'lucide-react';
import { ECanDrag, GraphState, MultipointConnection, polyline } from '@gravity-ui/graph';
import type { Graph, TBlock, TConnection, TGraphColors, TGraphConstants, TPoint, TRect } from '@gravity-ui/graph';
import { GraphBlock, GraphCanvas, useGraph } from '@gravity-ui/graph/react';
import type { LucideIcon } from 'lucide-react';
import { QRCodeSVG } from 'qrcode.react';
import type { CSSProperties, DragEvent, FormEvent, MouseEvent as ReactMouseEvent, PointerEvent as ReactPointerEvent, ReactNode } from 'react';
import { Fragment, useEffect, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { useLocation, useNavigate } from 'react-router-dom';

import { ApiError, api, type EmployeeHirePayload } from './api/client';
import { APP_VERSION, APP_VERSION_DATE, changelog } from './changelog';
import { getAppCopy, getTranslations, languageOptions, normalizeLanguage, normalizeTheme, themeOptions } from './i18n/locales';
import type { AppCopy, LanguageCode, ThemePreference } from './i18n/locales';
import type {
  AuthLoginResponse,
  AuthStatus,
  ClinicLocation,
  CompanyAttendanceSummary,
  DashboardOverview,
  DepartmentLevelOption,
  CmmsAsset,
  CmmsAssetOptions,
  CmmsLocation,
  DepartmentOption,
  DivisionOption,
  EmployeeAttendanceDay,
  EmployeeAttendanceDetail,
  EmployeeAttendancePeriod,
  EmployeeListItem,
  EmployeeProfile,
  GenderOption,
  HolidayOption,
  HolidayPolicyOption,
  JobLevel,
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
  SkillOption,
  TeamOption,
  TimeCorrectionRequest,
  WorkType,
  WorkingPatternOption,
  WorkDaySummary,
} from './types/api';

type Section =
  | 'home'
  | 'notifications'
  | 'people'
  | 'calendar'
  | 'attendance'
  | 'requests'
  | 'knowledge'
  | 'assets'
  | 'reports'
  | 'org'
  | 'settings'
  | 'changelog';

type LoadState = 'idle' | 'loading' | 'ok' | 'error';

type Person = {
  id: number;
  fullName: string;
  role: string;
  department: string;
  location: string;
  manager: string;
  startDate: string;
  email: string;
  phone: string;
  avatarUrl: string;
  accent: string;
  directReportsCount: number;
  employee: EmployeeListItem;
};

type PeopleFilterState = {
  status: string;
  position: string[];
  departmentLevel: string[];
  department: string[];
  division: string[];
  location: string[];
  team: string[];
  jobLevel: string[];
  workType: string[];
};

type PeopleMultiFilterKey = Exclude<keyof PeopleFilterState, 'status'>;

type PeopleFilterOption = {
  value: string;
  label: string;
  count?: number;
};

type PeopleFilterOptions = {
  positions: PeopleFilterOption[];
  departmentLevels: PeopleFilterOption[];
  departments: PeopleFilterOption[];
  divisions: PeopleFilterOption[];
  locations: PeopleFilterOption[];
  teams: PeopleFilterOption[];
  jobLevels: PeopleFilterOption[];
  workTypes: PeopleFilterOption[];
};

type NewHireStep = 'details' | 'review';

type NewHireFormState = {
  first_name: string;
  last_name: string;
  middle_name: string;
  personal_email: string;
  email: string;
  phone: string;
  phone2: string;
  birth_date: string;
  gender: string;
  hired_on: string;
  employment_type: string;
  working_pattern: string;
  probation_policy: string;
  position: string;
  department: string;
  division: string;
  clinic: string;
  manager: string;
  job_level: string;
  medical_specialties: string[];
  notes: string;
};

type NewHireOptions = {
  positions: PositionOption[];
  departments: DepartmentOption[];
  divisions: DivisionOption[];
  locations: ClinicLocation[];
  workTypes: WorkType[];
  workingPatterns: WorkingPatternOption[];
  probationPolicies: ProbationPolicyOption[];
  jobLevels: JobLevel[];
  genders: GenderOption[];
  skills: SkillOption[];
  managers: EmployeeListItem[];
};

const defaultPeopleFilters: PeopleFilterState = {
  status: 'active',
  position: [],
  departmentLevel: [],
  department: [],
  division: [],
  location: [],
  team: [],
  jobLevel: [],
  workType: [],
};

const emptyPeopleFilterOptions: PeopleFilterOptions = {
  positions: [],
  departmentLevels: [],
  departments: [],
  divisions: [],
  locations: [],
  teams: [],
  jobLevels: [],
  workTypes: [],
};

const emptyNewHireOptions: NewHireOptions = {
  positions: [],
  departments: [],
  divisions: [],
  locations: [],
  workTypes: [],
  workingPatterns: [],
  probationPolicies: [],
  jobLevels: [],
  genders: [],
  skills: [],
  managers: [],
};

type LeaveBand = {
  personId: number;
  start: number;
  span: number;
  label: string;
};

type AttendanceSummaryRow = {
  id: number;
  employeeId: number;
  fullName: string;
  expected: string;
  worked: string;
  overtime: string;
  breakTime: string;
  paidAbsence: string;
  unpaidAbsence: string;
  totalAbsence: string;
  difference: string;
};

type AttendancePeriodFormState = {
  start_time: string;
  end_time: string;
  comment: string;
};

const fallbackOverview: DashboardOverview = {
  employees_by_status: [],
  workday_exceptions: 0,
  pending_leave_requests: 0,
  last_integration_runs: [],
};

const fallbackEmployee: EmployeeProfile = {
  id: 0,
  full_name: 'Користувач',
  first_name: '',
  last_name: '',
  middle_name: '',
  email: '',
  phone: '',
  phone2: '',
  clinic_name: '',
  department_name: '',
  position_name: '',
  status: '',
  hired_on: null,
};

function profileFromAuthEmployee(employee: NonNullable<AuthStatus['employee']>): EmployeeProfile {
  return {
    ...fallbackEmployee,
    id: employee.id,
    full_name: employee.full_name || fallbackEmployee.full_name,
    status: employee.status,
  };
}

const fallbackLeaveTypes: LeaveType[] = [];
const TELEGRAM_BOT_URL = import.meta.env.VITE_HR_TELEGRAM_BOT_URL ?? 'https://t.me/Clinical_Photo_bot?start=link';
const LOGIN_CODE_RESEND_DELAY_SECONDS = 60;

const fallbackKnowledge: SelfKnowledge = {
  categories: [],
  documents: [],
};

const fallbackLeave: SelfLeave = {
  leave_types: fallbackLeaveTypes,
  requests: [],
};

const leaveBands: LeaveBand[] = [];

const sidebarItems: Array<{ section: Section; icon: LucideIcon; badge?: number; expandable?: boolean }> = [
  { section: 'home', icon: Home },
  { section: 'notifications', icon: Bell, badge: 3 },
  { section: 'people', icon: Users },
  { section: 'calendar', icon: Calendar },
  { section: 'attendance', icon: Clock3 },
  { section: 'requests', icon: Zap },
  { section: 'knowledge', icon: BookOpen },
  { section: 'assets', icon: Boxes },
  { section: 'reports', icon: Columns3 },
];

const mobileItems: Section[] = ['home', 'people', 'calendar', 'attendance', 'knowledge'];

const sectionPaths: Record<Section, string> = {
  home: '/',
  notifications: '/notifications',
  people: '/people',
  calendar: '/calendar',
  attendance: '/attendance',
  requests: '/requests',
  knowledge: '/knowledge',
  assets: '/assets',
  reports: '/reports',
  org: '/org',
  settings: '/settings',
  changelog: '/changelog',
};

const pathSectionMap: Record<string, Section> = {
  notifications: 'notifications',
  people: 'people',
  calendar: 'calendar',
  attendance: 'attendance',
  requests: 'requests',
  knowledge: 'knowledge',
  assets: 'assets',
  reports: 'reports',
  org: 'org',
  settings: 'settings',
  changelog: 'changelog',
};

const legacyHashPaths: Record<string, string> = {
  '#home': '/',
  '#notifications': '/notifications',
  '#people': '/people',
  '#calendar': '/calendar',
  '#attendance': '/attendance',
  '#requests': '/requests',
  '#documents': '/knowledge',
  '#knowledge': '/knowledge',
  '#reports': '/reports',
  '#org': '/org',
  '#settings': '/settings',
};

function sectionFromPathname(pathname: string): Section {
  const [segment = ''] = pathname.split('/').filter(Boolean);
  return segment ? pathSectionMap[segment] ?? 'home' : 'home';
}

function removedRouteRedirect(pathname: string): string | null {
  const [segment = ''] = pathname.split('/').filter(Boolean);
  return segment === 'documents' ? '/knowledge' : null;
}

type PeopleRoute =
  | { mode: 'list' }
  | { mode: 'teams' }
  | { mode: 'org' }
  | { mode: 'new' }
  | { mode: 'profile'; id: number };

function peopleRouteFromPathname(pathname: string): PeopleRoute {
  const [sectionName, resource, idSegment] = pathname.split('/').filter(Boolean);
  if (sectionName !== 'people') return { mode: 'list' };
  if (!resource) return { mode: 'list' };
  if (resource === 'teams') return { mode: 'teams' };
  if (resource === 'org') return { mode: 'org' };
  if (resource === 'new') return { mode: 'new' };
  if (resource === 'employees') {
    const id = positiveRouteId(idSegment);
    return id ? { mode: 'profile', id } : { mode: 'list' };
  }
  return { mode: 'list' };
}

function peopleEmployeePath(employeeId: number): string {
  return `/people/employees/${employeeId}`;
}

type AttendanceRoute = { mode: 'company' } | { mode: 'employee'; id: number };

function attendanceRouteFromPathname(pathname: string): AttendanceRoute {
  const [sectionName, resource, idSegment] = pathname.split('/').filter(Boolean);
  if (sectionName === 'attendance' && resource === 'employees') {
    const id = positiveRouteId(idSegment);
    return id ? { mode: 'employee', id } : { mode: 'company' };
  }
  return { mode: 'company' };
}

function monthQueryValue(month: Date): string {
  return `${month.getFullYear()}-${pad(month.getMonth() + 1)}`;
}

function monthFromAttendanceSearch(search: string): Date {
  const month = new URLSearchParams(search).get('month') || '';
  const match = month.match(/^(\d{4})-(\d{2})$/);
  if (!match) return getInitialMonth();
  const year = Number(match[1]);
  const monthIndex = Number(match[2]) - 1;
  if (!Number.isFinite(year) || monthIndex < 0 || monthIndex > 11) return getInitialMonth();
  return new Date(year, monthIndex, 1);
}

function attendanceEmployeePath(employeeId: number, month?: string): string {
  return `/attendance/employees/${employeeId}${month ? `?month=${month}` : ''}`;
}

type SettingsItem = {
  slug: string;
  label: string;
  icon: LucideIcon;
};

type SettingsGroup = {
  key: string;
  title: string;
  items: SettingsItem[];
};

type BrandingSettings = {
  language: LanguageCode;
  theme: ThemePreference;
  primaryColor: string;
  logoName: string;
  logoPreviewUrl: string;
  homeCoverDisabled: boolean;
  homeCoverUrl: string;
  homeCoverName: string;
  homeCoverBytes: number;
  employeeCoverDisabled: boolean;
  employeeCoverUrl: string;
  employeeCoverName: string;
  employeeCoverBytes: number;
  employeeCoverUploadAllowed: boolean;
};

type CoverCropResult = {
  url: string;
  name: string;
  bytes: number;
};

type EmployeeCoverMap = Record<string, CoverCropResult>;

const defaultCoverUrl = '/vidnova-profile-banner.png?v=20260625';
const brandingStorageKey = 'hr_vidnova_branding_settings_v1';
const peopleViewStorageKey = 'hr_vidnova_people_view_v1';
const peoplePageSize = 25;
const employeeCoverStorageKey = 'hr_vidnova_employee_covers_v1';
const defaultBrandingSettings: BrandingSettings = {
  language: 'en',
  theme: 'light',
  primaryColor: '#9e9cf7',
  logoName: '',
  logoPreviewUrl: '',
  homeCoverDisabled: true,
  homeCoverUrl: defaultCoverUrl,
  homeCoverName: '',
  homeCoverBytes: 0,
  employeeCoverDisabled: true,
  employeeCoverUrl: defaultCoverUrl,
  employeeCoverName: '',
  employeeCoverBytes: 0,
  employeeCoverUploadAllowed: false,
};

function brandingThemeStyle(settings: BrandingSettings): CSSProperties {
  return {
    '--brand-accent': settings.primaryColor,
    '--settings-accent': settings.primaryColor,
    '--primary': settings.primaryColor,
    '--primary-strong': `color-mix(in srgb, ${settings.primaryColor} 84%, #111827)`,
    '--primary-soft': `color-mix(in srgb, ${settings.primaryColor} 14%, #ffffff)`,
  } as CSSProperties;
}

const settingsGroups: SettingsGroup[] = [
  {
    key: 'general',
    title: 'Загальні',
    items: [
      { slug: 'general', label: 'Загальні', icon: Settings },
      { slug: 'webhooks', label: 'Вебхуки', icon: Link },
      { slug: 'subscription', label: 'Підписка', icon: CalendarCheck },
      { slug: 'notifications', label: 'Сповіщення', icon: Bell },
      { slug: 'import', label: 'Імпорт', icon: Upload },
      { slug: 'integrations', label: 'Інтеграції', icon: GitBranch },
      { slug: 'export', label: 'Експорт', icon: FileText },
    ],
  },
  {
    key: 'basics',
    title: 'Основні',
    items: [
      { slug: 'home', label: 'Головна', icon: Home },
      { slug: 'experience-levels', label: 'Рівень досвіду', icon: Star },
      { slug: 'locations', label: 'Локації', icon: MapPin },
      { slug: 'gender', label: 'Стать', icon: Users },
      { slug: 'forms', label: 'Форми', icon: FileText },
      { slug: 'calendars', label: 'Календарі', icon: Calendar },
      { slug: 'departments', label: 'Департаменти', icon: Building2 },
      { slug: 'holiday-policies', label: 'Політики свят', icon: Sparkles },
      { slug: 'positions', label: 'Посади', icon: BriefcaseBusiness },
      { slug: 'divisions', label: 'Підрозділи', icon: GitBranch },
      { slug: 'work-types', label: 'Типи роботи', icon: Laptop },
      { slug: 'skills', label: 'Навички', icon: ShieldCheck },
    ],
  },
  {
    key: 'hr',
    title: 'HR',
    items: [
      { slug: 'leave-types', label: 'Типи відсутностей', icon: Calendar },
      { slug: 'termination-reasons', label: 'Причини звільнення', icon: Users },
      { slug: 'people-data', label: 'Дані про людей', icon: FileText },
      { slug: 'work-schedules', label: 'Графік роботи', icon: List },
      { slug: 'termination-types', label: 'Типи звільнення', icon: X },
      { slug: 'asset-fields', label: 'Поля активів', icon: LayoutList },
      { slug: 'probation-conditions', label: 'Умови випробного терміну', icon: Users },
      { slug: 'documents', label: 'Документи', icon: FileText },
      { slug: 'asset-categories', label: 'Категорії активів', icon: Laptop },
    ],
  },
  {
    key: 'time',
    title: 'Time',
    items: [{ slug: 'attendance-policies', label: 'Політики обліку присутності', icon: Clock3 }],
  },
  {
    key: 'pulse',
    title: 'Pulse',
    items: [
      { slug: 'segments', label: 'Сегменти', icon: CircleGauge },
      { slug: 'rating-scales', label: 'Рейтингові шкали', icon: Star },
    ],
  },
  {
    key: 'payroll',
    title: 'Платіжна відомість',
    items: [{ slug: 'compensation', label: 'Компенсація', icon: CalendarCheck }],
  },
  {
    key: 'security',
    title: 'Безпека',
    items: [
      { slug: 'roles', label: 'Ролі та права доступу', icon: Users },
      { slug: 'authentications', label: 'Автентифікації', icon: ShieldCheck },
      { slug: 'api-keys', label: 'Ключі API', icon: Link },
    ],
  },
];

const settingsItemsBySlug = new Map(
  settingsGroups.flatMap((group) => group.items.map((item) => [item.slug, { ...item, group: group.title, groupKey: group.key }])),
);

function settingsSlugFromPathname(pathname: string): string {
  const [sectionName, slug = ''] = pathname.split('/').filter(Boolean);
  return sectionName === 'settings' ? slug : '';
}

function pad(value: number): string {
  return String(value).padStart(2, '0');
}

function minutesToText(minutes: number): string {
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  if (!hours && !mins) return '0год';
  if (!mins) return `${hours}год`;
  return `${hours}год ${mins}хв`;
}

function signedMinutesToText(minutes: number): string {
  if (minutes === 0) return '0год';
  return `${minutes > 0 ? '+' : '-'}${minutesToText(Math.abs(minutes))}`;
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat('uk-UA', { day: '2-digit', month: '2-digit', year: 'numeric' }).format(
    new Date(`${value}T00:00:00`),
  );
}

function formatGender(value: string): string {
  const labels: Record<string, string> = {
    female: 'Жінка',
    male: 'Чоловік',
  };
  return labels[value] ?? value;
}

function formatTenure(hiredOn: string | null): string {
  if (!hiredOn) return '-';
  const start = new Date(`${hiredOn}T00:00:00`);
  const now = new Date();
  let months = (now.getFullYear() - start.getFullYear()) * 12 + now.getMonth() - start.getMonth();
  if (now.getDate() < start.getDate()) months -= 1;
  if (months < 0) return '-';
  const years = Math.floor(months / 12);
  const restMonths = months % 12;
  return [years ? `${years} р.` : '', restMonths ? `${restMonths} міс.` : ''].filter(Boolean).join(' ') || 'менше місяця';
}

function peopleforceFieldValue(employee: EmployeeListItem | null, key: string): string {
  const field = employee?.peopleforce_fields[key];
  if (!field) return '';
  if (typeof field === 'object' && 'value' in field) {
    const value = (field as { value?: unknown }).value;
    return value == null ? '' : String(value).trim();
  }
  return String(field).trim();
}

function formatDateTime(value: string | null): string {
  if (!value) return '-';
  return new Intl.DateTimeFormat('uk-UA', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value));
}

function formatTime(value: string | null): string {
  if (!value) return '-';
  return new Intl.DateTimeFormat('uk-UA', { hour: '2-digit', minute: '2-digit' }).format(new Date(value));
}

function isoDateTimeToTimeInput(value: string | null): string {
  if (!value) return '';
  const date = new Date(value);
  return `${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function attendancePeriodFormFromPeriod(period?: EmployeeAttendancePeriod | null): AttendancePeriodFormState {
  return {
    start_time: period ? isoDateTimeToTimeInput(period.start_at) : '09:00',
    end_time: period ? isoDateTimeToTimeInput(period.end_at) : '18:00',
    comment: period?.comment || '',
  };
}

function sanitizeKnowledgeHtml(html: string): string {
  if (!html.trim() || typeof DOMParser === 'undefined') return '';
  const parser = new DOMParser();
  const document = parser.parseFromString(html, 'text/html');
  document.querySelectorAll('script,style,iframe,object,embed,form,input,button,textarea,select').forEach((node) => node.remove());
  document.body.querySelectorAll('*').forEach((node) => {
    Array.from(node.attributes).forEach((attribute) => {
      const name = attribute.name.toLowerCase();
      const value = attribute.value;
      if (name.startsWith('on') || name === 'style' || name === 'srcdoc') {
        node.removeAttribute(attribute.name);
        return;
      }
      if (node.tagName.toLowerCase() === 'a' && name === 'href') {
        if (/^(https?:|mailto:|tel:)/i.test(value)) {
          node.setAttribute('target', '_blank');
          node.setAttribute('rel', 'noopener noreferrer');
        } else {
          node.removeAttribute(attribute.name);
        }
        return;
      }
      if (node.tagName.toLowerCase() === 'a' && ['target', 'rel', 'name', 'size'].includes(name)) return;
      if (name === 'class' && value.split(/\s+/).every((item) => /^kb-[a-z0-9-]+$/.test(item))) return;
      if (node.tagName.toLowerCase() === 'img' && name === 'src' && /^(https?:|\/media\/)/i.test(value)) return;
      if (node.tagName.toLowerCase() === 'img' && name === 'alt') return;
      if (node.tagName.toLowerCase() === 'video' && ['src', 'poster'].includes(name) && /^(https?:|\/media\/)/i.test(value)) return;
      if (node.tagName.toLowerCase() === 'video' && ['controls', 'preload', 'playsinline'].includes(name)) return;
      if (['dir', 'type'].includes(name)) return;
      node.removeAttribute(attribute.name);
    });
  });
  return document.body.innerHTML;
}

function decodeKnowledgeText(value: string): string {
  return value
    .replace(/\\xa0/g, ' ')
    .replace(/\\u200b/g, '')
    .replace(/\\n/g, '\n')
    .replace(/\\'/g, "'")
    .trim();
}

function extractKnowledgeText(body: string): string[] {
  if (!body || body === '{}') return [];
  const matches = Array.from(body.matchAll(/['"]text['"]:\s*['"]([^'"]+)['"]/g));
  return matches.map((match) => decodeKnowledgeText(match[1])).filter(Boolean).slice(0, 80);
}

function extractKnowledgeLinks(body: string): Array<{ href: string; label: string }> {
  if (!body) return [];
  const links: Array<{ href: string; label: string }> = [];
  Array.from(body.matchAll(/['"]src['"]:\s*['"]([^'"]+)['"][\s\S]{0,240}?['"]name['"]:\s*['"]([^'"]+)['"]/g)).forEach(
    (match) => {
      links.push({ href: match[1], label: decodeKnowledgeText(match[2]) });
    },
  );
  Array.from(body.matchAll(/['"]href['"]:\s*['"]([^'"]+)['"]/g)).forEach((match) => {
    const href = decodeKnowledgeText(match[1]);
    if (!links.some((link) => link.href === href)) links.push({ href, label: href });
  });
  return links.slice(0, 20);
}

function isImportedKnowledgeBody(body: string): boolean {
  const trimmed = body.trim();
  return !trimmed || trimmed === '{}' || trimmed === '[]' || trimmed.startsWith("{'type':") || trimmed.startsWith('{"type":');
}

function extractKnowledgeHtmlEditorText(html: string): string {
  if (!html.trim()) return '';
  if (typeof DOMParser === 'undefined') {
    return decodeKnowledgeText(html.replace(/<br\s*\/?>/gi, '\n').replace(/<[^>]+>/g, '\n'))
      .split('\n')
      .map((line) => line.trim())
      .filter(Boolean)
      .join('\n\n');
  }

  const parser = new DOMParser();
  const document = parser.parseFromString(html, 'text/html');
  document.querySelectorAll('script,style,iframe,object,embed,form,input,button,textarea,select').forEach((node) => node.remove());
  const blocks: string[] = [];
  document.body.querySelectorAll('a, h1, h2, h3, p, li, blockquote').forEach((node) => {
    const tag = node.tagName.toLowerCase();
    const text = decodeKnowledgeText(node.textContent || '').replace(/\s+/g, ' ').trim();
    if (!text) return;
    if (tag === 'a') {
      const href = node.getAttribute('href') || '';
      blocks.push(href ? `[${text}](${href})` : text);
      return;
    }
    if (tag === 'h1') blocks.push(`# ${text}`);
    else if (tag === 'h2' || tag === 'h3') blocks.push(`## ${text}`);
    else if (tag === 'li') blocks.push(`- ${text}`);
    else if (tag === 'blockquote') blocks.push(`> ${text}`);
    else blocks.push(text);
  });

  return Array.from(new Set(blocks)).join('\n\n');
}

function editableKnowledgeBody(document: KnowledgeDocument): string {
  if (document.body && !isImportedKnowledgeBody(document.body)) return document.body;

  const bodyLinks = extractKnowledgeLinks(document.body).map((link) => `[${link.label}](${link.href})`);
  const bodyText = extractKnowledgeText(document.body);
  const richBody = [...bodyLinks, ...bodyText].filter(Boolean).join('\n\n');
  if (richBody) return richBody;

  return extractKnowledgeHtmlEditorText(document.body_html);
}

function knowledgeEditorDraftFromDocument(document: KnowledgeDocument): KnowledgeEditorDraft {
  return {
    id: document.id,
    category: document.category,
    title: document.title,
    summary: document.summary,
    cover_url: document.cover_url,
    body: editableKnowledgeBody(document),
    status: document.status,
    created_at: document.created_at,
    updated_at: document.updated_at,
    owner_name: document.owner_name || '',
    view_count: document.view_count || 0,
  };
}

function knowledgeEditorErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 401 || error.status === 403) {
      return 'Не вдалося зберегти сторінку: потрібна авторизація або увімкнений dev-доступ HR_PUBLIC_WRITE_API.';
    }
    return `Не вдалося зберегти сторінку: ${error.message}`;
  }
  return 'Не вдалося зберегти сторінку. Перевірте авторизацію адміністратора.';
}

function getMonthDays(year: number, monthIndex: number): string[] {
  const days = new Date(year, monthIndex + 1, 0).getDate();
  return Array.from({ length: days }, (_, index) => `${year}-${pad(monthIndex + 1)}-${pad(index + 1)}`);
}

function getInitialMonth(): Date {
  const now = new Date();
  return new Date(now.getFullYear(), now.getMonth(), 1);
}

function getMonthRange(month: Date): { from: string; to: string } {
  const year = month.getFullYear();
  const monthIndex = month.getMonth();
  const lastDay = new Date(year, monthIndex + 1, 0).getDate();
  return {
    from: `${year}-${pad(monthIndex + 1)}-01`,
    to: `${year}-${pad(monthIndex + 1)}-${pad(lastDay)}`,
  };
}

function dateLocaleForCopy(copy?: AppCopy): string {
  if (copy?.nav.settings === 'Ustawienia') return 'pl-PL';
  if (copy?.nav.settings === 'Settings') return 'en-US';
  return 'uk-UA';
}

function formatMonthTitle(month: Date, copy?: AppCopy): string {
  const title = new Intl.DateTimeFormat(dateLocaleForCopy(copy), { month: 'short', year: 'numeric' })
    .format(month)
    .replace(' р.', '');
  return `${title.charAt(0).toUpperCase()}${title.slice(1)}`;
}

const employeeAccentClasses = ['violet', 'blue', 'green', 'teal', 'amber', 'rose', 'slate'];

function employeeToPerson(employee: EmployeeListItem, index: number, copy?: AppCopy): Person {
  const specialties = Array.isArray(employee.medical_specialty_names) ? employee.medical_specialty_names : [];
  return {
    id: employee.id,
    fullName: employee.full_name || `${employee.last_name} ${employee.first_name}`.trim(),
    role: employee.position_name || specialties.join(', ') || copy?.people.noPosition || 'Без посади',
    department: employee.department_name || employee.division_name || copy?.people.noDepartment || 'Без департаменту',
    location: employee.clinic_name ? compactLocationName(employee.clinic_name) : copy?.people.noLocation || 'Без локації',
    manager: employee.manager_name || copy?.people.noManager || '-',
    startDate: employee.hired_on ? formatDate(employee.hired_on) : '-',
    email: employee.email || employee.personal_email || '-',
    phone: employee.phone || employee.phone2 || '',
    avatarUrl: employeeAvatarUrl(employee),
    accent: employeeAccentClasses[index % employeeAccentClasses.length],
    directReportsCount: Number(employee.direct_reports_count || 0),
    employee,
  };
}

function namedFilterOptions<T extends { id: number; name: string; employee_count?: number; department_count?: number; member_count?: number }>(
  items: T[],
): PeopleFilterOption[] {
  return items
    .map((item) => ({
      value: String(item.id),
      label: item.name,
      count: item.employee_count ?? item.department_count ?? item.member_count,
    }))
    .sort((first, second) => first.label.localeCompare(second.label, 'uk'));
}

function countActivePeopleFilters(filters: PeopleFilterState): number {
  return Object.entries(filters).reduce((count, [key, value]) => {
    if (Array.isArray(value)) return count + value.length;
    if (!value) return count;
    if (key === 'status' && value === defaultPeopleFilters.status) return count;
    return count + 1;
  }, 0);
}

function peopleFilterParam(values: string[]): string {
  return values.join(',');
}

function peopleFilterSelectionLabel(values: string[], options: PeopleFilterOption[], placeholder: string): string {
  if (!values.length) return placeholder;
  if (values.length === 1) return options.find((option) => option.value === values[0])?.label ?? placeholder;
  return `${values.length} вибрано`;
}

function peopleStatusLabel(status: string): string {
  if (status === 'active') return 'Працюючі';
  if (status === 'on_leave') return 'У відпустці';
  if (status === 'dismissed') return 'Звільнені';
  if (status === 'suspended') return 'Призупинені';
  return 'Усі статуси';
}

function employeeAvatarUrl(employee: Pick<EmployeeListItem, 'avatar_local_url' | 'avatar_url'> | null | undefined): string {
  if (employee?.avatar_local_url) return employee.avatar_local_url;
  const externalUrl = employee?.avatar_url || '';
  return externalUrl.includes('default_employee_thumbnail') || externalUrl.includes('default_employee_avatar') ? '' : externalUrl;
}

function compactLocationName(value: string): string {
  const trimmed = value.trim();
  const parenthesized = trimmed.match(/\(([^)]+)\)\s*$/);
  if (parenthesized?.[1]) return parenthesized[1];
  return trimmed.replace(/^vidnova\s+clinic\s*/i, '').trim() || trimmed;
}

function attendanceSummaryToRow(row: CompanyAttendanceSummary): AttendanceSummaryRow {
  return {
    id: row.id,
    employeeId: row.employee,
    fullName: row.employee_name,
    expected: minutesToText(row.planned_minutes),
    worked: minutesToText(row.actual_minutes),
    overtime: minutesToText(row.overtime_minutes),
    breakTime: minutesToText(row.break_minutes),
    paidAbsence: minutesToText(row.paid_absence_minutes),
    unpaidAbsence: minutesToText(row.unpaid_absence_minutes),
    totalAbsence: minutesToText(row.total_absence_minutes),
    difference: signedMinutesToText(row.difference_minutes),
  };
}

function navLabel(copy: AppCopy, section: Section): string {
  return copy.nav[section] ?? section;
}

function bottomNavLabel(copy: AppCopy, section: Section): string {
  const label = navLabel(copy, section);
  if (section !== 'home') return label;
  return label.replace(/\s+(сторінка|page|główna)$/i, '');
}

function copyValue(value: string | string[] | undefined, fallback: string): string {
  return typeof value === 'string' ? value : fallback;
}

function copyArray(value: string | string[] | undefined, fallback: string[]): string[] {
  return Array.isArray(value) ? value : fallback;
}

function interpolate(template: string, values: Record<string, string | number>): string {
  return Object.entries(values).reduce((current, [key, value]) => current.split(`{${key}}`).join(String(value)), template);
}

function resultMetaLabel(visibleCount: number, totalCount: number, copy?: AppCopy): string {
  const labels = copy?.common;
  if (!visibleCount) return interpolate(labels?.resultMetaZero ?? 'Відображено 0 з {total}', { total: totalCount });
  return interpolate(labels?.resultMetaRange ?? 'Відображено 1-{visible} з {total}', { visible: visibleCount, total: totalCount });
}

// Page numbers with gaps, e.g. 1 2 … 5 6 7 … 11 12.
function buildPageItems(current: number, total: number): Array<number | 'gap'> {
  if (total <= 7) return Array.from({ length: total }, (_, index) => index + 1);
  const pages = new Set<number>([1, 2, total - 1, total, current - 1, current, current + 1]);
  const sorted = [...pages].filter((page) => page >= 1 && page <= total).sort((a, b) => a - b);
  const items: Array<number | 'gap'> = [];
  let previous = 0;
  for (const page of sorted) {
    if (page - previous > 1) items.push('gap');
    items.push(page);
    previous = page;
  }
  return items;
}

function leaveAmountLabel(value?: string, unit?: string): string {
  if (!value) return '';
  const normalized = Number(value);
  const amount = Number.isFinite(normalized) ? normalized.toLocaleString('uk-UA', { maximumFractionDigits: 2 }) : value;
  return `${amount} ${unit === 'hours' ? 'год' : 'дн.'}`;
}

function readBrandingSettings(): BrandingSettings {
  if (typeof window === 'undefined') return defaultBrandingSettings;
  try {
    const raw = window.localStorage.getItem(brandingStorageKey);
    if (!raw) return defaultBrandingSettings;
    const parsed = JSON.parse(raw) as Partial<BrandingSettings>;
    return {
      ...defaultBrandingSettings,
      ...parsed,
      language: normalizeLanguage(parsed.language),
      theme: normalizeTheme(parsed.theme),
    };
  } catch {
    return defaultBrandingSettings;
  }
}

function saveBrandingSettings(settings: BrandingSettings) {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(brandingStorageKey, JSON.stringify(settings));
  } catch {
    // Large local image previews may exceed browser storage; keep current session state in that case.
  }
}

function readEmployeeCovers(): EmployeeCoverMap {
  if (typeof window === 'undefined') return {};
  try {
    const raw = window.localStorage.getItem(employeeCoverStorageKey);
    if (!raw) return {};
    const parsed = JSON.parse(raw) as EmployeeCoverMap;
    return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : {};
  } catch {
    return {};
  }
}

function saveEmployeeCovers(covers: EmployeeCoverMap) {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(employeeCoverStorageKey, JSON.stringify(covers));
  } catch {
    // Keep current session state if browser storage is full.
  }
}

function formatBytes(bytes: number): string {
  if (!bytes) return '';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function createFallbackWorkdays(): WorkDaySummary[] {
  return [];
}

function createFallbackAttendance(): SelfAttendance {
  return {
    employee: fallbackEmployee,
    range: { from: '2026-06-01', to: '2026-06-30' },
    workdays: createFallbackWorkdays(),
    events: [],
    correction_requests: [],
  };
}

const fallbackAttendance = createFallbackAttendance();

function initials(name: string): string {
  return name
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join('')
    .toUpperCase();
}

function statusLabel(status: string): string {
  const labels: Record<string, string> = {
    active: 'Активний',
    submitted: 'Очікує',
    approved: 'Погоджено',
    rejected: 'Відхилено',
    cancelled: 'Скасовано',
    applied: 'Застосовано',
    ok: 'OK',
    absent: 'Відсутність',
    late: 'Запізнення',
    manual_review: 'Перевірка',
    missing_entry: 'Немає входу',
    missing_exit: 'Немає виходу',
  };
  return labels[status] ?? status;
}

function StatusPill({ status }: { status: string }) {
  const tone = ['approved', 'applied', 'ok', 'active'].includes(status)
    ? 'ok'
    : ['rejected', 'absent', 'failed'].includes(status)
      ? 'bad'
      : 'warn';
  return <span className={`status-pill ${tone}`}>{statusLabel(status)}</span>;
}

function Avatar({
  name,
  src = '',
  accent = 'violet',
  size = 'default',
}: {
  name: string;
  src?: string;
  accent?: string;
  size?: 'default' | 'sm' | 'lg';
}) {
  const [failed, setFailed] = useState(false);
  const showImage = Boolean(src && !failed);

  return (
    <span className={`avatar ${accent} ${size} ${showImage ? 'image' : ''}`}>
      {showImage ? <img src={src} alt="" loading="lazy" onError={() => setFailed(true)} /> : initials(name) || 'V'}
    </span>
  );
}

function BrandMark({ brandingSettings }: { brandingSettings?: BrandingSettings }) {
  const logoUrl = brandingSettings?.logoPreviewUrl || '';
  return (
    <div className={`brand-mark ${logoUrl ? 'image-logo' : ''}`} aria-label="Vidnova HR">
      {logoUrl ? (
        <img src={logoUrl} alt="" />
      ) : (
        <>
          <span />
          <strong>VIDNOVA</strong>
        </>
      )}
    </div>
  );
}

function Sidebar({
  active,
  onChange,
  brandingSettings,
  copy,
}: {
  active: Section;
  onChange: (section: Section) => void;
  brandingSettings: BrandingSettings;
  copy: AppCopy;
}) {
  return (
    <aside className="sidebar" aria-label={copy.common.openMenu}>
      <BrandMark brandingSettings={brandingSettings} />
      <label className="global-search">
        <Search size={18} />
        <input type="search" placeholder={copy.common.search} />
        <kbd>Ctrl + K</kbd>
      </label>
      <nav className="nav-list">
        {sidebarItems.map((item, index) => {
          const Icon = item.icon;
          const activeItem = active === item.section || (active === 'org' && item.section === 'people');
          return (
            <button
              key={item.section}
              type="button"
              className={`nav-button ${activeItem ? 'active' : ''} ${index === 2 ? 'group-start' : ''}`}
              onClick={() => onChange(item.section)}
            >
              <Icon size={18} strokeWidth={2.25} />
              <span>{navLabel(copy, item.section)}</span>
              {item.badge ? <em>{item.badge}</em> : null}
              {item.expandable ? <ChevronRight size={15} className="nav-caret" /> : null}
            </button>
          );
        })}
      </nav>
      <button type="button" className={`settings-link ${active === 'settings' ? 'active' : ''}`} onClick={() => onChange('settings')}>
        <Settings size={18} />
        <span>{copy.common.settings}</span>
        <PanelLeftClose size={18} />
      </button>
      <button
        type="button"
        className={`sidebar-version ${active === 'changelog' ? 'active' : ''}`}
        onClick={() => onChange('changelog')}
        title="Історія версій"
      >
        <span className="sidebar-version-date">{APP_VERSION_DATE}</span>
        <strong className="sidebar-version-num">v{APP_VERSION}</strong>
      </button>
    </aside>
  );
}

// Shared overlay dismissal: Escape-to-close + body scroll-lock while open.
// onClose is read via ref so the effect only re-runs when `open` changes.
function useOverlayDismiss(open: boolean, onClose: () => void) {
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;
  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onCloseRef.current();
    };
    document.addEventListener('keydown', onKey);
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = prevOverflow;
    };
  }, [open]);
}

function MobileMenu({
  active,
  isOpen,
  onChange,
  onClose,
  brandingSettings,
  copy,
}: {
  active: Section;
  isOpen: boolean;
  onChange: (section: Section) => void;
  onClose: () => void;
  brandingSettings: BrandingSettings;
  copy: AppCopy;
}) {
  useOverlayDismiss(isOpen, onClose);
  if (!isOpen) return null;

  return (
    <div className="mobile-menu-layer" role="dialog" aria-modal="true" aria-label={copy.common.openMenu}>
      <button type="button" className="mobile-menu-backdrop" aria-label={copy.common.closeMenu} onClick={onClose} />
      <aside className="mobile-menu-panel">
        <div className="mobile-menu-head">
          <BrandMark brandingSettings={brandingSettings} />
          <button type="button" className="icon-button" aria-label={copy.common.closeMenu} onClick={onClose}>
            <X size={18} />
          </button>
        </div>
        <nav className="nav-list">
          {sidebarItems.map((item, index) => {
            const Icon = item.icon;
            const activeItem = active === item.section || (active === 'org' && item.section === 'people');
            return (
              <button
                key={item.section}
                type="button"
                className={`nav-button ${activeItem ? 'active' : ''} ${index === 2 ? 'group-start' : ''}`}
                onClick={() => onChange(item.section)}
              >
                <Icon size={18} strokeWidth={2.25} />
                <span>{navLabel(copy, item.section)}</span>
                {item.badge ? <em>{item.badge}</em> : null}
                {item.expandable ? <ChevronRight size={15} className="nav-caret" /> : null}
              </button>
            );
          })}
        </nav>
        <button type="button" className={`settings-link ${active === 'settings' ? 'active' : ''}`} onClick={() => onChange('settings')}>
          <Settings size={18} />
          <span>{copy.common.settings}</span>
          <PanelLeftClose size={18} />
        </button>
      </aside>
    </div>
  );
}

function Topbar({
  auth,
  employee,
  onOpenMobileMenu,
  onLogout,
  copy,
}: {
  auth: AuthStatus | null;
  employee: EmployeeProfile;
  onOpenMobileMenu: () => void;
  onLogout: () => void;
  copy: AppCopy;
}) {
  return (
    <header className="topbar">
      <div className="topbar-left">
        <button type="button" className="icon-button mobile-menu-button" aria-label={copy.common.openMenu} onClick={onOpenMobileMenu}>
          <Menu size={18} />
        </button>
      </div>
      <div className="top-actions">
        <button type="button" className="icon-button" aria-label={copy.common.timeTracking}>
          <Timer size={18} />
        </button>
        <button type="button" className="quick-add">
          <Plus size={18} />
          <span>{copy.common.quickAdd}</span>
        </button>
        <button type="button" className="icon-button with-badge" aria-label={navLabel(copy, 'notifications')}>
          <Bell size={18} />
          <span>5</span>
        </button>
        <button type="button" className="user-menu" onClick={onLogout} title="Вийти">
          <Avatar name={employee.full_name || copy.common.user} src={employee.avatar_local_url || ''} accent="teal" size="sm" />
          <strong>{employee.full_name || auth?.user?.username || copy.common.user}</strong>
          <LogOut size={16} />
        </button>
      </div>
    </header>
  );
}

type LoginStep = 'phone' | 'code';

const authModules: Array<{ title: string; text: string; icon: LucideIcon }> = [
  {
    title: 'Облік часу',
    text: 'Дані зі СКУД, зміни, запізнення та присутність.',
    icon: Clock3,
  },
  {
    title: 'Відпустки',
    text: 'Заявки керівнику, погодження та історія рішень.',
    icon: CalendarCheck,
  },
  {
    title: 'База знань',
    text: 'Інструкції, правила, документи та внутрішні процеси.',
    icon: BookOpen,
  },
  {
    title: 'Оргструктура',
    text: 'Візуальний граф керівників, відділів і ролей.',
    icon: Network,
  },
];

function LoginView({
  brandingSettings,
  onSuccess,
}: {
  brandingSettings: BrandingSettings;
  onSuccess: (response: AuthLoginResponse) => Promise<void>;
}) {
  const [step, setStep] = useState<LoginStep>('phone');
  const [phone, setPhone] = useState('');
  const [code, setCode] = useState('');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [resendAvailableAt, setResendAvailableAt] = useState(0);
  const [nowTick, setNowTick] = useState(() => Date.now());

  useEffect(() => {
    if (step !== 'code') return undefined;
    setNowTick(Date.now());
    const intervalId = window.setInterval(() => setNowTick(Date.now()), 1000);
    return () => window.clearInterval(intervalId);
  }, [step, resendAvailableAt]);

  async function requestCode(normalizedPhone: string, successMessage: string) {
    setBusy(true);
    setError('');
    setMessage('');
    try {
      await api.requestLoginCode(normalizedPhone);
      setStep('code');
      setMessage(successMessage);
      setResendAvailableAt(Date.now() + LOGIN_CODE_RESEND_DELAY_SECONDS * 1000);
    } catch (err) {
      if (err instanceof ApiError && err.status === 429) {
        setError('Забагато запитів. Спробуйте пізніше');
      } else {
        setError('Не вдалося запитати код');
      }
    } finally {
      setBusy(false);
    }
  }

  async function submitPhone(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalizedPhone = phone.trim();
    if (!normalizedPhone) {
      setError('Вкажіть телефон');
      return;
    }
    await requestCode(normalizedPhone, 'Перевірте Telegram або відкрийте бота за QR');
  }

  async function submitCode(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const cleanCode = code.trim();
    if (cleanCode.length < 6) {
      setError('Вкажіть 6-значний код');
      return;
    }
    setBusy(true);
    setError('');
    try {
      const response = await api.verifyLoginCode(phone.trim(), cleanCode);
      await onSuccess(response);
    } catch (err) {
      if (err instanceof ApiError && err.status === 429) {
        setError('Забагато спроб. Спробуйте пізніше');
      } else if (err instanceof ApiError && err.status === 400) {
        setError('Код недійсний або прострочений');
      } else {
        setError('Невірний код');
      }
    } finally {
      setBusy(false);
    }
  }

  function backToPhone() {
    setStep('phone');
    setCode('');
    setError('');
    setMessage('');
    setResendAvailableAt(0);
  }

  async function resendCode() {
    if (busy || resendRemaining > 0) return;
    setCode('');
    await requestCode(phone.trim(), 'Надіслали новий код у Telegram');
  }

  const isPhoneStep = step === 'phone';
  const resendRemaining = isPhoneStep ? 0 : Math.max(0, Math.ceil((resendAvailableAt - nowTick) / 1000));
  const loginDescription = isPhoneStep
    ? 'Введіть номер телефону. Якщо профіль знайдено, ми надішлемо код підтвердження в Telegram.'
    : 'Введіть код із Telegram. QR нижче веде в єдиного бота Vidnova для HR і Clinical Photo.';

  return (
    <div className="auth-shell" data-theme={normalizeTheme(brandingSettings.theme)} style={brandingThemeStyle(brandingSettings)}>
      <header className="auth-header">
        <div className="auth-logo">
          <BrandMark brandingSettings={brandingSettings} />
          <span>HR</span>
        </div>
        <p>
          Підтримка: <strong>IT / HR відділ</strong>
        </p>
      </header>

      <main className="auth-layout" aria-label="Вхід">
        <section className="auth-hero" aria-label="Про HR Vidnova">
          <div className="auth-hero-pattern" />
          <div className="auth-hero-content">
            <span className="auth-eyebrow">
              <ShieldCheck size={16} />
              Внутрішня система клініки
            </span>
            <div className="auth-hero-copy">
              <h1>Керування персоналом без хаосу</h1>
              <p>
                Єдиний простір для робочого часу, заявок на відпустку, бази знань
                і зрозумілої структури підпорядкування.
              </p>
            </div>
            <div className="auth-modules" aria-label="Модулі системи">
              {authModules.map((module) => {
                const Icon = module.icon;
                return (
                  <article className="auth-module" key={module.title}>
                    <span>
                      <Icon size={18} />
                    </span>
                    <div>
                      <strong>{module.title}</strong>
                      <p>{module.text}</p>
                    </div>
                  </article>
                );
              })}
            </div>
          </div>
        </section>

        <section className="auth-panel">
          <div className="auth-status">
            <ShieldCheck size={15} />
            <span>Захищений вхід</span>
          </div>
          <div className="auth-title">
            <h2>Увійдіть у кабінет</h2>
            <p>{loginDescription}</p>
          </div>

          {isPhoneStep ? (
            <form className="auth-form" onSubmit={submitPhone}>
              <label className={`auth-field ${error ? 'invalid' : ''}`}>
                <span>Номер телефону</span>
                <div>
                  <Phone size={18} />
                  <input
                    type="tel"
                    inputMode="tel"
                    value={phone}
                    onChange={(event) => {
                      setPhone(event.target.value);
                      if (error) setError('');
                    }}
                    placeholder="380 67 000 00 00"
                    autoComplete="tel"
                    aria-invalid={Boolean(error)}
                  />
                </div>
              </label>
              {error ? <p className="auth-error">{error}</p> : null}
              <button type="submit" className="primary-action auth-submit" disabled={busy}>
                <ShieldCheck size={18} />
                <span>{busy ? 'Надсилаємо код...' : 'Отримати код'}</span>
              </button>
            </form>
          ) : (
            <form className="auth-form" onSubmit={submitCode}>
              <div className="auth-telegram">
                <a
                  href={TELEGRAM_BOT_URL}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="auth-qr-link"
                  title="Відкрити Telegram-бот"
                  aria-label="Відкрити Telegram-бот Clinical Photo"
                >
                  <QRCodeSVG value={TELEGRAM_BOT_URL} size={126} level="M" marginSize={1} />
                </a>
                <div className="auth-telegram-copy">
                  <span>Clinical Photo</span>
                  <p>Скануйте QR або натисніть на нього, щоб перейти в Telegram-бот.</p>
                </div>
              </div>
              <label className={`auth-field ${error ? 'invalid' : ''}`}>
                <span>Код підтвердження</span>
                <div>
                  <Lock size={18} />
                  <input
                    type="text"
                    inputMode="numeric"
                    pattern="[0-9]*"
                    maxLength={6}
                    value={code}
                    onChange={(event) => {
                      setCode(event.target.value.replace(/\D/g, '').slice(0, 6));
                      if (error) setError('');
                    }}
                    placeholder="000000"
                    autoComplete="one-time-code"
                    aria-invalid={Boolean(error)}
                  />
                </div>
              </label>
              {message && !error ? <p className="auth-message">{message}</p> : null}
              {error ? <p className="auth-error">{error}</p> : null}
              <div className="auth-resend-row" aria-live="polite">
                <button type="button" className="auth-resend" onClick={resendCode} disabled={busy || resendRemaining > 0}>
                  <Timer size={16} />
                  <span>{resendRemaining > 0 ? `Повторно через ${resendRemaining} с` : 'Надіслати код ще раз'}</span>
                </button>
              </div>
              <div className="auth-actions">
                <button type="button" className="secondary-action" onClick={backToPhone} disabled={busy}>
                  <ChevronLeft size={17} />
                  <span>Назад</span>
                </button>
                <button type="submit" className="primary-action auth-submit" disabled={busy}>
                  <Check size={18} />
                  <span>{busy ? 'Перевіряємо...' : 'Увійти'}</span>
                </button>
              </div>
            </form>
          )}

          <div className="auth-security">
            <strong>Доступ лише для співробітників.</strong>
            <span>Якщо номер не розпізнано, зверніться до HR або адміністратора системи.</span>
          </div>
        </section>
      </main>
    </div>
  );
}

function AuthLoadingView({ brandingSettings }: { brandingSettings: BrandingSettings }) {
  return (
    <div className="auth-shell" data-theme={normalizeTheme(brandingSettings.theme)} style={brandingThemeStyle(brandingSettings)}>
      <header className="auth-header">
        <div className="auth-logo">
          <BrandMark brandingSettings={brandingSettings} />
          <span>HR</span>
        </div>
        <p>
          Підтримка: <strong>IT / HR відділ</strong>
        </p>
      </header>
      <main className="auth-layout loading" aria-label="Завантаження">
        <section className="auth-panel loading">
          <BrandMark brandingSettings={brandingSettings} />
          <div className="auth-title">
            <h2>HR Vidnova</h2>
            <p>Перевірка сесії</p>
          </div>
        </section>
      </main>
    </div>
  );
}

function SectionTabs({
  tabs,
  active,
  onChange,
}: {
  tabs: Array<{ key: string; label: string }>;
  active: string;
  onChange: (key: string) => void;
}) {
  return (
    <div className="section-tabs">
      {tabs.map((tab) => (
        <button type="button" key={tab.key} className={active === tab.key ? 'active' : ''} onClick={() => onChange(tab.key)}>
          {tab.label}
        </button>
      ))}
    </div>
  );
}

function EmptyState({ title, text }: { title: string; text?: string }) {
  return (
    <div className="empty-state">
      <strong>{title}</strong>
      {text ? <span>{text}</span> : null}
    </div>
  );
}

function HomeView({
  employee,
  leaveRequests,
  onOpenLeave,
  onOpenAttendance,
  onOpenKnowledge,
  onOpenOrg,
  brandingSettings,
  copy,
}: {
  employee: EmployeeProfile;
  leaveRequests: LeaveRequest[];
  onOpenLeave: () => void;
  onOpenAttendance: () => void;
  onOpenKnowledge: () => void;
  onOpenOrg: () => void;
  brandingSettings: BrandingSettings;
  copy: AppCopy;
}) {
  return (
    <main className="home-page">
      {!brandingSettings.homeCoverDisabled ? (
        <section
          className="brand-banner"
          aria-label="Vidnova Clinic"
          style={{ backgroundImage: `url("${brandingSettings.homeCoverUrl}")` }}
        />
      ) : null}

      <section className="home-welcome">
        <div className="welcome-person">
          <Avatar name={employee.full_name} accent="teal" size="lg" />
          <div>
            <h1>{copy.home.greeting}, {employee.full_name}</h1>
            <div className="quick-chips">
              <button type="button" onClick={onOpenLeave}>
                <CalendarCheck size={16} />
                {copy.home.requestTimeOff}
              </button>
              <button type="button" onClick={onOpenAttendance}>
                <Clock3 size={16} />
                {copy.home.time}
              </button>
            </div>
          </div>
        </div>
        <div className="welcome-actions">
          <button type="button" className="primary-action">
            <MegaphoneIcon />
            {copy.home.createAnnouncement}
          </button>
        </div>
      </section>

      <div className="home-content">
        <div className="home-main">
          <section className="panel tasks-panel">
            <div className="panel-title">
              <h2>{copy.home.tasks}</h2>
              <button type="button">{copy.home.viewInbox}</button>
            </div>
            <EmptyState title={copy.home.noTasksTitle} text={copy.home.noTasksText} />
          </section>

          <article className="feed-post">
            <EmptyState title={copy.home.noAnnouncementsTitle} text={copy.home.noAnnouncementsText} />
          </article>
        </div>

        <aside className="home-aside">
          <section className="panel leave-widget">
            <div className="widget-title">
              <div>
                <CalendarCheck size={19} />
                <h2>{copy.home.leave}</h2>
              </div>
            </div>
            <strong>-</strong>
            <p>{copy.home.availableDaysMissing}</p>
            <div className="widget-actions">
              <button type="button" onClick={onOpenLeave}>
                {copy.home.requestTimeOff}
              </button>
              <button type="button" aria-label={copy.home.calendar}>
                <Calendar size={15} />
              </button>
            </div>
            {leaveRequests.length ? (
              leaveRequests.slice(0, 1).map((item) => (
                <div className="mini-request" key={item.id}>
                  <span>
                    {formatDate(item.date_from)} - {formatDate(item.date_to)}
                  </span>
                  <StatusPill status={item.status} />
                </div>
              ))
            ) : (
              <EmptyState title={copy.home.noRequestsTitle} text={copy.home.noRequestsText} />
            )}
          </section>

          <section className="panel week-widget">
            <div className="widget-title">
              <div>
                <Calendar size={19} />
                <h2>{copy.home.plannedEvents}</h2>
              </div>
            </div>
            <div className="week-strip">
              {['24', '25', '26', '27', '28', '29', '30'].map((day, index) => (
                <span key={day} className={index === 0 ? 'active' : index === 3 ? 'marked' : ''}>
                  {day}
                </span>
              ))}
            </div>
            <p>{copy.home.today}</p>
            <small>{copy.home.noEvents}</small>
          </section>

          <section className="panel absent-widget">
            <div className="widget-title">
              <div>
                <Users size={19} />
                <h2>{copy.home.whoIsAbsent}</h2>
              </div>
            </div>
            <div className="absence-counter">
              <strong>0</strong>
              <span>{copy.home.absentCount}</span>
            </div>
          </section>

          <section className="panel links-widget">
            <div className="widget-title">
              <div>
                <Link size={19} />
                <h2>{copy.home.companyLinks}</h2>
              </div>
              <button type="button">{copy.home.manage}</button>
            </div>
            <button type="button" onClick={onOpenKnowledge}>{copy.home.knowledgeLink}</button>
            <button type="button" onClick={onOpenOrg}>{copy.home.orgLink}</button>
          </section>
        </aside>
      </div>
    </main>
  );
}

function MegaphoneIcon() {
  return <Sparkles size={17} />;
}

function optionalNumber(value: string): number | null {
  return value ? Number(value) : null;
}

function emptyNewHireForm(search: string = ''): NewHireFormState {
  const params = new URLSearchParams(search);
  return {
    first_name: '',
    last_name: '',
    middle_name: '',
    personal_email: '',
    email: '',
    phone: '',
    phone2: '',
    birth_date: '',
    gender: '',
    hired_on: todayIsoDate(),
    employment_type: params.get('work_type') || '',
    working_pattern: params.get('working_pattern') || '',
    probation_policy: '',
    position: '',
    department: '',
    division: '',
    clinic: params.get('location') || '',
    manager: '',
    job_level: '',
    medical_specialties: [],
    notes: '',
  };
}

function buildNewHireChoices(options: PeopleFilterOptions): Array<{ id: string; label: string; workType: string; location: string }> {
  const workTypes = options.workTypes.length ? options.workTypes : [{ value: '', label: 'Повна зайнятість' }];
  const locations = options.locations.length ? options.locations : [{ value: '', label: 'Vidnova Clinic' }];
  return workTypes.flatMap((workType) =>
    locations.map((location) => ({
      id: `${workType.value || 'work'}:${location.value || 'location'}`,
      label: `${workType.label} ${location.label}`.trim(),
      workType: workType.value,
      location: location.value,
    })),
  );
}

function newHirePayloadFromForm(form: NewHireFormState): EmployeeHirePayload {
  return {
    first_name: form.first_name.trim(),
    last_name: form.last_name.trim(),
    middle_name: form.middle_name.trim(),
    personal_email: form.personal_email.trim(),
    email: form.email.trim(),
    phone: form.phone.trim(),
    phone2: form.phone2.trim(),
    birth_date: form.birth_date || null,
    gender: form.gender,
    hired_on: form.hired_on || null,
    status: 'active',
    employment_type: optionalNumber(form.employment_type),
    working_pattern: optionalNumber(form.working_pattern),
    probation_policy: optionalNumber(form.probation_policy),
    position: optionalNumber(form.position),
    department: optionalNumber(form.department),
    division: optionalNumber(form.division),
    clinic: optionalNumber(form.clinic),
    manager: optionalNumber(form.manager),
    job_level: optionalNumber(form.job_level),
    medical_specialties: form.medical_specialties.map(Number),
    notes: form.notes.trim(),
  };
}

function newHireOptionLabel<T extends { id: number; name: string }>(items: T[], value: string, fallback = '-'): string {
  if (!value) return fallback;
  return items.find((item) => String(item.id) === value)?.name ?? fallback;
}

function NewHireFormPicker({
  open,
  options,
  optionsState,
  onClose,
  onContinue,
}: {
  open: boolean;
  options: PeopleFilterOptions;
  optionsState: LoadState;
  onClose: () => void;
  onContinue: (choice: { workType: string; location: string }) => void;
}) {
  const choices = useMemo(() => buildNewHireChoices(options), [options]);
  const [selectedId, setSelectedId] = useState('');

  useEffect(() => {
    if (!open) return;
    setSelectedId((current) => current || choices[0]?.id || '');
  }, [choices, open]);

  useEffect(() => {
    if (!open) return undefined;
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') onClose();
    }
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [onClose, open]);

  if (!open) return null;
  const selected = choices.find((choice) => choice.id === selectedId) ?? choices[0];
  const loading = optionsState === 'loading';

  return (
    <div className="settings-option-modal-layer new-hire-picker-layer" role="dialog" aria-modal="true" aria-label="Додати новий найм">
      <button type="button" className="settings-option-modal-backdrop" aria-label="Закрити" onClick={onClose} />
      <section className="settings-option-modal new-hire-picker-modal">
        <header>
          <strong>Додайте новий найм до PeopleForce</strong>
          <button type="button" className="modal-close" aria-label="Закрити" onClick={onClose}>
            <X size={22} />
          </button>
        </header>
        <label>
          <span>Форма</span>
          <select value={selectedId} disabled={loading || !choices.length} onChange={(event) => setSelectedId(event.target.value)}>
            {loading ? <option value="">Завантаження...</option> : null}
            {!loading && !choices.length ? <option value="">Форми не знайдені</option> : null}
            {choices.map((choice) => (
              <option key={choice.id} value={choice.id}>
                {choice.label}
              </option>
            ))}
          </select>
        </label>
        <footer>
          <button type="button" className="secondary-action" onClick={onClose}>
            Скасувати
          </button>
          <button type="button" className="primary-action" disabled={!selected} onClick={() => selected && onContinue(selected)}>
            Далі
            <ChevronRight size={16} />
          </button>
        </footer>
      </section>
    </div>
  );
}

function NewHireFlowView({
  search,
  onBack,
  onCreated,
}: {
  search: string;
  onBack: () => void;
  onCreated: (employee: EmployeeListItem) => void;
}) {
  const [step, setStep] = useState<NewHireStep>('details');
  const [form, setForm] = useState<NewHireFormState>(() => emptyNewHireForm(search));
  const [options, setOptions] = useState<NewHireOptions>(emptyNewHireOptions);
  const [loadState, setLoadState] = useState<LoadState>('idle');
  const [saveState, setSaveState] = useState<LoadState>('idle');
  const [error, setError] = useState('');

  useEffect(() => {
    setForm(emptyNewHireForm(search));
    setStep('details');
    setError('');
  }, [search]);

  useEffect(() => {
    let cancelled = false;
    async function loadOptions() {
      setLoadState('loading');
      try {
        const [positions, departments, divisions, locations, workTypes, workingPatterns, probationPolicies, jobLevels, genders, skills, managers] = await Promise.all([
          api.positions({ is_active: true, page_size: 500 }),
          api.departments({ is_active: true, page_size: 500 }),
          api.divisions({ is_active: true, page_size: 500 }),
          api.locations({ is_active: true, page_size: 500 }),
          api.workTypes({ is_active: true, page_size: 500 }),
          api.workingPatterns({ is_active: true, page_size: 500 }),
          api.probationPolicies({ is_active: true, page_size: 500 }),
          api.jobLevels({ is_active: true, page_size: 500 }),
          api.genders({ is_active: true, page_size: 500 }),
          api.skills({ is_active: true, page_size: 500 }),
          api.employees({ status: 'active', compact: true, page_size: 1000 }),
        ]);
        if (cancelled) return;
        setOptions({
          positions: positions.items,
          departments: departments.items,
          divisions: divisions.items,
          locations: locations.items,
          workTypes: workTypes.items,
          workingPatterns: workingPatterns.items,
          probationPolicies: probationPolicies.items,
          jobLevels: jobLevels.items,
          genders: genders.items,
          skills: skills.items,
          managers: managers.items,
        });
        setLoadState('ok');
      } catch (loadError) {
        if (cancelled) return;
        setOptions(emptyNewHireOptions);
        setError(loadError instanceof ApiError ? loadError.message : 'Не вдалося завантажити довідники.');
        setLoadState('error');
      }
    }
    void loadOptions();
    return () => {
      cancelled = true;
    };
  }, []);

  const detailsValid = Boolean(
    form.last_name.trim() &&
      form.first_name.trim() &&
      form.personal_email.trim() &&
      form.hired_on &&
      form.employment_type &&
      form.clinic &&
      form.manager,
  );
  const titleParts = [
    newHireOptionLabel(options.workTypes, form.employment_type, ''),
    newHireOptionLabel(options.locations, form.clinic, ''),
  ].filter(Boolean);
  const pageTitle = titleParts.length ? titleParts.join(' ') : 'Новий найм';

  function updateForm(patch: Partial<NewHireFormState>) {
    setForm((current) => ({ ...current, ...patch }));
    setError('');
  }

  function selectField<T extends { id: number; name: string }>(
    label: string,
    key: keyof NewHireFormState,
    items: T[],
    placeholder = '-- Немає --',
    required = false,
  ) {
    return (
      <label>
        <span>
          {label}
          {required ? ' *' : ''}
        </span>
        <select value={String(form[key] ?? '')} onChange={(event) => updateForm({ [key]: event.target.value } as Partial<NewHireFormState>)}>
          <option value="">{placeholder}</option>
          {items.map((item) => (
            <option key={item.id} value={item.id}>
              {item.name}
            </option>
          ))}
        </select>
      </label>
    );
  }

  function managerField() {
    return (
      <label>
        <span>Менеджер *</span>
        <select value={form.manager} onChange={(event) => updateForm({ manager: event.target.value })}>
          <option value="">-- Ніхто --</option>
          {options.managers.map((manager) => (
            <option key={manager.id} value={manager.id}>
              {[manager.full_name, manager.position_name, manager.department_name].filter(Boolean).join(' · ')}
            </option>
          ))}
        </select>
      </label>
    );
  }

  function goReview() {
    if (!detailsValid) {
      setError("Заповніть обов'язкові поля: прізвище, ім'я, особиста пошта, дата прийому, тип роботи, локація і менеджер.");
      return;
    }
    setStep('review');
    setError('');
  }

  async function saveHire() {
    if (!detailsValid || saveState === 'loading') {
      goReview();
      return;
    }
    setSaveState('loading');
    setError('');
    try {
      const saved = await api.hireEmployee(newHirePayloadFromForm(form));
      setSaveState('ok');
      onCreated(saved);
    } catch (saveError) {
      setSaveState('error');
      setError(saveError instanceof ApiError ? saveError.message : 'Не вдалося створити співробітника.');
    }
  }

  return (
    <main className="workspace new-hire-page">
      <header className="new-hire-header">
        <button type="button" onClick={onBack}>
          <ChevronLeft size={16} />
          Назад
        </button>
        <h1>{pageTitle}</h1>
      </header>

      <div className="new-hire-tabs">
        <button type="button" className={step === 'details' ? 'active' : ''} onClick={() => setStep('details')}>
          {step === 'review' ? <Check size={16} /> : null}
          Деталі
        </button>
        <button type="button" className={step === 'review' ? 'active' : ''} onClick={goReview}>
          Оцінка
        </button>
      </div>

      {error ? <p className="error-text new-hire-error">{error}</p> : null}

      {step === 'details' ? (
        <div className="new-hire-layout">
          <aside className="new-hire-nav">
            <button type="button" className="active">
              <FileText size={16} />
              Основна інформація
              <span>5</span>
            </button>
            <button type="button">
              <BriefcaseBusiness size={16} />
              Деталі роботи
              <span>9</span>
            </button>
          </aside>
          <section className="new-hire-form-card">
            <div className="new-hire-section">
              <h2>
                <FileText size={18} />
                Основна інформація
              </h2>
              <div className="new-hire-grid three">
                <label>
                  <span>Прізвище *</span>
                  <input value={form.last_name} onChange={(event) => updateForm({ last_name: event.target.value })} autoFocus />
                </label>
                <label>
                  <span>Ім'я *</span>
                  <input value={form.first_name} onChange={(event) => updateForm({ first_name: event.target.value })} />
                </label>
                <label>
                  <span>По-батькові</span>
                  <input value={form.middle_name} onChange={(event) => updateForm({ middle_name: event.target.value })} />
                </label>
              </div>
              <label>
                <span>Особиста ел. пошта *</span>
                <input type="email" value={form.personal_email} placeholder="eg. andrew@gmail.com" onChange={(event) => updateForm({ personal_email: event.target.value })} />
              </label>
              <label>
                <span>Робоча ел. пошта</span>
                <input type="email" value={form.email} placeholder="eg. andrew@microsoft.com" onChange={(event) => updateForm({ email: event.target.value })} />
              </label>
            </div>

            <div className="new-hire-section">
              <h2>
                <BriefcaseBusiness size={18} />
                Деталі роботи
              </h2>
              <label>
                <span>Дата прийому *</span>
                <input type="date" value={form.hired_on} onChange={(event) => updateForm({ hired_on: event.target.value })} />
              </label>
              <div className="new-hire-grid two">
                {selectField('Тип роботи', 'employment_type', options.workTypes, '-- Немає --', true)}
                {selectField('Графік роботи', 'working_pattern', options.workingPatterns)}
              </div>
              <div className="new-hire-grid two">
                {selectField('Посада', 'position', options.positions)}
                {selectField('Департамент', 'department', options.departments)}
              </div>
              <div className="new-hire-grid two">
                {selectField('Підрозділ', 'division', options.divisions)}
                {selectField('Локація', 'clinic', options.locations, '-- Немає локації --', true)}
              </div>
              <div className="new-hire-grid two">
                {managerField()}
                {selectField('Рівень', 'job_level', options.jobLevels)}
              </div>
              <div className="new-hire-grid two">
                {selectField('Випробний термін', 'probation_policy', options.probationPolicies)}
                <label>
                  <span>Стать</span>
                  <select value={form.gender} onChange={(event) => updateForm({ gender: event.target.value })}>
                    <option value="">-- Немає --</option>
                    {options.genders.map((gender) => (
                      <option key={gender.id} value={gender.code}>
                        {gender.name}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
              <div className="new-hire-grid two">
                <label>
                  <span>Мобільний телефон *</span>
                  <input value={form.phone} onChange={(event) => updateForm({ phone: event.target.value })} />
                </label>
                <label>
                  <span>Робочий телефон</span>
                  <input value={form.phone2} onChange={(event) => updateForm({ phone2: event.target.value })} />
                </label>
              </div>
              <label>
                <span>Коментар</span>
                <textarea value={form.notes} onChange={(event) => updateForm({ notes: event.target.value })} />
              </label>
            </div>
          </section>
        </div>
      ) : (
        <section className="new-hire-review">
          <h2>
            <Zap size={18} />
            Заплановані воркфлоу
          </h2>
          <div className="new-hire-review-grid">
            <span>Співробітник</span>
            <strong>{[form.last_name, form.first_name, form.middle_name].filter(Boolean).join(' ') || '-'}</strong>
            <span>Тип роботи</span>
            <strong>{newHireOptionLabel(options.workTypes, form.employment_type)}</strong>
            <span>Локація</span>
            <strong>{newHireOptionLabel(options.locations, form.clinic)}</strong>
            <span>Менеджер</span>
            <strong>{options.managers.find((manager) => String(manager.id) === form.manager)?.full_name || '-- Ніхто --'}</strong>
            <span>Графік роботи</span>
            <strong>{newHireOptionLabel(options.workingPatterns, form.working_pattern)}</strong>
          </div>
          <label className="settings-option-checkbox new-hire-workflow-check">
            <input type="checkbox" checked readOnly />
            <span>Запустити воркфлоу</span>
          </label>
        </section>
      )}

      <footer className="new-hire-footer">
        <button type="button" className="secondary-action" onClick={step === 'details' ? onBack : () => setStep('details')}>
          {step === 'details' ? 'Скасувати' : 'Назад'}
        </button>
        <button type="button" className="primary-action" disabled={loadState === 'loading' || saveState === 'loading'} onClick={step === 'details' ? goReview : () => void saveHire()}>
          {step === 'details' ? 'Далі' : saveState === 'loading' ? 'Збереження...' : 'Зберегти'}
          {step === 'details' ? <ChevronRight size={16} /> : <Check size={16} />}
        </button>
      </footer>
    </main>
  );
}

function PeopleView({
  brandingSettings,
  employeeCovers,
  onEmployeeCoverChange,
  copy,
}: {
  brandingSettings: BrandingSettings;
  employeeCovers: EmployeeCoverMap;
  onEmployeeCoverChange: (employeeId: number, cover: CoverCropResult) => void;
  copy: AppCopy;
}) {
  const location = useLocation();
  const navigate = useNavigate();
  const peopleRoute = useMemo(() => peopleRouteFromPathname(location.pathname), [location.pathname]);
  const [tab, setTab] = useState('people');
  const [viewMode, setViewMode] = useState<'cards' | 'list'>(() => {
    try {
      const saved = window.localStorage.getItem(peopleViewStorageKey);
      return saved === 'list' || saved === 'cards' ? saved : 'cards';
    } catch {
      return 'cards';
    }
  });
  useEffect(() => {
    try {
      window.localStorage.setItem(peopleViewStorageKey, viewMode);
    } catch {
      /* ignore */
    }
  }, [viewMode]);
  const [showNewProfile, setShowNewProfile] = useState(false);
  const [hireFormPickerOpen, setHireFormPickerOpen] = useState(false);
  const [selectedEmployee, setSelectedEmployee] = useState<EmployeeListItem | null>(null);
  const [employees, setEmployees] = useState<EmployeeListItem[]>([]);
  const [totalEmployees, setTotalEmployees] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [peopleFilters, setPeopleFilters] = useState<PeopleFilterState>(defaultPeopleFilters);
  const [filterOptions, setFilterOptions] = useState<PeopleFilterOptions>(emptyPeopleFilterOptions);
  const [filterOptionsState, setFilterOptionsState] = useState<LoadState>('idle');
  const [loadState, setLoadState] = useState<LoadState>('idle');
  const activeFilterCount = useMemo(() => countActivePeopleFilters(peopleFilters), [peopleFilters]);
  const visiblePeople = useMemo(() => employees.map((employee, index) => employeeToPerson(employee, index, copy)), [copy, employees]);
  const reportsByManager = useMemo(() => {
    const map = new Map<number, Person[]>();
    visiblePeople.forEach((person) => {
      const managerId = person.employee.manager_profile?.id;
      if (managerId == null) return;
      const list = map.get(managerId) ?? [];
      list.push(person);
      map.set(managerId, list);
    });
    return map;
  }, [visiblePeople]);

  const [orgFocus, setOrgFocus] = useState<{ id: number; mode: 'subtree' | 'lineage' } | null>(null);

  function openOrgForPerson(personId: number, mode: 'subtree' | 'lineage') {
    setOrgFocus({ id: personId, mode });
    changePeopleTab('org');
  }

  useEffect(() => {
    let cancelled = false;

    async function loadFilterOptions() {
      setFilterOptionsState('loading');
      try {
        const [positions, departmentLevels, departments, divisions, locations, teams, jobLevels, workTypes] = await Promise.all([
          api.positions({ is_active: true, page_size: 500 }),
          api.departmentLevels({ is_active: true, page_size: 500 }),
          api.departments({ is_active: true, page_size: 500 }),
          api.divisions({ is_active: true, page_size: 500 }),
          api.locations({ is_active: true, page_size: 500 }),
          api.teams({ is_active: true, page_size: 500 }),
          api.jobLevels({ is_active: true, page_size: 500 }),
          api.workTypes({ is_active: true, page_size: 500 }),
        ]);
        if (cancelled) return;
        setFilterOptions({
          positions: namedFilterOptions<PositionOption>(positions.items),
          departmentLevels: namedFilterOptions<DepartmentLevelOption>(departmentLevels.items),
          departments: namedFilterOptions<DepartmentOption>(departments.items),
          divisions: namedFilterOptions<DivisionOption>(divisions.items),
          locations: namedFilterOptions<ClinicLocation>(locations.items),
          teams: namedFilterOptions<TeamOption>(teams.items),
          jobLevels: namedFilterOptions<JobLevel>(jobLevels.items),
          workTypes: namedFilterOptions<WorkType>(workTypes.items),
        });
        setFilterOptionsState('ok');
      } catch {
        if (cancelled) return;
        setFilterOptions(emptyPeopleFilterOptions);
        setFilterOptionsState('error');
      }
    }

    void loadFilterOptions();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function loadPeople() {
      setLoadState('loading');
      try {
        const result = await api.employees({
          q: search,
          status: peopleFilters.status,
          clinic: peopleFilterParam(peopleFilters.location),
          department: peopleFilterParam(peopleFilters.department),
          department_level: peopleFilterParam(peopleFilters.departmentLevel),
          division: peopleFilterParam(peopleFilters.division),
          team: peopleFilterParam(peopleFilters.team),
          job_level: peopleFilterParam(peopleFilters.jobLevel),
          employment_type: peopleFilterParam(peopleFilters.workType),
          position: peopleFilterParam(peopleFilters.position),
          page,
          page_size: peoplePageSize,
        });
        if (cancelled) return;
        setEmployees(result.items);
        setTotalEmployees(result.total);
        setLoadState('ok');
      } catch {
        if (cancelled) return;
        setEmployees([]);
        setTotalEmployees(0);
        setLoadState('error');
      }
    }

    void loadPeople();
    return () => {
      cancelled = true;
    };
  }, [
    page,
    search,
    peopleFilters.department,
    peopleFilters.departmentLevel,
    peopleFilters.division,
    peopleFilters.jobLevel,
    peopleFilters.location,
    peopleFilters.position,
    peopleFilters.status,
    peopleFilters.team,
    peopleFilters.workType,
  ]);

  // Reset to the first page whenever the result set changes (search / filters).
  useEffect(() => {
    setPage(1);
  }, [
    search,
    peopleFilters.department,
    peopleFilters.departmentLevel,
    peopleFilters.division,
    peopleFilters.jobLevel,
    peopleFilters.location,
    peopleFilters.position,
    peopleFilters.status,
    peopleFilters.team,
    peopleFilters.workType,
  ]);

  useEffect(() => {
    if (sectionFromPathname(location.pathname) !== 'people') return;

    if (peopleRoute.mode === 'list') {
      setTab('people');
      setShowNewProfile(false);
      setSelectedEmployee(null);
      return;
    }

    if (peopleRoute.mode === 'teams') {
      setTab('teams');
      setShowNewProfile(false);
      setSelectedEmployee(null);
      return;
    }

    if (peopleRoute.mode === 'org') {
      setTab('org');
      setShowNewProfile(false);
      setSelectedEmployee(null);
      return;
    }

    if (peopleRoute.mode === 'new') {
      setTab('people');
      setSelectedEmployee(null);
      setShowNewProfile(true);
      return;
    }

    const employee = employees.find((item) => item.id === peopleRoute.id) ?? null;
    if (!employee && loadState !== 'ok' && loadState !== 'error') return;
    setTab('people');
    setShowNewProfile(false);
    setSelectedEmployee(employee);
  }, [employees, loadState, location.pathname, peopleRoute]);

  function changePeopleTab(nextTab: string) {
    setTab(nextTab);
    setShowNewProfile(false);
    setSelectedEmployee(null);
    setFiltersOpen(false);
    if (nextTab === 'teams') {
      navigate('/people/teams');
      return;
    }
    if (nextTab === 'org') {
      navigate('/people/org');
      return;
    }
    navigate('/people');
  }

  function openEmployeeProfile(employee: EmployeeListItem) {
    setTab('people');
    setShowNewProfile(false);
    setSelectedEmployee(employee);
    setFiltersOpen(false);
    navigate(peopleEmployeePath(employee.id));
  }

  function openNewProfile() {
    setTab('people');
    setSelectedEmployee(null);
    setFiltersOpen(false);
    setHireFormPickerOpen(true);
  }

  function backToPeopleList() {
    setShowNewProfile(false);
    setSelectedEmployee(null);
    setTab('people');
    setFiltersOpen(false);
    setHireFormPickerOpen(false);
    navigate('/people');
  }

  function startNewHire(choice: { workType: string; location: string }) {
    const params = new URLSearchParams();
    if (choice.workType) params.set('work_type', choice.workType);
    if (choice.location) params.set('location', choice.location);
    setTab('people');
    setSelectedEmployee(null);
    setShowNewProfile(true);
    setFiltersOpen(false);
    setHireFormPickerOpen(false);
    navigate(`/people/new${params.toString() ? `?${params.toString()}` : ''}`);
  }

  function handleEmployeeCreated(employee: EmployeeListItem) {
    setEmployees((current) => [employee, ...current.filter((item) => item.id !== employee.id)]);
    setTotalEmployees((current) => current + 1);
    setShowNewProfile(false);
    setSelectedEmployee(employee);
    setTab('people');
    navigate(peopleEmployeePath(employee.id));
  }

  if (showNewProfile) {
    return <NewHireFlowView search={location.search} onBack={backToPeopleList} onCreated={handleEmployeeCreated} />;
  }

  if (selectedEmployee) {
    return (
      <EmployeeAdminProfileView
        employee={selectedEmployee}
        onBack={backToPeopleList}
        brandingSettings={brandingSettings}
        employeeCover={selectedEmployee ? employeeCovers[String(selectedEmployee.id)] ?? null : null}
        onEmployeeCoverChange={selectedEmployee ? (cover) => onEmployeeCoverChange(selectedEmployee.id, cover) : undefined}
        copy={copy}
      />
    );
  }

  if (tab === 'org') {
    return (
      <OrgView
        embedded
        onBack={backToPeopleList}
        copy={copy}
        themeMode={normalizeTheme(brandingSettings.theme)}
        initialFocus={orgFocus}
        onFocusApplied={() => setOrgFocus(null)}
      />
    );
  }

  return (
    <main className="workspace people-page">
      <header className="page-header">
        <div>
          <h1>{copy.people.title}</h1>
          <SectionTabs
            tabs={[
              { key: 'people', label: copy.people.peopleTab },
              { key: 'teams', label: copy.people.teamsTab },
              { key: 'org', label: copy.people.orgTab },
            ]}
            active={tab}
            onChange={changePeopleTab}
          />
        </div>
        {tab === 'people' ? (
          <div className="header-actions">
            <button type="button" className="icon-button">
              <MoreHorizontal size={18} />
            </button>
            <button type="button" className="primary-action" onClick={openNewProfile}>
              <Plus size={18} />
              {copy.people.newHire}
            </button>
          </div>
        ) : null}
      </header>

      {tab === 'teams' ? (
        <TeamsPanel onOpenOrg={() => changePeopleTab('org')} copy={copy} />
      ) : (
        <>
          <div className="list-toolbar">
            <label className="wide-search">
              <Search size={19} />
              <input
                type="search"
                placeholder={copy.people.searchPlaceholder}
                value={search}
                onChange={(event) => setSearch(event.target.value)}
              />
            </label>
            <button
              type="button"
              className={`toolbar-button ${filtersOpen ? 'active' : ''}`}
              aria-expanded={filtersOpen}
              aria-controls="people-filter-drawer"
              onClick={() => setFiltersOpen((current) => !current)}
            >
              <Filter size={18} />
              {copy.common.filter}
              {activeFilterCount ? <span className="filter-count">{activeFilterCount}</span> : null}
              <ChevronRight size={15} />
            </button>
            <button
              type="button"
              className={`toolbar-icon ${viewMode === 'cards' ? 'active' : ''}`}
              aria-label={copy.people.cards}
              title={copy.people.cards}
              onClick={() => setViewMode('cards')}
            >
              <Grid3X3 size={18} />
            </button>
            <button
              type="button"
              className={`toolbar-icon ${viewMode === 'list' ? 'active' : ''}`}
              aria-label={copy.people.list}
              title={copy.people.list}
              onClick={() => setViewMode('list')}
            >
              <LayoutList size={18} />
            </button>
          </div>
          <div className="result-meta">
            <span>
              {loadState === 'loading'
                ? copy.common.loading
                : totalEmployees === 0
                  ? resultMetaLabel(0, 0, copy)
                  : `${(page - 1) * peoplePageSize + 1}-${(page - 1) * peoplePageSize + visiblePeople.length} / ${totalEmployees}`}
            </span>
            {totalEmployees > peoplePageSize
              ? (() => {
                  const totalPages = Math.max(1, Math.ceil(totalEmployees / peoplePageSize));
                  return (
                    <div className="pagination">
                      <button
                        type="button"
                        aria-label={copy.common.previous}
                        disabled={page <= 1}
                        onClick={() => setPage((current) => Math.max(1, current - 1))}
                      >
                        <ChevronLeft size={16} />
                      </button>
                      {buildPageItems(page, totalPages).map((item, index) =>
                        item === 'gap' ? (
                          <span key={`gap-${index}`} className="page-gap">
                            …
                          </span>
                        ) : (
                          <button type="button" key={item} className={item === page ? 'active' : ''} onClick={() => setPage(item)}>
                            {item}
                          </button>
                        ),
                      )}
                      <button
                        type="button"
                        aria-label={copy.common.next}
                        disabled={page >= totalPages}
                        onClick={() => setPage((current) => Math.min(totalPages, current + 1))}
                      >
                        <ChevronRight size={16} />
                      </button>
                    </div>
                  );
                })()
              : null}
          </div>
          {viewMode === 'cards' ? (
            <PeopleCards people={visiblePeople} loadState={loadState} onOpenPerson={(person) => openEmployeeProfile(person.employee)} copy={copy} />
          ) : (
            <PeopleTable
              people={visiblePeople}
              loadState={loadState}
              onOpenPerson={(person) => openEmployeeProfile(person.employee)}
              brandingSettings={brandingSettings}
              employeeCovers={employeeCovers}
              reportsByManager={reportsByManager}
              onOpenOrg={openOrgForPerson}
              copy={copy}
            />
          )}
          <PeopleFilterDrawer
            open={filtersOpen}
            filters={peopleFilters}
            options={filterOptions}
            optionsState={filterOptionsState}
            activeFilterCount={activeFilterCount}
            onStatusChange={(value) => setPeopleFilters((current) => ({ ...current, status: value }))}
            onMultiChange={(key, value) => setPeopleFilters((current) => ({ ...current, [key]: value }))}
            onReset={() => setPeopleFilters(defaultPeopleFilters)}
            onClose={() => setFiltersOpen(false)}
          />
          <NewHireFormPicker
            open={hireFormPickerOpen}
            options={filterOptions}
            optionsState={filterOptionsState}
            onClose={() => setHireFormPickerOpen(false)}
            onContinue={startNewHire}
          />
        </>
      )}
    </main>
  );
}

function PeopleFilterDrawer({
  open,
  filters,
  options,
  optionsState,
  activeFilterCount,
  onStatusChange,
  onMultiChange,
  onReset,
  onClose,
}: {
  open: boolean;
  filters: PeopleFilterState;
  options: PeopleFilterOptions;
  optionsState: LoadState;
  activeFilterCount: number;
  onStatusChange: (value: string) => void;
  onMultiChange: (key: PeopleMultiFilterKey, value: string[]) => void;
  onReset: () => void;
  onClose: () => void;
}) {
  useOverlayDismiss(open, onClose);
  const [expandedFilter, setExpandedFilter] = useState<PeopleMultiFilterKey | null>(null);
  const [statusOpen, setStatusOpen] = useState(false);
  const statusOptions: PeopleFilterOption[] = [
    { value: 'active', label: 'Працюючі' },
    { value: 'on_leave', label: 'У відпустці' },
    { value: 'dismissed', label: 'Звільнені' },
    { value: 'suspended', label: 'Призупинені' },
  ];
  const optionsLoading = optionsState === 'loading';
  const rows: Array<{ key: PeopleMultiFilterKey; label: string; placeholder: string; options: PeopleFilterOption[] }> = [
    { key: 'position', label: 'Посада', placeholder: 'Посада', options: options.positions },
    { key: 'departmentLevel', label: 'Рівень департаменту', placeholder: 'Рівень департаменту', options: options.departmentLevels },
    { key: 'department', label: 'Департамент', placeholder: 'Департамент', options: options.departments },
    { key: 'division', label: 'Підрозділ', placeholder: 'Підрозділ', options: options.divisions },
    { key: 'location', label: 'Локація', placeholder: 'Локація', options: options.locations },
    { key: 'team', label: 'Команда', placeholder: 'Команда', options: options.teams },
    { key: 'jobLevel', label: 'Рівень', placeholder: 'Рівень', options: options.jobLevels },
    { key: 'workType', label: 'Тип роботи', placeholder: 'Тип роботи', options: options.workTypes },
  ];

  useEffect(() => {
    if (!open) {
      setExpandedFilter(null);
      setStatusOpen(false);
    }
  }, [open]);

  return (
    <>
      <button
        type="button"
        className={`people-filter-scrim ${open ? 'open' : ''}`}
        aria-hidden={!open}
        tabIndex={open ? 0 : -1}
        onClick={onClose}
      />
      <aside id="people-filter-drawer" className={`people-filter-drawer ${open ? 'open' : ''}`} aria-hidden={!open}>
        <div className="people-filter-head">
          <h2>Фільтри</h2>
          <button type="button" className="people-filter-close" aria-label="Закрити фільтри" onClick={onClose}>
            <X size={22} />
          </button>
        </div>
        <div className="people-filter-body">
          <PeopleSingleFilter
            label="Статус"
            value={filters.status}
            placeholder={peopleStatusLabel(filters.status)}
            options={statusOptions}
            expanded={statusOpen}
            onToggle={() => {
              setExpandedFilter(null);
              setStatusOpen((current) => !current);
            }}
            onChange={(value) => {
              onStatusChange(value);
              setStatusOpen(false);
            }}
          />
          {rows.map((row) => (
            <PeopleMultiFilter
              key={row.key}
              label={row.label}
              value={filters[row.key]}
              placeholder={row.placeholder}
              options={row.options}
              loading={optionsLoading}
              expanded={expandedFilter === row.key}
              onToggle={() => {
                setStatusOpen(false);
                setExpandedFilter((current) => (current === row.key ? null : row.key));
              }}
              onChange={(value) => onMultiChange(row.key, value)}
            />
          ))}
          <PeopleMultiFilter label="Каталог посад" value={[]} placeholder="Каталог посад" options={[]} disabled />
          {optionsState === 'error' ? <p className="people-filter-error">Не вдалося завантажити частину фільтрів.</p> : null}
        </div>
        <div className="people-filter-foot">
          <button type="button" className="toolbar-button strong">
            <Filter size={16} />
            Додати фільтр
            <ChevronDown size={15} />
          </button>
          {activeFilterCount ? (
            <button type="button" className="people-filter-reset" onClick={onReset}>
              Очистити
            </button>
          ) : null}
        </div>
      </aside>
    </>
  );
}

function PeopleSingleFilter({
  label,
  value,
  placeholder,
  options,
  expanded,
  onToggle,
  onChange,
}: {
  label: string;
  value: string;
  placeholder: string;
  options: PeopleFilterOption[];
  expanded: boolean;
  onToggle: () => void;
  onChange: (value: string) => void;
}) {
  const selectedLabel = options.find((option) => option.value === value)?.label ?? placeholder;

  return (
    <div className={`people-filter-select people-filter-single ${value ? 'selected' : ''} ${expanded ? 'expanded' : ''}`}>
      <button type="button" className="people-filter-trigger" aria-expanded={expanded} aria-label={label} onClick={onToggle}>
        <span>{selectedLabel}</span>
        <ChevronDown size={17} aria-hidden="true" />
      </button>
      {expanded ? (
        <div className="people-filter-menu people-filter-single-menu">
          {options.map((option) => (
            <button
              key={option.value}
              type="button"
              className={`people-filter-single-option ${option.value === value ? 'selected' : ''}`}
              onClick={() => onChange(option.value)}
            >
              {option.label}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function PeopleMultiFilter({
  label,
  value,
  placeholder,
  options,
  loading = false,
  disabled = false,
  expanded = false,
  onToggle,
  onChange,
}: {
  label: string;
  value: string[];
  placeholder: string;
  options: PeopleFilterOption[];
  loading?: boolean;
  disabled?: boolean;
  expanded?: boolean;
  onToggle?: () => void;
  onChange?: (value: string[]) => void;
}) {
  const [query, setQuery] = useState('');
  const selected = useMemo(() => new Set(value), [value]);
  const filteredOptions = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    if (!normalized) return options;
    return options.filter((option) => option.label.toLowerCase().includes(normalized));
  }, [options, query]);
  const allVisibleSelected = filteredOptions.length > 0 && filteredOptions.every((option) => selected.has(option.value));

  useEffect(() => {
    if (!expanded) setQuery('');
  }, [expanded]);

  function toggleOption(optionValue: string) {
    if (!onChange) return;
    if (selected.has(optionValue)) {
      onChange(value.filter((item) => item !== optionValue));
      return;
    }
    onChange([...value, optionValue]);
  }

  function toggleVisibleOptions() {
    if (!onChange || !filteredOptions.length) return;
    const visibleValues = filteredOptions.map((option) => option.value);
    if (allVisibleSelected) {
      onChange(value.filter((item) => !visibleValues.includes(item)));
      return;
    }
    onChange(Array.from(new Set([...value, ...visibleValues])));
  }

  return (
    <div className={`people-filter-select people-filter-multi ${value.length ? 'selected' : ''} ${expanded ? 'expanded' : ''} ${disabled ? 'disabled' : ''}`}>
      <button type="button" className="people-filter-trigger" disabled={disabled || loading} onClick={onToggle}>
        <span>{loading ? 'Завантаження...' : peopleFilterSelectionLabel(value, options, placeholder)}</span>
        <ChevronDown size={17} aria-hidden="true" />
      </button>
      {expanded && !disabled ? (
        <div className="people-filter-menu">
          <label className="people-filter-search">
            <Search size={18} />
            <input autoFocus type="search" value={query} placeholder="Пошук..." onChange={(event) => setQuery(event.target.value)} />
          </label>
          <button type="button" className="people-filter-select-all" onClick={toggleVisibleOptions}>
            {allVisibleSelected ? 'Очистити вибрані' : 'Вибрати всі'}
          </button>
          <div className="people-filter-options">
            {filteredOptions.length ? (
              filteredOptions.map((option) => (
                <label key={option.value} className="people-filter-option">
                  <input type="checkbox" checked={selected.has(option.value)} onChange={() => toggleOption(option.value)} />
                  <span>{option.count != null ? `${option.label} (${option.count})` : option.label}</span>
                </label>
              ))
            ) : (
              <div className="people-filter-no-options">Нічого не знайдено</div>
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}

type TeamFormState = {
  name: string;
  description: string;
  leadId: string;
  memberIds: string[];
};

function emptyTeamForm(): TeamFormState {
  return {
    name: '',
    description: '',
    leadId: '',
    memberIds: [],
  };
}

function teamFormFromItem(team: TeamOption): TeamFormState {
  return {
    name: team.name,
    description: team.description || '',
    leadId: team.lead ? String(team.lead) : '',
    memberIds: (team.members || []).map((member) => String(member.id)),
  };
}

function teamEmployeeSubtitle(employee: EmployeeListItem, copy: AppCopy): string {
  return employee.position_name || employee.department_name || employee.division_name || copy.people.noPosition;
}

function filterTeamEmployees(employees: EmployeeListItem[], query: string): EmployeeListItem[] {
  const normalized = query.trim().toLowerCase();
  if (!normalized) return employees;
  return employees.filter((employee) => {
    const haystack = [
      employee.full_name,
      employee.position_name,
      employee.department_name,
      employee.clinic_name,
      employee.email,
    ]
      .filter(Boolean)
      .join(' ')
      .toLowerCase();
    return haystack.includes(normalized);
  });
}

function TeamLeadPicker({
  employees,
  value,
  loading,
  onChange,
  copy,
}: {
  employees: EmployeeListItem[];
  value: string;
  loading: boolean;
  onChange: (value: string) => void;
  copy: AppCopy;
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const selected = employees.find((employee) => String(employee.id) === value) ?? null;
  const visibleEmployees = filterTeamEmployees(employees, query).slice(0, 80);

  return (
    <div className="team-form-field team-picker-field">
      <span>Менеджер команди</span>
      <div className="team-picker">
        <div className={`team-picker-trigger ${open ? 'active' : ''}`}>
          <button type="button" className="team-picker-value" onClick={() => setOpen((current) => !current)}>
            {selected ? selected.full_name : loading ? copy.common.loading : '-- Виберіть --'}
          </button>
          {value ? (
            <button type="button" className="team-picker-icon" aria-label="Очистити" onClick={() => onChange('')}>
              <X size={16} />
            </button>
          ) : null}
          <button type="button" className="team-picker-icon" aria-label="Відкрити" onClick={() => setOpen((current) => !current)}>
            <ChevronDown size={16} />
          </button>
        </div>
        {open ? (
          <div className="team-picker-dropdown team-picker-dropdown-single">
            <label className="team-picker-search">
              <Search size={17} />
              <input value={query} placeholder="Пошук..." onChange={(event) => setQuery(event.target.value)} autoFocus />
            </label>
            <div className="team-picker-options">
              {visibleEmployees.map((employee, index) => {
                const isSelected = String(employee.id) === value;
                return (
                  <button
                    key={employee.id}
                    type="button"
                    className={`team-picker-option ${isSelected ? 'selected' : ''}`}
                    onClick={() => {
                      onChange(String(employee.id));
                      setOpen(false);
                    }}
                  >
                    <span className="team-picker-check">{isSelected ? <CheckSquare size={16} /> : null}</span>
                    <Avatar
                      name={employee.full_name}
                      src={employeeAvatarUrl(employee)}
                      accent={employeeAccentClasses[index % employeeAccentClasses.length]}
                      size="default"
                    />
                    <span>
                      <strong>{employee.full_name}</strong>
                      <small>{teamEmployeeSubtitle(employee, copy)}</small>
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}

function TeamMemberRemoveConfirmModal({
  employee,
  copy,
  onCancel,
  onConfirm,
}: {
  employee: EmployeeListItem;
  copy: AppCopy;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  return (
    <div className="settings-option-modal-layer team-member-remove-layer" role="dialog" aria-modal="true" aria-label="Видалити з команди">
      <button type="button" className="settings-option-modal-backdrop" aria-label={copy.settings.cancel} onClick={onCancel} />
      <section className="settings-option-modal settings-delete-modal">
        <header>
          <strong>Видалити з команди?</strong>
          <button type="button" className="modal-close" aria-label={copy.settings.cancel} onClick={onCancel}>
            <X size={22} />
          </button>
        </header>
        <div className="settings-delete-body">
          <p>Співробітника буде прибрано тільки з цієї команди. Профіль співробітника не зміниться.</p>
          <strong>{employee.full_name}</strong>
        </div>
        <footer>
          <button type="button" className="secondary-action" onClick={onCancel}>
            {copy.settings.cancel}
          </button>
          <button type="button" className="danger-action" onClick={onConfirm}>
            Видалити
          </button>
        </footer>
      </section>
    </div>
  );
}

function TeamMembersPicker({
  employees,
  selectedIds,
  loading,
  onChange,
  copy,
}: {
  employees: EmployeeListItem[];
  selectedIds: string[];
  loading: boolean;
  onChange: (selectedIds: string[]) => void;
  copy: AppCopy;
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [removeTarget, setRemoveTarget] = useState<EmployeeListItem | null>(null);
  const selectedSet = useMemo(() => new Set(selectedIds), [selectedIds]);
  const employeesById = useMemo(() => new Map(employees.map((employee) => [String(employee.id), employee])), [employees]);
  const selectedEmployees = useMemo(
    () => selectedIds.map((id) => employeesById.get(id)).filter((employee): employee is EmployeeListItem => Boolean(employee)),
    [employeesById, selectedIds],
  );
  const visibleEmployees = filterTeamEmployees(employees, query).slice(0, 120);
  const pickerLabel = loading ? copy.common.loading : selectedIds.length ? 'Додати ще учасників' : '-- Виберіть --';

  function addEmployee(employeeId: number) {
    const key = String(employeeId);
    if (selectedSet.has(key)) return;
    onChange([...selectedIds, key]);
    setQuery('');
  }

  function confirmRemove() {
    if (!removeTarget) return;
    const key = String(removeTarget.id);
    onChange(selectedIds.filter((id) => id !== key));
    setRemoveTarget(null);
  }

  return (
    <div className="team-form-field team-picker-field">
      <span>
        Учасники
        <small>{selectedIds.length ? `${selectedIds.length} вибрано` : ''}</small>
      </span>
      <div className="team-picker team-members-picker">
        <div className={`team-picker-trigger ${open ? 'active' : ''}`}>
          <button type="button" className="team-picker-value team-picker-summary" onClick={() => setOpen((current) => !current)}>
            {pickerLabel}
          </button>
          {selectedIds.length ? (
            <span className="team-picker-count">{selectedIds.length}</span>
          ) : null}
          <button type="button" className="team-picker-icon" aria-label="Відкрити" onClick={() => setOpen((current) => !current)}>
            <ChevronDown size={16} />
          </button>
        </div>
        {open ? (
          <div className="team-picker-dropdown">
            <label className="team-picker-search">
              <Search size={17} />
              <input value={query} placeholder="Пошук..." onChange={(event) => setQuery(event.target.value)} autoFocus />
            </label>
            <div className="team-picker-options">
              {visibleEmployees.length ? (
                visibleEmployees.map((employee, index) => {
                  const isSelected = selectedSet.has(String(employee.id));
                  return (
                    <button
                      key={employee.id}
                      type="button"
                      className={`team-picker-option ${isSelected ? 'selected' : ''}`}
                      aria-pressed={isSelected}
                      onClick={() => {
                        if (isSelected) {
                          setRemoveTarget(employee);
                          return;
                        }
                        addEmployee(employee.id);
                      }}
                    >
                      <span className="team-picker-check" aria-hidden="true">
                        {isSelected ? <Check size={15} /> : null}
                      </span>
                      <Avatar
                        name={employee.full_name}
                        src={employeeAvatarUrl(employee)}
                        accent={employeeAccentClasses[index % employeeAccentClasses.length]}
                        size="default"
                      />
                      <span>
                        <strong>{employee.full_name}</strong>
                        <small>{teamEmployeeSubtitle(employee, copy)}</small>
                      </span>
                    </button>
                  );
                })
              ) : (
                <span className="team-picker-empty">
                  {employees.length ? 'Нічого не знайдено' : copy.common.loading}
                </span>
              )}
            </div>
          </div>
        ) : null}
      </div>
      {selectedEmployees.length ? (
        <div className="team-selected-member-chips">
          {selectedEmployees.map((employee, index) => (
            <span key={employee.id} className="team-selected-member-chip">
              <Avatar
                name={employee.full_name}
                src={employeeAvatarUrl(employee)}
                accent={employeeAccentClasses[index % employeeAccentClasses.length]}
                size="sm"
              />
              <span>{employee.full_name}</span>
              <button type="button" aria-label={`Видалити ${employee.full_name}`} onClick={() => setRemoveTarget(employee)}>
                <X size={14} />
              </button>
            </span>
          ))}
        </div>
      ) : null}
      {removeTarget ? (
        <TeamMemberRemoveConfirmModal
          employee={removeTarget}
          copy={copy}
          onCancel={() => setRemoveTarget(null)}
          onConfirm={confirmRemove}
        />
      ) : null}
    </div>
  );
}

function TeamsPanel({ onOpenOrg, copy }: { onOpenOrg: () => void; copy: AppCopy }) {
  const navigate = useNavigate();
  const [teams, setTeams] = useState<TeamOption[]>([]);
  const [employees, setEmployees] = useState<EmployeeListItem[]>([]);
  const [search, setSearch] = useState('');
  const [loadState, setLoadState] = useState<LoadState>('idle');
  const [peopleLoadState, setPeopleLoadState] = useState<LoadState>('idle');
  const [saveState, setSaveState] = useState<LoadState>('idle');
  const [error, setError] = useState('');
  const [selectedTeam, setSelectedTeam] = useState<TeamOption | null>(null);
  useOverlayDismiss(Boolean(selectedTeam), () => setSelectedTeam(null));
  const [editingTeam, setEditingTeam] = useState<TeamOption | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<TeamOption | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const [form, setForm] = useState<TeamFormState>(() => emptyTeamForm());
  const [menuOpenId, setMenuOpenId] = useState<number | null>(null);

  const employeeOptions = useMemo(
    () => [...employees].sort((first, second) => first.full_name.localeCompare(second.full_name, 'uk')),
    [employees],
  );

  async function loadTeams() {
    setLoadState('loading');
    setError('');
    try {
      const result = await api.teams({ q: search, is_active: true, page_size: 300 });
      setTeams(result.items);
      setSelectedTeam((current) => {
        if (!current) return current;
        return result.items.find((item) => item.id === current.id) ?? null;
      });
      setLoadState('ok');
    } catch (loadError) {
      setTeams([]);
      setLoadState('error');
      setError(loadError instanceof ApiError ? loadError.message : copy.settings.loadErrorText);
    }
  }

  useEffect(() => {
    void loadTeams();
  }, [search]);

  useEffect(() => {
    let cancelled = false;

    async function loadEmployees() {
      setPeopleLoadState('loading');
      try {
        const result = await api.employees({ status: 'active', compact: true, page_size: 500 });
        if (cancelled) return;
        setEmployees(result.items);
        setPeopleLoadState('ok');
      } catch {
        if (cancelled) return;
        setEmployees([]);
        setPeopleLoadState('error');
      }
    }

    void loadEmployees();
    return () => {
      cancelled = true;
    };
  }, []);

  function openCreateForm() {
    setEditingTeam(null);
    setForm(emptyTeamForm());
    setFormOpen(true);
    setMenuOpenId(null);
  }

  function openEditForm(team: TeamOption) {
    setEditingTeam(team);
    setForm(teamFormFromItem(team));
    setFormOpen(true);
    setMenuOpenId(null);
  }

  function closeForm() {
    if (saveState === 'loading') return;
    setFormOpen(false);
    setEditingTeam(null);
    setForm(emptyTeamForm());
  }

  async function saveTeam(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!form.name.trim()) return;
    setSaveState('loading');
    setError('');
    const payload = {
      name: form.name.trim(),
      description: form.description.trim(),
      lead: form.leadId ? Number(form.leadId) : null,
      member_ids: form.memberIds.map(Number),
      is_active: true,
    };
    try {
      const saved = editingTeam ? await api.updateTeam(editingTeam.id, payload) : await api.createTeam(payload);
      setSelectedTeam(saved);
      setFormOpen(false);
      setEditingTeam(null);
      setSaveState('ok');
      await loadTeams();
    } catch (saveError) {
      setSaveState('error');
      setError(saveError instanceof ApiError ? saveError.message : copy.settings.loadErrorText);
    }
  }

  async function deleteTeam(team: TeamOption) {
    setSaveState('loading');
    setError('');
    try {
      await api.deleteTeam(team.id);
      setDeleteTarget(null);
      setSelectedTeam((current) => (current?.id === team.id ? null : current));
      setSaveState('ok');
      await loadTeams();
    } catch (deleteError) {
      setSaveState('error');
      setError(deleteError instanceof ApiError ? deleteError.message : copy.settings.loadErrorText);
    }
  }

  function openEmployee(employee: EmployeeListItem) {
    navigate(peopleEmployeePath(employee.id));
  }

  return (
    <section className="teams-workspace">
      <div className="team-toolbar">
        <label className="wide-search">
          <Search size={19} />
          <input
            type="search"
            placeholder="Пошук..."
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </label>
        <button type="button" className="icon-button" aria-label="Дії">
          <MoreHorizontal size={18} />
        </button>
        <button type="button" className="primary-action" onClick={openCreateForm}>
          <Plus size={18} />
          Створити команду
        </button>
      </div>

      {error ? <p className="error-text teams-error">{error}</p> : null}

      {loadState === 'loading' ? (
        <div className="people-card-empty">
          <EmptyState title={copy.common.loading} />
        </div>
      ) : !teams.length ? (
        <div className="people-card-empty">
          <EmptyState title={copy.people.teamsEmptyTitle} text={copy.people.teamsEmptyText} />
          <button type="button" className="secondary-action empty-action" onClick={onOpenOrg}>
            <GitBranch size={17} />
            {copy.people.goToStructure}
          </button>
        </div>
      ) : (
        <div className="team-grid">
          {teams.map((team, teamIndex) => {
            const lead = team.lead_profile || null;
            const leadPerson = lead ? employeeToPerson(lead, teamIndex, copy) : null;
            const members = team.members || [];
            return (
              <article
                key={team.id}
                className="team-card"
                tabIndex={0}
                onClick={() => setSelectedTeam(team)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter') setSelectedTeam(team);
                }}
              >
                <header>
                  <h2>{team.name}</h2>
                  <div className="settings-option-row-menu" onClick={(event) => event.stopPropagation()}>
                    <button
                      type="button"
                      className="settings-option-row-action"
                      aria-label="Дії"
                      onClick={() => setMenuOpenId((current) => (current === team.id ? null : team.id))}
                    >
                      <MoreHorizontal size={17} />
                    </button>
                    {menuOpenId === team.id ? (
                      <div className="settings-option-row-popover">
                        <button type="button" onClick={() => openEditForm(team)}>
                          {copy.settings.edit}
                        </button>
                        <button type="button" className="danger" onClick={() => setDeleteTarget(team)}>
                          {copy.settings.delete}
                        </button>
                      </div>
                    ) : null}
                  </div>
                </header>
                <div className="team-card-body">
                  <div>
                    <span>Менеджер команди</span>
                    {leadPerson ? (
                      <button
                        type="button"
                        className="team-lead-button"
                        onClick={(event) => {
                          event.stopPropagation();
                          if (lead) openEmployee(lead);
                        }}
                      >
                        <Avatar name={leadPerson.fullName} src={leadPerson.avatarUrl} accent={leadPerson.accent} size="sm" />
                        <span>
                          <strong>{leadPerson.fullName}</strong>
                          <small>{leadPerson.role}</small>
                        </span>
                      </button>
                    ) : (
                      <p>Без керівника</p>
                    )}
                  </div>
                  <div className="team-members-preview">
                    <strong>{team.member_count || members.length} учасників</strong>
                    <span>
                      {members.slice(0, 6).map((member, index) => (
                        <Avatar
                          key={member.id}
                          name={member.full_name}
                          src={employeeAvatarUrl(member)}
                          accent={employeeAccentClasses[(teamIndex + index) % employeeAccentClasses.length]}
                          size="sm"
                        />
                      ))}
                      {members.length > 6 ? <em>+{members.length - 6}</em> : null}
                    </span>
                  </div>
                </div>
              </article>
            );
          })}
        </div>
      )}

      {selectedTeam ? (
        <aside className="team-drawer" aria-label={selectedTeam.name}>
          <button type="button" className="team-drawer-backdrop" aria-label="Закрити" onClick={() => setSelectedTeam(null)} />
          <section>
            <header>
              <div>
                <h2>{selectedTeam.name}</h2>
                {selectedTeam.description ? <p>{selectedTeam.description}</p> : null}
              </div>
              <button type="button" className="modal-close" aria-label="Закрити" onClick={() => setSelectedTeam(null)}>
                <X size={22} />
              </button>
            </header>
            <div className="team-drawer-content">
              <div className="team-drawer-manager">
                <span>Менеджер команди</span>
                {selectedTeam.lead_profile ? (
                  <button type="button" onClick={() => openEmployee(selectedTeam.lead_profile as EmployeeListItem)}>
                    <Avatar
                      name={selectedTeam.lead_profile.full_name}
                      src={employeeAvatarUrl(selectedTeam.lead_profile)}
                      accent="slate"
                      size="default"
                    />
                    <span>
                      <strong>{selectedTeam.lead_profile.full_name}</strong>
                      <small>{selectedTeam.lead_profile.position_name || copy.people.noPosition}</small>
                    </span>
                  </button>
                ) : (
                  <p>Без керівника</p>
                )}
              </div>
              <div className="team-drawer-members">
                <h3>Учасники</h3>
                <div className="team-drawer-meta">{resultMetaLabel(selectedTeam.members.length, selectedTeam.member_count, copy)}</div>
                <table>
                  <thead>
                    <tr>
                      <th>{copy.people.fullName}</th>
                      <th>{copy.people.department}</th>
                      <th>{copy.people.location}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {selectedTeam.members.map((member, index) => {
                      const person = employeeToPerson(member, index, copy);
                      return (
                        <tr key={member.id} onClick={() => openEmployee(member)} tabIndex={0}>
                          <td>
                            <Avatar name={person.fullName} src={person.avatarUrl} accent={person.accent} size="sm" />
                            <span>
                              <strong>{person.fullName}</strong>
                              <small>{person.role}</small>
                            </span>
                          </td>
                          <td>{person.department}</td>
                          <td>{person.location}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          </section>
        </aside>
      ) : null}

      {formOpen ? (
        <div className="settings-option-modal-layer" role="dialog" aria-modal="true" aria-label={editingTeam ? 'Редагувати команду' : 'Створити команду'}>
          <button type="button" className="settings-option-modal-backdrop" aria-label={copy.settings.cancel} onClick={closeForm} />
          <form className="settings-option-modal team-form-modal" onSubmit={saveTeam}>
            <header>
              <strong>{editingTeam ? 'Редагувати команду' : 'Створити команду'}</strong>
              <button type="button" className="modal-close" aria-label={copy.settings.cancel} onClick={closeForm}>
                <X size={22} />
              </button>
            </header>
            <div className="team-form-body">
              <label>
                Ім'я
                <input
                  value={form.name}
                  onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))}
                  required
                />
              </label>
              <label>
                <span>
                  Опис
                  <small>За бажанням</small>
                </span>
                <textarea
                  value={form.description}
                  onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))}
                />
              </label>
              <TeamLeadPicker
                employees={employeeOptions}
                value={form.leadId}
                loading={peopleLoadState === 'loading'}
                onChange={(leadId) => setForm((current) => ({ ...current, leadId }))}
                copy={copy}
              />
              <TeamMembersPicker
                employees={employeeOptions}
                selectedIds={form.memberIds}
                loading={peopleLoadState === 'loading'}
                onChange={(memberIds) => setForm((current) => ({ ...current, memberIds }))}
                copy={copy}
              />
            </div>
            <footer>
              <button type="submit" className="primary-action" disabled={saveState === 'loading' || !form.name.trim()}>
                {copy.settings.save}
              </button>
            </footer>
          </form>
        </div>
      ) : null}

      {deleteTarget ? (
        <SettingsDeleteConfirmModal
          itemName={deleteTarget.name}
          copy={copy}
          loading={saveState === 'loading'}
          onCancel={() => {
            if (saveState !== 'loading') setDeleteTarget(null);
          }}
          onConfirm={() => void deleteTeam(deleteTarget)}
        />
      ) : null}
    </section>
  );
}

function PeopleCards({
  people,
  loadState,
  onOpenPerson,
  copy,
}: {
  people: Person[];
  loadState: LoadState;
  onOpenPerson: (person: Person) => void;
  copy: AppCopy;
}) {
  const emptyTitle =
    loadState === 'loading'
      ? copy.common.loading
      : loadState === 'error'
        ? copy.people.employeesLoadError
        : copy.people.employeesNotFound;
  const emptyText =
    loadState === 'loading'
      ? ''
      : loadState === 'error'
        ? copy.common.backendRetry
        : copy.people.notFoundText;

  if (!people.length) {
    return (
      <div className="people-card-empty">
        <EmptyState title={emptyTitle} text={emptyText} />
      </div>
    );
  }

  return (
    <div className="people-card-grid">
      {people.map((person) => (
        <article
          key={person.id}
          className="person-card"
          tabIndex={0}
          onClick={() => onOpenPerson(person)}
          onKeyDown={(event) => {
            if (event.key === 'Enter') onOpenPerson(person);
          }}
        >
          <div className="person-card-main">
            <Avatar name={person.fullName} src={person.avatarUrl} accent={person.accent} size="lg" />
            <div>
              <h2>{person.fullName}</h2>
              <p>
                {person.role}
                {person.location && person.location !== copy.people.noLocation ? ` · ${person.location}` : ''}
              </p>
            </div>
          </div>
          <div className="person-card-actions">
            {person.email && person.email !== '-' ? (
              <a href={`mailto:${person.email}`} aria-label={`${person.email}`} onClick={(event) => event.stopPropagation()}>
                <Mail size={17} />
              </a>
            ) : (
              <span aria-hidden="true" />
            )}
            {person.phone ? (
              <a href={`tel:${person.phone}`} aria-label={`${person.phone}`} onClick={(event) => event.stopPropagation()}>
                <Phone size={17} />
              </a>
            ) : (
              <span aria-hidden="true" />
            )}
          </div>
        </article>
      ))}
    </div>
  );
}

function resolveEmployeeCoverUrl(employeeId: number, brandingSettings: BrandingSettings, employeeCovers: EmployeeCoverMap): string {
  const personal = employeeCovers[String(employeeId)]?.url;
  if (brandingSettings.employeeCoverUploadAllowed && personal) return personal;
  return brandingSettings.employeeCoverUrl || '';
}

function PeopleTable({
  people,
  loadState,
  onOpenPerson,
  brandingSettings,
  employeeCovers,
  reportsByManager,
  onOpenOrg,
  copy,
}: {
  people: Person[];
  loadState: LoadState;
  onOpenPerson: (person: Person) => void;
  brandingSettings: BrandingSettings;
  employeeCovers: EmployeeCoverMap;
  reportsByManager: Map<number, Person[]>;
  onOpenOrg: (personId: number, mode: 'subtree' | 'lineage') => void;
  copy: AppCopy;
}) {
  const emptyTitle =
    loadState === 'loading'
      ? copy.common.loading
      : loadState === 'error'
        ? copy.people.employeesLoadError
        : copy.people.employeesNotFound;
  const emptyText =
    loadState === 'loading'
      ? ''
      : loadState === 'error'
        ? copy.common.backendRetry
        : copy.people.notFoundText;

  return (
    <div className="table-shell">
      <table className="people-table">
        <colgroup>
          <col className="people-name-col" />
          <col className="people-position-col" />
          <col className="people-department-col" />
          <col className="people-location-col" />
          <col className="people-manager-col" />
          <col className="people-date-col" />
        </colgroup>
        <thead>
          <tr>
            <th>{copy.people.fullName} ↑</th>
            <th>{copy.people.position}</th>
            <th>{copy.people.department}</th>
            <th>{copy.people.location}</th>
            <th>{copy.people.manager}</th>
            <th>{copy.people.startDate}</th>
          </tr>
        </thead>
        <tbody>
          {people.length ? people.map((person) => {
            const managerProfile = person.employee.manager_profile;
            const managerPerson = managerProfile ? employeeToPerson(managerProfile, person.id, copy) : null;
            return (
              <tr
                key={person.id}
                className="person-row"
                tabIndex={0}
                onClick={() => onOpenPerson(person)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter') onOpenPerson(person);
                }}
              >
                <td className="name-cell">
                  <ProfileHoverCard
                    className="person-name"
                    person={person}
                    coverUrl={resolveEmployeeCoverUrl(person.id, brandingSettings, employeeCovers)}
                    reports={reportsByManager.get(person.id) ?? []}
                    onOpenOrg={() => onOpenOrg(person.id, 'lineage')}
                    onOpenProfile={() => onOpenPerson(person)}
                  >
                    <Avatar name={person.fullName} src={person.avatarUrl} accent={person.accent} size="sm" />
                    <span>{person.fullName}</span>
                  </ProfileHoverCard>
                </td>
                <td title={person.role}>{person.role}</td>
                <td title={person.department}>{person.department}</td>
                <td title={person.location}>{person.location}</td>
                <td title={person.manager}>
                  {managerPerson ? (
                    <ProfileHoverCard
                      className="manager-cell"
                      align="right"
                      person={managerPerson}
                      coverUrl={resolveEmployeeCoverUrl(managerPerson.id, brandingSettings, employeeCovers)}
                      reports={reportsByManager.get(managerPerson.id) ?? []}
                      onOpenOrg={() => onOpenOrg(managerPerson.id, 'subtree')}
                      onOpenProfile={() => onOpenPerson(managerPerson)}
                      onClick={(event) => {
                        event.stopPropagation();
                        onOpenPerson(managerPerson);
                      }}
                    >
                      <Avatar name={person.manager} src={employeeAvatarUrl(managerProfile)} accent="slate" size="sm" />
                      <span>{person.manager}</span>
                    </ProfileHoverCard>
                  ) : (
                    <div className="manager-cell">
                      <Avatar name={person.manager} src="" accent="slate" size="sm" />
                      <span>{person.manager}</span>
                    </div>
                  )}
                </td>
                <td>{person.startDate}</td>
              </tr>
            );
          }) : (
            <tr>
              <td colSpan={6}>
                <EmptyState title={emptyTitle} text={emptyText} />
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

function ProfileHoverCard({
  person,
  coverUrl,
  reports,
  align = 'left',
  onOpenOrg,
  onOpenProfile,
  className,
  onClick,
  children,
}: {
  person: Person;
  coverUrl?: string;
  reports?: Person[];
  align?: 'left' | 'right';
  onOpenOrg?: () => void;
  onOpenProfile?: () => void;
  className?: string;
  onClick?: (event: ReactMouseEvent<HTMLDivElement>) => void;
  children: ReactNode;
}) {
  const triggerRef = useRef<HTMLDivElement | null>(null);
  const [pos, setPos] = useState<{ top: number; left: number } | null>(null);
  const showTimer = useRef<number | undefined>(undefined);
  const hideTimer = useRef<number | undefined>(undefined);
  const CARD_W = 332;
  const CARD_H = 360;

  function openCard() {
    window.clearTimeout(hideTimer.current);
    const element = triggerRef.current;
    if (!element) return;
    const rect = element.getBoundingClientRect();
    let left = align === 'right' ? rect.right - CARD_W : rect.left - 8;
    left = Math.max(12, Math.min(left, window.innerWidth - CARD_W - 12));
    let top = rect.bottom + 6;
    if (top + CARD_H > window.innerHeight - 12) {
      top = Math.max(12, rect.top - CARD_H - 6);
    }
    setPos({ top, left });
  }

  function scheduleShow() {
    window.clearTimeout(hideTimer.current);
    showTimer.current = window.setTimeout(openCard, 350);
  }

  function scheduleHide() {
    window.clearTimeout(showTimer.current);
    hideTimer.current = window.setTimeout(() => setPos(null), 160);
  }

  useEffect(
    () => () => {
      window.clearTimeout(showTimer.current);
      window.clearTimeout(hideTimer.current);
    },
    [],
  );

  return (
    <div
      ref={triggerRef}
      className={className}
      onMouseEnter={scheduleShow}
      onMouseLeave={scheduleHide}
      onFocus={scheduleShow}
      onBlur={scheduleHide}
      onClick={onClick}
    >
      {children}
      {pos
        ? createPortal(
            <div
              className="profile-portal"
              style={{ top: pos.top, left: pos.left }}
              onMouseEnter={() => window.clearTimeout(hideTimer.current)}
              onMouseLeave={scheduleHide}
            >
              <ProfilePopover
                person={person}
                coverUrl={coverUrl}
                reports={reports}
                align={align}
                inPortal
                onOpenOrg={onOpenOrg}
                onOpenProfile={onOpenProfile}
              />
            </div>,
            document.body,
          )
        : null}
    </div>
  );
}

function ProfilePopover({
  person,
  coverUrl,
  reports = [],
  align = 'left',
  inPortal = false,
  onOpenOrg,
  onOpenProfile,
}: {
  person: Person;
  coverUrl?: string;
  reports?: Person[];
  align?: 'left' | 'right';
  inPortal?: boolean;
  onOpenOrg?: () => void;
  onOpenProfile?: () => void;
}) {
  const managerProfile = person.employee.manager_profile;
  const reportCount = person.directReportsCount || reports.length;
  return (
    <aside className={`profile-popover ${align}${inPortal ? ' portal' : ''}`} onClick={(event) => event.stopPropagation()}>
      <div className="profile-popover-cover" style={coverUrl ? { backgroundImage: `url("${coverUrl}")` } : undefined} />
      <div className="popover-head">
        <Avatar name={person.fullName} src={person.avatarUrl} accent={person.accent} size="lg" />
        <div className="popover-actions">
          <button
            type="button"
            title="Орг. структура"
            aria-label="Орг. структура"
            onClick={(event) => {
              event.stopPropagation();
              onOpenOrg?.();
            }}
          >
            <Network size={15} />
          </button>
          <button
            type="button"
            title="Відкрити профіль"
            aria-label="Відкрити профіль"
            onClick={(event) => {
              event.stopPropagation();
              onOpenProfile?.();
            }}
          >
            <ArrowUpRight size={15} />
          </button>
        </div>
      </div>
      <strong>{person.fullName}</strong>
      <span>{person.role}</span>
      <ul>
        {person.email && person.email !== '-' ? (
          <li className="popover-email">
            <Mail size={15} />
            <a href={`mailto:${person.email}`} onClick={(event) => event.stopPropagation()}>
              {person.email}
            </a>
          </li>
        ) : null}
        <li>
          <BriefcaseBusiness size={15} />
          {person.department}
        </li>
        <li>
          <MapPin size={15} />
          {person.location}
        </li>
        <li className="popover-manager">
          <Users size={15} />
          {managerProfile ? (
            <Avatar name={person.manager} src={employeeAvatarUrl(managerProfile)} accent="slate" size="sm" />
          ) : null}
          <span>{person.manager}</span>
        </li>
        {reportCount > 0 ? (
          <li className="popover-reports">
            <span className="reports-trigger">
              <Network size={15} />
              <span className="reports-avatars">
                {reports.slice(0, 4).map((report) => (
                  <Avatar key={report.id} name={report.fullName} src={report.avatarUrl} accent={report.accent} size="sm" />
                ))}
              </span>
              <span className="reports-count">{reportCount} direct reports</span>
            </span>
            {reports.length ? (
              <div className="reports-flyout">
                {reports.map((report) => (
                  <div className="reports-flyout-item" key={report.id}>
                    <Avatar name={report.fullName} src={report.avatarUrl} accent={report.accent} size="sm" />
                    <span>
                      <strong>{report.fullName}</strong>
                      <small>{report.role}</small>
                    </span>
                  </div>
                ))}
              </div>
            ) : null}
          </li>
        ) : null}
      </ul>
    </aside>
  );
}

function EmployeeAdminProfileView({
  employee,
  onBack,
  brandingSettings,
  employeeCover,
  onEmployeeCoverChange,
  copy,
}: {
  employee: EmployeeListItem | null;
  onBack: () => void;
  brandingSettings: BrandingSettings;
  employeeCover: CoverCropResult | null;
  onEmployeeCoverChange?: (cover: CoverCropResult) => void;
  copy: AppCopy;
}) {
  const [coverCropOpen, setCoverCropOpen] = useState(false);
  const displayName = employee?.full_name || copy.people.newEmployee;
  const avatarUrl = employeeAvatarUrl(employee);
  const canEditCover = Boolean(employee && brandingSettings.employeeCoverUploadAllowed && onEmployeeCoverChange);
  const canUsePersonalCover = Boolean(brandingSettings.employeeCoverUploadAllowed && employeeCover?.url);
  const shouldShowDefaultCover = !brandingSettings.employeeCoverDisabled;
  const coverVisible = canUsePersonalCover || shouldShowDefaultCover || canEditCover;
  const coverUrl = canUsePersonalCover ? employeeCover?.url || '' : shouldShowDefaultCover ? brandingSettings.employeeCoverUrl : '';
  const mobilePhone = employee?.phone || peopleforceFieldValue(employee, 'mobile_number') || '-';
  const workPhone = employee?.phone2 || peopleforceFieldValue(employee, 'work_phone_number') || '-';
  const interestingFacts = peopleforceFieldValue(employee, 'цікаві_факти') || '-';
  const instagram = peopleforceFieldValue(employee, 'посилання_на_instagram') || '-';
  const facebook = peopleforceFieldValue(employee, 'facebook_url') || '-';
  const fields = [
    [copy.people.employeeId || 'Employee ID', employee?.employee_number || employee?.legacy_peopleforce_id || (employee ? String(employee.id) : '-')],
    [copy.people.lastName || 'Last name', employee?.last_name || '-'],
    [copy.people.firstName || 'First name', employee?.first_name || '-'],
    [copy.people.middleName || 'Middle name', employee?.middle_name || '-'],
    [copy.people.email || 'Email', employee?.email || '-'],
    [copy.people.personalEmail || 'Personal email', employee?.personal_email || '-'],
    [copy.people.birthDate || 'Birth date', employee?.birth_date ? formatDate(employee.birth_date) : '-'],
    [copy.people.gender || 'Gender', employee?.gender ? formatGender(employee.gender) : '-'],
    [copy.people.facts || 'Facts', interestingFacts],
  ];
  const contactFields = [
    [copy.people.mobilePhone || 'Mobile phone', mobilePhone],
    [copy.people.workPhone || 'Work phone', workPhone],
  ];
  const socialFields = [
    ['Instagram', instagram],
    ['Facebook', facebook],
  ];
  const summaryFields = [
    [copy.people.email || 'Email', employee?.email || '-'],
    [copy.people.mobilePhone || 'Mobile phone', mobilePhone],
    [copy.people.startDate, employee?.hired_on ? formatDate(employee.hired_on) : '-'],
    [copy.people.status || 'Status', employee?.peopleforce_status || employee?.status || '-'],
    [copy.people.workType || 'Work type', employee?.employment_type_name || '-'],
    [copy.people.position, employee?.position_name || '-'],
    [copy.people.department, employee?.department_name || '-'],
    [copy.people.division || 'Division', employee?.division_name || '-'],
    [copy.people.location, employee?.clinic_name || '-'],
    [copy.people.level || 'Level', employee?.job_level_name || '-'],
    [copy.people.manager, employee?.manager_name || '-'],
    [copy.people.tenure || 'Tenure', formatTenure(employee?.hired_on ?? null)],
    [copy.people.documents || 'Documents', employee ? String(employee.documents.length) : '-'],
  ];

  return (
    <main className="employee-profile-page">
      <section className={`employee-hero ${coverVisible ? '' : 'no-cover'}`}>
        {coverVisible ? (
          <div
            className={`employee-banner ${coverUrl ? '' : 'empty'}`}
            aria-label="Vidnova Clinic"
            style={coverUrl ? { backgroundImage: `url("${coverUrl}")` } : undefined}
          >
            {canEditCover ? (
              <button type="button" className="employee-cover-edit" aria-label={copy.people.editCover || 'Edit cover'} onClick={() => setCoverCropOpen(true)}>
                <Edit3 size={17} />
              </button>
            ) : null}
          </div>
        ) : null}
        <div className="employee-hero-body">
          <div className="employee-photo">
            {avatarUrl ? <img src={avatarUrl} alt="" /> : <Users size={46} />}
          </div>
          <div className="employee-title">
            <h1>{displayName}</h1>
            <p>
              <BriefcaseBusiness size={16} />
              {employee?.position_name || '-'}
              <MapPin size={16} />
              {employee?.clinic_name || '-'}
            </p>
          </div>
          <div className="employee-actions">
            <button type="button" className="toolbar-icon" onClick={onBack} aria-label={copy.common.previous}>
              <ChevronLeft size={18} />
            </button>
            <button type="button" className="toolbar-icon" aria-label={copy.common.next}>
              <ChevronRight size={18} />
            </button>
            <button type="button" className="toolbar-button">
              {copy.common.actions}
              <ChevronDown size={15} />
            </button>
          </div>
        </div>
        <SectionTabs
          tabs={[
            { key: 'personal', label: copy.people.personal || 'Personal' },
            { key: 'work', label: copy.people.work || 'Work' },
            { key: 'compensation', label: copy.people.compensation || 'Compensation' },
            { key: 'absence', label: copy.people.absence || 'Absence' },
            { key: 'time', label: copy.people.time || 'Time' },
            { key: 'documents', label: copy.people.documents || 'Documents' },
            { key: 'more', label: copy.people.more || 'More' },
          ]}
          active="personal"
          onChange={() => undefined}
        />
      </section>
      {coverCropOpen && onEmployeeCoverChange ? (
        <SettingsCoverCropModal
          title={copy.people.employeeCover || 'Employee cover'}
          onClose={() => setCoverCropOpen(false)}
          onApply={(result) => {
            onEmployeeCoverChange(result);
            setCoverCropOpen(false);
          }}
        />
      ) : null}

      <div className="employee-detail-layout">
        <div className="employee-detail-main">
          <EmployeeInfoPanel title={copy.people.personal || 'Personal'} fields={fields} copy={copy} />
          <EmployeeInfoPanel title={copy.people.contacts || 'Contacts'} fields={contactFields} copy={copy} />
          <EmployeeInfoPanel title={copy.people.social || 'Social networks'} fields={socialFields} copy={copy} />
          <EmployeeInfoPanel
            title={copy.people.documents || 'Documents'}
            fields={employee?.documents.length ? employee.documents.map((document) => [document.name, document.folder_name || document.document_type]) : []}
            copy={copy}
          />
        </div>
        <aside className="employee-summary">
          <h2>{copy.people.profileHome || 'Home'}</h2>
          <div>
            {summaryFields.map(([label, value]) => (
              <div className="summary-field" key={label}>
                <span>{label}</span>
                <strong>{value}</strong>
              </div>
            ))}
          </div>
        </aside>
      </div>
    </main>
  );
}

function EmployeeInfoPanel({ title, fields, copy }: { title: string; fields: string[][]; copy: AppCopy }) {
  return (
    <section className="panel employee-info-panel">
      <div className="panel-title">
        <h2>{title}</h2>
        <button type="button">
          <FileText size={15} />
          {copy.people.edit || 'Edit'}
        </button>
      </div>
      {fields.length ? (
        <div className="field-grid">
          {fields.map(([label, value]) => (
            <div className="field-row" key={label}>
              <span>{label}</span>
              <strong>{value}</strong>
            </div>
          ))}
        </div>
      ) : (
        <EmptyState title={copy.people.dataEmptyTitle} text={copy.people.dataEmptyText} />
      )}
    </section>
  );
}

function CompanyCalendarView({ copy }: { copy: AppCopy }) {
  const [scope, setScope] = useState('company');
  const [employees, setEmployees] = useState<EmployeeListItem[]>([]);
  const [totalEmployees, setTotalEmployees] = useState(0);
  const [search, setSearch] = useState('');
  const [loadState, setLoadState] = useState<LoadState>('idle');
  const days = Array.from({ length: 31 }, (_, index) => index + 1);
  const weekDays = copyArray(copy.calendar.weekdaysShort, ['Ср', 'Чт', 'Пт', 'Сб', 'Нд', 'Пн', 'Вт']);
  const calendarPeople = useMemo(() => employees.map((employee, index) => employeeToPerson(employee, index, copy)), [copy, employees]);

  useEffect(() => {
    let cancelled = false;

    async function loadPeople() {
      setLoadState('loading');
      try {
        const result = await api.employees({ q: search, status: 'active', page_size: 200 });
        if (cancelled) return;
        setEmployees(result.items);
        setTotalEmployees(result.total);
        setLoadState('ok');
      } catch {
        if (cancelled) return;
        setEmployees([]);
        setTotalEmployees(0);
        setLoadState('error');
      }
    }

    void loadPeople();
    return () => {
      cancelled = true;
    };
  }, [search]);

  return (
    <main className="workspace calendar-page">
      <header className="page-header compact">
        <div>
          <h1>{copyValue(copy.calendar.title, 'Календар')}</h1>
          <div className="segmented">
            <button type="button" className={scope === 'company' ? 'active' : ''} onClick={() => setScope('company')}>
              {copyValue(copy.calendar.company, 'Компанія')}
            </button>
            <button type="button" className={scope === 'mine' ? 'active' : ''} onClick={() => setScope('mine')}>
              {copyValue(copy.calendar.mine, 'Мої')}
            </button>
          </div>
          <SectionTabs
            tabs={[
              { key: 'schedule', label: copyValue(copy.calendar.schedule, 'Графік') },
              { key: 'calendar', label: copyValue(copy.calendar.calendar, 'Календар') },
            ]}
            active="schedule"
            onChange={() => undefined}
          />
        </div>
        <button type="button" className="primary-action">
          <Plus size={18} />
          {copyValue(copy.calendar.requestTimeOff, copy.home.requestTimeOff)}
        </button>
      </header>

      <div className="calendar-toolbar">
        <div className="month-controls">
          <button type="button" className="toolbar-icon">
            <ChevronLeft size={18} />
          </button>
          <strong>{copyValue(copy.calendar.monthTitle, 'лип, 2026')}</strong>
          <button type="button" className="toolbar-icon">
            <ChevronRight size={18} />
          </button>
          <button type="button" className="toolbar-icon">
            <Clock3 size={18} />
          </button>
          <button type="button" className="toolbar-button">
            <ListChecks size={18} />
            {copy.common.addFilter}
          </button>
        </div>
        <div className="calendar-tools-right">
          <label className="small-search">
            <Search size={18} />
            <input type="search" placeholder={copy.common.search} value={search} onChange={(event) => setSearch(event.target.value)} />
          </label>
          <button type="button" className="toolbar-button">
            <Settings size={18} />
            {copy.common.viewSettings}
            <span>2</span>
            <ChevronDown size={15} />
          </button>
        </div>
      </div>

      <div className="calendar-count">
        {loadState === 'loading' ? copy.common.loading : resultMetaLabel(calendarPeople.length, totalEmployees, copy)}
      </div>
      <div className="schedule-shell">
        <div className="schedule-grid header-row">
          <div className="employee-head" />
          {days.map((day) => (
            <div className="day-head" key={day}>
              <strong>{day}</strong>
              <span>{weekDays[(day - 1) % 7]}</span>
            </div>
          ))}
        </div>
        {calendarPeople.length ? calendarPeople.map((person) => {
          const band = leaveBands.find((item) => item.personId === person.id);
          return (
            <div className="schedule-grid schedule-row" key={person.id}>
              <div className="schedule-person">
                <Avatar name={person.fullName} accent={person.accent} size="sm" />
                <div>
                  <strong>{person.fullName}</strong>
                  <span>{person.role}</span>
                </div>
              </div>
              {days.map((day) => (
                <div className="schedule-day" key={day}>
                  {[15, 27].includes(day) ? <Star size={14} /> : null}
                </div>
              ))}
              {band ? (
                <div className="leave-band" style={{ gridColumn: `${band.start + 1} / span ${band.span}` }}>
                  <CalendarCheck size={15} />
                  {band.label}
                </div>
              ) : null}
            </div>
          );
        }) : (
          <div className="schedule-empty">
            <EmptyState
              title={loadState === 'error' ? copyValue(copy.calendar.loadErrorTitle, 'Не вдалося завантажити календар') : copyValue(copy.calendar.notLoadedTitle, 'Календар не завантажений')}
              text={loadState === 'error' ? copy.common.backendRetry : copyValue(copy.calendar.emptyText, 'За вибраним пошуком немає активних співробітників.')}
            />
          </div>
        )}
      </div>
    </main>
  );
}

function AttendanceCalendar({ workdays, copy }: { workdays: WorkDaySummary[]; copy: AppCopy }) {
  const byDate = useMemo(() => new Map(workdays.map((item) => [item.date, item])), [workdays]);
  const monthDays = useMemo(() => getMonthDays(2026, 5), []);
  const blanks = new Date(2026, 5, 1).getDay() === 0 ? 6 : new Date(2026, 5, 1).getDay() - 1;
  const weekDays = copyArray(copy.calendar.weekdaysShort, ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Нд']);

  return (
    <div className="attendance-calendar">
      {weekDays.map((day) => (
        <div className="weekday" key={day}>
          {day}
        </div>
      ))}
      {Array.from({ length: blanks }, (_, index) => (
        <div className="day-cell muted-cell" key={`blank-${index}`} />
      ))}
      {monthDays.map((date) => {
        const item = byDate.get(date);
        const planned = item?.planned_minutes ?? 0;
        const actual = item?.actual_minutes ?? 0;
        const delta = actual - planned;
        const day = Number(date.slice(-2));
        const hasLeave = [13, 14, 15, 16].includes(day);
        const isHoliday = day === 28;
        return (
          <div className={`day-cell ${date === '2026-06-24' ? 'today' : ''}`} key={date}>
            <div className="day-title">
              <strong>{day} Черв.</strong>
              {hasLeave ? <CalendarCheck size={18} className="day-icon" /> : null}
              {isHoliday ? <Star size={18} className="day-star" /> : null}
            </div>
            <div className={`delta-bar ${delta > 0 ? 'positive' : delta < 0 ? 'negative' : 'neutral'}`}>
              {delta === 0 ? '' : `${delta > 0 ? '+' : '-'}${minutesToText(Math.abs(delta))}`}
            </div>
            <div className="day-hours">
              <span>
                W <strong>{minutesToText(actual)}</strong>
              </span>
              <span>
                E <strong>{minutesToText(planned)}</strong>
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function AttendanceView(props: {
  copy: AppCopy;
  brandingSettings: BrandingSettings;
  employeeCovers: EmployeeCoverMap;
}) {
  const location = useLocation();
  const attendanceRoute = useMemo(() => attendanceRouteFromPathname(location.pathname), [location.pathname]);
  if (attendanceRoute.mode === 'employee') {
    return <EmployeeAttendanceDetailView {...props} employeeId={attendanceRoute.id} />;
  }
  return <CompanyAttendanceView {...props} />;
}

function CompanyAttendanceView({
  copy,
  brandingSettings,
  employeeCovers,
}: {
  copy: AppCopy;
  brandingSettings: BrandingSettings;
  employeeCovers: EmployeeCoverMap;
}) {
  const navigate = useNavigate();
  const [month, setMonth] = useState(getInitialMonth);
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [rows, setRows] = useState<CompanyAttendanceSummary[]>([]);
  const [totalRows, setTotalRows] = useState(0);
  const [loadState, setLoadState] = useState<LoadState>('idle');
  const [employeeById, setEmployeeById] = useState<Map<number, EmployeeListItem>>(new Map());
  const range = useMemo(() => getMonthRange(month), [month]);
  const visibleRows = useMemo(() => rows.map(attendanceSummaryToRow), [rows]);
  const pageSize = 25;

  useEffect(() => {
    api
      .employees({ status: 'active', page_size: 500 })
      .then((result) => setEmployeeById(new Map(result.items.map((emp) => [emp.id, emp]))))
      .catch(() => setEmployeeById(new Map()));
  }, []);

  useEffect(() => {
    setPage(1);
  }, [range.from, range.to, search]);

  useEffect(() => {
    let cancelled = false;

    async function loadAttendance() {
      setLoadState('loading');
      try {
        const result = await api.companyAttendance({
          from: range.from,
          to: range.to,
          q: search,
          employee_status: 'active',
          page,
          page_size: pageSize,
        });
        if (cancelled) return;
        setRows(result.items);
        setTotalRows(result.total);
        setLoadState('ok');
      } catch {
        if (cancelled) return;
        setRows([]);
        setTotalRows(0);
        setLoadState('error');
      }
    }

    void loadAttendance();
    return () => {
      cancelled = true;
    };
  }, [range.from, range.to, search, page]);

  const totalPages = Math.max(1, Math.ceil(totalRows / pageSize));

  return (
    <main className="workspace attendance-page attendance-company-page">
      <header className="page-header compact attendance-company-header">
        <div>
          <div className="title-with-segment">
            <h1>{copyValue(copy.attendance.title, 'Відвідуваність')}</h1>
            <div className="segmented">
              <button type="button" className="active">
                {copyValue(copy.attendance.company, 'Компанія')}
              </button>
              <button type="button">{copyValue(copy.attendance.mine, 'Мої')}</button>
            </div>
          </div>
          <SectionTabs
            tabs={[
              { key: 'main', label: copyValue(copy.attendance.main, 'Головна') },
              { key: 'overtime', label: copyValue(copy.attendance.overtime, 'Понаднормово') },
            ]}
            active="main"
            onChange={() => undefined}
          />
        </div>
        <div className="header-actions">
          <button type="button" className="secondary-action">
            <Settings size={18} />
            {copyValue(copy.attendance.projectManagement, 'Управління проектами')}
          </button>
          <button type="button" className="secondary-action">
            <FileText size={18} />
            {copyValue(copy.attendance.export, copy.common.export)}
          </button>
        </div>
      </header>

      <div className="attendance-search-row attendance-controls-row">
        <label className="wide-search">
          <Search size={18} />
          <input
            type="search"
            placeholder={copyValue(copy.attendance.searchPlaceholder, "Пошук за ім'ям...")}
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </label>
        <button type="button" className="toolbar-button">
          <Filter size={16} />
          {copy.common.filter}
        </button>
        <div className="month-controls">
          <button type="button" className="toolbar-button strong" onClick={() => setMonth(getInitialMonth())}>
            {copyValue(copy.attendance.currentMonth, 'Поточний місяць')}
          </button>
          <button
            type="button"
            className="toolbar-icon"
            onClick={() => setMonth((current) => new Date(current.getFullYear(), current.getMonth() - 1, 1))}
            aria-label={copyValue(copy.attendance.previousMonth, 'Попередній місяць')}
          >
            <ChevronLeft size={16} />
          </button>
          <button
            type="button"
            className="toolbar-icon"
            onClick={() => setMonth((current) => new Date(current.getFullYear(), current.getMonth() + 1, 1))}
            aria-label={copyValue(copy.attendance.nextMonth, 'Наступний місяць')}
          >
            <ChevronRight size={16} />
          </button>
          <span>{formatMonthTitle(month, copy)}</span>
        </div>
        <button type="button" className="secondary-action attendance-reminder-btn">
          <Bell size={16} />
          {copyValue(copy.attendance.sendReminder, 'Надіслати нагадування')}
        </button>
      </div>

      <div className="result-meta attendance-meta">
        <span>
          {loadState === 'loading'
            ? copy.common.loading
            : totalRows === 0
              ? resultMetaLabel(0, 0, copy)
              : `${(page - 1) * pageSize + 1}-${(page - 1) * pageSize + visibleRows.length} / ${totalRows}`}
        </span>
        {totalRows > pageSize ? (
          <div className="pagination">
            <button type="button" aria-label={copy.common.previous} disabled={page <= 1} onClick={() => setPage((current) => Math.max(1, current - 1))}>
              <ChevronLeft size={16} />
            </button>
            {buildPageItems(page, totalPages).map((item, index) =>
              item === 'gap' ? (
                <span key={`gap-${index}`} className="page-gap">
                  …
                </span>
              ) : (
                <button type="button" key={item} className={item === page ? 'active' : ''} onClick={() => setPage(item)}>
                  {item}
                </button>
              ),
            )}
            <button type="button" aria-label={copy.common.next} disabled={page >= totalPages} onClick={() => setPage((current) => Math.min(totalPages, current + 1))}>
              <ChevronRight size={16} />
            </button>
          </div>
        ) : null}
      </div>

      <AttendanceSummaryTable
        rows={visibleRows}
        loadState={loadState}
        copy={copy}
        employeeById={employeeById}
        brandingSettings={brandingSettings}
        employeeCovers={employeeCovers}
        onOpenProfile={(employeeId) => navigate(peopleEmployeePath(employeeId))}
        onOpenAttendance={(employeeId) => navigate(attendanceEmployeePath(employeeId, monthQueryValue(month)))}
        onOpenOrg={() => navigate('/people/org')}
      />
    </main>
  );
}

function AttendanceSummaryTable({
  rows,
  loadState,
  copy,
  employeeById,
  brandingSettings,
  employeeCovers,
  onOpenProfile,
  onOpenAttendance,
  onOpenOrg,
}: {
  rows: AttendanceSummaryRow[];
  loadState: LoadState;
  copy: AppCopy;
  employeeById: Map<number, EmployeeListItem>;
  brandingSettings: BrandingSettings;
  employeeCovers: EmployeeCoverMap;
  onOpenProfile: (employeeId: number) => void;
  onOpenAttendance: (employeeId: number) => void;
  onOpenOrg: () => void;
}) {
  const emptyTitle =
    loadState === 'loading'
      ? copyValue(copy.attendance.emptyLoading, 'Завантаження присутності')
      : loadState === 'error'
        ? copyValue(copy.attendance.emptyError, 'Не вдалося завантажити присутність')
        : copyValue(copy.attendance.emptyNotFound, 'Дані присутності не знайдені');
  const emptyText =
    loadState === 'loading'
      ? copyValue(copy.attendance.emptyLoadingText, 'Формується компанійна таблиця за вибраний місяць.')
      : loadState === 'error'
        ? copy.common.backendRetry
        : copyValue(copy.attendance.emptyNotFoundText, 'За вибраним місяцем або пошуком немає активних співробітників.');
  const headers = copyArray(copy.attendance.tableHeaders, [
    "Повне ім'я",
    'Очікувано',
    'Відпрацьовано',
    'Понаднормово',
    'Перерва',
    'Оплачувана відсутність',
    'Неоплачувана відсутність',
    'Загалом відсутності',
    'Різниця',
  ]);

  return (
    <div className="table-shell attendance-table-shell">
      <table className="attendance-summary-table">
        <thead>
          <tr>
            {headers.map((header) => (
              <th key={header}>{header}</th>
            ))}
            <th />
          </tr>
        </thead>
        <tbody>
          {rows.length ? (
            rows.map((row, index) => {
              const employee = employeeById.get(row.employeeId);
              const person = employee ? employeeToPerson(employee, index, copy) : null;
              return (
              <tr
                key={row.id}
                className="clickable-row"
                tabIndex={0}
                onClick={() => onOpenAttendance(row.employeeId)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' || event.key === ' ') {
                    event.preventDefault();
                    onOpenAttendance(row.employeeId);
                  }
                }}
              >
                <td className="name-cell">
                  {employee && person ? (
                    <ProfileHoverCard
                      className="person-name"
                      person={person}
                      coverUrl={resolveEmployeeCoverUrl(employee.id, brandingSettings, employeeCovers)}
                      onOpenProfile={() => onOpenProfile(employee.id)}
                      onOpenOrg={onOpenOrg}
                    >
                      <Avatar name={person.fullName} src={person.avatarUrl} accent={person.accent} size="sm" />
                      <span>{row.fullName}</span>
                    </ProfileHoverCard>
                  ) : (
                    <div className="person-name">
                      <Avatar name={row.fullName} src="" accent="slate" size="sm" />
                      <span>{row.fullName}</span>
                    </div>
                  )}
                </td>
                <td data-label={headers[1]}>{row.expected}</td>
                <td data-label={headers[2]}>{row.worked}</td>
                <td data-label={headers[3]}>{row.overtime}</td>
                <td data-label={headers[4]}>{row.breakTime}</td>
                <td data-label={headers[5]}>{row.paidAbsence}</td>
                <td data-label={headers[6]}>{row.unpaidAbsence}</td>
                <td data-label={headers[7]}>{row.totalAbsence}</td>
                <td data-label={headers[8]}>{row.difference}</td>
                <td>
                  <button
                    type="button"
                    className="row-action"
                    aria-label={copyValue(copy.attendance.rowActions, copy.common.actions)}
                    onClick={(event) => {
                      event.stopPropagation();
                      onOpenAttendance(row.employeeId);
                    }}
                  >
                    <FileText size={16} />
                  </button>
                </td>
              </tr>
              );
            })
          ) : (
            <tr>
              <td colSpan={10}>
                <EmptyState title={emptyTitle} text={emptyText} />
              </td>
            </tr>
          )}
        </tbody>
      </table>
      </div>
  );
}

function EmployeeAttendanceDetailView({
  employeeId,
  copy,
}: {
  employeeId: number;
  copy: AppCopy;
}) {
  const navigate = useNavigate();
  const location = useLocation();
  const [month, setMonth] = useState(() => monthFromAttendanceSearch(location.search));
  const [viewMode, setViewMode] = useState<'calendar' | 'list'>('calendar');
  const [detail, setDetail] = useState<EmployeeAttendanceDetail | null>(null);
  const [loadState, setLoadState] = useState<LoadState>('idle');
  const [selectedDayDate, setSelectedDayDate] = useState<string | null>(null);
  const [editingPeriodId, setEditingPeriodId] = useState<number | null>(null);
  const [periodFormMode, setPeriodFormMode] = useState<'closed' | 'create' | 'edit'>('closed');
  const [periodForm, setPeriodForm] = useState<AttendancePeriodFormState>(() => attendancePeriodFormFromPeriod());
  const [drawerBusy, setDrawerBusy] = useState(false);
  const [drawerError, setDrawerError] = useState('');
  const [deletePeriodTarget, setDeletePeriodTarget] = useState<EmployeeAttendancePeriod | null>(null);
  const range = useMemo(() => getMonthRange(month), [month]);
  const selectedDay = useMemo(
    () => (selectedDayDate ? detail?.days.find((day) => day.date === selectedDayDate) ?? emptyEmployeeAttendanceDay(selectedDayDate) : null),
    [detail?.days, selectedDayDate],
  );

  useEffect(() => {
    setMonth(monthFromAttendanceSearch(location.search));
  }, [employeeId, location.search]);

  useEffect(() => {
    let cancelled = false;

    async function loadDetail() {
      setLoadState('loading');
      try {
        const result = await api.employeeAttendance(employeeId, range);
        if (cancelled) return;
        setDetail(result);
        setLoadState('ok');
      } catch {
        if (cancelled) return;
        setDetail(null);
        setLoadState('error');
      }
    }

    void loadDetail();
    return () => {
      cancelled = true;
    };
  }, [employeeId, range.from, range.to]);

  function changeMonth(nextMonth: Date) {
    setMonth(nextMonth);
    navigate(attendanceEmployeePath(employeeId, monthQueryValue(nextMonth)), { replace: true });
  }

  async function reloadDetail() {
    const result = await api.employeeAttendance(employeeId, range);
    setDetail(result);
    setLoadState('ok');
    return result;
  }

  function openDayDrawer(day: EmployeeAttendanceDay) {
    setSelectedDayDate(day.date);
    setEditingPeriodId(null);
    setPeriodFormMode('closed');
    setPeriodForm(attendancePeriodFormFromPeriod());
    setDrawerError('');
  }

  function startCreatePeriod() {
    setEditingPeriodId(null);
    setPeriodFormMode('create');
    setPeriodForm(attendancePeriodFormFromPeriod());
    setDrawerError('');
  }

  function startEditPeriod(period: EmployeeAttendancePeriod) {
    setEditingPeriodId(period.id);
    setPeriodFormMode('edit');
    setPeriodForm(attendancePeriodFormFromPeriod(period));
    setDrawerError('');
  }

  async function savePeriod(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedDayDate) return;
    setDrawerBusy(true);
    setDrawerError('');
    try {
      const payload = { date: selectedDayDate, ...periodForm };
      if (editingPeriodId) {
        await api.updateEmployeeAttendancePeriod(employeeId, editingPeriodId, payload);
      } else {
        await api.createEmployeeAttendancePeriod(employeeId, payload);
      }
      await reloadDetail();
      setEditingPeriodId(null);
      setPeriodFormMode('closed');
      setPeriodForm(attendancePeriodFormFromPeriod());
    } catch {
      setDrawerError('Не вдалося зберегти запис. Перевірте час початку та завершення.');
    } finally {
      setDrawerBusy(false);
    }
  }

  async function confirmDeletePeriod() {
    if (!deletePeriodTarget) return;
    setDrawerBusy(true);
    setDrawerError('');
    try {
      await api.deleteEmployeeAttendancePeriod(employeeId, deletePeriodTarget.id);
      await reloadDetail();
      if (editingPeriodId === deletePeriodTarget.id) {
        setEditingPeriodId(null);
        setPeriodFormMode('closed');
        setPeriodForm(attendancePeriodFormFromPeriod());
      }
      setDeletePeriodTarget(null);
    } catch {
      setDrawerError('Не вдалося видалити запис.');
    } finally {
      setDrawerBusy(false);
    }
  }

  const employee = detail?.employee;
  const summary = detail?.summary;
  const role = [employee?.position_name, employee?.department_name].filter(Boolean).join(' · ') || 'Співробітник';
  const absenceMinutes = (summary?.paid_absence_minutes ?? 0) + (summary?.unpaid_absence_minutes ?? 0);

  return (
    <main className="workspace attendance-page attendance-detail-page">
      <header className="page-header compact profile-header attendance-detail-header">
        <div className="profile-back">
          <button type="button" onClick={() => navigate('/attendance')}>
            <ChevronLeft size={16} />
            Назад
          </button>
          <div className="profile-person">
            <Avatar
              name={employee?.full_name || 'Співробітник'}
              src={employeeAvatarUrl(employee)}
              accent={employeeAccentClasses[employeeId % employeeAccentClasses.length]}
              size="lg"
            />
            <div>
              <strong>{employee?.full_name || (loadState === 'loading' ? copy.common.loading : 'Співробітник')}</strong>
              <span>{role}</span>
            </div>
          </div>
        </div>
        <div className="header-actions">
          <button type="button" className="toolbar-icon" aria-label={copy.common.actions}>
            <MoreHorizontal size={18} />
          </button>
          <button type="button" className="secondary-action">
            <Sparkles size={16} />
            Автозаповнення
          </button>
          <button type="button" className="secondary-action" onClick={() => navigate(peopleEmployeePath(employeeId))}>
            <ArrowUpRight size={16} />
            Профіль
          </button>
        </div>
      </header>

      <div className="attendance-detail-toolbar">
        <div className="month-controls">
          <button type="button" className="toolbar-button strong" onClick={() => changeMonth(getInitialMonth())}>
            {copyValue(copy.attendance.currentMonth, 'Поточний місяць')}
          </button>
          <button
            type="button"
            className="toolbar-icon"
            onClick={() => changeMonth(new Date(month.getFullYear(), month.getMonth() - 1, 1))}
            aria-label={copyValue(copy.attendance.previousMonth, 'Попередній місяць')}
          >
            <ChevronLeft size={16} />
          </button>
          <button
            type="button"
            className="toolbar-icon"
            onClick={() => changeMonth(new Date(month.getFullYear(), month.getMonth() + 1, 1))}
            aria-label={copyValue(copy.attendance.nextMonth, 'Наступний місяць')}
          >
            <ChevronRight size={16} />
          </button>
          <span>{formatMonthTitle(month, copy)}</span>
        </div>
        <div className="attendance-detail-view-actions">
          <select aria-label="Проект" defaultValue="">
            <option value="">Виберіть проект</option>
          </select>
          <button
            type="button"
            className={`toolbar-icon ${viewMode === 'calendar' ? 'active' : ''}`}
            aria-label="Календар"
            onClick={() => setViewMode('calendar')}
          >
            <Grid3X3 size={16} />
          </button>
          <button
            type="button"
            className={`toolbar-icon ${viewMode === 'list' ? 'active' : ''}`}
            aria-label="Список"
            onClick={() => setViewMode('list')}
          >
            <List size={16} />
          </button>
        </div>
      </div>

      <div className="metric-row five attendance-detail-metrics">
        <MetricCard label="Очікувано" value={minutesToText(summary?.planned_minutes ?? 0)} />
        <MetricCard label="Відпрацьовано" value={minutesToText(summary?.actual_minutes ?? 0)} />
        <MetricCard label="Понаднормово" value={minutesToText(summary?.overtime_minutes ?? 0)} />
        <MetricCard label="Відсутності" value={minutesToText(absenceMinutes)} />
        <MetricCard label="Різниця" value={signedMinutesToText(summary?.difference_minutes ?? 0)} danger={(summary?.difference_minutes ?? 0) < 0} />
      </div>

      <div className="attendance-detail-body">
        {loadState === 'error' ? (
          <EmptyState title="Не вдалося завантажити табель" text={copy.common.backendRetry} />
        ) : viewMode === 'calendar' ? (
          <EmployeeAttendanceCalendar
            days={detail?.days ?? []}
            month={month}
            copy={copy}
            loadState={loadState}
            selectedDate={selectedDayDate}
            onOpenDay={openDayDrawer}
          />
        ) : (
          <EmployeeAttendanceList days={detail?.days ?? []} copy={copy} loadState={loadState} onOpenDay={openDayDrawer} />
        )}
      </div>

      {selectedDay ? (
        <AttendanceDayDrawer
          day={selectedDay}
          copy={copy}
          form={periodForm}
          busy={drawerBusy}
          error={drawerError}
          formMode={periodFormMode}
          editingPeriodId={editingPeriodId}
          onFormChange={setPeriodForm}
          onSave={savePeriod}
          onCancelForm={() => {
            setPeriodFormMode('closed');
            setEditingPeriodId(null);
            setPeriodForm(attendancePeriodFormFromPeriod());
            setDrawerError('');
          }}
          onClose={() => {
            setSelectedDayDate(null);
            setEditingPeriodId(null);
            setPeriodFormMode('closed');
            setDrawerError('');
          }}
          onCreate={startCreatePeriod}
          onEdit={startEditPeriod}
          onDelete={setDeletePeriodTarget}
        />
      ) : null}
      {deletePeriodTarget ? (
        <AttendancePeriodDeleteConfirmModal
          period={deletePeriodTarget}
          busy={drawerBusy}
          onCancel={() => {
            if (!drawerBusy) setDeletePeriodTarget(null);
          }}
          onConfirm={() => void confirmDeletePeriod()}
        />
      ) : null}
    </main>
  );
}

function EmployeeAttendanceCalendar({
  days,
  month,
  copy,
  loadState,
  selectedDate,
  onOpenDay,
}: {
  days: EmployeeAttendanceDay[];
  month: Date;
  copy: AppCopy;
  loadState: LoadState;
  selectedDate: string | null;
  onOpenDay: (day: EmployeeAttendanceDay) => void;
}) {
  const byDate = useMemo(() => new Map(days.map((item) => [item.date, item])), [days]);
  const monthDays = useMemo(() => getMonthDays(month.getFullYear(), month.getMonth()), [month]);
  const firstDay = new Date(month.getFullYear(), month.getMonth(), 1).getDay();
  const blanks = firstDay === 0 ? 6 : firstDay - 1;
  const weekDays = copyArray(copy.calendar.weekdaysShort, ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Нд']);
  const today = todayIsoDate();

  if (loadState === 'loading' && !days.length) {
    return <EmptyState title={copy.common.loading} text="Формується табель за вибраний місяць." />;
  }

  return (
    <div className="attendance-calendar employee-attendance-calendar">
      {weekDays.map((day) => (
        <div className="weekday" key={day}>
          {day}
        </div>
      ))}
      {Array.from({ length: blanks }, (_, index) => (
        <div className="day-cell muted-cell" key={`blank-${index}`} />
      ))}
      {monthDays.map((dateValue) => {
        const item = byDate.get(dateValue) ?? emptyEmployeeAttendanceDay(dateValue);
        const planned = item?.planned_minutes ?? 0;
        const actual = item?.actual_minutes ?? 0;
        const delta = item?.difference_minutes ?? actual - planned;
        return (
          <div
            className={`day-cell employee-day-cell ${dateValue === today ? 'today' : ''} ${dateValue === selectedDate ? 'selected' : ''}`}
            key={dateValue}
            role="button"
            tabIndex={0}
            onClick={() => onOpenDay(item)}
            onKeyDown={(event) => {
              if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault();
                onOpenDay(item);
              }
            }}
          >
            <div className="day-title">
              {dateValue === today ? <span className="today-pill">{formatAttendanceDayShort(dateValue, copy)}</span> : <strong>{formatAttendanceDayShort(dateValue, copy)}</strong>}
            </div>
            <div className={`delta-bar ${delta > 0 ? 'positive' : delta < 0 ? 'negative' : 'neutral'}`}>
              {signedMinutesToText(delta)}
            </div>
            <div className="day-hours">
              <span>
                W <strong>{minutesToText(actual)}</strong>
              </span>
              <span>
                E <strong>{minutesToText(planned)}</strong>
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function EmployeeAttendanceList({
  days,
  copy,
  loadState,
  onOpenDay,
}: {
  days: EmployeeAttendanceDay[];
  copy: AppCopy;
  loadState: LoadState;
  onOpenDay: (day: EmployeeAttendanceDay) => void;
}) {
  if (loadState === 'loading' && !days.length) {
    return <EmptyState title={copy.common.loading} text="Формується список днів за вибраний місяць." />;
  }

  return (
    <div className="table-shell attendance-table-shell employee-attendance-list-shell">
      <table className="attendance-summary-table employee-attendance-list">
        <thead>
          <tr>
            <th>День / Дата</th>
            <th>Очікувано</th>
            <th>Відпрацьовано</th>
            <th>Початок / кінець</th>
            <th>Понаднормово</th>
            <th>Перерва</th>
            <th>Відсутності</th>
            <th>Загалом відпрацьовано</th>
            <th>Різниця</th>
          </tr>
        </thead>
        <tbody>
          {days.length ? (
            days.map((day) => (
              <tr
                key={day.date}
                className="clickable-row"
                tabIndex={0}
                onClick={() => onOpenDay(day)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' || event.key === ' ') {
                    event.preventDefault();
                    onOpenDay(day);
                  }
                }}
              >
                <td className="date-cell">{formatAttendanceListDate(day.date, copy)}</td>
                <td>{minutesToText(day.planned_minutes)}</td>
                <td>{minutesToText(day.actual_minutes)}</td>
                <td>
                  <div className="period-list">
                    {day.periods.length ? (
                      day.periods.map((period) => (
                        <span key={period.id}>
                          <Edit3 size={13} />
                          {formatTime(period.start_at)} - {formatTime(period.end_at)}
                        </span>
                      ))
                    ) : (
                      <span className="muted-period">-</span>
                    )}
                  </div>
                </td>
                <td>{day.overtime_minutes ? minutesToText(day.overtime_minutes) : '-'}</td>
                <td>{minutesToText(day.break_minutes)}</td>
                <td>{minutesToText(day.paid_absence_minutes + day.unpaid_absence_minutes)}</td>
                <td>{minutesToText(day.actual_minutes)}</td>
                <td className={day.difference_minutes < 0 ? 'negative-diff' : day.difference_minutes > 0 ? 'positive-diff' : ''}>
                  {signedMinutesToText(day.difference_minutes)}
                </td>
              </tr>
            ))
          ) : (
            <tr>
              <td colSpan={9}>
                <EmptyState title="Табель порожній" text="За вибраний місяць немає даних присутності." />
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

function AttendanceDayDrawer({
  day,
  copy,
  form,
  formMode,
  busy,
  error,
  editingPeriodId,
  onFormChange,
  onSave,
  onCancelForm,
  onClose,
  onCreate,
  onEdit,
  onDelete,
}: {
  day: EmployeeAttendanceDay;
  copy: AppCopy;
  form: AttendancePeriodFormState;
  formMode: 'closed' | 'create' | 'edit';
  busy: boolean;
  error: string;
  editingPeriodId: number | null;
  onFormChange: (value: AttendancePeriodFormState) => void;
  onSave: (event: FormEvent<HTMLFormElement>) => void;
  onCancelForm: () => void;
  onClose: () => void;
  onCreate: () => void;
  onEdit: (period: EmployeeAttendancePeriod) => void;
  onDelete: (period: EmployeeAttendancePeriod) => void;
}) {
  const absenceMinutes = day.paid_absence_minutes + day.unpaid_absence_minutes;
  const editingPeriod = editingPeriodId ? day.periods.find((period) => period.id === editingPeriodId) : null;
  return (
    <aside className="attendance-day-drawer" aria-label="Записи дня">
      <header className="attendance-day-drawer-header">
        <strong>{formatAttendanceDrawerTitle(day.date, copy)}</strong>
        <button type="button" className="toolbar-icon" aria-label="Закрити" onClick={onClose}>
          <X size={18} />
        </button>
      </header>

      <div className="attendance-day-drawer-stats">
        <span>
          Відпрацьовано
          <strong>{minutesToText(day.actual_minutes)}</strong>
        </span>
        <span>
          Відсутності
          <strong>{absenceMinutes ? minutesToText(absenceMinutes) : '-'}</strong>
        </span>
        <span>
          Очікувано
          <strong>{minutesToText(day.planned_minutes)}</strong>
        </span>
      </div>

      {formMode !== 'closed' ? (
        <form className="attendance-period-form" onSubmit={onSave}>
          <label>
            <span>Виберіть проект</span>
            <select defaultValue="">
              <option value="">Виберіть проект</option>
            </select>
          </label>
          <div className="attendance-period-form-grid">
            <label>
              <span>Почати роботу</span>
              <div className="time-field">
                <Clock3 size={14} />
                <input
                  type="time"
                  value={form.start_time}
                  onChange={(event) => onFormChange({ ...form, start_time: event.target.value })}
                  required
                />
              </div>
            </label>
            <label>
              <span>Закінчити роботу</span>
              <div className="time-field">
                <Clock3 size={14} />
                <input
                  type="time"
                  value={form.end_time}
                  onChange={(event) => onFormChange({ ...form, end_time: event.target.value })}
                  required
                />
              </div>
            </label>
          </div>
          <label>
            <span>Коментар</span>
            <textarea value={form.comment} onChange={(event) => onFormChange({ ...form, comment: event.target.value })} rows={4} />
          </label>
          {error ? <p className="attendance-drawer-error">{error}</p> : null}
          <div className="attendance-period-form-actions">
            <button type="button" className="secondary-action" onClick={onCancelForm} disabled={busy}>
              Скасувати
            </button>
            <button type="submit" className="primary-action" disabled={busy}>
              Зберегти
            </button>
          </div>
        </form>
      ) : null}

      <div className="attendance-day-records">
        {day.periods.length ? (
          day.periods.map((period, index) => (
            <div className={`attendance-record-card ${editingPeriod?.id === period.id ? 'editing' : ''}`} key={period.id}>
              <div className="attendance-record-head">
                <span>
                  <Edit3 size={13} />
                  Запис #{index + 1}
                </span>
                <div>
                  <button type="button" aria-label="Редагувати запис" onClick={() => onEdit(period)} disabled={busy}>
                    <Edit3 size={15} />
                  </button>
                  <button type="button" aria-label="Видалити запис" onClick={() => onDelete(period)} disabled={busy}>
                    <Trash2 size={15} />
                  </button>
                </div>
              </div>
              <div className="attendance-record-body">
                <div>
                  <span className="status-dot" />
                  <strong>Почати роботу</strong>
                  <time>{formatTime(period.start_at)}</time>
                </div>
                <div>
                  <span className="status-dot" />
                  <strong>Закінчити роботу</strong>
                  <time>{formatTime(period.end_at)}</time>
                  <em>
                    <Clock3 size={12} />
                    {minutesToText(period.duration_minutes)}
                  </em>
                </div>
              </div>
            </div>
          ))
        ) : (
          <div className="attendance-record-empty">Записів за день ще немає</div>
        )}
      </div>

      <button type="button" className="secondary-action attendance-new-period" onClick={onCreate} disabled={busy}>
        <Plus size={17} />
        Новий запис
      </button>
    </aside>
  );
}

function AttendancePeriodDeleteConfirmModal({
  period,
  busy,
  onCancel,
  onConfirm,
}: {
  period: EmployeeAttendancePeriod;
  busy: boolean;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  return (
    <div className="settings-option-modal-layer" role="dialog" aria-modal="true" aria-label="Видалити запис часу">
      <button type="button" className="settings-option-modal-backdrop" aria-label="Скасувати" onClick={onCancel} />
      <section className="settings-option-modal settings-delete-modal">
        <header>
          <strong>Видалити запис часу?</strong>
          <button type="button" className="modal-close" aria-label="Скасувати" onClick={onCancel}>
            <X size={18} />
          </button>
        </header>
        <p>
          Запис {formatTime(period.start_at)} - {formatTime(period.end_at)} буде видалено з табеля. Цю дію не можна
          скасувати.
        </p>
        <footer>
          <button type="button" className="secondary-action" onClick={onCancel} disabled={busy}>
            Скасувати
          </button>
          <button type="button" className="danger-action" onClick={onConfirm} disabled={busy}>
            Видалити
          </button>
        </footer>
      </section>
    </div>
  );
}

function emptyEmployeeAttendanceDay(date: string): EmployeeAttendanceDay {
  return {
    date,
    planned_minutes: 0,
    actual_minutes: 0,
    overtime_minutes: 0,
    break_minutes: 0,
    paid_absence_minutes: 0,
    unpaid_absence_minutes: 0,
    total_absence_minutes: 0,
    difference_minutes: 0,
    first_entry_at: null,
    last_exit_at: null,
    status: '',
    exception_count: 0,
    working_pattern_names: [],
    periods: [],
  };
}

function formatAttendanceDayShort(value: string, copy: AppCopy): string {
  const date = new Date(`${value}T00:00:00`);
  const month = new Intl.DateTimeFormat(dateLocaleForCopy(copy), { month: 'short' }).format(date).replace('.', '');
  return `${date.getDate()} ${month}`;
}

function formatAttendanceDrawerTitle(value: string, copy: AppCopy): string {
  const date = new Date(`${value}T00:00:00`);
  const formatted = new Intl.DateTimeFormat(dateLocaleForCopy(copy), {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    weekday: 'long',
  })
    .format(date)
    .replace(' р.', '')
    .replace('.', '');
  return formatted.charAt(0).toUpperCase() + formatted.slice(1);
}

function formatAttendanceListDate(value: string, copy: AppCopy): string {
  const date = new Date(`${value}T00:00:00`);
  const weekday = new Intl.DateTimeFormat(dateLocaleForCopy(copy), { weekday: 'short' }).format(date).replace('.', '');
  return `${date.getDate()} ${weekday}`;
}

function MetricCard({ label, value, danger = false }: { label: string; value: string; danger?: boolean }) {
  return (
    <div className={`metric-card ${danger ? 'danger' : ''}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function RequestsView({
  leave,
  leaveForm,
  setLeaveForm,
  onSubmitLeave,
  copy,
}: {
  leave: SelfLeave;
  leaveForm: { leave_type: string; date_from: string; date_to: string; reason: string };
  setLeaveForm: (value: { leave_type: string; date_from: string; date_to: string; reason: string }) => void;
  onSubmitLeave: (event: FormEvent<HTMLFormElement>) => void;
  copy: AppCopy;
}) {
  const [leaveTypes, setLeaveTypes] = useState<LeaveType[]>(leave.leave_types);
  const [requestRows, setRequestRows] = useState<LeaveRequest[]>(leave.requests);
  const [balanceRows, setBalanceRows] = useState<LeaveBalance[]>([]);
  const [requestTotal, setRequestTotal] = useState(leave.requests.length);
  const [balanceTotal, setBalanceTotal] = useState(0);
  const [loadState, setLoadState] = useState<LoadState>('idle');

  useEffect(() => {
    let cancelled = false;

    async function loadLeave() {
      setLoadState('loading');
      try {
        const [typesResult, requestsResult, balancesResult] = await Promise.all([
          api.leaveTypes({ page_size: 100 }),
          api.leaveRequests({ page_size: 100 }),
          api.leaveBalances({ page_size: 100 }),
        ]);
        if (cancelled) return;
        setLeaveTypes(typesResult.items);
        setRequestRows(requestsResult.items);
        setBalanceRows(balancesResult.items);
        setRequestTotal(requestsResult.total);
        setBalanceTotal(balancesResult.total);
        setLoadState('ok');
        if (!leaveForm.leave_type && typesResult.items[0]) {
          setLeaveForm({ ...leaveForm, leave_type: String(typesResult.items[0].id) });
        }
      } catch {
        if (cancelled) return;
        setLeaveTypes(leave.leave_types);
        setRequestRows(leave.requests);
        setRequestTotal(leave.requests.length);
        setLoadState('error');
      }
    }

    void loadLeave();
    return () => {
      cancelled = true;
    };
  }, [leave.leave_types, leave.requests, leaveForm, setLeaveForm]);

  return (
    <main className="workspace requests-page">
      <header className="page-header">
        <div>
          <h1>{copyValue(copy.requests.title, 'Запити')}</h1>
          <SectionTabs
            tabs={[
              { key: 'mine', label: copyValue(copy.requests.mine, 'Мої запити') },
              { key: 'approvals', label: copyValue(copy.requests.approvals, 'Погодження') },
              { key: 'calendar', label: copyValue(copy.requests.absenceCalendar, 'Календар відсутностей') },
            ]}
            active="mine"
            onChange={() => undefined}
          />
        </div>
        <button type="button" className="primary-action">
          <Plus size={18} />
          {copyValue(copy.requests.newRequest, 'Новий запит')}
        </button>
      </header>

      <div className="requests-layout">
        <form className="panel request-form" onSubmit={onSubmitLeave}>
          <div className="panel-title">
            <h2>{copyValue(copy.requests.newLeaveRequest, 'Новий запит на відпустку')}</h2>
            <CalendarCheck size={18} />
          </div>
          <label>
            <span>{copyValue(copy.requests.type, 'Тип')}</span>
            <select value={leaveForm.leave_type} onChange={(event) => setLeaveForm({ ...leaveForm, leave_type: event.target.value })}>
              {leaveTypes.length ? (
                leaveTypes.map((item) => (
                  <option value={item.id} key={item.id}>
                    {item.name}
                  </option>
                ))
              ) : (
                <option value="">{copyValue(copy.requests.typesNotLoaded, 'Типи заявок не завантажені')}</option>
              )}
            </select>
          </label>
          <div className="form-row two">
            <label>
              <span>{copyValue(copy.requests.from, 'З')}</span>
              <input
                type="date"
                value={leaveForm.date_from}
                onChange={(event) => setLeaveForm({ ...leaveForm, date_from: event.target.value })}
              />
            </label>
            <label>
              <span>{copyValue(copy.requests.to, 'По')}</span>
              <input
                type="date"
                value={leaveForm.date_to}
                onChange={(event) => setLeaveForm({ ...leaveForm, date_to: event.target.value })}
              />
            </label>
          </div>
          <label>
            <span>{copyValue(copy.requests.comment, 'Коментар')}</span>
            <textarea rows={4} value={leaveForm.reason} onChange={(event) => setLeaveForm({ ...leaveForm, reason: event.target.value })} />
          </label>
          <button type="submit" className="primary-action" disabled={!leaveTypes.length}>
            {copyValue(copy.requests.submit, 'Подати заявку')}
          </button>
        </form>

        <section className="panel request-table-panel">
          <div className="panel-title">
            <h2>{copyValue(copy.requests.peopleforceRequests, 'Заявки PeopleForce')}</h2>
            <span>{requestTotal}</span>
          </div>
          <div className="request-list">
            {requestRows.length ? requestRows.map((item) => (
              <article className="request-row large" key={item.id}>
                <div>
                  <strong>{item.employee_name || item.leave_type_name}</strong>
                  <span>{item.leave_type_name}</span>
                  <span>
                    {formatDate(item.date_from)} - {formatDate(item.date_to)}
                    {item.amount ? ` · ${leaveAmountLabel(item.amount, item.tracking_time_in)}` : ''}
                  </span>
                  {item.reason ? <small>{item.reason}</small> : null}
                </div>
                <StatusPill status={item.status} />
              </article>
            )) : (
              <EmptyState
                title={loadState === 'loading' ? copyValue(copy.requests.loadingRequests, 'Завантаження заявок') : copyValue(copy.requests.noRequests, 'Заявок немає')}
                text={loadState === 'error' ? copyValue(copy.requests.loadErrorText, 'Не вдалося завантажити API відсутностей.') : copyValue(copy.requests.noRequestsText, 'За поточним фільтром заявок не знайдено.')}
              />
            )}
          </div>
        </section>
      </div>
      <section className="panel leave-balance-panel">
        <div className="panel-title">
          <h2>{copyValue(copy.requests.absenceBalances, 'Баланси відсутностей')}</h2>
          <span>{balanceTotal}</span>
        </div>
        <div className="table-shell">
          <table className="leave-balance-table">
            <thead>
              <tr>
                <th>{copyValue(copy.requests.employee, 'Співробітник')}</th>
                <th>{copyValue(copy.requests.type, 'Тип')}</th>
                <th>{copyValue(copy.requests.balance, 'Баланс')}</th>
                <th>{copyValue(copy.requests.policy, 'Політика')}</th>
                <th>{copyValue(copy.requests.date, 'Дата')}</th>
              </tr>
            </thead>
            <tbody>
              {balanceRows.length ? (
                balanceRows.map((balance) => (
                  <tr key={balance.id}>
                    <td>{balance.employee_name}</td>
                    <td>{balance.leave_type_name}</td>
                    <td>{leaveAmountLabel(balance.balance, 'days')}</td>
                    <td>{balance.policy_name || '-'}</td>
                    <td>{balance.effective_on ? formatDate(balance.effective_on) : '-'}</td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={5}>
                    <EmptyState title={copyValue(copy.requests.balancesNotFound, 'Баланси не знайдені')} text={copyValue(copy.requests.balancesNotFoundText, 'Баланси відсутностей зʼявляться після імпорту PeopleForce.')} />
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
}

type KnowledgeEditorDraft = {
  id: number | null;
  category: number;
  title: string;
  summary: string;
  cover_url: string;
  body: string;
  status: string;
  created_at?: string | null;
  updated_at?: string | null;
  owner_name?: string;
  view_count?: number;
};

type KnowledgeCategoryDraft = {
  id: number | null;
  name: string;
  description: string;
  parent: string;
  icon_emoji: string;
  visibility_mode: string;
  audience_employee_ids: string;
};

type KnowledgeCategoryTreeNode = {
  category: KnowledgeCategory;
  children: KnowledgeCategoryTreeNode[];
  depth: number;
  ownDocumentCount: number;
  totalDocumentCount: number;
};

type KnowledgeNavRow =
  | { type: 'category'; node: KnowledgeCategoryTreeNode }
  | { type: 'document'; document: KnowledgeDocument; depth: number };

type KnowledgeManagerDragItem = {
  type: 'category' | 'document';
  id: number;
};

type KnowledgeRoute =
  | { mode: 'home' }
  | { mode: 'manage' }
  | { mode: 'category'; id: number }
  | { mode: 'document'; id: number }
  | { mode: 'edit'; id: number }
  | { mode: 'new'; categoryId: number | null };

function positiveRouteId(value: string | undefined): number | null {
  if (!value) return null;
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : null;
}

function knowledgeRouteFromLocation(pathname: string, search: string): KnowledgeRoute {
  const [sectionName, resource, idSegment, action] = pathname.split('/').filter(Boolean);
  if (sectionName !== 'knowledge') return { mode: 'home' };
  if (!resource) return { mode: 'home' };
  if (resource === 'manage') return { mode: 'manage' };
  if (resource === 'new') {
    return { mode: 'new', categoryId: positiveRouteId(new URLSearchParams(search).get('category') ?? undefined) };
  }
  const id = positiveRouteId(idSegment);
  if (!id) return { mode: 'home' };
  if (resource === 'categories') return { mode: 'category', id };
  if (resource === 'documents') return action === 'edit' ? { mode: 'edit', id } : { mode: 'document', id };
  return { mode: 'home' };
}

function knowledgeCategoryPath(categoryId: number): string {
  return `/knowledge/categories/${categoryId}`;
}

function knowledgeDocumentPath(documentId: number): string {
  return `/knowledge/documents/${documentId}`;
}

function knowledgeDocumentEditPath(documentId: number): string {
  return `/knowledge/documents/${documentId}/edit`;
}

function knowledgeNewDocumentPath(categoryId: number): string {
  return `/knowledge/new?category=${categoryId}`;
}

const knowledgeCategoryIcons = ['🧑‍💼', '📄', '🛡', '💼', '🩺', '💻', '☎', '📊', '🦷', '📚', '🧾', '📌'];
const knowledgeEmojiGroups = [
  {
    id: 'frequent',
    label: 'Часті',
    icon: '🕘',
    emojis: ['🧑‍💼', '📄', '🧾', '📋', '🛡', '💼', '🩺', '🦷', '💻', '☎', '📊', '📈', '📚', '📌', '❤️', '🎯', '⚕️', '🏥', '📍', '✨'],
  },
  {
    id: 'smiles',
    label: 'Усмішки',
    icon: '🙂',
    emojis: ['🙂', '😊', '😀', '😁', '😌', '😉', '🤗', '🤝', '👍', '👏', '🙏', '💬', '💡', '⭐', '✨', '🌟', '🎉', '🎁', '💜', '❤️'],
  },
  {
    id: 'people',
    label: 'Люди',
    icon: '👥',
    emojis: ['👥', '🧑‍💼', '👩‍💼', '👨‍💼', '👩‍⚕️', '👨‍⚕️', '🧑‍⚕️', '🧑‍🏫', '🙋', '🧑‍💻', '👩‍💻', '👨‍💻', '🧑‍🔬', '👩‍🔬', '👨‍🔬', '🧑‍🔧', '👩‍🔧', '👨‍🔧'],
  },
  {
    id: 'clinic',
    label: 'Клініка',
    icon: '🩺',
    emojis: ['🩺', '⚕️', '🏥', '🦷', '💊', '💉', '🧬', '🧪', '🔬', '🩹', '🧴', '🧼', '😷', '🫶', '❤️', '💜', '🛡', '🧯'],
  },
  {
    id: 'documents',
    label: 'Документи',
    icon: '📄',
    emojis: ['📄', '📃', '📑', '📋', '📝', '🧾', '📚', '📖', '📘', '📗', '📙', '🗂️', '📁', '📎', '🔖', '🏷️', '✅', '☑️', '✍️', '🖊️'],
  },
  {
    id: 'work',
    label: 'Робота',
    icon: '💼',
    emojis: ['💼', '🖥️', '💻', '⌨️', '🖱️', '☎', '📞', '📧', '📅', '🗓️', '⏱️', '⏰', '⚙️', '🔒', '🔑', '🚀', '🎯', '🏆', '📌', '📎'],
  },
  {
    id: 'analytics',
    label: 'Аналітика',
    icon: '📊',
    emojis: ['📊', '📈', '📉', '💹', '🧮', '🎯', '🏅', '🥇', '📣', '📢', '💬', '🧠', '💡', '🔍', '🔎', '🧭', '🧩', '🗃️'],
  },
  {
    id: 'places',
    label: 'Локації',
    icon: '📍',
    emojis: ['📍', '🗺️', '🧭', '🏥', '🏢', '🏠', '🚪', '🌆', '🌇', '🏙️', '🚗', '🚕', '🚌', '🚎', '🚆', '✈️', '🚲', '🚶'],
  },
  {
    id: 'symbols',
    label: 'Позначки',
    icon: '🔣',
    emojis: ['✅', '☑️', '✔️', '❌', '⚠️', '❗', '❓', 'ℹ️', '🔔', '📣', '🔒', '🔓', '🟢', '🟡', '🔴', '🔵', '🟣', '⚪', '⚫', '⬆️', '⬇️'],
  },
];
const allKnowledgeEmojiOptions = Array.from(new Set(knowledgeEmojiGroups.flatMap((group) => group.emojis)));
const knowledgeEmojiKeywords: Record<string, string> = {
  '🧑‍💼': 'hr персонал люди менеджер керівник',
  '📄': 'документ сторінка файл',
  '🛡': 'безпека захист страховий',
  '💼': 'робота директор керівник бізнес',
  '🩺': 'медицина лікар клініка',
  '💻': 'baf компʼютер система інструкція',
  '☎': 'контакт центр телефон',
  '📊': 'маркетинг аналітика звіти',
  '🦷': 'стоматологія зуби',
  '📚': 'база знань навчання',
  '🧾': 'регламент стандарт протокол',
  '📌': 'важливо закріплено',
  '❤️': 'лояльність любов серце',
  '🎯': 'ціль nps план',
  '⚕️': 'медицина здоровʼя',
  '🖥️': 'компʼютер робоче місце',
  '📋': 'посадова інструкція список чеклист',
  '📈': 'звіт аналітика ріст',
  '📉': 'звіт аналітика спад',
  '📅': 'календар дата подія',
  '🗓️': 'календар графік дата',
  '📍': 'локація місто філія',
  '🏥': 'клініка медцентр філія',
  '✅': 'готово виконано підтверджено',
  '⚠️': 'увага попередження',
  '🔔': 'сповіщення нагадування',
};
const knowledgeEmojiSearchIndex = allKnowledgeEmojiOptions.reduce<Record<string, string>>((index, emoji) => {
  const groupLabels = knowledgeEmojiGroups
    .filter((group) => group.emojis.includes(emoji))
    .map((group) => group.label)
    .join(' ');
  index[emoji] = `${emoji} ${groupLabels} ${knowledgeEmojiKeywords[emoji] ?? ''}`;
  return index;
}, {});

const knowledgeTextColors = [
  { id: 'ink', label: 'Текст', value: '#061c3d' },
  { id: 'violet', label: 'Violet', value: '#7c3aed' },
  { id: 'teal', label: 'Teal', value: '#0f766e' },
  { id: 'rose', label: 'Rose', value: '#be123c' },
  { id: 'amber', label: 'Amber', value: '#b45309' },
  { id: 'blue', label: 'Blue', value: '#2563eb' },
];

const knowledgeFontOptions = [
  { id: 'sans', label: 'Системний', sample: 'Aa' },
  { id: 'serif', label: 'Serif', sample: 'Aa' },
  { id: 'mono', label: 'Mono', sample: 'Aa' },
];

const knowledgeEditorEmojiOptions = ['🙂', '👍', '✨', '❤️', '✅', '⚠️', '📌', '💡', '🦷', '🩺', '📄', '🎯', '🚀', '⭐', '💬', '🙏'];

const knowledgeSocialOptions = [
  { id: 'instagram', label: 'Instagram', placeholder: 'https://instagram.com/vidnova' },
  { id: 'facebook', label: 'Facebook', placeholder: 'https://facebook.com/vidnova' },
  { id: 'youtube', label: 'YouTube', placeholder: 'https://youtube.com/@vidnova' },
  { id: 'tiktok', label: 'TikTok', placeholder: 'https://tiktok.com/@vidnova' },
  { id: 'telegram', label: 'Telegram', placeholder: 'https://t.me/vidnova' },
  { id: 'website', label: 'Сайт', placeholder: 'https://vidnova.ua' },
];

function KnowledgeView({ knowledge, resetToken, copy }: { knowledge: SelfKnowledge; resetToken: number; copy: AppCopy }) {
  const location = useLocation();
  const navigate = useNavigate();
  const knowledgeRoute = useMemo(
    () => knowledgeRouteFromLocation(location.pathname, location.search),
    [location.pathname, location.search],
  );
  const knowledgeRouteId = 'id' in knowledgeRoute ? knowledgeRoute.id : null;
  const knowledgeRouteCategoryId = 'categoryId' in knowledgeRoute ? knowledgeRoute.categoryId : null;
  const [categories, setCategories] = useState(knowledge.categories);
  const [documents, setDocuments] = useState(knowledge.documents);
  const [search, setSearch] = useState('');
  const [activeCategoryId, setActiveCategoryId] = useState<number | null>(null);
  const [selectedDocumentId, setSelectedDocumentId] = useState<number | null>(null);
  const [expandedCategoryIds, setExpandedCategoryIds] = useState<Set<number>>(new Set());
  const [createMenuCategoryId, setCreateMenuCategoryId] = useState<number | null>(null);
  const [categoryManagerOpen, setCategoryManagerOpen] = useState(false);
  const [categoryDialogOpen, setCategoryDialogOpen] = useState(false);
  const [categoryDraft, setCategoryDraft] = useState<KnowledgeCategoryDraft>({
    id: null,
    name: '',
    description: '',
    parent: '',
    icon_emoji: '📄',
    visibility_mode: 'all',
    audience_employee_ids: '',
  });
  const [categorySaveState, setCategorySaveState] = useState<LoadState>('idle');
  const [categoryError, setCategoryError] = useState('');
  const [activePeopleTotal, setActivePeopleTotal] = useState(0);
  const [audiencePeople, setAudiencePeople] = useState<EmployeeListItem[]>([]);
  const [editorDraft, setEditorDraft] = useState<KnowledgeEditorDraft | null>(null);
  const [editorSaveState, setEditorSaveState] = useState<LoadState>('idle');
  const [editorError, setEditorError] = useState('');
  const [loadState, setLoadState] = useState<LoadState>('idle');

  function showKnowledgeHome({ clearSearch = false, closeDialogs = false }: { clearSearch?: boolean; closeDialogs?: boolean } = {}) {
    if (clearSearch) setSearch('');
    setActiveCategoryId(null);
    setSelectedDocumentId(null);
    setExpandedCategoryIds(new Set());
    setCreateMenuCategoryId(null);
    setCategoryManagerOpen(false);
    if (closeDialogs) setCategoryDialogOpen(false);
    setEditorDraft(null);
    setEditorError('');
    setEditorSaveState('idle');
    setCategoryError('');
    setCategorySaveState('idle');
  }

  function resetKnowledgeView() {
    showKnowledgeHome({ clearSearch: true, closeDialogs: true });
  }

  function navigateKnowledgeHome() {
    resetKnowledgeView();
    navigate('/knowledge');
  }

  useEffect(() => {
    resetKnowledgeView();
  }, [resetToken]);

  useEffect(() => {
    let cancelled = false;

    async function loadKnowledge() {
      setLoadState('loading');
      try {
        const [categoryResult, documentResult] = await Promise.all([
          api.knowledgeCategories({ page_size: 300 }),
          api.knowledgeDocuments({ q: search, page_size: 500 }),
        ]);
        if (cancelled) return;
        setCategories(categoryResult.items);
        setDocuments(documentResult.items);
        setLoadState('ok');
      } catch {
        if (cancelled) return;
        setCategories(knowledge.categories);
        setDocuments(knowledge.documents);
        setLoadState('error');
      }
    }

    void loadKnowledge();
    return () => {
      cancelled = true;
    };
  }, [knowledge.categories, knowledge.documents, search]);

  useEffect(() => {
    let cancelled = false;

    api
      .employees({ status: 'active', page_size: 200 })
      .then((result) => {
        if (!cancelled) {
          setActivePeopleTotal(result.total);
          setAudiencePeople(result.items);
        }
      })
      .catch(() => {
        if (!cancelled) setActivePeopleTotal(0);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const sortedCategories = useMemo(
    () => [...categories].sort((first, second) => first.position - second.position || first.name.localeCompare(second.name, 'uk')),
    [categories],
  );
  const documentsByCategory = useMemo(() => {
    const grouped = new Map<number, KnowledgeDocument[]>();
    documents.forEach((document) => {
      const current = grouped.get(document.category) ?? [];
      current.push(document);
      grouped.set(document.category, current);
    });
    grouped.forEach((items) => items.sort((first, second) => first.title.localeCompare(second.title, 'uk')));
    return grouped;
  }, [documents]);
  const categoryTree = useMemo(() => buildKnowledgeCategoryTree(sortedCategories, documentsByCategory), [documentsByCategory, sortedCategories]);
  const categoryNodeMap = useMemo(() => mapKnowledgeCategoryNodes(categoryTree), [categoryTree]);
  const rootCategoryIds = useMemo(() => new Set(categoryTree.map((node) => node.category.id)), [categoryTree]);
  const selectedDocument = documents.find((document) => document.id === selectedDocumentId) ?? null;
  const expandedIds = useMemo(() => {
    const next = new Set(expandedCategoryIds);
    if (selectedDocument) {
      knowledgeCategoryAncestorIds(categories, selectedDocument.category).forEach((id) => next.add(id));
      next.add(selectedDocument.category);
    }
    return next;
  }, [categories, expandedCategoryIds, selectedDocument]);
  const visibleNavRows = useMemo(
    () => buildKnowledgeNavRows(categoryTree, expandedIds, documentsByCategory),
    [categoryTree, documentsByCategory, expandedIds],
  );
  const activeCategory =
    sortedCategories.find((category) => category.id === (selectedDocument?.category ?? editorDraft?.category ?? activeCategoryId)) ??
    null;
  const activeCategoryNode = activeCategory ? categoryNodeMap.get(activeCategory.id) ?? null : null;
  const activeDocuments = activeCategory ? documentsByCategory.get(activeCategory.id) ?? [] : [];
  const activeChildNodes = activeCategoryNode?.children ?? [];
  const emptyTitle =
    loadState === 'loading'
      ? copy.knowledge.loading
      : loadState === 'error'
        ? copy.knowledge.loadError
        : copy.knowledge.notFound;
  const emptyText =
    loadState === 'loading'
      ? copy.knowledge.loadingText || 'Завантажуються категорії і документи з PeopleForce-імпорту.'
      : loadState === 'error'
        ? copy.common.backendRetry
        : copy.knowledge.noDocumentsForSearch || 'За поточним пошуком немає документів.';

  useEffect(() => {
    if (sectionFromPathname(location.pathname) !== 'knowledge') return;

    if (knowledgeRoute.mode === 'home') {
      showKnowledgeHome();
      return;
    }

    if (knowledgeRoute.mode === 'manage') {
      setCreateMenuCategoryId(null);
      setSelectedDocumentId(null);
      setEditorDraft(null);
      setCategoryManagerOpen(true);
      return;
    }

    if (knowledgeRoute.mode === 'category') {
      if (!categories.some((category) => category.id === knowledgeRoute.id)) return;
      setCreateMenuCategoryId(null);
      setActiveCategoryId(knowledgeRoute.id);
      setSelectedDocumentId(null);
      setEditorDraft(null);
      setCategoryManagerOpen(false);
      setExpandedCategoryIds(new Set([...knowledgeCategoryAncestorIds(categories, knowledgeRoute.id), knowledgeRoute.id]));
      return;
    }

    if (knowledgeRoute.mode === 'new') {
      const targetCategory =
        knowledgeRoute.categoryId && categories.some((category) => category.id === knowledgeRoute.categoryId)
          ? knowledgeRoute.categoryId
          : sortedCategories[0]?.id;
      if (!targetCategory) return;
      setCreateMenuCategoryId(null);
      setSelectedDocumentId(null);
      setCategoryManagerOpen(false);
      setActiveCategoryId(targetCategory);
      setExpandedCategoryIds(new Set([...knowledgeCategoryAncestorIds(categories, targetCategory), targetCategory]));
      setEditorError('');
      setEditorSaveState('idle');
      setEditorDraft((current) => {
        if (current?.id === null && current.category === targetCategory) return current;
        return {
          id: null,
          category: targetCategory,
          title: '',
          summary: '',
          cover_url: '',
          body: '',
          status: 'draft',
          created_at: null,
          updated_at: null,
          owner_name: '',
          view_count: 0,
        };
      });
      return;
    }

    const document = documents.find((item) => item.id === knowledgeRoute.id);
    if (!document) return;
    setCreateMenuCategoryId(null);
    setActiveCategoryId(document.category);
    setSelectedDocumentId(document.id);
    setCategoryManagerOpen(false);
    setExpandedCategoryIds(new Set([...knowledgeCategoryAncestorIds(categories, document.category), document.category]));

    if (knowledgeRoute.mode === 'edit') {
      setEditorError('');
      setEditorSaveState('idle');
      setEditorDraft((current) => {
        if (current?.id === document.id) return current;
        return knowledgeEditorDraftFromDocument(document);
      });
      return;
    }

    setEditorDraft(null);
  }, [
    categories,
    documents,
    knowledgeRouteCategoryId,
    knowledgeRouteId,
    knowledgeRoute.mode,
    location.pathname,
    sortedCategories,
  ]);

  function openCategory(categoryId: number) {
    setCreateMenuCategoryId(null);
    setActiveCategoryId(categoryId);
    setSelectedDocumentId(null);
    setEditorDraft(null);
    setCategoryManagerOpen(false);
    setExpandedCategoryIds((current) => {
      const ancestors = knowledgeCategoryAncestorIds(categories, categoryId);
      if (current.has(categoryId)) {
        const descendants = new Set(knowledgeCategoryDescendantIds(categories, categoryId));
        const next = new Set(current);
        next.delete(categoryId);
        descendants.forEach((id) => next.delete(id));
        ancestors.forEach((id) => next.add(id));
        return next;
      }
      return new Set([...current, ...ancestors, categoryId]);
    });
    navigate(knowledgeCategoryPath(categoryId));
  }

  function openDocument(document: KnowledgeDocument) {
    setCreateMenuCategoryId(null);
    setActiveCategoryId(document.category);
    setSelectedDocumentId(document.id);
    setEditorDraft(null);
    setCategoryManagerOpen(false);
    setExpandedCategoryIds(new Set([...knowledgeCategoryAncestorIds(categories, document.category), document.category]));
    navigate(knowledgeDocumentPath(document.id));
  }

  function startManageCategories() {
    setCreateMenuCategoryId(null);
    setSelectedDocumentId(null);
    setEditorDraft(null);
    setCategoryManagerOpen(true);
    navigate('/knowledge/manage');
  }

  function startCreateCategory(parentId?: number | null) {
    setCreateMenuCategoryId(null);
    setCategoryDraft({
      id: null,
      name: '',
      description: '',
      parent: parentId ? String(parentId) : '',
      icon_emoji: '📄',
      visibility_mode: 'all',
      audience_employee_ids: '',
    });
    setCategoryError('');
    setCategorySaveState('idle');
    setCategoryDialogOpen(true);
  }

  function startEditCategory(category: KnowledgeCategory) {
    setCreateMenuCategoryId(null);
    setCategoryDraft({
      id: category.id,
      name: category.name,
      description: category.description,
      parent: category.parent ? String(category.parent) : '',
      icon_emoji: categoryIcon(category, 0),
      visibility_mode: category.visibility_mode || 'all',
      audience_employee_ids: (category.audience_employee_ids || []).join(', '),
    });
    setCategoryError('');
    setCategorySaveState('idle');
    setCategoryDialogOpen(true);
  }

  function startCreateDocument(categoryId?: number) {
    setCreateMenuCategoryId(null);
    const targetCategory = categoryId ?? activeCategory?.id ?? sortedCategories[0]?.id;
    if (!targetCategory) {
      setCategoryError('Спочатку створіть категорію для сторінки.');
      startCreateCategory(null);
      return;
    }
    setSelectedDocumentId(null);
    setCategoryManagerOpen(false);
    setActiveCategoryId(targetCategory);
    setExpandedCategoryIds(new Set([...knowledgeCategoryAncestorIds(categories, targetCategory), targetCategory]));
    setEditorError('');
    setEditorSaveState('idle');
    setEditorDraft({
      id: null,
      category: targetCategory,
      title: '',
      summary: '',
      cover_url: '',
      body: '',
      status: 'draft',
      created_at: null,
      updated_at: null,
      owner_name: '',
      view_count: 0,
    });
    navigate(knowledgeNewDocumentPath(targetCategory));
  }

  function startEditDocument(document: KnowledgeDocument) {
    setCreateMenuCategoryId(null);
    setActiveCategoryId(document.category);
    setSelectedDocumentId(document.id);
    setCategoryManagerOpen(false);
    setExpandedCategoryIds(new Set([...knowledgeCategoryAncestorIds(categories, document.category), document.category]));
    setEditorError('');
    setEditorSaveState('idle');
    setEditorDraft(knowledgeEditorDraftFromDocument(document));
    navigate(knowledgeDocumentEditPath(document.id));
  }

  function cancelEditor() {
    const draft = editorDraft;
    setEditorDraft(null);
    setEditorError('');
    setEditorSaveState('idle');
    if (draft?.id) {
      navigate(knowledgeDocumentPath(draft.id));
      return;
    }
    const categoryId = draft?.category ?? activeCategory?.id ?? sortedCategories[0]?.id;
    navigate(categoryId ? knowledgeCategoryPath(categoryId) : '/knowledge');
  }

  function closeDocument(document: KnowledgeDocument) {
    setSelectedDocumentId(null);
    setEditorDraft(null);
    navigate(knowledgeCategoryPath(document.category));
  }

  async function saveCategory(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const name = categoryDraft.name.trim();
    if (!name) {
      setCategoryError('Назва категорії обовʼязкова.');
      return;
    }
    const audienceIds = parseIdList(categoryDraft.audience_employee_ids);
    if (categoryDraft.visibility_mode === 'specific' && categoryDraft.audience_employee_ids.trim() && !audienceIds.length) {
      setCategoryError('Вкажіть ID співробітників через кому або залиште поле порожнім.');
      return;
    }
    setCategorySaveState('loading');
    setCategoryError('');
    try {
      const payload = {
        name,
        description: categoryDraft.description.trim(),
        icon_emoji: categoryDraft.icon_emoji || '📄',
        visibility_mode: categoryDraft.visibility_mode,
        audience_employee_ids: categoryDraft.visibility_mode === 'specific' ? audienceIds : [],
        audience_filters: categoryDraft.visibility_mode === 'all' ? { employee_status: 'active' } : {},
        parent: categoryDraft.parent ? Number(categoryDraft.parent) : null,
        position: categoryDraft.id ? undefined : categories.length + 1,
        is_active: true,
      };
      const saved = categoryDraft.id
        ? await api.updateKnowledgeCategory(categoryDraft.id, payload)
        : await api.createKnowledgeCategory(payload);
      setCategories((current) => {
        const withoutSaved = current.filter((category) => category.id !== saved.id);
        return [...withoutSaved, saved];
      });
      setActiveCategoryId(saved.id);
      setExpandedCategoryIds(new Set([...(saved.parent ? [...knowledgeCategoryAncestorIds(categories, saved.parent), saved.parent] : []), saved.id]));
      setCategoryDialogOpen(false);
      setCategorySaveState('ok');
      navigate(knowledgeCategoryPath(saved.id));
    } catch {
      setCategorySaveState('error');
      setCategoryError('Не вдалося зберегти категорію. Перевірте, що ви увійшли як адміністратор.');
    }
  }

  async function moveCategory(categoryId: number, parentId: number | null) {
    const category = sortedCategories.find((item) => item.id === categoryId);
    if (!category || category.parent === parentId) return;
    if (parentId === categoryId || (parentId && knowledgeCategoryDescendantIds(categories, categoryId).includes(parentId))) return;

    const saved = await api.updateKnowledgeCategory(categoryId, { parent: parentId });
    setCategories((current) => current.map((item) => (item.id === saved.id ? saved : item)));
    setExpandedCategoryIds((current) => {
      const next = new Set(current);
      if (parentId) {
        knowledgeCategoryAncestorIds(categories, parentId).forEach((id) => next.add(id));
        next.add(parentId);
      }
      next.add(saved.id);
      return next;
    });
  }

  async function moveDocument(documentId: number, categoryId: number) {
    const document = documents.find((item) => item.id === documentId);
    if (!document || document.category === categoryId) return;

    const saved = await api.updateKnowledgeDocument(documentId, { category: categoryId });
    setDocuments((current) => current.map((item) => (item.id === saved.id ? saved : item)));
    setExpandedCategoryIds((current) => new Set([...current, ...knowledgeCategoryAncestorIds(categories, categoryId), categoryId]));
  }

  async function saveEditor(status: string) {
    if (!editorDraft) return;
    const title = editorDraft.title.trim();
    if (!title) {
      setEditorError('Додайте заголовок сторінки.');
      return;
    }
    setEditorSaveState('loading');
    setEditorError('');
    const payload = {
      category: editorDraft.category,
      title,
      summary: editorDraft.summary.trim(),
      cover_url: editorDraft.cover_url.trim(),
      body: editorDraft.body,
      body_html: renderKnowledgeEditorHtml(editorDraft.body),
      status,
      tags: [],
    };
    try {
      const saved = editorDraft.id
        ? await api.updateKnowledgeDocument(editorDraft.id, payload)
        : await api.createKnowledgeDocument(payload);
      setDocuments((current) => {
        const withoutSaved = current.filter((document) => document.id !== saved.id);
        return [...withoutSaved, saved];
      });
      setActiveCategoryId(saved.category);
      setSelectedDocumentId(saved.id);
      setExpandedCategoryIds(new Set([...knowledgeCategoryAncestorIds(categories, saved.category), saved.category]));
      setEditorDraft(null);
      setEditorSaveState('ok');
      navigate(knowledgeDocumentPath(saved.id));
    } catch (error) {
      setEditorSaveState('error');
      setEditorError(knowledgeEditorErrorMessage(error));
    }
  }

  return (
    <main className="knowledge-page">
      <aside className="knowledge-nav">
        <div className="side-search-title">
          <button type="button" className="knowledge-home-reset" onClick={navigateKnowledgeHome}>
            {copy.knowledge.title}
          </button>
          <button type="button" aria-label={copy.knowledge.createCategory || 'Create category'} onClick={() => startCreateCategory(null)}>
            <Plus size={16} />
          </button>
        </div>
        <label className="knowledge-side-search">
          <Search size={16} />
          <input type="search" placeholder={copy.knowledge.searchPlaceholder} value={search} onChange={(event) => setSearch(event.target.value)} />
        </label>
        <nav>
          {visibleNavRows.map((row, index) => {
            if (row.type === 'document') {
              return (
                <div
                  className="knowledge-tree-document-row"
                  key={`document-${row.document.id}`}
                  style={{ '--tree-depth': Math.min(row.depth, 3) } as CSSProperties}
                >
                  <button
                    type="button"
                    className={selectedDocument?.id === row.document.id ? 'active' : ''}
                    onClick={() => openDocument(row.document)}
                  >
                    <span className="knowledge-tree-caret" aria-hidden="true" />
                    <span className="knowledge-tree-icon knowledge-tree-document-icon">
                      <FileText size={14} />
                    </span>
                    <span className="knowledge-tree-document-title">{row.document.title}</span>
                  </button>
                </div>
              );
            }
            const category = row.node.category;
            const expanded = expandedIds.has(category.id);
            const canExpand = row.node.children.length > 0 || row.node.ownDocumentCount > 0;
            const navDepth = rootCategoryIds.has(category.id) ? 0 : Math.min(row.node.depth, 2);
            return (
              <div className="knowledge-tree-group" key={category.id} style={{ '--tree-depth': navDepth } as CSSProperties}>
                <div className={`knowledge-tree-category-row ${activeCategory?.id === category.id ? 'active' : ''}`}>
                  <button type="button" className="knowledge-tree-category" aria-expanded={canExpand ? expanded : undefined} onClick={() => openCategory(category.id)}>
                    <span className="knowledge-tree-caret">{canExpand ? <ChevronRight size={15} className={expanded ? 'expanded' : ''} /> : null}</span>
                    <span className="knowledge-tree-icon">{categoryIcon(category, index)}</span>
                    <strong>{category.name}</strong>
                    <em>{row.node.totalDocumentCount}</em>
                  </button>
                  <KnowledgeCreateMenuButton
                    categoryName={category.name}
                    isOpen={createMenuCategoryId === category.id}
                    buttonClassName="knowledge-tree-add-page"
                    onToggle={() => setCreateMenuCategoryId((current) => (current === category.id ? null : category.id))}
                    onCreateCategory={() => startCreateCategory(category.id)}
                    onCreateDocument={() => startCreateDocument(category.id)}
                  />
                </div>
              </div>
            );
          })}
        </nav>
        <div className="knowledge-scroll-hint" aria-hidden="true">
          <ChevronDown size={16} />
          <ChevronDown size={16} />
        </div>
      </aside>

      <section className={`knowledge-main ${selectedDocument ? 'document-open' : ''} ${editorDraft ? 'editor-open' : ''}`}>
        {editorDraft ? (
          <KnowledgeEditorView
            draft={editorDraft}
            category={activeCategory}
            saveState={editorSaveState}
            error={editorError}
            onDraftChange={setEditorDraft}
            onCancel={cancelEditor}
            onSaveDraft={() => saveEditor('draft')}
            onPublish={() => saveEditor('published')}
          />
        ) : selectedDocument ? (
          <KnowledgeArticleView
            document={selectedDocument}
            category={activeCategory}
            onEdit={() => startEditDocument(selectedDocument)}
            onClose={() => closeDocument(selectedDocument)}
          />
        ) : categoryManagerOpen ? (
          <KnowledgeCategoryManagerView
            tree={categoryTree}
            categories={sortedCategories}
            documentsByCategory={documentsByCategory}
            onClose={() => setCategoryManagerOpen(false)}
            onCreateCategory={() => startCreateCategory(null)}
            onCreateChild={(categoryId) => startCreateCategory(categoryId)}
            onCreateDocument={(categoryId) => startCreateDocument(categoryId)}
            onEditCategory={startEditCategory}
            onEditDocument={startEditDocument}
            onMoveCategory={moveCategory}
            onMoveDocument={moveDocument}
            activeCreateCategoryId={createMenuCategoryId}
            onToggleCreateMenu={(categoryId) => setCreateMenuCategoryId((current) => (current === categoryId ? null : categoryId))}
            copy={copy}
          />
        ) : activeCategory ? (
          <KnowledgeCategoryView
            category={activeCategory}
            childNodes={activeChildNodes}
            documents={activeDocuments}
            loadState={loadState}
            emptyTitle={emptyTitle}
            emptyText={emptyText}
            onOpenDocument={openDocument}
            onOpenCategory={openCategory}
            onCreateDocument={() => startCreateDocument(activeCategory.id)}
          />
        ) : (
          <KnowledgeHomeView
            tree={categoryTree}
            search={search}
            loadState={loadState}
            emptyTitle={emptyTitle}
            emptyText={emptyText}
            onSearch={setSearch}
            onOpenCategory={openCategory}
            onManageCategories={startManageCategories}
            copy={copy}
          />
        )}
      </section>
      {categoryDialogOpen ? (
        <KnowledgeCategoryDialog
          draft={categoryDraft}
          categories={sortedCategories}
          saveState={categorySaveState}
          error={categoryError}
          onDraftChange={setCategoryDraft}
          onClose={() => setCategoryDialogOpen(false)}
          onSubmit={saveCategory}
          activePeopleTotal={activePeopleTotal}
          people={audiencePeople}
        />
      ) : null}
    </main>
  );
}

function KnowledgeHomeView({
  tree,
  search,
  loadState,
  emptyTitle,
  emptyText,
  onSearch,
  onOpenCategory,
  onManageCategories,
  copy,
}: {
  tree: KnowledgeCategoryTreeNode[];
  search: string;
  loadState: LoadState;
  emptyTitle: string;
  emptyText: string;
  onSearch: (value: string) => void;
  onOpenCategory: (categoryId: number) => void;
  onManageCategories: () => void;
  copy: AppCopy;
}) {
  return (
    <>
      <header className="knowledge-home-header">
        <div>
          <h1>{copy.knowledge.title}</h1>
          <p>{copy.knowledge.subtitle || 'Категорії, регламенти і матеріали компанії'}</p>
        </div>
        <button type="button" className="toolbar-button strong" onClick={onManageCategories}>
          <Settings size={17} />
          {copy.knowledge.manageCategories || 'Управління категоріями'}
        </button>
      </header>
      <div className="knowledge-home-search">
        <Search size={16} />
        <input type="search" placeholder={copy.knowledge.searchPlaceholder} value={search} onChange={(event) => onSearch(event.target.value)} />
      </div>
      <div className="knowledge-category-grid">
        {tree.length ? (
          tree.map((node, index) => (
            <button type="button" key={node.category.id} className="knowledge-category-card" onClick={() => onOpenCategory(node.category.id)}>
              <span className="knowledge-category-icon">{categoryIcon(node.category, index)}</span>
              <div>
                <strong>{node.category.name}</strong>
                <span>{node.category.description || categoryDescription(node.category.name)}</span>
              </div>
              <em>{node.totalDocumentCount}</em>
            </button>
          ))
        ) : (
          <div className="panel">
            <EmptyState title={loadState === 'loading' ? emptyTitle : copy.knowledge.categoriesNotFound} text={emptyText} />
          </div>
        )}
      </div>
    </>
  );
}

function KnowledgeCreateMenuButton({
  categoryName,
  isOpen,
  buttonClassName,
  onToggle,
  onCreateCategory,
  onCreateDocument,
}: {
  categoryName: string;
  isOpen: boolean;
  buttonClassName: string;
  onToggle: () => void;
  onCreateCategory: () => void;
  onCreateDocument: () => void;
}) {
  return (
    <div className="knowledge-create-control" onClick={(event) => event.stopPropagation()} onDragStart={(event) => event.stopPropagation()}>
      <button type="button" className={buttonClassName} aria-label={`Додати в ${categoryName}`} aria-expanded={isOpen} onClick={onToggle}>
        <Plus size={15} />
      </button>
      {isOpen ? (
        <div className="knowledge-create-menu">
          <button type="button" onClick={onCreateCategory}>
            <GitBranch size={15} />
            <span>
              <strong>Підкатегорію</strong>
              <em>Новий розділ всередині</em>
            </span>
          </button>
          <button type="button" onClick={onCreateDocument}>
            <FileText size={15} />
            <span>
              <strong>Сторінку</strong>
              <em>Документ у цій категорії</em>
            </span>
          </button>
        </div>
      ) : null}
    </div>
  );
}

function KnowledgeCategoryManagerView({
  tree,
  categories,
  documentsByCategory,
  onClose,
  onCreateCategory,
  onCreateChild,
  onCreateDocument,
  onEditCategory,
  onEditDocument,
  onMoveCategory,
  onMoveDocument,
  activeCreateCategoryId,
  onToggleCreateMenu,
  copy,
}: {
  tree: KnowledgeCategoryTreeNode[];
  categories: KnowledgeCategory[];
  documentsByCategory: Map<number, KnowledgeDocument[]>;
  onClose: () => void;
  onCreateCategory: () => void;
  onCreateChild: (categoryId: number) => void;
  onCreateDocument: (categoryId: number) => void;
  onEditCategory: (category: KnowledgeCategory) => void;
  onEditDocument: (document: KnowledgeDocument) => void;
  onMoveCategory: (categoryId: number, parentId: number | null) => Promise<void>;
  onMoveDocument: (documentId: number, categoryId: number) => Promise<void>;
  activeCreateCategoryId: number | null;
  onToggleCreateMenu: (categoryId: number) => void;
  copy: AppCopy;
}) {
  const [dragItem, setDragItem] = useState<KnowledgeManagerDragItem | null>(null);
  const [dropTarget, setDropTarget] = useState<number | 'root' | null>(null);
  const [moveError, setMoveError] = useState('');
  const categoryById = useMemo(() => new Map(categories.map((category) => [category.id, category])), [categories]);
  const documentById = useMemo(() => {
    const map = new Map<number, KnowledgeDocument>();
    documentsByCategory.forEach((items) => {
      items.forEach((document) => map.set(document.id, document));
    });
    return map;
  }, [documentsByCategory]);

  function canDrop(targetCategoryId: number | null) {
    if (!dragItem) return false;
    if (dragItem.type === 'document') {
      if (!targetCategoryId) return false;
      return documentById.get(dragItem.id)?.category !== targetCategoryId;
    }

    const category = categoryById.get(dragItem.id);
    if (!category || category.parent === targetCategoryId) return false;
    if (!targetCategoryId) return Boolean(category.parent);
    if (targetCategoryId === dragItem.id) return false;
    return !knowledgeCategoryDescendantIds(categories, dragItem.id).includes(targetCategoryId);
  }

  function startDrag(event: DragEvent<HTMLElement>, item: KnowledgeManagerDragItem) {
    setMoveError('');
    setDragItem(item);
    event.dataTransfer.effectAllowed = 'move';
    event.dataTransfer.setData('application/x-knowledge-item', JSON.stringify(item));
  }

  function allowDrop(event: DragEvent<HTMLElement>, targetCategoryId: number | null) {
    if (!canDrop(targetCategoryId)) return;
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
    setDropTarget(targetCategoryId ?? 'root');
  }

  async function dropItem(event: DragEvent<HTMLElement>, targetCategoryId: number | null) {
    event.preventDefault();
    event.stopPropagation();
    if (!dragItem || !canDrop(targetCategoryId)) {
      setDropTarget(null);
      return;
    }

    try {
      if (dragItem.type === 'category') {
        await onMoveCategory(dragItem.id, targetCategoryId);
      } else if (targetCategoryId) {
        await onMoveDocument(dragItem.id, targetCategoryId);
      }
    } catch {
      setMoveError('Не вдалося перенести елемент. Перевірте права адміністратора і повторіть.');
    } finally {
      setDragItem(null);
      setDropTarget(null);
    }
  }

  function renderDocument(document: KnowledgeDocument) {
    const dragging = dragItem?.type === 'document' && dragItem.id === document.id;
    return (
      <div
        className={`knowledge-manager-row document ${dragging ? 'dragging' : ''}`}
        draggable
        key={`document-${document.id}`}
        onDragStart={(event) => startDrag(event, { type: 'document', id: document.id })}
        onDragEnd={() => {
          setDragItem(null);
          setDropTarget(null);
        }}
      >
        <span className="drag-dots">••</span>
        <span className="knowledge-category-icon knowledge-manager-doc-icon">
          <FileText size={14} />
        </span>
        <div>
          <strong>{document.title}</strong>
          <span>
            Сторінка · {categoryBreadcrumb(categories, document.category)}
            {' · '}
            {document.status === 'published' ? 'Опубліковано' : 'Чернетка'} · {formatDateTime(document.updated_at)}
          </span>
        </div>
        <span className="knowledge-manager-row-spacer" />
        <button type="button" className="toolbar-icon" aria-label="Редагувати сторінку" onClick={() => onEditDocument(document)}>
          <MoreHorizontal size={18} />
        </button>
      </div>
    );
  }

  function renderCategory(node: KnowledgeCategoryTreeNode, index: number) {
    const target = dropTarget === node.category.id;
    const dragging = dragItem?.type === 'category' && dragItem.id === node.category.id;
    const directDocuments = documentsByCategory.get(node.category.id) ?? [];
    const hasChildren = directDocuments.length > 0 || node.children.length > 0;

    return (
      <section className={`knowledge-manager-node ${node.depth ? 'nested' : 'root'}`} key={`category-${node.category.id}`}>
        <div
          className={`knowledge-manager-row category ${node.depth ? 'nested' : 'root'} ${target ? 'drop-target' : ''} ${dragging ? 'dragging' : ''}`}
          draggable
          onDragStart={(event) => startDrag(event, { type: 'category', id: node.category.id })}
          onDragOver={(event) => allowDrop(event, node.category.id)}
          onDrop={(event) => dropItem(event, node.category.id)}
          onDragLeave={() => setDropTarget(null)}
          onDragEnd={() => {
            setDragItem(null);
            setDropTarget(null);
          }}
        >
          <span className="drag-dots">••</span>
          <span className="knowledge-category-icon">{categoryIcon(node.category, index)}</span>
          <div>
            <strong>{node.category.name}</strong>
            <span>
              {node.category.parent ? 'Підкатегорія' : 'Категорія'} · {categoryBreadcrumb(categories, node.category.id)} · {node.totalDocumentCount} статей
              {node.category.parent ? ' · підкатегорія' : ' · верхній рівень'}
              {node.category.visibility_mode === 'specific' ? ' · конкретні люди' : ' · усі'}
            </span>
          </div>
          <KnowledgeCreateMenuButton
            categoryName={node.category.name}
            isOpen={activeCreateCategoryId === node.category.id}
            buttonClassName="toolbar-icon"
            onToggle={() => onToggleCreateMenu(node.category.id)}
            onCreateCategory={() => onCreateChild(node.category.id)}
            onCreateDocument={() => onCreateDocument(node.category.id)}
          />
          <button type="button" className="toolbar-icon" aria-label="Редагувати категорію" onClick={() => onEditCategory(node.category)}>
            <MoreHorizontal size={18} />
          </button>
        </div>
        {hasChildren ? (
          <div className="knowledge-manager-children">
            {directDocuments.map(renderDocument)}
            {node.children.map((childNode, childIndex) => renderCategory(childNode, index + childIndex + 1))}
          </div>
        ) : null}
      </section>
    );
  }

  return (
    <article className="knowledge-manager">
      <header className="knowledge-home-header">
        <div>
          <h1>{copy.knowledge.manageCategories || 'Управління категоріями'}</h1>
          <p>{copy.knowledge.manageCategoriesText || 'Структура бази знань, вкладеність, emoji і призначення'}</p>
        </div>
        <div className="knowledge-manager-actions">
          <button type="button" className="secondary-action" onClick={onClose}>
            <X size={17} />
            {copy.common.closeMenu}
          </button>
          <button type="button" className="primary-action" onClick={onCreateCategory}>
            <Plus size={17} />
            {copy.knowledge.addCategory || 'Додати категорію'}
          </button>
        </div>
      </header>
      {moveError ? <p className="form-error knowledge-manager-error">{moveError}</p> : null}
      <div className="knowledge-manager-list">
        <div
          className={`knowledge-manager-root-drop ${dropTarget === 'root' ? 'drop-target' : ''}`}
          onDragOver={(event) => allowDrop(event, null)}
          onDrop={(event) => dropItem(event, null)}
          onDragLeave={() => setDropTarget(null)}
        >
          <GitBranch size={15} />
          <span>Верхній рівень</span>
        </div>
        <div className="knowledge-manager-tree">{tree.map((node, index) => renderCategory(node, index))}</div>
      </div>
    </article>
  );
}

function KnowledgeCategoryDialog({
  draft,
  categories,
  saveState,
  error,
  activePeopleTotal,
  people,
  onDraftChange,
  onClose,
  onSubmit,
}: {
  draft: KnowledgeCategoryDraft;
  categories: KnowledgeCategory[];
  saveState: LoadState;
  error: string;
  activePeopleTotal: number;
  people: EmployeeListItem[];
  onDraftChange: (draft: KnowledgeCategoryDraft) => void;
  onClose: () => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}) {
  const [peopleSearch, setPeopleSearch] = useState('');
  const [emojiOpen, setEmojiOpen] = useState(false);
  const [emojiSearch, setEmojiSearch] = useState('');
  const [activeEmojiGroup, setActiveEmojiGroup] = useState(knowledgeEmojiGroups[0].id);
  const [parentPickerOpen, setParentPickerOpen] = useState(false);
  const [parentSearch, setParentSearch] = useState('');
  const excludedParentIds = draft.id ? new Set([draft.id, ...knowledgeCategoryDescendantIds(categories, draft.id)]) : new Set<number>();
  const availableParents = useMemo(
    () =>
      categories
        .filter((category) => !excludedParentIds.has(category.id))
        .sort((first, second) => first.position - second.position || first.name.localeCompare(second.name, 'uk')),
    [categories, excludedParentIds],
  );
  const availableParentTree = useMemo(() => buildKnowledgeCategoryTree(availableParents, new Map()), [availableParents]);
  const availableParentRows = useMemo(() => {
    const rows = flattenKnowledgeTree(availableParentTree);
    const query = parentSearch.trim().toLowerCase();
    if (!query) return rows;
    return rows.filter((node) =>
      [node.category.name, node.category.description, categoryBreadcrumb(categories, node.category.id)].some((value) =>
        (value || '').toLowerCase().includes(query),
      ),
    );
  }, [availableParentTree, categories, parentSearch]);
  const selectedParentId = draft.parent ? Number(draft.parent) : null;
  const selectedParentLabel = selectedParentId ? categoryBreadcrumb(categories, selectedParentId) || 'Категорію не знайдено' : 'Без батьківської категорії';
  const selectedSpecificIds = parseIdList(draft.audience_employee_ids);
  const selectedIdSet = new Set(selectedSpecificIds);
  const activeEmojiSet = knowledgeEmojiGroups.find((group) => group.id === activeEmojiGroup) ?? knowledgeEmojiGroups[0];
  const visibleEmojis = useMemo(() => {
    const query = emojiSearch.trim().toLowerCase();
    const source = query ? allKnowledgeEmojiOptions : activeEmojiSet.emojis;
    return source.filter((emoji) => {
      if (!query) return true;
      return knowledgeEmojiSearchIndex[emoji].toLowerCase().includes(query);
    });
  }, [activeEmojiSet.emojis, emojiSearch]);
  const filteredPeople = people
    .filter((person) => {
      const query = peopleSearch.trim().toLowerCase();
      if (!query) return true;
      return [person.full_name, person.position_name, person.department_name, person.email].some((value) =>
        (value || '').toLowerCase().includes(query),
      );
    })
    .slice(0, 12);

  function togglePerson(personId: number) {
    const next = new Set(selectedSpecificIds);
    if (next.has(personId)) {
      next.delete(personId);
    } else {
      next.add(personId);
    }
    onDraftChange({ ...draft, audience_employee_ids: Array.from(next).sort((first, second) => first - second).join(', ') });
  }

  return (
    <div className="knowledge-modal-layer" role="dialog" aria-modal="true" aria-label="Створення категорії">
      <button type="button" className="knowledge-modal-backdrop" aria-label="Закрити" onClick={onClose} />
      <form className="knowledge-category-dialog" onSubmit={onSubmit}>
        <div className="knowledge-dialog-head">
          <div>
            <strong>{draft.id ? 'Редагувати категорію' : 'Нова категорія'}</strong>
            <span>Структура, emoji і аудиторія бази знань</span>
          </div>
          <button type="button" className="icon-button" aria-label="Закрити" onClick={onClose}>
            <X size={18} />
          </button>
        </div>
        <div className="knowledge-category-form-grid">
          <label>
            <span>Назва</span>
            <input value={draft.name} onChange={(event) => onDraftChange({ ...draft, name: event.target.value })} autoFocus />
          </label>
          <label className="knowledge-emoji-field">
            <span>Emoji</span>
            <button
              type="button"
              className={`knowledge-emoji-trigger ${emojiOpen ? 'active' : ''}`}
              aria-expanded={emojiOpen}
              onClick={() => setEmojiOpen((current) => !current)}
            >
              <span>{draft.icon_emoji || '📄'}</span>
              <ChevronDown size={16} />
            </button>
            {emojiOpen ? (
              <div className="knowledge-emoji-popover">
                <div className="knowledge-emoji-tabs" role="tablist" aria-label="Групи emoji">
                  {knowledgeEmojiGroups.map((group) => (
                    <button
                      type="button"
                      key={group.id}
                      className={group.id === activeEmojiGroup ? 'active' : ''}
                      title={group.label}
                      aria-label={group.label}
                      onClick={() => setActiveEmojiGroup(group.id)}
                    >
                      {group.icon}
                    </button>
                  ))}
                </div>
                <label className="knowledge-emoji-search">
                  <Search size={16} />
                  <input value={emojiSearch} placeholder="Пошук emoji" onChange={(event) => setEmojiSearch(event.target.value)} />
                </label>
                <div className="knowledge-emoji-title">{emojiSearch.trim() ? 'Результати пошуку' : activeEmojiSet.label}</div>
                <div className="knowledge-emoji-grid">
                  {visibleEmojis.map((emoji) => (
                    <button
                      type="button"
                      key={emoji}
                      className={draft.icon_emoji === emoji ? 'active' : ''}
                      aria-label={`Обрати ${emoji}`}
                      onClick={() => {
                        onDraftChange({ ...draft, icon_emoji: emoji });
                        setEmojiOpen(false);
                      }}
                    >
                      {emoji}
                    </button>
                  ))}
                </div>
              </div>
            ) : null}
          </label>
        </div>
        <label className="knowledge-parent-field">
          <span>Батьківська категорія</span>
          <button
            type="button"
            className={`knowledge-parent-trigger ${parentPickerOpen ? 'active' : ''}`}
            aria-expanded={parentPickerOpen}
            onClick={() => setParentPickerOpen((current) => !current)}
          >
            <span>{selectedParentLabel}</span>
            <ChevronDown size={17} />
          </button>
          {parentPickerOpen ? (
            <div className="knowledge-parent-popover">
              <label className="knowledge-parent-search">
                <Search size={16} />
                <input value={parentSearch} placeholder="Пошук категорії" onChange={(event) => setParentSearch(event.target.value)} />
              </label>
              <div className="knowledge-parent-tree">
                <button
                  type="button"
                  className={!draft.parent ? 'active' : ''}
                  onClick={() => {
                    onDraftChange({ ...draft, parent: '' });
                    setParentPickerOpen(false);
                  }}
                >
                  <span className="knowledge-parent-branch" />
                  <span className="knowledge-parent-icon">—</span>
                  <strong>Без батьківської категорії</strong>
                </button>
                {availableParentRows.map((node, index) => (
                  <button
                    type="button"
                    key={node.category.id}
                    className={draft.parent === String(node.category.id) ? 'active' : ''}
                    style={{ '--picker-depth': Math.min(node.depth, 6) } as CSSProperties}
                    onClick={() => {
                      onDraftChange({ ...draft, parent: String(node.category.id) });
                      setParentPickerOpen(false);
                    }}
                  >
                    <span className="knowledge-parent-branch" />
                    <span className="knowledge-parent-icon">{categoryIcon(node.category, index)}</span>
                    <strong>{node.category.name}</strong>
                    {node.totalDocumentCount ? <em>{node.totalDocumentCount}</em> : null}
                  </button>
                ))}
              </div>
            </div>
          ) : null}
        </label>
        <label>
          <span>Опис</span>
          <textarea value={draft.description} onChange={(event) => onDraftChange({ ...draft, description: event.target.value })} />
        </label>
        <section className="knowledge-audience-box">
          <strong>Призначено</strong>
          <span className="audience-chip">Цикл зайнятості є Працюючі</span>
          <div className="knowledge-audience-options">
            <button
              type="button"
              className={draft.visibility_mode === 'specific' ? 'active' : ''}
              onClick={() => onDraftChange({ ...draft, visibility_mode: 'specific' })}
            >
              <span className="radio-dot" />
              <div>
                <strong>Конкретні люди</strong>
                <span>Вкажіть ID співробітників</span>
              </div>
            </button>
            <button
              type="button"
              className={draft.visibility_mode === 'all' ? 'active' : ''}
              onClick={() => onDraftChange({ ...draft, visibility_mode: 'all', audience_employee_ids: '' })}
            >
              <span className="radio-dot" />
              <div>
                <strong>Усі</strong>
                <span>Включає всіх працюючих</span>
              </div>
            </button>
          </div>
          {draft.visibility_mode === 'specific' ? (
            <div className="knowledge-specific-people">
              <label>
                <span>Пошук людей</span>
                <input value={peopleSearch} placeholder="Імʼя, посада, email" onChange={(event) => setPeopleSearch(event.target.value)} />
              </label>
              <div className="knowledge-people-picker">
                {filteredPeople.map((person) => (
                  <label key={person.id} className={selectedIdSet.has(person.id) ? 'active' : ''}>
                    <input type="checkbox" checked={selectedIdSet.has(person.id)} onChange={() => togglePerson(person.id)} />
                    <Avatar name={person.full_name} size="sm" accent="teal" />
                    <span>
                      <strong>{person.full_name}</strong>
                      <em>{person.position_name || person.department_name || person.email || `ID ${person.id}`}</em>
                    </span>
                  </label>
                ))}
              </div>
              <input
                value={draft.audience_employee_ids}
                placeholder="ID співробітників"
                onChange={(event) => onDraftChange({ ...draft, audience_employee_ids: event.target.value })}
              />
            </div>
          ) : null}
          <div className="knowledge-audience-summary">
            <span className="audience-avatar">V</span>
            <span className="audience-avatar muted">HR</span>
            <strong>{draft.visibility_mode === 'specific' ? selectedSpecificIds.length : activePeopleTotal || '—'} людей</strong>
            <span>відповідають обраним критеріям</span>
          </div>
        </section>
        {error ? <p className="form-error">{error}</p> : null}
        <div className="knowledge-dialog-actions">
          <button type="button" className="secondary-action" onClick={onClose}>
            Скасувати
          </button>
          <button type="submit" className="primary-action" disabled={saveState === 'loading'}>
            <Save size={17} />
            {saveState === 'loading' ? 'Збереження...' : 'Зберегти'}
          </button>
        </div>
      </form>
    </div>
  );
}

function KnowledgeCategoryView({
  category,
  childNodes,
  documents,
  loadState,
  emptyTitle,
  emptyText,
  onOpenDocument,
  onOpenCategory,
  onCreateDocument,
}: {
  category: KnowledgeCategory | null;
  childNodes: KnowledgeCategoryTreeNode[];
  documents: KnowledgeDocument[];
  loadState: LoadState;
  emptyTitle: string;
  emptyText: string;
  onOpenDocument: (document: KnowledgeDocument) => void;
  onOpenCategory: (categoryId: number) => void;
  onCreateDocument: () => void;
}) {
  if (!category) {
    return (
      <div className="panel">
        <EmptyState title={emptyTitle} text={emptyText} />
      </div>
    );
  }

  return (
    <>
      <header className="knowledge-category-header">
        <div className="knowledge-title-row flat">
          <span className="knowledge-category-icon">🧑‍💼</span>
          <div>
            <h1>{category.name}</h1>
            <p>{category.description || categoryDescription(category.name)}</p>
          </div>
        </div>
        <button type="button" className="toolbar-button strong" onClick={onCreateDocument}>
          <Plus size={17} />
          Додати сторінку
        </button>
      </header>
      <div className="knowledge-list">
        {childNodes.length ? (
          <div className="knowledge-subcategory-grid">
            {childNodes.map((node, index) => (
              <button type="button" key={node.category.id} className="knowledge-category-card" onClick={() => onOpenCategory(node.category.id)}>
                <span className="knowledge-category-icon">{categoryIcon(node.category, index)}</span>
                <div>
                  <strong>{node.category.name}</strong>
                  <span>{node.category.description || categoryDescription(node.category.name)}</span>
                </div>
                <em>{node.totalDocumentCount}</em>
              </button>
            ))}
          </div>
        ) : null}
        {documents.length ? (
          documents.map((document) => (
            <button type="button" key={document.id} onClick={() => onOpenDocument(document)}>
              <span className="drag-dots">••</span>
              <div>
                <strong>{document.title}</strong>
                <span>Останнє оновлення {formatDateTime(document.updated_at)}</span>
              </div>
            </button>
          ))
        ) : (
          <div className="panel">
            <EmptyState
              title={loadState === 'loading' ? 'Завантаження документів' : 'Сторінки не знайдені'}
              text={childNodes.length ? 'У цій категорії є підкатегорії, але немає сторінок напряму.' : emptyText}
            />
          </div>
        )}
      </div>
    </>
  );
}

function KnowledgeEditorView({
  draft,
  category,
  saveState,
  error,
  onDraftChange,
  onCancel,
  onSaveDraft,
  onPublish,
}: {
  draft: KnowledgeEditorDraft;
  category: KnowledgeCategory | null;
  saveState: LoadState;
  error: string;
  onDraftChange: (draft: KnowledgeEditorDraft) => void;
  onCancel: () => void;
  onSaveDraft: () => void;
  onPublish: () => void;
}) {
  const editorRef = useRef<HTMLElement | null>(null);
  const headerRef = useRef<HTMLElement | null>(null);
  const bodyRef = useRef<HTMLTextAreaElement | null>(null);
  const videoInputRef = useRef<HTMLInputElement | null>(null);
  const [coverModalOpen, setCoverModalOpen] = useState(false);
  const [metaOpen, setMetaOpen] = useState(false);
  const [activeToolMenu, setActiveToolMenu] = useState<null | 'color' | 'font' | 'emoji' | 'video' | 'social'>(null);
  const [videoUrl, setVideoUrl] = useState('');
  const [videoUploadState, setVideoUploadState] = useState<LoadState>('idle');
  const [mediaError, setMediaError] = useState('');
  const [socialType, setSocialType] = useState(knowledgeSocialOptions[0].id);
  const [socialUrl, setSocialUrl] = useState('');
  const displayTitle = draft.title.trim() || 'Untitled page';
  const categoryName = category?.name || 'База знань';
  const categoryEmoji = category ? categoryIcon(category, 0) : '📄';

  useEffect(() => {
    const element = bodyRef.current;
    if (!element) return;
    element.style.height = 'auto';
    element.style.height = `${Math.max(420, element.scrollHeight)}px`;
  }, [draft.body]);

  useEffect(() => {
    const editor = editorRef.current;
    const header = headerRef.current;
    if (!editor || !header) return;

    const syncHeaderHeight = () => {
      editor.style.setProperty('--knowledge-editor-header-height', `${Math.ceil(header.getBoundingClientRect().height)}px`);
    };

    syncHeaderHeight();
    window.addEventListener('resize', syncHeaderHeight);
    const observer = typeof ResizeObserver !== 'undefined' ? new ResizeObserver(syncHeaderHeight) : null;
    observer?.observe(header);

    return () => {
      window.removeEventListener('resize', syncHeaderHeight);
      observer?.disconnect();
    };
  }, []);

  const editorToolbar = (
    <div className="knowledge-editor-tools" aria-label="Панель форматування">
      <div className="knowledge-tool-group">
        <button type="button" onClick={() => applyFormat('h1')} title="Heading 1">
          <Heading1 size={17} />
        </button>
        <button type="button" onClick={() => applyFormat('h2')} title="Heading 2">
          <Heading2 size={17} />
        </button>
        <button type="button" onClick={() => applyFormat('h3')} title="Heading 3">
          <span className="knowledge-tool-text">H3</span>
        </button>
      </div>
      <div className="knowledge-tool-group">
        <button type="button" onClick={() => applyFormat('bold')} title="Bold">
          <Bold size={17} />
        </button>
        <button type="button" onClick={() => applyFormat('italic')} title="Italic">
          <Italic size={17} />
        </button>
        <button type="button" onClick={() => applyFormat('underline')} title="Underline">
          <Underline size={17} />
        </button>
      </div>
      <div className="knowledge-tool-group">
        <button type="button" onClick={() => applyFormat('bullet')} title="Bullet list">
          <List size={17} />
        </button>
        <button type="button" onClick={() => applyFormat('ordered')} title="Ordered list">
          <ListOrdered size={17} />
        </button>
        <button type="button" onClick={() => applyFormat('quote')} title="Quote">
          <Quote size={17} />
        </button>
      </div>
      <div className="knowledge-tool-menu-wrap">
        <button type="button" className={activeToolMenu === 'font' ? 'active' : ''} onClick={() => toggleToolMenu('font')} title="Шрифт">
          <Type size={17} />
        </button>
        {activeToolMenu === 'font' ? (
          <div className="knowledge-tool-popover compact">
            {knowledgeFontOptions.map((font) => (
              <button type="button" key={font.id} className={`kb-font-${font.id}`} onClick={() => applyFormat(`font:${font.id}`)}>
                <strong>{font.sample}</strong>
                <span>{font.label}</span>
              </button>
            ))}
          </div>
        ) : null}
      </div>
      <div className="knowledge-tool-menu-wrap">
        <button type="button" className={activeToolMenu === 'color' ? 'active' : ''} onClick={() => toggleToolMenu('color')} title="Колір тексту">
          <Palette size={17} />
        </button>
        {activeToolMenu === 'color' ? (
          <div className="knowledge-tool-popover color-grid">
            {knowledgeTextColors.map((color) => (
              <button type="button" key={color.id} onClick={() => applyFormat(`color:${color.id}`)} title={color.label}>
                <span style={{ backgroundColor: color.value }} />
                <em>{color.label}</em>
              </button>
            ))}
          </div>
        ) : null}
      </div>
      <div className="knowledge-tool-menu-wrap">
        <button type="button" className={activeToolMenu === 'emoji' ? 'active' : ''} onClick={() => toggleToolMenu('emoji')} title="Emoji">
          <Smile size={17} />
        </button>
        {activeToolMenu === 'emoji' ? (
          <div className="knowledge-tool-popover emoji-grid">
            {knowledgeEditorEmojiOptions.map((emoji) => (
              <button type="button" key={emoji} onClick={() => insertEmoji(emoji)}>
                {emoji}
              </button>
            ))}
          </div>
        ) : null}
      </div>
      <div className="knowledge-tool-group">
        <button type="button" onClick={() => applyFormat('link')} title="Посилання">
          <Link size={17} />
        </button>
        <button type="button" onClick={() => applyFormat('image')} title="Зображення за URL">
          <ImagePlus size={17} />
        </button>
      </div>
      <div className="knowledge-tool-menu-wrap">
        <button type="button" className={activeToolMenu === 'video' ? 'active' : ''} onClick={() => toggleToolMenu('video')} title="Відео">
          <Video size={17} />
        </button>
        {activeToolMenu === 'video' ? (
          <div className="knowledge-tool-popover media-popover">
            <label>
              <span>Відео за посиланням</span>
              <input value={videoUrl} placeholder="https://..." onChange={(event) => setVideoUrl(event.target.value)} />
            </label>
            <div className="knowledge-tool-actions">
              <button type="button" className="secondary-action compact-action" onClick={() => insertVideoUrl(videoUrl)}>
                <Link size={15} />
                Додати URL
              </button>
              <button type="button" className="secondary-action compact-action" onClick={() => videoInputRef.current?.click()}>
                <Upload size={15} />
                Файл
              </button>
            </div>
            <input ref={videoInputRef} type="file" accept="video/*" hidden onChange={(event) => uploadVideoFile(event.target.files?.[0])} />
            {videoUploadState === 'loading' ? <em className="knowledge-tool-note">Відео перекодовується...</em> : null}
            {mediaError ? <em className="knowledge-tool-error">{mediaError}</em> : null}
          </div>
        ) : null}
      </div>
      <div className="knowledge-tool-menu-wrap">
        <button type="button" className={activeToolMenu === 'social' ? 'active' : ''} onClick={() => toggleToolMenu('social')} title="Соцмережі">
          <Sparkles size={17} />
        </button>
        {activeToolMenu === 'social' ? (
          <div className="knowledge-tool-popover media-popover social-popover">
            <div className="social-options">
              {knowledgeSocialOptions.map((option) => (
                <button type="button" key={option.id} className={socialType === option.id ? 'active' : ''} onClick={() => setSocialType(option.id)}>
                  {option.label}
                </button>
              ))}
            </div>
            <label>
              <span>Посилання</span>
              <input
                value={socialUrl}
                placeholder={knowledgeSocialOptions.find((option) => option.id === socialType)?.placeholder || 'https://'}
                onChange={(event) => setSocialUrl(event.target.value)}
              />
            </label>
            <button type="button" className="secondary-action compact-action" onClick={() => insertSocialLink(socialType, socialUrl)}>
              <Link size={15} />
              Додати соцпосилання
            </button>
          </div>
        ) : null}
      </div>
    </div>
  );

  function updateBody(nextBody: string, selectionStart?: number, selectionEnd?: number) {
    onDraftChange({ ...draft, body: nextBody });
    if (selectionStart === undefined || selectionEnd === undefined) return;
    window.requestAnimationFrame(() => {
      bodyRef.current?.focus();
      bodyRef.current?.setSelectionRange(selectionStart, selectionEnd);
    });
  }

  function toggleToolMenu(menu: NonNullable<typeof activeToolMenu>) {
    setActiveToolMenu((current) => (current === menu ? null : menu));
    setMediaError('');
  }

  function replaceSelection(insert: string, selectStartOffset = insert.length, selectEndOffset = insert.length) {
    const element = bodyRef.current;
    const start = element?.selectionStart ?? draft.body.length;
    const end = element?.selectionEnd ?? draft.body.length;
    const before = draft.body.slice(0, start);
    const after = draft.body.slice(end);
    const nextBody = `${before}${insert}${after}`;
    updateBody(nextBody, before.length + selectStartOffset, before.length + selectEndOffset);
  }

  function wrapSelection(prefix: string, suffix: string, fallback = 'текст') {
    const element = bodyRef.current;
    const start = element?.selectionStart ?? draft.body.length;
    const end = element?.selectionEnd ?? draft.body.length;
    const selected = draft.body.slice(start, end) || fallback;
    replaceSelection(`${prefix}${selected}${suffix}`, prefix.length, prefix.length + selected.length);
  }

  function insertEmoji(emoji: string) {
    replaceSelection(emoji);
    setActiveToolMenu(null);
  }

  function insertVideoUrl(url: string) {
    const trimmed = url.trim();
    if (!/^https?:\/\/|^\/media\//i.test(trimmed)) {
      setMediaError('Вкажіть коректне https-посилання або завантажте файл.');
      return;
    }
    replaceSelection(`\n@[video](${trimmed})\n`);
    setVideoUrl('');
    setMediaError('');
    setActiveToolMenu(null);
  }

  async function uploadVideoFile(file: File | null | undefined) {
    if (!file) return;
    if (!file.type.startsWith('video/')) {
      setMediaError('Оберіть відеофайл.');
      return;
    }
    setVideoUploadState('loading');
    setMediaError('');
    try {
      const result = await api.uploadKnowledgeMedia(file);
      replaceSelection(`\n@[video](${result.url})\n`);
      setVideoUploadState('ok');
      setActiveToolMenu(null);
    } catch (err) {
      setVideoUploadState('error');
      setMediaError(err instanceof ApiError ? err.message : 'Не вдалося завантажити відео.');
    } finally {
      if (videoInputRef.current) videoInputRef.current.value = '';
    }
  }

  function insertSocialLink(type: string, url: string) {
    const trimmed = url.trim();
    if (!/^https?:\/\//i.test(trimmed)) {
      setMediaError('Вкажіть повне посилання, наприклад https://instagram.com/...');
      return;
    }
    replaceSelection(`\n@[social:${type}](${trimmed})\n`);
    setSocialUrl('');
    setMediaError('');
    setActiveToolMenu(null);
  }

  function applyFormat(format: string) {
    const element = bodyRef.current;
    const start = element?.selectionStart ?? draft.body.length;
    const end = element?.selectionEnd ?? draft.body.length;
    const before = draft.body.slice(0, start);
    const selected = draft.body.slice(start, end);
    const after = draft.body.slice(end);
    const fallback = selected || 'текст';
    let insert = fallback;

    if (format === 'h1') insert = `# ${fallback}`;
    if (format === 'h2') insert = `## ${fallback}`;
    if (format === 'h3') insert = `### ${fallback}`;
    if (format === 'bold') insert = `**${fallback}**`;
    if (format === 'italic') insert = `_${fallback}_`;
    if (format === 'underline') insert = `++${fallback}++`;
    if (format === 'bullet') insert = selected ? selected.split('\n').map((line) => `- ${line}`).join('\n') : '- пункт списку';
    if (format === 'ordered') insert = selected ? selected.split('\n').map((line, index) => `${index + 1}. ${line}`).join('\n') : '1. пункт списку';
    if (format === 'quote') insert = selected ? selected.split('\n').map((line) => `> ${line}`).join('\n') : '> цитата';
    if (format === 'link') insert = `[${selected || 'посилання'}](https://)`;
    if (format === 'image') insert = `![${selected || 'Опис зображення'}](https://)`;
    if (format.startsWith('color:')) {
      wrapSelection(`{color:${format.slice(6)}}`, '{/color}', fallback);
      setActiveToolMenu(null);
      return;
    }
    if (format.startsWith('font:')) {
      wrapSelection(`{font:${format.slice(5)}}`, '{/font}', fallback);
      setActiveToolMenu(null);
      return;
    }

    const nextBody = `${before}${insert}${after}`;
    updateBody(nextBody, before.length, before.length + insert.length);
  }

  return (
    <article ref={editorRef} className="knowledge-editor">
      <header ref={headerRef} className="knowledge-editor-header">
        <div className="knowledge-editor-heading">
          <div className="knowledge-editor-breadcrumb">
            <span>{categoryEmoji}</span>
            {categoryName}
          </div>
          <div className="knowledge-editor-heading-row">
            <span className="knowledge-editor-page-icon">{categoryEmoji}</span>
            <div>
              <h1>{displayTitle}</h1>
              <div className="knowledge-editor-state-row">
                <span className="knowledge-editor-status">{draft.status === 'published' ? 'Опубліковано' : 'Чернетка'}</span>
                <div className="knowledge-editor-meta-wrap">
                  <button
                    type="button"
                    className="knowledge-document-views"
                    data-tooltip="Переглянути більше"
                    aria-label={`Переглянути відвідувачів: ${draft.view_count || 0}`}
                    onClick={() => setMetaOpen((current) => !current)}
                  >
                    <Eye size={14} />
                    <span>{draft.view_count || 0}</span>
                  </button>
                  {metaOpen ? (
                    <div className="knowledge-editor-meta-popover">
                      <span>Створено</span>
                      <strong>{draft.created_at ? formatDateTime(draft.created_at) : 'Новий документ'}</strong>
                      <span>Створено</span>
                      <strong>{draft.owner_name || 'HR Vidnova'}</strong>
                      <span>Останнє оновлення</span>
                      <strong>{draft.updated_at ? formatDateTime(draft.updated_at) : 'Ще не збережено'}</strong>
                    </div>
                  ) : null}
                </div>
              </div>
            </div>
          </div>
        </div>
        <div className="knowledge-editor-actions">
          <button type="button" className="icon-button" title="Історія змін">
            <Clock3 size={17} />
            <span>0</span>
          </button>
          <button type="button" className="secondary-action compact-action" disabled={saveState === 'loading'} onClick={onSaveDraft}>
            <Save size={16} />
            Чернетка
          </button>
          <button type="button" className="icon-button" title="Додаткові дії">
            <MoreHorizontal size={18} />
          </button>
          <button type="button" className="secondary-action" onClick={onCancel}>
            <X size={17} />
            Скасувати
          </button>
          <button type="button" className="primary-action" disabled={saveState === 'loading'} onClick={onPublish}>
            <Rocket size={17} />
            Опублікувати
          </button>
        </div>
      </header>

      <div className="knowledge-editor-canvas">
        <div className="knowledge-editor-cover-control">
          <button type="button" className="toolbar-button" onClick={() => setCoverModalOpen(true)}>
            <ImagePlus size={17} />
            {draft.cover_url ? 'Змінити обкладинку' : 'Додати обкладинку'}
          </button>
          {draft.cover_url ? (
            <button type="button" className="secondary-action compact-action" onClick={() => onDraftChange({ ...draft, cover_url: '' })}>
              <X size={15} />
              Прибрати
            </button>
          ) : null}
        </div>
        {draft.cover_url ? (
          <div className="knowledge-editor-cover">
            <img src={draft.cover_url} alt="" />
          </div>
        ) : null}
        <label className="knowledge-editor-title">
          <span>Заголовок</span>
          <input
            value={draft.title}
            placeholder="Untitled page"
            onChange={(event) => onDraftChange({ ...draft, title: event.target.value })}
          />
        </label>
        <label className="knowledge-editor-field compact">
          <span>Короткий опис</span>
          <input value={draft.summary} placeholder="Опис для списків і пошуку" onChange={(event) => onDraftChange({ ...draft, summary: event.target.value })} />
        </label>
        <label className="knowledge-editor-field">
          <span>Текст сторінки</span>
          <div className="knowledge-editor-textbox">
            {editorToolbar}
            <textarea
              ref={bodyRef}
              value={draft.body}
              placeholder="Пишіть текст сторінки..."
              onChange={(event) => onDraftChange({ ...draft, body: event.target.value })}
            />
          </div>
        </label>
        {error ? <p className="form-error">{error}</p> : null}
      </div>
      {coverModalOpen ? (
        <KnowledgeCoverUploadModal
          onClose={() => setCoverModalOpen(false)}
          onUploaded={(url) => {
            onDraftChange({ ...draft, cover_url: url });
            setCoverModalOpen(false);
          }}
        />
      ) : null}
    </article>
  );
}

function KnowledgeCoverUploadModal({ onClose, onUploaded }: { onClose: () => void; onUploaded: (url: string) => void }) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const imageRef = useRef<HTMLImageElement | null>(null);
  const [objectUrl, setObjectUrl] = useState('');
  const [sourceName, setSourceName] = useState('cover');
  const [zoom, setZoom] = useState(1);
  const [saveState, setSaveState] = useState<LoadState>('idle');
  const [error, setError] = useState('');

  useEffect(() => {
    return () => {
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [objectUrl]);

  function selectFile(file: File | null | undefined) {
    if (!file) return;
    if (!file.type.startsWith('image/')) {
      setError('Завантажте зображення у форматі JPEG, PNG, GIF або WebP.');
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      setError('Максимальний розмір файлу 5 МБ.');
      return;
    }
    if (objectUrl) URL.revokeObjectURL(objectUrl);
    setObjectUrl(URL.createObjectURL(file));
    setSourceName(file.name.replace(/\.[^.]+$/, '') || 'cover');
    setZoom(1);
    setError('');
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    selectFile(event.dataTransfer.files[0]);
  }

  async function saveCover() {
    const image = imageRef.current;
    if (!image || !objectUrl || !image.naturalWidth || !image.naturalHeight) {
      setError('Зображення ще не готове для обрізки.');
      return;
    }

    setSaveState('loading');
    setError('');
    try {
      const outputWidth = 1440;
      const outputHeight = 360;
      const canvas = document.createElement('canvas');
      canvas.width = outputWidth;
      canvas.height = outputHeight;
      const context = canvas.getContext('2d');
      if (!context) throw new Error('Canvas is unavailable');
      context.fillStyle = '#f5f7fb';
      context.fillRect(0, 0, outputWidth, outputHeight);
      const scale = Math.max(outputWidth / image.naturalWidth, outputHeight / image.naturalHeight) * zoom;
      const drawWidth = image.naturalWidth * scale;
      const drawHeight = image.naturalHeight * scale;
      context.drawImage(image, (outputWidth - drawWidth) / 2, (outputHeight - drawHeight) / 2, drawWidth, drawHeight);
      const blob = await new Promise<Blob>((resolve, reject) => {
        canvas.toBlob((result) => (result ? resolve(result) : reject(new Error('Cover conversion failed'))), 'image/webp', 0.84);
      });
      const safeName = sourceName.replace(/[^0-9A-Za-zА-Яа-яІіЇїЄєҐґ_-]+/g, '-').replace(/^-+|-+$/g, '') || 'cover';
      const file = new File([blob], `${safeName}.webp`, { type: 'image/webp' });
      const result = await api.uploadKnowledgeCover(file);
      onUploaded(result.url);
      setSaveState('ok');
    } catch (err) {
      setSaveState('error');
      setError(err instanceof ApiError ? err.message : 'Не вдалося зберегти обкладинку.');
    }
  }

  return (
    <div className="knowledge-modal-layer cover-modal-layer" role="dialog" aria-modal="true" aria-label="Завантажити обкладинку">
      <div className="knowledge-cover-modal">
        <button type="button" className="modal-close" aria-label="Закрити" onClick={onClose}>
          <X size={22} />
        </button>
        {!objectUrl ? (
          <div
            className="cover-dropzone"
            onDragOver={(event) => event.preventDefault()}
            onDrop={handleDrop}
            onClick={() => inputRef.current?.click()}
          >
            <input
              ref={inputRef}
              type="file"
              accept="image/jpeg,image/png,image/gif,image/webp"
              onChange={(event) => selectFile(event.target.files?.[0])}
            />
            <ImagePlus size={24} />
            <strong>Для завантаження перетягніть файл або натисніть сюди</strong>
            <span>Макс. файлів: 1, максимальний розмір файлу: 5МБ.</span>
            <span>Дозволені типи файлів .jpeg, .png, .gif, .webp.</span>
          </div>
        ) : (
          <>
            <div className="cover-crop-frame">
              <img ref={imageRef} src={objectUrl} alt="" style={{ transform: `scale(${zoom})` }} />
              <div className="cover-crop-grid" />
            </div>
            <div className="cover-crop-controls">
              <ZoomOut size={18} />
              <input
                type="range"
                min="1"
                max="2.6"
                step="0.05"
                value={zoom}
                onChange={(event) => setZoom(Number(event.target.value))}
              />
              <ZoomIn size={18} />
              <button type="button" className="icon-button" aria-label="Скинути масштаб" onClick={() => setZoom(1)}>
                <Clock3 size={17} />
              </button>
            </div>
            <div className="cover-modal-actions">
              <button type="button" className="secondary-action" onClick={() => setObjectUrl('')}>
                <ChevronLeft size={17} />
                Назад
              </button>
              <button type="button" className="primary-action" disabled={saveState === 'loading'} onClick={saveCover}>
                {saveState === 'loading' ? 'Збереження...' : 'Зберегти'}
              </button>
            </div>
          </>
        )}
        {error ? <p className="form-error">{error}</p> : null}
      </div>
    </div>
  );
}

function KnowledgeArticleView({
  document,
  category,
  onEdit,
  onClose,
}: {
  document: KnowledgeDocument;
  category: KnowledgeCategory | null;
  onEdit: () => void;
  onClose: () => void;
}) {
  const sanitizedHtml = useMemo(() => sanitizeKnowledgeHtml(document.body_html), [document.body_html]);
  const fallbackText = useMemo(() => extractKnowledgeText(document.body), [document.body]);
  const fallbackLinks = useMemo(() => extractKnowledgeLinks(document.body), [document.body]);

  return (
    <article className="knowledge-article">
      <header className="knowledge-article-header">
        <div className="knowledge-article-headline">
          <div className="knowledge-breadcrumb">
            <span>🧑‍💼</span>
            <button type="button">{category?.name || document.category_name}</button>
          </div>
          <div className="knowledge-title-row">
            <span className="knowledge-category-icon">📄</span>
            <div>
              <h1>{document.title}</h1>
              <div className="knowledge-article-meta">
                <span className={`publish-pill ${document.status === 'draft' ? 'draft' : ''}`}>
                  {document.status === 'published' ? 'Опубліковано' : 'Чернетка'}
                </span>
                <span
                  className="knowledge-document-views"
                  data-tooltip="Переглянути більше"
                  aria-label={`Переглядів: ${document.view_count || 0}`}
                >
                  <Eye size={14} />
                  <span>{document.view_count || 0}</span>
                </span>
                <span>Оновлено {formatDateTime(document.updated_at)}</span>
              </div>
            </div>
          </div>
        </div>
        <div className="knowledge-article-actions">
          <button type="button" className="toolbar-button" onClick={onEdit}>
            <Edit3 size={17} />
            Редагувати
          </button>
          <button type="button" className="icon-button knowledge-mobile-close" aria-label="Закрити документ" onClick={onClose}>
            <X size={18} />
          </button>
        </div>
      </header>
      <div className="knowledge-article-body">
        {document.cover_url ? (
          <div className="knowledge-cover">
            <img src={document.cover_url} alt="" />
          </div>
        ) : null}
        {sanitizedHtml ? <div dangerouslySetInnerHTML={{ __html: sanitizedHtml }} /> : null}
        {!sanitizedHtml && fallbackText.length ? (
          <div className="knowledge-fallback-text">
            {fallbackText.map((text, index) => (
              <p key={`${document.id}-text-${index}`}>{text}</p>
            ))}
          </div>
        ) : null}
        {fallbackLinks.length ? (
          <div className="knowledge-links">
            {fallbackLinks.map((link) => (
              <a key={link.href} href={link.href} target="_blank" rel="noopener noreferrer">
                <FileText size={16} />
                {link.label}
              </a>
            ))}
          </div>
        ) : null}
        {document.attachments.length ? (
          <div className="knowledge-links">
            {document.attachments.map((attachment) => (
              <a key={attachment.id} href={attachment.file || attachment.source_url} target="_blank" rel="noopener noreferrer">
                <FileText size={16} />
                {attachment.original_name}
              </a>
            ))}
          </div>
        ) : null}
        {!sanitizedHtml && !fallbackText.length && !fallbackLinks.length && !document.attachments.length ? (
          <EmptyState title="Вміст не завантажений" text="Документ імпортовано, але текст або вкладення відсутні в PeopleForce payload." />
        ) : null}
      </div>
    </article>
  );
}

function renderKnowledgeEditorHtml(value: string): string {
  const lines = value.split('\n');
  const html: string[] = [];

  lines.forEach((line) => {
    const trimmed = line.trim();
    if (!trimmed) return;
    if (trimmed.startsWith('# ')) {
      html.push(`<h1>${renderInlineMarkdown(trimmed.slice(2))}</h1>`);
      return;
    }
    if (trimmed.startsWith('## ')) {
      html.push(`<h2>${renderInlineMarkdown(trimmed.slice(3))}</h2>`);
      return;
    }
    if (trimmed.startsWith('### ')) {
      html.push(`<h3>${renderInlineMarkdown(trimmed.slice(4))}</h3>`);
      return;
    }
    if (trimmed.startsWith('- ')) {
      html.push(`<ul><li>${renderInlineMarkdown(trimmed.slice(2))}</li></ul>`);
      return;
    }
    if (/^\d+\.\s/.test(trimmed)) {
      html.push(`<ol><li>${renderInlineMarkdown(trimmed.replace(/^\d+\.\s/, ''))}</li></ol>`);
      return;
    }
    if (trimmed.startsWith('> ')) {
      html.push(`<blockquote>${renderInlineMarkdown(trimmed.slice(2))}</blockquote>`);
      return;
    }
    html.push(`<p>${renderInlineMarkdown(trimmed)}</p>`);
  });

  return html.join('\n');
}

function renderInlineMarkdown(value: string): string {
  return escapeHtml(value)
    .replace(/\{color:(ink|violet|teal|rose|amber|blue)\}([\s\S]+?)\{\/color\}/g, '<span class="kb-color-$1">$2</span>')
    .replace(/\{font:(sans|serif|mono)\}([\s\S]+?)\{\/font\}/g, '<span class="kb-font-$1">$2</span>')
    .replace(/@\[video\]\(((?:https?:\/\/|\/media\/)[^)]+)\)/g, '<video class="kb-video" src="$1" controls preload="metadata" playsinline></video>')
    .replace(/@\[social:([a-z-]+)\]\((https?:\/\/[^)]+)\)/g, (_match, type: string, url: string) => {
      const safeType = knowledgeSocialOptions.some((option) => option.id === type) ? type : 'website';
      return `<a class="kb-social kb-social-${safeType}" href="${url}" target="_blank" rel="noopener noreferrer">${knowledgeSocialLabel(safeType)}</a>`;
    })
    .replace(/!\[([^\]]*)\]\(((?:https?:\/\/|\/media\/)[^)]+)\)/g, '<img src="$2" alt="$1" />')
    .replace(/\[([^\]]+)\]\((https?:\/\/[^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/_([^_]+)_/g, '<em>$1</em>')
    .replace(/\+\+([^+]+)\+\+/g, '<u>$1</u>');
}

function knowledgeSocialLabel(type: string): string {
  return knowledgeSocialOptions.find((option) => option.id === type)?.label || 'Посилання';
}

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function categoryDescription(name: string): string {
  const descriptions: Record<string, string> = {
    'Стандарти клініки': 'Регламенти, стандарти сервісу і роботи клініки',
    'Маркетинг і Аналітика': 'Матеріали для маркетингу, NPS та аналітики',
    'Для директорів': 'Посадові інструкції керівників, KPI і документи',
    'Медичні керівники': 'Матеріали для керівників медичних напрямків',
    'Робота з BAF': 'Імпорт, перевірка і щоденна робота з BAF',
    Адміністраторам: 'Інструкції для адміністраторів клінік',
    'Контакт-центр': 'Скрипти, стандарти і довідники контакт-центру',
  };
  return descriptions[name] ?? 'Документи і матеріали компанії';
}

function categoryIcon(category: KnowledgeCategory, index: number): string {
  if (category.icon_emoji && category.icon_emoji !== '📄') return category.icon_emoji;
  const name = category.name.toLowerCase();
  if (name.includes('hr') || name.includes('peopleforce')) return '🧑‍💼';
  if (name.includes('згод') || name.includes('стомат')) return '🦷';
  if (name.includes('страх')) return '🛡';
  if (name.includes('директор') || name.includes('керівник')) return '💼';
  if (name.includes('медич')) return '🩺';
  if (name.includes('baf')) return '💻';
  if (name.includes('адмін')) return '🙂';
  if (name.includes('контакт')) return '☎';
  if (name.includes('маркет') || name.includes('аналіт')) return '📊';
  if (name.includes('звіт')) return '📈';
  if (name.includes('лояль')) return '❤️';
  if (name.includes('протокол') || name.includes('регламент') || name.includes('стандарт')) return '🧾';
  if (name.includes('рекоменда')) return '💬';
  if (name.includes('посад')) return '📋';
  return knowledgeCategoryIcons[index % knowledgeCategoryIcons.length];
}

function buildKnowledgeCategoryTree(
  categories: KnowledgeCategory[],
  documentsByCategory: Map<number, KnowledgeDocument[]>,
): KnowledgeCategoryTreeNode[] {
  const nodeMap = new Map<number, KnowledgeCategoryTreeNode>();
  categories.forEach((category) => {
    nodeMap.set(category.id, {
      category,
      children: [],
      depth: 0,
      ownDocumentCount: documentsByCategory.get(category.id)?.length ?? 0,
      totalDocumentCount: documentsByCategory.get(category.id)?.length ?? 0,
    });
  });

  const roots: KnowledgeCategoryTreeNode[] = [];
  categories.forEach((category) => {
    const node = nodeMap.get(category.id);
    if (!node) return;
    const parentNode = category.parent ? nodeMap.get(category.parent) : null;
    if (parentNode) {
      parentNode.children.push(node);
    } else {
      roots.push(node);
    }
  });

  function calculateTotals(node: KnowledgeCategoryTreeNode, depth = 0): number {
    node.depth = depth;
    node.children.sort((first, second) => first.category.position - second.category.position || first.category.name.localeCompare(second.category.name, 'uk'));
    node.totalDocumentCount = node.ownDocumentCount + node.children.reduce((total, child) => total + calculateTotals(child, depth + 1), 0);
    return node.totalDocumentCount;
  }

  roots.sort((first, second) => first.category.position - second.category.position || first.category.name.localeCompare(second.category.name, 'uk'));
  roots.forEach(calculateTotals);
  return roots;
}

function flattenKnowledgeTree(tree: KnowledgeCategoryTreeNode[]): KnowledgeCategoryTreeNode[] {
  const rows: KnowledgeCategoryTreeNode[] = [];
  function visit(node: KnowledgeCategoryTreeNode) {
    rows.push(node);
    node.children.forEach(visit);
  }
  tree.forEach(visit);
  return rows;
}

function mapKnowledgeCategoryNodes(tree: KnowledgeCategoryTreeNode[]): Map<number, KnowledgeCategoryTreeNode> {
  const nodes = new Map<number, KnowledgeCategoryTreeNode>();
  flattenKnowledgeTree(tree).forEach((node) => {
    nodes.set(node.category.id, node);
  });
  return nodes;
}

function buildKnowledgeNavRows(
  tree: KnowledgeCategoryTreeNode[],
  expandedCategoryIds: Set<number>,
  documentsByCategory: Map<number, KnowledgeDocument[]>,
): KnowledgeNavRow[] {
  const rows: KnowledgeNavRow[] = [];
  function visit(node: KnowledgeCategoryTreeNode) {
    rows.push({ type: 'category', node });
    if (expandedCategoryIds.has(node.category.id)) {
      node.children.forEach(visit);
      (documentsByCategory.get(node.category.id) ?? []).forEach((document) => {
        rows.push({ type: 'document', document, depth: node.depth });
      });
    }
  }
  tree.forEach(visit);
  return rows;
}

function knowledgeCategoryAncestorIds(categories: KnowledgeCategory[], categoryId: number): number[] {
  const byId = new Map(categories.map((category) => [category.id, category]));
  const ancestors: number[] = [];
  let current = byId.get(categoryId);
  while (current?.parent) {
    ancestors.unshift(current.parent);
    current = byId.get(current.parent);
  }
  return ancestors;
}

function categoryBreadcrumb(categories: KnowledgeCategory[], categoryId: number): string {
  const byId = new Map(categories.map((category) => [category.id, category]));
  const names: string[] = [];
  let current = byId.get(categoryId);
  const visited = new Set<number>();
  while (current && !visited.has(current.id)) {
    visited.add(current.id);
    names.unshift(current.name);
    current = current.parent ? byId.get(current.parent) : undefined;
  }
  return names.join(' / ');
}

function knowledgeCategoryDescendantIds(categories: KnowledgeCategory[], categoryId: number): number[] {
  const childrenByParent = new Map<number, KnowledgeCategory[]>();
  categories.forEach((category) => {
    if (!category.parent) return;
    const children = childrenByParent.get(category.parent) ?? [];
    children.push(category);
    childrenByParent.set(category.parent, children);
  });
  const ids: number[] = [];
  function visit(parentId: number) {
    (childrenByParent.get(parentId) ?? []).forEach((child) => {
      ids.push(child.id);
      visit(child.id);
    });
  }
  visit(categoryId);
  return ids;
}

function parseIdList(value: string): number[] {
  return value
    .split(',')
    .map((part) => Number(part.trim()))
    .filter((item) => Number.isInteger(item) && item > 0);
}

type OrgPersonNode = {
  employee: EmployeeListItem;
  children: OrgPersonNode[];
  directReportsCount?: number;
  totalReportsCount?: number;
  isExpanded?: boolean;
};

type OrgDepartmentNode = {
  department: DepartmentOption;
  children: OrgDepartmentNode[];
  directReportsCount?: number;
  totalReportsCount?: number;
  isExpanded?: boolean;
};

function employeeSearchText(employee: EmployeeListItem): string {
  return [
    employee.full_name,
    employee.position_name,
    employee.department_name,
    employee.division_name,
    employee.clinic_name,
    employee.manager_name,
    employee.email,
  ]
    .filter(Boolean)
    .join(' ')
    .toLowerCase();
}

function departmentSearchText(department: DepartmentOption): string {
  return [
    department.name,
    department.parent_name,
    department.manager_name,
    department.level_name,
    department.clinic_name,
  ]
    .filter(Boolean)
    .join(' ')
    .toLowerCase();
}

function sortOrgPeople(nodes: OrgPersonNode[]): OrgPersonNode[] {
  return [...nodes]
    .sort((first, second) => {
      const reportDiff = Number(second.employee.direct_reports_count || 0) - Number(first.employee.direct_reports_count || 0);
      if (reportDiff) return reportDiff;
      return first.employee.full_name.localeCompare(second.employee.full_name, 'uk');
    })
    .map((node) => ({ ...node, children: sortOrgPeople(node.children) }));
}

function buildPeopleOrgTree(employees: EmployeeListItem[]): OrgPersonNode[] {
  const nodeById = new Map<number, OrgPersonNode>();
  employees.forEach((employee) => {
    nodeById.set(employee.id, { employee, children: [] });
  });

  const roots: OrgPersonNode[] = [];
  nodeById.forEach((node) => {
    const managerId = node.employee.manager_profile?.id ?? null;
    const managerNode = managerId && managerId !== node.employee.id ? nodeById.get(managerId) : null;
    if (managerNode) {
      managerNode.children.push(node);
    } else {
      roots.push(node);
    }
  });

  return sortOrgPeople(roots);
}

function filterPeopleOrgTree(nodes: OrgPersonNode[], query: string): OrgPersonNode[] {
  const normalized = query.trim().toLowerCase();
  if (!normalized) return nodes;
  return nodes.flatMap((node) => {
    const children = filterPeopleOrgTree(node.children, normalized);
    if (employeeSearchText(node.employee).includes(normalized) || children.length) {
      return [{ ...node, children }];
    }
    return [];
  });
}

function buildDepartmentOrgTree(departments: DepartmentOption[]): OrgDepartmentNode[] {
  const nodeById = new Map<number, OrgDepartmentNode>();
  departments.forEach((department) => {
    nodeById.set(department.id, { department, children: [] });
  });

  const roots: OrgDepartmentNode[] = [];
  nodeById.forEach((node) => {
    const parentNode = node.department.parent ? nodeById.get(node.department.parent) : null;
    if (parentNode) {
      parentNode.children.push(node);
    } else {
      roots.push(node);
    }
  });

  function sort(nodes: OrgDepartmentNode[]): OrgDepartmentNode[] {
    return [...nodes]
      .sort((first, second) => first.department.name.localeCompare(second.department.name, 'uk'))
      .map((node) => ({ ...node, children: sort(node.children) }));
  }

  return sort(roots);
}

function filterDepartmentOrgTree(nodes: OrgDepartmentNode[], query: string): OrgDepartmentNode[] {
  const normalized = query.trim().toLowerCase();
  if (!normalized) return nodes;
  return nodes.flatMap((node) => {
    const children = filterDepartmentOrgTree(node.children, normalized);
    if (departmentSearchText(node.department).includes(normalized) || children.length) {
      return [{ ...node, children }];
    }
    return [];
  });
}

function countPersonDescendants(node: OrgPersonNode): number {
  return node.children.reduce((sum, child) => sum + 1 + countPersonDescendants(child), 0);
}

function countDepartmentDescendants(node: OrgDepartmentNode): number {
  return node.children.reduce((sum, child) => sum + 1 + countDepartmentDescendants(child), 0);
}

function findPersonNode(nodes: OrgPersonNode[], id: number): OrgPersonNode | null {
  for (const node of nodes) {
    if (node.employee.id === id) return node;
    const found = findPersonNode(node.children, id);
    if (found) return found;
  }
  return null;
}

// Path of employee ids from the top of the tree down to (and including) `id`.
function personPathIds(nodes: OrgPersonNode[], id: number, trail: number[] = []): number[] | null {
  for (const node of nodes) {
    const next = [...trail, node.employee.id];
    if (node.employee.id === id) return next;
    const found = personPathIds(node.children, id, next);
    if (found) return found;
  }
  return null;
}

function findDepartmentNode(nodes: OrgDepartmentNode[], id: number): OrgDepartmentNode | null {
  for (const node of nodes) {
    if (node.department.id === id) return node;
    const found = findDepartmentNode(node.children, id);
    if (found) return found;
  }
  return null;
}

function collectExpandablePersonIds(nodes: OrgPersonNode[], acc: number[] = []): number[] {
  for (const node of nodes) {
    if (node.children.length) {
      acc.push(node.employee.id);
      collectExpandablePersonIds(node.children, acc);
    }
  }
  return acc;
}

function collectExpandableDepartmentIds(nodes: OrgDepartmentNode[], acc: number[] = []): number[] {
  for (const node of nodes) {
    if (node.children.length) {
      acc.push(node.department.id);
      collectExpandableDepartmentIds(node.children, acc);
    }
  }
  return acc;
}

function rootPersonIds(nodes: OrgPersonNode[]): number[] {
  return nodes.map((node) => node.employee.id);
}

function rootDepartmentIds(nodes: OrgDepartmentNode[]): number[] {
  return nodes.map((node) => node.department.id);
}

function visiblePeopleOrgTree(nodes: OrgPersonNode[], expandedIds: Set<number>, forceExpanded: boolean): OrgPersonNode[] {
  return nodes.map((node) => {
    const isExpanded = forceExpanded || expandedIds.has(node.employee.id);
    return {
      ...node,
      directReportsCount: node.children.length,
      totalReportsCount: countPersonDescendants(node),
      isExpanded,
      children: isExpanded ? visiblePeopleOrgTree(node.children, expandedIds, forceExpanded) : [],
    };
  });
}

function visibleDepartmentOrgTree(nodes: OrgDepartmentNode[], expandedIds: Set<number>, forceExpanded: boolean): OrgDepartmentNode[] {
  return nodes.map((node) => {
    const isExpanded = forceExpanded || expandedIds.has(node.department.id);
    return {
      ...node,
      directReportsCount: node.children.length,
      totalReportsCount: countDepartmentDescendants(node),
      isExpanded,
      children: isExpanded ? visibleDepartmentOrgTree(node.children, expandedIds, forceExpanded) : [],
    };
  });
}

type OrgCardFields = {
  photo: boolean;
  position: boolean;
  department: boolean;
  location: boolean;
};

const DEFAULT_ORG_CARD_FIELDS: OrgCardFields = { photo: true, position: true, department: true, location: false };

type OrgHierarchyType = 'manager';

type OrgInitialFocus = {
  id: number;
  mode: 'subtree' | 'lineage';
};

type OrgGraphBlockMeta = Record<string, unknown> & (
  | {
      kind: 'person';
      employee: EmployeeListItem;
      index: number;
      directReportsCount: number;
      totalReportsCount: number;
      isExpanded: boolean;
    }
  | {
      kind: 'department';
      department: DepartmentOption;
      directReportsCount: number;
      totalReportsCount: number;
      isExpanded: boolean;
      color: string;
    }
);
type OrgGraphBlock = Omit<TBlock<OrgGraphBlockMeta>, 'meta'> & { meta: OrgGraphBlockMeta };
type OrgGraphConnection = TConnection & { points?: TPoint[] };
type OrgGraphEntities = {
  blocks: OrgGraphBlock[];
  connections: OrgGraphConnection[];
  rect: TRect;
};
type OrgGraphBranch = {
  rootId: string;
  width: number;
  height: number;
  blocks: OrgGraphBlock[];
  connections: OrgGraphConnection[];
};
type OrgGraphDimensions = {
  nodeWidth: number;
  nodeHeight: number;
  columnGap: number;
  rowGap: number;
  levelGap: number;
  maxColumns: number;
};

function orgGraphDimensions(compact: boolean): OrgGraphDimensions {
  return compact
    ? { nodeWidth: 188, nodeHeight: 72, columnGap: 14, rowGap: 28, levelGap: 58, maxColumns: 0 }
    : { nodeWidth: 218, nodeHeight: 86, columnGap: 22, rowGap: 34, levelGap: 70, maxColumns: 0 };
}

class OrgElbowConnection extends MultipointConnection {
  createPath(): Path2D {
    const points = this.getPoints();
    if (!points.length) return super.createPath();
    return polyline(points);
  }
}

function orgConnection(
  sourceBlockId: string,
  targetBlockId: string,
  sourcePoint: TPoint,
  targetPoint: TPoint,
): OrgGraphConnection {
  const elbowY = sourcePoint.y + (targetPoint.y - sourcePoint.y) / 2;
  return {
    id: `${sourceBlockId}->${targetBlockId}`,
    sourceBlockId,
    targetBlockId,
    points: [
      sourcePoint,
      { x: sourcePoint.x, y: elbowY },
      { x: targetPoint.x, y: elbowY },
      targetPoint,
    ],
  };
}

function shiftOrgGraphBranch(branch: OrgGraphBranch, dx: number, dy: number): OrgGraphBranch {
  return {
    ...branch,
    blocks: branch.blocks.map((block) => ({ ...block, x: block.x + dx, y: block.y + dy })),
    connections: branch.connections.map((connection) =>
      connection.points
        ? {
            ...connection,
            points: connection.points.map((point) => ({ x: point.x + dx, y: point.y + dy })),
          }
        : connection,
    ),
  };
}

type OrgRowsLayout = Pick<OrgGraphBranch, 'width' | 'height' | 'blocks' | 'connections'> & { parentX: number };

// Children whose own subtrees are empty (leaves or collapsed) are stacked as a
// vertical, indented column — the PeopleForce "list" look. Mixed groups stay
// horizontal so wide branches keep breathing room.
function composeOrgColumn(parentId: string, children: OrgGraphBranch[], dimensions: OrgGraphDimensions): OrgRowsLayout {
  const { nodeWidth, nodeHeight } = dimensions;
  const busX = nodeWidth / 2;
  const childX = nodeWidth / 2 + 18;
  const topGap = Math.round(dimensions.levelGap * 0.42);
  const rowGap = Math.max(10, Math.round(dimensions.rowGap * 0.42));
  const blocks: OrgGraphBlock[] = [];
  const connections: OrgGraphConnection[] = [];
  let y = nodeHeight + topGap;
  let maxRight = nodeWidth;

  children.forEach((branch) => {
    const shifted = shiftOrgGraphBranch(branch, childX, y);
    const targetBlock = shifted.blocks.find((block) => block.id === branch.rootId);
    blocks.push(...shifted.blocks);
    connections.push(...shifted.connections);
    const centerY = targetBlock ? targetBlock.y + targetBlock.height / 2 : y + nodeHeight / 2;
    connections.push({
      id: `${parentId}->${branch.rootId}`,
      sourceBlockId: parentId,
      targetBlockId: branch.rootId,
      points: [
        { x: busX, y: nodeHeight },
        { x: busX, y: centerY },
        { x: childX, y: centerY },
      ],
    });
    maxRight = Math.max(maxRight, childX + branch.width);
    y += branch.height + rowGap;
  });

  return {
    width: maxRight,
    height: y - rowGap,
    blocks,
    connections,
    parentX: 0,
  };
}

function composeOrgRows(parentId: string, children: OrgGraphBranch[], dimensions: OrgGraphDimensions): OrgRowsLayout {
  if (!children.length) {
    return { width: dimensions.nodeWidth, height: dimensions.nodeHeight, blocks: [], connections: [], parentX: 0 };
  }

  // Stack reports as a vertical column when the group is predominantly leaves
  // (a flat list of staff). The managerial "backbone" — where a meaningful share
  // of children have their own subtrees — stays horizontal, like PeopleForce.
  const isLeafBranch = (branch: OrgGraphBranch) =>
    branch.blocks.length === 1 && Number(branch.blocks[0]?.meta.directReportsCount || 0) === 0;
  const leafShare = children.filter(isLeafBranch).length / children.length;
  if (children.length >= 2 && leafShare >= 0.8) {
    return composeOrgColumn(parentId, children, dimensions);
  }

  const childrenWidth = children.reduce((sum, branch) => sum + branch.width, 0) + Math.max(0, children.length - 1) * dimensions.columnGap;
  const childrenHeight = Math.max(...children.map((branch) => branch.height));
  const graphWidth = Math.max(dimensions.nodeWidth, childrenWidth);
  const blocks: OrgGraphBlock[] = [];
  const connections: OrgGraphConnection[] = [];
  let x = (graphWidth - childrenWidth) / 2;
  const y = dimensions.nodeHeight + dimensions.levelGap;

  children.forEach((branch) => {
    const shifted = shiftOrgGraphBranch(branch, x, y);
    const targetBlock = shifted.blocks.find((block) => block.id === branch.rootId);
    blocks.push(...shifted.blocks);
    connections.push(...shifted.connections);
    if (targetBlock) {
      connections.push(
        orgConnection(
          parentId,
          branch.rootId,
          { x: graphWidth / 2, y: dimensions.nodeHeight },
          { x: targetBlock.x + targetBlock.width / 2, y: targetBlock.y },
        ),
      );
    }
    x += branch.width + dimensions.columnGap;
  });

  return {
    width: graphWidth,
    height: dimensions.nodeHeight + dimensions.levelGap + childrenHeight,
    blocks,
    connections,
    parentX: Math.max(0, (graphWidth - dimensions.nodeWidth) / 2),
  };
}

function buildPersonGraphBranch(node: OrgPersonNode, dimensions: OrgGraphDimensions, nextIndex: () => number): OrgGraphBranch {
  const id = `person-${node.employee.id}`;
  const childBranches = node.children.map((child) => buildPersonGraphBranch(child, dimensions, nextIndex));
  const childLayout = composeOrgRows(id, childBranches, dimensions);
  const reportsCount = node.children.length || Number(node.employee.direct_reports_count || 0);
  const directReportsCount = node.directReportsCount ?? reportsCount;
  const totalReportsCount = node.totalReportsCount ?? countPersonDescendants(node);
  const block: OrgGraphBlock = {
    id,
    is: 'org-person',
    x: childLayout.parentX,
    y: 0,
    width: dimensions.nodeWidth,
    height: dimensions.nodeHeight,
    name: node.employee.full_name,
    meta: { kind: 'person', employee: node.employee, index: nextIndex(), directReportsCount, totalReportsCount, isExpanded: Boolean(node.isExpanded) },
  };

  return {
    rootId: id,
    width: childLayout.width,
    height: childLayout.height,
    blocks: [block, ...childLayout.blocks],
    connections: childLayout.connections,
  };
}

function buildDepartmentGraphBranch(node: OrgDepartmentNode, dimensions: OrgGraphDimensions): OrgGraphBranch {
  const id = `department-${node.department.id}`;
  const childBranches = node.children.map((child) => buildDepartmentGraphBranch(child, dimensions));
  const childLayout = composeOrgRows(id, childBranches, dimensions);
  const color = node.department.level_color || '#8f83f6';
  const directReportsCount = node.directReportsCount ?? node.children.length;
  const totalReportsCount = node.totalReportsCount ?? countDepartmentDescendants(node);
  const block: OrgGraphBlock = {
    id,
    is: 'org-department',
    x: childLayout.parentX,
    y: 0,
    width: dimensions.nodeWidth,
    height: dimensions.nodeHeight,
    name: node.department.name,
    meta: { kind: 'department', department: node.department, directReportsCount, totalReportsCount, isExpanded: Boolean(node.isExpanded), color },
  };

  return {
    rootId: id,
    width: childLayout.width,
    height: childLayout.height,
    blocks: [block, ...childLayout.blocks],
    connections: childLayout.connections,
  };
}

function composeOrgRoots(branches: OrgGraphBranch[], dimensions: OrgGraphDimensions): OrgGraphEntities {
  if (!branches.length) {
    return { blocks: [], connections: [], rect: { x: 0, y: 0, width: 1, height: 1 } };
  }

  const graphWidth = branches.reduce((sum, branch) => sum + branch.width, 0) + Math.max(0, branches.length - 1) * dimensions.columnGap * 2;
  const graphHeight = Math.max(...branches.map((branch) => branch.height), dimensions.nodeHeight);
  const blocks: OrgGraphBlock[] = [];
  const connections: OrgGraphConnection[] = [];
  let x = 0;

  branches.forEach((branch) => {
    const shifted = shiftOrgGraphBranch(branch, x, 0);
    blocks.push(...shifted.blocks);
    connections.push(...shifted.connections);
    x += branch.width + dimensions.columnGap * 2;
  });

  return {
    blocks,
    connections,
    rect: {
      x: 0,
      y: 0,
      width: graphWidth,
      height: Math.max(1, graphHeight),
    },
  };
}

function buildPeopleOrgGraph(nodes: OrgPersonNode[], compact: boolean): OrgGraphEntities {
  const dimensions = orgGraphDimensions(compact);
  let index = 0;
  const nextIndex = () => index++;
  return composeOrgRoots(nodes.map((node) => buildPersonGraphBranch(node, dimensions, nextIndex)), dimensions);
}

function buildDepartmentOrgGraph(nodes: OrgDepartmentNode[], compact: boolean): OrgGraphEntities {
  const dimensions = orgGraphDimensions(compact);
  return composeOrgRoots(nodes.map((node) => buildDepartmentGraphBranch(node, dimensions)), dimensions);
}

function readableOrgRect(entities: OrgGraphEntities, compact: boolean): TRect {
  const width = Math.min(entities.rect.width, compact ? 980 : 1320);
  const height = Math.min(entities.rect.height, compact ? 720 : 820);
  return {
    x: 0,
    y: 0,
    width: Math.max(width, 1),
    height: Math.max(height, 1),
  };
}

function formatOrgExpandLabel(directReportsCount: number, totalReportsCount: number): string {
  if (!directReportsCount) return '';
  return totalReportsCount > directReportsCount ? `${directReportsCount} (${totalReportsCount})` : String(directReportsCount);
}

function orgGraphColors(isDark: boolean): { colors: TGraphColors; constants: Partial<TGraphConstants> } {
  return {
    colors: {
      // Opaque theme background — the gravity canvas context has no alpha, so a
      // transparent fill renders as solid black (breaks the light theme). Dots are
      // drawn across the whole canvas, i.e. to the container edges.
      canvas: isDark
        ? {
            belowLayerBackground: '#0b111d',
            layerBackground: '#0b111d',
            dots: 'rgba(119, 140, 174, 0.30)',
            border: 'rgba(11, 17, 29, 0)',
          }
        : {
            belowLayerBackground: '#eef3f9',
            layerBackground: '#eef3f9',
            dots: 'rgba(137, 158, 184, 0.40)',
            border: 'rgba(238, 243, 249, 0)',
          },
      block: isDark
        ? { background: '#121c2d', border: '#2d3b52', text: '#f4f8ff', selectedBorder: '#9a8cff' }
        : { background: '#ffffff', border: '#d8e3ef', text: '#062044', selectedBorder: '#8f83f6' },
      anchor: { background: 'rgba(0, 0, 0, 0)', selectedBorder: 'rgba(0, 0, 0, 0)' },
      connection: isDark
        ? { background: 'rgba(129, 151, 180, 0.34)', selectedBackground: '#9a8cff' }
        : { background: 'rgba(112, 137, 166, 0.36)', selectedBackground: '#7468e8' },
      selection: isDark
        ? { background: 'rgba(154, 140, 255, 0.14)', border: '#9a8cff' }
        : { background: 'rgba(143, 131, 246, 0.12)', border: '#8f83f6' },
    },
    constants: {
      camera: {
        MOUSE_WHEEL_BEHAVIOR: 'zoom',
        SPEED: 0.08,
        STEP: 0.12,
        PINCH_ZOOM_SPEED: 1,
        PAN_SPEED: 1,
        AUTO_PAN_THRESHOLD: 50,
        AUTO_PAN_SPEED: 10,
      },
    },
  };
}

function useEffectiveDarkMode(themeMode: ThemePreference): boolean {
  const [isDark, setIsDark] = useState(false);

  useEffect(() => {
    const media = window.matchMedia?.('(prefers-color-scheme: dark)');
    const update = () => setIsDark(themeMode === 'dark' || (themeMode === 'auto' && Boolean(media?.matches)));
    update();
    media?.addEventListener?.('change', update);
    return () => media?.removeEventListener?.('change', update);
  }, [themeMode]);

  return isDark;
}

function OrgView({
  embedded = false,
  onBack,
  copy,
  themeMode,
  initialFocus = null,
  onFocusApplied,
}: {
  embedded?: boolean;
  onBack?: () => void;
  copy: AppCopy;
  themeMode: ThemePreference;
  initialFocus?: OrgInitialFocus | null;
  onFocusApplied?: () => void;
}) {
  const navigate = useNavigate();
  const [mode, setMode] = useState<'people' | 'departments'>('people');
  const [employees, setEmployees] = useState<EmployeeListItem[]>([]);
  const [departments, setDepartments] = useState<DepartmentOption[]>([]);
  const [search, setSearch] = useState('');
  const [compactView, setCompactView] = useState(false);
  const [cardFields, setCardFields] = useState<OrgCardFields>(DEFAULT_ORG_CARD_FIELDS);
  const [focusPersonId, setFocusPersonId] = useState<number | null>(null);
  const [focusDepartmentId, setFocusDepartmentId] = useState<number | null>(null);
  const [personPickerOpen, setPersonPickerOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [pickerQuery, setPickerQuery] = useState('');
  const [expandedPersonIds, setExpandedPersonIds] = useState<Set<number>>(new Set());
  const [expandedDepartmentIds, setExpandedDepartmentIds] = useState<Set<number>>(new Set());
  const [loadState, setLoadState] = useState<LoadState>('idle');
  const [error, setError] = useState('');
  const actionsRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadOrg() {
      setLoadState('loading');
      setError('');
      try {
        const [employeeResult, departmentResult] = await Promise.all([
          api.employees({ status: 'active', page_size: 500 }),
          api.departments({ is_active: true, page_size: 500 }),
        ]);
        if (cancelled) return;
        setEmployees(employeeResult.items);
        setDepartments(departmentResult.items);
        setLoadState('ok');
      } catch (loadError) {
        if (cancelled) return;
        setEmployees([]);
        setDepartments([]);
        setError(loadError instanceof ApiError ? loadError.message : copy.settings.loadErrorText);
        setLoadState('error');
      }
    }

    void loadOrg();
    return () => {
      cancelled = true;
    };
  }, [copy.settings.loadErrorText]);

  const peopleTree = useMemo(() => buildPeopleOrgTree(employees), [employees]);
  const departmentTree = useMemo(() => buildDepartmentOrgTree(departments), [departments]);
  const visiblePeopleTree = useMemo(() => filterPeopleOrgTree(peopleTree, search), [peopleTree, search]);
  const visibleDepartmentTree = useMemo(() => filterDepartmentOrgTree(departmentTree, search), [departmentTree, search]);
  const searchActive = search.trim().length > 0;
  const peopleRootKey = useMemo(() => rootPersonIds(peopleTree).join(','), [peopleTree]);
  const departmentRootKey = useMemo(() => rootDepartmentIds(departmentTree).join(','), [departmentTree]);
  const focusedPeopleTree = useMemo(() => {
    if (focusPersonId == null) return visiblePeopleTree;
    const node = findPersonNode(peopleTree, focusPersonId);
    return node ? [node] : visiblePeopleTree;
  }, [focusPersonId, peopleTree, visiblePeopleTree]);
  const focusedDepartmentTree = useMemo(() => {
    if (focusDepartmentId == null) return visibleDepartmentTree;
    const node = findDepartmentNode(departmentTree, focusDepartmentId);
    return node ? [node] : visibleDepartmentTree;
  }, [departmentTree, focusDepartmentId, visibleDepartmentTree]);
  const graphPeopleTree = useMemo(
    () => visiblePeopleOrgTree(focusedPeopleTree, expandedPersonIds, searchActive),
    [expandedPersonIds, focusedPeopleTree, searchActive],
  );
  const graphDepartmentTree = useMemo(
    () => visibleDepartmentOrgTree(focusedDepartmentTree, expandedDepartmentIds, searchActive),
    [expandedDepartmentIds, focusedDepartmentTree, searchActive],
  );

  useEffect(() => {
    if (initialFocus) return;
    setExpandedPersonIds(new Set(rootPersonIds(peopleTree)));
  }, [peopleRootKey]);

  useEffect(() => {
    setExpandedDepartmentIds(new Set(rootDepartmentIds(departmentTree)));
  }, [departmentRootKey]);

  useEffect(() => {
    if (!initialFocus || !peopleTree.length) return;
    const path = personPathIds(peopleTree, initialFocus.id);
    if (!path) {
      onFocusApplied?.();
      return;
    }
    setMode('people');
    setSearch('');
    if (initialFocus.mode === 'subtree') {
      setFocusDepartmentId(null);
      setFocusPersonId(initialFocus.id);
      const node = findPersonNode(peopleTree, initialFocus.id);
      setExpandedPersonIds(new Set([initialFocus.id, ...(node ? collectExpandablePersonIds([node]) : [])]));
    } else {
      setFocusPersonId(null);
      setFocusDepartmentId(null);
      setExpandedPersonIds(new Set(path));
    }
    onFocusApplied?.();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialFocus, peopleRootKey]);

  function exportOrgPdf() {
    const escapeHtml = (value: string) =>
      String(value || '').replace(/[&<>"]/g, (ch) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[ch] || ch));
    const initials = (name: string) =>
      name
        .split(/\s+/)
        .filter(Boolean)
        .slice(0, 2)
        .map((part) => part[0]?.toUpperCase() || '')
        .join('');

    const entities =
      mode === 'people' ? buildPeopleOrgGraph(graphPeopleTree, compactView) : buildDepartmentOrgGraph(graphDepartmentTree, compactView);
    if (!entities.blocks.length) return;

    const lines = entities.connections
      .map((connection) => {
        const points = connection.points;
        if (!points || points.length < 2) return '';
        return `<polyline points="${points.map((point) => `${point.x},${point.y}`).join(' ')}" />`;
      })
      .join('');

    const cards = entities.blocks
      .map((block) => {
        const expandLabel = formatOrgExpandLabel(block.meta.directReportsCount, block.meta.totalReportsCount);
        const badge = expandLabel ? `<span class="badge">${escapeHtml(expandLabel)}</span>` : '';
        const style = `left:${block.x}px;top:${block.y}px;width:${block.width}px;height:${block.height}px`;
        if (block.meta.kind === 'person') {
          const person = employeeToPerson(block.meta.employee, block.meta.index, copy);
          const avatar = person.avatarUrl
            ? `<span class="ava"><img src="${escapeHtml(person.avatarUrl)}" onerror="this.remove()" />${escapeHtml(initials(person.fullName))}</span>`
            : `<span class="ava">${escapeHtml(initials(person.fullName))}</span>`;
          const photo = cardFields.photo ? avatar : '';
          const role = cardFields.position ? `<span class="role">${escapeHtml(person.role)}</span>` : '';
          const dept = cardFields.department ? `<span class="muted">${escapeHtml(person.department)}</span>` : '';
          const loc = cardFields.location ? `<span class="muted">${escapeHtml(person.location)}</span>` : '';
          return `<div class="card" style="${style}">${photo}<div class="body"><strong>${escapeHtml(person.fullName)}</strong>${role}${dept}${loc}</div>${badge}</div>`;
        }
        const department = block.meta.department;
        const icon = cardFields.photo ? '<span class="ava dept">▦</span>' : '';
        const level = cardFields.position ? `<span class="role">${escapeHtml(department.level_name || department.clinic_name || 'Підрозділ')}</span>` : '';
        const manager = cardFields.department ? `<span class="muted">${escapeHtml(department.manager_name || 'Без менеджера')}</span>` : '';
        return `<div class="card" style="${style}">${icon}<div class="body"><strong>${escapeHtml(department.name)}</strong>${level}${manager}</div>${badge}</div>`;
      })
      .join('');

    const width = Math.ceil(entities.rect.width);
    const height = Math.ceil(entities.rect.height);
    // Scale the whole chart so it always fits a single landscape A4 page
    // (printable area ≈ 1040×720px at 96dpi with small margins). Never upscale.
    const PAGE_W = 1040;
    const PAGE_H = 720;
    const fit = Math.min(PAGE_W / width, PAGE_H / height, 1);
    const wrapW = Math.ceil(width * fit);
    const wrapH = Math.ceil(height * fit);
    const title = mode === 'people' ? 'Оргструктура — Люди' : 'Оргструктура — Департаменти';
    const win = window.open('', '_blank');
    if (!win) return;
    win.document.write(
      `<!doctype html><html lang="uk"><head><meta charset="utf-8"><title>${title}</title><style>` +
        `@page{size:A4 landscape;margin:6mm}` +
        `*{box-sizing:border-box}` +
        `html,body{margin:0;padding:0;background:#fff;font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;color:#0b1f3a}` +
        `.wrap{width:${wrapW}px;height:${wrapH}px;margin:0 auto;overflow:hidden;page-break-inside:avoid;break-inside:avoid}` +
        `.stage{position:relative;width:${width}px;height:${height}px;transform:scale(${fit});transform-origin:top left}` +
        `svg{position:absolute;inset:0;width:100%;height:100%;overflow:visible}` +
        `polyline{fill:none;stroke:#c2d2e4;stroke-width:1.5}` +
        `.card{position:absolute;display:flex;align-items:center;gap:8px;border:1px solid #d8e3ef;border-radius:8px;background:#fff;padding:8px 9px;box-shadow:0 6px 16px rgba(20,40,70,.08)}` +
        `.ava{flex:0 0 auto;position:relative;display:grid;place-items:center;width:32px;height:32px;border-radius:50%;overflow:hidden;background:#e8eef6;color:#3b6fb0;font-size:10px;font-weight:700}` +
        `.ava img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}` +
        `.ava.dept{border-radius:8px;background:#eef0ff;color:#6a5cf0}` +
        `.body{min-width:0;display:flex;flex-direction:column;gap:1px;overflow:hidden}` +
        `.body strong{font-size:11px;line-height:1.16;color:#0b2240;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}` +
        `.body .role{font-size:10px;color:#3f5f86;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}` +
        `.body .muted{font-size:10px;color:#7286a0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}` +
        `.badge{position:absolute;left:50%;bottom:-9px;transform:translateX(-50%);background:#f59e0b;color:#3a2400;font-size:9px;font-weight:700;padding:2px 7px;border-radius:10px;white-space:nowrap}` +
        `@page{size:landscape;margin:8mm}` +
        `</style></head><body><div class="wrap"><div class="stage"><svg viewBox="0 0 ${width} ${height}">${lines}</svg>${cards}</div></div>` +
        `<script>window.onload=function(){window.focus();setTimeout(function(){window.print();},350);};</script></body></html>`,
    );
    win.document.close();
  }

  function toggleCardField(field: keyof OrgCardFields) {
    setCardFields((current) => ({ ...current, [field]: !current[field] }));
  }

  function resetOrgFocus() {
    setFocusPersonId(null);
    setFocusDepartmentId(null);
    setPickerQuery('');
    setPersonPickerOpen(false);
  }

  function selectFocusPerson(employeeId: number) {
    setFocusPersonId(employeeId);
    setExpandedPersonIds((current) => new Set(current).add(employeeId));
    setPickerQuery('');
    setPersonPickerOpen(false);
  }

  function selectFocusDepartment(departmentId: number) {
    setFocusDepartmentId(departmentId);
    setExpandedDepartmentIds((current) => new Set(current).add(departmentId));
    setPickerQuery('');
    setPersonPickerOpen(false);
  }

  const pickerOptions = useMemo(() => {
    const query = pickerQuery.trim().toLowerCase();
    if (mode === 'people') {
      return employees
        .filter((employee) => {
          if (!query) return true;
          return `${employee.full_name} ${employee.position_name} ${employee.department_name}`.toLowerCase().includes(query);
        })
        .sort((a, b) => a.full_name.localeCompare(b.full_name, 'uk'))
        .slice(0, 60);
    }
    return [] as EmployeeListItem[];
  }, [employees, mode, pickerQuery]);

  const departmentPickerOptions = useMemo(() => {
    if (mode !== 'departments') return [] as DepartmentOption[];
    const query = pickerQuery.trim().toLowerCase();
    return departments
      .filter((department) => (!query ? true : `${department.name} ${department.manager_name}`.toLowerCase().includes(query)))
      .sort((a, b) => a.name.localeCompare(b.name, 'uk'))
      .slice(0, 60);
  }, [departments, mode, pickerQuery]);

  function pickerButtonLabel(): string {
    if (mode === 'people') {
      if (focusPersonId != null) {
        const node = findPersonNode(peopleTree, focusPersonId);
        if (node) return node.employee.full_name;
      }
      return copy.org.person;
    }
    if (focusDepartmentId != null) {
      const node = findDepartmentNode(departmentTree, focusDepartmentId);
      if (node) return node.department.name;
    }
    return copy.org.departments;
  }

  useEffect(() => {
    if (!personPickerOpen && !settingsOpen) return undefined;
    function handlePointerDown(event: PointerEvent) {
      if (actionsRef.current && !actionsRef.current.contains(event.target as Node)) {
        setPersonPickerOpen(false);
        setSettingsOpen(false);
      }
    }
    document.addEventListener('pointerdown', handlePointerDown);
    return () => document.removeEventListener('pointerdown', handlePointerDown);
  }, [personPickerOpen, settingsOpen]);

  useEffect(() => {
    // Focus is scoped to one mode at a time; switching tabs clears it.
    resetOrgFocus();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode]);

  function newHire() {
    navigate('/people/new');
  }

  function orgModeLabel() {
    return mode === 'people' ? copy.org.person : copy.org.departments;
  }

  function viewSettingsLabel() {
    return compactView ? 'Звичайний вигляд' : copy.common.viewSettings;
  }

  function shouldShowSearch(): boolean {
    return search.trim().length > 0;
  }

  function clearSearch() {
    if (search) {
      setSearch('');
    }
  }

  function changeTab(key: string) {
    if (key === 'people') {
      if (onBack) {
        onBack();
      } else {
        navigate('/people');
      }
      return;
    }
    if (key === 'teams') {
      navigate('/people/teams');
    }
  }

  function openEmployee(employee: EmployeeListItem) {
    navigate(peopleEmployeePath(employee.id));
  }

  function expandAllNodes() {
    if (mode === 'people') {
      const base = focusPersonId != null ? focusedPeopleTree : peopleTree;
      setExpandedPersonIds(new Set(collectExpandablePersonIds(base)));
    } else {
      const base = focusDepartmentId != null ? focusedDepartmentTree : departmentTree;
      setExpandedDepartmentIds(new Set(collectExpandableDepartmentIds(base)));
    }
  }

  function togglePersonNode(employeeId: number) {
    setExpandedPersonIds((current) => {
      const next = new Set(current);
      if (next.has(employeeId)) {
        next.delete(employeeId);
      } else {
        next.add(employeeId);
      }
      return next;
    });
  }

  function toggleDepartmentNode(departmentId: number) {
    setExpandedDepartmentIds((current) => {
      const next = new Set(current);
      if (next.has(departmentId)) {
        next.delete(departmentId);
      } else {
        next.add(departmentId);
      }
      return next;
    });
  }

  const graphState =
    loadState === 'loading' ? (
      <div className="org-empty-panel">
        <EmptyState title={copy.common.loading} />
      </div>
    ) : loadState === 'error' ? (
      <div className="org-empty-panel">
        <EmptyState title={copy.people.employeesLoadError} text={error || copy.common.backendRetry} />
      </div>
    ) : mode === 'people' ? (
      visiblePeopleTree.length ? (
        <div className="org-people-tree">
          {visiblePeopleTree.map((node, index) => (
            <OrgPersonBranch
              key={node.employee.id}
              node={node}
              index={index}
              copy={copy}
              onOpenEmployee={openEmployee}
            />
          ))}
        </div>
      ) : (
        <div className="org-empty-panel">
          <EmptyState title={copy.people.employeesNotFound} text={copy.settings.noResultsText} />
        </div>
      )
    ) : visibleDepartmentTree.length ? (
      <div className="org-department-tree">
        {visibleDepartmentTree.map((node) => (
          <OrgDepartmentBranch key={node.department.id} node={node} />
        ))}
      </div>
    ) : (
      <div className="org-empty-panel">
        <EmptyState title={copy.settings.noResultsTitle} text={copy.settings.noResultsText} />
      </div>
    );

  return (
    <main className={embedded ? 'workspace org-page embedded' : 'workspace org-page'}>
      <header className="page-header">
        <div>
          <h1>{copy.people.title}</h1>
          <SectionTabs
            tabs={[
              { key: 'people', label: copy.people.peopleTab },
              { key: 'teams', label: copy.people.teamsTab },
              { key: 'org', label: copy.people.orgTab },
            ]}
            active="org"
            onChange={changeTab}
          />
        </div>
        <button type="button" className="primary-action" onClick={newHire}>
          <Plus size={18} />
          {copy.people.newHire}
        </button>
      </header>

      <div className="org-toolbar">
        <div className="segmented flat">
          <button type="button" className={mode === 'people' ? 'active' : ''} onClick={() => setMode('people')}>
            {copy.org.people}
          </button>
          <button type="button" className={mode === 'departments' ? 'active' : ''} onClick={() => setMode('departments')}>
            {copy.org.departments}
          </button>
        </div>
        <div className="org-actions" ref={actionsRef}>
          {focusPersonId != null || focusDepartmentId != null ? (
            <button type="button" className="toolbar-button" onClick={resetOrgFocus}>
              <X size={16} />
              Уся структура
            </button>
          ) : null}

          <div className="org-dropdown">
            <button
              type="button"
              className={`toolbar-button${personPickerOpen ? ' active' : ''}`}
              onClick={() => {
                setSettingsOpen(false);
                setPersonPickerOpen((open) => !open);
              }}
            >
              <span className="org-dropdown-value">{pickerButtonLabel()}</span>
              <ChevronDown size={15} />
            </button>
            {personPickerOpen ? (
              <div className="org-dropdown-panel org-picker-panel">
                <div className="org-picker-search">
                  <Search size={15} />
                  <input
                    type="text"
                    value={pickerQuery}
                    onChange={(event) => setPickerQuery(event.target.value)}
                    placeholder="Пошук…"
                    autoFocus
                  />
                </div>
                <div className="org-picker-list">
                  <button type="button" className="org-picker-item reset" onClick={resetOrgFocus}>
                    Показати всю структуру
                  </button>
                  {mode === 'people'
                    ? pickerOptions.map((employee, index) => {
                        const person = employeeToPerson(employee, index, copy);
                        return (
                          <button
                            type="button"
                            key={employee.id}
                            className={`org-picker-item${focusPersonId === employee.id ? ' selected' : ''}`}
                            onClick={() => selectFocusPerson(employee.id)}
                          >
                            <Avatar name={person.fullName} src={person.avatarUrl} accent={person.accent} />
                            <span>
                              <strong>{person.fullName}</strong>
                              <small>{person.role}</small>
                            </span>
                          </button>
                        );
                      })
                    : departmentPickerOptions.map((department) => (
                        <button
                          type="button"
                          key={department.id}
                          className={`org-picker-item${focusDepartmentId === department.id ? ' selected' : ''}`}
                          onClick={() => selectFocusDepartment(department.id)}
                        >
                          <span className="org-department-icon small">
                            <Building2 size={15} />
                          </span>
                          <span>
                            <strong>{department.name}</strong>
                            <small>{department.manager_name || 'Без менеджера'}</small>
                          </span>
                        </button>
                      ))}
                  {(mode === 'people' ? pickerOptions.length : departmentPickerOptions.length) === 0 ? (
                    <div className="org-picker-empty">Нічого не знайдено</div>
                  ) : null}
                </div>
              </div>
            ) : null}
          </div>

          <div className="org-dropdown">
            <button
              type="button"
              className={`toolbar-button${settingsOpen ? ' active' : ''}`}
              onClick={() => {
                setPersonPickerOpen(false);
                setSettingsOpen((open) => !open);
              }}
            >
              <Settings size={18} />
              {copy.common.viewSettings}
              <ChevronDown size={15} />
            </button>
            {settingsOpen ? (
              <div className="org-dropdown-panel org-settings-panel">
                <div className="org-settings-group">
                  <h4>Поля картки</h4>
                  <p>Налаштуйте, які дані показувати на картках.</p>
                  <label className="org-settings-toggle">
                    <span>Фото</span>
                    <input type="checkbox" checked={cardFields.photo} onChange={() => toggleCardField('photo')} />
                  </label>
                  <div className="org-settings-readonly">Повне ім'я</div>
                  <label className="org-settings-toggle">
                    <span>Посада</span>
                    <input type="checkbox" checked={cardFields.position} onChange={() => toggleCardField('position')} />
                  </label>
                  <label className="org-settings-toggle">
                    <span>Департамент</span>
                    <input type="checkbox" checked={cardFields.department} onChange={() => toggleCardField('department')} />
                  </label>
                  <label className="org-settings-toggle">
                    <span>Локація</span>
                    <input type="checkbox" checked={cardFields.location} onChange={() => toggleCardField('location')} />
                  </label>
                </div>
                <div className="org-settings-group">
                  <h4>Вигляд</h4>
                  <label className="org-settings-toggle">
                    <span>Компактний вигляд</span>
                    <input type="checkbox" checked={compactView} onChange={() => setCompactView((value) => !value)} />
                  </label>
                </div>
                <div className="org-settings-group">
                  <h4>Ієрархія структури</h4>
                  <p>Тип зв'язку для побудови дерева.</p>
                  <select className="org-settings-select" value="manager" disabled>
                    <option value="manager">Менеджер</option>
                  </select>
                </div>
              </div>
            ) : null}
          </div>

          <button type="button" className="toolbar-button" onClick={exportOrgPdf}>
            {copy.common.export}
            <ChevronDown size={15} />
          </button>
        </div>
      </div>

      {loadState === 'ok' && ((mode === 'people' && graphPeopleTree.length) || (mode === 'departments' && graphDepartmentTree.length)) ? (
        <OrgGraphCanvasView
          mode={mode}
          peopleTree={graphPeopleTree}
          departmentTree={graphDepartmentTree}
          compactView={compactView}
          cardFields={cardFields}
          themeMode={themeMode}
          copy={copy}
          onOpenEmployee={openEmployee}
          onTogglePerson={togglePersonNode}
          onToggleDepartment={toggleDepartmentNode}
          onExpandAll={expandAllNodes}
        />
      ) : (
        <section className={`org-canvas ${mode === 'departments' ? 'departments' : 'people'} ${compactView ? 'compact' : ''}`}>
          {graphState}
        </section>
      )}
    </main>
  );
}

function OrgGraphCanvasView({
  mode,
  peopleTree,
  departmentTree,
  compactView,
  cardFields,
  themeMode,
  copy,
  onOpenEmployee,
  onTogglePerson,
  onToggleDepartment,
  onExpandAll,
}: {
  mode: 'people' | 'departments';
  peopleTree: OrgPersonNode[];
  departmentTree: OrgDepartmentNode[];
  compactView: boolean;
  cardFields: OrgCardFields;
  themeMode: ThemePreference;
  copy: AppCopy;
  onOpenEmployee: (employee: EmployeeListItem) => void;
  onTogglePerson: (employeeId: number) => void;
  onToggleDepartment: (departmentId: number) => void;
  onExpandAll: () => void;
}) {
  const canvasRef = useRef<HTMLElement | null>(null);
  const pendingFocusRef = useRef<string | null>(null);
  const [canvasFullscreen, setCanvasFullscreen] = useState(false);
  const isDark = useEffectiveDarkMode(themeMode);
  const graphTheme = useMemo(() => orgGraphColors(isDark), [isDark]);
  const { graph, setEntities, setViewConfiguration, start } = useGraph({
    name: 'hr-org-structure',
    settings: {
      canDragCamera: true,
      canZoomCamera: true,
      canDrag: ECanDrag.NONE,
      canCreateNewConnections: false,
      useBlocksAnchors: false,
      useBezierConnections: false,
      bezierConnectionDirection: 'vertical',
      showConnectionArrows: false,
      showConnectionLabels: false,
      connectivityComponentOnClickRaise: false,
      connection: OrgElbowConnection,
      emulateMouseEventsOnCameraChange: true,
    },
    viewConfiguration: graphTheme,
  });
  const entities = useMemo(
    () => (mode === 'people' ? buildPeopleOrgGraph(peopleTree, compactView) : buildDepartmentOrgGraph(departmentTree, compactView)),
    [compactView, departmentTree, mode, peopleTree],
  );

  useEffect(() => {
    setViewConfiguration(graphTheme);
  }, [graphTheme, setViewConfiguration]);

  useEffect(() => {
    setEntities({ blocks: entities.blocks, connections: entities.connections });
    const focusId = pendingFocusRef.current;
    pendingFocusRef.current = null;
    const frame = window.requestAnimationFrame(() => {
      // After an expand/collapse keep the toggled node centred instead of
      // refitting the whole graph (which made the view jump around).
      if (focusId && entities.blocks.some((block) => block.id === focusId)) {
        centerOnBlock(focusId);
      } else {
        fitOrgRect(entities.rect);
      }
    });
    return () => window.cancelAnimationFrame(frame);
  }, [compactView, entities, graph, setEntities]);

  useEffect(() => {
    if (!canvasFullscreen) return undefined;

    function handleNativeFullscreenChange() {
      if (document.fullscreenElement !== canvasRef.current) {
        setCanvasFullscreen(false);
      }
    }

    document.addEventListener('fullscreenchange', handleNativeFullscreenChange);
    return () => document.removeEventListener('fullscreenchange', handleNativeFullscreenChange);
  }, [canvasFullscreen]);

  useEffect(() => {
    // Refit after entering/leaving fullscreen, once the canvas has resized.
    const timer = window.setTimeout(() => {
      window.requestAnimationFrame(() => fitOrgRect(entities.rect));
    }, 80);
    return () => window.clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [canvasFullscreen]);

  function fitOrgRect(rect: TRect, padding = 48) {
    const canvas = canvasRef.current;
    // Fall back to a rect-derived viewport when the canvas has not been measured
    // yet (initial mount / fullscreen transition) so we never divide by zero and
    // push the whole chart off-screen.
    const viewWidth = canvas && canvas.clientWidth > 0 ? canvas.clientWidth : rect.width + padding * 2;
    const viewHeight = canvas && canvas.clientHeight > 0 ? canvas.clientHeight : rect.height + padding * 2;
    const camera = graph.cameraService.getCameraState();
    const rawScale = Math.min((viewWidth - padding * 2) / rect.width, (viewHeight - padding * 2) / rect.height);
    const scale = Math.max(camera.scaleMin, Math.min(camera.scaleMax, Math.min(rawScale, 1.1)));
    // Centre the whole content rect in the viewport so everything stays visible.
    graph.cameraService.set({
      x: (viewWidth - rect.width * scale) / 2 - rect.x * scale,
      y: (viewHeight - rect.height * scale) / 2 - rect.y * scale,
      scale,
    });
  }

  function centerOnBlock(blockId: string) {
    const block = entities.blocks.find((item) => item.id === blockId);
    const canvas = canvasRef.current;
    if (!block || !canvas || canvas.clientWidth === 0) {
      fitOrgRect(entities.rect);
      return;
    }
    const scale = graph.cameraService.getCameraState().scale;
    const centerX = block.x + block.width / 2;
    const centerY = block.y + block.height / 2;
    graph.cameraService.set({
      x: canvas.clientWidth / 2 - centerX * scale,
      y: canvas.clientHeight / 2 - centerY * scale,
      scale,
    });
  }

  function zoomToGraph(padding = 42) {
    fitOrgRect(entities.rect, padding);
  }

  function focusReadableGraph() {
    fitOrgRect(entities.rect);
  }

  function zoomGraph(direction: 1 | -1) {
    const camera = graph.cameraService.getCameraState();
    const factor = direction > 0 ? 1.16 : 0.86;
    const scale = Math.max(camera.scaleMin, Math.min(camera.scaleMax, camera.scale * factor));
    graph.zoom({ scale });
  }

  async function toggleFullscreen() {
    const canvas = canvasRef.current;
    if (!canvas) return;
    if (canvasFullscreen) {
      setCanvasFullscreen(false);
      if (document.fullscreenElement === canvas) {
        await document.exitFullscreen().catch(() => undefined);
      }
      return;
    }
    setCanvasFullscreen(true);
    await canvas.requestFullscreen?.().catch(() => undefined);
    window.requestAnimationFrame(() => focusReadableGraph());
  }

  function handleTogglePerson(employeeId: number) {
    pendingFocusRef.current = `person-${employeeId}`;
    onTogglePerson(employeeId);
  }

  function handleToggleDepartment(departmentId: number) {
    pendingFocusRef.current = `department-${departmentId}`;
    onToggleDepartment(departmentId);
  }

  function renderBlock(graphInstance: Graph, block: TBlock) {
    const orgBlock = block as OrgGraphBlock;
    return (
      <GraphBlock graph={graphInstance} block={orgBlock} className="org-graph-block-wrapper" containerClassName="org-graph-block-container">
        <OrgGraphBlockCard
          block={orgBlock}
          copy={copy}
          cardFields={cardFields}
          onOpenEmployee={onOpenEmployee}
          onTogglePerson={handleTogglePerson}
          onToggleDepartment={handleToggleDepartment}
        />
      </GraphBlock>
    );
  }

  return (
    <section
      ref={canvasRef}
      className={`org-canvas org-graph-canvas ${mode === 'departments' ? 'departments' : 'people'} ${compactView ? 'compact' : ''} ${canvasFullscreen ? 'fullscreen' : ''}`}
    >
      <GraphCanvas
        graph={graph}
        className="org-gravity-graph"
        blockListClassName="org-gravity-block-list"
        renderBlock={renderBlock}
        onStateChanged={({ state }) => {
          if (state === GraphState.ATTACHED) {
            start();
          }
          if (state === GraphState.READY) {
            window.requestAnimationFrame(() => focusReadableGraph());
          }
        }}
      />
      <div className="canvas-controls">
        <button type="button" aria-label="Expand all" data-tooltip="Розгорнути все" onClick={onExpandAll}>
          <Maximize2 size={19} />
        </button>
        <button type="button" aria-label="Fit" data-tooltip="Заповнити" onClick={focusReadableGraph}>
          <Grid3X3 size={19} />
        </button>
        <button type="button" aria-label="Zoom in" data-tooltip="Збільшити" onClick={() => zoomGraph(1)}>
          <ZoomIn size={19} />
        </button>
        <button type="button" aria-label="Zoom out" data-tooltip="Зменшити" onClick={() => zoomGraph(-1)}>
          <ZoomOut size={19} />
        </button>
        <button
          type="button"
          className={canvasFullscreen ? 'active' : ''}
          aria-label="Display"
          data-tooltip="Повний екран"
          onClick={() => void toggleFullscreen()}
        >
          <Laptop size={19} />
        </button>
      </div>
    </section>
  );
}

function OrgGraphBlockCard({
  block,
  copy,
  cardFields,
  onOpenEmployee,
  onTogglePerson,
  onToggleDepartment,
}: {
  block: OrgGraphBlock;
  copy: AppCopy;
  cardFields: OrgCardFields;
  onOpenEmployee: (employee: EmployeeListItem) => void;
  onTogglePerson: (employeeId: number) => void;
  onToggleDepartment: (departmentId: number) => void;
}) {
  if (block.meta.kind === 'person') {
    const employee = block.meta.employee;
    const person = employeeToPerson(employee, block.meta.index, copy);
    const expandLabel = formatOrgExpandLabel(block.meta.directReportsCount, block.meta.totalReportsCount);
    return (
      <article className={`org-card org-graph-card org-person-card${cardFields.photo ? '' : ' no-photo'}`}>
        <button type="button" className="org-graph-card-body" onClick={() => onOpenEmployee(employee)}>
          {cardFields.photo ? <Avatar name={person.fullName} src={person.avatarUrl} accent={person.accent} /> : null}
          <div>
            <strong>{person.fullName}</strong>
            {cardFields.position ? <span>{person.role}</span> : null}
            {cardFields.department ? <small>{person.department}</small> : null}
            {cardFields.location ? <small className="org-card-location">{person.location}</small> : null}
          </div>
        </button>
        {expandLabel ? (
          <button
            type="button"
            className={`org-expand-button ${block.meta.isExpanded ? 'expanded' : ''}`}
            aria-label={`${block.meta.isExpanded ? 'Згорнути' : 'Розгорнути'} ${person.fullName}`}
            aria-expanded={block.meta.isExpanded}
            onClick={() => onTogglePerson(employee.id)}
          >
            {expandLabel}
          </button>
        ) : null}
      </article>
    );
  }

  const department = block.meta.department;
  const color = block.meta.color;
  const expandLabel = formatOrgExpandLabel(block.meta.directReportsCount, block.meta.totalReportsCount);
  return (
    <article className={`org-card org-graph-card org-department-card${cardFields.photo ? '' : ' no-photo'}`} style={{ '--department-color': color } as CSSProperties}>
      <div className="org-graph-card-body static">
        {cardFields.photo ? (
          <div className="org-department-icon">
            <Building2 size={18} />
          </div>
        ) : null}
        <div>
          <strong>{department.name}</strong>
          {cardFields.position ? <span>{department.level_name || department.clinic_name || 'Підрозділ'}</span> : null}
          {cardFields.department ? <small>{department.manager_name || 'Без менеджера'}</small> : null}
        </div>
      </div>
      {expandLabel ? (
        <button
          type="button"
          className={`org-expand-button ${block.meta.isExpanded ? 'expanded' : ''}`}
          aria-label={`${block.meta.isExpanded ? 'Згорнути' : 'Розгорнути'} ${department.name}`}
          aria-expanded={block.meta.isExpanded}
          onClick={() => onToggleDepartment(department.id)}
        >
          {expandLabel}
        </button>
      ) : null}
    </article>
  );
}

function OrgPersonBranch({
  node,
  index,
  copy,
  onOpenEmployee,
}: {
  node: OrgPersonNode;
  index: number;
  copy: AppCopy;
  onOpenEmployee: (employee: EmployeeListItem) => void;
}) {
  const person = employeeToPerson(node.employee, index, copy);
  const reportsCount = node.children.length || Number(node.employee.direct_reports_count || 0);
  return (
    <div className={`org-person-branch ${node.children.length ? 'has-children' : ''}`}>
      <button type="button" className="org-card org-person-card" onClick={() => onOpenEmployee(node.employee)}>
        <Avatar name={person.fullName} src={person.avatarUrl} accent={person.accent} />
        <div>
          <strong>{person.fullName}</strong>
          <span>{person.role}</span>
          <small>{person.department}</small>
        </div>
        {reportsCount ? <em>{reportsCount}</em> : null}
      </button>
      {node.children.length ? (
        <div className="org-person-children">
          {node.children.map((child, childIndex) => (
            <OrgPersonBranch
              key={child.employee.id}
              node={child}
              index={index + childIndex + 1}
              copy={copy}
              onOpenEmployee={onOpenEmployee}
            />
          ))}
        </div>
      ) : null}
    </div>
  );
}

function OrgDepartmentBranch({ node }: { node: OrgDepartmentNode }) {
  const color = node.department.level_color || '#8f83f6';
  return (
    <div className={`org-department-branch ${node.children.length ? 'has-children' : ''}`}>
      <article className="org-card org-department-card" style={{ '--department-color': color } as CSSProperties}>
        <div className="org-department-icon">
          <Building2 size={18} />
        </div>
        <div>
          <strong>{node.department.name}</strong>
          <span>{node.department.level_name || node.department.clinic_name || 'Підрозділ'}</span>
          <small>{node.department.manager_name || 'Без менеджера'}</small>
        </div>
        <em>{node.department.employee_count}</em>
      </article>
      {node.children.length ? (
        <div className="org-department-children">
          {node.children.map((child) => (
            <OrgDepartmentBranch key={child.department.id} node={child} />
          ))}
        </div>
      ) : null}
    </div>
  );
}

type SettingsOptionKind =
  | 'experience-levels'
  | 'gender'
  | 'termination-reasons'
  | 'termination-types'
  | 'work-types'
  | 'probation-conditions'
  | 'positions'
  | 'divisions'
  | 'skills';
type SettingsOptionRow = {
  id: number;
  name: string;
  sort_order?: number;
  is_active: boolean;
  employee_count: number;
  duration_months?: number;
  external_peopleforce_id?: string;
  code?: string;
  is_system?: boolean;
};

type SettingsExportFormat = 'csv' | 'xlsx';
type LocationFormState = {
  name: string;
  country_code: string;
  address: string;
  holiday_policy_id: string;
  holiday_policy_name: string;
  time_zone: string;
  is_active: boolean;
};

type HolidayPolicyFormState = {
  name: string;
  country_code: string;
  is_active: boolean;
};

type HolidayFormState = {
  name: string;
  occurs_on: string;
  working: boolean;
  compensated_on: string;
  observed_on: string;
  recurrence: 'none' | 'yearly';
  is_active: boolean;
};

type WorkingPatternDayKey = 'monday' | 'tuesday' | 'wednesday' | 'thursday' | 'friday' | 'saturday' | 'sunday';
type WorkingPatternHourField =
  | 'monday_hours'
  | 'tuesday_hours'
  | 'wednesday_hours'
  | 'thursday_hours'
  | 'friday_hours'
  | 'saturday_hours'
  | 'sunday_hours';
type WorkingPatternDayForm = {
  key: WorkingPatternDayKey;
  label: string;
  time_range: string;
  break_hours: number;
  hours: number;
};
type WorkingPatternFormState = {
  name: string;
  uses_time_range: boolean;
  is_default: boolean;
  is_active: boolean;
  days: Record<WorkingPatternDayKey, WorkingPatternDayForm>;
};

const workingPatternDays: Array<{ key: WorkingPatternDayKey; label: string; field: WorkingPatternHourField }> = [
  { key: 'monday', label: 'Понеділок', field: 'monday_hours' },
  { key: 'tuesday', label: 'Вівторок', field: 'tuesday_hours' },
  { key: 'wednesday', label: 'Середа', field: 'wednesday_hours' },
  { key: 'thursday', label: 'Четвер', field: 'thursday_hours' },
  { key: 'friday', label: "П'ятниця", field: 'friday_hours' },
  { key: 'saturday', label: 'Субота', field: 'saturday_hours' },
  { key: 'sunday', label: 'Неділя', field: 'sunday_hours' },
];

const workingPatternHourOptions = Array.from({ length: 24 }, (_, index) => String(index).padStart(2, '0'));
const workingPatternMinuteOptions = Array.from({ length: 60 }, (_, index) => String(index).padStart(2, '0'));
const workingPatternHourStep = 1;

function numberFromApi(value: string | number | undefined | null): number {
  if (typeof value === 'number') return Number.isFinite(value) ? value : 0;
  const parsed = Number(String(value ?? '').replace(',', '.'));
  return Number.isFinite(parsed) ? parsed : 0;
}

function normalizeHours(value: number): number {
  if (!Number.isFinite(value) || value < 0) return 0;
  return Math.round(value * 100) / 100;
}

function parseTimeRangeHours(timeRange: string, breakHours: number): number | null {
  const match = timeRange.trim().match(/^(\d{1,2})[:.](\d{2})\s*-\s*(\d{1,2})[:.](\d{2})$/);
  if (!match) return null;
  const [, startHourText, startMinuteText, endHourText, endMinuteText] = match;
  const startHour = Number(startHourText);
  const startMinute = Number(startMinuteText);
  const endHour = Number(endHourText);
  const endMinute = Number(endMinuteText);
  if ([startHour, startMinute, endHour, endMinute].some((value) => !Number.isFinite(value))) return null;
  if (startHour > 23 || endHour > 23 || startMinute > 59 || endMinute > 59) return null;
  const start = startHour * 60 + startMinute;
  const end = endHour * 60 + endMinute;
  if (end <= start) return null;
  return normalizeHours(Math.max(0, (end - start) / 60 - breakHours));
}

function formatWorkingHours(value: number | null): string {
  if (value === null) return '-';
  return value.toFixed(1).replace('.', ',');
}

function formatWorkingHoursLabel(value: number | null, compact = false): string {
  if (value === null) return '-';
  const normalized = normalizeHours(value);
  const text = compact && Number.isInteger(normalized) ? String(normalized) : normalized.toFixed(1).replace('.', ',');
  return `${text} год`;
}

function splitWorkingTimeRange(value: string) {
  const match = value.trim().match(/^(\d{1,2})[:.](\d{2})\s*-\s*(\d{1,2})[:.](\d{2})$/);
  if (!match) {
    return { startHour: '08', startMinute: '00', endHour: '16', endMinute: '00' };
  }
  const [, startHour, startMinute, endHour, endMinute] = match;
  return {
    startHour: startHour.padStart(2, '0'),
    startMinute: startMinute.padStart(2, '0'),
    endHour: endHour.padStart(2, '0'),
    endMinute: endMinute.padStart(2, '0'),
  };
}

function buildWorkingTimeRange(parts: { startHour: string; startMinute: string; endHour: string; endMinute: string }) {
  return `${parts.startHour.padStart(2, '0')}:${parts.startMinute.padStart(2, '0')} - ${parts.endHour.padStart(2, '0')}:${parts.endMinute.padStart(2, '0')}`;
}

function emptyWorkingPatternForm(): WorkingPatternFormState {
  const days = workingPatternDays.reduce((acc, day) => {
    acc[day.key] = {
      key: day.key,
      label: day.label,
      time_range: '',
      break_hours: 0,
      hours: 0,
    };
    return acc;
  }, {} as Record<WorkingPatternDayKey, WorkingPatternDayForm>);
  return {
    name: '',
    uses_time_range: false,
    is_default: false,
    is_active: true,
    days,
  };
}

function workingPatternFormFromItem(item: WorkingPatternOption): WorkingPatternFormState {
  const form = emptyWorkingPatternForm();
  const scheduleDays = Array.isArray(item.schedule?.days) ? item.schedule.days : [];
  form.name = item.name;
  form.is_default = item.is_default;
  form.is_active = item.is_active;
  form.uses_time_range = Boolean(
    item.uses_time_range && scheduleDays.some((entry) => typeof entry.time_range === 'string' && entry.time_range.trim()),
  );
  workingPatternDays.forEach((day) => {
    const savedDay = scheduleDays.find((entry) => entry.key === day.key);
    form.days[day.key] = {
      key: day.key,
      label: day.label,
      time_range: typeof savedDay?.time_range === 'string' ? savedDay.time_range : '',
      break_hours: normalizeHours(numberFromApi(savedDay?.break_hours ?? 0)),
      hours: normalizeHours(numberFromApi(savedDay?.hours ?? item[day.field])),
    };
  });
  return form;
}

function workingPatternPayloadFromForm(form: WorkingPatternFormState) {
  const dayPayload = workingPatternDays.map((day) => {
    const value = form.days[day.key];
    const computedHours = form.uses_time_range ? parseTimeRangeHours(value.time_range, value.break_hours) : null;
    const hours = normalizeHours(computedHours ?? value.hours);
    return {
      key: day.key,
      label: day.label,
      time_range: value.time_range.trim(),
      break_hours: normalizeHours(value.break_hours),
      hours,
    };
  });
  const hoursByDay = Object.fromEntries(dayPayload.map((day) => [`${day.key}_hours`, day.hours]));
  return {
    name: form.name.trim(),
    ...hoursByDay,
    uses_time_range: form.uses_time_range,
    is_default: form.is_default,
    is_active: form.is_active,
    schedule: {
      source: 'local',
      days: dayPayload,
    },
  };
}

function SettingsDeleteConfirmModal({
  itemName,
  copy,
  loading,
  onCancel,
  onConfirm,
}: {
  itemName: string;
  copy: AppCopy;
  loading: boolean;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  return (
    <div className="settings-option-modal-layer" role="dialog" aria-modal="true" aria-label={copy.settings.confirmDeleteTitle}>
      <button type="button" className="settings-option-modal-backdrop" aria-label={copy.settings.cancel} onClick={onCancel} />
      <section className="settings-option-modal settings-delete-modal">
        <header>
          <strong>{copy.settings.confirmDeleteTitle}</strong>
          <button type="button" className="modal-close" aria-label={copy.settings.cancel} onClick={onCancel}>
            <X size={22} />
          </button>
        </header>
        <div className="settings-delete-body">
          <p>{copy.settings.confirmDeleteText}</p>
          <strong>{itemName}</strong>
        </div>
        <footer>
          <button type="button" className="secondary-action" onClick={onCancel} disabled={loading}>
            {copy.settings.cancel}
          </button>
          <button type="button" className="danger-action" onClick={onConfirm} disabled={loading}>
            {copy.settings.confirmDeleteAction}
          </button>
        </footer>
      </section>
    </div>
  );
}

function csvCell(value: string | number): string {
  const text = String(value);
  return /[",\n\r;]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

function htmlCell(value: string | number): string {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

const crcTable = Array.from({ length: 256 }, (_, index) => {
  let value = index;
  for (let bit = 0; bit < 8; bit += 1) {
    value = value & 1 ? 0xedb88320 ^ (value >>> 1) : value >>> 1;
  }
  return value >>> 0;
});

function crc32(bytes: Uint8Array): number {
  let crc = 0xffffffff;
  bytes.forEach((byte) => {
    crc = crcTable[(crc ^ byte) & 0xff] ^ (crc >>> 8);
  });
  return (crc ^ 0xffffffff) >>> 0;
}

function setUint16(view: DataView, offset: number, value: number) {
  view.setUint16(offset, value, true);
}

function setUint32(view: DataView, offset: number, value: number) {
  view.setUint32(offset, value, true);
}

function concatBytes(chunks: Uint8Array[]): Uint8Array {
  const total = chunks.reduce((sum, chunk) => sum + chunk.length, 0);
  const result = new Uint8Array(total);
  let offset = 0;
  chunks.forEach((chunk) => {
    result.set(chunk, offset);
    offset += chunk.length;
  });
  return result;
}

function zipStored(entries: Array<{ name: string; data: Uint8Array }>): Uint8Array {
  const encoder = new TextEncoder();
  const localParts: Uint8Array[] = [];
  const centralParts: Uint8Array[] = [];
  let offset = 0;

  entries.forEach((entry) => {
    const name = encoder.encode(entry.name);
    const crc = crc32(entry.data);
    const local = new Uint8Array(30 + name.length);
    const localView = new DataView(local.buffer);
    setUint32(localView, 0, 0x04034b50);
    setUint16(localView, 4, 20);
    setUint16(localView, 6, 0);
    setUint16(localView, 8, 0);
    setUint16(localView, 10, 0);
    setUint16(localView, 12, 0);
    setUint32(localView, 14, crc);
    setUint32(localView, 18, entry.data.length);
    setUint32(localView, 22, entry.data.length);
    setUint16(localView, 26, name.length);
    setUint16(localView, 28, 0);
    local.set(name, 30);
    localParts.push(local, entry.data);

    const central = new Uint8Array(46 + name.length);
    const centralView = new DataView(central.buffer);
    setUint32(centralView, 0, 0x02014b50);
    setUint16(centralView, 4, 20);
    setUint16(centralView, 6, 20);
    setUint16(centralView, 8, 0);
    setUint16(centralView, 10, 0);
    setUint16(centralView, 12, 0);
    setUint16(centralView, 14, 0);
    setUint32(centralView, 16, crc);
    setUint32(centralView, 20, entry.data.length);
    setUint32(centralView, 24, entry.data.length);
    setUint16(centralView, 28, name.length);
    setUint16(centralView, 30, 0);
    setUint16(centralView, 32, 0);
    setUint16(centralView, 34, 0);
    setUint16(centralView, 36, 0);
    setUint32(centralView, 38, 0);
    setUint32(centralView, 42, offset);
    central.set(name, 46);
    centralParts.push(central);
    offset += local.length + entry.data.length;
  });

  const centralDirectory = concatBytes(centralParts);
  const end = new Uint8Array(22);
  const endView = new DataView(end.buffer);
  setUint32(endView, 0, 0x06054b50);
  setUint16(endView, 4, 0);
  setUint16(endView, 6, 0);
  setUint16(endView, 8, entries.length);
  setUint16(endView, 10, entries.length);
  setUint32(endView, 12, centralDirectory.length);
  setUint32(endView, 16, offset);
  setUint16(endView, 20, 0);

  return concatBytes([...localParts, centralDirectory, end]);
}

function downloadTextFile(filename: string, content: string, type: string) {
  if (typeof document === 'undefined') return;
  const blob = new Blob([content], { type });
  downloadBlob(filename, blob);
}

function downloadBinaryFile(filename: string, content: Uint8Array, type: string) {
  if (typeof document === 'undefined') return;
  const buffer = new ArrayBuffer(content.byteLength);
  new Uint8Array(buffer).set(content);
  const blob = new Blob([buffer], { type });
  downloadBlob(filename, blob);
}

function downloadBlob(filename: string, blob: Blob) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 0);
}

function columnName(index: number): string {
  let value = index + 1;
  let name = '';
  while (value > 0) {
    const remainder = (value - 1) % 26;
    name = String.fromCharCode(65 + remainder) + name;
    value = Math.floor((value - 1) / 26);
  }
  return name;
}

function buildXlsx(rows: Array<Array<string | number>>, sheetName: string): Uint8Array {
  const encoder = new TextEncoder();
  const xmlRows = rows
    .map((row, rowIndex) => {
      const rowNumber = rowIndex + 1;
      const cells = row
        .map((cell, columnIndex) => {
          const reference = `${columnName(columnIndex)}${rowNumber}`;
          if (typeof cell === 'number') return `<c r="${reference}"><v>${cell}</v></c>`;
          return `<c r="${reference}" t="inlineStr"><is><t>${htmlCell(cell)}</t></is></c>`;
        })
        .join('');
      return `<row r="${rowNumber}">${cells}</row>`;
    })
    .join('');
  const safeSheetName = htmlCell(sheetName).slice(0, 31) || 'Export';
  const worksheet = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>${xmlRows}</sheetData></worksheet>`;
  const workbook = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="${safeSheetName}" sheetId="1" r:id="rId1"/></sheets></workbook>`;
  const workbookRels = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>`;
  const rootRels = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>`;
  const contentTypes = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>`;
  return zipStored([
    { name: '[Content_Types].xml', data: encoder.encode(contentTypes) },
    { name: '_rels/.rels', data: encoder.encode(rootRels) },
    { name: 'xl/workbook.xml', data: encoder.encode(workbook) },
    { name: 'xl/_rels/workbook.xml.rels', data: encoder.encode(workbookRels) },
    { name: 'xl/worksheets/sheet1.xml', data: encoder.encode(worksheet) },
  ]);
}

function SettingsOptionListView({
  kind,
  onBack,
  copy,
}: {
  kind: SettingsOptionKind;
  onBack: () => void;
  copy: AppCopy;
}) {
  const [items, setItems] = useState<SettingsOptionRow[]>([]);
  const [total, setTotal] = useState(0);
  const [loadState, setLoadState] = useState<LoadState>('idle');
  const [saveState, setSaveState] = useState<LoadState>('idle');
  const [error, setError] = useState('');
  const [editingItem, setEditingItem] = useState<SettingsOptionRow | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<SettingsOptionRow | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const [menuOpenId, setMenuOpenId] = useState<number | null>(null);
  const [exportMenuOpen, setExportMenuOpen] = useState(false);
  const [expandedKey, setExpandedKey] = useState<string | null>(null);
  const [expandedEmployees, setExpandedEmployees] = useState<Record<string, EmployeeListItem[]>>({});
  const [expandedLoadingKey, setExpandedLoadingKey] = useState<string | null>(null);
  const [draggingId, setDraggingId] = useState<number | null>(null);
  const [dragOverId, setDragOverId] = useState<number | null>(null);
  const [search, setSearch] = useState('');
  const [form, setForm] = useState({ name: '', is_active: true, duration_months: 0 });
  const title = copy.settings.items[kind] ?? kind;
  const isGender = kind === 'gender';
  const isTerminationReasons = kind === 'termination-reasons';
  const isTerminationTypes = kind === 'termination-types';
  const isTerminationDictionary = isTerminationReasons || isTerminationTypes;
  const isWorkTypes = kind === 'work-types';
  const isProbationConditions = kind === 'probation-conditions';
  const isPositions = kind === 'positions';
  const isDivisions = kind === 'divisions';
  const isSkills = kind === 'skills';
  const canExpandRows = !isTerminationDictionary;
  const showPeopleColumn = canExpandRows;
  const showDurationColumn = isProbationConditions;
  const hasSearch = isPositions || isTerminationDictionary || isProbationConditions;
  const searchQuery = hasSearch ? search.trim() : '';
  const navigate = useNavigate();

  function optionExpansionKey(item: SettingsOptionRow) {
    return `${kind}:${item.id}`;
  }

  function sortRows(rows: SettingsOptionRow[]) {
    return [...rows].sort((first, second) => {
      if (first.is_system !== second.is_system) return first.is_system ? 1 : -1;
      const firstOrder = first.sort_order ?? 0;
      const secondOrder = second.sort_order ?? 0;
      if (firstOrder !== secondOrder) return firstOrder - secondOrder;
      return first.name.localeCompare(second.name, 'uk');
    });
  }

  async function loadOptions(cancelled?: () => boolean) {
    setLoadState('loading');
    setError('');
    try {
      const result = isGender
        ? await api.genders({ page_size: 200 })
        : isTerminationReasons
          ? await api.terminationReasons({ q: searchQuery, page_size: 200 })
          : isTerminationTypes
            ? await api.terminationTypes({ q: searchQuery, page_size: 200 })
            : isWorkTypes
              ? await api.workTypes({ q: searchQuery, page_size: 200 })
              : isProbationConditions
                ? await api.probationPolicies({ q: searchQuery, page_size: 200 })
                : isPositions
                  ? await api.positions({ q: searchQuery, page_size: 200 })
                  : isDivisions
                    ? await api.divisions({ page_size: 200 })
                    : isSkills
                      ? await api.skills({ page_size: 200 })
                      : await api.jobLevels({ page_size: 200 });
      let rows: SettingsOptionRow[] = result.items.map((item) => ({ ...item }));
      let totalCount = result.total;
      if (kind === 'experience-levels') {
        const employeesResult = await api.employees({ status: 'active', page_size: 1 });
        const filledCount = rows.reduce((sum, item) => sum + item.employee_count, 0);
        rows = [
          ...rows,
          {
            id: 0,
            name: copy.settings.unfilledItem,
            sort_order: Number.MAX_SAFE_INTEGER,
            is_active: true,
            employee_count: Math.max(0, employeesResult.total - filledCount),
            is_system: true,
          },
        ];
        totalCount += 1;
      }
      if (cancelled?.()) return;
      setItems(sortRows(rows));
      setTotal(totalCount);
      setLoadState('ok');
    } catch {
      if (cancelled?.()) return;
      setItems([]);
      setTotal(0);
      setLoadState('error');
      setError(copy.settings.loadErrorText);
    }
  }

  useEffect(() => {
    let cancelled = false;

    void loadOptions(() => cancelled);
    return () => {
      cancelled = true;
    };
  }, [
    copy.settings.loadErrorText,
    copy.settings.unfilledItem,
    isGender,
    isTerminationReasons,
    isTerminationTypes,
    isWorkTypes,
    isProbationConditions,
    isPositions,
    isDivisions,
    isSkills,
    kind,
    searchQuery,
  ]);

  useEffect(() => {
    setExpandedKey(null);
    setExpandedEmployees({});
    setExpandedLoadingKey(null);
    setMenuOpenId(null);
    setExportMenuOpen(false);
  }, [kind, searchQuery]);

  function openCreateForm() {
    setExportMenuOpen(false);
    setMenuOpenId(null);
    setDeleteTarget(null);
    setEditingItem(null);
    setForm({ name: '', is_active: true, duration_months: 0 });
    setSaveState('idle');
    setError('');
    setFormOpen(true);
  }

  function openEditForm(item: SettingsOptionRow) {
    if (item.is_system) return;
    setMenuOpenId(null);
    setExportMenuOpen(false);
    setDeleteTarget(null);
    setEditingItem(item);
    setForm({ name: item.name, is_active: item.is_active, duration_months: item.duration_months ?? 0 });
    setSaveState('idle');
    setError('');
    setFormOpen(true);
  }

  function closeForm() {
    setFormOpen(false);
    setEditingItem(null);
    setForm({ name: '', is_active: true, duration_months: 0 });
    setSaveState('idle');
  }

  function requestDeleteOption(item: SettingsOptionRow) {
    if (item.is_system) return;
    setMenuOpenId(null);
    setExportMenuOpen(false);
    setFormOpen(false);
    setDeleteTarget(item);
    setSaveState('idle');
    setError('');
  }

  function closeDeleteConfirm() {
    if (saveState === 'loading') return;
    setDeleteTarget(null);
    setSaveState('idle');
  }

  async function saveOption(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const name = form.name.trim();
    if (!name) return;

    setSaveState('loading');
    setError('');
    try {
      const payload = isProbationConditions
        ? { name, duration_months: Math.max(0, Number(form.duration_months) || 0), is_active: form.is_active }
        : { name, is_active: form.is_active };
      const saved = editingItem
        ? isGender
          ? await api.updateGender(editingItem.id, payload)
          : isTerminationReasons
            ? await api.updateTerminationReason(editingItem.id, payload)
            : isTerminationTypes
              ? await api.updateTerminationType(editingItem.id, payload)
              : isWorkTypes
                ? await api.updateWorkType(editingItem.id, payload)
                : isProbationConditions
                  ? await api.updateProbationPolicy(editingItem.id, payload)
                  : isPositions
                    ? await api.updatePosition(editingItem.id, payload)
                    : isDivisions
                      ? await api.updateDivision(editingItem.id, payload)
                      : isSkills
                        ? await api.updateSkill(editingItem.id, payload)
                        : await api.updateJobLevel(editingItem.id, payload)
        : isGender
          ? await api.createGender(payload)
          : isTerminationReasons
            ? await api.createTerminationReason(payload)
            : isTerminationTypes
              ? await api.createTerminationType(payload)
              : isWorkTypes
                ? await api.createWorkType(payload)
                : isProbationConditions
                  ? await api.createProbationPolicy(payload)
                  : isPositions
                    ? await api.createPosition(payload)
                    : isDivisions
                      ? await api.createDivision(payload)
                      : isSkills
                        ? await api.createSkill(payload)
                        : await api.createJobLevel(payload);
      setItems((current) => {
        const withoutSaved = current.filter((item) => item.id !== saved.id);
        return sortRows([...withoutSaved, saved]);
      });
      if (!editingItem) setTotal((current) => current + 1);
      closeForm();
    } catch (saveError) {
      setSaveState('error');
      setError(saveError instanceof ApiError ? saveError.message : copy.settings.loadErrorText);
    }
  }

  async function deleteOption(item: SettingsOptionRow) {
    if (item.is_system) return;
    setMenuOpenId(null);
    setSaveState('loading');
    setError('');
    try {
      if (isGender) {
        await api.deleteGender(item.id);
      } else if (isTerminationReasons) {
        await api.deleteTerminationReason(item.id);
      } else if (isTerminationTypes) {
        await api.deleteTerminationType(item.id);
      } else if (isWorkTypes) {
        await api.deleteWorkType(item.id);
      } else if (isProbationConditions) {
        await api.deleteProbationPolicy(item.id);
      } else if (isPositions) {
        await api.deletePosition(item.id);
      } else if (isDivisions) {
        await api.deleteDivision(item.id);
      } else if (isSkills) {
        await api.deleteSkill(item.id);
      } else {
        await api.deleteJobLevel(item.id);
      }
      await loadOptions();
      setDeleteTarget(null);
      setSaveState('idle');
    } catch (deleteError) {
      setSaveState('error');
      setError(deleteError instanceof ApiError ? deleteError.message : copy.settings.loadErrorText);
    }
  }

  function employeeFullName(employee: EmployeeListItem) {
    return employee.full_name || `${employee.last_name} ${employee.first_name}`.trim();
  }

  async function loadEmployeesForOption(item: SettingsOptionRow, page = 1, pageSize = 500) {
    const base = { status: 'active', compact: true, page, page_size: pageSize };
    if (kind === 'gender') {
      return api.employees({ ...base, gender: item.code || 'none' });
    }
    if (kind === 'work-types') {
      return api.employees({ ...base, employment_type: item.id });
    }
    if (kind === 'probation-conditions') {
      return api.employees({ ...base, probation_policy: item.id });
    }
    if (kind === 'positions') {
      return api.employees({ ...base, position: item.id });
    }
    if (kind === 'divisions') {
      return api.employees({ ...base, division: item.id });
    }
    if (kind === 'skills') {
      return api.employees({ ...base, medical_specialty: item.id });
    }
    return api.employees({ ...base, job_level: item.is_system ? 'none' : item.id });
  }

  async function loadAllEmployeesForOption(item: SettingsOptionRow) {
    if (!item.employee_count) return [];
    const employees: EmployeeListItem[] = [];
    let page = 1;
    for (let guard = 0; guard < 20; guard += 1) {
      const result = await loadEmployeesForOption(item, page, 500);
      employees.push(...result.items);
      if (!result.next || employees.length >= result.total) break;
      page += 1;
    }
    return employees;
  }

  async function employeeExportRowsForOptions() {
    if (!canExpandRows) return [];
    const rows: Array<Array<string | number>> = [];
    for (const item of items) {
      const key = optionExpansionKey(item);
      const cached = expandedEmployees[key];
      const employees = cached && cached.length >= item.employee_count ? cached : await loadAllEmployeesForOption(item);
      employees.forEach((employee) => {
        rows.push([item.name, employeeFullName(employee), employee.status || '']);
      });
    }
    return rows;
  }

  async function exportOptions(format: SettingsExportFormat) {
    setExportMenuOpen(false);
    const headers = showPeopleColumn
      ? [copy.settings.nameColumn, ...(showDurationColumn ? ['Тривалість (місяці)'] : []), copy.settings.peopleColumn, copy.people.status ?? 'Status']
      : [copy.settings.nameColumn, copy.people.status ?? 'Status'];
    const rows = items.map((item) => [
      item.name,
      ...(showDurationColumn ? [item.duration_months ?? 0] : []),
      ...(showPeopleColumn ? [item.employee_count] : []),
      item.is_active ? copy.settings.active : copy.settings.inactive,
    ]);
    const employeeRows = await employeeExportRowsForOptions();
    const exportRows: Array<Array<string | number>> = [headers, ...rows];
    if (employeeRows.length) {
      exportRows.push([], [copy.settings.peopleColumn], [copy.settings.nameColumn, copy.settings.peopleColumn, copy.people.status ?? 'Status'], ...employeeRows);
    }
    const safeName = kind.replace(/[^a-z0-9-]/gi, '-').toLowerCase();

    if (format === 'csv') {
      const csv = exportRows.map((row) => row.map(csvCell).join(';')).join('\n');
      downloadTextFile(`${safeName}.csv`, `\uFEFF${csv}`, 'text/csv;charset=utf-8');
      return;
    }

    downloadBinaryFile(
      `${safeName}.xlsx`,
      buildXlsx(exportRows, title),
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    );
  }

  async function toggleEmployees(item: SettingsOptionRow) {
    if (!canExpandRows) return;
    const key = optionExpansionKey(item);
    setMenuOpenId(null);
    setExportMenuOpen(false);
    setExpandedKey((current) => (current === key ? null : key));
    if (expandedKey === key || expandedEmployees[key]) return;

    setExpandedLoadingKey(key);
    try {
      const result = await loadEmployeesForOption(item, 1, 300);
      setExpandedEmployees((current) => ({ ...current, [key]: result.items }));
    } catch {
      setExpandedEmployees((current) => ({ ...current, [key]: [] }));
    } finally {
      setExpandedLoadingKey((current) => (current === key ? null : current));
    }
  }

  function moveLocalRows(sourceId: number, targetId: number): SettingsOptionRow[] {
    const systemRows = items.filter((item) => item.is_system);
    const movableRows = items.filter((item) => !item.is_system);
    const sourceIndex = movableRows.findIndex((item) => item.id === sourceId);
    const targetIndex = movableRows.findIndex((item) => item.id === targetId);
    if (sourceIndex < 0 || targetIndex < 0 || sourceIndex === targetIndex) return items;
    const nextMovableRows = [...movableRows];
    const [moved] = nextMovableRows.splice(sourceIndex, 1);
    nextMovableRows.splice(targetIndex, 0, moved);
    return [...nextMovableRows, ...systemRows];
  }

  async function saveRowOrder(nextRows: SettingsOptionRow[]) {
    if (kind !== 'experience-levels') return;
    const ids = nextRows.filter((item) => !item.is_system).map((item) => item.id);
    try {
      const savedRows = await api.reorderJobLevels(ids);
      setItems((current) => {
        const systemRows = current.filter((item) => item.is_system);
        return [...savedRows.map((item) => ({ ...item })), ...systemRows];
      });
    } catch {
      setError(copy.settings.loadErrorText);
    }
  }

  function handleDragStart(event: DragEvent<HTMLButtonElement>, item: SettingsOptionRow) {
    if (kind !== 'experience-levels' || item.is_system) return;
    event.stopPropagation();
    setDraggingId(item.id);
    event.dataTransfer.effectAllowed = 'move';
    event.dataTransfer.setData('text/plain', String(item.id));
  }

  function handleDragOver(event: DragEvent<HTMLTableRowElement>, item: SettingsOptionRow) {
    if (kind !== 'experience-levels' || item.is_system || draggingId === null || draggingId === item.id) return;
    event.preventDefault();
    setDragOverId(item.id);
  }

  function handleDrop(event: DragEvent<HTMLTableRowElement>, item: SettingsOptionRow) {
    event.preventDefault();
    if (kind !== 'experience-levels' || item.is_system || draggingId === null || draggingId === item.id) {
      setDraggingId(null);
      setDragOverId(null);
      return;
    }
    const nextRows = moveLocalRows(draggingId, item.id);
    setItems(nextRows);
    setDraggingId(null);
    setDragOverId(null);
    void saveRowOrder(nextRows);
  }

  function openEmployee(employee: EmployeeListItem) {
    navigate(peopleEmployeePath(employee.id));
  }

  return (
    <main className="settings-page settings-option-page">
      <header className="settings-option-header">
        <div>
          <button type="button" className="settings-back-link" onClick={onBack}>
            <ChevronLeft size={17} />
            {copy.common.previous}
          </button>
          <h1>{title}</h1>
        </div>
        <div className="settings-option-actions">
          <div className="settings-option-export">
            <button
              type="button"
              className={`toolbar-icon ${exportMenuOpen ? 'active' : ''}`}
              aria-label={copy.common.export}
              aria-expanded={exportMenuOpen}
              onClick={() => {
                setMenuOpenId(null);
                setExportMenuOpen((current) => !current);
              }}
            >
              <MoreHorizontal size={18} />
            </button>
            {exportMenuOpen ? (
              <div className="settings-option-export-menu">
                <button type="button" onClick={() => void exportOptions('xlsx')}>
                  {copy.settings.exportXlsx}
                </button>
                <button type="button" onClick={() => void exportOptions('csv')}>
                  {copy.settings.exportCsv}
                </button>
              </div>
            ) : null}
          </div>
          <button type="button" className="primary-action" onClick={openCreateForm}>
            <Plus size={18} />
            {copy.settings.add}
          </button>
        </div>
      </header>

      {hasSearch ? (
        <div className="settings-option-search">
          <Search size={18} />
          <input value={search} placeholder={copy.common.search} onChange={(event) => setSearch(event.target.value)} />
        </div>
      ) : null}

      {formOpen ? (
        <div className="settings-option-modal-layer" role="dialog" aria-modal="true" aria-label={editingItem ? copy.settings.editItemTitle : copy.settings.createItemTitle}>
          <button type="button" className="settings-option-modal-backdrop" aria-label={copy.settings.cancel} onClick={closeForm} />
          <form className="settings-option-modal" onSubmit={saveOption}>
            <header>
              <strong>{editingItem ? copy.settings.editItemTitle : copy.settings.createItemTitle}</strong>
              <button type="button" className="modal-close" aria-label={copy.settings.cancel} onClick={closeForm}>
                <X size={22} />
              </button>
            </header>
            <label>
              <span>{copy.settings.nameColumn}</span>
              <input value={form.name} onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))} autoFocus />
            </label>
            {showDurationColumn ? (
              <label>
                <span>Тривалість (місяці)</span>
                <div className="settings-option-duration-control">
                  <input
                    type="number"
                    min="0"
                    step="1"
                    value={form.duration_months}
                    onChange={(event) =>
                      setForm((current) => ({ ...current, duration_months: Math.max(0, Number(event.target.value) || 0) }))
                    }
                  />
                  <button
                    type="button"
                    aria-label="Зменшити тривалість"
                    onClick={() => setForm((current) => ({ ...current, duration_months: Math.max(0, current.duration_months - 1) }))}
                  >
                    -
                  </button>
                  <button
                    type="button"
                    aria-label="Збільшити тривалість"
                    onClick={() => setForm((current) => ({ ...current, duration_months: current.duration_months + 1 }))}
                  >
                    +
                  </button>
                </div>
              </label>
            ) : null}
            <label className="settings-option-checkbox">
              <input
                type="checkbox"
                checked={form.is_active}
                onChange={(event) => setForm((current) => ({ ...current, is_active: event.target.checked }))}
              />
              <span>{copy.settings.activeField}</span>
            </label>
            <footer>
              <button type="submit" className="primary-action" disabled={!form.name.trim() || saveState === 'loading'}>
                {copy.settings.save}
              </button>
            </footer>
          </form>
        </div>
      ) : null}

      {deleteTarget ? (
        <SettingsDeleteConfirmModal
          itemName={deleteTarget.name}
          copy={copy}
          loading={saveState === 'loading'}
          onCancel={closeDeleteConfirm}
          onConfirm={() => void deleteOption(deleteTarget)}
        />
      ) : null}

      <div className="settings-option-meta">{loadState === 'loading' ? copy.common.loading : resultMetaLabel(items.length, total, copy)}</div>

      <section className={`settings-option-table ${showDurationColumn ? 'settings-option-duration-table' : ''}`}>
        {loadState === 'error' ? (
          <EmptyState title={copy.settings.loadErrorTitle} text={error || copy.settings.loadErrorText} />
        ) : items.length ? (
          <table>
            <thead>
              <tr>
                <th>{copy.settings.nameColumn}</th>
                {showDurationColumn ? <th>Тривалість (місяці)</th> : null}
                {showPeopleColumn ? <th>{copy.settings.peopleColumn}</th> : null}
                <th>{copy.common.actions}</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => {
                const expansionKey = optionExpansionKey(item);
                const isExpanded = expandedKey === expansionKey;
                const people = expandedEmployees[expansionKey] ?? [];
                const rowClassName = [
                  canExpandRows ? 'expandable' : '',
                  !item.is_active ? 'muted' : '',
                  item.is_system ? 'system' : '',
                  draggingId === item.id ? 'dragging' : '',
                  dragOverId === item.id ? 'drag-over' : '',
                  isExpanded ? 'expanded' : '',
                ]
                  .filter(Boolean)
                  .join(' ');

                return (
                  <Fragment key={item.id}>
                    <tr
                      className={rowClassName}
                      onClick={() => {
                        if (canExpandRows) void toggleEmployees(item);
                      }}
                      onDragOver={(event) => handleDragOver(event, item)}
                      onDragLeave={() => setDragOverId((current) => (current === item.id ? null : current))}
                      onDrop={(event) => handleDrop(event, item)}
                    >
                      <td>
                        <div className="settings-option-name-wrap">
                          {kind === 'experience-levels' && !item.is_system ? (
                            <button
                              type="button"
                              className="settings-option-drag"
                              draggable
                              aria-label={copy.common.actions}
                              onClick={(event) => event.stopPropagation()}
                              onDragStart={(event) => handleDragStart(event, item)}
                              onDragEnd={() => {
                                setDraggingId(null);
                                setDragOverId(null);
                              }}
                            >
                              <GripVertical size={18} />
                            </button>
                          ) : item.is_system ? (
                            <span className="settings-option-lock" title={copy.settings.systemItem}>
                              <Lock size={16} />
                            </span>
                          ) : (
                            <span className="settings-option-spacer" />
                          )}
                          {canExpandRows ? (
                            <button
                              type="button"
                              className="settings-option-name"
                              onClick={(event) => {
                                event.stopPropagation();
                                void toggleEmployees(item);
                              }}
                            >
                              <span>{item.name}</span>
                              {!item.is_active ? <em>{copy.settings.inactive}</em> : null}
                              {isExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                            </button>
                          ) : (
                            <div className="settings-option-name static">
                              <span>{item.name}</span>
                              {!item.is_active ? <em>{copy.settings.inactive}</em> : null}
                            </div>
                          )}
                        </div>
                      </td>
                      {showDurationColumn ? <td>{item.duration_months ?? 0}</td> : null}
                      {showPeopleColumn ? <td>{item.employee_count}</td> : null}
                      <td>
                        {item.is_system ? null : (
                          <div className="settings-option-row-menu">
                            <button
                              type="button"
                              className="row-action"
                              aria-label={copy.common.actions}
                              onClick={(event) => {
                                event.stopPropagation();
                                setMenuOpenId((current) => (current === item.id ? null : item.id));
                              }}
                            >
                              <MoreHorizontal size={16} />
                            </button>
                            {menuOpenId === item.id ? (
                              <div className="settings-option-row-popover">
                                <button
                                  type="button"
                                  onClick={(event) => {
                                    event.stopPropagation();
                                    openEditForm(item);
                                  }}
                                >
                                  {copy.settings.edit}
                                </button>
                                <button
                                  type="button"
                                  className="danger"
                                  onClick={(event) => {
                                    event.stopPropagation();
                                    requestDeleteOption(item);
                                  }}
                                >
                                  {copy.settings.delete}
                                </button>
                              </div>
                            ) : null}
                          </div>
                        )}
                      </td>
                    </tr>
                    {canExpandRows && isExpanded ? (
                      <tr className="settings-option-people-row">
                        <td colSpan={(showPeopleColumn ? 3 : 2) + (showDurationColumn ? 1 : 0)}>
                          <div className="settings-option-people-list">
                            {expandedLoadingKey === expansionKey ? (
                              <span className="settings-option-people-loading">{copy.common.loading}</span>
                            ) : people.length ? (
                              people.map((employee, index) => {
                                const fullName = employee.full_name || `${employee.last_name} ${employee.first_name}`.trim();
                                return (
                                  <button
                                    key={employee.id}
                                    type="button"
                                    className="settings-option-person"
                                    onClick={() => openEmployee(employee)}
                                  >
                                    <Avatar
                                      name={fullName}
                                      src={employeeAvatarUrl(employee)}
                                      accent={employeeAccentClasses[index % employeeAccentClasses.length]}
                                      size="sm"
                                    />
                                    <span>{fullName}</span>
                                  </button>
                                );
                              })
                            ) : (
                              <span className="settings-option-people-empty">{copy.people.employeesNotFound}</span>
                            )}
                          </div>
                        </td>
                      </tr>
                    ) : null}
                  </Fragment>
                );
              })}
            </tbody>
          </table>
        ) : (
          <EmptyState title={copy.settings.noRowsTitle} text={copy.settings.noRowsText} />
        )}
      </section>
    </main>
  );
}

const holidayMonths = [
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
];
const holidayWeekdays = ['ПН', 'ВТ', 'СР', 'ЧТ', 'ПТ', 'СБ', 'НД'];
const holidayCountryOptions = [
  { value: 'UA', label: 'Україна' },
  { value: 'PL', label: 'Польща' },
  { value: 'GB', label: 'Велика Британія' },
  { value: 'US', label: 'США' },
];
type HolidayPolicyDisplay = HolidayPolicyOption & {
  is_system?: boolean;
  system_kind?: 'birthdays';
};
type HolidayCalendarEvent = {
  id: string;
  kind: 'holiday' | 'birthday';
  name: string;
  isoDate: string;
  className: 'non-working' | 'working' | 'compensated' | 'birthday';
  holiday?: HolidayOption;
  employee?: EmployeeListItem;
  recurring?: boolean;
  source?: 'holiday' | 'observed' | 'compensated';
};

type BirthdayMilestoneInfo = {
  label: string;
  description: string;
  tone: 'early' | 'youth' | 'mature' | 'major' | 'honor';
  Icon: LucideIcon;
};

const birthdaySystemPolicy: HolidayPolicyDisplay = {
  id: -1,
  name: 'Дні народження співробітників',
  external_peopleforce_id: '',
  country_code: '',
  country_name: 'Система',
  is_active: true,
  location_count: 0,
  holiday_count: 0,
  is_system: true,
  system_kind: 'birthdays',
};

function padDatePart(value: number) {
  return String(value).padStart(2, '0');
}

function localIsoDate(year: number, monthIndex: number, day: number) {
  return `${year}-${padDatePart(monthIndex + 1)}-${padDatePart(day)}`;
}

function todayIsoDate() {
  const today = new Date();
  return localIsoDate(today.getFullYear(), today.getMonth(), today.getDate());
}

function parseIsoDateParts(value: string | null | undefined) {
  const match = String(value ?? '').match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (!match) return null;
  return {
    year: Number(match[1]),
    month: Number(match[2]),
    day: Number(match[3]),
  };
}

function monthDayCount(year: number, monthIndex: number) {
  return new Date(year, monthIndex + 1, 0).getDate();
}

function holidayOccurrenceIso(holiday: HolidayOption, year: number) {
  return recurringDateIso(holiday.occurs_on, holiday.recurrence, year);
}

function recurringDateIso(dateValue: string | null | undefined, recurrence: string | null | undefined, year: number) {
  const parts = parseIsoDateParts(dateValue);
  if (!parts) return String(dateValue ?? '');
  if (recurrence !== 'yearly') return String(dateValue);
  const monthIndex = parts.month - 1;
  const day = Math.min(parts.day, monthDayCount(year, monthIndex));
  return localIsoDate(year, monthIndex, day);
}

function formatHolidayDate(value: string) {
  const parts = parseIsoDateParts(value);
  if (!parts) return value;
  return `${padDatePart(parts.day)}.${padDatePart(parts.month)}.${parts.year}`;
}

function holidayTypeClass(holiday: HolidayOption) {
  if (holiday.working) return 'working';
  return 'non-working';
}

function employeeCalendarName(employee: EmployeeListItem) {
  return employee.full_name || `${employee.last_name ?? ''} ${employee.first_name ?? ''}`.trim();
}

function employeeBirthdayAge(employee: EmployeeListItem, calendarYear: number) {
  const parts = parseIsoDateParts(employee.birth_date);
  if (!parts) return null;
  return Math.max(0, calendarYear - parts.year);
}

function ageUnitUk(age: number) {
  const lastTwo = age % 100;
  const last = age % 10;
  if (lastTwo >= 11 && lastTwo <= 14) return 'років';
  if (last === 1) return 'рік';
  if (last >= 2 && last <= 4) return 'роки';
  return 'років';
}

function birthdayAgeText(employee: EmployeeListItem, calendarYear: number) {
  const age = employeeBirthdayAge(employee, calendarYear);
  return age === null ? 'Вік не вказано' : `Виповнюється ${age} ${ageUnitUk(age)}`;
}

function birthdayMilestoneForAge(age: number | null): BirthdayMilestoneInfo | null {
  if (age === null) return null;
  if ([10, 15, 20].includes(age)) {
    return {
      label: 'Перші усвідомлені дати',
      description: '10, 15 і 20 років: перші помітні особисті рубежі.',
      tone: 'early',
      Icon: Sparkles,
    };
  }
  if ([18, 25].includes(age)) {
    return {
      label: 'Повноліття і молодість',
      description: '18 і 25 років: важливий перехід до дорослого етапу.',
      tone: 'youth',
      Icon: Rocket,
    };
  }
  if ([30, 35, 40, 45].includes(age)) {
    return {
      label: 'Серйозний етап зрілості',
      description: '30, 35, 40 і 45 років: сильний життєвий та професійний рубіж.',
      tone: 'mature',
      Icon: Star,
    };
  }
  if ([50, 55, 60, 65].includes(age)) {
    return {
      label: 'Крупний ювілей',
      description: '50, 55, 60 і 65 років: велика ювілейна дата.',
      tone: 'major',
      Icon: ShieldCheck,
    };
  }
  if (age >= 70 && age % 5 === 0) {
    return {
      label: 'Почесна дата',
      description: '70, 75, 80 років і старше: особливий почесний ювілей.',
      tone: 'honor',
      Icon: Sparkles,
    };
  }
  return null;
}

function birthdayMilestoneForEmployee(employee: EmployeeListItem, calendarYear: number) {
  return birthdayMilestoneForAge(employeeBirthdayAge(employee, calendarYear));
}

function birthdayAccent(employee: EmployeeListItem) {
  return employeeAccentClasses[employee.id % employeeAccentClasses.length];
}

function BirthdayMilestoneMark({ milestone }: { milestone: BirthdayMilestoneInfo }) {
  const Icon = milestone.Icon;
  return (
    <span className={`settings-holiday-birthday-milestone ${milestone.tone}`} aria-hidden="true">
      <Icon size={13} />
    </span>
  );
}

function BirthdayTooltip({ events, year }: { events: HolidayCalendarEvent[]; year: number }) {
  const birthdays = events.filter((event) => event.kind === 'birthday' && event.employee);
  if (!birthdays.length) return null;
  return (
    <span className="settings-holiday-birthday-tooltip" aria-hidden="true">
      {birthdays.map((event) => {
        const employee = event.employee;
        if (!employee) return null;
        const milestone = birthdayMilestoneForEmployee(employee, year);
        const MilestoneIcon = milestone?.Icon;
        return (
          <span key={event.id} className={`settings-holiday-birthday-card ${milestone ? `milestone-${milestone.tone}` : ''}`}>
            <Avatar name={event.name} src={employeeAvatarUrl(employee)} accent={birthdayAccent(employee)} size="sm" />
            <span>
              <strong>{event.name}</strong>
              <em>{birthdayAgeText(employee, year)}</em>
              {milestone && MilestoneIcon ? (
                <span className={`settings-holiday-birthday-stage ${milestone.tone}`}>
                  <span className="settings-holiday-birthday-stage-icon">
                    <MilestoneIcon size={14} />
                  </span>
                  <span>
                    <b>{milestone.label}</b>
                    <small>{milestone.description}</small>
                  </span>
                </span>
              ) : null}
            </span>
          </span>
        );
      })}
    </span>
  );
}

function emptyHolidayPolicyForm(): HolidayPolicyFormState {
  return {
    name: '',
    country_code: 'UA',
    is_active: true,
  };
}

function holidayPolicyFormFromItem(item: HolidayPolicyOption): HolidayPolicyFormState {
  return {
    name: item.name,
    country_code: item.country_code || 'UA',
    is_active: item.is_active,
  };
}

function emptyHolidayForm(dateValue = todayIsoDate()): HolidayFormState {
  return {
    name: '',
    occurs_on: dateValue,
    working: false,
    compensated_on: '',
    observed_on: '',
    recurrence: 'none',
    is_active: true,
  };
}

function holidayFormFromItem(item: HolidayOption, year: number): HolidayFormState {
  return {
    name: item.name,
    occurs_on: item.recurrence === 'yearly' ? holidayOccurrenceIso(item, year) : item.occurs_on,
    working: item.working,
    compensated_on: item.compensated_on ? recurringDateIso(item.compensated_on, item.recurrence, year) : '',
    observed_on: item.observed_on ? recurringDateIso(item.observed_on, item.recurrence, year) : '',
    recurrence: item.recurrence === 'yearly' ? 'yearly' : 'none',
    is_active: item.is_active,
  };
}

function SettingsHolidayPoliciesView({ onBack, copy }: { onBack: () => void; copy: AppCopy }) {
  const navigate = useNavigate();
  const [policies, setPolicies] = useState<HolidayPolicyDisplay[]>([]);
  const [total, setTotal] = useState(0);
  const [loadState, setLoadState] = useState<LoadState>('idle');
  const [saveState, setSaveState] = useState<LoadState>('idle');
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [selectedPolicy, setSelectedPolicy] = useState<HolidayPolicyDisplay | null>(null);
  const [policyFormOpen, setPolicyFormOpen] = useState(false);
  const [editingPolicy, setEditingPolicy] = useState<HolidayPolicyOption | null>(null);
  const [policyForm, setPolicyForm] = useState<HolidayPolicyFormState>(() => emptyHolidayPolicyForm());
  const [policyMenuOpenId, setPolicyMenuOpenId] = useState<number | null>(null);
  const [policyDeleteTarget, setPolicyDeleteTarget] = useState<HolidayPolicyOption | null>(null);
  const [year, setYear] = useState(() => new Date().getFullYear());
  const [holidays, setHolidays] = useState<HolidayOption[]>([]);
  const [birthdayEmployees, setBirthdayEmployees] = useState<EmployeeListItem[]>([]);
  const [birthdayLoadState, setBirthdayLoadState] = useState<LoadState>('idle');
  const [holidayLoadState, setHolidayLoadState] = useState<LoadState>('idle');
  const [holidayFormOpen, setHolidayFormOpen] = useState(false);
  const [editingHoliday, setEditingHoliday] = useState<HolidayOption | null>(null);
  const [holidayForm, setHolidayForm] = useState<HolidayFormState>(() => emptyHolidayForm());
  const [holidayDeleteTarget, setHolidayDeleteTarget] = useState<HolidayOption | null>(null);
  const searchQuery = search.trim();
  const isBirthdayCalendar = selectedPolicy?.system_kind === 'birthdays';

  async function loadPolicies(cancelled?: () => boolean) {
    setLoadState('loading');
    setError('');
    try {
      const result = await api.holidayPolicies({ q: searchQuery, is_active: true, page_size: 300 });
      if (cancelled?.()) return;
      const rows: HolidayPolicyDisplay[] = [...result.items].sort((first, second) => first.name.localeCompare(second.name, 'uk'));
      const withSystem =
        !searchQuery || birthdaySystemPolicy.name.toLowerCase().includes(searchQuery.toLowerCase())
          ? [birthdaySystemPolicy, ...rows]
          : rows;
      setPolicies(withSystem);
      setTotal(result.total + (withSystem.some((item) => item.is_system) ? 1 : 0));
      setSelectedPolicy((current) => {
        if (!current) return current;
        if (current.system_kind === 'birthdays') return withSystem.find((item) => item.system_kind === 'birthdays') ?? null;
        return rows.find((item) => item.id === current.id) ?? current;
      });
      setLoadState('ok');
    } catch (loadError) {
      if (cancelled?.()) return;
      setPolicies([]);
      setTotal(0);
      setLoadState('error');
      setError(loadError instanceof ApiError ? loadError.message : copy.settings.loadErrorText);
    }
  }

  async function loadHolidays(policyId: number, calendarYear: number, cancelled?: () => boolean) {
    setHolidayLoadState('loading');
    setError('');
    try {
      const result = await api.holidays({ policy: policyId, year: calendarYear, is_active: true, page_size: 600 });
      if (cancelled?.()) return;
      setHolidays(result.items);
      setHolidayLoadState('ok');
    } catch (loadError) {
      if (cancelled?.()) return;
      setHolidays([]);
      setHolidayLoadState('error');
      setError(loadError instanceof ApiError ? loadError.message : copy.settings.loadErrorText);
    }
  }

  async function loadBirthdayEmployees(cancelled?: () => boolean) {
    setBirthdayLoadState('loading');
    setError('');
    try {
      const employees: EmployeeListItem[] = [];
      let page = 1;
      for (let guard = 0; guard < 20; guard += 1) {
        const result = await api.employees({ status: 'active', compact: true, page, page_size: 500 });
        employees.push(...result.items);
        if (!result.next || employees.length >= result.total) break;
        page += 1;
      }
      if (cancelled?.()) return;
      setBirthdayEmployees(employees.filter((employee) => Boolean(employee.birth_date)));
      setBirthdayLoadState('ok');
    } catch (loadError) {
      if (cancelled?.()) return;
      setBirthdayEmployees([]);
      setBirthdayLoadState('error');
      setError(loadError instanceof ApiError ? loadError.message : copy.settings.loadErrorText);
    }
  }

  useEffect(() => {
    let cancelled = false;
    void loadPolicies(() => cancelled);
    return () => {
      cancelled = true;
    };
  }, [copy.settings.loadErrorText, searchQuery]);

  useEffect(() => {
    if (!selectedPolicy || selectedPolicy.system_kind) return;
    let cancelled = false;
    void loadHolidays(selectedPolicy.id, year, () => cancelled);
    return () => {
      cancelled = true;
    };
  }, [selectedPolicy?.id, selectedPolicy?.system_kind, year]);

  useEffect(() => {
    if (selectedPolicy?.system_kind !== 'birthdays') return;
    let cancelled = false;
    setHolidays([]);
    void loadBirthdayEmployees(() => cancelled);
    return () => {
      cancelled = true;
    };
  }, [selectedPolicy?.system_kind]);

  const holidayEventsByDate = useMemo(() => {
    const grouped: Record<string, HolidayCalendarEvent[]> = {};
    const addEvent = (event: HolidayCalendarEvent) => {
      if (!event.isoDate.startsWith(`${year}-`)) return;
      grouped[event.isoDate] = [...(grouped[event.isoDate] ?? []), event];
    };
    holidays.forEach((holiday) => {
      const isoDate = holidayOccurrenceIso(holiday, year);
      addEvent({
        id: `holiday:${holiday.id}:date`,
        kind: 'holiday',
        name: holiday.name,
        isoDate,
        className: holidayTypeClass(holiday),
        holiday,
        recurring: holiday.recurrence === 'yearly',
        source: 'holiday',
      });
      const observedIso = holiday.observed_on ? recurringDateIso(holiday.observed_on, holiday.recurrence, year) : '';
      if (observedIso && observedIso !== isoDate) {
        addEvent({
          id: `holiday:${holiday.id}:observed`,
          kind: 'holiday',
          name: `Перенесення вихідного дня: ${holiday.name}`,
          isoDate: observedIso,
          className: 'non-working',
          holiday,
          recurring: holiday.recurrence === 'yearly',
          source: 'observed',
        });
      }
      const compensatedIso = holiday.compensated_on ? recurringDateIso(holiday.compensated_on, holiday.recurrence, year) : '';
      if (compensatedIso && compensatedIso !== isoDate) {
        addEvent({
          id: `holiday:${holiday.id}:compensated`,
          kind: 'holiday',
          name: `День відпрацювання: ${holiday.name}`,
          isoDate: compensatedIso,
          className: 'compensated',
          holiday,
          recurring: holiday.recurrence === 'yearly',
          source: 'compensated',
        });
      }
    });
    Object.values(grouped).forEach((items) => items.sort((first, second) => first.name.localeCompare(second.name, 'uk')));
    return grouped;
  }, [holidays, year]);

  const birthdayEventsByDate = useMemo(() => {
    const grouped: Record<string, HolidayCalendarEvent[]> = {};
    birthdayEmployees.forEach((employee) => {
      const parts = parseIsoDateParts(employee.birth_date);
      if (!parts) return;
      const monthIndex = parts.month - 1;
      const day = Math.min(parts.day, monthDayCount(year, monthIndex));
      const isoDate = localIsoDate(year, monthIndex, day);
      const name = employeeCalendarName(employee);
      grouped[isoDate] = [
        ...(grouped[isoDate] ?? []),
        {
          id: `birthday:${employee.id}`,
          kind: 'birthday',
          name,
          isoDate,
          className: 'birthday',
          employee,
          recurring: true,
        },
      ];
    });
    Object.values(grouped).forEach((items) => items.sort((first, second) => first.name.localeCompare(second.name, 'uk')));
    return grouped;
  }, [birthdayEmployees, year]);

  const calendarEventsByDate = isBirthdayCalendar ? birthdayEventsByDate : holidayEventsByDate;

  function openCreatePolicy() {
    setPolicyMenuOpenId(null);
    setPolicyDeleteTarget(null);
    setEditingPolicy(null);
    setPolicyForm(emptyHolidayPolicyForm());
    setSaveState('idle');
    setError('');
    setPolicyFormOpen(true);
  }

  function openEditPolicy(policy: HolidayPolicyOption) {
    setPolicyMenuOpenId(null);
    setPolicyDeleteTarget(null);
    setEditingPolicy(policy);
    setPolicyForm(holidayPolicyFormFromItem(policy));
    setSaveState('idle');
    setError('');
    setPolicyFormOpen(true);
  }

  function closePolicyForm() {
    if (saveState === 'loading') return;
    setPolicyFormOpen(false);
    setEditingPolicy(null);
    setPolicyForm(emptyHolidayPolicyForm());
    setSaveState('idle');
  }

  async function savePolicy(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const name = policyForm.name.trim();
    if (!name) return;
    setSaveState('loading');
    setError('');
    try {
      const payload = {
        name,
        country_code: policyForm.country_code,
        is_active: policyForm.is_active,
      };
      const saved = editingPolicy
        ? await api.updateHolidayPolicy(editingPolicy.id, payload)
        : await api.createHolidayPolicy(payload);
      setPolicies((current) => {
        const withoutSaved = current.filter((item) => item.id !== saved.id);
        return [...withoutSaved, saved].sort((first, second) => first.name.localeCompare(second.name, 'uk'));
      });
      setSelectedPolicy((current) => (current?.id === saved.id ? saved : current));
      if (!editingPolicy) setTotal((current) => current + 1);
      closePolicyForm();
    } catch (saveError) {
      setSaveState('error');
      setError(saveError instanceof ApiError ? saveError.message : copy.settings.loadErrorText);
    }
  }

  function requestDeletePolicy(policy: HolidayPolicyOption) {
    setPolicyMenuOpenId(null);
    setPolicyFormOpen(false);
    setPolicyDeleteTarget(policy);
    setSaveState('idle');
    setError('');
  }

  async function deletePolicy(policy: HolidayPolicyOption) {
    setSaveState('loading');
    setError('');
    try {
      await api.deleteHolidayPolicy(policy.id);
      setSelectedPolicy((current) => (current?.id === policy.id ? null : current));
      setPolicyDeleteTarget(null);
      setSaveState('idle');
      await loadPolicies();
    } catch (deleteError) {
      setSaveState('error');
      setError(deleteError instanceof ApiError ? deleteError.message : copy.settings.loadErrorText);
    }
  }

  function openCreateHoliday(dateValue = localIsoDate(year, new Date().getMonth(), 1)) {
    setEditingHoliday(null);
    setHolidayDeleteTarget(null);
    setHolidayForm(emptyHolidayForm(dateValue));
    setSaveState('idle');
    setError('');
    setHolidayFormOpen(true);
  }

  function openEditHoliday(holiday: HolidayOption) {
    setEditingHoliday(holiday);
    setHolidayDeleteTarget(null);
    setHolidayForm(holidayFormFromItem(holiday, year));
    setSaveState('idle');
    setError('');
    setHolidayFormOpen(true);
  }

  function closeHolidayForm() {
    if (saveState === 'loading') return;
    setHolidayFormOpen(false);
    setEditingHoliday(null);
    setHolidayForm(emptyHolidayForm());
    setSaveState('idle');
  }

  async function saveHoliday(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedPolicy || selectedPolicy.is_system || !holidayForm.name.trim() || !holidayForm.occurs_on) return;
    setSaveState('loading');
    setError('');
    try {
      const payload = {
        policy: selectedPolicy.id,
        name: holidayForm.name.trim(),
        occurs_on: holidayForm.occurs_on,
        starts_on: holidayForm.occurs_on,
        ends_on: holidayForm.occurs_on,
        working: holidayForm.working,
        compensated_on: holidayForm.compensated_on || null,
        observed_on: holidayForm.observed_on || null,
        recurrence: holidayForm.recurrence,
        is_active: holidayForm.is_active,
      };
      if (editingHoliday) {
        await api.updateHoliday(editingHoliday.id, payload);
      } else {
        await api.createHoliday(payload);
      }
      closeHolidayForm();
      await loadHolidays(selectedPolicy.id, year);
      await loadPolicies();
    } catch (saveError) {
      setSaveState('error');
      setError(saveError instanceof ApiError ? saveError.message : copy.settings.loadErrorText);
    }
  }

  function requestDeleteHoliday(holiday: HolidayOption) {
    setHolidayFormOpen(false);
    setHolidayDeleteTarget(holiday);
    setSaveState('idle');
    setError('');
  }

  async function deleteHoliday(holiday: HolidayOption) {
    if (!selectedPolicy || selectedPolicy.is_system) return;
    setSaveState('loading');
    setError('');
    try {
      await api.deleteHoliday(holiday.id);
      setHolidayDeleteTarget(null);
      setSaveState('idle');
      await loadHolidays(selectedPolicy.id, year);
      await loadPolicies();
    } catch (deleteError) {
      setSaveState('error');
      setError(deleteError instanceof ApiError ? deleteError.message : copy.settings.loadErrorText);
    }
  }

  function openCalendarEvent(event: HolidayCalendarEvent) {
    if (event.kind === 'birthday' && event.employee) {
      navigate(peopleEmployeePath(event.employee.id));
      return;
    }
    if (event.holiday) {
      openEditHoliday(event.holiday);
    }
  }

  function monthDays(monthIndex: number) {
    const firstDay = new Date(year, monthIndex, 1);
    const prefix = (firstDay.getDay() + 6) % 7;
    const days = Array.from({ length: monthDayCount(year, monthIndex) }, (_, index) => index + 1);
    return [...Array.from({ length: prefix }, () => null), ...days];
  }

  function renderPolicyList() {
    return (
      <main className="settings-page settings-option-page settings-holiday-page">
        <header className="settings-option-header">
          <div>
            <button type="button" className="settings-back-link" onClick={onBack}>
              <ChevronLeft size={17} />
              {copy.common.previous}
            </button>
            <h1>{copy.settings.items['holiday-policies'] ?? 'Політики свят'}</h1>
          </div>
          <div className="settings-option-actions">
            <button type="button" className="primary-action" onClick={openCreatePolicy}>
              <Plus size={18} />
              {copy.settings.add}
            </button>
          </div>
        </header>
        <div className="settings-option-search">
          <Search size={18} />
          <input value={search} placeholder={copy.common.search} onChange={(event) => setSearch(event.target.value)} />
        </div>
        {error ? <p className="error-text settings-option-inline-error">{error}</p> : null}
        <div className="settings-option-meta">{loadState === 'loading' ? copy.common.loading : resultMetaLabel(policies.length, total, copy)}</div>
        <section className="settings-option-table settings-holiday-policy-table">
          {loadState === 'error' ? (
            <EmptyState title={copy.settings.loadErrorTitle} text={error || copy.settings.loadErrorText} />
          ) : policies.length ? (
            <table>
              <thead>
                <tr>
                  <th>{copy.settings.nameColumn}</th>
                  <th>Країна</th>
                  <th>Локації</th>
                  <th>{copy.common.actions}</th>
                </tr>
              </thead>
              <tbody>
                {policies.map((policy) => (
                  <tr key={policy.id} className={`expandable ${policy.is_system ? 'settings-holiday-policy-system' : ''}`}>
                    <td>
                      <button type="button" className="settings-option-name" onClick={() => setSelectedPolicy(policy)}>
                        <span>{policy.name}</span>
                        {policy.is_system ? <em>Система</em> : null}
                        <ChevronRight size={16} />
                      </button>
                    </td>
                    <td>{policy.country_name || policy.country_code || '-'}</td>
                    <td>{policy.is_system ? 'Усі' : policy.location_count}</td>
                    <td>
                      {policy.is_system ? (
                        <span className="settings-option-lock" title={copy.settings.systemItem}>
                          <Lock size={16} />
                        </span>
                      ) : (
                      <div className="settings-option-row-menu">
                        <button
                          type="button"
                          className="row-action"
                          aria-label={copy.common.actions}
                          onClick={(event) => {
                            event.stopPropagation();
                            setPolicyMenuOpenId((current) => (current === policy.id ? null : policy.id));
                          }}
                        >
                          <MoreHorizontal size={16} />
                        </button>
                        {policyMenuOpenId === policy.id ? (
                          <div className="settings-option-row-popover">
                            <button type="button" onClick={() => openEditPolicy(policy)}>
                              {copy.settings.edit}
                            </button>
                            <button type="button" className="danger" onClick={() => requestDeletePolicy(policy)}>
                              {copy.settings.delete}
                            </button>
                          </div>
                        ) : null}
                      </div>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <EmptyState title={copy.settings.noRowsTitle} text={copy.settings.noRowsText} />
          )}
        </section>
        {renderPolicyModal()}
        {policyDeleteTarget ? (
          <SettingsDeleteConfirmModal
            itemName={policyDeleteTarget.name}
            copy={copy}
            loading={saveState === 'loading'}
            onCancel={() => setPolicyDeleteTarget(null)}
            onConfirm={() => void deletePolicy(policyDeleteTarget)}
          />
        ) : null}
      </main>
    );
  }

  function renderPolicyModal() {
    if (!policyFormOpen) return null;
    return (
      <div className="settings-option-modal-layer" role="dialog" aria-modal="true" aria-label={editingPolicy ? 'Редагувати політику свят' : 'Додати політику свят'}>
        <button type="button" className="settings-option-modal-backdrop" aria-label={copy.settings.cancel} onClick={closePolicyForm} />
        <form className="settings-option-modal settings-holiday-policy-modal" onSubmit={savePolicy}>
          <header>
            <strong>{editingPolicy ? 'Редагувати політику свят' : 'Додати політику свят'}</strong>
            <button type="button" className="modal-close" aria-label={copy.settings.cancel} onClick={closePolicyForm}>
              <X size={22} />
            </button>
          </header>
          <label>
            <span>{copy.settings.nameColumn}</span>
            <input value={policyForm.name} onChange={(event) => setPolicyForm((current) => ({ ...current, name: event.target.value }))} autoFocus />
          </label>
          <label>
            <span>Країна</span>
            <select value={policyForm.country_code} onChange={(event) => setPolicyForm((current) => ({ ...current, country_code: event.target.value }))}>
              {holidayCountryOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <label className="settings-option-checkbox">
            <input
              type="checkbox"
              checked={policyForm.is_active}
              onChange={(event) => setPolicyForm((current) => ({ ...current, is_active: event.target.checked }))}
            />
            <span>{copy.settings.activeField}</span>
          </label>
          {error ? <p className="error-text settings-working-error">{error}</p> : null}
          <footer>
            <button type="submit" className="primary-action" disabled={!policyForm.name.trim() || saveState === 'loading'}>
              {copy.settings.save}
            </button>
          </footer>
        </form>
      </div>
    );
  }

  function renderHolidayModal() {
    if (!holidayFormOpen) return null;
    return (
      <div className="settings-option-modal-layer" role="dialog" aria-modal="true" aria-label={editingHoliday ? 'Редагувати свято' : 'Нове свято'}>
        <button type="button" className="settings-option-modal-backdrop" aria-label={copy.settings.cancel} onClick={closeHolidayForm} />
        <form className="settings-option-modal settings-holiday-modal" onSubmit={saveHoliday}>
          <header>
            <strong>{editingHoliday ? 'Редагувати свято' : 'Нове свято'}</strong>
            <button type="button" className="modal-close" aria-label={copy.settings.cancel} onClick={closeHolidayForm}>
              <X size={22} />
            </button>
          </header>
          <label>
            <span>{copy.settings.nameColumn}</span>
            <input value={holidayForm.name} onChange={(event) => setHolidayForm((current) => ({ ...current, name: event.target.value }))} autoFocus />
          </label>
          <label>
            <span>Дата</span>
            <input type="date" value={holidayForm.occurs_on} onChange={(event) => setHolidayForm((current) => ({ ...current, occurs_on: event.target.value }))} />
          </label>
          <div className="settings-holiday-modal-flags">
            <label className="settings-option-checkbox">
              <input
                type="checkbox"
                checked={holidayForm.working}
                onChange={(event) => setHolidayForm((current) => ({ ...current, working: event.target.checked }))}
              />
              <span>Робоче свято</span>
            </label>
            <label className="settings-option-checkbox">
              <input
                type="checkbox"
                checked={Boolean(holidayForm.observed_on)}
                onChange={(event) =>
                  setHolidayForm((current) => ({
                    ...current,
                    observed_on: event.target.checked ? current.observed_on || current.occurs_on : '',
                  }))
                }
              />
              <span>Перенесення вихідного дня</span>
            </label>
            {holidayForm.observed_on ? (
              <label className="settings-holiday-transfer-date">
                <span>Дата перенесеного вихідного</span>
                <input type="date" value={holidayForm.observed_on} onChange={(event) => setHolidayForm((current) => ({ ...current, observed_on: event.target.value }))} />
              </label>
            ) : null}
            <label className="settings-option-checkbox">
              <input
                type="checkbox"
                checked={Boolean(holidayForm.compensated_on)}
                onChange={(event) =>
                  setHolidayForm((current) => ({
                    ...current,
                    compensated_on: event.target.checked ? current.compensated_on || current.occurs_on : '',
                  }))
                }
              />
              <span>Перенесення робочого дня</span>
            </label>
            {holidayForm.compensated_on ? (
              <label className="settings-holiday-transfer-date">
                <span>Дата відпрацювання</span>
                <input type="date" value={holidayForm.compensated_on} onChange={(event) => setHolidayForm((current) => ({ ...current, compensated_on: event.target.value }))} />
              </label>
            ) : null}
            <label className="settings-option-checkbox">
              <input
                type="checkbox"
                checked={holidayForm.recurrence === 'yearly'}
                onChange={(event) => setHolidayForm((current) => ({ ...current, recurrence: event.target.checked ? 'yearly' : 'none' }))}
              />
              <span>Повторювати щороку</span>
            </label>
          </div>
          {editingHoliday ? (
            <div className="settings-holiday-modal-delete">
              <button type="button" className="danger-action" onClick={() => requestDeleteHoliday(editingHoliday)}>
                <Trash2 size={16} />
                {copy.settings.delete}
              </button>
            </div>
          ) : null}
          {error ? <p className="error-text settings-working-error">{error}</p> : null}
          <footer>
            <button type="submit" className="primary-action" disabled={!holidayForm.name.trim() || !holidayForm.occurs_on || saveState === 'loading'}>
              {copy.settings.save}
            </button>
          </footer>
        </form>
      </div>
    );
  }

  function renderCalendar() {
    if (!selectedPolicy) return null;
    const currentDateIso = todayIsoDate();
    const calendarLoadState = isBirthdayCalendar ? birthdayLoadState : holidayLoadState;
    const calendarEventCount = Object.values(calendarEventsByDate).reduce((sum, items) => sum + items.length, 0);
    const holidayCount = holidays.filter((holiday) => holidayOccurrenceIso(holiday, year).startsWith(`${year}-`)).length;
    const countLabel = isBirthdayCalendar ? `Дні народження: ${calendarEventCount}` : `Свята: ${holidayCount}`;
    return (
      <main className="settings-page settings-option-page settings-holiday-page">
        <header className="settings-option-header settings-holiday-detail-header">
          <div>
            <button type="button" className="settings-back-link" onClick={() => setSelectedPolicy(null)}>
              <ChevronLeft size={17} />
              {copy.common.previous}
            </button>
            <h1>
              {selectedPolicy.name} ({year})
            </h1>
          </div>
          <div className="settings-option-actions">
            <div className="settings-holiday-year-nav">
              <button type="button" onClick={() => setYear((current) => current - 1)} aria-label="Попередній рік">
                <ChevronLeft size={17} />
              </button>
              <button type="button" onClick={() => setYear(new Date().getFullYear())}>
                Поточний
              </button>
              <button type="button" onClick={() => setYear((current) => current + 1)} aria-label="Наступний рік">
                <ChevronRight size={17} />
              </button>
            </div>
            {!isBirthdayCalendar ? (
              <button type="button" className="primary-action" onClick={() => openCreateHoliday(todayIsoDate().startsWith(`${year}-`) ? todayIsoDate() : localIsoDate(year, 0, 1))}>
                <Plus size={18} />
                Нове свято
              </button>
            ) : null}
          </div>
        </header>
        {error ? <p className="error-text settings-option-inline-error">{error}</p> : null}
        <div className="settings-option-meta settings-holiday-meta">
          <span>{calendarLoadState === 'loading' ? copy.common.loading : countLabel}</span>
          <div className="settings-holiday-legend" aria-label="Позначення календаря">
            {isBirthdayCalendar ? (
              <span className="birthday">Дні народження</span>
            ) : (
              <>
                <span className="non-working">Неробочі свята</span>
                <span className="working">Робочі свята</span>
                <span className="compensated">Дні відпрацювання</span>
              </>
            )}
          </div>
        </div>
        <section className="settings-holiday-calendar-grid">
          {holidayMonths.map((monthName, monthIndex) => {
            const monthEventDates = Object.entries(calendarEventsByDate).filter(([isoDate]) => {
              const parts = parseIsoDateParts(isoDate);
              return parts?.month === monthIndex + 1;
            });
            const monthEvents = monthEventDates.flatMap(([, items]) => items);
            return (
              <article key={monthName} className="settings-holiday-month">
                <header>
                  <h2>{monthName}</h2>
                </header>
                <div className="settings-holiday-weekdays">
                  {holidayWeekdays.map((weekday) => (
                    <span key={weekday}>{weekday}</span>
                  ))}
                </div>
                <div className="settings-holiday-days">
                  {monthDays(monthIndex).map((day, index) => {
                    if (!day) return <span key={`empty-${index}`} className="empty" />;
                    const isoDate = localIsoDate(year, monthIndex, day);
                    const dayEvents = calendarEventsByDate[isoDate] ?? [];
                    const firstEvent = dayEvents[0];
                    const hasBirthday = dayEvents.some((event) => event.kind === 'birthday');
                    const firstBirthdayMilestone = dayEvents
                      .map((event) => (event.employee ? birthdayMilestoneForEmployee(event.employee, year) : null))
                      .find(Boolean);
                    const title = dayEvents
                      .map((event) => {
                        if (event.kind === 'birthday') {
                          const milestone = event.employee ? birthdayMilestoneForEmployee(event.employee, year) : null;
                          return `${formatHolidayDate(isoDate)} - День народження: ${event.name}${event.employee ? ` · ${birthdayAgeText(event.employee, year)}` : ''}${milestone ? ` · ${milestone.label}` : ''}`;
                        }
                        return `${formatHolidayDate(isoDate)} - ${event.name}${event.recurring ? ' · щороку' : ''}`;
                      })
                      .join('\n');
                    return (
                      <button
                        key={isoDate}
                        type="button"
                        className={`settings-holiday-day ${isBirthdayCalendar ? 'readonly' : ''} ${isoDate === currentDateIso ? 'today' : ''} ${dayEvents.length ? 'marked' : ''} ${firstEvent ? firstEvent.className : ''}`}
                        aria-label={title || formatHolidayDate(isoDate)}
                        data-tooltip={!hasBirthday && title ? title : undefined}
                        onClick={() => {
                          if (firstEvent) {
                            openCalendarEvent(firstEvent);
                          } else if (!isBirthdayCalendar) {
                            openCreateHoliday(isoDate);
                          }
                        }}
                      >
                        <span>{day}</span>
                        {firstBirthdayMilestone ? <BirthdayMilestoneMark milestone={firstBirthdayMilestone} /> : null}
                        {hasBirthday ? <BirthdayTooltip events={dayEvents} year={year} /> : null}
                      </button>
                    );
                  })}
                </div>
                <div className="settings-holiday-month-list" aria-label={`Записи ${monthName}`}>
                  {monthEvents.length ? (
                    monthEventDates.flatMap(([isoDate, items]) =>
                      items.map((event) => {
                        const milestone = event.employee ? birthdayMilestoneForEmployee(event.employee, year) : null;
                        return (
                          <button key={`${isoDate}-${event.id}`} type="button" className={`settings-holiday-event ${event.className}`} onClick={() => openCalendarEvent(event)}>
                            <span className="settings-holiday-event-dot" />
                            <strong>{formatHolidayDate(isoDate)}</strong>
                            <span className="settings-holiday-event-name">{event.name}</span>
                            {milestone ? <BirthdayMilestoneMark milestone={milestone} /> : event.kind === 'birthday' ? null : event.source === 'observed' ? <em>перенесено</em> : event.source === 'compensated' ? <em>відпрацювання</em> : event.recurring ? <em>щороку</em> : null}
                            {event.kind === 'birthday' ? <BirthdayTooltip events={[event]} year={year} /> : null}
                          </button>
                        );
                      }),
                    )
                  ) : (
                    <span className="settings-holiday-empty-month">Немає записів</span>
                  )}
                </div>
              </article>
            );
          })}
        </section>
        {renderHolidayModal()}
        {holidayDeleteTarget ? (
          <SettingsDeleteConfirmModal
            itemName={holidayDeleteTarget.name}
            copy={copy}
            loading={saveState === 'loading'}
            onCancel={() => setHolidayDeleteTarget(null)}
            onConfirm={() => void deleteHoliday(holidayDeleteTarget)}
          />
        ) : null}
      </main>
    );
  }

  return selectedPolicy ? renderCalendar() : renderPolicyList();
}

function SettingsWorkingPatternsView({ onBack, copy }: { onBack: () => void; copy: AppCopy }) {
  const [items, setItems] = useState<WorkingPatternOption[]>([]);
  const [total, setTotal] = useState(0);
  const [loadState, setLoadState] = useState<LoadState>('idle');
  const [saveState, setSaveState] = useState<LoadState>('idle');
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [formOpen, setFormOpen] = useState(false);
  const [editingItem, setEditingItem] = useState<WorkingPatternOption | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<WorkingPatternOption | null>(null);
  const [menuOpenId, setMenuOpenId] = useState<number | null>(null);
  const [exportMenuOpen, setExportMenuOpen] = useState(false);
  const [activeTimeDay, setActiveTimeDay] = useState<WorkingPatternDayKey | null>(null);
  const [form, setForm] = useState<WorkingPatternFormState>(() => emptyWorkingPatternForm());
  const title = copy.settings.items['work-schedules'] ?? 'Графік роботи';
  const searchQuery = search.trim();

  async function loadWorkingPatterns(cancelled?: () => boolean) {
    setLoadState('loading');
    setError('');
    try {
      const result = await api.workingPatterns({ q: searchQuery, page_size: 300 });
      if (cancelled?.()) return;
      setItems(result.items);
      setTotal(result.total);
      setLoadState('ok');
    } catch {
      if (cancelled?.()) return;
      setItems([]);
      setTotal(0);
      setLoadState('error');
      setError(copy.settings.loadErrorText);
    }
  }

  useEffect(() => {
    let cancelled = false;
    void loadWorkingPatterns(() => cancelled);
    return () => {
      cancelled = true;
    };
  }, [copy.settings.loadErrorText, searchQuery]);

  function resetForm() {
    setForm(emptyWorkingPatternForm());
  }

  function openCreateForm() {
    setMenuOpenId(null);
    setExportMenuOpen(false);
    setDeleteTarget(null);
    setEditingItem(null);
    setActiveTimeDay(null);
    resetForm();
    setError('');
    setSaveState('idle');
    setFormOpen(true);
  }

  function openEditForm(item: WorkingPatternOption) {
    setMenuOpenId(null);
    setExportMenuOpen(false);
    setDeleteTarget(null);
    setEditingItem(item);
    setActiveTimeDay(null);
    setForm(workingPatternFormFromItem(item));
    setError('');
    setSaveState('idle');
    setFormOpen(true);
  }

  function closeForm() {
    if (saveState === 'loading') return;
    setFormOpen(false);
    setEditingItem(null);
    setActiveTimeDay(null);
    resetForm();
    setSaveState('idle');
  }

  function requestDelete(item: WorkingPatternOption) {
    setMenuOpenId(null);
    setExportMenuOpen(false);
    setFormOpen(false);
    setDeleteTarget(item);
    setError('');
    setSaveState('idle');
  }

  function closeDeleteConfirm() {
    if (saveState === 'loading') return;
    setDeleteTarget(null);
    setSaveState('idle');
  }

  function updateDay(dayKey: WorkingPatternDayKey, patch: Partial<WorkingPatternDayForm>) {
    setForm((current) => ({
      ...current,
      days: {
        ...current.days,
        [dayKey]: {
          ...current.days[dayKey],
          ...patch,
        },
      },
    }));
  }

  function stepDayHours(dayKey: WorkingPatternDayKey, field: 'break_hours' | 'hours', delta: number) {
    const value = form.days[dayKey][field];
    updateDay(dayKey, { [field]: normalizeHours(value + delta) } as Partial<WorkingPatternDayForm>);
  }

  function applyDayToAll(sourceDayKey: WorkingPatternDayKey) {
    setForm((current) => {
      const sourceDay = current.days[sourceDayKey];
      const days = { ...current.days };
      workingPatternDays.forEach((day) => {
        days[day.key] = {
          ...days[day.key],
          time_range: sourceDay.time_range,
          break_hours: sourceDay.break_hours,
          hours: sourceDay.hours,
        };
      });
      return { ...current, days };
    });
    setActiveTimeDay(null);
  }

  function updateTimeRangePart(dayKey: WorkingPatternDayKey, part: keyof ReturnType<typeof splitWorkingTimeRange>, nextValue: string) {
    const parts = splitWorkingTimeRange(form.days[dayKey].time_range);
    updateDay(dayKey, { time_range: buildWorkingTimeRange({ ...parts, [part]: nextValue }) });
  }

  function renderHourStepper(dayKey: WorkingPatternDayKey, field: 'break_hours' | 'hours', decreaseLabel: string, increaseLabel: string) {
    const value = form.days[dayKey][field];
    return (
      <div className="settings-working-break-control">
        <input
          type="number"
          min="0"
          step={workingPatternHourStep}
          value={value}
          onChange={(event) => updateDay(dayKey, { [field]: normalizeHours(Number(event.target.value)) } as Partial<WorkingPatternDayForm>)}
        />
        <span>год</span>
        <button type="button" onClick={() => stepDayHours(dayKey, field, -workingPatternHourStep)} aria-label={decreaseLabel}>
          -
        </button>
        <button type="button" onClick={() => stepDayHours(dayKey, field, workingPatternHourStep)} aria-label={increaseLabel}>
          +
        </button>
      </div>
    );
  }

  function renderTimePicker(dayKey: WorkingPatternDayKey, value: string) {
    const parts = splitWorkingTimeRange(value);
    const isOpen = activeTimeDay === dayKey;
    return (
      <div className="settings-working-time-picker">
        <button
          type="button"
          className={`settings-working-time-box ${value.trim() ? 'has-value' : ''}`}
          onClick={() => {
            if (!value.trim()) {
              updateDay(dayKey, { time_range: buildWorkingTimeRange(parts) });
            }
            setActiveTimeDay(isOpen ? null : dayKey);
          }}
        >
          {value.trim() ? (
            <span className="settings-working-time-pill">
              <Clock3 size={13} />
              {value}
            </span>
          ) : (
            <span className="settings-working-time-placeholder">ГГ:ХХ - ГГ:ХХ</span>
          )}
        </button>
        {value.trim() ? (
          <button
            type="button"
            className="settings-working-time-clear"
            aria-label="Очистити час"
            onClick={() => {
              updateDay(dayKey, { time_range: '' });
              setActiveTimeDay(null);
            }}
          >
            <X size={14} />
          </button>
        ) : null}
        {isOpen ? (
          <div className="settings-working-time-popover">
            <div className="settings-working-time-preview">
              <span>{parts.startHour}:{parts.startMinute}</span>
              <span>-</span>
              <span>{parts.endHour}:{parts.endMinute}</span>
            </div>
            <div className="settings-working-time-selects">
              <select value={parts.startHour} onChange={(event) => updateTimeRangePart(dayKey, 'startHour', event.target.value)}>
                {workingPatternHourOptions.map((option) => (
                  <option key={`start-hour-${option}`} value={option}>
                    {option}
                  </option>
                ))}
              </select>
              <select value={parts.startMinute} onChange={(event) => updateTimeRangePart(dayKey, 'startMinute', event.target.value)}>
                {workingPatternMinuteOptions.map((option) => (
                  <option key={`start-minute-${option}`} value={option}>
                    {option}
                  </option>
                ))}
              </select>
              <select value={parts.endHour} onChange={(event) => updateTimeRangePart(dayKey, 'endHour', event.target.value)}>
                {workingPatternHourOptions.map((option) => (
                  <option key={`end-hour-${option}`} value={option}>
                    {option}
                  </option>
                ))}
              </select>
              <select value={parts.endMinute} onChange={(event) => updateTimeRangePart(dayKey, 'endMinute', event.target.value)}>
                {workingPatternMinuteOptions.map((option) => (
                  <option key={`end-minute-${option}`} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            </div>
          </div>
        ) : null}
      </div>
    );
  }

  function workingHoursForDay(day: WorkingPatternDayForm) {
    if (!form.uses_time_range) return normalizeHours(day.hours);
    return parseTimeRangeHours(day.time_range, day.break_hours) ?? normalizeHours(day.hours);
  }

  function totalHoursForPattern(item: WorkingPatternOption) {
    return workingPatternDays.reduce((sum, day) => sum + numberFromApi(item[day.field]), 0);
  }

  function totalFormHours() {
    return workingPatternDays.reduce((sum, day) => sum + workingHoursForDay(form.days[day.key]), 0);
  }

  async function saveWorkingPattern(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!form.name.trim()) return;
    setSaveState('loading');
    setError('');
    try {
      const payload = workingPatternPayloadFromForm(form);
      const saved = editingItem ? await api.updateWorkingPattern(editingItem.id, payload) : await api.createWorkingPattern(payload);
      setItems((current) => {
        const withoutSaved = current.filter((item) => item.id !== saved.id);
        return [...withoutSaved, saved].sort((first, second) => first.name.localeCompare(second.name, 'uk'));
      });
      if (!editingItem) setTotal((current) => current + 1);
      closeForm();
    } catch (saveError) {
      setSaveState('error');
      setError(saveError instanceof ApiError ? saveError.message : copy.settings.loadErrorText);
    }
  }

  async function deleteWorkingPattern(item: WorkingPatternOption) {
    setMenuOpenId(null);
    setSaveState('loading');
    setError('');
    try {
      await api.deleteWorkingPattern(item.id);
      await loadWorkingPatterns();
      setDeleteTarget(null);
      setSaveState('idle');
    } catch (deleteError) {
      setSaveState('error');
      setError(deleteError instanceof ApiError ? deleteError.message : copy.settings.loadErrorText);
    }
  }

  function exportWorkingPatterns(format: SettingsExportFormat) {
    setExportMenuOpen(false);
    const headers = [
      copy.settings.nameColumn,
      'Пн',
      'Вт',
      'Ср',
      'Чт',
      'Пт',
      'Сб',
      'Нд',
      'Всього',
    ];
    const rows = items.map((item) => [
      item.name,
      ...workingPatternDays.map((day) => formatWorkingHours(numberFromApi(item[day.field]))),
      formatWorkingHours(totalHoursForPattern(item)),
    ]);
    const exportRows: Array<Array<string | number>> = [headers, ...rows];
    if (format === 'csv') {
      const csv = exportRows.map((row) => row.map(csvCell).join(';')).join('\n');
      downloadTextFile('working-patterns.csv', `\uFEFF${csv}`, 'text/csv;charset=utf-8');
      return;
    }
    downloadBinaryFile(
      'working-patterns.xlsx',
      buildXlsx(exportRows, title),
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    );
  }

  return (
    <main className="settings-page settings-option-page settings-working-page">
      <header className="settings-option-header">
        <div>
          <button type="button" className="settings-back-link" onClick={onBack}>
            <ChevronLeft size={17} />
            {copy.common.previous}
          </button>
          <h1>{title}</h1>
        </div>
        <div className="settings-option-actions">
          <div className="settings-option-export">
            <button
              type="button"
              className={`toolbar-icon ${exportMenuOpen ? 'active' : ''}`}
              aria-label={copy.common.export}
              aria-expanded={exportMenuOpen}
              onClick={() => {
                setMenuOpenId(null);
                setExportMenuOpen((current) => !current);
              }}
            >
              <MoreHorizontal size={18} />
            </button>
            {exportMenuOpen ? (
              <div className="settings-option-export-menu">
                <button type="button" onClick={() => exportWorkingPatterns('xlsx')}>
                  {copy.settings.exportXlsx}
                </button>
                <button type="button" onClick={() => exportWorkingPatterns('csv')}>
                  {copy.settings.exportCsv}
                </button>
              </div>
            ) : null}
          </div>
          <button type="button" className="primary-action" onClick={openCreateForm}>
            <Plus size={18} />
            {copy.settings.add}
          </button>
        </div>
      </header>

      <div className="settings-option-search">
        <Search size={18} />
        <input value={search} placeholder={copy.common.search} onChange={(event) => setSearch(event.target.value)} />
      </div>

      {formOpen ? (
        <div className="settings-option-modal-layer" role="dialog" aria-modal="true" aria-label={editingItem ? 'Редагувати графік роботи' : 'Додати графік роботи'}>
          <button type="button" className="settings-option-modal-backdrop" aria-label={copy.settings.cancel} onClick={closeForm} />
          <form className="settings-option-modal settings-working-modal" onSubmit={saveWorkingPattern}>
            <header>
              <strong>{editingItem ? 'Редагувати графік роботи' : 'Додати графік роботи'}</strong>
              <button type="button" className="modal-close" aria-label={copy.settings.cancel} onClick={closeForm}>
                <X size={22} />
              </button>
            </header>
            <label className="settings-working-name">
              <span>{copy.settings.nameColumn}</span>
              <input value={form.name} onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))} autoFocus />
            </label>
            <section className="settings-working-schedule">
              <div className="settings-working-schedule-head">
                <strong>{title}</strong>
                <label className="settings-working-toggle">
                  <span>Час початку та закінчення робочого дня</span>
                  <span className="settings-switch">
                    <input
                      type="checkbox"
                      checked={form.uses_time_range}
                      onChange={(event) => setForm((current) => ({ ...current, uses_time_range: event.target.checked }))}
                    />
                    <span />
                  </span>
                </label>
              </div>
              <table className={`settings-working-schedule-table ${form.uses_time_range ? 'time-mode' : 'hours-mode'}`}>
                <thead>
                  {form.uses_time_range ? (
                    <tr>
                      <th>День тижня</th>
                      <th>Час початку-закінчення</th>
                      <th>Години перерв</th>
                      <th>Робочі години</th>
                    </tr>
                  ) : (
                    <tr>
                      <th>День тижня</th>
                      <th>Години перерв</th>
                      <th>Робочі години</th>
                    </tr>
                  )}
                </thead>
                <tbody>
                  {workingPatternDays.map((day) => {
                    const value = form.days[day.key];
                    const computedHours = workingHoursForDay(value);
                    return (
                      <tr key={day.key}>
                        <td>
                          <div className="settings-working-day-cell">
                            <span>{day.label}</span>
                            <button type="button" className="settings-working-apply-all" onClick={() => applyDayToAll(day.key)}>
                              Застосувати до всіх
                            </button>
                          </div>
                        </td>
                        {form.uses_time_range ? <td>{renderTimePicker(day.key, value.time_range)}</td> : null}
                        <td>
                          {renderHourStepper(day.key, 'break_hours', 'Зменшити перерву', 'Збільшити перерву')}
                        </td>
                        <td>
                          {form.uses_time_range
                            ? formatWorkingHoursLabel(computedHours, true)
                            : renderHourStepper(day.key, 'hours', 'Зменшити робочі години', 'Збільшити робочі години')}
                        </td>
                      </tr>
                    );
                  })}
                  <tr className="settings-working-total-row">
                    <td>Всього</td>
                    {form.uses_time_range ? <td /> : null}
                    <td>-</td>
                    <td>{formatWorkingHoursLabel(totalFormHours(), true)}</td>
                  </tr>
                </tbody>
              </table>
            </section>
            {error ? <p className="error-text settings-working-error">{error}</p> : null}
            <footer>
              <button type="submit" className="primary-action" disabled={!form.name.trim() || saveState === 'loading'}>
                {copy.settings.save}
              </button>
            </footer>
          </form>
        </div>
      ) : null}

      {deleteTarget ? (
        <SettingsDeleteConfirmModal
          itemName={deleteTarget.name}
          copy={copy}
          loading={saveState === 'loading'}
          onCancel={closeDeleteConfirm}
          onConfirm={() => void deleteWorkingPattern(deleteTarget)}
        />
      ) : null}

      {error && !formOpen ? <p className="error-text settings-option-inline-error">{error}</p> : null}
      <div className="settings-option-meta">{loadState === 'loading' ? copy.common.loading : resultMetaLabel(items.length, total, copy)}</div>

      <section className="settings-option-table settings-working-table">
        {loadState === 'error' ? (
          <EmptyState title={copy.settings.loadErrorTitle} text={error || copy.settings.loadErrorText} />
        ) : items.length ? (
          <table>
            <thead>
              <tr>
                <th>{copy.settings.nameColumn}</th>
                <th>Всього</th>
                <th>{copy.common.actions}</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id} className={!item.is_active ? 'muted' : ''}>
                  <td>
                    <div className="settings-working-row-title">
                      <span>{item.name}</span>
                    </div>
                  </td>
                  <td>{formatWorkingHours(totalHoursForPattern(item))}</td>
                  <td>
                    <div className="settings-option-row-menu">
                      <button
                        type="button"
                        className="row-action"
                        aria-label={copy.common.actions}
                        onClick={(event) => {
                          event.stopPropagation();
                          setMenuOpenId((current) => (current === item.id ? null : item.id));
                        }}
                      >
                        <MoreHorizontal size={16} />
                      </button>
                      {menuOpenId === item.id ? (
                        <div className="settings-option-row-popover">
                          <button type="button" onClick={() => openEditForm(item)}>
                            {copy.settings.edit}
                          </button>
                          <button type="button" className="danger" onClick={() => requestDelete(item)}>
                            {copy.settings.delete}
                          </button>
                        </div>
                      ) : null}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <EmptyState title={copy.settings.noRowsTitle} text={copy.settings.noRowsText} />
        )}
      </section>
    </main>
  );
}

function SettingsLocationsView({ onBack, copy }: { onBack: () => void; copy: AppCopy }) {
  const navigate = useNavigate();
  const [items, setItems] = useState<ClinicLocation[]>([]);
  const [total, setTotal] = useState(0);
  const [loadState, setLoadState] = useState<LoadState>('idle');
  const [saveState, setSaveState] = useState<LoadState>('idle');
  const [error, setError] = useState('');
  const [editingItem, setEditingItem] = useState<ClinicLocation | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<ClinicLocation | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const [menuOpenId, setMenuOpenId] = useState<number | null>(null);
  const [exportMenuOpen, setExportMenuOpen] = useState(false);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [expandedEmployees, setExpandedEmployees] = useState<Record<number, EmployeeListItem[]>>({});
  const [expandedLoadingId, setExpandedLoadingId] = useState<number | null>(null);
  const [form, setForm] = useState<LocationFormState>({
    name: '',
    country_code: 'UA',
    address: '',
    holiday_policy_id: '',
    holiday_policy_name: '',
    time_zone: 'Kyiv',
    is_active: true,
  });
  const title = copy.settings.items.locations ?? 'Локації';

  async function loadLocations(cancelled?: () => boolean) {
    setLoadState('loading');
    setError('');
    try {
      const result = await api.locations({ page_size: 300 });
      if (cancelled?.()) return;
      setItems(result.items);
      setTotal(result.total);
      setLoadState('ok');
    } catch {
      if (cancelled?.()) return;
      setItems([]);
      setTotal(0);
      setLoadState('error');
      setError(copy.settings.loadErrorText);
    }
  }

  useEffect(() => {
    let cancelled = false;
    void loadLocations(() => cancelled);
    return () => {
      cancelled = true;
    };
  }, [copy.settings.loadErrorText]);

  function resetForm() {
    setForm({
      name: '',
      country_code: 'UA',
      address: '',
      holiday_policy_id: '',
      holiday_policy_name: '',
      time_zone: 'Kyiv',
      is_active: true,
    });
  }

  function openCreateForm() {
    setMenuOpenId(null);
    setExportMenuOpen(false);
    setDeleteTarget(null);
    setEditingItem(null);
    resetForm();
    setSaveState('idle');
    setError('');
    setFormOpen(true);
  }

  function openEditForm(item: ClinicLocation) {
    setMenuOpenId(null);
    setExportMenuOpen(false);
    setDeleteTarget(null);
    setEditingItem(item);
    setForm({
      name: item.name,
      country_code: item.country_code || 'UA',
      address: item.address || '',
      holiday_policy_id: item.holiday_policy_id || '',
      holiday_policy_name: item.holiday_policy_name || '',
      time_zone: item.time_zone || 'Kyiv',
      is_active: item.is_active,
    });
    setSaveState('idle');
    setError('');
    setFormOpen(true);
  }

  function closeForm() {
    setFormOpen(false);
    setEditingItem(null);
    resetForm();
    setSaveState('idle');
  }

  function requestDeleteLocation(item: ClinicLocation) {
    setMenuOpenId(null);
    setExportMenuOpen(false);
    setFormOpen(false);
    setDeleteTarget(item);
    setSaveState('idle');
    setError('');
  }

  function closeDeleteConfirm() {
    if (saveState === 'loading') return;
    setDeleteTarget(null);
    setSaveState('idle');
  }

  async function saveLocation(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const name = form.name.trim();
    if (!name) return;
    setSaveState('loading');
    setError('');
    const payload = {
      ...form,
      name,
      country_code: form.country_code.trim(),
      address: form.address.trim(),
      holiday_policy_id: form.holiday_policy_id.trim(),
      holiday_policy_name: form.holiday_policy_name.trim(),
      time_zone: form.time_zone.trim() || 'Kyiv',
    };
    try {
      const saved = editingItem ? await api.updateLocation(editingItem.id, payload) : await api.createLocation(payload);
      setItems((current) => {
        const withoutSaved = current.filter((item) => item.id !== saved.id);
        return [...withoutSaved, saved].sort((first, second) => first.name.localeCompare(second.name, 'uk'));
      });
      if (!editingItem) setTotal((current) => current + 1);
      closeForm();
    } catch (saveError) {
      setSaveState('error');
      setError(saveError instanceof ApiError ? saveError.message : copy.settings.loadErrorText);
    }
  }

  async function deleteLocation(item: ClinicLocation) {
    setMenuOpenId(null);
    setSaveState('loading');
    setError('');
    try {
      await api.deleteLocation(item.id);
      await loadLocations();
      setDeleteTarget(null);
      setSaveState('idle');
    } catch (deleteError) {
      setSaveState('error');
      setError(deleteError instanceof ApiError ? deleteError.message : copy.settings.loadErrorText);
    }
  }

  async function toggleEmployees(item: ClinicLocation) {
    setMenuOpenId(null);
    setExportMenuOpen(false);
    setExpandedId((current) => (current === item.id ? null : item.id));
    if (expandedId === item.id || expandedEmployees[item.id]) return;
    setExpandedLoadingId(item.id);
    try {
      const result = await api.employees({ status: 'active', clinic: item.id, compact: true, page_size: 300 });
      setExpandedEmployees((current) => ({ ...current, [item.id]: result.items }));
    } catch {
      setExpandedEmployees((current) => ({ ...current, [item.id]: [] }));
    } finally {
      setExpandedLoadingId((current) => (current === item.id ? null : current));
    }
  }

  function locationEmployeeFullName(employee: EmployeeListItem) {
    return employee.full_name || `${employee.last_name} ${employee.first_name}`.trim();
  }

  async function loadEmployeesForLocation(item: ClinicLocation, page = 1, pageSize = 500) {
    return api.employees({ status: 'active', clinic: item.id, compact: true, page, page_size: pageSize });
  }

  async function loadAllEmployeesForLocation(item: ClinicLocation) {
    if (!item.employee_count) return [];
    const employees: EmployeeListItem[] = [];
    let page = 1;
    for (let guard = 0; guard < 20; guard += 1) {
      const result = await loadEmployeesForLocation(item, page, 500);
      employees.push(...result.items);
      if (!result.next || employees.length >= result.total) break;
      page += 1;
    }
    return employees;
  }

  async function employeeExportRowsForLocations() {
    const rows: Array<Array<string | number>> = [];
    for (const item of items) {
      const cached = expandedEmployees[item.id];
      const employees = cached && cached.length >= item.employee_count ? cached : await loadAllEmployeesForLocation(item);
      employees.forEach((employee) => {
        rows.push([item.name, locationEmployeeFullName(employee), employee.status || '']);
      });
    }
    return rows;
  }

  async function exportLocations(format: SettingsExportFormat) {
    setExportMenuOpen(false);
    const headers = [copy.settings.nameColumn, 'Країна', 'Адреса', 'Політика свят', 'Часовий пояс', copy.settings.peopleColumn];
    const rows = items.map((item) => [
      item.name,
      item.country_name || item.country_code,
      item.address,
      item.holiday_policy_name,
      item.time_zone,
      item.employee_count,
    ]);
    const employeeRows = await employeeExportRowsForLocations();
    const exportRows: Array<Array<string | number>> = [headers, ...rows];
    if (employeeRows.length) {
      exportRows.push([], [copy.settings.peopleColumn], [copy.settings.nameColumn, copy.settings.peopleColumn, copy.people.status ?? 'Status'], ...employeeRows);
    }
    if (format === 'csv') {
      const csv = exportRows.map((row) => row.map(csvCell).join(';')).join('\n');
      downloadTextFile('locations.csv', `\uFEFF${csv}`, 'text/csv;charset=utf-8');
      return;
    }
    downloadBinaryFile('locations.xlsx', buildXlsx(exportRows, title), 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet');
  }

  function openEmployee(employee: EmployeeListItem) {
    navigate(peopleEmployeePath(employee.id));
  }

  return (
    <main className="settings-page settings-option-page">
      <header className="settings-option-header">
        <div>
          <button type="button" className="settings-back-link" onClick={onBack}>
            <ChevronLeft size={17} />
            {copy.common.previous}
          </button>
          <h1>{title}</h1>
        </div>
        <div className="settings-option-actions">
          <div className="settings-option-export">
            <button
              type="button"
              className={`toolbar-icon ${exportMenuOpen ? 'active' : ''}`}
              aria-label={copy.common.export}
              aria-expanded={exportMenuOpen}
              onClick={() => {
                setMenuOpenId(null);
                setExportMenuOpen((current) => !current);
              }}
            >
              <MoreHorizontal size={18} />
            </button>
            {exportMenuOpen ? (
              <div className="settings-option-export-menu">
                <button type="button" onClick={() => void exportLocations('xlsx')}>
                  {copy.settings.exportXlsx}
                </button>
                <button type="button" onClick={() => void exportLocations('csv')}>
                  {copy.settings.exportCsv}
                </button>
              </div>
            ) : null}
          </div>
          <button type="button" className="primary-action" onClick={openCreateForm}>
            <Plus size={18} />
            {copy.settings.add}
          </button>
        </div>
      </header>

      {formOpen ? (
        <div className="settings-option-modal-layer" role="dialog" aria-modal="true" aria-label={editingItem ? 'Редагувати локацію' : 'Додати локацію'}>
          <button type="button" className="settings-option-modal-backdrop" aria-label={copy.settings.cancel} onClick={closeForm} />
          <form className="settings-option-modal settings-location-modal" onSubmit={saveLocation}>
            <header>
              <strong>{editingItem ? 'Редагувати локацію' : 'Додати локацію'}</strong>
              <button type="button" className="modal-close" aria-label={copy.settings.cancel} onClick={closeForm}>
                <X size={22} />
              </button>
            </header>
            <label>
              <span>{copy.settings.nameColumn}</span>
              <input value={form.name} onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))} autoFocus />
            </label>
            <label>
              <span>Країна <em>За бажанням</em></span>
              <select value={form.country_code} onChange={(event) => setForm((current) => ({ ...current, country_code: event.target.value }))}>
                <option value="">-- Немає --</option>
                <option value="UA">Україна</option>
                <option value="PL">Polska</option>
              </select>
            </label>
            <label>
              <span>Адреса <em>За бажанням</em></span>
              <input value={form.address} onChange={(event) => setForm((current) => ({ ...current, address: event.target.value }))} />
            </label>
            <label>
              <span>Політика свят</span>
              <select
                value={form.holiday_policy_id || form.holiday_policy_name}
                onChange={(event) => {
                  const value = event.target.value;
                  setForm((current) => ({
                    ...current,
                    holiday_policy_id: value === '15490' ? '15490' : '',
                    holiday_policy_name: value === '15490' ? 'Vidnova' : '',
                  }));
                }}
              >
                <option value="">-- Немає --</option>
                <option value="15490">Vidnova</option>
              </select>
            </label>
            <label>
              <span>Часовий пояс</span>
              <select value={form.time_zone} onChange={(event) => setForm((current) => ({ ...current, time_zone: event.target.value }))}>
                <option value="Kyiv">(GMT+02:00) Kyiv</option>
                <option value="UTC">(GMT+00:00) UTC</option>
              </select>
            </label>
            <label className="settings-option-checkbox">
              <input
                type="checkbox"
                checked={form.is_active}
                onChange={(event) => setForm((current) => ({ ...current, is_active: event.target.checked }))}
              />
              <span>{copy.settings.activeField}</span>
            </label>
            <footer>
              <button type="submit" className="primary-action" disabled={!form.name.trim() || saveState === 'loading'}>
                {copy.settings.save}
              </button>
            </footer>
          </form>
        </div>
      ) : null}

      {deleteTarget ? (
        <SettingsDeleteConfirmModal
          itemName={deleteTarget.name}
          copy={copy}
          loading={saveState === 'loading'}
          onCancel={closeDeleteConfirm}
          onConfirm={() => void deleteLocation(deleteTarget)}
        />
      ) : null}

      <div className="settings-option-meta">{loadState === 'loading' ? copy.common.loading : resultMetaLabel(items.length, total, copy)}</div>

      <section className="settings-option-table settings-location-table">
        {loadState === 'error' ? (
          <EmptyState title={copy.settings.loadErrorTitle} text={error || copy.settings.loadErrorText} />
        ) : items.length ? (
          <table>
            <thead>
              <tr>
                <th>{copy.settings.nameColumn}</th>
                <th>Країна</th>
                <th>Політика свят</th>
                <th>{copy.settings.peopleColumn}</th>
                <th>{copy.common.actions}</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => {
                const isExpanded = expandedId === item.id;
                const people = expandedEmployees[item.id] ?? [];
                return (
                  <Fragment key={item.id}>
                    <tr className={`expandable ${!item.is_active ? 'muted' : ''} ${isExpanded ? 'expanded' : ''}`} onClick={() => void toggleEmployees(item)}>
                      <td>
                        <button
                          type="button"
                          className="settings-option-name"
                          onClick={(event) => {
                            event.stopPropagation();
                            void toggleEmployees(item);
                          }}
                        >
                          <span>{item.name}</span>
                          {!item.is_active ? <em>{copy.settings.inactive}</em> : null}
                          {isExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                        </button>
                      </td>
                      <td>{item.country_name || item.country_code}</td>
                      <td>{item.holiday_policy_name}</td>
                      <td>{item.employee_count}</td>
                      <td>
                        <div className="settings-option-row-menu">
                          <button
                            type="button"
                            className="row-action"
                            aria-label={copy.common.actions}
                            onClick={(event) => {
                              event.stopPropagation();
                              setMenuOpenId((current) => (current === item.id ? null : item.id));
                            }}
                          >
                            <MoreHorizontal size={16} />
                          </button>
                          {menuOpenId === item.id ? (
                            <div className="settings-option-row-popover">
                              <button
                                type="button"
                                onClick={(event) => {
                                  event.stopPropagation();
                                  openEditForm(item);
                                }}
                              >
                                {copy.settings.edit}
                              </button>
                              <button
                                type="button"
                                  className="danger"
                                  onClick={(event) => {
                                    event.stopPropagation();
                                    requestDeleteLocation(item);
                                  }}
                                >
                                {copy.settings.delete}
                              </button>
                            </div>
                          ) : null}
                        </div>
                      </td>
                    </tr>
                    {isExpanded ? (
                      <tr className="settings-option-people-row">
                        <td colSpan={5}>
                          <div className="settings-option-people-list">
                            {expandedLoadingId === item.id ? (
                              <span className="settings-option-people-loading">{copy.common.loading}</span>
                            ) : people.length ? (
                              people.map((employee, index) => {
                                const fullName = employee.full_name || `${employee.last_name} ${employee.first_name}`.trim();
                                return (
                                  <button key={employee.id} type="button" className="settings-option-person" onClick={() => openEmployee(employee)}>
                                    <Avatar
                                      name={fullName}
                                      src={employeeAvatarUrl(employee)}
                                      accent={employeeAccentClasses[index % employeeAccentClasses.length]}
                                      size="sm"
                                    />
                                    <span>{fullName}</span>
                                  </button>
                                );
                              })
                            ) : (
                              <span className="settings-option-people-empty">{copy.people.employeesNotFound}</span>
                            )}
                          </div>
                        </td>
                      </tr>
                    ) : null}
                  </Fragment>
                );
              })}
            </tbody>
          </table>
        ) : (
          <EmptyState title={copy.settings.noRowsTitle} text={copy.settings.noRowsText} />
        )}
      </section>
    </main>
  );
}

type DepartmentTab = 'structure' | 'fields' | 'levels';
type DepartmentFormState = {
  name: string;
  parent: string;
  manager: string;
  level: string;
  is_active: boolean;
};
type DepartmentLevelFormState = {
  name: string;
  color: string;
  is_active: boolean;
};
type DepartmentCustomField = {
  id: number;
  name: string;
  type: string;
  description: string;
  enabled: boolean;
  system?: boolean;
  required?: boolean;
};
type DepartmentDeleteTarget =
  | { kind: 'department'; item: DepartmentOption }
  | { kind: 'level'; item: DepartmentLevelOption };

const departmentLevelColors = [
  '#60a5fa',
  '#34d399',
  '#f59e0b',
  '#facc15',
  '#fb7185',
  '#a78bfa',
  '#94a3b8',
  '#2dd4bf',
  '#38bdf8',
  '#c084fc',
  '#f97316',
  '#64748b',
];

const departmentSystemFields: DepartmentCustomField[] = [
  { id: 1, name: 'Назва', type: 'Система', description: '', enabled: true, system: true, required: true },
  { id: 2, name: 'Батьківський департамент', type: 'Система', description: '', enabled: true, system: true },
  { id: 3, name: 'Менеджер', type: 'Система', description: '', enabled: true, system: true },
  { id: 4, name: 'Рівень', type: 'Система', description: '', enabled: true, system: true },
];

function SettingsDepartmentsView({ onBack, copy }: { onBack: () => void; copy: AppCopy }) {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<DepartmentTab>('structure');
  const [departments, setDepartments] = useState<DepartmentOption[]>([]);
  const [levels, setLevels] = useState<DepartmentLevelOption[]>([]);
  const [employees, setEmployees] = useState<EmployeeListItem[]>([]);
  const [customFields, setCustomFields] = useState<DepartmentCustomField[]>([]);
  const [loadState, setLoadState] = useState<LoadState>('idle');
  const [saveState, setSaveState] = useState<LoadState>('idle');
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [expandedIds, setExpandedIds] = useState<Set<number>>(new Set());
  const [expandedPeopleId, setExpandedPeopleId] = useState<number | null>(null);
  const [expandedEmployees, setExpandedEmployees] = useState<Record<number, EmployeeListItem[]>>({});
  const [expandedPeopleLoadingId, setExpandedPeopleLoadingId] = useState<number | null>(null);
  const [departmentFormOpen, setDepartmentFormOpen] = useState(false);
  const [levelFormOpen, setLevelFormOpen] = useState(false);
  const [fieldFormOpen, setFieldFormOpen] = useState(false);
  const [editingDepartment, setEditingDepartment] = useState<DepartmentOption | null>(null);
  const [editingLevel, setEditingLevel] = useState<DepartmentLevelOption | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<DepartmentDeleteTarget | null>(null);
  const [menuOpen, setMenuOpen] = useState<string | null>(null);
  const [exportMenuOpen, setExportMenuOpen] = useState(false);
  const [departmentForm, setDepartmentForm] = useState<DepartmentFormState>({
    name: '',
    parent: '',
    manager: '',
    level: '',
    is_active: true,
  });
  const [levelForm, setLevelForm] = useState<DepartmentLevelFormState>({
    name: '',
    color: '#94a3b8',
    is_active: true,
  });
  const [fieldForm, setFieldForm] = useState({ name: '', type: 'Текст в один рядок', description: '' });
  const allFields = [...departmentSystemFields, ...customFields];
  const visibleDepartments = useMemo(() => buildDepartmentTreeRows(departments, expandedIds, search), [departments, expandedIds, search]);
  const managerOptions = employees
    .filter((employee) => employee.status === 'active')
    .sort((first, second) => departmentEmployeeName(first).localeCompare(departmentEmployeeName(second), 'uk'));

  async function loadDepartments(cancelled?: () => boolean) {
    setLoadState('loading');
    setError('');
    try {
      const [departmentResult, levelResult, employeeResult] = await Promise.all([
        api.departments({ page_size: 500 }),
        api.departmentLevels({ page_size: 200 }),
        api.employees({ status: 'active', compact: true, page_size: 500 }),
      ]);
      if (cancelled?.()) return;
      setDepartments(departmentResult.items);
      setLevels(levelResult.items);
      setEmployees(employeeResult.items);
      setExpandedIds(new Set(departmentResult.items.filter((department) => department.children_count > 0).map((department) => department.id)));
      setLoadState('ok');
    } catch {
      if (cancelled?.()) return;
      setLoadState('error');
      setError(copy.settings.loadErrorText);
    }
  }

  useEffect(() => {
    let cancelled = false;
    void loadDepartments(() => cancelled);
    return () => {
      cancelled = true;
    };
  }, [copy.settings.loadErrorText]);

  function resetDepartmentForm() {
    setDepartmentForm({ name: '', parent: '', manager: '', level: '', is_active: true });
  }

  function openCreateDepartment() {
    setMenuOpen(null);
    setExportMenuOpen(false);
    setDeleteTarget(null);
    setEditingDepartment(null);
    resetDepartmentForm();
    setSaveState('idle');
    setError('');
    setDepartmentFormOpen(true);
  }

  function openEditDepartment(item: DepartmentOption) {
    setMenuOpen(null);
    setExportMenuOpen(false);
    setDeleteTarget(null);
    setEditingDepartment(item);
    setDepartmentForm({
      name: item.name,
      parent: item.parent ? String(item.parent) : '',
      manager: item.manager ? String(item.manager) : '',
      level: item.level ? String(item.level) : '',
      is_active: item.is_active,
    });
    setSaveState('idle');
    setError('');
    setDepartmentFormOpen(true);
  }

  function closeDepartmentForm() {
    setDepartmentFormOpen(false);
    setEditingDepartment(null);
    resetDepartmentForm();
    setSaveState('idle');
  }

  async function saveDepartment(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const name = departmentForm.name.trim();
    if (!name) return;
    setSaveState('loading');
    setError('');
    const payload = {
      name,
      parent: departmentForm.parent ? Number(departmentForm.parent) : null,
      manager: departmentForm.manager ? Number(departmentForm.manager) : null,
      level: departmentForm.level ? Number(departmentForm.level) : null,
      is_active: departmentForm.is_active,
    };
    try {
      const saved = editingDepartment
        ? await api.updateDepartment(editingDepartment.id, payload)
        : await api.createDepartment(payload);
      setDepartments((current) => {
        const next = current.filter((item) => item.id !== saved.id);
        return [...next, saved].sort((first, second) => first.name.localeCompare(second.name, 'uk'));
      });
      closeDepartmentForm();
      await loadDepartments();
    } catch (saveError) {
      setSaveState('error');
      setError(saveError instanceof ApiError ? saveError.message : copy.settings.loadErrorText);
    }
  }

  function openCreateLevel() {
    setMenuOpen(null);
    setExportMenuOpen(false);
    setDeleteTarget(null);
    setEditingLevel(null);
    setLevelForm({ name: '', color: '#94a3b8', is_active: true });
    setSaveState('idle');
    setError('');
    setLevelFormOpen(true);
  }

  function openEditLevel(item: DepartmentLevelOption) {
    setMenuOpen(null);
    setExportMenuOpen(false);
    setDeleteTarget(null);
    setEditingLevel(item);
    setLevelForm({ name: item.name, color: item.color || '#94a3b8', is_active: item.is_active });
    setSaveState('idle');
    setError('');
    setLevelFormOpen(true);
  }

  function closeLevelForm() {
    setLevelFormOpen(false);
    setEditingLevel(null);
    setLevelForm({ name: '', color: '#94a3b8', is_active: true });
    setSaveState('idle');
  }

  async function saveLevel(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const name = levelForm.name.trim();
    if (!name) return;
    setSaveState('loading');
    setError('');
    const payload = { name, color: levelForm.color, is_active: levelForm.is_active };
    try {
      const saved = editingLevel
        ? await api.updateDepartmentLevel(editingLevel.id, payload)
        : await api.createDepartmentLevel(payload);
      setLevels((current) => {
        const next = current.filter((item) => item.id !== saved.id);
        return [...next, saved].sort((first, second) => first.name.localeCompare(second.name, 'uk'));
      });
      closeLevelForm();
      await loadDepartments();
    } catch (saveError) {
      setSaveState('error');
      setError(saveError instanceof ApiError ? saveError.message : copy.settings.loadErrorText);
    }
  }

  function openFieldForm() {
    setFieldForm({ name: '', type: 'Текст в один рядок', description: '' });
    setFieldFormOpen(true);
  }

  function saveField(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const name = fieldForm.name.trim();
    if (!name) return;
    setCustomFields((current) => [
      ...current,
      {
        id: Date.now(),
        name,
        type: fieldForm.type,
        description: fieldForm.description.trim(),
        enabled: true,
      },
    ]);
    setFieldFormOpen(false);
  }

  function toggleTree(item: DepartmentOption) {
    setExpandedIds((current) => {
      const next = new Set(current);
      if (next.has(item.id)) {
        next.delete(item.id);
      } else {
        next.add(item.id);
      }
      return next;
    });
  }

  async function toggleDepartmentPeople(item: DepartmentOption) {
    setMenuOpen(null);
    setExportMenuOpen(false);
    setExpandedPeopleId((current) => (current === item.id ? null : item.id));
    if (expandedPeopleId === item.id || expandedEmployees[item.id]) return;
    setExpandedPeopleLoadingId(item.id);
    try {
      const result = await api.employees({ status: 'active', department: item.id, compact: true, page_size: 500 });
      setExpandedEmployees((current) => ({ ...current, [item.id]: result.items }));
    } catch {
      setExpandedEmployees((current) => ({ ...current, [item.id]: [] }));
    } finally {
      setExpandedPeopleLoadingId((current) => (current === item.id ? null : current));
    }
  }

  async function deleteSelectedTarget(target: DepartmentDeleteTarget) {
    setMenuOpen(null);
    setSaveState('loading');
    setError('');
    try {
      if (target.kind === 'department') {
        await api.deleteDepartment(target.item.id);
      } else {
        await api.deleteDepartmentLevel(target.item.id);
      }
      setDeleteTarget(null);
      setSaveState('idle');
      await loadDepartments();
    } catch (deleteError) {
      setSaveState('error');
      setError(deleteError instanceof ApiError ? deleteError.message : copy.settings.loadErrorText);
    }
  }

  function openEmployee(employee: EmployeeListItem) {
    navigate(peopleEmployeePath(employee.id));
  }

  function exportDepartments(format: SettingsExportFormat) {
    setExportMenuOpen(false);
    const rows: Array<Array<string | number>> = [
      [copy.settings.nameColumn, 'Рівень', 'Менеджер', copy.settings.peopleColumn, copy.settings.active],
      ...departments.map((item) => [
        item.name,
        item.level_name || '',
        item.manager_name || '',
        item.employee_count,
        item.is_active ? copy.settings.active : copy.settings.inactive,
      ]),
    ];
    if (format === 'csv') {
      const csv = rows.map((row) => row.map(csvCell).join(';')).join('\n');
      downloadTextFile('departments.csv', `\uFEFF${csv}`, 'text/csv;charset=utf-8');
      return;
    }
    downloadBinaryFile('departments.xlsx', buildXlsx(rows, 'Departments'), 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet');
  }

  function addForActiveTab() {
    if (activeTab === 'fields') {
      openFieldForm();
      return;
    }
    if (activeTab === 'levels') {
      openCreateLevel();
      return;
    }
    openCreateDepartment();
  }

  return (
    <main className="settings-page settings-option-page settings-departments-page">
      <header className="settings-option-header settings-departments-header">
        <div>
          <button type="button" className="settings-back-link" onClick={onBack}>
            <ChevronLeft size={17} />
            {copy.common.previous}
          </button>
          <h1>{copy.settings.items.departments ?? 'Департаменти'}</h1>
          <div className="settings-department-tabs" role="tablist" aria-label="Департаменти">
            {[
              ['structure', 'Структура'],
              ['fields', 'Поля'],
              ['levels', 'Рівні'],
            ].map(([tab, label]) => (
              <button
                key={tab}
                type="button"
                className={activeTab === tab ? 'active' : ''}
                onClick={() => {
                  setActiveTab(tab as DepartmentTab);
                  setMenuOpen(null);
                  setExportMenuOpen(false);
                }}
              >
                {label}
              </button>
            ))}
          </div>
        </div>
        <div className="settings-option-actions">
          {activeTab !== 'fields' ? (
            <div className="settings-option-export">
              <button
                type="button"
                className={`toolbar-icon ${exportMenuOpen ? 'active' : ''}`}
                aria-label={copy.common.export}
                aria-expanded={exportMenuOpen}
                onClick={() => {
                  setMenuOpen(null);
                  setExportMenuOpen((current) => !current);
                }}
              >
                <MoreHorizontal size={18} />
              </button>
              {exportMenuOpen ? (
                <div className="settings-option-export-menu">
                  <button type="button" onClick={() => exportDepartments('xlsx')}>
                    {copy.settings.exportXlsx}
                  </button>
                  <button type="button" onClick={() => exportDepartments('csv')}>
                    {copy.settings.exportCsv}
                  </button>
                </div>
              ) : null}
            </div>
          ) : null}
          <button type="button" className="primary-action" onClick={addForActiveTab}>
            <Plus size={18} />
            {copy.settings.add}
          </button>
        </div>
      </header>

      {activeTab === 'structure' ? (
        <div className="settings-option-search">
          <Search size={18} />
          <input value={search} placeholder={copy.common.search} onChange={(event) => setSearch(event.target.value)} />
        </div>
      ) : null}

      {error ? <div className="settings-option-meta error-text">{error}</div> : null}

      {activeTab === 'structure' ? (
        <section className="settings-option-table settings-department-table">
          {loadState === 'error' ? (
            <EmptyState title={copy.settings.loadErrorTitle} text={error || copy.settings.loadErrorText} />
          ) : visibleDepartments.length ? (
            <table>
              <thead>
                <tr>
                  <th>{copy.settings.nameColumn}</th>
                  <th>Рівень</th>
                  <th>Менеджер</th>
                  <th>{copy.settings.peopleColumn}</th>
                  <th>{copy.common.actions}</th>
                </tr>
              </thead>
              <tbody>
                {visibleDepartments.map(({ item, depth }) => {
                  const isExpanded = expandedIds.has(item.id);
                  const peopleExpanded = expandedPeopleId === item.id;
                  const people = expandedEmployees[item.id] ?? [];
                  const hasChildren = item.children_count > 0 || departments.some((department) => department.parent === item.id);
                  return (
                    <Fragment key={item.id}>
                      <tr className={!item.is_active ? 'muted' : ''}>
                        <td>
                          <div className="settings-department-name" style={{ '--department-depth': depth } as CSSProperties}>
                            {hasChildren ? (
                              <button type="button" className="settings-department-caret" onClick={() => toggleTree(item)} aria-label="Розгорнути">
                                {isExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                              </button>
                            ) : (
                              <span className="settings-department-caret-spacer" />
                            )}
                            <span>{item.name}</span>
                          </div>
                        </td>
                        <td>
                          {item.level_name ? (
                            <span className="settings-department-level">
                              <i style={{ backgroundColor: item.level_color || '#94a3b8' }} />
                              {item.level_name}
                            </span>
                          ) : null}
                        </td>
                        <td>{item.manager_name}</td>
                        <td>
                          <button
                            type="button"
                            className="settings-department-people-count"
                            onClick={(event) => {
                              event.stopPropagation();
                              void toggleDepartmentPeople(item);
                            }}
                          >
                            {item.employee_count}
                          </button>
                        </td>
                        <td>
                          <div className="settings-option-row-menu">
                            <button
                              type="button"
                              className="row-action"
                              aria-label={copy.common.actions}
                              onClick={(event) => {
                                event.stopPropagation();
                                setMenuOpen((current) => (current === `department-${item.id}` ? null : `department-${item.id}`));
                              }}
                            >
                              <MoreHorizontal size={16} />
                            </button>
                            {menuOpen === `department-${item.id}` ? (
                              <div className="settings-option-row-popover">
                                <button type="button" onClick={() => openEditDepartment(item)}>
                                  {copy.settings.edit}
                                </button>
                                <button type="button" className="danger" onClick={() => setDeleteTarget({ kind: 'department', item })}>
                                  {copy.settings.delete}
                                </button>
                              </div>
                            ) : null}
                          </div>
                        </td>
                      </tr>
                      {peopleExpanded ? (
                        <tr className="settings-option-people-row">
                          <td colSpan={5}>
                            <div className="settings-option-people-list">
                              {expandedPeopleLoadingId === item.id ? (
                                <span className="settings-option-people-loading">{copy.common.loading}</span>
                              ) : people.length ? (
                                people.map((employee, index) => {
                                  const fullName = departmentEmployeeName(employee);
                                  return (
                                    <button key={employee.id} type="button" className="settings-option-person" onClick={() => openEmployee(employee)}>
                                      <Avatar
                                        name={fullName}
                                        src={employeeAvatarUrl(employee)}
                                        accent={employeeAccentClasses[index % employeeAccentClasses.length]}
                                        size="sm"
                                      />
                                      <span>{fullName}</span>
                                    </button>
                                  );
                                })
                              ) : (
                                <span className="settings-option-people-empty">{copy.people.employeesNotFound}</span>
                              )}
                            </div>
                          </td>
                        </tr>
                      ) : null}
                    </Fragment>
                  );
                })}
              </tbody>
            </table>
          ) : (
            <EmptyState title="Департаменти не знайдені" text="Додайте департамент або змініть пошук." />
          )}
        </section>
      ) : null}

      {activeTab === 'fields' ? (
        <section className="settings-department-fields-card">
          {allFields.map((field) => (
            <div className="settings-department-field-row" key={field.id}>
              <div>
                <strong>
                  {field.name}
                  {field.required ? <em>*</em> : null}
                </strong>
                <span>{field.type}</span>
                {field.description ? <p>{field.description}</p> : null}
              </div>
              <label className="settings-switch">
                <input
                  type="checkbox"
                  checked={field.enabled}
                  onChange={() =>
                    setCustomFields((current) =>
                      current.map((item) => (item.id === field.id ? { ...item, enabled: !item.enabled } : item)),
                    )
                  }
                  disabled={field.system}
                />
                <span />
              </label>
            </div>
          ))}
        </section>
      ) : null}

      {activeTab === 'levels' ? (
        <section className={`settings-option-table settings-department-levels-table ${levels.length ? '' : 'empty'}`}>
          {levels.length ? (
            <table>
              <thead>
                <tr>
                  <th>{copy.settings.nameColumn}</th>
                  <th>Колір</th>
                  <th>Департаменти</th>
                  <th>{copy.common.actions}</th>
                </tr>
              </thead>
              <tbody>
                {levels.map((level) => (
                  <tr key={level.id} className={!level.is_active ? 'muted' : ''}>
                    <td>{level.name}</td>
                    <td>
                      <span className="settings-department-color-chip" style={{ backgroundColor: level.color || '#94a3b8' }} />
                    </td>
                    <td>{level.department_count}</td>
                    <td>
                      <div className="settings-option-row-menu">
                        <button
                          type="button"
                          className="row-action"
                          aria-label={copy.common.actions}
                          onClick={() => setMenuOpen((current) => (current === `level-${level.id}` ? null : `level-${level.id}`))}
                        >
                          <MoreHorizontal size={16} />
                        </button>
                        {menuOpen === `level-${level.id}` ? (
                          <div className="settings-option-row-popover">
                            <button type="button" onClick={() => openEditLevel(level)}>
                              {copy.settings.edit}
                            </button>
                            <button type="button" className="danger" onClick={() => setDeleteTarget({ kind: 'level', item: level })}>
                              {copy.settings.delete}
                            </button>
                          </div>
                        ) : null}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="settings-department-empty-levels">
              <FileText size={82} />
              <strong>Ще немає рівнів</strong>
              <span>Ви можете додати новий рівень прямо зараз</span>
              <button type="button" className="primary-action" onClick={openCreateLevel}>
                <Plus size={18} />
                Додати рівень
              </button>
            </div>
          )}
        </section>
      ) : null}

      {departmentFormOpen ? (
        <div className="settings-option-modal-layer" role="dialog" aria-modal="true" aria-label={editingDepartment ? 'Редагувати департамент' : 'Додати департамент'}>
          <button type="button" className="settings-option-modal-backdrop" aria-label={copy.settings.cancel} onClick={closeDepartmentForm} />
          <form className="settings-option-modal settings-location-modal" onSubmit={saveDepartment}>
            <header>
              <strong>{editingDepartment ? 'Редагувати департамент' : 'Додати департамент'}</strong>
              <button type="button" className="modal-close" aria-label={copy.settings.cancel} onClick={closeDepartmentForm}>
                <X size={22} />
              </button>
            </header>
            <label>
              <span>{copy.settings.nameColumn}</span>
              <input value={departmentForm.name} onChange={(event) => setDepartmentForm((current) => ({ ...current, name: event.target.value }))} autoFocus />
            </label>
            <label>
              <span>Батьківський департамент <em>За бажанням</em></span>
              <select value={departmentForm.parent} onChange={(event) => setDepartmentForm((current) => ({ ...current, parent: event.target.value }))}>
                <option value="">-- Немає --</option>
                {departments
                  .filter((department) => department.id !== editingDepartment?.id)
                  .map((department) => (
                    <option value={department.id} key={department.id}>
                      {department.name}
                    </option>
                  ))}
              </select>
            </label>
            <label>
              <span>Менеджер <em>За бажанням</em></span>
              <select value={departmentForm.manager} onChange={(event) => setDepartmentForm((current) => ({ ...current, manager: event.target.value }))}>
                <option value="">-- Виберіть --</option>
                {managerOptions.map((employee) => (
                  <option value={employee.id} key={employee.id}>
                    {departmentEmployeeName(employee)}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span>Рівень <em>За бажанням</em></span>
              <select value={departmentForm.level} onChange={(event) => setDepartmentForm((current) => ({ ...current, level: event.target.value }))}>
                <option value="">-- Виберіть --</option>
                {levels.map((level) => (
                  <option value={level.id} key={level.id}>
                    {level.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="settings-option-checkbox">
              <input
                type="checkbox"
                checked={departmentForm.is_active}
                onChange={(event) => setDepartmentForm((current) => ({ ...current, is_active: event.target.checked }))}
              />
              <span>{copy.settings.activeField}</span>
            </label>
            <footer>
              <button type="submit" className="primary-action" disabled={!departmentForm.name.trim() || saveState === 'loading'}>
                {copy.settings.save}
              </button>
            </footer>
          </form>
        </div>
      ) : null}

      {levelFormOpen ? (
        <div className="settings-option-modal-layer" role="dialog" aria-modal="true" aria-label={editingLevel ? 'Редагувати рівень' : 'Додати рівень'}>
          <button type="button" className="settings-option-modal-backdrop" aria-label={copy.settings.cancel} onClick={closeLevelForm} />
          <form className="settings-option-modal settings-department-level-modal" onSubmit={saveLevel}>
            <header>
              <strong>{editingLevel ? 'Редагувати рівень' : 'Додати рівень'}</strong>
              <button type="button" className="modal-close" aria-label={copy.settings.cancel} onClick={closeLevelForm}>
                <X size={22} />
              </button>
            </header>
            <label>
              <span>{copy.settings.nameColumn}</span>
              <div className="settings-level-name-row">
                <input value={levelForm.name} onChange={(event) => setLevelForm((current) => ({ ...current, name: event.target.value }))} autoFocus />
                <span className="settings-level-color-preview" style={{ backgroundColor: levelForm.color }} />
              </div>
            </label>
            <div className="settings-level-palette" aria-label="Колір рівня">
              {departmentLevelColors.map((color) => (
                <button
                  type="button"
                  className={levelForm.color === color ? 'active' : ''}
                  key={color}
                  style={{ backgroundColor: color }}
                  onClick={() => setLevelForm((current) => ({ ...current, color }))}
                />
              ))}
            </div>
            <label className="settings-option-checkbox">
              <input
                type="checkbox"
                checked={levelForm.is_active}
                onChange={(event) => setLevelForm((current) => ({ ...current, is_active: event.target.checked }))}
              />
              <span>{copy.settings.activeField}</span>
            </label>
            <footer>
              <button type="submit" className="primary-action" disabled={!levelForm.name.trim() || saveState === 'loading'}>
                {copy.settings.save}
              </button>
            </footer>
          </form>
        </div>
      ) : null}

      {fieldFormOpen ? (
        <div className="settings-option-modal-layer" role="dialog" aria-modal="true" aria-label="Додати поле">
          <button type="button" className="settings-option-modal-backdrop" aria-label={copy.settings.cancel} onClick={() => setFieldFormOpen(false)} />
          <form className="settings-option-modal settings-location-modal" onSubmit={saveField}>
            <header>
              <strong>Додати поле</strong>
              <button type="button" className="modal-close" aria-label={copy.settings.cancel} onClick={() => setFieldFormOpen(false)}>
                <X size={22} />
              </button>
            </header>
            <label>
              <span>{copy.settings.nameColumn}</span>
              <input value={fieldForm.name} onChange={(event) => setFieldForm((current) => ({ ...current, name: event.target.value }))} autoFocus />
            </label>
            <label>
              <span>Тип</span>
              <select value={fieldForm.type} onChange={(event) => setFieldForm((current) => ({ ...current, type: event.target.value }))}>
                <option>Текст в один рядок</option>
                <option>Багаторядковий текст</option>
                <option>Число</option>
                <option>Дата</option>
                <option>Список</option>
              </select>
            </label>
            <label>
              <span>Опис <em>За бажанням</em></span>
              <input
                value={fieldForm.description}
                placeholder="Додати інформацію"
                onChange={(event) => setFieldForm((current) => ({ ...current, description: event.target.value }))}
              />
            </label>
            <footer>
              <button type="submit" className="primary-action" disabled={!fieldForm.name.trim()}>
                {copy.settings.save}
              </button>
            </footer>
          </form>
        </div>
      ) : null}

      {deleteTarget ? (
        <SettingsDeleteConfirmModal
          itemName={deleteTarget.item.name}
          copy={copy}
          loading={saveState === 'loading'}
          onCancel={() => {
            if (saveState !== 'loading') setDeleteTarget(null);
          }}
          onConfirm={() => void deleteSelectedTarget(deleteTarget)}
        />
      ) : null}
    </main>
  );
}

function departmentEmployeeName(employee: EmployeeListItem) {
  return employee.full_name || `${employee.last_name} ${employee.first_name}`.trim();
}

function buildDepartmentTreeRows(departments: DepartmentOption[], expandedIds: Set<number>, search: string) {
  const childrenByParent = new Map<number | null, DepartmentOption[]>();
  departments.forEach((department) => {
    const parent = department.parent ?? null;
    const children = childrenByParent.get(parent) ?? [];
    children.push(department);
    childrenByParent.set(parent, children);
  });
  childrenByParent.forEach((children) => children.sort((first, second) => first.name.localeCompare(second.name, 'uk')));

  const query = search.trim().toLowerCase();
  const matches = (department: DepartmentOption) =>
    !query ||
    [department.name, department.parent_name, department.manager_name, department.level_name]
      .filter(Boolean)
      .some((value) => value.toLowerCase().includes(query));

  const hasVisibleDescendant = (department: DepartmentOption): boolean => {
    const children = childrenByParent.get(department.id) ?? [];
    return children.some((child) => matches(child) || hasVisibleDescendant(child));
  };

  const rows: Array<{ item: DepartmentOption; depth: number }> = [];
  const visit = (department: DepartmentOption, depth: number) => {
    const children = childrenByParent.get(department.id) ?? [];
    const visible = matches(department) || hasVisibleDescendant(department);
    if (!visible) return;
    rows.push({ item: department, depth });
    const shouldShowChildren = query ? true : expandedIds.has(department.id);
    if (!shouldShowChildren) return;
    children.forEach((child) => visit(child, depth + 1));
  };

  const roots = childrenByParent.get(null) ?? [];
  const visited = new Set<number>();
  roots.forEach((department) => {
    visited.add(department.id);
    visit(department, 0);
  });
  departments.forEach((department) => {
    if (!visited.has(department.id) && !departments.some((item) => item.id === department.parent)) {
      visit(department, 0);
    }
  });
  return rows;
}

function SettingsGeneralView({
  onBack,
  brandingSettings,
  onBrandingChange,
}: {
  onBack: () => void;
  brandingSettings: BrandingSettings;
  onBrandingChange: (settings: BrandingSettings) => void;
}) {
  const [companyName, setCompanyName] = useState('Vidnova Clinic');
  const [timeZone, setTimeZone] = useState('(GMT+02:00) Kyiv');
  const [currency, setCurrency] = useState('UAH - Ukrainian Hryvnia');
  const [nameDisplay, setNameDisplay] = useState('last_first');
  const [dateFormat, setDateFormat] = useState('ДД.ММ.РРРР');
  const [coverCropTarget, setCoverCropTarget] = useState<'home' | 'employee' | null>(null);
  const [features, setFeatures] = useState<Record<string, boolean>>({
    absenceTracking: true,
    jobOffers: true,
    assetManagement: true,
    knowledgeBase: true,
    moodTracking: false,
    announcements: true,
    childrenInfo: true,
    projectTimeTracking: true,
  });
  const language = normalizeLanguage(brandingSettings.language);
  const theme = normalizeTheme(brandingSettings.theme);
  const t = getTranslations(language).settingsGeneral;
  const settingsAccentStyle = { '--settings-accent': brandingSettings.primaryColor } as CSSProperties;
  const coreFeatures = [
    {
      key: 'absenceTracking',
      label: t.features.absenceTracking.label,
      text: t.features.absenceTracking.text,
    },
    {
      key: 'jobOffers',
      label: t.features.jobOffers.label,
      text: t.features.jobOffers.text,
    },
    {
      key: 'assetManagement',
      label: t.features.assetManagement.label,
      text: t.features.assetManagement.text,
    },
    {
      key: 'knowledgeBase',
      label: t.features.knowledgeBase.label,
      text: t.features.knowledgeBase.text,
    },
    {
      key: 'moodTracking',
      label: t.features.moodTracking.label,
      text: t.features.moodTracking.text,
    },
    {
      key: 'announcements',
      label: t.features.announcements.label,
      text: t.features.announcements.text,
    },
    {
      key: 'childrenInfo',
      label: t.features.childrenInfo.label,
      text: t.features.childrenInfo.text,
    },
  ];

  function updateBranding(patch: Partial<BrandingSettings>) {
    onBrandingChange({ ...brandingSettings, ...patch });
  }

  function handleLogoImage(fileList: FileList | null) {
    const file = fileList?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      updateBranding({ logoName: file.name, logoPreviewUrl: String(reader.result || '') });
    };
    reader.readAsDataURL(file);
  }

  function applyCoverCrop(result: CoverCropResult) {
    if (coverCropTarget === 'home') {
      updateBranding({ homeCoverUrl: result.url, homeCoverName: result.name, homeCoverBytes: result.bytes });
    }
    if (coverCropTarget === 'employee') {
      updateBranding({ employeeCoverUrl: result.url, employeeCoverName: result.name, employeeCoverBytes: result.bytes });
    }
    setCoverCropTarget(null);
  }

  function toggleFeature(key: string) {
    setFeatures((current) => ({ ...current, [key]: !current[key] }));
  }

  return (
    <main className="settings-page settings-form-page" style={settingsAccentStyle}>
      <header className="settings-form-header">
        <button type="button" className="settings-back-link" onClick={onBack}>
          <ChevronLeft size={17} />
          {t.back}
        </button>
        <h1>{t.pageTitle}</h1>
      </header>

      <section className="settings-form-section">
        <h2>{t.companyInfo}</h2>
        <div className="settings-form-card">
          <label className="settings-field">
            <span>{t.companyName}</span>
            <input value={companyName} onChange={(event) => setCompanyName(event.target.value)} />
          </label>
          <label className="settings-field">
            <span>{t.defaultLanguage}</span>
            <select value={language} onChange={(event) => updateBranding({ language: normalizeLanguage(event.target.value) })}>
              {languageOptions.map((option) => (
                <option value={option.code} key={option.code}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <p className="settings-field-note">{t.languageNote}</p>
          <label className="settings-field">
            <span>{t.interfaceTheme}</span>
            <select value={theme} onChange={(event) => updateBranding({ theme: normalizeTheme(event.target.value) })}>
              {themeOptions.map((option) => (
                <option value={option} key={option}>
                  {t.themeLabels[option]}
                </option>
              ))}
            </select>
          </label>
          <p className="settings-field-note">{t.themeNote}</p>
          <label className="settings-field">
            <span>{t.defaultTimeZone}</span>
            <select value={timeZone} onChange={(event) => setTimeZone(event.target.value)}>
              <option>(GMT+02:00) Kyiv</option>
              <option>(GMT+01:00) Warsaw</option>
              <option>(GMT+00:00) London</option>
            </select>
          </label>
          <p className="settings-field-note">{t.timeZoneNote}</p>
          <label className="settings-field">
            <span>{t.defaultCurrency}</span>
            <select value={currency} onChange={(event) => setCurrency(event.target.value)}>
              <option>UAH - Ukrainian Hryvnia</option>
              <option>EUR - Euro</option>
              <option>USD - US Dollar</option>
            </select>
          </label>
          <label className="settings-field">
            <span>{t.nameDisplay}</span>
            <select value={nameDisplay} onChange={(event) => setNameDisplay(event.target.value)}>
              <option value="last_first">{t.lastNameFirst}</option>
              <option value="first_last">{t.firstNameFirst}</option>
            </select>
          </label>
          <label className="settings-field">
            <span>{t.dateFormat}</span>
            <select value={dateFormat} onChange={(event) => setDateFormat(event.target.value)}>
              <option>ДД.ММ.РРРР</option>
              <option>MM/DD/YYYY</option>
              <option>YYYY-MM-DD</option>
            </select>
          </label>
        </div>
      </section>

      <section className="settings-form-section">
        <h2>{t.personalization}</h2>
        <div className="settings-form-card personalization-card">
          <div className="settings-brand-row">
            <label className="settings-file-field">
              <span>{t.logo}</span>
              <input
                type="file"
                accept=".svg,.png,.jpg,.jpeg"
                onChange={(event) => handleLogoImage(event.target.files)}
              />
              <small>{t.logoNote}</small>
            </label>
            <div className="settings-logo-preview" aria-label={t.logoPreviewLabel}>
              {brandingSettings.logoPreviewUrl ? <img src={brandingSettings.logoPreviewUrl} alt="" /> : <span className="settings-logo-mark" />}
              {brandingSettings.logoName ? <em>{brandingSettings.logoName}</em> : null}
            </div>
          </div>

          <div className="settings-color-row">
            <div>
              <strong>{t.primaryColor}</strong>
              <span>{t.primaryColorNote}</span>
            </div>
            <label className="settings-color-picker">
              <input type="color" value={brandingSettings.primaryColor} onChange={(event) => updateBranding({ primaryColor: event.target.value })} />
              <span style={{ backgroundColor: brandingSettings.primaryColor }} />
              <ChevronDown size={13} />
            </label>
          </div>

          <label className="settings-checkbox-row">
            <input type="checkbox" checked={brandingSettings.homeCoverDisabled} onChange={(event) => updateBranding({ homeCoverDisabled: event.target.checked })} />
            <span>{t.disableHomeCover}</span>
          </label>
          <div
            className={`settings-cover-preview ${brandingSettings.homeCoverDisabled ? 'muted' : ''}`}
            style={{
              backgroundImage: `linear-gradient(90deg, rgba(255, 255, 255, 0.12), rgba(255, 255, 255, 0)), url("${brandingSettings.homeCoverUrl}")`,
            }}
          >
            <button type="button" className="settings-cover-edit" onClick={() => setCoverCropTarget('home')}>
              {t.editCover}
              <ChevronDown size={14} />
            </button>
          </div>
          {brandingSettings.homeCoverName ? (
            <p className="settings-cover-note">
              {t.homeCoverName}: {brandingSettings.homeCoverName}
              {brandingSettings.homeCoverBytes ? <span> · {formatBytes(brandingSettings.homeCoverBytes)}</span> : null}
            </p>
          ) : null}

          <label className="settings-checkbox-row">
            <input type="checkbox" checked={brandingSettings.employeeCoverDisabled} onChange={(event) => updateBranding({ employeeCoverDisabled: event.target.checked })} />
            <span>{t.disableEmployeeCover}</span>
          </label>
          <div
            className={`settings-cover-preview employee-cover ${brandingSettings.employeeCoverDisabled ? 'muted' : ''}`}
            style={{
              backgroundImage: `linear-gradient(90deg, rgba(255, 255, 255, 0.12), rgba(255, 255, 255, 0)), url("${brandingSettings.employeeCoverUrl}")`,
            }}
          >
            <button type="button" className="settings-cover-edit" onClick={() => setCoverCropTarget('employee')}>
              {t.editCover}
              <ChevronDown size={14} />
            </button>
          </div>
          <p className="settings-cover-note">
            {t.employeeCoverNote}
            {brandingSettings.employeeCoverName ? (
              <span>
                {' '}
                {t.currentFile}: {brandingSettings.employeeCoverName}
                {brandingSettings.employeeCoverBytes ? ` · ${formatBytes(brandingSettings.employeeCoverBytes)}` : ''}
              </span>
            ) : null}
          </p>
          <label className="settings-checkbox-row compact">
            <input
              type="checkbox"
              checked={brandingSettings.employeeCoverUploadAllowed}
              onChange={(event) => updateBranding({ employeeCoverUploadAllowed: event.target.checked })}
            />
            <span>{t.allowEmployeeCoverUpload}</span>
          </label>
          <p className="settings-cover-note">{t.allowEmployeeCoverUploadNote}</p>
        </div>
      </section>

      <section className="settings-form-section settings-features-section">
        <h2>{t.featuresTitle}</h2>
        <div className="settings-form-card settings-feature-card">
          <div className="settings-feature-group">
            <h3>{t.coreHr}</h3>
            {coreFeatures.map((feature) => (
              <label className="settings-feature-toggle" key={feature.key}>
                <input type="checkbox" checked={features[feature.key]} onChange={() => toggleFeature(feature.key)} />
                <span>
                  <strong>{feature.label}</strong>
                  <em>{feature.text}</em>
                </span>
              </label>
            ))}
          </div>
          <div className="settings-feature-group">
            <h3>{t.time}</h3>
            <label className="settings-feature-toggle">
              <input type="checkbox" checked={features.projectTimeTracking} onChange={() => toggleFeature('projectTimeTracking')} />
              <span>
                <strong>{t.features.projectTimeTracking.label}</strong>
                <em>{t.features.projectTimeTracking.text}</em>
              </span>
            </label>
          </div>
        </div>
      </section>
      {coverCropTarget ? (
        <SettingsCoverCropModal
          title={coverCropTarget === 'home' ? t.homeCoverTitle : t.employeeCoverTitle}
          onClose={() => setCoverCropTarget(null)}
          onApply={applyCoverCrop}
        />
      ) : null}
    </main>
  );
}

function SettingsCoverCropModal({
  title,
  onClose,
  onApply,
}: {
  title: string;
  onClose: () => void;
  onApply: (result: CoverCropResult) => void;
}) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const imageRef = useRef<HTMLImageElement | null>(null);
  const stageRef = useRef<HTMLDivElement | null>(null);
  const [objectUrl, setObjectUrl] = useState('');
  const [sourceName, setSourceName] = useState('cover');
  const [cropRect, setCropRect] = useState({ x: 5, y: 44, width: 90, height: 12.8 });
  const [saveState, setSaveState] = useState<LoadState>('idle');
  const [error, setError] = useState('');
  const cropAspect = 1090 / 155;
  const dragRef = useRef<{
    mode: 'move' | 'resize';
    handle?: 'nw' | 'ne' | 'sw' | 'se';
    pointerX: number;
    pointerY: number;
    rect: typeof cropRect;
    stageWidth: number;
    stageHeight: number;
  } | null>(null);

  useEffect(() => {
    return () => {
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [objectUrl]);

  function selectFile(file: File | null | undefined) {
    if (!file) return;
    if (!file.type.startsWith('image/')) {
      setError('Завантажте зображення у форматі JPEG або PNG.');
      return;
    }
    if (file.size > 12 * 1024 * 1024) {
      setError('Максимальний розмір файлу 12 МБ.');
      return;
    }
    if (objectUrl) URL.revokeObjectURL(objectUrl);
    setObjectUrl(URL.createObjectURL(file));
    setSourceName(file.name.replace(/\.[^.]+$/, '') || 'cover');
    setCropRect({ x: 5, y: 44, width: 90, height: 12.8 });
    setSaveState('idle');
    setError('');
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    selectFile(event.dataTransfer.files[0]);
  }

  function createInitialCropRect(imageWidth: number, imageHeight: number) {
    let width = 90;
    let height = ((width / 100) * imageWidth / cropAspect / imageHeight) * 100;
    if (height > 80) {
      height = 80;
      width = ((height / 100) * imageHeight * cropAspect / imageWidth) * 100;
    }
    width = Math.min(94, width);
    height = Math.min(80, height);
    return {
      x: Math.max(0, (100 - width) / 2),
      y: Math.max(0, (100 - height) / 2),
      width,
      height,
    };
  }

  function cropHeightForWidth(width: number) {
    const image = imageRef.current;
    if (!image?.naturalWidth || !image.naturalHeight) return cropRect.height;
    return ((width / 100) * image.naturalWidth / cropAspect / image.naturalHeight) * 100;
  }

  function cropWidthForHeight(height: number) {
    const image = imageRef.current;
    if (!image?.naturalWidth || !image.naturalHeight) return cropRect.width;
    return ((height / 100) * image.naturalHeight * cropAspect / image.naturalWidth) * 100;
  }

  function clampCropRect(rect: typeof cropRect) {
    const width = Math.min(Math.max(rect.width, 12), 100);
    const height = cropHeightForWidth(width);
    const safeWidth = height > 100 ? cropWidthForHeight(100) : width;
    const safeHeight = cropHeightForWidth(safeWidth);
    const x = Math.min(Math.max(rect.x, 0), Math.max(0, 100 - safeWidth));
    const y = Math.min(Math.max(rect.y, 0), Math.max(0, 100 - safeHeight));
    return { x, y, width: safeWidth, height: safeHeight };
  }

  function startCropDrag(event: ReactPointerEvent<HTMLDivElement>) {
    if (event.button !== 0 || (event.target as HTMLElement).dataset.cropHandle) return;
    const stageBox = stageRef.current?.getBoundingClientRect();
    if (!stageBox) return;
    event.preventDefault();
    stageRef.current?.setPointerCapture(event.pointerId);
    dragRef.current = {
      mode: 'move',
      pointerX: event.clientX,
      pointerY: event.clientY,
      rect: cropRect,
      stageWidth: stageBox.width,
      stageHeight: stageBox.height,
    };
  }

  function startCropResize(event: ReactPointerEvent<HTMLButtonElement>, handle: 'nw' | 'ne' | 'sw' | 'se') {
    const stageBox = stageRef.current?.getBoundingClientRect();
    if (!stageBox) return;
    event.preventDefault();
    event.stopPropagation();
    stageRef.current?.setPointerCapture(event.pointerId);
    dragRef.current = {
      mode: 'resize',
      handle,
      pointerX: event.clientX,
      pointerY: event.clientY,
      rect: cropRect,
      stageWidth: stageBox.width,
      stageHeight: stageBox.height,
    };
  }

  function handleCropPointerMove(event: ReactPointerEvent<HTMLDivElement>) {
    const drag = dragRef.current;
    if (!drag) return;
    const deltaX = ((event.clientX - drag.pointerX) / drag.stageWidth) * 100;
    const deltaY = ((event.clientY - drag.pointerY) / drag.stageHeight) * 100;

    if (drag.mode === 'move') {
      setCropRect(clampCropRect({ ...drag.rect, x: drag.rect.x + deltaX, y: drag.rect.y + deltaY }));
      return;
    }

    const handle = drag.handle ?? 'se';
    const widthDeltaFromX = handle.includes('e') ? deltaX : -deltaX;
    const heightDelta = handle.includes('s') ? deltaY : -deltaY;
    const widthDeltaFromY = cropWidthForHeight(drag.rect.height + heightDelta) - drag.rect.width;
    const widthDelta = Math.abs(widthDeltaFromY) > Math.abs(widthDeltaFromX) ? widthDeltaFromY : widthDeltaFromX;
    let nextWidth = Math.max(12, drag.rect.width + widthDelta);
    const maxWidthX = handle.includes('e') ? 100 - drag.rect.x : drag.rect.x + drag.rect.width;
    const maxHeightY = handle.includes('s') ? 100 - drag.rect.y : drag.rect.y + drag.rect.height;
    const maxWidthY = cropWidthForHeight(maxHeightY);
    nextWidth = Math.min(nextWidth, maxWidthX, maxWidthY, 100);
    const nextHeight = cropHeightForWidth(nextWidth);
    const nextX = handle.includes('w') ? drag.rect.x + drag.rect.width - nextWidth : drag.rect.x;
    const nextY = handle.includes('n') ? drag.rect.y + drag.rect.height - nextHeight : drag.rect.y;
    setCropRect(clampCropRect({ x: nextX, y: nextY, width: nextWidth, height: nextHeight }));
  }

  function stopCropDrag(event: ReactPointerEvent<HTMLDivElement>) {
    if (dragRef.current) {
      stageRef.current?.releasePointerCapture(event.pointerId);
    }
    dragRef.current = null;
  }

  function drawCropToCanvas(canvas: HTMLCanvasElement) {
    const image = imageRef.current;
    if (!image || !image.complete || !image.naturalWidth || !image.naturalHeight) return false;

    const outputWidth = 1090;
    const outputHeight = 155;
    canvas.width = outputWidth;
    canvas.height = outputHeight;
    const context = canvas.getContext('2d');
    if (!context) return false;

    context.clearRect(0, 0, outputWidth, outputHeight);
    context.fillStyle = '#f5f7fb';
    context.fillRect(0, 0, outputWidth, outputHeight);

    context.imageSmoothingEnabled = true;
    context.imageSmoothingQuality = 'high';
    context.drawImage(
      image,
      (cropRect.x / 100) * image.naturalWidth,
      (cropRect.y / 100) * image.naturalHeight,
      (cropRect.width / 100) * image.naturalWidth,
      (cropRect.height / 100) * image.naturalHeight,
      0,
      0,
      outputWidth,
      outputHeight,
    );
    return true;
  }

  async function canvasToWebp(canvas: HTMLCanvasElement): Promise<Blob> {
    return new Promise((resolve, reject) => {
      canvas.toBlob((result) => (result ? resolve(result) : reject(new Error('WebP conversion failed'))), 'image/webp', 0.84);
    });
  }

  async function blobToDataUrl(blob: Blob): Promise<string> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(String(reader.result || ''));
      reader.onerror = () => reject(new Error('FileReader failed'));
      reader.readAsDataURL(blob);
    });
  }

  async function applyCrop() {
    const canvas = document.createElement('canvas');
    if (!drawCropToCanvas(canvas)) {
      setError('Зображення ще не готове для обрізки.');
      return;
    }

    setSaveState('loading');
    setError('');
    try {
      const blob = await canvasToWebp(canvas);
      const dataUrl = await blobToDataUrl(blob);
      const safeName = sourceName.replace(/[^0-9A-Za-zА-Яа-яІіЇїЄєҐґ_-]+/g, '-').replace(/^-+|-+$/g, '') || 'cover';
      onApply({ url: dataUrl, name: safeName, bytes: blob.size });
      setSaveState('ok');
    } catch {
      setSaveState('error');
      setError('Не вдалося зберегти обкладинку.');
    }
  }

  return (
    <div className="knowledge-modal-layer cover-modal-layer" role="dialog" aria-modal="true" aria-label={title}>
      <div className="settings-cover-crop-modal">
        <button type="button" className="modal-close" aria-label="Закрити" onClick={onClose}>
          <X size={22} />
        </button>
        <div className="settings-crop-head">
          <strong>{title}</strong>
          <span>Обрізка під формат банера 1090 × 155 px.</span>
        </div>

        {!objectUrl ? (
          <div
            className="cover-dropzone settings-cover-dropzone"
            onDragOver={(event) => event.preventDefault()}
            onDrop={handleDrop}
            onClick={() => inputRef.current?.click()}
          >
            <input
              ref={inputRef}
              type="file"
              accept="image/jpeg,image/png,image/webp"
              onChange={(event) => selectFile(event.target.files?.[0])}
            />
            <ImagePlus size={24} />
            <strong>Перетягніть фото або натисніть для вибору</strong>
            <span>Фото буде обрізане під формат банера.</span>
          </div>
        ) : (
          <>
            <div
              ref={stageRef}
              className="settings-crop-photo-stage"
              onPointerMove={handleCropPointerMove}
              onPointerUp={stopCropDrag}
              onPointerCancel={stopCropDrag}
            >
              <img
                ref={imageRef}
                src={objectUrl}
                alt=""
                onLoad={(event) => {
                  setCropRect(createInitialCropRect(event.currentTarget.naturalWidth, event.currentTarget.naturalHeight));
                }}
              />
              <div
                className="settings-crop-box"
                style={{
                  left: `${cropRect.x}%`,
                  top: `${cropRect.y}%`,
                  width: `${cropRect.width}%`,
                  height: `${cropRect.height}%`,
                }}
                onPointerDown={startCropDrag}
              >
                <span />
                {(['nw', 'ne', 'sw', 'se'] as const).map((handle) => (
                  <button
                    key={handle}
                    type="button"
                    className={`settings-crop-handle ${handle}`}
                    data-crop-handle={handle}
                    aria-label="Змінити область обрізки"
                    onPointerDown={(event) => startCropResize(event, handle)}
                  />
                ))}
              </div>
            </div>
            <div className="cover-modal-actions">
              <button type="button" className="secondary-action" onClick={() => setObjectUrl('')}>
                <ChevronLeft size={17} />
                Назад
              </button>
              <button type="button" className="primary-action" disabled={saveState === 'loading'} onClick={applyCrop}>
                <Save size={17} />
                {saveState === 'loading' ? 'Збереження...' : 'Зберегти'}
              </button>
            </div>
          </>
        )}
        {error ? <p className="form-error">{error}</p> : null}
      </div>
    </div>
  );
}

function SettingsView({
  brandingSettings,
  onBrandingChange,
  copy,
}: {
  brandingSettings: BrandingSettings;
  onBrandingChange: (settings: BrandingSettings) => void;
  copy: AppCopy;
}) {
  const location = useLocation();
  const navigate = useNavigate();
  const [search, setSearch] = useState('');
  const activeSlug = settingsSlugFromPathname(location.pathname);
  const activeItem = activeSlug ? settingsItemsBySlug.get(activeSlug) ?? null : null;
  const searchQuery = search.trim().toLowerCase();
  const visibleGroups = settingsGroups
    .map((group) => ({
      ...group,
      displayTitle: copy.settings.groups[group.key] ?? group.title,
      items: searchQuery
        ? group.items.filter((item) =>
            `${copy.settings.groups[group.key] ?? group.title} ${copy.settings.items[item.slug] ?? item.label}`.toLowerCase().includes(searchQuery),
          )
        : group.items,
    }))
    .filter((group) => group.items.length);

  if (activeSlug === 'general') {
    return <SettingsGeneralView onBack={() => navigate('/settings')} brandingSettings={brandingSettings} onBrandingChange={onBrandingChange} />;
  }

  if (
    activeSlug === 'experience-levels' ||
    activeSlug === 'gender' ||
    activeSlug === 'termination-reasons' ||
    activeSlug === 'termination-types' ||
    activeSlug === 'work-types' ||
    activeSlug === 'probation-conditions' ||
    activeSlug === 'positions' ||
    activeSlug === 'divisions' ||
    activeSlug === 'skills'
  ) {
    return <SettingsOptionListView kind={activeSlug} onBack={() => navigate('/settings')} copy={copy} />;
  }

  if (activeSlug === 'locations') {
    return <SettingsLocationsView onBack={() => navigate('/settings')} copy={copy} />;
  }

  if (activeSlug === 'holiday-policies') {
    return <SettingsHolidayPoliciesView onBack={() => navigate('/settings')} copy={copy} />;
  }

  if (activeSlug === 'work-schedules' || activeSlug === 'working-patterns') {
    return <SettingsWorkingPatternsView onBack={() => navigate('/settings')} copy={copy} />;
  }

  if (activeSlug === 'departments') {
    return <SettingsDepartmentsView onBack={() => navigate('/settings')} copy={copy} />;
  }

  if (activeSlug && activeItem) {
    const Icon = activeItem.icon;
    const activeLabel = copy.settings.items[activeItem.slug] ?? activeItem.label;
    const activeGroup = copy.settings.groups[activeItem.groupKey] ?? activeItem.group;
    return (
      <main className="settings-page">
        <header className="settings-detail-header">
          <button type="button" className="toolbar-button" onClick={() => navigate('/settings')}>
            <ChevronLeft size={17} />
            {copy.common.settings}
          </button>
          <div>
            <span>{activeGroup}</span>
            <h1>{activeLabel}</h1>
          </div>
        </header>
        <section className="settings-detail-panel">
          <div className="settings-detail-icon">
            <Icon size={22} />
          </div>
          <div>
            <h2>{activeLabel}</h2>
            <p>{copy.settings.inProgress}</p>
          </div>
          <StatusPill status="manual_review" />
        </section>
      </main>
    );
  }

  return (
    <main className="settings-page">
      <header className="settings-header">
        <h1>{copy.settings.title}</h1>
        <label className="settings-search">
          <Search size={18} />
          <input value={search} placeholder={copy.common.search} onChange={(event) => setSearch(event.target.value)} />
        </label>
      </header>
      <div className="settings-groups">
        {visibleGroups.map((group) => (
          <section className="settings-group" key={group.title}>
            <h2>{group.displayTitle}</h2>
            <div className="settings-grid">
              {group.items.map((item) => {
                const Icon = item.icon;
                return (
                  <button type="button" className="settings-item" key={item.slug} onClick={() => navigate(`/settings/${item.slug}`)}>
                    <span className="settings-item-icon">
                      <Icon size={16} />
                    </span>
                    <span>{copy.settings.items[item.slug] ?? item.label}</span>
                  </button>
                );
              })}
            </div>
          </section>
        ))}
        {!visibleGroups.length ? (
          <section className="settings-group">
            <EmptyState title={copy.settings.noResultsTitle} text={copy.settings.noResultsText} />
          </section>
        ) : null}
      </div>
    </main>
  );
}

function UtilityView({ section, overview, copy }: { section: Section; overview: DashboardOverview; copy: AppCopy }) {
  const activeEmployees = overview.employees_by_status.find((row) => row.status === 'active')?.count ?? 0;
  const title = navLabel(copy, section);

  return (
    <main className="workspace utility-page">
      <header className="page-header">
        <div>
          <h1>{title}</h1>
          <p>{copy.common.sectionPending}</p>
        </div>
      </header>
      <div className="metric-row">
        <MetricCard label={copy.common.activeEmployees} value={String(activeEmployees)} />
        <MetricCard label={copy.common.timeExceptions} value={String(overview.workday_exceptions)} />
        <MetricCard label={copy.common.pendingRequests} value={String(overview.pending_leave_requests)} />
      </div>
      <section className="panel placeholder-panel">
        <h2>{title}</h2>
        <p>{copy.common.placeholderStructure}</p>
      </section>
    </main>
  );
}

function NotificationsView() {
  return (
    <main className="workspace notifications-page">
      <header className="notifications-header">
        <h1>Сповіщення</h1>
      </header>
      <div className="notifications-tabs">
        <button type="button" className="active">
          Усі <span>0</span>
        </button>
      </div>
      <section className="notifications-empty-card" aria-label="Немає сповіщень">
        <div className="notifications-illustration" aria-hidden="true">
          <div className="notification-blob" />
          <div className="notification-board">
            <div className="notification-clip" />
            <span />
            <span />
            <span />
            <span />
          </div>
          <div className="notification-badge">
            <Rocket size={22} />
          </div>
        </div>
        <h2>Ви з усім ознайомилися</h2>
        <p>Коли щось потребуватиме вашої уваги, воно зʼявиться тут</p>
      </section>
    </main>
  );
}

function AssetsView({ copy }: { copy: AppCopy }) {
  const [items, setItems] = useState<CmmsAsset[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [loadState, setLoadState] = useState<LoadState>('idle');
  const [error, setError] = useState('');
  const [employees, setEmployees] = useState<EmployeeListItem[]>([]);
  const [openAssetId, setOpenAssetId] = useState<number | null>(null);
  const [pickerQuery, setPickerQuery] = useState('');
  const [savingId, setSavingId] = useState<number | null>(null);
  const [options, setOptions] = useState<CmmsAssetOptions | null>(null);
  const [statusFilter, setStatusFilter] = useState('all');
  const [locationPath, setLocationPath] = useState<number[]>([]);
  const [departmentFilter, setDepartmentFilter] = useState<number | ''>('');
  const [responsibleFilter, setResponsibleFilter] = useState<number | ''>('');
  const pageSize = 28;

  useEffect(() => {
    api
      .employees({ status: 'active', page_size: 500 })
      .then((result) => setEmployees(result.items))
      .catch(() => setEmployees([]));
    api
      .assetOptions()
      .then(setOptions)
      .catch(() => setOptions(null));
  }, []);

  // The deepest selected location filters by that location + all its descendants.
  const locationIds = useMemo(() => {
    if (!options || locationPath.length === 0) return [];
    const deepest = locationPath[locationPath.length - 1];
    const node = findLocationNode(options.locations, deepest);
    return node ? collectLocationIds(node) : [];
  }, [options, locationPath]);

  useEffect(() => {
    let cancelled = false;
    setLoadState('loading');
    setError('');
    api
      .assets({
        page,
        page_size: pageSize,
        search: search.trim() || undefined,
        status: statusFilter,
        location_ids: locationIds,
        department_ids: departmentFilter ? [departmentFilter] : [],
        responsible_ids: responsibleFilter ? [responsibleFilter] : [],
      })
      .then((data) => {
        if (cancelled) return;
        setItems(data.items);
        setTotal(data.total);
        setLoadState('ok');
      })
      .catch((loadError) => {
        if (cancelled) return;
        setError(loadError instanceof ApiError ? loadError.message : 'Не вдалося завантажити активи');
        setLoadState('error');
      });
    return () => {
      cancelled = true;
    };
  }, [page, search, statusFilter, locationIds, departmentFilter, responsibleFilter]);

  useEffect(() => {
    setPage(1);
  }, [search, statusFilter, locationIds, departmentFilter, responsibleFilter]);

  const hasActiveFilters =
    statusFilter !== 'all' || locationPath.length > 0 || departmentFilter !== '' || responsibleFilter !== '';

  function resetFilters() {
    setStatusFilter('all');
    setLocationPath([]);
    setDepartmentFilter('');
    setResponsibleFilter('');
    setSearch('');
  }

  function selectLocationLevel(level: number, value: string) {
    setLocationPath((current) => {
      const next = current.slice(0, level);
      if (value) next.push(Number(value));
      return next;
    });
  }

  useEffect(() => {
    if (openAssetId == null) return undefined;
    function handlePointerDown(event: PointerEvent) {
      const target = event.target as HTMLElement;
      if (!target.closest('.asset-responsible')) setOpenAssetId(null);
    }
    document.addEventListener('pointerdown', handlePointerDown);
    return () => document.removeEventListener('pointerdown', handlePointerDown);
  }, [openAssetId]);

  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const pickerOptions = useMemo(() => {
    const query = pickerQuery.trim().toLowerCase();
    return employees
      .filter((employee) => !query || `${employee.full_name} ${employee.position_name} ${employee.department_name}`.toLowerCase().includes(query))
      .slice(0, 60);
  }, [employees, pickerQuery]);

  async function assign(asset: CmmsAsset, employeeId: number | null) {
    setSavingId(asset.id);
    setError('');
    try {
      const result = await api.assignAssetResponsible(asset.id, employeeId);
      setItems((current) =>
        current.map((item) =>
          item.id === asset.id
            ? { ...item, responsible_person_id: result.responsible_person_id, responsible_person_name: result.responsible_person_name }
            : item,
        ),
      );
      setOpenAssetId(null);
      setPickerQuery('');
    } catch (assignError) {
      setError(assignError instanceof ApiError ? assignError.message : 'Не вдалося призначити відповідального');
    } finally {
      setSavingId(null);
    }
  }

  return (
    <main className="workspace assets-page">
      <header className="page-header">
        <div>
          <h1>{copy.nav.assets}</h1>
        </div>
      </header>

      <div className="list-toolbar">
        <label className="wide-search">
          <Search size={16} />
          <input type="text" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Пошук активу за назвою чи інв. номером" />
        </label>
        {hasActiveFilters ? (
          <button type="button" className="toolbar-button" onClick={resetFilters}>
            <X size={15} />
            Скинути фільтри
          </button>
        ) : null}
      </div>

      {options ? (
        <div className="asset-filters">
          <div className="asset-filter">
            <label>Статус</label>
            <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
              <option value="all">Всі</option>
              {options.statuses.map((status) => (
                <option key={status} value={status}>
                  {status}
                </option>
              ))}
            </select>
          </div>

          <div className="asset-filter asset-filter-location">
            <label>Локація</label>
            <div className="asset-location-levels">
              {Array.from({ length: locationPath.length + 1 }).map((_, level) => {
                const levelOptions = locationLevelOptions(options.locations, locationPath.slice(0, level));
                if (levelOptions.length === 0) return null;
                return (
                  <select key={level} value={locationPath[level] ?? ''} onChange={(event) => selectLocationLevel(level, event.target.value)}>
                    <option value="">Всі</option>
                    {levelOptions.map((loc) => (
                      <option key={loc.id} value={loc.id}>
                        {loc.name}
                      </option>
                    ))}
                  </select>
                );
              })}
            </div>
          </div>

          <div className="asset-filter">
            <label>Департамент</label>
            <select value={departmentFilter} onChange={(event) => setDepartmentFilter(event.target.value ? Number(event.target.value) : '')}>
              <option value="">Всі</option>
              {options.departments.map((dept) => (
                <option key={dept.id} value={dept.id}>
                  {dept.name}
                </option>
              ))}
            </select>
          </div>

          <div className="asset-filter">
            <label>Відповідальний</label>
            <select value={responsibleFilter} onChange={(event) => setResponsibleFilter(event.target.value ? Number(event.target.value) : '')}>
              <option value="">Всі</option>
              {options.employees.map((emp) => (
                <option key={emp.id} value={emp.id}>
                  {emp.full_name}
                </option>
              ))}
            </select>
          </div>
        </div>
      ) : null}

      <div className="result-meta">
        <span>
          {loadState === 'loading'
            ? copy.common.loading
            : total === 0
              ? 'Активів не знайдено'
              : `${(page - 1) * pageSize + 1}-${(page - 1) * pageSize + items.length} / ${total}`}
        </span>
        {total > pageSize ? (
          <div className="pagination">
            <button type="button" aria-label={copy.common.previous} disabled={page <= 1} onClick={() => setPage((current) => Math.max(1, current - 1))}>
              <ChevronLeft size={16} />
            </button>
            {buildPageItems(page, totalPages).map((item, index) =>
              item === 'gap' ? (
                <span key={`gap-${index}`} className="page-gap">
                  …
                </span>
              ) : (
                <button type="button" key={item} className={item === page ? 'active' : ''} onClick={() => setPage(item)}>
                  {item}
                </button>
              ),
            )}
            <button type="button" aria-label={copy.common.next} disabled={page >= totalPages} onClick={() => setPage((current) => Math.min(totalPages, current + 1))}>
              <ChevronRight size={16} />
            </button>
          </div>
        ) : null}
      </div>

      {error ? <div className="org-empty-panel"><EmptyState title="Помилка" text={error} /></div> : null}

      {loadState === 'ok' && items.length === 0 ? (
        <div className="org-empty-panel"><EmptyState title="Активів не знайдено" /></div>
      ) : (
        <div className="asset-grid">
          {items.map((asset) => (
            <article key={asset.id} className="asset-card">
              <div className="asset-card-media">
                <span className={`asset-status asset-status-${assetStatusClass(asset.status)}`}>{asset.status}</span>
                {asset.photo_url ? (
                  <img src={asset.photo_url} alt={asset.name} loading="lazy" />
                ) : (
                  <div className="asset-card-noimg">
                    <Boxes size={42} />
                  </div>
                )}
              </div>
              <div className="asset-card-body">
                <strong className="asset-card-name" title={asset.name}>{asset.name}</strong>
                <span className="asset-card-inv">Інв. № {asset.inventory_number}</span>
                <div className="asset-responsible">
                  <button
                    type="button"
                    className={`asset-responsible-trigger${openAssetId === asset.id ? ' active' : ''}`}
                    disabled={savingId === asset.id}
                    onClick={() => {
                      setOpenAssetId(openAssetId === asset.id ? null : asset.id);
                      setPickerQuery('');
                    }}
                  >
                    <Users size={14} />
                    {asset.responsible_person_name ? (
                      <span className="asset-responsible-name">{asset.responsible_person_name}</span>
                    ) : (
                      <span className="asset-responsible-empty">Не призначено</span>
                    )}
                    <ChevronDown size={14} />
                  </button>
                  {openAssetId === asset.id ? (
                    <div className="asset-picker">
                      <div className="org-picker-search">
                        <Search size={15} />
                        <input type="text" value={pickerQuery} onChange={(event) => setPickerQuery(event.target.value)} placeholder="Пошук співробітника…" autoFocus />
                      </div>
                      <div className="asset-picker-list">
                        {asset.responsible_person_id != null ? (
                          <button type="button" className="org-picker-item reset" onClick={() => assign(asset, null)}>
                            Зняти відповідального
                          </button>
                        ) : null}
                        {pickerOptions.map((employee, index) => {
                          const person = employeeToPerson(employee, index, copy);
                          return (
                            <button type="button" key={employee.id} className="org-picker-item" onClick={() => assign(asset, employee.id)}>
                              <Avatar name={person.fullName} src={person.avatarUrl} accent={person.accent} />
                              <span>
                                <strong>{person.fullName}</strong>
                                <small>{person.role}</small>
                              </span>
                            </button>
                          );
                        })}
                        {pickerOptions.length === 0 ? <div className="org-picker-empty">Нічого не знайдено</div> : null}
                      </div>
                    </div>
                  ) : null}
                </div>
              </div>
            </article>
          ))}
        </div>
      )}
    </main>
  );
}

function collectLocationIds(node: CmmsLocation): number[] {
  const ids = [node.id];
  for (const child of node.sublocations ?? []) ids.push(...collectLocationIds(child));
  return ids;
}

// Options for the next cascading location dropdown given the selected path so far.
function locationLevelOptions(locations: CmmsLocation[], path: number[]): CmmsLocation[] {
  let level = locations;
  for (const id of path) {
    const node = level.find((loc) => loc.id === id);
    if (!node) return [];
    level = node.sublocations ?? [];
  }
  return level;
}

function findLocationNode(locations: CmmsLocation[], id: number): CmmsLocation | null {
  for (const loc of locations) {
    if (loc.id === id) return loc;
    const found = findLocationNode(loc.sublocations ?? [], id);
    if (found) return found;
  }
  return null;
}

function assetStatusClass(status: string): string {
  const value = (status || '').toLowerCase();
  if (value.includes('експлуат')) return 'ok';
  if (value.includes('склад')) return 'idle';
  if (value.includes('ремонт')) return 'warn';
  if (value.includes('списан')) return 'muted';
  if (value.includes('резерв')) return 'info';
  return 'neutral';
}

function ChangelogView({ onBack }: { onBack: () => void }) {
  return (
    <main className="workspace changelog-page">
      <header className="page-header">
        <div>
          <button type="button" className="settings-back-link" onClick={onBack}>
            <ChevronLeft size={17} />
            Назад
          </button>
          <h1>Історія версій</h1>
        </div>
      </header>
      <div className="changelog-list">
        {changelog.map((entry) => (
          <article key={entry.version} className="changelog-entry panel">
            <div className="changelog-entry-head">
              <strong>v{entry.version}</strong>
              <span>{entry.date}</span>
            </div>
            <ul>
              {entry.changes.map((change, index) => (
                <li key={index}>{change}</li>
              ))}
            </ul>
          </article>
        ))}
      </div>
    </main>
  );
}

export function App() {
  const location = useLocation();
  const navigate = useNavigate();
  const section = sectionFromPathname(location.pathname);
  const loginRedirectState = location.state as { from?: unknown } | null;
  const loginRedirectPath =
    typeof loginRedirectState?.from === 'string' &&
    loginRedirectState.from.startsWith('/') &&
    !loginRedirectState.from.startsWith('//') &&
    !loginRedirectState.from.startsWith('/login')
      ? loginRedirectState.from
      : '/';
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [knowledgeResetToken, setKnowledgeResetToken] = useState(0);
  const [auth, setAuth] = useState<AuthStatus | null>(null);
  const [authChecked, setAuthChecked] = useState(false);
  const [overview, setOverview] = useState<DashboardOverview>(fallbackOverview);
  const [profile, setProfile] = useState<EmployeeProfile>(fallbackEmployee);
  const [attendance, setAttendance] = useState<SelfAttendance>(fallbackAttendance);
  const [leave, setLeave] = useState<SelfLeave>(fallbackLeave);
  const [knowledge, setKnowledge] = useState<SelfKnowledge>(fallbackKnowledge);
  const [brandingSettings, setBrandingSettings] = useState<BrandingSettings>(() => readBrandingSettings());
  const [employeeCovers, setEmployeeCovers] = useState<EmployeeCoverMap>(() => readEmployeeCovers());
  const [correctionForm, setCorrectionForm] = useState({
    date: '2026-06-24',
    requested_start_at: '',
    requested_end_at: '18:00',
    reason: '',
  });
  const [leaveForm, setLeaveForm] = useState({
    leave_type: '1',
    date_from: '2026-07-15',
    date_to: '2026-07-19',
    reason: '',
  });

  async function loadAuthenticatedData() {
    const [dashboard, selfProfile, selfAttendance, selfLeave, selfKnowledge] = await Promise.all([
      api.overview(),
      api.selfProfile(),
      api.selfAttendance(),
      api.selfLeave(),
      api.selfKnowledge(),
    ]);
    setOverview(dashboard);
    setProfile(selfProfile);
    setAttendance(selfAttendance);
    setLeave(selfLeave);
    setKnowledge(selfKnowledge);
    if (selfLeave.leave_types[0]) {
      setLeaveForm((current) => ({ ...current, leave_type: String(selfLeave.leave_types[0].id) }));
    }
  }

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const authStatus = await api.authStatus();
        if (cancelled) return;
        setAuth(authStatus);

        if (authStatus.authenticated && authStatus.employee) {
          const [dashboard, selfProfile, selfAttendance, selfLeave, selfKnowledge] = await Promise.all([
            api.overview(),
            api.selfProfile(),
            api.selfAttendance(),
            api.selfLeave(),
            api.selfKnowledge(),
          ]);
          if (cancelled) return;
          setOverview(dashboard);
          setProfile(selfProfile);
          setAttendance(selfAttendance);
          setLeave(selfLeave);
          setKnowledge(selfKnowledge);
          if (selfLeave.leave_types[0]) {
            setLeaveForm((current) => ({ ...current, leave_type: String(selfLeave.leave_types[0].id) }));
          }
        }
      } catch {
        if (!cancelled) {
          setAuth({ authenticated: false, user: null, employee: null });
        }
      } finally {
        if (!cancelled) setAuthChecked(true);
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!authChecked) return;
    if (!auth?.authenticated && location.pathname !== '/login') {
      navigate('/login', {
        replace: true,
        state: { from: `${location.pathname}${location.search}${location.hash}` },
      });
      return;
    }
    if (auth?.authenticated && location.pathname === '/login') {
      navigate(loginRedirectPath, { replace: true, state: null });
    }
  }, [authChecked, auth?.authenticated, location.hash, location.pathname, location.search, loginRedirectPath, navigate]);

  useEffect(() => {
    const legacyPath = legacyHashPaths[location.hash];
    if (legacyPath) {
      navigate(legacyPath, { replace: true });
      return;
    }

    const redirectPath = removedRouteRedirect(location.pathname);
    if (redirectPath) {
      navigate(redirectPath, { replace: true });
    }
  }, [location.hash, location.pathname, navigate]);

  useEffect(() => {
    saveBrandingSettings(brandingSettings);
  }, [brandingSettings]);

  useEffect(() => {
    saveEmployeeCovers(employeeCovers);
  }, [employeeCovers]);

  function updateEmployeeCover(employeeId: number, cover: CoverCropResult) {
    setEmployeeCovers((current) => ({ ...current, [String(employeeId)]: cover }));
  }

  async function handleCorrectionSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const start = correctionForm.requested_start_at
      ? `${correctionForm.date}T${correctionForm.requested_start_at}:00`
      : undefined;
    const end = correctionForm.requested_end_at ? `${correctionForm.date}T${correctionForm.requested_end_at}:00` : undefined;
    let request: TimeCorrectionRequest;
    try {
      request = await api.createTimeCorrection({
        date: correctionForm.date,
        requested_start_at: start,
        requested_end_at: end,
        reason: correctionForm.reason,
      });
    } catch {
      request = {
        id: Date.now(),
        date: correctionForm.date,
        requested_start_at: start ?? null,
        requested_end_at: end ?? null,
        reason: correctionForm.reason,
        status: 'submitted',
        submitted_at: new Date().toISOString(),
        decided_at: null,
        decision_comment: '',
        created_at: new Date().toISOString(),
      };
    }
    setAttendance((current) => ({
      ...current,
      correction_requests: [request, ...current.correction_requests],
    }));
    setCorrectionForm((current) => ({ ...current, reason: '' }));
  }

  async function handleLeaveSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const leaveType = leave.leave_types.find((item) => String(item.id) === leaveForm.leave_type);
    let request: LeaveRequest;
    try {
      request = await api.createLeaveRequest({
        leave_type: Number(leaveForm.leave_type),
        date_from: leaveForm.date_from,
        date_to: leaveForm.date_to,
        reason: leaveForm.reason,
      });
    } catch {
      request = {
        id: Date.now(),
        leave_type: Number(leaveForm.leave_type),
        leave_type_name: leaveType?.name ?? 'Відпустка',
        date_from: leaveForm.date_from,
        date_to: leaveForm.date_to,
        reason: leaveForm.reason,
        status: 'submitted',
        submitted_at: new Date().toISOString(),
        decided_at: null,
        created_at: new Date().toISOString(),
      };
    }
    setLeave((current) => ({ ...current, requests: [request, ...current.requests] }));
    setLeaveForm((current) => ({ ...current, reason: '' }));
  }

  async function handleLoginSuccess(response: AuthLoginResponse) {
    setAuth({ authenticated: true, user: response.user, employee: response.employee });
    setProfile(profileFromAuthEmployee(response.employee));
    void loadAuthenticatedData().catch(() => {
      setProfile(profileFromAuthEmployee(response.employee));
    });
    navigate(loginRedirectPath, { replace: true, state: null });
  }

  async function handleLogout() {
    try {
      await api.logout();
    } catch {
      // Local session state is cleared even if the network request fails.
    }
    setAuth({ authenticated: false, user: null, employee: null });
    setProfile(fallbackEmployee);
    setAttendance(fallbackAttendance);
    setLeave(fallbackLeave);
    setKnowledge(fallbackKnowledge);
    navigate('/login', { replace: true });
  }

  function changeSection(nextSection: Section) {
    if (nextSection === 'knowledge') {
      setKnowledgeResetToken((current) => current + 1);
    }
    navigate(sectionPaths[nextSection]);
    setMobileMenuOpen(false);
  }

  const copy = getAppCopy(brandingSettings.language);
  const themeMode = normalizeTheme(brandingSettings.theme);
  const content: Record<Section, ReactNode> = {
    home: (
      <HomeView
        employee={profile}
        leaveRequests={leave.requests}
        onOpenLeave={() => changeSection('requests')}
        onOpenAttendance={() => changeSection('attendance')}
        onOpenKnowledge={() => changeSection('knowledge')}
        onOpenOrg={() => changeSection('org')}
        brandingSettings={brandingSettings}
        copy={copy}
      />
    ),
    notifications: <NotificationsView />,
    people: <PeopleView brandingSettings={brandingSettings} employeeCovers={employeeCovers} onEmployeeCoverChange={updateEmployeeCover} copy={copy} />,
    calendar: <CompanyCalendarView copy={copy} />,
    attendance: <AttendanceView copy={copy} brandingSettings={brandingSettings} employeeCovers={employeeCovers} />,
    requests: <RequestsView leave={leave} leaveForm={leaveForm} setLeaveForm={setLeaveForm} onSubmitLeave={handleLeaveSubmit} copy={copy} />,
    knowledge: <KnowledgeView knowledge={knowledge} resetToken={knowledgeResetToken} copy={copy} />,
    assets: <AssetsView copy={copy} />,
    reports: <UtilityView section="reports" overview={overview} copy={copy} />,
    org: <OrgView copy={copy} themeMode={themeMode} />,
    settings: <SettingsView brandingSettings={brandingSettings} onBrandingChange={setBrandingSettings} copy={copy} />,
    changelog: <ChangelogView onBack={() => changeSection('settings')} />,
  };

  const mobileNav = mobileItems.map((item) => sidebarItems.find((navItem) => navItem.section === item)).filter(Boolean) as Array<{
    section: Section;
    icon: LucideIcon;
  }>;
  const appThemeStyle = brandingThemeStyle(brandingSettings);

  if (!authChecked) {
    return <AuthLoadingView brandingSettings={brandingSettings} />;
  }

  if (!auth?.authenticated) {
    return <LoginView brandingSettings={brandingSettings} onSuccess={handleLoginSuccess} />;
  }

  return (
    <div className="app-shell" data-theme={themeMode} data-density="compact" style={appThemeStyle}>
      <Sidebar active={section} onChange={changeSection} brandingSettings={brandingSettings} copy={copy} />
      <div className="main-shell">
        <Topbar
          auth={auth}
          employee={profile}
          onOpenMobileMenu={() => setMobileMenuOpen(true)}
          onLogout={handleLogout}
          copy={copy}
        />
        {content[section]}
      </div>
      <MobileMenu
        active={section}
        isOpen={mobileMenuOpen}
        onChange={changeSection}
        onClose={() => setMobileMenuOpen(false)}
        brandingSettings={brandingSettings}
        copy={copy}
      />
      <nav className="bottom-nav" aria-label={copy.common.openMenu}>
        {mobileNav.map((item) => {
          const Icon = item.icon;
          return (
            <button
              key={item.section}
              type="button"
              className={section === item.section ? 'active' : ''}
              onClick={() => changeSection(item.section)}
            >
              <Icon size={21} />
              <span>{bottomNavLabel(copy, item.section)}</span>
            </button>
          );
        })}
      </nav>
    </div>
  );
}
