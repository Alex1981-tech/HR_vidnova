import { useCallback, useEffect, useMemo, useState } from 'react';
import { ChevronLeft, Lock, Plus, Trash2, X } from 'lucide-react';

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
    <div className="roles-page">
      <div className="roles-head">
        <button type="button" className="icon-button" aria-label="Назад" onClick={onBack}>
          <ChevronLeft size={18} />
        </button>
        <h1 className="roles-title">Ролі та права доступу</h1>
        <button type="button" className="primary-action" onClick={() => setCreating(true)}>
          <Plus size={16} /> Нова роль
        </button>
      </div>

      {error ? <div className="roles-error">{error}</div> : null}
      {loading ? (
        <div className="roles-empty">Завантаження…</div>
      ) : (
        <div className="roles-list">
          <div className="roles-row roles-row-head">
            <span>Імʼя</span>
            <span>Тип</span>
            <span className="roles-col-count">Люди</span>
            <span className="roles-col-desc">Опис</span>
            <span />
          </div>
          {roles.map((role) => (
            <div
              key={role.id}
              className="roles-row roles-row-item"
              role="button"
              tabIndex={0}
              onClick={() => setSelected(role)}
              onKeyDown={(e) => e.key === 'Enter' && setSelected(role)}
            >
              <span className="roles-name">{role.name}</span>
              <span className={`roles-badge roles-badge-${role.type}`}>
                {role.type === 'system' ? 'Система' : 'Кастомна'}
              </span>
              <span className="roles-col-count">{role.people_count}</span>
              <span className="roles-col-desc">{role.description}</span>
              <span className="roles-row-actions">
                {role.type === 'custom' ? (
                  <button
                    type="button"
                    className="icon-button is-danger"
                    aria-label="Видалити роль"
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
                ) : (
                  <Lock size={14} className="roles-lock" aria-label="Системна роль" />
                )}
              </span>
            </div>
          ))}
        </div>
      )}

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
    </div>
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
  // code -> level ('' для atomic-вкл; 'view'/'edit' для graded; отсутствие = нет)
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
    <div className="roles-page">
      <div className="roles-head">
        <button type="button" className="icon-button" aria-label="Назад" onClick={onBack}>
          <ChevronLeft size={18} />
        </button>
        <div className="roles-editor-title">
          <h1 className="roles-title">{role.name}</h1>
          {role.description ? <p className="roles-editor-desc">{role.description}</p> : null}
        </div>
        <button type="button" className="primary-action" onClick={save} disabled={busy}>
          {busy ? 'Збереження…' : savedAt ? 'Збережено ✓' : 'Зберегти'}
        </button>
      </div>

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
  );
}
