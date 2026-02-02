/**
 * Utility functions for date formatting in Moroccan timezone
 */

/**
 * Format a date string to Moroccan timezone
 * Morocco uses UTC+1 (no daylight saving time)
 * @param {string} dateString - ISO date string from the backend
 * @returns {Object} - Object with formatted date and time strings
 */
export const formatMoroccanDate = (dateString) => {
  if (!dateString) return { date: '', time: '' };
  
  try {
    // Create date object from the string
    const date = new Date(dateString);
    
    // Check if date is valid
    if (isNaN(date.getTime())) {
      console.warn('Invalid date string:', dateString);
      return { date: '', time: '' };
    }
    
    // Convert to Moroccan time (UTC+1)
    // Morocco doesn't observe daylight saving time, so it's always UTC+1
    const moroccanTime = new Date(date.getTime() + (1 * 60 * 60 * 1000)); // Add 1 hour
    
    // Format date
    const moroccanDate = moroccanTime.toLocaleDateString('en-US', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit'
    });
    
    // Format time
    const moroccanTimeString = moroccanTime.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: false
    });
    
    return {
      date: moroccanDate,
      time: moroccanTimeString
    };
  } catch (error) {
    console.error('Error formatting Moroccan date:', error);
    return { date: '', time: '' };
  }
};

/**
 * Format a date string to Moroccan timezone with a single formatted string
 * @param {string} dateString - ISO date string from the backend
 * @param {Object} options - Formatting options
 * @returns {string} - Formatted date string
 */
export const formatMoroccanDateTime = (dateString, options = {}) => {
  if (!dateString) return '';
  
  try {
    const date = new Date(dateString);
    
    if (isNaN(date.getTime())) {
      console.warn('Invalid date string:', dateString);
      return '';
    }
    
    // Convert to Moroccan time (UTC+1)
    const moroccanTime = new Date(date.getTime() + (1 * 60 * 60 * 1000)); // Add 1 hour
    
    const defaultOptions = {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false
    };
    
    const formatOptions = { ...defaultOptions, ...options };
    
    return moroccanTime.toLocaleString('en-US', formatOptions);
  } catch (error) {
    console.error('Error formatting Moroccan date time:', error);
    return '';
  }
};

/**
 * Get relative time in Moroccan timezone (e.g., "2 hours ago")
 * @param {string} dateString - ISO date string from the backend
 * @returns {string} - Relative time string
 */
export const getMoroccanRelativeTime = (dateString) => {
  if (!dateString) return '';
  
  try {
    const date = new Date(dateString);
    
    if (isNaN(date.getTime())) {
      console.warn('Invalid date string:', dateString);
      return '';
    }
    
    // Convert to Moroccan time (UTC+1)
    const moroccanDate = new Date(date.getTime() + (1 * 60 * 60 * 1000)); // Add 1 hour
    const now = new Date();
    const diffInSeconds = Math.floor((now - moroccanDate) / 1000);
    
    if (diffInSeconds < 60) {
      return 'Just now';
    } else if (diffInSeconds < 3600) {
      const minutes = Math.floor(diffInSeconds / 60);
      return `${minutes} minute${minutes > 1 ? 's' : ''} ago`;
    } else if (diffInSeconds < 86400) {
      const hours = Math.floor(diffInSeconds / 3600);
      return `${hours} hour${hours > 1 ? 's' : ''} ago`;
    } else if (diffInSeconds < 2592000) {
      const days = Math.floor(diffInSeconds / 86400);
      return `${days} day${days > 1 ? 's' : ''} ago`;
    } else {
      // For older dates, show the actual date
      return formatMoroccanDate(dateString).date;
    }
  } catch (error) {
    console.error('Error getting Moroccan relative time:', error);
    return '';
  }
};
