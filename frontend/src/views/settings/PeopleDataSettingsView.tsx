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
  Trash2,
  X,
} from 'lucide-react';

type FieldType = 'system' | 'text' | 'textarea' | 'number' | 'date' | 'select' | 'employee' | 'url' | 'boolean';

type TableColumn = { key: string; label: string; type: FieldType; options?: string[] };

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

type FieldTable = { id: number; group: number; name: string; columns: TableColumn[]; is_enabled: boolean; order: number };

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
  boolean: 'Прапорець',
};

const CUSTOM_TYPES: FieldType[] = ['text', 'textarea', 'number', 'date', 'select', 'employee', 'url', 'boolean'];
// Типи стовпців таблиці (label у списку «Вибір однієї відповіді» = select)
const COLUMN_TYPES: FieldType[] = ['text', 'textarea', 'number', 'date', 'select', 'employee', 'url', 'boolean'];

function slugifyKey(label: string, existing: string[]): string {
  const base =
    label
      .toLowerCase()
      .replace(/[^a-z0-9а-яёіїєґ]+/gi, '_')
      .replace(/^_+|_+$/g, '')
      .slice(0, 40) || 'col';
  let key = base;
  let n = 2;
  while (existing.includes(key)) {
    key = `${base}_${n}`;
    n += 1;
  }
  return key;
}

function getCookie(name: string): string {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  return parts.length === 2 ? parts.pop()?.split(';').shift() ?? '' : '';
}

async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const csrf = getCookie('hr_csrftoken') || getCookie('csrftoken');
  const method = (init.method ?? 'GET').toUpperCase();
  const unsafe = !['GET', 'HEAD', 'OPTIONS', 'TRACE'].includes(method);
  const res = await fetch(path, {
    credentials: 'include',
    headers: {
      Accept: 'application/json',
      ...(init.body ? { 'Content-Type': 'application/json' } : {}),
      ...(unsafe && csrf ? { 'X-CSRFToken': csrf } : {}),
      ...(init.headers ?? {}),
    },
    ...init,
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  if (res.status === 204) return undefined as T;
  const text = await res.text();
  return text ? (JSON.parse(text) as T) : (undefined as T);
}

function GroupFormModal({
  title,
  initialName,
  onClose,
  onSave,
}: {
  title: string;
  initialName: string;
  onClose: () => void;
  onSave: (name: string) => Promise<void>;
}) {
  const [name, setName] = useState(initialName);
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    if (!name.trim() || busy) return;
    setBusy(true);
    try {
      await onSave(name.trim());
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="people-data-modal-layer" role="dialog" aria-modal="true" aria-label={title}>
      <button type="button" className="people-data-modal-backdrop" aria-label="Закрити" onClick={onClose} />
      <section className="people-data-modal">
        <header className="people-data-modal-head">
          <strong>{title}</strong>
          <button type="button" className="modal-close" aria-label="Закрити" onClick={onClose}>
            <X size={20} />
          </button>
        </header>
        <div className="people-data-modal-body">
          <label className="people-data-modal-field">
            <span>Ім'я</span>
            <input
              className="people-data-input"
              value={name}
              autoFocus
              onChange={(e) => setName(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') void submit();
              }}
            />
          </label>
        </div>
        <footer className="people-data-modal-foot">
          <button type="button" className="primary-action" onClick={submit} disabled={busy || !name.trim()}>
            Зберегти
          </button>
        </footer>
      </section>
    </div>
  );
}

function ConfirmDeleteModal({
  title,
  text,
  itemName,
  onCancel,
  onConfirm,
}: {
  title: string;
  text: string;
  itemName: string;
  onCancel: () => void;
  onConfirm: () => Promise<void>;
}) {
  const [busy, setBusy] = useState(false);
  const confirm = async () => {
    if (busy) return;
    setBusy(true);
    try {
      await onConfirm();
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="people-data-modal-layer" role="dialog" aria-modal="true" aria-label={title}>
      <button type="button" className="people-data-modal-backdrop" aria-label="Скасувати" onClick={onCancel} />
      <section className="people-data-modal">
        <header className="people-data-modal-head">
          <strong>{title}</strong>
          <button type="button" className="modal-close" aria-label="Скасувати" onClick={onCancel}>
            <X size={20} />
          </button>
        </header>
        <div className="people-data-modal-body">
          <p className="people-data-modal-text">{text}</p>
          <strong className="people-data-modal-target">{itemName}</strong>
        </div>
        <footer className="people-data-modal-foot">
          <button type="button" className="secondary-action" onClick={onCancel} disabled={busy}>
            Скасувати
          </button>
          <button type="button" className="danger-action" onClick={confirm} disabled={busy}>
            Видалити
          </button>
        </footer>
      </section>
    </div>
  );
}

function FieldEditModal({
  field,
  onClose,
  onSave,
}: {
  field: Field;
  onClose: () => void;
  onSave: (payload: { name: string; is_required: boolean; options: string[] }) => Promise<void>;
}) {
  const [name, setName] = useState(field.name);
  const [required, setRequired] = useState(field.is_required);
  const [options, setOptions] = useState<string[]>(field.options ?? []);
  const [busy, setBusy] = useState(false);
  const isSelect = field.field_type === 'select';

  const submit = async () => {
    if (!name.trim() || busy) return;
    setBusy(true);
    try {
      await onSave({
        name: name.trim(),
        is_required: required,
        options: isSelect ? options.map((o) => o.trim()).filter(Boolean) : field.options ?? [],
      });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="people-data-modal-layer" role="dialog" aria-modal="true" aria-label="Редагувати поле">
      <button type="button" className="people-data-modal-backdrop" aria-label="Закрити" onClick={onClose} />
      <section className="people-data-modal">
        <header className="people-data-modal-head">
          <strong>Редагувати поле</strong>
          <button type="button" className="modal-close" aria-label="Закрити" onClick={onClose}>
            <X size={20} />
          </button>
        </header>
        <div className="people-data-modal-body people-data-modal-body-stack">
          <label className="people-data-modal-field">
            <span>Назва</span>
            <input
              className="people-data-input"
              value={name}
              autoFocus
              onChange={(e) => setName(e.target.value)}
            />
          </label>
          <label className="people-data-modal-check">
            <input type="checkbox" checked={required} onChange={(e) => setRequired(e.target.checked)} />
            <span>Обов'язкове поле</span>
          </label>
          {isSelect ? (
            <div className="people-data-modal-options">
              <span className="people-data-modal-options-title">Варіанти списку</span>
              {options.map((opt, index) => (
                <div className="people-data-option-row" key={index}>
                  <input
                    className="people-data-input"
                    value={opt}
                    placeholder={`Варіант ${index + 1}`}
                    onChange={(e) =>
                      setOptions((prev) => prev.map((o, idx) => (idx === index ? e.target.value : o)))
                    }
                  />
                  <button
                    type="button"
                    className="icon-button"
                    aria-label="Прибрати варіант"
                    onClick={() => setOptions((prev) => prev.filter((_, idx) => idx !== index))}
                  >
                    <Trash2 size={15} />
                  </button>
                </div>
              ))}
              <button
                type="button"
                className="secondary-action"
                onClick={() => setOptions((prev) => [...prev, ''])}
              >
                <Plus size={15} />
                <span>Варіант</span>
              </button>
            </div>
          ) : null}
        </div>
        <footer className="people-data-modal-foot">
          <button type="button" className="secondary-action" onClick={onClose} disabled={busy}>
            Скасувати
          </button>
          <button type="button" className="primary-action" onClick={submit} disabled={busy || !name.trim()}>
            Зберегти
          </button>
        </footer>
      </section>
    </div>
  );
}

function NewFieldModal({
  groups,
  defaultGroupId,
  onClose,
  onSave,
}: {
  groups: Group[];
  defaultGroupId: number | null;
  onClose: () => void;
  onSave: (payload: { group: number; field_type: FieldType; name: string; help_text: string }) => Promise<void>;
}) {
  const [groupId, setGroupId] = useState<string>(defaultGroupId ? String(defaultGroupId) : '');
  const [type, setType] = useState<FieldType>('text');
  const [name, setName] = useState('');
  const [help, setHelp] = useState('');
  const [busy, setBusy] = useState(false);

  const canSave = Boolean(groupId) && Boolean(name.trim()) && !busy;

  const submit = async () => {
    if (!canSave) return;
    setBusy(true);
    try {
      await onSave({ group: Number(groupId), field_type: type, name: name.trim(), help_text: help.trim() });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="people-data-modal-layer" role="dialog" aria-modal="true" aria-label="Додати поле співробітника">
      <button type="button" className="people-data-modal-backdrop" aria-label="Закрити" onClick={onClose} />
      <section className="people-data-modal">
        <header className="people-data-modal-head">
          <strong>Додати поле співробітника</strong>
          <button type="button" className="modal-close" aria-label="Закрити" onClick={onClose}>
            <X size={20} />
          </button>
        </header>
        <div className="people-data-modal-body people-data-modal-body-stack">
          <label className="people-data-modal-field">
            <span>Група</span>
            <select className="people-data-input" value={groupId} onChange={(e) => setGroupId(e.target.value)}>
              <option value="" disabled>
                — Виберіть групу —
              </option>
              {groups.map((g) => (
                <option key={g.id} value={String(g.id)}>
                  {g.name}
                </option>
              ))}
            </select>
          </label>
          <label className="people-data-modal-field">
            <span>Тип</span>
            <select className="people-data-input" value={type} onChange={(e) => setType(e.target.value as FieldType)}>
              {CUSTOM_TYPES.map((t) => (
                <option key={t} value={t}>
                  {FIELD_TYPE_LABEL[t]}
                </option>
              ))}
            </select>
          </label>
          <label className="people-data-modal-field">
            <span>Ім'я</span>
            <input
              className="people-data-input"
              value={name}
              autoFocus
              onChange={(e) => setName(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') void submit();
              }}
            />
          </label>
          <label className="people-data-modal-field">
            <span className="people-data-modal-label-row">
              Опис <em>За бажанням</em>
            </span>
            <input className="people-data-input" value={help} onChange={(e) => setHelp(e.target.value)} />
          </label>
        </div>
        <footer className="people-data-modal-foot">
          <button type="button" className="primary-action" onClick={submit} disabled={!canSave}>
            Зберегти
          </button>
        </footer>
      </section>
    </div>
  );
}

function ColumnEditModal({
  initial,
  existingKeys,
  onClose,
  onSave,
}: {
  initial: TableColumn | null;
  existingKeys: string[];
  onClose: () => void;
  onSave: (column: TableColumn) => void;
}) {
  const [label, setLabel] = useState(initial?.label ?? '');
  const [type, setType] = useState<FieldType>(initial?.type ?? 'text');
  const [options, setOptions] = useState<string[]>(initial?.options ?? []);
  const isSelect = type === 'select';

  const submit = () => {
    if (!label.trim()) return;
    const key = initial?.key ?? slugifyKey(label, existingKeys);
    onSave({
      key,
      label: label.trim(),
      type,
      ...(isSelect ? { options: options.map((o) => o.trim()).filter(Boolean) } : {}),
    });
  };

  return (
    <div className="people-data-modal-layer people-data-modal-layer-top" role="dialog" aria-modal="true" aria-label="Стовпець таблиці">
      <button type="button" className="people-data-modal-backdrop" aria-label="Закрити" onClick={onClose} />
      <section className="people-data-modal people-data-modal-narrow">
        <header className="people-data-modal-head">
          <strong>{initial ? 'Редагувати стовпець' : 'Новий стовпець таблиці'}</strong>
          <button type="button" className="modal-close" aria-label="Закрити" onClick={onClose}>
            <X size={20} />
          </button>
        </header>
        <div className="people-data-modal-body people-data-modal-body-stack">
          <label className="people-data-modal-field">
            <span>Ім'я</span>
            <input className="people-data-input" value={label} autoFocus onChange={(e) => setLabel(e.target.value)} />
          </label>
          <label className="people-data-modal-field">
            <span>Тип</span>
            <select className="people-data-input" value={type} onChange={(e) => setType(e.target.value as FieldType)}>
              {COLUMN_TYPES.map((t) => (
                <option key={t} value={t}>
                  {FIELD_TYPE_LABEL[t]}
                </option>
              ))}
            </select>
          </label>
          {isSelect ? (
            <div className="people-data-modal-options">
              <span className="people-data-modal-options-title">Варіанти списку</span>
              {options.map((opt, index) => (
                <div className="people-data-option-row" key={index}>
                  <input
                    className="people-data-input"
                    value={opt}
                    placeholder={`Варіант ${index + 1}`}
                    onChange={(e) => setOptions((prev) => prev.map((o, idx) => (idx === index ? e.target.value : o)))}
                  />
                  <button
                    type="button"
                    className="icon-button"
                    aria-label="Прибрати варіант"
                    onClick={() => setOptions((prev) => prev.filter((_, idx) => idx !== index))}
                  >
                    <Trash2 size={15} />
                  </button>
                </div>
              ))}
              <button type="button" className="secondary-action" onClick={() => setOptions((prev) => [...prev, ''])}>
                <Plus size={15} />
                <span>Варіант</span>
              </button>
            </div>
          ) : null}
        </div>
        <footer className="people-data-modal-foot">
          <button type="button" className="primary-action" onClick={submit} disabled={!label.trim()}>
            Зберегти
          </button>
        </footer>
      </section>
    </div>
  );
}

function TableEditModal({
  groupName,
  initial,
  onClose,
  onSave,
}: {
  groupName: string;
  initial: FieldTable | null;
  onClose: () => void;
  onSave: (payload: { name: string; columns: TableColumn[] }) => Promise<void>;
}) {
  const [name, setName] = useState(initial?.name ?? '');
  const [columns, setColumns] = useState<TableColumn[]>(initial?.columns ?? []);
  const [columnModal, setColumnModal] = useState<{ index: number | null } | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    if (!name.trim() || busy) return;
    setBusy(true);
    try {
      await onSave({ name: name.trim(), columns });
    } finally {
      setBusy(false);
    }
  };

  const upsertColumn = (column: TableColumn) => {
    setColumns((prev) => {
      if (columnModal?.index == null) return [...prev, column];
      return prev.map((c, idx) => (idx === columnModal.index ? column : c));
    });
    setColumnModal(null);
  };

  return (
    <div className="people-data-modal-layer" role="dialog" aria-modal="true" aria-label="Таблиця">
      <button type="button" className="people-data-modal-backdrop" aria-label="Закрити" onClick={onClose} />
      <section className="people-data-modal">
        <header className="people-data-modal-head">
          <strong>{initial ? 'Редагувати таблицю' : 'Нова таблиця'}</strong>
          <button type="button" className="modal-close" aria-label="Закрити" onClick={onClose}>
            <X size={20} />
          </button>
        </header>
        <div className="people-data-modal-body people-data-modal-body-stack">
          <label className="people-data-modal-field">
            <span>Група</span>
            <input className="people-data-input" value={groupName} disabled readOnly />
          </label>
          <label className="people-data-modal-field">
            <span>Ім'я</span>
            <input className="people-data-input" value={name} autoFocus onChange={(e) => setName(e.target.value)} />
          </label>
          <div className="people-data-columns">
            {columns.map((col, index) => (
              <div className="people-data-column-row" key={col.key}>
                <div className="people-data-column-info">
                  <span className="people-data-column-name">{col.label}</span>
                  <span className="people-data-column-type">{FIELD_TYPE_LABEL[col.type]}</span>
                </div>
                <div className="people-data-column-actions">
                  <button type="button" className="icon-button" aria-label="Редагувати стовпець" onClick={() => setColumnModal({ index })}>
                    <Pencil size={14} />
                  </button>
                  <button
                    type="button"
                    className="icon-button"
                    aria-label="Видалити стовпець"
                    onClick={() => setColumns((prev) => prev.filter((_, idx) => idx !== index))}
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
            ))}
            {!columns.length ? <p className="people-data-empty">Ще немає стовпців.</p> : null}
          </div>
          <button type="button" className="secondary-action people-data-add" onClick={() => setColumnModal({ index: null })}>
            <Plus size={15} />
            <span>Додати стовпець</span>
          </button>
        </div>
        <footer className="people-data-modal-foot">
          <button type="button" className="primary-action" onClick={submit} disabled={busy || !name.trim()}>
            Зберегти
          </button>
        </footer>
      </section>
      {columnModal ? (
        <ColumnEditModal
          initial={columnModal.index == null ? null : columns[columnModal.index]}
          existingKeys={columns.map((c) => c.key)}
          onClose={() => setColumnModal(null)}
          onSave={upsertColumn}
        />
      ) : null}
    </div>
  );
}

function FieldRow({
  field,
  dragging,
  onToggle,
  onEdit,
  onDelete,
  onDragStart,
  onDragEnter,
  onDrop,
}: {
  field: Field;
  dragging: boolean;
  onToggle: () => void;
  onEdit: () => void;
  onDelete: () => void;
  onDragStart: () => void;
  onDragEnter: () => void;
  onDrop: () => void;
}) {
  return (
    <div
      className={`people-data-field${field.is_enabled ? '' : ' is-disabled'}${dragging ? ' is-dragging' : ''}`}
      draggable
      onDragStart={onDragStart}
      onDragEnter={onDragEnter}
      onDragOver={(e) => e.preventDefault()}
      onDrop={(e) => {
        e.preventDefault();
        onDrop();
      }}
    >
      <span className="people-data-field-grip" aria-hidden>
        <GripVertical size={14} />
      </span>
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
          <button type="button" className="icon-button" aria-label="Редагувати" onClick={onEdit}>
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
  onRename,
  onDelete,
  onAddField,
  onEditField,
  onAddTable,
  onEditTable,
  onDeleteTable,
  onDragStart,
  onDragEnter,
  onDrop,
  dragging,
}: {
  group: Group;
  onChanged: () => void;
  onRename: () => void;
  onDelete: () => void;
  onAddField: () => void;
  onEditField: (field: Field) => void;
  onAddTable: () => void;
  onEditTable: (table: FieldTable) => void;
  onDeleteTable: (table: FieldTable) => void;
  onDragStart: () => void;
  onDragEnter: () => void;
  onDrop: () => void;
  dragging: boolean;
}) {
  const [open, setOpen] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [fields, setFields] = useState<Field[]>(group.group_fields);
  const [fieldDragId, setFieldDragId] = useState<number | null>(null);

  useEffect(() => {
    setFields(group.group_fields);
  }, [group.group_fields]);

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

  const onFieldDragEnter = (overId: number) => {
    if (fieldDragId === null || fieldDragId === overId) return;
    setFields((prev) => {
      const from = prev.findIndex((f) => f.id === fieldDragId);
      const to = prev.findIndex((f) => f.id === overId);
      if (from < 0 || to < 0) return prev;
      const next = [...prev];
      const [moved] = next.splice(from, 1);
      next.splice(to, 0, moved);
      return next;
    });
  };

  const onFieldDrop = async () => {
    setFieldDragId(null);
    const changed = fields.filter((f, index) => f.order !== index);
    if (!changed.length) return;
    await Promise.all(
      fields.map((f, index) =>
        f.order === index
          ? null
          : apiFetch(`/api/employees/fields/${f.id}/`, {
              method: 'PATCH',
              body: JSON.stringify({ order: index }),
            }).catch(() => undefined),
      ),
    );
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
          <span className="people-data-group-menu-wrap">
            <button
              type="button"
              className="icon-button"
              aria-label="Дії групи"
              aria-haspopup="menu"
              aria-expanded={menuOpen}
              onClick={(e) => {
                e.stopPropagation();
                setMenuOpen((v) => !v);
              }}
            >
              <MoreHorizontal size={18} />
            </button>
            {menuOpen ? (
              <>
                <button
                  type="button"
                  className="people-data-menu-backdrop"
                  aria-hidden
                  tabIndex={-1}
                  onClick={(e) => {
                    e.stopPropagation();
                    setMenuOpen(false);
                  }}
                />
                <div className="people-data-menu" role="menu" onClick={(e) => e.stopPropagation()}>
                  <button
                    type="button"
                    role="menuitem"
                    onClick={() => {
                      setMenuOpen(false);
                      onRename();
                    }}
                  >
                    <Pencil size={14} />
                    <span>Перейменувати</span>
                  </button>
                  {!group.is_system ? (
                    <button
                      type="button"
                      role="menuitem"
                      className="is-danger"
                      onClick={() => {
                        setMenuOpen(false);
                        onDelete();
                      }}
                    >
                      <Trash2 size={14} />
                      <span>Видалити</span>
                    </button>
                  ) : null}
                </div>
              </>
            ) : null}
          </span>
        </span>
      </header>
      {open ? (
        <div className="people-data-group-body">
          <div className="people-data-section-head">
            <span>Поля</span>
            <button type="button" className="secondary-action people-data-add" onClick={onAddField}>
              <Plus size={15} />
              <span>Поле</span>
            </button>
          </div>
          {fields.length ? (
            <div className="people-data-fields">
              {fields.map((field) => (
                <FieldRow
                  key={field.id}
                  field={field}
                  dragging={fieldDragId === field.id}
                  onToggle={() => toggleField(field)}
                  onEdit={() => onEditField(field)}
                  onDelete={() => deleteField(field)}
                  onDragStart={() => setFieldDragId(field.id)}
                  onDragEnter={() => onFieldDragEnter(field.id)}
                  onDrop={onFieldDrop}
                />
              ))}
            </div>
          ) : (
            <p className="people-data-empty">У цій групі ще немає полів.</p>
          )}

          <div className="people-data-section-head">
            <span>Таблиці</span>
            <button type="button" className="secondary-action people-data-add" onClick={onAddTable}>
              <Plus size={15} />
              <span>Таблиця</span>
            </button>
          </div>
          {group.tables.length ? (
            <div className="people-data-tables">
              {group.tables.map((table) => (
                <div className="people-data-table-row" key={table.id}>
                  <span className="people-data-table-name">{table.name}</span>
                  <span className="people-data-table-cols">{table.columns.length} стовпців</span>
                  <div className="people-data-table-actions">
                    <button type="button" className="icon-button" aria-label="Редагувати таблицю" onClick={() => onEditTable(table)}>
                      <Pencil size={15} />
                    </button>
                    <button type="button" className="icon-button" aria-label="Видалити таблицю" onClick={() => onDeleteTable(table)}>
                      <Trash2 size={15} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="people-data-empty">У цій групі ще немає таблиць.</p>
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

  const load = useCallback(
    (silent = false) => {
      if (!silent) setState('loading');
      return apiFetch<{ results: Group[] } | Group[]>(`/api/employees/field-groups/?tab=${tab}`)
        .then((data) => {
          setGroups(Array.isArray(data) ? data : data.results);
          setState('ready');
        })
        .catch(() => {
          if (!silent) setState('error');
        });
    },
    [tab],
  );

  // Тихе оновлення після мутацій — без спінера, щоб список і розгорнуті групи не "дьоргались".
  const refresh = useCallback(() => load(true), [load]);

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

  const [groupModal, setGroupModal] = useState<{ mode: 'create' } | { mode: 'edit'; id: number; name: string } | null>(
    null,
  );
  const [deleteTarget, setDeleteTarget] = useState<Group | null>(null);

  const saveGroup = async (name: string) => {
    if (groupModal?.mode === 'edit') {
      await apiFetch(`/api/employees/field-groups/${groupModal.id}/`, {
        method: 'PATCH',
        body: JSON.stringify({ name }),
      });
    } else {
      await apiFetch('/api/employees/field-groups/', {
        method: 'POST',
        body: JSON.stringify({ tab, name, order: 999 }),
      });
    }
    setGroupModal(null);
    refresh();
  };

  const confirmDeleteGroup = async () => {
    if (!deleteTarget) return;
    await apiFetch(`/api/employees/field-groups/${deleteTarget.id}/`, { method: 'DELETE' });
    setDeleteTarget(null);
    refresh();
  };

  const [fieldModal, setFieldModal] = useState<Field | null>(null);

  const saveField = async (payload: { name: string; is_required: boolean; options: string[] }) => {
    if (!fieldModal) return;
    await apiFetch(`/api/employees/fields/${fieldModal.id}/`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
    setFieldModal(null);
    refresh();
  };

  const [newField, setNewField] = useState<{ groupId: number | null } | null>(null);

  const saveNewField = async (payload: {
    group: number;
    field_type: FieldType;
    name: string;
    help_text: string;
  }) => {
    await apiFetch('/api/employees/fields/', {
      method: 'POST',
      body: JSON.stringify({ ...payload, is_enabled: true }),
    });
    setNewField(null);
    refresh();
  };

  const [tableModal, setTableModal] = useState<{ group: Group; table: FieldTable | null } | null>(null);
  const [deleteTableTarget, setDeleteTableTarget] = useState<FieldTable | null>(null);

  const saveTable = async (payload: { name: string; columns: TableColumn[] }) => {
    if (!tableModal) return;
    if (tableModal.table) {
      await apiFetch(`/api/employees/field-tables/${tableModal.table.id}/`, {
        method: 'PATCH',
        body: JSON.stringify({ name: payload.name, columns: payload.columns }),
      });
    } else {
      await apiFetch('/api/employees/field-tables/', {
        method: 'POST',
        body: JSON.stringify({ group: tableModal.group.id, name: payload.name, columns: payload.columns, is_enabled: true }),
      });
    }
    setTableModal(null);
    refresh();
  };

  const confirmDeleteTable = async () => {
    if (!deleteTableTarget) return;
    await apiFetch(`/api/employees/field-tables/${deleteTableTarget.id}/`, { method: 'DELETE' });
    setDeleteTableTarget(null);
    refresh();
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
          <button type="button" className="secondary-action" onClick={() => setGroupModal({ mode: 'create' })}>
            <Folder size={15} />
            <span>Нова група</span>
          </button>
          <button type="button" className="secondary-action" onClick={() => setNewField({ groupId: null })}>
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
              onChanged={refresh}
              onRename={() => setGroupModal({ mode: 'edit', id: group.id, name: group.name })}
              onDelete={() => setDeleteTarget(group)}
              onAddField={() => setNewField({ groupId: group.id })}
              onEditField={(field) => setFieldModal(field)}
              onAddTable={() => setTableModal({ group, table: null })}
              onEditTable={(table) => setTableModal({ group, table })}
              onDeleteTable={(table) => setDeleteTableTarget(table)}
              dragging={dragId === group.id}
              onDragStart={() => setDragId(group.id)}
              onDragEnter={() => handleDragEnter(group.id)}
              onDrop={handleDrop}
            />
          ))}
        </div>
      )}

      {groupModal ? (
        <GroupFormModal
          title={groupModal.mode === 'edit' ? 'Редагувати групу' : 'Додати групу'}
          initialName={groupModal.mode === 'edit' ? groupModal.name : ''}
          onClose={() => setGroupModal(null)}
          onSave={saveGroup}
        />
      ) : null}

      {deleteTarget ? (
        <ConfirmDeleteModal
          title="Видалити групу"
          text="Групу буде видалено разом з усіма її полями. Цю дію не можна скасувати."
          itemName={deleteTarget.name}
          onCancel={() => setDeleteTarget(null)}
          onConfirm={confirmDeleteGroup}
        />
      ) : null}

      {fieldModal ? (
        <FieldEditModal field={fieldModal} onClose={() => setFieldModal(null)} onSave={saveField} />
      ) : null}

      {newField ? (
        <NewFieldModal
          groups={groups}
          defaultGroupId={newField.groupId}
          onClose={() => setNewField(null)}
          onSave={saveNewField}
        />
      ) : null}

      {tableModal ? (
        <TableEditModal
          groupName={tableModal.group.name}
          initial={tableModal.table}
          onClose={() => setTableModal(null)}
          onSave={saveTable}
        />
      ) : null}

      {deleteTableTarget ? (
        <ConfirmDeleteModal
          title="Видалити таблицю"
          text="Таблицю буде видалено разом зі стовпцями. Введені дані співробітників лишаться, але не показуватимуться."
          itemName={deleteTableTarget.name}
          onCancel={() => setDeleteTableTarget(null)}
          onConfirm={confirmDeleteTable}
        />
      ) : null}
    </main>
  );
}
