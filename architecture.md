# PlantBrain Architecture Diagram Description

Below is the architectural layout of the **PlantBrain** Industrial Knowledge Intelligence Platform. This description maps out how data flows from disparate industrial sources to the interactive web dashboard.

---

```mermaid
graph TD
    %% Define styles for distinct layers
    classDef source fill:#f8fafc,stroke:#cbd5e1,stroke-width:1.5px,color:#0f172a;
    classDef pipeline fill:#eff6ff,stroke:#3b82f6,stroke-width:1.5px,color:#1e3a8a;
    classDef storage fill:#f0fdf4,stroke:#10b981,stroke-width:1.5px,color:#064e3b;
    classDef engine fill:#faf5ff,stroke:#d946ef,stroke-width:1.5px,color:#581c87;
    classDef ui fill:#fff7ed,stroke:#ea580c,stroke-width:1.5px,color:#7c2d12;

    subgraph Layer1 [1. Heterogeneous Data Sources]
        SRC_WO[maintenance_logs.csv<br/>Work Orders]
        SRC_SOP[safety_procedures/*.md<br/>LOTO & Confined Space SOPs]
        SRC_INC[incident_reports.json<br/>Failures & Near-Miss Logs]
        SRC_OEM[equipment_manuals/*.md<br/>OEM Spec Manuals]
        SRC_INSP[inspection_reports.csv<br/>Regulatory Site Inspections]
        SRC_SENS[sensor_readings.txt<br/>Live Pressure/Temp Telemetry Logs]
    end

    subgraph Layer2 [2. Ingestion & Schema Mapper]
        ING_ZONE[Drag-and-Drop Uploader Zone<br/>Overview Reset Trigger]
        ING_PIPE[Ingestion Pipeline<br/>backend/ingestion.py]
        ING_SCHEMA[Column-Matching Heuristics<br/>Dynamic Header Schema Mapper]
        ING_EXT[Entity & Relation Extractor<br/>Equipment Tag Linking]
    end

    subgraph Layer3 [3. Dual Storage Engines]
        DB_VEC[(ChromaDB Vector Store<br/>Local Semantic Chunk Index)]
        DB_KG[(NetworkX Knowledge Graph<br/>Relational Node-Link JSON Store)]
    end

    subgraph Layer4 [4. AI & Pattern Intelligence Engines]
        ENG_COPILOT[RAG Expert Copilot<br/>backend/copilot.py]
        ENG_GEMINI[Google Gemini API<br/>gemini-3-flash-preview]
        ENG_BENCH[Search Speed Benchmarker<br/>Execution Latency Contrast]
        ENG_AGENT[Pattern Intelligence Agent<br/>backend/pattern_agent.py]
        ENG_RCA[AI RCA 5-Whys Assistant<br/>Context Assembler]
    end

    subgraph Layer5 [5. Vercel-Style Light UI Homepage]
        UI_NAV[Top Horizontal Navigation Header<br/>Overview, Copilot, Insights, Timeline, Blueprint, Compliance]
        UI_HERO[Welcome Hero Banner<br/>CSS-Animating SVG Robotic Arm]
        
        UI_GRID[2x2 Modules Grid]
        UI_MOD1[Module 01: Expert Copilot<br/>Chat History & suggestion chips]
        UI_MOD2[Module 02: P&ID Blueprint<br/>Flowing streams & Hotspot alerts]
        UI_MOD3[Module 03: Asset Timeline<br/>Consolidated work log & RCA]
        UI_MOD4[Module 04: Compliance Manager<br/>OSHA/PESO/OISD standards]
        
        UI_ALERTS[Live Safety Alerts Sidebar<br/>Bell icon & Critical warning list]
    end

    subgraph Layer6 [6. Special Workspace Views]
        VIEW_GRAPH[Force-Directed physics graph<br/>Canvas simulation bubble]
        VIEW_BLUE[Interactive SVG schematic diagram<br/>Live PLC telemetry dials]
        VIEW_RCA[5-Whys Analysis flow tree<br/>Corrective recommendations]
        VIEW_HEAT[Regulatory Risk Heatmap<br/>Signed Evidence Exporter + Hashes]
    end

    %% Apply CSS classes to nodes
    class SRC_WO,SRC_SOP,SRC_INC,SRC_OEM,SRC_INSP,SRC_SENS source;
    class ING_ZONE,ING_PIPE,ING_SCHEMA,ING_EXT pipeline;
    class DB_VEC,DB_KG storage;
    class ENG_COPILOT,ENG_GEMINI,ENG_BENCH,ENG_AGENT,ENG_RCA engine;
    class UI_NAV,UI_HERO,UI_GRID,UI_MOD1,UI_MOD2,UI_MOD3,UI_MOD4,UI_ALERTS ui;
    class VIEW_GRAPH,VIEW_BLUE,VIEW_RCA,VIEW_HEAT ui;

    %% Data Flow Connections
    SRC_WO & SRC_SOP & SRC_INC & SRC_OEM & SRC_INSP & SRC_SENS --> ING_ZONE
    ING_ZONE --> ING_PIPE
    ING_PIPE --> ING_SCHEMA
    ING_SCHEMA --> ING_EXT
    
    ING_EXT --> |Generate Chunk Embeddings| DB_VEC
    ING_EXT --> |Register Node Connections| DB_KG

    DB_VEC & DB_KG --> |Dual Retrieval Context| ENG_COPILOT
    ENG_COPILOT <--> |Context-Augmented Prompts| ENG_GEMINI
    ENG_COPILOT --> |Log Exec Latency| ENG_BENCH

    DB_KG --> |Scan Maintenance Loops & Calibration| ENG_AGENT
    DB_KG & DB_VEC --> |Extract Failure Logs| ENG_RCA
    ENG_RCA <--> |Prompt 5-Whys Synthesis| ENG_GEMINI

    %% UI Connections
    ENG_COPILOT --> |Cited Answers & Data Maps| UI_MOD1
    ENG_BENCH --> |Speed stats 99.9% saved| UI_MOD1
    UI_MOD1 --> |Click Graph relations| VIEW_GRAPH
    
    UI_NAV --> UI_HERO
    UI_HERO --> UI_GRID
    UI_GRID --> UI_MOD1 & UI_MOD2 & UI_MOD3 & UI_MOD4
    
    ENG_AGENT --> |Push live incident cards| UI_ALERTS
    
    UI_MOD2 --> |Click tag hotspots| VIEW_BLUE
    UI_MOD3 --> |Click Run Root Cause| VIEW_RCA
    UI_MOD4 --> |Interact grid cell filters| VIEW_HEAT

    %% Enforce vertical layer alignment
    Layer1 --> Layer2
    Layer2 --> Layer3
    Layer3 --> Layer4
    Layer4 --> Layer5
    Layer5 --> Layer6
```

---

## Technical Component Breakdown

### 1. Heterogeneous Data Sources
* **Structured Logs**: CSV files containing chronological operations, technicians, and compliance status.
* **Unstructured SOPs & OEM Manuals**: Text/Markdown files containing safety instructions, OEM guidelines, and engineering specs.
* **Incident Records**: JSON files containing near-miss details, severity, root causes, and corrective actions.
* **Sensor Streams**: Text files containing live pressure and temperature readings.

### 2. Ingestion & Dynamic Schema Mapper
* Reads any uploaded files dynamically using fallback CSV/JSON parsers.
* Performs column-matching to find equipment IDs, dates, and technicians across arbitrary table formats.
* Supports plain `.txt` and raw `.md` documents found directly inside the root import directory.

### 3. Dual Storage Model
* **Vector Database (ChromaDB)**: Chunks documents into logical segments, embeds them, and indexes them locally for high-speed semantic search.
* **Knowledge Graph (NetworkX)**: Links equipment IDs to their work orders, incidents, safety SOPs, manuals, and inspections. This structure ensures that relational queries can traverse paths immediately.

### 4. Engine Layer
* **Expert RAG Copilot**: Extracts equipment nodes in a user's question, fetches its linked graph nodes, merges them with semantic vector hits, and requests Gemini to generate a cited response.
* **Search Speed Benchmarker**: Calculates execution duration and displays a speed comparison indicator showing **99.9% Time Saved** vs manual folder lookups.
* **Pattern Intelligence Agent**: Scans maintenance frequency, failure intervals, and near-miss logs to find operational risks (e.g., a device failing repeatedly within a narrow day-interval).
* **AI Root Cause Analysis (RCA) Assistant**: Traces chronologies on the Knowledge Graph and fetches manuals from ChromaDB, feeding them to Gemini to synthesize a dynamic **5 Whys Analysis flowchart** on the fly.

### 5. Web Interface
* Served via **FastAPI** as a single-page app.
* Custom styled using a premium glassmorphic Slate-Light theme, featuring interactive onboarding, dynamic loading skeletons, active workspace transitions, and responsive chatbot controls.
* **Visual Additions**: Custom-drawn P&ID Blueprint with flashing sensor hotspots, live telemetry gauges, and interactive Regulatory Risk Heatmap matrices.
