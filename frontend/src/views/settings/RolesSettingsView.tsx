import { useCallback, useEffect, useMemo, useState } from 'react';
import { ChevronLeft, Lock, MoreHorizontal, Monitor, Plus, Search, Trash2, UserRound, X } from 'lucide-react';

import {
  accessApi,
  type MemberAction,
  type PermissionCatalog,
  type PickEmployee,
  type Role,
  type RoleMember,
  type RolePermission,
} from '../../api/access';

const GROUP_LABELS: Record<string, string> = {
  general: 'Загальні',
  hr: 'HR',
  pulse: 'Pulse',
  time: 'Час',
  reports: 'Звіти',
  settings: 'Налаштування',
  self: 'Власні дані',
};
const GROUP_ORDER = ['general', 'hr', 'time', 'reports', 'settings', 'self', 'pulse'];

type Props = { onBack: () => void };

export function RolesSettingsView({ onBack }: Props) {
  const [roles, setRoles] = useState<Role[]>([]);
  const [catalog, setCatalog] = useState<PermissionCatalog | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selected, setSelected] = useState<Role | null>(null);
  const [creating, setCreating] = useState(false);
  const [search, setSearch] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [r, c] = await Promise.all([accessApi.listRoles(), accessApi.permissionCatalog()]);
      setRoles(r);
      setCatalog(c);
    } catch (e) {
      setError(String(e instanceof Error ? e.message : e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const refreshRole = useCallback((updated: Role) => {
    setRoles((prev) => prev.map((r) => (r.id === updated.id ? updated : r)));
    setSelected((cur) => (cur && cur.id === updated.id ? updated : cur));
  }, []);

  const visible = useMemo(() => {
    const q = search.trim().toLowerCase();
    return q ? roles.filter((r) => r.name.toLowerCase().includes(q)) : roles;
  }, [roles, search]);

  if (selected && selected.slug === 'admin') {
    return <AdminRoleEditor role={selected} onBack={() => setSelected(null)} onSaved={refreshRole} />;
  }
  if (selected && catalog) {
    return (
      <RoleEditor
        role={selected}
        catalog={catalog}
        onBack={() => setSelected(null)}
        onSaved={refreshRole}
      />
    );
  }

  return (
    <main className="settings-page settings-option-page">
      <header className="settings-option-header">
        <div>
          <button type="button" className="settings-back-link" onClick={onBack}>
            <ChevronLeft size={17} /> Назад
          </button>
          <h1>Ролі та права доступу</h1>
        </div>
        <div className="settings-option-actions">
          <button type="button" className="primary-action" onClick={() => setCreating(true)}>
            <Plus size={18} /> Нова роль
          </button>
        </div>
      </header>

      <div className="settings-option-search">
        <Search size={18} />
        <input value={search} placeholder="Пошук" onChange={(e) => setSearch(e.target.value)} />
      </div>

      {error ? <div className="roles-error">{error}</div> : null}
      <div className="settings-option-meta">
        {loading ? 'Завантаження…' : `Відображено ${visible.length} з ${roles.length}`}
      </div>

      <section className="settings-option-table">
        {!loading && visible.length ? (
          <table>
            <thead>
              <tr>
                <th>Імʼя</th>
                <th>Тип</th>
                <th>Люди</th>
                <th>Опис</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {visible.map((role) => (
                <tr key={role.id} className="roles-trow-item" onClick={() => setSelected(role)}>
                  <td>
                    <div className="roles-name-cell">
                      {role.type === 'system' ? (
                        <span className="settings-option-lock" title="Системна роль">
                          <Lock size={15} />
                        </span>
                      ) : (
                        <span className="settings-option-spacer" />
                      )}
                      <span className="roles-name">{role.name}</span>
                    </div>
                  </td>
                  <td>
                    <span className="roles-type">
                      {role.type === 'system' ? <Monitor size={14} /> : <UserRound size={14} />}
                      {role.type === 'system' ? 'Система' : 'Кастомний'}
                    </span>
                  </td>
                  <td className="roles-col-count">{role.people_count}</td>
                  <td className="roles-col-desc">{role.description}</td>
                  <td className="roles-actions-cell">
                    {role.type === 'custom' ? (
                      <button
                        type="button"
                        className="roles-row-menu"
                        aria-label="Видалити роль"
                        title="Видалити"
                        onClick={(e) => {
                          e.stopPropagation();
                          void accessApi
                            .deleteRole(role.id)
                            .then(() => setRoles((prev) => prev.filter((r) => r.id !== role.id)))
                            .catch((err) => setError(String(err)));
                        }}
                      >
                        <Trash2 size={15} />
                      </button>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : !loading ? (
          <div className="roles-empty">Ролей не знайдено.</div>
        ) : null}
      </section>

      {creating ? (
        <CreateRoleModal
          onClose={() => setCreating(false)}
          onCreated={(role) => {
            setRoles((prev) => [...prev, role]);
            setCreating(false);
            setSelected(role);
          }}
        />
      ) : null}
    </main>
  );
}

function CreateRoleModal({ onClose, onCreated }: { onClose: () => void; onCreated: (r: Role) => void }) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');

  const submit = async () => {
    setBusy(true);
    setErr('');
    try {
      onCreated(await accessApi.createRole(name.trim(), description.trim()));
    } catch (e) {
      setErr(String(e instanceof Error ? e.message : e));
      setBusy(false);
    }
  };

  return (
    <div className="roles-modal-wrap">
      <button type="button" className="roles-modal-backdrop" aria-label="Закрити" onClick={onClose} />
      <div className="roles-modal" role="dialog" aria-modal="true">
        <div className="roles-modal-head">
          <span>Нова роль</span>
          <button type="button" className="modal-close" aria-label="Закрити" onClick={onClose}>
            <X size={18} />
          </button>
        </div>
        <div className="roles-modal-body">
          <label className="roles-field">
            <span>Назва</span>
            <input
              className="roles-input"
              value={name}
              autoFocus
              onChange={(e) => setName(e.target.value)}
              placeholder="Напр. Аудитори"
            />
          </label>
          <label className="roles-field">
            <span>Опис</span>
            <input
              className="roles-input"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Необовʼязково"
            />
          </label>
          {err ? <div className="roles-error">{err}</div> : null}
        </div>
        <div className="roles-modal-foot">
          <button type="button" className="secondary-action" onClick={onClose} disabled={busy}>
            Скасувати
          </button>
          <button type="button" className="primary-action" onClick={submit} disabled={busy || !name.trim()}>
            Створити
          </button>
        </div>
      </div>
    </div>
  );
}

function initials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase() ?? '')
    .join('');
}

function AdminRoleEditor({
  role,
  onBack,
  onSaved,
}: {
  role: Role;
  onBack: () => void;
  onSaved: (r: Role) => void;
}) {
  const [employees, setEmployees] = useState<PickEmployee[]>([]);
  const [members, setMembers] = useState<RoleMember[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');
  const [adding, setAdding] = useState(false);
  const [sortAsc, setSortAsc] = useState(true);
  const [menuOpenId, setMenuOpenId] = useState<number | null>(null);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    Promise.all([accessApi.listEmployees(), accessApi.getMembers(role.id)])
      .then(([emps, payload]) => {
        if (!alive) return;
        setEmployees(emps);
        setMembers(payload.members);
      })
      .catch((e) => alive && setErr(String(e instanceof Error ? e.message : e)))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [role.id]);

  useEffect(() => {
    if (menuOpenId === null) return;
    const close = () => setMenuOpenId(null);
    document.addEventListener('click', close);
    return () => document.removeEventListener('click', close);
  }, [menuOpenId]);

  const byId = useMemo(() => new Map(employees.map((e) => [e.id, e])), [employees]);
  const existingIds = useMemo(() => new Set(members.map((m) => m.employee_id)), [members]);
  const activeCount = useMemo(() => members.filter((m) => m.is_active).length, [members]);
  const rows = useMemo(() => {
    const dir = sortAsc ? 1 : -1;
    return members
      .map((m) => ({ ...m, emp: byId.get(m.employee_id) }))
      .filter((r): r is RoleMember & { emp: PickEmployee } => Boolean(r.emp))
      .sort((a, b) => dir * a.emp.full_name.localeCompare(b.emp.full_name, 'uk'));
  }, [members, byId, sortAsc]);

  const commit = async (op: () => Promise<{ members: RoleMember[]; people_count: number }>) => {
    setBusy(true);
    setErr('');
    try {
      const next = await op();
      setMembers(next.members);
      onSaved({ ...role, people_count: next.people_count });
    } catch (e) {
      setErr(String(e instanceof Error ? e.message : e));
    } finally {
      setBusy(false);
    }
  };

  const addMembers = (ids: number[]) => {
    setAdding(false);
    if (ids.length) commit(() => accessApi.addMembers(role.id, ids));
  };

  const act = (employeeId: number, action: MemberAction) => {
    setMenuOpenId(null);
    commit(() => accessApi.memberAction(role.id, employeeId, action));
  };

  return (
    <main className="settings-page settings-option-page">
      <header className="settings-option-header">
        <div>
          <button type="button" className="settings-back-link" onClick={onBack}>
            <ChevronLeft size={17} /> Назад
          </button>
          <h1>{role.name}</h1>
          <p className="roles-editor-desc">
            Адміністратори — суперкористувачі: повний доступ до всього й керування всіма даними.
          </p>
        </div>
        <div className="settings-option-actions">
          <button
            type="button"
            className="primary-action"
            onClick={() => setAdding(true)}
            disabled={busy || loading}
          >
            <Plus size={16} /> Додати
          </button>
        </div>
      </header>

      <div className="roles-editor-body">
        {err ? <div className="roles-error">{err}</div> : null}

        {loading ? (
          <p className="roles-empty">Завантаження…</p>
        ) : rows.length === 0 ? (
          <p className="roles-empty">Ще нікого не додано. Натисніть «Додати», щоб обрати адміністраторів.</p>
        ) : (
          <table className="settings-option-table roles-members-table">
            <thead>
              <tr>
                <th>
                  <button type="button" className="roles-sort-th" onClick={() => setSortAsc((v) => !v)}>
                    Повне імʼя {sortAsc ? '↑' : '↓'}
                  </button>
                </th>
                <th>Посада</th>
                <th>Департамент</th>
                <th>Локація</th>
                <th aria-label="Дії" />
              </tr>
            </thead>
            <tbody>
              {rows.map(({ emp, is_active }) => (
                <tr key={emp.id} className={is_active ? '' : 'muted'}>
                  <td>
                    <span className="roles-member-cell">
                      {emp.avatar_local_url ? (
                        <img className="roles-picker-avatar" src={emp.avatar_local_url} alt="" />
                      ) : (
                        <span className="roles-picker-avatar roles-picker-avatar-fallback">
                          {initials(emp.full_name)}
                        </span>
                      )}
                      <span className="roles-picker-name">{emp.full_name}</span>
                      {!is_active ? <span className="roles-inactive-badge">Неактивний</span> : null}
                    </span>
                  </td>
                  <td>{emp.position_name || '—'}</td>
                  <td>{emp.department_name || '—'}</td>
                  <td>{emp.clinic_name || '—'}</td>
                  <td className="roles-actions-cell">
                    <div className="settings-option-row-menu" onClick={(e) => e.stopPropagation()}>
                      <button
                        type="button"
                        className="settings-option-row-action"
                        aria-label="Дії"
                        disabled={busy}
                        onClick={() => setMenuOpenId((cur) => (cur === emp.id ? null : emp.id))}
                      >
                        <MoreHorizontal size={17} />
                      </button>
                      {menuOpenId === emp.id ? (
                        <div className="settings-option-row-popover">
                          {is_active ? (
                            <button type="button" onClick={() => act(emp.id, 'deactivate')}>
                              Деактивувати
                            </button>
                          ) : (
                            <button type="button" onClick={() => act(emp.id, 'activate')}>
                              Активувати
                            </button>
                          )}
                          <button type="button" className="danger" onClick={() => act(emp.id, 'remove')}>
                            Видалити
                          </button>
                        </div>
                      ) : null}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {!loading && rows.length > 0 ? (
          <p className="roles-picker-count">{pluralPeople(activeCount)}</p>
        ) : null}
      </div>

      {adding ? (
        <AddMembersModal
          employees={employees}
          existing={existingIds}
          onClose={() => setAdding(false)}
          onConfirm={addMembers}
        />
      ) : null}
    </main>
  );
}

function AddMembersModal({
  employees,
  existing,
  onClose,
  onConfirm,
}: {
  employees: PickEmployee[];
  existing: Set<number>;
  onClose: () => void;
  onConfirm: (ids: number[]) => void;
}) {
  const [search, setSearch] = useState('');
  const [picked, setPicked] = useState<Set<number>>(new Set());

  const candidates = useMemo(() => {
    const q = search.trim().toLowerCase();
    return employees
      .filter((e) => !existing.has(e.id))
      .filter((e) => (q ? e.full_name.toLowerCase().includes(q) : true));
  }, [employees, existing, search]);

  const toggle = (id: number) =>
    setPicked((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });

  return (
    <div className="roles-modal-wrap">
      <button type="button" className="roles-modal-backdrop" aria-label="Закрити" onClick={onClose} />
      <div className="roles-modal roles-modal-wide" role="dialog" aria-modal="true">
        <div className="roles-modal-head">
          <span>Додати адміністраторів</span>
          <button type="button" className="modal-close" aria-label="Закрити" onClick={onClose}>
            <X size={18} />
          </button>
        </div>
        <div className="roles-picker-search roles-modal-search">
          <Search size={16} />
          <input value={search} autoFocus placeholder="Пошук" onChange={(e) => setSearch(e.target.value)} />
        </div>
        <div className="roles-modal-list">
          {candidates.map((emp) => (
            <label key={emp.id} className="roles-picker-row">
              <input type="checkbox" checked={picked.has(emp.id)} onChange={() => toggle(emp.id)} />
              {emp.avatar_local_url ? (
                <img className="roles-picker-avatar" src={emp.avatar_local_url} alt="" />
              ) : (
                <span className="roles-picker-avatar roles-picker-avatar-fallback">{initials(emp.full_name)}</span>
              )}
              <span className="roles-picker-person">
                <span className="roles-picker-name">{emp.full_name}</span>
                {emp.position_name ? <span className="roles-picker-pos">{emp.position_name}</span> : null}
              </span>
            </label>
          ))}
          {candidates.length === 0 ? <div className="roles-picker-empty">Нікого не знайдено</div> : null}
        </div>
        <div className="roles-modal-foot">
          <button type="button" className="secondary-action" onClick={onClose}>
            Скасувати
          </button>
          <button
            type="button"
            className="primary-action"
            onClick={() => onConfirm([...picked])}
            disabled={picked.size === 0}
          >
            Додати{picked.size ? ` (${picked.size})` : ''}
          </button>
        </div>
      </div>
    </div>
  );
}

function pluralPeople(n: number): string {
  const mod10 = n % 10;
  const mod100 = n % 100;
  let word = 'осіб';
  if (mod10 === 1 && mod100 !== 11) word = 'особа';
  else if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) word = 'особи';
  return `Усього ${n} ${word}`;
}

function RoleEditor({
  role,
  catalog,
  onBack,
  onSaved,
}: {
  role: Role;
  catalog: PermissionCatalog;
  onBack: () => void;
  onSaved: (r: Role) => void;
}) {
  const [grants, setGrants] = useState<Map<string, string>>(
    () => new Map(role.permissions.map((p) => [p.permission_code, p.level])),
  );
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');
  const [savedAt, setSavedAt] = useState(false);

  const groups = useMemo(() => {
    const keys = Object.keys(catalog.groups);
    return [...keys].sort((a, b) => {
      const ia = GROUP_ORDER.indexOf(a);
      const ib = GROUP_ORDER.indexOf(b);
      return (ia < 0 ? 99 : ia) - (ib < 0 ? 99 : ib);
    });
  }, [catalog]);

  const setLevel = (code: string, level: string | null) => {
    setSavedAt(false);
    setGrants((prev) => {
      const next = new Map(prev);
      if (level === null) next.delete(code);
      else next.set(code, level);
      return next;
    });
  };

  const save = async () => {
    setBusy(true);
    setErr('');
    try {
      const items: RolePermission[] = [...grants.entries()].map(([permission_code, level]) => ({
        permission_code,
        level,
      }));
      onSaved(await accessApi.setRolePermissions(role.id, items));
      setSavedAt(true);
    } catch (e) {
      setErr(String(e instanceof Error ? e.message : e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="settings-page settings-option-page">
      <header className="settings-option-header">
        <div>
          <button type="button" className="settings-back-link" onClick={onBack}>
            <ChevronLeft size={17} /> Назад
          </button>
          <h1>{role.name}</h1>
          {role.description ? <p className="roles-editor-desc">{role.description}</p> : null}
        </div>
        <div className="settings-option-actions">
          <button type="button" className="primary-action" onClick={save} disabled={busy}>
            {busy ? 'Збереження…' : savedAt ? 'Збережено ✓' : 'Зберегти'}
          </button>
        </div>
      </header>

      <div className="roles-editor-body">
        {role.slug === 'admin' ? (
          <div className="roles-note">Адміністратор має повний доступ і не налаштовується через матрицю.</div>
        ) : null}
        {err ? <div className="roles-error">{err}</div> : null}

        <div className="roles-perm-groups">
        {groups.map((groupKey) => (
          <section key={groupKey} className="roles-perm-group">
            <h2 className="roles-perm-group-title">{GROUP_LABELS[groupKey] ?? groupKey}</h2>
            <div className="roles-perm-rows">
              {catalog.groups[groupKey].map((perm) => {
                const graded = perm.levels.length > 0;
                const current = grants.has(perm.code) ? grants.get(perm.code)! : null;
                return (
                  <div key={perm.code} className="roles-perm-row">
                    <div className="roles-perm-info">
                      <span className="roles-perm-label">
                        {perm.label}
                        {perm.risk === 'critical' || perm.risk === 'high' ? (
                          <span className={`roles-risk roles-risk-${perm.risk}`}>{perm.risk}</span>
                        ) : null}
                      </span>
                      <span className="roles-perm-desc">{perm.description}</span>
                    </div>
                    {graded ? (
                      <div className="roles-seg" role="group" aria-label={perm.label}>
                        <button
                          type="button"
                          className={current === null ? 'is-on' : ''}
                          onClick={() => setLevel(perm.code, null)}
                        >
                          Немає
                        </button>
                        <button
                          type="button"
                          className={current === 'view' ? 'is-on' : ''}
                          onClick={() => setLevel(perm.code, 'view')}
                        >
                          Перегляд
                        </button>
                        {perm.levels.includes('edit') ? (
                          <button
                            type="button"
                            className={current === 'edit' ? 'is-on' : ''}
                            onClick={() => setLevel(perm.code, 'edit')}
                          >
                            Редагування
                          </button>
                        ) : null}
                      </div>
                    ) : (
                      <label className="roles-check">
                        <input
                          type="checkbox"
                          checked={current !== null}
                          onChange={(e) => setLevel(perm.code, e.target.checked ? '' : null)}
                        />
                      </label>
                    )}
                  </div>
                );
              })}
            </div>
          </section>
        ))}
        </div>
      </div>
    </main>
  );
}
