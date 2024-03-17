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

    foto = request.FILES.get('foto', None)  # Obtener la foto del request

    fecha_hoy = timezone.now().date()
    asistencia, created = Asistencia.objects.get_or_create(
        empleado=empleado, 
        fecha=fecha_hoy,
        defaults={'entrada': timezone.now()}
    )

    if created:
        asistencia.foto = foto  # Guardar la foto si es un registro nuevo
    else:
        if asistencia.salida is None:
            asistencia.salida = timezone.now()
            asistencia.save()
            return Response({'mensaje': 'Salida registrada correctamente.'})
        else:
            return Response({'error': 'Entrada y salida ya registradas para hoy.'}, status=status.HTTP_409_CONFLICT)

    asistencia.save()  # No olvides guardar el objeto después de modificarlo
    return Response({'mensaje': 'Registro actualizado correctamente.'})