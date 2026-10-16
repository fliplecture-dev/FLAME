"""Bounded, self-contained HTML5 documents for isolated Interactive viewers."""
from html.parser import HTMLParser
import re

HTML_LIMIT = 2 * 1024 * 1024
# Embedded Rive runtimes need WASM compilation, not JavaScript eval or network access.
HTML_CSP = "default-src 'none'; script-src 'unsafe-inline' 'wasm-unsafe-eval'; style-src 'unsafe-inline'; img-src data:; media-src data:; font-src data:; connect-src 'none'; frame-src 'none'; worker-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'"


class InvalidInteractive(ValueError):
    pass


class DocumentCheck(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tags = set()

    def handle_starttag(self, tag, attrs):
        self.tags.add(tag)
        attributes = dict(attrs)
        if tag in {'iframe', 'frame', 'frameset', 'object', 'embed', 'base', 'form'}:
            raise InvalidInteractive('interactive_unsupported_element')
        if tag == 'meta' and (attributes.get('http-equiv') or '').lower() == 'refresh':
            raise InvalidInteractive('interactive_navigation_not_allowed')
        for name, value in attrs:
            if name in {'src', 'href', 'poster', 'action', 'formaction', 'srcset', 'xlink:href'} and value:
                if name == 'srcset' or not (value.startswith('#') or value.startswith('data:') and tag not in {'script', 'link', 'a'}):
                    raise InvalidInteractive('interactive_self_contained_required')

    handle_startendtag = handle_starttag


def validate_document(payload: bytes) -> str:
    if not payload or len(payload) > HTML_LIMIT:
        raise InvalidInteractive('interactive_document_size')
    try:
        document = payload.decode('utf-8-sig')
    except UnicodeDecodeError as exc:
        raise InvalidInteractive('interactive_utf8_required') from exc
    if '\x00' in document:
        raise InvalidInteractive('invalid_interactive_document')
    parser = DocumentCheck()
    parser.feed(document)
    parser.close()
    if not {'html', 'head', 'body'} <= parser.tags or not re.search(r'</body\s*>', document, re.I):
        raise InvalidInteractive('interactive_complete_html_required')
    return document


def isolated_document(payload: bytes) -> str:
    document = validate_document(payload)
    policy = f'<meta http-equiv="Content-Security-Policy" content="{HTML_CSP}">'
    return re.sub(r'(<head\b[^>]*>)', lambda match: match[0] + policy, document, count=1, flags=re.I)


def interactive_data(resource, storage):
    """JSON only: never issue an executable HTML signed URL on the app origin."""
    from app.modules.functional.resources.service import fail
    from app.modules.functional.resources.storage import StorageUnavailable
    if resource.type != 'interactive' or resource.mime_type != 'text/html' or not resource.storage_key:
        fail(404, 'interactive_document_unavailable')
    try:
        document = isolated_document(storage.read_document(resource.storage_key, HTML_LIMIT))
    except InvalidInteractive as exc:
        fail(422, str(exc))
    except StorageUnavailable:
        fail(503, 'resource_delivery_unavailable')
    return {'url': '', 'launch_mode': 'interactive', 'html_document': document,
            'version': resource.version, 'expires_at': None}
