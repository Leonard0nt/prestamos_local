# Préstamos Biblioteca CSF en PySide6

La edición de escritorio abre la interfaz completa de Django dentro de Qt WebEngine, sin servidor HTTP ni acceso desde un navegador externo. Puedes trabajar sin internet con SQLite.

En la primera apertura, la aplicación crea la base, aplica las migraciones y te pide un usuario y una contraseña de administrador. En las siguientes aperturas, inicia sesión con esa cuenta. El catálogo empieza vacío.

| Sistema | Carpeta de datos |
| --- | --- |
| Windows | `%LOCALAPPDATA%\prestamos-biblioteca` |
| Linux | `$XDG_CONFIG_HOME/prestamos-biblioteca` o `~/.config/prestamos-biblioteca` |

La base local es `prestamos.sqlite3`. Una actualización conserva la base y las cuentas. Si la app encuentra una conexión PostgreSQL configurada en el archivo `.env` de esa carpeta, sigue usándola.

## Windows x64

Si ya tienes el instalador, ábrelo y luego inicia **Préstamos Biblioteca CSF Nativo** desde el menú Inicio. El destino sugerido está dentro de tu perfil y puedes elegir otra carpeta donde tengas permisos.

Para generarlo, instala Python 3.15 x64 e Inno Setup 6 o 7. Descarga y extrae el [ZIP de la rama](https://github.com/Leonard0nt/prestamos_local/archive/refs/heads/codex/pyside6-desktop.zip). En PowerShell, desde la carpeta que contiene `requirements-native.txt`, ejecuta:

```powershell
python -m venv .venv-native
.\.venv-native\Scripts\python.exe -m pip install -r requirements-native.txt
.\.venv-native\Scripts\python.exe -m PyInstaller --noconfirm packaging\native.spec
```

Cuando PyInstaller indique `Build complete`, abre `packaging\native-windows.iss` en Inno Setup y elige **Build → Compile**. El instalador queda en `installer_output\prestamos-biblioteca-nativo-setup.exe`. Para distribuirlo en equipos con Control inteligente de aplicaciones, firma el ejecutable antes de empaquetarlo y firma también el instalador.

## Linux

Desde la raíz del código, con Python 3.12 o 3.15:

```bash
python3 -m venv .venv-native
.venv-native/bin/python -m pip install -r requirements-native.txt
.venv-native/bin/python native_app.py
```

En Arch, puedes instalar Python 3.12 con `uv` si el Python del sistema usa otra versión. Para generar e instalar un paquete en Arch x86_64, ejecuta desde la raíz:

```bash
sudo pacman -S --needed base-devel uv
uv venv --python 3.12 .venv-native
uv pip install --python .venv-native/bin/python -r requirements-native.txt
.venv-native/bin/python -m PyInstaller --noconfirm packaging/native.spec
tar -C dist -czf packaging/PrestamosBibliotecaCSF-Nativo-0.2.0.tar.gz PrestamosBibliotecaCSF-Nativo
cd packaging
makepkg --syncdeps
sudo pacman -U prestamos-biblioteca-nativo-0.2.0-1-x86_64.pkg.tar.zst
```

Luego abre **Préstamos Biblioteca CSF Nativo** desde el menú o ejecuta `prestamos-biblioteca-nativo`.

## Supabase opcional

Con las dependencias instaladas, ejecuta desde la raíz del código. En Windows usa `.\.venv-native\Scripts\python.exe` en vez de `.venv-native/bin/python`.

```bash
.venv-native/bin/python scripts/provision_supabase.py --full-desktop --org TU_ORGANIZACION
```

Introduce un [token personal de Supabase](https://supabase.com/dashboard/account/tokens), la contraseña de PostgreSQL y las credenciales que usarás para entrar en la app. El script crea el proyecto, aplica las migraciones, crea el administrador y guarda la conexión TLS en `.env`. Para un proyecto existente o para reanudar, cambia `--org TU_ORGANIZACION` por `--project-ref REFERENCIA`.

Si ya tienes un `.env`, el script lo conserva. Guárdalo con otro nombre antes de cambiar la conexión. La base local queda en el equipo y sus datos no se copian a Supabase. Para conectar otros equipos de confianza, copia el `.env` generado a su carpeta de datos por un canal seguro. Contiene las credenciales de un rol con acceso al catálogo y a las cuentas de la aplicación.

## Pruebas

```bash
env DB_ENGINE=sqlite DB_SQLITE_PATH=:memory: .venv-native/bin/python manage.py test
```
