# -*- coding: utf-8 -*-

from clastic.cline import Cline, run

app = Cline()


@app.route('/hi')
def hello():
    return 'Hello World!'


if __name__ == '__main__':
    run(app, host='0.0.0.0', port=8080)
