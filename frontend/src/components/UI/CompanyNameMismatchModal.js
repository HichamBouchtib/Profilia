import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { AlertTriangle, FileText, X } from 'lucide-react';

const CompanyNameMismatchModal = ({ 
  isOpen, 
  onClose, 
  onConfirm, 
  onCancel, 
  comparisonResult, 
  profileCompany, 
  documentCompanies,
  isVerificationMismatch = false
}) => {
  if (!isOpen) return null;

  const getSeverityColor = () => {
    if (comparisonResult?.partial_matches?.length > 0) {
      return 'yellow';
    }
    if (comparisonResult?.similar_names?.length > 0) {
      return 'orange';
    }
    return 'red';
  };

  const getSeverityIcon = () => {
    const color = getSeverityColor();
    switch (color) {
      case 'yellow':
        return <AlertTriangle className="h-6 w-6 text-yellow-600" />;
      case 'orange':
        return <AlertTriangle className="h-6 w-6 text-orange-600" />;
      default:
        return <AlertTriangle className="h-6 w-6 text-red-600" />;
    }
  };

  const getSeverityClass = () => {
    const color = getSeverityColor();
    switch (color) {
      case 'yellow':
        return 'border-yellow-200 bg-yellow-50';
      case 'orange':
        return 'border-orange-200 bg-orange-50';
      default:
        return 'border-red-200 bg-red-50';
    }
  };

  const getModalTitle = () => {
    if (isVerificationMismatch) {
      return 'Company Name Mismatch Detected';
    }
    return 'Company Name Mismatch Detected';
  };

  const getModalDescription = () => {
    if (isVerificationMismatch) {
      return 'The uploaded documents appear to be for different companies. You can still proceed with profile creation or start over with new documents.';
    }
    return 'The uploaded documents appear to be for different companies';
  };

  const getConfirmButtonText = () => {
    if (isVerificationMismatch) {
      return 'Yes, Process Anyway';
    }
    return 'Proceed Anyway';
  };

  const getCancelButtonText = () => {
    if (isVerificationMismatch) {
      return 'No, Start Over';
    }
    return 'Cancel Upload';
  };

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black bg-opacity-50"
        onClick={onClose}
      >
        <motion.div
          initial={{ scale: 0.95, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.95, opacity: 0 }}
          className={`relative w-full max-w-lg bg-white rounded-lg shadow-xl ${getSeverityClass()}`}
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b border-gray-200">
            <div className="flex items-center space-x-3">
              {getSeverityIcon()}
              <div>
                <h3 className="text-lg font-semibold text-gray-900">
                  {getModalTitle()}
                </h3>
                <p className="text-sm text-gray-600">
                  {getModalDescription()}
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 transition-colors"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Content */}
          <div className="p-6 space-y-6">
            {/* Document Companies */}
            <div className="bg-white p-4 rounded-lg border border-gray-200">
              <div className="flex items-center space-x-2 mb-3">
                <FileText className="h-4 w-4 text-gray-600" />
                <span className="font-medium text-gray-900">Companies in Documents</span>
              </div>
              <div className="space-y-2">
                {documentCompanies.map((company, index) => (
                  <div key={index} className="flex items-center space-x-2">
                    <div className="w-2 h-2 bg-gray-400 rounded-full"></div>
                    <span className="text-gray-700">{company}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center justify-end space-x-3 p-6 border-t border-gray-200 bg-gray-50">
            <button
              onClick={onCancel}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500 transition-colors"
            >
              {getCancelButtonText()}
            </button>
            <button
              onClick={onConfirm}
              className={`px-4 py-2 text-sm font-medium text-white border border-transparent rounded-md focus:outline-none focus:ring-2 focus:ring-offset-2 transition-colors ${
                isVerificationMismatch 
                  ? 'bg-blue-600 hover:bg-blue-700 focus:ring-blue-500' 
                  : 'bg-red-600 hover:bg-red-700 focus:ring-red-500'
              }`}
            >
              {getConfirmButtonText()}
            </button>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
};

export default CompanyNameMismatchModal;
