// src/App.jsx
import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';  // adjust path if needed
import Navbar from './components/Navbar';
import ProtectedRoute from './components/ProtectedRoute';
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import Profile from './pages/Profile';
import ChangePassword from './pages/ChangePassword';
import VerifyOTP from './pages/VerifyOTP';
import ActivityStatistics from './pages/ActivityStatistics';
import ActivityCaptures from './pages/ActivityCaptures';
import ActivityFingerprints from './pages/ActivityFingerprints';

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Navbar />
        <Routes>
          <Route path="/login"    element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/verify-OTP" element={<VerifyOTP />} />

          <Route
            path="/"
            element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            }
          />

          <Route
            path="/profile"
            element={
              <ProtectedRoute>
                <Profile />
              </ProtectedRoute>
            }
          />

          <Route
            path="/change-password"
            element={
              <ProtectedRoute>
                <ChangePassword />
              </ProtectedRoute>
            }
          />

          <Route
            path="/activity/statistics"
            element={
              <ProtectedRoute>
                <ActivityStatistics/>
              </ProtectedRoute>
            }
          />
          <Route
            path="/activity/captures"
            element={
              <ProtectedRoute>
                <ActivityCaptures/>
              </ProtectedRoute>
            }
          />
          <Route
            path="/activity/fingerprints"
            element={
              <ProtectedRoute>
                <ActivityFingerprints/>
              </ProtectedRoute>
            }
          />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
