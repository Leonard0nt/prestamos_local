# -*- mode: python ; coding: utf-8 -*-

import os
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

project_dir = Path.cwd()

# Evita que hook-django falle durante el análisis cuando faltan variables de entorno
# en la máquina de build (por ejemplo al no tener .env local).
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'prestamos_biblioteca.settings')
os.environ.setdefault('SECRET_KEY', 'desktop-build-secret-key')
os.environ.setdefault('DEBUG', 'False')
os.environ.setdefault('ALLOWED_HOSTS', '127.0.0.1,localhost')
os.environ.setdefault('DB_ENGINE', 'django.db.backends.sqlite3')
os.environ.setdefault('DB_NAME', 'db.sqlite3')
os.environ.setdefault('DB_USER', '')
os.environ.setdefault('DB_PASSWORD', '')
os.environ.setdefault('DB_HOST', '')
os.environ.setdefault('DB_PORT', '')

block_cipher = None


def data_dir(path: str, target: str):
    full_path = project_dir / path
    return [(str(full_path), target)] if full_path.exists() else []


hiddenimports = collect_submodules('webview')
hiddenimports += [
    'django',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'librosApp',
    'prestamoApp',
    'usuarioApp',
]

datas = []
datas += data_dir('manage.py', '.')
datas += data_dir('db.sqlite3', '.')
datas += data_dir('.env', '.')
datas += data_dir('templates', 'templates')
datas += data_dir('librosApp', 'librosApp')
datas += data_dir('prestamoApp', 'prestamoApp')
datas += data_dir('usuarioApp', 'usuarioApp')
datas += data_dir('prestamos_biblioteca', 'prestamos_biblioteca')

datas += collect_data_files('django')
datas += collect_data_files('rest_framework')

a = Analysis(
    ['desktop_app.py'],
    pathex=[str(project_dir)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='BibliotecaLocal',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)