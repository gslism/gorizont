from .models import Notification


def notifications_count(request):
    """Контекстный процессор для подсчета непрочитанных уведомлений и списка уведомлений"""
    if request.user.is_authenticated:
        unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
        notifications = Notification.objects.filter(user=request.user).order_by('-created_at')[:10]
        return {
            'unread_notifications_count': unread_count,
            'notifications_list': notifications
        }
    return {
        'unread_notifications_count': 0,
        'notifications_list': []
    }
