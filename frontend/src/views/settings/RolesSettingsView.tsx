import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  ChevronDown,
  ChevronLeft,
  Lock,
  MoreHorizontal,
  Monitor,
  Plus,
  Search,
  Trash2,
  UserRound,
  X,
} from 'lucide-react';

import {
  accessApi,
  type FieldAccessPayload,
  type MemberAction,
  type PermissionCatalog,
  type PermissionItem,
  type PickEmployee,
  type Role,
  type RoleMember,
  type RolePermission,
} from '../../api/access';

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
  const [tab, setTab] = useState<'company' | 'people'>('company');
  const [activeCat, setActiveCat] = useState(() => catalog.categories[0]?.key ?? '');
  const [fieldPayload, setFieldPayload] = useState<FieldAccessPayload | null>(null);
  const [fieldLevels, setFieldLevels] = useState<Map<string, string>>(new Map());

  useEffect(() => {
    let alive = true;
    accessApi
      .getFieldAccess(role.id)
      .then((payload) => {
        if (!alive) return;
        setFieldPayload(payload);
        const levels = new Map<string, string>();
        for (const t of payload.tabs)
          for (const g of t.groups)
            for (const row of [...g.fields, ...g.tables]) if (row.level) levels.set(row.code, row.level);
        setFieldLevels(levels);
      })
      .catch(() => {
        /* вкладка «Люди» необовʼязкова; ігноруємо помилку завантаження */
      });
    return () => {
      alive = false;
    };
  }, [role.id]);

  const setLevel = (code: string, level: string | null) => {
    setSavedAt(false);
    setGrants((prev) => {
      const next = new Map(prev);
      if (level === null) next.delete(code);
      else next.set(code, level);
      return next;
    });
  };

  const setFieldLevel = (code: string, level: string) => {
    setSavedAt(false);
    setFieldLevels((prev) => {
      const next = new Map(prev);
      if (level) next.set(code, level);
      else next.delete(code);
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
      const updated = await accessApi.setRolePermissions(role.id, items);
      if (fieldPayload) {
        const fieldItems = fieldPayload.tabs
          .flatMap((t) => t.groups)
          .flatMap((g) => [...g.fields, ...g.tables])
          .map((row) => ({ code: row.code, level: fieldLevels.get(row.code) ?? '' }));
        await accessApi.saveFieldAccess(role.id, fieldItems);
      }
      onSaved(updated);
      setSavedAt(true);
    } catch (e) {
      setErr(String(e instanceof Error ? e.message : e));
    } finally {
      setBusy(false);
    }
  };

  const category =
    catalog.categories.find((c) => c.key === activeCat) ?? catalog.categories[0] ?? null;

  return (
    <main className="settings-page settings-option-page role-editor-page">
      <header className="settings-option-header">
        <div>
          <button type="button" className="settings-back-link" onClick={onBack}>
            <ChevronLeft size={17} /> Назад
          </button>
          <h1>{role.name}</h1>
          {role.description ? <p className="roles-editor-desc">{role.description}</p> : null}
        </div>
      </header>

      <div className="role-editor-body">
        <div className="role-editor-tabs" role="tablist">
          <button
            type="button"
            role="tab"
            className={tab === 'company' ? 'is-on' : ''}
            onClick={() => setTab('company')}
          >
            Компанія
          </button>
          <button
            type="button"
            role="tab"
            className={tab === 'people' ? 'is-on' : ''}
            onClick={() => setTab('people')}
          >
            Люди
          </button>
        </div>

        {err ? <div className="roles-error">{err}</div> : null}

        {tab === 'company' ? (
          <>
            <p className="role-editor-hint">
              Права доступу, які застосовуються до дій, що ця роль може виконувати у компанії.
            </p>
            <div className="role-editor-layout">
              <nav className="role-cat-nav">
                {catalog.categories.map((c) => (
                  <button
                    key={c.key}
                    type="button"
                    className={c.key === (category?.key ?? '') ? 'is-on' : ''}
                    onClick={() => setActiveCat(c.key)}
                  >
                    {c.label}
                  </button>
                ))}
              </nav>
              <div className="role-perm-panel">
                {category?.sections.map((sec) => (
                  <section key={sec.key} className="role-perm-section">
                    {sec.label ? <h3 className="role-perm-section-title">{sec.label}</h3> : null}
                    <div className="roles-perm-rows">
                      {sec.permissions.map((perm) => (
                        <PermRow
                          key={perm.code}
                          perm={perm}
                          current={grants.has(perm.code) ? grants.get(perm.code)! : null}
                          present={grants.has(perm.code)}
                          onSet={setLevel}
                        />
                      ))}
                    </div>
                  </section>
                ))}
              </div>
            </div>
          </>
        ) : (
          <PeopleFieldsTab payload={fieldPayload} levels={fieldLevels} onSet={setFieldLevel} />
        )}
      </div>

      <footer className="role-editor-footer">
        <button type="button" className="secondary-action" onClick={onBack}>
          Скасувати
        </button>
        <button type="button" className="primary-action" onClick={save} disabled={busy}>
          {busy ? 'Збереження…' : savedAt ? 'Збережено ✓' : 'Зберегти'}
        </button>
      </footer>
    </main>
  );
}

function PermRow({
  perm,
  current,
  present,
  onSet,
}: {
  perm: PermissionItem;
  current: string | null;
  present: boolean;
  onSet: (code: string, level: string | null) => void;
}) {
  return (
    <div className="roles-perm-row">
      <div className="roles-perm-info">
        <span className="roles-perm-label">{perm.label}</span>
        {perm.description ? <span className="roles-perm-desc">{perm.description}</span> : null}
      </div>
      {perm.kind === 'graded' ? (
        <div className="roles-seg" role="group" aria-label={perm.label}>
          <button type="button" className={current === null ? 'is-on' : ''} onClick={() => onSet(perm.code, null)}>
            Немає
          </button>
          <button
            type="button"
            className={current === 'view' ? 'is-on' : ''}
            onClick={() => onSet(perm.code, 'view')}
          >
            Перегляд
          </button>
          <button
            type="button"
            className={current === 'edit' ? 'is-on' : ''}
            onClick={() => onSet(perm.code, 'edit')}
          >
            Редагування
          </button>
        </div>
      ) : (
        <label className="roles-check">
          <input
            type="checkbox"
            checked={present}
            onChange={(e) => onSet(perm.code, e.target.checked ? perm.on_level : null)}
          />
        </label>
      )}
    </div>
  );
}

function FieldSeg({
  level,
  onSet,
  label,
}: {
  level: string;
  onSet: (level: string) => void;
  label: string;
}) {
  return (
    <div className="roles-seg" role="group" aria-label={label}>
      <button type="button" className={!level ? 'is-on' : ''} onClick={() => onSet('')}>
        Немає
      </button>
      <button type="button" className={level === 'view' ? 'is-on' : ''} onClick={() => onSet('view')}>
        Перегляд
      </button>
      <button type="button" className={level === 'edit' ? 'is-on' : ''} onClick={() => onSet('edit')}>
        Редагування
      </button>
    </div>
  );
}

function PeopleFieldsTab({
  payload,
  levels,
  onSet,
}: {
  payload: FieldAccessPayload | null;
  levels: Map<string, string>;
  onSet: (code: string, level: string) => void;
}) {
  const [activeTab, setActiveTab] = useState('');
  const [open, setOpen] = useState<Set<number>>(new Set());

  const tabs = payload?.tabs ?? [];
  const current = tabs.find((t) => t.key === activeTab) ?? tabs[0] ?? null;

  if (!payload) return <p className="roles-empty">Завантаження…</p>;
  if (!tabs.length) return <p className="roles-empty">Немає налаштованих полів профілю.</p>;

  const toggleGroup = (id: number) =>
    setOpen((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });

  return (
    <>
      <p className="role-editor-hint">
        Налаштуйте, до яких даних і чиїх даних люди в цій ролі мають доступ.
      </p>
      <div className="role-editor-layout">
        <nav className="role-cat-nav">
          {tabs.map((t) => (
            <button
              key={t.key}
              type="button"
              className={t.key === (current?.key ?? '') ? 'is-on' : ''}
              onClick={() => setActiveTab(t.key)}
            >
              {t.label}
            </button>
          ))}
        </nav>
        <div className="role-perm-panel">
          {current && current.groups.length ? (
            current.groups.map((g) => {
              const expanded = open.has(g.id);
              return (
                <section key={g.id} className="role-acc">
                  <button type="button" className="role-acc-head" onClick={() => toggleGroup(g.id)}>
                    <span>{g.name}</span>
                    <ChevronDown size={18} className={expanded ? 'role-acc-chevron is-open' : 'role-acc-chevron'} />
                  </button>
                  {expanded ? (
                    <div className="role-acc-body">
                      {g.fields.length ? (
                        <>
                          <h4 className="role-acc-subtitle">Поля</h4>
                          <div className="roles-perm-rows">
                            {g.fields.map((row) => (
                              <div key={row.code} className="roles-perm-row">
                                <div className="roles-perm-info">
                                  <span className="roles-perm-label">{row.label}</span>
                                </div>
                                <FieldSeg
                                  label={row.label}
                                  level={levels.get(row.code) ?? ''}
                                  onSet={(lvl) => onSet(row.code, lvl)}
                                />
                              </div>
                            ))}
                          </div>
                        </>
                      ) : null}
                      {g.tables.length ? (
                        <>
                          <h4 className="role-acc-subtitle">Таблиці</h4>
                          <div className="roles-perm-rows">
                            {g.tables.map((row) => (
                              <div key={row.code} className="roles-perm-row">
                                <div className="roles-perm-info">
                                  <span className="roles-perm-label">{row.label}</span>
                                </div>
                                <FieldSeg
                                  label={row.label}
                                  level={levels.get(row.code) ?? ''}
                                  onSet={(lvl) => onSet(row.code, lvl)}
                                />
                              </div>
                            ))}
                          </div>
                        </>
                      ) : null}
                    </div>
                  ) : null}
                </section>
              );
            })
          ) : (
            <p className="roles-empty">У цій вкладці немає полів.</p>
          )}
        </div>
      </div>
    </>
  );
}
