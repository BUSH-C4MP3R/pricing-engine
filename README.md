# Biologics Pricing Model

A pricing engine for Bio-Techne's Maurice and iCE3 product lines. It reads
historical sales data with pandas to compute current prices and price
elasticity per product category, reads macro/inflation commentary (PDFs or
text files) with a local LLM (RAG), and combines both into a recommended
price change per category. Everything runs locally — no cloud API keys
required.

This guide assumes a brand-new computer with nothing installed yet.

## What you'll need

- **macOS, Linux, or Windows**
- **Python 3.11 or newer**
- **Git**
- **Ollama** (runs a small LLM locally — only used to read macro/inflation
  documents, never touches the sales data)
- **Your own sales data CSV** — not included in this repo (see step 4)

## 1. Install Python

Check if you already have it:

```bash
python3 --version
```

If that fails or shows a version older than 3.11:
- **macOS**: `brew install python3` (install [Homebrew](https://brew.sh) first if you don't have it), or download from [python.org](https://www.python.org/downloads/)
- **Windows**: download the installer from [python.org](https://www.python.org/downloads/) — check "Add python.exe to PATH" during install
- **Linux**: `sudo apt install python3 python3-venv python3-pip` (Debian/Ubuntu) or your distro's equivalent

## 2. Install Git

```bash
git --version
```

If that fails:
- **macOS**: `brew install git`
- **Windows**: download from [git-scm.com](https://git-scm.com/downloads)
- **Linux**: `sudo apt install git`

## 3. Get the code

```bash
git clone https://github.com/ProteinSimple/Biologics_Pricing_Model.git
cd Biologics_Pricing_Model
```

## 4. Set up a virtual environment and install dependencies

```bash
python3 -m venv venv

# macOS/Linux:
source venv/bin/activate
# Windows (Command Prompt):
venv\Scripts\activate.bat
# Windows (PowerShell):
venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

Leave this environment activated for every command below — you'll see
`(venv)` at the start of your terminal prompt when it's active. If you close
your terminal, just re-run the `source`/`activate` line to pick up where you
left off (no need to reinstall anything).

## 5. Install Ollama (the local LLM)

Download and install from **[ollama.com/download](https://ollama.com)** for
your OS, then pull the model this project uses:

```bash
ollama pull llama3.1
```

Start the Ollama server (skip this if the installer already set it up to run
automatically in the background — check with `ollama list`):

```bash
# macOS, if installed via Homebrew:
brew services start ollama
# Otherwise, on any OS:
ollama serve
```

You can leave this running in its own terminal tab/window.

## 6. Add your data

### Required: sales data

The sales CSV is **not included in this repo** (it's excluded via
`.gitignore` since it's large and sensitive). Place your file at:

```
data/sales/Biologics Sales Data (2)_2020-2026.csv
```

using that exact name — that's the path `generate_reports.py` reads from. If
your file has a different name, either rename it to match, or edit the `CSV`
constant near the top of `generate_reports.py`.

The file should be a comma-separated export (latin-1 encoded) with at least
these columns: `OrderDate`, `ItemCode`, `ItemDescription`, `ShippedQty`,
`ReportingSalesPrice`, `CustomerNo`.

### Optional: macro/inflation documents

Drop any PDF or `.txt` files with inflation/cost commentary into:

```
data/macro/
```

The app reads whatever's in that folder and extracts an inflation rate per
bucket (Instruments/Consumables/Service) via the local LLM. If you skip this
step, the model just uses a default inflation rate (3%) for every category —
everything still runs fine without it.

## 7. Run it

### Option A: Streamlit UI (recommended)

```bash
streamlit run app.py
```

This opens a browser tab (usually `http://localhost:8501`) where you can
upload macro documents, review/override the extracted inflation rates, and
click "Run Pricing" to see results by product line (Maurice / iCE3), broken
down by category.

### Option B: command line

```bash
python3 pipeline.py
```

This prices every category and writes the results to
`output/pricing_results.json`, printing a summary to the terminal as it goes.

## 8. Verify everything works

```bash
python3 -m pytest tests/test_pipeline.py tests/test_schema.py -v
```

All tests should pass. This doesn't require your sales data or Ollama to be
set up for most tests, but a couple read `output/pricing_results.json`, so
run step 7 (Option A or B) at least once first.

## Troubleshooting

- **First run is slow / needs internet** — the very first time you run
  anything, `sentence-transformers` downloads a small embedding model
  (~90MB) from Hugging Face. After that it's cached locally and works
  offline. If you want to force offline mode after that first run, create a
  `.env` file in the project root with `HF_HUB_OFFLINE=1` — but don't set
  that before the first run, or the download will fail.
- **Ollama connection errors** — make sure `ollama serve` (or the background
  service) is actually running, and that `ollama list` shows `llama3.1`.
- **"Not enough yearly history to price" warnings** — a category needs at
  least one full year of sales data to be priced; this is expected for very
  new or very low-volume product lines.
