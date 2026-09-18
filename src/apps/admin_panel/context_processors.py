from apps.admin_panel.models import SystemSettings

def system_settings(request):
    try:
        return {'system_settings': SystemSettings.load()}
    except Exception:
        return {}
