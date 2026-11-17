from pathlib import Path
from app import core

def test_dialogue():
    assert core.clean_dialogue('[personaggio_1|felice]\nCiao\n\nMondo') == 'Ciao\nMondo'

def test_video_escape(tmp_path, monkeypatch):
    root = tmp_path / 'media'
    root.mkdir()
    outside = tmp_path / 'secret.mp4'
    outside.write_bytes(b'x')
    (root / 'link.mp4').symlink_to(outside)
    monkeypatch.setattr(core, 'MEDIA', root)
    assert core.safe_video('../secret.mp4') is None
    assert core.safe_video('link.mp4') is None
    assert core.safe_video('missing.mp4') is None
    (root / 'ok.mp4').write_bytes(b'x')
    assert core.safe_video('ok.mp4') == root / 'ok.mp4'

def test_empty_dialogue():
    assert core.clean_dialogue('[speaker|tone]\n\n') == ''


def test_lan_access(monkeypatch):
    import asyncio
    import httpx
    from fastapi import FastAPI
    from app.web import NetworkAccess
    monkeypatch.setenv('WEB_ALLOWED_NETWORKS', '127.0.0.0/8,::1/128,192.168.0.0/24')
    app = FastAPI()
    app.add_middleware(NetworkAccess)
    @app.get('/')
    def home():
        return {'ok': True}
    async def check():
        for peer, expected in [('192.168.0.10', 200), ('127.0.0.1', 200), ('::1', 200),
                               ('192.168.1.10', 403), ('203.0.113.1', 403), ('invalid', 403)]:
            transport = httpx.ASGITransport(app=app, client=(peer, 1234))
            async with httpx.AsyncClient(transport=transport, base_url='http://test') as client:
                response = await client.get('/', headers={'X-Forwarded-For': '192.168.0.10'})
                assert response.status_code == expected
    asyncio.run(check())

def test_api_dependency_failure(monkeypatch):
    from fastapi.testclient import TestClient
    from app import web
    def unavailable(*args, **kwargs):
        raise ConnectionError('test dependency unavailable')
    monkeypatch.setattr(web, 'db', unavailable)
    # Nessun context manager: evita il lifespan/modello nei test unitari.
    client = TestClient(web.app)
    assert client.get('/health').status_code == 503
    monkeypatch.setattr(web, 'search', unavailable)
    assert client.get('/search', params={'q': 'test'}).status_code == 503

def test_incompatible_collection_is_preserved():
    from types import SimpleNamespace
    import pytest
    from qdrant_client import models
    class ExistingCollection:
        def collection_exists(self, name):
            return True
        def get_collection(self, name):
            return SimpleNamespace(config=SimpleNamespace(params=SimpleNamespace(
                vectors=models.VectorParams(size=32, distance=models.Distance.COSINE))))
        def create_collection(self, *args, **kwargs):
            raise AssertionError('Non ricreare dati esistenti')
    with pytest.raises(RuntimeError, match='incompatibile'):
        core.ensure_collection(ExistingCollection())
