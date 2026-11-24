"""Adaptador WSGI para solicitar vistas de Django sin sockets ni servidor HTTP."""

from dataclasses import dataclass
from http.cookies import SimpleCookie
from io import BytesIO
import json
from urllib.parse import quote, urlsplit

HOST = "biblioteca.local"
ORIGIN = f"https://{HOST}"
SCHEME = "biblioteca"
DESKTOP_ORIGIN = f"{SCHEME}://{HOST}"
BOOTSTRAP_CDN = "https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/"
ASSETS = "/_desktop/assets/"


@dataclass
class Result:
    status: int
    headers: dict
    body: bytes


class DjangoBridge:
    def __init__(self, application):
        self.application = application
        self.cookies = SimpleCookie()

    def dispatch(self, path, query="", method="GET", body=b"", headers=None):
        response_headers = {}
        status = 500

        def start_response(line, values, exc_info=None):
            nonlocal status
            status = int(line.split(" ", 1)[0])
            for name, value in values:
                if name.lower() == "set-cookie":
                    self.update_cookies(value)
                else:
                    response_headers[name.lower()] = value

        headers = {key.lower(): value for key, value in (headers or {}).items()}
        environ = {
            "REQUEST_METHOD": method,
            "SCRIPT_NAME": "",
            "PATH_INFO": path.encode("utf-8").decode("latin-1"),
            "QUERY_STRING": query,
            "SERVER_NAME": HOST,
            "SERVER_PORT": "443",
            "SERVER_PROTOCOL": "HTTP/1.1",
            "HTTP_HOST": HOST,
            "HTTP_ORIGIN": ORIGIN,
            "HTTP_REFERER": ORIGIN + quote(path),
            "HTTP_COOKIE": "; ".join(m.OutputString().split(";", 1)[0] for m in self.cookies.values()),
            "HTTP_ACCEPT": headers.get("accept", "*/*"),
            "HTTP_X_CSRFTOKEN": headers.get("x-csrftoken", ""),
            "CONTENT_TYPE": headers.get("content-type", ""),
            "CONTENT_LENGTH": str(len(body)),
            "wsgi.input": BytesIO(body),
            "wsgi.url_scheme": "https",
        }
        response = self.application(environ, start_response)
        try:
            content = b"".join(response)
        finally:
            response.close()

        if response_headers.get("content-type", "").startswith("text/html"):
            content = self.prepare_html(content)
        return Result(status, response_headers, b"" if method == "HEAD" else content)

    def update_cookies(self, header):
        incoming = SimpleCookie(header)
        for key, morsel in incoming.items():
            if morsel["max-age"] == "0" or not morsel.value:
                self.cookies.pop(key, None)
            else:
                self.cookies[key] = morsel

    def visible_cookies(self):
        return "; ".join(
            f"{key}={morsel.coded_value}" for key, morsel in self.cookies.items()
            if not morsel["httponly"]
        )

    def prepare_html(self, content):
        html = content.decode()
        html = html.replace(BOOTSTRAP_CDN + "css/bootstrap.min.css", ASSETS + "bootstrap.min.css")
        html = html.replace(BOOTSTRAP_CDN + "js/bootstrap.bundle.min.js", ASSETS + "bootstrap.bundle.min.js")
        cookies = json.dumps(self.visible_cookies()).replace("<", "\\u003c")
        initialization = f"<script>window.__bibliotecaCookies = {cookies};</script>"
        if "<head>" in html:
            html = html.replace("<head>", "<head>" + initialization, 1)
        else:
            html = initialization + html
        return html.encode()


def internal_target(value):
    target = urlsplit(value)
    if target.netloc or target.scheme:
        if (target.scheme, target.netloc) not in {(SCHEME, HOST), ("https", HOST)}:
            raise ValueError("Destino externo")
    if not target.path.startswith("/") or target.path.startswith("//"):
        raise ValueError("Ruta inválida")
    return target
