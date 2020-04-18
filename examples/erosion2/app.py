import os

from clastic import Application
from clastic.render import AshesRenderFactory
from clastic.static import StaticApplication


CUR_PATH = os.path.dirname(os.path.abspath(__file__))
STATIC_PATH = os.path.join(CUR_PATH, "static")


def home():
    return {}


def create_app():
    static_app = StaticApplication(STATIC_PATH)
    routes = [
        ("/", home, "home.html"),
        ("/static", static_app),
    ]
    render_factory = AshesRenderFactory(CUR_PATH)
    return Application(routes, render_factory=render_factory)


app = create_app()

if __name__ == "__main__":
    app.serve()
