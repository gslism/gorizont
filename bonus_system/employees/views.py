from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Sum, Count
from django.http import JsonResponse
from django.utils import timezone
from datetime import date, datetime, timedelta
from .models import Employee, Department, Position, News, BonusTransfer, Holiday, StaffMember, Notification
from .forms import EmployeeRegistrationForm, EmployeeLoginForm, BonusTransferForm, ProfileEditForm, NewsForm, StaffMemberForm
from django.utils import timezone


def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        form = EmployeeLoginForm(request.POST)
        if form.is_valid():
            login_value = form.cleaned_data['login']
            password = form.cleaned_data['password']
            
            # Попытка входа по email или телефону
            try:
                if '@' in login_value:
                    user = Employee.objects.get(email=login_value)
                else:
                    user = Employee.objects.get(phone=login_value)
                
                user = authenticate(request, username=user.username, password=password)
                if user is not None:
                    login(request, user)
                    user.reset_monthly_balance()  # Проверка и сброс баланса
                    return redirect('home')
                else:
                    messages.error(request, 'Неверный пароль')
            except Employee.DoesNotExist:
                messages.error(request, 'Пользователь с таким email или телефоном не найден')
    else:
        form = EmployeeLoginForm()
    
    return render(request, 'employees/login.html', {'form': form})


def register_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        form = EmployeeRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Регистрация успешна!')
            return redirect('home')
    else:
        form = EmployeeRegistrationForm()
    
    return render(request, 'employees/register.html', {'form': form})


@login_required
def home_view(request):
    # Проверка и сброс баланса
    request.user.reset_monthly_balance()
    
    # Новости (последние 5)
    news = News.objects.all()[:5]
    
    # Рейтинг за текущий месяц
    current_month = timezone.now().month
    current_year = timezone.now().year
    rating = Employee.objects.annotate(
        total_received=Sum(
            'received_transfers__amount',
            filter=Q(received_transfers__created_at__month=current_month,
                    received_transfers__created_at__year=current_year,
                    received_transfers__is_deleted=False)
        )
    ).filter(total_received__isnull=False).order_by('-total_received')[:10]
    
    # Новые отзывы (последние 5) - исключаем удаленные
    recent_reviews = BonusTransfer.objects.filter(is_deleted=False).select_related('from_employee', 'to_employee').order_by('-created_at')[:5]
    
    # Непрочитанные переводы (уведомления)
    unread_transfers = BonusTransfer.objects.filter(
        to_employee=request.user,
        notification_sent=False
    ).select_related('from_employee').order_by('-created_at')
    
    # Помечаем переводы как прочитанные
    if unread_transfers.exists():
        BonusTransfer.objects.filter(
            to_employee=request.user,
            notification_sent=False
        ).update(notification_sent=True)
    
    # Проверка дней рождения и праздников
    today = date.today()
    birthdays = Employee.objects.filter(
        birth_date__month=today.month,
        birth_date__day=today.day
    ).exclude(id=request.user.id)
    
    holidays = Holiday.objects.filter(
        date=today,
        is_annual=True
    )
    
    context = {
        'news': news,
        'rating': rating,
        'recent_reviews': recent_reviews,
        'unread_transfers': unread_transfers,
        'birthdays': birthdays,
        'holidays': holidays,
    }
    
    return render(request, 'employees/home.html', context)


@login_required
def employees_list_view(request):
    # Используем модель StaffMember вместо Employee - это сотрудники компании, не зарегистрированные в системе
    employees = StaffMember.objects.select_related('department', 'position').filter(is_active=True)
    
    # Фильтрация
    department_filter = request.GET.get('department')
    position_filter = request.GET.get('position')
    search_query = request.GET.get('search')
    
    if department_filter:
        employees = employees.filter(department_id=department_filter)
    if position_filter:
        employees = employees.filter(position_id=position_filter)
    if search_query:
        employees = employees.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(middle_name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(phone__icontains=search_query)
        )
    
    departments = Department.objects.all()
    # Фильтруем должности только с указанным отделом, если выбран отдел
    if department_filter:
        positions = Position.objects.filter(department_id=department_filter, department__isnull=False)
    else:
        positions = Position.objects.filter(department__isnull=False)
    
    context = {
        'employees': employees,
        'departments': departments,
        'positions': positions,
        'selected_department': department_filter,
        'selected_position': position_filter,
        'search_query': search_query,
    }
    
    return render(request, 'employees/employees_list.html', context)


@login_required
def reviews_list_view(request):
    # Исключаем удаленные переводы
    reviews = BonusTransfer.objects.filter(is_deleted=False).select_related('from_employee', 'to_employee').all()
    
    # Фильтрация
    employee_filter = request.GET.get('employee')
    month_filter = request.GET.get('month')
    my_reviews = request.GET.get('my_reviews')
    
    if my_reviews == 'sent':
        reviews = reviews.filter(from_employee=request.user)
    elif my_reviews == 'received':
        reviews = reviews.filter(to_employee=request.user)
    
    if employee_filter:
        reviews = reviews.filter(
            Q(from_employee_id=employee_filter) | Q(to_employee_id=employee_filter)
        )
    
    if month_filter:
        year, month = month_filter.split('-')
        month = int(month)
        year = int(year)
        reviews = reviews.filter(created_at__month=month, created_at__year=year)
    
    employees = Employee.objects.all()
    
    # Генерация списка месяцев для фильтра
    months = []
    for i in range(12):
        date_obj = timezone.now() - timedelta(days=30*i)
        months.append(date_obj.strftime('%Y-%m'))
    
    context = {
        'reviews': reviews,
        'employees': employees,
        'months': months,
        'selected_employee': employee_filter,
        'selected_month': month_filter,
        'my_reviews': my_reviews,
    }
    
    return render(request, 'employees/reviews_list.html', context)


@login_required
def rating_view(request):
    month_filter = request.GET.get('month')
    
    if month_filter:
        year, month = month_filter.split('-')
        month = int(month)
        year = int(year)
    else:
        month = timezone.now().month
        year = timezone.now().year
    
    rating = Employee.objects.annotate(
        total_received=Sum(
            'received_transfers__amount',
            filter=Q(received_transfers__created_at__month=month,
                    received_transfers__created_at__year=year,
                    received_transfers__is_deleted=False)
        )
    ).filter(total_received__isnull=False).order_by('-total_received')
    
    # Данные для диаграммы
    chart_data = {
        'labels': [emp.get_full_name() for emp in rating[:10]],
        'data': [float(emp.total_received or 0) for emp in rating[:10]],
    }
    
    # Генерация списка месяцев для фильтра
    month_names_ru = {
        1: 'Январь', 2: 'Февраль', 3: 'Март', 4: 'Апрель',
        5: 'Май', 6: 'Июнь', 7: 'Июль', 8: 'Август',
        9: 'Сентябрь', 10: 'Октябрь', 11: 'Ноябрь', 12: 'Декабрь'
    }
    months = []
    for i in range(12):
        date_obj = timezone.now() - timedelta(days=30*i)
        month_num = date_obj.month
        months.append({
            'value': date_obj.strftime('%Y-%m'),
            'label': f'{month_names_ru[month_num]} {date_obj.year}'
        })
    
    context = {
        'rating': rating,
        'chart_data': chart_data,
        'months': months,
        'selected_month': month_filter or f'{year}-{month:02d}',
    }
    
    return render(request, 'employees/rating.html', context)


@login_required
def bonus_transfer_view(request):
    request.user.reset_monthly_balance()
    
    # Проверка, что пользователь не директор
    if request.user.is_director():
        messages.error(request, 'Директора не могут переводить бонусы')
        return redirect('home')

    # Проверка, что пользователь не администратор
    if request.user.is_administrator():
        messages.error(request, 'Администратор не может переводить бонусы')
        return redirect('home')
    
    if request.method == 'POST':
        form = BonusTransferForm(request.POST, request.FILES, from_employee=request.user)
        if form.is_valid():
            transfer = form.save(commit=False)
            transfer.from_employee = request.user
            
            # Проверка баланса
            if transfer.amount > request.user.monthly_bonus_balance:
                messages.error(request, 'Недостаточно средств')
                return redirect('bonus_transfer')
            
            # Проверка, что получатель не директор
            if transfer.to_employee.is_director():
                messages.error(request, 'Нельзя переводить бонусы директорам')
                return redirect('bonus_transfer')

            # Проверка, что получатель не администратор
            if transfer.to_employee.is_administrator():
                messages.error(request, 'Нельзя переводить бонусы администратору')
                return redirect('bonus_transfer')
            
            # Перевод
            request.user.monthly_bonus_balance -= transfer.amount
            request.user.save()
            
            transfer.to_employee.received_bonus_balance += transfer.amount
            transfer.to_employee.save()
            
            transfer.save()
            
            # Создаем уведомление для получателя
            Notification.objects.create(
                user=transfer.to_employee,
                type='transfer_received',
                title='Получен перевод бонусов',
                message=f'Вы получили {transfer.amount} руб. от {request.user.get_full_name()}. Причина: {transfer.get_reason_display()}',
                related_transfer=transfer
            )
            
            messages.success(request, f'Премия успешно переведена {transfer.to_employee.get_full_name()}!')
            return redirect('bonus_transfer')
    else:
        form = BonusTransferForm(from_employee=request.user)
    
    context = {
        'form': form,
        'balance': request.user.monthly_bonus_balance,
    }
    
    return render(request, 'employees/bonus_transfer.html', context)


@login_required
def profile_view(request):
    if request.method == 'POST':
        form = ProfileEditForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Профиль успешно обновлен!')
            return redirect('profile')
    else:
        form = ProfileEditForm(instance=request.user)
    
    # Отзывы пользователя
    sent_reviews = BonusTransfer.objects.filter(from_employee=request.user).order_by('-created_at')
    received_reviews = BonusTransfer.objects.filter(to_employee=request.user).order_by('-created_at')
    
    context = {
        'form': form,
        'sent_reviews': sent_reviews,
        'received_reviews': received_reviews,
    }
    
    return render(request, 'employees/profile.html', context)


@login_required
def logout_view(request):
    from django.contrib.auth import logout
    logout(request)
    return redirect('login')


def get_positions_by_department(request):
    """AJAX-эндпоинт для получения должностей по отделу"""
    department_id = request.GET.get('department_id')
    if department_id:
        # Фильтруем только должности с указанным отделом (исключаем null)
        positions = Position.objects.filter(department_id=department_id, department__isnull=False).values('id', 'name')
        return JsonResponse(list(positions), safe=False)
    return JsonResponse([], safe=False)


@login_required
def notifications_view(request):
    """Страница уведомлений"""
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
    unread_count = notifications.filter(is_read=False).count()
    
    # Помечаем все как прочитанные при явном запросе
    if request.method == 'GET' and 'mark_read' in request.GET:
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return redirect('notifications')
    
    context = {
        'notifications': notifications,
        'unread_count': unread_count,
    }
    
    return render(request, 'employees/notifications.html', context)


@login_required
def admin_panel_view(request):
    """Панель администратора"""
    if not request.user.is_admin:
        messages.error(request, 'У вас нет прав доступа к панели администратора')
        return redirect('home')
    
    context = {
        'staff_count': StaffMember.objects.filter(is_active=True).count(),
        'transfers_count': BonusTransfer.objects.filter(is_deleted=False).count(),
        'news_count': News.objects.count(),
    }
    
    return render(request, 'employees/admin_panel.html', context)


@login_required
def admin_staff_manage_view(request):
    """Управление сотрудниками для администратора"""
    if not request.user.is_admin:
        messages.error(request, 'У вас нет прав доступа')
        return redirect('home')
    
    if request.method == 'POST':
        form = StaffMemberForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Сотрудник успешно добавлен!')
            return redirect('admin_staff_manage')
    else:
        form = StaffMemberForm()
    
    staff_members = StaffMember.objects.all().order_by('-id')
    
    context = {
        'form': form,
        'staff_members': staff_members,
    }
    
    return render(request, 'employees/admin_staff_manage.html', context)


@login_required
def admin_staff_delete_view(request, staff_id):
    """Удаление сотрудника администратором"""
    if not request.user.is_admin:
        messages.error(request, 'У вас нет прав доступа')
        return redirect('home')
    
    staff_member = get_object_or_404(StaffMember, id=staff_id)
    staff_member.delete()
    messages.success(request, 'Сотрудник удален')
    return redirect('admin_staff_manage')


@login_required
def admin_transfers_view(request):
    """Управление переводами для администратора"""
    if not request.user.is_admin:
        messages.error(request, 'У вас нет прав доступа')
        return redirect('home')
    
    transfers = BonusTransfer.objects.filter(is_deleted=False).select_related('from_employee', 'to_employee').order_by('-created_at')
    
    context = {
        'transfers': transfers,
    }
    
    return render(request, 'employees/admin_transfers.html', context)


@login_required
def admin_transfer_delete_view(request, transfer_id):
    """Удаление перевода администратором"""
    if not request.user.is_admin:
        messages.error(request, 'У вас нет прав доступа')
        return redirect('home')
    
    transfer = get_object_or_404(BonusTransfer, id=transfer_id)
    
    if request.method == 'POST':
        # Возвращаем средства
        transfer.from_employee.monthly_bonus_balance += transfer.amount
        transfer.from_employee.save()
        
        transfer.to_employee.received_bonus_balance -= transfer.amount
        if transfer.to_employee.received_bonus_balance < 0:
            transfer.to_employee.received_bonus_balance = 0
        transfer.to_employee.save()
        
        # Помечаем как удаленный
        transfer.is_deleted = True
        transfer.deleted_by = request.user
        transfer.deleted_at = timezone.now()
        transfer.save()
        
        # Создаем уведомление для получателя
        Notification.objects.create(
            user=transfer.to_employee,
            type='transfer_cancelled',
            title='Перевод отменен',
            message=f'Перевод на сумму {transfer.amount} руб. от {transfer.from_employee.get_full_name()} был отменен администратором.',
            related_transfer=transfer
        )
        
        # Создаем уведомление для отправителя
        Notification.objects.create(
            user=transfer.from_employee,
            type='transfer_cancelled',
            title='Перевод отменен',
            message=f'Ваш перевод на сумму {transfer.amount} руб. для {transfer.to_employee.get_full_name()} был отменен администратором. Средства возвращены на ваш баланс.',
            related_transfer=transfer
        )
        
        messages.success(request, 'Перевод удален, средства возвращены')
        return redirect('admin_transfers')
    
    context = {
        'transfer': transfer,
    }
    
    return render(request, 'employees/admin_transfer_delete.html', context)


@login_required
def admin_news_create_view(request):
    """Создание новостей администратором"""
    if not request.user.is_admin:
        messages.error(request, 'У вас нет прав доступа')
        return redirect('home')
    
    if request.method == 'POST':
        form = NewsForm(request.POST)
        if form.is_valid():
            news = form.save(commit=False)
            news.author = request.user
            news.save()
            
            # Создаем уведомления для всех пользователей
            employees = Employee.objects.exclude(id=request.user.id)
            for employee in employees:
                Notification.objects.create(
                    user=employee,
                    type='news',
                    title='Новая новость',
                    message=f'{news.title}',
                )
            
            messages.success(request, 'Новость создана!')
            return redirect('home')
    else:
        form = NewsForm()
    
    context = {
        'form': form,
    }
    
    return render(request, 'employees/admin_news_create.html', context)