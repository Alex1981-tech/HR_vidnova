import type { ChangeEvent } from 'react';
import { useEffect, useRef, useState } from 'react';
import { mergeAttributes, Node } from '@tiptap/core';
import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import Placeholder from '@tiptap/extension-placeholder';
import Link from '@tiptap/extension-link';
import Underline from '@tiptap/extension-underline';
import {
  Bold,
  Heading2,
  Heading3,
  ImagePlus,
  Images,
  Italic,
  Link as LinkIcon,
  List,
  ListOrdered,
  Loader2,
  Pilcrow,
  Quote,
  Redo2,
  Underline as UnderlineIcon,
  Undo2,
  Video,
  Youtube,
} from 'lucide-react';

type MediaUpload = {
  url: string;
  kind: 'image' | 'video';
  content_type: string;
  name?: string;
};

type GalleryImage = {
  url: string;
  name: string;
};

type Props = {
  value: string;
  onChange: (html: string) => void;
  placeholder?: string;
  onUploadMedia?: (file: File) => Promise<MediaUpload>;
};

const MediaImage = Node.create({
  name: 'mediaImage',
  group: 'block',
  atom: true,
  draggable: true,
  addAttributes() {
    return {
      src: { default: null },
      alt: { default: null },
      title: { default: null },
    };
  },
  parseHTML() {
    return [{ tag: 'img[src]' }];
  },
  renderHTML({ HTMLAttributes }) {
    return ['img', mergeAttributes(HTMLAttributes, { loading: 'lazy' })];
  },
});

const MediaGallery = Node.create({
  name: 'mediaGallery',
  group: 'block',
  atom: true,
  draggable: true,
  addAttributes() {
    return {
      images: {
        default: [],
        parseHTML: (element) => {
          try {
            const raw = element.getAttribute('data-images') || '[]';
            const parsed = JSON.parse(raw);
            return Array.isArray(parsed) ? parsed : [];
          } catch {
            return [];
          }
        },
      },
    };
  },
  parseHTML() {
    return [{ tag: 'div[data-ann-gallery]' }];
  },
  renderHTML({ node }) {
    const images = Array.isArray(node.attrs.images) ? node.attrs.images as GalleryImage[] : [];
    return [
      'div',
      {
        class: 'announcement-gallery',
        'data-ann-gallery': 'true',
        'data-images': JSON.stringify(images),
      },
      ['button', { type: 'button', class: 'announcement-gallery-arrow prev', 'data-ann-gallery-prev': 'true', 'aria-label': 'Попереднє фото' }, '‹'],
      [
        'div',
        { class: 'announcement-gallery-track', 'data-ann-gallery-track': 'true' },
        ...images.map((image, index) => [
          'figure',
          { class: 'announcement-gallery-slide' },
          ['img', { src: image.url, alt: image.name || `Фото ${index + 1}`, loading: 'lazy' }],
        ]),
      ],
      ['button', { type: 'button', class: 'announcement-gallery-arrow next', 'data-ann-gallery-next': 'true', 'aria-label': 'Наступне фото' }, '›'],
      [
        'div',
        { class: 'announcement-gallery-dots', 'data-ann-gallery-dots': 'true' },
        ...images.map((_, index) => [
          'button',
          {
            type: 'button',
            class: `announcement-gallery-dot${index === 0 ? ' active' : ''}`,
            'data-ann-gallery-dot': String(index),
            'aria-label': `Фото ${index + 1}`,
          },
          '',
        ]),
      ],
    ];
  },
});

const MediaVideo = Node.create({
  name: 'mediaVideo',
  group: 'block',
  atom: true,
  draggable: true,
  addAttributes() {
    return {
      src: { default: null },
      title: { default: null },
      type: { default: null },
    };
  },
  parseHTML() {
    return [{ tag: 'video[src]' }];
  },
  renderHTML({ HTMLAttributes }) {
    return [
      'video',
      mergeAttributes(HTMLAttributes, {
        controls: 'true',
        preload: 'metadata',
        playsinline: 'true',
      }),
    ];
  },
});

const YouTubeEmbed = Node.create({
  name: 'youtubeEmbed',
  group: 'block',
  atom: true,
  draggable: true,
  addAttributes() {
    return {
      src: { default: null },
      url: { default: null },
      title: { default: 'YouTube video' },
    };
  },
  parseHTML() {
    return [{ tag: 'iframe[src*="youtube.com/embed"]' }];
  },
  renderHTML({ HTMLAttributes }) {
    return [
      'iframe',
      mergeAttributes(HTMLAttributes, {
        class: 'announcement-youtube',
        loading: 'lazy',
        allow: 'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share',
        allowfullscreen: 'true',
        referrerpolicy: 'strict-origin-when-cross-origin',
      }),
    ];
  },
});

function getYouTubeEmbedUrl(input: string): string {
  const raw = input.trim();
  if (!raw) return '';
  try {
    const url = new URL(raw);
    const host = url.hostname.replace(/^www\./, '');
    let id = '';
    if (host === 'youtu.be') {
      id = url.pathname.split('/').filter(Boolean)[0] || '';
    } else if (host === 'youtube.com' || host === 'm.youtube.com' || host === 'music.youtube.com') {
      if (url.pathname.startsWith('/watch')) id = url.searchParams.get('v') || '';
      if (!id && url.pathname.startsWith('/shorts/')) id = url.pathname.split('/').filter(Boolean)[1] || '';
      if (!id && url.pathname.startsWith('/embed/')) id = url.pathname.split('/').filter(Boolean)[1] || '';
    }
    if (!/^[A-Za-z0-9_-]{6,}$/.test(id)) return '';
    return `https://www.youtube.com/embed/${id}`;
  } catch {
    return '';
  }
}

export function RichTextEditor({ value, onChange, placeholder, onUploadMedia }: Props) {
  const imageInputRef = useRef<HTMLInputElement | null>(null);
  const galleryInputRef = useRef<HTMLInputElement | null>(null);
  const videoInputRef = useRef<HTMLInputElement | null>(null);
  const [uploadingMedia, setUploadingMedia] = useState(false);
  const [mediaError, setMediaError] = useState('');
  const [youtubePanelOpen, setYoutubePanelOpen] = useState(false);
  const [youtubeUrl, setYoutubeUrl] = useState('');

  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        heading: { levels: [2, 3] },
      }),
      Link.configure({ openOnClick: false, HTMLAttributes: { rel: 'noopener noreferrer', target: '_blank' } }),
      Underline,
      MediaImage,
      MediaGallery,
      MediaVideo,
      YouTubeEmbed,
      Placeholder.configure({ placeholder: placeholder || 'Текст оголошення…' }),
    ],
    content: value || '',
    onUpdate: ({ editor }) => {
      const html = editor.getHTML();
      onChange(html === '<p></p>' ? '' : html);
    },
  });

  useEffect(() => {
    if (!editor) return;
    const current = editor.getHTML();
    const next = value || '<p></p>';
    if (current !== next && !editor.isFocused) {
      editor.commands.setContent(value || '', { emitUpdate: false });
    }
  }, [value, editor]);

  if (!editor) return null;

  const setLink = () => {
    const prev = editor.getAttributes('link').href as string | undefined;
    const raw = window.prompt('Посилання (URL):', prev || 'https://');
    if (raw === null) return;
    const trimmed = raw.trim();
    if (!trimmed || trimmed === 'https://') {
      editor.chain().focus().extendMarkRange('link').unsetLink().run();
      return;
    }
    const href = /^[a-z][a-z0-9+.-]*:/i.test(trimmed) ? trimmed : `https://${trimmed}`;
    editor.chain().focus().extendMarkRange('link').setLink({ href }).run();
  };

  const insertMedia = async (file: File, expectedKind: 'image' | 'video') => {
    if (!onUploadMedia || uploadingMedia) return;
    if (expectedKind === 'image' && !file.type.startsWith('image/')) {
      setMediaError('Оберіть файл зображення.');
      return;
    }
    if (expectedKind === 'video' && !file.type.startsWith('video/')) {
      setMediaError('Оберіть відеофайл.');
      return;
    }
    setUploadingMedia(true);
    setMediaError('');
    try {
      const media = await onUploadMedia(file);
      if (media.kind === 'image') {
        editor.chain().focus().insertContent({
          type: 'mediaImage',
          attrs: { src: media.url, alt: media.name || file.name, title: media.name || file.name },
        }).run();
      } else {
        editor.chain().focus().insertContent({
          type: 'mediaVideo',
          attrs: { src: media.url, title: media.name || file.name, type: media.content_type },
        }).run();
      }
    } catch {
      setMediaError('Не вдалося завантажити медіа.');
    } finally {
      setUploadingMedia(false);
    }
  };

  const insertGallery = async (files: File[]) => {
    if (!onUploadMedia || uploadingMedia || !files.length) return;
    const images = files.filter((file) => file.type.startsWith('image/'));
    if (!images.length) {
      setMediaError('Оберіть фото для альбому.');
      return;
    }
    setUploadingMedia(true);
    setMediaError('');
    try {
      const uploaded: GalleryImage[] = [];
      for (const file of images) {
        const media = await onUploadMedia(file);
        if (media.kind === 'image') uploaded.push({ url: media.url, name: media.name || file.name });
      }
      if (!uploaded.length) {
        setMediaError('Не вдалося завантажити фотоальбом.');
        return;
      }
      editor.chain().focus().insertContent({ type: 'mediaGallery', attrs: { images: uploaded } }).run();
    } catch {
      setMediaError('Не вдалося завантажити фотоальбом.');
    } finally {
      setUploadingMedia(false);
    }
  };

  const insertYouTube = () => {
    const src = getYouTubeEmbedUrl(youtubeUrl);
    if (!src) {
      setMediaError('Вставте коректне посилання YouTube.');
      return;
    }
    setMediaError('');
    editor.chain().focus().insertContent({
      type: 'youtubeEmbed',
      attrs: { src, url: youtubeUrl.trim(), title: 'YouTube video' },
    }).run();
    setYoutubeUrl('');
    setYoutubePanelOpen(false);
  };

  const onPickMedia = (event: ChangeEvent<HTMLInputElement>, kind: 'image' | 'video') => {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file) return;
    void insertMedia(file, kind);
  };

  const onPickGallery = (event: ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files || []);
    event.target.value = '';
    void insertGallery(files);
  };

  const btn = (active: boolean) => `rte-btn${active ? ' active' : ''}`;

  return (
    <div className="rte">
      <div className="rte-toolbar">
        <div className="rte-toolbar-group" aria-label="Стиль тексту">
          <button type="button" className={btn(editor.isActive('paragraph'))}
            onClick={() => editor.chain().focus().setParagraph().run()} title="Звичайний текст">
            <Pilcrow size={16} />
          </button>
          <button type="button" className={btn(editor.isActive('heading', { level: 2 }))}
            onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()} title="Заголовок H2">
            <Heading2 size={16} />
          </button>
          <button type="button" className={btn(editor.isActive('heading', { level: 3 }))}
            onClick={() => editor.chain().focus().toggleHeading({ level: 3 }).run()} title="Заголовок H3">
            <Heading3 size={16} />
          </button>
        </div>
        <span className="rte-sep" />
        <div className="rte-toolbar-group" aria-label="Форматування">
          <button type="button" className={btn(editor.isActive('bold'))}
            onClick={() => editor.chain().focus().toggleBold().run()} title="Жирний">
            <Bold size={16} />
          </button>
          <button type="button" className={btn(editor.isActive('italic'))}
            onClick={() => editor.chain().focus().toggleItalic().run()} title="Курсив">
            <Italic size={16} />
          </button>
          <button type="button" className={btn(editor.isActive('underline'))}
            onClick={() => editor.chain().focus().toggleUnderline().run()} title="Підкреслення">
            <UnderlineIcon size={16} />
          </button>
        </div>
        <span className="rte-sep" />
        <div className="rte-toolbar-group" aria-label="Списки">
          <button type="button" className={btn(editor.isActive('bulletList'))}
            onClick={() => editor.chain().focus().toggleBulletList().run()} title="Маркований список">
            <List size={16} />
          </button>
          <button type="button" className={btn(editor.isActive('orderedList'))}
            onClick={() => editor.chain().focus().toggleOrderedList().run()} title="Нумерований список">
            <ListOrdered size={16} />
          </button>
          <button type="button" className={btn(editor.isActive('blockquote'))}
            onClick={() => editor.chain().focus().toggleBlockquote().run()} title="Цитата">
            <Quote size={16} />
          </button>
        </div>
        <span className="rte-sep" />
        <div className="rte-toolbar-group" aria-label="Вставка">
          <button type="button" className={btn(editor.isActive('link'))} onClick={setLink} title="Посилання">
            <LinkIcon size={16} />
          </button>
          <button type="button" className="rte-btn" onClick={() => imageInputRef.current?.click()} title="Додати фото" disabled={uploadingMedia}>
            <ImagePlus size={16} />
          </button>
          <button type="button" className="rte-btn" onClick={() => galleryInputRef.current?.click()} title="Додати фотоальбом" disabled={uploadingMedia}>
            <Images size={16} />
          </button>
          <button type="button" className={btn(youtubePanelOpen)} onClick={() => setYoutubePanelOpen((v) => !v)} title="Додати YouTube" disabled={uploadingMedia}>
            <Youtube size={16} />
          </button>
          <button type="button" className="rte-btn" onClick={() => videoInputRef.current?.click()} title="Додати відеофайл" disabled={uploadingMedia}>
            <Video size={16} />
          </button>
        </div>
        <span className="rte-sep" />
        <div className="rte-toolbar-group" aria-label="Історія">
          <button type="button" className="rte-btn" onClick={() => editor.chain().focus().undo().run()} title="Скасувати">
            <Undo2 size={16} />
          </button>
          <button type="button" className="rte-btn" onClick={() => editor.chain().focus().redo().run()} title="Повторити">
            <Redo2 size={16} />
          </button>
        </div>
        {uploadingMedia ? (
          <span className="rte-uploading"><Loader2 size={14} /> Завантаження</span>
        ) : null}
      </div>
      <input
        ref={imageInputRef}
        className="rte-media-input"
        type="file"
        accept="image/*"
        onChange={(event) => onPickMedia(event, 'image')}
      />
      <input
        ref={galleryInputRef}
        className="rte-media-input"
        type="file"
        accept="image/*"
        multiple
        onChange={onPickGallery}
      />
      <input
        ref={videoInputRef}
        className="rte-media-input"
        type="file"
        accept="video/*"
        onChange={(event) => onPickMedia(event, 'video')}
      />
      {youtubePanelOpen ? (
        <div className="rte-youtube-panel">
          <input
            className="people-data-input"
            value={youtubeUrl}
            onChange={(event) => setYoutubeUrl(event.target.value)}
            placeholder="https://www.youtube.com/watch?v=..."
            autoFocus
          />
          <button type="button" className="secondary-action" onClick={() => setYoutubePanelOpen(false)}>
            Скасувати
          </button>
          <button type="button" className="primary-action compact" onClick={insertYouTube}>
            Додати
          </button>
        </div>
      ) : null}
      <EditorContent editor={editor} className="rte-content" />
      {mediaError ? <div className="rte-error">{mediaError}</div> : null}
    </div>
  );
}
