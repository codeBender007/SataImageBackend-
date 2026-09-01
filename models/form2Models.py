from datetime import datetime
from database.db import Base
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, Float
from sqlalchemy.orm import relationship


# 1. Master Form 2 Table: First Operation Part (FOP) & Shift Handover Header
class Form2HandoverLog(Base):
    __tablename__ = "form2_handover_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    form_code = Column(String(100), unique=True, index=True, nullable=False)
    page_type = Column(String(50), default="Page B")
    form_title = Column(String(150), default="First Operation Part (FOP) Record & Shift Handover")
    
    # Metadata
    log_date = Column(String(50), index=True, nullable=False)
    shift = Column(String(20), index=True, nullable=False)
    machine_no = Column(String(50), index=True, nullable=True)
    qa_cell = Column(String(50), nullable=True)
    operation_no = Column(String(50), nullable=True)
    
    employee_id = Column(String(50), index=True, nullable=True)
    employee_name = Column(String(100), nullable=True)
    supervisor_name = Column(String(100), nullable=True)
    shift_incharge = Column(String(100), nullable=True)
    module_incharge = Column(String(100), nullable=True)
    
    status = Column(String(50), default="submitted", index=True)  # draft, pending_verification, submitted, approved
    original_image_path = Column(String(255), nullable=True)
    
    # Aggregated Summary Totals
    total_fop_parts = Column(Integer, default=0)
    total_fop_rejections = Column(Integer, default=0)
    total_rework_generated = Column(Integer, default=0)
    total_rework_cleared = Column(Integer, default=0)
    
    # Section 2: Shift Handover & 5-Why Problem Analysis
    problem_analysis = Column(Text, nullable=True)
    why_1 = Column(Text, nullable=True)
    why_2 = Column(Text, nullable=True)
    why_3 = Column(Text, nullable=True)
    why_4 = Column(Text, nullable=True)
    why_5 = Column(Text, nullable=True)
    root_cause = Column(Text, nullable=True)
    action_1 = Column(Text, nullable=True)
    action_2 = Column(Text, nullable=True)
    
    # Handover Checklist & Quantitative Status
    handover_check = Column(String(100), nullable=True)
    rm_online_qty = Column(String(100), nullable=True)
    running_cavity = Column(String(100), nullable=True)
    all_gauges_online = Column(String(20), default="Y")
    missing_gauges = Column(String(150), nullable=True)
    pdi_report_pv_no = Column(String(100), nullable=True)
    tool_in_line_no = Column(String(100), nullable=True)
    
    # Section 3: Shift Remarks & Communications
    shift_communication = Column(Text, nullable=True)
    material_tool_communication = Column(Text, nullable=True)
    prepared_by_emp_no = Column(String(50), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    tool_records = relationship(
        "Form2ToolRecord",
        back_populates="form2_log",
        cascade="all, delete-orphan",
        order_by="Form2ToolRecord.row_index"
    )
    pdi_records = relationship(
        "Form2PDIInspectionRecord",
        back_populates="form2_log",
        cascade="all, delete-orphan",
        order_by="Form2PDIInspectionRecord.row_index"
    )


# 2. Child Table: Itemized Tabular Tool & FOP Setting Records (Up to 16 Rows)
class Form2ToolRecord(Base):
    __tablename__ = "form2_tool_records"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    form2_id = Column(Integer, ForeignKey("form2_handover_logs.id", ondelete="CASCADE"), nullable=False, index=True)
    row_index = Column(Integer, nullable=False, default=0)
    
    tool_description = Column(String(150), nullable=True)
    operation_no = Column(String(50), nullable=True)
    machine_no = Column(String(50), nullable=True)
    tool_no = Column(String(50), nullable=True)
    time_stamp = Column(String(50), nullable=True)
    reason_for_fop = Column(String(150), nullable=True)
    fop_parts = Column(Integer, default=0)
    fop_rejection = Column(Integer, default=0)
    tool_set_by = Column(String(100), nullable=True)
    handover_check = Column(String(100), nullable=True)
    defect = Column(String(150), nullable=True)
    remarks = Column(Text, nullable=True)
    material_or_tool = Column(String(150), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)

    form2_log = relationship("Form2HandoverLog", back_populates="tool_records")


# 3. Child Table: PDI Inspection, Rework & Defect Matrix Records
class Form2PDIInspectionRecord(Base):
    __tablename__ = "form2_pdi_inspection_records"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    form2_id = Column(Integer, ForeignKey("form2_handover_logs.id", ondelete="CASCADE"), nullable=False, index=True)
    row_index = Column(Integer, nullable=False, default=0)
    
    row_label = Column(String(150), nullable=False)
    operation_no = Column(String(50), nullable=True)
    machining_rejection = Column(Integer, default=0)
    casting_rejection = Column(Integer, default=0)
    supplier_info = Column(String(150), nullable=True)
    die_cavity_no = Column(String(100), nullable=True)
    abnormality_alarm = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)

    form2_log = relationship("Form2HandoverLog", back_populates="pdi_records")
