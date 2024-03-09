"""asistencias URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from asistencias_obras.views import accesos, register, admin_dashboard, rh_dashboard, user_asistencia
from django.contrib.auth import views as auth_views
from asistencias_obras import views

urlpatterns = [
    path('', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('register/', register, name='register'),
    path('accesos/', views.accesos, name='accesos'),
    path('admin_dashboard/', admin_dashboard, name='admin_dashboard'),
    path('rh_dashboard/', rh_dashboard, name='rh_dashboard'),
    path('user_asistencia/', user_asistencia, name='user_asistencia'),
    # ... other paths ...
]