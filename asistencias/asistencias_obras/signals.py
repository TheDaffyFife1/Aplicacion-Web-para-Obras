from django.db.models.signals import pre_delete
from django.dispatch import receiver
from .models import Empleado, EmpleadoEliminado

@receiver(pre_delete, sender=Empleado)
def guardar_empleado_eliminado(sender, instance, **kwargs):
    puesto_nombre = instance.puesto.nombre if instance.puesto else ''
    obra_nombre = instance.obra.nombre if instance.obra else ''
    EmpleadoEliminado.objects.create(
        nombre=instance.nombre,
        apellido=instance.apellido,
        puesto=puesto_nombre,
        obra=obra_nombre,
        num_identificacion=instance.num_identificacion
    )
