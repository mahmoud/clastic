import json
import os
from datetime import datetime

from clastic import Application, render_json
from clastic.render import AshesRenderFactory
from clastic.static import StaticApplication
from dateutil import parser, tz, zoneinfo


CUR_PATH = os.path.dirname(os.path.abspath(__file__))
STATIC_PATH = os.path.join(CUR_PATH, "static")


def get_location(zone):
    return zone.split("/")[-1].replace("_", " ")


def get_all_time_zones():
    zone_info = zoneinfo.get_zonefile_instance()
    zone_names = zone_info.zones.keys()
    entries = {get_location(zone): zone for zone in zone_names}
    return [
        {"location": location, "zone": entries[location]}
        for location in sorted(entries.keys())
    ]


ALL_TIME_ZONES = get_all_time_zones()


def home():
    render_ctx = {
        "zones": ALL_TIME_ZONES,
        "default_src": "UTC",
        "default_dst": "UTC",
        "now": datetime.utcnow().strftime("%Y-%m-%dT%H:%M"),
    }
    return render_ctx


def convert_tz(dt_naive, src_zone, dst_zone):
    src_dt = dt_naive.replace(tzinfo=src_zone)
    dst_dt = src_dt.astimezone(dst_zone)
    return dst_dt


def show_time(request):
    values = json.loads(request.data)

    dt = values.get("dt")
    dt_naive = parser.parse(dt)

    src = values.get("src")
    src_zone = tz.gettz(src)

    dst = values.get("dst")
    dst_zone = tz.gettz(dst)

    dst_dt = convert_tz(dt_naive, src_zone, dst_zone)
    render_ctx = {
        "src_dt": {
            "text": dt_naive.ctime(),
            "value": dt
        },
        "dst_dt": {
            "text": dst_dt.ctime(),
            "value": dst_dt.strftime('%Y-%m-%dT%H:%M')
        },
        "src_location": get_location(src),
        "dst_location": get_location(dst),
    }
    return render_ctx


def create_app():
    static_app = StaticApplication(STATIC_PATH)
    routes = [
        ("/", home, "home.html"),
        ("/show", show_time, render_json),
        ("/static", static_app),
    ]
    render_factory = AshesRenderFactory(CUR_PATH)
    return Application(routes, render_factory=render_factory)


app = create_app()

if __name__ == "__main__":
    app.serve()
