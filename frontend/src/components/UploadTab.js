import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Button } from './ui/button';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8002';

function DocumentManagementTab() {
  // Upload states
  const [files, setFiles] = useState([]);
  const [prefix, setPrefix] = useState('sop/');
  const [uploadResult, setUploadResult] = useState('');
  const [uploadLoading, setUploadLoading] = useState(false);

  // List states
  const [documents, setDocuments] = useState([]);
  const [listPrefix, setListPrefix] = useState('sop/');
  const [listLoading, setListLoading] = useState(false);

  // Delete states - modified to handle individual deletes
  const [deleteLoading, setDeleteLoading] = useState({});
  const [deleteResults, setDeleteResults] = useState({});

  // Debug states
  const [inspectBlob, setInspectBlob] = useState('');
  const [inspectResult, setInspectResult] = useState('');
  const [schemaResult, setSchemaResult] = useState('');
  const [debugLoading, setDebugLoading] = useState(false);

  // Reindex states
  const [reindexPrefix, setReindexPrefix] = useState('sop/');
  const [reindexResult, setReindexResult] = useState('');
  const [reindexLoading, setReindexLoading] = useState(false);

  // Active tab state - removed delete tab, keeping only 4 tabs
  const [activeTab, setActiveTab] = useState('upload');

  const tabs = [
    { id: 'upload', label: 'Upload & Index' },
    { id: 'manage', label: 'Manage Documents'},
    { id: 'debug', label: 'Debug & Inspect'},
    { id: 'reindex', label: 'Reindex'}
  ];

  // Upload functions
  const handleFileChange = (e) => {
    setFiles(Array.from(e.target.files));
  };

  const handleUpload = async () => {
    if (files.length === 0) {
      alert('Please select files to upload');
      return;
    }

    setUploadLoading(true);
    const formData = new FormData();
    files.forEach(file => {
      formData.append('files', file);
    });
    formData.append('prefix', prefix);

    try {
      const response = await axios.post(`${API_BASE}/documents/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setUploadResult(JSON.stringify(response.data, null, 2));
      
      // Auto refresh document list if we're on manage tab
      if (activeTab === 'manage') {
        handleListDocuments();
      }
    } catch (error) {
      setUploadResult(`Error: ${error.response?.data?.detail || error.message}`);
    } finally {
      setUploadLoading(false);
    }
  };

  // List functions
  const handleListDocuments = async () => {
    setListLoading(true);
    try {
      const response = await axios.get(`${API_BASE}/documents`, {
        params: { prefix: listPrefix }
      });
      setDocuments(response.data.documents || []);
    } catch (error) {
      console.error('Error listing documents:', error);
      setDocuments([]);
    } finally {
      setListLoading(false);
    }
  };

  // Modified delete function for individual documents
  const handleDeleteDocument = async (blobName, index) => {
    if (!window.confirm(`Are you sure you want to delete "${blobName}"? This action cannot be undone.`)) {
      return;
    }

    setDeleteLoading(prev => ({ ...prev, [index]: true }));

    try {
      const response = await axios.delete(`${API_BASE}/documents`, {
        data: { blob_names: [blobName] }
      });
      
      // Store the result for this specific document
      setDeleteResults(prev => ({
        ...prev,
        [index]: { success: true, data: response.data }
      }));

      // Remove the document from the list
      setDocuments(prev => prev.filter((_, i) => i !== index));

      // Show success message briefly
      setTimeout(() => {
        setDeleteResults(prev => {
          const newResults = { ...prev };
          delete newResults[index];
          return newResults;
        });
      }, 3000);

    } catch (error) {
      setDeleteResults(prev => ({
        ...prev,
        [index]: { 
          success: false, 
          error: error.response?.data?.detail || error.message 
        }
      }));

      // Clear error message after 5 seconds
      setTimeout(() => {
        setDeleteResults(prev => {
          const newResults = { ...prev };
          delete newResults[index];
          return newResults;
        });
      }, 5000);
    } finally {
      setDeleteLoading(prev => {
        const newLoading = { ...prev };
        delete newLoading[index];
        return newLoading;
      });
    }
  };

  // Bulk delete function


  // Debug functions
  const handleInspectIndex = async () => {
    setDebugLoading(true);
    try {
      const response = await axios.get(`${API_BASE}/documents/inspect`, {
        params: inspectBlob ? { blob_name: inspectBlob } : {}
      });
      setInspectResult(JSON.stringify(response.data, null, 2));
    } catch (error) {
      setInspectResult(`Error: ${error.response?.data?.detail || error.message}`);
    } finally {
      setDebugLoading(false);
    }
  };

  const handleGetSchema = async () => {
    setDebugLoading(true);
    try {
      const response = await axios.get(`${API_BASE}/documents/schema`);
      setSchemaResult(JSON.stringify(response.data, null, 2));
    } catch (error) {
      setSchemaResult(`Error: ${error.response?.data?.detail || error.message}`);
    } finally {
      setDebugLoading(false);
    }
  };

  // Reindex functions
  const handleReindex = async () => {
    setReindexLoading(true);
    try {
      const response = await axios.post(`${API_BASE}/documents/reindex`, null, {
        params: { prefix: reindexPrefix }
      });
      setReindexResult(JSON.stringify(response.data, null, 2));
    } catch (error) {
      setReindexResult(`Error: ${error.response?.data?.detail || error.message}`);
    } finally {
      setReindexLoading(false);
    }
  };

  // Load documents on tab change
  useEffect(() => {
    if (activeTab === 'manage') {
      handleListDocuments();
    }
  }, [activeTab, handleListDocuments]);

  const formatFileSize = (bytes) => {
    if (!bytes) return 'Unknown';
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'Unknown';
    return new Date(dateString).toLocaleString();
  };

  return (
    <div className="p-6 space-y-6">
      <Card className="glass-effect modern-shadow">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            Document Management
          </CardTitle>
          <p className="text-muted-foreground">Smart Document Management with Azure Blob Storage and AI Search</p>
        </CardHeader>
        
        {/* Tab Navigation */}
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-2 border-b pb-4">
            {tabs.map((tab) => (
              <Button
                key={tab.id}
                variant={activeTab === tab.id ? "default" : "outline"}
                size="sm"
                onClick={() => setActiveTab(tab.id)}
                className="flex items-center gap-2"
              >
                {tab.label}
              </Button>
            ))}
          </div>

          {/* Upload & Index Tab */}
          {activeTab === 'upload' && (
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-4">
                  <h3 className="text-lg font-semibold">Upload dokumen ke Azure Blob dan auto-index ke Cognitive Search</h3>
                  
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
                    disabled={uploadLoading}
                    className="w-full"
                  >
                    {uploadLoading ? '🚀 Processing...' : '🚀 Upload & Index'}
                  </Button>
                </div>

                <div className="space-y-2">
                  <h4 className="text-sm font-medium">ℹ️ Info</h4>
                  <div className="bg-muted p-4 rounded-md text-sm space-y-2">
                    <p><strong>Supported Files:</strong></p>
                    <ul className="list-disc list-inside space-y-1">
                      <li>PDF, Word (DOC/DOCX)</li>
                      <li>PowerPoint (PPTX)</li>
                      <li>Excel (XLSX)</li>
                      <li>Text files (TXT)</li>
                      <li>Images (JPG/PNG)</li>
                    </ul>
                    <p><strong>Process:</strong></p>
                    <ol className="list-decimal list-inside space-y-1">
                      <li>Upload ke Blob Storage</li>
                      <li>Auto-extract text</li>
                      <li>Index ke AI Search</li>
                      <li>Ready for RAG queries</li>
                    </ol>
                  </div>
                </div>
              </div>

              {uploadResult && (
                <Card className="mt-4">
                  <CardHeader>
                    <CardTitle>📊 Hasil Upload + Index (JSON)</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <pre className="bg-muted p-4 rounded-md text-sm overflow-auto max-h-96">{uploadResult}</pre>
                  </CardContent>
                </Card>
              )}
            </div>
          )}

          {/* Manage Documents Tab - Combined List and Delete */}
          {activeTab === 'manage' && (
            <div className="space-y-4">
              <h3 className="text-lg font-semibold">Manage Documents</h3>
              <p className="text-muted-foreground">List, view, and delete documents from Blob Storage & Search Index</p>
              
              <div className="flex gap-4 items-end">
                <div className="flex-1 space-y-2">
                  <label className="text-sm font-medium">📂 Folder/Prefix untuk list:</label>
                  <input
                    type="text"
                    value={listPrefix}
                    onChange={(e) => setListPrefix(e.target.value)}
                    placeholder="sop/"
                    className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                  />
                </div>
                <Button 
                  onClick={handleListDocuments} 
                  disabled={listLoading}
                  variant="secondary"
                >
                  {listLoading ? '📋 Loading...' : '📋 Refresh List'}
                </Button>
              </div>

              {documents.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center justify-between">
                      <span>📄 Documents ({documents.length} found)</span>
                      <div className="text-sm text-muted-foreground">
                        Click trash icon to delete individual documents
                      </div>
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2 max-h-96 overflow-auto">
                      {documents.map((doc, index) => (
                        <div key={index} className="border rounded-md p-3 space-y-1 relative">
                          {/* Delete button positioned at top right */}
                          <div className="absolute top-3 right-3">
                            <Button
                              onClick={() => handleDeleteDocument(doc.name, index)}
                              disabled={deleteLoading[index]}
                              variant="destructive"
                              size="sm"
                              className="h-8 w-8 p-0"
                              title={`Delete ${doc.display_name || doc.name}`}
                            >
                              {deleteLoading[index] ? '⏳' : '🗑️'}
                            </Button>
                          </div>

                          <div className="flex items-center justify-between pr-12">
                            <span className="font-medium">{doc.display_name || doc.name}</span>
                            <span className="text-sm text-muted-foreground">{formatFileSize(doc.size)}</span>
                          </div>
                          <div className="text-sm text-muted-foreground">
                            <p>Type: {doc.content_type}</p>
                            <p>Modified: {formatDate(doc.last_modified)}</p>
                            <p>Full path: {doc.name}</p>
                          </div>

                          {/* Show delete result for this document */}
                          {deleteResults[index] && (
                            <div className={`mt-2 p-2 rounded text-sm ${
                              deleteResults[index].success 
                                ? 'bg-green-100 text-green-800 border border-green-200' 
                                : 'bg-red-100 text-red-800 border border-red-200'
                            }`}>
                              {deleteResults[index].success 
                                ? '✅ Successfully deleted!' 
                                : `❌ Error: ${deleteResults[index].error}`
                              }
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}

              {documents.length === 0 && !listLoading && (
                <div className="text-center py-8 text-muted-foreground">
                  <p>No documents found in this folder.</p>
                  <p className="text-sm mt-2">Try changing the folder prefix or upload some documents first.</p>
                </div>
              )}
            </div>
          )}

          {/* Debug & Inspect Tab */}
          {activeTab === 'debug' && (
            <div className="space-y-4">
              <h3 className="text-lg font-semibold">Debug Tools untuk Search Index</h3>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-4">
                  <h4 className="text-base font-medium">🔍 Inspect Index Sample</h4>
                  <div className="space-y-2">
                    <label className="text-sm font-medium">🔍 Specific Blob Name (optional):</label>
                    <input
                      type="text"
                      value={inspectBlob}
                      onChange={(e) => setInspectBlob(e.target.value)}
                      placeholder="sop/document.pdf"
                      className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                    />
                  </div>
                  <Button 
                    onClick={handleInspectIndex} 
                    disabled={debugLoading}
                    className="w-full"
                  >
                    {debugLoading ? '🔍 Inspecting...' : '🔍 Inspect Index'}
                  </Button>
                </div>

                <div className="space-y-4">
                  <h4 className="text-base font-medium">📊 Index Schema</h4>
                  <Button 
                    onClick={handleGetSchema} 
                    disabled={debugLoading}
                    className="w-full"
                  >
                    {debugLoading ? '📊 Loading...' : '📊 Get Index Schema'}
                  </Button>
                </div>
              </div>

              {inspectResult && (
                <Card className="mt-4">
                  <CardHeader>
                    <CardTitle>🔍 Index Inspection Results</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <pre className="bg-muted p-4 rounded-md text-sm overflow-auto max-h-96">{inspectResult}</pre>
                  </CardContent>
                </Card>
              )}

              {schemaResult && (
                <Card className="mt-4">
                  <CardHeader>
                    <CardTitle>📊 Index Schema Info</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <pre className="bg-muted p-4 rounded-md text-sm overflow-auto max-h-96">{schemaResult}</pre>
                  </CardContent>
                </Card>
              )}
            </div>
          )}

          {/* Reindex Tab */}
          {activeTab === 'reindex' && (
            <div className="space-y-4">
              <h3 className="text-lg font-semibold">Re-index Documents</h3>
              <p className="text-muted-foreground">Proses ulang semua dokumen dari Blob Storage ke Search Index</p>
              
              <div className="space-y-2">
                <label className="text-sm font-medium">📂 Folder/Prefix untuk reindex:</label>
                <input
                  type="text"
                  value={reindexPrefix}
                  onChange={(e) => setReindexPrefix(e.target.value)}
                  placeholder="sop/"
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                />
              </div>
              
              <Button 
                onClick={handleReindex} 
                disabled={reindexLoading}
                className="w-full"
              >
                {reindexLoading ? '🔄 Reindexing...' : '🔄 Reindex All Documents'}
              </Button>

              {reindexResult && (
                <Card className="mt-4">
                  <CardHeader>
                    <CardTitle>🔄 Reindex Results</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <pre className="bg-muted p-4 rounded-md text-sm overflow-auto max-h-96">{reindexResult}</pre>
                  </CardContent>
                </Card>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

export default DocumentManagementTab;