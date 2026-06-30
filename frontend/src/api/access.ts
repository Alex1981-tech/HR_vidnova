// RBAC management API client (/api/access/). Самодостаточный модуль (Этап 7).

export type AccessLevel = 'view' | 'edit';

export type RolePermission = { permission_code: string; level: string };

export type Role = {
  id: number;
  slug: string;
  name: string;
  description: string;
  type: 'system' | 'custom';
  is_active: boolean;
  is_membership_computed: boolean;
  order: number;
  people_count: number;
  permissions: RolePermission[];
};

export type PermissionItem = {
  code: string;
  module: string;
  action: string;
  label: string;
  description: string;
  risk: 'low' | 'medium' | 'high' | 'critical';
  levels: AccessLevel[];
};

export type PermissionCatalog = { groups: Record<string, PermissionItem[]> };

export type PickEmployee = {
  id: number;
  full_name: string;
  position_name?: string;
  department_name?: string;
  clinic_name?: string;
  avatar_local_url?: string;
};

export type RoleMember = { employee_id: number; is_active: boolean };
export type MembersPayload = { members: RoleMember[]; people_count: number };
export type MemberAction = 'remove' | 'deactivate' | 'activate';

function getCookie(name: string): string {
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : '';
}

async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const unsafe = !['GET', 'HEAD', 'OPTIONS'].includes((init.method ?? 'GET').toUpperCase());
  const csrf = getCookie('hr_csrftoken') || getCookie('csrftoken');
  const res = await fetch(path, {
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...(unsafe && csrf ? { 'X-CSRFToken': csrf } : {}),
      ...(init.headers ?? {}),
    },
    ...init,
  });
  if (!res.ok) {
    let detail = `${res.status}`;
    try {
      const body = await res.json();
      detail = typeof body === 'object' ? JSON.stringify(body) : String(body);
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

function unwrap<T>(data: { results?: T[] } | T[]): T[] {
  return Array.isArray(data) ? data : data.results ?? [];
}

export const accessApi = {
  listRoles: () => apiFetch<{ results?: Role[] } | Role[]>('/api/access/roles/').then(unwrap),
  permissionCatalog: () => apiFetch<PermissionCatalog>('/api/access/permissions/'),
  createRole: (name: string, description = '') =>
    apiFetch<Role>('/api/access/roles/', {
      method: 'POST',
      body: JSON.stringify({ name, description }),
    }),
  updateRole: (id: number, patch: Partial<Pick<Role, 'name' | 'description' | 'is_active' | 'order'>>) =>
    apiFetch<Role>(`/api/access/roles/${id}/`, { method: 'PATCH', body: JSON.stringify(patch) }),
  deleteRole: (id: number) => apiFetch<void>(`/api/access/roles/${id}/`, { method: 'DELETE' }),
  setRolePermissions: (id: number, items: RolePermission[]) =>
    apiFetch<Role>(`/api/access/roles/${id}/set-permissions/`, {
      method: 'POST',
      body: JSON.stringify(items),
    }),
  getMembers: (id: number) =>
    apiFetch<MembersPayload>(`/api/access/roles/${id}/members/`),
  addMembers: (id: number, add: number[]) =>
    apiFetch<MembersPayload>(`/api/access/roles/${id}/members/`, {
      method: 'POST',
      body: JSON.stringify({ add }),
    }),
  memberAction: (id: number, employee_id: number, action: MemberAction) =>
    apiFetch<MembersPayload>(`/api/access/roles/${id}/member-action/`, {
      method: 'POST',
      body: JSON.stringify({ employee_id, action }),
    }),
  listEmployees: () =>
    apiFetch<{ results?: PickEmployee[] } | PickEmployee[]>(
      '/api/employees/employees/?compact=1&page_size=500',
    ).then(unwrap),
};
