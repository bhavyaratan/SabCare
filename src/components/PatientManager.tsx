import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Separator } from "@/components/ui/separator";
import { Plus, User, Clock, Phone, FileText, AlertCircle, RefreshCw, MessageSquare } from "lucide-react";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from "@/components/ui/dialog";
import React from "react"; // Added missing import for React
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";

interface Patient {
  id: string;
  name: string;
  diagnosis: string;
  phone: string;
  description: string;
  medication_schedule: string;
  call_schedule: string;
  medications: Array<{
    name: string;
    dosage: string;
    times: string[];
  }>;
  callSchedule: string[];
  lastCall: string;
  adherenceRate: number;
  status: "active" | "alert" | "missed";
  race: string;
  height: string;
  weight: string;
  bmi: string;
  age: string;
  risk_factors: string;
  additional_notes: string;
  risk_category: "low" | "medium" | "high";
  // Postnatal Care Fields
  delivery_date?: string;
  delivery_type?: string;
  is_postpartum?: boolean;
  postpartum_week?: number;
  // Patient Metrics Fields
  total_calls_scheduled?: number;
  total_calls_completed?: number;
  total_calls_failed?: number;
  total_calls_missed?: number;
  call_success_rate?: number;
  average_call_duration?: number;
  last_call_date?: string;
  last_call_status?: string;
}

export const PatientManager = () => {
  const [patients, setPatients] = useState<Patient[]>([]);
  const [selectedPatient, setSelectedPatient] = useState<Patient | null>(null);
  const [editingPatient, setEditingPatient] = useState<Patient | null>(null);
  const [deletingPatient, setDeletingPatient] = useState<Patient | null>(null);
  const [showAddForm, setShowAddForm] = useState(false);

  useEffect(() => {
    fetchPatients();
  }, []);

  const fetchPatients = async () => {
    try {
      const response = await fetch('http://localhost:8000/patients/');
      if (!response.ok) {
        throw new Error('Failed to fetch patients');
      }
      const data = await response.json();
      console.log("=== FETCHED PATIENTS ===");
      console.log("Raw patient data:", data);
      console.log("First patient:", data[0]);
      console.log("First patient description:", data[0]?.description);
      setPatients(data.map((p: any) => ({
        id: p.id,
        name: p.name,
        diagnosis: p.diagnosis,
        phone: p.phone,
        description: p.summary,
        medication_schedule: p.medication_schedule,
        call_schedule: p.call_schedule,
        medications: p.medications || [],
        callSchedule: p.callSchedule || [],
        lastCall: p.lastCall || "",
        adherenceRate: p.adherenceRate || 0,
        status: p.status || "active",
        race: p.race || "",
        age: p.age || "",
        height: p.height || "",
        weight: p.weight || "",
        bmi: p.bmi || "",
        risk_factors: p.risk_factors || "",
        additional_notes: p.additional_notes || "",
        risk_category: p.risk_category || "low",
        // Postnatal Care Fields
        delivery_date: p.delivery_date || undefined,
        delivery_type: p.delivery_type || undefined,
        is_postpartum: p.is_postpartum || false,
        postpartum_week: p.postpartum_week || undefined,
        // Patient Metrics Fields
        total_calls_scheduled: p.total_calls_scheduled || undefined,
        total_calls_completed: p.total_calls_completed || undefined,
        total_calls_failed: p.total_calls_failed || undefined,
        total_calls_missed: p.total_calls_missed || undefined,
        call_success_rate: p.call_success_rate || undefined,
        average_call_duration: p.average_call_duration || undefined,
        last_call_date: p.last_call_date || undefined,
        last_call_status: p.last_call_status || undefined
      })));
    } catch (error) {
      console.error('Error fetching patients:', error);
    }
  };

  const handleDelete = async (id: string) => {
    await fetch(`http://localhost:8000/patients/${id}`, { method: "DELETE" });
    setDeletingPatient(null);
    fetchPatients();
  };

  const getStatusColor = (status: Patient["status"]) => {
    switch (status) {
      case "active": return "bg-medical-green";
      case "alert": return "bg-medical-orange";
      case "missed": return "bg-medical-red";
      default: return "bg-muted";
    }
  };

  const getStatusText = (status: Patient["status"]) => {
    switch (status) {
      case "active": return "Active";
      case "alert": return "Alert";
      case "missed": return "Missed Call";
      default: return "Unknown";
    }
  };

  const getRiskColor = (risk_category: Patient["risk_category"]) => {
    switch (risk_category) {
      case "low":
        return "bg-green-100 text-green-800 border-green-200";
      case "medium":
        return "bg-yellow-100 text-yellow-800 border-yellow-200";
      case "high":
        return "bg-red-100 text-red-800 border-red-200";
      default:
        return "bg-gray-100 text-gray-800 border-gray-200";
    }
  };

  const getRiskText = (risk_category: string) => {
    switch (risk_category) {
      case "low":
        return "Low Risk";
      case "medium":
        return "Medium Risk";
      case "high":
        return "High Risk";
      default:
        return "Unknown";
    }
  };

  const getCallFrequency = (risk_category: string) => {
    switch (risk_category) {
      case "low":
        return "biweekly";
      case "medium":
        return "weekly";
      case "high":
        return "twice-weekly";
      default:
        return "biweekly";
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Patient Management</h2>
          <p className="text-muted-foreground">
            Manage patient records and medication schedules
          </p>
        </div>
        <Dialog open={showAddForm} onOpenChange={setShowAddForm}>
          <DialogTrigger asChild>
            <Button className="flex items-center gap-2">
              <Plus className="h-4 w-4" />
              Add Patient
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>Add New Patient</DialogTitle>
              <DialogDescription>
                Enter details manually
              </DialogDescription>
            </DialogHeader>
            <AddPatientForm 
              onClose={() => { 
                console.log("=== FORM CLOSING ===");
                setShowAddForm(false); 
                fetchPatients(); 
              }} 
              onPatientUpdated={fetchPatients} 
            />
          </DialogContent>
        </Dialog>
        {/* Edit Patient Dialog */}
        <Dialog open={!!editingPatient} onOpenChange={v => { if (!v) setEditingPatient(null); }}>
          <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>Edit Patient</DialogTitle>
              <DialogDescription>
                Update patient details
              </DialogDescription>
            </DialogHeader>
            {editingPatient && (
              <EditPatientForm
                onClose={() => { setEditingPatient(null); fetchPatients(); }}
                patient={editingPatient}
                onPatientUpdated={fetchPatients}
              />
            )}
          </DialogContent>
        </Dialog>
        {/* Delete Patient Dialog */}
        <Dialog open={!!deletingPatient} onOpenChange={v => { if (!v) setDeletingPatient(null); }}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Delete Patient</DialogTitle>
              <DialogDescription>
                Are you sure you want to delete this patient?
              </DialogDescription>
            </DialogHeader>
            <div className="flex justify-end gap-2 mt-4">
              <Button variant="outline" onClick={() => setDeletingPatient(null)}>
                Cancel
              </Button>
              <Button variant="destructive" onClick={() => handleDelete(deletingPatient!.id)}>
                Delete
              </Button>
      </div>
          </DialogContent>
        </Dialog>
      </div>
      {/* Patient List */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="space-y-4">
          <h3 className="text-lg font-semibold">Active Patients</h3>
          {patients.map((patient) => (
            <Card 
              key={patient.id} 
              className={`cursor-pointer transition-all hover:shadow-md ${
                selectedPatient?.id === patient.id ? "ring-2 ring-primary" : ""
              }`}
              onClick={() => setSelectedPatient(patient)}
            >
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-lg flex items-center gap-2">
                    <User className="h-4 w-4" />
                    {patient.name}
                  </CardTitle>
                  <Badge variant="secondary" className={`${getRiskColor(patient.risk_category)}`}>
                    {getRiskText(patient.risk_category)} ({getCallFrequency(patient.risk_category)})
                  </Badge>
                </div>
                <CardDescription>{patient.diagnosis}</CardDescription>
              </CardHeader>
              <CardContent className="space-y-2">
                <div className="flex items-center gap-2 text-sm">
                  <Phone className="h-3 w-3" />
                  {patient.phone}
                </div>
                <div className="flex items-center gap-2 text-sm">
                  <Clock className="h-3 w-3" />
                  Last call: {patient.lastCall}
                </div>
                <div className="flex gap-2 mt-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      console.log("=== EDIT BUTTON CLICKED ===");
                      console.log("Patient to edit:", patient);
                      console.log("Patient description:", patient.description);
                      setSelectedPatient(patient);
                      setEditingPatient(patient); // Use the separate edit form
                    }}
                  >
                    Edit
                  </Button>
                  <Button size="sm" variant="destructive" onClick={e => { e.stopPropagation(); setDeletingPatient(patient); }}>
                    Delete
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
        {/* Patient Details unchanged */}
        <div>
          {selectedPatient ? (
            <PatientDetails patient={selectedPatient} />
          ) : (
            <Card className="h-full flex items-center justify-center">
              <CardContent>
                <div className="text-center text-muted-foreground">
                  <User className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>Select a patient to view details</p>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
};

const PatientDetails = ({ patient }: { patient: any }) => {
  const [loadingIvr, setLoadingIvr] = useState(false);
  const [ivrSchedule, setIvrSchedule] = useState<any[]>([]);

  const getRiskColor = (risk_category: string) => {
    switch (risk_category) {
      case "low":
        return "bg-green-100 text-green-800 border-green-200";
      case "medium":
        return "bg-yellow-100 text-yellow-800 border-yellow-200";
      case "high":
        return "bg-red-100 text-red-800 border-red-200";
      default:
        return "bg-gray-100 text-gray-800 border-gray-200";
    }
  };

  const getRiskText = (risk_category: string) => {
    switch (risk_category) {
      case "low":
        return "Low Risk";
      case "medium":
        return "Medium Risk";
      case "high":
        return "High Risk";
      default:
        return "Unknown";
    }
  };

  const getCallFrequency = (risk_category: string) => {
    switch (risk_category) {
      case "low":
        return "biweekly";
      case "medium":
        return "weekly";
      case "high":
        return "twice-weekly";
      default:
        return "biweekly";
    }
  };

  const fetchIvrSchedule = async () => {
    if (!patient.id) return;
    
    setLoadingIvr(true);
    try {
      // Instead of calling the API, parse the call_schedule directly from patient data
      if (patient.call_schedule) {
        try {
          const scheduleData = JSON.parse(patient.call_schedule);
          console.log("Parsed call schedule:", scheduleData);
          
          // Handle both array format and object with schedule property
          const scheduleArray = Array.isArray(scheduleData) ? scheduleData : 
                              (scheduleData.schedule && Array.isArray(scheduleData.schedule)) ? scheduleData.schedule : [];
          
          setIvrSchedule(scheduleArray);
        } catch (parseError) {
          console.error("Failed to parse call_schedule:", parseError);
          setIvrSchedule([]);
        }
      } else {
        setIvrSchedule([]);
      }
    } catch (error) {
      console.error("Failed to fetch IVR schedule:", error);
      setIvrSchedule([]);
    } finally {
      setLoadingIvr(false);
    }
  };

  const generateNewIvrSchedule = async () => {
    if (!patient.id) return;
    
    setLoadingIvr(true);
    try {
      // Extract gestational age from diagnosis
      const gestationalAgeMatch = patient.diagnosis?.match(/Week (\d+)/);
      const gestationalAge = gestationalAgeMatch ? parseInt(gestationalAgeMatch[1]) : 20;
      
      // Parse risk factors
      const riskFactors = patient.risk_factors ? patient.risk_factors.split(',').map(f => f.trim()) : [];
      
      // Create structured medications
      const structuredMedications = patient.medications?.map(med => ({
        name: med.name,
        dosage: med.dosage,
        time: "09:00 AM",
        days: ["Monday", "Wednesday", "Friday"]
      })) || [];
      
      const response = await fetch(`http://localhost:8000/generate_comprehensive_ivr_schedule`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          patient_name: patient.name,
          gestational_age_weeks: gestationalAge,
          risk_factors: riskFactors,
          risk_category: patient.risk_category || "low",
          structured_medications: structuredMedications,
          patient_data: {
            medications: patient.medications || [],
            allergies: [],
            medical_history: [patient.diagnosis]
          }
        })
      });
      
      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          console.log("Generated new IVR schedule:", data);
          // Update the patient's call schedule
          await fetch(`http://localhost:8000/patients/${patient.id}`, {
            method: 'PUT',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              call_schedule: JSON.stringify(data.schedule)
            })
          });
          // Refresh the IVR schedule
          fetchIvrSchedule();
        }
      }
    } catch (error) {
      console.error("Failed to generate IVR schedule:", error);
    } finally {
      setLoadingIvr(false);
    }
  };

  // Check if this is a pregnancy patient
  const isPregnancyPatient = patient.diagnosis?.toLowerCase().includes("pregnancy") || 
                            patient.diagnosis?.toLowerCase().includes("week");

  React.useEffect(() => {
    if (isPregnancyPatient) {
      fetchIvrSchedule();
    }
  }, [patient.id, isPregnancyPatient]);

  // Use the state-based ivrSchedule instead of useMemo
  // The schedule is now fetched from the backend and stored in state

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <FileText className="h-5 w-5" />
          Patient Record
        </CardTitle>
        <CardDescription>Detailed patient information and schedule</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Basic Info */}
        <div>
          <h4 className="font-semibold mb-2">Patient Information</h4>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <Label className="text-muted-foreground">Name</Label>
              <p className="font-medium">{patient.name}</p>
            </div>
            <div>
              <Label className="text-muted-foreground">Phone</Label>
              <p className="font-medium">{patient.phone}</p>
            </div>
            <div>
              <Label className="text-muted-foreground">Diagnosis</Label>
              <p className="font-medium">{patient.diagnosis}</p>
            </div>
            <div>
              <Label className="text-muted-foreground">Risk Category</Label>
              <p className="font-medium">{getRiskText(patient.risk_category)} ({getCallFrequency(patient.risk_category)} calls)</p>
          </div>
            <div>
              <Label className="text-muted-foreground">Race</Label>
              <p className="font-medium">{patient.race || "Not specified"}</p>
        </div>
        <div>
              <Label className="text-muted-foreground">Height</Label>
              <p className="font-medium">{patient.height ? `${patient.height} cm` : "Not specified"}</p>
                </div>
        <div>
              <Label className="text-muted-foreground">Weight</Label>
              <p className="font-medium">{patient.weight ? `${patient.weight} kg` : "Not specified"}</p>
              </div>
        <div>
              <Label className="text-muted-foreground">BMI</Label>
              <p className="font-medium">
                {(() => {
                  if (patient.height && patient.weight) {
                    const heightM = parseFloat(patient.height) / 100;
                    const weightKg = parseFloat(patient.weight);
                    if (heightM > 0 && weightKg > 0) {
                      return (weightKg / (heightM * heightM)).toFixed(1);
                    }
                  }
                  return patient.bmi || "Not calculated";
                })()}
                </p>
              </div>
            <div className="col-span-2">
              <Label className="text-muted-foreground">Description</Label>
              <p className="font-medium whitespace-pre-line">{patient.description}</p>
            </div>
          </div>
        </div>

        {/* IVR System Status */}
        <div className="space-y-4">
          <h4 className="font-semibold flex items-center gap-2">
            <MessageSquare className="h-4 w-4" />
            IVR System Status
          </h4>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 bg-green-500 rounded-full"></div>
              <span className="text-sm">Backend API</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 bg-green-500 rounded-full"></div>
              <span className="text-sm">Gemma Model</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 bg-green-500 rounded-full"></div>
              <span className="text-sm">Enhanced Fallback</span>
            </div>
          </div>
        </div>

        {/* IVR Schedule for Pregnancy Patients */}
        {isPregnancyPatient && (
        <div>
            <h4 className="font-semibold mb-2 flex items-center gap-2">
              <Clock className="h-4 w-4" />
              IVR Message Schedule
            </h4>
            {loadingIvr ? (
              <div className="text-sm text-muted-foreground">Loading IVR schedule...</div>
            ) : ivrSchedule.length > 0 ? (
              <div className="space-y-3">
                <div className="flex items-center justify-between mb-4">
                  <div className="text-sm text-muted-foreground">
                    Total Calls: {ivrSchedule.length}
                  </div>
                  <Badge variant="outline" className="text-xs">
                    Enhanced Fallback System
                  </Badge>
                </div>
                {ivrSchedule.map((item, idx) => (
                  <div key={idx} className="bg-muted p-3 rounded-lg">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-sm">
                          {item.type === 'medication_reminder' ? '💊 Medication' :
                           item.type === 'checkin' ? '📞 Weekly Check-in' :
                           item.type === 'postnatal_care' ? '👶 Postnatal Care' :
                           item.type === 'high_risk_additional' ? '⚠️ High Risk' :
                           item.type === 'appointment_reminder' ? '📅 Appointment' :
                           '📋 General'}
                        </span>
                        <Badge variant="secondary" className="text-xs">
                          {item.topic || item.type}
                        </Badge>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-muted-foreground">
                          {item.date} at {item.time}
                        </span>
                        {item.medication_name && (
                          <Badge variant="outline" className="text-xs">
                            {item.medication_name}
                          </Badge>
                        )}
                      </div>
                    </div>
                    <p className="text-sm text-muted-foreground">{item.message}</p>
                    {item.risk_factor && (
                      <div className="mt-2">
                        <Badge variant="destructive" className="text-xs">
                          Risk Factor: {item.risk_factor}
                        </Badge>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="space-y-2">
                <div className="text-sm text-muted-foreground">No IVR schedule available</div>
                <Button 
                  size="sm" 
                  onClick={generateNewIvrSchedule}
                  disabled={loadingIvr}
                >
                  {loadingIvr ? "Generating..." : "Generate IVR Schedule"}
                </Button>
              </div>
            )}
            
            {/* Enhanced Schedule Generation */}
            <div className="mt-4 space-y-2">
              <div className="flex gap-2">
                <Button 
                  variant="outline" 
                  size="sm"
                  onClick={async () => {
                    try {
                      // Extract gestational age from diagnosis
                      const gestationalAgeMatch = patient.diagnosis?.match(/Week (\d+)/);
                      const gestationalAge = gestationalAgeMatch ? parseInt(gestationalAgeMatch[1]) : 20;
                      
                      // Parse risk factors
                      const riskFactors = patient.risk_factors ? patient.risk_factors.split(',').map(f => f.trim()) : [];
                      
                      // Create structured medications
                      const structuredMedications = patient.medications?.map(med => ({
                        name: med.name,
                        dosage: med.dosage,
                        time: "09:00 AM",
                        days: ["Monday", "Wednesday", "Friday"]
                      })) || [];
                      
                      const response = await fetch('http://localhost:8000/generate_comprehensive_ivr_schedule', {
                        method: 'POST',
                        headers: {
                          'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                          patient_name: patient.name,
                          gestational_age_weeks: gestationalAge,
                          risk_factors: riskFactors,
                          risk_category: patient.risk_category || "low",
                          structured_medications: structuredMedications,
                          patient_data: {
                            medications: patient.medications || [],
                            allergies: [],
                            medical_history: [patient.diagnosis]
                          }
                        })
                      });
                      
                      if (response.ok) {
                        const data = await response.json();
                        if (data.success) {
                          console.log("Generated new IVR schedule:", data);
                          // Update the patient's call schedule
                          await fetch(`http://localhost:8000/patients/${patient.id}`, {
                            method: 'PUT',
                            headers: {
                              'Content-Type': 'application/json',
                            },
                            body: JSON.stringify({
                              call_schedule: JSON.stringify(data.schedule)
                            })
                          });
                          // Refresh the IVR schedule
                          fetchIvrSchedule();
                        }
                      }
                    } catch (error) {
                      console.error("Failed to generate IVR schedule:", error);
                    }
                  }}
                >
                  Generate Comprehensive IVR Schedule
                </Button>
                <Button 
                  variant="outline" 
                  size="sm"
                  onClick={fetchIvrSchedule}
                  disabled={loadingIvr}
                >
                  <RefreshCw className="h-4 w-4" />
                </Button>
              </div>
              <p className="text-xs text-muted-foreground">
                This will create a complete weekly schedule with medication reminders, weekly check-ins, and risk-based additional calls using the enhanced fallback system.
              </p>
            </div>
            
            {/* IVR Schedule Editor */}
            <div className="mt-6">
              <IVRScheduleEditor 
                patient={patient} 
                onScheduleUpdated={fetchIvrSchedule}
              />
            </div>
          </div>
        )}
        
        {/* Postnatal Care Section */}
        <div>
          <h4 className="font-semibold mb-2">Postnatal Care</h4>
          <PostnatalCareSection patient={patient} />
        </div>

        {/* Patient Metrics Section */}
        <div>
          <h4 className="font-semibold mb-2">Call Metrics</h4>
          <PatientMetrics patient={patient} />
        </div>
        
        <PatientMessages patient={patient} />
      </CardContent>
    </Card>
  );
};

const PatientMetrics = ({ patient }: { patient: Patient }) => {
  const [metrics, setMetrics] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (patient.id) {
      fetchPatientMetrics();
    }
  }, [patient.id]);

  const fetchPatientMetrics = async () => {
    setLoading(true);
    try {
      const response = await fetch(`http://localhost:8000/patients/${patient.id}/metrics`);
      if (response.ok) {
        const data = await response.json();
        setMetrics(data);
      }
    } catch (error) {
      console.error('Error fetching patient metrics:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="text-sm text-gray-500">Loading metrics...</div>;
  }

  if (!metrics) {
    return <div className="text-sm text-gray-500">No metrics available</div>;
  }

  return (
    <div className="space-y-4">
      <h4 className="font-semibold text-sm">Call Metrics</h4>
      
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-blue-50 p-3 rounded-lg">
          <div className="text-xs text-blue-600 font-medium">Success Rate</div>
          <div className="text-lg font-bold text-blue-800">
            {metrics.call_success_rate}%
          </div>
        </div>
        
        <div className="bg-green-50 p-3 rounded-lg">
          <div className="text-xs text-green-600 font-medium">Completed Calls</div>
          <div className="text-lg font-bold text-green-800">
            {metrics.total_calls_completed}/{metrics.total_calls_scheduled}
          </div>
        </div>
        
        <div className="bg-orange-50 p-3 rounded-lg">
          <div className="text-xs text-orange-600 font-medium">Failed Calls</div>
          <div className="text-lg font-bold text-orange-800">
            {metrics.total_calls_failed}
          </div>
        </div>
        
        <div className="bg-red-50 p-3 rounded-lg">
          <div className="text-xs text-red-600 font-medium">Missed Calls</div>
          <div className="text-lg font-bold text-red-800">
            {metrics.total_calls_missed}
          </div>
        </div>
      </div>
      
      {metrics.average_call_duration > 0 && (
        <div className="bg-purple-50 p-3 rounded-lg">
          <div className="text-xs text-purple-600 font-medium">Average Call Duration</div>
          <div className="text-lg font-bold text-purple-800">
            {Math.round(metrics.average_call_duration)}s
          </div>
        </div>
      )}
      
      {metrics.last_call_date && (
        <div className="text-xs text-gray-500">
          Last call: {new Date(metrics.last_call_date).toLocaleDateString()} 
          ({metrics.last_call_status})
        </div>
      )}
    </div>
  );
};

const PostnatalCareSection = ({ patient }: { patient: Patient }) => {
  const [deliveryDate, setDeliveryDate] = useState("");
  const [deliveryType, setDeliveryType] = useState("vaginal");
  const [isUpdating, setIsUpdating] = useState(false);

  const handleDeliveryUpdate = async () => {
    if (!deliveryDate) return;
    
    setIsUpdating(true);
    try {
      const response = await fetch(`http://localhost:8000/patients/${patient.id}/delivery`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          delivery_date: deliveryDate,
          delivery_type: deliveryType
        })
      });
      
      if (response.ok) {
        // Refresh patient data
        window.location.reload();
      }
    } catch (error) {
      console.error('Error updating delivery info:', error);
    } finally {
      setIsUpdating(false);
    }
  };

  if (patient.is_postpartum) {
    return (
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <Badge variant="default" className="bg-purple-100 text-purple-800">
            Postnatal Care
          </Badge>
          <span className="text-sm text-gray-600">
            Week {patient.postpartum_week || 1} postpartum
          </span>
        </div>
        
        <div className="text-sm text-gray-600">
          <div>Delivery Date: {patient.delivery_date ? new Date(patient.delivery_date).toLocaleDateString() : 'Not set'}</div>
          <div>Delivery Type: {patient.delivery_type || 'Not specified'}</div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <h4 className="font-semibold text-sm">Postnatal Care Setup</h4>
      
      <div className="space-y-3">
        <div>
          <Label htmlFor="delivery-date">Delivery Date</Label>
          <Input
            id="delivery-date"
            type="date"
            value={deliveryDate}
            onChange={(e) => setDeliveryDate(e.target.value)}
            className="mt-1"
          />
        </div>
        
        <div>
          <Label htmlFor="delivery-type">Delivery Type</Label>
          <Select value={deliveryType} onValueChange={setDeliveryType}>
            <SelectTrigger className="mt-1">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="vaginal">Vaginal</SelectItem>
              <SelectItem value="c-section">C-Section</SelectItem>
              <SelectItem value="assisted">Assisted</SelectItem>
            </SelectContent>
          </Select>
        </div>
        
        <Button 
          onClick={handleDeliveryUpdate}
          disabled={!deliveryDate || isUpdating}
          className="w-full"
        >
          {isUpdating ? "Updating..." : "Start Postnatal Care"}
        </Button>
      </div>
    </div>
  );
};

const IVRScheduleEditor = ({ patient, onScheduleUpdated }: { patient: Patient; onScheduleUpdated: () => void }) => {
  const [schedule, setSchedule] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (patient.call_schedule) {
      try {
        const scheduleData = JSON.parse(patient.call_schedule);
        const scheduleList = Array.isArray(scheduleData) ? scheduleData : scheduleData.schedule || [];
        setSchedule(scheduleList);
      } catch (e) {
        console.error("Error parsing call schedule:", e);
        setSchedule([]);
      }
    }
  }, [patient.call_schedule]);

  const updateScheduleTime = async (index: number, newTime: string) => {
    setLoading(true);
    setError(null);
    try {
      const updatedSchedule = [...schedule];
      updatedSchedule[index] = { ...updatedSchedule[index], time: newTime };
      setSchedule(updatedSchedule);
      const response = await fetch(`http://localhost:8000/patients/${patient.id}/ivr-schedule`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ schedule: updatedSchedule }), // Send as wrapped object
      });
      if (!response.ok) {
        throw new Error('Failed to update schedule');
      }
      onScheduleUpdated();
    } catch (e) {
      setError('Failed to update schedule');
      console.error('Error updating schedule:', e);
    } finally {
      setLoading(false);
    }
  };

  const formatTime = (time: string) => {
    // Convert '9:00 AM', '9 AM', '3:30 PM', etc. to '09:00', '15:30', etc.
    if (!time) return '';
    // Match 'h:mm AM/PM' or 'h AM/PM'
    const match = time.match(/^(\d{1,2})(?::(\d{2}))?\s*(AM|PM)$/i);
    if (match) {
      let hour = parseInt(match[1]);
      const minute = match[2] || '00';
      const ampm = match[3].toUpperCase();
      if (ampm === 'PM' && hour !== 12) hour += 12;
      if (ampm === 'AM' && hour === 12) hour = 0;
      return `${hour.toString().padStart(2, '0')}:${minute}`;
    }
    // If already in 24-hour format, return as is
    if (/^\d{2}:\d{2}$/.test(time)) return time;
    return '';
  };

  const formatTimeForDisplay = (time: string) => {
    // Convert '09:00' to '9:00 AM', '15:30' to '3:30 PM', etc.
    if (!time) return '';
    const match = time.match(/^(\d{1,2}):(\d{2})$/);
    if (match) {
      let hour = parseInt(match[1]);
      const minute = match[2];
      const ampm = hour >= 12 ? 'PM' : 'AM';
      if (hour > 12) hour -= 12;
      if (hour === 0) hour = 12;
      return `${hour}:${minute} ${ampm}`;
    }
    return time;
  };

  if (schedule.length === 0) {
    return (
      <div className="p-4 text-center text-gray-500">
        No IVR schedule available for this patient.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <h4 className="font-semibold text-sm">IVR Schedule Editor</h4>
      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-md text-red-700 text-sm">
          {error}
        </div>
      )}
      
      <div className="space-y-3">
        {schedule.map((item, index) => (
          <div key={index} className="flex items-center gap-3 p-3 border rounded-md">
            <div className="flex-1">
              <div className="font-medium text-sm">{item.topic || 'General'}</div>
              <div className="text-xs text-gray-600">{item.date}</div>
            </div>
            
            <div className="flex items-center gap-2">
              <Label htmlFor={`time-${index}`} className="text-xs">Time:</Label>
              <Input
                id={`time-${index}`}
                type="time"
                value={formatTime(item.time)}
                onChange={(e) => updateScheduleTime(index, formatTimeForDisplay(e.target.value))}
                disabled={loading}
                className="w-24 h-8 text-xs"
              />
            </div>
          </div>
        ))}
      </div>
      
      {loading && (
        <div className="text-center text-sm text-gray-600">
          Updating schedule...
        </div>
      )}
    </div>
  );
};

const EditPatientForm = ({ onClose, patient, onPatientUpdated }: { onClose: () => void; patient: Patient; onPatientUpdated: () => void }) => {
  const [name, setName] = useState(patient.name || "");
  const [phone, setPhone] = useState(patient.phone || "");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // State variables for patient registration form
  const [gestationalAge, setGestationalAge] = useState("");
  const [age, setAge] = useState(patient.age || "");
  const [race, setRace] = useState(patient.race || "");
  const [height, setHeight] = useState(patient.height || "");
  const [weight, setWeight] = useState(patient.weight || "");
  const [medications, setMedications] = useState("");
  const [riskFactors, setRiskFactors] = useState("");
  const [additionalNotes, setAdditionalNotes] = useState("");
  
  // Medication schedule state
  const [medicationSchedule, setMedicationSchedule] = useState<Array<{
    name: string;
    dosage: string;
    time: string;
    ampm: 'AM' | 'PM';
    frequency: {
      monday: boolean;
      tuesday: boolean;
      wednesday: boolean;
      thursday: boolean;
      friday: boolean;
      saturday: boolean;
      sunday: boolean;
    };
  }>>([]);

  // Initialize form with existing patient data
  useEffect(() => {
    console.log("=== PATIENT EDIT FORM LOADING ===");
    console.log("Patient prop received:", patient);
    console.log("Patient ID:", patient?.id);
    console.log("Patient name:", patient?.name);
    
    if (patient) {
      console.log("Patient data for editing:", patient);
      console.log("Patient description:", patient.description);
      console.log("Patient medication_schedule:", patient.medication_schedule);
      console.log("Patient risk_factors:", patient.risk_factors);
      
      // Set basic patient information
      setName(patient.name || "");
      setPhone(patient.phone || "");
      setAge(patient.age || "");
      setRace(patient.race || "");
      setHeight(patient.height || "");
      setWeight(patient.weight || "");
      
      // Extract gestational age from diagnosis
      const gaMatch = patient.diagnosis?.match(/Week (\d+)/);
      if (gaMatch) {
        setGestationalAge(gaMatch[1]);
      }
      
      // Load risk factors and additional notes from the original OPD text
      // These would be stored in the patient record or extracted from the description
      // For now, we'll set them to empty and let the user re-enter them
      const formattedRiskFactors = patient.risk_factors 
        ? patient.risk_factors.split(', ').map(factor => 
            factor.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
          ).join(', ')
        : "";
      setRiskFactors(formattedRiskFactors);
      setAdditionalNotes(patient.additional_notes || "Any additional medical information, symptoms, or special considerations...");
      
      // Parse existing medication schedule
      if (patient.medication_schedule) {
        console.log("Parsing medication schedule:", patient.medication_schedule);
        const parsedMeds: Array<{
          name: string;
          dosage: string;
          time: string;
          ampm: 'AM' | 'PM';
          frequency: {
            monday: boolean;
            tuesday: boolean;
            wednesday: boolean;
            thursday: boolean;
            friday: boolean;
            saturday: boolean;
            sunday: boolean;
          };
        }> = [];
        
        // Split by newlines and filter out empty lines
        const medLines = patient.medication_schedule.split('\n').filter(line => line.trim());
        console.log("Medication lines:", medLines);
        console.log("Raw medication_schedule:", patient.medication_schedule);
        
        for (const line of medLines) {
          // Remove leading dash and spaces
          const cleanLine = line.replace(/^-\s*/, '').trim();
          console.log("Processing line:", cleanLine);
          
          // Parse format: "Medication Name - Time AM/PM (Days) - Dosage"
          const match = cleanLine.match(/^([^-]+)\s*-\s*(\d{1,2})\s*(AM|PM)\s*\(([^)]+)\)(?:\s*-\s*([^-]+))?/);
          if (!match) {
            // Try alternative format: "Medication Name - Time AM/PM (Days)"
            const altMatch = cleanLine.match(/^([^-]+)\s*-\s*(\d{1,2})\s*(AM|PM)\s*\(([^)]+)\)/);
            if (altMatch) {
              const medName = altMatch[1].trim();
              const time = altMatch[2];
              const ampm = altMatch[3] as 'AM' | 'PM';
              const daysStr = altMatch[4];
              
              console.log("Parsed medication (alt format):", { medName, time, ampm, daysStr });
              
              // Parse days
              const days = daysStr.toLowerCase().split(',').map(d => d.trim());
              const frequency = {
                monday: days.includes('monday') || days.includes('daily'),
                tuesday: days.includes('tuesday') || days.includes('daily'),
                wednesday: days.includes('wednesday') || days.includes('daily'),
                thursday: days.includes('thursday') || days.includes('daily'),
                friday: days.includes('friday') || days.includes('daily'),
                saturday: days.includes('saturday') || days.includes('daily'),
                sunday: days.includes('sunday') || days.includes('daily')
              };
              
              parsedMeds.push({
                name: medName,
                dosage: "1 tablet", // Default dosage
                time,
                ampm,
                frequency
              });
            }
          } else {
            const medName = match[1].trim();
            const time = match[2];
            const ampm = match[3] as 'AM' | 'PM';
            const daysStr = match[4];
            const dosage = match[5] || "1 tablet";
            
            console.log("Parsed medication:", { medName, time, ampm, daysStr, dosage });
            
            // Parse days
            const days = daysStr.toLowerCase().split(',').map(d => d.trim());
            const frequency = {
              monday: days.includes('monday') || days.includes('daily'),
              tuesday: days.includes('tuesday') || days.includes('daily'),
              wednesday: days.includes('wednesday') || days.includes('daily'),
              thursday: days.includes('thursday') || days.includes('daily'),
              friday: days.includes('friday') || days.includes('daily'),
              saturday: days.includes('saturday') || days.includes('daily'),
              sunday: days.includes('sunday') || days.includes('daily')
            };
            
            parsedMeds.push({
              name: medName,
              dosage,
              time,
              ampm,
              frequency
            });
          }
        }
        
        console.log("Parsed medications:", parsedMeds);
        if (parsedMeds.length === 0) {
          console.log("No medications parsed, adding default medication");
          // Add a default medication if none were parsed
          parsedMeds.push({
            name: "Prenatal Vitamins",
            dosage: "1 tablet",
            time: "8",
            ampm: "AM" as 'AM' | 'PM',
            frequency: {
              monday: true,
              tuesday: true,
              wednesday: true,
              thursday: true,
              friday: true,
              saturday: true,
              sunday: true
            }
          });
        }
        setMedicationSchedule(parsedMeds);
      }
    }
  }, [patient]);

  // Calculate BMI when height or weight changes
  const calculateBMI = (height: string, weight: string) => {
    if (!height || !weight) return "";
    const heightM = parseFloat(height) / 100;
    const weightKg = parseFloat(weight);
    if (heightM > 0 && weightKg > 0) {
      return (weightKg / (heightM * heightM)).toFixed(1);
    }
    return "";
  };

  // Update BMI when height or weight changes
  useEffect(() => {
    const bmi = calculateBMI(height, weight);
    // Note: We can't directly update BMI in the form since it's calculated
    // But we can store it for submission
  }, [height, weight]);

  const addMedication = () => {
    setMedicationSchedule([...medicationSchedule, {
      name: "",
      dosage: "",
      time: "",
      ampm: "AM",
      frequency: {
        monday: false,
        tuesday: false,
        wednesday: false,
        thursday: false,
        friday: false,
        saturday: false,
        sunday: false
      }
    }]);
  };

  const updateMedication = (index: number, field: string, value: any) => {
    const updated = [...medicationSchedule];
    if (field === "frequency") {
      updated[index].frequency = { ...updated[index].frequency, ...value };
    } else {
      (updated[index] as any)[field] = value;
    }
    setMedicationSchedule(updated);
  };

  const removeMedication = (index: number) => {
    setMedicationSchedule(medicationSchedule.filter((_, i) => i !== index));
  };

  const formatMedicationSchedule = () => {
    return medicationSchedule.map(med => 
      `${med.name} - ${med.time} ${med.ampm} (${Object.entries(med.frequency)
        .filter(([_, enabled]) => enabled)
        .map(([day, _]) => day.charAt(0).toUpperCase() + day.slice(1))
        .join(', ')}) - ${med.dosage}`
    ).join('\n');
  };

  const handleEditPatient = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const bmi = calculateBMI(height, weight);
      const formattedMedications = formatMedicationSchedule();
      
      const response = await fetch(`http://localhost:8000/update_patient_with_ivr/${patient.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name,
          phone,
          age,
          height,
          weight,
          gestational_age: gestationalAge,
          risk_factors: riskFactors,
          medications: formattedMedications
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to update patient');
      }

      const result = await response.json();
      console.log('Patient updated successfully:', result);
      onPatientUpdated();
      onClose();
    } catch (error) {
      console.error('Error updating patient:', error);
      setError('Failed to update patient. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={true} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Edit Patient</DialogTitle>
          <DialogDescription>
            Update patient information and medication schedule for personalized IVR scheduling.
          </DialogDescription>
        </DialogHeader>
        
        <form onSubmit={handleEditPatient} className="space-y-6">
          {/* Phone Number */}
          <div className="space-y-2">
            <Label htmlFor="phone">Phone Number</Label>
            <Input
              id="phone"
              type="tel"
              placeholder="Enter phone number"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              required
            />
          </div>

          {/* Patient Registration Information */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
          <Label htmlFor="name">Patient Name</Label>
              <Input
                id="name"
                placeholder="e.g., Sarah Johnson"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
              />
        </div>
            
            <div className="space-y-2">
              <Label htmlFor="gestationalAge">Gestational Age (weeks)</Label>
              <Input
                id="gestationalAge"
                type="number"
                placeholder="e.g., 24"
                value={gestationalAge}
                onChange={(e) => setGestationalAge(e.target.value)}
                required
              />
        </div>
            
            <div className="space-y-2">
              <Label htmlFor="age">Age</Label>
              <Input
                id="age"
                type="number"
                placeholder="e.g., 28"
                value={age}
                onChange={(e) => setAge(e.target.value)}
                required
              />
      </div>
      
            <div className="space-y-2">
              <Label htmlFor="race">Race/Ethnicity</Label>
              <Input
                id="race"
                placeholder="e.g., Asian, Caucasian"
                value={race}
                onChange={(e) => setRace(e.target.value)}
              />
      </div>

            <div className="space-y-2">
              <Label htmlFor="height">Height (cm)</Label>
              <Input
                id="height"
                type="number"
                placeholder="e.g., 165"
                value={height}
                onChange={(e) => setHeight(e.target.value)}
                required
              />
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="weight">Weight (kg)</Label>
              <Input
                id="weight"
                type="number"
                placeholder="e.g., 70"
                value={weight}
                onChange={(e) => setWeight(e.target.value)}
                required
              />
            </div>
          </div>

          {/* Medication Schedule */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <Label>Medication Schedule</Label>
              <Button type="button" onClick={addMedication} variant="outline" size="sm">
                <Plus className="h-4 w-4 mr-2" />
                Add Medication
              </Button>
            </div>
            
            {medicationSchedule.map((med, index) => (
              <div key={index} className="border rounded-lg p-4 space-y-4">
                <div className="flex items-center justify-between">
                  <h4 className="font-medium">Medication {index + 1}</h4>
                  <Button
                    type="button"
                    onClick={() => removeMedication(index)}
                    variant="outline"
                    size="sm"
                    className="text-red-600 hover:text-red-700"
                  >
                    Remove
                  </Button>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="space-y-2">
                    <Label>Medication Name</Label>
                    <Input
                      placeholder="e.g., Prenatal Vitamins"
                      value={med.name}
                      onChange={(e) => updateMedication(index, "name", e.target.value)}
                      required
                    />
                  </div>
                  
                  <div className="space-y-2">
                    <Label>Dosage</Label>
                    <Input
                      placeholder="e.g., 1 tablet"
                      value={med.dosage}
                      onChange={(e) => updateMedication(index, "dosage", e.target.value)}
                      required
                    />
                  </div>
                  
                  <div className="space-y-2">
                    <Label>Time</Label>
                    <div className="flex gap-2">
                      <Input
                        type="number"
                        placeholder="8"
                        value={med.time}
                        onChange={(e) => updateMedication(index, "time", e.target.value)}
                        className="w-20"
                        required
                      />
                      <Select value={med.ampm} onValueChange={(value) => updateMedication(index, "ampm", value)}>
                        <SelectTrigger className="w-20">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="AM">AM</SelectItem>
                          <SelectItem value="PM">PM</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                </div>
                
                <div className="space-y-2">
                  <Label>Frequency</Label>
                  <div className="grid grid-cols-7 gap-2">
                    {Object.entries(med.frequency).map(([day, enabled]) => (
                      <div key={day} className="flex items-center space-x-2">
                        <Checkbox
                          id={`${day}-${index}`}
                          checked={enabled}
                          onCheckedChange={(checked) => 
                            updateMedication(index, "frequency", { [day]: checked })
                          }
                        />
                        <Label htmlFor={`${day}-${index}`} className="text-xs">
                          {day.charAt(0).toUpperCase()}
                        </Label>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Risk Factors & Medical Conditions */}
          <div className="space-y-2">
            <Label htmlFor="riskFactors">Risk Factors & Medical Conditions</Label>
        <Textarea 
              id="riskFactors"
              placeholder="e.g., Diabetes, Hypertension, Obesity, Advanced maternal age, Previous cesarean, Smoking, Anemia, Thyroid disorder, Asthma, Depression, Eating disorder, Malnutrition, Vitamin deficiency, Severe underweight, Underweight, Severe obesity, Binge eating, Food restriction, Bias, Gastroparesis, Celiac disease, Food allergies."
              value={riskFactors}
              onChange={(e) => setRiskFactors(e.target.value)}
              rows={4}
        />
      </div>

          {/* Additional Notes */}
          <div className="space-y-2">
            <Label htmlFor="additionalNotes">Additional Notes</Label>
            <Textarea
              id="additionalNotes"
              placeholder="Any additional medical information, symptoms, or special considerations..."
              value={additionalNotes}
              onChange={(e) => setAdditionalNotes(e.target.value)}
              rows={3}
            />
      </div>

          {error && (
            <div className="text-red-600 text-sm">{error}</div>
          )}

          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose}>
          Cancel
        </Button>
            <Button type="submit" disabled={loading}>
              {loading ? "Updating..." : "Update Patient"}
        </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
};

const AddPatientForm = ({ onClose, onPatientUpdated }: { onClose: () => void; onPatientUpdated: () => void }) => {
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // State variables for patient registration form
  const [gestationalAge, setGestationalAge] = useState("");
  const [lmpDate, setLmpDate] = useState("");
  const [age, setAge] = useState("");
  const [race, setRace] = useState("");
  const [height, setHeight] = useState("");
  const [weight, setWeight] = useState("");
  const [medications, setMedications] = useState("");
  const [riskFactors, setRiskFactors] = useState("");
  const [additionalNotes, setAdditionalNotes] = useState("");
  const [riskCategory, setRiskCategory] = useState<"low" | "medium" | "high">("low");
  const [description, setDescription] = useState("");
  
  // Medication schedule state
  const [medicationSchedule, setMedicationSchedule] = useState<Array<{
    name: string;
    dosage: string;
    time: string;
    ampm: 'AM' | 'PM';
    frequency: {
      monday: boolean;
      tuesday: boolean;
      wednesday: boolean;
      thursday: boolean;
      friday: boolean;
      saturday: boolean;
      sunday: boolean;
    };
  }>>([]);

  // ... rest of the form logic (same as before but with handleSubmit)
  const calculateBMI = (height: string, weight: string) => {
    if (!height || !weight) return "";
    const heightM = parseFloat(height) / 100;
    const weightKg = parseFloat(weight);
    if (heightM > 0 && weightKg > 0) {
      return (weightKg / (heightM * heightM)).toFixed(1);
    }
    return "";
  };

  const addMedication = () => {
    setMedicationSchedule([...medicationSchedule, {
      name: "",
      dosage: "",
      time: "",
      ampm: "AM",
      frequency: {
        monday: false,
        tuesday: false,
        wednesday: false,
        thursday: false,
        friday: false,
        saturday: false,
        sunday: false
      }
    }]);
  };

  const updateMedication = (index: number, field: string, value: any) => {
    const updated = [...medicationSchedule];
    if (field === "frequency") {
      updated[index].frequency = { ...updated[index].frequency, ...value };
    } else {
      (updated[index] as any)[field] = value;
    }
    setMedicationSchedule(updated);
  };

  const removeMedication = (index: number) => {
    setMedicationSchedule(medicationSchedule.filter((_, i) => i !== index));
  };

  const formatMedicationSchedule = () => {
    return medicationSchedule.map(med => 
      `${med.name} - ${med.time} ${med.ampm} (${Object.entries(med.frequency)
        .filter(([_, enabled]) => enabled)
        .map(([day, _]) => day.charAt(0).toUpperCase() + day.slice(1))
        .join(', ')}) - ${med.dosage}`
    ).join('\n');
  };

  const handleOpdUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const bmi = calculateBMI(height, weight);
      const formattedMedications = formatMedicationSchedule();
      
      // Create structured medications array for the backend
      const structuredMedications = medicationSchedule.map(med => ({
        name: med.name,
        dosage: med.dosage,
        time: `${med.time} ${med.ampm}`,
        days: Object.entries(med.frequency)
          .filter(([_, enabled]) => enabled)
          .map(([day, _]) => day.charAt(0).toUpperCase() + day.slice(1)),
        frequency: Object.values(med.frequency).every(v => v) ? "daily" : "specific"
      }));

      const response = await fetch('http://localhost:8000/register_patient_with_opd', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          opd_paper_text: `Patient: ${name}, Age: ${age}, Height: ${height}cm, Weight: ${weight}kg, Gestational Age: ${gestationalAge}, Phone: ${phone}, Risk Factors: ${riskFactors}, Medications: ${formattedMedications}`,
          structured_medications: structuredMedications
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to register patient');
      }

      const result = await response.json();
      console.log('Patient registered successfully:', result);
      onPatientUpdated();
      onClose();
    } catch (error) {
      console.error('Error registering patient:', error);
      setError('Failed to register patient. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const bmi = calculateBMI(height, weight);
      const formattedMedications = formatMedicationSchedule();
      
      // Create structured medications array for the backend
      const structuredMedications = medicationSchedule.map(med => ({
        name: med.name,
        dosage: med.dosage,
        time: `${med.time} ${med.ampm}`,
        days: Object.entries(med.frequency)
          .filter(([_, enabled]) => enabled)
          .map(([day, _]) => day.charAt(0).toUpperCase() + day.slice(1)),
        frequency: Object.values(med.frequency).every(v => v) ? "daily" : "specific"
      }));

      const response = await fetch('http://localhost:8000/patients/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: name,
          lmp_date: lmpDate,
          risk_category: riskCategory,
          medications: formattedMedications,
          phone: phone,
          description: description,
          race: race,
          age: age,
          height: height,
          weight: weight,
          bmi: bmi,
          risk_factors: riskFactors,
          additional_notes: additionalNotes,
          structured_medications: structuredMedications
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to register patient');
      }

      const result = await response.json();
      console.log('Patient registered successfully:', result);
      onPatientUpdated();
      onClose();
    } catch (error) {
      console.error('Error registering patient:', error);
      setError('Failed to register patient. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={true} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Add Patient</DialogTitle>
          <DialogDescription>
            Register a new patient with comprehensive medical information for personalized IVR scheduling.
          </DialogDescription>
        </DialogHeader>
        
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Phone Number */}
          <div className="space-y-2">
            <Label htmlFor="phone">Phone Number</Label>
            <Input
              id="phone"
              type="tel"
              placeholder="Enter phone number"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              required
            />
      </div>

          {/* Patient Registration Information */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="name">Patient Name</Label>
              <Input
                id="name"
                placeholder="e.g., Sarah Johnson"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
              />
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="lmpDate">LMP (Last Menstrual Period) Date</Label>
              <Input
                id="lmpDate"
                type="date"
                placeholder="Select LMP date"
                value={lmpDate}
                onChange={(e) => setLmpDate(e.target.value)}
                required
              />
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="age">Age</Label>
              <Input
                id="age"
                type="number"
                placeholder="e.g., 28"
                value={age}
                onChange={(e) => setAge(e.target.value)}
                required
              />
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="race">Race/Ethnicity</Label>
              <Input
                id="race"
                placeholder="e.g., Asian, Caucasian"
                value={race}
                onChange={(e) => setRace(e.target.value)}
              />
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="height">Height (cm)</Label>
              <Input
                id="height"
                type="number"
                placeholder="e.g., 165"
                value={height}
                onChange={(e) => setHeight(e.target.value)}
                required
              />
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="weight">Weight (kg)</Label>
              <Input
                id="weight"
                type="number"
                placeholder="e.g., 70"
                value={weight}
                onChange={(e) => setWeight(e.target.value)}
                required
              />
            </div>
          </div>

          {/* Medication Schedule */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <Label>Medication Schedule</Label>
              <Button type="button" onClick={addMedication} variant="outline" size="sm">
                <Plus className="h-4 w-4 mr-2" />
                Add Medication
              </Button>
            </div>
            
            {medicationSchedule.map((med, index) => (
              <div key={index} className="border rounded-lg p-4 space-y-4">
                <div className="flex items-center justify-between">
                  <h4 className="font-medium">Medication {index + 1}</h4>
                  <Button
                    type="button"
                    onClick={() => removeMedication(index)}
                    variant="outline"
                    size="sm"
                    className="text-red-600 hover:text-red-700"
                  >
                    Remove
                  </Button>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="space-y-2">
                    <Label>Medication Name</Label>
                    <Input
                      placeholder="e.g., Prenatal Vitamins"
                      value={med.name}
                      onChange={(e) => updateMedication(index, "name", e.target.value)}
                      required
                    />
                  </div>
                  
                  <div className="space-y-2">
                    <Label>Dosage</Label>
                    <Input
                      placeholder="e.g., 1 tablet"
                      value={med.dosage}
                      onChange={(e) => updateMedication(index, "dosage", e.target.value)}
                      required
                    />
                  </div>
                  
                  <div className="space-y-2">
                    <Label>Time</Label>
                    <div className="flex gap-2">
                      <Input
                        type="number"
                        placeholder="8"
                        value={med.time}
                        onChange={(e) => updateMedication(index, "time", e.target.value)}
                        className="w-20"
                        required
                      />
                      <Select value={med.ampm} onValueChange={(value) => updateMedication(index, "ampm", value)}>
                        <SelectTrigger className="w-20">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="AM">AM</SelectItem>
                          <SelectItem value="PM">PM</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                </div>
                
                <div className="space-y-2">
                  <Label>Frequency</Label>
                  <div className="grid grid-cols-7 gap-2">
                    {Object.entries(med.frequency).map(([day, enabled]) => (
                      <div key={day} className="flex items-center space-x-2">
                        <Checkbox
                          id={`${day}-${index}`}
                          checked={enabled}
                          onCheckedChange={(checked) => 
                            updateMedication(index, "frequency", { [day]: checked })
                          }
                        />
                        <Label htmlFor={`${day}-${index}`} className="text-xs">
                          {day.charAt(0).toUpperCase()}
                        </Label>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Risk Factors & Medical Conditions */}
          <div className="space-y-2">
            <Label htmlFor="riskFactors">Risk Factors & Medical Conditions</Label>
            <Textarea
              id="riskFactors"
              placeholder="e.g., Diabetes, Hypertension, Obesity, Advanced maternal age, Previous cesarean, Smoking, Anemia, Thyroid disorder, Asthma, Depression, Eating disorder, Malnutrition, Vitamin deficiency, Severe underweight, Underweight, Severe obesity, Binge eating, Food restriction, Bias, Gastroparesis, Celiac disease, Food allergies."
              value={riskFactors}
              onChange={(e) => setRiskFactors(e.target.value)}
              rows={4}
            />
          </div>

          {/* Additional Notes */}
          <div className="space-y-2">
            <Label htmlFor="additionalNotes">Additional Notes</Label>
            <Textarea
              id="additionalNotes"
              placeholder="Any additional medical information, symptoms, or special considerations..."
              value={additionalNotes}
              onChange={(e) => setAdditionalNotes(e.target.value)}
              rows={3}
            />
          </div>

          {error && (
            <div className="text-red-600 text-sm">{error}</div>
          )}

          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" disabled={loading}>
              {loading ? "Registering..." : "Register Patient"}
            </Button>
          </DialogFooter>
    </form>
      </DialogContent>
    </Dialog>
  );
};

const PatientMessages = ({ patient }: { patient: Patient }) => {
  const [messages, setMessages] = useState<any[]>([]);
  const [loadingMessages, setLoadingMessages] = useState(false);

  const fetchMessages = async () => {
    if (!patient.id) return;
    
    setLoadingMessages(true);
    try {
      const response = await fetch(`http://localhost:8000/patients/${patient.id}/messages`);
      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          setMessages(data.messages || []);
        }
      }
    } catch (error) {
      console.error("Failed to fetch messages:", error);
    } finally {
      setLoadingMessages(false);
    }
  };

  React.useEffect(() => {
    fetchMessages();
  }, [patient.id]);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pending': return 'bg-yellow-100 text-yellow-800';
      case 'processed': return 'bg-blue-100 text-blue-800';
      case 'completed': return 'bg-green-100 text-green-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'pending': return 'Pending';
      case 'processed': return 'Processed';
      case 'completed': return 'Completed';
      default: return 'Unknown';
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h4 className="font-semibold flex items-center gap-2">
          <MessageSquare className="h-4 w-4" />
          Patient Messages
        </h4>
        <Button 
          size="sm" 
          variant="outline"
          onClick={fetchMessages}
          disabled={loadingMessages}
        >
          <RefreshCw className="h-4 w-4" />
        </Button>
      </div>
      
      {loadingMessages ? (
        <div className="text-sm text-muted-foreground">Loading messages...</div>
      ) : messages.length > 0 ? (
        <div className="space-y-3">
          {messages.map((message) => (
            <div key={message.id} className="bg-muted p-3 rounded-lg">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <Badge variant="outline" className="text-xs">
                    {message.message_type}
                  </Badge>
                  <Badge className={`text-xs ${getStatusColor(message.status)}`}>
                    {getStatusText(message.status)}
                  </Badge>
                </div>
                <div className="text-xs text-muted-foreground">
                  {new Date(message.created_at).toLocaleDateString()}
                </div>
              </div>
              
              <div className="space-y-2">
                <p className="text-sm">
                  <strong>Message:</strong> {message.message_text}
                </p>
                
                {message.processed_response && (
                  <p className="text-sm">
                    <strong>Response:</strong> {message.processed_response}
                  </p>
                )}
                
                {message.callback_message && (
                  <p className="text-sm">
                    <strong>Callback:</strong> {message.callback_message}
                  </p>
                )}
                
                {message.scheduled_callback && (
                  <p className="text-xs text-muted-foreground">
                    Scheduled callback: {new Date(message.scheduled_callback).toLocaleString()}
                  </p>
                )}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-sm text-muted-foreground">No messages found</div>
      )}
    </div>
  );
};