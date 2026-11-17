"""Test su corpus dimostrativo: la reindicizzazione SCRIVE su SQL/Qdrant."""
import pytest

pytestmark = pytest.mark.integration

from fastapi.testclient import TestClient
from app.web import app
from app.core import db, qdrant, COLLECTION, import_dialogues, chunks

def counts():
    with db() as conn:
        ids = conn.execute('SELECT source_key,episode_id FROM episode_sources ORDER BY source_key').fetchall()
    return ids, qdrant().get_collection(COLLECTION).points_count

def test_reindex_idempotent():
    before = counts()
    assert import_dialogues() >= 2
    assert counts() == before
    with db() as conn:
        assert conn.execute('SELECT title FROM episodes WHERE id=1').fetchone()['title'] == 'Docker: le basi'

def test_end_to_end():
    with TestClient(app) as client:
        assert client.get('/health').status_code == 200
        assert client.get('/').status_code == 200
        for query, expected in [('Come isolare applicazioni con i container?', 'docker'),
                                ('Come orchestrare un cluster di pod?', 'kubernetes')]:
            response = client.get('/search', params={'q': query})
            assert response.status_code == 200
            hits = response.json()['results']
            assert expected in hits[0]['title'].lower()
            assert len({h['id'] for h in hits}) == len(hits)
            video = next(h['video_url'] for h in hits if h['video_url'])
            assert client.get(video, headers={'Range': 'bytes=0-99'}).status_code == 206
        assert client.get('/search', params={'q': ' '}).status_code == 422
        assert client.get('/search', params={'q': 'x', 'limit': 100}).status_code == 422
        assert client.get('/video/9999999').status_code == 404

def test_long_text():
    parts = chunks('Questa è una frase sui container Docker. ' * 300)
    assert len(parts) > 1
