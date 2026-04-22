from django.contrib.auth.models import User
from rest_framework import serializers
from .models import EncargadoBiblioteca, usuario


def obtener_password_inicial_desde_rut(rut):
    rut_normalizado = (rut or '').strip()
    cuerpo_rut = rut_normalizado.split('-')[0]
    digitos_cuerpo = ''.join(ch for ch in cuerpo_rut if ch.isdigit())
    return digitos_cuerpo[-4:]


class UsuarioSerializer(serializers.ModelSerializer):
    nivel_pertenencia = serializers.SerializerMethodField()

    def get_nivel_pertenencia(self, obj):
        if obj.nivel_asignado == usuario.NIVEL_MEDIA:
            return 'Media'
        if obj.nivel_asignado == usuario.NIVEL_BASICA:
            return 'Basica'

        encargado = getattr(obj, 'encargado_agrego', None)
        return encargado.get_nivel_display() if encargado else ''

    def validate(self, attrs):
        request = self.context.get('request')
        if (
            request
            and request.user.is_superuser
            and self.instance is None
            and not attrs.get('nivel_asignado')
        ):
            raise serializers.ValidationError(
                {'nivel_asignado': 'Debes seleccionar un nivel (Basica o Media).'}
            )
        return attrs

    class Meta:
        model = usuario
        fields = '__all__'


class EncargadoBibliotecaSerializer(serializers.ModelSerializer):
    password_temporal = serializers.CharField(read_only=True)

    class Meta:
        model = EncargadoBiblioteca
        fields = ['id', 'nombre', 'rut', 'correo', 'nivel', 'creado_en', 'password_temporal']
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

        password_temporal = obtener_password_inicial_desde_rut(rut)

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

    def update(self, instance, validated_data):
        user = instance.user

        instance.nombre = validated_data.get('nombre', instance.nombre)
        instance.rut = validated_data.get('rut', instance.rut)
        instance.correo = validated_data.get('correo', instance.correo)
        instance.save()

        if user:
            user.first_name = instance.nombre
            user.email = instance.correo

            base_username = instance.rut.replace('.', '').replace('-', '').lower()
            username = base_username
            idx = 1
            while User.objects.filter(username=username).exclude(pk=user.pk).exists():
                username = f"{base_username}{idx}"
                idx += 1

            user.username = username
            user.save()

        return instance