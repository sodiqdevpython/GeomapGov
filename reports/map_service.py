import os
import folium
from django.conf import settings
from .models import Report
from folium.plugins import HeatMap
from folium.plugins import MarkerCluster
from .forecast_service import forecast_hotspots



def get_color(category):
    colors = {
        "road": "red",
        "waste": "green",
        "traffic": "blue",
        "ecology": "orange",
        "other": "gray",
    }
    return colors.get(category, "gray")



def generate_reports_map():
    reports = Report.objects.exclude(
        latitude__isnull=True,
        longitude__isnull=True
    )

    map_obj = folium.Map(
        location=[41.311081, 69.240562],
        zoom_start=12,
        tiles="CartoDB positron"
    )

    # 🔥 1. MARKERLAR
    for report in reports:
        category = report.category_ai or "other"

        popup_text = f"""
        <b>{report.title}</b><br>
        {report.description}<br>
        <b>AI kategoriya:</b> {category}<br>
        """

        folium.Marker(
            location=[float(report.latitude), float(report.longitude)],
            popup=popup_text,
            icon=folium.Icon(color=get_color(category))
        ).add_to(map_obj)

    # 🔥 2. PROGNOZ QO‘SHILADI (SHU YERGA!)
    hotspots = forecast_hotspots()

    for h in hotspots:
        folium.Circle(
            location=[h["lat"], h["lon"]],
            radius=200,
            color="purple",
            fill=True,
            fill_opacity=0.4,
            popup=f"Forecast muammo: {round(h['count'],2)}"
        ).add_to(map_obj)

    # 🔥 3. SAQLASH
    map_obj.save("templates/reports_map.html")

    return "reports_map.html"