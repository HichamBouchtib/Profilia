"""
Centralized logging configuration for the company profile agent.
Controls log verbosity and provides consistent logging across all services.
"""

import os
import sys
from datetime import datetime
from typing import Any, Optional

class Logger:
    """Centralized logger with configurable verbosity levels"""
    
    # Log levels
    CRITICAL = 0  # Only critical errors and important status updates
    ERROR = 1     # Errors and warnings
    INFO = 2      # Basic information
    DEBUG = 3     # Detailed debugging information
    VERBOSE = 4   # Very detailed debugging (current default behavior)
    
    def __init__(self):
        # Get log level from environment variable, default to CRITICAL for production
        self.log_level = int(os.environ.get('LOG_LEVEL', str(self.CRITICAL)))
        self.enable_emojis = os.environ.get('LOG_EMOJIS', 'true').lower() in ('1', 'true', 'yes')
        
    def _should_log(self, level: int) -> bool:
        """Check if message should be logged based on current log level"""
        return level <= self.log_level
    
    def _format_message(self, level: str, message: str, emoji: str = "") -> str:
        """Format log message with timestamp and level"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        if self.enable_emojis and emoji:
            return f"{timestamp} [{level}] {emoji} {message}"
        else:
            return f"{timestamp} [{level}] {message}"
    
    def critical(self, message: str, emoji: str = "🚨"):
        """Log critical messages (always shown)"""
        if self._should_log(self.CRITICAL):
            print(self._format_message("CRITICAL", message, emoji), flush=True)
    
    def error(self, message: str, emoji: str = "❌"):
        """Log error messages"""
        if self._should_log(self.ERROR):
            print(self._format_message("ERROR", message, emoji), flush=True)
    
    def warning(self, message: str, emoji: str = "⚠️"):
        """Log warning messages"""
        if self._should_log(self.ERROR):
            print(self._format_message("WARNING", message, emoji), flush=True)
    
    def info(self, message: str, emoji: str = "ℹ️"):
        """Log informational messages"""
        if self._should_log(self.INFO):
            print(self._format_message("INFO", message, emoji), flush=True)
    
    def success(self, message: str, emoji: str = "✅"):
        """Log success messages"""
        if self._should_log(self.INFO):
            print(self._format_message("SUCCESS", message, emoji), flush=True)
    
    def debug(self, message: str, data: Any = None, emoji: str = "🔍"):
        """Log debug messages with optional data"""
        if self._should_log(self.DEBUG):
            print(self._format_message("DEBUG", message, emoji), flush=True)
            if data is not None:
                import json
                print(f"  Data: {json.dumps(data, indent=2, ensure_ascii=False)}", flush=True)
    
    def verbose(self, message: str, data: Any = None, emoji: str = "🔍"):
        """Log very detailed debug messages (current default behavior)"""
        if self._should_log(self.VERBOSE):
            print(self._format_message("VERBOSE", message, emoji), flush=True)
            if data is not None:
                import json
                print(f"  Data: {json.dumps(data, indent=2, ensure_ascii=False)}", flush=True)
    
    def processing(self, profile_id: str, message: str, emoji: str = "📄"):
        """Log processing messages for specific profiles"""
        if self._should_log(self.INFO):
            timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
            if self.enable_emojis and emoji:
                print(f"[PROCESSING {profile_id}] {timestamp}: {emoji} {message}", flush=True)
            else:
                print(f"[PROCESSING {profile_id}] {timestamp}: {message}", flush=True)
    
    def web_exploring(self, message: str, data: Any = None, emoji: str = "🌐"):
        """Log web exploring messages"""
        if self._should_log(self.DEBUG):
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            if self.enable_emojis and emoji:
                print(f"{timestamp} [WEB_EXPLORING] {emoji} {message}", flush=True)
            else:
                print(f"{timestamp} [WEB_EXPLORING] {message}", flush=True)
            if data is not None:
                import json
                print(f"  Data: {json.dumps(data, indent=2, ensure_ascii=False)}", flush=True)
    
    def news(self, message: str, emoji: str = "📰"):
        """Log news retrieval messages"""
        if self._should_log(self.DEBUG):
            if self.enable_emojis and emoji:
                print(f"{emoji} {message}", flush=True)
            else:
                print(f"NEWS: {message}", flush=True)
    
    def database(self, message: str, emoji: str = "💾"):
        """Log database operations"""
        if self._should_log(self.DEBUG):
            if self.enable_emojis and emoji:
                print(f"{emoji} {message}", flush=True)
            else:
                print(f"DB: {message}", flush=True)
    
    def cleanup(self, message: str, emoji: str = "🗑️"):
        """Log cleanup operations"""
        if self._should_log(self.INFO):
            if self.enable_emojis and emoji:
                print(f"{emoji} {message}", flush=True)
            else:
                print(f"CLEANUP: {message}", flush=True)

# Global logger instance
logger = Logger()

# Convenience functions for backward compatibility
def log_critical(message: str, emoji: str = "🚨"):
    logger.critical(message, emoji)

def log_error(message: str, emoji: str = "❌"):
    logger.error(message, emoji)

def log_warning(message: str, emoji: str = "⚠️"):
    logger.warning(message, emoji)

def log_info(message: str, emoji: str = "ℹ️"):
    logger.info(message, emoji)

def log_success(message: str, emoji: str = "✅"):
    logger.success(message, emoji)

def log_debug(message: str, data: Any = None, emoji: str = "🔍"):
    logger.debug(message, data, emoji)

def log_verbose(message: str, data: Any = None, emoji: str = "🔍"):
    logger.verbose(message, data, emoji)

def log_processing(profile_id: str, message: str, emoji: str = "📄"):
    logger.processing(profile_id, message, emoji)

def log_web_exploring(message: str, data: Any = None, emoji: str = "🌐"):
    logger.web_exploring(message, data, emoji)

def log_news(message: str, emoji: str = "📰"):
    logger.news(message, emoji)

def log_database(message: str, emoji: str = "💾"):
    logger.database(message, emoji)

def log_cleanup(message: str, emoji: str = "🗑️"):
    logger.cleanup(message, emoji)
