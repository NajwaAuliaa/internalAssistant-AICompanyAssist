import React from 'react';
import { Button } from "./ui/button";
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from "./ui/card";

const LoginPage = () => {
  const handleMicrosoftLogin = () => {
    window.location.href = 'http://localhost:8001/auth/microsoft';
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-black p-4">
      <Card className="w-full max-w-sm" style={{ backgroundColor: '#171717', borderColor: '#2a2a2a' }}>
        <CardHeader className="text-center">
          <div style={{color: '#ffffff', fontSize: '1.25rem', fontWeight: '600', lineHeight: '1.75rem'}}>
            Login to your account
          </div>
        </CardHeader>
        <CardContent className="space-y-8">
          {/* Premium tagline */}
          <div className="text-center">
            <p style={{fontSize: '0.875rem', color: '#9ca3af', fontWeight: '300', letterSpacing: '0.025em'}}>
              Authenticate with your Microsoft credentials to access your enterprise workspace
            </p>
          </div>
          
          {/* Elegant spacing */}
          <div className="h-8"></div>
          
          {/* Trust indicators */}
          <div className="flex justify-center items-center gap-6">
            <div className="flex items-center gap-2 text-sm" style={{color: '#9ca3af'}}>
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clipRule="evenodd" />
              </svg>
              <span>Secure</span>
            </div>
            <div className="w-px h-4 bg-gray-600"></div>
            <div className="flex items-center gap-2 text-sm" style={{color: '#9ca3af'}}>
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M6.267 3.455a3.066 3.066 0 001.745-.723 3.066 3.066 0 013.976 0 3.066 3.066 0 001.745.723 3.066 3.066 0 012.812 2.812c.051.643.304 1.254.723 1.745a3.066 3.066 0 010 3.976 3.066 3.066 0 00-.723 1.745 3.066 3.066 0 01-2.812 2.812 3.066 3.066 0 00-1.745.723 3.066 3.066 0 01-3.976 0 3.066 3.066 0 00-1.745-.723 3.066 3.066 0 01-2.812-2.812 3.066 3.066 0 00-.723-1.745 3.066 3.066 0 010-3.976 3.066 3.066 0 00.723-1.745 3.066 3.066 0 012.812-2.812zm7.44 5.252a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
              <span>Verified</span>
            </div>
          </div>
        </CardContent>
        <CardFooter className="flex-col gap-2">
          <Button 
            onClick={handleMicrosoftLogin}
            variant="outline" 
            className="w-full hover:opacity-90"
            style={{ backgroundColor: '#212121', borderColor: '#404040', color: '#ffffff' }}
          >
            <svg width="16" height="16" viewBox="0 0 21 21" fill="none" className="mr-2">
              <rect width="10" height="10" fill="#F25022"/>
              <rect x="11" width="10" height="10" fill="#7FBA00"/>
              <rect y="11" width="10" height="10" fill="#00A4EF"/>
              <rect x="11" y="11" width="10" height="10" fill="#FFB900"/>
            </svg>
            Login with Microsoft
          </Button>
        </CardFooter>
      </Card>
    </div>
  );
};

export default LoginPage;