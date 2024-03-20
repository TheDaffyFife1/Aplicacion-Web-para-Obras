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
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path
from asistencias_obras.views import asistencia_obras, obras_con_empleados, progreso_obras, progreso_obras_indivual, reporte_asistencia,editar_empleado,lista_obras,accesos, register, admin_dashboard, rh_dashboard, user_asistencia,crear_obra,cambiar_estado_obra, eliminar_obra, editar_obra,lista_user_profiles,asignar_obra_a_usuario,lista_empleados,crear_empleado
from django.contrib.auth import views as auth_views
from asistencias_obras import views
from asistencias_obras.api import registrar_asistencia
from asistencias_obras.views import attendance_by_week_project,project_progress,summary_week_data



urlpatterns = [
    path('', auth_views.LoginView.as_view(template_name='login.html'), name='root_login'),
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('registro/', register, name='register'),
    path('accesos/', views.accesos, name='accesos'),
    path('admin_dashboard/', admin_dashboard, name='admin_dashboard'),
    path('rh_dashboard/', rh_dashboard, name='rh_dashboard'),
    path('user_asistencia/', user_asistencia, name='user_asistencia'),
    path('obra/crear/', crear_obra, name='crear_obra'),
    path('obras/', views.lista_obras, name='lista_obras'),
    path('obra/cambiar_estado/<int:obra_id>/', views.cambiar_estado_obra, name='cambiar_estado_obra'),
    path('obra/eliminar/<int:obra_id>/', views.eliminar_obra, name='eliminar_obra'),
    path('obras/', lista_obras, name='lista_obras'),
    path('obra/editar/<int:obra_id>/', editar_obra, name='editar_obra'),
    path('asignaciones/', lista_user_profiles, name='lista_user_profiles'),
    path('user_profile/<int:user_profile_id>/asignar_obra/', asignar_obra_a_usuario, name='asignar_obra_a_usuario'),
    path('empleados/', views.lista_empleados, name='lista_empleados'),
    path('empleados/crear_empleado/', views.crear_empleado, name='crear_empleado'),
    path('empleados/crear_empleado/<int:obra_id>/', crear_empleado, name='crear_empleado'),
    path('empleados/editar/<int:empleado_id>/', editar_empleado, name='editar_empleado'),
    path('api/registrar_asistencia/', registrar_asistencia, name='registrar_asistencia'),
    path('reporte-asistencia/', reporte_asistencia, name='reporte_asistencia'),
    path('reporte-asistencia/<str:fecha_referencia>/', reporte_asistencia, name='reporte_asistencia_con_fecha'),
    path('attendance-by-project/', views.attendance_by_week_project, name='attendance_by_project'),
    path('project-progress/', views.project_progress, name='project_progress'),
    path('summary-data/', views.summary_week_data, name='summary_data'),


    #dashboard Ashwin
    path('ajax/progreso_obras/', progreso_obras, name='progreso_obras'),
    path('ajax/asistencia_obras/', asistencia_obras, name='asistencia_obras'),
    path('ajax/obras_con_empleados/', obras_con_empleados, name='obras_con_empleados'),
    path('ajax/progreso_obras_indivual/', progreso_obras_indivual, name='progreso_obras_indivual'),
    # ... other paths ...
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)