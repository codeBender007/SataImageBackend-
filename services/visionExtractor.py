import json
import os
import re
from typing import List, Optional
from dotenv import load_dotenv
from fastapi import HTTPException
from google import genai
from google.genai import types
from pydantic import BaseModel

load_dotenv()

# --- 1. Schemas ---
class ProductionGridItem(BaseModel):
    hour_slot: str
    uph: Optional[int] = None
    actual_production: Optional[int] = None
    casting_rejection: Optional[int] = None
    machining_rejection: Optional[int] = None
    unprocessed_rejection: Optional[int] = None

class TPMLossItem(BaseModel):
    loss_category: str
    loss_reason: str
    hour_slot: str
    duration_minutes: int

class FormHeaderData(BaseModel):
    log_date: Optional[str] = None
    shift: Optional[str] = None
    qa_cell: Optional[str] = None
    part: Optional[str] = None
    page_no: Optional[str] = None
    operation_number: Optional[str] = None
    machine_no: Optional[str] = None
    employee_number: Optional[str] = None
    supervisor_name: Optional[str] = None
    shift_incharge_name: Optional[str] = None
    pdi_ok_part1: Optional[str] = None
    pdi_ok_part2: Optional[str] = None
    total_loss_minutes: Optional[int] = None
    entry_person_name: Optional[str] = None
    abnormality_parts: Optional[str] = None
    other_abnormality: Optional[str] = None

class ExtractedFormSchema(BaseModel):
    header: FormHeaderData
    production_grid: List[ProductionGridItem]
    loss_entries: List[TPMLossItem]


# --- 2. Initialize Client ---
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_KEY:
    raise ValueError("GEMINI_API_KEY environment variable is not set in .env")

client = genai.Client(api_key=GEMINI_KEY)


def run_vision_extractor(imageBytes: bytes, mimeType: str = "image/jpeg") -> dict:
    json_schema_str = json.dumps(ExtractedFormSchema.model_json_schema(), indent=2)

    prompt = f"""
    You are an expert industrial document OCR & table parsing system.
    Analyze the provided 'Hourly Production Monitoring Book' handwritten form.
    
    1. Extract Header metadata (Date, Shift, QA Cell, Part, Machine Nos, Employee IDs, Supervisor, etc.).
    2. Extract Hourly Production Grid (H1 to H13 rows with UPH, Actual Production, Casting/Machining/Unprocessed Rejections).
    3. Extract TPM 16 Loss Entry items with non-zero minute values (Breakdown, Setup, Waiting, etc., along with hour slot and minutes).
    4. Return ONLY a valid JSON object matching strictly this schema:
    {json_schema_str}
    """

    try:
        # Updated to gemini-3.6-flash
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=[
                prompt,
                types.Part.from_bytes(data=imageBytes, mime_type=mimeType)
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.1,
            )
        )

        raw_text = response.text.strip()

        if "```" in raw_text:
            match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw_text)
            if match:
                raw_text = match.group(1)

        return json.loads(raw_text)

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Gemini Extraction Error: {str(e)}"
        )