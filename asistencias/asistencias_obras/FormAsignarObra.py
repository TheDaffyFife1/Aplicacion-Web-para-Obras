from django import forms
from .models import UserProfile, Obra

class AsignarObraForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['obra']
        labels = {
            'obra': 'Asignar Obra',
        }