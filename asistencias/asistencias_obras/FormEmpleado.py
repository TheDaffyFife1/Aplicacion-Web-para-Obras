from django import forms
from .models import Empleado, Puesto

class EmpleadoForm(forms.ModelForm):
    class Meta:
        model = Empleado
        fields = ['nombre', 'apellido', 'puesto', 'obra', 'num_identificacion', 'sueldo', 'fotografia']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'apellido': forms.TextInput(attrs={'class': 'form-control'}),
            'num_identificacion': forms.NumberInput(attrs={'class': 'form-control'}),
            'sueldo': forms.NumberInput(attrs={'class': 'form-control'}),
            # Añade más widgets según necesites para personalizar la presentación de los campos
        }
