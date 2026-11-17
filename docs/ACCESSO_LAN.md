# Accesso dalla rete locale

La distribuzione pubblica usa `WEB_BIND_IP=127.0.0.1`. Per una LAN fidata impostare nel proprio `.env` l'IP del server e le reti sorgenti consentite. Ad esempio, **sostituendo i valori dimostrativi non instradabili**:

```dotenv
WEB_BIND_IP=192.0.2.10
WEB_ALLOWED_NETWORKS=127.0.0.0/8,::1/128,192.0.2.0/24
```

Il modello `compose.example.yaml`, copiato in `compose.yaml`, risolve queste variabili; il vecchio Compose locale può invece avere valori fissi. Non sostituire una configurazione di produzione senza una migrazione pianificata. L'applicazione delle modifiche richiede un aggiornamento del servizio web nel proprio ambiente: i comandi di questo documento non sono stati eseguiti durante la preparazione GitHub.

## Percorso delle richieste

`127.0.0.1` indica il computer del browser. Da un altro dispositivo usare `http://IP_DEL_SERVER:8000`. Il mapping è `${WEB_BIND_IP:-127.0.0.1}:8000:8000`: il primo indirizzo appartiene all'host; Uvicorn ascolta su `0.0.0.0` dentro il container. SQL e Qdrant sono raggiunti dai nomi DNS `postgres` e `qdrant` della rete Compose.

Browser → porta host 8000 → Uvicorn → filtro IP → FastAPI. `GET /` serve la pagina; `/search` cerca gli episodi, `/episodes` legge il catalogo SQL. I video hanno link relativi `/video/ID`, risolti sulla stessa origine; non richiedono CORS né accesso al filesystem da parte del client.

## Riproduzione e Range

Il server recupera il percorso dal catalogo, verifica che sia un file ammesso entro la directory media e restituisce `FileResponse`. I mount dei media sono in sola lettura. Una richiesta completa produce HTTP 200; `Range: bytes=0-99` produce 206 e `Content-Range`, permettendo buffering e spostamento. Un intervallo fuori file produce 416. Nella versione Starlette fissata è stata osservata l'omissione del prefisso `bytes` nell'header del solo errore 416, accettata esplicitamente dal test diagnostico. Non c'è transcodifica: verificare i codec nel browser.

## Sicurezza della rete

`WEB_ALLOWED_NETWORKS` controlla il peer TCP reale su tutti gli endpoint, inclusa la documentazione API. Uvicorn usa `--no-proxy-headers`, quindi `X-Forwarded-For` non consente di aggirare il filtro. Una lista vuota disabilita il controllo: usarla soltanto nei test isolati. NAT Docker e proxy possono cambiare l'IP osservato; verificare sorgenti ammesse e rifiutate sul proprio sistema prima dell'uso. Non autorizzare reti estese per aggirare un errore di configurazione.

Il filtro restituisce 403 ma non blocca la connessione TCP. HTTP non cifra i dati e non c'è autenticazione, quindi ogni dispositivo autorizzato può leggere testi, catalogo e video e consumare CPU. Non configurare DMZ o port forwarding. Un IP privato non protegge da reti instradate o NAT. Per accessi più ampi occorrono autenticazione, HTTPS e una revisione del filtro dietro proxy.

PostgreSQL e Qdrant devono restare pubblicati solo su `127.0.0.1`, rispettivamente 5432 e 6333; nessuna porta host 6334. Le porte Docker possono attraversare FORWARD e non le sole regole UFW INPUT. Lo stato active di un'unità systemd non prova l'efficacia del firewall. Un amministratore può ispezionare, senza cambiare regole:

```bash
sudo ufw status verbose
sudo iptables -S DOCKER-USER
sudo iptables -t nat -S DOCKER
sudo nft list ruleset
```

Verificare il backend effettivo e il router. Non resettare regole, attivare firewall alla cieca o aggiungere aperture generiche della porta 8000. Valutare una riserva DHCP per l'indirizzo del server.

## Verifiche sul server e sul client

```bash
docker compose config --quiet
docker compose ps
ss -lnt
# Sostituire IP_DEL_SERVER con l'indirizzo reale
curl -fsS http://IP_DEL_SERVER:8000/health
```

Su Windows usare `Test-NetConnection IP_DEL_SERVER -Port 8000`: atteso successo. Per 5432, 6333 e 6334 è atteso fallimento dalla LAN. Aprire il browser, mostrare il catalogo, cercare un argomento presente, avviare e spostare un video; in F12 verificare stessa origine e risposte Range 206. Provare anche da una sorgente non autorizzata: atteso 403. Annotare browser, rete ed esiti senza pubblicare i dati personali.

`STORYCAST_URL=http://IP_DEL_SERVER:8000 python3 scripts/smoke.py` richiede il corpus dimostrativo Docker/Kubernetes. `verify_lan.py` richiede inoltre l'esecuzione dal server, un binding esclusivo sulla LAN, loopback web chiuso e database raggiungibili su loopback: non è adatto alla configurazione locale predefinita. Scarica per intero i video e può produrre traffico significativo.

## Ripristino della configurazione di accesso

Conservare privatamente una copia della configurazione precedente prima di ogni cambiamento pianificato. Per tornare all'accesso locale, impostare binding loopback e reti consentite coerenti, validare e aggiornare solo il web nel proprio ambiente. Verificare l'accesso locale e il rifiuto dalla LAN. Non usare copie storiche non distribuite come prerequisito e non arrestare i database né eliminare volumi. Per accesso remoto privato può essere preferibile il tunnel SSH del [prontuario](COMANDI.md).
