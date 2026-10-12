"""
FastAPI application for the IP-addressing grader.

Endpoints
  POST /api/login              {username, password} -> {token}  (public)
  POST /api/logout             (auth) revoke token
  GET  /                      health (public)
  GET  /api/cases             (auth) list cases
  GET  /api/cases/{id}        (auth) full case
  POST /api/cases             (auth) create case
  PUT  /api/cases/{id}        (auth) update case
  DELETE /api/cases/{id}      (auth) delete case
  POST /api/parse-pkt         (auth) upload .pkt -> StudentJSON
  POST /api/solve             (auth) {case, npm} -> expected answer key
  POST /api/grade             (auth) multipart {case(json), npm, file(.pkt)} -> GradeReport
  POST /api/grade-json        (auth) {case, npm, student} -> GradeReport (testing)
"""
from __future__ import annotations

import shutil
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

import ptdecoder

from app.adapter import adapt
from app.auth import login as auth_login, logout as auth_logout, require_auth
from app.cases_store import (
    _seed_if_empty,
    delete_case,
    get_case,
    init_db,
    list_cases,
    save_case,
)
from app.engine.solver import solve_case
from app.grader.score import grade
from app.master_store import (
    create_device_type,
    delete_device_type,
    list_device_types,
    update_device_type,
)
from app.schemas import (
    CaseSchema,
    DeviceType,
    GradeJsonRequest,
    GradeReport,
    SolveRequest,
    SolveResult,
    StudentJSON,
)

app = FastAPI(title="IP Addressing Grader", version="0.3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _init_and_seed() -> None:
    init_db()
    _seed_if_empty()
    from app.master_store import init_db as master_init, _seed as master_seed

    master_init()
    master_seed()


@app.get("/")
def root():
    return {"service": "ip-addressing-grader", "status": "ok"}


@app.post("/api/login")
def login(creds: dict):
    token = auth_login(creds.get("username", ""), creds.get("password", ""))
    if not token:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"token": token}


@app.post("/api/logout")
def logout(token: str = Depends(require_auth)):
    auth_logout(token)
    return {"ok": True}


# --------------------------------------------------------------------------- #
# Cases
# --------------------------------------------------------------------------- #
@app.get("/api/cases")
def get_cases(_: str = Depends(require_auth)):
    return list_cases()


@app.get("/api/cases/{case_id}")
def get_case_by_id(case_id: str, _: str = Depends(require_auth)):
    case = get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case


@app.post("/api/cases", status_code=201)
def create_case(case: CaseSchema, _: str = Depends(require_auth)):
    return save_case(case)


@app.put("/api/cases/{case_id}")
def update_case(case_id: str, case: CaseSchema, _: str = Depends(require_auth)):
    if case.case_id != case_id:
        raise HTTPException(status_code=400, detail="case_id mismatch")
    if not get_case(case_id):
        raise HTTPException(status_code=404, detail="Case not found")
    return save_case(case)


@app.delete("/api/cases/{case_id}")
def delete_case_by_id(case_id: str, _: str = Depends(require_auth)):
    if not delete_case(case_id):
        raise HTTPException(status_code=404, detail="Case not found")
    return {"ok": True}


# --------------------------------------------------------------------------- #
# Master data: device types (TA-editable)
# --------------------------------------------------------------------------- #
@app.get("/api/master/device-types", response_model=list[DeviceType])
def get_device_types(_: str = Depends(require_auth)):
    return list_device_types()


@app.post("/api/master/device-types", response_model=DeviceType, status_code=201)
def create_device_type_endpoint(d: DeviceType, _: str = Depends(require_auth)):
    try:
        return create_device_type(d)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@app.put("/api/master/device-types/{code}", response_model=DeviceType)
def update_device_type_endpoint(code: str, d: DeviceType, _: str = Depends(require_auth)):
    try:
        return update_device_type(code, d)
    except KeyError:
        raise HTTPException(status_code=404, detail="Device type not found")


@app.delete("/api/master/device-types/{code}")
def delete_device_type_endpoint(code: str, _: str = Depends(require_auth)):
    try:
        delete_device_type(code)
    except KeyError:
        raise HTTPException(status_code=404, detail="Device type not found")
    return {"ok": True}


# --------------------------------------------------------------------------- #
# Decode / solve / grade
# --------------------------------------------------------------------------- #
@app.post("/api/parse-pkt", response_model=StudentJSON)
def parse_pkt(file: UploadFile = File(...), _: str = Depends(require_auth)):
    if not file.filename or not file.filename.lower().endswith((".pkt", ".pka", ".xml")):
        raise HTTPException(status_code=400, detail="Upload a .pkt / .pka / .xml file")
    data = file.file.read()
    try:
        doc = ptdecoder.parse_pkt(data, file_name=file.filename)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=422, detail=f"Failed to decode pkt: {exc}") from exc
    return adapt(doc.to_dict())


@app.post("/api/solve", response_model=SolveResult)
def solve(req: SolveRequest, _: str = Depends(require_auth)):
    return solve_case(req.case, req.npm)


@app.post("/api/grade", response_model=GradeReport)
def grade_submission(
    case: str = Form(...),
    npm: str = Form(...),
    file: UploadFile = File(...),
    _: str = Depends(require_auth),
):
    try:
        case_obj = CaseSchema.model_validate_json(case)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Invalid case JSON: {exc}") from exc

    data = file.file.read()
    try:
        doc = ptdecoder.parse_pkt(data, file_name=file.filename)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=422, detail=f"Failed to decode pkt: {exc}") from exc

    student = adapt(doc.to_dict())
    solve = solve_case(case_obj, npm)
    return grade(case_obj, student, solve)


@app.post("/api/grade-json", response_model=GradeReport)
def grade_json(req: GradeJsonRequest, _: str = Depends(require_auth)):
    solve = solve_case(req.case, req.npm)
    return grade(req.case, req.student, solve)
