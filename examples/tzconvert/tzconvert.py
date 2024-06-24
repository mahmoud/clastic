# Copyright (C) 2024 H. Turgut Uyar <uyar@tekir.org>
#
# Released under the BSD license.
#
# This is an example application for the Clastic web application framework.
# It is developed as part of a tutorial:
#
# https://python-clastic.readthedocs.io/en/latest/tutorial.html

from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo, available_timezones

from clastic import Application, render_json
from clastic.render import AshesRenderFactory
from clastic.static import StaticApplication


def get_location(zone):
    return zone.split("/")[-1].replace("_", " ")


def get_all_time_zones():
    time_zones = []
    for zone in available_timezones():
        entry = {
            "location": get_location(zone),
            "zone": zone,
        }
        time_zones.append(entry)
    return sorted(time_zones, key=lambda x: x["location"])


ALL_TIME_ZONES = get_all_time_zones()


def home():
    render_ctx = {
        "default_time": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M"),
        "default_src": "UTC",
        "default_dst": "UTC",
        "zones": ALL_TIME_ZONES,
    }
    return render_ctx


def convert_tz(dt_naive, src_zone, dst_zone):
    src_dt = dt_naive.replace(tzinfo=src_zone)
    dst_dt = src_dt.astimezone(dst_zone)
    return dst_dt


def show_time(request):
    dt = request.values.get("dt")
    dt_naive = datetime.strptime(dt, "%Y-%m-%dT%H:%M")

    src = request.values.get("src")
    src_zone = ZoneInfo(src)

    dst = request.values.get("dst")
    dst_zone = ZoneInfo(dst)

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
    static_path = Path(__file__).parent / "static"
    static_app = StaticApplication(str(static_path))
    routes = [
        ("/", home, "home.html"),
        ("/show", show_time, render_json),
        ("/static", static_app),
    ]
    templates_path = Path(__file__).parent
    render_factory = AshesRenderFactory(str(templates_path))
    return Application(routes, render_factory=render_factory)


app = create_app()

if __name__ == "__main__":
    app.serve()
