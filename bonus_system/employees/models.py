from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.utils import timezone
from datetime import date


class Department(models.Model):
    name = models.CharField(max_length=100, verbose_name='Название отдела')
    
    class Meta:
        verbose_name = 'Отдел'
        verbose_name_plural = 'Отделы'
    
    def __str__(self):
        return self.name


class Position(models.Model):
    name = models.CharField(max_length=100, verbose_name='Название должности')
    department = models.ForeignKey(Department, on_delete=models.CASCADE, verbose_name='Отдел', related_name='positions', null=True, blank=True)
    
    class Meta:
        verbose_name = 'Должность'
        verbose_name_plural = 'Должности'
    
    def __str__(self):
        return self.name


class Employee(AbstractUser):
    GENDER_CHOICES = [
        ('M', 'Мужской'),
        ('F', 'Женский'),
    ]
    
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Номер телефона должен быть в формате: '+999999999'. До 15 цифр."
    )
    
    first_name = models.CharField(max_length=150, verbose_name='Имя')
    last_name = models.CharField(max_length=150, verbose_name='Фамилия')
    middle_name = models.CharField(max_length=150, blank=True, verbose_name='Отчество')
    phone = models.CharField(validators=[phone_regex], max_length=17, unique=True, verbose_name='Телефон')
    email = models.EmailField(unique=True, verbose_name='Email')
    birth_date = models.DateField(null=True, blank=True, verbose_name='Дата рождения')
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, verbose_name='Отдел')
    position = models.ForeignKey(Position, on_delete=models.SET_NULL, null=True, verbose_name='Должность')
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, null=True, blank=True, verbose_name='Пол')
    photo = models.ImageField(upload_to='photos/', blank=True, null=True, verbose_name='Фото')
    office_start_date = models.DateField(verbose_name='С какого момента в офисе', default=timezone.now)
    data_processing_consent = models.BooleanField(default=False, verbose_name='Согласие на обработку данных')
    
    # Балансы
    monthly_bonus_balance = models.DecimalField(max_digits=10, decimal_places=2, default=1000.00, verbose_name='Баланс бонусных рублей на месяц')
    received_bonus_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name='Баланс полученных рублей')
    
    # Сброс баланса каждый месяц
    last_balance_reset = models.DateField(default=date.today, verbose_name='Дата последнего сброса баланса')
    
    # Роль администратора (управление через отдельный профиль)
    is_admin = models.BooleanField(default=False, verbose_name='Администратор')
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'phone']
    
    def is_director(self):
        """Проверка, является ли сотрудник директором (по названию должности)"""
        if self.position:
            director_positions = ['Генеральный директор', 'Технический директор', 'Коммерческий директор']
            return self.position.name in director_positions
        return False
    
    def is_administrator(self):
        """
        Проверка, является ли сотрудник администратором.
        Считаем администратором либо пользователя с флагом is_admin,
        либо с должностью 'Администратор'.
        """
        if self.is_admin:
            return True
        if self.position and self.position.name == 'Администратор':
            return True
        return False
    
    class Meta:
        verbose_name = 'Сотрудник'
        verbose_name_plural = 'Сотрудники'
    
    def __str__(self):
        return f"{self.last_name} {self.first_name} {self.middle_name}".strip()
    
    def get_full_name(self):
        return f"{self.last_name} {self.first_name} {self.middle_name}".strip()
    
    def reset_monthly_balance(self):
        """Сброс баланса бонусных рублей каждый месяц"""
        today = date.today()
        if self.last_balance_reset.month != today.month or self.last_balance_reset.year != today.year:
            self.monthly_bonus_balance = 1000.00
            self.last_balance_reset = today
            self.save()


class News(models.Model):
    title = models.CharField(max_length=200, verbose_name='Заголовок')
    content = models.TextField(verbose_name='Содержание')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    author = models.ForeignKey(Employee, on_delete=models.CASCADE, verbose_name='Автор')
    
    class Meta:
        verbose_name = 'Новость'
        verbose_name_plural = 'Новости'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title


class BonusTransfer(models.Model):
    REASON_CHOICES = [
        ('excellent_work', 'Отличная работа'),
        ('help_colleague', 'Помощь коллеге'),
        ('project_success', 'Успешный проект'),
        ('innovation', 'Инновация'),
        ('teamwork', 'Командная работа'),
        ('client_satisfaction', 'Довольный клиент'),
        ('other', 'Другое'),
    ]
    
    from_employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='sent_transfers', verbose_name='От кого')
    to_employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='received_transfers', verbose_name='Кому')
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Сумма')
    reason = models.CharField(max_length=50, choices=REASON_CHOICES, null=True, blank=True, verbose_name='Причина перевода')
    explanation = models.TextField(null=True, blank=True, verbose_name='Объяснение причины')
    document = models.FileField(upload_to='transfer_documents/', blank=True, null=True, verbose_name='Документ')
    review = models.TextField(verbose_name='Отзыв')  # Оставляем для обратной совместимости
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    notification_sent = models.BooleanField(default=False, verbose_name='Уведомление отправлено')
    is_deleted = models.BooleanField(default=False, verbose_name='Удален')
    deleted_by = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name='deleted_transfers', verbose_name='Удален администратором')
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name='Дата удаления')
    
    class Meta:
        verbose_name = 'Перевод бонусов'
        verbose_name_plural = 'Переводы бонусов'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.from_employee} -> {self.to_employee}: {self.amount} руб."


class Notification(models.Model):
    TYPE_CHOICES = [
        ('transfer_received', 'Получен перевод'),
        ('transfer_cancelled', 'Перевод отменен'),
        ('news', 'Новость'),
        ('system', 'Системное'),
    ]
    
    user = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='notifications', verbose_name='Пользователь')
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, verbose_name='Тип уведомления')
    title = models.CharField(max_length=200, verbose_name='Заголовок')
    message = models.TextField(verbose_name='Сообщение')
    is_read = models.BooleanField(default=False, verbose_name='Прочитано')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    related_transfer = models.ForeignKey(BonusTransfer, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Связанный перевод')
    
    class Meta:
        verbose_name = 'Уведомление'
        verbose_name_plural = 'Уведомления'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user} - {self.title}"


class Holiday(models.Model):
    name = models.CharField(max_length=200, verbose_name='Название праздника')
    date = models.DateField(verbose_name='Дата')
    is_annual = models.BooleanField(default=True, verbose_name='Ежегодный')
    
    class Meta:
        verbose_name = 'Праздник'
        verbose_name_plural = 'Праздники'
    
    def __str__(self):
        return self.name


class StaffMember(models.Model):
    """Модель для сотрудников компании (не зарегистрированных в системе)"""
    GENDER_CHOICES = [
        ('M', 'Мужской'),
        ('F', 'Женский'),
    ]
    
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Номер телефона должен быть в формате: '+999999999'. До 15 цифр."
    )
    
    first_name = models.CharField(max_length=150, verbose_name='Имя')
    last_name = models.CharField(max_length=150, verbose_name='Фамилия')
    middle_name = models.CharField(max_length=150, blank=True, verbose_name='Отчество')
    phone = models.CharField(validators=[phone_regex], max_length=17, blank=True, null=True, verbose_name='Телефон')
    email = models.EmailField(blank=True, null=True, verbose_name='Email')
    birth_date = models.DateField(null=True, blank=True, verbose_name='Дата рождения')
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Отдел')
    position = models.ForeignKey(Position, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Должность')
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, null=True, blank=True, verbose_name='Пол')
    photo = models.ImageField(upload_to='staff_photos/', blank=True, null=True, verbose_name='Фото')
    office_start_date = models.DateField(verbose_name='С какого момента в офисе', default=timezone.now)
    is_active = models.BooleanField(default=True, verbose_name='Работает')
    
    class Meta:
        verbose_name = 'Сотрудник компании'
        verbose_name_plural = 'Сотрудники компании'
        ordering = ['last_name', 'first_name']
    
    def __str__(self):
        return f"{self.last_name} {self.first_name} {self.middle_name}".strip()
    
    def get_full_name(self):
        return f"{self.last_name} {self.first_name} {self.middle_name}".strip()

