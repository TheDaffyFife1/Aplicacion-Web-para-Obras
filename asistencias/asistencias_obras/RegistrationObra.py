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
        widgets = {
            'fecha_inicio': forms.DateInput(format=('%Y-%m-%d'), attrs={'class': 'form-control', 'placeholder': 'Selecciona una fecha', 'type': 'date'}),
            'fecha_fin': forms.DateInput(format=('%Y-%m-%d'), attrs={'class': 'form-control', 'placeholder': 'Selecciona una fecha', 'type': 'date'}),
        }