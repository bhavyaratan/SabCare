from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, JSON, Float, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

SQLALCHEMY_DATABASE_URL = "sqlite:///./patients.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    diagnosis = Column(String)
    summary = Column(Text)
    phone = Column(String)
    medication_schedule = Column(Text)
    call_schedule = Column(Text)
    automated_call_category = Column(String)
    race = Column(String, default="")
    age = Column(String, default="")  # in years
    height = Column(String, default="")  # in cm
    weight = Column(String, default="")  # in kg
    bmi = Column(String, default="")
    risk_factors = Column(Text, default="")  # stored as text
    additional_notes = Column(Text, default="")  # stored as text
    risk_category = Column(String, default="low")  # low, medium, high
    lmp_date = Column(DateTime, nullable=True)  # Last Menstrual Period date
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # RAG and Medical Context fields
    medical_context = Column(JSON, default=dict)  # Store patient-specific medical context
    rag_embeddings = Column(JSON, default=dict)  # Store relevant medical embeddings
    medical_guidelines = Column(JSON, default=dict)  # Store personalized guidelines
    treatment_history = Column(Text, default="")  # Store treatment history
    symptoms_log = Column(Text, default="")  # Store symptom tracking
    medication_history = Column(Text, default="")  # Store medication history
    
    # Postnatal Care Fields
    delivery_date = Column(DateTime, nullable=True)  # Date of childbirth
    delivery_type = Column(String, default="")  # vaginal, c-section, etc.
    is_postpartum = Column(Boolean, default=False)  # True if patient is in postnatal period
    postpartum_week = Column(Integer, default=0)  # Current week postpartum (1-4)
    postnatal_care_schedule = Column(Text, default="")  # Weekly postnatal care schedule
    
    # Patient Metrics for Call Success Rates and Duration
    total_calls_scheduled = Column(Integer, default=0)
    total_calls_completed = Column(Integer, default=0)
    total_calls_failed = Column(Integer, default=0)
    total_calls_missed = Column(Integer, default=0)
    average_call_duration = Column(Float, default=0.0)  # in seconds
    total_call_duration = Column(Float, default=0.0)  # total duration in seconds
    last_call_date = Column(DateTime, nullable=True)
    last_call_status = Column(String, default="")  # completed, failed, missed
    call_success_rate = Column(Float, default=0.0)  # percentage of successful calls
    
    # Call History Tracking
    call_history = Column(JSON, default=list)  # Store detailed call history
    response_times = Column(JSON, default=list)  # Store response time data
    engagement_metrics = Column(JSON, default=dict)  # Store engagement data
    
    # Relationship to messages
    messages = relationship("PatientMessage", back_populates="patient")

class PatientMessage(Base):
    __tablename__ = "patient_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    message_text = Column(Text)  # The patient's original message
    message_type = Column(String, default="inbound")  # inbound, callback
    recording_url = Column(String, nullable=True)  # URL to audio recording if available
    processed_response = Column(Text, nullable=True)  # AI-generated response
    gemma_response = Column(Text, nullable=True)  # Raw Gemma model response
    scheduled_callback = Column(DateTime, nullable=True)  # When to call back
    callback_message = Column(Text, nullable=True)  # The callback message to deliver
    status = Column(String, default="pending")  # pending, processed, scheduled, completed
    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)
    callback_completed_at = Column(DateTime, nullable=True)
    
    # Relationship to patient
    patient = relationship("Patient", back_populates="messages")

# Create tables
Base.metadata.create_all(bind=engine)
