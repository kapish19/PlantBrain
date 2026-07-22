import os
import re
import json
import pandas as pd
import networkx as nx
import chromadb
from chromadb.utils import embedding_functions
import google.generativeai as genai

class PlantBrainCopilot:
    def __init__(self, data_dir, db_dir):
        self.data_dir = data_dir
        self.db_dir = db_dir
        
        # Load Knowledge Graph
        graph_path = os.path.join(db_dir, "knowledge_graph.json")
        if os.path.exists(graph_path):
            with open(graph_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.graph = nx.node_link_graph(data)
            print(f"Loaded Knowledge Graph with {len(self.graph.nodes)} nodes")
        else:
            self.graph = nx.Graph()
            print("Warning: Knowledge Graph file not found!")
            
        # Connect to ChromaDB
        self.chroma_client = chromadb.PersistentClient(path=db_dir)
        self.embed_fn = embedding_functions.DefaultEmbeddingFunction()
        try:
            self.collection = self.chroma_client.get_collection(
                name="plantbrain_docs",
                embedding_function=self.embed_fn
            )
        except Exception:
            self.collection = self.chroma_client.create_collection(
                name="plantbrain_docs",
                embedding_function=self.embed_fn
            )
        
        # Initialize Gemini API Client
        api_key = os.environ.get("GEMINI_API_KEY")
        if api_key:
            try:
                genai.configure(api_key=api_key)
                self.gemini_model = genai.GenerativeModel("gemini-3-flash-preview")
                print("Gemini API client initialized successfully.")
            except Exception as e:
                self.gemini_model = None
                print(f"Error configuring Gemini client: {e}")
        else:
            self.gemini_model = None
            print("Warning: GEMINI_API_KEY environment variable not found. Copilot will run in Mock/Dry-Run mode.")

    def extract_equipment_ids(self, text):
        pattern = r"\b[A-Z]{3,10}-\d{1,4}\b"
        return list(set(re.findall(pattern, text, re.IGNORECASE)))

    def get_graph_context(self, equipment_ids):
        if not equipment_ids:
            return "No specific equipment IDs detected in the query."
            
        context_parts = []
        for eq_id in equipment_ids:
            # Normalize to uppercase
            eq_id_upper = eq_id.upper()
            if eq_id_upper not in self.graph:
                context_parts.append(f"Equipment {eq_id_upper} is not currently indexed in the knowledge graph.")
                continue
                
            neighbors = list(self.graph.neighbors(eq_id_upper))
            context_parts.append(f"### Knowledge Graph Relations for {eq_id_upper}:")
            
            # Group neighbors by type
            grouped = {}
            for n in neighbors:
                node_data = self.graph.nodes[n]
                node_type = node_data.get("type", "unknown")
                grouped.setdefault(node_type, []).append(n)
                
            for n_type, nodes in grouped.items():
                context_parts.append(f"- Connected {n_type.capitalize()}(s): {', '.join(nodes)}")
                
            # Grab latest 3 incidents/maintenance logs details if they exist in the graph
            if "incident" in grouped:
                context_parts.append(f"- Detailed Incident History: The graph connects {eq_id_upper} to: {', '.join(grouped['incident'])}")
            if "maintenance" in grouped:
                context_parts.append(f"- Detailed Maintenance History: The graph connects {eq_id_upper} to: {', '.join(grouped['maintenance'])}")
                
        return "\n".join(context_parts)

    def calculate_confidence(self, sources):
        unique_sources = set(sources)
        num_sources = len(unique_sources)
        
        if num_sources >= 4:
            return {
                "level": "High confidence",
                "message": f"High confidence - {num_sources} corroborating sources found across maintenance logs, manuals, or incident reports."
            }
        elif num_sources >= 2:
            return {
                "level": "Medium confidence",
                "message": f"Medium confidence - {num_sources} corroborating sources found."
            }
        elif num_sources == 1:
            return {
                "level": "Low confidence",
                "message": "Low confidence - Answer based on a single source."
            }
        else:
            return {
                "level": "Low confidence",
                "message": "Low confidence - No direct sources found. Synthesizing based on general knowledge."
            }

    def ask(self, query):
        query_lower = query.lower().strip()
        
        # Check for general greetings or capabilities query (prevent random fallback dumps)
        greetings = ["hello", "hi", "hey", "who are you", "what can you do", "what you can do", "help", "capabilities"]
        if any(g in query_lower for g in greetings) or query_lower == "?":
            # Extract dynamically loaded equipment list
            equipment_ids = [node for node, attr in self.graph.nodes(data=True) if attr.get("type") == "equipment"]
            equip_str = ""
            if equipment_ids:
                equip_str = f" for assets like **{', '.join(equipment_ids[:4])}**"
            
            return {
                "answer": (
                    f"Hello! I am **PlantBrain Copilot**, your expert industrial safety and maintenance assistant.\n\n"
                    f"Here is what I can help you with based on your uploaded dataset:\n\n"
                    f"*   **Maintenance Auditing**: Retrieve maintenance records, work orders, and action logs{equip_str}.\n"
                    f"*   **SOP and safety checks**: Check Lockout-Tagout (LOTO) protocols, safety warnings, and confined space entry permits.\n"
                    f"*   **Proactive Insights**: Scan for recurring failure loops, calibration drift issues, and safety compliance alerts.\n"
                    f"*   **Interactive Visualizations**: Click the top-right **Knowledge Graph** button to view asset relationships in real-time!\n\n"
                    f"Try asking suggestions like: *'What is the maintenance history of {equipment_ids[0] if equipment_ids else 'PUMP-204'}?'* or *'What is the safety procedure for confined space entry?'*"
                ),
                "citations": ["System Prompt / Dynamic Schema Mapper"],
                "confidence": {
                    "level": "High confidence",
                    "message": "High confidence - System capabilities map directly to the loaded schema."
                },
                "graph_nodes": equipment_ids[:3] if equipment_ids else ["PUMP-204"],
                "graph_edges": [],
                "storage_visualization": (
                    "📂 Data Storage Architecture\n"
                    f"├── 🕸️ NetworkX: {len(self.graph.nodes)} Graph Nodes loaded\n"
                    f"└── 🗄️ ChromaDB: Vector search active"
                )
            }



        # 1. Extract equipment IDs
        eq_ids = self.extract_equipment_ids(query)
        
        # 2. Retrieve semantic context from ChromaDB
        chroma_query = query
        if eq_ids:
            chroma_query += " " + " ".join(eq_ids)
            
        results = self.collection.query(
            query_texts=[chroma_query],
            n_results=8
        )
        
        vector_contexts = []
        citations = []
        
        if results and results["documents"]:
            for doc, metadata in zip(results["documents"][0], results["metadatas"][0]):
                vector_contexts.append(doc)
                source_file = metadata.get("source", "Unknown Source")
                
                if metadata.get("type") == "maintenance":
                    citations.append(f"{source_file} (Work Order {metadata.get('work_order_id')})")
                elif metadata.get("type") == "incident":
                    citations.append(f"{source_file} (Incident Report {metadata.get('report_id')})")
                elif metadata.get("type") == "inspection":
                    citations.append(f"{source_file} (Inspection {metadata.get('inspection_id')})")
                elif "section_title" in metadata:
                    citations.append(f"{source_file} - Section: {metadata.get('section_title')}")
                else:
                    citations.append(source_file)

        unique_citations = []
        for c in citations:
            if c not in unique_citations:
                unique_citations.append(c)

        # 3. Retrieve Graph Context
        graph_context = self.get_graph_context(eq_ids)
        
        # 4. Combine Contexts
        full_context = "=== SEMANTIC DOCUMENT CHUNKS ===\n\n"
        full_context += "\n\n---\n\n".join(vector_contexts)
        full_context += "\n\n=== KNOWLEDGE GRAPH RELATIONSHIPS ===\n\n"
        full_context += graph_context
        
        # 5. Determine confidence
        confidence_info = self.calculate_confidence(unique_citations)
        
        # Extract nodes and edges dynamically for the response metadata
        retrieved_nodes = []
        retrieved_edges = []
        for eq_id in eq_ids:
            eq_id_upper = eq_id.upper()
            if eq_id_upper in self.graph:
                retrieved_nodes.append(eq_id_upper)
                for neighbor in self.graph.neighbors(eq_id_upper):
                    retrieved_nodes.append(neighbor)
                    edge_data = self.graph.get_edge_data(eq_id_upper, neighbor)
                    edge_type = edge_data.get("type", "connected") if edge_data else "connected"
                    retrieved_edges.append({
                        "source": eq_id_upper,
                        "target": neighbor,
                        "type": edge_type
                    })
        retrieved_nodes = list(set(retrieved_nodes))
        
        # Dynamic storage visualization map
        storage_vis = (
            "📂 Data Storage Architecture\n"
            "├── 🗄️ ChromaDB (Vector Store)\n"
            "│   └── Collection: plantbrain_docs\n"
        )
        for i, citation in enumerate(unique_citations[:3]):
            storage_vis += f"│       ├── Chunk ID: doc_{i} ── [{citation}]\n"
        storage_vis += (
            "└── 🕸️ NetworkX (Graph DB)\n"
            f"    ├── Nodes Count: {len(self.graph.nodes)}\n"
            f"    ├── Edges Count: {len(self.graph.edges)}\n"
            f"    └── Retrieved Path: {', '.join(eq_ids) if eq_ids else 'General Semantic Query'}\n"
        )
        
        # 6. Generate answer via Google Gemini API
        system_prompt = (
            "You are 'PlantBrain Copilot', an expert AI Industrial Safety and Maintenance Assistant for a manufacturing plant.\n"
            "Your job is to answer the user's natural language questions using the provided context from our vector database and knowledge graph.\n\n"
            "CRITICAL RULES:\n"
            "1. BE EXTREMELY CONCISE. Your answer must be direct, well-formatted, and under 150 words. Do not write long paragraphs.\n"
            "2. Use brief bullet points. Focus only on key actionable details.\n"
            "3. Base your answer strictly on the provided context. If the context is insufficient, state that clearly.\n"
            "4. Explicitly cite the source documents (e.g. [maintenance_logs.csv], [incident_reports.json], or [SOP name]) for every claim.\n"
            "5. Boldly highlight any safety warnings or LOTO requirements.\n"
        )
        
        user_message = (
            f"User Question: {query}\n\n"
            f"Retrieved Context:\n{full_context}\n\n"
            "Provide a very concise, direct, and well-formatted bulleted answer below (maximum 150 words):"
        )
        
        if self.gemini_model:
            models_to_try = ["gemini-3-flash-preview", "gemini-2.5-flash", "gemini-1.5-flash"]
            answer = None
            last_error = None
            
            for model_name in models_to_try:
                try:
                    model = genai.GenerativeModel(
                        model_name,
                        system_instruction=system_prompt
                    )
                    response = model.generate_content(user_message)
                    answer = response.text
                    print(f"Gemini API call succeeded with model: {model_name}")
                    break
                except Exception as e:
                    last_error = e
                    print(f"Failed to query {model_name}: {e}")
            
            if not answer:
                answer = self._generate_fallback_answer(query, eq_ids, vector_contexts, graph_context, error=str(last_error))
        else:
            answer = self._generate_fallback_answer(query, eq_ids, vector_contexts, graph_context, error="GEMINI_API_KEY environment variable not found.")
            
        return {
            "answer": answer,
            "citations": unique_citations,
            "confidence": confidence_info,
            "graph_nodes": retrieved_nodes,
            "graph_edges": retrieved_edges,
            "storage_visualization": storage_vis
        }

    def _generate_fallback_answer(self, query, eq_ids, chunks, graph_ctx, error=None):
        """Generates a beautiful local RAG-synthesized response if the Gemini API is completely unavailable."""
        # Print error details to console for debugging
        if error:
            print(f"[Fallback Active] Gemini API Error: {error}")
            
        bullet_points = []
        safety_warnings = []
        
        # Parse the chunks to find relevant facts and safety procedures
        for chunk in chunks:
            # Check for header names or file context
            lines = chunk.split("\n")
            for line in lines:
                line = line.strip()
                if not line or len(line) < 10:
                    continue
                
                # Check for safety warnings
                if any(k in line.lower() for k in ["safety", "danger", "warning", "loto", "hazard", "lockout"]):
                    # Clean up markdown headers and balance bold markers if present
                    clean_line = re.sub(r"^#+\s*", "", line)
                    clean_line = re.sub(r"^\*\*|^\*|\*\*$|\*$", "", clean_line).strip()
                    if clean_line not in safety_warnings:
                        safety_warnings.append(clean_line)
                elif line.startswith("-") or line.startswith("*") or ":" in line:
                    clean_line = re.sub(r"^[-\*\s]+", "", line)
                    clean_line = re.sub(r"^\*\*|^\*|\*\*$|\*$", "", clean_line).strip()
                    if clean_line not in bullet_points:
                        bullet_points.append(clean_line)
        
        # Combine points into a structured response under 150 words
        answer_parts = []
        if eq_ids:
            answer_parts.append(f"Retrieved logs and specifications for **{', '.join(eq_ids)}**:")
        else:
            answer_parts.append("Retrieved information from plant safety manuals and maintenance logs:")
            
        # Add top structured bullet points
        points_to_add = bullet_points[:4]
        if not points_to_add:
            # Fallback to sentences if no structured bullet points were extracted
            for chunk in chunks[:2]:
                sentences = [s.strip() for s in chunk.split(".") if len(s.strip()) > 15]
                for s in sentences[:2]:
                    points_to_add.append(s)
                    
        for pt in points_to_add:
            # Ensure line starts with bullet formatting
            answer_parts.append(f"* {pt}")
            
        if safety_warnings:
            answer_parts.append(f"\n**⚠️ SAFETY WARNING: {safety_warnings[0]}**")
            
        return "\n".join(answer_parts)

if __name__ == "__main__":
    # Test execution
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_directory = os.path.join(base, "sample_data")
    db_directory = os.path.join(base, "chroma_db")
    
    copilot = PlantBrainCopilot(data_directory, db_directory)
    
    print("\n--- TEST QUERY 1: PUMP-204 ---")
    res1 = copilot.ask("What's the maintenance history of PUMP-204?")
    print(res1["answer"])
    print(f"Citations: {res1['citations']}")
    print(f"Confidence: {res1['confidence']}")
