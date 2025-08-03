import React, { useEffect, useState } from "react";

function PatientList() {
  const [patients, setPatients] = useState<any[]>([]);

  useEffect(() => {
    fetch("http://localhost:8000/patients/")
      .then((res) => res.json())
      .then(setPatients);
  }, []);

  return (
    <div style={{ margin: 16 }}>
      {/* Removed patient name and ID display */}
    </div>
  );
}

export default PatientList; 