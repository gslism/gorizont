from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import Employee, Department, Position, News, BonusTransfer, Holiday, StaffMember, Notification, Notification


@admin.register(Employee)
class EmployeeAdmin(BaseUserAdmin):
    list_display = ('email', 'get_full_name', 'department', 'position', 'phone', 'is_admin', 'monthly_bonus_balance', 'received_bonus_balance')
    list_filter = ('department', 'position', 'gender', 'is_admin')
    search_fields = ('email', 'phone', 'first_name', 'last_name')
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Дополнительная информация', {
            'fields': ('phone', 'middle_name', 'birth_date', 'department', 'position', 
                      'gender', 'photo', 'office_start_date', 'data_processing_consent',
                      'monthly_bonus_balance', 'received_bonus_balance', 'last_balance_reset', 'is_admin')
        }),
    )
    
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Дополнительная информация', {
            'fields': ('phone', 'middle_name', 'birth_date', 'department', 'position', 
                      'gender', 'photo', 'office_start_date', 'data_processing_consent', 'is_admin')
        }),
    )


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name',)


@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = ('name',)


@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'created_at')
    list_filter = ('created_at',)


@admin.register(BonusTransfer)
class BonusTransferAdmin(admin.ModelAdmin):
    list_display = ('from_employee', 'to_employee', 'amount', 'created_at')
    list_filter = ('created_at',)


@admin.register(Holiday)
class HolidayAdmin(admin.ModelAdmin):
    list_display = ('name', 'date', 'is_annual')
    list_filter = ('is_annual',)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'type', 'title', 'is_read', 'created_at')
    list_filter = ('type', 'is_read', 'created_at')
    search_fields = ('user__email', 'title', 'message')


@admin.register(StaffMember)
class StaffMemberAdmin(admin.ModelAdmin):
    list_display = ('get_full_name', 'department', 'position', 'phone', 'email', 'is_active', 'office_start_date')
    list_filter = ('department', 'position', 'gender', 'is_active')
    search_fields = ('first_name', 'last_name', 'middle_name', 'email', 'phone')
    fieldsets = (
        ('Основная информация', {
            'fields': ('first_name', 'last_name', 'middle_name', 'birth_date', 'gender', 'photo')
        }),
        ('Работа', {
            'fields': ('department', 'position', 'office_start_date', 'is_active')
        }),
        ('Контакты', {
            'fields': ('phone', 'email')
        }),
    )

