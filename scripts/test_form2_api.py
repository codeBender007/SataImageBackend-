import sys
import os
import io

if sys.platform.startswith("win"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def run_tests():
    print("==========================================================")
    print("[TEST] Running Automated API Tests for Normalized Form 2 (Form B) Endpoints...")
    print("==========================================================")

    # Test 0: Login endpoint (POST /api/login)
    res_login = client.post("/api/login", json={"username": "admin", "password": "admin123"})
    assert res_login.status_code == 200, f"Login failed: {res_login.text}"
    login_json = res_login.json()
    assert "access_token" in login_json, "access_token missing in login response"
    print(f"[PASS] POST /api/login -> Logged in as: {login_json['username']} ({login_json['role']}), Token length: {len(login_json['access_token'])}")

    # Test 1: List Form 2 records via GET /api/form-b/list
    res_list = client.get("/api/form-b/list")
    assert res_list.status_code == 200, f"List failed: {res_list.text}"
    list_json = res_list.json()
    print(f"[PASS] GET /api/form-b/list -> Total Records: {list_json['pagination']['totalCount']}")


    # Test 2: Get Form 2 by ID via GET /api/form-b/1
    res_get = client.get("/api/form-b/1")
    assert res_get.status_code == 200, f"Get by ID failed: {res_get.text}"
    get_json = res_get.json()
    print(f"[PASS] GET /api/form-b/1 -> Code: {get_json['data']['formCode']}, Tool Records: {len(get_json['data']['records'])}")

    # Test 3: OCR Extraction via POST /api/form-b/extract
    fake_img = io.BytesIO(b"fake image bytes for testing")
    res_extract = client.post(
        "/api/form-b/extract",
        files={"file": ("test_form.jpg", fake_img, "image/jpeg")}
    )
    assert res_extract.status_code == 200, f"Extract failed: {res_extract.text}"
    extract_json = res_extract.json()
    print(f"[PASS] POST /api/form-b/extract -> Status: {extract_json['status']}, Confidence: {extract_json.get('extractionConfidence')}")

    # Test 4: Submit / Save Form 2 via POST /api/form-b/save
    submit_payload = {
        "header": {
            "page_type": "Page B",
            "form_title": "First Operation Part (FOP) Record & Shift Handover",
            "log_date": "2026-08-08",
            "shift": "B",
            "machine_no": "MC-305",
            "qa_cell": "Cell B",
            "operation_no": "20",
            "employee_id": "EMP003",
            "employee_name": "Vikram Singh",
            "supervisor_name": "Mahesh Gupta",
            "shift_incharge": "Pradeep Chauhan",
            "status": "submitted"
        },
        "records": [
            {
                "rowIndex": 0,
                "toolDescription": "Facing Tool Ø100",
                "operationNo": "20",
                "machineNo": "MC-305",
                "toolNo": "TL-301",
                "time": "14:15",
                "reasonForFOP": "Insert Chipped",
                "fopParts": 8,
                "fopRejection": 0,
                "toolSetBy": "Vikram Singh",
                "handoverCheck": "OK",
                "defect": "None",
                "remarks": "Tool OK",
                "materialOrTool": "Grade CNMG"
            }
        ],
        "details": {
            "problemAnalysis": "Facing tool edge chipped during first cycle",
            "rootCause": "Feed rate was high on casting crust",
            "action": "Reduced entry feed by 15% and rotated insert",
            "action1": "Reduced entry feed by 15% and rotated insert",
            "shiftCommunication": "Shift B running without interruption.",
            "supervisor": "Mahesh Gupta"
        },
        "pdiInspection": [
            {
                "rowIndex": 0,
                "rowLabel": "Part 1",
                "operationNo": "20",
                "machiningRejection": 0,
                "castingRejection": 0,
                "supplierInfo": "Sata Plant 2",
                "dieCavityNo": "Cavity #01",
                "abnormalityAlarm": "None"
            }
        ]
    }

    res_submit = client.post("/api/form-b/save", json=submit_payload)
    assert res_submit.status_code == 201, f"Submit failed: {res_submit.text}"
    submit_json = res_submit.json()
    new_id = submit_json["formId"]
    print(f"[PASS] POST /api/form-b/save -> Created ID: {new_id}, Code: {submit_json['formCode']}")

    # Test 5: Verify list count increased
    res_list2 = client.get("/api/form-b/list")
    assert res_list2.json()["pagination"]["totalCount"] >= 2
    print(f"[PASS] Total records in DB after submission: {res_list2.json()['pagination']['totalCount']}")

    print("==========================================================")
    print("[ALL TESTS PASSED] Normalized Form 2 (Form B) Endpoints Verified!")
    print("==========================================================")

if __name__ == "__main__":
    run_tests()
