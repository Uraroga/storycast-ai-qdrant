"""Catalogo SQL e indice derivato: PostgreSQL resta la fonte autorevole."""
import os
import re
import uuid
from pathlib import Path
from functools import lru_cache
import psycopg
from psycopg.rows import dict_row
from qdrant_client import QdrantClient, models

MODEL = 'intfloat/multilingual-e5-small'
REVISION = os.environ.get('MODEL_REVISION', '')
COLLECTION = 'storycast_e5_small_v1'
DIMENSION = 384
SOURCE = Path('/storycast/input')
MEDIA = Path('/storycast/output')


def db():
    return psycopg.connect(host='postgres', dbname=os.environ['POSTGRES_DB'],
                          user=os.environ['POSTGRES_USER'], password=os.environ['POSTGRES_PASSWORD'],
                          connect_timeout=5, row_factory=dict_row)


def qdrant():
    return QdrantClient(url='http://qdrant:6333', timeout=30)


def migrate(conn):
    # Tabella separata: nessuna modifica alle colonne o ai record preesistenti.
    conn.execute('''CREATE TABLE IF NOT EXISTS episode_sources (
        source_key TEXT PRIMARY KEY,
        episode_id BIGINT UNIQUE NOT NULL REFERENCES episodes(id),
        indexed_at TIMESTAMPTZ
    )''')


@lru_cache(maxsize=1)
def model():
    from sentence_transformers import SentenceTransformer
    if not REVISION:
        raise RuntimeError('MODEL_REVISION obbligatoria')
    return SentenceTransformer(MODEL, revision=REVISION, device='cpu')


def encode(texts, prefix):
    return model().encode([prefix + t for t in texts], normalize_embeddings=True,
                          batch_size=8, show_progress_bar=False).tolist()


def ensure_collection(client):
    if not client.collection_exists(COLLECTION):
        client.create_collection(COLLECTION, vectors_config=models.VectorParams(
            size=DIMENSION, distance=models.Distance.COSINE))
    vectors = client.get_collection(COLLECTION).config.params.vectors
    if not isinstance(vectors, models.VectorParams) or vectors.size != DIMENSION or vectors.distance != models.Distance.COSINE:
        raise RuntimeError('Collection incompatibile: nessuna ricreazione automatica')


def clean_dialogue(raw):
    return '\n'.join(line.strip() for line in raw.splitlines()
                     if line.strip() and not re.fullmatch(r'\s*\[[^\]]+\]\s*', line))


def chunks(text):
    # Finestre di token reali: nessun troncamento silenzioso dei dialoghi lunghi.
    tokenizer = model().tokenizer
    tokens = tokenizer.encode(text, add_special_tokens=False, truncation=False, verbose=False)
    return [tokenizer.decode(tokens[i:i+420], skip_special_tokens=True)
            for i in range(0, len(tokens), 360)]


def safe_video(relative):
    if not relative:
        return None
    path = (MEDIA / relative).resolve()
    if path.is_relative_to(MEDIA.resolve()) and path.is_file() and path.suffix.lower() in {'.mp4', '.webm'}:
        return path
    return None


def import_dialogues():
    client = qdrant()
    model()  # Caricamento e verifica dimensione PRIMA della creazione collection.
    if model().get_sentence_embedding_dimension() != DIMENSION:
        raise RuntimeError('Dimensione modello inattesa')
    count = 0
    with db() as conn:
        # Lock per tutta la sessione: impedisce indicizzatori concorrenti.
        conn.execute('SELECT pg_advisory_lock(839401)')
        ensure_collection(client)
        migrate(conn)
        conn.commit()
        for path in sorted(SOURCE.glob('*.txt')):
            if path.is_symlink() or path.stem.upper().startswith('MODELLO'):
                continue
            text = clean_dialogue(path.read_text(encoding='utf-8'))
            if not text:
                continue
            key = path.name
            title = path.stem.replace('_', ' ')[:200]
            video_stem = path.stem.removesuffix('-short')
            suffix = '_short_video.mp4' if path.stem.endswith('-short') else '_video.mp4'
            video = f'{video_stem}/{video_stem}{suffix}'
            video = video if safe_video(video) else None
            existing = conn.execute('SELECT episode_id FROM episode_sources WHERE source_key=%s', (key,)).fetchone()
            if existing:
                eid = existing['episode_id']
                conn.execute('UPDATE episodes SET title=%s,description=%s,transcript=%s,video_path=%s WHERE id=%s',
                             (title, text[:350], text, video, eid))
            else:
                eid = conn.execute('INSERT INTO episodes(title,description,transcript,video_path) VALUES (%s,%s,%s,%s) RETURNING id',
                                   (title, text[:350], text, video)).fetchone()['id']
                conn.execute('INSERT INTO episode_sources(source_key,episode_id) VALUES (%s,%s)', (key, eid))
            conn.execute('UPDATE episode_sources SET indexed_at=NULL WHERE episode_id=%s', (eid,))
            conn.commit()  # ID stabile anche se Qdrant fallisce: il prossimo giro ripara.
            parts = chunks(title + '\n' + text)
            vectors = encode(parts, 'passage: ')
            points = [models.PointStruct(id=str(uuid.uuid5(uuid.NAMESPACE_URL, f'storycast:{eid}:{i}')),
                                         vector=v, payload={'episode_id': eid, 'chunk': i,
                                                            'model_revision': REVISION})
                      for i, v in enumerate(vectors)]
            client.upsert(COLLECTION, points=points, wait=True)
            # Rimuove solo i frammenti obsoleti dello stesso episodio, dopo l'upsert.
            client.delete(COLLECTION, points_selector=models.FilterSelector(filter=models.Filter(must=[
                models.FieldCondition(key='episode_id', match=models.MatchValue(value=eid)),
                models.FieldCondition(key='chunk', range=models.Range(gte=len(parts)))
            ])), wait=True)
            conn.execute('UPDATE episode_sources SET indexed_at=now() WHERE episode_id=%s', (eid,))
            conn.commit()
            print(f'Indicizzato episode_id={eid}: {len(parts)} frammenti', flush=True)
            count += 1
    return count


def search(query, limit=5):
    client = qdrant()
    if not client.collection_exists(COLLECTION):
        return []
    vector = encode([query], 'query: ')[0]
    # group_by restituisce episodi distinti anche con molti frammenti.
    groups = client.query_points_groups(COLLECTION, query=vector, group_by='episode_id',
                                        group_size=1, limit=limit).groups
    result = []
    with db() as conn:
        for group in groups:
            row = conn.execute('SELECT id,title,description,video_path FROM episodes WHERE id=%s', (int(group.id),)).fetchone()
            if row:
                row['score'] = group.hits[0].score
                row['video_url'] = f'/video/{row["id"]}' if safe_video(row.pop('video_path')) else None
                result.append(row)
    return result
