import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

DATABASE_PATH = Path(os.getenv("DATABASE_PATH", "./clearbooks.db"))

@contextmanager
def db_connection():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()

def initialize_database():
    with db_connection() as db:
        db.executescript("""
          CREATE TABLE IF NOT EXISTS reconciliation_exceptions (id TEXT PRIMARY KEY, name TEXT, source TEXT, amount TEXT, action TEXT, status TEXT);
          CREATE TABLE IF NOT EXISTS filings (id TEXT PRIMARY KEY, type TEXT, period TEXT, prepared_by TEXT, evidence TEXT, status TEXT, owner_approved INTEGER);
          CREATE TABLE IF NOT EXISTS documents (id TEXT PRIMARY KEY, name TEXT, category TEXT, uploaded_at TEXT);
          CREATE TABLE IF NOT EXISTS ca_tasks (id TEXT PRIMARY KEY, title TEXT, assignee TEXT, status TEXT, created_at TEXT);
          CREATE TABLE IF NOT EXISTS audit_events (id TEXT PRIMARY KEY, action TEXT, entity_id TEXT, actor TEXT, at TEXT);
        """)
        if db.execute("SELECT COUNT(*) FROM filings").fetchone()[0] == 0:
            db.executemany("INSERT INTO reconciliation_exceptions VALUES (?, ?, ?, ?, ?, ?)", [("ex-1","NEFT / Riya Traders","HDFC statement","₹74,000","Link sales invoice or mark as advance","open"),("ex-2","INV-237 · Apex Dyes","Purchase register","₹32,400 ITC","Ask supplier to upload invoice","open"),("ex-3","UPI / Office expense","HDFC statement","₹8,750","Upload bill and select category","open")])
            db.executemany("INSERT INTO filings VALUES (?, ?, ?, ?, ?, ?, ?)", [("filing-1","GSTR-3B","Oct 2026","Rao & Co.","1 mismatch","draft",0),("filing-2","GSTR-1","Oct 2026","Rao & Co.","Matched","filed",1),("filing-3","TDS return","Q2 FY27","Not started","—","not_started",0)])

app = FastAPI(title="ClearBooks MVP API", version="0.3.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.on_event("startup")
def startup(): initialize_database()

class ExceptionUpdate(BaseModel): status: Literal["open", "resolved", "escalated"]
class DocumentCreate(BaseModel): name: str; category: str
class TaskCreate(BaseModel): title: str; assignee: str = "Rao & Co."
class TaskUpdate(BaseModel): status: Literal["open", "done"]

def rows(cursor): return [dict(row) for row in cursor.fetchall()]
def audit(db, action, entity_id): db.execute("INSERT INTO audit_events VALUES (?, ?, ?, ?, ?)", (str(uuid4()), action, entity_id, "Arnav, Director", datetime.now(timezone.utc).isoformat()))

@app.get("/api/health")
def health(): return {"status":"ok", "database":"sqlite", "path":str(DATABASE_PATH)}

@app.get("/api/dashboard")
def dashboard():
    with db_connection() as db:
        open_count = db.execute("SELECT COUNT(*) FROM reconciliation_exceptions WHERE status='open'").fetchone()[0]
        completed = db.execute("SELECT COUNT(*) FROM filings WHERE status IN ('filed','approved')").fetchone()[0]
    return {"company":"Aarav Textiles Pvt Ltd","financial_year":"FY 2026–27","metrics":[{"label":"Bank reconciliation","value":"96%","detail":"↑ 8% this month","tone":"good"},{"label":"Unmatched transactions","value":str(open_count),"detail":"₹1.48L needs review","tone":"warning"},{"label":"Input tax at risk","value":"₹68K","detail":"4 supplier invoices missing","tone":"warning"},{"label":"October filings","value":f"{completed} / 3","detail":"One filed, two ready","tone":"good"}],"actions":[{"title":"Approve GSTR-3B draft","detail":"Prepared by Rao & Co. · Due in 3 days","status":"Review","tone":"warning"},{"title":"Match purchase invoices","detail":"Reconciliation exceptions still open","status":"Risk","tone":"danger"},{"title":"GSTR-1 acknowledgement received","detail":"ARN: AA070… · Filed 9 Oct","status":"Filed","tone":"good"}],"health":[{"label":"Bank ↔ books","value":96,"tone":"good"},{"label":"Sales ↔ GSTR-1","value":100,"tone":"primary"},{"label":"Purchases ↔ GSTR-2B","value":88,"tone":"warning"}]}

@app.get("/api/exceptions")
def exceptions():
    with db_connection() as db: return rows(db.execute("SELECT * FROM reconciliation_exceptions"))

@app.patch("/api/exceptions/{item_id}")
def update_exception(item_id: str, payload: ExceptionUpdate):
    with db_connection() as db:
        if not db.execute("SELECT id FROM reconciliation_exceptions WHERE id=?", (item_id,)).fetchone(): raise HTTPException(404,"Exception not found")
        db.execute("UPDATE reconciliation_exceptions SET status=? WHERE id=?", (payload.status,item_id)); audit(db,f"Exception marked {payload.status}",item_id)
        return dict(db.execute("SELECT * FROM reconciliation_exceptions WHERE id=?",(item_id,)).fetchone())

@app.get("/api/filings")
def filings():
    with db_connection() as db: return rows(db.execute("SELECT id,type,period,prepared_by,evidence,status,CAST(owner_approved AS BOOLEAN) AS owner_approved FROM filings"))

@app.post("/api/filings/{item_id}/approve")
def approve_filing(item_id: str):
    with db_connection() as db:
        item=db.execute("SELECT * FROM filings WHERE id=?",(item_id,)).fetchone()
        if not item: raise HTTPException(404,"Filing not found")
        if item["status"] != "draft": raise HTTPException(409,"Only a draft can be approved")
        db.execute("UPDATE filings SET status='approved',owner_approved=1 WHERE id=?",(item_id,)); audit(db,"Owner approved filing draft",item_id)
        return dict(db.execute("SELECT id,type,period,prepared_by,evidence,status,CAST(owner_approved AS BOOLEAN) AS owner_approved FROM filings WHERE id=?",(item_id,)).fetchone())

@app.get("/api/documents")
def documents():
    with db_connection() as db: return rows(db.execute("SELECT * FROM documents ORDER BY uploaded_at DESC"))

@app.post("/api/documents", status_code=201)
def create_document(payload: DocumentCreate):
    if not payload.name.strip(): raise HTTPException(400,"Document name is required")
    item_id=str(uuid4()); timestamp=datetime.now(timezone.utc).isoformat()
    with db_connection() as db:
        db.execute("INSERT INTO documents VALUES (?,?,?,?)",(item_id,payload.name.strip(),payload.category,timestamp)); audit(db,"Document registered",item_id)
    return {"id":item_id,"name":payload.name.strip(),"category":payload.category,"uploaded_at":timestamp}

@app.get("/api/ca-tasks")
def ca_tasks():
    with db_connection() as db: return rows(db.execute("SELECT * FROM ca_tasks ORDER BY created_at DESC"))

@app.post("/api/ca-tasks", status_code=201)
def create_ca_task(payload: TaskCreate):
    if not payload.title.strip(): raise HTTPException(400,"Task title is required")
    item_id=str(uuid4()); timestamp=datetime.now(timezone.utc).isoformat()
    with db_connection() as db:
        db.execute("INSERT INTO ca_tasks VALUES (?,?,?,?,?)",(item_id,payload.title.strip(),payload.assignee,"open",timestamp)); audit(db,"CA task created",item_id)
    return {"id":item_id,"title":payload.title.strip(),"assignee":payload.assignee,"status":"open","created_at":timestamp}

@app.patch("/api/ca-tasks/{item_id}")
def update_ca_task(item_id: str, payload: TaskUpdate):
    with db_connection() as db:
        if not db.execute("SELECT id FROM ca_tasks WHERE id=?",(item_id,)).fetchone(): raise HTTPException(404,"Task not found")
        db.execute("UPDATE ca_tasks SET status=? WHERE id=?",(payload.status,item_id)); audit(db,f"CA task marked {payload.status}",item_id)
        return dict(db.execute("SELECT * FROM ca_tasks WHERE id=?",(item_id,)).fetchone())

@app.get("/api/audit-events")
def audit_events():
    with db_connection() as db: return rows(db.execute("SELECT * FROM audit_events ORDER BY at DESC LIMIT 50"))
