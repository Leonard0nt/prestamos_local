from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import render
from rest_framework import permissions, viewsets

from .models import EncargadoBiblioteca, usuario
from .serializers import EncargadoBibliotecaSerializer, UsuarioSerializer

@staticmethod
class UsuarioViewSet(viewsets.ModelViewSet):
    queryset = usuario.objects.all()
    serializer_class = UsuarioSerializer

    def usuarios_view(request):
        return render(request, 'usuarios.html')


class EncargadoBibliotecaViewSet(viewsets.ModelViewSet):
    queryset = EncargadoBiblioteca.objects.all()
    serializer_class = EncargadoBibliotecaSerializer
    permission_classes = [permissions.IsAdminUser]

    @staticmethod
    @user_passes_test(lambda u: u.is_authenticated and u.is_superuser)
    def encargados_view(request):
        return render(request, 'encargados.html')