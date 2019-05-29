
from clastic import Application, render_basic, Middleware, Route

### ACCOUNT BEGIN

class AccountMW(Middleware):
    provides = ('account',)

    def request(self, next, token, db_session):
        # imagine looking up the account with the token

        return next(account={'name': 'rohit'})


class DBSessionMW(Middleware):
    provides = ('db_session',)

    def request(self, next, config):
        # imagine connecting to a db according to a config
        return next(db_session={})


class TokenMW(Middleware):
    provides = ('token',)

    def request(self, next, request):
        # imagine decoding a header and checking a signature
        return next(token={})


def index():
    return {'msg': 'hello'}


def register(request, db_session):
    return {'msg': 'welcome'}


def check_account(account):
    return {'msg': 'checks out'}


def test_resolution_acct():
    routes = [('/', index, render_basic),
              ('/register', register, render_basic),
              ('/check', check_account, render_basic)]
    resources = {'config': {'db_url': 'dbsql:///'}}
    mws = [DBSessionMW(),
           TokenMW(),
           AccountMW()]

    app = Application(routes, resources=resources, middlewares=mws)

    assert app.routes[0].is_required_arg('config') is False
    assert app.routes[0].is_required_arg('db_session') is False
    assert app.routes[0].is_required_arg('token') is False
    assert app.routes[0].is_required_arg('account') is False

    assert app.routes[1].is_required_arg('config') is True
    assert app.routes[1].is_required_arg('db_session') is True
    assert app.routes[1].is_required_arg('token') is False
    assert app.routes[1].is_required_arg('account') is False

    assert app.routes[2].is_required_arg('config') is True
    assert app.routes[2].is_required_arg('db_session') is True
    assert app.routes[2].is_required_arg('token') is True
    assert app.routes[2].is_required_arg('account') is True


### ACCOUNT END

### BASIC BEGIN

class FirstMW(Middleware):
    provides = ('a',)

    def request(self, next):
        return next(a='AAA')


class SecondMW(Middleware):
    provides = ('b',)

    def request(self, next, a, request=None):
        return next(b='BBB')


def test_resolution_basic():
    mws = [FirstMW(), SecondMW()]

    def endpoint_func(url_arg, b):
        return {}

    route = Route('/<url_arg>/', endpoint_func, middlewares=mws)
    bound_route = route.bind(Application())
    assert bound_route.is_required_arg('a') is True


### BASIC END

### NULL BEGIN

def test_resolution_null():
    def endpoint_func():
        pass

    route = Route('/', endpoint_func)
    bound_route = route.bind(Application())
    assert len(bound_route.get_required_args()) == 0

### NULL END
