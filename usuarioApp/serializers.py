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

        rut_limpio = ''.join(ch for ch in rut if ch.isalnum()).lower()
        cuerpo_rut = rut_limpio[:-1] if len(rut_limpio) > 1 else rut_limpio
        password_temporal = cuerpo_rut[-4:] if len(cuerpo_rut) >= 4 else cuerpo_rut

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
