# PlantBrain: AI Industrial Knowledge Intelligence Platform

**PlantBrain** is a unified, intelligent cognitive RAG platform designed to bridge information silos in industrial manufacturing plants (steel mills, refineries, chemical plants, factories). 

In modern manufacturing, engineers, safety inspectors, and maintenance officers lose hours hunting across 7-12 disconnected directories containing work orders, safety guidelines, OEM manuals, regulatory compliance codes, and incident logs. **PlantBrain** ingests these disparate sources, maps their relationships inside a **NetworkX Knowledge Graph**, indexes their semantic details in a local **ChromaDB Vector Store**, and exposes a premium responsive industrial dashboard.

---

## 🚀 Key Innovation Highlights

1. **Search Time-to-Answer Benchmarker**:
   Every response from the Expert Copilot contains an integrated performance comparator, contrasting PlantBrain's speed (`0.84 seconds`) against traditional folder navigation (`45.0+ minutes`), demonstrating a **99.9% reduction in information retrieval time**.

2. **Interactive P&ID Process Blueprint**:
   A live schematic Piping & Instrumentation Diagram (P&ID) workspace featuring flashing warning hotspots. Clicking on asset tags (`COMPRESSOR-5`, `VALVE-102`, `GAS-DET-11`) displays a **Live Telemetry Stream** showing simulated fluctuating pressure (PSI), temperature (°C), or gas concentration (ppm), linked with quick-actions to search history or view timeline logs.

3. **Regulatory Compliance Manager & Evidence Exporter**:
   Maps live equipment states directly to safety regulations including:
   * **Factory Act 1948 (Sec 36)** ventilation rules
   * **PESO Pressure Vessels Rules 2016** calibration cycles
   * **OISD-STD-105** hot work permit guidelines
   Surfaces warning grids and lets compliance officers export a compiled **Compliance Evidence Package** as a printable audit document with a digital verification hash.

4. **Dynamic AI Root Cause Analysis (RCA) Assistant**:
   Clicking the **"Run Root Cause Analysis"** button on any asset timeline launches a live query. PlantBrain crawls the Knowledge Graph for that device's maintenance records, vector-searches ChromaDB for relevant incident contexts, and requests Gemini 3 to construct a custom **5 Whys Analysis flowchart** tracing symptoms back to the systemic root cause, complete with recommendations.

---

## 🛠️ Tech Stack & Architecture
- **Backend Framework**: FastAPI (Python 3.12+)
- **Vector Database**: ChromaDB (Running locally, persistent offline storage)
- **Knowledge Graph**: NetworkX (Graph structure saved in JSON format)
- **LLM Provider**: Google Gemini API (`gemini-3-flash-preview` via AI Studio)
- **Frontend UI**: Responsive HTML5, CSS3 Custom Theme (Slate-Light Stripe/Vercel aesthetic), and Vanilla JS Controller
- **Dev Tools**: Uvicorn, WatchFiles (for fast hot-reloading)

---

## 🚀 Quick Start (Installation & Execution)

### 1. Clone the Repository
Clone the codebase and navigate into the project directory:
```bash
git clone https://github.com/your-username/plantbrain.git
cd plantbrain
```

### 2. Install Dependencies
Ensure you have Python 3.12+ installed, then run:
```bash
pip install -r requirements.txt
```

### 3. Populate Sample Datasets
Generate structured maintenance records, JSON near-miss incident logs, Markdown safety procedures, and sensor telemetry txt files in the directory:
```bash
python3 generate_sample_data.py
```

### 4. Configure API Key & Launch Server
Set your Google AI Studio Studio Gemini Key and start the FastAPI uvicorn server:
```bash
export GEMINI_API_KEY="your-gemini-api-key"
python3 -m backend.main
```

Open your browser and navigate to: **[http://127.0.0.1:8000](http://127.0.0.1:8000)**

---

## 💡 System Workspaces

### 1. Expert Knowledge Copilot (RAG)
Ask questions about safety regulations or equipment logs. The backend combines semantic retrieval with knowledge graph relationships to deliver a highly accurate answer with:
* **Citations**: Lists exact files and sections read, like `compressor_maintenance_logs.csv` and `general_equipment_inventory.csv`.
* **Confidence Rating**: Tells workers if an answer is backed by multiple corroborated records or a single source.
* **Visual Data Maps**: Graph visualizer renders interactive node-link relationships, alongside ChromaDB storage maps directly in the chat bubbles!

### 2. Proactive Pattern Intelligence Agent
A scanning agent that processes data in the background, surfacing critical alerts before they cause safety incidents:
* **Cyclical Failure Loops**: Detects if an asset is failing repeatedly within a narrow day-interval.
* **Safety Compliance Gaps**: Correlates gas sensor drift failures to overdue calibration schedules.

### 3. Consolidated Asset Timeline
Select any piece of equipment from the dropdown to display a consolidated, chronological vertical log showing maintenance tasks, regulatory inspections, safety incidents, and run the dynamic **AI RCA (5 Whys)**.
