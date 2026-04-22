from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from django.db.models import Q

from librosApp.models import Ejemplar

from datetime import date
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import prestamo
from .serializers import PrestamoSerializer

class PrestamoViewSet(viewsets.ModelViewSet):
    queryset = prestamo.objects.all()
    serializer_class = PrestamoSerializer

    @staticmethod
    @login_required(login_url='login')
    def dashboard(request):
        vista = request.GET.get('vista', 'activos')
        vista = vista if vista in ['activos', 'archivados'] else 'activos'
        return render(request, 'dashboard.html', {
            'prestamos_vista': vista,
            'active_tab': 'prestamos_archivados' if vista == 'archivados' else 'prestamos',
        })


    @action(detail=False, methods=['get'])
    def historial(self, request):
        historial = prestamo.objects.filter(activo=False)
        if not request.user.is_superuser:
            encargado = getattr(request.user, 'encargado', None)
            if encargado:
                historial = historial.filter(
                    Q(nivel_asignado=encargado.nivel) |
                    Q(nivel_asignado__isnull=True, encargado_agrego__nivel=encargado.nivel)
                )
            else:
                historial = historial.none()
        serializer = self.get_serializer(historial, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def devolver(self, request, pk=None):
        prestamo_obj = self.get_object()
        hoy = date.today()

        # Evitar devolver dos veces
        if prestamo_obj.estado == 'D':
            return Response({"error": "Este libro ya fue devuelto"}, status=400)

        # Calcular atraso
        if hoy > prestamo_obj.fecha_devolucion:
            dias = (hoy - prestamo_obj.fecha_devolucion).days
            prestamo_obj.estado = 'A'
            prestamo_obj.dias_atraso = dias
        else:
            prestamo_obj.estado = 'D'
            prestamo_obj.dias_atraso = 0

        ejemplar = prestamo_obj.ejemplar
        if ejemplar.estado not in {Ejemplar.ESTADO_BAJA, Ejemplar.ESTADO_EXTRAVIADO, Ejemplar.ESTADO_DANIADO}:
            ejemplar.estado = Ejemplar.ESTADO_DISPONIBLE
            ejemplar.save(update_fields=['estado'])
        prestamo_obj.save()

        return Response(
            {
                'mensaje': 'Libro devuelto correctamente',
                'estado': prestamo_obj.estado,
                'dias_atraso': prestamo_obj.dias_atraso,
            }
        )

    def get_queryset(self):
        queryset = prestamo.objects.filter(activo=True)

        if not self.request.user.is_superuser:
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

        hoy = date.today()

        for p in queryset:
            if p.estado == 'P' and hoy > p.fecha_devolucion:
                p.estado = 'A'
                p.dias_atraso = (hoy - p.fecha_devolucion).days
                p.save()

        return queryset

    def perform_create(self, serializer):
        encargado = getattr(self.request.user, 'encargado', None)
        if encargado and not self.request.user.is_superuser:
            ejemplar = serializer.validated_data['ejemplar']
            usuario_obj = serializer.validated_data['usuario']

            nivel_ejemplar = ejemplar.libro.nivel_asignado or getattr(
                ejemplar.libro.encargado_agrego, 'nivel', None
            )
            nivel_usuario = usuario_obj.nivel_asignado or getattr(
                usuario_obj.encargado_agrego, 'nivel', None
            )

            mismo_nivel_ejemplar = (
                nivel_ejemplar is not None
                and nivel_ejemplar == encargado.nivel
            )
            mismo_nivel_usuario = (
                nivel_usuario is not None
                and nivel_usuario == encargado.nivel
            )

            if not mismo_nivel_ejemplar or not mismo_nivel_usuario:
                raise ValidationError("Solo puedes crear préstamos con libros y usuarios de tu nivel.")

            serializer.save(encargado_agrego=encargado, nivel_asignado=encargado.nivel)
            return

        serializer.save()

    def destroy(self, request, *args, **kwargs):
        prestamo_obj = self.get_object()
        prestamo_obj.activo = False
        prestamo_obj.save(update_fields=['activo'])

        return Response({"mensaje": "Préstamo archivado (no eliminado)"})
