from django import template
from ..models import SystemSettings

register = template.Library()

@register.simple_tag
def get_system_settings():
    return SystemSettings.get_settings()
