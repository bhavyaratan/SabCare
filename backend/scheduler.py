import logging
import json
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
from db import SessionLocal, Patient
from automated_calls import automated_call_service
from typing import Dict, Any, List, Optional
import threading
import time
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class CallPriority(Enum):
    URGENT = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4

@dataclass
class ScheduledCall:
    """Data class for scheduled call information"""
    patient_id: int
    patient_name: str
    phone_number: str
    message: str
    scheduled_date: datetime
    scheduled_time: str
    call_type: str = "ivr"
    priority: CallPriority = CallPriority.MEDIUM
    retry_count: int = 0
    topic: str = ""
    week_number: Optional[int] = None
    risk_level: Optional[str] = None

class EnhancedScheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.call_queue = []  # Queue for pending calls
        self.scheduled_calls = []  # All scheduled calls for the day
        self.failed_calls = {}  # Track failed calls for retry
        self.max_retries = 3
        self.retry_delay = 300  # 5 minutes
        self.missed_call_retry_delay = 1800  # 30 minutes
        
        # Configure scheduler
        self.scheduler.add_listener(self._job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)
        
        # Start background thread for call processing
        self.call_processor_thread = threading.Thread(target=self._process_call_queue, daemon=True)
        self.call_processor_thread.start()
    
    def _job_listener(self, event):
        """Handle job execution events"""
        if hasattr(event, 'exception'):
            logger.error(f"Job failed: {event.exception}")
        else:
            logger.info(f"Job completed successfully: {event.job_id}")
    
    def start_scheduler(self):
        """Start the enhanced scheduler with multiple job types"""
        try:
            # Add call scheduler job (runs every 5 minutes to fetch all scheduled calls)
            self.scheduler.add_job(
                self.fetch_all_scheduled_calls_job,
                'interval',
                minutes=5,
                id='fetch_scheduled_calls_job',
                name='Fetch all scheduled IVR calls'
            )
            
            # Add medication reminder job (runs every minute to process current calls)
            self.scheduler.add_job(
                self.medication_reminder_job,
                'interval',
                minutes=1,
                id='medication_reminder_job',
                name='Process current IVR calls'
            )
            
            # Add call queue processor job (runs every 30 seconds)
            self.scheduler.add_job(
                self._process_call_queue_job,
                'interval',
                seconds=30,
                id='call_queue_processor',
                name='Process call queue'
            )
            
            # Add failed call retry job (runs every 5 minutes)
            self.scheduler.add_job(
                self._retry_failed_calls_job,
                'interval',
                minutes=5,
                id='failed_call_retry',
                name='Retry failed calls'
            )
            
            # Add missed call handler job (runs every 30 minutes)
            self.scheduler.add_job(
                self._handle_missed_calls_job,
                'interval',
                minutes=30,
                id='missed_call_handler',
                name='Handle missed calls'
            )
            
            # Add daily statistics job (runs at midnight)
            self.scheduler.add_job(
                self._daily_statistics_job,
                'cron',
                hour=0,
                minute=0,
                id='daily_statistics',
                name='Generate daily call statistics'
            )
            
            # Add callback processor job (runs every 10 minutes)
            self.scheduler.add_job(
                self._process_callbacks_job,
                'interval',
                minutes=10,
                id='callback_processor',
                name='Process pending callbacks'
            )
            
            self.scheduler.start()
            logger.info("Enhanced scheduler started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start scheduler: {e}")
    
    def fetch_all_scheduled_calls_job(self):
        """Job to fetch all scheduled calls from all patients"""
        try:
            logger.info("Fetching all scheduled calls from database...")
            current_date = datetime.now().date()
            logger.info(f"Current date: {current_date}")
            
            # Clear existing scheduled calls
            self.scheduled_calls.clear()
            logger.info("Cleared existing scheduled calls")
            
            # Get all patients from database
            db = SessionLocal()
            try:
                patients = db.query(Patient).all()
                logger.info(f"Found {len(patients)} patients to process")
                
                for patient in patients:
                    logger.info(f"Processing patient: {patient.name} (ID: {patient.id})")
                    logger.info(f"Patient has call schedule: {bool(patient.call_schedule)}")
                    
                    # Replace all patient.call_schedule with patient.call_schedule
                    # When parsing schedule, do:
                    if isinstance(patient.call_schedule, str):
                        try:
                            schedule_data = json.loads(patient.call_schedule)
                        except Exception:
                            schedule_data = []
                    else:
                        schedule_data = patient.call_schedule
                    if isinstance(schedule_data, list):
                        schedule = schedule_data
                    elif isinstance(schedule_data, dict):
                        schedule = schedule_data.get("schedule", [])
                    else:
                        schedule = []
                    
                    if patient.call_schedule:
                        logger.info(f"Call schedule length: {len(schedule)}")
                    
                    self._fetch_patient_scheduled_calls(patient, current_date)
                
                # Sort scheduled calls by date and time
                self._sort_scheduled_calls()
                
                logger.info(f"Fetched {len(self.scheduled_calls)} scheduled calls for the next 7 days")
                
                # Log some details about the fetched calls
                for i, call in enumerate(self.scheduled_calls[:5], 1):
                    logger.info(f"Call {i}: {call.patient_name} on {call.scheduled_date} at {call.scheduled_time}")
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error in fetch_all_scheduled_calls_job: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
    
    def _fetch_patient_scheduled_calls(self, patient, current_date):
        """Fetch all scheduled calls for a single patient for the next 7 days"""
        try:
            if not patient.call_schedule:
                logger.info(f"No call schedule for patient {patient.name}")
                return
            
            # Replace all patient.call_schedule with patient.call_schedule
            # When parsing schedule, do:
            if isinstance(patient.call_schedule, str):
                try:
                    schedule_data = json.loads(patient.call_schedule)
                except Exception:
                    schedule_data = []
            else:
                schedule_data = patient.call_schedule
            if isinstance(schedule_data, list):
                schedule = schedule_data
            elif isinstance(schedule_data, dict):
                schedule = schedule_data.get("schedule", [])
            else:
                schedule = []
            
            logger.info(f"Parsed schedule for {patient.name}: {len(schedule)} items")
            
            # Check calls for the next 7 days
            for days_ahead in range(7):
                check_date = current_date + timedelta(days=days_ahead)
                logger.info(f"Checking date: {check_date} (day {days_ahead})")
                
                for item in schedule:
                    try:
                        # Check if item has required fields
                        if "date" not in item or "time" not in item or "message" not in item:
                            logger.warning(f"Skipping incomplete schedule item for {patient.name}: missing required fields")
                            continue
                        
                        # Parse date and time
                        if isinstance(item["date"], str):
                            item_date = datetime.strptime(item["date"], "%Y-%m-%d").date()
                        else:
                            item_date = item["date"].date()
                        
                        logger.info(f"Schedule item date: {item_date}, checking against: {check_date}")
                        
                        # Check if this is the date we're looking for
                        if item_date == check_date:
                            logger.info(f"✅ Found matching date for {patient.name}: {item_date}")
                            
                            # Parse time
                            time_str = item["time"]
                            
                            # Create scheduled call object
                            scheduled_call = ScheduledCall(
                                patient_id=patient.id,
                                patient_name=patient.name,
                                phone_number=patient.phone,
                                message=item["message"],
                                scheduled_date=item_date,
                                scheduled_time=time_str,
                                call_type=item.get("type", "ivr"),
                                topic=item.get("topic", ""),
                                week_number=item.get("week", None),
                                risk_level=patient.risk_category,
                                priority=self._determine_call_priority(patient, item)
                            )
                            
                            self.scheduled_calls.append(scheduled_call)
                            logger.info(f"Added scheduled call for {patient.name} on {item_date} at {time_str}")
                        else:
                            logger.info(f"❌ Date mismatch: {item_date} != {check_date}")
                            
                    except Exception as e:
                        logger.error(f"Error processing schedule item for {patient.name}: {e}")
                        continue
                    
        except Exception as e:
            logger.error(f"Error fetching patient schedule for {patient.name}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
    
    def _determine_call_priority(self, patient, schedule_item):
        """Determine call priority based on patient risk and schedule type"""
        # High priority for high-risk patients
        if patient.risk_category == "high":
            return CallPriority.HIGH
        
        # Medium priority for medium-risk patients
        elif patient.risk_category == "medium":
            return CallPriority.MEDIUM
        
        # Low priority for low-risk patients
        elif patient.risk_category == "low":
            return CallPriority.LOW
        
        # Default to medium priority
        return CallPriority.MEDIUM
    
    def _sort_scheduled_calls(self):
        """Sort scheduled calls by date, priority, and time"""
        self.scheduled_calls.sort(key=lambda x: (x.scheduled_date, x.priority.value, x.scheduled_time))
    
    def medication_reminder_job(self):
        """Enhanced job to process current IVR calls from the scheduled list"""
        try:
            logger.info("Processing current IVR calls...")
            current_time = datetime.now()
            current_time_only = current_time.time()
            
            # Process scheduled calls that are due
            calls_to_process = []
            
            for scheduled_call in self.scheduled_calls:
                try:
                    # Parse scheduled time
                    scheduled_time = datetime.strptime(scheduled_call.scheduled_time, "%I:%M %p").time()
                    
                    # Check if it's time to make the call (within 1 minute window)
                    time_diff = abs((current_time_only.hour * 60 + current_time_only.minute) - 
                                   (scheduled_time.hour * 60 + scheduled_time.minute))
                    
                    if time_diff <= 1:  # Within 1 minute of scheduled time
                        calls_to_process.append(scheduled_call)
                        
                except Exception as e:
                    logger.error(f"Error processing scheduled call for {scheduled_call.patient_name}: {e}")
                    continue
            
            # Add calls to queue
            for call in calls_to_process:
                self._add_scheduled_call_to_queue(call)
                logger.info(f"Added scheduled call to queue for {call.patient_name}: {call.topic}")
                
        except Exception as e:
            logger.error(f"Error in medication_reminder_job: {e}")
    
    def _add_scheduled_call_to_queue(self, scheduled_call):
        """Add scheduled call to processing queue"""
        call_data = {
            "patient_id": scheduled_call.patient_id,
            "patient_name": scheduled_call.patient_name,
            "phone_number": scheduled_call.phone_number,
            "message": scheduled_call.message,
            "call_type": scheduled_call.call_type,
            "scheduled_time": datetime.now().isoformat(),
            "retry_count": 0,
            "priority": scheduled_call.priority.value,
            "topic": scheduled_call.topic,
            "week_number": scheduled_call.week_number,
            "risk_level": scheduled_call.risk_level
        }
        
        self.call_queue.append(call_data)
        logger.info(f"Added call to queue for {scheduled_call.patient_name}")
    
    def get_scheduled_calls_summary(self) -> Dict[str, Any]:
        """Get summary of all scheduled calls"""
        try:
            current_date = datetime.now().date()
            
            summary = {
                "total_scheduled_calls": len(self.scheduled_calls),
                "current_date": current_date.isoformat(),
                "calls_by_priority": {
                    "high": len([c for c in self.scheduled_calls if c.priority == CallPriority.HIGH]),
                    "medium": len([c for c in self.scheduled_calls if c.priority == CallPriority.MEDIUM]),
                    "low": len([c for c in self.scheduled_calls if c.priority == CallPriority.LOW])
                },
                "calls_by_risk_level": {
                    "high": len([c for c in self.scheduled_calls if c.risk_level == "high"]),
                    "medium": len([c for c in self.scheduled_calls if c.risk_level == "medium"]),
                    "low": len([c for c in self.scheduled_calls if c.risk_level == "low"])
                },
                "queue_status": {
                    "pending_calls": len(self.call_queue),
                    "failed_calls": len(self.failed_calls)
                },
                "scheduled_calls": [
                    {
                        "patient_name": call.patient_name,
                        "phone_number": call.phone_number,
                        "scheduled_time": call.scheduled_time,
                        "topic": call.topic,
                        "priority": call.priority.name,
                        "risk_level": call.risk_level,
                        "week_number": call.week_number
                    }
                    for call in self.scheduled_calls
                ]
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting scheduled calls summary: {e}")
            return {"error": str(e)}
    
    def get_upcoming_calls_summary(self, days_ahead: int = 7) -> Dict[str, Any]:
        """Get summary of upcoming calls for the next N days"""
        try:
            current_date = datetime.now().date()
            current_time = datetime.now().time()
            upcoming_calls = []
            
            # Get all patients and their schedules
            db = SessionLocal()
            try:
                patients = db.query(Patient).all()
                
                for patient in patients:
                    if not patient.call_schedule:
                        continue
                    
                    # Replace all patient.call_schedule with patient.call_schedule
                    # When parsing schedule, do:
                    if isinstance(patient.call_schedule, str):
                        try:
                            schedule_data = json.loads(patient.call_schedule)
                        except Exception:
                            schedule_data = []
                    else:
                        schedule_data = patient.call_schedule
                    if isinstance(schedule_data, list):
                        schedule = schedule_data
                    elif isinstance(schedule_data, dict):
                        schedule = schedule_data.get("schedule", [])
                    else:
                        schedule = []
                    
                    for item in schedule:
                        try:
                            # Check if item has required fields
                            if "date" not in item or "time" not in item or "message" not in item:
                                logger.warning(f"Skipping incomplete schedule item for {patient.name}: missing required fields")
                                continue
                            
                            # Parse date
                            if isinstance(item["date"], str):
                                item_date = datetime.strptime(item["date"], "%Y-%m-%d").date()
                            else:
                                item_date = item["date"].date()
                            
                            # Check if within the next N days
                            days_until_call = (item_date - current_date).days
                            if 0 <= days_until_call <= days_ahead:
                                # Parse the scheduled time
                                time_str = item["time"]
                                try:
                                    # Handle different time formats
                                    if "AM" in time_str or "PM" in time_str:
                                        scheduled_time = datetime.strptime(time_str, "%I:%M %p").time()
                                    else:
                                        # Handle 24-hour format or other formats
                                        scheduled_time = datetime.strptime(time_str, "%H:%M").time()
                                except ValueError:
                                    # If time parsing fails, skip this call
                                    logger.warning(f"Could not parse time '{time_str}' for patient {patient.name}")
                                    continue
                                
                                # Filter out calls that are in the past
                                if days_until_call == 0:  # Today
                                    if scheduled_time <= current_time:
                                        # This call is in the past, skip it
                                        continue
                                
                                upcoming_calls.append({
                                    "patient_id": patient.id,
                                    "patient_name": patient.name,
                                    "phone_number": patient.phone,
                                    "scheduled_date": item_date.isoformat(),
                                    "scheduled_time": item["time"],
                                    "topic": item.get("topic", ""),
                                    "week_number": item.get("week", None),
                                    "risk_level": patient.risk_category,
                                    "days_until_call": days_until_call,
                                    "message": item["message"][:100] + "..." if len(item["message"]) > 100 else item["message"]
                                })
                                
                        except Exception as e:
                            logger.error(f"Error processing upcoming call for {patient.name}: {e}")
                            continue
                            
            finally:
                db.close()
            
            # Sort by date and time
            upcoming_calls.sort(key=lambda x: (x["days_until_call"], x["scheduled_time"]))
            
            summary = {
                "current_date": current_date.isoformat(),
                "current_time": current_time.strftime("%I:%M %p"),
                "days_ahead": days_ahead,
                "total_upcoming_calls": len(upcoming_calls),
                "calls_by_day": {},
                "calls_by_risk_level": {
                    "high": len([c for c in upcoming_calls if c["risk_level"] == "high"]),
                    "medium": len([c for c in upcoming_calls if c["risk_level"] == "medium"]),
                    "low": len([c for c in upcoming_calls if c["risk_level"] == "low"])
                },
                "upcoming_calls": upcoming_calls
            }
            
            # Group calls by day
            for call in upcoming_calls:
                day_key = f"day_{call['days_until_call']}"
                if day_key not in summary["calls_by_day"]:
                    summary["calls_by_day"][day_key] = []
                summary["calls_by_day"][day_key].append(call)
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting upcoming calls summary: {e}")
            return {"error": str(e)}
    
    def _process_patient_schedule(self, patient, current_time, current_date):
        """Legacy method - kept for backward compatibility"""
        # This method is now replaced by _fetch_patient_scheduled_calls
        pass
    
    def _process_call_queue(self):
        """Process calls from the queue"""
        while True:
            try:
                if self.call_queue:
                    call_data = self.call_queue.pop(0)
                    self._make_call_from_queue(call_data)
                else:
                    time.sleep(1)  # Wait if queue is empty
            except Exception as e:
                logger.error(f"Error in call queue processor: {e}")
                time.sleep(5)
    
    def _process_call_queue_job(self):
        """Job wrapper for call queue processing"""
        try:
            # This job ensures the queue processor is running
            if not self.call_queue:
                logger.debug("Call queue is empty")
        except Exception as e:
            logger.error(f"Error in call queue processor job: {e}")
    
    def _make_call_from_queue(self, call_data):
        """Make call from queue data"""
        try:
            result = twilio_call_service.make_call_and_play_script(
                call_data["phone_number"],
                call_data["message"],
                call_data["call_type"]
            )
            
            if result.get("success"):
                logger.info(f"Call successful for {call_data['patient_name']}")
            else:
                # Add to failed calls for retry
                self._add_to_failed_calls(call_data)
                
        except Exception as e:
            logger.error(f"Error making call for {call_data['patient_name']}: {e}")
            self._add_to_failed_calls(call_data)
    
    def _add_to_failed_calls(self, call_data):
        """Add failed call to retry queue"""
        call_id = f"{call_data['patient_id']}_{call_data['scheduled_time']}"
        
        if call_id not in self.failed_calls:
            self.failed_calls[call_id] = {
                **call_data,
                "failed_at": datetime.now().isoformat(),
                "retry_count": 0
            }
        else:
            self.failed_calls[call_id]["retry_count"] += 1
    
    def _retry_failed_calls_job(self):
        """Retry failed calls"""
        try:
            current_time = datetime.now()
            calls_to_remove = []
            
            for call_id, call_data in self.failed_calls.items():
                # Check if enough time has passed for retry
                failed_at = datetime.fromisoformat(call_data["failed_at"])
                time_since_failure = (current_time - failed_at).total_seconds()
                
                if time_since_failure >= self.retry_delay:
                    if call_data["retry_count"] < self.max_retries:
                        # Retry the call
                        logger.info(f"Retrying call for {call_data['patient_name']}")
                        self._make_call_from_queue(call_data)
                        calls_to_remove.append(call_id)
                    else:
                        # Max retries reached
                        logger.warning(f"Max retries reached for {call_data['patient_name']}")
                        calls_to_remove.append(call_id)
            
            # Remove processed calls
            for call_id in calls_to_remove:
                del self.failed_calls[call_id]
                
        except Exception as e:
            logger.error(f"Error in retry failed calls job: {e}")
    
    def _handle_missed_calls_job(self):
        """Handle missed calls with longer delay"""
        try:
            # Get call statistics to identify missed calls
            stats = twilio_call_service.get_call_statistics()
            
            if stats["missed_calls"] > 0:
                logger.info(f"Processing {stats['missed_calls']} missed calls")
                
                # Get recent call history for missed calls
                call_history = twilio_call_service.get_call_history()
                
                for call in call_history:
                    if call.get("current_status") in ["busy", "no-answer"]:
                        # Check if enough time has passed for retry
                        last_status = call.get("status_history", [])[-1]
                        failed_at = datetime.fromisoformat(last_status["timestamp"])
                        time_since_failure = (datetime.now() - failed_at).total_seconds()
                        
                        if time_since_failure >= self.missed_call_retry_delay:
                            # Retry the missed call
                            phone_number = last_status.get("details", {}).get("phone_number")
                            if phone_number:
                                # Get original script from call details
                                script = last_status.get("details", {}).get("script", "Hello, this is your health reminder.")
                                
                                logger.info(f"Retrying missed call to {phone_number}")
                                twilio_call_service.handle_missed_calls(phone_number, script)
                                
        except Exception as e:
            logger.error(f"Error in missed calls handler job: {e}")
    
    def _daily_statistics_job(self):
        """Generate daily call statistics"""
        try:
            stats = twilio_call_service.get_call_statistics()
            
            logger.info("Daily Call Statistics:")
            logger.info(f"Total Calls: {stats['total_calls']}")
            logger.info(f"Successful Calls: {stats['successful_calls']}")
            logger.info(f"Failed Calls: {stats['failed_calls']}")
            logger.info(f"Missed Calls: {stats['missed_calls']}")
            logger.info(f"Success Rate: {stats['success_rate']:.2f}%")
            logger.info(f"Delivery Rate: {stats['delivery_rate']:.2f}%")
            
            # Reset daily counters (optional)
            # self._reset_daily_counters()
            
        except Exception as e:
            logger.error(f"Error in daily statistics job: {e}")
    
    def _process_callbacks_job(self):
        """Process pending callbacks from patient messages"""
        try:
            logger.info("Processing pending callbacks...")
            db = SessionLocal()
            try:
                from db import PatientMessage
                
                # Get all pending callbacks that are due
                current_time = datetime.now()
                pending_callbacks = db.query(PatientMessage).filter(
                    PatientMessage.status == "pending",
                    PatientMessage.scheduled_callback <= current_time,
                    PatientMessage.callback_message.isnot(None)
                ).all()
                
                logger.info(f"Found {len(pending_callbacks)} pending callbacks to process")
                
                for callback in pending_callbacks:
                    try:
                        # Get patient information
                        patient = db.query(Patient).filter(Patient.id == callback.patient_id).first()
                        if not patient:
                            logger.warning(f"Patient not found for callback {callback.id}")
                            continue
                        
                        # Create callback call
                        callback_message = callback.callback_message or f"About your question yesterday, {callback.processed_response or 'we have a response for you.'}"
                        
                        # Add to call queue
                        scheduled_call = ScheduledCall(
                            patient_id=patient.id,
                            patient_name=patient.name,
                            phone_number=patient.phone,
                            message=callback_message,
                            scheduled_date=current_time.date(),
                            scheduled_time=current_time.strftime("%I:%M %p"),
                            call_type="callback",
                            priority=CallPriority.HIGH,  # Callbacks are high priority
                            topic="callback"
                        )
                        
                        self.scheduled_calls.append(scheduled_call)
                        
                        # Update callback status
                        callback.status = "scheduled"
                        callback.processed_at = current_time
                        db.commit()
                        
                        logger.info(f"Scheduled callback for {patient.name}: {callback_message[:50]}...")
                        
                    except Exception as e:
                        logger.error(f"Error processing callback {callback.id}: {e}")
                        continue
                        
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error in callback processing job: {e}")
    
    def schedule_immediate_call(self, patient_id: int, message: str, call_type: str = "ivr"):
        """Schedule an immediate call"""
        try:
            db = SessionLocal()
            patient = db.query(Patient).filter(Patient.id == patient_id).first()
            
            if patient:
                call_data = {
                    "patient_id": patient.id,
                    "patient_name": patient.name,
                    "phone_number": patient.phone,
                    "message": message,
                    "call_type": call_type,
                    "scheduled_time": datetime.now().isoformat(),
                    "retry_count": 0
                }
                
                self.call_queue.append(call_data)
                logger.info(f"Scheduled immediate call for {patient.name}")
                
            db.close()
            
        except Exception as e:
            logger.error(f"Error scheduling immediate call: {e}")
    
    def get_scheduler_status(self) -> Dict[str, Any]:
        """Get scheduler status and statistics"""
        return {
            "scheduler_running": self.scheduler.running,
            "jobs_count": len(self.scheduler.get_jobs()),
            "call_queue_size": len(self.call_queue),
            "failed_calls_count": len(self.failed_calls),
            "call_statistics": twilio_call_service.get_call_statistics()
        }

# Global enhanced scheduler instance
enhanced_scheduler = EnhancedScheduler()

# Backward compatibility functions
def format_phone_e164(phone: str) -> str:
    """Format a US phone number to E.164 (+1XXXXXXXXXX)."""
    return twilio_call_service.format_phone_number(phone)

def medication_reminder_job():
    """Backward compatibility function"""
    enhanced_scheduler.medication_reminder_job()

def start_scheduler():
    """Start the enhanced scheduler"""
    enhanced_scheduler.start_scheduler()

# Legacy functions for backward compatibility
def handle_date_based_schedule(patient, schedule, current_time, current_date):
    """Legacy function - now handled by _process_patient_schedule"""
    enhanced_scheduler._process_patient_schedule(patient, current_time, current_date)

def handle_legacy_schedule(patient, current_time_str):
    """Legacy function - kept for backward compatibility"""
    # This function is now deprecated in favor of the new schedule format
    logger.warning("Legacy schedule format is deprecated")
    pass

def make_pregnancy_ivr_call(patient, week_num, schedule_line):
    """Legacy function - kept for backward compatibility"""
    # This function is now deprecated in favor of the new schedule format
    logger.warning("Legacy pregnancy IVR call is deprecated")
    pass

def trigger_outbound_call(patient):
    """Legacy function - now handled by schedule_immediate_call"""
    enhanced_scheduler.schedule_immediate_call(patient.id, "Hello, this is your health reminder.")
