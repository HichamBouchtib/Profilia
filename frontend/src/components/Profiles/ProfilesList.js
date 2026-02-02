import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { motion } from 'framer-motion';
import { 
  Search, 
  Plus, 
  FileText, 
  Filter,
  ChevronLeft,
  ChevronRight,
  Eye,
  Download,
  AlertCircle,
  RefreshCw,
  X,
  Mail
} from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';
import axios from 'axios';
import LoadingSpinner from '../UI/LoadingSpinner';
import DeleteConfirmationModal from '../UI/DeleteConfirmationModal';
import toast from 'react-hot-toast';
import { useAuth } from '../../contexts/AuthContext';
import { formatMoroccanDate } from '../../utils/dateUtils';

const ProfilesList = () => {
  const { user } = useAuth();
  const location = useLocation();
  const [profiles, setProfiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalProfiles, setTotalProfiles] = useState(0);
  const [deleteLoading, setDeleteLoading] = useState(null);
  const [emailLoading, setEmailLoading] = useState(null);
  const perPage = 10;

  // Debounce search term to avoid too many API calls
  const [debouncedSearchTerm, setDebouncedSearchTerm] = useState('');
  
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearchTerm(searchTerm);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchTerm]);

  const [showDetailModal, setShowDetailModal] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [reprocessLoading, setReprocessLoading] = useState(false);
  const [selectedProfile, setSelectedProfile] = useState(null);
  
  // Delete confirmation modal state
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [profileToDelete, setProfileToDelete] = useState(null);
  
  // Auto-refresh functionality
  const refreshIntervalRef = useRef(null);
  const [isAutoRefreshEnabled, setIsAutoRefreshEnabled] = useState(false);

  const fetchProfiles = useCallback(async (silent = false) => {
    try {
      if (!silent) {
        setLoading(true);
      }
      const response = await axios.get('/api/profiles', {
        params: {
          page: currentPage,
          per_page: perPage,
          search: debouncedSearchTerm
        }
      });
      
      setProfiles(response.data.profiles);
      setTotalPages(response.data.pages);
      setTotalProfiles(response.data.total);
    } catch (error) {
      console.error('Error fetching profiles:', error);
      toast.error('Failed to fetch profiles');
    } finally {
      setLoading(false);
    }
  }, [currentPage, debouncedSearchTerm, perPage]);

  useEffect(() => {
    fetchProfiles();
  }, [fetchProfiles]);

  // Handle navigation state from NewProfile component
  useEffect(() => {
    if (location.state?.refreshNeeded) {
      const { message, newProfileId } = location.state;
      if (message) {
        toast.success(message, { duration: 4000 });
      }
      // Clear the navigation state to prevent re-showing the message on refresh
      window.history.replaceState({}, document.title);
      
      // Force immediate refresh to show the new profile
      setTimeout(() => {
        fetchProfiles();
      }, 500);
    }
  }, [location.state, fetchProfiles]);

  // Check if there are any processing profiles
  const hasProcessingProfiles = useMemo(() => {
    return profiles.some(profile => profile.status === 'processing');
  }, [profiles]);

  // Auto-refresh effect
  useEffect(() => {
    if (hasProcessingProfiles && !isAutoRefreshEnabled) {
      setIsAutoRefreshEnabled(true);
    } else if (!hasProcessingProfiles && isAutoRefreshEnabled) {
      setIsAutoRefreshEnabled(false);
    }
  }, [hasProcessingProfiles, isAutoRefreshEnabled]);

  // Start/stop refresh interval based on auto-refresh state
  useEffect(() => {
    if (isAutoRefreshEnabled) {
      refreshIntervalRef.current = setInterval(() => {
        fetchProfiles(true); // Silent refresh - no loading state
      }, 5000); // Refresh every 5 seconds

      return () => {
        if (refreshIntervalRef.current) {
          clearInterval(refreshIntervalRef.current);
          refreshIntervalRef.current = null;
        }
      };
    } else {
      if (refreshIntervalRef.current) {
        clearInterval(refreshIntervalRef.current);
        refreshIntervalRef.current = null;
      }
    }
  }, [isAutoRefreshEnabled, fetchProfiles]);

  // Cleanup interval on component unmount
  useEffect(() => {
    return () => {
      if (refreshIntervalRef.current) {
        clearInterval(refreshIntervalRef.current);
      }
    };
  }, []);

  const handleSearch = useCallback((e) => {
    const newSearchTerm = e.target.value;
    setSearchTerm(newSearchTerm);
    // Reset to page 1 when search term changes
    setCurrentPage(1);
  }, []);

  const handleDeleteClick = (profileId, companyName) => {
    setProfileToDelete({ id: profileId, name: companyName });
    setShowDeleteModal(true);
  };

  const handleDelete = async () => {
    if (!profileToDelete) return;

    try {
      setDeleteLoading(profileToDelete.id);
      await axios.delete(`/api/profiles/${profileToDelete.id}`);
      
      // Remove the profile from the local state
      setProfiles(profiles.filter(profile => profile.id !== profileToDelete.id));
      setTotalProfiles(totalProfiles - 1);
      
      toast.success('Profile deleted successfully');
      setShowDeleteModal(false);
      setProfileToDelete(null);
    } catch (error) {
      console.error('Error deleting profile:', error);
      const errorMessage = error.response?.data?.error || 'Failed to delete profile';
      toast.error(errorMessage);
    } finally {
      setDeleteLoading(null);
    }
  };

  const getStatusBadge = (status) => {
    const statusColors = {
      completed: 'bg-green-100 text-green-800',
      processing: 'bg-yellow-100 text-yellow-800',
      failed: 'bg-red-100 text-red-800',
      pending: 'bg-gray-100 text-gray-800'
    };
    
    return (
      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${statusColors[status] || statusColors.pending}`}>
        {status}
      </span>
    );
  };

  const viewProfileDetails = async (profile) => {
    // If profile is completed, open the report in a new tab
    if (profile.status === 'completed') {
      try {
        // Temporarily test without authentication
        // TODO: Re-enable authentication after testing
        const reportUrl = `http://localhost:5000/api/profiles/${profile.id}/report`;
        window.open(reportUrl, '_blank', 'noopener,noreferrer');
      } catch (error) {
        console.error('Error opening report:', error);
        toast.error('Failed to open report');
      }
    } else {
      // For non-completed profiles, show toast message instead of modal
      toast.error('Report is not yet completed. Please wait for processing to complete.');
    }
  };

  const reprocessProfile = async (profileId) => {
    try {
      setReprocessLoading(profileId);
      await axios.post(`/api/profiles/${profileId}/reprocess`);
      toast.success('Reprocessing started');
      // Optimistically update UI
      setProfiles(prev => prev.map(p => p.id === profileId ? { ...p, status: 'processing' } : p));
      setSelectedProfile(prev => prev ? { ...prev, status: 'processing' } : prev);
    } catch (error) {
      console.error('Error reprocessing profile:', error);
      toast.error(error.response?.data?.error || 'Failed to start reprocessing');
    } finally {
      setReprocessLoading(null);
    }
  };

  const downloadProfileReport = async (profile) => {
    if (profile.status !== 'completed') {
      toast.error('Report is not ready yet. Please wait for processing to complete.');
      return;
    }

    try {
      toast.loading('Generating PDF...', { id: 'pdf-download' });
      
      const response = await axios.get(`/api/profiles/${profile.id}/pdf`, {
        responseType: 'blob',
      });

      // Create blob link to download
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      
      // Generate filename with company name and timestamp
      const timestamp = new Date().toISOString().split('T')[0];
      const filename = `${profile.company_name.replace(/[^a-z0-9]/gi, '_')}_report_${timestamp}.pdf`;
      link.setAttribute('download', filename);
      
      // Trigger download
      document.body.appendChild(link);
      link.click();
      link.remove();
      
      // Clean up
      window.URL.revokeObjectURL(url);
      
      toast.success('PDF downloaded successfully!', { id: 'pdf-download' });
    } catch (error) {
      console.error('Error downloading PDF:', error);
      toast.error(error.response?.data?.error || 'Failed to download PDF', { id: 'pdf-download' });
    }
  };

  const sendProfileEmail = async (profile) => {
    if (profile.status !== 'completed') {
      toast.error('Profile must be completed before sending email');
      return;
    }

    try {
      setEmailLoading(profile.id);
      
      const response = await axios.post(`/api/profiles/${profile.id}/send-email`);
      
      if (response.data.message) {
        toast.success('PDF report sent successfully via email!');
      }
    } catch (error) {
      console.error('Error sending email:', error);
      toast.error(error.response?.data?.error || 'Failed to send email');
    } finally {
      setEmailLoading(null);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="flex flex-col sm:flex-row sm:items-center sm:justify-between"
      >
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Company Profiles</h1>
          <p className="text-gray-600 mt-1">
            Manage and view all your company analysis profiles
          </p>
        </div>
        <Link 
          to="/profiles/new"
          className="mt-4 sm:mt-0 btn-primary inline-flex items-center"
        >
          <Plus className="h-4 w-4 mr-2" />
          New Profile
        </Link>
      </motion.div>

      {/* Search and Filters */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.1 }}
        className="card"
      >
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between space-y-4 sm:space-y-0">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
            <input
              type="text"
              placeholder="Search by company name..."
              className="pl-10 input-field"
              value={searchTerm}
              onChange={handleSearch}
            />
          </div>
          
          <div className="flex items-center space-x-3">
            <button className="btn-secondary inline-flex items-center">
              <Filter className="h-4 w-4 mr-2" />
              Filter
            </button>
            <span className="text-sm text-gray-600">
              {totalProfiles} total profiles
            </span>
          </div>
        </div>
      </motion.div>

      {/* Profiles Table */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.2 }}
        className="card p-0 overflow-hidden"
      >
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <LoadingSpinner size="lg" />
          </div>
        ) : profiles.length > 0 ? (
          <>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="table-header">Company</th>
                    <th className="table-header">Status</th>
                    <th className="table-header">Created</th>
                    <th className="table-header">Actions</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {profiles.map((profile, index) => (
                    <motion.tr
                      key={profile.id}
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ duration: 0.3, delay: index * 0.05 }}
                      className="hover:bg-gray-50 transition-colors duration-150"
                    >
                      <td className="table-cell">
                        <div className="flex items-center">
                          <div className="w-8 h-8 bg-primary-100 rounded-lg flex items-center justify-center mr-3">
                            <FileText className="h-4 w-4 text-primary-600" />
                          </div>
                          <div>
                            <div className="font-medium text-gray-900">
                              {profile.company_name}
                            </div>
                            <div className="text-sm text-gray-500">
                              {profile.fiscal_year ? `Fiscal Year: ${profile.fiscal_year}` : ``}
                            </div>
                          </div>
                        </div>
                      </td>
                      <td className="table-cell">
                        {getStatusBadge(profile.status)}
                      </td>
                      <td className="table-cell">
                        <div className="text-sm text-gray-900">
                          {formatMoroccanDate(profile.created_at).date}
                        </div>
                        <div className="text-xs text-gray-500">
                          {formatMoroccanDate(profile.created_at).time}
                        </div>
                      </td>
                      <td className="table-cell">
                        <div className="flex items-center space-x-2">
                          <button 
                            onClick={() => viewProfileDetails(profile)} 
                            className="p-1 text-gray-400 hover:text-gray-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                            disabled={profile.status !== 'completed'}
                            title={profile.status === 'completed' ? 'View report' : 'Report is not yet completed'}
                          >
                            <Eye className="h-4 w-4" />
                          </button>
                          <button 
                            className="p-1 text-gray-400 hover:text-gray-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                            title={profile.status === 'completed' ? 'Download report' : 'Report is not ready yet'}
                            onClick={() => downloadProfileReport(profile)}
                            disabled={profile.status !== 'completed'}
                          >
                            <Download className="h-4 w-4" />
                          </button>
                          <button 
                            className="p-1 text-gray-400 hover:text-blue-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                            title={profile.status === 'completed' ? 'Send report via email' : 'Report is not ready yet'}
                            onClick={() => sendProfileEmail(profile)}
                            disabled={emailLoading === profile.id || profile.status !== 'completed'}
                          >
                            {emailLoading === profile.id ? (
                              <div className="w-4 h-4 border border-gray-300 border-t-blue-600 rounded-full animate-spin"></div>
                            ) : (
                              <Mail className="h-4 w-4" />
                            )}
                          </button>
                          <button
                            onClick={() => reprocessProfile(profile.id)}
                            disabled={reprocessLoading === profile.id || profile.status !== 'completed'}
                            className="p-1 text-gray-400 hover:text-orange-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                            title={profile.status === 'completed' ? 'Reprocess profile' : 'Report is not yet completed'}
                          >
                            {reprocessLoading === profile.id ? (
                              <div className="w-4 h-4 border border-gray-300 border-t-orange-600 rounded-full animate-spin"></div>
                            ) : (
                              <RefreshCw className="h-4 w-4" />
                            )}
                          </button>
                          {user?.role === 'admin' && (
                            <button 
                              className="p-1 text-gray-400 hover:text-red-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                              title="Delete profile"
                              onClick={() => handleDeleteClick(profile.id, profile.company_name)}
                              disabled={deleteLoading === profile.id}
                            >
                              {deleteLoading === profile.id ? (
                                <div className="w-4 h-4 border border-gray-300 border-t-red-600 rounded-full animate-spin"></div>
                              ) : (
                                <X className="h-4 w-4" />
                              )}
                            </button>
                          )}

                        </div>
                      </td>
                    </motion.tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="bg-gray-50 px-6 py-3 flex items-center justify-between border-t border-gray-200">
                <div className="flex items-center text-sm text-gray-700">
                  <span>
                    Showing {((currentPage - 1) * perPage) + 1} to {Math.min(currentPage * perPage, totalProfiles)} of {totalProfiles} results
                  </span>
                </div>
                <div className="flex items-center space-x-2">
                  <button
                    onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                    disabled={currentPage === 1}
                    className="p-2 rounded-lg border border-gray-300 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-100 transition-colors"
                  >
                    <ChevronLeft className="h-4 w-4" />
                  </button>
                  
                  <div className="flex items-center space-x-1">
                    {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                      const page = i + 1;
                      return (
                        <button
                          key={page}
                          onClick={() => setCurrentPage(page)}
                          className={`px-3 py-1 rounded-lg text-sm font-medium transition-colors ${
                            currentPage === page
                              ? 'bg-primary-600 text-white'
                              : 'text-gray-700 hover:bg-gray-100'
                          }`}
                        >
                          {page}
                        </button>
                      );
                    })}
                  </div>
                  
                  <button
                    onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
                    disabled={currentPage === totalPages}
                    className="p-2 rounded-lg border border-gray-300 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-100 transition-colors"
                  >
                    <ChevronRight className="h-4 w-4" />
                  </button>
                </div>
              </div>
            )}
          </>
        ) : (
          <div className="text-center py-12">
            <FileText className="h-12 w-12 text-gray-300 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">No profiles found</h3>
            <p className="text-gray-500 mb-6">
              {searchTerm ? 'Try adjusting your search terms' : 'Get started by creating your first company profile'}
            </p>
            <Link to="/profiles/new" className="btn-primary inline-flex items-center">
              <Plus className="h-4 w-4 mr-2" />
              Create New Profile
            </Link>
          </div>
        )}
      </motion.div>

      {/* Detail Modal */}
      {showDetailModal && selectedProfile && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900">Profile Details</h3>
              <button onClick={() => setShowDetailModal(false)} className="text-gray-400 hover:text-gray-600">
                <X className="h-5 w-5" />
              </button>
            </div>

            {detailLoading ? (
              <div className="py-10 text-center"><LoadingSpinner /></div>
            ) : (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <div className="text-gray-500">ID</div>
                    <div className="text-gray-900 break-all">{selectedProfile.id}</div>
                  </div>
                  <div>
                    <div className="text-gray-500">Company</div>
                    <div className="text-gray-900">{selectedProfile.company_name}</div>
                  </div>
                  {selectedProfile.fiscal_year && (
                    <div>
                      <div className="text-gray-500">Fiscal Year</div>
                      <div className="text-gray-900">{selectedProfile.fiscal_year}</div>
                    </div>
                  )}
                  <div>
                    <div className="text-gray-500">Status</div>
                    <div>{getStatusBadge(selectedProfile.status)}</div>
                  </div>
                </div>

                {selectedProfile.profile_data?.error && (
                  <div className="flex items-start p-4 rounded-lg bg-red-50 border border-red-200">
                    <AlertCircle className="h-5 w-5 text-red-600 mr-3 mt-0.5" />
                    <div>
                      <div className="text-sm font-medium text-red-800">Processing Error</div>
                      <div className="text-sm text-red-700 break-words whitespace-pre-wrap">
                        {selectedProfile.profile_data.error}
                      </div>
                    </div>
                  </div>
                )}

                {selectedProfile.profile_data?.markdown_path && (
                  <div className="text-sm text-gray-700">
                    Markdown saved at: <code className="bg-gray-100 px-1 py-0.5 rounded">{selectedProfile.profile_data.markdown_path}</code>
                  </div>
                )}

                <div>
                  <div className="text-sm font-medium text-gray-900 mb-1">Raw profile_data</div>
                  <pre className="bg-gray-50 border border-gray-200 rounded p-3 text-xs overflow-auto max-h-64">
{JSON.stringify(selectedProfile.profile_data || {}, null, 2)}
                  </pre>
                </div>

                <div className="flex items-center justify-end space-x-2 pt-2">
                  <button onClick={() => setShowDetailModal(false)} className="btn-secondary">Close</button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      <DeleteConfirmationModal
        isOpen={showDeleteModal}
        onClose={() => {
          setShowDeleteModal(false);
          setProfileToDelete(null);
        }}
        onConfirm={handleDelete}
        title="Delete Profile"
        message={profileToDelete ? `Are you sure you want to delete the profile for "${profileToDelete.name}"? This action cannot be undone.` : ''}
        confirmText="Delete"
        cancelText="Cancel"
        isLoading={deleteLoading === profileToDelete?.id}
        danger={true}
      />
    </div>
  );
};

export default ProfilesList;
