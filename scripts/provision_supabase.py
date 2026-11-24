"""Crea un proyecto Supabase y prepara la base del cliente PySide6."""

import argparse
from getpass import getpass
import json
import os
from pathlib import Path
import re
import secrets
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.core.exceptions import ValidationError
from django.db import DatabaseError
import psycopg
from psycopg import sql

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

API = "https://api.supabase.com/v1"
SCHEMA = "biblioteca"
CLIENT_ROLE = "biblioteca_desktop"


class ProvisionError(Exception):
    pass


def request_api(token, path, payload=None):
    body = json.dumps(payload).encode() if payload is not None else None
    request = Request(
        API + path,
        data=body,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    with urlopen(request, timeout=30) as response:
        return json.load(response)


def wait_for_pooler(token, ref, timeout):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            project = request_api(token, f"/projects/{ref}")
            status = project["status"]
            if status in {"INIT_FAILED", "REMOVED", "RESTORE_FAILED", "INACTIVE"}:
                raise ProvisionError(f"El proyecto está en estado {status}. Revísalo en Supabase.")
            if status == "ACTIVE_HEALTHY":
                entries = request_api(token, f"/projects/{ref}/config/database/pooler")
                for entry in entries:
                    if entry["pool_mode"] == "session" and entry["database_type"] == "PRIMARY":
                        host = entry["db_host"]
                        if not host.endswith(".pooler.supabase.com"):
                            raise ProvisionError("El host del pooler no es un dominio esperado de Supabase.")
                        return host, entry["db_port"], entry["db_name"]
        except HTTPError as error:
            if error.code not in {404, 429, 500, 502, 503, 504}:
                raise
        except (URLError, TimeoutError):
            pass
        time.sleep(5)
    raise ProvisionError("El proyecto todavía no ofrece un pooler activo. Reanuda con --project-ref.")


def setup_database(admin, librarian, client_password):
    from django import setup
    from django.db import connections
    from django.core.management import call_command
    from django.contrib.auth import get_user_model
    from django.db import transaction

    options = {
        "dbname": admin["DB_NAME"], "user": admin["DB_USER"],
        "host": admin["DB_HOST"], "port": admin["DB_PORT"],
        "password": admin["DB_PASSWORD"], "sslmode": admin["DB_SSLMODE"],
        "sslrootcert": admin["DB_SSLROOTCERT"], "connect_timeout": 10,
    }
    schema = sql.Identifier(SCHEMA)
    with psycopg.connect(**options) as connection:
        connection.execute(sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(schema))

    os.environ.update(admin, DJANGO_SETTINGS_MODULE="prestamos_biblioteca.settings")
    setup()
    call_command("migrate", interactive=False)

    from librosApp.models import Ejemplar, Libro
    from prestamoApp.models import prestamo
    from usuarioApp.models import EncargadoBiblioteca, usuario

    User = get_user_model()
    with transaction.atomic():
        account, created = User.objects.get_or_create(
            username=librarian["username"], defaults={"email": librarian["email"]},
        )
        if created:
            from django.contrib.auth.password_validation import validate_password

            validate_password(librarian["password"], account)
            account.set_password(librarian["password"])
            account.save(update_fields=["password"])
            EncargadoBiblioteca.objects.create(
                user=account, nombre=librarian["name"], rut=librarian["rut"],
                correo=librarian["email"], nivel=librarian["level"],
            )
        elif not EncargadoBiblioteca.objects.filter(
            user=account, rut=librarian["rut"], correo=librarian["email"], nivel=librarian["level"]
        ).exists():
            raise ProvisionError("El nombre de usuario ya corresponde a otra cuenta.")

    with psycopg.connect(**options) as connection:
        role = sql.Identifier(CLIENT_ROLE)
        if connection.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (CLIENT_ROLE,)).fetchone():
            statement = "ALTER ROLE {} WITH LOGIN PASSWORD {}"
        else:
            statement = "CREATE ROLE {} WITH LOGIN PASSWORD {}"
        connection.execute(sql.SQL(statement).format(role, sql.Literal(client_password)))
        connection.execute(sql.SQL("GRANT USAGE ON SCHEMA {} TO {}").format(schema, role))
        for model in (User, EncargadoBiblioteca, usuario, Libro, Ejemplar, prestamo):
            table = sql.Identifier(SCHEMA, model._meta.db_table)
            connection.execute(sql.SQL("GRANT SELECT ON TABLE {} TO {}").format(table, role))
        for model, column in ((User, "password"), (Ejemplar, "estado")):
            table = sql.Identifier(SCHEMA, model._meta.db_table)
            connection.execute(
                sql.SQL("GRANT UPDATE ({}) ON TABLE {} TO {}").format(sql.Identifier(column), table, role)
            )
        loan_table = sql.Identifier(SCHEMA, prestamo._meta.db_table)
        connection.execute(sql.SQL("GRANT INSERT ON TABLE {} TO {}").format(loan_table, role))
        sequence = connection.execute(
            "SELECT pg_get_serial_sequence(%s, %s)::regclass::oid",
            (loan_table.as_string(), prestamo._meta.pk.column),
        ).fetchone()[0]
        sequence_name = connection.execute(
            "SELECT relname FROM pg_class WHERE oid = %s", (sequence,),
        ).fetchone()[0]
        connection.execute(
            sql.SQL("GRANT USAGE ON SEQUENCE {} TO {}").format(
                sql.Identifier(SCHEMA, sequence_name), role
            )
        )
    connections.close_all()


def default_config_path():
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local"))
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "prestamos-biblioteca" / ".env"


def write_config(path, settings):
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as config:
        for key, value in settings.items():
            config.write(f"{key}={value}\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--org", help="Slug de la organización de Supabase")
    parser.add_argument("--name", default="prestamos-biblioteca")
    parser.add_argument("--region", default="sa-east-1")
    parser.add_argument("--project-ref", help="Reanuda la preparación de un proyecto existente")
    parser.add_argument("--config", type=Path, default=default_config_path())
    args = parser.parse_args()
    if args.project_ref and not re.fullmatch("[a-z]{20}", args.project_ref):
        parser.error("--project-ref requiere la referencia de 20 letras del proyecto")
    if not (args.project_ref or args.org):
        parser.error("indica --org para crear un proyecto o --project-ref para reanudar")
    if args.config.exists():
        parser.error(f"el archivo {args.config} ya existe; elige otra ruta con --config")

    token = os.environ.get("SUPABASE_ACCESS_TOKEN") or getpass("Token personal de Supabase: ")
    admin_password = getpass("Contraseña de PostgreSQL del proyecto: ")
    if not args.project_ref and len(admin_password) < 16:
        parser.error("usa una contraseña de PostgreSQL de al menos 16 caracteres")

    librarian = {
        "username": input("Usuario del bibliotecario: ").strip(),
        "name": input("Nombre: ").strip(),
        "rut": input("RUT: ").strip(),
        "email": input("Correo: ").strip(),
        "level": input("Nivel (BASICA o MEDIA): ").strip().upper(),
        "password": getpass("Contraseña del bibliotecario: "),
    }
    if not token or not admin_password or not all(librarian.values()):
        parser.error("completa todos los datos")
    from django.core.validators import validate_email

    try:
        validate_email(librarian["email"])
    except ValidationError:
        parser.error("indica un correo válido")
    if any(len(librarian[field]) > limit for field, limit in (
        ("username", 150), ("name", 100), ("rut", 20),
    )):
        parser.error("revisa la longitud del usuario, nombre y RUT")
    if len(librarian["password"]) < 8:
        parser.error("usa una contraseña de bibliotecario de al menos ocho caracteres")
    if librarian["level"] not in {"BASICA", "MEDIA"}:
        parser.error("el nivel debe ser BASICA o MEDIA")

    ref = args.project_ref
    try:
        if ref is None:
            print(f"Creando {args.name} en {args.org} ({args.region}).", flush=True)
            result = request_api(token, "/projects", {
                "db_pass": admin_password,
                "name": args.name,
                "organization_slug": args.org,
                "region_selection": {"type": "specific", "code": args.region},
            })
            ref = result["ref"]
        print(f"Proyecto: https://supabase.com/dashboard/project/{ref}", flush=True)
        host, port, database = wait_for_pooler(token, ref, timeout=600)
        settings = {
            "DB_NAME": database, "DB_HOST": host, "DB_PORT": str(port),
            "DB_SCHEMA": SCHEMA, "DB_SSLMODE": "verify-full", "DB_SSLROOTCERT": "system",
        }
        db_user = f"postgres.{ref}"
        client_password = secrets.token_urlsafe(32)
        setup_database(
            dict(settings, DB_USER=db_user, DB_PASSWORD=admin_password),
            librarian, client_password,
        )
        write_config(args.config, dict(settings, DB_USER=f"{CLIENT_ROLE}.{ref}", DB_PASSWORD=client_password))
    except (HTTPError, URLError, TimeoutError, OSError, ProvisionError, psycopg.Error, DatabaseError, ValidationError) as error:
        if isinstance(error, HTTPError):
            message = f"Supabase respondió con HTTP {error.code}."
        elif isinstance(error, ProvisionError):
            message = str(error)
        elif isinstance(error, ValidationError):
            message = " ".join(error.messages)
        else:
            message = f"Falló la preparación ({type(error).__name__})."
        print(message, file=sys.stderr)
        if ref:
            print(f"Puedes continuar con --project-ref {ref}.", file=sys.stderr)
        else:
            print("Revisa el panel de Supabase antes de volver a crear el proyecto.", file=sys.stderr)
        return 1
    print(f"Configuración del cliente guardada en {args.config}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
