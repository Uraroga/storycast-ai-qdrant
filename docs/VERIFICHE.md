# Registro delle verifiche

## Prove storiche precedenti alla preparazione GitHub

La documentazione tecnica originale registrava prove del 16 novembre 2026 su Linux amd64. Questo riepilogo conserva metodo, risultati e limiti; omette indirizzi reali, inventario dei servizi esterni, nomi dei contenuti personali, dettagli dei backup e altre informazioni dell'installazione privata. Le copie originali della documentazione restano fuori dai file pubblicabili. Questi risultati non sono stati rieseguiti integralmente durante la preparazione GitHub.

| Prova storica | Risultato registrato |
|---|---|
| Build Docker e `pip check` | Build completata, dipendenze compatibili nell'immagine verificata. |
| Modello e cache offline | Caricamento CPU, dimensione 384, indicizzazione offline dopo download. |
| Importazione e ripetizione | ID e numero di punti stabili; record manuale preesistente preservato. |
| Test del testo lungo | Frammentazione senza troncamento globale. |
| Collection incompatibile | Rifiuto senza ricreazione automatica. |
| Percorsi video | Traversal, symlink esterni e file assenti rifiutati. |
| API | Errori 422, 404 e dipendenze indisponibili simulate con 503. |
| Backup e ripristino isolato | Impronte delle due tabelle SQL coincidenti, conteggi e ricerca vettoriale riusciti. |
| Accesso LAN | HTTP, Range iniziale/intermedio/suffisso 206, 416 oltre fine e filtro sorgente verificati dal server. |
| Catalogo SQL | Totale e paginazione confrontati con SQL; nessun uso di modello o Qdrant. |
| Browser headless Linux | Navigazione catalogo, pagine, ritorno al form e ricerca verificati. |

Le suite storiche erano rispettivamente di otto test e, dopo l'aggiunta del catalogo, nove test su un insieme selezionato. I conteggi non sono il risultato della suite attuale. La prova di reindicizzazione scrive sui database, anche se conserva ID e conteggi: non va chiamata «non distruttiva» e non va eseguita automaticamente in produzione.

## Preparazione GitHub — 17 novembre 2026

- Test sull'immagine applicativa locale esistente, con sorgenti e test aggiornati montati in sola lettura: **8 passed, 4 deselected**, una deprecazione interna Starlette/AnyIO. Container temporaneo senza rete, senza credenziali e senza volumi di produzione; nessun download modello. I quattro test di integrazione sono esclusi dalla configurazione predefinita.
- Sintassi Python verificata con parsing AST e sintassi Bash con `bash -n`.
- Validazione silenziosa del Compose locale e del modello pubblico con soli valori dimostrativi; nessuna applicazione della configurazione.
- Controlli sui file candidati alla pubblicazione, esclusioni Git e confronto con i segreti locali senza stamparli. Rapporto e inventario completi conservati localmente, fuori dal repository pubblico.
- Nessun avvio, arresto, aggiornamento o ricreazione dei servizi di produzione; nessun backup, snapshot, ripristino o indicizzazione eseguito in questa fase.

## Metodo e limiti

I test isolati sostituiscono le dipendenze esterne; i test marcati `integration` richiedono servizi e corpus dimostrativo. Consultare il README per l'attivazione esplicita e il prontuario per gli effetti dei comandi.

Non sono stati eseguiti in questa fase una build completa, un avvio da volumi vuoti, un ripristino o test di qualità semantica su un dataset etichettato. La portabilità del nuovo modello Compose e dello schema iniziale è controllata staticamente; il collaudo completo su una seconda macchina resta da effettuare. Non è stato eseguito un audit delle vulnerabilità di tutte le dipendenze.

Non sono certificati carichi elevati, CPU ARM/GPU, accesso da Windows o playback grafico su tutti i browser. Nessuna prova di interruzione forzata dei database. Un backup SQL/Qdrant non include media, sorgenti o segreti; le impronte SQL e una query vettoriale non equivalgono a un confronto esaustivo di tutti i vettori. I volumi di ripristino conservati occupano spazio e richiedono gestione separata.

L'avvertenza Starlette/AnyIO osservata nei test isolati riguarda un alias deprecato di `BlockingPortal`; non ha causato fallimenti. Le dipendenze fissate richiedono manutenzione periodica.
