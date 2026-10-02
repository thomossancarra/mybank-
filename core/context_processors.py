from .models import SystemSettings


def system_settings(request):
    settings = SystemSettings.objects.first()

    return {
        "system_settings": settings,
    }