#!/usr/bin/env python3
"""
Script to easily set the logging level for the company profile agent.
Usage: python set_log_level.py [level]
Levels: critical, error, info, debug, verbose
"""

import os
import sys

def set_log_level(level: str):
    """Set the log level in the environment"""
    level_map = {
        'critical': 0,
        'error': 1,
        'info': 2,
        'debug': 3,
        'verbose': 4
    }
    
    if level.lower() not in level_map:
        print(f"Invalid log level: {level}")
        print("Valid levels: critical, error, info, debug, verbose")
        return False
    
    log_level = level_map[level.lower()]
    os.environ['LOG_LEVEL'] = str(log_level)
    
    print(f"Log level set to: {level.upper()} (level {log_level})")
    print("This will take effect on the next application restart.")
    return True

def show_current_level():
    """Show the current log level"""
    current_level = int(os.environ.get('LOG_LEVEL', '0'))
    level_names = {0: 'CRITICAL', 1: 'ERROR', 2: 'INFO', 3: 'DEBUG', 4: 'VERBOSE'}
    print(f"Current log level: {level_names.get(current_level, 'UNKNOWN')} (level {current_level})")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python set_log_level.py [level]")
        print("Levels: critical, error, info, debug, verbose")
        print()
        show_current_level()
        sys.exit(1)
    
    level = sys.argv[1]
    if set_log_level(level):
        print("To make this permanent, add LOG_LEVEL=<number> to your .env file")
        print("Example: LOG_LEVEL=0  # for critical only")
