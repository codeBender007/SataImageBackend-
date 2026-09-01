import sys
import os

# Set standard streams to utf-8 if possible
if sys.platform.startswith("win"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Add Backend root directory to sys.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from database.db import engine, Base, sessionLocal
from models.form2Models import Form2HandoverLog, Form2ToolRecord, Form2PDIInspectionRecord
from sqlalchemy import text


def init_form2_database():
    print("==========================================================")
    print("[INIT] Initializing SATA Vikas Form 2 (Page B - FOP) Database...")
    print("==========================================================")

    # 1. Enable SQLite Foreign Keys & WAL mode
    with engine.connect() as conn:
        conn.execute(text("PRAGMA foreign_keys = ON;"))
        conn.execute(text("PRAGMA journal_mode = WAL;"))
        conn.commit()

    # 2. Create all tables defined in Base (including Form 2 models)
    print("[INFO] Creating Form 2 tables in SQLite database...")
    Base.metadata.create_all(bind=engine)
    print("[SUCCESS] Tables created: form2_handover_logs, form2_tool_records, form2_pdi_inspection_records")

    db = sessionLocal()
    try:
        # 3. Check if seed data exists
        existing_count = db.query(Form2HandoverLog).count()
        if existing_count == 0:
            print("[INFO] Seeding demonstration Form 2 record...")
            
            seed_log = Form2HandoverLog(
                form_code="FOP-2026-0001",
                page_type="Page B",
                form_title="First Operation Part (FOP) Record & Shift Handover",
                log_date="2026-08-07",
                shift="A",
                machine_no="MC-201",
                qa_cell="Cell A",
                operation_no="10",
                employee_id="EMP002",
                employee_name="Suresh Yadav",
                supervisor_name="Mahesh Gupta",
                shift_incharge="Rakesh Verma",
                module_incharge="Mahesh Gupta",
                status="submitted",
                total_fop_parts=45,
                total_fop_rejections=2,
                total_rework_generated=3,
                total_rework_cleared=3,
                
                # 5-Why Analysis
                problem_analysis="Tool insert wear causing dimensional variance in bore diameter Ø45.2",
                why_1="Excessive vibration on spindle at high feed rate",
                why_2="Hardness of casting batch was at upper tolerance limit (220 BHN)",
                why_3="Cutting speed was high without coolant nozzle repositioning",
                why_4="Coolant pressure dropped below 15 bar",
                why_5="Coolant filter clogged with fine aluminum chips",
                root_cause="Coolant filter clogging caused thermal degradation of carbide insert coating",
                action_1="Replaced coolant mesh filter and cleaned reservoir",
                action_2="Installed new Sandvik WNMG insert and reset tool offset +0.02mm",
                
                # Checklist & Status
                handover_check="All 4 tools calibrated and zero-offset verified with master gauge",
                rm_online_qty="150 pcs",
                running_cavity="Cavity #2",
                all_gauges_online="Y",
                missing_gauges="None",
                pdi_report_pv_no="PV-2026-0891",
                tool_in_line_no="TL-LINE-04",
                shift_communication="Shift A handover to Shift B completed smoothly. Machine running on spec.",
                material_tool_communication="New insert batch staged in tool cabinet.",
                prepared_by_emp_no="EMP002"
            )
            db.add(seed_log)
            db.flush()

            # Seed 4 tool rows
            seed_tools = [
                Form2ToolRecord(
                    form2_id=seed_log.id,
                    row_index=0,
                    tool_description="Rough Boring Bar Ø45",
                    operation_no="10",
                    machine_no="MC-201",
                    tool_no="TL-101",
                    time_stamp="08:30",
                    reason_for_fop="Insert Replacement",
                    fop_parts=10,
                    fop_rejection=1,
                    tool_set_by="Ramesh Kumar",
                    handover_check="OK",
                    defect="None",
                    remarks="Normal wear",
                    material_or_tool="Grade WNMG080408"
                ),
                Form2ToolRecord(
                    form2_id=seed_log.id,
                    row_index=1,
                    tool_description="Finish Boring Bar Ø45.2",
                    operation_no="10",
                    machine_no="MC-201",
                    tool_no="TL-102",
                    time_stamp="09:15",
                    reason_for_fop="New Setup",
                    fop_parts=15,
                    fop_rejection=0,
                    tool_set_by="Ramesh Kumar",
                    handover_check="OK",
                    defect="None",
                    remarks="Dimensions OK",
                    material_or_tool="Bore Gauge 45.20"
                ),
                Form2ToolRecord(
                    form2_id=seed_log.id,
                    row_index=2,
                    tool_description="Chamfer Tool 45°",
                    operation_no="20",
                    machine_no="MC-201",
                    tool_no="TL-204",
                    time_stamp="11:00",
                    reason_for_fop="Edge Chipping",
                    fop_parts=12,
                    fop_rejection=1,
                    tool_set_by="Dinesh Shah",
                    handover_check="OK",
                    defect="Minor Burr",
                    remarks="Burr cleared",
                    material_or_tool="Tool changed"
                ),
                Form2ToolRecord(
                    form2_id=seed_log.id,
                    row_index=3,
                    tool_description="Facing Cutter Ø80",
                    operation_no="10",
                    machine_no="MC-201",
                    tool_no="TL-105",
                    time_stamp="13:45",
                    reason_for_fop="Routine Check",
                    fop_parts=8,
                    fop_rejection=0,
                    tool_set_by="Ramesh Kumar",
                    handover_check="OK",
                    defect="None",
                    remarks="Surface finish Ra 1.6",
                    material_or_tool="Tool OK"
                )
            ]
            db.add_all(seed_tools)

            # Seed PDI Matrix rows
            pdi_labels = [
                "Part 1", "Part 2", "Rework generation - Part 1", "Rework generation - Part 2",
                "Rework cleared in shift - Part 1", "Rework cleared in shift - Part 2",
                "Rework approval No : XYZ", "Tool No. XYZ", "Tool No. ABCD", "Total"
            ]
            op_nos = ["10", "20", "30", "40", "50", "60", "70", "80", "90", "Total"]

            pdi_records = [
                Form2PDIInspectionRecord(
                    form2_id=seed_log.id,
                    row_index=idx,
                    row_label=label,
                    operation_no=op_nos[idx] if idx < len(op_nos) else "",
                    machining_rejection=2 if idx == 0 else 0,
                    casting_rejection=1 if idx == 0 else 0,
                    supplier_info="Sata Supplier Plant-1",
                    die_cavity_no="Cavity #02",
                    abnormality_alarm="High vibration" if idx == 2 else "None"
                )
                for idx, label in enumerate(pdi_labels)
            ]
            db.add_all(pdi_records)

            db.commit()
            print(f"[SUCCESS] Demonstration Record Created with ID: {seed_log.id} (Code: {seed_log.form_code})")
        else:
            print(f"[INFO] Form 2 table already contains {existing_count} record(s). Schema verified.")

        print("==========================================================")
        print("[COMPLETE] Form 2 SQLite Database Initialization Completed!")
        print("==========================================================")

    except Exception as e:
        db.rollback()
        print(f"[ERROR] Initialization Error: {e}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    init_form2_database()
