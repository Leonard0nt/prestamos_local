from django.contrib import admin
from django.urls import path

from rest_framework.routers import DefaultRouter
from librosApp.views import EjemplarViewSet, LibroViewSet
from prestamoApp.views import PrestamoViewSet
from usuarioApp.views import EncargadoBibliotecaViewSet, UsuarioViewSet, actualizar_credenciales_view, login_view, logout_view

router = DefaultRouter()

router.register(r'usuarios', UsuarioViewSet)
router.register(r'encargados', EncargadoBibliotecaViewSet)
router.register(r'libros', LibroViewSet)
router.register(r'prestamos', PrestamoViewSet)
router.register(r'ejemplares', EjemplarViewSet)

urlpatterns = [
    path('', PrestamoViewSet.dashboard, name='dashboard'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),

    # UI
    path('usuarios-ui/', UsuarioViewSet.usuarios_view, name='usuarios_ui'),
    path('encargados-ui/', EncargadoBibliotecaViewSet.encargados_view, name='encargados_ui'),
    path('libros-ui/', LibroViewSet.libros_view, name='libros_ui'),
    path('libros/<int:libro_id>/ejemplares/', LibroViewSet.ejemplares_view, name='libro_ejemplares'),
    path('mi-cuenta/actualizar/', actualizar_credenciales_view, name='actualizar_credenciales'),
]

urlpatterns += router.urls