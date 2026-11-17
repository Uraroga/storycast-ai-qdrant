
#!/usr/bin/env bash
set -e

cd "$(dirname "${BASH_SOURCE[0]}")"

echo "Avvio aggiornamento catalogo Storycast..."

docker compose run --rm --no-deps indexer

echo "Aggiornamento completato con successo!"
