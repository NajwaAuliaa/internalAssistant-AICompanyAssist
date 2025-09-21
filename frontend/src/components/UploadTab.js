import React, { useState } from 'react';
import axios from 'axios';
import { Button } from './ui/button';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8002';

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
    <div className="p-6 space-y-6">
      <Card className="glass-effect modern-shadow">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <div className="w-6 h-6 rounded gradient-bg flex items-center justify-center">
              <span className="text-white text-xs font-bold">↑</span>
            </div>
            Upload & Index Documents
          </CardTitle>
          <p className="text-muted-foreground">Upload dokumen kamu ke Azure Blob, lalu index ke Cognitive Search.</p>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">Folder/Prefix di Blob:</label>
            <input
              type="text"
              value={prefix}
              onChange={(e) => setPrefix(e.target.value)}
              placeholder="sop/"
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
            />
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">Upload Files:</label>
            <input
              type="file"
              multiple
              onChange={handleFileChange}
              accept=".pdf,.docx,.doc,.txt,.pptx,.xlsx,.jpg,.jpeg,.png"
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
            />
          </div>

          <Button 
            onClick={handleUpload} 
            disabled={loading}
            className="w-full"
          >
            {loading ? 'Processing...' : 'Upload & Index'}
          </Button>
        </CardContent>
      </Card>

      {result && (
        <Card className="glass-effect modern-shadow">
          <CardHeader>
            <CardTitle>Hasil Upload + Index</CardTitle>
          </CardHeader>
          <CardContent>
            <pre className="bg-muted p-4 rounded-md text-sm overflow-auto">{result}</pre>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

export default UploadTab;