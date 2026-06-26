import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  ChevronDown,
  ChevronLeft,
  ChevronUp,
  Folder,
  GripVertical,
  MoreHorizontal,
  Pencil,
  Plus,
  SquarePlus,
  Table2,
  Trash2,
} from 'lucide-react';

type FieldType = 'system' | 'text' | 'textarea' | 'number' | 'date' | 'select' | 'employee' | 'url';

type Field = {
  id: number;
  group: number;
  name: string;
  field_type: FieldType;
  is_system: boolean;
  system_key: string;
  is_enabled: boolean;
  is_required: boolean;
  show_in_summary: boolean;
  options: string[];
  help_text: string;
  order: number;
};

type FieldTable = { id: number; group: number; name: string; columns: unknown[]; is_enabled: boolean; order: number };

type Group = {
  id: number;
  tab: string;
  name: string;
  slug: string;
  is_system: boolean;
  order: number;
  group_fields: Field[];
  tables: FieldTable[];
};

const TABS: Array<{ key: string; label: string }> = [
  { key: 'personal', label: 'Особисте' },
  { key: 'work', label: 'Робота' },
  { key: 'compensation', label: 'Компенсація' },
];

const FIELD_TYPE_LABEL: Record<FieldType, string> = {
  system: 'Система',
  text: 'Однорядковий текст',
  textarea: 'Текст з багато рядків',
  number: 'Число',
  date: 'Дата',
  select: 'Список',
  employee: 'Вибір співробітника',
  url: 'Посилання',
};

const CUSTOM_TYPES: FieldType[] = ['text', 'textarea', 'number', 'date', 'select', 'employee', 'url'];

function getCookie(name: string): string {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  return parts.length === 2 ? parts.pop()?.split(';').shift() ?? '' : '';
}

async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const csrf = getCookie('hr_csrftoken') || getCookie('csrftoken');
  const res = await fetch(path, {
    credentials: 'include',
    headers: {
      Accept: 'application/json',
      ...(init.body ? { 'Content-Type': 'application/json' } : {}),
      ...(init.body && csrf ? { 'X-CSRFToken': csrf } : {}),
      ...(init.headers ?? {}),
    },
    ...init,
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  if (res.status === 204) return undefined as T;
  const text = await res.text();
  return text ? (JSON.parse(text) as T) : (undefined as T);
}

function AddFieldRow({ groupId, onAdded }: { groupId: number; onAdded: () => void }) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState('');
  const [type, setType] = useState<FieldType>('text');
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    if (!name.trim() || busy) return;
    setBusy(true);
    try {
      await apiFetch('/api/employees/fields/', {
        method: 'POST',
        body: JSON.stringify({ group: groupId, name: name.trim(), field_type: type, is_enabled: true }),
      });
      setName('');
      setType('text');
      setOpen(false);
      onAdded();
    } finally {
      setBusy(false);
    }
  };

  if (!open) {
    return (
      <button type="button" className="secondary-action people-data-add" onClick={() => setOpen(true)}>
        <Plus size={15} />
        <span>Поле</span>
      </button>
    );
  }
  return (
    <div className="people-data-add-form">
      <input
        className="people-data-input"
        placeholder="Назва поля"
        value={name}
        onChange={(e) => setName(e.target.value)}
        autoFocus
      />
      <select className="people-data-input" value={type} onChange={(e) => setType(e.target.value as FieldType)}>
        {CUSTOM_TYPES.map((t) => (
          <option key={t} value={t}>
            {FIELD_TYPE_LABEL[t]}
          </option>
        ))}
      </select>
      <button type="button" className="primary-action" onClick={submit} disabled={busy}>
        Додати
      </button>
      <button type="button" className="secondary-action" onClick={() => setOpen(false)}>
        Скасувати
      </button>
    </div>
  );
}

function FieldRow({ field, onToggle, onDelete }: { field: Field; onToggle: () => void; onDelete: () => void }) {
  return (
    <div className={`people-data-field${field.is_enabled ? '' : ' is-disabled'}`}>
      <div className="people-data-field-info">
        <span className="people-data-field-name">
          {field.name}
          {field.is_required ? ' *' : ''}
        </span>
        <span className="people-data-field-type">{FIELD_TYPE_LABEL[field.field_type]}</span>
      </div>
      <div className="people-data-field-actions">
        {!field.is_system ? (
          <button type="button" className="icon-button" aria-label="Видалити" onClick={onDelete}>
            <Trash2 size={15} />
          </button>
        ) : null}
        {!field.is_system ? (
          <button type="button" className="icon-button" aria-label="Редагувати">
            <Pencil size={15} />
          </button>
        ) : null}
        <button
          type="button"
          role="switch"
          aria-checked={field.is_enabled}
          className={`people-data-toggle${field.is_enabled ? ' on' : ''}`}
          onClick={onToggle}
        >
          <span />
        </button>
      </div>
    </div>
  );
}

function GroupCard({
  group,
  onChanged,
  onDragStart,
  onDragEnter,
  onDrop,
  dragging,
}: {
  group: Group;
  onChanged: () => void;
  onDragStart: () => void;
  onDragEnter: () => void;
  onDrop: () => void;
  dragging: boolean;
}) {
  const [open, setOpen] = useState(false);

  const toggleField = async (field: Field) => {
    await apiFetch(`/api/employees/fields/${field.id}/`, {
      method: 'PATCH',
      body: JSON.stringify({ is_enabled: !field.is_enabled }),
    });
    onChanged();
  };
  const deleteField = async (field: Field) => {
    await apiFetch(`/api/employees/fields/${field.id}/`, { method: 'DELETE' });
    onChanged();
  };

  return (
    <section
      className={`people-data-group${dragging ? ' is-dragging' : ''}`}
      draggable
      onDragStart={onDragStart}
      onDragEnter={onDragEnter}
      onDragOver={(e) => e.preventDefault()}
      onDrop={(e) => {
        e.preventDefault();
        onDrop();
      }}
    >
      <header className="people-data-group-head" onClick={() => setOpen((v) => !v)}>
        <span className="people-data-grip" aria-hidden>
          <GripVertical size={16} />
        </span>
        <strong>{group.name}</strong>
        <span className="people-data-group-head-actions">
          {open ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
          <MoreHorizontal size={18} />
        </span>
      </header>
      {open ? (
        <div className="people-data-group-body">
          <div className="people-data-section-head">
            <span>Поля</span>
            <AddFieldRow groupId={group.id} onAdded={onChanged} />
          </div>
          {group.group_fields.length ? (
            <div className="people-data-fields">
              {group.group_fields.map((field) => (
                <FieldRow
                  key={field.id}
                  field={field}
                  onToggle={() => toggleField(field)}
                  onDelete={() => deleteField(field)}
                />
              ))}
            </div>
          ) : (
            <p className="people-data-empty">У цій групі ще немає полів.</p>
          )}
        </div>
      ) : null}
    </section>
  );
}

export function PeopleDataSettingsView({ onBack }: { onBack: () => void }) {
  const [tab, setTab] = useState('personal');
  const [groups, setGroups] = useState<Group[]>([]);
  const [state, setState] = useState<'loading' | 'ready' | 'error'>('loading');

  const load = useCallback(() => {
    setState('loading');
    apiFetch<{ results: Group[] } | Group[]>(`/api/employees/field-groups/?tab=${tab}`)
      .then((data) => {
        setGroups(Array.isArray(data) ? data : data.results);
        setState('ready');
      })
      .catch(() => setState('error'));
  }, [tab]);

  useEffect(() => {
    load();
  }, [load]);

  const [dragId, setDragId] = useState<number | null>(null);

  const persistOrder = (ordered: Group[]) => {
    ordered.forEach((g, index) => {
      if (g.order !== index) {
        apiFetch(`/api/employees/field-groups/${g.id}/`, {
          method: 'PATCH',
          body: JSON.stringify({ order: index }),
        }).catch(() => undefined);
      }
    });
  };

  const handleDragEnter = (overId: number) => {
    if (dragId === null || dragId === overId) return;
    setGroups((prev) => {
      const from = prev.findIndex((g) => g.id === dragId);
      const to = prev.findIndex((g) => g.id === overId);
      if (from < 0 || to < 0) return prev;
      const next = [...prev];
      const [moved] = next.splice(from, 1);
      next.splice(to, 0, moved);
      return next;
    });
  };

  const handleDrop = () => {
    setGroups((prev) => {
      persistOrder(prev);
      return prev.map((g, index) => ({ ...g, order: index }));
    });
    setDragId(null);
  };

  const createGroup = async () => {
    await apiFetch('/api/employees/field-groups/', {
      method: 'POST',
      body: JSON.stringify({ tab, name: 'Нова група', order: 999 }),
    });
    load();
  };

  const totals = useMemo(() => {
    const fields = groups.reduce((sum, g) => sum + g.group_fields.length, 0);
    const tables = groups.reduce((sum, g) => sum + g.tables.length, 0);
    return { fields, tables };
  }, [groups]);

  const summaryChips = useMemo(
    () => groups.flatMap((g) => g.group_fields.filter((f) => f.show_in_summary)),
    [groups],
  );

  return (
    <main className="settings-page people-data-page">
      <button type="button" className="report-back" onClick={onBack}>
        <ChevronLeft size={16} />
        <span>Назад</span>
      </button>

      <header className="people-data-head">
        <div>
          <h1>Дані про людей</h1>
          <p>
            {totals.fields} полів · {totals.tables} таблиці
          </p>
        </div>
        <div className="people-data-head-actions">
          <button type="button" className="secondary-action" onClick={createGroup}>
            <Folder size={15} />
            <span>Нова група</span>
          </button>
          <button type="button" className="secondary-action">
            <Table2 size={15} />
            <span>Нова таблиця</span>
          </button>
          <button type="button" className="secondary-action">
            <SquarePlus size={15} />
            <span>Нове поле</span>
          </button>
        </div>
      </header>

      <div className="section-tabs people-data-tabs">
        {TABS.map((t) => (
          <button key={t.key} type="button" className={tab === t.key ? 'active' : ''} onClick={() => setTab(t.key)}>
            {t.label}
          </button>
        ))}
      </div>

      {state === 'loading' ? (
        <p className="people-data-empty">Завантаження…</p>
      ) : state === 'error' ? (
        <p className="people-data-empty">Не вдалося завантажити налаштування.</p>
      ) : (
        <div className="people-data-groups">
          <section className="people-data-summary">
            <strong>Головна</strong>
            <p>Налаштуйте віджет-підсумок в профілі ваших людей</p>
            <div className="people-data-chips">
              {summaryChips.length ? (
                summaryChips.map((f) => (
                  <span key={f.id} className="people-data-chip">
                    <i className="people-data-chip-dot" aria-hidden />
                    {f.name}
                  </span>
                ))
              ) : (
                <span className="people-data-empty">Немає полів у підсумку.</span>
              )}
            </div>
          </section>

          {groups.map((group) => (
            <GroupCard
              key={group.id}
              group={group}
              onChanged={load}
              dragging={dragId === group.id}
              onDragStart={() => setDragId(group.id)}
              onDragEnter={() => handleDragEnter(group.id)}
              onDrop={handleDrop}
            />
          ))}
        </div>
      )}
    </main>
  );
}
