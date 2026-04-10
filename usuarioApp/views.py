from urllib import request
from django.shortcuts import render

from rest_framework import viewsets
from .models import usuario
from .serializers import UsuarioSerializer

class UsuarioViewSet(viewsets.ModelViewSet):
    queryset = usuario.objects.all()
    serializer_class = UsuarioSerializer

    def usuarios_view(request):
        return render(request, 'usuarios.html')