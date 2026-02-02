import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useAuth } from './contexts/AuthContext';
import Login from './components/Auth/Login';
import ExpertComptablePage from './components/ExpertComptable/ExpertComptablePage';
import Navbar from './components/Layout/Navbar';
import Sidebar from './components/Layout/Sidebar';
import LoadingSpinner from './components/UI/LoadingSpinner';

// Component that uses useLocation to conditionally show sidebar
function AppContent() {
  const { user } = useAuth();
  const location = useLocation();
  
  // Hide sidebar on expert comptable page
  const hideSidebar = location.pathname === '/expertcompta';
  
  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <div className="flex">
        {!hideSidebar && <Sidebar />}
        <main className={`flex-1 p-6 mt-16 ${hideSidebar ? 'ml-0' : 'ml-64'}`}>
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
          >
            <Routes>
              <Route path="/expertcompta" element={<ExpertComptablePage />} />
              <Route 
                path="*" 
                element={<Navigate to="/expertcompta" replace />}
              />
            </Routes>
          </motion.div>
        </main>
      </div>
    </div>
  );
}

function App() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (!user) {
    return (
      <Router>
        <div className="min-h-screen bg-gradient-to-br from-primary-50 to-secondary-50">
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="*" element={<Navigate to="/login" replace />} />
          </Routes>
        </div>
      </Router>
    );
  }

  return (
    <Router>
      <AppContent />
    </Router>
  );
}

export default App;
