from django.db import models

# Create your models here.

class Puesto(models.Model):
    nombre = models.CharField(max_length=100, verbose_name="Nombre del Puesto")
    descripcion = models.TextField(verbose_name="Descripción", null=True, blank=True)

    def str(self):
        return self.nombre

    class Meta:
        verbose_name = "puesto"
        verbose_name_plural = "puestos"


class Obra(models.Model):
    nombre = models.CharField(max_length=100, verbose_name="Nombre de la Obra")
    ubicacion = models.CharField(max_length=100, verbose_name="Ubicación", null=True, blank=True)
    descripcion = models.TextField(verbose_name="Descripción", null=True, blank=True)

    def str(self):
        return self.nombre

    class Meta:
        verbose_name = "obra"
        verbose_name_plural = "obras"

#Modelo de empleado
class Empleado(models.Model):
    nombre = models.CharField(max_length=100, verbose_name="Nombre")
    apellido = models.CharField(max_length=100, verbose_name="Apellido")
    puesto = models.ForeignKey(Puesto, on_delete=models.CASCADE, verbose_name="Puesto")
    obra = models.ForeignKey(Obra, on_delete=models.CASCADE, verbose_name="Obra")
    num_identificacion = models.IntegerField(verbose_name="Número de Identificación")

    def str(self):
        return f"{self.nombre} {self.apellido} ({self.num_identificacion})"

    class Meta:
        verbose_name = "empleado"
        verbose_name_plural = "empleados"
