> Documentazione tecnica adattata per la distribuzione indipendente. Gli indirizzi `192.0.2.*` e `198.51.100.*` sono esempi non operativi: sostituirli con quelli della propria rete. Per una nuova installazione seguire prima il [README](../README.md); `compose.yaml` è locale, generato da `compose.example.yaml`. Le prove storiche non certificano una nuova installazione.

# Domande e risposte

1. **Che differenza c'è tra immagine e container?** L'immagine è il pacchetto immutabile; il container è un'istanza in esecuzione con il proprio processo.
2. **Che cos'è un servizio Compose?** La descrizione di come avviare un componente: immagine, rete, risorse, volumi e configurazione.
3. **Perché usare un volume?** Per conservare dati al di fuori della vita del container.
4. **I bind mount sono volumi nominati?** No: espongono un percorso specifico dell'host; qui sono in sola lettura.
5. **Perché Python usa `postgres` come hostname?** È il nome DNS del servizio nella rete Compose.
6. **Perché `localhost` sarebbe sbagliato dentro Python?** Indicherebbe il container Python stesso.
7. **Qual è la fonte autorevole dei titoli?** PostgreSQL; Qdrant conserva l'indice con episode_id.
8. **Che cos'è una chiave primaria?** Un identificatore unico e non nullo di una riga, qui episodes.id.
9. **A cosa serve una chiave esterna?** Garantisce che l'episode_id del mapping riferisca un episodio esistente.
10. **Perché usare query parametrizzate?** Per separare dati e codice SQL, evitando concatenazioni pericolose.
11. **Che cosa fa commit?** Rende persistenti le modifiche della transazione SQL.
12. **Che cos'è un embedding?** Una rappresentazione numerica appresa del testo in uno spazio vettoriale.
13. **Quale modello è usato?** intfloat/multilingual-e5-small, revisione fissata nel Compose.
14. **Quante dimensioni ha il vettore?** 384, verificate prima di creare la collection.
15. **Perché usare `query:` e `passage:`?** Sono i prefissi previsti dall'addestramento del modello per domanda e contenuto.
16. **Perché frammentare un episodio lungo?** Il modello accetta al massimo 512 token; finestre di 420 evitano di perdere il resto del testo.
17. **Perché sovrapporre i frammenti?** Per mantenere contesto tra la fine di uno e l'inizio del successivo.
18. **Che cosa misura il coseno?** La somiglianza tra direzioni dei vettori; non una probabilità di correttezza.
19. **La ricerca produce una risposta generativa?** No, restituisce episodi pertinenti già presenti nel catalogo.
20. **Come si evitano duplicati SQL?** Con source_key univoca e riuso dell'episode_id associato.
21. **Come si evitano duplicati in Qdrant?** UUID deterministici per episodio/frammento e upsert degli stessi punti.
22. **Che succede se un testo si accorcia?** Dopo l'upsert si eliminano i soli frammenti obsoleti di quell'episodio.
23. **Che succede se rinomino un TXT?** Il nome è l'identità della sorgente, quindi viene creato un nuovo episodio; non si cancella quello precedente.
24. **Che succede se SQL riesce ma Qdrant fallisce?** L'indice può essere incompleto; indexed_at resta nullo e una nuova indicizzazione lo ripara.
25. **Il lock del backup blocca qualsiasi modifica SQL?** No, coordina soltanto i client che usano lo stesso advisory lock.
26. **Un healthcheck positivo garantisce risultati pertinenti?** No, verifica disponibilità tecnica; servono anche test funzionali.
27. **Perché il video viene richiesto tramite ID?** Il server recupera e valida il percorso senza accettare un percorso arbitrario dal browser.
28. **Perché `.env` non va versionato?** Contiene credenziali; è escluso anche dal contesto Docker.
29. **Cambiare POSTGRES_PASSWORD aggiorna il database esistente?** No, le variabili dell'immagine inizializzano solo un volume nuovo.
30. **Perché un backup non basta senza ripristino?** Il file potrebbe essere corrotto, incompatibile o incompleto: importarlo in un ambiente isolato dà una prova concreta.
31. **Che cosa non contiene il backup automatico?** Video, TXT originali, cache modello e credenziali, da conservare separatamente.
32. **Perché fissare immagini per digest e pacchetti con un lock?** Per ridurre variazioni fra build e ricostruzioni nel tempo.
33. **Come si accede da un altro computer senza esporre il web?** Tramite il tunnel SSH documentato nel prontuario.
34. **Perché l'episodio ID 1 non compare automaticamente nelle ricerche?** È un record manuale preesistente, preservato senza associarlo arbitrariamente a un dialogo.
35. **Dove girano embedding e librerie Python?** Nei container applicativi sulla CPU di server, senza installazioni Python globali host.
