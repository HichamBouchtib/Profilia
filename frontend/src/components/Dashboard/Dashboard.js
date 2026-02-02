import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { 
  FileText, 
  TrendingUp, 
  Clock, 
  CheckCircle,
  BarChart3,
  Download,
  Plus
} from 'lucide-react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../../contexts/AuthContext';
import LoadingSpinner from '../UI/LoadingSpinner';
import { formatMoroccanDate } from '../../utils/dateUtils';

const Dashboard = () => {
  const { user } = useAuth();
  const [stats, setStats] = useState({
    totalProfiles: 0,
    thisMonth: 0,
    processing: 0,
    completed: 0,
    totalChangePercent: 0,
    monthChangePercent: 0,
    successRate: 0
  });
  const [recentProfiles, setRecentProfiles] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      // Fetch dashboard stats and recent profiles in parallel
      const [statsResponse, profilesResponse] = await Promise.all([
        axios.get('/api/dashboard/stats'),
        axios.get('/api/profiles?per_page=5')
      ]);
      
      setRecentProfiles(profilesResponse.data.profiles);
      
      // Use real stats from the API
      console.log('Dashboard stats received:', statsResponse.data);
      setStats({
        totalProfiles: statsResponse.data.total_profiles,
        thisMonth: statsResponse.data.this_month,
        processing: statsResponse.data.processing,
        completed: statsResponse.data.completed,
        totalChangePercent: statsResponse.data.total_change_percent,
        monthChangePercent: statsResponse.data.month_change_percent,
        successRate: statsResponse.data.success_rate
      });
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  const statCards = [
    {
      title: 'Total Profiles',
      value: stats.totalProfiles,
      icon: FileText,
      color: 'primary',
      change: `${stats.totalChangePercent >= 0 ? '+' : ''}${stats.totalChangePercent}%`
    },
    {
      title: 'This Month (versus last month)',
      value: stats.thisMonth,
      icon: TrendingUp,
      color: 'green',
      change: `${stats.monthChangePercent >= 0 ? '+' : ''}${stats.monthChangePercent}%`
    },
    {
      title: 'Processing',
      value: stats.processing,
      icon: Clock,
      color: 'yellow',
      change: `${stats.processing} active`
    },
    {
      title: 'Completed',
      value: stats.completed,
      icon: CheckCircle,
      color: 'green',
      change: `${stats.successRate}% success`
    }
  ];

  const getColorClasses = (color) => {
    const colors = {
      primary: 'bg-primary-50 text-primary-600',
      green: 'bg-green-50 text-green-600',
      yellow: 'bg-yellow-50 text-yellow-600',
      red: 'bg-red-50 text-red-600'
    };
    return colors[color] || colors.primary;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Welcome Header */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="bg-gradient-to-r from-primary-600 to-primary-700 rounded-xl p-8 text-white"
      >
        <h1 className="text-3xl font-bold mb-2">
          Welcome back, {user?.name?.split(' ')[0]}!
        </h1>
        <p className="text-primary-100 text-lg">
          Ready to analyze more company profiles? Let's get started.
        </p>
        <Link 
          to="/profiles/new"
          className="inline-flex items-center mt-4 bg-white text-primary-600 px-6 py-2 rounded-lg font-medium hover:bg-primary-50 transition-colors duration-200"
        >
          <Plus className="h-4 w-4 mr-2" />
          Create New Profile
        </Link>
      </motion.div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {statCards.map((stat, index) => {
          const Icon = stat.icon;
          return (
            <motion.div
              key={stat.title}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: index * 0.1 }}
              className="card hover:shadow-md transition-shadow duration-200"
            >
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">{stat.title}</p>
                  <p className="text-3xl font-bold text-gray-900 mt-1">{stat.value}</p>

                </div>
                <div className={`p-3 rounded-lg ${getColorClasses(stat.color)}`}>
                  <Icon className="h-6 w-6" />
                </div>
              </div>
            </motion.div>
          );
        })}
      </div>

      {/* Recent Profiles and Quick Actions */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Recent Profiles */}
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.5, delay: 0.3 }}
          className="lg:col-span-2 card"
        >
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-lg font-semibold text-gray-900">Recent Profiles</h2>
            <Link 
              to="/profiles"
              className="text-primary-600 hover:text-primary-700 text-sm font-medium"
            >
              View all
            </Link>
          </div>
          
          {recentProfiles.length > 0 ? (
            <div className="space-y-4">
              {recentProfiles.map((profile) => (
                <div key={profile.id} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                  <div className="flex items-center space-x-4">
                    <div className="w-10 h-10 bg-primary-100 rounded-lg flex items-center justify-center">
                      <FileText className="h-5 w-5 text-primary-600" />
                    </div>
                    <div>
                      <h3 className="font-medium text-gray-900">{profile.company_name}</h3>
                    </div>
                  </div>
                  <div className="text-right">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      profile.status === 'completed' 
                        ? 'bg-green-100 text-green-800'
                        : profile.status === 'processing'
                        ? 'bg-yellow-100 text-yellow-800'
                        : 'bg-gray-100 text-gray-800'
                    }`}>
                      {profile.status}
                    </span>
                    <p className="text-xs text-gray-500 mt-1">
                      {formatMoroccanDate(profile.created_at).date}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8">
              <FileText className="h-12 w-12 text-gray-300 mx-auto mb-4" />
              <p className="text-gray-500">No profiles yet. Create your first one!</p>
            </div>
          )}
        </motion.div>

        {/* Quick Actions */}
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.5, delay: 0.4 }}
          className="card"
        >
          <h2 className="text-lg font-semibold text-gray-900 mb-6">Quick Actions</h2>
          <div className="space-y-3">
            <Link 
              to="/profiles/new"
              className="flex items-center p-3 rounded-lg bg-primary-50 text-primary-700 hover:bg-primary-100 transition-colors duration-200"
            >
              <Plus className="h-5 w-5 mr-3" />
              New Analysis
            </Link>
            <Link 
              to="/profiles"
              className="flex items-center p-3 rounded-lg bg-gray-50 text-gray-700 hover:bg-gray-100 transition-colors duration-200"
            >
              <BarChart3 className="h-5 w-5 mr-3" />
              View Reports
            </Link>
            <button className="flex items-center p-3 rounded-lg bg-gray-50 text-gray-700 hover:bg-gray-100 transition-colors duration-200 w-full">
              <Download className="h-5 w-5 mr-3" />
              Export Data
            </button>
          </div>

          {/* System Status */}
          <div className="mt-8 pt-6 border-t border-gray-200">
            <h3 className="text-sm font-medium text-gray-900 mb-3">System Status</h3>
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-gray-600">API Status</span>
                <span className="flex items-center text-green-600">
                  <div className="w-2 h-2 bg-green-500 rounded-full mr-1"></div>
                  Online
                </span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-gray-600">OCR Service</span>
                <span className="flex items-center text-green-600">
                  <div className="w-2 h-2 bg-green-500 rounded-full mr-1"></div>
                  Ready
                </span>
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  );
};

export default Dashboard;
