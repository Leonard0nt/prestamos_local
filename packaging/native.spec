import os
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules

# El análisis de Django necesita valores, pero la compilación no se conecta a la base.
for key, value in {
    "DB_NAME": "build", "DB_USER": "build", "DB_PASSWORD": "build",
    "DB_HOST": "127.0.0.1", "DB_PORT": "5432",
}.items():
    os.environ.setdefault(key, value)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "prestamos_biblioteca.settings")

root = Path(SPECPATH).parent
packages = (
    "django.contrib.admin", "django.contrib.auth", "django.contrib.contenttypes",
    "django.contrib.sessions", "django.contrib.messages", "django.contrib.staticfiles",
    "django.db.backends.postgresql", "librosApp", "usuarioApp", "prestamoApp",
)
hidden = ["prestamos_biblioteca.settings"]
for package in packages:
    hidden.extend(collect_submodules(package))

analysis = Analysis(
    [str(root / "native_app.py")],
    pathex=[str(root)],
    hiddenimports=hidden,
)
pyz = PYZ(analysis.pure)
name = "PrestamosBibliotecaCSF-Nativo"
exe = EXE(
    pyz, analysis.scripts, [], exclude_binaries=True, name=name,
    console=False, upx=False,
    icon=str(root / "assets" / "prestamos_csfv2.ico") if sys.platform == "win32" else None,
)
distribution = COLLECT(
    exe, analysis.binaries, analysis.datas, name=name, upx=False,
)
