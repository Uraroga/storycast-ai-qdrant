# Storycast AI Qdrant

Catalogo e ricerca semantica locale dei dialoghi di **Storycast**, con interfaccia web in italiano e riproduzione dei video già generati. Il progetto è indipendente da [Uraroga/storycast-docker](https://github.com/Uraroga/storycast-docker): ne legge `input/` e `output/` in sola lettura, senza modificare il generatore originale. Può usare anche una directory autonoma con lo stesso formato. Non genera video, non trascrive audio e non produce risposte con un LLM.

## Architettura

| Servizio | Ruolo |
|---|---|
| PostgreSQL | Fonte autorevole: episodi, testi, percorsi video e associazioni sorgente/ID. |
| Qdrant | Indice derivato `storycast_e5_small_v1`: vettori da 384 dimensioni, distanza coseno. |
| `web` | FastAPI e interfaccia sulla porta **8000**, ricerca, catalogo e streaming video HTTP Range. |
| `indexer` | Importazione manuale dei TXT, embedding CPU e aggiornamento dell'indice; profilo `tools`. |

Il modello è [`intfloat/multilingual-e5-small`](https://huggingface.co/intfloat/multilingual-e5-small), con revisione fissata nel Compose. Usa i prefissi `query: ` e `passage: ` e finestre di 420 token con passo 360. Il primo utilizzo scarica i pesi; l'inferenza successiva è locale. La cache vive in un volume dedicato. Non servono chiavi API né GPU.

La **ricerca semantica** restituisce episodi distinti ordinati per affinità: il punteggio non è una probabilità. **Mostra tutti gli episodi** legge invece l'intero catalogo PostgreSQL, inclusi i record non indicizzati, con totale e paginazione per ID decrescente; funziona senza caricare il modello e senza consultare Qdrant.

## Installazione su Ubuntu

Procedura per una **nuova installazione**, in una directory separata da servizi esistenti. Non copiare questi file sopra un'installazione funzionante. Servono Ubuntu con Docker Engine e plugin Compose, Git, Bash, curl, Python 3 e sha256sum. Installare Docker seguendo la [documentazione ufficiale Ubuntu](https://docs.docker.com/engine/install/ubuntu/). I digest e l'ambiente attuali sono stati usati su Linux amd64; altre architetture non sono verificate. Prevedere diversi GB di disco e RAM: web e indicizzatore possono usare fino a 3 GB ciascuno, oltre ai database.

Per installare il progetto:

```bash
git clone https://github.com/Uraroga/storycast-ai-qdrant.git
cd storycast-ai-qdrant
# Solo nella nuova copia: non sovrascrivere configurazioni esistenti.
cp -n compose.example.yaml compose.yaml
cp -n .env.example .env
chmod 600 .env
mkdir -p local/storycast/input local/storycast/output
```

Modificare `.env` con un editor: sostituire `POSTGRES_PASSWORD` con una password casuale lunga e impostare `STORYCAST_ROOT` sulla directory contenente `input/` e `output/`. Il valore dimostrativo usa `./local/storycast`; è possibile indicare una copia separata dei contenuti. L'UID 10001 del container deve poter leggere i file e attraversare le directory, senza aprire indiscriminatamente i permessi. Il repository non contiene dialoghi o video.

```bash
docker compose config --quiet
docker compose build web
docker compose up -d postgres qdrant
# Attendere che i database siano pronti: consultare ps e log.
docker compose ps
docker compose run --rm --no-deps indexer
docker compose up -d --no-deps web
```

Lo schema `initdb/001-episodes.sql` inizializza **solo un volume PostgreSQL nuovo**. La tabella di mapping viene creata dall'indicizzatore. Non occorre il database di Storycast originale. Cambiare le variabili `POSTGRES_*` non cambia credenziali o schema di un volume già inizializzato. Se le porte 5432, 6333 o 8000 sono occupate, scegliere una macchina isolata o adattare le pubblicazioni prima dell'avvio; non arrestare altri servizi.

Aprire `http://127.0.0.1:8000`. API: `/episodes`, `/search?q=domanda`, `/video/ID`, `/health`; documentazione interattiva FastAPI in `/docs`.

## Indicizzazione manuale e video

Mettere i dialoghi UTF-8 direttamente in `input/*.txt`. I marcatori di riga `[personaggio|tono]`, i template `MODELLO*`, i file vuoti e i symlink sorgente vengono ignorati. La corrispondenza video è:

- `input/esempio.txt` → `output/esempio/esempio_video.mp4`;
- `input/esempio-short.txt` → `output/esempio/esempio_short_video.mp4`.

Eseguire `./aggiorna-storycast.sh` o `docker compose run --rm --no-deps indexer` ogni volta che si aggiornano i testi o si aggiungono video. L'operazione **scrive** su PostgreSQL e Qdrant: riusa ID e UUID dei file già noti. Rinominare un TXT crea una nuova identità; eliminarlo non cancella automaticamente i record. Non c'è un watcher né un'integrazione automatica con il generatore.

I media sono letti in sola lettura; percorsi esterni e symlink che escono dalla directory autorizzata vengono rifiutati. HTTP Range permette lo spostamento nel video, ma non c'è transcodifica: i codec devono essere supportati dal browser.

## Accesso dalla LAN

Il modello pubblico espone il web su loopback. Per una LAN fidata configurare in `.env` `WEB_BIND_IP` con l'IP privato del server e `WEB_ALLOWED_NETWORKS` con loopback più la propria subnet CIDR. Dopo l'applicazione della configurazione sul proprio ambiente, aprire `http://IP_DEL_SERVER:8000`. I link video relativi usano la stessa origine. [Guida LAN e firewall](docs/ACCESSO_LAN.md).

## Test, backup e ripristino

Test isolati, senza collegamenti ai database e senza download del modello:

```bash
docker compose run --rm --no-deps -e WEB_ALLOWED_NETWORKS= indexer pytest -q
```

I test marcati `integration` sono esclusi per impostazione predefinita. `tests/test_catalog_sql.py` fa letture reali; `tests/test_integration.py` include **reindicizzazione con scritture** e richiede uno specifico corpus dimostrativo, non distribuito. Eseguirli solo su un ambiente di prova predisposto, con `pytest -o addopts= -m integration`. Gli script `smoke.py` e `verify_lan.py` dipendono anch'essi da episodi Docker/Kubernetes con video disponibili; non costituiscono un test generico di installazione vuota.

```bash
# Lettura del servizio della propria installazione
curl -fsS http://127.0.0.1:8000/health
# Operazioni amministrative da eseguire quando pianificate
./scripts/backup.sh
./scripts/verify-restore.sh backups/NOME_CARTELLA
```

Il backup crea un dump SQL e uno snapshot Qdrant con checksum, coordinandosi con l'indicizzatore mediante lock. **Crea dati persistenti e uno snapshot nel servizio Qdrant**. Non include sorgenti, video, credenziali o cache: salvarli separatamente. I backup contengono testi riservati; proteggerli e conservarne copie cifrate fuori macchina.

La verifica di ripristino crea database e volumi separati, senza porte host, importa i backup, confronta impronte SQL e conteggi e prova una ricerca vettoriale. Richiede l'immagine applicativa già costruita; arresta le copie e conserva i volumi. Non effettua un ripristino sopra la produzione. Per un recupero reale verificare prima una copia isolata e pianificare il passaggio dei client. [Guida operativa](docs/GUIDA.md) e [comandi](docs/COMANDI.md).

## Limitazioni e sicurezza

Non ci sono login, HTTPS, quote o limiti di frequenza. Tutti i client autorizzati dalla rete possono leggere l'intero catalogo e i video. Non esporre il servizio a Internet o tramite port forwarding. Qdrant non ha autenticazione nella configurazione fornita; PostgreSQL e Qdrant sono pubblicati solo su loopback. Il filtro IP applicativo non sostituisce firewall, autenticazione o isolamento di rete; una lista di reti vuota disabilita il filtro. Uvicorn ignora gli header proxy.

SQL e Qdrant non condividono una transazione: un errore può lasciare l'indice incompleto, riparabile rilanciando l'indicizzatore. Il lock coordina solo gli strumenti cooperanti. `/health` controlla SQL e Qdrant, non la qualità dell'indice. Il catalogo può funzionare anche con Qdrant indisponibile. Non usare `docker compose down -v` sui dati da conservare.

Le dipendenze sono fissate per riproducibilità, ma questo non garantisce assenza di vulnerabilità; prima di un'esposizione più ampia servono audit e aggiornamenti verificati. Non sono certificati carichi elevati, altre architetture o il playback su tutti i browser.

## Documentazione e licenza

[Architettura](docs/ARCHITETTURA.md) · [Catalogo](docs/CATALOGO.md) · [Guida](docs/GUIDA.md) · [Lezioni](docs/LEZIONI.md) · [Domande](docs/DOMANDE.md) · [Verifiche](docs/VERIFICHE.md).

Distribuito con [licenza MIT](LICENSE). Copyright © 2026 Sergio De Rossi (Uraroga). Le licenze di modelli, dipendenze e contenuti restano distinte.
