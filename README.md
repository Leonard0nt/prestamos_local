# Préstamos Biblioteca CSF

Sistema de gestión de biblioteca escolar para administrar usuarios, libros, ejemplares y préstamos. El proyecto está construido con Django y Django REST Framework, incluye vistas web para operación diaria y un lanzador de escritorio con PyWebView para abrir la aplicación como ventana nativa en Windows.

## ¿Qué permite hacer?

- Iniciar sesión con perfiles de administrador o encargado de biblioteca.
- Administrar encargados de biblioteca por nivel: Básica o Media.
- Registrar, listar, desactivar, reactivar y eliminar usuarios conservando historial cuando corresponde.
- Registrar libros y crear ejemplares físicos con códigos automáticos.
- Controlar disponibilidad de ejemplares: disponible, prestado, baja, extraviado o dañado.
- Crear préstamos, registrar devoluciones y calcular atrasos.
- Archivar préstamos sin eliminarlos definitivamente.
- Separar la información por nivel para que cada encargado vea y gestione solo su ámbito.
- Exponer endpoints REST mediante `DefaultRouter` para integraciones o consumo desde la interfaz.

## Tecnologías principales

- Python
- Django
- Django REST Framework
- PostgreSQL
- django-environ para configuración por variables de entorno
- Waitress como servidor embebido del lanzador de escritorio
- PyWebView para la ventana de escritorio
- PyInstaller e Inno Setup para empaquetado/instalador en Windows

## Estructura del proyecto

```text
prestamos_local/
├── librosApp/                 # Libros, ejemplares, serializers y vistas API/UI
├── prestamoApp/               # Préstamos, devoluciones, historial y dashboard
├── usuarioApp/                # Usuarios, encargados, login y credenciales
├── prestamos_biblioteca/      # Configuración principal de Django y URLs
├── templates/                 # Plantillas HTML de la interfaz
├── assets/                    # Íconos y recursos del ejecutable
├── desktop_app.py             # Lanzador de escritorio con Waitress + PyWebView
├── PrestamosBibliotecaCSF.spec# Configuración de PyInstaller
├── installer.iss              # Script del instalador de Windows
├── manage.py                  # CLI de Django
└── requirements.txt           # Dependencias del proyecto
```

## Módulos principales

### `usuarioApp`

Gestiona estudiantes/usuarios y encargados de biblioteca.

- El modelo `usuario` guarda RUT, nombre, curso, correo, teléfono, estado activo e información de nivel.
- El modelo `EncargadoBiblioteca` se vincula con `django.contrib.auth.models.User` y define el nivel que administra.
- Al crear un encargado se genera una cuenta Django asociada; el usuario inicial se deriva del RUT y la contraseña temporal corresponde a los últimos 4 dígitos del cuerpo del RUT.
- Los usuarios se pueden desactivar para conservar historial y luego reactivar o eliminar definitivamente.

### `librosApp`

Gestiona el catálogo y los ejemplares físicos.

- `Libro` contiene título, autor, editorial, fecha de registro, código, nivel asignado y encargado que lo agregó.
- `Ejemplar` representa una copia física del libro y almacena código, fecha de llegada y estado.
- La combinación `codigo_libro` + `nivel_asignado` es única para evitar duplicados dentro de un mismo nivel.
- Al crear un libro se pueden generar varios ejemplares automáticamente con códigos secuenciales.

### `prestamoApp`

Gestiona préstamos y devoluciones.

- `prestamo` registra ejemplar, usuario, fecha de préstamo, fecha de devolución esperada, días de atraso, estado y nivel.
- Los préstamos nuevos marcan el ejemplar como `prestado`.
- Al devolver, el sistema cambia el estado del préstamo a devuelto o atrasado según la fecha, calcula días de atraso y libera el ejemplar si corresponde.
- La eliminación desde la API archiva el préstamo, manteniendo el registro histórico.

## Rutas principales

La aplicación registra rutas web y endpoints REST desde `prestamos_biblioteca/urls.py`.

### Interfaz web

| Ruta | Descripción |
| --- | --- |
| `/` | Dashboard de préstamos |
| `/login/` | Inicio de sesión |
| `/logout/` | Cierre de sesión |
| `/usuarios-ui/` | Gestión visual de usuarios |
| `/encargados-ui/` | Gestión visual de encargados, solo administrador |
| `/libros-ui/` | Gestión visual de libros |
| `/libros/<libro_id>/ejemplares/` | Vista de ejemplares de un libro |
| `/mi-cuenta/actualizar/` | Actualización de credenciales del usuario autenticado |

### API REST

| Recurso | Endpoint base |
| --- | --- |
| Usuarios | `/usuarios/` |
| Encargados | `/encargados/` |
| Libros | `/libros/` |
| Préstamos | `/prestamos/` |
| Ejemplares | `/ejemplares/` |

Además, hay acciones personalizadas como:

- `/libros/{id}/ejemplares_json/`
- `/libros/{id}/agregar_ejemplar/`
- `/libros/{id}/actualizar_estado_ejemplares/`
- `/ejemplares/{id}/eliminar_definitivo/`
- `/prestamos/{id}/devolver/`
- `/prestamos/historial/`
- `/usuarios/{id}/reactivar/`

## Requisitos previos

- Python instalado.
- PostgreSQL disponible.
- Un entorno virtual de Python recomendado.
- Variables de entorno configuradas en un archivo `.env` en la raíz del proyecto.

> Nota: `requirements.txt` está incluido en el repositorio. Si tu editor o terminal muestra caracteres extraños al abrirlo, revisa su codificación antes de instalar dependencias.

## Configuración de entorno

Crea un archivo `.env` en la raíz del proyecto con una configuración similar:

```env
SECRET_KEY=coloca-una-clave-segura
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost
DB_NAME=prestamos_biblioteca
DB_USER=postgres
DB_PASSWORD=tu_password
DB_HOST=localhost
DB_PORT=5432
```

En producción, usa `DEBUG=False`, una `SECRET_KEY` segura y limita `ALLOWED_HOSTS` a los dominios o hosts permitidos.

## Instalación y ejecución local

1. Crear y activar un entorno virtual:

   ```bash
   python -m venv .venv
   # Windows
   .venv\Scripts\activate
   # Linux/macOS
   source .venv/bin/activate
   ```

2. Instalar dependencias:

   ```bash
   pip install -r requirements.txt
   ```

3. Configurar el archivo `.env` y crear la base de datos PostgreSQL indicada.

4. Ejecutar migraciones:

   ```bash
   python manage.py migrate
   ```

5. Crear un usuario administrador:

   ```bash
   python manage.py createsuperuser
   ```

6. Levantar el servidor de desarrollo:

   ```bash
   python manage.py runserver
   ```

7. Abrir la aplicación en:

   ```text
   http://127.0.0.1:8000/login/
   ```

## Ejecución como aplicación de escritorio

El archivo `desktop_app.py` inicia Django con Waitress en `127.0.0.1:8765` y abre una ventana PyWebView en `/login/`.

```bash
python desktop_app.py
```

Este modo busca `manage.py`, carga variables desde `.env`, inicia el servidor embebido y escribe logs en `desktop_app.log` junto al script o ejecutable.

## Empaquetado para Windows

El repositorio incluye configuración para generar ejecutables e instaladores:

- `PrestamosBibliotecaCSF.spec`: configuración de PyInstaller con ícono del proyecto.
- `desktop_app.spec`: configuración alternativa para el lanzador.
- `installer.iss`: script de Inno Setup para construir el instalador.

Ejemplo de empaquetado con PyInstaller:

```bash
pyinstaller PrestamosBibliotecaCSF.spec
```

Luego puedes usar Inno Setup con `installer.iss` para crear el instalador final.

## Reglas de negocio destacadas

- Los encargados de biblioteca solo operan sobre el nivel que tienen asignado.
- El administrador puede gestionar encargados y seleccionar nivel en registros globales.
- No se puede prestar un ejemplar que no esté disponible.
- No se pueden registrar préstamos a usuarios desactivados.
- Un préstamo devuelto fuera de plazo queda marcado con atraso y días de atraso.
- Los ejemplares con préstamos activos no se pueden dar de baja ni eliminar definitivamente sin validaciones.
- Los préstamos se archivan en vez de eliminarse para preservar historial.

## Estado del proyecto

Este repositorio corresponde a una aplicación Django funcional orientada a uso interno de biblioteca escolar, con interfaz web, API REST y soporte para ejecución como aplicación de escritorio en Windows.
