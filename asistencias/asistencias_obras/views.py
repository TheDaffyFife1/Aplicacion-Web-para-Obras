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

    # Assuming the end of a week is Sunday, to get the current week's start and end.
    today = timezone.now().date()
    start_of_week = today - timezone.timedelta(days=today.weekday() + 1)
    end_of_week = start_of_week + timezone.timedelta(days=6)

    # Aggregate data for the General Section
    weekly_payment = Empleado.objects.filter(
        obra__activa=True,
        obra__fecha_inicio__lte=end_of_week,
        obra__fecha_fin__gte=start_of_week
    ).aggregate(Sum('sueldo'))

    attendance_by_project = (
        Obra.objects.annotate(num_employees=Count('empleado'))
        .values('nombre', 'num_employees')
    )

    full_time_employees = Empleado.objects.filter(puesto__nombre='Jornada completa').count()

    # Data for Administrator Views
    active_projects = Obra.objects.filter(activa=True).count()
    active_employees = Empleado.objects.filter(obra__activa=True).count()
    project_progress_data = []  # You'll need to define how to calculate this

    # Data for Individual Section
    # This will require a more complex query or additional methods on your models
    # to calculate the percentage of project completion.
    project_completion_data = []  # Placeholder for project completion data

    # Data for the table of employees working on the projects
    employees_table_data = list(Empleado.objects.values(
        'nombre', 'apellido', 'puesto__nombre', 'obra__nombre'
    ))

    # Render the dashboard with the collected context data
    context = {
        'weekly_payment': weekly_payment,
        'attendance_by_project': attendance_by_project,
        'full_time_employees': full_time_employees,
        'active_projects': active_projects,
        'active_employees': active_employees,
        'project_progress_data': project_progress_data,
        'project_completion_data': project_completion_data,
        'employees_table_data': employees_table_data,
    }

    return render(request, 'admin/admin_dashboard.html', context)
@login_required
def dashboard_data(request):
    # Ensure only admins can access this data
    if request.user.userprofile.role != ADMIN_ROLE:
        return HttpResponseForbidden("No tienes permiso para ver esta página.")

    # Retrieve the 'timeframe' from GET parameters
    timeframe = request.GET.get('timeframe', 'week')

    # Initialize the base queryset
    queryset = Asistencia.objects.select_related('empleado').filter(empleado__obra__activa=True)

    # Filter the queryset based on the selected timeframe
    if timeframe == 'week':
        # Filter data for the current week
        queryset = queryset.annotate(week=TruncWeek('fecha')).values('week').annotate(total=Count('id'))
    elif timeframe == 'month':
        # Filter data for the current month
        queryset = queryset.annotate(month=TruncMonth('fecha')).values('month').annotate(total=Count('id'))
    else:
        # For custom range, you would need additional GET parameters to specify the start and end dates
        # For simplicity, this will just default to showing the current week's data
        queryset = queryset.annotate(week=TruncWeek('fecha')).values('week').annotate(total=Count('id'))

    # Convert the queryset to a list of dictionaries
    data = list(queryset)

    # Return a JsonResponse with the data
    return JsonResponse(data, safe=False)

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

