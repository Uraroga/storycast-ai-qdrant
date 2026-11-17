#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
umask 077
folder="backups/$(date -u +%Y%m%dT%H%M%S)-$$"
mkdir -p "$folder"
# Sessione SQL tenuta aperta: stesso lock cooperativo usato dall'indicizzatore.
coproc LOCK { docker compose exec -T postgres sh -c 'exec psql -qAt -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"'; }
lock_in=${LOCK[1]}
lock_out=${LOCK[0]}
lock_pid=$LOCK_PID
trap 'printf "\\q\n" >&"$lock_in" 2>/dev/null || true; wait "$lock_pid" || true' EXIT
printf "SELECT pg_advisory_lock(839401); SELECT 'LOCKED';\n" >&"$lock_in"
locked=false
while IFS= read -r -t 300 line <&"$lock_out"; do
  if [[ "$line" == LOCKED ]]; then locked=true; break; fi
done
[[ "$locked" == true ]] || { echo 'Lock non ottenuto' >&2; exit 1; }
docker compose exec -T postgres sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "$folder/postgres.dump"
snapshot=$(curl -fsS -X POST http://127.0.0.1:6333/collections/storycast_e5_small_v1/snapshots | python3 -c 'import sys,json; print(json.load(sys.stdin)["result"]["name"])')
curl -fsS "http://127.0.0.1:6333/collections/storycast_e5_small_v1/snapshots/$snapshot" -o "$folder/qdrant.snapshot"
docker compose exec -T postgres sh -c 'psql -qAt -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT count(*) FROM episodes"' > "$folder/episodes.count"
curl -fsS http://127.0.0.1:6333/collections/storycast_e5_small_v1 | python3 -c 'import sys,json; print(json.load(sys.stdin)["result"]["points_count"])' > "$folder/points.count"
docker compose exec -T postgres sh -c 'psql -qAt -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT md5(coalesce(jsonb_agg(to_jsonb(e) ORDER BY id)::text, chr(32))) FROM episodes e; SELECT md5(coalesce(jsonb_agg(to_jsonb(s) ORDER BY source_key)::text, chr(32))) FROM episode_sources s"' > "$folder/sql.fingerprint"
cp compose.yaml "$folder/compose.yaml"
(cd "$folder" && sha256sum postgres.dump qdrant.snapshot episodes.count points.count sql.fingerprint compose.yaml > SHA256SUMS)
printf 'Backup completato: %s\n' "$folder"
