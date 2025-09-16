import React, { useState } from 'react';
import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8001';

function UploadTab() {
  const [files, setFiles] = useState([]);
  const [prefix, setPrefix] = useState('sop/');
  const [result, setResult] = useState('');
  const [loading, setLoading] = useState(false);

  const handleFileChange = (e) => {
    setFiles(Array.from(e.target.files));
  };

  const handleUpload = async () => {
    if (files.length === 0) {
      alert('Please select files to upload');
      return;
    }

    setLoading(true);
    const formData = new FormData();
    files.forEach(file => {
      formData.append('files', file);
    });
    formData.append('prefix', prefix);

    try {
      const response = await axios.post(`${API_BASE}/upload-and-index`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setResult(JSON.stringify(response.data, null, 2));
    } catch (error) {
      setResult(`Error: ${error.response?.data?.detail || error.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="upload-tab">
      <p>Upload dokumen kamu ke Azure Blob, lalu index ke Cognitive Search.</p>
      
      <div className="form-group">
        <label>Folder/Prefix di Blob:</label>
        <input
          type="text"
          value={prefix}
          onChange={(e) => setPrefix(e.target.value)}
          placeholder="sop/"
        />
      </div>

      <div className="form-group">
        <label>Upload Files:</label>
        <input
          type="file"
          multiple
          onChange={handleFileChange}
          accept=".pdf,.docx,.doc,.txt,.pptx,.xlsx,.jpg,.jpeg,.png"
        />
      </div>

      <button 
        onClick={handleUpload} 
        disabled={loading}
        className="btn-primary"
      >
        {loading ? 'Processing...' : 'Upload & Index'}
      </button>

      {result && (
        <div className="result-container">
          <label>Hasil Upload + Index (JSON):</label>
          <pre className="result-code">{result}</pre>
        </div>
      )}
    </div>
  );
}

export default UploadTab;