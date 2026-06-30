import { useCallback, useEffect, useMemo, useState } from 'react';
import { ChevronLeft, Lock, Monitor, Plus, Search, Trash2, UserRound, X } from 'lucide-react';

import { accessApi, type PermissionCatalog, type Role, type RolePermission } from '../../api/access';

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
    </main>
  );
}
