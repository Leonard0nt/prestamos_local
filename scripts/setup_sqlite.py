"""Prepara la base SQLite local y crea la primera cuenta de acceso."""

import argparse
from datetime import date
import os
from pathlib import Path
import sys

import django
import environ

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from desktop_native.config import config_file


def add_demo_data():
    from django.db import transaction

    from librosApp.models import Ejemplar, Libro
    from usuarioApp.models import usuario

    with transaction.atomic():
        book, _ = Libro.objects.get_or_create(
            codigo_libro="DEMO-LIBRO", nivel_asignado=Libro.NIVEL_BASICA,
            defaults={
                "titulo": "El libro de prueba", "autor": "Autor de ejemplo",
                "editorial": "Editorial Demo", "fecha_registro": date.today(),
            },
        )
        Ejemplar.objects.get_or_create(libro=book, codigo="DEMO-EJEMPLAR")
        usuario.objects.get_or_create(
            rut="DEMO-LECTOR",
            defaults={
                "nombre": "Lector de prueba", "email": "lector@example.test",
                "nivel_asignado": usuario.NIVEL_BASICA,
            },
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo", action="store_true", help="Carga un libro y un lector ficticios")
    args = parser.parse_args()

    path = config_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8") as config:
            config.write("DB_ENGINE=sqlite\n")
    except FileExistsError:
        pass
    class LocalConfig(environ.Env):
        ENVIRON = {}

    LocalConfig.read_env(path)
    if LocalConfig.ENVIRON.get("DB_ENGINE") != "sqlite":
        parser.error(f"{path} ya tiene otra configuración. Muévelo antes de activar SQLite.")

    os.environ.update(LocalConfig.ENVIRON)
    os.environ["DJANGO_SETTINGS_MODULE"] = "prestamos_biblioteca.settings"
    django.setup()

    from django.conf import settings
    from django.contrib.auth import get_user_model
    from django.core.management import call_command

    database = settings.DATABASES["default"]["NAME"]
    Path(database).parent.mkdir(parents=True, exist_ok=True)
    call_command("migrate", interactive=False)
    if not get_user_model().objects.filter(is_active=True, is_superuser=True).exists():
        print("Crea la primera cuenta de la aplicación.")
        call_command("createsuperuser")
    if args.demo:
        add_demo_data()
    print(f"Base SQLite lista en {database}.")


if __name__ == "__main__":
    main()
