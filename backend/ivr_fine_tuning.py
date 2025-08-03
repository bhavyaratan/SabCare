import json
import os
import logging
from typing import Dict, List, Any
from pregnancy_rag_database import pregnancy_rag_db

class IVRFineTuning:
    def __init__(self):
        self.database_file = "pregnancy_rag_database.json"
        self.ivr_training_data = []
        self.patient_inquiry_data = []
        
    def load_database(self):
        """Load the pregnancy care database"""
        if os.path.exists(self.database_file):
            with open(self.database_file, 'r') as f:
                return json.load(f)
        return None
    
    def create_ivr_schedule_training_data(self):
        """Create training data for IVR schedule generation"""
        print("Creating IVR schedule training data...")
        
        data = self.load_database()
        if not data:
            print("Database not found")
            return []
        
        ivr_examples = []
        
        # Extract medication adherence data for IVR schedules
        for key, embedding_data in data.get('embeddings', {}).items():
            if embedding_data.get('category') == 'medication_adherence':
                text = embedding_data.get('text', '')
                
                # Create IVR schedule prompts
                ivr_examples.extend([
                    {
                        "input": f"Generate IVR reminder for {text}",
                        "output": f"Hello, this is your pregnancy care reminder. {text} Please take your medication as prescribed. Call your healthcare provider if you have any questions.",
                        "type": "medication_reminder"
                    },
                    {
                        "input": f"Create appointment reminder for {text}",
                        "output": f"Hello, this is your pregnancy care appointment reminder. Please remember to attend your scheduled appointment. {text}",
                        "type": "appointment_reminder"
                    },
                    {
                        "input": f"Generate monitoring reminder for {text}",
                        "output": f"Hello, this is your pregnancy care monitoring reminder. {text} Please monitor your symptoms and contact your healthcare provider if needed.",
                        "type": "monitoring_reminder"
                    }
                ])
        
        # Extract nutrition data for dietary reminders
        for key, embedding_data in data.get('embeddings', {}).items():
            if embedding_data.get('category') == 'nutrition':
                text = embedding_data.get('text', '')
                
                ivr_examples.extend([
                    {
                        "input": f"Create nutrition reminder for {text}",
                        "output": f"Hello, this is your pregnancy nutrition reminder. {text} Remember to maintain a healthy diet for you and your baby.",
                        "type": "nutrition_reminder"
                    }
                ])
        
        # Extract exercise data for activity reminders
        for key, embedding_data in data.get('embeddings', {}).items():
            if embedding_data.get('category') == 'exercise':
                text = embedding_data.get('text', '')
                
                ivr_examples.extend([
                    {
                        "input": f"Generate exercise reminder for {text}",
                        "output": f"Hello, this is your pregnancy exercise reminder. {text} Stay active and safe during your pregnancy.",
                        "type": "exercise_reminder"
                    }
                ])
        
        self.ivr_training_data = ivr_examples
        print(f"Created {len(ivr_examples)} IVR training examples")
        return ivr_examples
    
    def create_patient_inquiry_training_data(self):
        """Create training data for patient inquiry responses"""
        print("Creating patient inquiry training data...")
        
        data = self.load_database()
        if not data:
            print("Database not found")
            return []
        
        inquiry_examples = []
        
        # Extract all medical knowledge for patient inquiries
        for key, embedding_data in data.get('embeddings', {}).items():
            text = embedding_data.get('text', '')
            category = embedding_data.get('category', '')
            
            if text and len(text) > 10:  # Filter out very short entries
                # Create various inquiry scenarios
                inquiry_examples.extend([
                    {
                        "input": f"What should I know about {category} during pregnancy?",
                        "output": f"Based on medical guidelines: {text}",
                        "category": category,
                        "type": "general_inquiry"
                    },
                    {
                        "input": f"Is it safe to {text} during pregnancy?",
                        "output": f"Regarding safety during pregnancy: {text} Always consult your healthcare provider for personalized advice.",
                        "category": category,
                        "type": "safety_inquiry"
                    },
                    {
                        "input": f"What are the risks of {text} during pregnancy?",
                        "output": f"Risk assessment for pregnancy: {text} Monitor for any concerning symptoms and contact your healthcare provider.",
                        "category": category,
                        "type": "risk_inquiry"
                    },
                    {
                        "input": f"How should I manage {text} during pregnancy?",
                        "output": f"Management guidelines: {text} Follow your healthcare provider's recommendations closely.",
                        "category": category,
                        "type": "management_inquiry"
                    }
                ])
        
        self.patient_inquiry_data = inquiry_examples
        print(f"Created {len(inquiry_examples)} patient inquiry training examples")
        return inquiry_examples
    
    def generate_fine_tuning_dataset(self):
        """Generate complete fine-tuning dataset for MedGemma"""
        print("Generating complete fine-tuning dataset...")
        
        # Create IVR training data
        ivr_data = self.create_ivr_schedule_training_data()
        
        # Create patient inquiry training data
        inquiry_data = self.create_patient_inquiry_training_data()
        
        # Combine all training data
        complete_dataset = ivr_data + inquiry_data
        
        # Save the dataset
        dataset_file = "medgemma_fine_tuning_dataset.json"
        with open(dataset_file, 'w') as f:
            json.dump({
                "ivr_training_data": ivr_data,
                "patient_inquiry_data": inquiry_data,
                "complete_dataset": complete_dataset,
                "total_examples": len(complete_dataset),
                "ivr_examples": len(ivr_data),
                "inquiry_examples": len(inquiry_data)
            }, f, indent=2)
        
        print(f"✅ Complete dataset saved to {dataset_file}")
        print(f"📊 Total training examples: {len(complete_dataset)}")
        print(f"📞 IVR examples: {len(ivr_data)}")
        print(f"💬 Patient inquiry examples: {len(inquiry_data)}")
        
        return complete_dataset
    
    def create_specialized_training_sets(self):
        """Create specialized training sets for different use cases"""
        
        data = self.load_database()
        if not data:
            return {}
        
        specialized_sets = {
            "medication_adherence": [],
            "nutrition_guidance": [],
            "emergency_responses": [],
            "appointment_scheduling": [],
            "symptom_monitoring": []
        }
        
        # Medication adherence training set
        for key, embedding_data in data.get('embeddings', {}).items():
            if embedding_data.get('category') == 'medication_adherence':
                text = embedding_data.get('text', '')
                specialized_sets["medication_adherence"].append({
                    "input": f"Patient asks about medication adherence: {text}",
                    "output": f"Medication adherence guidance: {text} Take your medication exactly as prescribed and contact your healthcare provider with any concerns.",
                    "type": "medication_guidance"
                })
        
        # Nutrition guidance training set
        for key, embedding_data in data.get('embeddings', {}).items():
            if embedding_data.get('category') == 'nutrition':
                text = embedding_data.get('text', '')
                specialized_sets["nutrition_guidance"].append({
                    "input": f"Patient asks about nutrition: {text}",
                    "output": f"Nutrition guidance: {text} Maintain a balanced diet for optimal pregnancy health.",
                    "type": "nutrition_guidance"
                })
        
        # Emergency responses training set
        for key, embedding_data in data.get('embeddings', {}).items():
            if embedding_data.get('category') == 'emergencies':
                text = embedding_data.get('text', '')
                specialized_sets["emergency_responses"].append({
                    "input": f"Patient reports emergency: {text}",
                    "output": f"Emergency response: {text} Seek immediate medical attention if you experience these symptoms.",
                    "type": "emergency_response"
                })
        
        return specialized_sets

# Global instance
ivr_fine_tuner = IVRFineTuning() 