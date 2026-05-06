import pandas as pd
from datetime import datetime, timedelta
from .models import Report


def get_reports_dataframe():
    data = []

    for r in Report.objects.exclude(latitude__isnull=True):
        data.append({
            "lat": float(r.latitude),
            "lon": float(r.longitude),
            "date": r.created_at,  # ✅ TUZATILDI
            "category": r.category_ai or "other"
        })

    df = pd.DataFrame(data)
    return df


def forecast_hotspots(days=3):
    df = get_reports_dataframe()

    if df.empty:
        return []

    # vaqt bo‘yicha guruhlash
    df_grouped = df.groupby(["lat", "lon", "date"]).size().reset_index(name="count")

    # oxirgi kunlarni olish
    recent_date = df_grouped["date"].max()
    last_days = df_grouped[
        df_grouped["date"] >= (recent_date - timedelta(days=days))
    ]

    # o‘rtacha qiymat
    forecast = last_days.groupby(["lat", "lon"])["count"].mean().reset_index()

    # yuqori muammo zonalari
    hotspots = forecast.sort_values(by="count", ascending=False).head(10)

    return hotspots.to_dict(orient="records")