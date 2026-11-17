> Documentazione tecnica adattata per la distribuzione indipendente. Gli indirizzi `192.0.2.*` e `198.51.100.*` sono esempi non operativi: sostituirli con quelli della propria rete. Per una nuova installazione seguire prima il [README](../README.md); `compose.yaml` è locale, generato da `compose.example.yaml`. Le prove storiche non certificano una nuova installazione.

# Guida pratica in italiano

Questa estensione legge i dialoghi di Storycast, li cataloga in PostgreSQL e li cerca per significato con Qdrant. Non trascrive audio, non produce video e non modifica il progetto Storycast originale. L’interfaccia è accessibile dalla LAN autorizzata e apre i video già disponibili.

Studiare prima ARCHITETTURA.md, poi seguire LEZIONI.md. COMANDI.md spiega per ogni comando effetti e verifica. VERIFICHE.md registra ciò che è stato realmente provato; DOMANDE.md serve per l'autovalutazione.

## File realizzati

| File | Scopo |
|---|---|
| `compose.yaml` | Configurazione locale ricavata dal modello pubblico; definisce database, web, indexer e cache. Fissa le immagini per digest. |
| `Dockerfile` | Costruisce Python con PyTorch CPU e dipendenze, esegue con utente non root. |
| `requirements.txt` | Dipendenze dirette, versionate. |
| `requirements.lock` | Ambiente completo con versioni anche transitive, ricavato dall'immagine verificata. |
| `.dockerignore` | Esclude segreti, backup e file inutili dal contesto di build. |
| `.gitignore` | Impedisce il versionamento accidentale di `.env`, backup e cache Python. |
| `.env.example` | Schema pubblico delle variabili, senza credenziali reali. |
| `app/__init__.py` | Dichiara il package Python. |
| `app/core.py` | Connessioni SQL/Qdrant, migrazione additiva, parsing, modello, frammentazione, upsert e ricerca. |
| `app/indexer.py` | Punto di ingresso dell'importazione batch. |
| `app/web.py` | API FastAPI, catalogo SQL, healthcheck e video con percorso confinato; modello caricato dalla ricerca. |
| `app/index.html` | Interfaccia italiana, query asincrona, gestione errori; testo renderizzato senza HTML arbitrario. |
| `pytest.ini` | Configura import del package e cache test nella directory temporanea scrivibile. |
| `tests/test_unit.py` | Parsing e protezione percorsi, senza database. |
| `tests/test_integration.py` | Reindicizzazione, SQL/Qdrant, ricerca pertinente, video Range, validazione richieste. |
| `scripts/smoke.py` | Controlla HTTP reale della demo, ricerche sui dialoghi campione e Range video. |
| `scripts/backup.sh` | Dump PostgreSQL e snapshot Qdrant, lock e checksum. |
| `scripts/verify-restore.sh` | Ripristino effettivo in ambiente isolato e confronto conteggi. |
| `compose.restore.yaml` | Definizione dei servizi temporanei di ripristino, volumi distinti e zero porte host. |
| `README.md` | Avvio rapido e rimandi didattici. |
| `docs/*.md` | Guida, architettura, lezioni, prontuario, verifiche e domande. |

Il file `.env` preesistente è preservato. I backup locali sono esclusi dal contesto Docker e dal controllo versione. La cartella `backups/` contiene anche il dump precedente all'estensione e la copia della configurazione iniziale.

## Uso ordinario

Seguire l'avvio documentato in COMANDI.md. Dopo il primo download, è possibile aggiungere `HF_HUB_OFFLINE=1` a `.env` per impedire anche le richieste di metadati a Hugging Face; aggiornare poi solo il web con il comando di avvio selettivo nel prontuario. L’inferenza è sempre locale. Il primo download può richiedere minuti: controllare i log invece di ricreare volumi. Inserire una domanda nell'interfaccia, per esempio «Come isolare le applicazioni?» o «Come gestire un cluster di pod?». I risultati sono ordinati per coseno del frammento migliore e raggruppati per episodio. Il link video compare soltanto se il file esiste e il percorso è interno all'output autorizzato.

Dopo aver modificato o aggiunto un TXT, rilanciare l'indicizzatore: mantiene l'identità della sorgente e aggiorna tutti i vettori. Le varianti short sono catalogate separatamente. Il record dimostrativo SQL ID 1 è conservato ma non inserito automaticamente nell'indice: la pipeline importa dialoghi originali, non inventa un'associazione.

## Backup e ripristino

Eseguire backup quando non ci sono modifiche manuali al catalogo o ai sorgenti. Il lock coordina questo indicizzatore e il backup, non altri client SQL. Le ricerche restano disponibili. Il backup include dati SQL e snapshot della collection, ma non i video, i dialoghi originali, la cache modello o `.env`: conservarli separatamente con permessi sicuri. Lo snapshot resta anche nello storage Qdrant: monitorare lo spazio; nessuna cancellazione automatica.

Eseguire lo script di verifica con il percorso appena prodotto. Esso controlla SHA-256 e importa i dati in servizi nuovi, con le stesse immagini dei servizi originali. Confronta numero di episodi e vettori e impronte del contenuto completo delle due tabelle SQL; il successo conferma leggibilità del dump e dello snapshot. Non è una prova esaustiva di ogni byte o di ogni video. Le copie sono arrestate alla fine e i volumi di prova conservati per ispezione.

Per un disastro reale, verificare prima il backup con questo procedimento; predisporre una nuova istanza isolata e confrontare contenuti e credenziali. Solo dopo una decisione esplicita, pianificare il passaggio dei client alla nuova istanza. Gli script non svuotano né sovrascrivono database esistenti.

## Ricostruzione su Ubuntu

Servono Docker Engine con Compose, Git o una copia dei sorgenti, Bash, curl, sha256sum e Python 3 di sistema per gli script amministrativi (solo libreria standard). Nessun pip o ambiente virtuale sull'host. Conservare il nome progetto se si vogliono ritrovare gli stessi volumi: Compose deriva i nomi dalla cartella o dall'opzione progetto.

Su una macchina nuova copiare questo repository, i dialoghi e i video; preparare `.env` come nel prontuario. Usare i comandi di build e avvio. I dati possono essere rigenerati dai TXT per gli episodi importati; per conservare anche ID e record manuali serve il dump. Verificare il ripristino prima di decidere la procedura di migrazione. I digest e il lock delle dipendenze riducono variazioni; occorre un host amd64 compatibile, accesso ai registry e, al primo caricamento, a Hugging Face. Non sono state verificate altre architetture CPU.

## Diagnostica

| Sintomo | Possibile causa | Azione e controllo |
|---|---|---|
| Prima ricerca lenta | Download o caricamento modello | Leggere log web, verificare rete e spazio disco. |
| HTTP 503 | SQL o Qdrant non raggiungibili | Leggere health e log; verificare i due servizi con `ps`. |
| Nessun risultato | Collection non ancora creata | Eseguire indexer e leggere il numero episodi elaborati. |
| Video assente | Mount errato o file non leggibile | Controllare `STORYCAST_ROOT`, nome file e permessi host. |
| Errore dimensione collection | Modello/indice incompatibili | Non ricreare la collection: preservarla, scegliere una nuova collection e una migrazione esplicita. |
| Container terminato 137 | Limite RAM raggiunto | Misurare con stats, ridurre batch o rivedere limiti con risorse disponibili. |
| Credenziali non valide dopo modifica `.env` | Il database era già inizializzato | Ripristinare le credenziali corrette; non cancellare il volume. |
| Backup fermo sul lock | Indicizzatore ancora attivo | Attendere e leggere i log; timeout del lock dopo 300 secondi. |
| Errore durante l'indicizzazione | SQL già aggiornato, Qdrant incompleto | Correggere la causa e rilanciare: ID e UUID stabili consentono il recupero. |
| Risultati poco pertinenti | Domanda fuori corpus o limiti del modello | Confrontare il testo originale; il punteggio non è una certezza e non c'è soglia universale. |

Gli healthcheck rilevano disponibilità, non qualità semantica. Un servizio può essere healthy con indice vuoto. Il healthcheck Qdrant aggiunto al file verrà applicato alla prossima ricreazione pianificata del suo container; quello preesistente non è stato riavviato solo per attivarlo.

## Aggiornare in futuro

Non cambiare tag o modello casualmente. Per una dipendenza Python, aggiornare la versione diretta e rigenerare il lock in un container di build, poi ricostruire e rieseguire la suite. Per un modello differente, progettare una nuova collection con dimensione e distanza corrette; non ricreare quella esistente. Per applicare un healthcheck o una nuova immagine al database, pianificare il riavvio e verificare prima il backup: l'avvio `--no-recreate` usato qui protegge i container esistenti ma non applica quei cambiamenti.

## Accesso da Windows nella LAN

L’interfaccia è ora pubblicata su http://192.0.2.10:8000. La [guida LAN](ACCESSO_LAN.md) spiega rete, Docker, video, filtro delle sorgenti, controlli firewall ancora necessari, prova finale da Windows e rollback locale.

## Catalogo completo

Il pulsante **Mostra tutti gli episodi** legge tutte le righe SQL, inclusi i record manuali non indicizzati, con totale, video disponibili e paginazione. Non usa Qdrant né embedding. La [guida al catalogo](CATALOGO.md) documenta ordine ID decrescente, API, differenze dalla ricerca e verifiche. Il modello viene ora caricato solo alla prima ricerca semantica.

## Database nuovo

Il modello pubblico monta `initdb/001-episodes.sql`: lo schema base viene creato solo sul primo avvio con volume vuoto. Non richiede tabelle o credenziali del progetto originale. I test di integrazione si attivano esplicitamente; vedere il README. I record manuali citati negli esempi storici non sono inclusi nella distribuzione.
