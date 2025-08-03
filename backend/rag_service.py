import json
import requests
from typing import List, Dict, Any, Optional
import os
import numpy as np
from datetime import datetime

class RAGService:
    def __init__(self):
        self.medical_guidelines = {
            "pregnancy_nutrition": [
                "Take prenatal vitamins daily with folic acid, iron, and calcium",
                "Eat a balanced diet with plenty of fruits, vegetables, lean proteins, and whole grains",
                "Stay hydrated by drinking 8-10 glasses of water daily",
                "Avoid raw fish, unpasteurized dairy, and excessive caffeine",
                "Gain appropriate weight: 25-35 pounds for normal BMI, 28-40 pounds for underweight, 15-25 pounds for overweight"
            ],
            "pregnancy_exercise": [
                "Engage in moderate exercise for 30 minutes most days",
                "Safe activities include walking, swimming, prenatal yoga, and low-impact aerobics",
                "Avoid contact sports, scuba diving, and activities with high fall risk",
                "Stop exercise if you experience dizziness, chest pain, or vaginal bleeding",
                "Consult your healthcare provider before starting any new exercise program"
            ],
            "pregnancy_monitoring": [
                "Track fetal movements daily - should feel at least 10 movements in 2 hours",
                "Monitor blood pressure regularly, especially if you have hypertension",
                "Watch for signs of preeclampsia: severe headaches, vision changes, swelling",
                "Report decreased fetal movement immediately to your healthcare provider",
                "Attend all scheduled prenatal appointments"
            ],
            "medication_safety": [
                "Always consult your healthcare provider before taking any medication",
                "Continue prescribed medications unless specifically told to stop",
                "Take medications at the same time each day for consistency",
                "Store medications properly and check expiration dates",
                "Report any side effects or concerns to your healthcare provider immediately"
            ],
            "high_risk_pregnancy": [
                "More frequent prenatal visits may be required",
                "Additional monitoring and testing may be necessary",
                "Follow all medical recommendations strictly",
                "Report any concerning symptoms immediately",
                "Consider consulting with a maternal-fetal medicine specialist"
            ],
            "diabetes_management": [
                "Monitor blood sugar levels regularly as recommended",
                "Follow a consistent meal plan with carbohydrate counting",
                "Exercise regularly to help control blood sugar",
                "Take diabetes medications as prescribed",
                "Report any blood sugar readings outside the target range"
            ],
            "hypertension_management": [
                "Monitor blood pressure regularly at home",
                "Take blood pressure medications as prescribed",
                "Reduce salt intake and follow a heart-healthy diet",
                "Report any sudden increases in blood pressure",
                "Watch for signs of preeclampsia: severe headaches, vision changes"
            ]
        }
        
        # Initialize embedding model (placeholder for now)
        self.embedding_model = None
        self.initialize_embeddings()
    
    def initialize_embeddings(self):
        """Initialize embedding model for generating embeddings"""
        try:
            # For now, we'll use a simple hash-based embedding
            # In production, you'd use a proper embedding model like sentence-transformers
            print("RAG Service: Using simple hash-based embeddings")
        except Exception as e:
            print(f"Failed to initialize embedding model: {e}")
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text (placeholder implementation)"""
        # Simple hash-based embedding for demonstration
        # In production, use sentence-transformers or similar
        import hashlib
        
        # Create a simple embedding based on text hash
        hash_obj = hashlib.md5(text.encode())
        hash_bytes = hash_obj.digest()
        
        # Convert to 128-dimensional embedding
        embedding = []
        for i in range(0, len(hash_bytes), 4):
            chunk = hash_bytes[i:i+4]
            value = int.from_bytes(chunk, byteorder='big')
            embedding.append(value / 2**32)  # Normalize to [0,1]
        
        # Pad or truncate to 128 dimensions
        while len(embedding) < 128:
            embedding.append(0.0)
        embedding = embedding[:128]
        
        return embedding
    
    def generate_patient_embeddings(self, patient_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate embeddings for patient-specific medical context"""
        embeddings = {}
        
        # Generate embeddings for different aspects of patient data
        if patient_data.get("diagnosis"):
            embeddings["diagnosis"] = self.generate_embedding(patient_data["diagnosis"])
        
        if patient_data.get("risk_factors"):
            embeddings["risk_factors"] = self.generate_embedding(patient_data["risk_factors"])
        
        if patient_data.get("medication_schedule"):
            embeddings["medication_schedule"] = self.generate_embedding(patient_data["medication_schedule"])
        
        if patient_data.get("summary"):
            embeddings["summary"] = self.generate_embedding(patient_data["summary"])
        
        # Generate embeddings for relevant medical guidelines
        relevant_guidelines = self.get_relevant_guidelines_for_patient(patient_data)
        embeddings["medical_guidelines"] = self.generate_embedding(relevant_guidelines)
        
        return embeddings
    
    def get_relevant_guidelines_for_patient(self, patient_data: Dict[str, Any]) -> str:
        """Get relevant medical guidelines based on patient data"""
        guidelines = []
        risk_factors = patient_data.get("risk_factors", "").split(", ") if patient_data.get("risk_factors") else []
        
        # Add general pregnancy guidelines
        guidelines.extend(self.medical_guidelines["pregnancy_monitoring"])
        guidelines.extend(self.medical_guidelines["pregnancy_nutrition"])
        
        # Add medication guidelines if patient has medications
        if patient_data.get("medication_schedule"):
            guidelines.extend(self.medical_guidelines["medication_safety"])
        
        # Add risk-specific guidelines
        if risk_factors:
            if any("diabetes" in risk.lower() for risk in risk_factors):
                guidelines.extend(self.medical_guidelines["diabetes_management"])
            if any("hypertension" in risk.lower() for risk in risk_factors):
                guidelines.extend(self.medical_guidelines["hypertension_management"])
            if any(risk in ["high_risk", "advanced_maternal_age", "multiple_pregnancy"] for risk in risk_factors):
                guidelines.extend(self.medical_guidelines["high_risk_pregnancy"])
        
        return "\n".join(guidelines)
    
    def create_patient_medical_context(self, patient_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create comprehensive medical context for patient"""
        medical_context = {
            "patient_info": {
                "name": patient_data.get("name", ""),
                "age": patient_data.get("age", ""),
                "gestational_age": self.extract_gestational_age(patient_data.get("diagnosis", "")),
                "risk_category": patient_data.get("risk_category", "low"),
                "bmi": patient_data.get("bmi", ""),
                "race": patient_data.get("race", "")
            },
            "medical_data": {
                "diagnosis": patient_data.get("diagnosis", ""),
                "risk_factors": patient_data.get("risk_factors", ""),
                "medications": patient_data.get("medication_schedule", ""),
                "additional_notes": patient_data.get("additional_notes", "")
            },
            "guidelines": self.get_relevant_guidelines_for_patient(patient_data),
            "last_updated": datetime.now().isoformat()
        }
        
        return medical_context
    
    def extract_gestational_age(self, diagnosis: str) -> int:
        """Extract gestational age from diagnosis"""
        import re
        match = re.search(r"Week (\d+)", diagnosis)
        return int(match.group(1)) if match else 0
    
    def get_relevant_guidelines(self, topic: str, risk_factors: List[str] = None) -> str:
        """Get relevant medical guidelines based on topic and risk factors"""
        guidelines = []
        
        # Add general pregnancy guidelines
        if "pregnancy" in topic.lower() or "check-in" in topic.lower():
            guidelines.extend(self.medical_guidelines["pregnancy_monitoring"])
            guidelines.extend(self.medical_guidelines["pregnancy_nutrition"])
        
        # Add exercise guidelines for general check-ins
        if "exercise" in topic.lower() or "activity" in topic.lower():
            guidelines.extend(self.medical_guidelines["pregnancy_exercise"])
        
        # Add medication guidelines for medication reminders
        if "medication" in topic.lower() or "reminder" in topic.lower():
            guidelines.extend(self.medical_guidelines["medication_safety"])
        
        # Add risk-specific guidelines
        if risk_factors:
            if "diabetes" in risk_factors:
                guidelines.extend(self.medical_guidelines["diabetes_management"])
            if "hypertension" in risk_factors:
                guidelines.extend(self.medical_guidelines["hypertension_management"])
            if any(risk in risk_factors for risk in ["high_risk", "advanced_maternal_age", "multiple_pregnancy"]):
                guidelines.extend(self.medical_guidelines["high_risk_pregnancy"])
        
        return "\n".join(guidelines)
    
    def enhance_message_with_guidelines(self, base_message: str, topic: str, risk_factors: List[str] = None) -> str:
        """Enhance a base message with relevant medical guidelines"""
        guidelines = self.get_relevant_guidelines(topic, risk_factors)
        
        if guidelines:
            enhanced_message = f"{base_message}\n\nBased on medical guidelines:\n{guidelines}"
        else:
            enhanced_message = base_message
        
        return enhanced_message
    
    def enhance_message_with_patient_context(self, base_message: str, patient_data: Dict[str, Any], topic: str) -> str:
        """Enhance message with patient-specific context and embeddings"""
        # Get patient-specific guidelines
        patient_guidelines = self.get_relevant_guidelines_for_patient(patient_data)
        
        # Create personalized message
        personalized_message = f"{base_message}\n\nBased on your specific medical profile:\n{patient_guidelines}"
        
        return personalized_message

# Global instance
rag_service = RAGService() 