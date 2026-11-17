"""Test del catalogo sul database reale: sole letture, nessuna reindicizzazione."""
import pytest

pytestmark = pytest.mark.integration

from fastapi.testclient import TestClient
from app import core, web


def test_catalog_sql_complete_without_semantic_dependencies(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('Il catalogo non deve usare Qdrant, embedding o indicizzazione')
    for name in ['qdrant', 'model', 'encode', 'search', 'import_dialogues']:
        monkeypatch.setattr(core, name, forbidden)
    monkeypatch.setattr(web, 'qdrant', forbidden)
    monkeypatch.setattr(web, 'search', forbidden)
    with core.db() as conn:
        expected = conn.execute('SELECT id,title,description,video_path FROM episodes ORDER BY id DESC').fetchall()
        manual_ids = {row['id'] for row in conn.execute('''SELECT e.id FROM episodes e
            LEFT JOIN episode_sources s ON e.id=s.episode_id WHERE s.episode_id IS NULL''').fetchall()}
    # Il context manager esegue anche l'avvio: nessun caricamento del modello.
    with TestClient(web.app) as client:
        for size in [1, 2, 100]:
            collected, cursor = [], None
            while True:
                params = {'limit': size}
                if cursor is not None:
                    params['before_id'] = cursor
                response = client.get('/episodes', params=params)
                assert response.status_code == 200
                data = response.json()
                assert data['total'] == len(expected)
                assert len(data['episodes']) <= size
                collected.extend(data['episodes'])
                new_cursor = data['next_before_id']
                if new_cursor is None:
                    break
                assert new_cursor == data['episodes'][-1]['id']
                assert cursor is None or new_cursor < cursor
                cursor = new_cursor
            assert [item['id'] for item in collected] == [row['id'] for row in expected]
            assert manual_ids <= {item['id'] for item in collected}
            for item, row in zip(collected, expected):
                assert item['title'] == row['title'] and item['description'] == row['description']
                url = f'/video/{row["id"]}' if core.safe_video(row['video_path']) else None
                assert item['video_url'] == url
                assert 'video_path' not in item
        assert client.get('/episodes?before_id=1').json()['episodes'] == []
        for params in [{'limit': 0}, {'limit': 101}, {'before_id': 0},
                       {'before_id': '1 OR 1=1'}, {'before_id': 9223372036854775808}]:
            assert client.get('/episodes', params=params).status_code == 422
