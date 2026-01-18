try:
    from zoneinfo import ZoneInfo
    print("Standard library zoneinfo available")
except ImportError:
    try:
        from backports.zoneinfo import ZoneInfo
        print("Backports zoneinfo available")
    except ImportError:
        print("No zoneinfo available!")
        exit(1)

from datetime import datetime
tz = ZoneInfo("America/Toronto")
print(f"Current time in Toronto: {datetime.now(tz)}")
print("ZoneInfo load successful")
