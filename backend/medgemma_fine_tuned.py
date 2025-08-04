
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
import logging
import os
from datetime import datetime, timedelta
import json
import re
from typing import Dict, Any, List, Optional
from rag_service import rag_service
from googletrans import Translator

# Fix OpenMP issue
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# When generating or copying any 'time' field, always use 'h:mm AM/PM' format
def ensure_time_format(time_str):
    import re
    match = re.match(r'^(\d{1,2})(?::(\d{2}))?\s*(AM|PM)$', time_str, re.IGNORECASE)
    if match:
        hour = match.group(1)
        minute = match.group(2) if match.group(2) else '00'
        ampm = match.group(3).upper()
        return f"{int(hour)}:{minute} {ampm}"
    return time_str

class FineTunedMedGemmaAI:
    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model_path = "google/gemma-2b"
        self.translator = Translator()
        logger.info(f"Using device: {self.device}")
        
    def load_model(self):
        """Load the Gemma model for personalized IVR messages"""
        try:
            logger.info("🤖 Loading Gemma model...")
            
            # Load Gemma model directly
            logger.info(f"📁 Loading Gemma model from {self.model_path}")
            
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_path,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                low_cpu_mem_usage=True,
                device_map="auto" if self.device == "cuda" else None
            )
            
            # Add padding token if not present
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
                
            logger.info("✅ Gemma model loaded successfully!")
            return True
                
        except Exception as e:
            logger.error(f"❌ Error loading Gemma model: {e}")
            logger.info("🔄 Falling back to simple model...")
            return self._load_simple_fallback()
    
    def _load_base_model(self):
        """Load the base Gemma3n model as fallback"""
        try:
            logger.info("📥 Loading base Gemma3n model...")
            
            # Use the base Gemma3n model
            model_name = "unsloth/gemma-2b-it"
            
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForCausalLM.from_pretrained(
                model_name,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                low_cpu_mem_usage=True,
                device_map="auto" if self.device == "cuda" else None
            )
            
            # Add padding token if not present
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
                
            logger.info("✅ Base Gemma3n model loaded successfully!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error loading base model: {e}")
            return self._load_simple_fallback()
    
    def _load_simple_fallback(self):
        """Load a very simple fallback if model loading fails"""
        try:
            logger.info("🔄 Loading simple fallback...")
            # Create a simple tokenizer and model
            from transformers import GPT2Tokenizer, GPT2LMHeadModel
            
            self.tokenizer = GPT2Tokenizer.from_pretrained("gpt2")
            self.model = GPT2LMHeadModel.from_pretrained("gpt2")
            
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
                
            logger.info("✅ Simple fallback loaded successfully!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error loading fallback model: {e}")
            return False

    def _simplify_hindi(self, text: str) -> str:
        """Replace complex Hindi words with simpler alternatives"""
        replacements = {
            "गर्भावस्था": "प्रेगनेंसी",
            "भोजन": "खाना",
            "आहार": "खाना",
            "चिकित्सक": "डॉक्टर",
            "औषधि": "दवा",
            "नियमित": "रोज",
            "जल": "पानी",
            "तुरंत": "फौरन"
        }
        for original, simple in replacements.items():
            text = text.replace(original, simple)
        return text
    
    def generate_personalized_ivr_message(self, topic: str, patient_name: str, gestational_age_weeks: int = 28,
                                          risk_factors: list = None, risk_category: str = "low",
                                          patient_data: dict = None, language: str = "en") -> dict:
        """Generate personalized IVR messages with optional Hindi translation"""
        try:
            medications = patient_data.get("medications", []) if patient_data else []

            message = self._generate_enhanced_fallback_message(
                topic=topic,
                patient_name=patient_name,
                gestational_age_weeks=gestational_age_weeks,
                risk_factors=risk_factors or [],
                medications=medications,
                risk_category=risk_category
            )

            if language != "en":
                try:
                    translated = self.translator.translate(message, dest=language).text
                    if language == "hi":
                        translated = self._simplify_hindi(translated)
                    message = translated
                except Exception as e:
                    logger.error(f"Translation error: {e}")

            word_count = len(message.split())

            return {
                "message": message,
                "word_count": word_count,
                "model_used": "Enhanced Fallback System",
                "topic": topic,
                "patient_name": patient_name,
                "gestational_age_weeks": gestational_age_weeks,
                "language": language
            }

        except Exception as e:
            logger.error(f"Error generating personalized IVR message: {e}")
            fallback_message = (
                f"Hello {patient_name}, this is your health reminder. Please take your medication as prescribed. "
                "Press 1 if you'd like to leave a message for our medical team."
            )
            return {
                "message": fallback_message,
                "word_count": len(fallback_message.split()),
                "model_used": "Enhanced Fallback System (Error Recovery)",
                "topic": topic,
                "patient_name": patient_name,
                "gestational_age_weeks": gestational_age_weeks,
                "language": language
            }
    
    def _is_poor_response(self, response: str) -> bool:
        """Check if the model response is poor quality"""
        # Check for repetitive phrases
        if response.count("very") > 2:
            return True
        if response.count("baby") > 4:
            return True
        if response.count("important") > 3:
            return True
        
        # Check for incoherent patterns
        if response.count("?") > 2:
            return True
        if response.count("What are") > 2:
            return True
        
        # Check for too short responses
        if len(response) < 20:
            return True
        
        # Check for repetitive words
        words = response.lower().split()
        if len(words) > 0:
            word_counts = {}
            for word in words:
                if len(word) > 3:  # Only count longer words
                    word_counts[word] = word_counts.get(word, 0) + 1
            
            # If any word appears too frequently
            for word, count in word_counts.items():
                if count > len(words) * 0.1:  # More than 10% of words
                    return True
        
        return False
    
    def _create_structured_prompt(self, patient_name: str, topic: str, gestational_age_weeks: int, risk_factors: list, context: str) -> str:
        """Create a more structured prompt for better model responses"""
        
        # Build context information
        context_parts = []
        
        if gestational_age_weeks > 0:
            context_parts.append(f"gestational age: {gestational_age_weeks} weeks")
        
        if risk_factors:
            risk_text = ", ".join(risk_factors[:3])  # Limit to first 3 risk factors
            context_parts.append(f"risk factors: {risk_text}")
        
        if context:
            context_parts.append(f"context: {context}")
        
        context_str = f" ({', '.join(context_parts)})" if context_parts else ""
        
        # Create a more specific prompt with professional medical tone
        prompt = f"<|im_start|>user\nCreate a professional medical IVR message for {patient_name} about {topic}{context_str}. Use a professional, caring tone appropriate for healthcare communication. Keep it informative, clear, and under 150 words. Avoid casual language or medical jargon.<|im_end|>\n<|im_start|>assistant\n"
        
        return prompt
    
    def _create_enhanced_structured_prompt(self, patient_name: str, topic: str, gestational_age_weeks: int, risk_factors: list, context: str, patient_data: dict) -> str:
        """Create a more structured prompt for better model responses, incorporating patient data"""
        
        # Build context information
        context_parts = []
        
        if gestational_age_weeks > 0:
            context_parts.append(f"gestational age: {gestational_age_weeks} weeks")
        
        if risk_factors:
            risk_text = ", ".join(risk_factors[:3])  # Limit to first 3 risk factors
            context_parts.append(f"risk factors: {risk_text}")
        
        if context:
            context_parts.append(f"context: {context}")
        
        if patient_data:
            # Add patient-specific data if available
            if patient_data.get("height"):
                context_parts.append(f"height: {patient_data['height']} inches")
            if patient_data.get("weight"):
                context_parts.append(f"weight: {patient_data['weight']} lbs")
            if patient_data.get("bmi"):
                context_parts.append(f"bmi: {patient_data['bmi']:.1f}")
            if patient_data.get("medications"):
                med_text = ", ".join([f"{med['name']} ({med['dosage']})" for med in patient_data['medications']])
                context_parts.append(f"current medications: {med_text}")
            if patient_data.get("allergies"):
                allergy_text = ", ".join(patient_data['allergies'])
                context_parts.append(f"allergies: {allergy_text}")
            if patient_data.get("medical_history"):
                med_hist_text = ", ".join(patient_data['medical_history'])
                context_parts.append(f"medical history: {med_hist_text}")
        
        context_str = f" ({', '.join(context_parts)})" if context_parts else ""
        
        # Create a more specific prompt with professional medical tone
        prompt = f"<|im_start|>user\nCreate a professional medical IVR message for {patient_name} about {topic}{context_str}. Use a professional, caring tone appropriate for healthcare communication. Keep it informative, clear, and under 150 words. Avoid casual language or medical jargon.<|im_end|>\n<|im_start|>assistant\n"
        
        return prompt
    
    def _clean_and_structure_response(self, response: str, prompt: str, patient_name: str, topic: str) -> str:
        """Clean and structure the model response"""
        # Remove the original prompt from the response
        if prompt in response:
            response = response.replace(prompt, "").strip()
        
        # Remove repetitive phrases
        response = response.replace("Create a personalized IVR message for", "").strip()
        response = response.replace("personalized IVR message", "").strip()
        
        # If response is too short or incoherent, use fallback
        if len(response) < 15 or response.count("very") > 3 or response.count("baby") > 5:
            return self._generate_enhanced_fallback_message(patient_name, topic, 0, [], {})
        
        # Ensure it starts with a greeting
        if not response.lower().startswith(("dear", "hello", "hi", "good")):
            response = f"Dear {patient_name}, {response}"
        
        # Limit response length
        if len(response) > 300:
            response = response[:300] + "..."
        
        # Ensure it ends properly
        if not response.endswith((".", "!", "?")):
            response += "."
        
        return response
    
    def _generate_fallback_message(self, patient_name: str, topic: str, gestational_age_weeks: int, risk_factors: list) -> str:
        """Generate a high-quality fallback message using rule-based logic"""
        logger.info("🔄 Using enhanced fallback message generation")
        
        # Create more personalized fallback messages
        if "nutrition" in topic.lower():
            return f"Dear {patient_name}, this is your nutrition reminder. Please eat a balanced diet with plenty of fruits, vegetables, and proteins. Remember to take your prenatal vitamins and stay hydrated. Your health and your baby's health are our priority."
        elif "medication" in topic.lower():
            return f"Dear {patient_name}, this is your medication reminder. Please take your prescribed medications on time as directed by your healthcare provider. If you have any questions or concerns, don't hesitate to contact your doctor."
        elif "exercise" in topic.lower():
            return f"Dear {patient_name}, this is your exercise reminder. Gentle walking and prenatal yoga are safe exercises during pregnancy. Listen to your body and rest when needed. Regular physical activity helps maintain your health and prepares you for delivery."
        elif "check" in topic.lower() or "appointment" in topic.lower():
            return f"Dear {patient_name}, this is a reminder about your upcoming prenatal check-up. Regular appointments are crucial for monitoring your pregnancy progress and ensuring both you and your baby are healthy."
        elif "symptoms" in topic.lower() or "warning" in topic.lower():
            return f"Dear {patient_name}, please be aware of any unusual symptoms during your pregnancy. Contact your healthcare provider immediately if you experience severe pain, bleeding, or other concerning symptoms."
        else:
            return f"Dear {patient_name}, this is your pregnancy care reminder. Please attend your regular check-ups, follow your doctor's advice, and take care of yourself and your baby. Remember, you're doing great!"
    
    def _generate_enhanced_fallback_message(self, patient_name: str, topic: str, gestational_age_weeks: int = 28, risk_factors: list = None, medications: list = None, risk_category: str = "low") -> str:
        """Generate high-quality IVR messages using rule-based templates with Press 1 option"""
        try:
            # Base message generation
            if topic == "medication_reminder":
                if isinstance(medications, list) and medications:
                    med_details = ", ".join([f"{med.get('name', 'Medication')} ({med.get('dosage', 'as prescribed')})" for med in medications])
                else:
                    med_details = "your medication as prescribed"
                
                message = f"Hello {patient_name}, this is your medication reminder. Please take {med_details}. Remember to take it at the same time each day for best results."
                
            elif topic == "nutrition and blood sugar management":
                message = f"Hello {patient_name}, this is your nutrition and blood sugar management reminder. Continue monitoring your blood glucose levels as recommended by your healthcare provider. Maintain a balanced diet with plenty of vegetables, lean proteins, and whole grains. Stay hydrated and avoid sugary beverages. Remember to check your blood sugar before and after meals as instructed."
                
            elif topic == "exercise guidelines":
                message = f"Hello {patient_name}, this is your exercise reminder. Gentle physical activity is beneficial during pregnancy. Consider walking, swimming, or prenatal yoga for 30 minutes most days. Listen to your body and stop if you feel uncomfortable. Stay hydrated and avoid exercises that involve lying on your back after the first trimester."
                
            elif topic == "blood pressure monitoring":
                message = f"Hello {patient_name}, this is your blood pressure monitoring reminder. Continue checking your blood pressure as recommended by your healthcare provider. Keep a log of your readings and bring it to your next appointment. Contact your doctor immediately if you experience severe headaches, vision changes, or swelling in your hands and face."
                
            elif topic == "morning sickness management":
                message = f"Hello {patient_name}, this is your morning sickness management reminder. Try eating small, frequent meals throughout the day. Keep crackers by your bedside and eat them before getting up. Stay hydrated with small sips of water or ginger tea. Avoid strong smells and spicy foods. Contact your doctor if you experience severe nausea or vomiting."
                
            elif topic == "iron supplementation":
                message = f"Hello {patient_name}, this is your iron supplementation reminder. Take your iron supplement as prescribed, preferably with vitamin C to improve absorption. Take it on an empty stomach if possible, but if it causes stomach upset, take it with food. Remember that iron supplements can cause constipation, so drink plenty of water and eat fiber-rich foods."
                
            elif topic == "weekly_checkin":
                week_num = (gestational_age_weeks // 4) + 1
                message = f"Hello {patient_name}, this is your week {week_num} pregnancy check-in. How are you feeling today? Remember to track your baby's movements - you should feel at least 10 movements in 2 hours. If you notice decreased movement, contact your healthcare provider immediately. Continue with your prenatal vitamins and healthy eating. Stay hydrated and get adequate rest. Don't hesitate to call your doctor if you have any concerns about your pregnancy. You're doing great!"
                
            elif topic == "high_risk_additional":
                risk_text = ""
                if risk_factors and any("gestational_diabetes" in str(rf).lower() for rf in risk_factors):
                    risk_text = "Given your gestational diabetes, continue monitoring your blood sugar levels closely. Follow your meal plan and exercise recommendations."
                elif risk_factors and any("hypertension" in str(rf).lower() for rf in risk_factors):
                    risk_text = "Given your hypertension, continue monitoring your blood pressure daily. Take your medications as prescribed and report any concerning symptoms."
                elif risk_factors and any("preterm" in str(rf).lower() for rf in risk_factors):
                    risk_text = "Given your risk of preterm labor, pay attention to any signs of early labor such as regular contractions, pelvic pressure, or changes in vaginal discharge."
                else:
                    risk_text = "Given your high-risk pregnancy status, continue following all your healthcare provider's recommendations closely."
                
                message = f"Hello {patient_name}, this is your additional high-risk pregnancy check-in. {risk_text} Contact your healthcare provider immediately if you experience any concerning symptoms or have questions about your care plan."
                
            elif topic == "appointment_reminder":
                message = f"Hello {patient_name}, this is your appointment reminder. Please confirm your upcoming prenatal appointment. If you need to reschedule, contact your healthcare provider's office as soon as possible. Remember to bring any questions you have for your doctor."
                
            else:
                message = f"Hello {patient_name}, this is your health reminder. Continue following your healthcare provider's recommendations and don't hesitate to contact them if you have any concerns."
            
            # Add Press 1 option to every message
            message += " Press 1 if you'd like to leave a message for our medical team."
            
            return message
            
        except Exception as e:
            logger.error(f"Error in enhanced fallback message generation: {e}")
            return f"Hello {patient_name}, this is your health reminder. Please take your medication as prescribed. Press 1 if you'd like to leave a message for our medical team."
    
    def generate_comprehensive_ivr_schedule(self, gestational_age_weeks: int, patient_name: str, current_date: datetime = None, risk_factors: list = None, risk_category: str = "low", structured_medications: list = None, patient_data: dict = None) -> dict:
        """Generate a comprehensive IVR schedule with Press 1 option in all messages"""
        try:
            if current_date is None:
                current_date = datetime.now()
            
            schedule = []
            
            # Generate medication reminders
            if structured_medications:
                for med in structured_medications:
                    med_name = med.get('name', 'Medication')
                    dosage = med.get('dosage', 'as prescribed')
                    time = med.get('time', '8:00 AM')
                    
                    message = f"Hello {patient_name}, this is your medication reminder. Please take {med_name} ({dosage}) at {time}. Remember to take it at the same time each day for best results. Press 1 if you'd like to leave a message for our medical team."
                    
                    # Schedule for next few days
                    for i in range(4):
                        call_date = current_date + timedelta(days=i+1)
                        schedule.append({
                            "type": "medication_reminder",
                            "date": call_date.strftime("%Y-%m-%d"),
                            "time": time,
                            "message": message,
                            "medication_name": med_name,
                            "dosage": dosage
                        })
            
            # Generate weekly check-ins
            week_num = (gestational_age_weeks // 4) + 1
            checkin_message = f"Hello {patient_name}, this is your week {week_num} pregnancy check-in. How are you feeling today? Remember to track your baby's movements - you should feel at least 10 movements in 2 hours. If you notice decreased movement, contact your healthcare provider immediately. Continue with your prenatal vitamins and healthy eating. Stay hydrated and get adequate rest. Don't hesitate to call your doctor if you have any concerns about your pregnancy. You're doing great! Press 1 if you'd like to leave a message for our medical team."
            
            for i in range(4):
                call_date = current_date + timedelta(days=i*7+1)
                schedule.append({
                    "type": "checkin",
                    "date": call_date.strftime("%Y-%m-%d"),
                    "time": "4:30 PM",
                    "message": checkin_message,
                    "week": week_num
                })
            
            # Generate high-risk additional calls if applicable
            if risk_category == "high" and risk_factors:
                risk_text = ""
                if any("gestational_diabetes" in str(rf).lower() for rf in risk_factors):
                    risk_text = "Given your gestational diabetes, continue monitoring your blood sugar levels closely. Follow your meal plan and exercise recommendations."
                elif any("hypertension" in str(rf).lower() for rf in risk_factors):
                    risk_text = "Given your hypertension, continue monitoring your blood pressure daily. Take your medications as prescribed and report any concerning symptoms."
                elif any("preterm" in str(rf).lower() for rf in risk_factors):
                    risk_text = "Given your risk of preterm labor, pay attention to any signs of early labor such as regular contractions, pelvic pressure, or changes in vaginal discharge."
                else:
                    risk_text = "Given your high-risk pregnancy status, continue following all your healthcare provider's recommendations closely."
                
                high_risk_message = f"Hello {patient_name}, this is your additional high-risk pregnancy check-in. {risk_text} Contact your healthcare provider immediately if you experience any concerning symptoms or have questions about your care plan. Press 1 if you'd like to leave a message for our medical team."
                
                for i in range(2):
                    call_date = current_date + timedelta(days=i*3+2)
                    schedule.append({
                        "type": "high_risk_additional",
                        "date": call_date.strftime("%Y-%m-%d"),
                        "time": "2:00 PM",
                        "message": high_risk_message,
                        "risk_factor": "high_risk"
                    })
            
            # Generate appointment reminders
            appointment_message = f"Hello {patient_name}, this is your appointment reminder. Please confirm your upcoming prenatal appointment. If you need to reschedule, contact your healthcare provider's office as soon as possible. Remember to bring any questions you have for your doctor. Press 1 if you'd like to leave a message for our medical team."
            
            for i in range(2):
                call_date = current_date + timedelta(days=i*14+3)
                schedule.append({
                    "type": "appointment_reminder",
                    "date": call_date.strftime("%Y-%m-%d"),
                    "time": "10:00 AM",
                    "message": appointment_message
                })
            
            return {
                "schedule": schedule,
                "total_calls": len(schedule),
                "patient_name": patient_name,
                "gestational_age_weeks": gestational_age_weeks,
                "risk_category": risk_category,
                "generated_at": current_date.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating comprehensive IVR schedule: {e}")
            # Fallback schedule
            fallback_message = f"Hello {patient_name}, this is your health reminder. Please take your medication as prescribed. Press 1 if you'd like to leave a message for our medical team."
            return {
                "schedule": [{
                    "type": "fallback",
                    "date": current_date.strftime("%Y-%m-%d"),
                    "time": "9:00 AM",
                    "message": fallback_message
                }],
                "total_calls": 1,
                "patient_name": patient_name,
                "gestational_age_weeks": gestational_age_weeks,
                "risk_category": risk_category,
                "generated_at": current_date.isoformat()
            }
    
    def process_medical_query(self, query: str, patient_name: str = "", context: str = "") -> str:
        """Process medical queries using the fine-tuned model"""
        try:
            if self.model is None or self.tokenizer is None:
                return "I'm sorry, I'm not able to process medical queries at the moment. Please contact your healthcare provider."
            
            # Create prompt for medical query
            prompt = f"<|im_start|>user\nMedical query: {query}<|im_end|>\n<|im_start|>assistant\n"
            
            # Tokenize and generate
            inputs = self.tokenizer(prompt, return_tensors="pt", max_length=512, truncation=True)
            
            if self.device == "cuda":
                inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_length=512,
                    temperature=0.7,
                    do_sample=True,
                    pad_token_id=self.tokenizer.eos_token_id
                )
            
            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            # Extract assistant response
            if "<|im_start|>assistant" in response:
                response = response.split("<|im_start|>assistant")[-1].split("<|im_end|>")[0].strip()
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing medical query: {e}")
            return "I'm sorry, I encountered an error processing your query. Please try again or contact your healthcare provider."

# Create a global instance
fine_tuned_medgemma_ai = FineTunedMedGemmaAI()
