#!/usr/bin/env python3
import sqlite3
import sys
import bcrypt


def initialize_db() -> None:
    """Ensure that the database has the required tables and that there is at least one admin user."""
    """Note: If the database already has tables with the correct names, but improper schema, this will not fix it."""
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
                          bcrypt.hashpw(bytes('password', 'utf-8'), bcrypt.gensalt()).decode('utf-8'),
                          '1'])
        cur.fetchall()
        cur.close()
        db.commit()
        print('Added default user. Email: "admin@admin.admin" Password: "password"')
    db.close()


if __name__ == '__main__':
    # test1.py executed as script
    # do something
    initialize_db()
