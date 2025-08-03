[README.md](https://github.com/user-attachments/files/21568334/README.md)
A comprehensive pregnancy care system that processes patient prescriptions, creates personalized care schedules, and provides voice-based medical assistance in Hindi and English.

## 🎯 System Overview

### Workflow Process:
1. **Input:** Patient prescription (text/image) → Extract patient info
2. **Schedule Creation:** Generate personalized care schedule based on gestational age
3. **Outbound Messages:** Send scheduled voice reminders (TTS)
4. **Inbound Calls:** Handle patient complaints → Convert to text → Process with Gemma → Call back with answer

## 🚀 Quick Start

### 1. Start n8n
```bash
n8n start
```
Access at: http://localhost:5678

### 2. Create Project
- Open http://localhost:5678
- Create new project: "MedGemmaCare"

### 3. Set Up Credentials
Go to "Credentials" tab and add:

#### Twilio Credentials
- **Name:** "Twilio Account"
- **Account SID:** Your Twilio SID
- **Auth Token:** Your Twilio token
- **From Phone Number:** Your Twilio number

#### TTS API Credentials
- **Name:** "TTS Service"
- **URL:** Your TTS API endpoint
- **API Key:** Your TTS API key

#### Speech-to-Text API Credentials
- **Name:** "STT Service"
- **URL:** Your STT API endpoint
- **API Key:** Your STT API key

#### Gemma3n API Credentials
- **Name:** "Gemma3n API"
- **URL:** Your Gemma3n API endpoint
- **API Key:** Your API key

### 4. Import Workflows

#### Workflow 1: Patient Data Processing
1. Copy content from `patient_processing_workflow.json`
2. In n8n, click "Import from JSON"
3. Paste the JSON and import
4. Save and activate the workflow

#### Workflow 2: Voice Message Scheduler
1. Copy content from `voice_message_workflow.json`
2. Import as above
3. Update the URLs to point to your actual APIs
4. Save and activate

#### Workflow 3: Inbound Call Handler
1. Copy content from `inbound_call_workflow.json`
2. Import as above
3. Update the URLs to point to your actual APIs
4. Save and activate

## 🧪 Testing

### Test Patient Data Processing
```bash
curl -X POST http://localhost:5678/webhook/patient-data \
  -H 'Content-Type: application/json' \
  -d @test_patient_data.json
```

### Test Inbound Call Handling
```bash
curl -X POST http://localhost:5678/webhook/inbound-call \
  -H 'Content-Type: application/json' \
  -d '{"CallSid":"test123","From":"+919876543210","To":"+911234567890"}'
```

## 📞 Twilio Setup

### 1. Configure Webhook URL
Set your Twilio webhook URL to:
```
https://your-domain.com/webhook/inbound-call
```

### 2. Set up TwiML for Call Recording
```xml
<Response>
  <Record action="/webhook/inbound-call" maxLength="60"/>
</Response>
```

## 🎯 Pilot Testing Plan

### Phase 1: Research
1. **Interview 1 obstetrician doctor**
   - Understand current care processes
   - Identify pain points
   - Validate medical content

### Phase 2: User Research
2. **Interview 5-10 mothers**
   - Understand their needs
   - Test message content
   - Validate voice interface

### Phase 3: Pilot Testing
3. **Test with 5-10 personalized messages**
   - Send scheduled reminders
   - Test inbound call handling
   - Collect feedback

### Phase 4: Iteration
4. **Collect feedback and iterate**
   - Refine message content
   - Improve voice quality
   - Optimize timing

## 📁 File Structure

```
├── patient_processing_workflow.json    # Patient data processing workflow
├── voice_message_workflow.json         # Voice message scheduler
├── inbound_call_workflow.json          # Inbound call handler
├── test_patient_data.json             # Sample patient data
├── setup_n8n_workflows.sh             # Setup script
└── README.md                          # This file
```

## 🔧 Configuration

### Update API Endpoints
In each workflow, update these URLs:
- `https://your-tts-api.com/convert` → Your TTS API
- `https://your-speech-to-text-api.com/transcribe` → Your STT API
- `https://your-gemma-api.com/query` → Your Gemma3n API
- `https://your-database-api.com/patients/schedule` → Your database API

### Voice Settings
- **Language:** Hindi (hi-IN)
- **Voice:** hi-IN-NeerjaNeural (Microsoft Azure)
- **Fallback:** English (en-US)

## 🎯 Sample Patient Data

Based on the prescription image, here's the extracted data:
- **Name:** Asha Shankar
- **Age:** 22 years
- **Gestational Age:** 8 weeks + 4 days
- **EDD:** March 4, 2026
- **Complaints:** No bleeding, no vomiting, nausea, mild fatigue
- **Advice:** USG, Iron Folic Acid, Calcium tablets

## 🚀 Next Steps

1. **Set up your APIs:**
   - Deploy Gemma3n model
   - Set up TTS service
   - Set up Speech-to-Text service

2. **Configure Twilio:**
   - Set up phone numbers
   - Configure webhooks
   - Test call flow

3. **Run pilot tests:**
   - Test with sample patients
   - Validate message content
   - Optimize timing

4. **Scale up:**
   - Add more patients
   - Expand message library
   - Add more languages

## 📞 Support

For technical issues or questions, refer to the n8n documentation or contact the development team.

---

**Built with ❤️ for better maternal healthcare** 
