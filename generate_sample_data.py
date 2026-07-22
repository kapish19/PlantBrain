import os
import json
import csv
from datetime import datetime, timedelta

def create_directory_structure(base_dir):
    os.makedirs(os.path.join(base_dir, "sample_data"), exist_ok=True)
    os.makedirs(os.path.join(base_dir, "sample_data", "safety_procedures"), exist_ok=True)
    os.makedirs(os.path.join(base_dir, "sample_data", "equipment_manuals"), exist_ok=True)

def generate_maintenance_logs(base_dir):
    file_path = os.path.join(base_dir, "sample_data", "maintenance_logs.csv")
    headers = [
        "work_order_id", "equipment_id", "equipment_name", "date",
        "technician", "issue_reported", "action_taken", "downtime_hours", "status"
    ]
    
    logs = []
    
    # 1. PUMP-204 recurring bearing failure pattern (every 45-60 days)
    pump_failures = [
        ("WO-101", "2025-10-05", "David Vance", "High vibration and rattling sound in pump casing.", "Inspected bearing housing, found severe wear. Replaced outer bearing assembly.", 8.5, "Completed"),
        ("WO-115", "2025-11-28", "David Vance", "Pump high vibration warning triggered on SCADA.", "Reconditioned shaft assembly, replaced worn bearings, and topped up lubrication.", 12.0, "Completed"),
        ("WO-128", "2026-01-20", "Sarah Connor", "Loud bearing noise and high temperature readings.", "Replaced bearings, realigned motor coupling. Run test successful.", 6.0, "Completed"),
        ("WO-144", "2026-03-15", "David Vance", "Pump seal leakage and high vibration.", "Replaced ruptured mechanical seal and failed bearings. Checked alignment.", 16.0, "Completed"),
        ("WO-162", "2026-05-10", "Michael Chen", "High motor current draw and squealing bearing noise.", "Replaced bearing set, cleaned grease port, adjusted shaft alignment.", 8.0, "Completed"),
        ("WO-180", "2026-07-05", "David Vance", "Pump seized. Massive vibration prior to shutdown.", "Seized bearing overhaul. Replaced shaft, bearings, and mechanical seals. Re-aligned.", 24.0, "Completed")
    ]
    
    for wo_id, date_str, tech, issue, action, downtime, status in pump_failures:
        logs.append({
            "work_order_id": wo_id,
            "equipment_id": "PUMP-204",
            "equipment_name": "Crude Oil Transfer Centrifugal Pump",
            "date": date_str,
            "technician": tech,
            "issue_reported": issue,
            "action_taken": action,
            "downtime_hours": downtime,
            "status": status
        })
        
    # 2. BOILER-3 recurring pressure valve sticking pattern
    boiler_events = [
        ("WO-103", "2025-10-15", "Sarah Connor", "Boiler pressure relief valve stuck closed during high load.", "Manually freed the valve spindle. Cleaned scaling and scale deposits.", 4.0, "Completed"),
        ("WO-124", "2025-12-20", "Michael Chen", "Steam leakage from PRV-99 exhaust.", "Laid out boiler, disassembled PRV-99. Cleaned valve seat and replaced gasket.", 6.5, "Completed"),
        ("WO-151", "2026-04-05", "Sarah Connor", "PRV-99 sticking during test blowdown.", "Polished valve stem, adjusted spring tension to OEM specs. Calibrated pressure trigger.", 5.0, "Completed"),
        ("WO-177", "2026-06-25", "Michael Chen", "Overpressure alarm on BOILER-3. PRV-99 did not pop automatically.", "Emergency shutdown. Replaced stuck PRV-99 valve cartridge. Inspected steam line for scaling.", 10.0, "Completed")
    ]
    
    for wo_id, date_str, tech, issue, action, downtime, status in boiler_events:
        logs.append({
            "work_order_id": wo_id,
            "equipment_id": "BOILER-3",
            "equipment_name": "High-Pressure Steam Boiler",
            "date": date_str,
            "technician": tech,
            "issue_reported": issue,
            "action_taken": action,
            "downtime_hours": downtime,
            "status": status
        })

    # 3. GAS-DET-11 routine calibration issues and failures
    gas_events = [
        ("WO-110", "2025-11-02", "Elena Rostova", "Methane sensor calibration failed.", "Replaced filter cap, calibrated sensor using 50% LEL calibration gas.", 1.5, "Completed"),
        ("WO-135", "2026-02-16", "Elena Rostova", "Sensor drift warning on gas detector.", "Cleaned sensor head. Recalibrated methane and oxygen electrochemical cells.", 2.0, "Completed"),
        ("WO-159", "2026-05-02", "Elena Rostova", "Zero-point calibration failure.", "Sensor element poisoned. Replaced catalytic bead sensor module. Recalibrated.", 3.0, "Completed"),
        ("WO-175", "2026-06-20", "Elena Rostova", "Erratic sensor readings during daily test.", "Replaced battery, cleaned sensor cover, ran standard calibration cycle.", 2.0, "Completed")
    ]
    
    for wo_id, date_str, tech, issue, action, downtime, status in gas_events:
        logs.append({
            "work_order_id": wo_id,
            "equipment_id": "GAS-DET-11",
            "equipment_name": "Methane Gas Detector Area B",
            "date": date_str,
            "technician": tech,
            "issue_reported": issue,
            "action_taken": action,
            "downtime_hours": downtime,
            "status": status
        })

    # 4. Fill in other random maintenance logs to reach 50 rows
    techs = ["David Vance", "Sarah Connor", "Michael Chen", "Elena Rostova", "John Doe"]
    equip_list = [
        ("VALVE-102", "Main Feed Control Valve", "Stem leakage or sticking"),
        ("COMPRESSOR-5", "Instrument Air Compressor", "Oil level low / air filter clogged"),
        ("TURBINE-01", "Power Generation Steam Turbine", "Vibration analysis / filter swap"),
        ("HEATER-402", "Feed Preheater", "Tube cleaning / scale removal"),
        ("PUMP-205", "Crude Oil Transfer Backup Pump", "Motor coupling check / greasing")
    ]
    
    start_date = datetime(2025, 10, 1)
    for i in range(1, 35):
        wo_num = 200 + i
        date_val = start_date + timedelta(days=i * 8)
        eq_id, eq_name, issue_desc = equip_list[i % len(equip_list)]
        logs.append({
            "work_order_id": f"WO-{wo_num}",
            "equipment_id": eq_id,
            "equipment_name": eq_name,
            "date": date_val.strftime("%Y-%m-%d"),
            "technician": techs[i % len(techs)],
            "issue_reported": f"Routine check: {issue_desc}.",
            "action_taken": "Inspected, cleaned, lubricated, and verified operational state.",
            "downtime_hours": round((i * 1.3) % 4 + 0.5, 1),
            "status": "Completed"
        })

    # Sort logs by date
    logs.sort(key=lambda x: x["date"])
    
    with open(file_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(logs)
    print(f"Generated {len(logs)} rows in {file_path}")

def generate_safety_procedures(base_dir):
    procedures = {
        "Confined_Space_Entry.md": """# SOP-SAFETY-01: Confined Space Entry Procedure
**Document Version:** 4.2  
**Effective Date:** 2024-05-15  
**Governing Standard:** Factory Act Section 36 / OSHA 1910.146  

## 1. Scope
This procedure applies to all personnel entering vessels, boilers (including `BOILER-3`), storage tanks, and pump pits (including the pit for `PUMP-204`).

## 2. Hazard Identification
- Oxygen deficiency (< 19.5% O2)
- Flammable gas accumulation (e.g., Methane, H2S)
- Mechanical hazards (entrapment, rotating parts)

## 3. Mandatory Steps
1. **Isolate Space (LOTO):** Apply Lockout-Tagout to all electrical feeds and block valves (such as `VALVE-102`).
2. **Ventilation:** Purge space with fresh air blower for at least 30 minutes.
3. **Atmospheric Testing:** 
   - A qualified gas inspector must test the atmosphere using a calibrated gas detector, specifically `GAS-DET-11` or equivalent.
   - Entry is permitted ONLY if Oxygen is between 19.5% and 23.5%, LEL is < 5%, and toxic gases are below PEL.
4. **Permit Approval:** The safety supervisor must sign the Confined Space Entry Permit.
5. **Standby Attendant:** An attendant must remain outside the space at all times.

## 4. Emergency Action Plan
In case of alarm or collapse, the attendant must NOT enter. Trigger the emergency siren and deploy the rescue team with SCADA breathing gear.
""",
        "Hot_Work_Permit.md": """# SOP-SAFETY-02: Hot Work Permit Procedure
**Document Version:** 3.1  
**Effective Date:** 2024-08-01  
**Governing Standard:** OISD-GDN-137  

## 1. Scope
Applies to welding, cutting, grinding, or any operation generating heat/sparks within the process area.

## 2. Pre-Work Requirements
1. **Clear Area:** Remove all combustible materials within a 15-meter radius.
2. **Equipment Isolation:** If working near boilers (`BOILER-3`) or oil pumps (`PUMP-204`), ensure lines are blanked off.
3. **Gas Testing:** 
   - Perform continuous combustible gas monitoring using `GAS-DET-11`.
   - Work must immediately stop if gas levels exceed 1% LEL.
4. **Fire Watch:** Station a fire watch with a minimum of two 10kg CO2 fire extinguishers and a pressurized fire hose.
5. **Wet Down:** Wet the surrounding concrete floor and cover open sewers with fire-retardant blankets.

## 3. Permit Validity
Hot Work Permits are valid for a single shift only. If work is suspended for more than 30 minutes, gas testing must be re-conducted.
""",
        "Lockout_Tagout_LOTO.md": """# SOP-SAFETY-03: Lockout-Tagout (LOTO) Procedure
**Document Version:** 5.0  
**Effective Date:** 2025-01-10  
**Governing Standard:** OSHA 1910.147  

## 1. Purpose
To prevent accidental startup of equipment during maintenance or inspection activities.

## 2. Sequence of LOTO Application
1. **Notify Affected Personnel:** Inform operators that maintenance is starting on the equipment.
2. **Shut Down Equipment:** Perform normal stop sequence. E.g., for `PUMP-204`, shut down motor via localized controller. For `BOILER-3`, execute boiler control shutdown sequence.
3. **Isolate Energy Sources:**
   - Turn off electrical circuit breakers at MCC Room Panel B.
   - Close and lock inlet/outlet isolation valves (e.g., control valve `VALVE-102` and backup manual valves).
4. **Apply LOTO Devices:** Attach lockout clasps and personal padlock + safety tag to breaker switch and valve handles.
5. **Verify Isolation:** Attempt to restart the equipment locally to confirm energy is completely isolated. Ensure pressure gauges read zero before opening lines.
"""
    }
    
    for filename, content in procedures.items():
        file_path = os.path.join(base_dir, "sample_data", "safety_procedures", filename)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content.strip())
        print(f"Generated safety SOP: {file_path}")

def generate_incident_reports(base_dir):
    file_path = os.path.join(base_dir, "sample_data", "incident_reports.json")
    
    incidents = [
        {
            "report_id": "INC-2026-001",
            "date": "2026-02-15",
            "location": "Boiler House - B3 Area",
            "equipment_involved": "GAS-DET-11",
            "description": "During a routine entry check into BOILER-3's combustion chamber, the technician entered the space. A portable gas detector later alarmed, indicating 15% LEL Methane. The fixed area detector GAS-DET-11 failed to alarm or register gas buildup.",
            "root_cause": "Sensor drift and calibration failure. GAS-DET-11 was last calibrated 95 days prior, violating the 30-day SOP interval.",
            "severity": "High",
            "corrective_action": "Evacuated area. Recalibrated GAS-DET-11 immediately. Instituted an automated SCADA lock on Confined Space Permits if gas detector calibration logs are expired."
        },
        {
            "report_id": "INC-2026-002",
            "date": "2026-03-16",
            "location": "Pump House Pit",
            "equipment_involved": "PUMP-204",
            "description": "Mechanical seal ruptured on Crude Oil Transfer Pump PUMP-204, causing crude oil leakage of approximately 150 liters into the pump pit. Incident triggered localized gas alarms. Emergency containment was activated.",
            "root_cause": "High vibration caused by shaft misalignment led to seal rupture. Maintenance log indicates bearings were replaced on 2026-01-20 but shaft was not properly aligned under load conditions.",
            "severity": "High",
            "corrective_action": "Cleaned spill using absorbents. Replaced seals and bearings on PUMP-204 (see WO-144). Updated pump maintenance SOP to require mandatory laser alignment checks after any bearing replacement."
        },
        {
            "report_id": "INC-2026-003",
            "date": "2026-05-20",
            "location": "Chemical Storage Area B",
            "equipment_involved": "GAS-DET-11",
            "description": "Near-miss incident. Technician smelled solvent vapors near the storage rack. Checked GAS-DET-11 display which read 0.0 ppm methane/VOCs. Checked with hand-held sniffer which showed 800 ppm volatile organics.",
            "root_cause": "Catalytic sensor element on GAS-DET-11 was poisoned by trace silicone fumes from nearby painting. The sensor was unresponsive.",
            "severity": "Medium",
            "corrective_action": "Replaced catalytic bead sensor module on GAS-DET-11 (WO-159) and relocated detector 2 meters away from storage shelving. Enforced daily bump testing."
        },
        {
            "report_id": "INC-2026-006",
            "date": "2026-06-18",
            "location": "Pump House Pit",
            "equipment_involved": "GAS-DET-11",
            "description": "A technician preparing for entry into the Pump House pit for a scheduled inspection of PUMP-204 noticed that GAS-DET-11 displayed an error code 'ERR-DRIFT' and erratic atmospheric readings.",
            "root_cause": "Electrochemical cell drift and battery deterioration due to high temperature and moisture in the pump pit environment.",
            "severity": "Medium",
            "corrective_action": "Postponed pit entry. Conducted emergency calibration and battery replacement under WO-175."
        },
        {
            "report_id": "INC-2026-004",
            "date": "2026-06-25",
            "location": "Boiler House - B3 Area",
            "equipment_involved": "BOILER-3",
            "description": "Steam overpressure incident. Boiler steam pressure reached 18.5 bar (safety limit: 16 bar). The Pressure Relief Valve PRV-99 did not pop or relieve steam. Manual shutdown was initiated by the control room.",
            "root_cause": "The PRV-99 valve spindle was stuck due to calcium scaling deposits inside the valve seat, preventing mechanical release at 16 bar.",
            "severity": "High",
            "corrective_action": "Cooled down boiler, isolated valve, and replaced the valve cartridge (WO-177). Added weekly manual blowdown logs to prevent scale build-up."
        },
        {
            "report_id": "INC-2026-005",
            "date": "2026-04-10",
            "location": "Utility Yard",
            "equipment_involved": "VALVE-102",
            "description": "Near-miss: Valve VALVE-102 failed to actuate closed on automated signal from SCADA. Flow continued for 4 minutes before technician manually isolated the line using the handwheel.",
            "root_cause": "Actuator solenoid signal wire was corroded. Lack of grease on the valve stem caused mechanical binding.",
            "severity": "Medium",
            "corrective_action": "Rewired the solenoid connector, greased valve stem, and verified operation."
        },
        {
            "report_id": "INC-2026-007",
            "date": "2026-07-06",
            "location": "Pump House Pit",
            "equipment_involved": "PUMP-204",
            "description": "Complete mechanical lockup of PUMP-204. Technicians reported loud metallic grinding before motor tripped. Spill barrier caught minor oil leakage.",
            "root_cause": "Bearing seized completely due to lubrication starvation and prolonged bearing housing vibration (over 30mm/s). The lubrication line was blocked by metal shavings.",
            "severity": "High",
            "corrective_action": "Replaced entire rotating assembly, bearings, seals, and flushed lubrication lines. Implemented continuous vibration sensors for SCADA alarm integration."
        }
    ]
    
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(incidents, f, indent=4)
    print(f"Generated incident reports: {file_path}")

def generate_equipment_manuals(base_dir):
    manuals = {
        "PUMP-204_manual.md": """# OEM Technical Specification & Manual: PUMP-204
**Equipment Type:** Centrifugal Crude Oil Transfer Pump  
**Manufacturer:** FlowServe Industrial Corp.  
**Model:** FX-200-Centri  

## 1. Specifications
- **Flow Rate:** 350 m³/hr
- **Discharge Pressure:** 12.0 bar max
- **Motor Speed:** 2950 RPM (Direct Drive)
- **Bearing Type:** SKF Explorer Deep Groove Ball Bearings (Double Row)
- **Seal Type:** Dual Cartridge Mechanical Seal

## 2. Maintenance Intervals
- **Bearing Lubrication:** Every 30 days (Use Shell Gadus S2 V220 grease).
- **Shaft Alignment Check:** Every 90 days. Laser alignment must be within 0.05 mm tolerance.
- **Mechanical Seal Inspection:** Every 180 days. Check for oil traces in buffer fluid.

## 3. Critical Troubleshooting Table
| Symptom | Probable Cause | Action |
|---|---|---|
| **Vibration > 6.0 mm/s** | Shaft misalignment or bearing wear. | Check laser alignment. Realign coupling if mismatch exceeds 0.05 mm. |
| **High Bearing Temp (>80°C)** | Lubrication starvation or overloaded bearing. | Verify grease levels. If vibration persists, replace bearing assembly immediately. |
| **Buffer Fluid Pressure Drop** | Outer mechanical seal leak. | Shut down pump, inspect seal faces, and replace cartridge seal if damaged. |

> [!WARNING]
> Operating the pump under high vibration (>7.5 mm/s) for more than 48 hours will cause premature mechanical seal rupture and bearing seizure.
""",
        "BOILER-3_manual.md": """# OEM Operating Manual: BOILER-3 Steam Generator
**Equipment Type:** Water-Tube High-Pressure Boiler  
**Manufacturer:** Babcock & Wilcox Power Systems  
**Design Pressure:** 20.0 bar  

## 1. Technical Specs
- **Steam Output:** 15 Tons/hour
- **Operating Pressure:** 14.5 bar
- **Overpressure Protection:** Dual Pressure Relief Valves (Model: PRV-99) set to open at 16.0 bar.

## 2. Weekly Testing SOP
- **PRV Blowdown Test:** Perform weekly manual lift of PRV-99 lever to flush sediment and scaling out of the valve seat.
- **Feedwater Quality:** Maintain pH between 8.5 and 9.5. Total Dissolved Solids (TDS) must be < 1000 ppm. High TDS leads to scale deposits on heating elements and valve seats.

## 3. Maintenance Protocols
- **PRV-99 Inspection:** Disassemble and clean valve internal components every 12 months.
- **Tube Descaling:** Annual chemical wash is required to clean scale buildup.
""",
        "GAS-DET-11_manual.md": """# User Manual: GAS-DET-11 Combustible Gas Detector
**Sensor Technology:** Catalytic Bead Sensor & Electrochemical Cell  
**Target Gases:** Methane (CH4), Hydrogen Sulfide (H2S), Oxygen (O2)  

## 1. Safety Specifications
- **LEL Range:** 0 to 100% LEL Methane.
- **Alarm Setpoints:** Low Alarm at 10% LEL, High Alarm at 20% LEL.
- **Enclosure Class:** Class I, Div 1, Groups B, C, D (Explosion Proof).

## 2. Calibration Requirements
- **Interval:** Must be calibrated every 30 days.
- **Procedure:** Apply 50% LEL Methane gas bottle at 0.5 L/min flow rate. Run zero-point check and gain adjustment.
- **Sensor Drift:** Electochemical and catalytic bead sensors exhibit natural sensitivity loss of ~2% per month. Neglecting calibration will result in false safe readings.
- **Poisoning Agents:** Silicate compounds, silicones, and chlorinated solvents poison catalytic elements. If exposed, sensor element must be replaced.
"""
    }
    
    for filename, content in manuals.items():
        file_path = os.path.join(base_dir, "sample_data", "equipment_manuals", filename)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content.strip())
        print(f"Generated equipment manual: {file_path}")

def generate_inspection_reports(base_dir):
    file_path = os.path.join(base_dir, "sample_data", "inspection_reports.csv")
    headers = [
        "inspection_id", "equipment_id", "date", "inspector",
        "findings", "compliance_status", "next_inspection_due"
    ]
    
    inspections = [
        # PUMP-204 inspections
        {"inspection_id": "INSP-101", "equipment_id": "PUMP-204", "date": "2025-10-10", "inspector": "Gary Thomas", "findings": "Post-maintenance check. Vibration levels normal (2.1 mm/s). No seal leaks.", "compliance_status": "Compliant", "next_inspection_due": "2026-01-10"},
        {"inspection_id": "INSP-109", "equipment_id": "PUMP-204", "date": "2026-01-12", "inspector": "Gary Thomas", "findings": "Scheduled quarterly check. Slight vibration detected (4.8 mm/s). Recommended for checking alignment during next maintenance opportunity.", "compliance_status": "Compliant", "next_inspection_due": "2026-04-12"},
        {"inspection_id": "INSP-118", "equipment_id": "PUMP-204", "date": "2026-04-15", "inspector": "Gary Thomas", "findings": "Post-leak repair inspection. Replaced seals verified tight. Vibration measured at 1.8 mm/s. Laser alignment logged.", "compliance_status": "Compliant", "next_inspection_due": "2026-07-15"},
        {"inspection_id": "INSP-129", "equipment_id": "PUMP-204", "date": "2026-07-07", "inspector": "Gary Thomas", "findings": "Post-seizure rebuild audit. Vibration analysis normal. Temperature logs aligned. Automatic monitoring sensors checked.", "compliance_status": "Compliant", "next_inspection_due": "2026-10-07"},
        
        # BOILER-3 inspections
        {"inspection_id": "INSP-103", "equipment_id": "BOILER-3", "date": "2025-10-20", "inspector": "Gary Thomas", "findings": "Boiler inspected. PRV-99 freed and scales removed. Internal steam drum shows slight carbonate scaling. TDS control required.", "compliance_status": "Compliant", "next_inspection_due": "2026-04-20"},
        {"inspection_id": "INSP-120", "equipment_id": "BOILER-3", "date": "2026-04-10", "inspector": "Alice Carter", "findings": "Boiler casing inspection. PRV testing logs are incomplete. Recommendation to establish digital blowdown logs.", "compliance_status": "Non-Compliant", "next_inspection_due": "2026-07-10"},
        {"inspection_id": "INSP-127", "equipment_id": "BOILER-3", "date": "2026-06-27", "inspector": "Gary Thomas", "findings": "Audit following overpressure incident. PRV-99 replaced cartridge tested. Discharge pipe cleared of scale. Re-rated for 20 bar service.", "compliance_status": "Compliant", "next_inspection_due": "2026-12-27"},

        # GAS-DET-11 inspections
        {"inspection_id": "INSP-105", "equipment_id": "GAS-DET-11", "date": "2025-11-05", "inspector": "Alice Carter", "findings": "Gas sensor calibrated. Response time is within specs. Battery levels healthy.", "compliance_status": "Compliant", "next_inspection_due": "2025-12-05"},
        {"inspection_id": "INSP-111", "equipment_id": "GAS-DET-11", "date": "2025-12-10", "inspector": "Alice Carter", "findings": "Methane detector test. Calibration was due on 2025-12-05 but missed by 5 days. Calibrated today.", "compliance_status": "Non-Compliant", "next_inspection_due": "2026-01-10"},
        {"inspection_id": "INSP-115", "equipment_id": "GAS-DET-11", "date": "2026-01-15", "inspector": "Alice Carter", "findings": "Detector calibration verified. No drift detected.", "compliance_status": "Compliant", "next_inspection_due": "2026-02-15"},
        {"inspection_id": "INSP-119", "equipment_id": "GAS-DET-11", "date": "2026-03-20", "inspector": "Gary Thomas", "findings": "Audit following INC-2026-001 (Boiler methane leak). Detector found to have missed its February 15 calibration check. Recalibration logs missing.", "compliance_status": "Non-Compliant", "next_inspection_due": "2026-04-20"},
        {"inspection_id": "INSP-122", "equipment_id": "GAS-DET-11", "date": "2026-05-22", "inspector": "Alice Carter", "findings": "Sensor inspection after near-miss INC-2026-003. Old poisoned sensor module discarded. Replacement module calibrated. Daily test schedule setup.", "compliance_status": "Compliant", "next_inspection_due": "2026-06-22"}
    ]
    
    # Fill with some random equipment checks
    equip_list = ["VALVE-102", "COMPRESSOR-5", "TURBINE-01", "HEATER-402"]
    start_date = datetime(2025, 10, 1)
    for i in range(1, 15):
        insp_num = 200 + i
        date_val = start_date + timedelta(days=i * 20)
        eq_id = equip_list[i % len(equip_list)]
        inspections.append({
            "inspection_id": f"INSP-{insp_num}",
            "equipment_id": eq_id,
            "date": date_val.strftime("%Y-%m-%d"),
            "inspector": "Alice Carter" if i % 2 == 0 else "Gary Thomas",
            "findings": f"Routine structural and functional check for {eq_id}. Found in satisfactory working condition.",
            "compliance_status": "Compliant",
            "next_inspection_due": (date_val + timedelta(days=90)).strftime("%Y-%m-%d")
        })

    # Sort inspections by date
    inspections.sort(key=lambda x: x["date"])
    
    with open(file_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(inspections)
    print(f"Generated {len(inspections)} rows in {file_path}")

if __name__ == "__main__":
    # Base directory is the current directory where the script is executed
    base = os.path.dirname(os.path.abspath(__file__))
    create_directory_structure(base)
    generate_maintenance_logs(base)
    generate_safety_procedures(base)
    generate_incident_reports(base)
    generate_equipment_manuals(base)
    generate_inspection_reports(base)
    print("Sample data generation complete!")
