from django import forms
from .models import Obra

class ObraForm(forms.ModelForm):
    class Meta:
        model = Obra
        fields = ['nombre', 'ubicacion', 'descripcion', 'presupuesto','fecha_inicio','fecha_fin']
        labels = {
            'nombre': 'Nombre de la Obra',
            'ubicacion': 'Ubicación',
            'descripcion': 'Descripción',
            'presupuesto': 'Presupuesto',
            'fecha_inicio': 'Fecha de Inicio',
            'fecha_fin': 'Fecha de Fin'
        }