from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models.deletion import ProtectedError
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, render
from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from prestamoApp.models import prestamo

from .models import Ejemplar, Libro
from .serializers import EjemplarSerializer, LibroSerializer


def limitar_por_nivel(queryset, user, prefix=''):
    if user.is_superuser:
        return queryset
    encargado = getattr(user, 'encargado', None)
    if encargado is None:
        return queryset.none()
    return queryset.filter(
        Q(**{prefix + 'nivel_asignado': encargado.nivel})
        | Q(**{
            prefix + 'nivel_asignado__isnull': True,
            prefix + 'encargado_agrego__nivel': encargado.nivel,
        })
    )


class LibroViewSet(ModelViewSet):
    queryset = Libro.objects.select_related('encargado_agrego')
    serializer_class = LibroSerializer

    def get_queryset(self):
        queryset = Libro.objects.annotate(
            cantidad_ejemplares=Count('ejemplar'),
            cantidad_disponibles=Count('ejemplar', filter=Q(ejemplar__estado=Ejemplar.ESTADO_DISPONIBLE)),
        ).select_related('encargado_agrego')
        if self.request.user.is_superuser:
            return queryset

        queryset = limitar_por_nivel(queryset, self.request.user)

        encargado_id = self.request.query_params.get('encargado_id')
        if encargado_id:
            queryset = queryset.filter(encargado_agrego_id=encargado_id)
        return queryset

    def perform_create(self, serializer):
        encargado = getattr(self.request.user, 'encargado', None)
        if encargado and not self.request.user.is_superuser:
            serializer.save(encargado_agrego=encargado, nivel_asignado=encargado.nivel)
            return
        serializer.save()

    @staticmethod
    @login_required(login_url='login')
    def libros_view(request):
        libros = Libro.objects.all()
        return render(request, 'libros.html', {'libros': libros})

    @staticmethod
    @login_required(login_url='login')  
    def ejemplares_view(request, libro_id):
        libros = limitar_por_nivel(Libro.objects.all(), request.user)
        libro = get_object_or_404(libros, id=libro_id)
        return render(request, 'libros.html', {'libro_inicial': libro.pk})
    
    @action(detail=True, methods=['get'])
    def ejemplares_json(self, request, pk=None):
        libro = self.get_object()
        ejemplares = Ejemplar.objects.filter(libro=libro)
        serializer = EjemplarSerializer(ejemplares, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def agregar_ejemplar(self, request, pk=None):
        try:
            cantidad = serializers.IntegerField(min_value=1).run_validation(
                request.data.get('cantidad', 1)
            )
        except serializers.ValidationError:
            return Response(
                {'detail': 'La cantidad debe ser un entero mayor que 0.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        libro = Libro.objects.select_for_update().get(pk=self.get_object().pk)
        codigos = Ejemplar.objects.filter(libro=libro).values_list('codigo', flat=True)
        # Los códigos anteriores pueden no terminar en un número.
        sufijos = (codigo.rsplit('-', 1)[-1] for codigo in codigos)
        ultimo_num = max(
            (int(sufijo) for sufijo in sufijos if sufijo.isascii() and sufijo.isdecimal()),
            default=0,
        )
        prefijo = f"{libro.codigo_libro}-"
        if len(f"{prefijo}{ultimo_num + cantidad}") > Ejemplar._meta.get_field('codigo').max_length:
            return Response(
                {'detail': 'La numeración resultante supera el largo admitido para un código.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        nuevos = Ejemplar.objects.bulk_create([
            Ejemplar(libro=libro, codigo=f"{prefijo}{ultimo_num + i}")
            for i in range(1, cantidad + 1)
        ])
        return Response(EjemplarSerializer(nuevos, many=True).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def actualizar_estado_ejemplares(self, request, pk=None):
        libro = self.get_object()
        estado = request.data.get('estado')
        estados_validos = {Ejemplar.ESTADO_EXTRAVIADO, Ejemplar.ESTADO_DANIADO}

        if estado not in estados_validos:
            return Response(
                {'detail': 'Estado inválido. Usa "extraviado" o "danado".'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ejemplares = Ejemplar.objects.filter(libro=libro)
        if not ejemplares.exists():
            return Response(
                {'detail': 'Este libro no tiene ejemplares registrados.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ejemplares_con_prestamo_activo = prestamo.objects.filter(
            ejemplar__in=ejemplares,
            estado__in=['P', 'A'],
        ).exists()
        if ejemplares_con_prestamo_activo:
            return Response(
                {
                    'detail': (
                        'No se puede actualizar el estado de todos los ejemplares '
                        'mientras exista un préstamo activo.'
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        actualizados = ejemplares.update(estado=estado)
        return Response(
            {
                'detail': f'Se actualizó el estado de {actualizados} ejemplar(es).',
                'cantidad_actualizada': actualizados,
                'estado_aplicado': estado,
            },
            status=status.HTTP_200_OK,
        )

    def destroy(self, request, *args, **kwargs):
        libro = self.get_object()
        if Ejemplar.objects.filter(libro=libro).exists():
            return Response(
                {'detail': 'No se puede eliminar este libro porque tiene ejemplares registrados.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            return Response(
                {
                    'detail': (
                        'No se puede eliminar este libro porque está relacionado con '
                        'registros históricos.'
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

class EjemplarViewSet(ModelViewSet):
    queryset = Ejemplar.objects.all()
    serializer_class = EjemplarSerializer

    def get_queryset(self):
        queryset = Ejemplar.objects.select_related('libro', 'libro__encargado_agrego')
        return limitar_por_nivel(queryset, self.request.user, prefix='libro__')

    def destroy(self, request, *args, **kwargs):
        ejemplar = self.get_object()

        if prestamo.objects.filter(ejemplar=ejemplar, estado__in=['P', 'A']).exists():
            return Response(
                {
                    'detail': (
                        'No se puede dar de baja este ejemplar mientras tenga un '
                        'préstamo activo.'
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if ejemplar.estado == Ejemplar.ESTADO_BAJA:
            return Response(
                {'detail': 'El ejemplar ya se encuentra dado de baja.'},
                status=status.HTTP_200_OK,
            )

        ejemplar.estado = Ejemplar.ESTADO_BAJA
        ejemplar.save(update_fields=['estado'])

        return Response(
            {'detail': 'Ejemplar dado de baja correctamente. Se conserva su historial.'},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=['delete'])
    def eliminar_definitivo(self, request, pk=None):
        ejemplar = self.get_object()

        if prestamo.objects.filter(ejemplar=ejemplar).exists():
            return Response(
                {
                    'detail': (
                        'No se puede eliminar este ejemplar porque tiene historial de '
                        'préstamos.'
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        ejemplar.delete()
        return Response(
            {'detail': 'Ejemplar eliminado correctamente.'},
            status=status.HTTP_200_OK,
        )