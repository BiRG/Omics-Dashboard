#!/usr/bin/env python3
import sqlite3
import sys
from passlib.hash import pbkdf2_sha256
# ensure database has required tables (note if database already has tables with correct names,
# but improper schema, this will not fix them


def initialize_db():
    db = sqlite3.connect(sys.argv[1])
    with open('schema.sql', mode='r') as f:
        db.cursor().executescript(f.read())
    db.commit()
    cur = db.execute('select * from Users where admin=1')

    val = cur.fetchall()
    print('select * from Users where admin=1')
    cur.close()

    if len(val) is 0:
        cur = db.execute('insert into Users (email, name, password, admin) values (?, ?, ?, ?)',
                         ['admin@admin.admin', 'Addison Minh',
                          pbkdf2_sha256.hash('password'),
                          '1'])
        cur.fetchall()
        cur.close()
        db.commit()
        print('Added default user. Email: \'admin@admin.admin\' Password: \'password\'')
    db.close()


if __name__ == '__main__':
    # test1.py executed as script
    # do something
    initialize_db()