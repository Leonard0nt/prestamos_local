from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from datetime import date
from django.shortcuts import render
from .models import prestamo
from .serializers import PrestamoSerializer

class PrestamoViewSet(viewsets.ModelViewSet):
    queryset = prestamo.objects.all()
    serializer_class = PrestamoSerializer

    @staticmethod
    def dashboard(request):
        return render(request, 'dashboard.html')


    @action(detail=False, methods=['get'])
    def historial(self, request):
        historial = prestamo.objects.filter(activo=False)
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
        ejemplar.estado = 'disponible'
        ejemplar.save()
        prestamo_obj.save()

        return Response({
            "mensaje": "Libro devuelto correctamente",
            "estado": prestamo_obj.estado,
            "dias_atraso": prestamo_obj.dias_atraso
        })
    
    def get_queryset(self):
        queryset = prestamo.objects.filter(activo=True)
        hoy = date.today()

        for p in queryset:
            if p.estado == 'P' and hoy > p.fecha_devolucion:
                p.estado = 'A'
                p.dias_atraso = (hoy - p.fecha_devolucion).days
                p.save()

        return queryset
    def destroy(self, request, *args, **kwargs):
        prestamo_obj = self.get_object()
        prestamo_obj.activo = False
        prestamo_obj.save()

        return Response({"mensaje": "Préstamo archivado (no eliminado)"})
