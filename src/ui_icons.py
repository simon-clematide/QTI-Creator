"""Small, consistent outline icons for application actions and metadata."""
from html import escape
from urllib.parse import quote

_PATHS = {
    'copy': '<rect x="8" y="8" width="13" height="13" rx="2"/><path d="M16 8V3H3v13h5"/>',
    'upload': '<path d="M12 16V3m-5 5 5-5 5 5M4 16v5h16v-5"/>',
    'download': '<path d="M12 3v13m-5-5 5 5 5-5M4 16v5h16v-5"/>',
    'refresh': '<path d="M20 7v5h-5M4 17v-5h5"/><path d="M6 6a8 8 0 0 1 13 2M18 18A8 8 0 0 1 5 16"/>',
    'expand': '<path d="M8 3H3v5m13-5h5v5M3 16v5h5m13-5v5h-5"/>',
    'close': '<path d="m6 6 12 12M6 18 18 6"/>',
    'edit': '<path d="m15 4 5 5M4 20l5-1L21 7l-5-5L4 14z"/>',
    'eye': '<path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/>',
    'learner': '<circle cx="12" cy="7" r="4"/><path d="M4 21v-2a8 8 0 0 1 16 0v2"/>',
    'hint': '<path d="M8 16c0-3-3-3-3-8a7 7 0 0 1 14 0c0 5-3 5-3 8M8 17h8m-7 4h6"/>',
    'feedback': '<path d="M3 3h18v14H8l-5 4z"/>',
    'trash': '<path d="M3 6h18M9 6V3h6v3M6 6l1 15h10l1-15M10 10v7m4-7v7"/>',
    'plus': '<path d="M12 4v16M4 12h16"/>',
}


def icon(name: str, label: str = '') -> str:
    attrs = f'role="img" aria-label="{escape(label, quote=True)}"' if label else 'aria-hidden="true"'
    return f'<svg xmlns="http://www.w3.org/2000/svg" class="ui-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" {attrs}>{_PATHS[name]}</svg>'


def button_icon_css() -> str:
    mappings = {
        '#btn_upload_file': 'upload', '#btn_upload_media_zip': 'upload',
        '#btn_download_package': 'download', '#btn_download_example_media': 'download',
        '#btn_refresh': 'refresh', '#btn_copy_prompt': 'copy', '#btn_editor_fs': 'expand', '#btn_preview_fs': 'expand',
        '#btn_editor_fs[title^="Exit"]': 'close', '#btn_preview_fs[title^="Exit"]': 'close',
    }
    rules = ['.ui-icon { width: 1rem; height: 1rem; flex: 0 0 1rem; vertical-align: -0.15em; display: inline-block; }']
    for selector, name in mappings.items():
        svg = icon(name).replace('currentColor', '#475569')
        uri = 'data:image/svg+xml,' + quote(svg)
        rules.append(f'{selector}::before {{ content: ""; display: inline-block; width: 1rem; height: 1rem; flex: 0 0 1rem; background: currentColor; mask: url("{uri}") center / contain no-repeat; }}')
    return '\n'.join(rules)
