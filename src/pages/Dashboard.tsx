import React, { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { 
  Activity, 
  Phone, 
  Users, 
  Database, 
  Server, 
  MessageSquare,
  BarChart3,
  Settings,
  Bell,
  CheckCircle,
  AlertCircle,
  Clock,
  Zap,
  Layers,
  Cpu,
  HardDrive,
  Network,
  Cloud,
  Brain,
  Mic,
  FileText
} from 'lucide-react';
import { PatientManager } from '@/components/PatientManager';
import IVRQueueNode from '@/components/IVRQueueNode';

const Dashboard = () => {
  const [activeTab, setActiveTab] = useState('overview');

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50">
      {/* Header */}
      <div className="border-b bg-white/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <h1 className="text-2xl font-bold text-gray-900">सब.AI Clinician Dashboard</h1>
            </div>

          </div>
        </div>
      </div>

      {/* Main Content with Tabs */}
      <div className="container mx-auto px-6 py-8">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
          <div className="flex justify-center">
            <TabsList className="grid w-auto grid-cols-2">
              <TabsTrigger value="overview" className="flex items-center gap-2">
                <BarChart3 className="h-4 w-4" />
                Overview
              </TabsTrigger>
              <TabsTrigger value="patients" className="flex items-center gap-2">
                <Users className="h-4 w-4" />
                Patient Manager
              </TabsTrigger>
            </TabsList>
          </div>

          <TabsContent value="overview" className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 h-full">
              {/* Left Half - System Status and Architecture */}
              <div className="flex flex-col space-y-2 h-full">
                {/* System Status */}
                <Card className="flex-shrink-0">
                  <CardHeader className="pb-3">
                    <CardTitle className="flex items-center gap-2">
                      <Activity className="h-5 w-5" />
                      System Status
                    </CardTitle>
                    <CardDescription>
                      Overview of सब.AI backend and service integrations
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-2">
                    <div className="space-y-2">
                      <div className="flex items-center justify-between p-2 bg-green-50 rounded-lg">
                        <div className="flex items-center gap-3">
                          <Server className="h-5 w-5 text-green-600" />
                          <div>
                            <p className="font-medium text-sm">Backend API (FastAPI)</p>
                            <p className="text-xs text-gray-600">Port 8000</p>
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center justify-between p-2 bg-blue-50 rounded-lg">
                        <div className="flex items-center gap-3">
                          <Clock className="h-5 w-5 text-blue-600" />
                          <div>
                            <p className="font-medium text-sm">Scheduler Service</p>
                            <p className="text-xs text-gray-600">Running</p>
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center justify-between p-2 bg-purple-50 rounded-lg">
                        <div className="flex items-center gap-3">
                          <Phone className="h-5 w-5 text-purple-600" />
                          <div>
                            <p className="font-medium text-sm">Twilio Integration</p>
                            <p className="text-xs text-gray-600">Connected</p>
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center justify-between p-2 bg-orange-50 rounded-lg">
                        <div className="flex items-center gap-3">
                          <MessageSquare className="h-5 w-5 text-orange-600" />
                          <div>
                            <p className="font-medium text-sm">Text-to-Speech (TTS)</p>
                            <p className="text-xs text-gray-600">Integrated</p>
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center justify-between p-2 bg-emerald-50 rounded-lg">
                        <div className="flex items-center gap-3">
                          <Brain className="h-5 w-5 text-emerald-600" />
                          <div>
                            <p className="font-medium text-sm">IVR System</p>
                            <p className="text-xs text-gray-600">Gemma 2B + Enhanced Fallback</p>
                          </div>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {/* System Architecture */}
                <Card className="flex-1">
                  <CardHeader className="pb-3">
                    <CardTitle className="flex items-center gap-2">
                      <Layers className="h-5 w-5" />
                      System Architecture
                    </CardTitle>
                    <CardDescription>
                      Technical stack and component overview
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-2">
                    <div className="space-y-2">
                      <div className="flex items-center justify-between p-2 bg-indigo-50 rounded-lg">
                        <div className="flex items-center gap-3">
                          <Cpu className="h-5 w-5 text-indigo-600" />
                          <div>
                            <p className="font-medium text-sm">AI Models</p>
                            <p className="text-xs text-gray-600">Google Gemma 2B, Enhanced Fallback</p>
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center justify-between p-2 bg-teal-50 rounded-lg">
                        <div className="flex items-center gap-3">
                          <HardDrive className="h-5 w-5 text-teal-600" />
                          <div>
                            <p className="font-medium text-sm">Database</p>
                            <p className="text-xs text-gray-600">SQLite, RAG Vector DB</p>
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center justify-between p-2 bg-pink-50 rounded-lg">
                        <div className="flex items-center gap-3">
                          <Brain className="h-5 w-5 text-pink-600" />
                          <div>
                            <p className="font-medium text-sm">RAG Service</p>
                            <p className="text-xs text-gray-600">Pregnancy Knowledge Base</p>
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center justify-between p-2 bg-cyan-50 rounded-lg">
                        <div className="flex items-center gap-3">
                          <Mic className="h-5 w-5 text-cyan-600" />
                          <div>
                            <p className="font-medium text-sm">Voice Processing</p>
                            <p className="text-xs text-gray-600">TTS, Speech Recognition</p>
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center justify-between p-2 bg-emerald-50 rounded-lg">
                        <div className="flex items-center gap-3">
                          <Network className="h-5 w-5 text-emerald-600" />
                          <div>
                            <p className="font-medium text-sm">API Gateway</p>
                            <p className="text-xs text-gray-600">RESTful Endpoints</p>
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center justify-between p-2 bg-amber-50 rounded-lg">
                        <div className="flex items-center gap-3">
                          <FileText className="h-5 w-5 text-amber-600" />
                          <div>
                            <p className="font-medium text-sm">Document Processing</p>
                            <p className="text-xs text-gray-600">Manual Upload</p>
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center justify-between p-2 bg-violet-50 rounded-lg">
                        <div className="flex items-center gap-3">
                          <Phone className="h-5 w-5 text-violet-600" />
                          <div>
                            <p className="font-medium text-sm">Twilio Service</p>
                            <p className="text-xs text-gray-600">Voice & SMS Integration</p>
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center justify-between p-2 bg-slate-50 rounded-lg">
                        <div className="flex items-center gap-3">
                          <Clock className="h-5 w-5 text-slate-600" />
                          <div>
                            <p className="font-medium text-sm">Scheduler</p>
                            <p className="text-xs text-gray-600">Automated Call Management</p>
                          </div>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* Right Half - IVR Call Queue */}
              <div className="h-full">
                <Card className="h-full flex flex-col">
                  <CardHeader className="flex-shrink-0">
                    <CardTitle className="flex items-center gap-2">
                      <Phone className="h-5 w-5" />
                      IVR Call Queue
                    </CardTitle>
                    <CardDescription>
                      Upcoming automated calls and reminders (next 10)
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="flex-1 overflow-hidden">
                    <div className="h-full overflow-y-auto">
                      <IVRQueueNode />
                    </div>
                  </CardContent>
                </Card>
              </div>
            </div>
          </TabsContent>

          <TabsContent value="patients" className="space-y-6">
            <PatientManager />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
};

export default Dashboard;