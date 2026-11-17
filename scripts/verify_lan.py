"""Verifiche HTTP LAN dal server, senza scritture al catalogo o all'indice."""
import os
import json
import socket
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from urllib.parse import urlencode, urljoin, urlsplit

BASE = os.environ.get('STORYCAST_URL', 'http://127.0.0.1:8000').rstrip('/')
LAN_HOST = urlsplit(BASE).hostname
assert LAN_HOST not in {'127.0.0.1', 'localhost', '::1'}, 'Impostare STORYCAST_URL con IP LAN'


def get(path, headers=None):
    return urlopen(Request(BASE + path, headers=headers or {}), timeout=30)


with get('/search?' + urlencode({'q': 'container Kubernetes', 'limit': 20})) as response:
    hits = json.load(response)['results']
videos = sorted({hit['video_url'] for hit in hits if hit['video_url']})
assert videos
for path in videos:
    assert path.startswith('/video/')
    assert urlsplit(urljoin(BASE, path)).netloc == urlsplit(BASE).netloc
    with get(path) as response:
        body = response.read()
        total = len(body)
        assert response.status == 200 and int(response.headers['Content-Length']) == total
        assert total > 200 and response.headers['Content-Type'].startswith('video/')
    for spec, start, end in [('0-99', 0, 99), ('100-199', 100, 199), ('-100', total-100, total-1)]:
        with get(path, {'Range': 'bytes=' + spec}) as response:
            assert response.status == 206 and response.read() == body[start:end+1]
            assert response.headers['Content-Range'] == f'bytes {start}-{end}/{total}'
    try:
        get(path, {'Range': f'bytes={total}-'})
    except HTTPError as error:
        assert error.code == 416
        # Starlette 0.41.3 omette "bytes " in questa sola risposta di errore.
        assert error.headers['Content-Range'] in {f'bytes */{total}', f'*/{total}'}
    else:
        raise AssertionError('416 mancante')
    print(path, f'200 completo: {total} byte; Range iniziale/intermedio/suffisso 206 esatti; 416; URL LAN')
for path, code in [('/search?q=', 422), ('/search?q=test&limit=21', 422), ('/video/999999999', 404)]:
    try:
        get(path)
    except HTTPError as error:
        assert error.code == code
    else:
        raise AssertionError(path)
print('Errori 422/404 verificati')
for host, ports in [(LAN_HOST, [5432, 6333, 6334]), ('127.0.0.1', [8000])]:
    for port in ports:
        try:
            with socket.create_connection((host, port), timeout=2):
                pass
        except OSError:
            print(host, port, 'non raggiungibile dal server (atteso)')
        else:
            raise AssertionError((host, port))
for port in [5432, 6333]:
    with socket.create_connection(('127.0.0.1', port), timeout=2):
        pass
print('PostgreSQL/Qdrant raggiungibili su loopback')
