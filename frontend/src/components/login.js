import React from 'react';
import { Button } from "./ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "./ui/card";

const LoginPage = () => {
  const handleMicrosoftLogin = () => {
    window.location.href = 'http://localhost:8001/auth/microsoft';
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-600 via-purple-600 to-purple-800 p-4">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle className="text-2xl font-bold text-center">🤖 Internal Assistant</CardTitle>
          <div className="text-center text-sm text-muted-foreground">
            Login dengan Microsoft untuk mengakses semua fitur
          </div>
        </CardHeader>
        <CardContent>
          <Button 
            onClick={handleMicrosoftLogin}
            className="w-full h-12 bg-[#0078d4] hover:bg-[#106ebe] text-white font-semibold flex items-center justify-center gap-3 transition-all duration-300 shadow-lg hover:shadow-xl"
          >
            <svg width="20" height="20" viewBox="0 0 21 21" fill="none">
              <rect width="10" height="10" fill="#F25022"/>
              <rect x="11" width="10" height="10" fill="#7FBA00"/>
              <rect y="11" width="10" height="10" fill="#00A4EF"/>
              <rect x="11" y="11" width="10" height="10" fill="#FFB900"/>
            </svg>
            Login dengan Microsoft
          </Button>
        </CardContent>
        <div className="flex flex-col space-y-2 p-6 pt-0">
          <p className="text-sm font-medium">Fitur yang tersedia:</p>
          <div className="text-sm text-gray-600 space-y-1">
            <div>📋 Smart Project Management</div>
            <div>✅ Microsoft To-Do</div>
            <div>📚 RAG Q&A Internal</div>
          </div>
        </div>
      </Card>
    </div>
  );
};

export default LoginPage;
