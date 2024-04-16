from django import forms
from django.core.exceptions import ValidationError
from .models import UserProfile, Obra
from .models import UserProfile, Obra
from .roles import ADMIN_ROLE, RH_ROLE, USER_ROLE

class AsignarObraForm(forms.ModelForm):
    obras = forms.ModelMultipleChoiceField(
        queryset=Obra.objects.all(),
        widget=forms.CheckboxSelectMultiple(),
        required=False
    )

    class Meta:
        model = UserProfile
        fields = ['obras']

    def __init__(self, *args, **kwargs):
        self.user_profile = kwargs.pop('user_profile', None)
        super(AsignarObraForm, self).__init__(*args, **kwargs)

    def clean_obras(self):
        obras = self.cleaned_data.get('obras')
        if self.user_profile.role == RH_ROLE and obras.count() > 2:
            raise ValidationError("Un usuario de RH no puede tener más de dos obras asignadas.")
        elif self.user_profile.role == USER_ROLE and obras.count() > 1:
            raise ValidationError("Un usuario no puede tener más de una obra asignada.")
        return obras
