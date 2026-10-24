import os
import shutil
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from uuid import uuid4

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from .models import AuditEvent, CATask, Document, Filing, ReconciliationException

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "./uploads"))

@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    db = next(get_db())
    try:
        if not db.scalar(select(ReconciliationException.id).limit(1)):
            db.add_all([
                ReconciliationException(id="ex-1", name="NEFT / Riya Traders", source="HDFC statement", amount="₹74,000", action="Link sales invoice or mark as advance"),
                ReconciliationException(id="ex-2", name="INV-237 · Apex Dyes", source="Purchase register", amount="₹32,400 ITC", action="Ask supplier to upload invoice"),
                ReconciliationException(id="ex-3", name="UPI / Office expense", source="HDFC statement", amount="₹8,750", action="Upload bill and select category"),
                Filing(id="filing-1", type="GSTR-3B", period="Oct 2026", prepared_by="Rao & Co.", evidence="1 mismatch"),
                Filing(id="filing-2", type="GSTR-1", period="Oct 2026", prepared_by="Rao & Co.", evidence="Matched", status="filed", owner_approved=True),
                Filing(id="filing-3", type="TDS return", period="Q2 FY27", prepared_by="Not started", evidence="—", status="not_started"),
            ]); db.commit()
    finally: db.close()
    yield

app = FastAPI(title="ClearBooks MVP API", version="0.2.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

class ExceptionUpdate(BaseModel): status: Literal["open", "resolved", "escalated"]
class TaskCreate(BaseModel): title: str; assignee: str = "Rao & Co."
class TaskUpdate(BaseModel): status: Literal["open", "done"]

def as_dict(item): return {column.name: getattr(item, column.name) for column in item.__table__.columns}
def audit(db: Session, action: str, entity_id: str): db.add(AuditEvent(id=str(uuid4()), action=action, entity_id=entity_id, actor="Arnav, Director", at=datetime.now(timezone.utc)))

@app.get("/api/health")
def health(): return {"status": "ok"}

@app.get("/api/dashboard")
def dashboard(db: Session = Depends(get_db)):
    open_count = len(db.scalars(select(ReconciliationException).where(ReconciliationException.status == "open")).all())
    done = len(db.scalars(select(Filing).where(Filing.status.in_(["filed", "approved"]))).all())
    return {"company":"Aarav Textiles Pvt Ltd","financial_year":"FY 2026–27","metrics":[{"label":"Bank reconciliation","value":"96%","detail":"↑ 8% this month","tone":"good"},{"label":"Unmatched transactions","value":str(open_count),"detail":"₹1.48L needs review","tone":"warning"},{"label":"Input tax at risk","value":"₹68K","detail":"4 supplier invoices missing","tone":"warning"},{"label":"October filings","value":f"{done} / 3","detail":"One filed, two ready","tone":"good"}],"actions":[{"title":"Approve GSTR-3B draft","detail":"Prepared by Rao & Co. · Due in 3 days","status":"Review","tone":"warning"},{"title":"Match purchase invoices","detail":"Reconciliation exceptions still open","status":"Risk","tone":"danger"},{"title":"GSTR-1 acknowledgement received","detail":"ARN: AA070… · Filed 9 Oct","status":"Filed","tone":"good"}],"health":[{"label":"Bank ↔ books","value":96,"tone":"good"},{"label":"Sales ↔ GSTR-1","value":100,"tone":"primary"},{"label":"Purchases ↔ GSTR-2B","value":88,"tone":"warning"}]}

@app.get("/api/exceptions")
def list_exceptions(db: Session = Depends(get_db)): return [as_dict(x) for x in db.scalars(select(ReconciliationException)).all()]

@app.patch("/api/exceptions/{exception_id}")
def update_exception(exception_id: str, payload: ExceptionUpdate, db: Session = Depends(get_db)):
    item = db.get(ReconciliationException, exception_id)
    if not item: raise HTTPException(404, "Exception not found")
    item.status = payload.status; audit(db, f"Exception marked {payload.status}", exception_id); db.commit(); return as_dict(item)

@app.get("/api/filings")
def list_filings(db: Session = Depends(get_db)): return [as_dict(x) for x in db.scalars(select(Filing)).all()]

@app.post("/api/filings/{filing_id}/approve")
def approve_filing(filing_id: str, db: Session = Depends(get_db)):
    item = db.get(Filing, filing_id)
    if not item: raise HTTPException(404, "Filing not found")
    if item.status != "draft": raise HTTPException(409, "Only a draft can be approved")
    item.owner_approved, item.status = True, "approved"; audit(db, "Owner approved filing draft", filing_id); db.commit(); return as_dict(item)

@app.get("/api/documents")
def list_documents(db: Session = Depends(get_db)): return [as_dict(x) for x in db.scalars(select(Document).order_by(Document.uploaded_at.desc())).all()]

@app.post("/api/documents", status_code=201)
def upload_document(category: str = Form(...), file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename: raise HTTPException(400, "Choose a file")
    item_id = str(uuid4()); destination = UPLOAD_DIR / f"{item_id}{Path(file.filename).suffix}"
    with destination.open("wb") as buffer: shutil.copyfileobj(file.file, buffer)
    item = Document(id=item_id, name=file.filename, category=category, storage_path=str(destination)); db.add(item); audit(db, "Document uploaded", item_id); db.commit(); return as_dict(item)

@app.get("/api/ca-tasks")
def list_ca_tasks(db: Session = Depends(get_db)): return [as_dict(x) for x in db.scalars(select(CATask).order_by(CATask.created_at.desc())).all()]

@app.post("/api/ca-tasks", status_code=201)
def create_ca_task(payload: TaskCreate, db: Session = Depends(get_db)):
    if not payload.title.strip(): raise HTTPException(400, "Task title is required")
    item = CATask(id=str(uuid4()), title=payload.title.strip(), assignee=payload.assignee); db.add(item); audit(db, "CA task created", item.id); db.commit(); return as_dict(item)

@app.patch("/api/ca-tasks/{task_id}")
def update_ca_task(task_id: str, payload: TaskUpdate, db: Session = Depends(get_db)):
    item = db.get(CATask, task_id)
    if not item: raise HTTPException(404, "Task not found")
    item.status = payload.status; audit(db, f"CA task marked {payload.status}", task_id); db.commit(); return as_dict(item)

@app.get("/api/audit-events")
def list_audit_events(db: Session = Depends(get_db)): return [as_dict(x) for x in db.scalars(select(AuditEvent).order_by(AuditEvent.at.desc()).limit(50)).all()]
