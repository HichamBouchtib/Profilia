# Chartered Accountant Agent

A streamlined document analysis platform designed specifically for chartered accountants to process and analyze financial documents. The system provides automated document processing, KPI extraction, and comprehensive financial reporting.

![Chartered Accountant Agent](officialpage.png)

## 🚀 Features

### Core Functionality
- **Document Processing**: Upload PDF financial documents for automated analysis
- **KPI Extraction**: Automatically extract key financial indicators and ratios from documents
- **Financial Reporting**: Generate comprehensive financial analysis reports
- **Email Integration**: Send analysis reports directly via email
- **Clean Interface**: Simplified, focused interface for efficient workflow

### Key Capabilities
- **PDF Analysis**: Process financial documents using AI-powered OCR
- **Data Extraction**: Extract financial KPIs, ratios, and metadata automatically
- **Report Generation**: Create professional HTML and PDF reports
- **Email Delivery**: Send reports directly to clients via email
- **Secure Processing**: JWT-based authentication and secure file handling

## 🛠 Tech Stack

### Frontend
- **React 18** - Modern UI framework
- **Tailwind CSS** - Utility-first CSS framework
- **Framer Motion** - Smooth animations and transitions
- **Axios** - HTTP client for API communication
- **React Router** - Client-side routing

### Backend
- **Python 3.11** - Core programming language
- **Flask** - Lightweight web framework
- **PostgreSQL** - Reliable database system
- **SQLAlchemy** - Database ORM
- **Anthropic Claude** - AI-powered document analysis
- **PyMuPDF** - PDF processing library
- **WeasyPrint** - HTML to PDF conversion

### Infrastructure
- **Docker & Docker Compose** - Containerized deployment
- **JWT Authentication** - Secure user authentication
- **File Upload System** - Secure document handling

## 📋 Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for local development)
- Node.js 18+ (for local frontend development)

## 🚀 Quick Start

### Using Docker (Recommended)

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd chartered-accountant-agent
   ```

2. **Set up environment variables:**
   ```bash
   # Create .env file
   cp .env.example .env
   # Edit .env with your API keys and configuration
   ```

3. **Start the application:**
   ```bash
   docker-compose up -d
   ```

4. **Access the application:**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:5000
   - Database: localhost:5432

5. **Default Login Credentials:**
   - Email: `admin@example.com`
   - Password: `admin123`

### Local Development

#### Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/accountant_db"
export JWT_SECRET_KEY="your-secret-key"
export ANTHROPIC_API_KEY="your-anthropic-api-key"

python app.py
```

#### Frontend Setup
```bash
cd frontend
npm install
npm start
```

## 📁 Project Structure

```
chartered-accountant-agent/
├── backend/
│   ├── app.py                 # Main Flask application
│   ├── config.py              # Configuration management
│   ├── init.sql               # Database initialization
│   ├── requirements.txt       # Python dependencies
│   ├── services/              # Service modules
│   │   ├── doc_processing.py  # Document OCR and KPI extraction
│   │   ├── financial_reporting.py  # AI-powered financial analysis
│   │   ├── send_email.py      # Email notifications
│   │   └── profile_verification.py  # Document validation
│   ├── expertcomptable/       # Expert comptable specific modules
│   ├── static/                # Static assets
│   ├── uploads/               # File upload directory
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/        # React components
│   │   │   ├── Auth/          # Authentication components
│   │   │   ├── ExpertComptable/ # Main application component
│   │   │   ├── Layout/        # Layout components
│   │   │   └── UI/           # Reusable UI components
│   │   ├── contexts/          # React contexts
│   │   ├── report_template/   # HTML report templates
│   │   └── App.js            # Main React application
│   ├── tailwind.config.js     # Tailwind configuration
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml         # Docker Compose configuration
├── .env.example              # Environment variables template
├── .gitignore                # Git ignore rules
└── README.md
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file with the following variables:

```bash
# Database Configuration
DATABASE_URL=postgresql://postgres:postgres@db:5432/accountant_db

# Security
JWT_SECRET_KEY=your-super-secret-jwt-key
SECRET_KEY=your-flask-secret-key

# AI Services
ANTHROPIC_API_KEY=your-anthropic-api-key
MODEL=claude-sonnet-4-20250514

# File Upload
UPLOAD_FOLDER=uploads
MAX_CONTENT_LENGTH=16777216  # 16MB

# Email Configuration (Optional)
SMTP_HOST=your-smtp-host
SMTP_PORT=587
SMTP_USERNAME=your-email
SMTP_PASSWORD=your-password

# Application Settings
FLASK_ENV=development
DEBUG=True
```

## 🔄 Processing Workflow

The application uses a streamlined processing pipeline:

### 1. **Document Upload**
- Secure file upload with validation
- Support for PDF financial documents
- File size and type validation

### 2. **Document Processing**
- AI-powered OCR using Anthropic Claude
- Automatic KPI extraction from financial documents
- Financial ratio calculations and analysis

### 3. **Report Generation**
- Comprehensive financial analysis reports
- Professional HTML templates
- PDF export capability

### 4. **Email Delivery**
- Send reports directly to clients
- Professional email templates
- Secure file attachments

## 📖 API Documentation

### Expert Comptable Endpoints

#### Process Document
```http
POST /api/expertcompta/process
Content-Type: multipart/form-data

{
  "companyName": "Company Name",
  "file": [PDF file]
}
```

#### Generate Report
```http
POST /api/expertcompta/report
Content-Type: application/json

{
  "companyName": "Company Name",
  "analysisData": {...}
}
```

#### Generate PDF
```http
POST /api/expertcompta/pdf
Content-Type: application/json

{
  "reportData": {...}
}
```

#### Send Email
```http
POST /api/expertcompta/send-email
Content-Type: application/json

{
  "email": "client@example.com",
  "reportData": {...}
}
```

### Authentication Endpoints

#### Login
```http
POST /api/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password123"
}
```

## 🎨 UI/UX Features

### Design System
- **Primary Color:** Blue (`#0ea5e9`)
- **Secondary Color:** Purple (`#d946ef`)
- **Typography:** Inter font family
- **Animations:** Smooth transitions and micro-interactions
- **Layout:** Responsive design optimized for desktop use

### Key User Flows
1. **Authentication:** Secure login with form validation
2. **Document Upload:** Drag-and-drop file upload with validation
3. **Processing:** Real-time processing status updates
4. **Report Viewing:** Interactive HTML reports with financial data
5. **PDF Export:** One-click PDF generation
6. **Email Delivery:** Send reports directly to clients

## 🔒 Security Features

- **JWT Authentication** with configurable expiration
- **Password Hashing** using Werkzeug's secure methods
- **File Validation** for type, size, and security
- **CORS Protection** with configurable origins
- **SQL Injection Prevention** through SQLAlchemy ORM
- **XSS Protection** through React's built-in sanitization

## 🚀 Deployment

### Production Deployment

1. **Server Setup:**
   ```bash
   # Install Docker
   curl -fsSL https://get.docker.com -o get-docker.sh
   sh get-docker.sh

   # Install Docker Compose
   sudo apt-get update
   sudo apt-get install docker-compose-plugin
   ```

2. **Deploy Application:**
   ```bash
   # Clone repository
   git clone <repository-url>
   cd chartered-accountant-agent

   # Set production environment variables
   export FLASK_ENV=production
   export JWT_SECRET_KEY="production-secret-key"
   export DATABASE_URL="postgresql://postgres:secure_password@db:5432/accountant_db"

   # Start production services
   docker-compose up -d
   ```

3. **Configure Reverse Proxy (Nginx):**
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;

       location / {
           proxy_pass http://localhost:3000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }

       location /api {
           proxy_pass http://localhost:5000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

## 📊 Database Schema

### Users Table
- `id` (UUID, Primary Key)
- `email` (Unique, Not Null)
- `password_hash` (Not Null)
- `first_name`, `last_name`
- `role` (analyst, admin)
- `is_active` (Boolean)
- `created_at`, `updated_at`

### Company Profiles Table
- `id` (UUID, Primary Key)
- `company_name` (Not Null)
- `fiscal_years` (String)
- `profile_data` (JSONB) - Financial analysis data
- `status` (processing, completed, failed)
- `created_by` (Foreign Key to Users)
- `created_at`, `updated_at`

### Liasse Documents Table
- `id` (UUID, Primary Key)
- `profile_id` (Foreign Key to Company Profiles)
- `document_type`, `file_name`, `file_path`
- `file_size`
- `upload_status`, `ocr_status`
- `extracted_data` (JSONB)
- `created_at`

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

For technical support or questions:
- Create an issue in the GitHub repository
- Contact the development team

---

**Chartered Accountant Agent** - Streamlining financial document analysis with AI-powered automation.