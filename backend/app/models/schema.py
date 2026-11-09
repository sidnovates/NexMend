from datetime import date, datetime
from typing import List, Optional
from sqlalchemy import (
    String, Integer, Numeric, Boolean, Date, DateTime, 
    ForeignKey, Text, func
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    pincode: Mapped[str] = mapped_column(String(10), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    appliances: Mapped[List["Appliance"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    tickets: Mapped[List["RepairTicket"]] = relationship(back_populates="user", cascade="all, delete-orphan")

class Appliance(Base):
    __tablename__ = "appliances"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    brand: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    model_number: Mapped[str] = mapped_column(String(100), nullable=False)
    serial_number: Mapped[Optional[str]] = mapped_column(String(100))
    purchase_date: Mapped[date] = mapped_column(Date, nullable=False)
    invoice_url: Mapped[Optional[str]] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="appliances")
    tickets: Mapped[List["RepairTicket"]] = relationship(back_populates="appliance")

class Technician(Base):
    __tablename__ = "technicians"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    brands_supported: Mapped[List[str]] = mapped_column(ARRAY(String), nullable=False)
    service_pincodes: Mapped[List[str]] = mapped_column(ARRAY(String), nullable=False)
    rating: Mapped[float] = mapped_column(Numeric(2, 1), default=4.5)
    base_inspection_fee: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)

    tickets: Mapped[List["RepairTicket"]] = relationship(back_populates="technician")

class ManualChunk(Base):
    __tablename__ = "manual_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    brand: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    model_series: Mapped[str] = mapped_column(String(100), nullable=False)
    section_name: Mapped[str] = mapped_column(String(150), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding = mapped_column(Vector(1536))

class RepairTicket(Base):
    __tablename__ = "repair_tickets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    appliance_id: Mapped[int] = mapped_column(ForeignKey("appliances.id", ondelete="CASCADE"), nullable=False)
    symptoms_text: Mapped[str] = mapped_column(Text, nullable=False)
    diagnosis_summary: Mapped[Optional[dict]] = mapped_column(JSONB)
    warranty_status: Mapped[Optional[str]] = mapped_column(String(50))
    technician_id: Mapped[Optional[int]] = mapped_column(ForeignKey("technicians.id", ondelete="SET NULL"))
    booking_status: Mapped[str] = mapped_column(String(30), default="REPORTED")
    scheduled_slot: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user: Mapped["User"] = relationship(back_populates="tickets")
    appliance: Mapped["Appliance"] = relationship(back_populates="tickets")
    technician: Mapped[Optional["Technician"]] = relationship(back_populates="tickets")