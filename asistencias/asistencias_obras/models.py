from django.db import models
from .roles import ADMIN_ROLE, RH_ROLE, USER_ROLE
from django.contrib.auth.models import User
import uuid
from io import BytesIO
import qrcode
from django.core.files.base import ContentFile
from django.utils import timezone
from datetime import timedelta

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
    presupuesto = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Presupuesto", null=True, blank=True)
    activa = models.BooleanField(default=True)  # Campo para activar/inactivar
    fecha_inicio = models.DateField(null=True, blank=True)  # Opcional, para rango de fechas
    fecha_fin = models.DateField(null=True, blank=True)  # Opcional, para rango de fechas

    @property
    def porcentaje_tiempo_transcurrido(self):
        hoy = timezone.now().date()
        if not self.fecha_inicio or not self.fecha_fin:
            return 0
        total_dias = (self.fecha_fin - self.fecha_inicio).days
        dias_transcurridos = (hoy - self.fecha_inicio).days
        if hoy < self.fecha_inicio or total_dias <= 0:
            return 0
        if hoy > self.fecha_fin:
            return 100
        return (dias_transcurridos / total_dias) * 100

    def save(self, *args, **kwargs):
        if self.fecha_fin and timezone.now().date() > (self.fecha_fin + timedelta(days=1)):
            self.activa = False
        super().save(*args, **kwargs)

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
    fotografia = models.ImageField(upload_to='fotos_empleados/', verbose_name="Fotografía", null=True, blank=True)
    codigo_qr = models.ImageField(upload_to='codigos_qr_empleados/', verbose_name="Código QR", null=True, blank=True)

    def __str__(self):
        return f"{self.nombre} {self.apellido} ({self.num_identificacion})"

    def save(self, *args, **kwargs):
        if not self.sueldo:
            self.sueldo = self.puesto.sueldo_base
        super(Empleado, self).save(*args, **kwargs)

        # Generación del código QR
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(f'{self.nombre} {self.apellido} ({self.num_identificacion})')
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")

        # Guardar el código QR como una imagen en el campo correspondiente
        temp_handle = BytesIO()
        img.save(temp_handle, 'PNG')
        temp_handle.seek(0)
        self.codigo_qr.save(f'codigo_qr_{self.num_identificacion}.png', ContentFile(temp_handle.read()), save=False)
        temp_handle.close()

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
    fotografia = models.ImageField(upload_to='fotos_empleados/', verbose_name="Fotografía", null=True, blank=True)
    codigo_qr = models.ImageField(upload_to='codigos_qr_empleados/', verbose_name="Código QR", null=True, blank=True)

    fecha_eliminacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nombre} {self.apellido} ({self.num_identificacion}) eliminado en {self.fecha_eliminacion}"

    class Meta:
        verbose_name = "empleado eliminado"
        verbose_name_plural = "empleados eliminados"

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    role = models.CharField(max_length=50, choices=[
        (ADMIN_ROLE, 'Admin'),
        (RH_ROLE, 'RH'),
        (USER_ROLE, 'User'),
    ])
    obras = models.ManyToManyField(Obra, verbose_name="Obras", blank=True)  # Usamos ManyToManyField aquí

    def __str__(self):
        return self.user.username
    
class Asistencia(models.Model):
    empleado = models.ForeignKey(
        'Empleado',  # Use a string if Empleado is defined later in the file or imported from another module
        on_delete=models.CASCADE,
        related_name='asistencias'  # This is the name you use in prefetch_related
    )
    fecha = models.DateField(default=timezone.now)
    entrada = models.DateTimeField(null=True, blank=True)
    salida = models.DateTimeField(null=True, blank=True)
    foto = models.ImageField(upload_to='fotos_asistencia/', null=True, blank=True)

    def __str__(self):
        return f"{self.empleado.nombre} {self.fecha}"

    class Meta:
        verbose_name = "asistencia"
        verbose_name_plural = "asistencias"