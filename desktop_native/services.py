from datetime import date
from types import SimpleNamespace

from django.db import transaction
from django.db.models import Q

from librosApp.models import Ejemplar
from prestamoApp.serializers import PrestamoSerializer
from usuarioApp.models import usuario


def _scope(account, prefix=""):
    if account.is_superuser:
        return Q()
    librarian = account.encargado
    return (
        Q(**{prefix + "nivel_asignado": librarian.nivel})
        | Q(
            **{
                prefix + "nivel_asignado__isnull": True,
                prefix + "encargado_agrego__nivel": librarian.nivel,
            }
        )
    )


def find_copies(account, query):
    return (
        Ejemplar.objects.filter(_scope(account, "libro__"))
        .filter(
            Q(libro__titulo__icontains=query)
            | Q(libro__autor__icontains=query)
            | Q(libro__codigo_libro__icontains=query)
            | Q(codigo__icontains=query)
        )
        .select_related("libro")
        .order_by("libro__titulo", "codigo", "pk")[:100]
    )


def find_readers(account, query):
    return (
        usuario.objects.filter(_scope(account), activo=True)
        .filter(Q(nombre__icontains=query) | Q(rut__icontains=query))
        .order_by("nombre", "pk")[:50]
    )


@transaction.atomic
def register_loan(account, copy_id, reader_id, due_date, level):
    # El bloqueo mantiene la validación y la actualización del ejemplar juntas.
    copy = Ejemplar.objects.select_for_update().filter(pk=copy_id).first()
    if copy is None or not Ejemplar.objects.filter(
        _scope(account, "libro__"), pk=copy_id
    ).exists():
        raise ValueError("El ejemplar no está disponible para tu perfil.")
    if not usuario.objects.filter(_scope(account), activo=True, pk=reader_id).exists():
        raise ValueError("El lector no está disponible para tu perfil.")

    librarian = getattr(account, "encargado", None)
    serializer = PrestamoSerializer(
        data={
            "ejemplar": copy_id,
            "usuario": reader_id,
            "fecha_prestamo": date.today().isoformat(),
            "fecha_devolucion": due_date.isoformat(),
            "nivel_asignado": level if account.is_superuser else librarian.nivel,
        },
        context={"request": SimpleNamespace(user=account)},
    )
    serializer.is_valid(raise_exception=True)
    return serializer.save(encargado_agrego=None if account.is_superuser else librarian)
