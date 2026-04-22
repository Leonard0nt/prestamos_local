from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import redirect, render
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import EncargadoBiblioteca, usuario
from .serializers import (
    EncargadoBibliotecaSerializer,
    UsuarioSerializer,
    obtener_password_inicial_desde_rut,
)

SESSION_TIMEOUT_SECONDS = 9 * 60 * 60


def login_view(request):
    if request.user.is_authenticated:
        return redirect(_landing_url(request.user))

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)

        if user is None:
            messages.error(request, 'Usuario o contraseña incorrectos.')
        else:
            login(request, user)
            request.session.set_expiry(SESSION_TIMEOUT_SECONDS)
            if user.is_superuser:
                messages.success(request, 'Inicio de sesión exitoso: perfil administrador.')
            elif hasattr(user, 'encargado'):
                messages.success(request, 'Inicio de sesión exitoso: perfil encargado.')
            else:
                logout(request)
                messages.error(
                    request,
                    'Tu cuenta no tiene un rol válido para ingresar al sistema.',
                )
                return redirect('login')

            return redirect(_landing_url(user))

    return render(request, 'login.html')


def logout_view(request):
    logout(request)
    messages.info(request, 'Sesión cerrada correctamente.')
    return redirect('login')


@login_required(login_url='login')
def actualizar_credenciales_view(request):
    if request.method != 'POST':
        return JsonResponse({'detail': 'Método no permitido.'}, status=405)

    user = request.user
    username = request.POST.get('username', '').strip()
    email = request.POST.get('email', '').strip()
    password = request.POST.get('password', '')

    if not username:
        return JsonResponse({'detail': 'El nombre de usuario es obligatorio.'}, status=400)

    username_existente = user.__class__.objects.filter(username=username).exclude(pk=user.pk).exists()
    if username_existente:
        return JsonResponse({'detail': 'El nombre de usuario ya está en uso.'}, status=400)

    if password:
        try:
            validate_password(password, user=user)
        except ValidationError as error:
            return JsonResponse({'detail': error.messages[0]}, status=400)
        user.set_password(password)

    user.username = username
    user.email = email
    user.save()

    if password:
        login(request, user)

    return JsonResponse({'detail': 'Configuración actualizada correctamente.'})


def _landing_url(user):
    return 'encargados_ui' if user.is_superuser else 'dashboard'


class UsuarioViewSet(viewsets.ModelViewSet):
    queryset = usuario.objects.filter(activo=True)
    serializer_class = UsuarioSerializer

    def get_queryset(self):
        queryset = usuario.objects.all()

        if not self.request.user.is_superuser:
            encargado = getattr(self.request.user, 'encargado', None)
            if encargado:
                queryset = queryset.filter(
                    Q(nivel_asignado=encargado.nivel) |
                    Q(nivel_asignado__isnull=True, encargado_agrego=encargado)
                )
            else:
                return queryset.none()

        if self.action == 'list':
            queryset = queryset.filter(activo=True)

        return queryset

    def perform_create(self, serializer):
        encargado = getattr(self.request.user, 'encargado', None)
        if encargado:
            serializer.save(encargado_agrego=encargado, nivel_asignado=encargado.nivel)
            return
        serializer.save()

    @staticmethod
    @login_required(login_url='login')
    def usuarios_view(request):
        return render(request, 'usuarios.html')

    def destroy(self, request, *args, **kwargs):
        usuario_obj = self.get_object()
        if not usuario_obj.activo:
            return Response(
                {'detail': 'El usuario ya está desactivado.'},
                status=status.HTTP_200_OK,
            )

        usuario_obj.activo = False
        usuario_obj.save(update_fields=['activo'])
        return Response(
            {'detail': 'Usuario desactivado correctamente. Se conserva su historial.'},
            status=status.HTTP_200_OK,
        )


class EncargadoBibliotecaViewSet(viewsets.ModelViewSet):
    queryset = EncargadoBiblioteca.objects.all()
    serializer_class = EncargadoBibliotecaSerializer
    permission_classes = [permissions.IsAdminUser]

    @staticmethod
    @user_passes_test(lambda u: u.is_authenticated and u.is_superuser)
    def encargados_view(request):
        return render(request, 'encargados.html')

    def destroy(self, request, *args, **kwargs):
        encargado = self.get_object()
        user = encargado.user
        encargado.delete()

        if user:
            user.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def reestablecer_password(self, request, pk=None):
        encargado = self.get_object()
        user = encargado.user

        if not user:
            return Response(
                {'detail': 'El encargado no tiene un usuario asociado.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        password_temporal = obtener_password_inicial_desde_rut(encargado.rut)
        if not password_temporal:
            return Response(
                {'detail': 'No fue posible calcular una contraseña válida desde el RUT.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(password_temporal)
        user.save(update_fields=['password'])

        return Response(
            {
                'detail': 'Contraseña reestablecida correctamente.',
                'password_temporal': password_temporal,
            },
            status=status.HTTP_200_OK,
        )   