from django.contrib.auth.models import User
from rest_framework import serializers
from .models import EncargadoBiblioteca, usuario


class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = usuario
        fields = '__all__'


class EncargadoBibliotecaSerializer(serializers.ModelSerializer):
    password_temporal = serializers.CharField(read_only=True)

    class Meta:
        model = EncargadoBiblioteca
        fields = ['id', 'nombre', 'rut', 'correo', 'creado_en', 'password_temporal']
        read_only_fields = ['id', 'creado_en', 'password_temporal']

    def create(self, validated_data):
        rut = validated_data['rut']
        correo = validated_data['correo']
        nombre = validated_data['nombre']

        base_username = rut.replace('.', '').replace('-', '').lower()
        username = base_username
        idx = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{idx}"
            idx += 1

        password_temporal = f"{base_username[:6]}123!"

        user = User.objects.create_user(
            username=username,
            email=correo,
            password=password_temporal,
            first_name=nombre,
            is_staff=False,
            is_superuser=False,
        )

        encargado = EncargadoBiblioteca.objects.create(user=user, **validated_data)
        encargado.password_temporal = password_temporal
        return encargado
