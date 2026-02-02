#!/usr/bin/env python3
"""
Script to generate password hashes for the application.
Usage: python generate_password.py <password>
"""

import sys
from werkzeug.security import generate_password_hash


    
hash_value = generate_password_hash("Admin123")
print(f"Hash: {hash_value}")
print(f"\nFor SQL insertion:")
print(f"'{hash_value}'")


# hash_value = generate_password_hash("Salma123.")
# print(f"Hash: {hash_value}")
# print(f"\nFor SQL insertion:")
# print(f"'{hash_value}'")


