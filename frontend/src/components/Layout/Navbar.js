import React from 'react';
import { motion } from 'framer-motion';
import { Building2, User, LogOut } from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import { useLocation } from 'react-router-dom';

const Navbar = () => {
  const { user, logout } = useAuth();
  const location = useLocation();
  
  // Detect if we're on ExpertComptable page
  const isExpertComptablePage = location.pathname.includes('/expertcomptable') || location.pathname.includes('/expertcompta');
  
  // Debug log to see current path
  console.log('Current pathname:', location.pathname, 'isExpertComptablePage:', isExpertComptablePage);
  
  const brandText = isExpertComptablePage ? 'by Granitai for OEC Maroc' : 'by Granitai for Burj Finance';
  const navbarColor = isExpertComptablePage ? 'bg-gray-300' : 'bg-white';
  const textColor = isExpertComptablePage ? 'text-gray-800' : 'text-gray-900';
  const iconColor = isExpertComptablePage ? 'text-gray-700' : 'text-primary-600';
  const borderColor = isExpertComptablePage ? 'border-gray-300' : 'border-gray-200';

  return (
    <motion.nav 
      className={`fixed top-0 left-0 right-0 z-50 ${navbarColor} border-b ${borderColor} shadow-sm`}
      initial={{ y: -100 }}
      animate={{ y: 0 }}
      transition={{ duration: 0.5 }}
    >
      <div className="px-6 py-4">
        <div className="flex items-center justify-between">
          {/* Left - Brand Text */}
          <div className="flex items-center flex-1">
            <div>
              <h1 className={`text-xl font-bold ${textColor}`}>{isExpertComptablePage ? 'Agent Comptable' : 'Company Profile Agent'}</h1>
              <p className={`text-xs ${isExpertComptablePage ? 'text-gray-600' : 'text-gray-500'}`}>{brandText}</p>
            </div>
          </div>

          {/* Center - Logo */}
          <div className="flex items-center justify-center flex-1">
            <img 
              src="/logo.webp" 
              alt="Logo" 
                className="w-auto"
                style={{ height: '60px' }}
              onError={(e) => {
                // Fallback to icon if image fails to load
                e.target.style.display = 'none';
                e.target.nextSibling.style.display = 'block';
              }}
            />
            <Building2 className={`h-20 w-10 ${iconColor}`} style={{ display: 'none' }} />
          </div>

          {/* Right - User Menu */}
          <div className="flex items-center space-x-4 flex-1 justify-end">
            <div className="flex items-center space-x-3">
              <div className="text-right">
                <p className={`text-sm font-medium ${textColor}`}>{user?.name}</p>
                <p className={`text-xs ${isExpertComptablePage ? 'text-gray-600' : 'text-gray-500'} capitalize`}>{user?.role}</p>
              </div>
              <div className={`w-8 h-8 ${isExpertComptablePage ? 'bg-gray-200' : 'bg-primary-100'} rounded-full flex items-center justify-center`}>
                <User className={`h-4 w-4 ${isExpertComptablePage ? 'text-gray-600' : 'text-primary-600'}`} />
              </div>
            </div>

            <div className={`h-6 border-l ${isExpertComptablePage ? 'border-gray-400' : 'border-gray-300'}`}></div>

            <button
              onClick={logout}
              className={`flex items-center space-x-2 ${isExpertComptablePage ? 'text-gray-700 hover:text-gray-900' : 'text-gray-600 hover:text-gray-900'} transition-colors duration-200`}
            >
              <LogOut className="h-4 w-4" />
              <span className="text-sm">Logout</span>
            </button>
          </div>
        </div>
      </div>
    </motion.nav>
  );
};

export default Navbar;
