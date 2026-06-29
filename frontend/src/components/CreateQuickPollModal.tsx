import { useEffect, useMemo, useRef, useState } from 'react';
import { Plus, Send, Trash2, Users, X } from 'lucide-react';

import { api } from '../api/client';
import type { Announcement, AnnouncementCondition, AnnouncementPayload } from '../types/api';
import {
  ConditionRow,
  isCompleteCondition,
  type AnnouncementConditionOption,
} from './CreateAnnouncementModal';

export function CreateQuickPollModal({
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
  const [options, setOptions] = useState(announcement?.poll_options?.length ? announcement.poll_options : ['', '']);
  const [audience, setAudience] = useState<'all' | 'conditions'>(announcement?.audience_type ?? 'all');
  const [conditions, setConditions] = useState<AnnouncementCondition[]>(announcement?.conditions ?? []);
  const [notifyTelegram, setNotifyTelegram] = useState(announcement?.notify_telegram ?? true);
  const [preview, setPreview] = useState<{ count: number; sample: Array<{ id: number; full_name: string; avatar_url: string }> }>({ count: 0, sample: [] });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const dictCache = useRef<Record<string, AnnouncementConditionOption[]>>({});

  const previewConditions = useMemo(
    () => (audience === 'conditions' ? conditions.filter(isCompleteCondition) : []),
    [audience, conditions],
  );
  const validOptions = useMemo(() => options.map((option) => option.trim()).filter(Boolean), [options]);

  useEffect(() => {
    setTitle(announcement?.title ?? '');
    setOptions(announcement?.poll_options?.length ? announcement.poll_options : ['', '']);
    setAudience(announcement?.audience_type ?? 'all');
    setConditions(announcement?.conditions ?? []);
    setNotifyTelegram(announcement?.notify_telegram ?? true);
    setError('');
  }, [announcement?.id]);

  useEffect(() => {
    const t = setTimeout(() => {
      api
        .announcementAudiencePreview({ audience_type: audience, conditions: previewConditions })
        .then(setPreview)
        .catch(() => setPreview({ count: 0, sample: [] }));
    }, 300);
    return () => clearTimeout(t);
  }, [audience, previewConditions]);

  const updateOption = (index: number, value: string) => {
    setOptions((current) => current.map((option, idx) => (idx === index ? value : option)));
  };
  const addOption = () => setOptions((current) => [...current, '']);
  const removeOption = (index: number) => {
    setOptions((current) => (current.length <= 2 ? current : current.filter((_, idx) => idx !== index)));
  };
  const addCondition = () => setConditions((current) => [...current, { field: '', operator: '', value: [] }]);
  const updateCondition = (index: number, patch: Partial<AnnouncementCondition>) => {
    setConditions((current) => current.map((condition, idx) => (idx === index ? { ...condition, ...patch } : condition)));
  };
  const removeCondition = (index: number) => {
    setConditions((current) => current.filter((_, idx) => idx !== index));
  };

  const submit = async () => {
    if (saving) return;
    if (!title.trim()) {
      setError('Вкажіть питання опитування.');
      return;
    }
    if (validOptions.length < 2) {
      setError('Додайте щонайменше два варіанти відповіді.');
      return;
    }
    const incomplete = audience === 'conditions' && conditions.some((condition) => !isCompleteCondition(condition));
    if (incomplete) {
      setError('Заповніть або видаліть незавершені умови.');
      return;
    }
    setSaving(true);
    setError('');
    try {
      const payload: AnnouncementPayload = {
        kind: 'poll',
        title: title.trim(),
        body_html: '',
        poll_options: validOptions,
        audience_type: audience,
        conditions: audience === 'conditions' ? previewConditions : [],
        notify_telegram: notifyTelegram,
        notify_email: false,
        notify_web: true,
        allow_comments: false,
        scheduled_at: null,
      };
      const saved = isEdit && announcement
        ? await api.updateAnnouncement(announcement.id, payload)
        : await api.createAnnouncement(payload);
      onCreated(saved);
    } catch {
      setError('Не вдалося зберегти опитування.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="ann-modal-layer" role="dialog" aria-modal="true" aria-label={isEdit ? 'Редагувати швидке опитування' : 'Створити швидке опитування'}>
      <button type="button" className="ann-modal-backdrop" aria-label="Закрити" onClick={onClose} />
      <section className="ann-modal quick-poll-modal">
        <header className="ann-modal-head">
          <strong>{isEdit ? 'Редагувати швидке опитування' : 'Створити швидке опитування'}</strong>
          <button type="button" className="modal-close" aria-label="Закрити" onClick={onClose}>
            <X size={20} />
          </button>
        </header>

        <div className="ann-modal-body">
          <label className="ann-field">
            <span>Назва</span>
            <textarea
              className="people-data-input quick-poll-title-input"
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              placeholder="Задати питання"
              rows={2}
              autoFocus
            />
          </label>

          <div className="ann-field">
            <span>Варіанти</span>
            <div className="quick-poll-options">
              {options.map((option, index) => (
                <div key={index} className="quick-poll-option-row">
                  <textarea
                    className="people-data-input quick-poll-option-input"
                    value={option}
                    onChange={(event) => updateOption(index, event.target.value)}
                    placeholder="Додати опцію..."
                    rows={1}
                  />
                  {options.length > 2 ? (
                    <button type="button" className="quick-poll-option-delete" aria-label="Видалити опцію" onClick={() => removeOption(index)}>
                      <Trash2 size={16} />
                    </button>
                  ) : null}
                </div>
              ))}
              <button type="button" className="ann-add-condition quick-poll-add-option" onClick={addOption}>
                <Plus size={15} /> Додати опцію
              </button>
            </div>
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
              {conditions.map((condition, index) => (
                <ConditionRow
                  key={index}
                  condition={condition}
                  dictCache={dictCache}
                  onChange={(patch) => updateCondition(index, patch)}
                  onRemove={() => removeCondition(index)}
                />
              ))}
              <button type="button" className="ann-add-condition" onClick={addCondition}>
                <Plus size={15} /> Додати умову
              </button>
            </div>
          ) : null}

          <div className="ann-audience-count">
            <span className="ann-avatars">
              {preview.sample.map((person) => (
                <span key={person.id} className="ann-avatar" title={person.full_name}>
                  {person.avatar_url ? <img src={person.avatar_url} alt="" /> : <Users size={13} />}
                </span>
              ))}
            </span>
            <strong>{preview.count} людей</strong> відповідають обраним критеріям
          </div>

          <div className="ann-section-title">Налаштування</div>
          <div className="ann-settings">
            <label className="ann-check">
              <input type="checkbox" checked={notifyTelegram} onChange={(event) => setNotifyTelegram(event.target.checked)} />
              <Send size={15} /> Оповіщення в Telegram (через бота)
            </label>
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
