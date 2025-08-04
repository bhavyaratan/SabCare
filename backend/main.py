from fastapi import FastAPI, UploadFile, File, HTTPException, Body, Path, Query, Request, Form
from typing import Union, List, Dict, Any
from fastapi.responses import JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from db import SessionLocal, Patient, PatientMessage
from scheduler import enhanced_scheduler, start_scheduler
from medgemma import medgemma_ai
from medgemma_fine_tuned import fine_tuned_medgemma_ai
import re
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timedelta
from twilio.twiml.voice_response import VoiceResponse, Gather
import requests
import os
import uuid
import time
import json
import logging
from automated_calls import automated_call_service
from rag_service import rag_service
from pregnancy_rag_database import pregnancy_rag_db
from fine_tune_gemma import gemma_fine_tuner
from twilio_call import twilio_call_service
from tts_service import tts_service

app = FastAPI()

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = logging.getLogger(__name__)

def calculate_gestational_age_from_lmp(lmp_date: datetime, current_date: datetime = None) -> int:
    """Calculate gestational age in weeks from LMP date"""
    if current_date is None:
        current_date = datetime.now()
    
    # Calculate the difference in days
    days_diff = (current_date - lmp_date).days
    
    # Convert to weeks (7 days per week)
    weeks = days_diff // 7
    
    # Ensure gestational age is between 0 and 42 weeks
    return max(0, min(42, weeks))

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    # Start the enhanced scheduler
    start_scheduler()
    print("Enhanced scheduler started.")

@app.get("/")
def read_root():
    return {"message": "AI Health Companion Backend Running"}

# Helper: Parse patient record from text
PATIENT_RECORD_REGEX = re.compile(r"""
Patient Name:\s*(?P<name>.+)\n
Date:\s*(?P<date>.+)\n
Diagnosis:\s*(?P<diagnosis>.+)\n
Summary:\n(?P<summary>(?:.+\n)+?)\nMedication Schedule:\n(?P<medication_schedule>(?:- .+\n)+)
\nCall Schedule:\n(?P<call_schedule>(?:- .+\n)+)
\nAutomated Call Category:\s*(?P<automated_call_category>.+)
""", re.MULTILINE)

def ensure_call_schedule_format(schedule_data):
    """Ensure call_schedule is always stored as a dictionary with consistent format"""
    if isinstance(schedule_data, str):
        try:
            # Try to parse as JSON
            parsed = json.loads(schedule_data)
            if isinstance(parsed, list):
                return json.dumps({"schedule": parsed})
            elif isinstance(parsed, dict):
                if "schedule" in parsed:
                    return json.dumps(parsed)
                else:
                    return json.dumps({"schedule": [parsed]})
            else:
                return json.dumps({"schedule": []})
        except json.JSONDecodeError:
            # If it's not valid JSON, create a basic structure
            return json.dumps({"schedule": []})
    elif isinstance(schedule_data, list):
        return json.dumps({"schedule": schedule_data})
    elif isinstance(schedule_data, dict):
        if "schedule" in schedule_data:
            return json.dumps(schedule_data)
        else:
            return json.dumps({"schedule": [schedule_data]})
    else:
        return json.dumps({"schedule": []})

def parse_patient_record(text: str):
    match = PATIENT_RECORD_REGEX.search(text)
    if not match:
        raise ValueError("Invalid patient record format.")
    return match.groupdict()

@app.post("/upload_patient_record/")
async def upload_patient_record(file: UploadFile = File(...)):
    content = await file.read()
    try:
        text = content.decode("utf-8")
        data = parse_patient_record(text)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse file: {e}")
    # Store in DB
    db = SessionLocal()
    patient = Patient(
        name=data["name"],
        diagnosis=data["diagnosis"],
        summary=data["summary"].strip(),
        medication_schedule=data["medication_schedule"].strip(),
        call_schedule=ensure_call_schedule_format(data["call_schedule"]),
        automated_call_category=data["automated_call_category"].strip(),
    )
    db.add(patient)
    db.commit()
    db.refresh(patient)
    db.close()
    return {"status": "success", "patient_id": patient.id, "name": patient.name}

@app.get("/patients/")
def list_patients():
    db = SessionLocal()
    patients = db.query(Patient).all()
    db.close()
    return [{
        "id": p.id,
        "name": p.name,
        "diagnosis": p.diagnosis,
        "phone": p.phone,
        "description": p.summary,
        "medication_schedule": p.medication_schedule,
        "call_schedule": p.call_schedule,
        "automated_call_category": p.automated_call_category,
        "race": p.race,
        "age": p.age,
        "height": p.height,
        "weight": p.weight,
        "bmi": p.bmi,
        "risk_factors": p.risk_factors,
        "additional_notes": p.additional_notes,
        "risk_category": p.risk_category,
        # Postnatal care fields
        "delivery_date": p.delivery_date.isoformat() if p.delivery_date else None,
        "delivery_type": p.delivery_type,
        "is_postpartum": p.is_postpartum,
        "postpartum_week": p.postpartum_week,
        # Patient metrics
        "total_calls_scheduled": p.total_calls_scheduled,
        "total_calls_completed": p.total_calls_completed,
        "total_calls_failed": p.total_calls_failed,
        "total_calls_missed": p.total_calls_missed,
        "call_success_rate": p.call_success_rate,
        "average_call_duration": p.average_call_duration,
        "last_call_date": p.last_call_date.isoformat() if p.last_call_date else None,
        "last_call_status": p.last_call_status,
    } for p in patients]

@app.post("/patients/")
def create_patient(
    patient: dict = Body(...)
):
    db = SessionLocal()
    try:
        # Extract patient data
        patient_name = patient.get("name", "")
        lmp_date_str = patient.get("lmp_date", "")
        risk_category = patient.get("risk_category", "low")
        medications = patient.get("medications", "")
        phone = patient.get("phone", "")
        # Postnatal care data
        delivery_date_str = patient.get("delivery_date")
        delivery_type = patient.get("delivery_type", "vaginal")
        is_postpartum = patient.get("is_postpartum", False)
        
        # Parse LMP date and calculate gestational age
        lmp_date = None
        gestational_age = 0
        if lmp_date_str:
            try:
                lmp_date = datetime.fromisoformat(lmp_date_str.replace('Z', '+00:00'))
                gestational_age = calculate_gestational_age_from_lmp(lmp_date)
            except ValueError:
                # If LMP date is invalid, try to parse gestational age directly
                gestational_age = patient.get("gestational_age", 0)
        
        # Parse medications into structured format
        structured_medications = patient.get("structured_medications", [])
        if not structured_medications and medications:
            # Handle medications whether it's a string or list
            if isinstance(medications, str):
                med_list = [med.strip() for med in medications.split(',')]
            elif isinstance(medications, list):
                med_list = medications
            else:
                med_list = []
            
            for med in med_list:
                if med:
                    structured_medications.append({
                        "name": med,
                        "dosage": "as prescribed",
                        "frequency": "daily"
                    })
        
        current_date = datetime.now()

        # Handle postnatal care patients
        delivery_date = None
        postpartum_week = 0
        if delivery_date_str:
            try:
                delivery_date = datetime.fromisoformat(delivery_date_str.replace('Z', '+00:00'))
                is_postpartum = True
                postpartum_week = max(0, (current_date - delivery_date).days // 7)
            except ValueError:
                delivery_date = None

        call_schedule = None
        if is_postpartum and delivery_date:
            try:
                postnatal_result = medgemma_ai.generate_postnatal_care_schedule(
                    patient_name=patient_name,
                    delivery_date=delivery_date,
                    current_date=current_date,
                    delivery_type=delivery_type
                )
                call_schedule = ensure_call_schedule_format(postnatal_result.get("schedule", []))
            except Exception as e:
                print(f"Warning: Postnatal schedule generation failed: {e}")
                call_schedule = ensure_call_schedule_format([])
        else:
            # Use fine-tuned MedGemma to generate proper IVR schedule for pregnancy
            try:
                ivr_result = fine_tuned_medgemma_ai.generate_comprehensive_ivr_schedule(
                    gestational_age_weeks=gestational_age,
                    patient_name=patient_name,
                    current_date=current_date,
                    risk_factors=patient.get("risk_factors", []),
                    risk_category=risk_category,
                    structured_medications=structured_medications
                )
            except Exception as e:
                print(f"Warning: IVR schedule generation failed: {e}")
                ivr_result = None

            # Extract the schedule from the result
            if isinstance(ivr_result, dict) and ivr_result.get("success"):
                ivr_schedule = ivr_result.get("schedule", [])
                call_schedule = ensure_call_schedule_format(ivr_schedule)
            else:
                # Fallback to basic schedule if MedGemma fails
                call_schedule = ensure_call_schedule_format([
                    {
                        "type": "medication_reminder",
                        "message": f"Hello {patient_name}, this is your medication reminder. Please take your medications as prescribed.",
                        "time": "09:00 AM"
                    },
                    {
                        "type": "appointment_reminder",
                        "message": f"Hello {patient_name}, this is your appointment reminder. Please attend your scheduled prenatal visit.",
                        "time": "02:00 PM"
                    }
                ])

        # Create diagnosis string
        diagnosis = patient.get("diagnosis", "")
        if not is_postpartum and gestational_age > 0:
            diagnosis = f"Pregnancy - Week {gestational_age}"
        
        new_patient = Patient(
            name=patient_name,
            diagnosis=diagnosis,
            summary=patient.get("description", ""),
            phone=phone,
            medication_schedule=medications,
            call_schedule=call_schedule,
            automated_call_category=patient.get("automated_call_category", "pregnancy_care"),
            race=patient.get("race", ""),
            age=patient.get("age", ""),
            height=patient.get("height", ""),
            weight=patient.get("weight", ""),
            bmi=patient.get("bmi", ""),
            risk_factors=", ".join(patient.get("risk_factors", [])) if isinstance(patient.get("risk_factors"), list) else patient.get("risk_factors", ""),
            additional_notes=patient.get("additional_notes", ""),
            risk_category=risk_category,
            lmp_date=lmp_date,
            delivery_date=delivery_date,
            delivery_type=delivery_type if is_postpartum else "",
            is_postpartum=is_postpartum,
            postpartum_week=postpartum_week,
            postnatal_care_schedule=call_schedule if is_postpartum else ""
        )
        db.add(new_patient)
        db.commit()
        db.refresh(new_patient)
        return {
            "id": new_patient.id,
            "name": new_patient.name,
            "diagnosis": new_patient.diagnosis,
            "phone": new_patient.phone,
            "description": new_patient.summary,
            "medication_schedule": new_patient.medication_schedule,
            "call_schedule": new_patient.call_schedule,
            "automated_call_category": new_patient.automated_call_category,
            "race": new_patient.race,
            "age": new_patient.age,
            "height": new_patient.height,
            "weight": new_patient.weight,
            "bmi": new_patient.bmi,
            "risk_factors": new_patient.risk_factors,
            "additional_notes": new_patient.additional_notes,
            "risk_category": new_patient.risk_category,
            "lmp_date": new_patient.lmp_date.isoformat() if new_patient.lmp_date else None,
            "gestational_age": gestational_age,
            "delivery_date": new_patient.delivery_date.isoformat() if new_patient.delivery_date else None,
            "delivery_type": new_patient.delivery_type,
            "is_postpartum": new_patient.is_postpartum,
            "postpartum_week": new_patient.postpartum_week
        }
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    finally:
        db.close()

@app.get("/patients/{patient_id}")
def get_patient(patient_id: int):
    db = SessionLocal()
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    db.close()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return {
        "id": patient.id,
        "name": patient.name,
        "diagnosis": patient.diagnosis,
        "phone": patient.phone,
        "description": patient.summary,
        "medication_schedule": patient.medication_schedule,
        "call_schedule": patient.call_schedule,
        "automated_call_category": patient.automated_call_category,
        "race": patient.race,
        "age": patient.age,
        "height": patient.height,
        "weight": patient.weight,
        "bmi": patient.bmi,
        "risk_factors": patient.risk_factors,
        "additional_notes": patient.additional_notes,
        "risk_category": patient.risk_category,
        "delivery_date": patient.delivery_date.isoformat() if patient.delivery_date else None,
        "delivery_type": patient.delivery_type,
        "is_postpartum": patient.is_postpartum,
        "postpartum_week": patient.postpartum_week,
        "total_calls_scheduled": patient.total_calls_scheduled,
        "total_calls_completed": patient.total_calls_completed,
        "total_calls_failed": patient.total_calls_failed,
        "total_calls_missed": patient.total_calls_missed,
        "call_success_rate": patient.call_success_rate,
        "average_call_duration": patient.average_call_duration,
        "last_call_date": patient.last_call_date.isoformat() if patient.last_call_date else None,
        "last_call_status": patient.last_call_status,
    }

@app.put("/patients/{patient_id}")
def update_patient(patient_id: int, patient: dict = Body(...)):
    db = SessionLocal()
    try:
        db_patient = db.query(Patient).filter(Patient.id == patient_id).first()
        if not db_patient:
            raise HTTPException(status_code=404, detail="Patient not found")
        db_patient.name = patient.get("name", db_patient.name)
        db_patient.diagnosis = patient.get("diagnosis", db_patient.diagnosis)
        db_patient.summary = patient.get("description", db_patient.summary)
        db_patient.phone = patient.get("phone", db_patient.phone)
        db_patient.medication_schedule = patient.get("medication_schedule", db_patient.medication_schedule)
        db_patient.call_schedule = ensure_call_schedule_format(patient.get("call_schedule", db_patient.call_schedule))
        db_patient.automated_call_category = patient.get("automated_call_category", db_patient.automated_call_category)
        # Postnatal fields
        if patient.get("delivery_date"):
            try:
                db_patient.delivery_date = datetime.fromisoformat(patient.get("delivery_date").replace('Z', '+00:00'))
            except ValueError:
                pass
        db_patient.delivery_type = patient.get("delivery_type", db_patient.delivery_type)
        db_patient.is_postpartum = patient.get("is_postpartum", db_patient.is_postpartum)
        db_patient.postpartum_week = patient.get("postpartum_week", db_patient.postpartum_week)
        db.commit()
        db.refresh(db_patient)
        return {
            "id": db_patient.id,
            "name": db_patient.name,
            "diagnosis": db_patient.diagnosis,
            "phone": db_patient.phone,
            "description": db_patient.summary,
            "medication_schedule": db_patient.medication_schedule,
            "call_schedule": db_patient.call_schedule,
            "automated_call_category": db_patient.automated_call_category,
            "delivery_date": db_patient.delivery_date.isoformat() if db_patient.delivery_date else None,
            "delivery_type": db_patient.delivery_type,
            "is_postpartum": db_patient.is_postpartum,
            "postpartum_week": db_patient.postpartum_week
        }
    finally:
        db.close()

@app.delete("/patients/{patient_id}")
def delete_patient(patient_id: int = Path(...)):
    db = SessionLocal()
    try:
        db_patient = db.query(Patient).filter(Patient.id == patient_id).first()
        if not db_patient:
            raise HTTPException(status_code=404, detail="Patient not found")
        db.delete(db_patient)
        db.commit()
        return {"status": "deleted"}
    finally:
        db.close()

@app.get("/patient_context/")
def get_patient_context(name: str = Query(..., description="Patient's name")):
    db = SessionLocal()
    patient = db.query(Patient).filter(Patient.name == name).first()
    db.close()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return {
        "id": patient.id,
        "name": patient.name,
        "phone": patient.phone,
        "diagnosis": patient.diagnosis,
        "description": patient.summary,
        "medication_schedule": patient.medication_schedule,
        "call_schedule": patient.call_schedule,
        "automated_call_category": patient.automated_call_category
    }

@app.get("/call_queue/")
def get_call_queue():
    db = SessionLocal()
    patients = db.query(Patient).all()
    all_calls = []
    now = datetime.now()
    for patient in patients:
        if not patient.call_schedule:
            continue
        try:
            schedule_data = patient.call_schedule
            schedule = schedule_data if isinstance(schedule_data, dict) else schedule_data.get("schedule", [])
            for item in schedule:
                # Only include future calls
                call_datetime = datetime.strptime(item["date"] + " " + item["time"], "%Y-%m-%d %I:%M %p")
                if call_datetime >= now:
                    all_calls.append({
                        "patient_id": patient.id,
                        "patient_name": patient.name,
                        "date": item["date"],
                        "time": item["time"],
                        "topic": item.get("topic", ""),
                        "message": item.get("message", "")
                    })
        except Exception as e:
            logger.error(f"Error parsing schedule for {patient.name}: {e}")
            continue
    # Sort all calls by date/time
    all_calls.sort(key=lambda x: (x["date"], x["time"]))
    return all_calls[:10]

# Placeholder for outbound call schedule system
# In the future, implement a daily job that checks each patient's call_schedule and triggers outbound calls at the right times.

@app.post("/twilio/inbound")
async def inbound_call(request: Request):
    """Handles the initial inbound call and prompts the patient to ask a question."""
    response = VoiceResponse()
    gather = Gather(
        input="speech",
        action="/twilio/process_question",
        method="POST",
        timeout=5,
        speechTimeout="auto"
    )
    gather.say("Hello, this is your AI health assistant. Please ask your question after the beep.")
    response.append(gather)
    response.say("Sorry, I didn't get your question. Goodbye.")
    return Response(content=str(response), media_type="application/xml")

@app.post("/twilio/handle_message_choice")
async def handle_message_choice(request: Request):
    """Handle the patient's choice to leave a message (Press 1)"""
    form_data = await request.form()
    digits = form_data.get("Digits", "")
    
    response = VoiceResponse()
    
    if digits == "1":
        # Patient wants to leave a message
        response.say("Please leave your message after the beep. Press any key when you're done.")
        response.record(
            action="/twilio/process_message",
            method="POST",
            maxLength="120",
            timeout="10",
            playBeep="true",
            trim="trim-silence"
        )
    else:
        # Patient didn't press 1 or pressed something else
        response.say("Thank you for calling. Goodbye.")
    
    return Response(content=str(response), media_type="application/xml")

@app.post("/twilio/process_message")
async def process_message(request: Request):
    """Process the recorded message and schedule a callback"""
    try:
        form_data = await request.form()
        recording_url = form_data.get("RecordingUrl", "")
        recording_duration = form_data.get("RecordingDuration", "0")
        from_number = form_data.get("From", "")
        
        # Find patient by phone number
        db = SessionLocal()
        patient = db.query(Patient).filter(Patient.phone == from_number).first()
        
        if not patient:
            # If no patient found, create a generic message
            response = VoiceResponse()
            response.say("Thank you for your message. We'll get back to you soon.")
            return Response(content=str(response), media_type="application/xml")
        
        # Store the message in database
        from datetime import datetime, timedelta
        patient_message = PatientMessage(
            patient_id=patient.id,
            message_text=f"Voice message recorded for {patient.name}",
            message_type="inbound",
            recording_url=recording_url,
            status="pending"
        )
        db.add(patient_message)
        db.commit()
        
        # Process with fine-tuned Gemma model
        try:
            from medgemma_fine_tuned import fine_tuned_medgemma_ai
            
            # Create a prompt for the AI to process the message
            prompt = f"""Patient {patient.name} left a voice message. 
            Please analyze this message and provide a helpful medical response.
            Patient context: {patient.diagnosis}
            Risk factors: {patient.risk_factors}
            
            Generate a professional, caring response that addresses their concerns."""
            
            gemma_response = fine_tuned_medgemma_ai.generate_personalized_ivr_message(
                topic="patient_message_response",
                patient_name=patient.name,
                gestational_age_weeks=20,  # Default, could be extracted from diagnosis
                risk_factors=patient.risk_factors.split(', ') if patient.risk_factors else [],
                risk_category=patient.risk_category or "low"
            )
            
            # Schedule callback for tomorrow
            tomorrow = datetime.now() + timedelta(days=1)
            callback_message = f"About your question yesterday on {datetime.now().strftime('%B %d')}, {gemma_response}"
            
            patient_message.processed_response = callback_message
            patient_message.gemma_response = gemma_response
            patient_message.scheduled_callback = tomorrow
            patient_message.callback_message = callback_message
            patient_message.status = "processed"
            patient_message.processed_at = datetime.now()
            
            db.commit()
            
            # Schedule the callback call
            from scheduler import enhanced_scheduler
            enhanced_scheduler.add_job(
                func="backend.twilio_call:make_callback_call",
                trigger="date",
                run_date=tomorrow,
                args=[patient.phone, callback_message, patient.id, patient_message.id],
                id=f"callback_{patient_message.id}_{patient.id}"
            )
            
        except Exception as e:
            logger.error(f"Error processing message with Gemma: {e}")
            # Fallback response
            callback_message = f"About your question yesterday on {datetime.now().strftime('%B %d')}, thank you for your message. Our medical team will review it and get back to you soon."
            patient_message.callback_message = callback_message
            patient_message.status = "processed"
            db.commit()
        
        db.close()
        
        # Respond to the patient
        response = VoiceResponse()
        response.say("Thank you for your message. We'll get back to you tomorrow with a detailed response.")
        
        return Response(content=str(response), media_type="application/xml")
        
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        response = VoiceResponse()
        response.say("Thank you for your message. We'll get back to you soon.")
        return Response(content=str(response), media_type="application/xml")

@app.post("/n8n/trigger_patient_add")
async def n8n_trigger_patient_add(patient_data: dict):
    """Webhook endpoint for n8n to trigger patient addition"""
    try:
        # Use existing patient creation logic
        db = SessionLocal()
        patient = Patient(
            name=patient_data.get("name"),
            diagnosis=patient_data.get("diagnosis", ""),
            phone=patient_data.get("phone", ""),
            summary=patient.get("description", ""),
            medication_schedule=patient.get("medication_schedule", ""),
            call_schedule=ensure_call_schedule_format(patient.get("call_schedule", "")),
            automated_call_category=patient.get("automated_call_category", "")
        )
        db.add(patient)
        db.commit()
        db.refresh(patient)
        db.close()
        return {"success": True, "patient_id": patient.id, "message": "Patient added via n8n"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/n8n/trigger_call")
async def n8n_trigger_call(call_data: dict):
    """Webhook endpoint for n8n to trigger outbound calls"""
    try:
        phone_number = call_data.get("phone_number")
        script = call_data.get("script", "")
        
        if not phone_number:
            return {"success": False, "error": "Phone number required"}
        
        # Use existing Twilio call function
        from twilio_call import make_call_and_play_script
        make_call_and_play_script(phone_number, script)
        
        return {"success": True, "message": f"Call initiated to {phone_number}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/n8n/trigger_sms")
async def n8n_trigger_sms(sms_data: dict):
    """Webhook endpoint for n8n to trigger SMS alerts"""
    try:
        phone_number = sms_data.get("phone_number")
        message = sms_data.get("message", "")
        
        if not phone_number:
            return {"success": False, "error": "Phone number required"}
        
        # Use existing SMS function
        from gsm import send_sms
        send_sms(phone_number, message)
        
        return {"success": True, "message": f"SMS sent to {phone_number}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/n8n/get_patients")
async def n8n_get_patients():
    """Webhook endpoint for n8n to get all patients"""
    try:
        db = SessionLocal()
        patients = db.query(Patient).all()
        db.close()
        
        patient_list = []
        for patient in patients:
                    patient_list.append({
            "id": patient.id,
            "name": patient.name,
            "diagnosis": patient.diagnosis,
            "phone": patient.phone,
            "description": patient.summary,
            "medication_schedule": patient.medication_schedule,
            "call_schedule": patient.call_schedule,
            "automated_call_category": patient.automated_call_category
        })
        
        return {"success": True, "patients": patient_list}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/n8n/get_call_queue")
async def n8n_get_call_queue():
    """Webhook endpoint for n8n to get today's call queue"""
    try:
        # Use existing call queue logic
        return get_call_queue()
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/n8n/inbound_call")
async def n8n_inbound_call(call_data: dict):
    """Webhook endpoint for n8n to handle inbound calls"""
    try:
        # Extract call data
        patient_name = call_data.get("patient_name", "")
        call_recording_url = call_data.get("recording_url", "")
        call_duration = call_data.get("duration", 0)
        
        # Process with AI (Gemma)
        ai_response = await process_with_gemma({
            "patient_name": patient_name,
            "recording_url": call_recording_url,
            "context": "inbound_call"
        })
        
        # Generate voice script
        voice_script = await generate_voice_script({
            "patient_name": patient_name,
            "medication_info": ai_response,
            "call_type": "reminder"
        })
        
        # Convert to speech
        audio_url = await convert_to_speech(voice_script)
        
        # Call back patient with AI response
        call_result = await call_back_patient(call_data.get("phone_number"), audio_url)
        
        return {
            "success": True,
            "ai_response": ai_response,
            "voice_script": voice_script,
            "audio_url": audio_url,
            "call_result": call_result
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/n8n/process_with_gemma")
async def n8n_process_with_gemma(data: dict):
    """Webhook endpoint for n8n to process data with MedGemma AI"""
    try:
        # Extract data from n8n
        patient_name = data.get("patient_name", "")
        question = data.get("question", "")
        context = data.get("context", "general")
        
        # Process with MedGemma (placeholder for actual AI integration)
        ai_response = await process_with_gemma({
            "patient_name": patient_name,
            "question": question,
            "context": context
        })
        
        return {
            "success": True,
            "ai_response": ai_response,
            "model": "MedGemma",
            "message": "Processed with MedGemma AI"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/n8n/generate_voice_script")
async def n8n_generate_voice_script(data: dict):
    """Webhook endpoint for n8n to generate voice scripts"""
    try:
        # Extract script data
        patient_name = data.get("patient_name", "")
        medication_info = data.get("medication_info", "")
        call_type = data.get("call_type", "reminder")
        
        # Generate voice script using RAG
        voice_script = await generate_voice_script({
            "patient_name": patient_name,
            "medication_info": medication_info,
            "call_type": call_type
        })
        
        return {
            "success": True,
            "voice_script": voice_script,
            "generated_at": datetime.now().isoformat()
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/n8n/convert_to_speech")
async def n8n_convert_to_speech(data: dict):
    """Webhook endpoint for n8n to convert text to speech"""
    try:
        text = data.get("text", "")
        voice = data.get("voice", "alice")
        
        # Convert text to speech
        audio_url = await convert_to_speech(text, voice)
        
        return {
            "success": True,
            "audio_url": audio_url,
            "converted_at": datetime.now().isoformat()
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

# Helper functions for AI processing
async def process_with_gemma(data: dict) -> str:
    """Process data with MedGemma AI model"""
    try:
        patient_name = data.get("patient_name", "Patient")
        question = data.get("question", "")
        context = data.get("context", "general")
        
        # Use actual MedGemma model for processing
        response = medgemma_ai.process_medical_query(question, patient_name, context)
        return response
        
    except Exception as e:
        return f"Hello {patient_name}, I'm having trouble processing your request. Please contact your healthcare provider for assistance."

async def generate_voice_script(data: dict) -> str:
    """Generate voice script using RAG system"""
    patient_name = data.get("patient_name", "")
    medication_info = data.get("medication_info", "")
    call_type = data.get("call_type", "reminder")
    
    if call_type == "reminder":
        return f"Hello {patient_name}, this is your medication reminder. {medication_info}. Please take your medication as prescribed."
    else:
        return f"Hello {patient_name}, this is your AI health assistant. {medication_info}"

async def convert_to_speech(text: str, voice: str = "alice") -> str:
    """Convert text to speech and return audio URL"""
    # Placeholder for TTS conversion
    # In real implementation, this would use a TTS service
    return f"https://example.com/audio/{hash(text)}.wav"

async def call_back_patient(phone_number: str, audio_url: str) -> dict:
    """Call back patient with AI response"""
    try:
        # Use existing Twilio call function
        from twilio_call import make_call_and_play_script
        make_call_and_play_script(phone_number, "Your AI assistant is calling you back.")
        
        return {"success": True, "message": f"Call back initiated to {phone_number}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

# AI Processing Functions
async def process_opd_paper(paper_text: str) -> dict:
    """
    Extract patient details from OPD paper using MedGemma AI
    """
    try:
        # Use actual MedGemma model for processing
        extracted_data = medgemma_ai.extract_medical_info(paper_text)
        
        return {
            "success": True,
            "extracted_data": extracted_data,
            "message": "OPD paper processed successfully with MedGemma"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

async def generate_ivr_schedule(gestational_age_weeks: int, patient_name: str, risk_factors: list = None, risk_category: str = "low", structured_medications: list = None) -> dict:
    """
    Generate IVR message schedule based on gestational age using MedGemma
    """
    try:
        # Use MedGemma to generate comprehensive IVR schedule with specific dates
        from datetime import datetime
        current_date = datetime.now()
        
        ivr_schedule = medgemma_ai.generate_comprehensive_ivr_schedule(
            gestational_age_weeks, 
            patient_name, 
            current_date,
            risk_factors or [],
            risk_category,
            structured_medications or []
        )
        
        return ivr_schedule
        
    except Exception as e:
        return {"success": False, "error": str(e)}

async def generate_voice_script_with_rag(topic: str, patient_name: str, gestational_age: int) -> str:
    """
    Generate voice script using MedGemma's medical knowledge base and guidelines
    """
    try:
        # Use actual MedGemma model for script generation
        script = medgemma_ai.generate_medical_script(topic, patient_name, gestational_age)
        return script
    except Exception as e:
        return f"Hello {patient_name}, this is your pregnancy health reminder. Please contact your healthcare provider for personalized advice."

async def process_inbound_call_with_gemma(patient_query: str, patient_name: str, recording_url: str = None) -> dict:
    """
    Process inbound call using multimodal MedGemma AI
    """
    try:
        # Use actual MedGemma model for processing
        ai_response = medgemma_ai.process_medical_query(patient_query, patient_name)
        
        # Determine urgency level based on query content
        query_lower = patient_query.lower()
        urgency_level = "medium"
        if any(word in query_lower for word in ["appointment", "nutrition", "general"]):
            urgency_level = "low"
        elif any(word in query_lower for word in ["pain", "bleeding", "emergency"]):
            urgency_level = "high"
        
        return {
            "success": True,
            "patient_query": patient_query,
            "ai_response": ai_response,
            "recommendation": "Contact healthcare provider if symptoms persist",
            "urgency_level": urgency_level
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "ai_response": f"Hello {patient_name}, I'm having trouble processing your request. Please contact your healthcare provider directly for assistance."
        }

@app.post("/register_patient_with_opd")
def register_patient_with_opd(opd_data: dict):
    """Register a new patient with OPD paper"""
    try:
        # Simple parsing for now to avoid coroutine issues
        opd_text = opd_data["opd_paper_text"]
        phone = opd_data.get("phone", "")
        
        # Extract basic information using regex
        import re
        
        # Extract patient name
        name_match = re.search(r"Patient:?\s*([A-Za-z\s]+?)(?:\n|,|$)", opd_text)
        patient_name = name_match.group(1).strip() if name_match else "Unknown Patient"
        
        # Extract gestational age
        ga_match = re.search(r"Gestational Age:\s*(\d+)\s*weeks?", opd_text)
        gestational_age = int(ga_match.group(1)) if ga_match else 0
        
        # Extract age
        age_match = re.search(r"Age:\s*(\d+)\s*years?", opd_text)
        age = int(age_match.group(1)) if age_match else 0
        
        # Extract race
        race_match = re.search(r"Race:\s*([A-Za-z\s]+?)(?:\n|$)", opd_text)
        race = race_match.group(1).strip() if race_match else ""
        
        # Extract height
        height_match = re.search(r"Height:\s*(\d+)\s*cm", opd_text)
        height = height_match.group(1) if height_match else ""
        
        # Extract weight
        weight_match = re.search(r"Weight:\s*(\d+)\s*kg", opd_text)
        weight = weight_match.group(1) if weight_match else ""
        
        # Extract medications
        med_match = re.search(r"Medications:\s*([^\n]+)", opd_text)
        medications = med_match.group(1).strip() if med_match else ""
        
        # Extract risk factors
        risk_match = re.search(r"Risk Factors:\s*([^\n]+)", opd_text)
        risk_factors = risk_match.group(1).strip() if risk_match else ""
        
        # Extract additional notes
        notes_match = re.search(r"Additional Notes:\s*([^\n]+)", opd_text)
        additional_notes = notes_match.group(1).strip() if notes_match else ""
        
        # Calculate BMI
        bmi = "0"
        if height and weight:
            try:
                height_m = float(height) / 100
                weight_kg = float(weight)
                bmi = str(round(weight_kg / (height_m * height_m), 1))
            except:
                bmi = "0"
        
        # Determine risk category based on BMI
        risk_category = "low"
        try:
            bmi_val = float(bmi)
            if bmi_val >= 30:
                risk_category = "high"
            elif bmi_val >= 25:
                risk_category = "medium"
        except:
            risk_category = "low"
        
        # Generate comprehensive IVR schedule using original MedGemma
        from datetime import datetime, timedelta
        
        # Use original MedGemma to generate proper IVR schedule
        current_date = datetime.now()
        structured_medications = opd_data.get("structured_medications", [])
        ivr_result = medgemma_ai.generate_comprehensive_ivr_schedule(
            gestational_age_weeks=gestational_age,
            patient_name=patient_name,
            current_date=current_date,
            risk_factors=risk_factors.split(', ') if risk_factors else [],
            risk_category=risk_category,
            structured_medications=structured_medications
        )
        
        # Extract the schedule from the result
        if isinstance(ivr_result, dict) and ivr_result.get("success"):
            ivr_schedule = ivr_result.get("schedule", [])
        else:
            # Fallback to basic schedule if MedGemma fails
            ivr_schedule = [
                {
                    "type": "medication_reminder",
                    "message": f"Hello {patient_name}, this is your medication reminder. Please take your medications as prescribed.",
                    "time": "09:00 AM"
                },
                {
                    "type": "appointment_reminder", 
                    "message": f"Hello {patient_name}, this is your appointment reminder. Please attend your scheduled prenatal visit.",
                    "time": "02:00 PM"
                }
            ]
        
        # Create patient record
        db = SessionLocal()
        patient = Patient(
            name=patient_name,
            diagnosis=f"Pregnancy - Week {gestational_age}",
            summary=f"Gestational Age: {gestational_age} weeks",
            phone=phone,
            medication_schedule=medications,
            call_schedule=ensure_call_schedule_format(ivr_schedule),
            automated_call_category="pregnancy_care",
            race=race,
            height=height,
            weight=weight,
            bmi=bmi,
            risk_category=risk_category,
            age=str(age),
            risk_factors=risk_factors,
            additional_notes=additional_notes
        )
        
        db.add(patient)
        db.commit()
        db.refresh(patient)
        db.close()
        
        return {
            "success": True,
            "patient_id": patient.id,
            "extracted_data": {
                "patient_name": patient_name,
                "gestational_age_weeks": gestational_age,
                "age": age,
                "race": race,
                "height": height,
                "weight": weight,
                "medications": medications,
                "risk_factors": risk_factors,
                "additional_notes": additional_notes
            },
            "ivr_schedule": ivr_schedule,
            "message": "Patient registered successfully"
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/generate_ivr_message")
async def generate_ivr_message(request_data: dict):
    """Generate personalized IVR message using enhanced fallback system"""
    try:
        patient_name = request_data.get("patient_name", "")
        topic = request_data.get("topic", "general")
        gestational_age_weeks = request_data.get("gestational_age_weeks", 0)
        risk_factors = request_data.get("risk_factors", [])
        patient_data = request_data.get("patient_data", {})
        
        # Use the enhanced fallback system for reliable quality
        message = fine_tuned_medgemma_ai.generate_personalized_ivr_message(
            patient_name, topic, gestational_age_weeks, risk_factors, patient_data=patient_data
        )
        
        return {
            "success": True,
            "message": message,
            "patient_name": patient_name,
            "topic": topic,
            "gestational_age_weeks": gestational_age_weeks,
            "word_count": len(message.split()),
            "model_used": "Google Gemma 2B with Enhanced Fallback"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/process_inbound_call")
async def process_inbound_call(call_data: dict):
    """Process inbound call with multimodal Gemma AI"""
    try:
        patient_name = call_data.get("patient_name", "")
        patient_query = call_data.get("patient_query", "")
        recording_url = call_data.get("recording_url", "")
        
        # Process with multimodal Gemma
        result = await process_inbound_call_with_gemma(patient_query, patient_name, recording_url)
        
        if result["success"]:
            # Generate voice script for response
            voice_script = await generate_voice_script_with_rag("general", patient_name, 0)
            
            # Convert to speech (simulated)
            audio_url = f"generated_audio_{patient_name}_{int(time.time())}.mp3"
            
            return {
                "success": True,
                "ai_analysis": result,
                "voice_script": voice_script,
                "audio_url": audio_url,
                "recommendation": result.get("recommendation", "Contact healthcare provider"),
                "urgency_level": result.get("urgency_level", "low")
            }
        else:
            return result
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/get_ivr_schedule/{patient_id}")
async def get_ivr_schedule(patient_id: int):
    """Get IVR schedule for a specific patient"""
    try:
        db = SessionLocal()
        patient = db.query(Patient).filter(Patient.id == patient_id).first()
        db.close()
        
        if not patient:
            return {"success": False, "error": "Patient not found"}
        
        # Parse the stored schedule
        try:
            import json
            stored_schedule = patient.call_schedule
            if isinstance(stored_schedule, str):
                parsed_schedule = json.loads(stored_schedule)
            else:
                parsed_schedule = stored_schedule
            
            return {
                "success": True,
                "patient_name": patient.name,
                "ivr_schedule": parsed_schedule,
                "total_calls": len(parsed_schedule) if isinstance(parsed_schedule, list) else 0
            }
        except (json.JSONDecodeError, TypeError):
            # If parsing fails, return empty schedule
            return {
                "success": True,
                "patient_name": patient.name,
                "ivr_schedule": [],
                "total_calls": 0
            }
            
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/generate_comprehensive_ivr_schedule")
async def generate_comprehensive_ivr_schedule(request_data: dict):
    """Generate comprehensive IVR schedule for a patient"""
    try:
        patient_name = request_data.get("patient_name", "")
        gestational_age_weeks = request_data.get("gestational_age_weeks", 0)
        risk_factors = request_data.get("risk_factors", [])
        risk_category = request_data.get("risk_category", "low")
        structured_medications = request_data.get("structured_medications", [])
        patient_data = request_data.get("patient_data", {})
        
        # Generate comprehensive IVR schedule using enhanced fallback
        schedule = fine_tuned_medgemma_ai.generate_comprehensive_ivr_schedule(
            gestational_age_weeks=gestational_age_weeks,
            patient_name=patient_name,
            risk_factors=risk_factors,
            risk_category=risk_category,
            structured_medications=structured_medications,
            patient_data=patient_data
        )
        
        return {
            "success": True,
            "schedule": schedule,
            "patient_name": patient_name,
            "total_calls": schedule.get("total_calls", 0),
            "risk_category": schedule.get("risk_category", "low")
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.put("/update_patient_with_ivr/{patient_id}")
async def update_patient_with_ivr(patient_id: int, patient_data: dict):
    """Update patient information and regenerate IVR schedule"""
    try:
        db = SessionLocal()
        patient = db.query(Patient).filter(Patient.id == patient_id).first()
        
        if not patient:
            return {"success": False, "error": "Patient not found"}
        
        # Update basic patient information
        patient.name = patient_data.get("name", patient.name)
        patient.phone = patient.get("phone", patient.phone)
        patient.race = patient.get("race", patient.race)
        patient.height = patient.get("height", patient.height)
        patient.weight = patient.get("weight", patient.weight)
        
        # Update diagnosis and description
        gestational_age = patient_data.get("gestational_age", 0)
        if gestational_age:
            patient.diagnosis = f"Pregnancy - Week {gestational_age}"
            patient.summary = f"Gestational Age: {gestational_age} weeks"
        
        # Update medication schedule
        if patient_data.get("medications"):
            patient.medication_schedule = patient_data["medications"]
        
        # Recalculate BMI and risk category
        bmi_risk_result = medgemma_ai.calculate_bmi_and_risk(
            patient_data.get("height", ""),
            patient_data.get("weight", ""),
            patient_data.get("age", 0),
            patient_data.get("risk_factors", []).split(",") if patient_data.get("risk_factors") else []
        )
        
        patient.bmi = str(bmi_risk_result["bmi"])
        patient.risk_category = bmi_risk_result["risk_category"]
        
        # Parse structured medications from the formatted string
        structured_medications = []
        if patient_data.get("medications"):
            med_lines = patient_data["medications"].split('\n')
            for line in med_lines:
                # Parse format: "Medication Name - Time AM/PM (Days)"
                match = re.match(r'([^-]+)\s*-\s*(\d{1,2})\s*(AM|PM)\s*\(([^)]+)\)', line)
                if match:
                    med_name = match.group(1).strip()
                    time = match.group(2)
                    ampm = match.group(3)
                    days = [day.strip() for day in match.group(4).split(', ')]
                    structured_medications.append({
                        "name": med_name,
                        "time": f"{time} {ampm}",
                        "days": days
                    })
        
        # Regenerate IVR schedule with updated information
        ivr_result = await generate_ivr_schedule(
            int(gestational_age) if gestational_age else 0,
            patient.name,
            patient_data.get("risk_factors", []).split(",") if patient_data.get("risk_factors") else [],
            patient.risk_category,
            structured_medications
        )
        
        if ivr_result["success"]:
            patient.call_schedule = ensure_call_schedule_format(ivr_result)
        
        db.commit()
        db.refresh(patient)
        db.close()
        
        logger.info(f"Updated IVR schedule for patient {patient_id}: {patient.call_schedule}")
        return {
            "success": True,
            "patient_id": patient.id,
            "ivr_schedule": patient.call_schedule,
            "message": "Patient updated with new IVR schedule"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/test_automated_call/{patient_id}")
async def test_automated_call(patient_id: int):
    """Test the automated call system using actual patient data"""
    try:
        # Get patient from database
        db = SessionLocal()
        patient = db.query(Patient).filter(Patient.id == patient_id).first()
        db.close()
        
        if not patient:
            return {"success": False, "error": "Patient not found"}
        
        # Create a test schedule item using patient's actual data
        test_schedule_item = {
            "topic": "Test call",
            "message": f"Hello {patient.name}, this is a test call from your healthcare system.",
            "time": "3:30 PM",
            "date": "2025-07-28"
        }
        
        success = automated_call_service.generate_and_send_ivr_call(patient_id, test_schedule_item)
        return {
            "success": success,
            "message": f"Automated call test completed for {patient.name}" if success else f"Automated call test failed for {patient.name}",
            "patient_name": patient.name,
            "patient_phone": patient.phone
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/voice-providers")
async def get_voice_providers():
    """Get available voice providers and their settings"""
    from voice_config import voice_config
    
    available_providers = voice_config.get_available_providers()
    best_provider = voice_config.get_best_provider()
    
    return {
        "available_providers": available_providers,
        "best_provider": best_provider,
        "voice_settings": {
            provider: voice_config.get_voice_settings(provider) 
            for provider in available_providers
        },
        "api_keys_configured": {
            "azure": bool(voice_config.get_api_key("azure")),
            "elevenlabs": bool(voice_config.get_api_key("elevenlabs"))
        }
    }

@app.post("/test-voice-quality")
async def test_voice_quality(provider: str = "google"):
    """Test voice quality with a sample medical message"""
    try:
        from tts_service import tts_service
        
        test_message = "Hello, this is a test of the voice quality system. This message contains important medical information about your pregnancy care. Please contact your healthcare provider if you have any concerns."
        
        # Test the specified provider
        audio_file = None
        if provider == "azure":
            audio_file = tts_service.text_to_speech_azure(test_message, "test_voice.wav")
        elif provider == "elevenlabs":
            audio_file = tts_service.text_to_speech_elevenlabs(test_message, "test_voice.mp3")
        else:
            audio_file = tts_service.text_to_speech_google(test_message, "test_voice.mp3")
        
        if audio_file:
            return {
                "success": True,
                "provider": provider,
                "audio_file": audio_file,
                "message": f"Voice test completed using {provider}"
            }
        else:
            return {
                "success": False,
                "provider": provider,
                "error": f"Failed to generate audio with {provider}"
            }
            
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/patient-rag-data/{patient_id}")
async def get_patient_rag_data(patient_id: int):
    """Get RAG embeddings and medical context for a patient"""
    try:
        db = SessionLocal()
        patient = db.query(Patient).filter(Patient.id == patient_id).first()
        db.close()
        
        if not patient:
            return {"success": False, "error": "Patient not found"}
        
        # Check if RAG data exists
        has_rag_data = (
            patient.medical_context is not None and 
            patient.rag_embeddings is not None and 
            patient.medical_guidelines is not None
        )
        
        return {
            "success": True,
            "patient_name": patient.name,
            "has_rag_data": has_rag_data,
            "rag_embeddings": {
                "count": len(patient.rag_embeddings) if patient.rag_embeddings else 0,
                "types": list(patient.rag_embeddings.keys()) if patient.rag_embeddings else []
            },
            "medical_context": {
                "patient_info": patient.medical_context.get("patient_info", {}) if patient.medical_context else {},
                "medical_data": patient.medical_context.get("medical_data", {}) if patient.medical_context else {},
                "last_updated": patient.medical_context.get("last_updated", "") if patient.medical_context else ""
            },
            "medical_guidelines": {
                "count": len(patient.medical_guidelines) if patient.medical_guidelines else 0,
                "types": list(patient.medical_guidelines.keys()) if patient.medical_guidelines else []
            }
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/update-patient-rag/{patient_id}")
async def update_patient_rag(patient_id: int):
    """Update RAG embeddings and medical context for an existing patient"""
    try:
        db = SessionLocal()
        patient = db.query(Patient).filter(Patient.id == patient_id).first()
        db.close()
        
        if not patient:
            return {"success": False, "error": "Patient not found"}
        
        # Create patient data dictionary
        patient_data = {
            "name": patient.name,
            "diagnosis": patient.diagnosis,
            "summary": patient.summary,
            "phone": patient.phone,
            "medication_schedule": patient.medication_schedule,
            "race": patient.race,
            "height": patient.height,
            "weight": patient.weight,
            "bmi": patient.bmi,
            "risk_category": patient.risk_category,
            "age": patient.age,
            "risk_factors": patient.risk_factors,
            "additional_notes": patient.additional_notes
        }
        
        # Generate new RAG embeddings and medical context
        rag_embeddings = rag_service.generate_patient_embeddings(patient_data)
        medical_context = rag_service.create_patient_medical_context(patient_data)
        medical_guidelines = {
            "relevant_guidelines": rag_service.get_relevant_guidelines_for_patient(patient_data),
            "risk_specific_guidelines": rag_service.get_relevant_guidelines("pregnancy", patient.risk_factors.split(", ") if patient.risk_factors else []),
            "medication_guidelines": rag_service.get_relevant_guidelines("medication", patient.risk_factors.split(", ") if patient.risk_factors else [])
        }
        
        # Update patient record with new RAG data
        db = SessionLocal()
        patient.medical_context = medical_context
        patient.rag_embeddings = rag_embeddings
        patient.medical_guidelines = medical_guidelines
        patient.updated_at = datetime.now()
        
        db.commit()
        db.close()
        
        return {
            "success": True,
            "patient_name": patient.name,
            "rag_data": {
                "embeddings_generated": len(rag_embeddings),
                "medical_context_updated": True,
                "guidelines_stored": len(medical_guidelines)
            },
            "message": "Patient RAG data updated successfully"
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/generate-pregnancy-rag-database")
async def generate_pregnancy_rag_database():
    """Generate comprehensive pregnancy care RAG database using MedGemma"""
    try:
        # Generate embeddings for the pregnancy knowledge base
        pregnancy_rag_db.generate_medgemma_embeddings()
        
        # Get database statistics
        stats = pregnancy_rag_db.get_database_stats()
        
        return {
            "success": True,
            "message": "Pregnancy RAG database generated successfully",
            "database_stats": stats
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/pregnancy-rag-stats")
async def get_pregnancy_rag_stats():
    """Get statistics about the pregnancy RAG database"""
    try:
        stats = pregnancy_rag_db.get_database_stats()
        return {
            "success": True,
            "database_stats": stats
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/query-pregnancy-rag")
async def query_pregnancy_rag(query: str, patient_id: int = None):
    """Query the pregnancy RAG database with personalized response using MedGemma-generated knowledge"""
    try:
        patient_context = None
        
        # Get patient context if patient_id provided
        if patient_id:
            db = SessionLocal()
            patient = db.query(Patient).filter(Patient.id == patient_id).first()
            db.close()
            
            if patient:
                patient_context = {
                    "name": patient.name,
                    "diagnosis": patient.diagnosis,
                    "risk_factors": patient.risk_factors,
                    "medication_schedule": patient.medication_schedule,
                    "risk_category": patient.risk_category,
                    "age": patient.age,
                    "bmi": patient.bmi
                }
        
        # Generate personalized response using RAG and MedGemma
        response = pregnancy_rag_db.generate_personalized_response(query, patient_context)
        
        # Find relevant knowledge for context
        relevant_knowledge = pregnancy_rag_db.find_relevant_knowledge(query, patient_context)
        
        return {
            "success": True,
            "query": query,
            "response": response,
            "relevant_knowledge": relevant_knowledge[:3],  # Top 3 most relevant
            "patient_context": patient_context,
            "database_source": "MedGemma-generated pregnancy care knowledge base"
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/test-pregnancy-rag")
async def test_pregnancy_rag():
    """Test the pregnancy RAG system with sample queries"""
    try:
        test_queries = [
            "What should I eat during pregnancy?",
            "Is it safe to exercise while pregnant?",
            "What are the symptoms of preeclampsia?",
            "How should I manage gestational diabetes?",
            "What medications are safe during pregnancy?"
        ]
        
        results = []
        for query in test_queries:
            response = pregnancy_rag_db.generate_personalized_response(query, None)
            relevant_knowledge = pregnancy_rag_db.find_relevant_knowledge(query, None)
            
            results.append({
                "query": query,
                "response": response,
                "relevant_knowledge_count": len(relevant_knowledge)
            })
        
        return {
            "success": True,
            "test_results": results,
            "total_queries": len(test_queries)
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/prepare-fine-tuning-data")
async def prepare_fine_tuning_data():
    """Prepare training data from pregnancy care database for fine-tuning"""
    try:
        # Prepare training data from the pregnancy care database
        training_examples = gemma_fine_tuner.prepare_training_data()
        
        # Format data for training
        formatted_data = gemma_fine_tuner.format_for_training(training_examples)
        
        return {
            "success": True,
            "training_examples": len(training_examples),
            "formatted_examples": len(formatted_data),
            "message": "Training data prepared successfully for fine-tuning"
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/fine-tune-gemma")
async def fine_tune_gemma():
    """Fine-tune Gemma model using pregnancy care database"""
    try:
        # Prepare training data
        training_examples = gemma_fine_tuner.prepare_training_data()
        formatted_data = gemma_fine_tuner.format_for_training(training_examples)
        
        # Load model and tokenizer
        gemma_fine_tuner.load_model_and_tokenizer()
        
        # Prepare dataset
        dataset = gemma_fine_tuner.prepare_dataset(formatted_data)
        
        # Fine-tune the model
        gemma_fine_tuner.fine_tune_model(dataset)
        
        return {
            "success": True,
            "message": "Gemma model fine-tuned successfully on pregnancy care data",
            "training_examples": len(training_examples),
            "model_path": gemma_fine_tuner.fine_tuned_model_path
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/test-fine-tuned-model")
async def test_fine_tuned_model():
    """Test the fine-tuned model with sample queries"""
    try:
        test_queries = [
            "What should I eat during pregnancy if I have gestational diabetes?",
            "What are the warning signs of preeclampsia?",
            "Is it safe to exercise during the third trimester?",
            "What medications are safe during pregnancy?",
            "How should I monitor fetal movements?"
        ]
        
        # Compare base model vs fine-tuned model
        comparison_results = gemma_fine_tuner.compare_responses(test_queries)
        
        return {
            "success": True,
            "comparison_results": comparison_results,
            "test_queries": test_queries
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/use-fine-tuned-model")
async def use_fine_tuned_model(query: str, patient_id: int = None):
    """Use the fine-tuned model for pregnancy care patient inquiries only"""
    try:
        # Get patient context if patient_id is provided
        patient_context = ""
        patient_name = ""
        if patient_id:
            db = SessionLocal()
            patient = db.query(Patient).filter(Patient.id == patient_id).first()
            db.close()
            if patient:
                patient_context = f"Patient: {patient.name}, Diagnosis: {patient.diagnosis}"
                patient_name = patient.name
        
        # Use fine-tuned model for patient inquiries only
        response = fine_tuned_medgemma.process_medical_query(query, patient_name, patient_context)
        
        return {
            "success": True,
            "query": query,
            "response": response,
            "model": "fine_tuned_pregnancy_medgemma",
            "usage": "patient_inquiries_only"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/call-statistics")
def get_call_statistics():
    """Get call statistics and delivery rates"""
    try:
        stats = twilio_call_service.get_call_statistics()
        scheduler_status = enhanced_scheduler.get_scheduler_status()
        
        return {
            "call_statistics": stats,
            "scheduler_status": scheduler_status,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/call-history")
def get_call_history(phone_number: str = None, limit: int = 50):
    """Get call history with optional phone number filter"""
    try:
        history = twilio_call_service.get_call_history(phone_number, limit)
        return {
            "call_history": history,
            "total_calls": len(history),
            "phone_number": phone_number
        }
    except Exception as e:
        return {"error": str(e)}

@app.post("/schedule-immediate-call")
def schedule_immediate_call(patient_id: int, message: str, call_type: str = "ivr"):
    """Schedule an immediate call for a patient"""
    try:
        enhanced_scheduler.schedule_immediate_call(patient_id, message, call_type)
        return {
            "success": True,
            "message": f"Immediate call scheduled for patient {patient_id}",
            "call_type": call_type
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/scheduler-status")
def get_scheduler_status():
    """Get enhanced scheduler status"""
    return enhanced_scheduler.get_scheduler_status()

@app.get("/scheduled-calls-summary")
def get_scheduled_calls_summary():
    """Get comprehensive summary of all scheduled IVR calls"""
    return enhanced_scheduler.get_scheduled_calls_summary()

@app.get("/upcoming-calls-summary")
def get_upcoming_calls_summary(days_ahead: int = 7):
    """Get summary of upcoming calls for the next N days"""
    return enhanced_scheduler.get_upcoming_calls_summary(days_ahead)

@app.post("/test-tts")
def test_tts(text: str, language: str = "en", provider: str = None):
    """Test TTS service with different providers"""
    try:
        if provider == "azure":
            audio_file = tts_service.text_to_speech_azure(text, language=language)
        elif provider == "elevenlabs":
            audio_file = tts_service.text_to_speech_elevenlabs(text)
        elif provider == "google":
            audio_file = tts_service.text_to_speech_google(text, language=language)
        else:
            audio_file = tts_service.text_to_speech(text, language=language)
        
        if audio_file:
            return {
                "success": True,
                "audio_file": audio_file,
                "provider": provider or "auto",
                "language": language
            }
        else:
            return {"error": "Failed to generate audio"}
            
    except Exception as e:
        return {"error": str(e)}

@app.post("/test-call")
def test_call(phone_number: str, message: str, call_type: str = "ivr"):
    """Test endpoint to demonstrate TwiML generation with Press 1 functionality"""
    try:
        from twilio_call import TwilioCallService
        
        twilio_service = TwilioCallService()
        
        # Generate TwiML with message option
        twiml = twilio_service.create_twiml_with_message_option(message)
        
        # For testing, we'll return the TwiML instead of making an actual call
        return {
            "success": True,
            "message": "Test call TwiML generated successfully",
            "twiml": twiml,
            "phone_number": phone_number,
            "call_type": call_type
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/test-twiml")
def test_twiml():
    """Test endpoint to show sample TwiML with Press 1 functionality"""
    try:
        from twilio_call import TwilioCallService
        
        twilio_service = TwilioCallService()
        
        # Generate sample TwiML
        sample_twiml = twilio_service.create_twiml_with_message_option(
            "Hello Sarah Johnson, this is your medication reminder. Please take your medication as prescribed."
        )
        
        return {
            "success": True,
            "twiml": sample_twiml,
            "description": "Sample TwiML with Press 1 functionality"
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}

# Initialize fine-tuned model (temporarily disabled due to loading issues)
# fine_tuned_medgemma = FineTunedMedGemma()
# fine_tuned_medgemma.load_fine_tuned_model()

# Use a simple mock for now
class MockFineTunedMedGemma:
    def process_medical_query(self, query: str, patient_name: str = "", context: str = "") -> str:
        return f"AI Response: {query} - Please consult your healthcare provider for personalized advice."

fine_tuned_medgemma = MockFineTunedMedGemma()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

# Patient Metrics and Postnatal Care Endpoints

@app.post("/patients/{patient_id}/delivery")
def update_delivery_info(patient_id: int, delivery_data: dict = Body(...)):
    db = SessionLocal()
    try:
        patient = db.query(Patient).filter(Patient.id == patient_id).first()
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")
        delivery_date_str = delivery_data.get("delivery_date")
        delivery_type = delivery_data.get("delivery_type", "vaginal")
        if delivery_date_str:
            delivery_date = datetime.fromisoformat(delivery_date_str)
            patient.delivery_date = delivery_date
            patient.delivery_type = delivery_type
            patient.is_postpartum = True
            patient.postpartum_week = max(0, (datetime.now() - delivery_date).days // 7)
            # Generate postnatal care schedule
            postnatal_schedule = medgemma_ai.generate_postnatal_care_schedule(
                patient_name=patient.name,
                delivery_date=delivery_date,
                delivery_type=delivery_type
            )
            patient.postnatal_care_schedule = ensure_call_schedule_format(postnatal_schedule.get("schedule", []))
            # Merge with existing schedule
            try:
                existing_schedule = patient.call_schedule
                if isinstance(existing_schedule, str):
                    existing_schedule = json.loads(existing_schedule)
                if not isinstance(existing_schedule, dict):
                    existing_schedule = existing_schedule.get("schedule", [])
            except:
                existing_schedule = []
            merged_schedule = existing_schedule + postnatal_schedule.get("schedule", [])
            patient.call_schedule = ensure_call_schedule_format(merged_schedule)
        db.commit()
        return {"success": True, "delivery_date": delivery_date_str, "delivery_type": delivery_type}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.get("/patients/{patient_id}/metrics")
def get_patient_metrics(patient_id: int):
    """Get patient call metrics and success rates"""
    db = SessionLocal()
    try:
        patient = db.query(Patient).filter(Patient.id == patient_id).first()
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")
        
        # Calculate success rate
        total_calls = patient.total_calls_scheduled or 0
        completed_calls = patient.total_calls_completed or 0
        failed_calls = patient.total_calls_failed or 0
        missed_calls = patient.total_calls_missed or 0
        
        success_rate = 0
        if total_calls > 0:
            success_rate = (completed_calls / total_calls) * 100
        
        # Parse call history
        call_history = []
        if patient.call_history:
            try:
                call_history = json.loads(patient.call_history) if isinstance(patient.call_history, str) else patient.call_history
            except:
                call_history = []
        
        metrics = {
            "patient_id": patient.id,
            "patient_name": patient.name,
            "total_calls_scheduled": total_calls,
            "total_calls_completed": completed_calls,
            "total_calls_failed": failed_calls,
            "total_calls_missed": missed_calls,
            "call_success_rate": round(success_rate, 2),
            "average_call_duration": patient.average_call_duration or 0,
            "total_call_duration": patient.total_call_duration or 0,
            "last_call_date": patient.last_call_date.isoformat() if patient.last_call_date else None,
            "last_call_status": patient.last_call_status,
            "call_history": call_history,
            "is_postpartum": patient.is_postpartum,
            "postpartum_week": patient.postpartum_week,
            "delivery_date": patient.delivery_date.isoformat() if patient.delivery_date else None,
            "delivery_type": patient.delivery_type
        }
        
        return metrics
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.post("/patients/{patient_id}/call-result")
def update_call_result(patient_id: int, call_result: dict = Body(...)):
    """Update patient metrics after a call attempt"""
    db = SessionLocal()
    try:
        patient = db.query(Patient).filter(Patient.id == patient_id).first()
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")
        
        status = call_result.get("status")  # completed, failed, missed
        duration = call_result.get("duration", 0)  # in seconds
        call_date = datetime.now()
        
        # Update call counts
        patient.total_calls_scheduled = (patient.total_calls_scheduled or 0) + 1
        
        if status == "completed":
            patient.total_calls_completed = (patient.total_calls_completed or 0) + 1
        elif status == "failed":
            patient.total_calls_failed = (patient.total_calls_failed or 0) + 1
        elif status == "missed":
            patient.total_calls_missed = (patient.total_calls_missed or 0) + 1
        
        # Update duration metrics
        if duration > 0:
            current_total = patient.total_call_duration or 0
            current_avg = patient.average_call_duration or 0
            completed_calls = patient.total_calls_completed or 0
            
            new_total = current_total + duration
            patient.total_call_duration = new_total
            
            if completed_calls > 0:
                patient.average_call_duration = new_total / completed_calls
        
        # Update last call info
        patient.last_call_date = call_date
        patient.last_call_status = status
        
        # Update call history
        call_history = []
        if patient.call_history:
            try:
                call_history = json.loads(patient.call_history) if isinstance(patient.call_history, str) else patient.call_history
            except:
                call_history = []
        
        call_record = {
            "date": call_date.isoformat(),
            "status": status,
            "duration": duration,
            "message": call_result.get("message", "")
        }
        call_history.append(call_record)
        patient.call_history = json.dumps(call_history)
        
        # Calculate new success rate
        total_calls = patient.total_calls_scheduled
        completed_calls = patient.total_calls_completed
        if total_calls > 0:
            patient.call_success_rate = (completed_calls / total_calls) * 100
        
        db.commit()
        
        return {
            "success": True,
            "message": f"Call result updated: {status}",
            "new_metrics": {
                "total_calls_scheduled": patient.total_calls_scheduled,
                "total_calls_completed": patient.total_calls_completed,
                "call_success_rate": round(patient.call_success_rate, 2),
                "average_call_duration": patient.average_call_duration
            }
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.get("/postnatal-patients")
def get_postnatal_patients():
    """Get all patients currently in postnatal care period"""
    db = SessionLocal()
    try:
        postnatal_patients = db.query(Patient).filter(
            Patient.is_postpartum == True
        ).all()
        
        patients_data = []
        for patient in postnatal_patients:
            patients_data.append({
                "id": patient.id,
                "name": patient.name,
                "delivery_date": patient.delivery_date.isoformat() if patient.delivery_date else None,
                "delivery_type": patient.delivery_type,
                "postpartum_week": patient.postpartum_week,
                "phone": patient.phone,
                "last_call_date": patient.last_call_date.isoformat() if patient.last_call_date else None,
                "call_success_rate": patient.call_success_rate
            })
        
        return {
            "total_postnatal_patients": len(patients_data),
            "patients": patients_data
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.post("/patients/{patient_id}/postnatal-message")
def generate_postnatal_message(patient_id: int, message_request: dict = Body(...)):
    """Generate a specific postnatal care message"""
    db = SessionLocal()
    try:
        patient = db.query(Patient).filter(Patient.id == patient_id).first()
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")
        
        if not patient.is_postpartum:
            raise HTTPException(status_code=400, detail="Patient is not in postnatal care period")
        
        topic = message_request.get("topic", "general")
        postpartum_week = patient.postpartum_week or 1
        delivery_type = patient.delivery_type or "vaginal"
        
        message = medgemma_ai.generate_postnatal_medical_script(
            topic=topic,
            patient_name=patient.name,
            postpartum_week=postpartum_week,
            delivery_type=delivery_type
        )
        
        return {
            "success": True,
            "message": message,
            "topic": topic,
            "postpartum_week": postpartum_week,
            "delivery_type": delivery_type
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.post("/patients/{patient_id}/regenerate-schedule")
async def regenerate_patient_schedule(patient_id: int):
    """Regenerate IVR schedule for an existing patient with medication reminders"""
    try:
        db = SessionLocal()
        patient = db.query(Patient).filter(Patient.id == patient_id).first()
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")
        
        # Parse structured medications from the patient's medications field
        structured_medications = []
        if patient.medication_schedule:
            try:
                # Try to parse as JSON first
                structured_medications = json.loads(patient.medication_schedule)
            except:
                # If not JSON, try to parse as string
                if patient.medication_schedule.strip():
                    structured_medications = [{"name": patient.medication_schedule, "dosage": "as prescribed", "time": "9:00 AM", "days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]}]
        
        # Generate new comprehensive IVR schedule
        ivr_schedule = medgemma_ai.generate_comprehensive_ivr_schedule(
            patient_name=patient.name,
            gestational_age=patient.gestational_age,
            risk_category=patient.risk_category,
            structured_medications=structured_medications,
            is_postpartum=patient.is_postpartum,
            postpartum_week=patient.postpartum_week
        )
        
        # Update the patient's call schedule
        patient.call_schedule = ensure_call_schedule_format(ivr_schedule)
        db.commit()
        
        return {"message": "IVR schedule regenerated successfully", "schedule": patient.call_schedule}
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error regenerating schedule for patient {patient_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to regenerate schedule: {str(e)}")
    finally:
        db.close()

@app.put("/patients/{patient_id}/ivr-schedule")
def update_ivr_schedule_time(patient_id: int, schedule_update: Union[List, Dict] = Body(...)):
    """Update the patient's IVR schedule (expects a list of schedule items)"""
    db = SessionLocal()
    try:
        patient = db.query(Patient).filter(Patient.id == patient_id).first()
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")
        
        if not patient.call_schedule:
            raise HTTPException(status_code=400, detail="No IVR schedule found for this patient")
        
        # Handle both direct array and wrapped object formats
        new_schedule = None
        if isinstance(schedule_update, list):
            # Direct array format
            new_schedule = schedule_update
        elif isinstance(schedule_update, dict):
            # Wrapped object format
            new_schedule = schedule_update.get("schedule", schedule_update)
        
        if not isinstance(new_schedule, list):
            raise HTTPException(status_code=400, detail="IVR schedule must be a list of schedule items")
        
        # Save the new schedule
        patient.call_schedule = ensure_call_schedule_format(new_schedule)
        db.commit()
        logger.info(f"Updated IVR schedule for patient {patient_id}: {patient.call_schedule}")
        return {"success": True, "call_schedule": patient.call_schedule}
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating IVR schedule for patient {patient_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update IVR schedule: {str(e)}")
    finally:
        db.close()

@app.get("/patients/{patient_id}/messages")
def get_patient_messages(patient_id: int):
    """Get all messages for a specific patient"""
    try:
        db = SessionLocal()
        messages = db.query(PatientMessage).filter(PatientMessage.patient_id == patient_id).order_by(PatientMessage.created_at.desc()).all()
        
        message_list = []
        for msg in messages:
            message_list.append({
                "id": msg.id,
                "message_text": msg.message_text,
                "message_type": msg.message_type,
                "recording_url": msg.recording_url,
                "processed_response": msg.processed_response,
                "gemma_response": msg.gemma_response,
                "scheduled_callback": msg.scheduled_callback.isoformat() if msg.scheduled_callback else None,
                "callback_message": msg.callback_message,
                "status": msg.status,
                "created_at": msg.created_at.isoformat(),
                "processed_at": msg.processed_at.isoformat() if msg.processed_at else None,
                "callback_completed_at": msg.callback_completed_at.isoformat() if msg.callback_completed_at else None
            })
        
        db.close()
        return {"success": True, "messages": message_list}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/messages/pending")
def get_pending_messages():
    """Get all pending messages that need processing"""
    try:
        db = SessionLocal()
        messages = db.query(PatientMessage).filter(PatientMessage.status == "pending").order_by(PatientMessage.created_at.desc()).all()
        
        message_list = []
        for msg in messages:
            patient = db.query(Patient).filter(Patient.id == msg.patient_id).first()
            message_list.append({
                "id": msg.id,
                "patient_id": msg.patient_id,
                "patient_name": patient.name if patient else "Unknown",
                "patient_phone": patient.phone if patient else "",
                "message_text": msg.message_text,
                "recording_url": msg.recording_url,
                "created_at": msg.created_at.isoformat()
            })
        
        db.close()
        return {"success": True, "messages": message_list}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/messages/{message_id}/process")
def process_pending_message(message_id: int):
    """Manually process a pending message and schedule callback"""
    try:
        db = SessionLocal()
        message = db.query(PatientMessage).filter(PatientMessage.id == message_id).first()
        
        if not message:
            return {"error": "Message not found"}
        
        if message.status != "pending":
            return {"error": f"Message is already {message.status}"}
        
        # Process with Gemma AI
        from medgemma_fine_tuned import fine_tuned_medgemma_ai
        
        patient = db.query(Patient).filter(Patient.id == message.patient_id).first()
        if not patient:
            return {"error": "Patient not found"}
        
        # Generate response
        gemma_response = fine_tuned_medgemma_ai.generate_personalized_ivr_message(
            topic="patient_message_response",
            patient_name=patient.name,
            gestational_age_weeks=20,
            risk_factors=patient.risk_factors.split(', ') if patient.risk_factors else [],
            risk_category=patient.risk_category or "low"
        )
        
        # Extract message from response (it returns a dict)
        if isinstance(gemma_response, dict):
            gemma_message = gemma_response.get('message', 'Thank you for your message.')
        else:
            gemma_message = str(gemma_response)
        
        # Schedule callback for tomorrow
        from datetime import datetime, timedelta
        tomorrow = datetime.now() + timedelta(days=1)
        callback_message = f"About your question yesterday on {datetime.now().strftime('%B %d')}, {gemma_message}"
        
        # Update message
        message.processed_response = callback_message
        message.gemma_response = str(gemma_response)  # Convert dict to string for database
        message.scheduled_callback = tomorrow
        message.callback_message = callback_message
        message.status = "scheduled"
        message.processed_at = datetime.now()
        
        db.commit()
        
        return {
            "success": True,
            "message": "Message processed and callback scheduled",
            "callback_message": callback_message,
            "scheduled_for": tomorrow.isoformat()
        }
        
    except Exception as e:
        return {"error": str(e)}
    finally:
        db.close()
