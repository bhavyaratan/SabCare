import json
import logging
import os
from typing import Dict, Any, List
from datetime import datetime
import time
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, TrainingArguments, Trainer
from datasets import Dataset
from pregnancy_rag_database import pregnancy_rag_db
from medgemma import medgemma_ai

class GemmaFineTuner:
    def __init__(self):
        self.model_name = "microsoft/DialoGPT-small"  # Current model
        self.fine_tuned_model_path = "fine_tuned_pregnancy_gemma"
        self.training_data = []
        self.tokenizer = None
        self.model = None
        
    def prepare_training_data(self):
        """Prepare training data from the pregnancy care database"""
        print("Preparing training data from pregnancy care database...")
        
        # Load the pregnancy care database
        if os.path.exists("pregnancy_rag_database.json"):
            with open("pregnancy_rag_database.json", 'r') as f:
                data = json.load(f)
                knowledge_base = data.get('knowledge_base', {})
        else:
            print("Pregnancy care database not found. Generating it first...")
            pregnancy_rag_db.generate_medgemma_embeddings()
            with open("pregnancy_rag_database.json", 'r') as f:
                data = json.load(f)
                knowledge_base = data.get('knowledge_base', {})
        
        # Convert database entries to training examples
        training_examples = []
        
        for category, subcategories in knowledge_base.items():
            for subcategory, content in subcategories.items():
                if isinstance(content, dict):
                    # Create training examples from medical content
                    if 'content' in content and content.get('source') == 'medgemma':
                        medical_content = content['content']
                        
                        # Create various training scenarios
                        training_examples.extend(self.create_training_scenarios(
                            medical_content, category, subcategory
                        ))
        
        self.training_data = training_examples
        print(f"Prepared {len(self.training_data)} training examples")
        return training_examples
    
    def create_training_scenarios(self, medical_content: str, category: str, subcategory: str) -> List[Dict[str, str]]:
        """Create training scenarios from medical content"""
        scenarios = []
        
        # Scenario 1: Direct medical question
        if "trimester" in category.lower():
            question = f"What should I know about {subcategory} during pregnancy?"
            scenarios.append({
                "input": question,
                "output": medical_content,
                "category": category,
                "type": "direct_question"
            })
        
        # Scenario 2: Symptom-based question
        if "complications" in category.lower():
            question = f"What are the warning signs I should watch for?"
            scenarios.append({
                "input": question,
                "output": medical_content,
                "category": category,
                "type": "symptom_question"
            })
        
        # Scenario 3: Management question
        if "risk_factors" in category.lower():
            question = f"How should this condition be managed during pregnancy?"
            scenarios.append({
                "input": question,
                "output": medical_content,
                "category": category,
                "type": "management_question"
            })
        
        # Scenario 4: Nutrition question
        if "nutrition" in category.lower():
            question = f"What should I eat for {subcategory} during pregnancy?"
            scenarios.append({
                "input": question,
                "output": medical_content,
                "category": category,
                "type": "nutrition_question"
            })
        
        # Scenario 5: Medication question
        if "medications" in category.lower():
            question = f"Is this medication safe during pregnancy?"
            scenarios.append({
                "input": question,
                "output": medical_content,
                "category": category,
                "type": "medication_question"
            })
        
        return scenarios
    
    def format_for_training(self, training_examples: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Format training examples for model fine-tuning"""
        formatted_data = []
        
        for example in training_examples:
            # Create conversation format for DialoGPT
            conversation = f"Patient: {example['input']}\nDoctor: {example['output']}"
            
            formatted_data.append({
                "text": conversation,
                "category": example.get('category', 'general'),
                "type": example.get('type', 'general')
            })
        
        return formatted_data
    
    def load_model_and_tokenizer(self):
        """Load the base model and tokenizer"""
        print("Loading base model and tokenizer...")
        
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForCausalLM.from_pretrained(self.model_name)
            
            # Add padding token if not present
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            
            print("Model and tokenizer loaded successfully")
            
        except Exception as e:
            print(f"Error loading model: {e}")
            # Fallback to a simpler model if needed
            self.tokenizer = AutoTokenizer.from_pretrained("gpt2")
            self.model = AutoModelForCausalLM.from_pretrained("gpt2")
    
    def prepare_dataset(self, formatted_data: List[Dict[str, str]]) -> Dataset:
        """Prepare dataset for fine-tuning"""
        print("Preparing dataset for fine-tuning...")
        
        # Tokenize the data
        def tokenize_function(examples):
            return self.tokenizer(
                examples["text"],
                truncation=True,
                padding="max_length",
                max_length=512,
                return_tensors="pt"
            )
        
        # Create dataset
        dataset = Dataset.from_dict({
            "text": [item["text"] for item in formatted_data],
            "category": [item["category"] for item in formatted_data],
            "type": [item["type"] for item in formatted_data]
        })
        
        # Tokenize dataset
        tokenized_dataset = dataset.map(tokenize_function, batched=True)
        
        return tokenized_dataset
    
    def fine_tune_model(self, dataset: Dataset):
        """Fine-tune the model on pregnancy care data"""
        print("Starting fine-tuning process...")
        
        # Training arguments
        training_args = TrainingArguments(
            output_dir=self.fine_tuned_model_path,
            num_train_epochs=3,
            per_device_train_batch_size=4,
            per_device_eval_batch_size=4,
            warmup_steps=500,
            weight_decay=0.01,
            logging_dir=f"{self.fine_tuned_model_path}/logs",
            logging_steps=100,
            save_steps=1000,
            eval_steps=1000,
            evaluation_strategy="steps",
            load_best_model_at_end=True,
            save_total_limit=2,
        )
        
        # Initialize trainer
        trainer = Trainer(
            model=self.model,
            args=training_args,
            train_dataset=dataset,
            tokenizer=self.tokenizer,
        )
        
        # Start fine-tuning
        print("Training the model...")
        trainer.train()
        
        # Save the fine-tuned model
        trainer.save_model()
        self.tokenizer.save_pretrained(self.fine_tuned_model_path)
        
        print(f"Fine-tuned model saved to {self.fine_tuned_model_path}")
    
    def test_fine_tuned_model(self, test_queries: List[str]):
        """Test the fine-tuned model with sample queries"""
        print("Testing fine-tuned model...")
        
        # Load fine-tuned model
        fine_tuned_tokenizer = AutoTokenizer.from_pretrained(self.fine_tuned_model_path)
        fine_tuned_model = AutoModelForCausalLM.from_pretrained(self.fine_tuned_model_path)
        
        results = []
        for query in test_queries:
            # Format input
            input_text = f"Patient: {query}\nDoctor:"
            
            # Tokenize
            inputs = fine_tuned_tokenizer.encode(input_text, return_tensors="pt")
            
            # Generate response
            with torch.no_grad():
                outputs = fine_tuned_model.generate(
                    inputs,
                    max_length=200,
                    num_return_sequences=1,
                    temperature=0.7,
                    do_sample=True,
                    pad_token_id=fine_tuned_tokenizer.eos_token_id
                )
            
            # Decode response
            response = fine_tuned_tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            results.append({
                "query": query,
                "response": response,
                "model": "fine_tuned"
            })
        
        return results
    
    def compare_responses(self, test_queries: List[str]):
        """Compare responses between base model and fine-tuned model"""
        print("Comparing base model vs fine-tuned model responses...")
        
        # Test base model
        base_results = []
        for query in test_queries:
            response = medgemma_ai.process_medical_query(query, "", "")
            base_results.append({
                "query": query,
                "response": response,
                "model": "base"
            })
        
        # Test fine-tuned model
        fine_tuned_results = self.test_fine_tuned_model(test_queries)
        
        return {
            "base_model": base_results,
            "fine_tuned_model": fine_tuned_results
        }

# Global instance
gemma_fine_tuner = GemmaFineTuner() 