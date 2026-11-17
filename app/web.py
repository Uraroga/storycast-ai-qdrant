import logging
import os
from ipaddress import ip_address, ip_network
from pathlib import Path
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse
from app.core import db, qdrant, search, safe_video

logger = logging.getLogger(__name__)

# Il modello viene caricato da search() solo alla prima ricerca semantica.
app = FastAPI()


class NetworkAccess:
    """Controlla il peer TCP reale; Uvicorn deve ignorare gli header proxy."""

    def __init__(self, app):
        self.app = app
        self.networks = tuple(ip_network(value.strip()) for value in
                              os.environ.get('WEB_ALLOWED_NETWORKS', '').split(',') if value.strip())

    async def __call__(self, scope, receive, send):
        if scope['type'] == 'http' and self.networks:
            try:
                peer = ip_address(scope['client'][0])
            except (ValueError, TypeError, KeyError):
                peer = None
            if peer is None or not any(peer in network for network in self.networks):
                response = PlainTextResponse('Accesso consentito solo dalla LAN autorizzata', status_code=403)
                return await response(scope, receive, send)
        await self.app(scope, receive, send)


app.add_middleware(NetworkAccess)

@app.get('/')
def home():
    return FileResponse(Path(__file__).with_name('index.html'))

@app.get('/health')
def health():
    try:
        with db() as conn:
            conn.execute('SELECT 1')
        qdrant().get_collections()
        return {'status': 'ok'}
    except Exception:
        logger.exception('Healthcheck fallito')
        raise HTTPException(503, 'Dipendenza non disponibile')

@app.get('/search')
def find(q: str = Query(min_length=1, max_length=1000), limit: int = Query(default=5, ge=1, le=20)):
    if not q.strip():
        raise HTTPException(422, 'Scrivere una domanda')
    try:
        return {'results': search(q.strip(), limit)}
    except Exception:
        logger.exception('Ricerca fallita')
        raise HTTPException(503, 'Ricerca non disponibile; controllare servizi e indice')


@app.get('/episodes')
def episodes(limit: int = Query(default=20, ge=1, le=100),
             before_id: int | None = Query(default=None, ge=1, le=9223372036854775807)):
    """Catalogo SQL completo: cursore sulla chiave primaria, nessun embedding."""
    try:
        with db() as conn:
            # Totale e pagina appartengono alla stessa fotografia del catalogo.
            conn.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
            total = conn.execute('SELECT count(*) AS total FROM episodes').fetchone()['total']
            if before_id is None:
                rows = conn.execute(
                    'SELECT id,title,description,video_path FROM episodes ORDER BY id DESC LIMIT %s',
                    (limit + 1,)).fetchall()
            else:
                rows = conn.execute(
                    'SELECT id,title,description,video_path FROM episodes WHERE id < %s ORDER BY id DESC LIMIT %s',
                    (before_id, limit + 1)).fetchall()
        has_more = len(rows) > limit
        items = rows[:limit]
        for row in items:
            row['video_url'] = f'/video/{row["id"]}' if safe_video(row.pop('video_path')) else None
        return {'total': total, 'episodes': items,
                'next_before_id': items[-1]['id'] if has_more else None}
    except Exception:
        logger.exception('Catalogo SQL non disponibile')
        raise HTTPException(503, 'Catalogo non disponibile; controllare PostgreSQL')

@app.get('/video/{episode_id}')
def video(episode_id: int):
    with db() as conn:
        row = conn.execute('SELECT video_path FROM episodes WHERE id=%s', (episode_id,)).fetchone()
    path = safe_video(row['video_path']) if row else None
    if not path:
        raise HTTPException(404, 'Video non disponibile')
    return FileResponse(path, media_type='video/mp4' if path.suffix == '.mp4' else 'video/webm')
