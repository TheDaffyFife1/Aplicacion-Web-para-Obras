from rest_framework import serializers, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Empleado, Asistencia
from django.utils import timezone
import datetime

class AsistenciaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asistencia
        fields = ['empleado', 'fecha', 'entrada', 'salida']

@api_view(['POST'])
def registrar_asistencia(request):
    num_identificacion = request.data.get('num_identificacion')
    try:
        empleado = Empleado.objects.get(num_identificacion=num_identificacion)
    except Empleado.DoesNotExist:
        return Response({'error': 'Empleado no encontrado'}, status=status.HTTP_404_NOT_FOUND)

    fecha_hoy = timezone.now().date()
    asistencia, created = Asistencia.objects.get_or_create(
        empleado=empleado, 
        fecha=fecha_hoy,
        defaults={'entrada': timezone.now()}
    )

    if not created and asistencia.salida is None:
        # Si ya existe una asistencia para hoy y no se ha registrado la salida
        hora_actual = timezone.now()
        asistencia.salida = hora_actual
        asistencia.save()
        return Response({'mensaje': 'Salida registrada correctamente.'})

    elif not created:
        return Response({'error': 'Entrada y salida ya registradas para hoy.'}, status=status.HTTP_409_CONFLICT)

    return Response({'mensaje': 'Entrada registrada correctamente.'})
