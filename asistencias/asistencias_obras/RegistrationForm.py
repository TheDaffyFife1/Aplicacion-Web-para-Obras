from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import UserProfile
from .roles import ADMIN_ROLE, RH_ROLE, USER_ROLE

# Formulario de creación de usuarios con campo adicional para el rol
class RegistrationForm(UserCreationForm):
    # Agregamos el campo de rol al formulario
    role = forms.ChoiceField(choices=[
        (ADMIN_ROLE, 'Admin'),
        (RH_ROLE, 'RH'),
        (USER_ROLE, 'User'),
    ])

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2', 'role']

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            # Ensure that you don't create a duplicate UserProfile
            if not UserProfile.objects.filter(user=user).exists():
                UserProfile.objects.create(user=user, role=self.cleaned_data['role'])
        return user
