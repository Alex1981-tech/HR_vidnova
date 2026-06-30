import { useEffect, useState } from 'react';
import { Check, ChevronLeft, Folder, MoreHorizontal, Pencil, Plus, Search, Trash2, X } from 'lucide-react';
import { api } from '../../api/client';
import type { EmployeeDocumentFolder, EmployeeDocumentFolderPayload } from '../../types/api';

type ModalState = { mode: 'create' } | { mode: 'edit'; folder: EmployeeDocumentFolder } | null;

function FolderModal({
  initial,
  folders,
  onClose,
  onSave,
}: {
  initial: EmployeeDocumentFolder | null;
  folders: EmployeeDocumentFolder[];
  onClose: () => void;
  onSave: (payload: EmployeeDocumentFolderPayload) => Promise<void>;
}) {
  const [name, setName] = useState(initial?.name ?? '');
  const [description, setDescription] = useState(initial?.description ?? '');
  const [parent, setParent] = useState<string>(initial?.parent != null ? String(initial.parent) : '');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  // Не можна обрати саму себе батьком.
  const parentOptions = folders.filter((f) => f.id !== initial?.id);

  async function submit() {
    if (!name.trim()) {
      setError('Введіть ім’я папки');
      return;
    }
    setSaving(true);
    setError('');
    try {
      await onSave({
        name: name.trim(),
        description: description.trim(),
        parent: parent ? Number(parent) : null,
      });
    } catch {
      setError('Не вдалося зберегти. Спробуйте ще раз.');
      setSaving(false);
    }
  }

  return (
    <div className="people-data-modal-backdrop" role="dialog" aria-modal>
      <div className="people-data-modal">
        <div className="people-data-modal-head">
          <h2>{initial ? 'Редагувати папку' : 'Нова папка для документів'}</h2>
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
            <span>Опис</span>
            <textarea
              className="people-data-input"
              rows={2}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </label>
          <label className="people-data-modal-field">
            <span>Батьківська папка</span>
            <select className="people-data-input" value={parent} onChange={(e) => setParent(e.target.value)}>
              <option value="">— Немає —</option>
              {parentOptions.map((f) => (
                <option key={f.id} value={f.id}>
                  {f.name}
                </option>
              ))}
            </select>
          </label>
          <label className="people-data-modal-field doc-autoassign" title="Скоро">
            <input type="checkbox" disabled />
            <span>Увімкнути автопризначення документів за полями (скоро)</span>
          </label>
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

export function SettingsDocumentsView({ onBack }: { onBack: () => void }) {
  const [tab, setTab] = useState<'folders' | 'templates'>('folders');
  const [folders, setFolders] = useState<EmployeeDocumentFolder[]>([]);
  const [state, setState] = useState<'loading' | 'ok' | 'error'>('loading');
  const [search, setSearch] = useState('');
  const [modal, setModal] = useState<ModalState>(null);
  const [menuFor, setMenuFor] = useState<number | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<EmployeeDocumentFolder | null>(null);

  async function load() {
    setState('loading');
    try {
      const res = await api.documentFolders({ q: search, page_size: 200 });
      setFolders(res.items);
      setState('ok');
    } catch {
      setState('error');
    }
  }
  useEffect(() => {
    const handle = setTimeout(() => void load(), 250);
    return () => clearTimeout(handle);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search]);

  async function handleSave(payload: EmployeeDocumentFolderPayload) {
    if (modal?.mode === 'edit') {
      await api.updateDocumentFolder(modal.folder.id, payload);
    } else {
      await api.createDocumentFolder(payload);
    }
    setModal(null);
    await load();
  }

  async function handleDelete(folder: EmployeeDocumentFolder) {
    await api.deleteDocumentFolder(folder.id);
    setConfirmDelete(null);
    await load();
  }

  return (
    <main className="settings-page documents-settings-page">
      <header className="people-data-head">
        <div>
          <button type="button" className="settings-back-link" onClick={onBack}>
            <ChevronLeft size={17} />
            Назад
          </button>
          <h1>Папки документів</h1>
          <p>Керування папками та шаблонами документів для людей</p>
        </div>
        <div className="people-data-head-actions">
          <button type="button" className="primary-action" onClick={() => setModal({ mode: 'create' })}>
            <Plus size={15} />
            <span>Додати</span>
          </button>
        </div>
      </header>

      <div className="section-tabs people-data-tabs">
        <button type="button" className={tab === 'folders' ? 'active' : ''} onClick={() => setTab('folders')}>
          Папки
        </button>
        <button type="button" className={tab === 'templates' ? 'active' : ''} onClick={() => setTab('templates')}>
          Шаблони
        </button>
      </div>

      {tab === 'templates' ? (
        <p className="people-data-empty">Шаблони документів — скоро.</p>
      ) : (
        <>
          <div className="doc-search">
            <Search size={15} />
            <input placeholder="Пошук…" value={search} onChange={(e) => setSearch(e.target.value)} />
          </div>

          {state === 'loading' ? (
            <p className="people-data-empty">Завантаження…</p>
          ) : state === 'error' ? (
            <p className="people-data-empty">Не вдалося завантажити папки.</p>
          ) : folders.length === 0 ? (
            <p className="people-data-empty">Папок ще немає. Додайте першу.</p>
          ) : (
            <div className="doc-folder-table">
              <div className="doc-folder-head">
                <span>Ім’я</span>
                <span>Кількість документів</span>
                <span />
              </div>
              {folders.map((folder) => (
                <div className="doc-folder-row" key={folder.id}>
                  <div className="doc-folder-name">
                    <Folder size={16} />
                    <div>
                      <strong>{folder.name}</strong>
                      {folder.description ? <span>{folder.description}</span> : null}
                    </div>
                  </div>
                  <div className="doc-folder-count">{folder.document_count}</div>
                  <div className="doc-folder-actions">
                    <button
                      type="button"
                      className="icon-button"
                      aria-label="Дії"
                      onClick={() => setMenuFor(menuFor === folder.id ? null : folder.id)}
                    >
                      <MoreHorizontal size={16} />
                    </button>
                    {menuFor === folder.id ? (
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
                              setModal({ mode: 'edit', folder });
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
                              setConfirmDelete(folder);
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
        </>
      )}

      {modal ? (
        <FolderModal
          initial={modal.mode === 'edit' ? modal.folder : null}
          folders={folders}
          onClose={() => setModal(null)}
          onSave={handleSave}
        />
      ) : null}

      {confirmDelete ? (
        <div className="people-data-modal-backdrop" role="dialog" aria-modal>
          <div className="people-data-modal people-data-modal-sm">
            <div className="people-data-modal-head">
              <h2>Видалити папку?</h2>
              <button type="button" className="icon-button" onClick={() => setConfirmDelete(null)} aria-label="Закрити">
                <X size={18} />
              </button>
            </div>
            <div className="people-data-modal-body">
              <p>Видалити «{confirmDelete.name}»? Документи в ній не видаляться, а лишаться без папки.</p>
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
