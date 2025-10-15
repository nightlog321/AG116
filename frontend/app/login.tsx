import React from 'react';
import { useEffect } from 'react';
import { router } from 'expo-router';

export default function LoginRedirect() {
  useEffect(() => {
    // Immediately redirect back to home which will show LoginPage component
    router.replace('/');
  }, []);

  return null; // This component doesn't render anything
}