"""Verifica HTTP della demo in esecuzione; solo libreria standard, nessuna scrittura."""
import json
import os
from urllib.request import Request, urlopen

BASE = os.environ.get('STORYCAST_URL', 'http://127.0.0.1:8000').rstrip('/')

def get(path, headers=None):
    return urlopen(Request(BASE + path, headers=headers or {}), timeout=30)

with get('/') as response:
    assert response.status == 200 and b'Storycast' in response.read()
with get('/health') as response:
    assert json.load(response)['status'] == 'ok'
from urllib.parse import urlencode
for query, topic in [('Come isolare applicazioni con i container?', 'docker'),
                     ('Come orchestrare un cluster di pod?', 'kubernetes')]:
    with get('/search?' + urlencode({'q': query})) as response:
        hits = json.load(response)['results']
    assert hits and topic in hits[0]['title'].lower()
    print(f'Ricerca {topic}: primo risultato {hits[0]["title"]}, score={hits[0]["score"]:.4f}')
    video = next(hit['video_url'] for hit in hits if hit['video_url'])
    with get(video, {'Range': 'bytes=0-99'}) as response:
        assert response.status == 206 and len(response.read()) == 100
        print('Video: HTTP 206, 100 byte ricevuti')
print('Smoke test HTTP completato: home, health, ricerche e video corretti')
