> **⚠️ DISCLAIMER**
>
> **Il presente software viene fornito "così com'è", senza garanzie di alcun tipo, esplicite o implicite. L'autore non si assume alcuna responsabilità per eventuali danni diretti, indiretti, incidentali o consequenziali derivanti dall'utilizzo, dalla modifica o dalla distribuzione di questo software. L'utilizzo è interamente a rischio e responsabilità dell'utente.**

# Glu2k-Image-Resizer

Applicazione Windows per la compressione batch di immagini con interfaccia grafica e supporto drag & drop.
Pensata per preparare immagini da caricare su siti web, riducendo drasticamente le dimensioni dei file mantenendo l'aspect ratio.

## Caratteristiche

### Compressione Immagini
- **Qualita regolabile**: slider da 1% a 100% per controllare la qualita JPEG/WebP
- **Ridimensionamento percentuale**: scala le immagini dal 5% al 100% della dimensione originale mantenendo sempre l'aspect ratio
- **Formati supportati in input**: JPG, JPEG, PNG, BMP, TIFF, WebP
- **Formati di output**: JPEG, PNG, WebP

### Elaborazione Batch
- **Drag & Drop**: trascina file o intere cartelle direttamente nella finestra dell'applicazione
- **Selezione multipla**: aggiungi centinaia o migliaia di immagini in una volta sola
- **Scansione ricorsiva**: quando aggiungi una cartella, vengono trovate automaticamente tutte le immagini nelle sottocartelle
- **Elaborazione multi-thread**: la compressione avviene in background senza bloccare l'interfaccia

### Opzioni di Output
- **Cartella di output personalizzabile**: scegli dove salvare le immagini compresse
- **Prefisso personalizzabile**: aggiungi un prefisso ai file compressi (default: `compressed_`)
- **Sovrascrittura originali**: opzione per sovrascrivere i file originali invece di crearne di nuovi
- **Salvataggio nella stessa cartella**: se non specifichi una cartella di output, i file vengono salvati accanto agli originali

### Interfaccia Utente
- **Tema scuro** moderno e confortevole
- **Barra di progresso** con percentuale di avanzamento
- **Anteprima dimensioni**: visualizza la dimensione originale e quella compressa per ogni immagine
- **Contatore file**: mostra il numero totale di immagini in lista
- **Report finale**: riepilogo con numero di file compressi e spazio risparmiato

## Esempio d'Uso

Per preparare immagini da caricare su un sito web (es. da 6 MB a ~600 KB):
1. Trascina le immagini nella finestra (o usa "Aggiungi File"/"Aggiungi Cartella")
2. Imposta la **Qualita JPEG** al 10-15%
3. Se le immagini sono troppo grandi, riduci il **Ridimensionamento** (es. 50%)
4. Seleziona la cartella di output
5. Clicca **COMPRIMI TUTTO**

## Installazione

### Da Installer (consigliato)
1. Scarica `Glu2k-Image-Resizer-Setup-1.0.0.exe` dalla sezione [Releases](../../releases)
2. Esegui l'installer
3. L'applicazione sara disponibile nel menu Start e opzionalmente sul desktop

### Da sorgente
```bash
# Clona il repository
git clone https://github.com/glu2k/Glu2k-Image-Resizer.git
cd Glu2k-Image-Resizer

# Installa le dipendenze
pip install -r requirements.txt

# Avvia l'applicazione
python image_squeezer.py
```

## Build

### Creare l'eseguibile
```bash
# Metodo rapido
build.bat

# Oppure manualmente
pip install -r requirements.txt
pyinstaller --onefile --windowed --name "Glu2k-Image-Resizer" image_squeezer.py
```

L'eseguibile verra creato in `dist/Glu2k-Image-Resizer.exe`.

### Creare l'installer
1. Installa [Inno Setup](https://jrsoftware.org/isinfo.php)
2. Apri `installer.iss` con Inno Setup
3. Compila (Ctrl+F9)
4. L'installer verra creato in `installer_output/`

## Requisiti di Sistema

- Windows 10/11
- Nessuna dipendenza esterna richiesta (tutto incluso nell'installer)

## Dipendenze (sviluppo)

- Python 3.9+
- [Pillow](https://pillow.readthedocs.io/) - elaborazione immagini
- [tkinterdnd2](https://github.com/pmgagne/tkinterdnd2) - supporto drag & drop
- [PyInstaller](https://pyinstaller.org/) - creazione eseguibile

## Licenza

MIT License
