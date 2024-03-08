from django.db import models

# Create your models here.

#Modelo Puesto
class Puesto(models.Model):
    nombre = models.CharField(max_length=100, verbose_name="Nombre del Puesto")
    descripcion = models.TextField(verbose_name="Descripción", null=True, blank=True)
    sueldo_base = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Sueldo Base")

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = "puesto"
        verbose_name_plural = "puestos"

#Modelo Obra
class Obra(models.Model):
    nombre = models.CharField(max_length=100, verbose_name="Nombre de la Obra")
    ubicacion = models.CharField(max_length=100, verbose_name="Ubicación", null=True, blank=True)
    descripcion = models.TextField(verbose_name="Descripción", null=True, blank=True)

    def __str__(self):
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
    sueldo = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Sueldo", null=True, blank=True)

    def __str__(self):
        return f"{self.nombre} {self.apellido} ({self.num_identificacion})"

    def save(self, *args, **kwargs):
        if not self.sueldo:
            self.sueldo = self.puesto.sueldo_base
        super(Empleado, self).save(*args, **kwargs)

    class Meta:
        verbose_name = "empleado"
        verbose_name_plural = "empleados"


#Modelo Empleado Eliminado
class EmpleadoEliminado(models.Model):
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    puesto = models.CharField(max_length=100)
    obra = models.CharField(max_length=100)
    num_identificacion = models.IntegerField()
    fecha_eliminacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nombre} {self.apellido} ({self.num_identificacion}) eliminado en {self.fecha_eliminacion}"

    class Meta:
        verbose_name = "empleado eliminado"
        verbose_name_plural = "empleados eliminados"
