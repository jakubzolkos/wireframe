from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy import String, DateTime, ForeignKey, JSON, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="PENDING")
    pdf_path: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    job_states: Mapped[list["JobState"]] = relationship(back_populates="job", cascade="all, delete-orphan")
    designs: Mapped[list["Design"]] = relationship(back_populates="job", cascade="all, delete-orphan")
    artifacts: Mapped[list["Artifact"]] = relationship(back_populates="job", cascade="all, delete-orphan")


class JobState(Base):
    __tablename__ = "job_states"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    job_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"))
    graph_state: Mapped[dict] = mapped_column(JSONB)
    checkpoint_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    job: Mapped["Job"] = relationship(back_populates="job_states")


class Design(Base):
    __tablename__ = "designs"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    job_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"))
    device_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    datasheet_title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    metadata: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    job: Mapped["Job"] = relationship(back_populates="designs")
    bom_items: Mapped[list["BOMItem"]] = relationship(back_populates="design", cascade="all, delete-orphan")
    circuit_components: Mapped[list["CircuitComponent"]] = relationship(
        back_populates="design", cascade="all, delete-orphan"
    )


class BOMItem(Base):
    __tablename__ = "bom_items"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    design_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("designs.id", ondelete="CASCADE"))
    reference: Mapped[str] = mapped_column(String(50))
    part_number: Mapped[str | None] = mapped_column(String(255), nullable=True)
    manufacturer: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    value: Mapped[str | None] = mapped_column(String(100), nullable=True)
    quantity: Mapped[int] = mapped_column(default=1)
    package: Mapped[str | None] = mapped_column(String(100), nullable=True)

    design: Mapped["Design"] = relationship(back_populates="bom_items")


class CircuitComponent(Base):
    __tablename__ = "circuit_components"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    design_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("designs.id", ondelete="CASCADE"))
    ref_des: Mapped[str] = mapped_column(String(50))
    value: Mapped[str] = mapped_column(String(255))
    pins: Mapped[dict] = mapped_column(JSONB)
    footprint: Mapped[str | None] = mapped_column(String(255), nullable=True)
    x_pos: Mapped[float | None] = mapped_column(nullable=True)
    y_pos: Mapped[float | None] = mapped_column(nullable=True)

    design: Mapped["Design"] = relationship(back_populates="circuit_components")


class Artifact(Base):
    __tablename__ = "artifacts"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    job_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"))
    artifact_type: Mapped[str] = mapped_column(String(50))
    file_path: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    job: Mapped["Job"] = relationship(back_populates="artifacts")
