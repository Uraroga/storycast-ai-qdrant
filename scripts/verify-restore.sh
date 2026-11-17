#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export BACKUP_DIR=$(realpath "${1:?Uso: scripts/verify-restore.sh backups/cartella}")
(cd "$BACKUP_DIR" && sha256sum -c SHA256SUMS)
project="storycast-restore-$(date +%s)-$$"
compose=(docker compose -p "$project" -f compose.restore.yaml)
trap '"${compose[@]}" stop >/dev/null; echo "Copia di verifica arrestata; volumi conservati. Progetto: $project"' EXIT
"${compose[@]}" up -d
ready=false
for i in {1..60}; do
  if "${compose[@]}" exec -T postgres sh -c 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"' >/dev/null 2>&1; then ready=true; break; fi
  sleep 1
done
[[ "$ready" == true ]]
"${compose[@]}" exec -T postgres sh -c 'pg_restore --exit-on-error --no-owner -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < "$BACKUP_DIR/postgres.dump"
actual=$("${compose[@]}" exec -T postgres sh -c 'psql -qAt -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT count(*) FROM episodes"')
[[ "$actual" == "$(cat "$BACKUP_DIR/episodes.count")" ]]
fingerprint=$("${compose[@]}" exec -T postgres sh -c 'psql -qAt -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT md5(coalesce(jsonb_agg(to_jsonb(e) ORDER BY id)::text, chr(32))) FROM episodes e; SELECT md5(coalesce(jsonb_agg(to_jsonb(s) ORDER BY source_key)::text, chr(32))) FROM episode_sources s"')
[[ "$fingerprint" == "$(cat "$BACKUP_DIR/sql.fingerprint")" ]]
# Nessuna porta pubblicata: interrogazione attraverso la rete Docker isolata.
docker run --rm --user 0 --network "${project}_default" --mount "type=bind,src=$BACKUP_DIR,dst=/backup,readonly" --entrypoint python storycast-search:1.0 -c '
import json,time,urllib.request
from pathlib import Path
for attempt in range(60):
    try:
        data=json.load(urllib.request.urlopen("http://qdrant:6333/collections/storycast_e5_small_v1"))
        assert data["result"]["points_count"] == int(Path("/backup/points.count").read_text())
        from qdrant_client import QdrantClient
        client = QdrantClient(url="http://qdrant:6333")
        points, _ = client.scroll("storycast_e5_small_v1", limit=1, with_vectors=True)
        if points:
            hits = client.query_points("storycast_e5_small_v1", query=points[0].vector, limit=1).points
            assert hits and hits[0].score > 0.99
        print("Qdrant: conteggio e ricerca vettoriale sullo snapshot ripristinato corretti")
        break
    except (OSError, AssertionError):
        time.sleep(1)
else:
    raise RuntimeError("Ripristino Qdrant non verificato")
'
printf 'Ripristino verificato: %s episodi; nessuna modifica ai dati originali.\n' "$actual"
