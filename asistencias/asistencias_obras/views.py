from calendar import monthrange
from itertools import groupby
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import Group
from .roles import ADMIN_ROLE, RH_ROLE, USER_ROLE
from .models import UserProfile,Obra,Empleado,Puesto,Asistencia
from django.contrib.auth.decorators import login_required
from .RegistrationForm import RegistrationForm
from django.contrib.auth import login
from django.db import IntegrityError
from django.http import HttpResponseForbidden, HttpResponseRedirect,JsonResponse,HttpResponseBadRequest
from .RegistrationObra import ObraForm
from django.urls import reverse
from .FormAsignarObra import AsignarObraForm
from .FormEmpleado import EmpleadoForm
from django.core.serializers import serialize
import json
from django import forms
from django.views.decorators.http import require_POST
from django.utils import timezone
from datetime import timedelta
from django.db.models import Sum, Count, Q
from django.db.models.functions import TruncWeek, TruncMonth
from django.core.serializers import serialize
from django.db.models.functions import Coalesce
from django.db.models import ExpressionWrapper, F, FloatField
from django.db.models.functions import Cast, Coalesce, Least
from django.db.models import Count, Case, When, DecimalField
from django.utils.timezone import now
from django.db.models import F, FloatField, ExpressionWrapper, Case, When, Value, IntegerField
from django.views.decorators.cache import never_cache
from calendar import monthrange
from dateutil.relativedelta import relativedelta
from weasyprint import HTML, CSS
from django.template.loader import render_to_string
from django.http import HttpResponse


@login_required
def accesos(request):
    # Asumiendo que los roles son variables globales o están importados correctamente
    role = request.user.userprofile.role
    if role == ADMIN_ROLE:
        return redirect('admin_dashboard')
    elif role == RH_ROLE:
        return redirect('rh_dashboard')
    
    elif role == USER_ROLE:
        return redirect('user_asistencia')
    else:
        # Puedes redirigir a una página de error o a la página de inicio, etc.
        return redirect('default_page')

# =========================================================== Funciones para administrador ============================================ 
@login_required
def admin_dashboard(request):
    if request.user.userprofile.role != ADMIN_ROLE:
        return HttpResponseForbidden("No tienes permiso para ver esta página.")
    return render(request, 'admin/admin_dashboard.html')


@login_required
def register(request):
    if request.user.userprofile.role != ADMIN_ROLE:
        return HttpResponseForbidden("No tienes permiso para ver esta página.")

    form = RegistrationForm(request.POST or None)  # Inicializa el formulario con datos POST o vacío

    if request.method == 'POST':
        if form.is_valid():
            try:
                # Intenta crear el usuario y su perfil de usuario correspondiente
                user = form.save()  # Guarda la información del usuario
                user.refresh_from_db()  # Carga la instancia del usuario recién creada

                # Establece los atributos adicionales del usuario aquí si es necesario
                # user.profile.some_attribute = 'some_value'
                
                user.save()  # Guarda los cambios en el objeto de usuario

                # Verifica si ya existe un UserProfile para el usuario
                if not UserProfile.objects.filter(user=user).exists():
                    role = form.cleaned_data.get('role')
                    UserProfile.objects.create(user=user, role=role)  # Crea el perfil de usuario con el rol

                    login(request, user)  # Inicia sesión del usuario
                    return redirect('accesos')  # Redirecciona según el rol del usuario
                else:
                    # Si el UserProfile ya existe, muestra un mensaje de error
                    form.add_error(None, 'El usuario ya tiene un perfil asignado.')
                    form = RegistrationForm()  # Resetea el formulario después de un error
            except IntegrityError as e:
                # Añade un mensaje de error al formulario si hay un error de integridad
                form.add_error(None, f'Ocurrió un error de integridad: {e}')
                form = RegistrationForm()  # Resetea el formulario después de un error

    return render(request, 'admin/registro.html', {'form': form})

@login_required
def crear_obra(request):
    """
    Vista para crear una nueva obra. Maneja solicitudes GET para mostrar el formulario y POST para procesar el formulario.
    """
    if request.user.userprofile.role != ADMIN_ROLE:
        return HttpResponseForbidden("No tienes permiso para ver esta página.")
    if request.method == 'POST':
        form = ObraForm(request.POST)
        if form.is_valid():
            form.save()
            # Reemplaza 'lista_obras' con el nombre de la ruta de la vista a la que deseas redirigir
            return redirect('lista_obras')
    else:
        form = ObraForm()  # Inicializa un formulario en blanco para solicitudes GET

    # Renderiza el template con el formulario, sea nuevo o con errores
    return render(request, 'admin/registro_obra.html', {'form': form})

@login_required
def lista_obras(request):
    """
    Vista para listar todas las obras registradas en la base de datos.
    """
    if request.user.userprofile.role != ADMIN_ROLE:
        return HttpResponseForbidden("No tienes permiso para ver esta página.")
    obras = Obra.objects.all()  # Recupera todas las obras
    return render(request, 'admin/lista_obras.html', {'obras': obras})

@login_required
def cambiar_estado_obra(request, obra_id):
    if request.user.userprofile.role != ADMIN_ROLE:
        return HttpResponseForbidden("No tienes permiso para ver esta página.")
    obra = Obra.objects.get(id=obra_id)
    obra.activa = not obra.activa
    obra.save()
    return HttpResponseRedirect(reverse('lista_obras'))

@login_required
@require_POST  # Asegura que esta vista solo acepte solicitudes POST
def eliminar_obra(request, obra_id):
    if request.user.userprofile.role != ADMIN_ROLE:
        return HttpResponseForbidden("No tienes permiso para realizar esta acción.")

    obra = get_object_or_404(Obra, id=obra_id)
    obra.delete()
    
    # Reemplaza request.is_ajax() con la comprobación del encabezado HTTP_X_REQUESTED_WITH
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success', 'message': 'Obra eliminada correctamente'})
    else:
        return HttpResponseRedirect(reverse('lista_obras'))

    
@login_required
def editar_obra(request, obra_id):
    if request.user.userprofile.role != ADMIN_ROLE:
        return HttpResponseForbidden("No tienes permiso para ver esta página.")
    obra = get_object_or_404(Obra, id=obra_id)
    if request.method == 'POST':
        form = ObraForm(request.POST, instance=obra)
        if form.is_valid():
            form.save()
            return redirect('lista_obras')
    else:
        form = ObraForm(instance=obra)
    return render(request, 'admin/editar_obra.html', {'form': form, 'obra': obra})

@login_required
def asignar_obra_a_usuario(request, user_profile_id):
    if request.user.userprofile.role != ADMIN_ROLE:
        return HttpResponseForbidden("No tienes permiso para ver esta página.")
    
    user_profile = get_object_or_404(UserProfile, pk=user_profile_id)
    
    if request.method == 'POST':
        form = AsignarObraForm(request.POST, instance=user_profile, user_profile=user_profile)
        if form.is_valid():
            form.save()
            return redirect('lista_user_profiles')
        else:
            # Si el formulario no es válido, se renderiza de nuevo con errores.
            return render(request, 'admin/asignar_obra.html', {'form': form, 'user_profile': user_profile})
    else:
        form = AsignarObraForm(instance=user_profile, user_profile=user_profile)

    return render(request, 'admin/asignar_obra.html', {'form': form, 'user_profile': user_profile})

@login_required
def lista_user_profiles(request):
    if request.user.userprofile.role != ADMIN_ROLE:
        return HttpResponseForbidden("No tienes permiso para ver esta página.")
    # Si deseas filtrar por roles específicos, puedes hacerlo aquí
    user_profiles = UserProfile.objects.filter(role__in=[RH_ROLE, USER_ROLE])
    return render(request, 'admin/lista_user_profiles.html', {'user_profiles': user_profiles})

#Progreso de las obras Administrador
@login_required
def progreso_obras(request):
    try:
        time_range = request.GET.get('time_range', 'weekly')
        conjunto = int(request.GET.get('conjunto', 1))
        today = now().date()

        if time_range == 'weekly':
            start_date = today - timedelta(days=today.weekday() + 7 * (conjunto - 1))
            end_date = start_date + timedelta(days=6)
        elif time_range == 'monthly':
            start_date = today.replace(day=1)
            end_date = today.replace(day=monthrange(today.year, today.month)[1])
        elif time_range == 'multiweek':
            start_date = today - timedelta(days=today.weekday() + 7 * (conjunto - 1))
            end_date = start_date + timedelta(days=7 * conjunto - 1)

        # Asegura que las obras sean activas durante el rango de fechas especificado
        obras_activas = Obra.objects.filter(fecha_inicio__lte=end_date, fecha_fin__gte=start_date)

        labels = []
        data = []

        for obra in obras_activas:
            tiempo_total = (obra.fecha_fin - obra.fecha_inicio).days + 1  # +1 to include the end day
            tiempo_transcurrido = (today - obra.fecha_inicio).days + 1
            porcentaje_transcurrido = (tiempo_transcurrido / tiempo_total) * 100 if tiempo_total > 0 else 0
            porcentaje_transcurrido = min(porcentaje_transcurrido, 100)  # Limitar el porcentaje a 100%
            labels.append(obra.nombre)
            data.append(int(porcentaje_transcurrido))

        return JsonResponse({'labels': labels, 'data': data})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)  
    
@login_required
def attendance_by_week_project(request):
    # Retrieve request parameters
    time_range = request.GET.get('time_range', 'weekly')
    conjunto = int(request.GET.get('conjunto', 1))
    today = timezone.now().date()

    # Determine the time range for the query
    if time_range == 'weekly':
        week_start = today - timedelta(days=today.weekday() + 7 * (conjunto - 1))
        week_end = week_start + timedelta(days=6)
    elif time_range == 'monthly':
        week_start = today.replace(day=1)
        week_end = week_start + relativedelta(months=1, days=-1)
    elif time_range == 'multiweek':
        week_start = today - timedelta(days=today.weekday() + 7 * (conjunto - 1))
        week_end = week_start + timedelta(days=7 * conjunto - 1)

    # Prepare the response dictionary
    response_data = {
        'weekly_data': [],
        'daily_data': []
    }

    # Get the relevant projects for the time range
    projects = Obra.objects.filter(fecha_inicio__lte=week_end, fecha_fin__gte=week_start)

    # Calculate total employees per project
    for project in projects:
        project_data = {
            'project_name': project.nombre,
            'daily_attendance': []
        }
        
        total_employees = project.empleado_set.count()
        project_data['total_employees'] = total_employees

        # Calculate daily attendance details
        for single_date in (week_start + timedelta(n) for n in range((week_end - week_start).days + 1)):
            attendees = project.empleado_set.filter(
                asistencias__fecha=single_date,
                asistencias__entrada__isnull=False,
                asistencias__salida__isnull=False
            ).distinct()
            attended_count = attendees.count()

            half_day_attendees = project.empleado_set.filter(
                asistencias__fecha=single_date,
                asistencias__entrada__isnull=False,
                asistencias__salida__isnull=True
            ).distinct()
            half_day_count = half_day_attendees.count()

            not_attended_count = total_employees - attended_count - half_day_count

            project_data['daily_attendance'].append({
                'date': single_date,
                'attended': attended_count,
                'not_attended': not_attended_count,
                'half_day': half_day_count
            })

        # Add project data to weekly data
        response_data['weekly_data'].append(project_data)

    # Summarize weekly data
    for project in response_data['weekly_data']:
        weekly_not_attended = sum(day['not_attended'] for day in project['daily_attendance'])
        project['weekly_not_attended'] = weekly_not_attended

    return JsonResponse(response_data, safe=False)


@login_required
def summary_week_data(request):
    time_range = request.GET.get('time_range', 'weekly')
    conjunto = int(request.GET.get('conjunto', 1))
    today = timezone.now().date()

    # Time range calculations
    if time_range == 'weekly':
        start_date = today - timedelta(days=today.weekday() + 7 * (conjunto - 1))
        end_date = start_date + timedelta(days=6)
    elif time_range == 'monthly':
        month_first_day = today.replace(day=1) - timedelta(days=31 * (conjunto - 1))
        last_day = monthrange(month_first_day.year, month_first_day.month)[1]
        start_date = month_first_day
        end_date = month_first_day.replace(day=last_day)
    elif time_range == 'multiweek':
        start_date = today - timedelta(days=today.weekday() + 7 * (conjunto - 1))
        end_date = start_date + timedelta(days=7 * conjunto - 1)

    if not start_date or not end_date:
        return JsonResponse({'error': 'Invalid time range.'}, status=400)

    # Querying active projects and employees
    active_projects = Obra.objects.filter(
        Q(fecha_inicio__lte=end_date) & Q(fecha_fin__gte=start_date)
    )
    active_projects_id = active_projects.values_list('id', flat=True)

    # Calculating payments and handling half-days
    valid_attendances = Asistencia.objects.filter(
    fecha__range=(start_date, end_date),
    entrada__isnull=False,
    empleado__obra__id__in=active_projects_id
).values('empleado', 'fecha').annotate(
    daily_payment=ExpressionWrapper(
        Coalesce(Sum(
            ExpressionWrapper(F('empleado__sueldo') / 6, output_field=DecimalField()),
            filter=Q(salida__isnull=False)
        ), 0) + Coalesce(Sum(
            ExpressionWrapper(F('empleado__sueldo') / 12, output_field=DecimalField()),  # Assuming half pay for half-days
            filter=Q(salida__isnull=True)
        ), 0),
        output_field=DecimalField()
    )
).order_by('empleado')

    total_payment = sum(attendance['daily_payment'] for attendance in valid_attendances) if valid_attendances else 0.0
    total_payment = round(total_payment, 2)
    total_payment_float = float(total_payment)

    active_employees_count = Empleado.objects.filter(obra__id__in=active_projects_id).distinct().count()

    # Fetching and using attendance data
    attendance_response = attendance_by_week_project(request)
    attendance_data = json.loads(attendance_response.content.decode('utf-8'))

    # Calculating attendance metrics
    total_attended = 0
    total_half_days = 0
    total_possible_attendances = 0

    for project in attendance_data['weekly_data']:
        project_attended = sum(day['attended'] for day in project['daily_attendance'])
        project_half_days = sum(day['half_day'] for day in project['daily_attendance'])
        total_attended += project_attended
        total_half_days += project_half_days
        total_possible_attendances += project['total_employees'] * ((end_date - start_date).days + 1)

    # Calculating attendance percentage
    attendance_percentage = ((total_attended + 0.5 * total_half_days) / total_possible_attendances * 100) if total_possible_attendances > 0 else 0

    return JsonResponse({
        'data': {
            'active_projects': active_projects.count(),
            'active_employees': active_employees_count,
            'total_payment_for_week': total_payment_float,
            'attendance_percentage': int(attendance_percentage)
        }
    }, safe=False)

@login_required
def tabla_pagos(request):
    time_range = request.GET.get('time_range', 'weekly')
    conjunto = int(request.GET.get('conjunto', 1))
    today = timezone.now().date()

    if time_range == 'weekly':
        start_date = today - timedelta(days=today.weekday() + (conjunto - 1) * 7)
        end_date = start_date + timedelta(days=6)
    elif time_range == 'multiweek':
        start_date = today - timedelta(days=today.weekday())
        end_date = start_date + timedelta(weeks=conjunto) - timedelta(days=1)
    elif time_range == 'monthly':
        if conjunto == 1:
            start_date = today.replace(day=1)
        else:
            start_date = today.replace(day=1)
            for _ in range(1, conjunto):
                start_date = (start_date - timedelta(days=1)).replace(day=1)
        last_day = monthrange(start_date.year, start_date.month)[1]
        end_date = start_date.replace(day=last_day)

    active_obras = Obra.objects.filter(fecha_inicio__lte=end_date, fecha_fin__gte=start_date)
    active_projects_id = active_obras.values('id')

    valid_attendances = Asistencia.objects.filter(
        fecha__range=(start_date, end_date),
        entrada__isnull=False,
        salida__isnull=False,
        empleado__obra__id__in=active_projects_id
    ).annotate(
        days_worked=Count('fecha'),
        total_payment=ExpressionWrapper(
            Coalesce(F('days_worked') * F('empleado__puesto__sueldo_base') / 6, 0),
            output_field=DecimalField(max_digits=10, decimal_places=2)
        )
    ).order_by('empleado')

    if not valid_attendances.exists():
        return JsonResponse({'error': 'No data found for the specified range.'}, status=404)

    response_data = list(valid_attendances.values('empleado__nombre', 'empleado__obra__nombre', 'days_worked', 'total_payment'))
    print(response_data)
    return JsonResponse({'data': response_data}, safe=False)

@login_required
def supervisores_obras(request):
    time_range = request.GET.get('time_range', 'weekly')
    conjunto = int(request.GET.get('conjunto', 1))
    today = now().date()

    if time_range == 'weekly':
        start_date = today - timedelta(days=today.weekday() + (conjunto - 1) * 7)
        end_date = start_date + timedelta(days=6)
    elif time_range == 'multiweek':
        start_date = today - timedelta(days=today.weekday())
        end_date = start_date + timedelta(weeks=conjunto) - timedelta(days=1)
    elif time_range == 'monthly':
        if conjunto == 1:
            start_date = today.replace(day=1)
        else:
            start_date = today.replace(day=1)
            for _ in range(1, conjunto):
                start_date = (start_date - timedelta(days=1)).replace(day=1)
        last_day = monthrange(start_date.year, start_date.month)[1]
        end_date = start_date.replace(day=last_day)

    # Filtrar obras activas en el rango de fechas especificado
    active_obras = Obra.objects.filter(fecha_inicio__lte=end_date, fecha_fin__gte=start_date)
    active_projects_id = active_obras.values_list('id', flat=True)

    supervisores = UserProfile.objects.filter(role=RH_ROLE)
    data = []

    for supervisor in supervisores:
        obras_activas = supervisor.obras.filter(id__in=active_projects_id)
        print(f'Supervisor: {supervisor.user.username}, Obras Activas: {[obra.nombre for obra in obras_activas]}')
        for obra in obras_activas:
            data.append({
                'nombre': supervisor.user.username,
                'obra': obra.nombre
            })
    print("Start Date:", start_date)
    print("End Date:", end_date)
    print("Active obras IDs:", list(active_projects_id))

    data = sorted(data, key=lambda x: x['obra'])
    return JsonResponse({"data": data}, safe=False)



# ===================================================Aplicacion de RH ===================================================
def is_ajax(request):
    return request.headers.get('X-Requested-With') == 'XMLHttpRequest'

# Dise;o de RH Dashboard
@login_required
def rh_dashboard(request):
    user_profile = request.user.userprofile
    if user_profile.role == RH_ROLE:
        obras = user_profile.obras.all()
        if obras.exists():
            selected_obra_id = request.GET.get('obra_id', obras.first().id)  # Obra predeterminada si no se especifica
            try:
                selected_obra = obras.get(id=selected_obra_id)
                if is_ajax(request):  # Usa la función is_ajax aquí
                    obra_data = {
                        'id': selected_obra.id,
                        'nombre': selected_obra.nombre,
                        # Agrega más datos según necesites
                    }
                    return JsonResponse(obra_data)
                # Renderizar página normalmente si no es una petición AJAX
                return render(request, 'rh/rh_dashboard.html', {'obras': obras, 'selected_obra': selected_obra})
            except obras.model.DoesNotExist:
                return HttpResponseBadRequest("Obra no encontrada.")
        else:
            return HttpResponseForbidden("Este usuario de RH no tiene obras asignadas.")
    else:
        return HttpResponseForbidden("No tienes permiso para ver esta página.")
    
@login_required
def lista_empleados(request):
    user_profile = request.user.userprofile
    if user_profile.role == RH_ROLE:
        obras = user_profile.obras.all()
        if obras.exists():
            obra_id = request.GET.get('obra_id')
            if obra_id:
                obra = get_object_or_404(Obra, id=obra_id)
                empleados = Empleado.objects.filter(obra=obra)
                return render(request, 'rh/lista_empleados.html', {'empleados': empleados, 'obra': obra, 'obras': obras})
            else:
                # Returning obras but no empleados if obra_id is not specified
                return render(request, 'rh/lista_empleados.html', {'obras': obras})
        else:
            return HttpResponseForbidden("Este usuario de RH no tiene obras asignadas.")
    else:
        return HttpResponseForbidden("No tienes permiso para ver esta página.")

@login_required
def crear_empleado(request):
    user_profile = request.user.userprofile
    if user_profile.role == RH_ROLE:
        obras = user_profile.obras.all()
        if not obras.exists():
            return HttpResponseForbidden("Este usuario de RH no tiene obras asignadas.")

        obra_id = request.GET.get('obra_id')
        obra = get_object_or_404(Obra, id=obra_id) if obra_id else None

        if request.method == 'POST' and obra:
            form = EmpleadoForm(request.POST, request.FILES)
            if form.is_valid():
                empleado = form.save(commit=False)
                empleado.obra = obra  # Directly assign the obra object
                empleado.save()
                return redirect(f'/empleados?obra_id={obra_id}')
        else:
            # Si no hay un obra_id en GET o no estamos en POST, mostramos un formulario vacío o preseleccionado
            initial_data = {'obra': obra} if obra else {}
            form = EmpleadoForm(initial=initial_data)
            if obra:
                form.fields['obra'].widget = forms.HiddenInput()

        sueldos_base = {str(puesto.id): str(puesto.sueldo_base) for puesto in Puesto.objects.all()}
        sueldos_base_json = json.dumps(sueldos_base)

        return render(request, 'rh/registro_empleados.html', {
            'form': form,
            'sueldos_base': sueldos_base_json,
            'obras': obras,
               'selected_obra': obra
        })
    else:
        return HttpResponseForbidden("No tienes permiso para ver esta página.")
    
@login_required
def editar_empleado(request, empleado_id):

    empleado = get_object_or_404(Empleado, id=empleado_id)
    
    if request.method == 'POST':
        form = EmpleadoForm(request.POST, request.FILES, instance=empleado)
        if form.is_valid():
            form.save()
            return redirect('lista_empleados')  # Asume que tienes esta vista y URL definidas
    else:
        form = EmpleadoForm(instance=empleado)
    
    return render(request, 'rh/editar_empleado.html', {'form': form, 'empleado': empleado})

@login_required
def reporte_asistencia(request):
    user_profile = request.user.userprofile
    if user_profile.role != RH_ROLE:
        return HttpResponseForbidden("No tienes permiso para ver esta página.")

    obras = user_profile.obras.all()
    if not obras.exists():
        return HttpResponseForbidden("Este usuario de RH no tiene obras asignadas.")

    obra_id = request.GET.get('obra_id')
    if not obra_id:
        # No obra_id provided, show the page to select an obra
        return render(request, 'rh/reporte_asistencia.html', {'obras': obras})

    obra = get_object_or_404(Obra, id=obra_id)
    empleados = Empleado.objects.filter(obra=obra)

    hoy = timezone.localtime().date()
    inicio_semana = hoy - timedelta(days=hoy.weekday())  # Lunes
    fin_semana = inicio_semana + timedelta(days=5)  # Sábado

    asistencias_semana_actual = Asistencia.objects.filter(
        empleado__obra=obra,
        fecha__range=(inicio_semana, fin_semana)
    ).select_related('empleado').order_by('fecha')

    empleados_context = {
        empleado.id: {
            'nombre': empleado.nombre + " " + empleado.apellido,
            'foto_url': empleado.fotografia.url if empleado.fotografia else None,
            'sueldo_total': empleado.sueldo,
            'asistencias': {dia: {'entrada': None, 'salida': None, 'foto_dia': None, 'sueldo_diario': 0} for dia in range(6)}
        } for empleado in empleados
    }

    for asistencia in asistencias_semana_actual:
        dia_semana = asistencia.fecha.weekday()
        empleado_context = empleados_context.get(asistencia.empleado_id)
        if empleado_context:
            empleado_context['asistencias'][dia_semana] = {
                'entrada': asistencia.entrada,
                'salida': asistencia.salida,
                'foto_dia': asistencia.foto.url if asistencia.foto else None,
                'sueldo_diario': empleado_context['sueldo_total'] / 6
            }
            if not (asistencia.entrada and asistencia.salida):
                empleado_context['asistencias'][dia_semana]['sueldo_diario'] /= 2

    for datos in empleados_context.values():
        total_semanal = sum(asistencia['sueldo_diario'] for asistencia in datos['asistencias'].values())
        datos['total_semanal'] = total_semanal

    context = {
        'empleados_context': empleados_context.values(),
        'obra': obra,
        'inicio_semana': inicio_semana,
        'fin_semana': fin_semana,
            'obra_id': obra_id,  # Asegúrate de pasar obra_id

        'obras': obras  # Include obras to maintain the drop-down list state
    }

    return render(request, 'rh/reporte_asistencia.html', context)

@login_required
def reporte_asistencia_pdf(request, obra_id):
    obra = get_object_or_404(Obra, id=obra_id)
    empleados = Empleado.objects.filter(obra=obra)

    hoy = timezone.localtime().date()
    inicio_semana = hoy - timedelta(days=hoy.weekday())  # Lunes
    fin_semana = inicio_semana + timedelta(days=5)  # Sábado

    asistencias_semana_actual = Asistencia.objects.filter(
        empleado__obra=obra,
        fecha__range=(inicio_semana, fin_semana)
    ).select_related('empleado').order_by('fecha')

    empleados_context = {
        empleado.id: {
            'nombre': empleado.nombre + " " + empleado.apellido,
            'foto_url': empleado.fotografia.url if empleado.fotografia else None,
            'sueldo_total': empleado.sueldo,
            'asistencias': {dia: {'entrada': None, 'salida': None, 'foto_dia': None, 'sueldo_diario': 0} for dia in range(6)}
        } for empleado in empleados
    }

    for asistencia in asistencias_semana_actual:
        dia_semana = asistencia.fecha.weekday()
        empleado_context = empleados_context.get(asistencia.empleado_id)
        if empleado_context:
            empleado_context['asistencias'][dia_semana] = {
                'entrada': asistencia.entrada,
                'salida': asistencia.salida,
                'foto_dia': asistencia.foto.url if asistencia.foto else None,
                'sueldo_diario': empleado_context['sueldo_total'] / 6
            }
            if not (asistencia.entrada and asistencia.salida):
                empleado_context['asistencias'][dia_semana]['sueldo_diario'] /= 2

    for datos in empleados_context.values():
        total_semanal = sum(asistencia['sueldo_diario'] for asistencia in datos['asistencias'].values())
        datos['total_semanal'] = total_semanal

    context = {
        'empleados': empleados_context.values(),
        'obra': obra,
        'week_start': inicio_semana,
        'week_end': fin_semana
    }

    # Render the HTML template with data
    html_string = render_to_string('rh/reporte_asistencia_pdf.html', context)

    # Generate the PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{obra.nombre}_reporte_asistencia_{hoy.strftime("%Y%m%d")}.pdf"'
    HTML(string=html_string).write_pdf(response, stylesheets=[
        CSS(string='@page { size: A4 landscape; margin: 1cm; } body { font-family: Arial; }')
    ])

    return response

@login_required
def asistencia_obras(request):
    time_range = request.GET.get('time_range', 'weekly')
    conjunto = request.GET.get('conjunto', 1)
    try:
        conjunto = int(conjunto) if conjunto.isdigit() else 1
    except ValueError:
        conjunto = 1

    today = timezone.now().date()

    # Inicializa start_date y end_date a None
    start_date = None
    end_date = None

    if time_range == 'weekly' or time_range == 'range':
        start_date = today - timedelta(days=today.weekday(), weeks=(conjunto - 1))
        end_date = start_date + timedelta(days=6)
    elif time_range == 'monthly':
        start_date = today.replace(day=1) - timedelta(days=31 * (conjunto - 1))
        end_date = today

    else:
        # Opción para manejar un valor no esperado en time_range
        return JsonResponse({'error': 'El rango de tiempo especificado no es válido.'}, status=400)
    
    if start_date is None or end_date is None:
        # Asegurarse de que start_date y end_date estén definidos
        return JsonResponse({'error': 'Las fechas de inicio y fin no están definidas.'}, status=500)
    # Filtrar asistencias dentro del rango de fechas
    obras_con_asistencias = Obra.objects.filter(
        empleado__asistencia__fecha__range=(start_date, end_date)
    ).annotate(
        total_asistencias=Count('empleado__asistencia', distinct=True),
        total_empleados=Count('empleado', distinct=True)
    )

    # Calcular el porcentaje de asistencias por obra
    obras_data = []
    for obra in obras_con_asistencias:
        # Asumiendo que cada empleado debería haber asistido cada día de trabajo
        dias_laborales = (end_date - start_date).days + 1
        porcentaje = (obra.total_asistencias / (obra.total_empleados * dias_laborales) * 100) if obra.total_empleados else 0
        obras_data.append({
            'obra_nombre': obra.nombre,
            'porcentaje_asistencia': int(porcentaje)
        })

    # Retorna la información en formato JSON
    return JsonResponse({'obras': obras_data})

@login_required
def obras_con_empleados(request):
    #  modelo 'Obra' y  modelo 'Empleado' con una llave foranea a 'Obra'
    todas_las_obras = Obra.objects.prefetch_related('empleado_set').all()

    # Construye un diccionario para cada obra con su lista de empleados
    data = [
        {
            'obra_id': obra.id,
            'obra_nombre': obra.nombre,
            'empleados': [
                {
                    'empleado_id': empleado.id,
                    'empleado_nombre': empleado.nombre,
                    'empleado_puesto_id': empleado.puesto.id,
                }
                for empleado in obra.empleado_set.all()
            ]
        }
        for obra in todas_las_obras
    ]
  
    return JsonResponse({'obras': data})

@login_required
def progreso_obras_indivual(request):
    hoy = now().date()  # Asegúrate de trabajar solo con la parte de la fecha.
    # Filtra las obras que están dentro del rango de fechas actual.
    obras_activas = Obra.objects.filter(fecha_inicio__lte=hoy, fecha_fin__gte=hoy)
    
    labels = []
    data = []
    resto = []

    for obra in obras_activas:
        tiempo_total = (obra.fecha_fin - obra.fecha_inicio).days
        tiempo_transcurrido = (hoy - obra.fecha_inicio).days

        # Asegúrate de que el tiempo transcurrido sea positivo antes de calcular el porcentaje.
        if tiempo_transcurrido > 0:
            porcentaje_transcurrido = (tiempo_transcurrido / tiempo_total) * 100 if tiempo_total > 0 else 0
            restante = 100 - porcentaje_transcurrido

            labels.append(obra.nombre)  # Nombre de la obra.
            data.append(abs(int(porcentaje_transcurrido)))  # Porcentaje de progreso de la obra.
            resto.append(int(restante))  # Porcentaje restante para completar la obra.

    return JsonResponse({'labels': labels, 'data': data, 'resto': resto})




@login_required
def progreso(request):
    obra_id = request.GET.get('id')
    hoy = now()
    user = request.user.userprofile
    data = []

    if user.role == RH_ROLE:
        try:
            obra = Obra.objects.get(id=obra_id)  # Use get() to retrieve a single instance
            total = (obra.fecha_fin - obra.fecha_inicio).days
            transcurrido = (hoy.date() - obra.fecha_inicio).days

            if transcurrido > 0:
                porcentaje = (transcurrido / total) * 100 if total else 0
                if porcentaje > 100:
                    porcentaje = 100
                    resto = 0
                else:
                    resto = 100 - porcentaje
                porcentaje = round(porcentaje, 2)
                resto = round(resto, 2)
                data.append({
                    'obra_nombre': obra.nombre,
                    'porcentaje': porcentaje,
                    'restante': resto
                })
        except Obra.DoesNotExist:
            return JsonResponse({'error': 'Obra not found'}, status=404)
    return JsonResponse({'data': data}, safe=False)


@login_required
def summary_week_data_RH(request):
    obra_id = request.GET.get('obra_id')
    user = request.user.userprofile
    if user.role != RH_ROLE:
        return HttpResponseBadRequest("Acceso no autorizado.")

    obra = get_object_or_404(Obra, id=obra_id)
    today = timezone.now().date()
    this_week_start = today - timezone.timedelta(days=today.weekday())
    this_week_end = this_week_start + timezone.timedelta(days=6)

    valid_attendances_week = Asistencia.objects.filter(
    fecha__gte=this_week_start,
    fecha__lte=this_week_end,
    empleado__obra_id=obra_id,  # Ajuste aquí
    entrada__isnull=False,
    salida__isnull=False
).values('empleado', 'fecha').annotate(daily_payment=Sum('empleado__sueldo')/6).order_by('empleado')
    
    total_payment_for_week = sum(attendance['daily_payment'] for attendance in valid_attendances_week)
    total_payment_for_week = round(total_payment_for_week, 2)
    active_employees_count = Empleado.objects.filter(obra=obra).distinct().count()

    porcentaje_asistencia = (len(valid_attendances_week) / active_employees_count) * 100 if active_employees_count > 0 else 0

    data = {
        'obra': obra.nombre,
        'active_employees': active_employees_count,
        'total_payment_for_week': total_payment_for_week,
        'porcentaje': int(porcentaje_asistencia)
    }

    return JsonResponse(data, safe=False)

@login_required
def attendance_by_week_project_RH(request):
    obra_id = request.GET.get('obra_id', None)
    if not obra_id:
        return HttpResponseBadRequest("No se proporcionó un ID de obra válido.")

    user = request.user.userprofile
    if user.role != RH_ROLE:
        return HttpResponseBadRequest("No autorizado.")

    obra = get_object_or_404(Obra, id=obra_id)
    
    today = timezone.now().date()
    week_start = today - timezone.timedelta(days=today.weekday())
    week_end = week_start + timezone.timedelta(days=6)

    # Ensure that the attendance_data QuerySet is properly used
    attendance_data = Obra.objects.filter(id=obra_id).annotate(
        full_time=Count(
            Case(
                When(
                    Q(empleado__asistencia__entrada__isnull=False) & 
                    Q(empleado__asistencia__salida__isnull=False) & 
                    Q(empleado__asistencia__fecha__range=(week_start, week_end)),
                    then=1
                )
            )
        ),
        part_time=Count(
            Case(
                When(
                    Q(empleado__asistencia__entrada__isnull=False) & 
                    Q(empleado__asistencia__salida__isnull=True) & 
                    Q(empleado__asistencia__fecha__range=(week_start, week_end)),
                    then=1
                )
            )
        ),
        not_attended=Count(
            Case(
                When(
                    Q(empleado__asistencia__entrada__isnull=True) & 
                    Q(empleado__asistencia__fecha__range=(week_start, week_end)),
                    then=1
                )
            )
        )
    ).values('full_time', 'part_time', 'not_attended')[0]  # Use indexing after values()

    active_employees_count = Empleado.objects.filter(obra=obra).distinct().count()

    # Simplify data aggregation and usage
    faltas = active_employees_count - sum(attendance_data.values())
    data = {
        'labels': ['Jornadas completas', 'Jornada Incompleta', 'Sin Asistencia'],
        'data': [
            attendance_data['full_time'],
            attendance_data['part_time'],
            faltas
        ]
    }

    return JsonResponse(data)

# =============================================== Funciones para Supervisor =====================================================
@login_required
def user_asistencia(request):
    user_profile = request.user.userprofile
    if user_profile.role == USER_ROLE:
        obras = user_profile.obras.all()
        if obras.exists():
            selected_obra_id = request.GET.get('obra_id')
            if selected_obra_id:
                try:
                    selected_obra = obras.get(id=selected_obra_id)
                    # Aquí puedes procesar la información específica de la obra seleccionada
                    # y luego pasar esos datos al template
                except obras.model.DoesNotExist:
                    return HttpResponseBadRequest("Obra no encontrada.")
            return render(request,'supervisor/user_asistencia.html', {'obra': obras})
        else:
            # Manejar el caso de que no haya un ID de obra asociado
            return HttpResponseForbidden("Este usuario no tiene una obra asignada.")
    else:
        return HttpResponseForbidden("No tienes permiso para ver esta página.")

    


# ================== Variables Nuevas de Dashboard Admin ====================================