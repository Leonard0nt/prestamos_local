from django.http import JsonResponse
from django.shortcuts import redirect, render
from rest_framework import permissions, viewsets
from rest_framework.response import Response
from rest_framework import status

from .models import EncargadoBiblioteca, usuario
from .serializers import EncargadoBibliotecaSerializer, UsuarioSerializer



def login_view(request):
    """Modo escritorio: no se solicita inicio de sesión."""
    return redirect('dashboard')


def logout_view(request):
    """Modo escritorio: no existe sesión que cerrar."""
    return redirect('dashboard')

def actualizar_credenciales_view(request):
    return JsonResponse(
        {
            'detail': (
                'La configuración de credenciales está deshabilitada en modo escritorio '
                'porque la aplicación funciona sin inicio de sesión.'
            )
        },
        status=405,
    )
def _landing_url(_user):
    return 'dashboard'

class UsuarioViewSet(viewsets.ModelViewSet):
    queryset = usuario.objects.filter(activo=True)
    serializer_class = UsuarioSerializer

    @staticmethod
    def usuarios_view(request):
        return render(request, 'usuarios.html')

    def destroy(self, request, *args, **kwargs):
        usuario_obj = self.get_object()
        usuario_obj.activo = False
        usuario_obj.save(update_fields=['activo'])
        return Response(status=status.HTTP_204_NO_CONTENT)


class EncargadoBibliotecaViewSet(viewsets.ModelViewSet):
    queryset = EncargadoBiblioteca.objects.all()
    serializer_class = EncargadoBibliotecaSerializer
    permission_classes = [permissions.AllowAny]

    @staticmethod
    def encargados_view(request):
        return render(request, 'encargados.html')

    def destroy(self, request, *args, **kwargs):
        encargado = self.get_object()
        user = encargado.user
        encargado.delete()

        if user:
            user.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)