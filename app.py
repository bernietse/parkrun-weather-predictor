import datetime as dt
import streamlit as st

from weather import get_forecast_at_9am
from model import predict_finish_time, format_mmss, parse_mmss

st.set_page_config(page_title="parkrun weather predictor", page_icon="🏃", layout="centered")
st.title("🏃 parkrun weather finish time predictor")
st.caption(
    "Estimates how much faster or slower you might run at 9am based on "
    "forecast weather and general sports-science trends for endurance running. "
    "This is a general-purpose heuristic, not trained on any specific parkrun's "
    "own results (that data isn't open to reuse) — see model.py for the "
    "assumptions behind the estimate."
)

average = st.text_input("Your average parkrun time (mm:ss)", "22:15")

with st.expander("Course & weather details (optional)"):
    exposure = st.selectbox(
        "How exposed is the course to wind?",
        ["exposed", "sheltered"],
        index=0,
        help="Open, riverside/coastal courses are usually exposed; wooded or urban courses are usually sheltered.",
    )
    surface = st.selectbox(
        "Surface",
        ["towpath", "tarmac"],
        index=0,
        help="Grass/gravel/towpath surfaces get slippery in the rain; tarmac is less affected.",
    )
    target_date = st.date_input("Run date", dt.date.today())

predict_clicked = st.button("Predict finish time", type="primary", use_container_width=True)

if predict_clicked:
    try:
        avg_sec = parse_mmss(average)
    except ValueError:
        st.error("Times must be in mm:ss format, e.g. 22:15")
        st.stop()

    try:
        weather = get_forecast_at_9am(target_date)
    except Exception as e:
        st.error(f"Couldn't fetch weather: {e}")
        st.stop()

    result = predict_finish_time(avg_sec, weather, course_exposure=exposure, surface=surface)

    direction = "slower" if result.pct_change >= 0 else "faster"
    st.metric(
        f"Predicted finish ({direction} than your average)",
        format_mmss(result.predicted_seconds),
        delta=f"{result.pct_change:+.1f}%",
        delta_color="inverse",
    )

    st.write("**Breakdown of the weather effect:**")
    e = result.effect
    st.table({
        "Factor": ["Temperature", "Humidity", "Wind", "Rain/surface"],
        "Effect on pace": [
            f"{e.temperature_pct:+.2f}%",
            f"{e.humidity_pct:+.2f}%",
            f"{e.wind_pct:+.2f}%",
            f"{e.rain_pct:+.2f}%",
        ],
    })

    st.write(f"**9am weather used ({target_date}):**")
    wcol1, wcol2 = st.columns(2)
    wcol1.metric("Temperature", f"{weather['temperature_c']:.0f}°C")
    wcol2.metric("Humidity", f"{weather['humidity_pct']:.0f}%")
    wcol3, wcol4 = st.columns(2)
    wcol3.metric("Wind", f"{weather['wind_speed_kmh']:.0f} km/h")
    wcol4.metric("Rain", f"{weather['precipitation_mm']:.1f} mm")
