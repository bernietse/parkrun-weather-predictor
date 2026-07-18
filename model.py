"""
Heuristic weather-adjustment model for 5km parkrun finish times.

This is NOT a model trained on any specific parkrun course's own results —
there is no open dataset of parkrun times available to train on (parkrun's
results pages are public to view but their terms of service prohibit bulk
scraping/reuse).

Instead this encodes the general, well-established sports-science
relationship between endurance running performance and weather:
  - Performance is best in a cool ~8-14C band; heat above that impairs
    thermoregulation and slows pace. The effect is proportionally SMALLER
    for a 5km effort (~20-30 min) than for a marathon (~3-5 hrs), since
    there's much less time for heat stress to accumulate.
  - High humidity compounds heat stress (sweat evaporates less effectively).
  - Wind has an asymmetric cost: a headwind costs more time than a tailwind
    saves, so any wind is a net negative on an out-and-back/loop course.
  - Rain reduces grip, more so on grass/gravel towpath than tarmac.

Coefficients below are deliberately conservative, round-number approximations
of published trends, not fitted statistics. Treat outputs as an informed
estimate, not a precise prediction.
"""
from dataclasses import dataclass, field


@dataclass
class WeatherEffect:
    temperature_pct: float
    humidity_pct: float
    wind_pct: float
    rain_pct: float

    @property
    def total_pct(self) -> float:
        return self.temperature_pct + self.humidity_pct + self.wind_pct + self.rain_pct


def compute_weather_effect(
    temperature_c: float,
    humidity_pct: float,
    wind_speed_kmh: float,
    precipitation_mm: float,
    course_exposure: str = "exposed",  # "exposed" or "sheltered"
    surface: str = "towpath",  # "towpath" (grass/gravel) or "tarmac"
) -> WeatherEffect:
    # Temperature: no penalty in the 8-14C optimal band.
    if temperature_c > 14:
        over = temperature_c - 14
        temp_pct = 0.4 * over
        if temperature_c > 22:
            temp_pct += 0.3 * (temperature_c - 22)
    elif temperature_c < 5:
        temp_pct = 0.15 * (5 - temperature_c)
    else:
        temp_pct = 0.0

    # Humidity only bites once it's warm enough for sweating to matter.
    humidity_effect = 0.0
    if temperature_c > 18 and humidity_pct > 60:
        humidity_effect = 0.05 * (humidity_pct - 60)

    # Wind: exposed towpath feels the full effect, sheltered sections less so.
    wind_factor = 0.08 if course_exposure == "exposed" else 0.04
    wind_effect = wind_factor * wind_speed_kmh

    # Rain: mainly a grip/surface issue, worse on towpath than tarmac.
    rain_effect = 0.0
    if precipitation_mm > 0:
        base_rain = 1.0 if surface == "towpath" else 0.4
        rain_effect = min(base_rain + 0.2 * precipitation_mm, base_rain * 2.5)

    return WeatherEffect(
        temperature_pct=round(temp_pct, 2),
        humidity_pct=round(humidity_effect, 2),
        wind_pct=round(wind_effect, 2),
        rain_pct=round(rain_effect, 2),
    )


@dataclass
class Prediction:
    predicted_seconds: float
    pct_change: float
    effect: WeatherEffect
    baseline_seconds: float


def predict_finish_time(
    average_seconds: float,
    weather: dict,
    course_exposure: str = "exposed",
    surface: str = "towpath",
) -> Prediction:
    effect = compute_weather_effect(
        temperature_c=weather["temperature_c"],
        humidity_pct=weather["humidity_pct"],
        wind_speed_kmh=weather["wind_speed_kmh"],
        precipitation_mm=weather["precipitation_mm"],
        course_exposure=course_exposure,
        surface=surface,
    )
    pct = effect.total_pct
    predicted = average_seconds * (1 + pct / 100)
    return Prediction(
        predicted_seconds=predicted,
        pct_change=pct,
        effect=effect,
        baseline_seconds=average_seconds,
    )


def format_mmss(seconds: float) -> str:
    seconds = round(seconds)
    m, s = divmod(seconds, 60)
    return f"{m}:{s:02d}"


def parse_mmss(text: str) -> float:
    text = text.strip()
    if ":" in text:
        m, s = text.split(":")
        return int(m) * 60 + float(s)
    return float(text)
