import React, { useState } from "react";

function PatientDetail() {
  const [id, setId] = useState("");
  const [patient, setPatient] = useState<any>(null);

  const fetchPatient = () => {
    fetch(`http://localhost:8000/patients/${id}`)
      .then((res) => res.json())
      .then(setPatient);
  };

  return (
    <div style={{ margin: 16 }}>
      <h3>Get Patient Details</h3>
      <input
        value={id}
        onChange={(e) => setId(e.target.value)}
        placeholder="Enter patient ID"
        style={{ marginRight: 8 }}
      />
      <button onClick={fetchPatient}>Get Patient</button>
      {patient && <pre>{JSON.stringify(patient, null, 2)}</pre>}
    </div>
  );
}

export default PatientDetail; 