# -*- coding: utf-8 -*-

import sys
sys.path.append('../..')

import os
import sqlite3

from clastic.cline import Cline
from clastic.middleware import GetParamMiddleware


class TodoList(object):
    SCHEMA = """CREATE TABLE todo (id INTEGER PRIMARY KEY,
                                   task char(100) NOT NULL,
                                   status bool NOT NULL)"""

    def __init__(self, path):
        self.path = path

    def get_connection(self):
        return sqlite3.connect(self.path)

    def _execute(self, *a):
        print a
        "a handy convenience function for executin SQLs right quick"
        conn = self.get_connection()
        conn.row_factory = self._dict_factory
        cursor = conn.cursor()
        cursor.execute(*a)
        conn.commit()
        return cursor

    def create_db(self, reset=False):
        if os.path.isfile(self.path):
            os.remove(self.path)
        self._execute(self.SCHEMA)

    def add_task(self, name, done=False):
        query = "INSERT INTO todo (task, status) VALUES (:name, :done)"
        self._execute(query, {'name': name, 'done': done})

    def set_status(self, name, done=True):
        query = "UPDATE todo SET status=:done WHERE task=':name'"
        self._execute(query, {'name': name, 'done': done})

    def get_tasks(self, done=None):
        query = 'SELECT id, task, status FROM todo'
        if done is not None:
            query += " WHERE status=:done"
        cursor = self._execute(query, {'done': done})
        return cursor.fetchall()

    @staticmethod
    def _dict_factory(cursor, row):
        d = {}
        for idx, col in enumerate(cursor.description):
            d[col[0]] = row[idx]
        return d


def _add_test_data(the_list, count=6):
    for i in range(count):
        is_done = (i % 2) == 1
        the_list.add_task('task_%s' % i, done=is_done)
    return


the_list = TodoList('todo.db')
the_list.create_db(reset=True)
_add_test_data(the_list)

app = Cline(resources={'todo_list': the_list})
done_mw = GetParamMiddleware({'done': int})


@app.route('/', middlewares=[done_mw])
@app.route('/todo', middlewares=[done_mw])
def get_tasks(todo_list, done=None):
    return todo_list.get_tasks(done=done)


if __name__ == '__main__':
    app.run()
