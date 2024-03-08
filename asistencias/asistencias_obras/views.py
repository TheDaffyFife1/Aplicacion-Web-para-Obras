from django.shortcuts import render, redirect
from django.contrib.auth.models import Group
from .roles import ADMIN_ROLE, RH_ROLE, USER_ROLE
from .models import UserProfile
from django.contrib.auth.decorators import login_required

@login_required
def accesos(request):
    role = request.user.userprofile.role
    if role == ADMIN_ROLE:
        return redirect('admin_dashboard')
    elif role == RH_ROLE:
        return redirect('rh_dashboard')
    elif role == USER_ROLE:
        return redirect('user_asistencia')

@login_required
def admin_dashboard(request):
    return render(request, 'admin_dashboard.html')

@login_required
def rh_dashboard(request):
    return render(request, 'rh_dashboard.html')

@login_required
def user_asistencia(request):
    return render(request,'user_asistencia.html')