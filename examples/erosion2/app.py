import os
from configparser import ConfigParser

from clastic import Application
from clastic.render import AshesRenderFactory
from clastic.static import StaticApplication


CUR_PATH = os.path.dirname(os.path.abspath(__file__))
STATIC_PATH = os.path.join(CUR_PATH, "static")


def home(host_url):
    return {"host_url": host_url}


def create_app():
    static_app = StaticApplication(STATIC_PATH)
    routes = [
        ("/", home, "home.html"),
        ("/static", static_app),
    ]

    config_path = os.path.join(CUR_PATH, "erosion.ini")
    config = ConfigParser()
    config.read(config_path)
    host_url = config["erosion"]["host_url"].rstrip('/') + '/'
    resources = {"host_url": host_url}

    render_factory = AshesRenderFactory(CUR_PATH)
    return Application(routes, resources=resources, render_factory=render_factory)


app = create_app()

if __name__ == "__main__":
    app.serve()
