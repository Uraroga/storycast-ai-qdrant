"""Catalogo isolato: nessuna dipendenza esterna e nessuna scrittura."""
from fastapi.testclient import TestClient
from app import web


def test_empty_catalog(monkeypatch):
    class EmptyDB:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def execute(self, query, params=None):
            return self
        def fetchone(self):
            return {'total': 0}
        def fetchall(self):
            return []
    monkeypatch.setattr(web, 'db', EmptyDB)
    with TestClient(web.app) as client:
        response = client.get('/episodes')
    assert response.status_code == 200
    assert response.json() == {'total': 0, 'episodes': [], 'next_before_id': None}


def test_catalog_unavailable(monkeypatch):
    def unavailable():
        raise ConnectionError('PostgreSQL test unavailable')
    monkeypatch.setattr(web, 'db', unavailable)
    response = TestClient(web.app).get('/episodes')
    assert response.status_code == 503
    assert response.json()['detail'] == 'Catalogo non disponibile; controllare PostgreSQL'
