from django.shortcuts import render, get_object_or_404
from .models import Libro, Ejemplar
from .serializers import LibroSerializer, EjemplarSerializer
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status

class LibroViewSet(ModelViewSet):
    queryset = Libro.objects.all()
    serializer_class = LibroSerializer

    @staticmethod
    def libros_view(request):
        libros = Libro.objects.all()
        return render(request, 'libros.html', {'libros': libros})

    @staticmethod
    def ejemplares_view(request, libro_id):
        libro = get_object_or_404(Libro, id=libro_id)
        ejemplares = Ejemplar.objects.filter(libro=libro)

        return render(request, 'ejemplares.html', {
            'libro': libro,
            'ejemplares': ejemplares
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

        cantidad = int(request.data.get("cantidad", 1))

        nuevos = []

        # obtener último código existente
        ultimo = Ejemplar.objects.filter(libro=libro).order_by('-id').first()

        if ultimo:
            ultimo_num = int(ultimo.codigo.split('-')[-1])
        else:
            ultimo_num = 0

        for i in range(1, cantidad + 1):
            codigo = f"{libro.id}-{ultimo_num + i}"

            ejemplar = Ejemplar.objects.create(
                libro=libro,
                codigo=codigo
            )
            nuevos.append(ejemplar)

        serializer = EjemplarSerializer(nuevos, many=True)

        return Response(serializer.data, status=201)

class EjemplarViewSet(ModelViewSet):
    queryset = Ejemplar.objects.all()
    serializer_class = EjemplarSerializer

    def destroy(self, request, *args, **kwargs):
        ejemplar = self.get_object()

        # 🚫 VALIDACIÓN
        if ejemplar.estado != 'disponible':
            return Response(
                {"error": "No se puede eliminar un ejemplar que no está disponible"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ✅ si pasa validación, elimina normal
        return super().destroy(request, *args, **kwargs)