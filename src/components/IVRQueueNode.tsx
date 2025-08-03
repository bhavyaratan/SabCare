import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Phone, Clock, User, MessageSquare, Calendar, AlertTriangle } from "lucide-react";

interface IVRCall {
  patient_name: string;
  phone_number: string;
  scheduled_date: string;
  scheduled_time: string;
  topic: string;
  message: string;
  risk_level: string;
}

interface IVRQueueData {
  total_upcoming_calls: number;
  calls_by_day: {
    [key: string]: IVRCall[];
  };
  calls_by_risk_level: {
    high: number;
    medium: number;
    low: number;
  };
  upcoming_calls: IVRCall[];
}

const IVRQueueNode = () => {
  const [queueData, setQueueData] = useState<IVRQueueData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchQueueData = async () => {
    try {
      setLoading(true);
      const response = await fetch("http://localhost:8000/upcoming-calls-summary?days_ahead=30");
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      setQueueData(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch queue data");
      console.error("Error fetching IVR queue data:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchQueueData();
    // Refresh every 30 seconds to show real-time updates
    const interval = setInterval(fetchQueueData, 30000);
    return () => clearInterval(interval);
  }, []);

  const getNext10Calls = (): IVRCall[] => {
    if (!queueData || !queueData.upcoming_calls) return [];
    
    // The backend returns upcoming_calls as a flat array, already sorted
    return queueData.upcoming_calls.slice(0, 10);
  };

  const formatDateTime = (date: string, time: string) => {
    const dateObj = new Date(`${date} ${time}`);
    return dateObj.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
      hour12: true
    });
  };

  const getRiskColor = (risk: string) => {
    switch (risk.toLowerCase()) {
      case 'high': return 'bg-red-100 text-red-800 border-red-200';
      case 'medium': return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'low': return 'bg-green-100 text-green-800 border-green-200';
      default: return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const next10Calls = getNext10Calls();

  if (loading) {
    return (
      <Card className="w-full">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Phone className="h-5 w-5" />
            IVR Call Queue
          </CardTitle>
          <CardDescription>Next 10 scheduled calls</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
            <span className="ml-2 text-muted-foreground">Loading queue...</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="w-full">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Phone className="h-5 w-5" />
            IVR Call Queue
          </CardTitle>
          <CardDescription>Next 10 scheduled calls</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-8 text-red-600">
            <AlertTriangle className="h-5 w-5 mr-2" />
            Error loading queue: {error}
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="w-full h-full">
      <CardContent className="h-full overflow-y-auto">
        {/* Priority Badges - Centered with top spacing */}
        <div className="flex items-center justify-center gap-3 mb-6 pt-4">
          <Badge variant="outline" className="text-xs">
            Total: {queueData?.total_upcoming_calls || 0}
          </Badge>
          <Badge variant="outline" className="text-xs bg-red-50 text-red-700 border-red-200">
            High: {queueData?.calls_by_risk_level?.high || 0}
          </Badge>
          <Badge variant="outline" className="text-xs bg-yellow-50 text-yellow-700 border-yellow-200">
            Medium: {queueData?.calls_by_risk_level?.medium || 0}
          </Badge>
          <Badge variant="outline" className="text-xs bg-green-50 text-green-700 border-green-200">
            Low: {queueData?.calls_by_risk_level?.low || 0}
          </Badge>
        </div>

        <div className="space-y-4">
          {next10Calls.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              <Phone className="h-16 w-16 mx-auto mb-4 opacity-50" />
              <p className="text-lg font-medium mb-2">No upcoming calls scheduled</p>
              <p className="text-sm">Calls will appear here when patients are registered</p>
            </div>
          ) : (
            next10Calls.map((call, index) => (
              <div
                key={`${call.patient_name}-${call.scheduled_date}-${call.scheduled_time}`}
                className={`p-4 rounded-lg border transition-all duration-200 hover:shadow-md ${
                  index === 0 
                    ? 'bg-primary/5 border-primary/20 shadow-sm' 
                    : 'bg-card border-border hover:bg-accent/50'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3 mb-3">
                      <div className={`w-3 h-3 rounded-full ${
                        index === 0 ? 'bg-primary animate-pulse' : 'bg-muted-foreground'
                      }`}></div>
                      <h4 className="font-semibold text-sm flex items-center gap-2 truncate">
                        <User className="h-4 w-4 flex-shrink-0" />
                        {call.patient_name}
                      </h4>
                      <Badge 
                        variant="outline" 
                        className={`text-xs flex-shrink-0 ${getRiskColor(call.risk_level)}`}
                      >
                        {call.risk_level}
                      </Badge>
                    </div>
                    
                    <div className="grid grid-cols-2 gap-4 text-xs text-muted-foreground mb-3">
                      <div className="flex items-center gap-2">
                        <Phone className="h-3 w-3 flex-shrink-0" />
                        <span className="truncate">{call.phone_number}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <Calendar className="h-3 w-3 flex-shrink-0" />
                        <span className="truncate">{formatDateTime(call.scheduled_date, call.scheduled_time)}</span>
                      </div>
                    </div>
                    
                    <div className="space-y-2">
                      <div className="flex items-center gap-2 text-xs text-muted-foreground">
                        <MessageSquare className="h-3 w-3 flex-shrink-0" />
                        <span className="font-medium text-foreground">{call.topic}</span>
                      </div>
                      <p className="text-xs text-muted-foreground line-clamp-3 leading-relaxed">
                        {call.message}
                      </p>
                    </div>
                  </div>
                  
                  {index === 0 && (
                    <div className="ml-4 flex-shrink-0">
                      <Badge className="bg-primary text-primary-foreground text-xs">
                        <Clock className="h-3 w-3 mr-1" />
                        Next
                      </Badge>
                    </div>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
        
        {next10Calls.length > 0 && (
          <div className="mt-6 pt-4 border-t">
            <div className="flex items-center justify-between text-xs text-muted-foreground">
              <span>Auto-refresh every 30 seconds</span>
              <button 
                onClick={fetchQueueData}
                className="text-primary hover:underline font-medium"
              >
                Refresh now
              </button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default IVRQueueNode; 