import os
import json
import csv
import re
import pandas as pd
import networkx as nx
import chromadb
from chromadb.utils import embedding_functions

class IngestionPipeline:
    def __init__(self, data_dir, db_dir, chroma_client=None):
        self.data_dir = data_dir
        self.db_dir = db_dir
        self.graph = nx.Graph()
        
        # Initialize or reuse persistent ChromaDB client
        if chroma_client:
            self.chroma_client = chroma_client
        else:
            self.chroma_client = chromadb.PersistentClient(path=db_dir)
        # Using default embedding function (downloads ONNX MiniLM-L6-v2)
        self.embed_fn = embedding_functions.DefaultEmbeddingFunction()
        
        # Get or create collection, then clear existing documents to avoid UUID invalidation errors in concurrent clients
        try:
            self.collection = self.chroma_client.get_collection(
                name="plantbrain_docs",
                embedding_function=self.embed_fn
            )
            # Fetch all existing document IDs and delete them to start fresh
            existing = self.collection.get()
            if existing and existing["ids"]:
                self.collection.delete(ids=existing["ids"])
        except Exception:
            self.collection = self.chroma_client.create_collection(
                name="plantbrain_docs",
                embedding_function=self.embed_fn
            )

    def extract_equipment_ids(self, text):
        # Regex to find equipment IDs like PUMP-204, BOILER-3, GAS-DET-11, VALVE-102, COMPRESSOR-5
        pattern = r"\b[A-Z]{3,10}-\d{1,4}\b"
        return list(set(re.findall(pattern, text)))

    def ingest_maintenance_logs(self, file_path=None):
        if file_path is None:
            file_path = os.path.join(self.data_dir, "maintenance_logs.csv")
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            return
        
        df = pd.read_csv(file_path)
        for _, row in df.iterrows():
            wo_id = str(row["work_order_id"])
            equip_id = str(row["equipment_id"])
            equip_name = str(row["equipment_name"])
            date = str(row["date"])
            tech = str(row["technician"])
            issue = str(row["issue_reported"])
            action = str(row["action_taken"])
            downtime = float(row["downtime_hours"])
            status = str(row["status"])
            
            # Text for vector search
            text_content = (
                f"Maintenance Work Order: {wo_id}\n"
                f"Equipment ID: {equip_id} ({equip_name})\n"
                f"Date: {date}\n"
                f"Technician: {tech}\n"
                f"Issue Reported: {issue}\n"
                f"Action Taken: {action}\n"
                f"Downtime: {downtime} hours\n"
                f"Status: {status}"
            )
            
            # Ingest to ChromaDB
            metadata = {
                "source": os.path.basename(file_path),
                "type": "maintenance",
                "work_order_id": wo_id,
                "equipment_id": equip_id,
                "date": date,
                "technician": tech,
                "downtime_hours": downtime
            }
            self.collection.add(
                documents=[text_content],
                metadatas=[metadata],
                ids=[f"maintenance_{wo_id}"]
            )
            
            # Build Graph Nodes & Edges
            self.graph.add_node(equip_id, type="equipment", label=equip_id, name=equip_name)
            self.graph.add_node(wo_id, type="maintenance", label=wo_id, date=date, technician=tech, downtime=downtime)
            self.graph.add_edge(equip_id, wo_id, relation="maintained_on")
            
            # Check for other mentions
            other_equips = self.extract_equipment_ids(issue + " " + action)
            for other_eq in other_equips:
                if other_eq != equip_id:
                    self.graph.add_node(other_eq, type="equipment", label=other_eq)
                    self.graph.add_edge(wo_id, other_eq, relation="references_equipment")

    def ingest_safety_procedures(self):
        dir_path = os.path.join(self.data_dir, "safety_procedures")
        if not os.path.exists(dir_path):
            print(f"Directory not found: {dir_path}")
            return
            
        for filename in os.listdir(dir_path):
            if filename.endswith(".md"):
                file_path = os.path.join(dir_path, filename)
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                
                # Split markdown into sections by header to get better chunking
                sections = re.split(r"(?=\n#+ )", "\n" + content)
                for idx, section in enumerate(sections):
                    section = section.strip()
                    if not section:
                        continue
                    
                    # Extract SOP code (e.g. SOP-SAFETY-01) or title
                    first_line = section.split("\n")[0]
                    title_match = re.search(r"#+\s*(.*)", first_line)
                    title = title_match.group(1) if title_match else filename
                    
                    text_content = f"Document: {filename} - Section: {title}\nContent:\n{section}"
                    
                    # Store in ChromaDB
                    sop_id = f"sop_{filename.split('.')[0]}_{idx}"
                    metadata = {
                        "source": f"safety_procedures/{filename}",
                        "type": "procedure",
                        "section_title": title,
                        "filename": filename
                    }
                    self.collection.add(
                        documents=[text_content],
                        metadatas=[metadata],
                        ids=[sop_id]
                    )
                    
                    # Add to graph
                    sop_node = filename.split(".md")[0]
                    self.graph.add_node(sop_node, type="procedure", label=sop_node, title=title)
                    
                    # Detect equipment mentioned in SOP section
                    equips = self.extract_equipment_ids(section)
                    for eq in equips:
                        self.graph.add_node(eq, type="equipment", label=eq)
                        self.graph.add_edge(sop_node, eq, relation="governs_safety")

    def ingest_incident_reports(self, file_path=None):
        if file_path is None:
            file_path = os.path.join(self.data_dir, "incident_reports.json")
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            return
            
        with open(file_path, "r", encoding="utf-8") as f:
            incidents = json.load(f)
            
        for inc in incidents:
            inc_id = inc["report_id"]
            date = inc["date"]
            location = inc["location"]
            equip_id = inc["equipment_involved"]
            description = inc["description"]
            root_cause = inc["root_cause"]
            severity = inc["severity"]
            corrective = inc["corrective_action"]
            
            text_content = (
                f"Incident Report: {inc_id}\n"
                f"Date: {date}\n"
                f"Location: {location}\n"
                f"Equipment Involved: {equip_id}\n"
                f"Severity: {severity}\n"
                f"Description: {description}\n"
                f"Root Cause: {root_cause}\n"
                f"Corrective Action: {corrective}"
            )
            
            # Store in ChromaDB
            metadata = {
                "source": os.path.basename(file_path),
                "type": "incident",
                "report_id": inc_id,
                "equipment_id": equip_id,
                "date": date,
                "severity": severity
            }
            self.collection.add(
                documents=[text_content],
                metadatas=[metadata],
                ids=[f"incident_{inc_id}"]
            )
            
            # Add to graph
            self.graph.add_node(inc_id, type="incident", label=inc_id, severity=severity, date=date)
            self.graph.add_node(equip_id, type="equipment", label=equip_id)
            self.graph.add_edge(equip_id, inc_id, relation="involved_in")
            
            # Find other equipment in description/actions
            other_equips = self.extract_equipment_ids(description + " " + root_cause + " " + corrective)
            for other_eq in other_equips:
                if other_eq != equip_id:
                    self.graph.add_node(other_eq, type="equipment", label=other_eq)
                    self.graph.add_edge(inc_id, other_eq, relation="references_equipment")

    def ingest_equipment_manuals(self):
        dir_path = os.path.join(self.data_dir, "equipment_manuals")
        if not os.path.exists(dir_path):
            print(f"Directory not found: {dir_path}")
            return
            
        for filename in os.listdir(dir_path):
            if filename.endswith(".md"):
                file_path = os.path.join(dir_path, filename)
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                
                # Try to extract equipment ID from filename (e.g., PUMP-204_manual.md -> PUMP-204)
                equip_match = re.search(r"([A-Z]{3,10}-\d{1,4})", filename)
                equip_id = equip_match.group(1) if equip_match else None
                
                # Split manual into sections
                sections = re.split(r"(?=\n#+ )", "\n" + content)
                for idx, section in enumerate(sections):
                    section = section.strip()
                    if not section:
                        continue
                    
                    first_line = section.split("\n")[0]
                    title_match = re.search(r"#+\s*(.*)", first_line)
                    title = title_match.group(1) if title_match else filename
                    
                    text_content = f"Equipment Manual Excerpt: {filename} - Section: {title}\nContent:\n{section}"
                    
                    # Store in ChromaDB
                    manual_id = f"manual_{filename.split('.')[0]}_{idx}"
                    metadata = {
                        "source": f"equipment_manuals/{filename}",
                        "type": "manual",
                        "equipment_id": equip_id or "UNKNOWN",
                        "section_title": title
                    }
                    self.collection.add(
                        documents=[text_content],
                        metadatas=[metadata],
                        ids=[manual_id]
                    )
                    
                    # Add to graph
                    manual_node = filename.split(".md")[0]
                    self.graph.add_node(manual_node, type="manual", label=manual_node, title=title)
                    if equip_id:
                        self.graph.add_node(equip_id, type="equipment", label=equip_id)
                        self.graph.add_edge(manual_node, equip_id, relation="describes_equipment")
                    
                    # Extract any other referenced equipment
                    equips = self.extract_equipment_ids(section)
                    for eq in equips:
                        if eq != equip_id:
                            self.graph.add_node(eq, type="equipment", label=eq)
                            self.graph.add_edge(manual_node, eq, relation="references_equipment")

    def ingest_inspection_reports(self, file_path=None):
        if file_path is None:
            file_path = os.path.join(self.data_dir, "inspection_reports.csv")
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            return
            
        df = pd.read_csv(file_path)
        for _, row in df.iterrows():
            insp_id = str(row["inspection_id"])
            equip_id = str(row["equipment_id"])
            date = str(row["date"])
            inspector = str(row["inspector"])
            findings = str(row["findings"])
            status = str(row["compliance_status"])
            next_due = str(row["next_inspection_due"])
            
            text_content = (
                f"Inspection Report: {insp_id}\n"
                f"Equipment ID: {equip_id}\n"
                f"Date: {date}\n"
                f"Inspector: {inspector}\n"
                f"Findings: {findings}\n"
                f"Compliance Status: {status}\n"
                f"Next Inspection Due: {next_due}"
            )
            
            # Store in ChromaDB
            metadata = {
                "source": os.path.basename(file_path),
                "type": "inspection",
                "inspection_id": insp_id,
                "equipment_id": equip_id,
                "date": date,
                "inspector": inspector,
                "compliance_status": status
            }
            self.collection.add(
                documents=[text_content],
                metadatas=[metadata],
                ids=[f"inspection_{insp_id}"]
            )
            
            # Add to graph
            self.graph.add_node(insp_id, type="inspection", label=insp_id, date=date, inspector=inspector, status=status)
            self.graph.add_node(equip_id, type="equipment", label=equip_id)
            self.graph.add_edge(equip_id, insp_id, relation="inspected_under")
            
            # Check for other mentions
            other_equips = self.extract_equipment_ids(findings)
            for other_eq in other_equips:
                if other_eq != equip_id:
                    self.graph.add_node(other_eq, type="equipment", label=other_eq)
                    self.graph.add_edge(insp_id, other_eq, relation="references_equipment")

    def save_graph(self):
        graph_path = os.path.join(self.db_dir, "knowledge_graph.json")
        data = nx.node_link_data(self.graph)
        with open(graph_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        print(f"Saved Knowledge Graph with {len(self.graph.nodes)} nodes and {len(self.graph.edges)} edges to {graph_path}")

    def ingest_generic_csv(self, file_path):
        try:
            df = pd.read_csv(file_path)
            filename = os.path.basename(file_path)
            for idx, row in df.iterrows():
                row_str = ", ".join(f"{k}: {v}" for k, v in row.items())
                text_content = f"Generic Record from {filename} (Row {idx}):\n{row_str}"
                record_id = f"generic_{filename.split('.')[0]}_{idx}"
                metadata = {
                    "source": filename,
                    "type": "generic",
                    "row_index": idx
                }
                self.collection.add(
                    documents=[text_content],
                    metadatas=[metadata],
                    ids=[record_id]
                )
                
                # Check for equipment mentions
                equips = self.extract_equipment_ids(row_str)
                for eq in equips:
                    self.graph.add_node(eq, type="equipment", label=eq)
                    self.graph.add_node(record_id, type="generic", label=record_id)
                    self.graph.add_edge(eq, record_id, relation="referenced_in")
        except Exception as e:
            print(f"Generic CSV ingest failed for {file_path}: {e}")

    def ingest_generic_json(self, file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            filename = os.path.basename(file_path)
            records = data if isinstance(data, list) else [data]
            for idx, rec in enumerate(records):
                row_str = json.dumps(rec)
                text_content = f"Generic JSON Excerpt from {filename} (Record {idx}):\n{row_str}"
                record_id = f"generic_json_{filename.split('.')[0]}_{idx}"
                metadata = {
                    "source": filename,
                    "type": "generic",
                    "record_index": idx
                }
                self.collection.add(
                    documents=[text_content],
                    metadatas=[metadata],
                    ids=[record_id]
                )
                
                equips = self.extract_equipment_ids(row_str)
                for eq in equips:
                    self.graph.add_node(eq, type="equipment", label=eq)
                    self.graph.add_node(record_id, type="generic", label=record_id)
                    self.graph.add_edge(eq, record_id, relation="referenced_in")
        except Exception as e:
            print(f"Generic JSON ingest failed for {file_path}: {e}")

    def ingest_generic_text(self, file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                text_content = f.read()
            filename = os.path.basename(file_path)
            record_id = f"text_{filename.replace('.', '_')}"
            metadata = {
                "source": filename,
                "type": "safety" if "safety" in filename.lower() else "generic"
            }
            self.collection.add(
                documents=[text_content],
                metadatas=[metadata],
                ids=[record_id]
            )
            
            # Check for equipment mentions
            equips = self.extract_equipment_ids(text_content)
            for eq in equips:
                self.graph.add_node(eq, type="equipment", label=eq)
                node_type = "procedure" if "safety" in filename.lower() else "generic"
                self.graph.add_node(record_id, type=node_type, label=record_id)
                self.graph.add_edge(eq, record_id, relation="governed_by" if "safety" in filename.lower() else "referenced_in")
            print(f"Ingested text file: {filename}")
        except Exception as e:
            print(f"Generic text ingest failed for {file_path}: {e}")

    def run_all(self):
        print("Starting ingestion pipeline...")
        # 1. Ingest folder documents first
        self.ingest_safety_procedures()
        self.ingest_equipment_manuals()
        
        # 2. Dynamically scan data_dir files
        if os.path.exists(self.data_dir):
            for filename in os.listdir(self.data_dir):
                file_path = os.path.join(self.data_dir, filename)
                if os.path.isdir(file_path):
                    continue
                    
                # Match CSV
                if filename.endswith(".csv"):
                    try:
                        df = pd.read_csv(file_path)
                        cols = [c.lower().strip() for c in df.columns]
                        if "work_order_id" in cols:
                            print(f"Dynamic Ingest: processing {filename} as maintenance logs...")
                            self.ingest_maintenance_logs(file_path)
                        elif "inspection_id" in cols:
                            print(f"Dynamic Ingest: processing {filename} as inspection reports...")
                            self.ingest_inspection_reports(file_path)
                        else:
                            print(f"Dynamic Ingest: processing {filename} as generic CSV...")
                            self.ingest_generic_csv(file_path)
                    except Exception as e:
                        print(f"Error parsing CSV {filename}: {e}")
                
                # Match JSON
                elif filename.endswith(".json"):
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        if isinstance(data, list) and len(data) > 0 and "report_id" in data[0]:
                            print(f"Dynamic Ingest: processing {filename} as incident reports...")
                            self.ingest_incident_reports(file_path)
                        else:
                            print(f"Dynamic Ingest: processing {filename} as generic JSON...")
                            self.ingest_generic_json(file_path)
                    except Exception as e:
                        print(f"Error parsing JSON {filename}: {e}")
                
                # Match TXT or MD files directly in root
                elif filename.endswith(".txt") or (filename.endswith(".md") and not filename.startswith(".")):
                    try:
                        print(f"Dynamic Ingest: processing {filename} as generic text...")
                        self.ingest_generic_text(file_path)
                    except Exception as e:
                        print(f"Error parsing text {filename}: {e}")
                        
        self.save_graph()
        print("Ingestion pipeline finished successfully!")

if __name__ == "__main__":
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_directory = os.path.join(base, "sample_data")
    db_directory = os.path.join(base, "chroma_db")
    os.makedirs(db_directory, exist_ok=True)
    
    pipeline = IngestionPipeline(data_directory, db_directory)
    pipeline.run_all()
