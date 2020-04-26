import os
from configparser import ConfigParser
from http import HTTPStatus

from clastic import Application, GET, POST, redirect
from clastic.errors import NotFound
from clastic.middleware.cookie import SignedCookieMiddleware
from clastic.middleware.form import PostDataMiddleware
from clastic.render import AshesRenderFactory
from clastic.static import StaticApplication

from storage import LinkDB


CUR_PATH = os.path.dirname(os.path.abspath(__file__))
STATIC_PATH = os.path.join(CUR_PATH, "static")


def home(host_url, db, cookie):
    entries = db.get_links()
    new_entry_alias = cookie.pop("new_entry_alias", None)
    return {
        "host_url": host_url,
        "entries": entries,
        "new_entry_alias": new_entry_alias,
    }


def add_entry(db, cookie, target_url, new_alias, expiry_time, max_count):
    entry = db.add_link(
        alias=new_alias,
        target_url=target_url,
        expiry_time=expiry_time,
        max_count=max_count,
    )
    cookie["new_entry_alias"] = new_alias
    return redirect("/", code=HTTPStatus.SEE_OTHER)


def use_entry(alias, db):
    entry = db.use_link(alias)
    if entry is None:
        return NotFound()
    return redirect(entry["target"], code=HTTPStatus.MOVED_PERMANENTLY)


def create_app():
    new_link_mw = PostDataMiddleware(
        {"target_url": str, "new_alias": str, "max_count": int, "expiry_time": str}
    )

    static_app = StaticApplication(STATIC_PATH)
    routes = [
        ("/", home, "home.html"),
        POST("/submit", add_entry, middlewares=[new_link_mw]),
        ("/static", static_app),
        GET("/<alias>", use_entry),
    ]

    config_path = os.path.join(CUR_PATH, "erosion.ini")
    config = ConfigParser()
    config.read(config_path)

    host_url = config["erosion"]["host_url"].rstrip("/") + "/"
    db_path = config["erosion"]["db_path"]
    resources = {"host_url": host_url, "db": LinkDB(db_path)}

    cookie_secret = config["erosion"]["cookie_secret"]
    cookie_mw = SignedCookieMiddleware(secret_key=cookie_secret)

    render_factory = AshesRenderFactory(CUR_PATH)
    return Application(
        routes,
        resources=resources,
        middlewares=[cookie_mw],
        render_factory=render_factory,
    )


app = create_app()

if __name__ == "__main__":
    app.serve()
