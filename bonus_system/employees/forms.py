from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import Employee, Department, Position, BonusTransfer, News, StaffMember


class EmployeeRegistrationForm(UserCreationForm):
    first_name = forms.CharField(max_length=150, label='Имя', widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(max_length=150, label='Фамилия', widget=forms.TextInput(attrs={'class': 'form-control'}))
    middle_name = forms.CharField(max_length=150, required=False, label='Отчество', widget=forms.TextInput(attrs={'class': 'form-control'}))
    phone = forms.CharField(max_length=17, label='Телефон', widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+79999999999'}))
    email = forms.EmailField(label='Email', widget=forms.EmailInput(attrs={'class': 'form-control'}))
    birth_date = forms.DateField(label='Дата рождения', widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}))
    department = forms.ModelChoiceField(queryset=Department.objects.all(), label='Отдел', widget=forms.Select(attrs={'class': 'form-control'}))
    position = forms.ModelChoiceField(queryset=Position.objects.all(), label='Должность', widget=forms.Select(attrs={'class': 'form-control'}))
    gender = forms.ChoiceField(choices=Employee.GENDER_CHOICES, label='Пол', widget=forms.RadioSelect(attrs={'class': 'form-check-input'}))
    data_processing_consent = forms.BooleanField(label='Согласие на обработку данных', widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    password1 = forms.CharField(label='Пароль', widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    password2 = forms.CharField(label='Подтверждение пароля', widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    
    class Meta:
        model = Employee
        fields = ('username','first_name', 'last_name', 'middle_name', 'phone', 'email', 'birth_date',
                 'department', 'position', 'gender', 'data_processing_consent', 'password1', 'password2')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget = forms.HiddenInput()
        self.fields['username'].required = False
        
        # Инициализация queryset для должностей - пустой, будет заполняться через AJAX
        self.fields['position'].queryset = Position.objects.none()
        
        # Если форма уже заполнена (например, при ошибке валидации), фильтруем должности по отделу
        if 'department' in self.data:
            try:
                department_id = int(self.data.get('department'))
                # Фильтруем только должности с указанным отделом (исключаем null)
                self.fields['position'].queryset = Position.objects.filter(department_id=department_id, department__isnull=False)
            except (ValueError, TypeError):
                pass
        elif self.instance and self.instance.pk and self.instance.department:
            # Если редактируем существующего пользователя
            self.fields['position'].queryset = Position.objects.filter(department=self.instance.department, department__isnull=False)
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            # Проверяем, не используется ли email активным пользователем
            active_user = Employee.objects.filter(email=email, is_active=True).exclude(pk=self.instance.pk if self.instance.pk else None)
            if active_user.exists():
                raise forms.ValidationError('Пользователь с таким email уже зарегистрирован.')
        return email
    
    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if phone:
            # Проверяем, не используется ли phone активным пользователем
            active_user = Employee.objects.filter(phone=phone, is_active=True).exclude(pk=self.instance.pk if self.instance.pk else None)
            if active_user.exists():
                raise forms.ValidationError('Пользователь с таким телефоном уже зарегистрирован.')
        return phone
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = user.email
        
        # Проверяем, есть ли неактивный Employee с таким же ФИО (созданный при переводе бонусов)
        existing_inactive_employee = None
        try:
            existing_inactive_employee = Employee.objects.get(
                last_name=user.last_name,
                first_name=user.first_name,
                middle_name=user.middle_name or '',
                is_active=False
            )
        except (Employee.DoesNotExist, Employee.MultipleObjectsReturned):
            # Если не найден или несколько, пробуем найти по фамилии и имени
            inactive_employees = Employee.objects.filter(
                last_name=user.last_name,
                first_name=user.first_name,
                is_active=False
            )
            if inactive_employees.exists():
                existing_inactive_employee = inactive_employees.first()
        
        if existing_inactive_employee:
            # Найден неактивный Employee - активируем его и обновляем данными из формы
            # Сохраняем бонусы, которые были начислены до регистрации
            saved_received_balance = existing_inactive_employee.received_bonus_balance
            saved_monthly_balance = existing_inactive_employee.monthly_bonus_balance
            
            # Проверяем, не конфликтует ли новый email/phone с другими активными пользователями
            if user.email != existing_inactive_employee.email:
                if Employee.objects.filter(email=user.email, is_active=True).exists():
                    raise forms.ValidationError({'email': 'Пользователь с таким email уже зарегистрирован.'})
            
            if user.phone != existing_inactive_employee.phone:
                if Employee.objects.filter(phone=user.phone, is_active=True).exists():
                    raise forms.ValidationError({'phone': 'Пользователь с таким телефоном уже зарегистрирован.'})
            
            # Обновляем данные существующего Employee
            existing_inactive_employee.username = user.email
            existing_inactive_employee.email = user.email
            existing_inactive_employee.phone = user.phone
            existing_inactive_employee.birth_date = user.birth_date
            existing_inactive_employee.department = user.department
            existing_inactive_employee.position = user.position
            existing_inactive_employee.gender = user.gender
            existing_inactive_employee.data_processing_consent = user.data_processing_consent
            existing_inactive_employee.is_active = True  # Активируем
            existing_inactive_employee.set_password(self.cleaned_data['password1'])
            
            # Сохраняем бонусы, которые были начислены до регистрации
            existing_inactive_employee.received_bonus_balance = saved_received_balance
            
            # Если monthly_bonus_balance равен 0, устанавливаем начальный баланс из настроек системы
            if saved_monthly_balance == 0:
                from .models import SystemSettings
                from datetime import date
                try:
                    settings = SystemSettings.get_settings()
                    existing_inactive_employee.monthly_bonus_balance = settings.monthly_bonus_amount
                except:
                    # Если настройки еще не созданы, используем значение по умолчанию
                    existing_inactive_employee.monthly_bonus_balance = 1000.00
                # Устанавливаем дату последнего сброса на сегодня, чтобы баланс правильно обновлялся
                existing_inactive_employee.last_balance_reset = date.today()
            else:
                existing_inactive_employee.monthly_bonus_balance = saved_monthly_balance
            
            # Обновляем фото, если загружено новое, иначе оставляем существующее
            if user.photo:
                existing_inactive_employee.photo = user.photo
            # Если фото не было загружено, но есть в StaffMember, используем его
            elif not existing_inactive_employee.photo:
                from .models import StaffMember
                staff_member = StaffMember.objects.filter(
                    last_name=existing_inactive_employee.last_name,
                    first_name=existing_inactive_employee.first_name,
                    middle_name=existing_inactive_employee.middle_name or ''
                ).first()
                if staff_member and staff_member.photo:
                    existing_inactive_employee.photo = staff_member.photo
            
            if commit:
                existing_inactive_employee.save()
            
            # Обновляем связь в StaffMember, если есть
            from .models import StaffMember
            staff_member = StaffMember.objects.filter(
                last_name=existing_inactive_employee.last_name,
                first_name=existing_inactive_employee.first_name,
                middle_name=existing_inactive_employee.middle_name or ''
            ).first()
            if staff_member:
                staff_member.employee_profile = existing_inactive_employee
                staff_member.save()
            
            return existing_inactive_employee
        else:
            # Создаем нового Employee
            if commit:
                user.save()
            return user


class EmployeeLoginForm(forms.Form):
    login = forms.CharField(label='Email или телефон', widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Email или телефон'}))
    password = forms.CharField(label='Пароль', widget=forms.PasswordInput(attrs={'class': 'form-control'}))


class BonusTransferForm(forms.ModelForm):
    REASON_CHOICES = [
        ('excellent_work', 'Отличная работа'),
        ('help_colleague', 'Помощь коллеге'),
        ('project_success', 'Успешный проект'),
        ('innovation', 'Инновация'),
        ('teamwork', 'Командная работа'),
        ('client_satisfaction', 'Довольный клиент'),
        ('other', 'Другое'),
    ]
    
    to_employee = forms.ModelChoiceField(
        queryset=Employee.objects.none(),
        label='Сотрудник',
        required=False,  # Необязательное, если выбран сотрудник из справочника
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'to_employee'})
    )
    amount = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        label='Сумма',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'})
    )
    reason = forms.ChoiceField(
        choices=REASON_CHOICES,
        label='Причина поощрения',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    explanation = forms.CharField(
        label='Объяснение причины начисления поощрения',
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Опишите подробно причину начисления поощрения...'})
    )
    document = forms.FileField(
        required=False,
        label='Документ (необязательно)',
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.pdf,.doc,.docx,.jpg,.jpeg,.png'})
    )
    review = forms.CharField(
        required=False,
        widget=forms.HiddenInput()
    )
    
    class Meta:
        model = BonusTransfer
        fields = ('to_employee', 'amount', 'reason', 'explanation', 'document')
    
    def __init__(self, *args, **kwargs):
        self.from_employee = kwargs.pop('from_employee', None)
        preselected_employee = kwargs.pop('preselected_employee', None)
        super().__init__(*args, **kwargs)
        if self.from_employee:
            # Показываем всех, кто участвует в системе премирования
            queryset = Employee.objects.filter(participates_in_bonus=True).exclude(id=self.from_employee.id).order_by('last_name', 'first_name')
            self.fields['to_employee'].queryset = queryset
            if preselected_employee:
                self.fields['to_employee'].initial = preselected_employee.id
    
    def clean(self):
        cleaned_data = super().clean()
        amount = cleaned_data.get('amount')
        to_employee = cleaned_data.get('to_employee')
        
        # Проверка баланса и участия в системе
        if self.from_employee:
            if not self.from_employee.participates_in_bonus:
                raise forms.ValidationError('Вы не участвуете в системе премирования!')
            
            if amount and amount > self.from_employee.monthly_bonus_balance:
                raise forms.ValidationError(f'Недостаточно средств. Доступно: {self.from_employee.monthly_bonus_balance} руб.')
            
            # Проверка на перевод самому себе (только если to_employee указан)
            if to_employee and self.from_employee.id == to_employee.id:
                raise forms.ValidationError('Нельзя переводить деньги самому себе!')
            
            # Проверка участия получателя (только если to_employee указан)
            if to_employee and not to_employee.participates_in_bonus:
                raise forms.ValidationError('Этот сотрудник не участвует в системе премирования!')
        
        return cleaned_data
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        # Сохраняем explanation в review для обратной совместимости
        instance.review = self.cleaned_data.get('explanation', '')
        if commit:
            instance.save()
        return instance


class StaffMemberForm(forms.ModelForm):
    """Форма для добавления сотрудников администратором"""
    gender = forms.ChoiceField(
        choices=StaffMember.GENDER_CHOICES,
        label='Пол',
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        required=True,
    )

    class Meta:
        model = StaffMember
        fields = ('first_name', 'last_name', 'middle_name', 'phone', 'email', 'birth_date', 
                 'department', 'position', 'gender', 'photo', 'office_start_date', 'is_active')
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'middle_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'birth_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'department': forms.Select(attrs={'class': 'form-control', 'id': 'id_department'}),
            'position': forms.Select(attrs={'class': 'form-control', 'id': 'id_position'}),
            'photo': forms.FileInput(attrs={'class': 'form-control'}),
            'office_start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Инициализация queryset для должностей - пустой, будет заполняться через AJAX
        self.fields['position'].queryset = Position.objects.none()
        
        # Если форма уже заполнена (например, при ошибке валидации), фильтруем должности по отделу
        if 'department' in self.data:
            try:
                department_id = int(self.data.get('department'))
                self.fields['position'].queryset = Position.objects.filter(department_id=department_id, department__isnull=False)
            except (ValueError, TypeError):
                pass
        elif self.instance and self.instance.pk and self.instance.department:
            # Если редактируем существующего сотрудника
            self.fields['position'].queryset = Position.objects.filter(department=self.instance.department, department__isnull=False)


class ProfileEditForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = ('photo', 'email', 'phone', 'first_name', 'last_name', 'middle_name')
        widgets = {
            'photo': forms.FileInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'middle_name': forms.TextInput(attrs={'class': 'form-control'}),
        }


class NewsForm(forms.ModelForm):
    class Meta:
        model = News
        fields = ('title', 'content')
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
        }

