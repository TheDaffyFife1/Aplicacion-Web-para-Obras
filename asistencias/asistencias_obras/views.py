from itertools import groupby
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import Group
from .roles import ADMIN_ROLE, RH_ROLE, USER_ROLE
from .models import UserProfile,Obra,Empleado,Puesto,Asistencia
from django.contrib.auth.decorators import login_required
from .RegistrationForm import RegistrationForm
from django.contrib.auth import login
from django.db import IntegrityError
from django.http import HttpResponseForbidden, HttpResponseRedirect,JsonResponse
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
from django.db.models.functions import Cast
from django.db.models import Count, Case, When, DecimalField
from django.utils.timezone import now


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

#Funciones para administrador  
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
        form = AsignarObraForm(request.POST, instance=user_profile)
        if form.is_valid():
            # Asegúrate de que el usuario es RH o User antes de guardar
            if user_profile.role in [RH_ROLE, USER_ROLE]:
                form.save()
                return redirect('lista_user_profiles')
            else:
                # Manejar el caso en que el rol no es permitido para la asignación
                pass  # Puedes redirigir o mostrar un mensaje de error
    else:
        form = AsignarObraForm(instance=user_profile)

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
    # Obtener la fecha de inicio y fin de la semana actual
    today = timezone.now().date()
    week_start = today - timezone.timedelta(days=today.weekday())  # Lunes
    week_end = week_start + timezone.timedelta(days=6)  # Domingo

    # Ajustar la consulta para calcular asistencia semanal por proyecto
    attendance_data = Obra.objects.annotate(
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
    ).values('nombre', 'full_time', 'part_time', 'not_attended')

    return JsonResponse(list(attendance_data), safe=False)

@login_required
def project_progress(request):
    current_date = timezone.now().date()

    progress_data = Obra.objects.filter(activa=True).annotate(
        total_days=Cast((F('fecha_fin') - F('fecha_inicio')), output_field=FloatField()),
        elapsed_days=Cast((current_date - F('fecha_inicio')), output_field=FloatField()),
        progress=ExpressionWrapper(
            Coalesce(100 * F('elapsed_days') / F('total_days'), 0),
            output_field=FloatField()
        )
    ).values('nombre', 'progress')
    
    return JsonResponse(list(progress_data), safe=False)

@login_required
def summary_week_data(request):
    today = timezone.now().date()
    this_week_start = today - timezone.timedelta(days=today.weekday())
    this_week_end = this_week_start + timezone.timedelta(days=6)  # Semana de lunes a domingo

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

    # Calcular jornadas completas de la semana
    jornadas_completas_week = sum(1 for _ in valid_attendances_week)

    # Contar proyectos y empleados activos
    active_projects_count = Obra.objects.filter(activa=True).count()
    active_employees_count = Empleado.objects.filter(obra__activa=True).distinct().count()

    summary = {
        'active_projects': active_projects_count,
        'active_employees': active_employees_count,
        'total_payment_for_week': total_payment_for_week,
        'weekly_attendance_count': valid_attendances_week.count(),
        'jornadas_completas_week': jornadas_completas_week,
    }

    return JsonResponse(summary)

#Funciones para RH
@login_required
def rh_dashboard(request):
    user_profile = request.user.userprofile
    if user_profile.role == RH_ROLE:
        # Asumiendo que 'obra_id' es un campo en el modelo de UserProfile para el ID de la obra.
        obra_id = user_profile.obra_id
        if obra_id:
            obra = get_object_or_404(Obra, id=obra_id)
            # Puedes pasar 'obra' al contexto si la plantilla necesita mostrar información sobre la obra
            return render(request, 'rh/rh_dashboard.html', {'obra': obra})
        else:
            # Manejar el caso de que no haya un ID de obra asociado
            return HttpResponseForbidden("Este usuario de RH no tiene una obra asignada.")
    else:
        return HttpResponseForbidden("No tienes permiso para ver esta página.")

@login_required
def lista_empleados(request):
    user_profile = request.user.userprofile
    if user_profile.role == RH_ROLE:
        # Asumiendo que 'obra_id' es un campo en el modelo de UserProfile para el ID de la obra.
        obra_id = user_profile.obra_id
        if obra_id:
            obra = get_object_or_404(Obra, id=obra_id)
            # Puedes pasar 'obra' al contexto si la plantilla necesita mostrar información sobre la obra
            empleados = Empleado.objects.filter(obra_id=obra)
            return render(request, 'rh/lista_empleados.html', {'empleados': empleados, 'obra': obra})
        else:
            # Manejar el caso de que no haya un ID de obra asociado
            return HttpResponseForbidden("Este usuario de RH no tiene una obra asignada.")
    else:
        return HttpResponseForbidden("No tienes permiso para ver esta página.")

@login_required
def crear_empleado(request):
    user_profile = request.user.userprofile
    if user_profile.role == RH_ROLE:
        obra_id = user_profile.obra_id
        if obra_id:
            if request.method == 'POST':
                form = EmpleadoForm(request.POST, request.FILES)
                if form.is_valid():
                    empleado = form.save(commit=False)
                    # Establece la obra al empleado antes de guardar
                    empleado.obra_id = obra_id
                    empleado.save()
                    return redirect('lista_empleados')
            else:
                # Inicializa el formulario con la obra del usuario RH
                form = EmpleadoForm(initial={'obra': obra_id})
                # Oculta el campo 'obra' ya que no queremos que sea editable
                form.fields['obra'].widget = forms.HiddenInput()
            
            sueldos_base = {str(puesto.id): str(puesto.sueldo_base) for puesto in Puesto.objects.all()}
            sueldos_base_json = json.dumps(sueldos_base)
            
            return render(request, 'rh/registro_empleados.html', {
                'form': form,
                'sueldos_base': sueldos_base_json,  # Pass 'sueldos_base' as JSON to the template
            })
        else:
            return HttpResponseForbidden("Este usuario de RH no tiene una obra asignada.")
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
    if user_profile.role == RH_ROLE:
        obra_id = user_profile.obra_id
        if obra_id:
            obra = get_object_or_404(Obra, id=obra_id)
            # Filtrar empleados que pertenecen a la obra específica
            empleados = Empleado.objects.filter(obra=obra)

            hoy = timezone.localtime().date()
            inicio_semana = hoy - timedelta(days=hoy.weekday())  # Lunes
            fin_semana = inicio_semana + timedelta(days=5)  # Sábado
            
            # Asegurarse de que las asistencias pertenecen a los empleados de la obra específica
            asistencias_semana_actual = Asistencia.objects.filter(
                empleado__obra=obra,
                fecha__range=(inicio_semana, fin_semana)
            ).select_related('empleado').order_by('fecha')

            # Inicializar y llenar el contexto de empleados con datos de asistencia
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

            # Calcular el sueldo diario y total semanal para cada empleado
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
                'obra': obra,  # Opcional: pasar la obra al contexto si se necesita en la plantilla
                'inicio_semana': inicio_semana,
                'fin_semana': fin_semana
            }

            return render(request, 'rh/reporte_asistencia.html', context)

        else:
            return HttpResponseForbidden("Este usuario de RH no tiene una obra asignada.")
    else:
        return HttpResponseForbidden("No tienes permiso para ver esta página.")

#Funciones para Supervisor
@login_required
def user_asistencia(request):
    user_profile = request.user.userprofile
    if user_profile.role == USER_ROLE:
        obra_id = user_profile.obra_id
        if obra_id:
            obra = get_object_or_404(Obra, id=obra_id)
            # La lógica para mostrar la asistencia del usuario en la obra
            return render(request,'supervisor/user_asistencia.html', {'obra': obra})
        else:
            # Manejar el caso de que no haya un ID de obra asociado
            return HttpResponseForbidden("Este usuario no tiene una obra asignada.")
    else:
        return HttpResponseForbidden("No tienes permiso para ver esta página.")


@login_required
def progreso_obras(request):
    objetos = Obra.objects.all()
    hoy = now()
    labels = []
    data = []

    for objeto in objetos:
        tiempo_total = (objeto.fecha_fin - objeto.fecha_inicio).days
        tiempo_transcurrido = (hoy.date() - objeto.fecha_inicio).days 
        
        if tiempo_transcurrido > 0:
        
            porcentaje_transcurrido = (tiempo_transcurrido / tiempo_total) * 100 if tiempo_total else 0
            porcentaje_transcurrido

            labels.append(objeto.nombre)  # Agrega el nombre de la obra a la lista de etiquetas
            data.append(abs(int(porcentaje_transcurrido))) # Agrega el porcentaje de progreso a la lista de datos
        

    return JsonResponse({'labels': labels, 'data': data})

@login_required
def asistencia_obras(request):
    # Obtener parámetros de la solicitud
    time_range = request.GET.get('time_range', 'weekly')
    conjunto = int(request.GET.get('conjunto', 1))

    today = timezone.now().date()

    if time_range == 'weekly':
        start_date = today - timedelta(days=today.weekday(), weeks=(conjunto - 1) * 7)
        end_date = start_date + timedelta(days=6 + (conjunto - 1) * 7)
    elif time_range == 'monthly':
        # Ajusta el rango al mes actual y va hacia atrás según el conjunto indicado
        start_date = today.replace(day=1) - timedelta(days=31)
        end_date = today

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
            'porcentaje_asistencia': porcentaje
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
    objetos = Obra.objects.all()
    hoy = now()
    labels = []
    data = []
    resto = []

    for objeto in objetos:
        tiempo_total = (objeto.fecha_fin - objeto.fecha_inicio).days
        tiempo_transcurrido = (hoy.date() - objeto.fecha_inicio).days 

        if tiempo_transcurrido > 0:
            porcentaje_transcurrido = (tiempo_transcurrido / tiempo_total) * 100 if tiempo_total else 0
            restante = 100 - abs(porcentaje_transcurrido) 
            
            labels.append(objeto.nombre)  # Agrega el nombre de la obra a la lista de etiquetas
            data.append(abs(int(porcentaje_transcurrido))) # Agrega el porcentaje de progreso a la lista de datos
            resto.append(int(restante))


    return JsonResponse({'labels': labels, 'data': data, 'resto': resto})

@login_required

def tabla_pagos(request):
    # Parámetros para determinar el rango de tiempo y el conjunto de semanas/meses
    time_range = request.GET.get('time_range', 'weekly')
    conjunto = int(request.GET.get('conjunto', 1))  # El número de semanas/meses a considerar

    today = timezone.now().date()
    if time_range == 'weekly':
        # Ajustar el rango de fechas para abarcar el conjunto de semanas especificado
        start_date = today - timezone.timedelta(days=today.weekday(), weeks=(conjunto - 1) * 7)
        end_date = start_date + timezone.timedelta(days=6 + (conjunto - 1) * 7)
    else:  # Si es 'monthly', ajustar según el número de meses especificado
        # Establecer el inicio al primer día del mes actual y retroceder los meses necesarios
        start_date = today.replace(day=1) - timezone.timedelta(days=31)
        # Ajustar para que el final del periodo sea el último día del mes actual
        end_date = today.replace(day=1) + timezone.timedelta(days=31) - timezone.timedelta(days=today.day)

    # Filtrar asistencias válidas en el rango de fechas ajustado
    valid_attendances = Asistencia.objects.filter(
        fecha__range=(start_date, end_date),
        entrada__isnull=False,
        salida__isnull=False
    ).values('empleado', 'empleado__nombre', 'empleado__obra__nombre', 'empleado__puesto__sueldo_base')

    # Agregar conteo de asistencias válidas y calcular el pago
    payment_data = valid_attendances.annotate(
        days_worked=Count('fecha'),
        total_payment=ExpressionWrapper(
            Coalesce(F('days_worked') * (F('empleado__puesto__sueldo_base')/6), 0),
            output_field=DecimalField(max_digits=10, decimal_places=2)
        )
    ).order_by('empleado')

    # Preparar la respuesta
    response_data = list(payment_data.values('empleado__nombre', 'empleado__obra__nombre', 'days_worked', 'total_payment'))
    response_data.sort(key=lambda x: x['empleado__obra__nombre'])
    
    data = []
    for key, group in groupby(response_data, key=lambda x: x['empleado__obra__nombre']):
        pagos = sum(d['total_payment'] for d in group)
        data.append({'obra': key, 'total_pago': pagos})

    return JsonResponse({'data': response_data, 'pago_obra': data}, safe=False)



#RH
@login_required
def progreso(request):
    hoy = now()
    user = request.user.userprofile
    data = []

    if user.role == RH_ROLE:
        obra = user.obra_id
        obra = Obra.objects.get(id=obra)

        total = (obra.fecha_fin - obra.fecha_inicio).days
        transcurrido = (hoy.date() - obra.fecha_inicio).days
        if transcurrido > 0:
            porcenaje = (transcurrido / total) * 100 if total else 0
            resto = 100 - abs(porcenaje)
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

    


