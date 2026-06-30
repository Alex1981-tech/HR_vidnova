"""Центральный HTML-санитайзер (P4).

Закрывает stored-XSS: весь rich-text (announcements, employee notes, knowledge)
проходит через этот allowlist на serializer boundary ДО сохранения в БД. Так
хранится уже безопасный HTML, независимо от того, как его потом рендерит клиент
(`dangerouslySetInnerHTML`) или сторонний потребитель API.

Allowlist сохраняет реальный функционал редактора: форматирование, ссылки,
картинки, <video>, галереи (button + data-ann-gallery-*) и YouTube-embed —
но только iframe с src https://www.youtube.com/embed/... (через attribute_filter).
Вырезается script/on*/style/srcdoc/прочие iframe/javascript:-URL.
"""

from __future__ import annotations

import re

import nh3

# Разрешённые теги (надмножество словаря RichTextEditor для всех типов контента).
ALLOWED_TAGS = {
    # текст
    "p", "br", "span", "div", "strong", "b", "em", "i", "u", "s", "strike",
    "del", "ins", "sub", "sup", "mark", "small", "blockquote", "code", "pre", "hr",
    # заголовки
    "h1", "h2", "h3", "h4", "h5", "h6",
    # списки
    "ul", "ol", "li",
    # ссылки/медиа
    "a", "img", "video", "source", "iframe", "figure", "figcaption",
    # галерея объявлений
    "button",
    # таблицы
    "table", "thead", "tbody", "tr", "td", "th", "caption", "colgroup", "col",
}

ALLOWED_ATTRIBUTES = {
    "*": {"class", "dir", "title"},
    # "rel" не указываем: nh3 управляет им через link_rel="noopener noreferrer".
    "a": {"href", "target", "name"},
    "img": {"src", "alt", "loading", "width", "height"},
    "video": {"src", "poster", "controls", "preload", "playsinline", "muted", "loop", "width", "height"},
    "source": {"src", "type"},
    "iframe": {"src", "allow", "allowfullscreen", "frameborder", "width", "height", "title"},
    "button": {"type", "aria-label"},
    "td": {"colspan", "rowspan"},
    "th": {"colspan", "rowspan", "scope"},
    "col": {"span"},
    "colgroup": {"span"},
}

# data-* атрибуты (нужны галереям объявлений) разрешаем по префиксу.
GENERIC_ATTRIBUTE_PREFIXES = {"data-"}

# Схемы URL. Относительные URL (например /media/...) разрешены отдельно (url_relative).
URL_SCHEMES = {"http", "https", "mailto", "tel"}

# iframe допускаем только для YouTube-embed.
_YOUTUBE_EMBED_RE = re.compile(r"^https://(www\.)?youtube(-nocookie)?\.com/embed/", re.IGNORECASE)


def _attribute_filter(tag: str, attr: str, value: str):
    """Дополнительный фильтр поверх allowlist.

    Возвращает значение для сохранения или None для удаления атрибута.
    """
    if tag == "iframe" and attr == "src":
        return value if _YOUTUBE_EMBED_RE.match(value or "") else None
    return value


def sanitize_rich_html(html: str | None) -> str:
    """Очищает rich-text HTML по allowlist. None/'' -> ''."""
    if not html:
        return ""
    return nh3.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        generic_attribute_prefixes=GENERIC_ATTRIBUTE_PREFIXES,
        attribute_filter=_attribute_filter,
        url_schemes=URL_SCHEMES,
        link_rel="noopener noreferrer",
        strip_comments=True,
    )
