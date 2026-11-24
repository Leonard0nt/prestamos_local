# Préstamos Biblioteca CSF en PySide6

Este prototipo abre ventanas nativas y usa los modelos de Django con SQLite local o PostgreSQL. Puedes iniciar sesión con una cuenta existente, buscar libros y lectores y registrar préstamos. El prototipo cubre ese recorrido. Para devoluciones, historial y administración del catálogo, sigue usando la edición web.

El cliente usa el ORM de Django directamente, sin servidor HTTP, Waitress ni WebView2.

## Probar en un solo PC con SQLite

Con Python 3.12 y `requirements-native.txt` instalados, ejecuta desde la raíz
del repositorio:

```bash
python scripts/setup_sqlite.py --demo
python native_app.py
```

El script aplica las migraciones, pide crear la primera cuenta y agrega un
libro y un lector ficticios. Para probar un préstamo, busca **El libro de
prueba** y **Lector de prueba**, selecciona **Básica** y registra el préstamo.
Puedes omitir `--demo` si quieres partir con el catálogo vacío.

El archivo `prestamos.sqlite3` queda en la misma carpeta que la configuración
del usuario, indicada en la tabla de abajo. Si ya configuraste PostgreSQL o
Supabase, guarda tu `.env` existente con otro nombre antes de ejecutar el
script. El script conserva esa configuración y te avisa si la encuentra.
SQLite crea una base independiente en este PC. Para usar el instalador con
SQLite, prepara primero la base con el script y compila el ejecutable desde
esta versión de la rama.

## Ubicación de la configuración y conexión a PostgreSQL

Para usar PostgreSQL en lugar de SQLite, copia `packaging/native.env.example` como `.env` en la ubicación correspondiente y rellena los datos de conexión. La base debe estar accesible y tener las migraciones aplicadas.

| Sistema | Archivo de configuración |
| --- | --- |
| Windows | `%LOCALAPPDATA%\prestamos-biblioteca\.env` |
| Arch Linux | `${XDG_CONFIG_HOME:-$HOME/.config}/prestamos-biblioteca/.env` |

Utiliza una cuenta de PostgreSQL autorizada para esta base. El instalador distribuye un ejemplo vacío y el cliente lee la configuración de cada equipo. Para probar desde el código puedes usar la misma configuración o exportar las variables de conexión antes de ejecutar `python native_app.py`.

## Crear el proyecto en Supabase

Desde la raíz de esta rama, con Python 3.12 y las dependencias de
`requirements-native.txt` instaladas, ejecuta:

```bash
python scripts/provision_supabase.py --org TU_ORGANIZACION --name prestamos-biblioteca --region sa-east-1
```

Usa el **slug** de tu organización y un
[token personal de acceso de Supabase](https://supabase.com/dashboard/account/tokens)
con permisos para crear proyectos en ella. El script pide el token, la contraseña
de PostgreSQL y los datos del primer bibliotecario en la terminal. Las contraseñas
y el token se escriben de forma oculta. El proyecto se crea con el plan de la
organización y cuenta para su cuota.

El proceso espera al pooler en modo sesión, aplica las migraciones en el esquema
`biblioteca`, crea la cuenta de la aplicación y escribe el archivo de conexión
en la ruta del sistema indicada arriba. La configuración usa TLS con
verificación del servidor y guarda la contraseña de un rol PostgreSQL limitado
al flujo de la app nativa. El token de gestión y la contraseña administrativa
quedan fuera de ese archivo. Usa equipos de confianza para este cliente, ya que
se conecta directamente a la base con ese rol.

Si el proyecto se creó y la preparación se interrumpió, conserva la referencia
que imprime el script y continúa con:

```bash
python scripts/provision_supabase.py --project-ref REFERENCIA
```

Usa la misma contraseña de PostgreSQL. Si la cuenta del bibliotecario ya se
creó, el script conserva su contraseña. Volver a preparar el rol PostgreSQL
genera una contraseña nueva para el cliente. Si ya tienes un `.env`, el script
te pide elegir otra ruta con `--config`. Actualiza las instalaciones que usaban
la contraseña anterior al reemplazar su configuración.

El proyecto nuevo comienza con el catálogo y los lectores vacíos. Si ya tienes
datos, su traslado es un paso aparte. Para ejecutar el cliente empaquetado,
genera nuevamente el ejecutable desde esta versión para que lea la configuración
de TLS y del esquema.

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
