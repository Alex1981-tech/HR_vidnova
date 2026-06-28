import { useEffect, useState } from 'react';
import {
  Check,
  ChevronLeft,
  ClipboardList,
  Gift,
  GripVertical,
  MoreHorizontal,
  Pencil,
  Plus,
  Trash2,
  X,
} from 'lucide-react';
import { api } from '../../api/client';
import type { LeaveType, LeaveTypePayload } from '../../types/api';
import { LEAVE_ICON_OPTIONS, LeaveTypeIcon } from '../../lib/leaveIcons';

const UNIT_OPTIONS: Array<{ value: string; label: string }> = [
  { value: 'days', label: 'Днях' },
  { value: 'hours', label: 'Годинах' },
];

const DEFAULT_COLOR = '#9e9cf7';

function unitSubtitle(unit: string): string {
  return unit === 'hours' ? 'Відстеження у годинах' : 'Відстеження у днях';
}

type ModalState = { mode: 'create' } | { mode: 'edit'; type: LeaveType } | null;

function LeaveTypeModal({
  initial,
  onClose,
  onSave,
}: {
  initial: LeaveType | null;
  onClose: () => void;
  onSave: (payload: LeaveTypePayload) => Promise<void>;
}) {
  const [name, setName] = useState(initial?.name ?? '');
  const [unit, setUnit] = useState(initial?.unit || 'days');
  const [icon, setIcon] = useState(initial?.icon || 'calendar');
  const [color, setColor] = useState(initial?.color || DEFAULT_COLOR);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  async function submit() {
    if (!name.trim()) {
      setError('Введіть ім’я типу');
      return;
    }
    setSaving(true);
    setError('');
    try {
      await onSave({ name: name.trim(), unit, icon, color });
    } catch {
      setError('Не вдалося зберегти. Спробуйте ще раз.');
      setSaving(false);
    }
  }

  return (
    <div className="people-data-modal-backdrop" role="dialog" aria-modal>
      <div className="people-data-modal">
        <div className="people-data-modal-head">
          <h2>{initial ? 'Редагувати тип відсутності' : 'Додати тип відсутності'}</h2>
          <button type="button" className="icon-button" onClick={onClose} aria-label="Закрити">
            <X size={18} />
          </button>
        </div>
        <div className="people-data-modal-body">
          <label className="people-data-modal-field">
            <span>Ім’я</span>
            <input className="people-data-input" value={name} onChange={(e) => setName(e.target.value)} autoFocus />
          </label>
          <label className="people-data-modal-field">
            <span>Одиниця відстеження часу</span>
            <select className="people-data-input" value={unit} onChange={(e) => setUnit(e.target.value)}>
              {UNIT_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </label>
          <div className="people-data-modal-field">
            <span>Іконка та колір</span>
            <div className="leave-icon-grid">
              {LEAVE_ICON_OPTIONS.map((opt) => (
                <button
                  type="button"
                  key={opt.key}
                  className={`leave-icon-option${icon === opt.key ? ' active' : ''}`}
                  title={opt.label}
                  onClick={() => setIcon(opt.key)}
                  style={icon === opt.key ? { color } : undefined}
                >
                  <opt.Icon size={18} />
                </button>
              ))}
            </div>
            <label className="leave-color-row">
              <span>з кольором</span>
              <input type="color" value={color} onChange={(e) => setColor(e.target.value)} />
            </label>
          </div>
          {error ? <p className="people-data-modal-error">{error}</p> : null}
        </div>
        <div className="people-data-modal-foot">
          <button type="button" className="secondary-action" onClick={onClose} disabled={saving}>
            Скасувати
          </button>
          <button type="button" className="primary-action" onClick={submit} disabled={saving}>
            <Check size={15} />
            {saving ? 'Збереження…' : 'Зберегти'}
          </button>
        </div>
      </div>
    </div>
  );
}

export function SettingsLeaveTypesView({ onBack }: { onBack: () => void }) {
  const [types, setTypes] = useState<LeaveType[]>([]);
  const [state, setState] = useState<'loading' | 'ok' | 'error'>('loading');
  const [modal, setModal] = useState<ModalState>(null);
  const [menuFor, setMenuFor] = useState<number | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<LeaveType | null>(null);
  const [dragId, setDragId] = useState<number | null>(null);

  async function load() {
    setState('loading');
    try {
      const res = await api.leaveTypes({ page_size: 100 });
      setTypes(res.items);
      setState('ok');
    } catch {
      setState('error');
    }
  }
  useEffect(() => {
    void load();
  }, []);

  async function handleSave(payload: LeaveTypePayload) {
    if (modal?.mode === 'edit') {
      await api.updateLeaveType(modal.type.id, payload);
    } else {
      await api.createLeaveType(payload);
    }
    setModal(null);
    await load();
  }

  async function handleDelete(type: LeaveType) {
    await api.deleteLeaveType(type.id);
    setConfirmDelete(null);
    await load();
  }

  function handleDrop(targetId: number) {
    if (dragId == null || dragId === targetId) {
      setDragId(null);
      return;
    }
    const ids = types.map((t) => t.id);
    const from = ids.indexOf(dragId);
    const to = ids.indexOf(targetId);
    if (from < 0 || to < 0) {
      setDragId(null);
      return;
    }
    ids.splice(to, 0, ids.splice(from, 1)[0]);
    const reordered = ids.map((id) => types.find((t) => t.id === id)!).filter(Boolean);
    setTypes(reordered);
    setDragId(null);
    void api.reorderLeaveTypes(ids).catch(() => load());
  }

  return (
    <main className="settings-page leave-types-page">
      <button type="button" className="report-back" onClick={onBack}>
        <ChevronLeft size={16} />
        <span>Назад</span>
      </button>

      <header className="people-data-head">
        <div>
          <h1>Типи відсутностей</h1>
          <p>{types.length} типів</p>
        </div>
        <div className="people-data-head-actions">
          <button type="button" className="secondary-action" disabled title="Скоро">
            <Gift size={15} />
            <span>Збори «Задонать відпустку»</span>
          </button>
          <button type="button" className="secondary-action" disabled title="Скоро">
            <ClipboardList size={15} />
            <span>Призначення</span>
          </button>
          <button type="button" className="primary-action" onClick={() => setModal({ mode: 'create' })}>
            <Plus size={15} />
            <span>Додати тип відсутності</span>
          </button>
        </div>
      </header>

      {state === 'loading' ? (
        <p className="people-data-empty">Завантаження…</p>
      ) : state === 'error' ? (
        <p className="people-data-empty">Не вдалося завантажити типи відсутностей.</p>
      ) : types.length === 0 ? (
        <p className="people-data-empty">Типів ще немає. Додайте перший.</p>
      ) : (
        <div className="leave-types-list">
          {types.map((type) => (
            <div
              key={type.id}
              className={`leave-type-row${dragId === type.id ? ' dragging' : ''}`}
              draggable
              onDragStart={() => setDragId(type.id)}
              onDragOver={(e) => e.preventDefault()}
              onDrop={() => handleDrop(type.id)}
            >
              <span className="leave-type-grip">
                <GripVertical size={16} />
              </span>
              <span className="leave-type-icon" style={type.color ? { color: type.color } : undefined}>
                <LeaveTypeIcon iconKey={type.icon} size={18} />
              </span>
              <div className="leave-type-info">
                <strong>{type.name}</strong>
                <span>{unitSubtitle(type.unit)}</span>
              </div>
              <div className="leave-type-actions">
                <button
                  type="button"
                  className="icon-button"
                  aria-label="Дії"
                  onClick={() => setMenuFor(menuFor === type.id ? null : type.id)}
                >
                  <MoreHorizontal size={16} />
                </button>
                {menuFor === type.id ? (
                  <>
                    <button
                      type="button"
                      className="leave-menu-backdrop"
                      aria-hidden
                      tabIndex={-1}
                      onClick={() => setMenuFor(null)}
                    />
                    <div className="leave-row-menu" role="menu">
                      <button
                        type="button"
                        onClick={() => {
                          setModal({ mode: 'edit', type });
                          setMenuFor(null);
                        }}
                      >
                        <Pencil size={14} />
                        Редагувати
                      </button>
                      <button
                        type="button"
                        className="danger"
                        onClick={() => {
                          setConfirmDelete(type);
                          setMenuFor(null);
                        }}
                      >
                        <Trash2 size={14} />
                        Видалити
                      </button>
                    </div>
                  </>
                ) : null}
              </div>
            </div>
          ))}
        </div>
      )}

      {modal ? (
        <LeaveTypeModal initial={modal.mode === 'edit' ? modal.type : null} onClose={() => setModal(null)} onSave={handleSave} />
      ) : null}

      {confirmDelete ? (
        <div className="people-data-modal-backdrop" role="dialog" aria-modal>
          <div className="people-data-modal people-data-modal-sm">
            <div className="people-data-modal-head">
              <h2>Видалити тип?</h2>
              <button type="button" className="icon-button" onClick={() => setConfirmDelete(null)} aria-label="Закрити">
                <X size={18} />
              </button>
            </div>
            <div className="people-data-modal-body">
              <p>
                Видалити «{confirmDelete.name}»? Якщо є пов’язані запити/баланси — видалення може бути заблоковане
                бекендом.
              </p>
            </div>
            <div className="people-data-modal-foot">
              <button type="button" className="secondary-action" onClick={() => setConfirmDelete(null)}>
                Скасувати
              </button>
              <button type="button" className="primary-action danger" onClick={() => void handleDelete(confirmDelete)}>
                <Trash2 size={15} />
                Видалити
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </main>
  );
}
