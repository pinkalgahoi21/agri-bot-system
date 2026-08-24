import asyncio
import requests
from config import OPENWEATHER_KEY


def _fetch_weather(city: str) -> dict | None:
    """
    Synchronous weather fetch — called via run_in_executor from async context.
    City is passed directly from farmer profile — no state resolution needed.
    """
    city = city.strip()
    print(f"[weather] Fetching for: '{city}'")

    try:
        # ── Step 1: Geocode city → lat/lon ────────────────────────────────
        geo_resp = requests.get(
            "http://api.openweathermap.org/geo/1.0/direct",
            params={
                "q":     f"{city},India",
                "limit": 1,
                "appid": OPENWEATHER_KEY
            },
            timeout=10
        )

        if geo_resp.status_code != 200:
            print(f"[weather] Geocode HTTP {geo_resp.status_code}: {geo_resp.text}")
            return None

        geo_data = geo_resp.json()

        if not isinstance(geo_data, list) or len(geo_data) == 0:
            print(f"[weather] No geocode results for '{city}'")
            return None

        lat       = geo_data[0]["lat"]
        lon       = geo_data[0]["lon"]
        city_name = geo_data[0].get("name", city)

        # ── Step 2: Current weather ───────────────────────────────────────
        w_resp = requests.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params={
                "lat":   lat,
                "lon":   lon,
                "appid": OPENWEATHER_KEY,
                "units": "metric"
            },
            timeout=10
        )

        if w_resp.status_code != 200:
            print(f"[weather] Weather HTTP {w_resp.status_code}: {w_resp.text}")
            return None

        w = w_resp.json()

        # ── Step 3: 5-day forecast (cnt=40 = 8 slots/day × 5 days) ──────
        f_resp = requests.get(
            "https://api.openweathermap.org/data/2.5/forecast",
            params={
                "lat":   lat,
                "lon":   lon,
                "appid": OPENWEATHER_KEY,
                "units": "metric",
                "cnt":   40
            },
            timeout=10
        )

        if f_resp.status_code != 200:
            print(f"[weather] Forecast HTTP {f_resp.status_code}: {f_resp.text}")
            forecast_summary = "Forecast unavailable"
        else:
            f_data = f_resp.json()
            forecast_lines = []
            seen_dates     = set()

            for item in f_data.get("list", []):
                date = item["dt_txt"].split(" ")[0]
                if date not in seen_dates:
                    seen_dates.add(date)
                    rain_mm  = item.get("rain", {}).get("3h", 0)
                    rain_str = f", 🌧 Rain: {rain_mm}mm" if rain_mm else ""
                    forecast_lines.append(
                        f"{date}: {item['main']['temp']}°C, "
                        f"{item['weather'][0]['description'].title()}"
                        f"{rain_str}"
                    )

            forecast_summary = "\n".join(forecast_lines[:5])

        return {
            "city":        city_name,
            "temp":        w["main"]["temp"],
            "feels_like":  w["main"]["feels_like"],
            "humidity":    w["main"]["humidity"],
            "wind_speed":  w["wind"]["speed"],
            "description": w["weather"][0]["description"].title(),
            "rain":        w.get("rain", {}).get("1h", 0),
            "forecast":    forecast_summary
        }

    except requests.exceptions.Timeout:
        print("[weather] Request timed out")
        return None
    except Exception as e:
        print(f"[weather] Fetch error: {e}")
        return None


async def get_weather(city: str) -> dict | None:
    """
    Async wrapper — runs blocking fetch in thread pool
    so the bot stays responsive during API calls.
    """
    return await asyncio.get_event_loop().run_in_executor(
        None, _fetch_weather, city
    )