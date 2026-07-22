import os
import json
import csv
import pandas as pd
from datetime import datetime

class PatternIntelligenceAgent:
    def __init__(self, data_dir):
        self.data_dir = data_dir

    def load_maintenance_logs(self):
        logs = []
        if not os.path.exists(self.data_dir):
            return logs
            
        for filename in os.listdir(self.data_dir):
            if filename.endswith(".csv"):
                file_path = os.path.join(self.data_dir, filename)
                try:
                    df = pd.read_csv(file_path)
                    cols = [c.lower().strip() for c in df.columns]
                    if "work_order_id" in cols and "equipment_id" in cols:
                        # Parse logs
                        for _, row in df.iterrows():
                            logs.append({
                                "work_order_id": str(row.get("work_order_id", "")),
                                "equipment_id": str(row.get("equipment_id", "")),
                                "equipment_name": str(row.get("equipment_name", f"Asset {row.get('equipment_id')}")),
                                "date": str(row.get("date", "")),
                                "technician": str(row.get("technician", "Unknown")),
                                "issue_reported": str(row.get("issue_reported", "")),
                                "action_taken": str(row.get("action_taken", "")),
                                "downtime_hours": float(row.get("downtime_hours", 0)),
                                "status": str(row.get("status", ""))
                            })
                except Exception as e:
                    print(f"Error parsing logs in {filename}: {e}")
        return logs

    def load_incident_reports(self):
        incidents = []
        if not os.path.exists(self.data_dir):
            return incidents
            
        for filename in os.listdir(self.data_dir):
            if filename.endswith(".json"):
                file_path = os.path.join(self.data_dir, filename)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    records = data if isinstance(data, list) else [data]
                    if len(records) > 0 and "report_id" in records[0]:
                        for rec in records:
                            incidents.append({
                                "report_id": str(rec.get("report_id", "")),
                                "date": str(rec.get("date", "")),
                                "location": str(rec.get("location", "")),
                                "equipment_involved": str(rec.get("equipment_involved", "")),
                                "description": str(rec.get("description", "")),
                                "root_cause": str(rec.get("root_cause", "")),
                                "severity": str(rec.get("severity", "Info")),
                                "corrective_action": str(rec.get("corrective_action", ""))
                            })
                except Exception as e:
                    print(f"Error parsing incidents in {filename}: {e}")
        return incidents

    def load_inspection_reports(self):
        inspections = []
        if not os.path.exists(self.data_dir):
            return inspections
            
        for filename in os.listdir(self.data_dir):
            if filename.endswith(".csv"):
                file_path = os.path.join(self.data_dir, filename)
                try:
                    df = pd.read_csv(file_path)
                    cols = [c.lower().strip() for c in df.columns]
                    if "inspection_id" in cols and "equipment_id" in cols:
                        for _, row in df.iterrows():
                            inspections.append({
                                "inspection_id": str(row.get("inspection_id", "")),
                                "equipment_id": str(row.get("equipment_id", "")),
                                "date": str(row.get("date", "")),
                                "inspector": str(row.get("inspector", "Unknown")),
                                "findings": str(row.get("findings", "")),
                                "compliance_status": str(row.get("compliance_status", "Compliant")),
                                "next_inspection_due": str(row.get("next_inspection_due", ""))
                            })
                except Exception as e:
                    print(f"Error parsing inspections in {filename}: {e}")
        return inspections

    def scan_for_patterns(self):
        logs = self.load_maintenance_logs()
        incidents = self.load_incident_reports()
        inspections = self.load_inspection_reports()
        
        insights = []
        if not logs:
            return insights
            
        # Group data by equipment ID
        equipments_in_logs = set(l["equipment_id"] for l in logs if l.get("equipment_id"))
        
        for eq_id in equipments_in_logs:
            eq_logs = [l for l in logs if l["equipment_id"] == eq_id]
            eq_name = eq_logs[0].get("equipment_name", f"Asset {eq_id}")
            eq_incidents = [i for i in incidents if i.get("equipment_involved") == eq_id or eq_id in i.get("description", "")]
            eq_inspections = [i for i in inspections if i.get("equipment_id") == eq_id]
            
            # 1. Cyclical Failure Loop Detection (bearing / vibration / wear)
            vibration_wear = [l for l in eq_logs if any(k in (l.get("issue_reported", "") + " " + l.get("action_taken", "")).lower() for k in ["bearing", "vibration", "seal", "noise", "wear"])]
            if len(vibration_wear) >= 2 or len(eq_logs) >= 3:
                total_downtime = sum(float(l.get("downtime_hours", 0)) for l in eq_logs)
                eq_logs.sort(key=lambda x: x.get("date", ""))
                
                # Check interval
                avg_interval = 30.0
                try:
                    dates = [datetime.strptime(l["date"], "%Y-%m-%d") for l in eq_logs if l.get("date")]
                    if len(dates) >= 2:
                        intervals = [(dates[i] - dates[i-1]).days for i in range(1, len(dates))]
                        avg_interval = sum(intervals) / len(intervals) if intervals else 30.0
                except Exception:
                    pass
                    
                insights.append({
                    "id": f"INS-VIB-{eq_id}",
                    "title": f"Cyclical Wear Loop on {eq_id}",
                    "equipment_id": eq_id,
                    "equipment_name": eq_name,
                    "severity": "Critical" if len(eq_incidents) > 0 else "Warning",
                    "description": (
                        f"Asset {eq_id} has logged {len(eq_logs)} maintenance events and {len(eq_incidents)} incident(s). "
                        f"A recurring failure pattern is observed repeating approximately every {avg_interval:.1f} days, "
                        f"causing {total_downtime:.1f} hours of total downtime."
                    ),
                    "pattern_type": "Cyclical Mechanical Wear Loop",
                    "recommendation": (
                        f"Enforce alignment tolerances, check for shaft fatigue, and perform a lubrication audit on {eq_id}. "
                        "Continuous vibration monitoring sensors are advised."
                    ),
                    "evidence": {
                        "work_orders": [l.get("work_order_id") for l in eq_logs],
                        "incidents": [i.get("report_id") for i in eq_incidents],
                        "downtime_hours": total_downtime
                    }
                })
                
            # 2. Calibration & Safety Compliance Drift Alert
            non_compliant = [i for i in eq_inspections if i.get("compliance_status", "").lower() == "non-compliant"]
            if len(non_compliant) >= 1 or len(eq_incidents) >= 2:
                insights.append({
                    "id": f"INS-COMP-{eq_id}",
                    "title": f"Calibration Drift / Safety Hazard on {eq_id}",
                    "equipment_id": eq_id,
                    "equipment_name": eq_name,
                    "severity": "Critical",
                    "description": (
                        f"Safety critical alert: {eq_id} is linked to {len(eq_incidents)} safety incident reports. "
                        f"Inspection records show non-compliance issues (Inspection IDs: {', '.join([i.get('inspection_id') for i in non_compliant]) or 'None'})."
                    ),
                    "pattern_type": "Regulatory Compliance Drift",
                    "recommendation": (
                        f"Recalibrate sensor instruments on {eq_id} immediately. Do not approve work orders "
                        "unless compliance checks are fully logged."
                    ),
                    "evidence": {
                        "work_orders": [l.get("work_order_id") for l in eq_logs],
                        "incidents": [i.get("report_id") for i in eq_incidents],
                        "inspections": [i.get("inspection_id") for i in eq_inspections]
                    }
                })
                
        return insights
