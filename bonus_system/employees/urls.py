from django.urls import path
from . import views

urlpatterns = [
    path('', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('home/', views.home_view, name='home'),
    path('employees/', views.employees_list_view, name='employees_list'),
    path('reviews/', views.reviews_list_view, name='reviews_list'),
    path('rating/', views.rating_view, name='rating'),
    path('bonus-transfer/', views.bonus_transfer_view, name='bonus_transfer'),
    path('profile/', views.profile_view, name='profile'),
    path('logout/', views.logout_view, name='logout'),
    path('api/positions/', views.get_positions_by_department, name='get_positions_by_department'),
    path('notifications/', views.notifications_view, name='notifications'),
    path('app-admin/', views.admin_panel_view, name='admin_panel'),
    path('app-admin/staff/', views.admin_staff_manage_view, name='admin_staff_manage'),
    path('app-admin/staff/<int:staff_id>/edit/', views.admin_staff_edit_view, name='admin_staff_edit'),
    path('app-admin/staff/<int:staff_id>/delete/', views.admin_staff_delete_view, name='admin_staff_delete'),
    path('app-admin/users/<int:employee_id>/delete/', views.admin_user_delete_view, name='admin_user_delete'),
    path('app-admin/transfers/', views.admin_transfers_view, name='admin_transfers'),
    path('app-admin/transfers/<int:transfer_id>/delete/', views.admin_transfer_delete_view, name='admin_transfer_delete'),
    path('app-admin/news/create/', views.admin_news_create_view, name='admin_news_create'),
    path('app-admin/bonus-participation/', views.admin_bonus_participation_view, name='admin_bonus_participation'),
    path('app-admin/settings/', views.admin_settings_view, name='admin_settings'),
    path('app-admin/manage-admins/', views.admin_manage_admins_view, name='admin_manage_admins'),
    path('app-admin/export-transfers/', views.admin_export_transfers_view, name='admin_export_transfers'),
    path('update-staff-photo/', views.update_staff_photo_view, name='update_staff_photo'),
]

