# Manuale Utente - Gestione arTEper

## 📥 Download

### 🏁 Windows (senza Python)
👉 **[Scarica l'ultima versione per Windows](https://github.com/enzotnt/gestione-arteper/releases/latest)** 👈  
✅ INSTALLAZIONE:
1. Estrai tutto in una cartella (es. C:\Gestionale)
2. Fai doppio click su "Gestionale_arTEper.exe"
3. Il programma si avvia. :-)

📁 STRUTTURA:
- Gestionale_arTEper.exe  ← il programma
- icons\                   ← icone (non spostare!)
- database\                 ← qui vengono salvati i tuoi dati
- export\                   ← qui finiscono i PDF
- backup\                   ← qui vanno i backup

📌 NOTE:
- Non spostare l'EXE fuori dalla cartella
- La cartella icons deve stare nella stessa posizione dell'EXE
- I dati vengono salvati nella cartella database

❓ PROBLEMI?
- Se non si avvia, controlla che la cartella "icons" sia presente
- Per supporto: apri una issue su GitHub

🐍 Versione con Python: https://github.com/enzotnt/gestione-arteper

### 🐍 Linux / Windows (con Python)
- Clona il repository: `git clone https://github.com/enzotnt/gestione-arteper.git`
- Entra nella cartella: `cd gestione-arteper`
- Per Linux: esegui `./installa_linux.sh` poi `./avvia_gestionale.sh`
- Per Windows con Python: esegui `installa_windows.bat` poi `avvia_windows.bat`

---

## Introduzione

Benvenuto nel gestionale **arTEper**, un'applicazione progettata per gestire tutti gli aspetti della tua attività artigianale: dalla creazione di progetti alla vendita, passando per la gestione del magazzino, degli ordini e delle finanze. -(TESTATO SU UBUNTU 25.xx)

Questo manuale ti guiderà all'utilizzo di tutte le funzionalità del programma.

## Indice

1. [Primi Passi](#primi-passi)
2. [Panoramica dell'Interfaccia](#panoramica-interfaccia)
3. [Gestione Magazzino](#magazzino)
4. [Gestione Progetti](#progetti)
5. [Gestione Negozio](#negozio)
6. [Gestione Mercatini](#mercatini)
7. [Gestione Buoni Regalo](#buoni)
8. [Gestione Ordini](#ordini)
9. [Gestione Lavorazione](#lavorazione)
10. [Gestione Venduti](#venduti)
11. [Gestione Spese](#spese)
12. [Gestione Bilancio](#bilancio)
13. [Configurazione e Backup](#configurazione)
14. [FAQ e Risoluzione Problemi](#faq)

<a name="primi-passi"></a>
## 1. Primi Passi

### 1.1 Avvio del Programma
Esegui il file `main.py` per avviare l'applicazione. Si aprirà la finestra principale con tutte le funzionalità organizzate in schede.

### 1.2 Configurazione Iniziale
Prima di iniziare, è consigliabile configurare i tuoi dati anagrafici:
1. Clicca sul pulsante **⚙️ Configurazione** nel footer
2. Inserisci i tuoi dati nelle schede:
   - **Anagrafica**: nome, numero tessera, ecc. (usati nelle stampe)
   - **Applicazione**: tema, dimensione font, backup automatico
   - **Mercati**: cartella predefinita per i PDF
   - **Ordini**: cartelle sorgente e destinazione per i file degli ordini

<a name="panoramica-interfaccia"></a>
## 2. Panoramica dell'Interfaccia

La finestra principale è divisa in tre aree:

- **Header superiore**: logo e titolo dell'applicazione
- **Area centrale**: schede (tab) per accedere a tutte le funzionalità
- **Footer inferiore**: orario in tempo reale, pulsanti per configurazione e backup

### 2.1 Navigazione tra le Schede
Clicca sulle schede in alto per passare da una funzione all'altra:

| Scheda | Descrizione |
|--------|-------------|
| 📦 Magazzino | Gestione componenti e scorte |
| 🛠️ Progetti | Creazione e modifica progetti |
| 🛍️ Negozio | Gestione vendite |
| 🎪 Mercatini | Liste per fiere e mercatini |
| 🎁 Buoni Regalo | Gestione buoni sconto/regalo |
| 📋 Ordini | Gestione ordini clienti |
| 🛠️ In Lavorazione | Tracciamento assemblaggio |
| ✅ Venduti | Storico vendite |
| 💸 Spese | Spese di gestione |
| 📈 Bilancio | Analisi economica |

### 2.2 Funzionalità Comuni a Tutte le Schede
- **Tabelle interattive**: clicca sulle intestazioni per ordinare i dati
- **Doppio click**: spesso apre finestre di dettaglio o modifica
- **Click destro**: apre menu contestuale con operazioni specifiche
- **Selezione multipla**: usa `Ctrl+click` per selezionare più elementi

<a name="magazzino"></a>
## 3. Gestione Magazzino

La scheda **Magazzino** ti permette di gestire tutti i componenti che utilizzi per creare i tuoi progetti.

### 3.1 Visualizzazione
La tabella mostra per ogni componente:
- ID, Nome, Unità di misura
- Quantità disponibile
- Costo unitario
- Ultimo acquisto e fornitore
- Note

### 3.2 Operazioni Principali

#### Aggiungere un Nuovo Componente
1. Clicca su **➕ Nuovo componente**
2. Compila i campi:
   - **Nome componente** (obbligatorio)
   - **Unità di misura** (pz, g, ml, m, kg, l)
   - **Quantità iniziale**
   - **Costo totale** (il costo unitario viene calcolato automaticamente)
   - **Fornitore** (opzionale)
   - **Note** (opzionali)
   - **Immagine** (opzionale)
3. Clicca **Conferma**

#### Aggiungere Scorte a un Componente
1. Seleziona il componente dalla tabella
2. Clicca **📦 Aggiungi scorte** (o tasto destro → Aggiungi scorte)
3. Inserisci quantità e costo totale
4. Le nuove scorte copriranno automaticamente eventuali componenti mancanti prima di aumentare il magazzino

#### Forzare la Quantità
⚠️ **Operazione delicata**: modifica direttamente la quantità senza aggiornare i componenti mancanti
1. Seleziona il componente
2. Clicca **🔧 Forza Quantità** (o tasto destro → Forza Quantità)
3. Inserisci la nuova quantità
4. Conferma l'operazione

#### Modificare un Componente
- Seleziona il componente
- Tasto destro → **✏️ Modifica componente**
- Puoi modificare: nome, unità, fornitore, note e immagine

#### Visualizzare Storico Acquisti
- Seleziona un componente
- Tasto destro → **📜 Mostra storico**
- Oppure usa **📦 Storico Magazzino** per vedere tutti i movimenti

#### Esportare Storico
- **💾 Esporta storico singolo**: esporta CSV del componente selezionato
- **💾 Esporta storico completo**: esporta tutti i movimenti in CSV

#### Eliminare un Componente
- Seleziona il componente
- Tasto destro → **🗑️ Elimina**
- Conferma l'operazione

### 3.3 Componenti Mancanti
Clicca su **🧩 Componenti Mancanti** per aprire una finestra che mostra tutti i componenti che scarseggiano, raggruppati per componente e con l'indicazione dei progetti coinvolti. **Doppio click** per aggiungere scorte direttamente.

<a name="progetti"></a>
## 4. Gestione Progetti

I progetti sono l'insieme di componenti che costituiscono i tuoi prodotti finiti.

### 4.1 Creare un Nuovo Progetto
1. Clicca su **➕ Aggiungi Progetto**
2. Inserisci il nome del progetto
3. Si aprirà la finestra di selezione componenti:
   - Seleziona i componenti necessari dal magazzino
   - Per ognuno, specifica **quantità** e **moltiplicatore** (default: 3.0)
   - Conferma
4. Il progetto viene creato e i componenti vengono scalati dal magazzino

### 4.2 Visualizzazione
La tabella mostra per ogni progetto:
- ID, Data creazione, Nome
- Stato vendita
- Prezzo, Costo, Ricavo (calcolati automaticamente)
- Note

### 4.3 Modificare un Progetto
1. Seleziona il progetto e clicca **✏️ Modifica** (o doppio click)
2. Nella finestra che si apre puoi:
   - Modificare **nome** e **moltiplicatore globale**
   - **Aggiungi Componente**: seleziona dal magazzino (con quantità e moltiplicatore individuale)
   - **Rimuovi Componente**: elimina un componente (restituito al magazzino)
   - Modificare il **moltiplicatore di un singolo componente** (doppio click sulla riga)
   - **Cambia/Aggiungi immagine**
   - Impostare il **percorso della cartella** del progetto
3. Clicca **Salva modifiche**

### 4.4 Altre Operazioni
- **📝 Modifica note**: aggiungi o modifica le note
- **📄 Duplica progetto**: crea una copia (i componenti vengono ripresi dal magazzino)
- **📜 Mostra storico**: visualizza tutte le modifiche e le note
- **📂 Vai a posizione**: apre la cartella del progetto
- **🛍️ Al negozio**: mette in vendita il progetto (vedi sezione Negozio)

### 4.5 Aggiungere a Mercatino
1. Seleziona **uno o più progetti** (usa `Ctrl+click`)
2. Clicca **🎪 Aggiungi a Mercatino**
3. Nella finestra puoi modificare prezzo e quantità per ogni progetto
4. Conferma per inviarli alla scheda Mercatini

<a name="negozio"></a>
## 5. Gestione Negozio

Questa scheda gestisce i progetti pronti per la vendita.

### 5.1 Mettere in Vendita un Progetto
- Dalla scheda Progetti: seleziona il progetto → **🛍️ Al negozio**
- Specifica quante copie mettere in vendita

### 5.2 Visualizzazione
La tabella mostra:
- Nome progetto, Data inserimento
- Prezzo di vendita (calcolato automaticamente)
- Disponibili e Venduti

### 5.3 Vendere Progetti (Vendita Multipla)
1. Seleziona **uno o più progetti** da vendere (usa `Ctrl+click`)
2. Clicca **💰 Vendi multipli**
3. Inserisci il nome del cliente
4. Se il cliente esiste già, scegli se:
   - **Sì**: aggiungi al cliente esistente
   - **No**: crea un nuovo cliente (inserisci nuovo nome)
5. Nella finestra di vendita puoi:
   - Modificare **quantità** per ogni prodotto
   - Modificare il **prezzo totale** (se modificato manualmente, non viene più ricalcolato)
   - Applicare un **codice sconto** (buono regalo o percentuale)
6. Il totale netto viene calcolato automaticamente
7. Conferma per registrare la vendita

### 5.4 Gestire Rientri
Se un progetto non viene venduto e vuoi ritirarlo dal negozio:
1. Seleziona il progetto
2. Tasto destro → **↩️ Rientra**
3. Specifica quante copie rientrare
4. Verranno creati nuovi progetti con nome `NomeOriginale_R1`, `NomeOriginale_R2`, ecc.

### 5.5 Altre Operazioni
- **📜 Storico vendite**: mostra tutte le vendite del progetto selezionato
- **📝 Modifica note**: modifica le note del progetto
- **🖼️ Mostra immagine**: visualizza l'immagine del progetto
- **🗑️ Elimina**: rimuove il progetto dal negozio (senza venderlo)

<a name="mercatini"></a>
## 6. Gestione Mercatini

Questa scheda ti permette di preparare e stampare liste per la partecipazione a mercatini/fiere.

### 6.1 Aggiungere Elementi al Mercatino
Puoi aggiungere elementi da tre schede diverse:
- **Da Progetti**: seleziona progetti → **🎪 Aggiungi a Mercatino**
- **Da Negozio**: seleziona progetti → **🎪 Aggiungi a Mercatino**
- **Da Magazzino**: seleziona componenti → **🎪 Aggiungi a Mercatino** (i componenti avranno prefisso `[MAT]`)

In tutti i casi, si aprirà una finestra dove puoi modificare:
- **Prezzo** (arrotondato a 1 decimale)
- **Quantità**
- **Note**

### 6.2 Gestire la Lista
- **➕ Nuovo**: aggiungi manualmente un elemento alla lista
- **✏️ Modifica**: modifica l'elemento selezionato (o doppio click)
- **🗑️ Elimina**: rimuovi l'elemento selezionato
- Clicca sulle **intestazioni** per ordinare la tabella

### 6.3 Stampare la Lista
1. Clicca **📄 Stampa Lista**
2. Inserisci:
   - **Città/Luogo** del mercatino
   - **Data** (selezionabile con calendario)
3. Il nome file viene generato automaticamente (es. `Milano-15-03-2025.pdf`)
4. Scegli dove salvare il PDF
5. Il documento includerà:
   - Intestazione con luogo e data
   - I tuoi dati anagrafici (da configurazione)
   - Tabella con tutti gli elementi (nome, prezzo, quantità, note)
   - Riepilogo totale pezzi e valore
   - Spazio per la firma

<a name="buoni"></a>
## 7. Gestione Buoni Regalo/Sconto

Questa funzionalità ti permette di creare e gestire buoni regalo e sconti.

### 7.1 Creare un Nuovo Buono
1. Clicca **➕ Nuovo Buono**
2. Seleziona il tipo:
   - **Regalo**: valore in euro
   - **Sconto %**: percentuale di sconto
3. Inserisci:
   - **Valore nominale**
   - **Importo incassato** (se il cliente ha pagato - 0 se non ancora pagato)
   - **Metodo di pagamento**
   - **Cliente acquirente** (obbligatorio)
   - **Intestatario** (opzionale)
   - **Scadenza** (nessuna, 30, 60, 90 giorni)
   - **Note**
4. Il sistema genera automaticamente un codice univoco (es. `ARTE-4F9K`)
5. Puoi copiare il codice negli appunti

### 7.2 Visualizzazione
La tabella mostra:
- ID, Codice, Tipo
- Valore originale e residuo
- **Stato**: ATTIVO, UTILIZZATO, SCADUTO, ANNULLATO
- Scadenza, Cliente

Puoi filtrare per stato e tipo usando i menu a tendina.

### 7.3 Utilizzare un Buono in Vendita
Durante una vendita (nel Negozio o nella Lavorazione):
1. Inserisci il codice nel campo **Codice sconto**
2. Clicca **Applica**
3. Il sistema verifica validità e scadenza
4. Lo sconto viene applicato automaticamente al totale

### 7.4 Gestire i Buoni
- **📋 Copia codice**: copia il codice negli appunti
- **🔍 Dettagli buono**: mostra tutte le informazioni del buono
- **📜 Storico utilizzi**: mostra quando e come è stato utilizzato
- **❌ Annulla buono**: annulla un buono (es. per smarrimento)

<a name="ordini"></a>
## 8. Gestione Ordini

Questa scheda gestisce gli ordini dei clienti.

### 8.1 Creare un Nuovo Ordine
1. Seleziona **uno o più progetti** dalla lista (solo progetti con stato "IN VENDITA")
2. Inserisci:
   - **Cliente** (obbligatorio)
   - **Data consegna** (default tra 7 giorni)
   - **Note** (opzionali)
3. Clicca **📝 Crea Ordine**

Si aprirà una finestra dettagliata dove puoi:
- Modificare **quantità** per ogni progetto
- Modificare i **prezzi** (se necessario)
- Inserire un **acconto**
- Visualizzare in tempo reale i **componenti mancanti**
- Vedere quanti progetti sono **assemblabili** con le scorte attuali

### 8.2 Visualizzazione Ordini
La tabella mostra:
- ID Ordine, Cliente
- Data inserimento e consegna
- **Giorni mancanti** alla consegna
- Stato consegna (✔️ consegnato, ❌ non consegnato)

### 8.3 Gestire gli Ordini
- **✅ Stato Consegna**: cambia lo stato di consegna
- **🗑️ Elimina Ordine/i**: elimina uno o più ordini selezionati
- **Doppio click su un ordine**: apre il dettaglio dove puoi:
  - Modificare cliente, data, note
  - Visualizzare i progetti con i prezzi
  - Salvare le modifiche

### 8.4 Salvare su Disco
Alla creazione di un ordine, puoi scegliere di salvarlo su disco:
1. Conferma l'ordine
2. Alla richiesta "Vuoi salvare i dettagli dell'ordine su disco?", scegli **Sì**
3. Se configurato, verranno copiati automaticamente i file dalla cartella sorgente
4. Verrà creato un file `ordine.txt` con tutti i dettagli

<a name="lavorazione"></a>
## 9. Gestione Lavorazione

Questa scheda traccia lo stato di avanzamento degli ordini.

### 9.1 Visualizzazione
La tabella mostra tutti gli ordini non ancora consegnati con:
- ID Ordine, Cliente
- Date
- Quantità totale
- **Stato lavorazione**: 🛠️ In lavorazione / ❌ Non avviato
- **Stato assemblaggio**: ✅ Tutti / 🟠 Parziale / ❌ Nessuno

**Colori delle righe**:
- 🟢 Verde: tutti assemblati
- 🟠 Arancione: parzialmente assemblati
- 🔴 Rosso: nessuno assemblato

### 9.2 Dettaglio Ordine (Doppio click)
Aprendo un ordine puoi:
1. **Impostare data inizio lavorazione**: inserisci data e clicca Salva
2. **Visualizzare progetti**: tabella con nome, quantità, assemblati, prezzi
3. **Aggiornare quantità assemblata**:
   - Seleziona un progetto
   - Imposta la nuova quantità
   - Clicca Salva
4. **Componenti mancanti**: visualizzati in tempo reale per il progetto selezionato

### 9.3 Vendere un Ordine Completato
Quando tutti i progetti sono assemblati:
1. Clicca **💰 Consegna Ordine**
2. Si aprirà la finestra di vendita (simile a quella del negozio)
3. Puoi modificare quantità e prezzi se necessario
4. Applicare eventuali codici sconto
5. **L'acconto già versato viene detratto automaticamente**
6. Conferma per registrare la vendita e marcare l'ordine come consegnato

<a name="venduti"></a>
## 10. Gestione Venduti

Questa scheda mostra lo storico delle vendite.

### 10.1 Due Modalità di Visualizzazione
- **Raggruppa Clienti**: mostra i totali per ogni cliente
  - Oggetti acquistati, quantità totale, totale speso
- **Vista dettaglio**: mostra ogni singola vendita
  - ID, Data, Cliente, Quantità, Prezzi, Ricavo

Puoi passare da una modalità all'altra con il pulsante **🔁 Vista dettaglio / Raggruppa Clienti**.

### 10.2 Dettaglio Vendita (Doppio click)
Nella vista dettaglio, doppio click su una vendita per aprire la finestra di dettaglio dove puoi:
- Visualizzare l'immagine del progetto
- **📁 Cambia immagine**: associare una nuova immagine
- **❌ Rimuovi immagine**: eliminare l'immagine
- Modificare le **note**
- Impostare la **posizione del progetto**
- **🔍 Cerca posizione**: scegli una cartella
- **📂 Vai a posizione**: apri la cartella
- **💾 Salva modifiche**: salva le modifiche

### 10.3 Altre Operazioni
- **🗑️ Elimina vendita**: elimina la vendita selezionata (solo in vista dettaglio)
- **Clicca su cliente nella vista raggruppata**: mostra tutte le vendite di quel cliente

<a name="spese"></a>
## 11. Gestione Spese

Questa scheda gestisce le spese di gestione (non di magazzino).

### 11.1 Visualizzazione
La tabella mostra:
- Data, Categoria, Descrizione
- Importo, Metodo pagamento
- Note

### 11.2 Aggiungere una Spesa
1. Clicca **➕ Nuova Spesa**
2. Inserisci:
   - **Data** (formato YYYY-MM-DD)
   - **Categoria**
   - **Nome/Descrizione**
   - **Importo**
   - **Metodo pagamento** (opzionale)
   - **Note** (opzionali)
3. Clicca **💾 Salva**

### 11.3 Altre Operazioni
- **Doppio click su una spesa**: modifica
- **🗑️ Elimina Spesa**: elimina la spesa selezionata
- **🔁 Ricompra**: nella finestra di modifica, crea una nuova spesa con la stessa data di oggi

<a name="bilancio"></a>
## 12. Gestione Bilancio

Questa scheda ti permette di analizzare le performance economiche.

### 12.1 Filtri Temporali
Puoi selezionare il periodo in due modi:
1. **Manuale**: imposta data "Da" e "A"
2. **Filtri rapidi**: scegli tra:
   - Ultimi 30 giorni
   - Ultimi 3 mesi
   - Ultimi 6 mesi
   - Ultimo anno
   - Tutto

### 12.2 Dati Visualizzati
Il pannello mostra:

**Dati principali:**
- **Spese Magazzino**: totale acquisti componenti
- **Spese Gestione**: totale spese di gestione
- **Totale Spese**: somma delle due
- **Ricavi**: totale vendite + utilizzo buoni + acconti
- **Utile Netto**: ricavi - spese

**Sezione Buoni:**
- Buoni venduti (numero)
- Incassato da buoni
- Buoni utilizzati (numero)
- Valore utilizzato
- Buoni attivi residui

**Sezione Acconti:**
- Ordini con acconto
- Totale acconti
- Acconti attivi residui
- Clicca **📋 Dettaglio Ordini con Acconto** per vedere l'elenco

### 12.3 Grafico
Il grafico mostra l'andamento cumulativo nel tempo di:
- 📈 Ricavi (verde)
- 📉 Spese (rosso)
- 📊 Bilancio (blu tratteggiato)

**Passa il mouse** sul grafico per vedere i valori precisi.

<a name="configurazione"></a>
## 13. Configurazione e Backup

### 13.1 Configurazione Generale
Clicca **⚙️ Configurazione** nel footer per accedere a:

**Anagrafica** (usati nelle stampe mercatini):
- Nome e Cognome
- Numero Tessera
- Data rilascio
- Comune

**Applicazione**:
- Tema
- Dimensione font
- Backup automatico
- Giorni tra backup

**Mercati**:
- Cartella predefinita per salvare i PDF
- Pulsante per aprire la cartella

**Ordini**:
- Cartella sorgente (file da copiare)
- Cartella destinazione base
- Opzioni di copia automatica

### 13.2 Backup e Ripristino
- **📁 Backup Database**: crea una copia di backup del database
- **♻️ Ripristina Backup**: ripristina da un backup precedente

<a name="faq"></a>
## 14. FAQ e Risoluzione Problemi

### Come si calcola il prezzo di un progetto?
Il prezzo = somma(quantità componente × costo_unitario × moltiplicatore)
Il moltiplicatore può essere globale per il progetto o specifico per ogni componente.

### Cosa significa "componenti mancanti"?
Quando un ordine richiede più componenti di quelli disponibili, il sistema registra la differenza come "componenti mancanti". Quando arriveranno nuove scorte, verranno automaticamente assegnate a coprire questi mancanti prima di aumentare il magazzino.

### Posso modificare i prezzi durante la vendita?
Sì, sia nella vendita dal negozio che nella vendita di un ordine, puoi modificare i prezzi. Se modifichi manualmente, il sistema non li ricalcolerà automaticamente.

### Cosa succede quando "rientra" un progetto?
Il progetto viene rimosso dal negozio e vengono create nuove copie nel database progetti con nome "Nome_R1", "Nome_R2", ecc. I componenti **NON** vengono restituiti al magazzino.

### Come funzionano i buoni regalo?
- **Buono REGALO**: ha un valore in euro. Quando usato, scala l'importo dal totale.
- **Buono SCONTO**: ha una percentuale. Applica lo sconto una sola volta e si esaurisce.
Entrambi hanno un codice univoco e possono avere scadenza.

### Perché nel bilancio i ricavi da buoni sono separati?
L'incasso dalla vendita di un buono **NON** è un ricavo immediato (è una passività finché il buono non viene speso). I ricavi effettivi si registrano quando il buono viene **UTILIZZATO** in una vendita.

### Il grafico del bilancio non mostra tutti i mesi?
Assicurati di aver selezionato un periodo sufficientemente ampio. Il grafico mostra solo i mesi con dati nel periodo selezionato.

### Come si configura la stampa per i mercatini?
1. Vai in Configurazione → **Anagrafica** e inserisci i tuoi dati
2. Vai in Configurazione → **Mercati**, imposta la cartella predefinita per i PDF
3. Quando stampi, il sistema userà questi dati per l'intestazione

### Cosa fare se un componente va in negativo?
Il sistema crea automaticamente un record nei "Componenti Mancanti". Quando arriveranno nuove scorte, verranno automaticamente assegnate a coprire quel debito.

### Come si selezionano più elementi?
Usa `Ctrl+click` per selezionare elementi non contigui, o `Shift+click` per selezionare un intervallo.

### Come si ordinano le tabelle?
Clicca sull'intestazione della colonna per ordinare. Clicca di nuovo per invertire l'ordine.

---

**Versione manuale**: 1.0
**Ultimo aggiornamento**: Marzo 2026
]()
