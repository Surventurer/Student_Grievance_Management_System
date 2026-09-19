import re
from datetime import datetime, time
from django.utils import timezone

DAY_MAP = {
    'mon': 0, 'monday': 0,
    'tue': 1, 'tues': 1, 'tuesday': 1,
    'wed': 2, 'wednesday': 2,
    'thu': 3, 'thur': 3, 'thurs': 3, 'thursday': 3,
    'fri': 4, 'friday': 4,
    'sat': 5, 'saturday': 5,
    'sun': 6, 'sunday': 6
}

DAY_NAMES = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']


def parse_time_component(t_str):
    """
    Parses a single time string like '9:00 AM', '5:00 PM', '09:00', '17:00', '9 AM', '5pm'.
    Returns datetime.time or None.
    """
    if not t_str:
        return None
    t_str = t_str.strip().upper()
    formats = [
        '%I:%M %p',
        '%I:%M%p',
        '%I %p',
        '%I%p',
        '%H:%M',
        '%H',
    ]
    for fmt in formats:
        try:
            return datetime.strptime(t_str, fmt).time()
        except ValueError:
            continue
    return None


def is_within_support_hours(support_hours_str=None, current_dt=None):
    """
    Checks if current_dt (or now in current timezone) is within the given support hours string.
    
    Returns:
        (is_active: bool, message: str)
    """
    if support_hours_str is None:
        try:
            from apps.admin_panel.models import SystemSettings
            settings_obj = SystemSettings.load()
            support_hours_str = getattr(settings_obj, 'support_hours', 'Mon-Fri, 9:00 AM - 5:00 PM')
        except Exception:
            support_hours_str = 'Mon-Fri, 9:00 AM - 5:00 PM'

    support_hours_str = (support_hours_str or '').strip()

    # Always open keywords
    if not support_hours_str or any(kw in support_hours_str.lower() for kw in ['24/7', 'always', '24x7', 'anytime', 'all day', 'open 24', 'none', 'unlimited']):
        return True, "Support is available 24/7."

    if current_dt is None:
        if timezone.is_aware(timezone.now()):
            current_dt = timezone.localtime()
        else:
            current_dt = datetime.now()

    # Split day and time components
    parts = [p.strip() for p in support_hours_str.split(',') if p.strip()]
    day_part = None
    time_part = None

    if len(parts) >= 2:
        day_part = parts[0]
        time_part = parts[1]
    elif len(parts) == 1:
        part_str = parts[0]
        # Check if day names are present
        if any(d in part_str.lower() for d in ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun', 'daily', 'everyday']):
            m = re.search(r'([A-Za-z]+(?:\s*-\s*[A-Za-z]+)?)\s*,?\s*(.*)', part_str)
            if m and m.group(2).strip():
                day_part = m.group(1).strip()
                time_part = m.group(2).strip()
            else:
                day_part = part_str
        else:
            time_part = part_str

    current_weekday = current_dt.weekday()  # 0=Monday, 6=Sunday

    # 1. Day of Week Verification
    if day_part:
        dp_lower = day_part.lower()
        if 'everyday' in dp_lower or 'daily' in dp_lower or 'mon-sun' in dp_lower:
            allowed_days = set(range(0, 7))
        elif '-' in dp_lower:
            d_start_raw, d_end_raw = [d.strip() for d in dp_lower.split('-', 1)]
            s_num = DAY_MAP.get(d_start_raw)
            e_num = DAY_MAP.get(d_end_raw)
            if s_num is not None and e_num is not None:
                if s_num <= e_num:
                    allowed_days = set(range(s_num, e_num + 1))
                else:
                    allowed_days = set(range(s_num, 7)) | set(range(0, e_num + 1))
            else:
                allowed_days = set(range(0, 5))
        else:
            # Single day or comma/space list
            matched = DAY_MAP.get(dp_lower)
            if matched is not None:
                allowed_days = {matched}
            else:
                allowed_days = set(range(0, 5))

        if current_weekday not in allowed_days:
            today_name = DAY_NAMES[current_weekday]
            return False, f"Support is inactive on {today_name}. Operational days: {day_part}."
    else:
        # Default to Mon-Fri
        if current_weekday not in range(0, 5):
            today_name = DAY_NAMES[current_weekday]
            return False, f"Support is inactive on {today_name}. Operational days are Mon-Fri."

    # 2. Time Range Verification
    if time_part:
        time_match = re.search(
            r'([0-9]{1,2}(?::[0-9]{2})?\s*(?:[APap][Mm])?)\s*-\s*([0-9]{1,2}(?::[0-9]{2})?\s*(?:[APap][Mm])?)',
            time_part
        )
        if time_match:
            t_start = parse_time_component(time_match.group(1))
            t_end = parse_time_component(time_match.group(2))
            if t_start and t_end:
                current_time = current_dt.time()
                if t_start <= t_end:
                    if not (t_start <= current_time <= t_end):
                        return False, f"Support hours are currently closed. Active hours: {support_hours_str}."
                else:
                    # Overnight schedule e.g. 10 PM - 6 AM
                    if not (current_time >= t_start or current_time <= t_end):
                        return False, f"Support hours are currently closed. Active hours: {support_hours_str}."

    return True, "Within support hours."

