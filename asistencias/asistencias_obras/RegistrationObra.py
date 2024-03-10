from django import forms
from .models import Obra

class ObraForm(forms.ModelForm):
    class Meta:
        model = Obra
        fields = ['nombre', 'ubicacion', 'descripcion', 'presupuesto']
        labels = {
            'nombre': 'Nombre de la Obra',
            'ubicacion': 'Ubicación',
            'descripcion': 'Descripción',
            'presupuesto': 'Presupuesto'
        }