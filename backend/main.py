import os
import re
import json
import uvicorn
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Dict, Any

# Import our custom engines
from backend.copilot import PlantBrainCopilot
from backend.pattern_agent import PatternIntelligenceAgent
from backend.ingestion import IngestionPipeline

# Initialize FastAPI
app = FastAPI(title="PlantBrain AI - Industrial Knowledge Intelligence Platform")

# CORS middleware for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# No-cache middleware to force frontend changes immediately
@app.middleware("http")
async def add_no_cache_header(request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "sample_data")
DB_DIR = os.path.join(BASE_DIR, "chroma_db")
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

# Ensure frontend directory exists
os.makedirs(FRONTEND_DIR, exist_ok=True)

# State tracking to allow user to trigger ingestion
data_ingested = False
active_welcome_summary = None
copilot = None
agent = None

class ChatRequest(BaseModel):
    query: str

@app.post("/api/upload")
async def upload_files_endpoint(files: List[UploadFile] = File(...)):
    global data_ingested
    try:
        import shutil
        # Clear existing sample data to start fresh
        if os.path.exists(DATA_DIR):
            shutil.rmtree(DATA_DIR)
        os.makedirs(DATA_DIR, exist_ok=True)
        
        for file in files:
            lower_name = file.filename.lower()
            target_path = DATA_DIR
            
            # Sort files into correct folders
            if "manual" in lower_name:
                target_path = os.path.join(DATA_DIR, "equipment_manuals")
            elif ".md" in lower_name or "safety" in lower_name or "procedure" in lower_name:
                target_path = os.path.join(DATA_DIR, "safety_procedures")
                
            os.makedirs(target_path, exist_ok=True)
            full_path = os.path.join(target_path, os.path.basename(file.filename))
            
            with open(full_path, "wb") as f:
                content = await file.read()
                f.write(content)
                
        # Reset ingestion state since new files are uploaded
        data_ingested = False
        return {"status": "success", "uploaded": len(files)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

def generate_welcoming_summary(file_names, equipment_ids):
    global copilot
    # Try using live Gemini model to generate a custom welcome summary
    if copilot and copilot.gemini_model:
        try:
            prompt = (
                f"We just uploaded and ingested the following industrial datasets into our RAG dashboard:\n"
                f"Ingested Files: {', '.join(file_names)}\n"
                f"Identified Equipment Assets: {', '.join(equipment_ids)}\n\n"
                "Write a very concise, welcoming summary (under 40 words) explaining what safety procedures "
                "and maintenance logs the user can now ask me to check based on these specific files. "
                "Do NOT use markdown headers or list formatting. "
                "Start directly with: 'I have successfully mapped your dataset! You can now query me to...'"
            )
            response = copilot.gemini_model.generate_content(prompt)
            summary = response.text.strip()
            if len(summary) > 20:
                return summary
        except Exception as e:
            print("Failed to generate dynamic welcome summary via Gemini:", e)
            
    # Heuristic fallback summary if Gemini times out or is offline:
    asset_str = f" for assets like {', '.join(equipment_ids[:3])}" if equipment_ids else ""
    file_str = f" (loaded from {', '.join(file_names[:3])})" if file_names else ""
    return (
        f"I have successfully mapped your dataset{file_str}! You can now query me to analyze maintenance history, "
        f"check calibration compliance, and verify LOTO safety procedures{asset_str}."
    )

def auto_initialize_if_data_exists():
    global copilot, agent, data_ingested, active_welcome_summary
    graph_path = os.path.join(DB_DIR, "knowledge_graph.json")
    if os.path.exists(graph_path) and os.path.exists(DATA_DIR) and len(os.listdir(DATA_DIR)) > 0:
        try:
            print("Auto-initializing engines from existing data...")
            copilot = PlantBrainCopilot(DATA_DIR, DB_DIR)
            agent = PatternIntelligenceAgent(DATA_DIR)
            data_ingested = False  # Keep false so first load prompts ingestion again
            
            file_names = [f for f in os.listdir(DATA_DIR) if not f.startswith(".")]
            equipment_ids = [node for node, attr in copilot.graph.nodes(data=True) if attr.get("type") == "equipment"]
            
            # Use quick local heuristic summary for startup to prevent blocking port binding during slow API queries
            asset_str = f" for assets like {', '.join(equipment_ids[:3])}" if equipment_ids else ""
            file_str = f" (loaded from {', '.join(file_names[:3])})" if file_names else ""
            active_welcome_summary = (
                f"I have successfully mapped your dataset{file_str}! You can now query me to analyze maintenance history, "
                f"check calibration compliance, and verify LOTO safety procedures{asset_str}."
            )
            print("Auto-initialization complete. Welcome Summary:", active_welcome_summary)
        except Exception as e:
            print("Failed to auto-initialize on boot:", e)

@app.on_event("startup")
def startup_event():
    auto_initialize_if_data_exists()


@app.post("/api/ingest")
def ingest_data_endpoint():
    global copilot, agent, data_ingested
    try:
        # Pass copilot's existing ChromaDB client reference to prevent UUID conflict errors
        client_ref = copilot.chroma_client if copilot else None
        pipeline = IngestionPipeline(DATA_DIR, DB_DIR, chroma_client=client_ref)
        pipeline.run_all()
        
        # Re-initialize engines with newly built database
        copilot = PlantBrainCopilot(DATA_DIR, DB_DIR)
        agent = PatternIntelligenceAgent(DATA_DIR)
        data_ingested = True
        
        # Get count of nodes/edges for response
        node_count = len(copilot.graph.nodes)
        edge_count = len(copilot.graph.edges)
        
        # Generate dynamic summary
        file_names = [f for f in os.listdir(DATA_DIR) if not f.startswith(".")]
        equipment_ids = [node for node, attr in pipeline.graph.nodes(data=True) if attr.get("type") == "equipment"]
        welcome_summary = generate_welcoming_summary(file_names, equipment_ids)
        global active_welcome_summary
        active_welcome_summary = welcome_summary
        
        return {
            "status": "success",
            "message": "Data ingested and Knowledge Graph built successfully!",
            "nodes": node_count,
            "edges": edge_count,
            "welcome_summary": welcome_summary
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")

@app.get("/api/graph")
def get_graph_endpoint():
    graph_path = os.path.join(DB_DIR, "knowledge_graph.json")
    if not os.path.exists(graph_path):
        return {"nodes": [], "links": []}
    try:
        with open(graph_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
def health_check():
    global data_ingested, active_welcome_summary
    return {
        "status": "healthy",
        "database": "chromadb + networkx",
        "ingested": data_ingested,
        "welcome_summary": active_welcome_summary
    }

@app.post("/api/chat")
def chat_endpoint(req: ChatRequest):
    if not data_ingested or copilot is None:
        return {
            "answer": "⚠️ **System Uninitialized**: Please ingest documents and build the knowledge graph using the button in the top header bar first.",
            "citations": [],
            "confidence": {"level": "Low confidence", "message": "System not ingested yet."}
        }
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    try:
        response = copilot.ask(req.query)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/patterns")
def patterns_endpoint():
    if not data_ingested or agent is None:
        return []
    try:
        patterns = agent.scan_for_patterns()
        return patterns
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/equipment")
def get_equipment_list():
    global copilot, data_ingested
    if not data_ingested or copilot is None or copilot.graph is None:
        return []
    
    # Gather dynamic list of equipment assets from active Knowledge Graph nodes
    equipment_list = []
    for node, attr in copilot.graph.nodes(data=True):
        if attr.get("type") == "equipment":
            equipment_list.append({
                "id": node,
                "name": attr.get("name") or attr.get("device_class") or f"{node} Asset"
            })
            
    # Sort alphabetically by ID for UI consistency
    equipment_list.sort(key=lambda x: x["id"])
    return equipment_list

@app.get("/api/timeline/{equipment_id}")
def get_equipment_timeline(equipment_id: str):
    if not data_ingested or agent is None:
        return []
    eq_id_upper = equipment_id.upper()
    timeline = []
    
    # 1. Load Maintenance Logs
    logs = agent.load_maintenance_logs()
    for l in logs:
        if l["equipment_id"].upper() == eq_id_upper:
            timeline.append({
                "date": l["date"],
                "type": "maintenance",
                "id": l["work_order_id"],
                "title": f"Work Order: {l['issue_reported']}",
                "status": l["status"],
                "badge_class": "badge-maintenance",
                "details": f"Technician: {l['technician']} | Action Taken: {l['action_taken']} | Downtime: {l['downtime_hours']} hrs"
            })
            
    # 2. Load Incidents
    incidents = agent.load_incident_reports()
    for i in incidents:
        if i["equipment_involved"].upper() == eq_id_upper:
            timeline.append({
                "date": i["date"],
                "type": "incident",
                "id": i["report_id"],
                "title": f"Incident: {i['description'][:80]}...",
                "status": f"Severity: {i['severity']}",
                "badge_class": f"badge-incident-{i['severity'].lower()}",
                "details": f"Location: {i['location']} | Root Cause: {i['root_cause']} | Corrective Action: {i['corrective_action']}"
            })
            
    # 3. Load Inspections
    inspections = agent.load_inspection_reports()
    for insp in inspections:
        if insp["equipment_id"].upper() == eq_id_upper:
            status = insp["compliance_status"]
            timeline.append({
                "date": insp["date"],
                "type": "inspection",
                "id": insp["inspection_id"],
                "title": f"Inspection: {insp['findings']}",
                "status": status,
                "badge_class": "badge-compliant" if status.lower() == "compliant" else "badge-noncompliant",
                "details": f"Inspector: {insp['inspector']} | Next Inspection Due: {insp['next_inspection_due']}"
            })
            
    # Sort chronologically
    timeline.sort(key=lambda x: x["date"])
    return timeline

@app.get("/api/compliance")
def get_compliance_status():
    global copilot, data_ingested, agent
    if not data_ingested or copilot is None or agent is None:
        return []
    
    # Extract dynamic equipment lists
    equipment_ids = [node for node, attr in copilot.graph.nodes(data=True) if attr.get("type") == "equipment"]
    
    compliance_package = []
    
    # 1. Factory Act 1948 (Ventilation & Gas Hazards)
    gas_detectors = [eq for eq in equipment_ids if "DET" in eq or "GAS" in eq]
    gas_det = gas_detectors[0] if gas_detectors else "GAS-DET-11"
    
    # Find any gas incident reports
    incidents = agent.load_incident_reports()
    gas_incidents = [inc["report_id"] for inc in incidents if gas_det.lower() in inc["equipment_involved"].lower()]
    inspections = agent.load_inspection_reports()
    gas_insps = [insp["inspection_id"] for insp in inspections if gas_det.lower() in insp["equipment_id"].lower()]
    
    compliance_package.append({
        "regulation": "Factory Act 1948 (Sec 36 - Gas Hazards)",
        "regulatory_body": "Directorate General Factory Advice Service (DGFASLI)",
        "equipment_id": gas_det,
        "status": "Warning" if gas_incidents else "Compliant",
        "requirement": "Verify Methane gas detectors are calibrated every 30 days and ventilation meets safety clearance.",
        "evidence": {
            "inspections": gas_insps[:2],
            "incidents": gas_incidents[:2],
            "last_audit": "2026-06-10"
        }
    })
    
    # 2. PESO Rules (Pressure Equipment Safety Regulations)
    compressors = [eq for eq in equipment_ids if "COMP" in eq or "VALVE" in eq]
    comp = compressors[0] if compressors else "COMPRESSOR-5"
    comp_incidents = [inc["report_id"] for inc in incidents if comp.lower() in inc["equipment_involved"].lower()]
    comp_insps = [insp["inspection_id"] for insp in inspections if comp.lower() in insp["equipment_id"].lower()]
    
    compliance_package.append({
        "regulation": "PESO Pressure Vessels Rules 2016",
        "regulatory_body": "Petroleum and Explosives Safety Organisation (PESO)",
        "equipment_id": comp,
        "status": "Non-Compliant" if comp_incidents else "Compliant",
        "requirement": "Annual pressure vessel hydrostatic tests, safety relief valve calibration certification.",
        "evidence": {
            "inspections": comp_insps[:2],
            "incidents": comp_incidents[:2],
            "last_audit": "2026-05-18"
        }
    })
    
    # 3. OISD Standards (Oil Industry Safety Directorate)
    loto_devices = [eq for eq in equipment_ids if "LOTO" in eq]
    loto = loto_devices[0] if loto_devices else "LOTO-2026"
    
    compliance_package.append({
        "regulation": "OISD-STD-105 (Work Permit System)",
        "regulatory_body": "Oil Industry Safety Directorate (OISD)",
        "equipment_id": loto,
        "status": "Compliant",
        "requirement": "Lock Out Tag Out compliance audit records, work permit system verification for hot work.",
        "evidence": {
            "inspections": ["INSP-903"],
            "incidents": [],
            "last_audit": "2026-07-01"
        }
    })
    
    return compliance_package

@app.get("/api/rca/{equipment_id}")
def get_root_cause_analysis(equipment_id: str):
    eq_id = equipment_id.upper()
    global copilot, agent, data_ingested
    
    # 1. Fetch live timeline logs for context
    timeline_events = get_equipment_timeline(equipment_id)
    events_text = "\n".join([f"- Date: {e['date']} | Type: {e['type']} | Title: {e['title']} | Details: {e['details']}" for e in timeline_events])
    
    # 2. Query ChromaDB for extra manual context
    manual_context = ""
    if data_ingested and copilot and copilot.collection:
        try:
            results = copilot.collection.query(
                query_texts=[f"failure incident root cause analysis {eq_id}"],
                n_results=3
            )
            docs = results.get("documents", [])
            if docs:
                # Flatten the list of lists
                flat_docs = [item for sublist in docs for item in sublist]
                manual_context = "\n".join(flat_docs)
        except Exception as e:
            print("ChromaDB query failed in RCA generation:", e)

    # 3. Ask Gemini to generate the 5-Whys JSON
    if data_ingested and copilot and copilot.gemini_model:
        try:
            prompt = (
                f"You are a principal industrial failure analyst. Perform a Root Cause Analysis (RCA) "
                f"using the '5 Whys' method for the industrial asset: {eq_id}.\n\n"
                f"Historical timeline logs:\n{events_text}\n\n"
                f"Retrieved document context:\n{manual_context}\n\n"
                "Formulate a structured analysis. You MUST return a single valid JSON block containing exactly the following keys (do NOT wrap in markdown code fences or code formatting, return raw json string):\n"
                "{\n"
                '  "equipment_id": "the asset tag ID",\n'
                '  "incident": "a brief 1-sentence description of the main failure event",\n'
                '  "whys": [\n'
                '    "1. Why: [First symptom description]",\n'
                '    "2. Why: [Second layer description]",\n'
                '    "3. Why: [Third layer description]",\n'
                '    "4. Why: [Fourth layer description]",\n'
                '    "5. Why (Root Cause): [Traced systemic root cause, e.g. inspection gaps or missing procedures]"\n'
                '  ],\n'
                '  "corrective_action": "a concise, actionable corrective action to prevent future recurrence",\n'
                '  "technician": "a professional safety inspector name (e.g. Sunil Mehta)"\n'
                "}\n"
            )
            response = copilot.gemini_model.generate_content(prompt)
            resp_text = response.text.strip()
            
            # Clean markdown code block wraps if Gemini outputs them
            if resp_text.startswith("```"):
                resp_text = re.sub(r"^```(?:json)?\n", "", resp_text)
                resp_text = re.sub(r"\n```$", "", resp_text)
            
            parsed = json.loads(resp_text)
            # Basic validation
            if "whys" in parsed and len(parsed["whys"]) == 5:
                return parsed
        except Exception as e:
            print("Failed to generate dynamic Gemini RCA, falling back to static:", e)

    # Fallback to local structured data
    if "COMPRESSOR" in eq_id or "VALVE" in eq_id:
        return {
            "equipment_id": eq_id,
            "incident": "High pressure valve failure and gas backup on 2026-06-15",
            "whys": [
                "1. Why: Gas compressor pressure relief valve (VALVE-102) was stuck closed, triggering high pressure alarm.",
                "2. Why: Scale build-up and mechanical friction seized the valve plunger.",
                "3. Why: Missed scale flushing routine check in maintenance work orders.",
                "4. Why: Lubricant oil and water scale treatment records were not checked for VALVE-102.",
                "5. Why (Root Cause): Fragmented inspection records were stored in a separate database and compliance alert was not integrated."
            ],
            "corrective_action": "Integrate Pattern Intelligence Agent to auto-alert the operations team 15 days before valve calibration becomes overdue.",
            "technician": "Rajesh Kumar (Safety Lead)"
        }
    elif "DET" in eq_id or "GAS" in eq_id:
        return {
            "equipment_id": eq_id,
            "incident": "Methane gas sensor drift audit failure (+18% drift) on 2026-07-02",
            "whys": [
                "1. Why: Sensor failed to record methane levels within Factory Act +/-5% safety range.",
                "2. Why: Catalyst bead sensor element experienced poisoning due to heavy hydrocarbons.",
                "3. Why: Scheduled 30-day system cleaning and calibration check was missed.",
                "4. Why: Inadequate technician allocation for hazardous gas monitoring zones.",
                "5. Why (Root Cause): Overdue inspection reminder was not flagged because schedule was not linked to live incident dashboards."
            ],
            "corrective_action": "Apply automatic schedule updates on the unified graph and block permit-to-work requests for area if gas sensors are non-compliant.",
            "technician": "Sunita Rao (Compliance Inspector)"
        }
    else:
        return {
            "equipment_id": eq_id,
            "incident": f"Unplanned maintenance outage on asset {eq_id}",
            "whys": [
                f"1. Why: Asset {eq_id} experienced sudden operational slowdown.",
                "2. Why: Friction wear was not addressed during standard shift routines.",
                "3. Why: Shift logs and work order updates were not reviewed.",
                "4. Why: Training materials and OEM guides were stored in a separate offline database.",
                "5. Why (Root Cause): Retiree operational knowledge was not codified, leaving newer technicians without historical incident context."
            ],
            "corrective_action": "Verify all work order logs and index technical manuals into ChromaDB RAG Copilot database.",
            "technician": "Plant Operations Desk"
        }

# Mount frontend files at the end to allow API routes precedence
if os.path.exists(FRONTEND_DIR):
    @app.get("/")
    def read_index():
        global data_ingested
        data_ingested = False  # Reset state on browser reload/refresh!
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))
        
    @app.get("/index.html")
    def read_index_html():
        global data_ingested
        data_ingested = False  # Reset state on direct file path loads!
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))
        
    app.mount("/", StaticFiles(directory=FRONTEND_DIR), name="frontend")
else:
    @app.get("/")
    def index_fallback():
        return {"message": "Frontend files not found. Mount frontend directory."}

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
