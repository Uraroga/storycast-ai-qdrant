> Documentazione tecnica adattata per la distribuzione indipendente. Gli indirizzi `192.0.2.*` e `198.51.100.*` sono esempi non operativi: sostituirli con quelli della propria rete. Per una nuova installazione seguire prima il [README](../README.md); `compose.yaml` è locale, generato da `compose.example.yaml`. Le prove storiche non certificano una nuova installazione.

# Prontuario: comandi, effetti e verifiche

Eseguire dalla directory del progetto. Non usare comandi di rimozione volumi. La colonna «verifica» indica cosa osservare; non è necessario leggere i segreti. I comandi Docker riguardano solo questo progetto, salvo la consultazione globale esplicitamente indicata.

| Comando | Funzione ed effetti | Verifica |
|---|---|---|
| `pwd` | Stampa la directory corrente, nessuna modifica. | Deve terminare in `storycast-ai-qdrant`. |
| `ls -la` | Elenca anche file nascosti; non legge il contenuto di `.env`. | Presenza di Compose, sorgenti e docs. |
| `docker compose ps` | Legge stato e porte dei servizi. | PostgreSQL e web healthy; Qdrant running. |
| `docker ps --format '{{.Names}} {{.Status}}'` | Osserva tutti i container, nessuna modifica. | Gli altri progetti continuano a funzionare. |
| `docker compose config --quiet` | Valida Compose senza stampare valori delle credenziali. | Codice di uscita zero. |
| `docker compose up -d --no-recreate postgres qdrant` | Avvia i servizi mancanti e conserva i container esistenti; crea rete/volumi se assenti. | `docker compose ps`. Non applica modifiche di configurazione ai container già presenti. |
| `docker compose build web` | Costruisce l'immagine applicativa; scarica pacchetti nei layer Docker, nessun pacchetto host. | Build completata, immagine `storycast-search:1.0`. |
| `docker compose run --rm --no-deps indexer` | Crea un container temporaneo; scarica/cache modello; aggiunge la tabella di mapping, importa e aggiorna episodi e punti. Il container viene rimosso, i volumi restano. | Log con ID e frammenti; ricerche disponibili. PostgreSQL e Qdrant devono già essere avviati. |
| `docker compose up -d --no-deps web` | Avvia o aggiorna soltanto il web, senza riavviare DB/Qdrant. | HTTP locale e healthcheck. |
| `curl -fsS http://192.0.2.10:8000/health` | Legge stato SQL/Qdrant tramite web, non modifica dati. | JSON `status: ok`. |
| `curl -fsS --get --data-urlencode 'q=Come isolare applicazioni?' http://192.0.2.10:8000/search` | Calcola una query locale e legge i risultati. | Titoli, descrizioni, punteggi e link video nel JSON. |
| `curl -fsS http://127.0.0.1:6333/collections` | Legge le collection Qdrant. | `storycast_e5_small_v1` dopo l'indicizzazione. |
| `docker compose logs --tail=100 web` | Legge ultimi log; non modifica dati. | Avvio completato, richieste HTTP, eventuali errori. |
| `docker compose logs --tail=100 postgres qdrant` | Legge log dei due servizi. | Servizi pronti, nessun errore di storage. |
| `docker compose run --rm --no-deps -e WEB_ALLOWED_NETWORKS= indexer pytest -o addopts= -m integration -q` | Esegue solo i test marcati integration; reindicizza davvero i dialoghi con stessi ID. | Tutti i test passano; non usare se un'altra persona sta modificando i dialoghi. |
| `docker compose run --rm --no-deps indexer pytest -q tests/test_unit.py` | Esegue solo test isolati, senza scrivere nei database. | I test isolati passano. |
| `docker compose exec -T postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT id,title FROM episodes ORDER BY id"'` | Legge gli episodi; variabili risolte dentro il container, password non stampata. | ID 1 e dialoghi importati. |
| `docker compose exec -T postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT * FROM episode_sources ORDER BY source_key"'` | Legge le associazioni e il completamento dell'indice. | Un ID per sorgente, `indexed_at` valorizzato. |
| `docker stats --no-stream` | Fotografia dei consumi di tutti i container. | Limiti applicativi e RAM utilizzata. |
| `python3 scripts/smoke.py` | Interroga il web reale su `127.0.0.1:8000` (oppure `STORYCAST_URL`), cerca Docker/Kubernetes e legge 100 byte di ciascun video campione; non scrive dati. Richiede i dialoghi originali dimostrativi. | Messaggio finale di successo, HTTP 206 per i video. |
| `./scripts/backup.sh` | Blocca gli indicizzatori cooperativi, salva dump SQL e snapshot Qdrant con checksum, poi rilascia il lock. Non arresta servizi. | Percorso stampato, file `SHA256SUMS`. |
| `./scripts/verify-restore.sh backups/NOME_CARTELLA` | Verifica checksum, crea un progetto isolato, importa realmente dump e snapshot, confronta conteggi, arresta copie; conserva i volumi di prova. | Messaggio di successo e nome del progetto isolato. |
| `docker compose stop web` | Arresta il solo web; preserva tutti i dati. | Web stopped e DB/Qdrant attivi. |
| `docker compose stop` | Arresta i servizi di questo progetto, mai quelli degli altri progetti. Interrompe la demo. | Servizi stopped; volumi presenti. Eseguire solo quando si desidera arrestarla. |
| `docker compose start postgres qdrant web` | Riavvia container già creati con la loro configurazione corrente. | Servizi running/healthy; non esegue l'indicizzatore. |

## Da un'altra macchina

`ssh -N -L 8000:192.0.2.10:8000 utente@server` apre un tunnel SSH senza shell remota: la porta 8000 del proprio computer inoltra a quella LAN di server. Non cambia Compose e non espone pubblicamente il servizio. Verificare aprendo `http://127.0.0.1:8000`; chiudere il tunnel con Ctrl+C.

## Nuova Ubuntu: preparazione

Consultare la [procedura ufficiale Docker per Ubuntu](https://docs.docker.com/engine/install/ubuntu/) per installare Engine e plugin Compose compatibili con la distribuzione. Non installare Python applicativo sull'host.

| Comando | Effetto | Verifica |
|---|---|---|
| `cp -n .env.example .env` | Crea il file credenziali solo se assente; usarlo esclusivamente nella nuova copia e verificare il file prima di configurarlo. | File presente; modificarlo con un editor prima del primo avvio. |
| `chmod 600 .env` | Limita lettura/scrittura al proprietario. | `ls -la` mostra `-rw-------`. |
| `chmod 700 backups` | Limita l'accesso alla directory dei backup. | Permessi `drwx------`. |

Impostare in `.env` una password casuale lunga e `STORYCAST_ROOT` sulla directory contenente `input/` e `output/` (default dimostrativo `./local/storycast`). Copiare anche input e video con strumenti di trasferimento sicuri. L'utente UID 10001 deve poter leggere file e attraversare directory. Poi seguire i comandi di avvio sopra, nello stesso ordine.

Le variabili `POSTGRES_*` inizializzano un volume nuovo: cambiarle nel file **non** cambia automaticamente utenti e password di un database esistente. Non stampare `docker compose config` senza `--quiet`, perché risolverebbe anche i segreti.

## Note operative

Le verifiche includono anche `bash -n scripts/backup.sh scripts/verify-restore.sh`: controlla la sintassi degli script senza eseguirli e senza scrivere dati; il successo è un codice di uscita zero.

`docker compose run --rm --no-deps indexer python -m pip check` controlla che le versioni dei pacchetti installati siano compatibili fra loro: crea soltanto un container temporaneo, senza installare pacchetti. Il risultato atteso è `No broken requirements found`.

`docker compose run --rm --no-deps -e HF_HUB_OFFLINE=1 indexer python -c 'from app.core import model; print(model().get_sentence_embedding_dimension())'` prova il caricamento dalla cache senza accesso a Hugging Face. Non modifica SQL/Qdrant; può leggere o aggiornare metadati di cache. Il risultato atteso è `384`, dopo un primo download completo.

## Configurazione pubblica e test

Per una nuova installazione copiare senza sovrascrivere `compose.example.yaml` in `compose.yaml` e configurare `.env` seguendo il README. Lo schema base è in `initdb/001-episodes.sql`, applicato soltanto ai volumi nuovi. Gli indirizzi LAN qui usati sono esempi; il default pubblico è loopback. La suite predefinita esclude `integration`; usare `docker compose run --rm --no-deps -e WEB_ALLOWED_NETWORKS= indexer pytest -q` per i soli test isolati. I test SQL reali richiedono `-o addopts=` se selezionati esplicitamente.
