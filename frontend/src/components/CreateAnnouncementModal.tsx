import { useEffect, useMemo, useRef, useState } from 'react';
import { X, Plus, Trash2, ChevronDown, Search, Send, Users, Check } from 'lucide-react';
import { api } from '../api/client';
import type { Announcement, AnnouncementCondition } from '../types/api';
import { RichTextEditor } from './RichTextEditor';

export type AnnouncementConditionOption = { id: number; name: string };
type Opt = AnnouncementConditionOption;
export type AnnouncementConditionOperator = Exclude<AnnouncementCondition['operator'], ''>;
type Operator = AnnouncementConditionOperator;
type CompleteCondition = AnnouncementCondition & { operator: Operator };
type FieldOption = {
  key: string;
  label: string;
  loader: () => Promise<Opt[]>;
  operators?: Operator[];
};

const toOpts = (p: Promise<{ items: Array<{ id: number; name: string }> }>): Promise<Opt[]> =>
  p.then((r) => r.items.map((o) => ({ id: o.id, name: o.name })));

const employeeOpts = (): Promise<Opt[]> =>
  api.employees({ status: 'active', compact: true, page_size: 500 }).then((result) =>
    result.items
      .map((employee) => ({ id: employee.id, name: employee.full_name || `${employee.last_name} ${employee.first_name}`.trim() }))
      .filter((employee) => employee.name)
      .sort((first, second) => first.name.localeCompare(second.name, 'uk')),
  );

const genderOpts = (): Promise<Opt[]> =>
  api.genders({ is_active: true, page_size: 200 }).then((result) =>
    result.items.map((gender) => ({ id: gender.id, name: gender.name || gender.code })).filter((gender) => gender.name),
  );

const noValueOptions = (): Promise<Opt[]> => Promise.resolve([]);
const selectOperators: Operator[] = ['is', 'is_not', 'is_not_empty', 'is_empty'];
const personOperators: Operator[] = ['is', 'is_not'];
const presenceOperators: Operator[] = ['is_not_empty', 'is_empty'];

export const ANNOUNCEMENT_FIELD_OPTIONS: FieldOption[] = [
  { key: 'instagram_url', label: 'URL-адреса Instagram', loader: noValueOptions, operators: presenceOperators },
  { key: 'employee_number', label: 'Ідентифікатор працівника', loader: noValueOptions, operators: presenceOperators },
  { key: 'first_name', label: "Ім'я", loader: noValueOptions, operators: presenceOperators },
  { key: 'probation_policy', label: 'Випр. термін закінчується', loader: () => toOpts(api.probationPolicies({ is_active: true, page_size: 500 })), operators: selectOperators },
  { key: 'birth_date', label: 'Дата народження', loader: noValueOptions, operators: presenceOperators },
  { key: 'hired_on', label: 'Дата початку', loader: noValueOptions, operators: presenceOperators },
  { key: 'department', label: 'Департамент', loader: () => toOpts(api.departments({ page_size: 500 })), operators: selectOperators },
  { key: 'email', label: 'Електронна пошта', loader: noValueOptions, operators: presenceOperators },
  { key: 'dismissed_on', label: 'Звільнено', loader: noValueOptions, operators: presenceOperators },
  { key: 'team', label: 'Команда', loader: () => toOpts(api.teams({ page_size: 500 })), operators: selectOperators },
  { key: 'employee', label: 'Конкретна особа', loader: employeeOpts },
  { key: 'clinic', label: 'Локація', loader: () => toOpts(api.locations({ page_size: 500 })), operators: selectOperators },
  { key: 'manager', label: 'Менеджер', loader: employeeOpts, operators: selectOperators },
  { key: 'phone2', label: 'Номер робочого телефону', loader: noValueOptions, operators: presenceOperators },
  { key: 'personal_email', label: 'Особиста ел. пошта', loader: noValueOptions, operators: presenceOperators },
  { key: 'position', label: 'Посада', loader: () => toOpts(api.positions({ page_size: 500 })), operators: selectOperators },
  { key: 'direct_reports', label: 'Прямі підлеглі', loader: employeeOpts, operators: personOperators },
  { key: 'direct_and_indirect_reports', label: 'Прямі та непрямі підлеглі', loader: employeeOpts, operators: personOperators },
  { key: 'last_name', label: 'Прізвище', loader: noValueOptions, operators: presenceOperators },
  { key: 'division', label: 'Підрозділ', loader: () => toOpts(api.divisions({ page_size: 500 })), operators: selectOperators },
  { key: 'job_level', label: 'Рівень', loader: () => toOpts(api.jobLevels({ page_size: 500 })), operators: selectOperators },
  { key: 'department_level', label: 'Рівень департаменту', loader: () => toOpts(api.departmentLevels({ page_size: 500 })), operators: selectOperators },
  { key: 'gender', label: 'Стать', loader: genderOpts, operators: selectOperators },
  { key: 'employment_type', label: 'Тип роботи', loader: () => toOpts(api.workTypes({ page_size: 500 })), operators: selectOperators },
];

export const ANNOUNCEMENT_OPERATOR_OPTIONS: Array<{ value: Operator; label: string }> = [
  { value: 'is', label: 'Є' },
  { value: 'is_not', label: 'Не є' },
  { value: 'is_not_empty', label: 'Не є порожнім' },
  { value: 'is_empty', label: 'Є порожнім' },
];

function operatorOptionsForField(field: string): Array<{ value: Operator; label: string }> {
  const allowed = FIELD_OPTIONS.find((option) => option.key === field)?.operators ?? (field === 'employee' ? personOperators : undefined);
  if (!allowed) return ANNOUNCEMENT_OPERATOR_OPTIONS;
  return ANNOUNCEMENT_OPERATOR_OPTIONS.filter((option) => allowed.includes(option.value));
}

export const announcementConditionNeedsValue = (op: AnnouncementCondition['operator']) => op === 'is' || op === 'is_not';
export const isCompleteAnnouncementCondition = (condition: AnnouncementCondition): condition is CompleteCondition =>
  Boolean(condition.field && condition.operator && (!announcementConditionNeedsValue(condition.operator) || condition.value.length));

const FIELD_OPTIONS = ANNOUNCEMENT_FIELD_OPTIONS;
const OPERATOR_OPTIONS = ANNOUNCEMENT_OPERATOR_OPTIONS;
const needsValue = announcementConditionNeedsValue;
export const isCompleteCondition = isCompleteAnnouncementCondition;

function toLocalInput(iso: string | null): string {
  if (!iso) return '';
  const d = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

export function CreateAnnouncementModal({
  onClose,
  onCreated,
  announcement,
}: {
  onClose: () => void;
  onCreated: (a: Announcement) => void;
  announcement?: Announcement | null;
}) {
  const isEdit = Boolean(announcement);
  const [title, setTitle] = useState(announcement?.title ?? '');
  const [bodyHtml, setBodyHtml] = useState(announcement?.body_html ?? '');
  const [audience, setAudience] = useState<'all' | 'conditions'>(announcement?.audience_type ?? 'all');
  const [conditions, setConditions] = useState<AnnouncementCondition[]>(announcement?.conditions ?? []);
  const [notifyTelegram, setNotifyTelegram] = useState(announcement?.notify_telegram ?? true);
  const [notifyWeb, setNotifyWeb] = useState(announcement?.notify_web ?? true);
  const [allowComments, setAllowComments] = useState(announcement?.allow_comments ?? false);
  const [schedule, setSchedule] = useState(Boolean(announcement?.scheduled_at));
  const [scheduledAt, setScheduledAt] = useState(toLocalInput(announcement?.scheduled_at ?? null));

  const [preview, setPreview] = useState<{ count: number; sample: Array<{ id: number; full_name: string; avatar_url: string }> }>({ count: 0, sample: [] });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  // Кеш довідників за ключем поля.
  const dictCache = useRef<Record<string, Opt[]>>({});
  const previewConditions = useMemo(
    () => (audience === 'conditions' ? conditions.filter(isCompleteCondition) : []),
    [audience, conditions],
  );

  // Лічильник аудиторії (debounced).
  useEffect(() => {
    const t = setTimeout(() => {
      api
        .announcementAudiencePreview({ audience_type: audience, conditions: previewConditions })
        .then(setPreview)
        .catch(() => setPreview({ count: 0, sample: [] }));
    }, 300);
    return () => clearTimeout(t);
  }, [audience, previewConditions]);

  const addCondition = () => setConditions((c) => [...c, { field: '', operator: '', value: [] }]);
  const removeCondition = (i: number) => setConditions((c) => c.filter((_, idx) => idx !== i));
  const updateCondition = (i: number, patch: Partial<AnnouncementCondition>) =>
    setConditions((c) => c.map((cond, idx) => (idx === i ? { ...cond, ...patch } : cond)));

  const submit = async () => {
    if (saving) return;
    if (!title.trim()) {
      setError('Вкажіть назву оголошення.');
      return;
    }
    const incomplete = audience === 'conditions' && conditions.some((condition) => !isCompleteCondition(condition));
    if (incomplete) {
      setError('Заповніть або видаліть незавершені умови.');
      return;
    }
    setSaving(true);
    setError('');
    const payload = {
      title: title.trim(),
      body_html: bodyHtml,
      audience_type: audience,
      conditions: audience === 'conditions' ? previewConditions : [],
      notify_telegram: notifyTelegram,
      notify_web: notifyWeb,
      allow_comments: allowComments,
      scheduled_at: schedule && scheduledAt ? new Date(scheduledAt).toISOString() : null,
    };
    try {
      const saved = isEdit && announcement
        ? await api.updateAnnouncement(announcement.id, payload)
        : await api.createAnnouncement(payload);
      onCreated(saved);
    } catch {
      setError('Не вдалося зберегти оголошення.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="ann-modal-layer" role="dialog" aria-modal="true" aria-label="Створити оголошення">
      <button type="button" className="ann-modal-backdrop" aria-label="Закрити" onClick={onClose} />
      <section className="ann-modal">
        <header className="ann-modal-head">
          <strong>{isEdit ? 'Редагувати оголошення' : 'Створити оголошення'}</strong>
          <button type="button" className="modal-close" aria-label="Закрити" onClick={onClose}>
            <X size={20} />
          </button>
        </header>

        <div className="ann-modal-body">
          <label className="ann-field">
            <span>Назва</span>
            <input className="people-data-input" value={title} onChange={(e) => setTitle(e.target.value)} autoFocus />
          </label>

          <div className="ann-field">
            <span>Зміст</span>
            <RichTextEditor value={bodyHtml} onChange={setBodyHtml} onUploadMedia={api.uploadAnnouncementMedia} />
          </div>

          <div className="ann-section-title">Призначено</div>
          <div className="ann-base-chip">Цикл зайнятості є <strong>Працюючі</strong></div>

          <div className="ann-audience-cards">
            <button type="button" className={`ann-audience-card${audience === 'conditions' ? ' active' : ''}`} onClick={() => setAudience('conditions')}>
              <span className="ann-radio">{audience === 'conditions' ? <span className="ann-radio-dot" /> : null}</span>
              <span><strong>Конкретні люди</strong><small>Виберіть людей на основі умов</small></span>
            </button>
            <button type="button" className={`ann-audience-card${audience === 'all' ? ' active' : ''}`} onClick={() => setAudience('all')}>
              <span className="ann-radio">{audience === 'all' ? <span className="ann-radio-dot" /> : null}</span>
              <span><strong>Усі</strong><small>Включає всіх людей</small></span>
            </button>
          </div>

          {audience === 'conditions' ? (
            <div className="ann-conditions">
              {conditions.map((cond, i) => (
                <ConditionRow
                  key={i}
                  condition={cond}
                  dictCache={dictCache}
                  onChange={(patch) => updateCondition(i, patch)}
                  onRemove={() => removeCondition(i)}
                />
              ))}
              <button type="button" className="ann-add-condition" onClick={addCondition}>
                <Plus size={15} /> Додати умову
              </button>
            </div>
          ) : null}

          <div className="ann-audience-count">
            <span className="ann-avatars">
              {preview.sample.map((p) => (
                <span key={p.id} className="ann-avatar" title={p.full_name}>
                  {p.avatar_url ? <img src={p.avatar_url} alt="" /> : <Users size={13} />}
                </span>
              ))}
            </span>
            <strong>{preview.count} людей</strong> відповідають обраним критеріям
          </div>

          <div className="ann-section-title">Налаштування</div>
          <div className="ann-settings">
            <label className="ann-check">
              <input type="checkbox" checked={notifyTelegram} onChange={(e) => setNotifyTelegram(e.target.checked)} />
              <Send size={15} /> Оповіщення в Telegram (через бота)
            </label>
            <label className="ann-check">
              <input type="checkbox" checked={notifyWeb} onChange={(e) => setNotifyWeb(e.target.checked)} />
              Надіслати веб повідомлення
            </label>
            <label className="ann-check">
              <input type="checkbox" checked={allowComments} onChange={(e) => setAllowComments(e.target.checked)} />
              Увімкнути коментарі
            </label>
            <label className="ann-check">
              <input type="checkbox" checked={schedule} onChange={(e) => setSchedule(e.target.checked)} />
              Запланувати
            </label>
            {schedule ? (
              <input
                type="datetime-local"
                className="people-data-input ann-schedule-input"
                value={scheduledAt}
                onChange={(e) => setScheduledAt(e.target.value)}
              />
            ) : null}
          </div>

          {error ? <p className="ann-error">{error}</p> : null}
        </div>

        <footer className="ann-modal-foot">
          <button type="button" className="ann-save" onClick={submit} disabled={saving}>
            {saving ? 'Збереження…' : 'Зберегти'}
          </button>
        </footer>
      </section>
    </div>
  );
}

export function ConditionRow({
  condition,
  dictCache,
  onChange,
  onRemove,
}: {
  condition: AnnouncementCondition;
  dictCache: React.MutableRefObject<Record<string, Opt[]>>;
  onChange: (patch: Partial<AnnouncementCondition>) => void;
  onRemove: () => void;
}) {
  const [options, setOptions] = useState<Opt[]>(condition.field ? dictCache.current[condition.field] || [] : []);
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const fieldDef = FIELD_OPTIONS.find((f) => f.key === condition.field);

  useEffect(() => {
    let alive = true;
    if (!condition.field || !fieldDef) {
      setOptions([]);
      setOpen(false);
      setQuery('');
      return () => {
        alive = false;
      };
    }
    if (dictCache.current[condition.field]) {
      setOptions(dictCache.current[condition.field]);
      return;
    }
    fieldDef?.loader().then((opts) => {
      if (!alive) return;
      dictCache.current[condition.field] = opts;
      setOptions(opts);
    }).catch(() => undefined);
    return () => {
      alive = false;
    };
  }, [condition.field, fieldDef]);

  useEffect(() => {
    setOpen(false);
    setQuery('');
  }, [condition.field, condition.operator]);

  const filtered = useMemo(
    () => options.filter((o) => o.name.toLowerCase().includes(query.toLowerCase())),
    [options, query],
  );
  const operatorOptions = operatorOptionsForField(condition.field);
  const selectedNames = options.filter((o) => condition.value.includes(o.id)).map((o) => o.name);
  const toggleValue = (id: number) =>
    onChange({ value: condition.value.includes(id) ? condition.value.filter((v) => v !== id) : [...condition.value, id] });

  return (
    <div className="ann-condition-row">
      <select
        className="ann-select"
        value={condition.field || ''}
        onChange={(e) => onChange({ field: e.target.value, operator: '', value: [] })}
      >
        <option value="" disabled>Оберіть поле</option>
        {FIELD_OPTIONS.map((f) => (
          <option key={f.key} value={f.key}>{f.label}</option>
        ))}
      </select>

      <select
        className="ann-select"
        value={condition.operator || ''}
        disabled={!condition.field}
        onChange={(e) => onChange({ operator: e.target.value as Operator, value: [] })}
      >
        <option value="" disabled>Оберіть умову</option>
        {operatorOptions.map((o) => (
          <option key={o.value} value={o.value}>{o.label}</option>
        ))}
      </select>

      {needsValue(condition.operator) ? (
        <div className="ann-value-wrap">
          <button type="button" className="ann-value-trigger" onClick={() => setOpen((v) => !v)}>
            <span className="ann-value-label">
              {selectedNames.length ? selectedNames.join(', ') : 'Оберіть значення'}
            </span>
            <ChevronDown size={14} />
          </button>
          {open ? (
            <>
              <button type="button" className="ann-value-backdrop" aria-hidden onClick={() => setOpen(false)} />
              <div className="ann-value-menu">
                <div className="ann-value-search">
                  <Search size={14} />
                  <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Пошук…" autoFocus />
                </div>
                <div className="ann-value-list">
                  {filtered.map((o) => (
                    <button key={o.id} type="button" className="ann-value-item" onClick={() => toggleValue(o.id)}>
                      <span className={`ann-checkbox${condition.value.includes(o.id) ? ' checked' : ''}`}>
                        {condition.value.includes(o.id) ? <Check size={12} /> : null}
                      </span>
                      {o.name}
                    </button>
                  ))}
                  {!filtered.length ? <p className="ann-value-empty">Нічого не знайдено</p> : null}
                </div>
              </div>
            </>
          ) : null}
        </div>
      ) : (
        <div className="ann-value-spacer" />
      )}

      <button type="button" className="ann-condition-del" onClick={onRemove} aria-label="Видалити умову">
        <Trash2 size={16} />
      </button>
    </div>
  );
}
