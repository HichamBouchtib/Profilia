import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { NavLink, useLocation } from 'react-router-dom';
import { 
  Calculator,
} from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import axios from 'axios';

const Sidebar = () => {
  const location = useLocation();
  const { user } = useAuth();
  const [stats, setStats] = useState({
    totalProfiles: 0,
    thisMonth: 0,
    processing: 0
  });

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const response = await axios.get('/api/dashboard/stats');
        setStats({
          totalProfiles: response.data.total_profiles,
          thisMonth: response.data.this_month,
          processing: response.data.processing
        });
      } catch (error) {
        console.error('Error fetching sidebar stats:', error);
      }
    };

    fetchStats();
  }, []);

  const menuItems = [
    {
      name: 'Expert Comptable',
      href: '/expertcompta',
      icon: Calculator,
    }
  ];

  return (
    <motion.aside 
      className="fixed left-0 top-16 h-full w-64 bg-white border-r border-gray-200 shadow-sm z-40"
      initial={{ x: -300 }}
      animate={{ x: 0 }}
      transition={{ duration: 0.5, delay: 0.2 }}
    >
      <div className="p-6">
        <nav className="space-y-2">
          {menuItems.map((item, index) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.href;
            
            return (
              <motion.div
                key={item.href}
                initial={{ x: -50, opacity: 0 }}
                animate={{ x: 0, opacity: 1 }}
                transition={{ duration: 0.3, delay: 0.1 * index }}
              >
                <NavLink
                  to={item.href}
                  className={`
                    flex items-center px-4 py-3 text-sm font-medium rounded-lg transition-all duration-200
                    ${isActive 
                      ? 'bg-primary-50 text-primary-700 border-l-4 border-primary-600' 
                      : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                    }
                  `}
                >
                  <Icon className={`mr-3 h-5 w-5 ${isActive ? 'text-primary-600' : 'text-gray-400'}`} />
                  {item.name}
                </NavLink>
              </motion.div>
            );
          })}
        </nav>

        {/* Statistics Panel */}
        <motion.div 
          className="mt-8 p-4 bg-gradient-to-r from-primary-50 to-secondary-50 rounded-lg"
          initial={{ y: 20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ duration: 0.5, delay: 0.6 }}
        >
          <h3 className="text-sm font-medium text-gray-900 mb-2">Quick Stats</h3>
          <div className="space-y-2">
            <div className="flex justify-between text-xs">
              <span className="text-gray-600">Total Profiles</span>
              <span className="font-medium text-gray-900">{stats.totalProfiles}</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-gray-600">This Month</span>
              <span className="font-medium text-gray-900">{stats.thisMonth}</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-gray-600">Processing</span>
              <span className="font-medium text-gray-900">{stats.processing}</span>
            </div>
          </div>
        </motion.div>
      </div>
    </motion.aside>
  );
};

export default Sidebar;
