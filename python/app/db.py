from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

import pymysql
from pymysql.connections import Connection

from app.config import settings


@contextmanager
def get_connection(*, autocommit: bool = False) -> Iterator[Connection]:
    conn = pymysql.connect(
        host=settings.db_host,
        port=settings.db_port,
        user=settings.db_user,
        password=settings.db_password,
        database=settings.db_name,
        charset=settings.db_charset,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=autocommit,
    )
    try:
        yield conn
        if not autocommit:
            conn.commit()
    except Exception:
        if not autocommit:
            conn.rollback()
        raise
    finally:
        conn.close()
