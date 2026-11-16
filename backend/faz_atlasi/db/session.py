"""Bağlantı: FAZ_DB_URL ortam değişkeni (ör. postgresql+psycopg://user:pw@host/faz), yoksa yerel SQLite."""
import os

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

VARSAYILAN_SQLITE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'data', 'faz_atlasi.db')


def db_url():
    return os.environ.get('FAZ_DB_URL') or 'sqlite:///' + os.path.abspath(VARSAYILAN_SQLITE).replace('\\', '/')


def make_engine(url=None, echo=False):
    url = url or db_url()
    if url.startswith('sqlite:///') and ':memory:' not in url:
        os.makedirs(os.path.dirname(url[len('sqlite:///'):]), exist_ok=True)
    engine = create_engine(url, echo=echo, future=True)
    if engine.dialect.name == 'sqlite':
        # SQLite yabancı anahtarları ancak açıkça istenirse uygular (ON DELETE CASCADE için gerekli)
        @event.listens_for(engine, 'connect')
        def _fk(dbapi_conn, _):
            dbapi_conn.execute('PRAGMA foreign_keys=ON')
    return engine


def make_session(engine):
    return sessionmaker(bind=engine, expire_on_commit=False)()
