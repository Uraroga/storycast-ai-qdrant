> Documentazione tecnica adattata per la distribuzione indipendente. Gli indirizzi `192.0.2.*` e `198.51.100.*` sono esempi non operativi: sostituirli con quelli della propria rete. Per una nuova installazione seguire prima il [README](../README.md); `compose.yaml` è locale, generato da `compose.example.yaml`. Le prove storiche non certificano una nuova installazione.

# Corso progressivo sul codice realizzato

Tutti i comandi citati si trovano con effetti e verifiche in COMANDI.md. Gli esercizi che scrivono sui servizi sono esplicitamente indicati; svolgerli dopo un backup, preferibilmente su una copia.

## 1 — Dal processo al servizio

Leggere `compose.yaml`. Individuare immagine, porte e volumi di PostgreSQL. Un servizio è una dichiarazione; il container è la sua esecuzione concreta. L'immagine contiene il software, il volume i dati modificabili. Le risorse del container sono limitate, ma il kernel è quello dell'host.

Esercizio di sola lettura: osservare `docker compose ps`. Spiegare perché le porte pubblicate iniziano con 127.0.0.1 e perché i container comunicano anche senza quelle porte.

## 2 — Costruire Python senza installarlo sull'host

Leggere Dockerfile e i due file delle dipendenze. `FROM` sceglie la base, `COPY` trasferisce file nel contesto dell'immagine, `RUN` installa durante la build, `CMD` sceglie il processo di avvio. `USER` limita i privilegi. Un digest identifica il contenuto dell'immagine; un tag può invece cambiare.

Esercizio: eseguire la build come nel prontuario e riconoscere i layer riutilizzati. La build non modifica i dati PostgreSQL. La cache dei layer Docker è distinta dal volume di cache del modello.

## 3 — Comprendere SQL e le chiavi

Leggere `db()` e `migrate()` in core.py. Una connessione apre una sessione; `commit()` rende persistenti le modifiche. `episodes.id` è una chiave primaria generata da PostgreSQL. `episode_sources.episode_id` è una chiave esterna; `source_key` è un nome sorgente univoco.

Esercizio di sola lettura: interrogare entrambe le tabelle con i comandi documentati. Spiegare perché l'ID 1 non viene sovrascritto e perché la query SQL usa `%s` invece di concatenare stringhe. I parametri evitano di trattare input utente come codice SQL.

## 4 — Estrarre il testo utile

Leggere `clean_dialogue()`. I marcatori `[personaggio|tono]` descrivono la recitazione; vengono esclusi dagli embedding. Le battute restano nell'ordine originale. Il parser accetta il formato effettivamente trovato, senza fingere di leggere trascrizioni JSON o file video.

Esercizio senza database: eseguire i test unitari. Individuare un esempio di marcatore rimosso e uno di frase mantenuta. Discutere perché vanno esclusi i file modello.

## 5 — Dai token agli embedding

Leggere `model()`, `chunks()` ed `encode()`. I token sono unità del tokenizer, non necessariamente parole. Un embedding è un vettore numerico appreso: testi simili tendono a stare vicini nello spazio. La normalizzazione porta il vettore a lunghezza unitaria; il coseno confronta la direzione.

Esercizio: leggere il test sul testo lungo. Spiegare come finestre sovrapposte mantengono il contesto ai bordi e perché non basta passare l'intero episodio a un modello con limite 512 token.

## 6 — Identità, ripetibilità e guasti

Seguire `import_dialogues()`. PostgreSQL assegna l'ID; il nome file permette di ritrovarlo. Ogni frammento ottiene un UUID deterministico basato su episodio e posizione. L'upsert aggiorna se il punto esiste e inserisce altrimenti. I frammenti oltre la nuova lunghezza vengono rimossi solo per quell'episodio.

Esercizio con scritture idempotenti: eseguire il test di reindicizzazione. I conteggi e gli ID devono restare uguali. Spiegare cosa succede se Qdrant non risponde dopo il commit SQL: non c'è rollback comune a due database, ma un nuovo giro ripara l'indice.

## 7 — Ricerca e API

Leggere `search()` e `app/web.py`. Il browser invia una domanda; Python calcola `query: ...`, Qdrant trova i gruppi per episode_id, PostgreSQL fornisce titoli e descrizioni. La ricerca è diversa da una query `LIKE`: cerca affinità di significato, non soltanto coincidenza di caratteri.

Esercizio di lettura: cercare prima «isolare applicazioni», poi «gestire pod». Annotare il primo risultato e confrontarlo con i dialoghi. Provare una domanda fuori tema e spiegare perché il motore restituisce comunque i più vicini.

## 8 — Interfaccia e file locali

Leggere index.html e `safe_video()`. `textContent` visualizza il testo senza interpretarlo come HTML. Il server offre un video tramite ID SQL, non accetta un percorso libero dal browser. `resolve()` e il controllo del prefisso della directory impediscono di attraversare cartelle o seguire symlink esterni.

Esercizio: leggere il test sui percorsi e quello HTTP Range. Spiegare perché un video deve supportare richieste parziali per permettere la navigazione nel lettore.

## 9 — Osservabilità e risorse

Leggere gli healthcheck e i limiti di Compose. `pg_isready` verifica il server PostgreSQL; `/health` verifica SQL e Qdrant, mentre il modello viene caricato alla prima ricerca. I log mostrano eventi, stats mostra consumi. Healthy non significa che ogni ricerca sia corretta.

Esercizio di sola lettura: osservare log e stats con il prontuario. Distinguere limite RAM, RAM osservata, memoria del modello e spazio disco della cache.

## 10 — Backup e prova del ripristino

Leggere entrambi gli script e compose.restore.yaml. Un dump logico PostgreSQL è diverso da una copia dei file live di un volume. Qdrant fornisce uno snapshot della collection. SHA-256 rileva alterazioni dei file; importare in una copia prova che il formato sia utilizzabile.

Esercizio con nuove copie persistenti: effettuare backup e verifica. Annotare nome del progetto isolato e risultato. Spiegare che i conteggi non dimostrano l'integrità di tutti i contenuti e che i video vanno salvati separatamente.

## 11 — Ricostruzione e sicurezza

Seguire la sezione nuova Ubuntu della guida, prima su carta. Elencare prerequisiti, sorgenti, credenziali, modello, volumi e versioni. Nessun comando deve stampare password o eliminare dati. Modificare `.env` non reinizializza un database esistente.

Esercizio finale: spiegare a un'altra persona l'intero viaggio di una domanda, dal browser al risultato e al video. Poi rispondere alle domande in DOMANDE.md senza consultare il codice, verificando infine ogni risposta.
