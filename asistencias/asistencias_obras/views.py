from django.shortcuts import render
from django.contrib.auth.models import Group

# Create your views here.
def create_user_groups():
    # Lista de nombres de grupos a crear
    group_names = ['admin', 'rh', 'user']

    for group_name in group_names:
        group, created = Group.objects.get_or_create(name=group_name)
        if created:
            print(f'Grupo creado: {group_name}')
        else:
            print(f'Grupo {group_name} ya existe')