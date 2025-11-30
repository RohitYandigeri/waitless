from datetime import datetime

def get_live_crowd_level(place: dict) -> int:
    """
    Returns a crowd level 1–5 based on:
    - place category
    - current hour of day

    This is a DEMO "auto crowd" engine.
    In a real system, this is where you'd plug:
    - Google Popular Times
    - Wi-Fi/Bluetooth density
    - CCTV-based counting
    """
    now = datetime.now()
    hour = now.hour
    category = place["category"].lower()

    # Default crowd level
    level = 3

    if "hospital" in category:
        # Hospitals: busy mornings & evenings
        if 8 <= hour < 11 or 17 <= hour < 20:
            level = 4
        elif 11 <= hour < 17:
            level = 3
        else:
            level = 2

    elif "bank" in category:
        # Banks: peak mid-day
        if 11 <= hour < 14:
            level = 4
        elif 10 <= hour < 11 or 14 <= hour < 16:
            level = 3
        else:
            level = 2

    elif "government" in category:
        # Govt offices: heavy mid-morning to afternoon
        if 10 <= hour < 13 or 14 <= hour < 16:
            level = 4
        elif 9 <= hour < 10 or 16 <= hour < 17:
            level = 3
        else:
            level = 2
    else:
        # Generic pattern
        if 18 <= hour < 21:
            level = 4
        elif 11 <= hour < 14:
            level = 3
        else:
            level = 2

    # Ensure between 1–5
    level = max(1, min(5, level))
    return level
