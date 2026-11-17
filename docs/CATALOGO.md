> Documentazione tecnica adattata per la distribuzione indipendente. Gli indirizzi `192.0.2.*` e `198.51.100.*` sono esempi non operativi: sostituirli con quelli della propria rete. Per una nuova installazione seguire prima il [README](../README.md); `compose.yaml` è locale, generato da `compose.example.yaml`. Le prove storiche non certificano una nuova installazione.

# Catalogo completo e ricerca semantica

Aprire http://192.0.2.10:8000 e premere **Mostra tutti gli episodi**, accanto al campo di ricerca. Il catalogo mostra il totale PostgreSQL e, per ciascun episodio, ID, titolo, descrizione quando presente e **Riproduci video** solo se il file è disponibile. Altrimenti indica **Video non disponibile**. **Torna alla ricerca** riapre il campo con la domanda conservata; premere Cerca per una nuova ricerca.

## Due viste con scopi diversi

| | Catalogo completo | Ricerca semantica |
|---|---|---|
| Origine | Tutte le righe della tabella PostgreSQL `episodes` | Embedding della domanda, indice Qdrant e metadati PostgreSQL |
| Include record manuali non indicizzati | Sì | Solo se presenti nell'indice, nessuna indicizzazione automatica |
| Ordine | ID decrescente | Affinità semantica dei frammenti, raggruppati per episodio |
| Numero mostrato | Totale esatto SQL, anche senza video | Numero di risultati della domanda, con limite |
| Modello di embedding | Non utilizzato | Caricato alla prima ricerca e riutilizzato dalla cache in memoria |

Il catalogo è una lettura del catalogo autorevole SQL. Qdrant è un indice derivato per trovare contenuti pertinenti; non rappresenta necessariamente tutti gli episodi. Un eventuale record manuale rimane nel catalogo anche senza embedding. Il percorso video non viene inventato: se il file manca, la vista lo segnala. I record e i media delle prove storiche non sono distribuiti.

## Ordine e paginazione

Lo schema reale ha `id BIGINT` identity, chiave primaria, e `created_at` nullable con default CURRENT_TIMESTAMP. Quest'ultima descrive l'inserimento SQL, non una data di pubblicazione verificata dei video; non è stata certificata la provenienza delle date dei record manuali/importati. Si usa quindi **ID decrescente**, senza inventare una cronologia editoriale. Indica gli ID assegnati più recentemente, non l'ultima modifica o la data originale del video. Nessun dato o schema è stato modificato per aggiungere questa funzione.

`GET /episodes?limit=20` legge la prima pagina; la risposta contiene `total`, `episodes` e `next_before_id`. Se il cursore è presente, `GET /episodes?limit=20&before_id=ID` legge gli episodi con ID minore. I valori dei parametri SQL sono separati dal testo delle query, con placeholder `%s`. FastAPI valida `limit` fra 1 e 100 e il cursore nel dominio positivo BIGINT. Parametri non validi producono 422; errori SQL producono 503 con un messaggio italiano senza dettagli interni.

La pagina legge al massimo `limit + 1` righe e sfrutta la chiave primaria per `WHERE id < ... ORDER BY id DESC`: evita OFFSET e il costo di scartare tutte le righe delle pagine precedenti. Il browser conserva i cursori per Pagina precedente/Pagina successiva e mostra 20 episodi per pagina. Il totale esatto usa COUNT(*), che richiede comunque lavoro proporzionale alla dimensione del catalogo: non è un conteggio stimato né una cache. Non è stata effettuata una prova di carico con molti episodi.

Totale e pagina sono letti nella stessa transazione REPEATABLE READ READ ONLY. Ogni richiesta successiva legge una nuova fotografia: nuovi ID compariranno riaprendo il catalogo dalla prima pagina; eventuali modifiche contemporanee possono cambiare totale e contenuto tra pagine. Le pagine non costituiscono uno snapshot persistente dell'intero catalogo.

## Indipendenza e sicurezza

L'endpoint del catalogo non chiama Qdrant, ricerca o modello. È stato eliminato il caricamento obbligatorio del modello all'avvio web: avviene al primo uso della ricerca semantica. Questa prima ricerca può quindi essere più lenta. Il controllo `/health` continua a verificare SQL e Qdrant; un problema Qdrant può farlo risultare unhealthy pur lasciando utilizzabile il catalogo SQL.

I link sono relativi, ad esempio `/video/2`, e riusano l'endpoint video esistente con supporto HTTP Range. I percorsi vengono controllati con `safe_video`, sia per creare il link sia quando viene richiesto il video: file assenti, traversal e symlink esterni restano rifiutati. Se un file scompare dopo il caricamento della pagina, il link può restituire 404. I percorsi locali non vengono restituiti dall'API. Titoli e descrizioni vengono inseriti nel DOM con `textContent`.

Restano validi il filtro IP della LAN, Uvicorn senza fiducia negli header proxy, i mount video in sola lettura e il binding web `192.0.2.10:8000`. SQL e Qdrant rimangono solo su loopback. Il catalogo amplia la visibilità a tutti i record SQL: in assenza di autenticazione, tutti i client della LAN autorizzata possono consultarli. Per limiti firewall e rischi HTTP vedere [ACCESSO_LAN.md](ACCESSO_LAN.md).

## Test ripetibili senza reindicizzazione

```bash
cd /percorso/storycast-ai-qdrant
docker compose run --rm --no-deps -e WEB_ALLOWED_NETWORKS= web pytest -o addopts= -q tests/test_unit.py tests/test_catalog.py tests/test_catalog_sql.py
python3 scripts/smoke.py
python3 scripts/verify_lan.py
```

Il container temporaneo di test non pubblica porte; la variabile vuota serve al TestClient interno e non cambia il filtro del servizio web attivo. I test SQL fanno solo letture e sostituiscono modello/Qdrant/indicizzatore con funzioni che sollevano errore se chiamate dal catalogo. Confrontano tutti gli episodi reali, inclusi quelli senza associazione in `episode_sources`, e percorrono pagine di 1, 2 e 100 elementi. Verificano anche descrizioni, link autorizzati, ultimo cursore, parametri invalidi, catalogo vuoto simulato e indisponibilità SQL simulata. Non eseguire tutta la suite d'integrazione per questo controllo: il vecchio test `test_reindex_idempotent` riesegue intenzionalmente l'indicizzazione.

## Controllo finale nel browser Windows

1. Aprire http://192.0.2.10:8000 e premere Mostra tutti gli episodi, anche senza compilare la domanda. Controllare totale 5, ordine ID 5 → 1 e presenza di «Docker: le basi» con Video non disponibile (situazione osservata durante l'intervento).
2. Aprire Riproduci video, avviare il playback e spostarsi nella riproduzione. Nei dettagli Rete di F12 verificare URL sull'IP LAN e richieste Range/risposte 206.
3. Premere Torna alla ricerca e cercare «Come isolare applicazioni con i container?» e «Come orchestrare un cluster di pod?». Controllare risultati e video; attendere il caricamento del modello alla prima ricerca.
4. Con il catalogo attuale di cinque episodi, i pulsanti pagina sono disabilitati: la paginazione su più pagine è stata verificata tramite API con limiti 1 e 2, senza aggiungere dati fittizi alla produzione.

Queste verifiche grafiche e il playback da Windows non sono stati eseguiti su Windows durante l'intervento.

## Applicazione e copia precedente

Dopo build e test è stato ricreato esclusivamente web con `docker compose up -d --no-deps --no-build --pull never --force-recreate web`. Nessuna indicizzazione, modifica al progetto Storycast originale, cancellazione di volumi o riavvio di PostgreSQL/Qdrant/altri servizi/llama.cpp. Copie dei due sorgenti web precedenti e del Compose in `backups/catalog/`; il Compose non è stato modificato da questa funzionalità.

Una prova automatizzata con Chrome headless su server ha verificato click, catalogo, pagine avanti/indietro e ritorno alla ricerca. Per esercitare tre pagine con soli cinque episodi, la sessione diagnostica ha richiesto pagine da due tramite fetch; il valore dell’interfaccia in produzione resta 20. Non è una prova da Windows né una verifica del playback grafico.
