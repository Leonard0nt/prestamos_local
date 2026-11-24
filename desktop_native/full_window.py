"""Ventana Qt con las vistas originales y transporte interno hacia Django."""

import json
from pathlib import Path
from urllib.parse import unquote

from PySide6.QtCore import QByteArray, QBuffer, QFile, QIODevice, QObject, QUrl, Slot
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import (
    QWebEnginePage, QWebEngineProfile, QWebEngineScript, QWebEngineUrlRequestInfo,
    QWebEngineUrlRequestInterceptor,
    QWebEngineUrlRequestJob, QWebEngineUrlScheme, QWebEngineUrlSchemeHandler,
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from shiboken6 import delete

from .bridge import ASSETS, DESKTOP_ORIGIN, HOST, SCHEME, DjangoBridge, internal_target

FILES = Path(__file__).with_name("web_assets")
MIME_TYPES = {"bootstrap.min.css": b"text/css", "bootstrap.bundle.min.js": b"text/javascript"}
READ_ONLY = QIODevice.OpenModeFlag.ReadOnly


def register_scheme():
    scheme = QWebEngineUrlScheme(QByteArray(SCHEME.encode()))
    scheme.setSyntax(QWebEngineUrlScheme.Syntax.Host)
    scheme.setFlags(QWebEngineUrlScheme.Flag.SecureScheme | QWebEngineUrlScheme.Flag.LocalScheme)
    QWebEngineUrlScheme.registerScheme(scheme)


def is_internal(url):
    return url.scheme() == SCHEME and url.host() == HOST


class RequestInterceptor(QWebEngineUrlRequestInterceptor):
    def interceptRequest(self, info):
        url = info.requestUrl()
        embedded_image = (
            url.scheme() == "data"
            and info.resourceType() == QWebEngineUrlRequestInfo.ResourceType.ResourceTypeImage
        )
        if not (is_internal(url) or embedded_image):
            info.block(True)


class ResourceHandler(QWebEngineUrlSchemeHandler):
    def __init__(self, bridge, parent):
        super().__init__(parent)
        self.bridge = bridge

    def requestStarted(self, job):
        url = job.requestUrl()
        if not is_internal(url) or job.requestMethod() != b"GET":
            job.fail(QWebEngineUrlRequestJob.Error.RequestDenied)
            return
        path = url.path()
        filename = path.removeprefix(ASSETS)
        if path.startswith(ASSETS) and filename in MIME_TYPES:
            body, mime = (FILES / filename).read_bytes(), MIME_TYPES[filename]
        else:
            result = self.bridge.dispatch(path, url.query(QUrl.ComponentFormattingOption.FullyEncoded))
            if 300 <= result.status < 400 and "location" in result.headers:
                try:
                    target = internal_target(result.headers["location"])
                except ValueError:
                    job.fail(QWebEngineUrlRequestJob.Error.RequestDenied)
                    return
                destination = QUrl(DESKTOP_ORIGIN + target.path)
                destination.setQuery(target.query)
                job.redirect(destination)
                return
            body = result.body
            mime = result.headers.get("content-type", "text/plain").split(";")[0].encode()

        buffer = QBuffer(job)
        buffer.setData(QByteArray(body))
        buffer.open(READ_ONLY)
        job.reply(QByteArray(mime), buffer)


class RequestChannel(QObject):
    def __init__(self, bridge, parent):
        super().__init__(parent)
        self.bridge = bridge

    @Slot(str, result=str)
    def request(self, packed):
        try:
            if len(packed) > 1_000_000:
                raise ValueError("Solicitud demasiado grande")
            data = json.loads(packed)
            target = internal_target(data["target"])
            method = data["method"]
            if method not in {"GET", "HEAD", "POST", "PATCH", "PUT", "DELETE"}:
                raise ValueError("Método no permitido")
            result = self.bridge.dispatch(
                unquote(target.path), target.query, method, data["payload"].encode(), data["headers"],
            )
            payload = {
                "status": result.status,
                "headers": result.headers,
                "body": result.body.decode(errors="replace"),
            }
        except (KeyError, ValueError, AttributeError, TypeError):
            payload = {"status": 400, "headers": {}, "body": "Solicitud inválida."}

        payload["cookies"] = self.bridge.visible_cookies()
        return json.dumps(payload)


class LibraryBrowser(QWebEngineView):
    def __init__(self, application, config_path):
        super().__init__()
        self.setWindowTitle("Préstamos Biblioteca CSF")
        self.resize(1165, 740)
        self.profile = QWebEngineProfile("biblioteca", self)
        self.profile.setPersistentStoragePath(str(config_path.parent / "interfaz"))
        self.profile.setCachePath(str(config_path.parent / "cache-interfaz"))
        self.profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.MemoryHttpCache)
        self.profile.setUrlRequestInterceptor(RequestInterceptor(self.profile))
        bridge = DjangoBridge(application)
        self.profile.installUrlSchemeHandler(QByteArray(SCHEME.encode()), ResourceHandler(bridge, self.profile))

        page = QWebEnginePage(self.profile, self)
        self.setPage(page)
        self.channel = QWebChannel(page)
        self.channel.registerObject("django", RequestChannel(bridge, self.channel))
        page.setWebChannel(self.channel)

        channel_script = QFile(":/qtwebchannel/qwebchannel.js")
        if not channel_script.open(READ_ONLY):
            raise RuntimeError("No se encontró la biblioteca Qt WebChannel.")
        script = QWebEngineScript()
        script.setName("Biblioteca: transporte interno")
        script.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld.value)
        script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentCreation)
        script.setSourceCode(
            bytes(channel_script.readAll()).decode() + "\n" + (FILES / "bridge.js").read_text(encoding="utf-8")
        )
        page.scripts().insert(script)
        self.load(QUrl(DESKTOP_ORIGIN + "/login/"))

    def dispose(self):
        # Chromium necesita destruir la página antes de destruir su perfil.
        delete(self.page())
