# Préstamos Biblioteca CSF en PySide6

Este prototipo abre ventanas nativas y usa los modelos de Django y la misma base PostgreSQL. Puedes iniciar sesión con una cuenta existente, buscar libros y lectores y registrar préstamos. El prototipo cubre ese recorrido. Para devoluciones, historial y administración del catálogo, sigue usando la edición web.

El cliente llama a Django y a PostgreSQL directamente. No levanta un servidor HTTP ni requiere Waitress o WebView2. PostgreSQL debe estar accesible desde el equipo y tener las migraciones del proyecto aplicadas.

## Configurar la conexión en cada PC

Copia `packaging/native.env.example` como `.env` en la ubicación correspondiente y rellena los datos de PostgreSQL.

| Sistema | Archivo de configuración |
| --- | --- |
| Windows | `%LOCALAPPDATA%\prestamos-biblioteca\.env` |
| Arch Linux | `${XDG_CONFIG_HOME:-$HOME/.config}/prestamos-biblioteca/.env` |

Utiliza una cuenta de PostgreSQL autorizada para esta base. El instalador distribuye un ejemplo vacío y el cliente lee la configuración de cada equipo. Para probar desde el código puedes usar la misma configuración o exportar las variables de conexión antes de ejecutar `python native_app.py`.

## Generar el instalador de Windows x64

Compila en Windows x64 con **Python 3.12** e **Inno Setup 6**. Desde PowerShell:

```powershell
git clone --branch codex/pyside6-desktop https://github.com/Leonard0nt/prestamos_local.git
cd prestamos_local
py -3.12 -m venv .venv-native
.\.venv-native\Scripts\python.exe -m pip install -r requirements-native.txt
.\.venv-native\Scripts\python.exe -m PyInstaller --noconfirm packaging\native.spec
```

Prueba `dist\PrestamosBibliotecaCSF-Nativo\PrestamosBibliotecaCSF-Nativo.exe`. Luego abre `packaging\native-windows.iss` en Inno Setup y elige **Build → Compile**. El resultado queda en `installer_output\prestamos-biblioteca-nativo-setup.exe`. El instalador coloca el ejecutable y sus bibliotecas y crea un acceso directo en el menú Inicio.

## Generar el paquete de Arch Linux x86_64

Compila en Arch x86_64. Desde Bash, instala las herramientas. El ejemplo usa `uv` para obtener la misma versión de Python que en Windows.

```bash
sudo pacman -S --needed base-devel git uv
git clone --branch codex/pyside6-desktop https://github.com/Leonard0nt/prestamos_local.git
cd prestamos_local
uv python install 3.12
uv venv --python 3.12 .venv-native
uv pip install --python .venv-native/bin/python -r requirements-native.txt
.venv-native/bin/python -m PyInstaller --noconfirm packaging/native.spec
tar -C dist -czf packaging/PrestamosBibliotecaCSF-Nativo-0.1.0.tar.gz PrestamosBibliotecaCSF-Nativo
cd packaging
makepkg --syncdeps
sudo pacman -U prestamos-biblioteca-nativo-0.1.0-1-x86_64.pkg.tar.zst
```

Ejecuta `makepkg` con tu usuario habitual. La aplicación aparece en el menú como **Préstamos Biblioteca CSF Nativo**. El ejemplo de conexión también queda disponible en `/usr/share/prestamos-biblioteca-nativo/native.env.example`.

## Probar el arranque

Una vez configurada la base, abre el ejecutable o el acceso directo. Prueba primero con una base de desarrollo. El registro guarda un préstamo real en la base configurada. Para comparar el arranque, mide desde el doble clic hasta el diálogo de acceso en el mismo PC y con las dos ediciones cerradas.
