from django.contrib.auth.decorators import login_required
from django.db.models.deletion import ProtectedError
from django.db.models import Q
from django.shortcuts import get_object_or_404, render
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from prestamoApp.models import prestamo

from .models import Ejemplar, Libro
from .serializers import EjemplarSerializer, LibroSerializer


class LibroViewSet(ModelViewSet):
    queryset = Libro.objects.all()
    serializer_class = LibroSerializer

    def get_queryset(self):
        queryset = Libro.objects.all()
        if self.request.user.is_superuser:
            return queryset

        encargado = getattr(self.request.user, 'encargado', None)
        if encargado:
            queryset = queryset.filter(
                Q(nivel_asignado=encargado.nivel) |
                Q(nivel_asignado__isnull=True, encargado_agrego__nivel=encargado.nivel)
            )
        else:
            queryset = queryset.none()

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
        libro = get_object_or_404(Libro, id=libro_id)
        ejemplares = Ejemplar.objects.filter(libro=libro)

        return render(request, 'ejemplares.html', {
            'libro': libro,
            'ejemplares': ejemplares,
        })
    
    @action(detail=True, methods=['get'])
    def ejemplares_json(self, request, pk=None):
        libro = self.get_object()
        ejemplares = Ejemplar.objects.filter(libro=libro)
        serializer = EjemplarSerializer(ejemplares, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def agregar_ejemplar(self, request, pk=None): 
        libro = self.get_object()

        cantidad = int(request.data.get('cantidad', 1))
        if cantidad <= 0:
            return Response(
                {'detail': 'La cantidad debe ser mayor que 0.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        nuevos = []

        # obtener último código existente
        ultimo = Ejemplar.objects.filter(libro=libro).order_by('-id').first()

        if ultimo:
            ultimo_num = int(ultimo.codigo.split('-')[-1])
        else:
            ultimo_num = 0

        for i in range(1, cantidad + 1):
            codigo = f"{libro.codigo_libro}-{ultimo_num + i}"

            ejemplar = Ejemplar.objects.create(
                libro=libro,
                codigo=codigo,
            )
            nuevos.append(ejemplar)

        serializer = EjemplarSerializer(nuevos, many=True)

        return Response(serializer.data, status=201)

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
        if self.request.user.is_superuser:
            return queryset

        encargado = getattr(self.request.user, 'encargado', None)
        if encargado:
            return queryset.filter(libro__encargado_agrego__nivel=encargado.nivel)
        return queryset.none()

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