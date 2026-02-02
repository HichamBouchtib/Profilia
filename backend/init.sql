-- Create database schema
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Ensure postgres user exists with correct password
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'postgres') THEN
        CREATE ROLE postgres WITH LOGIN SUPERUSER CREATEDB CREATEROLE PASSWORD 'postgres';
    END IF;
END
$$;

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    role VARCHAR(50) DEFAULT 'analyst',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Company profiles table
CREATE TABLE IF NOT EXISTS company_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_name VARCHAR(255) NOT NULL,
    fiscal_years VARCHAR(20),
    profile_data JSONB,
    status VARCHAR(50) DEFAULT 'processing',
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Liasse fiscale documents table
CREATE TABLE IF NOT EXISTS liasse_documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    profile_id UUID REFERENCES company_profiles(id) ON DELETE CASCADE,
    document_type VARCHAR(100),
    file_name VARCHAR(255),
    file_path VARCHAR(500),
    file_size INTEGER,
    upload_status VARCHAR(50) DEFAULT 'uploaded',
    ocr_status VARCHAR(50) DEFAULT 'pending',
    extracted_data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_company_profiles_created_by ON company_profiles(created_by);
CREATE INDEX IF NOT EXISTS idx_company_profiles_status ON company_profiles(status);
CREATE INDEX IF NOT EXISTS idx_company_profiles_fiscal_years ON company_profiles(fiscal_years);
CREATE INDEX IF NOT EXISTS idx_company_profiles_name_year ON company_profiles(company_name, fiscal_years);
CREATE INDEX IF NOT EXISTS idx_liasse_documents_profile_id ON liasse_documents(profile_id);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- Insert default admin user (password: Admin123)
-- Hash generated with: python scripts/generate_password.py
INSERT INTO users (email, password_hash, first_name, last_name, role) 
VALUES (
    'admin@burjfinance.com', 
    'scrypt:32768:8:1$mccrtS3P8W5Z9f53$6e78cbc0536772ed544c272a24226d47476df523980fd72e41d7a5201ad34567e14f1ada619496d0df4d8f780be351f7bde4931de12a51b1052f1fd3442e2fcc',
    'Admin',
    'User',
    'admin'
) ON CONFLICT (email) DO NOTHING;

-- Insert user s.benaddou@burjfinance.com (password: Salma123.)
-- Hash generated with: python scripts/generate_password.py
INSERT INTO users (email, password_hash, first_name, last_name, role) 
VALUES (
    's.benaddou@burjfinance.com', 
    'scrypt:32768:8:1$NHlVh9xEFqCN7XWB$c5db28d988e4575951d0842934cc90d477fa36ac66d0fab4658d9a97477d383c21d260a2d0a56c7548f2d10f90ccca49caad3d67d4e0dfa0a1d4f0d93db5feee',
    'Salma',
    'Benaddou',
    'admin'
) ON CONFLICT (email) DO NOTHING;
