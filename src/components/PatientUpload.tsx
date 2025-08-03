import React, { useState } from "react";

function PatientUpload() {
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<any>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setFile(e.target.files[0]);
    }
  };

  const handleUpload = async () => {
    if (!file) return;
    const formData = new FormData();
    formData.append("file", file);

    const res = await fetch("http://localhost:8000/upload_patient_record/", {
      method: "POST",
      body: formData,
    });
    const data = await res.json();
    setResult(data);
  };

  return (
    <div style={{ margin: 16 }}>
      <h3>Upload Patient Record</h3>
      <input type="file" accept=".txt" onChange={handleFileChange} />
      <button onClick={handleUpload} style={{ marginLeft: 8 }}>Upload</button>
      {result && <pre>{JSON.stringify(result, null, 2)}</pre>}
    </div>
  );
}

export default PatientUpload; 