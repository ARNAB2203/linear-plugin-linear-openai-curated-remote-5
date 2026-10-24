from datetime import datetime
from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base

class ReconciliationException(Base):
    __tablename__ = "reconciliation_exceptions"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(255)); source: Mapped[str] = mapped_column(String(120)); amount: Mapped[str] = mapped_column(String(60)); action: Mapped[str] = mapped_column(Text); status: Mapped[str] = mapped_column(String(20), default="open")

class Filing(Base):
    __tablename__ = "filings"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    type: Mapped[str] = mapped_column(String(80)); period: Mapped[str] = mapped_column(String(80)); prepared_by: Mapped[str] = mapped_column(String(120)); evidence: Mapped[str] = mapped_column(String(80)); status: Mapped[str] = mapped_column(String(30), default="draft"); owner_approved: Mapped[bool] = mapped_column(Boolean, default=False)

class Document(Base):
    __tablename__ = "documents"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(255)); category: Mapped[str] = mapped_column(String(80)); storage_path: Mapped[str] = mapped_column(Text); uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class CATask(Base):
    __tablename__ = "ca_tasks"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    title: Mapped[str] = mapped_column(String(255)); assignee: Mapped[str] = mapped_column(String(120), default="Rao & Co."); status: Mapped[str] = mapped_column(String(30), default="open"); created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    action: Mapped[str] = mapped_column(String(255)); entity_id: Mapped[str] = mapped_column(String(40)); actor: Mapped[str] = mapped_column(String(120)); at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
