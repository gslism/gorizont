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
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = user.email
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
        label='Причина перевода',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    explanation = forms.CharField(
        label='Объяснение причины',
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Опишите подробно причину начисления премии...'})
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
        super().__init__(*args, **kwargs)
        if self.from_employee:
            # Исключаем текущего пользователя, директоров и администраторов из списка
            queryset = Employee.objects.exclude(id=self.from_employee.id)
            # Исключаем директоров
            director_positions = ['Генеральный директор', 'Технический директор', 'Коммерческий директор']
            queryset = queryset.exclude(position__name__in=director_positions)
            # Исключаем администраторов
            queryset = queryset.exclude(is_admin=True).exclude(position__name='Администратор')
            self.fields['to_employee'].queryset = queryset
    
    def clean(self):
        cleaned_data = super().clean()
        amount = cleaned_data.get('amount')
        to_employee = cleaned_data.get('to_employee')
        
        if self.from_employee and to_employee:
            if self.from_employee.id == to_employee.id:
                raise forms.ValidationError('Нельзя переводить деньги самому себе!')
            
            # Проверка, что получатель не директор
            if to_employee.is_director():
                raise forms.ValidationError('Нельзя переводить бонусы директорам!')
            
            # Проверка, что получатель не администратор
            if to_employee.is_administrator():
                raise forms.ValidationError('Нельзя переводить бонусы администратору!')
            
            # Проверка, что отправитель не директор
            if self.from_employee.is_director():
                raise forms.ValidationError('Директора не могут переводить бонусы!')
            
            # Проверка, что отправитель не администратор
            if self.from_employee.is_administrator():
                raise forms.ValidationError('Администратор не может переводить бонусы!')
            
            if amount and amount > self.from_employee.monthly_bonus_balance:
                raise forms.ValidationError(f'Недостаточно средств. Доступно: {self.from_employee.monthly_bonus_balance} руб.')
        
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
            # gender задаём явно выше, чтобы не было варианта "---------"
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

