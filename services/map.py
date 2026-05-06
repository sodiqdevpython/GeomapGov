import folium
from folium.plugins import HeatMap

def generate_map(data):
    m = folium.Map(location=[41.31, 69.28], zoom_start=12)

    coords = [[row['lat'], row['lon']] for _, row in data.iterrows()]
    HeatMap(coords).add_to(m)

    for _, row in data.iterrows():
        folium.Marker(
            [row['lat'], row['lon']],
            popup=row['text']
        ).add_to(m)

    m.save("static/map.html")