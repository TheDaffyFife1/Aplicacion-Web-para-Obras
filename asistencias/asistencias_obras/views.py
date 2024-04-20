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
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
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
                    # Si el UserProfile ya existe, podrías redireccionar al usuario a una página de error o de inicio
                    # O mostrar un mensaje de error en la misma página de registro
                    form.add_error(None, 'El usuario ya tiene un perfil asignado.')
            except IntegrityError as e:
                # Añade un mensaje de error al formulario si hay un error de integridad (por ejemplo, un duplicado)
                form.add_error(None, f'Ocurrió un error de integridad: {e}')
            
    else:
        form = RegistrationForm()
    
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


@login_required
def attendance_by_week_project(request):
    # Leer parámetros de la petición
    time_range = request.GET.get('time_range', 'weekly')
    conjunto = int(request.GET.get('conjunto', 1))
    today = timezone.now().date()

    if time_range == 'weekly':
        week_start = today - timedelta(days=today.weekday() + 7 * (conjunto - 1))
        week_end = week_start + timedelta(days=6)
    elif time_range == 'monthly':
        week_start = today.replace(day=1)
        week_end = today.replace(day=1) + timedelta(days=monthrange(today.year, today.month)[1] - 1)
    elif time_range == 'multiweek':
        start_date = today - timedelta(days=today.weekday() + 7 * (conjunto - 1))
        end_date = start_date + timedelta(days=7 * conjunto - 1)

    # Ajustar la consulta para calcular asistencia semanal por proyecto
    # Usando min() para asegurarnos de que fecha_inicio__lte utiliza la fecha más temprana posible
    earliest_start = min(today, week_end)
    attendance_data = Obra.objects.filter(
        fecha_inicio__lte=earliest_start,
        fecha_fin__gte=week_start
    ).annotate(
        full_time=Count(
            Case(
                When(
                    empleado__asistencia__entrada__isnull=False,
                    empleado__asistencia__salida__isnull=False,
                    empleado__asistencia__fecha__range=(week_start, week_end),
                    then=1
                )
            )
        ),
        part_time=Count(
            Case(
                When(
                    empleado__asistencia__entrada__isnull=False,
                    empleado__asistencia__salida__isnull=True,
                    empleado__asistencia__fecha__range=(week_start, week_end),
                    then=1
                )
            )
        ),
        not_attended=Count(
            Case(
                When(
                    empleado__asistencia__entrada__isnull=True,
                    empleado__asistencia__fecha__range=(week_start, week_end),
                    then=1
                )
            )
        ),
        total_employees=Count('empleado', distinct=True)
    ).values('nombre', 'full_time', 'part_time', 'not_attended', 'total_employees')

    for obra in attendance_data:
        obra['not_attended'] = obra['total_employees'] - (obra['full_time'] + obra['part_time'])

    attendance_data = list(attendance_data)

    return JsonResponse(attendance_data, safe=False)

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
            end_date = today.replace(day=monthrange(today.year, today.month)[1] - 1)
        elif time_range == 'multiweek':
            start_date = today - timedelta(days=today.weekday() + 7 * (conjunto - 1))
            end_date = start_date + timedelta(days=7 * conjunto - 1)

        obras_activas = Obra.objects.filter(fecha_inicio__lte=today, fecha_fin__gte=start_date)

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
        return JsonResponse({'error': str(e)}, status=500)  # Provide error message in the response

@login_required
def summary_week_data(request):
    time_range = request.GET.get('time_range', 'weekly')
    conjunto = int(request.GET.get('conjunto', 1))
    today = now().date()

    start_date, end_date = None, None
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

    if start_date is None or end_date is None:
        return JsonResponse({'error': 'Invalid time range.'}, status=400)

    # Asegurándose de que solo se incluyan obras que han comenzado en o antes de la fecha actual o el inicio del intervalo
    active_obras = Obra.objects.filter(
        Q(fecha_inicio__lte=today) & (Q(fecha_inicio__lte=end_date) & Q(fecha_fin__gte=start_date))
    )
    active_projects_id = active_obras.values('id')

    valid_attendances = Asistencia.objects.filter(
        fecha__range=(start_date, end_date),
        entrada__isnull=False,
        salida__isnull=False,
        empleado__obra__id__in=active_projects_id
    ).values('empleado', 'fecha').annotate(daily_payment=Sum(F('empleado__sueldo') / 6)).order_by('empleado')

    total_payment = sum(attendance['daily_payment'] for attendance in valid_attendances) if valid_attendances else 0.0
    total_payment = round(total_payment, 2)
    total_payment_float = float(total_payment)  # Convertir Decimal a float

    active_employees_count = Empleado.objects.filter(obra__in=active_projects_id).distinct().count()

    data = attendance_by_week_project(request)
    data = json.loads(data.content)

    asistencia = [d['full_time'] + d['part_time'] for d in data]
    total = [d['total_employees'] for d in data]
    porcentaje = (sum(asistencia) / sum(total) * 100) if total and sum(total) > 0 else 0
    print("Total payment type:", type(total_payment_float))
    # En Django
    return JsonResponse({
        'data': {
            'active_projects': active_obras.count(),
            'active_employees': active_employees_count,
            'total_payment_for_week': total_payment_float,
            'attendance_percentage': int(porcentaje)
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
# ===================================================Aplicacion de RH ===================================================

# Dise;o de RH Dashboard
@login_required
def rh_dashboard(request):
    user_profile = request.user.userprofile
    if user_profile.role == RH_ROLE:
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
            # Si no se especifica obra_id, se pueden mostrar todas o ninguna
            return render(request, 'rh/rh_dashboard.html', {'obras': obras})
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
                # Si no se especifica obra_id, mostrar todas las obras pero sin seleccionar ninguna específicamente
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
                return redirect(f'/empleados    ?obra_id={obra_id}')
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
@never_cache  # Asegura que las respuestas de esta vista no sean almacenadas en cache.
def reporte_asistencia(request):
    user_profile = request.user.userprofile
    if user_profile.role == RH_ROLE:
        obras = user_profile.obras.all()
        if obras.exists():  # Verificar si el usuario tiene obras asignadas
            obra_id = request.GET.get('obra_id')
            if obra_id:
                obra = get_object_or_404(Obra, id=obra_id)
                empleados = Empleado.objects.filter(obra=obra)

                hoy = timezone.localtime().date()
                inicio_semana = hoy - timedelta(days=hoy.weekday())  # Lunes
                fin_semana = inicio_semana + timedelta(days=5)  # Sábado

                asistencias_semana_actual = Asistencia.objects.filter(
                    empleado__obra=obra,
                    fecha__range=(inicio_semana, fin_semana)
                ).select_related('empleado').order_by('fecha')

                empleados_context = {empleado.id: {
                    'nombre': empleado.nombre + " " + empleado.apellido,
                    'foto_url': empleado.fotografia.url if empleado.fotografia else None,
                    'sueldo_total': empleado.sueldo,
                    'asistencias': {dia: {'entrada': None, 'salida': None, 'foto_dia': None, 'sueldo_diario': 0} for dia in range(6)}
                } for empleado in empleados}

                for asistencia in asistencias_semana_actual:
                    dia_semana = asistencia.fecha.weekday()
                    empleado_context = empleados_context.get(asistencia.empleado_id)
                    if empleado_context:  # Verifica si el empleado está en la obra antes de proceder
                        empleado_context['asistencias'][dia_semana] = {
                            'entrada': asistencia.entrada,
                            'salida': asistencia.salida,
                            'foto_dia': asistencia.foto.url if asistencia.foto else None
                        }

                for datos in empleados_context.values():
                    sueldo_diario_completo = datos['sueldo_total'] / 6
                    total_semanal = 0
                    for asistencia in datos['asistencias'].values():
                        if asistencia['entrada'] and asistencia['salida']:
                            asistencia['sueldo_diario'] = sueldo_diario_completo
                        elif asistencia['entrada'] or asistencia['salida']:
                            asistencia['sueldo_diario'] = sueldo_diario_completo / 2
                        total_semanal += asistencia.get('sueldo_diario', 0)
                    datos['total_semanal'] = total_semanal

                context = {
                    'empleados_context': empleados_context.values(),
                    'obra': obra,
                    'inicio_semana': inicio_semana,
                    'fin_semana': fin_semana
                }

                return render(request, 'rh/reporte_asistencia.html', context)
            else:
                # Si no se especifica obra_id, mostrar todas las obras pero sin seleccionar ninguna específicamente
                return render(request, 'rh/reporte_asistencia.html', {'obras': obras})
        else:
            return HttpResponseForbidden("Este usuario de RH no tiene obras asignadas.")
    else:
        return HttpResponseForbidden("No tienes permiso para ver esta página.")




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
def supervisores_obras(request):
    supervisores = UserProfile.objects.all().filter(role=RH_ROLE)
    
    data = []

    for supervisor in supervisores:
        obras = Obra.objects.all().filter(id__in=supervisor.obras.all().values_list('id', flat=True))
        
        for obra in obras:

            data.append({
                'nombre': supervisor.user.username,
                'obra': obra.nombre
            })
    data = sorted(data, key=lambda x: x['obra'])

    return JsonResponse({"data":data}, safe=False)  


    
    data = []
    for key, group in groupby(response_data, key=lambda x: x['empleado__obra__nombre']):
        pagos = sum(d['total_payment'] for d in group)
        data.append({'obra': key, 'total_pago': pagos})
    unificados = sorted(unificados, key=lambda x: x['obra'])
    data = sorted(data, key=lambda x: x['obra'])
    suma = {}
    for pago in data:
        obra = pago['obra']
        total = pago['total_pago']
        if obra in suma:
            suma[obra] += total
        else:
            suma[obra] = total
    resultado = [{'obra': obra, 'total_pago': int(total)} for obra, total in suma.items()]

    obras = []
    pagos = []
    
    for obra in resultado:
        obras.append(obra['obra'])
        pagos.append(obra['total_pago'])

    return JsonResponse({'labels': obras, 'data': pagos}, safe=False)

@login_required
def progreso(request):
    obra_id = request.GET.get('id')
    hoy = now()
    user = request.user.userprofile
    data = []

    if user.role == RH_ROLE:
        obra = Obra.objects.filter(id=obra_id)
        
        total = (obra.fecha_fin - obra.fecha_inicio).days
        
        transcurrido = (hoy.date() - obra.fecha_inicio).days

        if transcurrido > 0:
            porcenaje = (transcurrido / total) * 100 if total else 0
            if porcenaje > 100:
                porcenaje = 100
                resto = 0
            resto = 100 - porcenaje
            porcenaje = round(porcenaje, 2)
            resto = round(resto, 2)
            data.append({
                    'obra_nombre': obra.nombre,
                    'porcentaje': porcenaje,
                    'restante': resto
                })
    return JsonResponse({'data':data}, safe=False)     

@login_required
def empleados_rh(request):
    user = request.user.userprofile
    data = []

    if user.role == RH_ROLE:
        obra = user.obra_id
        empleados = Empleado.objects.filter(obra=obra)
        for empleado in empleados:
            data.append({
                'nombre': empleado.nombre,
                'apellido': empleado.apellido,
                'puesto': empleado.puesto.nombre,
                'sueldo': empleado.sueldo
            })

    return JsonResponse({'data': data}, safe=False)


@login_required
def summary_week_data_RH(request):
    obra_id = request.GET.get('obra_id')
    user = request.user.userprofile
    data = []

    if user.role == RH_ROLE:
        obra = get_object_or_404(Obra, id=obra_id)
        today = timezone.now().date()
        this_week_start = today - timezone.timedelta(days=today.weekday())
        this_week_end = this_week_start + timezone.timedelta(days=6)


        # Asistencia válida para la semana actual
        valid_attendances_week = Asistencia.objects.filter(
            fecha__gte=this_week_start,
            fecha__lte=this_week_end,
            entrada__isnull=False,
            salida__isnull=False
        ).values('empleado', 'fecha').annotate(daily_payment=Sum(F('empleado__sueldo')/6)).order_by('empleado')

        # Inicializar el total del pago para la semana
        total_payment_for_week = 0

        # Calcular el sueldo total de la semana basado en la asistencia válida
        for attendance in valid_attendances_week:
            total_payment_for_week += attendance['daily_payment']

        total_payment_for_week = round(total_payment_for_week, 2)
        active_employees_count = Empleado.objects.filter(obra=obra_id).distinct().count()



        data = attendance_by_week_project_RH(request)
        data = json.loads(data.content)

        data = data['data']

        asistencia = data[0] + data[1]
        porcentaje = (asistencia/active_employees_count) * 100



        # Contar proyectos y empleados activos

        data = {
            'obra' : obra.nombre,
            'active_employees': active_employees_count,
            'total_payment_for_week': total_payment_for_week,
            'porcentaje': int(porcentaje)

        }

    return JsonResponse(data, safe=False)

@login_required
def attendance_by_week_project_RH(request):
    obra_id = request.GET.get('obra_id', None)

    user = request.user.userprofile
   
    if user.role == RH_ROLE:
        #obra = get_object_or_404(Obra, id=obra_id)
        
        # Obtener la fecha de inicio y fin de la semana actual
        today = timezone.now().date()
        week_start = today - timezone.timedelta(days=today.weekday())  # Lunes
        week_end = week_start + timezone.timedelta(days=6)  # Domingo

        # Ajustar la consulta para calcular asistencia semanal por proyecto
        attendance_data = Obra.objects.filter(id=obra_id).annotate(
            full_time=Count(
                Case(
                    When(
                        empleado__asistencia__entrada__isnull=False, 
                        empleado__asistencia__salida__isnull=False, 
                        empleado__asistencia__fecha__range=(week_start, week_end),
                        then=1
                    )
                )
            ),
            part_time=Count(
                Case(
                    When(
                        empleado__asistencia__entrada__isnull=False, 
                        empleado__asistencia__salida__isnull=True, 
                        empleado__asistencia__fecha__range=(week_start, week_end),
                        then=1
                    )
                )
            ),
            not_attended=Count(
                Case(
                    When(
                        empleado__asistencia__entrada__isnull=True, 
                        empleado__asistencia__fecha__range=(week_start, week_end),
                        then=1
                    )
                )
            )
            
        ).values('full_time', 'part_time', 'not_attended')

        active_employees_count = Empleado.objects.filter(obra=obra_id).distinct().count()

    attendance_data = list(attendance_data)
    key = []
    values = []
    for data in attendance_data:
        key.append(list(data.keys()))
        values.append(list(data.values()))
    

    key = [item for sublist in key for item in sublist]
    values = [item for sublist in values for item in sublist]
    a = sum(values)
    faltas = active_employees_count - a
    values[-1] = faltas 

    key[0] = 'Jornadas completas'
    key[1] = 'Jornada Incompleta'
    key[2] = 'Sin Asistencia'


    return JsonResponse({'labels': key ,'data':values}, safe=False)


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