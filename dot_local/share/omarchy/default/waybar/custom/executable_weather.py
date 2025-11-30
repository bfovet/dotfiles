#!/usr/bin/env python3
import requests
import json
import sys
from datetime import datetime, timedelta
import calendar
import re

DAYS_FORECAST = 5

WEATHER_MAP = {
    0: ("☀️", "Clear sky"),
    1: ("🌤️", "Mainly clear"),
    2: ("⛅", "Partly cloudy"),
    3: ("☁️", "Overcast"),
    45: ("🌫️", "Fog"),
    48: ("🌫️", "Depositing rime fog"),
    51: ("🌦️", "Light drizzle"),
    53: ("🌦️", "Moderate drizzle"),
    55: ("🌦️", "Dense drizzle"),
    61: ("🌧️", "Slight rain"),
    63: ("🌧️", "Moderate rain"),
    65: ("🌧️", "Heavy rain"),
    66: ("🌧️", "Light freezing rain"),
    67: ("🌧️", "Heavy freezing rain"),
    71: ("❄️", "Slight snow"),
    73: ("❄️", "Moderate snow"),
    75: ("❄️", "Heavy snow"),
    80: ("🌦️", "Slight rain showers"),
    81: ("🌧️", "Moderate rain showers"),
    82: ("🌧️", "Violent rain showers"),
    95: ("⛈️", "Thunderstorm"),
    96: ("⛈️", "Thunderstorm with hail (slight)"),
    99: ("⛈️", "Thunderstorm with hail (severe)"),
}

SHORT_DESC_MAP = {
    "Slight rain showers": "Slight rain",
    "Moderate rain showers": "Moderate rain",
    "Violent rain showers": "Heavy rain",
    "Thunderstorm with hail (slight)": "Hail Storm",
    "Thunderstorm with hail (severe)": "Severe Storm",
    "Light drizzle": "Drizzle",
    "Moderate drizzle": "Mod drizzle",
    "Dense drizzle": "Dense drizzle",
    "Slight rain": "Slight rain",
    "Moderate rain": "Mod rain",
    "Heavy rain": "Heavy rain",
    "Light freezing rain": "Freezing rain",
    "Heavy freezing rain": "Heavy freeze",
    "Slight snow": "Snow",
    "Moderate snow": "Mod snow",
    "Heavy snow": "Heavy snow",
    "Clear sky": "Clear",
    "Mainly clear": "Mainly clear",
    "Partly cloudy": "Part cloudy",
    "Overcast": "Overcast",
    "Fog": "Fog",
    "Depositing rime fog": "Rime fog",
}

FG_HEADER = "#f4b8e4"
FG_TEXT = "#ffffff"

TEMP_COLORS = [
    (15, "#8caaee"),
    (18, "#85c1dc"),
    (21, "#99d1db"),
    (24, "#81c8be"),
    (27, "#a6d189"),
    (30, "#e5c890"),
    (32, "#ef9f76"),
    (33, "#ea999c"),
    (100, "#e78284"),
]


def temp_to_color(temp):
    """Return color based on temperature threshold."""
    for t_max, color in TEMP_COLORS:
        if temp <= t_max:
            return color
    return TEMP_COLORS[-1][1]


def get_weather_info(code):
    """Return icon and description for weather code."""
    return WEATHER_MAP.get(code, ("❓", "Unknown"))


def get_short_desc(desc):
    """Return shortened description for display."""
    return SHORT_DESC_MAP.get(desc, desc)


def max_line_length(lines):
    """Calculate max line length excluding markup tags."""
    clean = [re.sub(r"<.*?>", "", line) for line in lines]
    return max((len(x) for x in clean), default=0)


def fail(msg="Weather unavailable"):
    """Output error message and exit."""
    print(
        json.dumps(
            {"text": "N/A", "tooltip": f"<span foreground='{FG_HEADER}'>{msg}</span>"}
        )
    )
    sys.exit(0)


def get_location_by_ip():
    """Get latitude, longitude, and city name from IP address."""
    try:
        r = requests.get("https://checkip.amazonaws.com", timeout=5)
        ip = r.text.strip()

        r = requests.get(f"http://ip-api.com/json/{ip}", timeout=5)
        r.raise_for_status()
        data = r.json()
        return data["lat"], data["lon"], data.get("city", "Your Location")
    except Exception:
        return 0.0, 0.0, "Your Location"


def build_api_url(lat, lon):
    """Build Open-Meteo API URL."""
    return (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lon}"
        f"&current_weather=true"
        f"&hourly=temperature_2m,apparent_temperature,weathercode,"
        f"relativehumidity_2m,windspeed_10m,precipitation_probability,precipitation"
        f"&daily=temperature_2m_max,temperature_2m_min,weathercode,precipitation_sum"
        f"&timezone=auto"
    )


def fetch_weather_data(url):
    """Fetch weather data from API."""
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        fail(f"Failed to fetch weather: {e}")


def find_current_hour_index(times, now):
    """Find index of current hour in times array."""
    for i, t in enumerate(times):
        dt = datetime.fromisoformat(t)
        if dt.hour == now.hour and dt.date() == now.date():
            return i
    return 0


def extract_current_weather(data, now):
    """Extract current weather information."""
    current = data["current_weather"]
    hourly = data["hourly"]
    times = hourly["time"]

    idx = find_current_hour_index(times, now)

    return {
        "temp": current["temperature"],
        "code": current["weathercode"],
        "feels_like": hourly.get(
            "apparent_temperature", [current["temperature"]] * len(times)
        )[idx],
        "humidity": hourly.get("relativehumidity_2m", [0] * len(times))[idx],
        "windspeed": hourly.get("windspeed_10m", [0] * len(times))[idx],
    }


def build_current_section(weather, location_name):
    """Build current weather section lines."""
    icon, desc = get_weather_info(weather["code"])
    temp = weather["temp"]
    feels_like = weather["feels_like"]

    return [
        f"🌡️ <span foreground='{temp_to_color(temp)}'>{temp}°C</span> "
        f"(Feels like <span foreground='{temp_to_color(feels_like)}'>{feels_like}°C</span>)",
        f"{icon} {desc}",
        f"💧 Humidity: {weather['humidity']}%",
        f"🌬️ Wind Speed: {weather['windspeed']} km/h",
    ]


def build_today_rain_info(hourly, now):
    """Build rain information for today."""
    lines = []
    times = hourly["time"]
    rain_arr = hourly.get("precipitation_probability", [0] * len(times))
    precip_arr = hourly.get("precipitation", [0] * len(times))

    rain_probs = []
    rain_start_time = None
    precip_total = 0

    for t, prob, precip in zip(times, rain_arr, precip_arr):
        dt = datetime.fromisoformat(t)
        if dt.date() == now.date() and dt >= now:
            rain_probs.append(prob)
            precip_total += precip
            if prob > 0 and rain_start_time is None:
                rain_start_time = dt

    if rain_probs and max(rain_probs) > 0:
        lines.append(
            f"🌧️ Chance of rain today: <span foreground='{FG_TEXT}'>{max(rain_probs)}%</span>"
        )
        if rain_start_time:
            lines.append(
                f"⏱️ Expected rain start: {rain_start_time.strftime('%I:%M %p')}"
            )
        else:
            lines.append("⏱️ Expected rain start: None predicted")
        lines.append(f"☔ Total predicted rain: {precip_total:.1f} mm")
        lines.append("")

    return lines


def build_hourly_forecast(hourly, now, for_date):
    """Build hourly forecast lines for a specific date."""
    lines = []
    times = hourly["time"]
    temps = hourly["temperature_2m"]
    codes = hourly["weathercode"]

    for t, temp, code in zip(times, temps, codes):
        dt = datetime.fromisoformat(t)
        if dt.date() != for_date:
            continue
        if for_date == now.date() and dt < now:
            continue

        hour = dt.strftime("%H:%M")
        icon, desc = get_weather_info(code)
        short_desc = get_short_desc(desc)
        color = temp_to_color(temp)
        lines.append(
            f"{hour} - <span foreground='{color}'>{temp:>2}°C</span> {icon} {short_desc}"
        )

    return lines if lines else ["Hourly forecast unavailable"]


def build_tomorrow_forecast(hourly, tomorrow):
    """Build tomorrow's forecast at key times."""
    lines = []
    TIME_LABELS = {6: "Morning", 12: "Midday", 15: "Afternoon", 18: "Evening"}
    label_width = max(len(v) for v in TIME_LABELS.values())

    times = hourly["time"]
    temps = hourly["temperature_2m"]
    codes = hourly["weathercode"]

    for t, temp, code in zip(times, temps, codes):
        dt = datetime.fromisoformat(t)
        if dt.date() != tomorrow:
            continue
        label = TIME_LABELS.get(dt.hour)
        if not label:
            continue

        icon, desc = get_weather_info(code)
        short_desc = get_short_desc(desc)
        color = temp_to_color(temp)
        lines.append(
            f"{label:<{label_width}} - <span foreground='{color}'>{temp:>2}°C</span> {icon} {short_desc}"
        )

    return lines if lines else ["Tomorrow forecast unavailable"]


def build_daily_forecast(daily, days):
    """Build multi-day forecast."""
    lines = []
    dates = daily["time"]
    max_temps = daily["temperature_2m_max"]
    min_temps = daily["temperature_2m_min"]
    codes = daily["weathercode"]

    for i in range(1, min(days + 1, len(dates))):
        day_name = calendar.day_name[datetime.fromisoformat(dates[i]).weekday()][:3]
        icon, desc = get_weather_info(codes[i])
        short_desc = get_short_desc(desc)
        lines.append(
            f"{day_name:<3} "
            f"⬆️<span foreground='{temp_to_color(max_temps[i])}'>{max_temps[i]:>2}°C</span> "
            f"⬇️<span foreground='{temp_to_color(min_temps[i])}'>{min_temps[i]:>2}°C</span> "
            f"{icon} {short_desc}"
        )

    return lines


def render_section(lines, heading, max_len):
    """Render a tooltip section with heading and separator."""
    return [
        f"<span foreground='{FG_HEADER}' font='9'>{heading}</span>",
        f"<span foreground='#ffffff'>{'─' * max_len}</span>",
        *[f"<span foreground='{FG_TEXT}' font='9'>{line}</span>" for line in lines],
        "",
    ]


def build_tooltip(sections, max_len):
    """Build complete tooltip from sections."""
    tooltip_lines = []
    for lines, heading in sections:
        tooltip_lines += render_section(lines, heading, max_len)
    return "\n".join(tooltip_lines)


def main():
    lat, lon, location_name = get_location_by_ip()
    url = build_api_url(lat, lon)
    data = fetch_weather_data(url)
    now = datetime.now()
    tomorrow = now.date() + timedelta(days=1)

    try:
        weather = extract_current_weather(data, now)
    except Exception:
        fail("Failed to parse current weather")

    icon, _ = get_weather_info(weather["code"])
    text = f" | {icon} <span foreground='{temp_to_color(weather['temp'])}'>{weather['temp']}°C</span>"

    hourly = data["hourly"]
    daily = data["daily"]
    current_lines = build_current_section(weather, location_name)
    today_lines = build_today_rain_info(hourly, now) + build_hourly_forecast(
        hourly, now, now.date()
    )
    tomorrow_lines = build_tomorrow_forecast(hourly, tomorrow)
    daily_lines = build_daily_forecast(daily, DAYS_FORECAST)

    all_lines = current_lines + today_lines + tomorrow_lines + daily_lines
    headings = [
        f"🌍 Current Weather - {location_name}",
        "☀️ Today Forecast:",
        "⛅ Tomorrow Forecast:",
        f"📅 Upcoming {DAYS_FORECAST}-day Forecast:",
    ]
    max_len = max_line_length(all_lines + headings)

    sections = [
        (current_lines, f"🌍 Current Weather - {location_name}"),
        (today_lines, "☀️ Today Forecast:"),
        (tomorrow_lines, "⛅ Tomorrow Forecast:"),
        (daily_lines, f"📅 Upcoming {DAYS_FORECAST}-day Forecast:"),
    ]
    tooltip = build_tooltip(sections, max_len)
    print(
        json.dumps(
            {"text": text, "tooltip": tooltip, "markup": "pango"}, ensure_ascii=False
        )
    )


if __name__ == "__main__":
    main()
