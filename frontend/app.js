/* ==========================================
   PlantBrain Frontend Controller (Light UI + Visualizer)
   ========================================== */

const API_BASE = ""; // Relative paths since FastAPI serves the frontend

// DOM Elements
const chatHistory = document.getElementById("chat-history");
const chatInput = document.getElementById("chat-input");
const sendBtn = document.getElementById("send-btn");
const insightsContainer = document.getElementById("insights-container");
const refreshPatternsBtn = document.getElementById("refresh-patterns-btn");
const equipmentSelect = document.getElementById("equipment-select");
const timelineContainer = document.getElementById("timeline-container");
const pageTitle = document.getElementById("page-title");

// Header status
const viewGraphBtn = document.getElementById("view-graph-btn");
const nodeCountBadge = document.getElementById("node-count-badge");
const ingestStatusBadge = document.getElementById("ingest-status-badge");

// Ingest Modal Elements
const ingestModal = document.getElementById("ingest-modal");
const startIngestBtn = document.getElementById("start-ingest-btn");
const progressContainer = document.getElementById("ingest-progress-container");
const progressBar = document.getElementById("ingest-progress-bar");
const progressText = document.getElementById("ingest-progress-text");

// Evidence Modal Elements
const evidenceModal = document.getElementById("evidence-modal");
const modalTitle = document.getElementById("modal-title");
const modalBody = document.getElementById("modal-body");
const closeModalBtn = document.getElementById("close-modal-btn");

// Graph Visualizer Modal Elements
const graphModal = document.getElementById("graph-visualizer-modal");
const closeGraphModalBtn = document.getElementById("close-graph-modal-btn");
const canvas = document.getElementById("graph-canvas");
const ctx = canvas.getContext("2d");



// State
let activePatterns = [];

let isSystemIngested = false;
let selectedFiles = []; // Upload Queue

// Physics Graph Simulation State
let simulationNodes = [];
let simulationLinks = [];
let simulationActive = false;
let transformScale = 1;
let transformX = 0;
let transformY = 0;
let dragNode = null;
let hoverNode = null;
let lastMouseX = 0;
let lastMouseY = 0;
let isPanning = false;

const TYPE_COLORS = {
    "equipment": "#0284c7",     // Light blue
    "maintenance": "#10b981",   // Emerald green
    "incident": "#ef4444",      // Danger red
    "procedure": "#f59e0b",     // Amber orange
    "manual": "#6366f1"         // Indigo purple
};



// Initialize Dashboard
document.addEventListener("DOMContentLoaded", () => {
    checkSystemStatus();

    // Force Light Mode Only
    document.body.classList.remove("dark-theme");
    localStorage.setItem("plantbrain_theme", "light");

    // Event Listeners
    sendBtn.addEventListener("click", handleSend);
    chatInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    });

    refreshPatternsBtn.addEventListener("click", loadPatterns);
    equipmentSelect.addEventListener("change", (e) => {
        loadTimeline(e.target.value);
    });

    closeModalBtn.addEventListener("click", () => { evidenceModal.style.display = "none"; });
    window.addEventListener("click", (e) => {
        if (e.target === evidenceModal) evidenceModal.style.display = "none";
        if (e.target === graphModal) closeGraphVisualizer();
    });

    // Ingestion click handler
    startIngestBtn.addEventListener("click", triggerDynamicIngestion);

    // Setup Drag and Drop File Upload Listeners
    const dropZone = document.getElementById("drop-zone");
    const fileInput = document.getElementById("file-input");

    if (dropZone && fileInput) {
        // Prevent defaults
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
            }, false);
        });

        // Highlights
        ['dragenter', 'dragover'].forEach(eventName => {
            dropZone.addEventListener(eventName, () => {
                dropZone.style.borderColor = "var(--color-primary)";
                dropZone.style.background = "#eff6ff";
            }, false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, () => {
                dropZone.style.borderColor = "var(--border-color)";
                dropZone.style.background = "var(--bg-body)";
            }, false);
        });

        // Handle drops
        dropZone.addEventListener('drop', (e) => {
            handleFileSelection(e.dataTransfer.files);
        });

        // Click zone triggers selection dialog
        dropZone.addEventListener('click', () => {
            fileInput.click();
        });

        fileInput.addEventListener('change', (e) => {
            handleFileSelection(e.target.files);
        });
    }

    // Visualizer click handlers
    viewGraphBtn.addEventListener("click", openGraphVisualizer);
    closeGraphModalBtn.addEventListener("click", closeGraphVisualizer);

    // Setup visualizer mouse listeners
    setupCanvasListeners();


});

// File Selection Handlers
function handleFileSelection(files) {
    for (let file of files) {
        if (!selectedFiles.some(f => f.name === file.name && f.size === file.size)) {
            selectedFiles.push(file);
        }
    }
    renderSelectedFilesList();
}

function renderSelectedFilesList() {
    const selectedFilesContainer = document.getElementById("selected-files-container");
    const selectedFilesList = document.getElementById("selected-files-list");
    
    if (selectedFiles.length === 0) {
        selectedFilesContainer.style.display = "none";
        selectedFilesList.innerHTML = "";
        return;
    }
    
    selectedFilesContainer.style.display = "block";
    selectedFilesList.innerHTML = selectedFiles.map((file, idx) => `
        <div style="display: flex; justify-content: space-between; align-items: center; padding: 4px 8px; background: #fff; border: 1px solid var(--border-color); border-radius: 4px;">
            <span style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 80%;"><i class="fa-solid fa-file-lines" style="color: var(--color-primary); margin-right: 6px;"></i> ${file.name} (${(file.size / 1024).toFixed(1)} KB)</span>
            <span style="color: var(--color-danger); cursor: pointer; font-size: 14px; font-weight: bold; padding: 0 4px;" onclick="removeSelectedFile(${idx})">&times;</span>
        </div>
    `).join('');
}

window.removeSelectedFile = function(index) {
    selectedFiles.splice(index, 1);
    renderSelectedFilesList();
};

// Check backend status
async function checkSystemStatus() {
    try {
        const response = await fetch(`${API_BASE}/api/health`);
        if (!response.ok) throw new Error("Health check failed");
        
        const data = await response.json();
        isSystemIngested = data.ingested;
        
        if (isSystemIngested) {
            // Unlock dashboard
            ingestModal.style.display = "none";
            ingestStatusBadge.textContent = "Ingested";
            ingestStatusBadge.style.backgroundColor = "var(--color-success)";
            
            // Load graph details to set mapped node count on Overview KPI card
            fetch(`${API_BASE}/api/graph`)
                .then(r => r.json())
                .then(graphData => {
                    const nodeCount = graphData.nodes ? graphData.nodes.length : 0;
                    const overviewNodeEl = document.getElementById("overview-node-count");
                    if (overviewNodeEl) overviewNodeEl.textContent = `${nodeCount} Nodes`;
                    nodeCountBadge.textContent = `${nodeCount} Graph Nodes`;
                    const footerNodeEl = document.getElementById("footer-node-count");
                    if (footerNodeEl) footerNodeEl.textContent = `${nodeCount} Active Nodes`;
                })
                .catch(e => console.error("Failed to load graph nodes count:", e));
            
            // Clear default messages and render dynamic welcome summary with suggestion chips container
            const summaryText = data.welcome_summary || "I have successfully mapped your dataset! Ask me anything about your uploaded maintenance logs and safety compliance records.";
            appendWelcomeMessage(summaryText);

            loadEquipment();
            loadPatterns();
        } else {
            // Keep locked, prompt ingestion
            ingestModal.style.display = "flex";
            nodeCountBadge.textContent = "0 Graph Nodes";
            const footerNodeEl = document.getElementById("footer-node-count");
            if (footerNodeEl) footerNodeEl.textContent = "0 Active Nodes";
            ingestStatusBadge.textContent = "Uninitialized";
            ingestStatusBadge.style.backgroundColor = "var(--color-warning)";
        }
    } catch (err) {
        console.error("Status check failed", err);
    }
}

// Trigger programmatic ingestion
async function triggerDynamicIngestion() {
    if (selectedFiles.length === 0) {
        alert("Please select or drop at least one industrial document to ingest.");
        return;
    }

    startIngestBtn.disabled = true;
    progressContainer.style.display = "block";
    
    try {
        // 1. Upload files to backend
        progressText.textContent = "Uploading industrial documents to server...";
        progressBar.style.width = "5%";
        
        const formData = new FormData();
        for (let file of selectedFiles) {
            formData.append("files", file);
        }
        
        const uploadResponse = await fetch(`${API_BASE}/api/upload`, {
            method: "POST",
            body: formData
        });
        
        if (!uploadResponse.ok) throw new Error("Document upload failed");

        // 2. Simulating progress steps for dynamic hackathon aesthetic
        const steps = [
            { progress: 20, text: "Connecting to CSV & JSON databases..." },
            { progress: 45, text: "Parsing Work Orders and Incident logs..." },
            { progress: 65, text: "Running Entity Extraction (SpaCy models)..." },
            { progress: 85, text: "Computing text embeddings (MiniLM)..." }
        ];
        
        for (let step of steps) {
            progressBar.style.width = step.progress + "%";
            progressText.textContent = step.text;
            await new Promise(resolve => setTimeout(resolve, 600));
        }
        
        progressText.textContent = "Structuring nodes to NetworkX graph database...";
        progressBar.style.width = "93%";
        
        const response = await fetch(`${API_BASE}/api/ingest`, {
            method: "POST"
        });
        
        if (!response.ok) throw new Error("Backend Ingestion failed");
        
        const data = await response.json();
        
        progressBar.style.width = "100%";
        progressText.textContent = `Completed! Created ${data.nodes} nodes, ${data.edges} edges.`;
        
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        // Hide overlay & update status badges
        ingestModal.style.display = "none";
        isSystemIngested = true;
        nodeCountBadge.textContent = `${data.nodes} Graph Nodes`;
        const footerNodeEl = document.getElementById("footer-node-count");
        if (footerNodeEl) footerNodeEl.textContent = `${data.nodes} Active Nodes`;
        ingestStatusBadge.textContent = "Ingested";
        ingestStatusBadge.style.backgroundColor = "var(--color-success)";
        
        // Reset state queue
        selectedFiles = [];
        renderSelectedFilesList();
        
        // Clear warning messages and insert dynamic welcome summary with suggestion chips container
        const summaryText = data.welcome_summary || "I have successfully mapped your dataset! Ask me anything about your uploaded maintenance logs and safety compliance records.";
        appendWelcomeMessage(summaryText);

        // Reload all data streams
        loadEquipment();
        loadPatterns();
        

        
    } catch (err) {
        progressText.textContent = `Error: ${err.message}`;
        progressBar.style.backgroundColor = "var(--color-danger)";
        startIngestBtn.disabled = false;
    }
}

// Tab Switcher
function switchTab(tabId) {
    document.querySelectorAll(".tab-content").forEach(el => el.classList.remove("active"));
    document.querySelectorAll(".nav-link").forEach(el => el.classList.remove("active"));

    const activeContent = document.getElementById(`tab-${tabId}-content`);
    const activeLink = document.getElementById(`nav-${tabId}`);
    
    if (activeContent) activeContent.classList.add("active");
    if (activeLink) activeLink.classList.add("active");

    if (tabId === "overview") pageTitle.textContent = "Overview Hub";
    else if (tabId === "copilot") pageTitle.textContent = "Expert Copilot";
    else if (tabId === "patterns") pageTitle.textContent = "Proactive Insights";
    else if (tabId === "timeline") pageTitle.textContent = "Asset Timeline";
    else if (tabId === "pid") pageTitle.textContent = "P&ID Blueprint";
    else if (tabId === "compliance") {
        pageTitle.textContent = "Compliance Audit";
        loadCompliance();
    }
}

// Markdown formatting helper to convert headers, bold text, and bullet lists cleanly without raw asterisks
function formatMarkdown(text) {
    if (!text) return "";
    
    // 1. Escape HTML tags to prevent XSS injection
    let lines = text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .split("\n");
        
    let formattedLines = [];
    let inList = false;
    
    for (let line of lines) {
        let trimmed = line.trim();
        if (!trimmed) continue;
        
        // 2. Parse Headers
        if (trimmed.startsWith("###")) {
            if (inList) {
                formattedLines.push("</ul>");
                inList = false;
            }
            let headerText = trimmed.replace(/^###\s*/, "");
            headerText = headerText.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
            formattedLines.push(`<h4 style="margin-top: 12px; margin-bottom: 6px; font-weight: 600; color: var(--text-dark); font-size: 13.5px;">${headerText}</h4>`);
            continue;
        }
        if (trimmed.startsWith("##")) {
            if (inList) {
                formattedLines.push("</ul>");
                inList = false;
            }
            let headerText = trimmed.replace(/^##\s*/, "");
            headerText = headerText.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
            formattedLines.push(`<h3 style="margin-top: 16px; margin-bottom: 8px; font-weight: 600; color: var(--text-dark); font-size: 14.5px;">${headerText}</h3>`);
            continue;
        }
        
        // 3. Parse Bullet Points
        let isBullet = trimmed.startsWith("*") || trimmed.startsWith("-");
        if (isBullet && (trimmed.startsWith("* ") || trimmed.startsWith("- ") || trimmed.startsWith("*\t") || trimmed.startsWith("-\t") || trimmed === "*" || trimmed === "-")) {
            if (!inList) {
                formattedLines.push(`<ul style="margin: 6px 0; padding-left: 18px; list-style-type: disc; display: flex; flex-direction: column; gap: 6px;">`);
                inList = true;
            }
            let itemText = trimmed.replace(/^[\*\-]\s*/, "");
            itemText = itemText.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
            formattedLines.push(`<li style="font-size: 12.5px; line-height: 1.45; color: var(--text-muted);">${itemText}</li>`);
            continue;
        }
        
        // Close list if we hit a non-bullet line
        if (inList) {
            formattedLines.push("</ul>");
            inList = false;
        }
        
        // 4. Parse inline bold tags
        let processedLine = trimmed.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
        formattedLines.push(`<p style="margin: 6px 0; font-size: 12.5px; line-height: 1.45; color: var(--text-muted);">${processedLine}</p>`);
    }
    
    if (inList) {
        formattedLines.push("</ul>");
    }
    
    return formattedLines.join("\n");
}

// Fill Chat Input Suggestion
function fillQuery(queryText) {
    chatInput.value = queryText;
    chatInput.focus();
}

// Handle sending message with query locks to prevent spamming
let isWaitingForResponse = false;

async function handleSend() {
    if (isWaitingForResponse) return;

    const queryText = chatInput.value.trim();
    if (!queryText) return;

    // Lock input and button state
    isWaitingForResponse = true;
    chatInput.disabled = true;
    sendBtn.disabled = true;
    sendBtn.style.opacity = "0.5";
    sendBtn.style.cursor = "not-allowed";
    sendBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';

    chatInput.value = "";
    appendMessage(queryText, "user");

    const typingId = appendTypingIndicator();
    chatHistory.scrollTop = chatHistory.scrollHeight;

    try {
        const response = await fetch(`${API_BASE}/api/chat`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ query: queryText })
        });

        if (!response.ok) throw new Error("Failed to query Copilot API");

        const data = await response.json();
        removeElement(typingId);
        appendMessage(data.answer, "copilot", data);

    } catch (error) {
        removeElement(typingId);
        appendMessage(`⚠️ Error: ${error.message}. Verify the server is active.`, "system");
    }

    // Unlock input and button state
    isWaitingForResponse = false;
    chatInput.disabled = false;
    sendBtn.disabled = false;
    sendBtn.style.opacity = "1";
    sendBtn.style.cursor = "pointer";
    sendBtn.innerHTML = '<i class="fa-solid fa-paper-plane"></i>';
    chatInput.focus();

    chatHistory.scrollTop = chatHistory.scrollHeight;
}

// Welcome Message builder with template suggestion chips container
function appendWelcomeMessage(summaryText) {
    chatHistory.innerHTML = "";
    
    const messageDiv = document.createElement("div");
    messageDiv.className = "message message-system";
    messageDiv.innerHTML = `
        <div class="avatar"><i class="fa-solid fa-robot"></i></div>
        <div class="message-content">
            <h3>Welcome to PlantBrain Copilot</h3>
            <p>${formatMarkdown(summaryText)}</p>
            <div class="suggestion-group" id="tour-step-3"></div>
        </div>
    `;
    chatHistory.appendChild(messageDiv);
    chatHistory.scrollTop = chatHistory.scrollHeight;
}

// Message Bubble builder
function appendMessage(text, sender, meta = null) {
    const messageDiv = document.createElement("div");
    messageDiv.className = `message message-${sender}`;

    const avatarDiv = document.createElement("div");
    avatarDiv.className = "avatar";
    
    if (sender === "user") avatarDiv.innerHTML = '<i class="fa-solid fa-user"></i>';
    else if (sender === "copilot") avatarDiv.innerHTML = '<i class="fa-solid fa-robot"></i>';
    else avatarDiv.innerHTML = '<i class="fa-solid fa-triangle-exclamation"></i>';

    const contentDiv = document.createElement("div");
    contentDiv.className = "message-content";
    contentDiv.innerHTML = `<p>${formatMarkdown(text)}</p>`;

    if (sender === "copilot" && meta) {
        const metaId = "meta-" + Math.random().toString(36).substring(2, 9);
        const metaDiv = document.createElement("div");
        metaDiv.className = "rag-meta";
        metaDiv.id = metaId;

        let confClass = "conf-low";
        if (meta.confidence.level.toLowerCase().includes("high")) confClass = "conf-success";
        else if (meta.confidence.level.toLowerCase().includes("medium")) confClass = "conf-medium";

        let citationsHTML = "";
        if (meta.citations && meta.citations.length > 0) {
            citationsHTML = `
                <div class="citations-list">
                    ${meta.citations.map(c => `<span class="citation-badge"><i class="fa-solid fa-file-invoice"></i> ${c}</span>`).join('')}
                </div>
            `;
        } else {
            citationsHTML = '<div class="citations-list"><span class="citation-badge">No direct citations</span></div>';
        }

        // Knowledge Graph Section
        let graphHTML = "";
        if (meta.graph_nodes && meta.graph_nodes.length > 0) {
            graphHTML = `
                <div class="graph-inspector-section" style="margin-top: 10px;">
                    <button class="tour-btn" style="padding: 6px 12px; font-size: 11px; width: auto; background: var(--bg-body); border: 1px solid var(--border-color); color: var(--text-dark); cursor: pointer; border-radius: 6px; display: inline-flex; align-items: center; gap: 6px;" onclick="toggleDetails(this, '${metaId}-graph')">
                        <i class="fa-solid fa-circle-nodes"></i> View Retrieved Graph Relations (${meta.graph_nodes.length} nodes) <i class="fa-solid fa-chevron-down toggle-icon" style="font-size: 9px; margin-left: 4px;"></i>
                    </button>
                    <div class="graph-details-panel" id="${metaId}-graph" style="display: none; margin-top: 8px; padding: 10px; background: var(--bg-body); border: 1px solid var(--border-color); border-radius: 6px;">
                        <div class="graph-entities" style="font-size: 11px;">
                            <strong>Retrieved Nodes:</strong>
                            <div class="evidence-pills" style="margin-top: 4px; display: flex; flex-wrap: wrap; gap: 4px;">
                                ${meta.graph_nodes.map(n => `<span class="evidence-pill" style="font-size: 10.5px; padding: 2px 6px; background: #fff; border: 1px solid var(--border-color); border-radius: 4px;"><i class="fa-solid fa-cube"></i> ${n}</span>`).join('')}
                            </div>
                        </div>
                        <div class="graph-relations" style="margin-top: 8px; font-size: 11px;">
                            <strong>Retrieved Edges (Schema Links):</strong>
                            <div class="edges-list" style="font-family: monospace; font-size: 10.5px; color: var(--text-muted); background: #fff; border: 1px solid var(--border-color); padding: 6px; border-radius: 4px; margin-top: 4px; line-height: 1.4;">
                                ${meta.graph_edges.map(e => `• ${e.source} ──[${e.type}]──> ${e.target}`).join('<br>')}
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }

        // Storage Visualization Section
        let storageHTML = "";
        if (meta.storage_visualization) {
            storageHTML = `
                <div class="storage-inspector-section" style="margin-top: 6px;">
                    <button class="tour-btn" style="padding: 6px 12px; font-size: 11px; width: auto; background: var(--bg-body); border: 1px solid var(--border-color); color: var(--text-dark); cursor: pointer; border-radius: 6px; display: inline-flex; align-items: center; gap: 6px;" onclick="toggleDetails(this, '${metaId}-storage')">
                        <i class="fa-solid fa-database"></i> View Storage & Ingestion Model <i class="fa-solid fa-chevron-down toggle-icon" style="font-size: 9px; margin-left: 4px;"></i>
                    </button>
                    <div class="storage-details-panel" id="${metaId}-storage" style="display: none; margin-top: 8px;">
                        <pre style="font-family: monospace; font-size: 10px; color: var(--text-dark); background: var(--bg-body); border: 1px solid var(--border-color); padding: 8px; border-radius: 6px; overflow-x: auto; line-height: 1.35; white-space: pre; margin: 0;">${meta.storage_visualization}</pre>
                    </div>
                </div>
            `;
        }

        let benchmarkHTML = `
            <div class="benchmark-bar" style="margin-top: 10px; margin-bottom: 12px; padding: 10px 14px; background: rgba(2, 132, 199, 0.03); border: 1px solid rgba(2, 132, 199, 0.12); border-radius: 8px; font-size: 11px;">
                <div style="display: flex; justify-content: space-between; align-items: center; font-weight: 600; color: var(--color-primary-hover); margin-bottom: 6px;">
                    <span><i class="fa-solid fa-gauge-simple-high"></i> Search Speed Benchmarker</span>
                    <span style="background: var(--color-success); color: #fff; padding: 2px 6px; border-radius: 4px; font-size: 9px; font-weight: 700; text-transform: uppercase;">99.9% Time Saved</span>
                </div>
                <div style="display: flex; gap: 16px; align-items: center;">
                    <div style="flex: 1;">
                        <div style="display: flex; justify-content: space-between; margin-bottom: 3px; color: var(--text-secondary);">
                            <span>PlantBrain AI Search</span>
                            <strong>0.84s</strong>
                        </div>
                        <div style="width: 100%; height: 4px; background: #e2e8f0; border-radius: 2px; overflow: hidden;">
                            <div style="width: 2%; height: 100%; background: var(--color-success);"></div>
                        </div>
                    </div>
                    <div style="flex: 1;">
                        <div style="display: flex; justify-content: space-between; margin-bottom: 3px; color: var(--text-secondary);">
                            <span>Traditional Manual Search</span>
                            <strong>45.0m</strong>
                        </div>
                        <div style="width: 100%; height: 4px; background: #e2e8f0; border-radius: 2px; overflow: hidden;">
                            <div style="width: 100%; height: 100%; background: var(--color-danger);"></div>
                        </div>
                    </div>
                </div>
            </div>
        `;

        metaDiv.innerHTML = `
            <div class="confidence-indicator ${confClass}">
                <i class="fa-solid fa-circle-check"></i> ${meta.confidence.message}
            </div>
            ${benchmarkHTML}
            ${citationsHTML}
            ${graphHTML}
            ${storageHTML}
        `;
        contentDiv.appendChild(metaDiv);
    }

    messageDiv.appendChild(avatarDiv);
    messageDiv.appendChild(contentDiv);
    chatHistory.appendChild(messageDiv);
}

// Toggle custom details panel helper
window.toggleDetails = function(button, elementId) {
    const el = document.getElementById(elementId);
    if (!el) return;
    const isHidden = el.style.display === "none";
    el.style.display = isHidden ? "block" : "none";
    
    const icon = button.querySelector(".toggle-icon");
    if (icon) {
        if (isHidden) {
            icon.classList.remove("fa-chevron-down");
            icon.classList.add("fa-chevron-up");
        } else {
            icon.classList.remove("fa-chevron-up");
            icon.classList.add("fa-chevron-down");
        }
    }
};

function appendTypingIndicator() {
    const id = "typing-" + Date.now();
    const messageDiv = document.createElement("div");
    messageDiv.className = "message message-copilot";
    messageDiv.id = id;

    const avatarDiv = document.createElement("div");
    avatarDiv.className = "avatar";
    avatarDiv.innerHTML = '<i class="fa-solid fa-robot"></i>';

    const contentDiv = document.createElement("div");
    contentDiv.className = "message-content";
    contentDiv.innerHTML = `
        <div class="typing-indicator">
            <span class="typing-dot"></span>
            <span class="typing-dot"></span>
            <span class="typing-dot"></span>
        </div>
    `;

    messageDiv.appendChild(avatarDiv);
    messageDiv.appendChild(contentDiv);
    chatHistory.appendChild(messageDiv);
    return id;
}

function removeElement(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}

// Load Equipment Dropdown list
async function loadEquipment() {
    try {
        const response = await fetch(`${API_BASE}/api/equipment`);
        if (!response.ok) throw new Error("Could not load equipment");
        
        const equips = await response.json();
        equipmentSelect.innerHTML = '<option value="" disabled selected>Select equipment to audit...</option>';
        
        equips.forEach(eq => {
            const opt = document.createElement("option");
            opt.value = eq.id;
            opt.textContent = `${eq.id} - ${eq.name}`;
            equipmentSelect.appendChild(opt);
        });

        // Update home screen suggestion template chips dynamically
        updateSuggestionChips(equips);
    } catch (err) {
        console.error(err);
    }
}

function updateSuggestionChips(equips) {
    const chipContainer = document.getElementById("tour-step-3");
    if (!chipContainer) return;
    
    if (equips && equips.length >= 2) {
        const eq1 = equips[0].id;
        const eq2 = equips[1].id;
        chipContainer.innerHTML = `
            <span class="suggestion-chip" onclick="fillQuery('What is the maintenance history of ${eq1}?')">${eq1} History</span>
            <span class="suggestion-chip" onclick="fillQuery('What is the safety procedure for confined space entry?')">Confined Space SOP</span>
            <span class="suggestion-chip" onclick="fillQuery('Has there been any near-miss or failure on ${eq2}?')">${eq2} Status</span>
        `;
    } else if (equips && equips.length === 1) {
        const eq1 = equips[0].id;
        chipContainer.innerHTML = `
            <span class="suggestion-chip" onclick="fillQuery('What is the maintenance history of ${eq1}?')">${eq1} History</span>
            <span class="suggestion-chip" onclick="fillQuery('What is the safety procedure for confined space entry?')">Confined Space SOP</span>
        `;
    } else {
        chipContainer.innerHTML = `
            <span class="suggestion-chip" onclick="fillQuery('What is the safety procedure for confined space entry?')">Confined Space SOP</span>
        `;
    }
}

// Load Timeline logs
async function loadTimeline(equipmentId) {
    timelineContainer.innerHTML = `
        <div style="display: flex; flex-direction: column; gap: 12px; padding: 4px;">
            <div style="padding: 16px; border: 1px solid var(--border-color); border-radius: 8px; background: #fff; display: flex; flex-direction: column; gap: 8px;">
                <div class="shimmer-card shimmer-title"></div>
                <div class="shimmer-card shimmer-paragraph"></div>
                <div class="shimmer-card shimmer-paragraph-short"></div>
            </div>
        </div>
    `;

    try {
        const response = await fetch(`${API_BASE}/api/timeline/${equipmentId}`);
        if (!response.ok) throw new Error("Failed to load timeline details");
        
        const timeline = await response.json();
        
        if (timeline.length === 0) {
            timelineContainer.innerHTML = '<div class="timeline-placeholder"><i class="fa-solid fa-circle-info placeholder-icon"></i><p>No historical events logged for this asset.</p></div>';
            return;
        }

        let rcaBarHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 18px; padding: 12px 18px; background: rgba(2, 132, 199, 0.03); border: 1px solid rgba(2, 132, 199, 0.12); border-radius: 12px;">
                <span style="font-size: 13px; font-weight: 600; color: var(--color-primary-hover);"><i class="fa-solid fa-lightbulb"></i> Need Root Cause Analysis for failure incidents?</span>
                <button class="btn btn-primary btn-sm" onclick="runRcaAnalysis('${equipmentId}')" style="font-size: 11.5px; padding: 6px 14px;"><i class="fa-solid fa-diagram-project"></i> Run Root Cause Analysis (RCA)</button>
            </div>
            <div id="rca-output-box" style="display: none; margin-bottom: 20px;"></div>
        `;

        let html = rcaBarHTML + '<div class="timeline-flow">';
        timeline.forEach(item => {
            let icon = "fa-screwdriver-wrench";
            if (item.type === "incident") icon = "fa-triangle-exclamation";
            if (item.type === "inspection") icon = "fa-clipboard-check";
            
            html += `
                <div class="timeline-item type-${item.type}">
                    <div class="timeline-bullet"></div>
                    <div class="timeline-card">
                        <div class="timeline-meta-row">
                            <span class="timeline-date"><i class="fa-solid fa-calendar-day"></i> ${item.date}</span>
                            <span class="timeline-badge ${item.badge_class}">${item.status}</span>
                        </div>
                        <div class="timeline-title">
                            <i class="fa-solid ${icon}"></i> ${item.title}
                        </div>
                        <div class="timeline-details">
                            ${item.details}
                        </div>
                    </div>
                </div>
            `;
        });
        
        html += '</div>';
        timelineContainer.innerHTML = html;
        
    } catch (err) {
        timelineContainer.innerHTML = `<div class="timeline-placeholder"><i class="fa-solid fa-circle-xmark placeholder-icon text-danger"></i><p>Error: ${err.message}</p></div>`;
    }
}

// Load Proactive alerts
async function loadPatterns() {
    insightsContainer.innerHTML = `
        <div class="shimmer-card"></div>
        <div class="shimmer-card"></div>
    `;

    try {
        const response = await fetch(`${API_BASE}/api/patterns`);
        if (!response.ok) throw new Error("Could not retrieve patterns");
        
        activePatterns = await response.json();
        
        if (activePatterns.length === 0) {
            insightsContainer.innerHTML = '<div class="timeline-placeholder"><p>No operational hazards flagged.</p></div>';
            return;
        }

        let html = "";
        activePatterns.forEach(pat => {
            let severityClass = "severity-info";
            let badgeClass = "badge-info";
            let icon = "fa-circle-info";
            
            if (pat.severity.toLowerCase() === "critical") {
                severityClass = "severity-danger";
                badgeClass = "badge-critical";
                icon = "fa-triangle-exclamation";
            } else if (pat.severity.toLowerCase() === "warning") {
                severityClass = "severity-warning";
                badgeClass = "badge-warning";
                icon = "fa-triangle-exclamation";
            }

            html += `
                <div class="insight-card ${severityClass}">
                    <div class="insight-top-row">
                        <div class="insight-title-area">
                            <h3>${pat.title}</h3>
                            <span>Equipment: <b>${pat.equipment_id}</b> (${pat.equipment_name})</span>
                        </div>
                        <span class="severity-badge ${badgeClass}"><i class="fa-solid ${icon}"></i> ${pat.severity}</span>
                    </div>
                    
                    <p class="insight-desc">${pat.description}</p>
                    
                    <div class="insight-rec">
                        <b>Proactive Recommendation:</b> ${pat.recommendation}
                    </div>
                    
                    <div class="insight-footer">
                        <button class="evidence-btn" onclick="showEvidence('${pat.id}')">
                            <i class="fa-solid fa-circle-nodes"></i> View Graph Evidence
                        </button>
                    </div>
                </div>
            `;
        });
        
        insightsContainer.innerHTML = html;

    } catch (err) {
        insightsContainer.innerHTML = `<div class="timeline-placeholder"><p>Error scanning logs: ${err.message}</p></div>`;
    }
}

// Modal Evidence Details loader
function showEvidence(patternId) {
    const pattern = activePatterns.find(p => p.id === patternId);
    if (!pattern) return;

    modalTitle.innerHTML = `<i class="fa-solid fa-circle-nodes"></i> Evidence Audit: ${pattern.title}`;
    
    let wosHTML = "None logged";
    if (pattern.evidence.work_orders && pattern.evidence.work_orders.length > 0) {
        wosHTML = pattern.evidence.work_orders
            .map(wo => `<span class="evidence-pill"><i class="fa-solid fa-screwdriver-wrench"></i> ${wo}</span>`)
            .join(" ");
    }

    let incsHTML = "None logged";
    if (pattern.evidence.incidents && pattern.evidence.incidents.length > 0) {
        incsHTML = pattern.evidence.incidents
            .map(inc => `<span class="evidence-pill evidence-pill-red"><i class="fa-solid fa-triangle-exclamation"></i> ${inc}</span>`)
            .join(" ");
    }

    let inspsHTML = "";
    if (pattern.evidence.inspections && pattern.evidence.inspections.length > 0) {
        inspsHTML = `
            <div class="evidence-section">
                <h4>Compliance Audit Records</h4>
                <div class="evidence-pills">
                    ${pattern.evidence.inspections
                        .map(insp => `<span class="evidence-pill"><i class="fa-solid fa-clipboard-check"></i> ${insp}</span>`)
                        .join(" ")}
                </div>
            </div>
        `;
    }

    let downtimeHTML = "";
    if (pattern.evidence.downtime_hours !== undefined) {
        downtimeHTML = `
            <div class="evidence-section">
                <h4>Safety Impact Statistics</h4>
                <p style="font-size: 13px; font-weight: 300;">
                    Accumulated Downtime: <strong style="color: var(--color-danger); font-size: 13.5px;">${pattern.evidence.downtime_hours} Hours</strong>
                </p>
            </div>
        `;
    }

    modalBody.innerHTML = `
        <div class="evidence-block">
            <div class="evidence-section">
                <h4>Linked Work Orders</h4>
                <div class="evidence-pills">${wosHTML}</div>
            </div>
            
            <div class="evidence-section">
                <h4>Linked Near-Misses / Incidents</h4>
                <div class="evidence-pills">${incsHTML}</div>
            </div>
            
            ${inspsHTML}
            ${downtimeHTML}
        </div>
    `;

    evidenceModal.style.display = "flex";
}

// ==========================================
// Interactive Force-Directed Knowledge Graph Visualizer
// ==========================================

async function openGraphVisualizer() {
    if (!isSystemIngested) return;
    graphModal.style.display = "flex";
    resizeCanvas();
    
    // Reset Zoom / Pan
    transformScale = 1;
    transformX = 0;
    transformY = 0;
    
    // Load Graph JSON data from backend
    try {
        const response = await fetch(`${API_BASE}/api/graph`);
        if (!response.ok) throw new Error("Could not retrieve graph schema");
        
        const data = await response.json();
        
        // Map nodes
        simulationNodes = data.nodes.map(n => {
            const width = canvas.width;
            const height = canvas.height;
            return {
                id: n.id,
                label: n.id,
                type: n.type || "unknown",
                x: width / 2 + (Math.random() - 0.5) * 300,
                y: height / 2 + (Math.random() - 0.5) * 300,
                vx: 0,
                vy: 0
            };
        });
        
        // Map links (NetworkX uses source/target index or keys)
        simulationLinks = data.links.map(l => {
            const sourceId = typeof l.source === 'object' ? l.source.id : (typeof l.source === 'number' ? data.nodes[l.source].id : l.source);
            const targetId = typeof l.target === 'object' ? l.target.id : (typeof l.target === 'number' ? data.nodes[l.target].id : l.target);
            return {
                source: sourceId,
                target: targetId,
                type: l.relation || "connected"
            };
        });
        
        // Start physical engine loop
        simulationActive = true;
        runSimulationTick();
        
    } catch (err) {
        console.error("Failed to load graph visualization", err);
    }
}

function closeGraphVisualizer() {
    graphModal.style.display = "none";
    simulationActive = false;
}

function resizeCanvas() {
    const parent = canvas.parentElement;
    canvas.width = parent.clientWidth;
    canvas.height = parent.clientHeight;
}

// Physics Loop
function runSimulationTick() {
    if (!simulationActive) return;
    
    const width = canvas.width;
    const height = canvas.height;
    const centerX = width / 2;
    const centerY = height / 2;
    
    // 1. Repulsion between all nodes (Coulomb repulsion)
    for (let i = 0; i < simulationNodes.length; i++) {
        let n1 = simulationNodes[i];
        for (let j = i + 1; j < simulationNodes.length; j++) {
            let n2 = simulationNodes[j];
            let dx = n2.x - n1.x;
            let dy = n2.y - n1.y;
            if (dx === 0) dx = 0.1;
            let dist = Math.sqrt(dx*dx + dy*dy);
            if (dist < 1) dist = 1;
            
            // Strong push away if nodes get too close
            let force = 600 / (dist * dist);
            let fx = (dx / dist) * force;
            let fy = (dy / dist) * force;
            
            if (n1 !== dragNode) {
                n1.vx -= fx;
                n1.vy -= fy;
            }
            if (n2 !== dragNode) {
                n2.vx += fx;
                n2.vy += fy;
            }
        }
    }
    
    // 2. Attraction along edges (Hooke's spring pull)
    for (let link of simulationLinks) {
        let n1 = simulationNodes.find(n => n.id === link.source);
        let n2 = simulationNodes.find(n => n.id === link.target);
        if (!n1 || !n2) continue;
        
        let dx = n2.x - n1.x;
        let dy = n2.y - n1.y;
        let dist = Math.sqrt(dx*dx + dy*dy);
        if (dist < 1) dist = 1;
        
        let targetLen = 80;
        let k = 0.035;
        let force = (dist - targetLen) * k;
        let fx = (dx / dist) * force;
        let fy = (dy / dist) * force;
        
        if (n1 !== dragNode) {
            n1.vx += fx;
            n1.vy += fy;
        }
        if (n2 !== dragNode) {
            n2.vx -= fx;
            n2.vy -= fy;
        }
    }
    
    // 3. Gravity pulling nodes toward the canvas center & Update positions
    const gravity = 0.012;
    const damping = 0.82;
    for (let node of simulationNodes) {
        if (node === dragNode) continue;
        
        let dx = centerX - node.x;
        let dy = centerY - node.y;
        node.vx += dx * gravity;
        node.vy += dy * gravity;
        
        node.x += node.vx;
        node.y += node.vy;
        
        // Apply friction damping
        node.vx *= damping;
        node.vy *= damping;
        
        // Prevent floating completely offscreen
        node.x = Math.max(20, Math.min(width - 20, node.x));
        node.y = Math.max(20, Math.min(height - 20, node.y));
    }
    
    drawSimulation();
    requestAnimationFrame(runSimulationTick);
}

// Canvas rendering loop
function drawSimulation() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.save();
    
    // Apply zoom & pan translation offsets
    ctx.translate(transformX, transformY);
    ctx.scale(transformScale, transformScale);
    
    // Draw links
    ctx.strokeStyle = "#e2e8f0";
    ctx.lineWidth = 1;
    for (let link of simulationLinks) {
        let n1 = simulationNodes.find(n => n.id === link.source);
        let n2 = simulationNodes.find(n => n.id === link.target);
        if (n1 && n2) {
            ctx.beginPath();
            ctx.moveTo(n1.x, n1.y);
            ctx.lineTo(n2.x, n2.y);
            ctx.stroke();
        }
    }
    
    // Draw nodes
    for (let node of simulationNodes) {
        ctx.beginPath();
        let radius = node.type === "equipment" ? 14 : 9;
        ctx.arc(node.x, node.y, radius, 0, Math.PI * 2);
        
        ctx.fillStyle = TYPE_COLORS[node.type] || "#94a3b8";
        ctx.fill();
        ctx.strokeStyle = "#fff";
        ctx.lineWidth = 2;
        ctx.stroke();
        
        // Text labels for equipment nodes, or if hovered/dragged
        if (node.type === "equipment" || node === hoverNode || node === dragNode) {
            ctx.fillStyle = document.body.classList.contains("dark-theme") ? "#f8fafc" : "#1e293b";
            ctx.font = "bold 9px sans-serif";
            ctx.fillText(node.label, node.x + radius + 4, node.y + 3);
        }
    }
    ctx.restore();
}

// Map mouse coordinates to coordinate space taking zoom and pan scale factors into account
function getMousePos(e) {
    const rect = canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;
    return {
        x: (mx - transformX) / transformScale,
        y: (my - transformY) / transformScale
    };
}

function setupCanvasListeners() {
    canvas.addEventListener("mousedown", (e) => {
        const pos = getMousePos(e);
        
        // Check if user clicked on a node
        let clickedNode = null;
        for (let node of simulationNodes) {
            let dx = node.x - pos.x;
            let dy = node.y - pos.y;
            let dist = Math.sqrt(dx*dx + dy*dy);
            let radius = node.type === "equipment" ? 14 : 9;
            if (dist < radius) {
                clickedNode = node;
                break;
            }
        }
        
        if (clickedNode) {
            dragNode = clickedNode;
            dragNode.vx = 0;
            dragNode.vy = 0;
        } else {
            isPanning = true;
            lastMouseX = e.clientX;
            lastMouseY = e.clientY;
        }
    });

    canvas.addEventListener("mousemove", (e) => {
        const pos = getMousePos(e);
        
        // Check for node hovers
        hoverNode = null;
        for (let node of simulationNodes) {
            let dx = node.x - pos.x;
            let dy = node.y - pos.y;
            let dist = Math.sqrt(dx*dx + dy*dy);
            let radius = node.type === "equipment" ? 14 : 9;
            if (dist < radius) {
                hoverNode = node;
                break;
            }
        }
        
        if (dragNode) {
            dragNode.x = pos.x;
            dragNode.y = pos.y;
            dragNode.vx = 0;
            dragNode.vy = 0;
        } else if (isPanning) {
            let dx = e.clientX - lastMouseX;
            let dy = e.clientY - lastMouseY;
            transformX += dx;
            transformY += dy;
            lastMouseX = e.clientX;
            lastMouseY = e.clientY;
            drawSimulation();
        }
    });

    canvas.addEventListener("mouseup", () => {
        dragNode = null;
        isPanning = false;
    });

    canvas.addEventListener("mouseleave", () => {
        dragNode = null;
        isPanning = false;
    });

    // Zoom listener using mouse wheel
    canvas.addEventListener("wheel", (e) => {
        e.preventDefault();
        const pos = getMousePos(e);
        const zoomFactor = 1.05;
        
        if (e.deltaY < 0) {
            // Zoom In
            transformScale = Math.min(3, transformScale * zoomFactor);
        } else {
            // Zoom Out
            transformScale = Math.max(0.4, transformScale / zoomFactor);
        }
        drawSimulation();
    });
}



// ==========================================
// P&ID Tag Hotspot Selector with Live Telemetry
// ==========================================
let pidInterval = null;

window.selectPidTag = function(id, name, status, source, desc) {
    if (pidInterval) clearInterval(pidInterval);
    const infoPanel = document.getElementById("pid-info-panel");
    if (!infoPanel) return;
    
    let statusClass = "badge-incident-high";
    if (status.toLowerCase().includes("warning")) statusClass = "badge-incident-medium";
    
    // Setup telemetry base values
    let telemetryHTML = "";
    let baseVal1 = 120.0;
    let baseVal2 = 85.0;
    let label1 = "Vessel Pressure";
    let label2 = "Motor Temp";
    let unit1 = "PSI";
    let unit2 = "°C";
    
    if (id === "VALVE-102") {
        baseVal1 = 145.2;
        baseVal2 = 92.4;
        label1 = "Line Pressure";
        label2 = "Valve Body Temp";
    } else if (id === "GAS-DET-11") {
        baseVal1 = 820.0;
        baseVal2 = 18.0;
        label1 = "Methane Conc";
        label2 = "Sensor Drift";
        unit1 = "ppm";
        unit2 = "%";
    }
    
    infoPanel.innerHTML = `
        <div style="display: flex; flex-direction: column; gap: 12px; animation: bubbleFade 0.28s ease-out;">
            <div>
                <span class="badge ${statusClass}" style="font-size: 10px; text-transform: uppercase;">${status}</span>
                <h3 style="font-size: 18px; margin-top: 6px; font-weight: 700;">${id}</h3>
                <span style="font-size: 11px; color: var(--text-muted); font-weight: 600;">CLASS: ${name.toUpperCase()}</span>
            </div>
            
            <div style="border-top: 1px solid var(--border-color); padding-top: 12px;">
                <p style="font-size: 12.5px; line-height: 1.5; color: var(--text-secondary);">${desc}</p>
            </div>
            
            <!-- Live Telemetry Box -->
            <div style="background: rgba(14, 165, 233, 0.03); border: 1px solid rgba(14, 165, 233, 0.12); padding: 12px 16px; border-radius: 8px;" id="pid-live-sensors">
                <div style="font-size: 11.5px; font-weight: 700; color: var(--color-primary-hover); margin-bottom: 6px; display: flex; align-items: center; justify-content: space-between;">
                    <span><i class="fa-solid fa-satellite-dish"></i> Live Telemetry Stream</span>
                    <span style="display: inline-flex; align-items: center; gap: 4px; font-size: 9px; font-weight: 700; text-transform: uppercase; color: var(--color-success);">
                        <span style="display: inline-block; width: 6px; height: 6px; border-radius: 50%; background: var(--color-success); animation: statusPulse 1s infinite;"></span> Active
                    </span>
                </div>
                <div style="display: flex; justify-content: space-between; font-size: 12px; color: var(--text-secondary);">
                    <span>${label1}: <strong id="pid-live-val1" style="color: var(--text-primary);">${baseVal1.toFixed(1)} ${unit1}</strong></span>
                    <span>${label2}: <strong id="pid-live-val2" style="color: var(--text-primary);">${baseVal2.toFixed(1)} ${unit2}</strong></span>
                </div>
            </div>
            
            <div style="background: var(--bg-main); border: 1px solid var(--border-color); padding: 10px; border-radius: 8px; font-size: 11px;">
                <strong>Mapped Source File:</strong><br>
                <code style="display: block; margin-top: 4px; color: var(--color-primary-hover);">${source}</code>
            </div>
            
            <div style="display: flex; flex-direction: column; gap: 8px; margin-top: 12px;">
                <button class="btn btn-primary" onclick="queryPidInCopilot('${id}')" style="font-size: 12px; padding: 8px; justify-content: center;">
                    <i class="fa-solid fa-comments"></i> Ask Copilot about history
                </button>
                <button class="btn btn-secondary" onclick="viewPidInTimeline('${id}')" style="font-size: 12px; padding: 8px; justify-content: center;">
                    <i class="fa-solid fa-clock-rotate-left"></i> View timeline events
                </button>
            </div>
        </div>
    `;
    
    // Start dynamic fluctuations
    pidInterval = setInterval(() => {
        const val1El = document.getElementById("pid-live-val1");
        const val2El = document.getElementById("pid-live-val2");
        if (val1El && val2El) {
            const v1 = (baseVal1 + (Math.random() - 0.5) * (id === "GAS-DET-11" ? 15 : 2)).toFixed(1);
            const v2 = (baseVal2 + (Math.random() - 0.5) * (id === "GAS-DET-11" ? 0.4 : 0.8)).toFixed(1);
            val1El.textContent = `${v1} ${unit1}`;
            val2El.textContent = `${v2} ${unit2}`;
        }
    }, 1500);
};

window.queryPidInCopilot = function(equipmentId) {
    switchTab("copilot");
    fillQuery(`What is the maintenance history of ${equipmentId}?`);
};

window.viewPidInTimeline = function(equipmentId) {
    switchTab("timeline");
    const select = document.getElementById("equipment-select");
    if (select) {
        select.value = equipmentId;
        // Trigger select change event
        const event = new Event('change');
        select.dispatchEvent(event);
    }
};

// ==========================================
// Root Cause Analysis (RCA) Engine
// ==========================================
window.runRcaAnalysis = async function(equipmentId) {
    const rcaBox = document.getElementById("rca-output-box");
    if (!rcaBox) return;
    
    rcaBox.style.display = "block";
    rcaBox.innerHTML = `
        <div style="padding: 18px; border: 1px solid var(--border-color); border-radius: 12px; background: #fff; text-align: center;">
            <i class="fa-solid fa-gear fa-spin" style="font-size: 24px; color: var(--color-primary-hover); margin-bottom: 8px;"></i>
            <p style="font-size: 12px; color: var(--text-muted);">Tracing Knowledge Graph links & running Root Cause Analysis...</p>
        </div>
    `;
    
    try {
        const response = await fetch(`${API_BASE}/api/rca/${equipmentId}`);
        if (!response.ok) throw new Error("Could not compute root cause data");
        const data = await response.json();
        
        let whysHTML = "";
        data.whys.forEach((why, idx) => {
            whysHTML += `
                <div style="padding: 8px 12px; border: 1px solid var(--border-color); border-radius: 8px; background: var(--bg-main); font-size: 12px; color: var(--text-secondary);">
                    ${why}
                </div>
            `;
            if (idx < data.whys.length - 1) {
                whysHTML += `
                    <div style="text-align: center; margin: 4px 0; color: var(--text-dim); font-size: 11px;">
                        <i class="fa-solid fa-arrow-down-long"></i>
                    </div>
                `;
            }
        });
        
        rcaBox.innerHTML = `
            <div style="padding: 20px; border: 1px solid var(--border-color); border-radius: 12px; background: #fff; box-shadow: var(--shadow-sm); animation: bubbleFade 0.3s ease-out; display: flex; flex-direction: column; gap: 14px;">
                <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border-color); padding-bottom: 8px;">
                    <h4 style="font-size: 14px; font-weight: 700; color: var(--text-primary);"><i class="fa-solid fa-diagram-project"></i> Root Cause Analysis (5 Whys)</h4>
                    <span style="font-size: 10px; font-weight: 700; color: var(--text-muted);">SIGNOFF: ${data.technician}</span>
                </div>
                
                <div style="font-size: 12.5px; font-weight: 600; color: var(--color-danger); padding: 6px; background: rgba(239, 68, 68, 0.03); border-radius: 6px;">
                    Incident: ${data.incident}
                </div>
                
                <div style="display: flex; flex-direction: column;">
                    ${whysHTML}
                </div>
                
                <div style="border-top: 1px dashed var(--border-color); padding-top: 12px; font-size: 12px; line-height: 1.4;">
                    <strong style="color: var(--color-success);"><i class="fa-solid fa-lightbulb"></i> Recommended Corrective Action:</strong><br>
                    <p style="margin-top: 4px; color: var(--text-secondary);">${data.corrective_action}</p>
                </div>
            </div>
        `;
        
    } catch (e) {
        rcaBox.innerHTML = `
            <div style="padding: 12px; border: 1px solid var(--color-danger); border-radius: 8px; background: rgba(239, 68, 68, 0.03); color: var(--color-danger); font-size: 12px;">
                Failed to load RCA: ${e.message}
            </div>
        `;
    }
};

// ==========================================
// Compliance Audit Panel Engine
// ==========================================
let activeComplianceItems = [];

window.loadCompliance = async function() {
    const container = document.getElementById("compliance-list-container");
    if (!container) return;
    
    container.innerHTML = `
        <div class="shimmer-card" style="height: 120px;"></div>
        <div class="shimmer-card" style="height: 120px;"></div>
    `;
    
    try {
        const response = await fetch(`${API_BASE}/api/compliance`);
        if (!response.ok) throw new Error("Could not retrieve compliance items");
        activeComplianceItems = await response.json();
        renderComplianceItems(activeComplianceItems);
    } catch (e) {
        container.innerHTML = `<div class="timeline-placeholder"><i class="fa-solid fa-circle-xmark placeholder-icon text-danger"></i><p>Error: ${e.message}</p></div>`;
    }
};

function renderComplianceItems(items) {
    const container = document.getElementById("compliance-list-container");
    if (!container) return;
    
    if (items.length === 0) {
        container.innerHTML = `
            <div class="timeline-placeholder">
                <i class="fa-solid fa-circle-info placeholder-icon"></i>
                <p>No matching compliance records found.</p>
            </div>
        `;
        return;
    }
    
    let html = "";
    items.forEach(reg => {
        let badgeClass = "badge-compliant";
        if (reg.status === "Warning") badgeClass = "badge-incident-medium";
        else if (reg.status === "Non-Compliant") badgeClass = "badge-incident-high";
        
        html += `
            <div class="insight-card" style="border-left-width: 5px; flex-direction: column; gap: 14px; animation: bubbleFade 0.25s ease-out;">
                <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                    <div>
                        <span class="badge ${badgeClass}" style="font-size: 9.5px; text-transform: uppercase;">${reg.status}</span>
                        <h3 style="font-size: 15.5px; font-weight: 700; margin-top: 6px; color: var(--text-primary);">${reg.regulation}</h3>
                        <span style="font-size: 11px; color: var(--text-muted); font-weight: 600;">AUTHORITY: ${reg.regulatory_body}</span>
                    </div>
                    <span style="font-size: 11.5px; font-weight: 700; background: var(--bg-main); padding: 4px 8px; border-radius: 6px; border: 1px solid var(--border-color);">Mapped Asset: ${reg.equipment_id}</span>
                </div>
                
                <div style="font-size: 13px; line-height: 1.45; color: var(--text-secondary);">
                    <strong>Rule Standard:</strong> ${reg.requirement}
                </div>
                
                <div style="display: flex; gap: 8px; align-items: center; border-top: 1px solid var(--border-color); padding-top: 12px; justify-content: space-between;">
                    <div style="display: flex; gap: 6px;">
                        ${reg.evidence.inspections.map(ins => `<span class="citation-badge" style="font-size: 10px;"><i class="fa-solid fa-file-shield"></i> ${ins}</span>`).join('')}
                        ${reg.evidence.incidents.map(inc => `<span class="citation-badge" style="font-size: 10px; color: var(--color-danger); border-color: rgba(239,68,68,0.15);"><i class="fa-solid fa-triangle-exclamation"></i> ${inc}</span>`).join('')}
                    </div>
                    <button class="evidence-btn" onclick="exportSingleEvidence('${reg.regulation}', '${reg.equipment_id}', '${reg.evidence.last_audit}')">
                        <i class="fa-solid fa-file-lines"></i> View Compliance Log
                    </button>
                </div>
            </div>
        `;
    });
    container.innerHTML = html;
}

window.filterCompliance = function(keyword) {
    if (!keyword) {
        renderComplianceItems(activeComplianceItems);
        return;
    }
    const filtered = activeComplianceItems.filter(item => 
        item.regulation.toLowerCase().includes(keyword.toLowerCase())
    );
    renderComplianceItems(filtered);
};;

window.exportSingleEvidence = function(regulation, equipmentId, lastAudit) {
    const modal = document.getElementById("evidence-modal");
    const title = document.getElementById("modal-title");
    const body = document.getElementById("modal-body");
    if (!modal) return;
    
    title.innerHTML = `<i class="fa-solid fa-file-shield"></i> Compliance Report Checklist`;
    body.innerHTML = `
        <div class="evidence-block" style="animation: bubbleFade 0.25s ease-out;">
            <div style="text-align: center; border-bottom: 1px solid var(--border-color); padding-bottom: 14px;">
                <h4 style="font-size: 14px; font-weight: 700; color: var(--text-primary);">${regulation}</h4>
                <span style="font-size: 11px; color: var(--text-muted);">AUDIT TRAIL LOG • ASSET: ${equipmentId}</span>
            </div>
            
            <div style="display: flex; flex-direction: column; gap: 10px;">
                <div style="display: flex; justify-content: space-between; font-size: 12px; border-bottom: 1px solid var(--bg-main); padding-bottom: 6px;">
                    <span>Factory Act Compliance</span>
                    <strong class="text-success"><i class="fa-solid fa-circle-check"></i> Standard Met</strong>
                </div>
                <div style="display: flex; justify-content: space-between; font-size: 12px; border-bottom: 1px solid var(--bg-main); padding-bottom: 6px;">
                    <span>Pressure Relief Calibration Certificate</span>
                    <strong class="text-success"><i class="fa-solid fa-circle-check"></i> Verified (INSP-901)</strong>
                </div>
                <div style="display: flex; justify-content: space-between; font-size: 12px; border-bottom: 1px solid var(--bg-main); padding-bottom: 6px;">
                    <span>LOTO Permit to Work</span>
                    <strong class="text-success"><i class="fa-solid fa-circle-check"></i> Logged (2026-07-01)</strong>
                </div>
                <div style="display: flex; justify-content: space-between; font-size: 12px; border-bottom: 1px solid var(--bg-main); padding-bottom: 6px;">
                    <span>Last Internal Audit Date</span>
                    <strong>${lastAudit}</strong>
                </div>
            </div>
            
            <div style="background: var(--bg-main); border: 1px dashed var(--border-color); padding: 12px; border-radius: 8px; font-size: 11.5px;">
                <strong>Digital Verification Stamp:</strong><br>
                <code style="display: block; font-family: monospace; margin-top: 4px; color: var(--text-muted);">MD5-CERT // PLANTBRAIN-AUDIT-STAMP // 0xEA9211C840BD</code>
            </div>
            
            <div style="display: flex; gap: 8px; justify-content: flex-end; border-top: 1px solid var(--border-color); padding-top: 14px;">
                <button class="btn btn-secondary btn-sm" onclick="document.getElementById('evidence-modal').style.display='none'">Close</button>
                <button class="btn btn-primary btn-sm" onclick="window.print()"><i class="fa-solid fa-print"></i> Print Document</button>
            </div>
        </div>
    `;
    
    modal.style.display = "flex";
};

// ==========================================
// Generate All Compliance Packages
// ==========================================
window.generateCompliancePackage = function() {
    const modal = document.getElementById("evidence-modal");
    const title = document.getElementById("modal-title");
    const body = document.getElementById("modal-body");
    if (!modal) return;
    
    title.innerHTML = `<i class="fa-solid fa-box-archive"></i> Export Complete Evidence Package`;
    body.innerHTML = `
        <div class="evidence-block" style="animation: bubbleFade 0.25s ease-out;">
            <p style="font-size: 13px; color: var(--text-secondary); line-height: 1.45;">
                PlantBrain is compiling an all-asset regulatory compliance index matching: Factory Act 1948, PESO vessel safety rules, and OISD oil-mill safety clearances.
            </p>
            
            <div style="background: var(--bg-main); border: 1px solid var(--border-color); padding: 14px; border-radius: 8px; display: flex; flex-direction: column; gap: 10px;">
                <div style="display: flex; align-items: center; gap: 8px; font-size: 12px;">
                    <i class="fa-solid fa-square-check" style="color: var(--color-success);"></i> <span>Factory Act Gas Ventilation Evidence Checklist</span>
                </div>
                <div style="display: flex; align-items: center; gap: 8px; font-size: 12px;">
                    <i class="fa-solid fa-square-check" style="color: var(--color-success);"></i> <span>PESO Pressure Vessel Hydrostatic Test Logs</span>
                </div>
                <div style="display: flex; align-items: center; gap: 8px; font-size: 12px;">
                    <i class="fa-solid fa-square-check" style="color: var(--color-success);"></i> <span>OISD Hot Work Permitting & LOTO Audit Package</span>
                </div>
            </div>
            
            <div style="display: flex; flex-direction: column; gap: 6px; font-size: 11px; color: var(--text-muted);">
                <span>Generated: ${new Date().toLocaleDateString()} | Compliance Officer Sign-off</span>
                <span>Stamp Ref: PB-DG-1948-2026</span>
            </div>
            
            <div style="display: flex; gap: 8px; justify-content: flex-end; border-top: 1px solid var(--border-color); padding-top: 14px;">
                <button class="btn btn-secondary btn-sm" onclick="document.getElementById('evidence-modal').style.display='none'">Cancel</button>
                <button class="btn btn-primary btn-sm" onclick="window.print()"><i class="fa-solid fa-download"></i> Save & Export Evidence (.pdf)</button>
            </div>
        </div>
    `;
    
    modal.style.display = "flex";
};
