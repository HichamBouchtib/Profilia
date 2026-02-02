import os
import sys
import time
from datetime import datetime, timedelta
import threading

# Ensure stdout is unbuffered for immediate output visibility in Docker
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

# Import the new logging system
from utils.logger import log_info, log_success, log_error, log_warning, log_debug, log_database
from flask import Flask, request, jsonify, render_template_string
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_cors import CORS
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from services.send_email import send_email
from services.doc_processing import process_doc_processing
import uuid
import json
from pathlib import Path
from config import config
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy import text

# Thread tracking system for background processes
class ThreadTracker:
    def __init__(self):
        self.active_threads = {}  # profile_id -> list of thread objects
        self.lock = threading.Lock()
    
    def add_thread(self, profile_id, thread):
        """Add a thread to the tracking system for a specific profile."""
        with self.lock:
            if profile_id not in self.active_threads:
                self.active_threads[profile_id] = []
            self.active_threads[profile_id].append(thread)
    
    def remove_thread(self, profile_id, thread):
        """Remove a thread from the tracking system."""
        with self.lock:
            if profile_id in self.active_threads:
                try:
                    self.active_threads[profile_id].remove(thread)
                    if not self.active_threads[profile_id]:
                        del self.active_threads[profile_id]
                        # print(f"🔗 No more active threads for profile {profile_id}", flush=True)
                except ValueError:
                    pass  # Thread was already removed
    
    def stop_profile_threads(self, profile_id):
        """Stop all threads associated with a specific profile."""
        with self.lock:
            if profile_id in self.active_threads:
                threads_to_stop = self.active_threads[profile_id].copy()
                print(f"🛑 Stopping {len(threads_to_stop)} threads for profile {profile_id}", flush=True)
                
                for thread in threads_to_stop:
                    if thread.is_alive():
                        # Set a flag to stop the thread gracefully
                        if hasattr(thread, '_stop_flag'):
                            thread._stop_flag = True
                        print(f"🛑 Stopping thread {thread.name} for profile {profile_id}", flush=True)
                
                # Clear the threads from tracking
                del self.active_threads[profile_id]
                print(f"🛑 Cleared thread tracking for profile {profile_id}", flush=True)
                
                return len(threads_to_stop)
            return 0
    
    def get_active_profiles(self):
        """Get list of profile IDs that have active threads."""
        with self.lock:
            return list(self.active_threads.keys())
    
    def cleanup_dead_threads(self):
        """Remove references to threads that are no longer alive."""
        with self.lock:
            for profile_id in list(self.active_threads.keys()):
                self.active_threads[profile_id] = [
                    thread for thread in self.active_threads[profile_id] 
                    if thread.is_alive()
                ]
                if not self.active_threads[profile_id]:
                    del self.active_threads[profile_id]

# Global thread tracker instance
thread_tracker = ThreadTracker()

app = Flask(__name__)

# Configuration
env = os.environ.get('FLASK_ENV', 'default')
app.config.from_object(config[env])

# Extensions
db = SQLAlchemy(app)
jwt = JWTManager(app)
CORS(app, origins=app.config['CORS_ORIGINS'])

# Ensure upload directory exists
Path(app.config['UPLOAD_FOLDER']).mkdir(exist_ok=True)



def send_pdf_report_email(profile_id: str) -> bool:
    """Send PDF report via email to the user who requested it."""
    try:
        with app.app_context():
            profile = db.session.get(CompanyProfile, profile_id)
            if not profile:
                print(f"❌ Profile {profile_id} not found for email sending", flush=True)
                return False
                
            # Check if user opted for email report
            profile_data = profile.profile_data or {}
            email_report = profile_data.get('email_report', False)
            
            if not email_report:
                print(f"📧 User did not opt for email report for profile {profile_id}", flush=True)
                return False
                
            # Get user email
            user = db.session.get(User, profile.created_by)
            if not user or not user.email:
                print(f"❌ User email not found for profile {profile_id}", flush=True)
                return False
                
            # Generate PDF using the existing get_profile_pdf logic
            from datetime import datetime
            from io import BytesIO
            
            # Reuse the PDF generation logic from get_profile_pdf
            if profile.status != 'completed':
                print(f"⏳ Profile {profile_id} is not completed yet, skipping email", flush=True)
                return False
                
            extracted_kpis = profile_data.get('extracted_kpis')
            computed_ratios = profile_data.get('computed_ratios')
            web_data = profile_data.get('web_data', {})
            company_name = profile_data.get('company_name') or profile.company_name
            
            if not extracted_kpis and not computed_ratios:
                print(f"❌ Financial data not available for profile {profile_id}", flush=True)
                return False
                
            # Generate PDF content (simplified version)
            basic_info = web_data.get('basic_info', {})
            company_overview = basic_info.get('companyOverview', {})
            contact = basic_info.get('contact', {})
            
            def safe_get(value, default=''):
                return str(value) if value is not None else default
            
            # Create clean PDF-friendly HTML
            clean_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>{company_name} - Company Profile</title>
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        margin: 40px;
                        line-height: 1.6;
                        color: #333;
                    }}
                    .header {{
                        text-align: center;
                        border-bottom: 3px solid #007bff;
                        padding-bottom: 20px;
                        margin-bottom: 30px;
                    }}
                    h1 {{
                        color: #007bff;
                        font-size: 28px;
                        margin-bottom: 10px;
                    }}
                    h2 {{
                        color: #555;
                        font-size: 20px;
                        margin-top: 30px;
                        margin-bottom: 15px;
                        border-left: 4px solid #007bff;
                        padding-left: 15px;
                    }}
                    .section {{
                        margin: 25px 0;
                        padding: 15px;
                        border: 1px solid #eee;
                        border-radius: 5px;
                    }}
                    .metric {{
                        margin: 8px 0;
                        padding: 5px 0;
                    }}
                    .metric strong {{
                        color: #007bff;
                        display: inline-block;
                        width: 150px;
                    }}
                    table {{
                        width: 100%;
                        border-collapse: collapse;
                        margin: 15px 0;
                    }}
                    th, td {{
                        border: 1px solid #ddd;
                        padding: 8px;
                        text-align: left;
                    }}
                    th {{
                        background-color: #f2f2f2;
                        font-weight: bold;
                    }}
                    .footer {{
                        margin-top: 40px;
                        padding-top: 20px;
                        border-top: 1px solid #ddd;
                        font-size: 12px;
                        color: #666;
                        text-align: center;
                    }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>{company_name}</h1>
                    <p>Company Profile Report</p>
                </div>

                <div class="section">
                    <h2>Company Overview</h2>
                    <div class="metric"><strong>Company Name:</strong> {company_name}</div>
                    <div class="metric"><strong>Legal Form:</strong> {safe_get(company_overview.get('legal_form'), 'Not specified')}</div>
                    <div class="metric"><strong>Founded:</strong> {safe_get(company_overview.get('companyFoundationyear'), 'Not specified')}</div>
                    <div class="metric"><strong>Primary Sector:</strong> {safe_get(company_overview.get('primary_sector'), 'General sector')}</div>
                    <div class="metric"><strong>Expertise:</strong> {safe_get(company_overview.get('companyExpertise'), 'To be determined')}</div>
                </div>"""
            
            # Add financial data if available
            if extracted_kpis:
                clean_html += """
                <div class="section">
                    <h2>Financial Information</h2>
                    <table>
                        <tr><th>Metric</th><th>Value</th></tr>"""
                
                for key, value in extracted_kpis.items():
                    if value is not None:
                        clean_html += f"<tr><td>{key.replace('_', ' ').title()}</td><td>{value}</td></tr>"
                
                clean_html += "</table></div>"
            
            if computed_ratios:
                clean_html += """
                    <div class="section">
                        <h2>Financial Ratios</h2>
                        <table>
                            <tr><th>Ratio</th><th>Value</th></tr>"""
                
                for key, value in computed_ratios.items():
                    if value is not None:
                        clean_html += f"<tr><td>{key.replace('_', ' ').title()}</td><td>{value}</td></tr>"
                
                clean_html += "</table></div>"
            
            clean_html += f"""
                <div class="section">
                    <h2>Contact Information</h2>
                    <div class="metric"><strong>Address:</strong> {safe_get(contact.get('address'), 'Not available')}</div>
                    <div class="metric"><strong>Phone:</strong> {safe_get(contact.get('phone'), 'Not available')}</div>
                    <div class="metric"><strong>Email:</strong> {safe_get(contact.get('email'), 'Not available')}</div>
                    <div class="metric"><strong>Website:</strong> {safe_get(contact.get('website'), 'Not available')}</div>
                </div>
                
                <div class="footer">
                    <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                    <p>Company Profile Agent - Automated Analysis Report</p>
                </div>
            </body>
            </html>
            """
            
            # Generate PDF from HTML
            from weasyprint import HTML
            pdf_buffer = BytesIO()
            html_doc = HTML(string=clean_html, encoding='utf-8', base_url='')
            html_doc.write_pdf(pdf_buffer)
            
            # Get PDF content
            pdf_content = pdf_buffer.getvalue()
            pdf_buffer.close()
            
            # Generate filename
            timestamp = datetime.now().strftime('%Y-%m-%d')
            filename = f"{company_name.replace(' ', '_')}_report_{timestamp}.pdf"
            
            # Send email with PDF attachment
            email_body = f"""Hello,

            Your company analysis report for {company_name} is now ready!

            Please find attached the comprehensive PDF report with:
            - Company overview and financial analysis
            - Key performance indicators and ratios
            - Market insights and recommendations

            The report has been automatically generated based on the documents you provided.

            Best regards,
            Company Profile Agent

            ---
            This is an automated message. The report was generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}.
            """
            
            print(f"📧 Attempting to send PDF report to {user.email} for profile {profile_id}", flush=True)
            success = send_email(
                to_email=user.email,
                subject=f'Your Company Analysis Report - {company_name}',
                body=email_body,
                attachment_data=pdf_content,
                attachment_filename=filename
            )
            
            if success:
                print(f"✅ PDF report sent successfully to {user.email} for profile {profile_id}", flush=True)
                return True
            else:
                print(f"❌ Failed to send PDF report to {user.email} for profile {profile_id}", flush=True)
                return False
                
    except Exception as e:
        print(f"❌ Error sending PDF report for profile {profile_id}: {str(e)}", flush=True)
        return False

def process_doc_processing_with_web_sync(flask_app, db, CompanyProfile, LiasseDocument, profile_id: str, web_thread) -> None:
    """Process documents directly without waiting for web exploring."""
    with flask_app.app_context():
        try:
            
            # Skip web exploring wait if web_thread is None
            if web_thread is not None:
                # Wait for web exploring to complete (with timeout)
                web_thread.join(timeout=300)  # 5 minutes timeout
                
                if web_thread.is_alive():
                    print(f"⚠️ Web exploring timeout for profile {profile_id}, proceeding with doc processing", flush=True)
            
            # Now proceed with document processing
            from services.doc_processing import process_doc_processing
            process_doc_processing(flask_app, db, CompanyProfile, LiasseDocument, profile_id)
            
            # After doc processing completes, generate financial analysis
            try:
                # print(f"📊 Starting financial analysis generation for profile {profile_id}", flush=True)
                from services.financial_reporting import generate_financial_analysis
                
                # Get the profile data
                profile = CompanyProfile.query.get(profile_id)
                if profile and profile.profile_data:
                    profile_data = profile.profile_data
                    
                    # Extract data for financial analysis
                    extracted_kpis = profile_data.get('extracted_kpis', {})
                    computed_ratios = profile_data.get('computed_ratios', {})
                    
                    if extracted_kpis and computed_ratios:
                        print(f"📊 Generating financial analysis for {profile.company_name}", flush=True)
                        print(f"📊 Data summary - KPIs: {len(extracted_kpis)} keys, Ratios: {len(computed_ratios)} keys", flush=True)
                        
                        # Generate financial analysis without web and news data
                        financial_analysis = generate_financial_analysis(
                            company_name=profile.company_name,
                            extracted_kpis=extracted_kpis,
                            computed_ratios=computed_ratios,
                            news_data='',
                            web_data={},
                            fiscal_year=profile.fiscal_years
                        )
                        
                        # Debug: Log what we got from financial analysis
                        print(f"🔍 Financial analysis result keys: {list(financial_analysis.keys()) if isinstance(financial_analysis, dict) else 'Not a dict'}", flush=True)
                        if isinstance(financial_analysis, dict):
                            for key, value in financial_analysis.items():
                                if isinstance(value, str):
                                    print(f"🔍 {key}: {len(value)} chars - {value[:100]}...", flush=True)
                                elif isinstance(value, dict):
                                    print(f"🔍 {key}: {len(value)} keys - {list(value.keys())}", flush=True)
                                else:
                                    print(f"🔍 {key}: {type(value)} - {value}", flush=True)
                        
                        # Add financial analysis to profile data
                        profile_data.update(financial_analysis)
                        profile.profile_data = profile_data
                        db.session.commit()
                        
                        # print(f"✅ Financial analysis completed and saved for {profile.company_name}", flush=True)
                        
                        # Now set the profile status to completed after financial analysis is done
                        profile.status = 'completed'
                        db.session.commit()
                        # print(f"✅ Profile {profile_id} marked as completed after financial analysis", flush=True)
                        
                        # Verify the data was saved
                        db.session.refresh(profile)
                        saved_data = profile.profile_data or {}
                        # print(f"🔍 Verification - saved profile_data keys: {list(saved_data.keys())}", flush=True)
                        if 'recommendation' in saved_data:
                            print(f"🔍 Verification - recommendation length: {len(saved_data['recommendation'])}", flush=True)
                        if 'detailed_analysis' in saved_data:
                            print(f"🔍 Verification - detailed_analysis length: {len(saved_data['detailed_analysis'])}", flush=True)
                    else:
                        print(f"⚠️ Missing data for financial analysis: KPIs={bool(extracted_kpis)}, Ratios={bool(computed_ratios)}", flush=True)
                        # Even if financial analysis fails, mark as completed with fallback data
                        profile.status = 'completed'
                        db.session.commit()
                        print(f"✅ Profile {profile_id} marked as completed with fallback data", flush=True)
                        
            except Exception as analysis_error:
                print(f"❌ Error generating financial analysis for profile {profile_id}: {str(analysis_error)}", flush=True)
                # Mark as completed even if financial analysis fails
                try:
                    profile = CompanyProfile.query.get(profile_id)
                    if profile:
                        profile.status = 'completed'
                        db.session.commit()
                        print(f"✅ Profile {profile_id} marked as completed despite financial analysis error", flush=True)
                except Exception as status_error:
                    print(f"❌ Failed to update profile status: {str(status_error)}", flush=True)
            
            # Check if profile was completed and send email if user opted in
            try:
                profile = CompanyProfile.query.get(profile_id)
                if profile and profile.status == 'completed':
                    email_report = bool((profile.profile_data or {}).get('email_report'))
                    if email_report:
                        print(f"📧 Profile {profile_id} completed with email preference, sending PDF report...", flush=True)
                        # Send PDF report via email in a separate thread to avoid blocking
                        import threading
                        email_thread = threading.Thread(
                            target=send_pdf_report_email,
                            args=(profile_id,),
                            daemon=True
                        )
                        email_thread.start()
                        print(f"🚀 Started email thread for profile {profile_id}", flush=True)
                    else:
                        print(f"📧 Profile {profile_id} completed but no email preference set", flush=True)
                else:
                    print(f"📧 Profile {profile_id} status: {profile.status if profile else 'not found'}", flush=True)
            except Exception as email_error:
                print(f"⚠️ Error checking email preference for profile {profile_id}: {str(email_error)}", flush=True)
            
        except Exception as e:
            print(f"❌ Doc processing with web sync failed for profile {profile_id}: {str(e)}", flush=True)

# Models
class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(50), default='analyst')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class CompanyProfile(db.Model):
    __tablename__ = 'company_profiles'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    company_name = db.Column(db.String(255), nullable=False)
    fiscal_years = db.Column(db.String(20), nullable=True)  # Fiscal years column (can be single year or range like "2022-2023")
    profile_data = db.Column(MutableDict.as_mutable(db.JSON))  # 👈 this
    status = db.Column(db.String(50), default='processing')
    created_by = db.Column(db.String(36), db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class LiasseDocument(db.Model):
    __tablename__ = 'liasse_documents'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    profile_id = db.Column(db.String(36), db.ForeignKey('company_profiles.id', ondelete='CASCADE'))
    document_type = db.Column(db.String(100))
    file_name = db.Column(db.String(255))
    file_path = db.Column(db.String(500))
    file_size = db.Column(db.Integer)
    upload_status = db.Column(db.String(50), default='uploaded')
    ocr_status = db.Column(db.String(50), default='pending')
    extracted_data = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Routes
@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()})

@app.route('/api/auth/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({'error': 'Email and password are required'}), 400
        
        user = User.query.filter_by(email=email, is_active=True).first()
        
        if user and check_password_hash(user.password_hash, password):
            access_token = create_access_token(
                identity=user.id,
                additional_claims={
                    'email': user.email,
                    'role': user.role,
                    'name': f"{user.first_name} {user.last_name}"
                }
            )
            
            return jsonify({
                'access_token': access_token,
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'name': f"{user.first_name} {user.last_name}",
                    'role': user.role
                }
            })
        
        return jsonify({'error': 'Invalid credentials'}), 401
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/auth/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        
        # Check if user already exists
        if User.query.filter_by(email=data['email']).first():
            return jsonify({'error': 'User already exists'}), 400
        
        # Create new user
        user = User(
            email=data['email'],
            password_hash=generate_password_hash(data['password']),
            first_name=data['first_name'],
            last_name=data['last_name'],
            role=data.get('role', 'analyst')
        )
        
        db.session.add(user)
        db.session.commit()
        
        return jsonify({'message': 'User created successfully'}), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/dashboard/stats', methods=['GET'])
@jwt_required()
def get_dashboard_stats():
    """Get dashboard statistics including counts and percentage changes"""
    try:
        from sqlalchemy import func, extract
        from datetime import datetime, timedelta
        
        # Get current date info
        now = datetime.utcnow()
        current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_month_start = (current_month_start - timedelta(days=1)).replace(day=1)
        last_month_end = current_month_start - timedelta(seconds=1)
        
        # Total profiles count
        total_profiles = CompanyProfile.query.count()
        
        # This month's profiles
        this_month_profiles = CompanyProfile.query.filter(
            CompanyProfile.created_at >= current_month_start
        ).count()
        
        # Last month's profiles for comparison
        last_month_profiles = CompanyProfile.query.filter(
            CompanyProfile.created_at >= last_month_start,
            CompanyProfile.created_at <= last_month_end
        ).count()
        
        # Processing profiles
        processing_profiles = CompanyProfile.query.filter(
            CompanyProfile.status == 'processing'
        ).count()
        
        # Completed profiles
        completed_profiles = CompanyProfile.query.filter(
            CompanyProfile.status == 'completed'
        ).count()
        
        # Failed profiles (for success rate calculation)
        failed_profiles = CompanyProfile.query.filter(
            CompanyProfile.status == 'failed'
        ).count()
        
        # Debug: Let's see all status values
        all_profiles = CompanyProfile.query.all()
        status_counts = {}
        for profile in all_profiles:
            status = profile.status
            status_counts[status] = status_counts.get(status, 0) + 1
        
        print(f"[DASHBOARD DEBUG] Status counts: {status_counts}", flush=True)
        print(f"[DASHBOARD DEBUG] Completed: {completed_profiles}, Failed: {failed_profiles}, Processing: {processing_profiles}", flush=True)
        
        # Calculate percentage changes
        total_change = 0
        if last_month_profiles > 0:
            total_change = round(((this_month_profiles - last_month_profiles) / last_month_profiles) * 100, 1)
        elif this_month_profiles > 0:
            total_change = 100.0
        
        # Calculate success rate
        total_processed = completed_profiles + failed_profiles
        success_rate = 0
        if total_processed > 0:
            success_rate = round((completed_profiles / total_processed) * 100, 1)
        elif completed_profiles > 0:
            # If we have completed profiles but no failed ones, success rate is 100%
            success_rate = 100.0
        
        print(f"[DASHBOARD DEBUG] Total processed: {total_processed}, Success rate: {success_rate}%", flush=True)
        
        # Calculate month-over-month change for total profiles
        # Get profiles from 2 months ago for comparison
        two_months_ago_start = (last_month_start - timedelta(days=1)).replace(day=1)
        two_months_ago_end = last_month_start - timedelta(seconds=1)
        
        two_months_ago_profiles = CompanyProfile.query.filter(
            CompanyProfile.created_at >= two_months_ago_start,
            CompanyProfile.created_at <= two_months_ago_end
        ).count()
        
        total_change_percent = 0
        if two_months_ago_profiles > 0:
            total_change_percent = round(((last_month_profiles - two_months_ago_profiles) / two_months_ago_profiles) * 100, 1)
        elif last_month_profiles > 0:
            total_change_percent = 100.0
        
        result = {
            'total_profiles': total_profiles,
            'this_month': this_month_profiles,
            'processing': processing_profiles,
            'completed': completed_profiles,
            'total_change_percent': total_change_percent,
            'month_change_percent': total_change,
            'success_rate': success_rate
        }
        
        print(f"[DASHBOARD DEBUG] Returning stats: {result}", flush=True)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/profiles', methods=['GET'])
@jwt_required()
def get_profiles():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        search = request.args.get('search', '')
        
        query = CompanyProfile.query
        
        if search:
            query = query.filter(CompanyProfile.company_name.ilike(f'%{search}%'))
        
        # Sort profiles: processing status first, then by created_at DESC (recent to old)
        profiles = query.order_by(
            db.case(
                (CompanyProfile.status == 'processing', 0),
                else_=1
            ),
            CompanyProfile.created_at.desc()
        ).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'profiles': [{
                'id': p.id,
                'company_name': p.company_name,
                'fiscal_years': p.fiscal_years,
                'status': p.status,
                'created_at': p.created_at.isoformat()
            } for p in profiles.items],
            'total': profiles.total,
            'pages': profiles.pages,
            'current_page': page
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/profiles/verify', methods=['POST'])
@jwt_required()
def verify_profile():
    """
    Verify if a profile already exists by analyzing the first page of uploaded documents.
    This endpoint processes all uploaded files to extract company name and fiscal years,
    then checks if a matching profile already exists in the database.
    """
    try:
        from services.profile_verification import verify_profile_before_creation
        
        # Check if files were uploaded
        if 'files' not in request.files:
            return jsonify({'error': 'No files uploaded'}), 400
        
        files = request.files.getlist('files')
        if not files or len(files) == 0:
            return jsonify({'error': 'No files provided'}), 400
        
        # Get optional company name from form data
        company_name = request.form.get('company_name', '').strip()
        if not company_name:
            company_name = None
        
        # Validate all files
        valid_files = []
        for file in files:
            if file.filename == '':
                continue
            valid_files.append(file)
        
        if not valid_files:
            return jsonify({'error': 'No valid files provided'}), 400
        
        print(f"[VERIFICATION] Processing {len(valid_files)} files for verification", flush=True)
        
        # Save all files temporarily for analysis
        import tempfile
        import os
        
        temp_file_paths = []
        try:
            for i, file in enumerate(valid_files):
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                    file.save(temp_file.name)
                    temp_file_paths.append(temp_file.name)
            
            # Get Anthropic API key from config
            api_key = app.config.get('ANTHROPIC_API_KEY')
            if not api_key:
                return jsonify({'error': 'Anthropic API key not configured'}), 500
            
            # Perform verification with all files
            verification_result = verify_profile_before_creation(
                temp_file_paths, 
                api_key, 
                db, 
                CompanyProfile,
                company_name
            )
            
            # Log verification result summary
            if verification_result.get('existing_profile'):
                print(f"[VERIFICATION] Existing profile found: {verification_result['existing_profile']['id']}", flush=True)
            else:
                print(f"[VERIFICATION] No existing profile found", flush=True)
            
            return jsonify(verification_result)
            
        finally:
            # Clean up all temporary files
            for temp_path in temp_file_paths:
                try:
                    os.unlink(temp_path)
                    # print(f"[VERIFICATION] Cleaned up temporary file: {temp_path}", flush=True)
                except:
                    pass
        
    except Exception as e:
        print(f"[VERIFICATION] Error in verify_profile endpoint: {str(e)}", flush=True)
        return jsonify({'error': f'Verification failed: {str(e)}'}), 500

@app.route('/api/profiles', methods=['POST'])
@jwt_required()
def create_profile():
    try:
        data = request.get_json()
        user_id = get_jwt_identity()
        
        email_report = bool(data.get('email_report'))

        # Convert fiscal year to string if provided
        fiscal_year = data.get('fiscal_year')
        if fiscal_year is not None:
            fiscal_year = str(fiscal_year)

        profile = CompanyProfile(
            company_name=data['company_name'],
            fiscal_years=fiscal_year,  # Include fiscal year from frontend
            created_by=user_id,
            profile_data={
                'email_report': email_report
            }
        )
        
        db.session.add(profile)
        db.session.commit()
        
        # If user opted for email delivery, send a confirmation email now.
        # The actual PDF report will be sent when the profile is completed.
        if email_report:
            user = db.session.get(User, user_id)
            if user and user.email:
                send_email(
                    to_email=user.email,
                    subject='Report delivery preference confirmed',
                    body=(
                        'Hello,\n\n'
                        'You selected to receive the company analysis report by email.\n'
                        'We will automatically send you the PDF report as soon as your analysis is complete.\n\n'
                        'Best regards,\nCompany Profile Agent'
                    )
                )

        # Start doc processing directly
        thread = threading.Thread(
            target=process_doc_processing_with_web_sync,
            args=(app, db, CompanyProfile, LiasseDocument, profile.id, None),
            daemon=False
        )
        thread.start()

        return jsonify({
            'id': profile.id,
            'message': 'Profile created successfully'
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/profiles/<profile_id>', methods=['GET'])
@jwt_required()
def get_profile(profile_id):
    """Return full profile details including profile_data to diagnose failures."""
    try:
        profile = CompanyProfile.query.get_or_404(profile_id)
        return jsonify({
            'id': profile.id,
            'company_name': profile.company_name,
            'status': profile.status,
            'profile_data': profile.profile_data or {},
            'created_at': profile.created_at.isoformat(),
            'updated_at': profile.updated_at.isoformat() if profile.updated_at else None
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/profiles/<profile_id>/upload', methods=['POST'])
@jwt_required()
def upload_documents(profile_id):
    try:
        # Check if profile exists
        profile = CompanyProfile.query.get_or_404(profile_id)
        
        # Check file count
        files = request.files.getlist('files')
        if len(files) > 3:
            return jsonify({'error': 'Maximum 3 files allowed'}), 400
        
        # For upload to existing profiles, we'll do a lightweight company name check
        # to avoid duplicate API calls that were already done during verification
        from services.profile_verification import extract_company_info_from_first_page, compare_company_names
        
        api_key = app.config.get('ANTHROPIC_API_KEY')
        document_company_names = []
        temp_file_paths = []
        
        try:
            # Save files temporarily for company name extraction
            import tempfile
            for i, file in enumerate(files):
                if file.filename == '':
                    continue
                    
                # Check file size (16MB limit)
                if file.content_length and file.content_length > app.config['MAX_CONTENT_LENGTH']:
                    return jsonify({'error': f'File {file.filename} exceeds size limit'}), 400
                
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                    file.save(temp_file.name)
                    temp_file_paths.append(temp_file.name)
            
            # Only extract company names if we have multiple files or need verification
            # For single file uploads to existing profiles, skip the expensive extraction
            if len(temp_file_paths) > 1 or app.config.get('ENABLE_UPLOAD_VERIFICATION', False):
                print(f"[UPLOAD] Extracting company info from {len(temp_file_paths)} documents for comparison", flush=True)
                for i, file_path in enumerate(temp_file_paths):
                    company_info = extract_company_info_from_first_page(file_path, api_key)
                    if company_info and company_info.get('company_name'):
                        document_company_names.append(company_info['company_name'])
                        print(f"[UPLOAD] Document {i+1} company: {company_info['company_name']}", flush=True)
                    else:
                        print(f"[UPLOAD] Failed to extract company name from document {i+1}", flush=True)
                
                # Compare company names
                if document_company_names:
                    comparison_result = compare_company_names(profile.company_name, document_company_names)
                    
                    # If confirmation is required, return early with comparison details
                    if comparison_result['requires_confirmation']:
                        return jsonify({
                            'requires_confirmation': True,
                            'comparison_result': comparison_result,
                            'message': 'Company name mismatch detected - requires user confirmation',
                            'profile_company': profile.company_name,
                            'document_companies': document_company_names
                        }), 200
                else:
                    print(f"[UPLOAD] No company names extracted from documents, proceeding with upload", flush=True)
            else:
                print(f"[UPLOAD] Skipping company name extraction for single file upload to existing profile", flush=True)
            
            # If we reach here, company names match or comparison failed - proceed with upload
            uploaded_files = []
            
            for i, file in enumerate(files):
                if file.filename == '':
                    continue
                    
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{profile_id}_{filename}")
                
                # Copy from temp file to final location
                import shutil
                shutil.copy2(temp_file_paths[i], file_path)
                
                # Save document record
                document = LiasseDocument(
                    profile_id=profile_id,
                    file_name=filename,
                    file_path=file_path,
                    file_size=os.path.getsize(file_path)
                )
                
                db.session.add(document)
                uploaded_files.append({
                    'id': document.id,
                    'filename': filename,
                    'size': document.file_size
                })
            
            db.session.commit()
            
            return jsonify({
                'message': 'Files uploaded successfully',
                'files': uploaded_files,
                'requires_confirmation': False,
                'company_names_match': True
            })
            
        finally:
            # Clean up temporary files
            for temp_path in temp_file_paths:
                try:
                    os.unlink(temp_path)
                    print(f"[UPLOAD] Cleaned up temporary file: {temp_path}", flush=True)
                except:
                    pass
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/profiles/<profile_id>/smart-upload', methods=['POST'])
@jwt_required()
def smart_upload_documents(profile_id):
    """
    Smart document upload that only processes new documents and reuses existing document data.
    """
    try:
        from services.profile_verification import identify_new_vs_existing_documents
        
        # Check if profile exists
        profile = CompanyProfile.query.get_or_404(profile_id)
        
        # Check file count
        files = request.files.getlist('files')
        if len(files) > 3:
            return jsonify({'error': 'Maximum 3 files allowed'}), 400
        
        # Save files temporarily for analysis
        import tempfile
        temp_file_paths = []
        try:
            for i, file in enumerate(files):
                if file.filename == '':
                    continue
                    
                # Check file size (16MB limit)
                if file.content_length and file.content_length > app.config['MAX_CONTENT_LENGTH']:
                    return jsonify({'error': f'File {file.filename} exceeds size limit'}), 400
                
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                    file.save(temp_file.name)
                    temp_file_paths.append(temp_file.name)
                    
            
            # Identify which documents are new vs existing
            # We need to extract company info first to pass to the function
            from services.profile_verification import extract_company_info_from_first_page
            
            # Extract company info from all documents to get the all_company_info parameter
            all_company_info = []
            api_key = app.config.get('ANTHROPIC_API_KEY')
            
            # Only extract company info if we have multiple files or if verification is explicitly enabled
            # For single file uploads after verification, we can skip the expensive extraction
            if len(temp_file_paths) > 1 or app.config.get('ENABLE_SMART_UPLOAD_VERIFICATION', False):
                print(f"[SMART_UPLOAD] Extracting company info from {len(temp_file_paths)} documents for analysis", flush=True)
                for i, file_path in enumerate(temp_file_paths):
                    company_info = extract_company_info_from_first_page(file_path, api_key)
                    if company_info:
                        all_company_info.append(company_info)
                        print(f"[SMART_UPLOAD] Document {i+1} extracted: {company_info}", flush=True)
                    else:
                        print(f"[SMART_UPLOAD] Failed to extract info from document {i+1}", flush=True)
            else:
                print(f"[SMART_UPLOAD] Skipping company info extraction for single file upload after verification", flush=True)
                # Create minimal company info for single file uploads
                for i, file_path in enumerate(temp_file_paths):
                    all_company_info.append({
                        'company_name': profile.company_name,  # Use profile company name
                        'fiscal_year': None  # Will be determined during processing
                    })
            
            # Now call the function with all required parameters
            document_analysis = identify_new_vs_existing_documents(
                db, CompanyProfile, temp_file_paths, profile.company_name, all_company_info
            )
            
            print(f"[SMART_UPLOAD] Document analysis: {document_analysis['total_new']} new, {document_analysis['total_existing']} existing", flush=True)
            
            # Check for company name mismatches
            from services.profile_verification import compare_company_names
            
            document_company_names = [info.get('company_name') for info in all_company_info if info.get('company_name')]
            if document_company_names:
                comparison_result = compare_company_names(profile.company_name, document_company_names)
                # print(f"[SMART_UPLOAD] Company name comparison result: {comparison_result}", flush=True)
                
                # If confirmation is required, return early with comparison details
                if comparison_result['requires_confirmation']:
                    return jsonify({
                        'requires_confirmation': True,
                        'comparison_result': comparison_result,
                        'message': 'Company name mismatch detected - requires user confirmation',
                        'profile_company': profile.company_name,
                        'document_companies': document_company_names,
                        'document_analysis': document_analysis
                    }), 200
            else:
                print(f"[SMART_UPLOAD] No company names extracted from documents, proceeding with upload", flush=True)
            
            uploaded_files = []
            processed_count = 0
            
            # Handle existing documents - reuse saved data
            for match in document_analysis['existing_matches']:
                print(f"[SMART_UPLOAD] Reusing existing document data for: {os.path.basename(match['file_path'])}", flush=True)
                
                # Save document record with existing data
                filename = os.path.basename(match['file_path'])
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{profile_id}_{filename}")
                
                # Copy the file to the new profile's directory
                import shutil
                shutil.copy2(match['file_path'], file_path)
                
                document = LiasseDocument(
                    profile_id=profile_id,
                    file_name=filename,
                    file_path=file_path,
                    file_size=os.path.getsize(file_path),
                    extracted_data=match['existing_data'].get('extracted_data'),
                    upload_status='reused',
                    ocr_status='completed'  # Mark as completed since we're reusing data
                )
                
                db.session.add(document)
                uploaded_files.append({
                    'id': document.id,
                    'filename': filename,
                    'size': document.file_size,
                    'status': 'reused',
                    'message': 'Document data reused from existing profile'
                })
            
            # Handle new documents - process normally
            for new_doc in document_analysis['new_documents']:
                # print(f"[SMART_UPLOAD] Processing new document: {os.path.basename(new_doc['file_path'])}", flush=True)
                
                filename = os.path.basename(new_doc['file_path'])
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{profile_id}_{filename}")
                
                # Copy the file to the new profile's directory
                import shutil
                shutil.copy2(new_doc['file_path'], file_path)
                
                # Save document record for new document
                document = LiasseDocument(
                    profile_id=profile_id,
                    file_name=filename,
                    file_path=file_path,
                    file_size=os.path.getsize(file_path),
                    upload_status='uploaded',
                    ocr_status='pending'  # Will be processed by the document processing pipeline
                )
                
                db.session.add(document)
                uploaded_files.append({
                    'id': document.id,
                    'filename': filename,
                    'size': document.file_size,
                    'status': 'new',
                    'message': 'Document will be processed'
                })
                processed_count += 1
            
            # Ensure all documents have the correct status for processing pipeline
            # print(f"[SMART_UPLOAD] Setting up documents for processing pipeline", flush=True)
            for doc in uploaded_files:
                if doc['status'] == 'new':
                    print(f"[SMART_UPLOAD] Document {doc['filename']} marked for processing (upload_status: uploaded, ocr_status: pending)", flush=True)
                elif doc['status'] == 'reused':
                    print(f"[SMART_UPLOAD] Document {doc['filename']} marked as reused (upload_status: reused, ocr_status: completed)", flush=True)
            
            # print(f"[SMART_UPLOAD] About to commit {len(uploaded_files)} documents to database", flush=True)
            db.session.commit()
            # print(f"[SMART_UPLOAD] Database commit completed successfully", flush=True)
            
            # Double-check that documents are actually in the database
            try:
                final_check = db.session.execute(
                    text("SELECT COUNT(*) as doc_count FROM liasse_documents WHERE profile_id = :profile_id"),
                    {"profile_id": profile_id}
                ).scalar()
                # print(f"[SMART_UPLOAD] Final database check: {final_check} documents found for profile {profile_id}", flush=True)
                
                if final_check != len(uploaded_files):
                    print(f"[SMART_UPLOAD] ⚠️ WARNING: Expected {len(uploaded_files)} documents but found {final_check} in database", flush=True)
                else:
                    print(f"[SMART_UPLOAD] ✅ SUCCESS: All {final_check} documents properly saved to database", flush=True)
                    
            except Exception as e:
                print(f"[SMART_UPLOAD] Error in final database check: {e}", flush=True)
            
            # Add a small delay to ensure database commit is fully processed
            import time
            time.sleep(1)
            # print(f"[SMART_UPLOAD] Added 1 second delay to ensure database synchronization", flush=True)
            
            return jsonify({
                'message': 'Smart upload completed successfully',
                'uploaded_files': uploaded_files,
                'document_analysis': document_analysis,
                'new_documents_to_process': processed_count
            })
            
        finally:
            # Clean up temporary files
            for temp_path in temp_file_paths:
                try:
                    os.unlink(temp_path)
                    print(f"[SMART_UPLOAD] Cleaned up temporary file: {temp_path}", flush=True)
                except:
                    pass
        
    except Exception as e:
        db.session.rollback()
        print(f"[SMART_UPLOAD] Error in smart upload: {str(e)}", flush=True)
        return jsonify({'error': f'Smart upload failed: {str(e)}'}), 500

@app.route('/api/profiles/<profile_id>', methods=['DELETE'])
@jwt_required()
def delete_profile(profile_id):
    """Delete a profile and all associated documents"""
    try:
        profile = CompanyProfile.query.get_or_404(profile_id)
        
        # Get the current user to check permissions
        user_id = get_jwt_identity()
        
        # Check if user is admin or the profile creator
        user = db.session.get(User, user_id)
        if user.role != 'admin' and profile.created_by != user_id:
            return jsonify({'error': 'Unauthorized to delete this profile'}), 403
        
        # Delete associated documents from filesystem (including markdown files)
        from services.doc_processing import cleanup_profile_files
        cleanup_profile_files(profile_id, app.config['UPLOAD_FOLDER'], db, LiasseDocument)
        
        # Delete the profile (CASCADE will delete associated documents from DB)
        db.session.delete(profile)
        db.session.commit()
        
        return jsonify({'message': 'Profile deleted successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/profiles/<profile_id>/complete', methods=['POST'])
@jwt_required()
def mark_profile_complete(profile_id):
    """Mark a profile as completed and optionally email the user a report link.

    Request JSON body (all optional):
      - report_url: string URL where the report can be downloaded/viewed
      - message: additional text to include in the email body
    """
    try:
        profile = CompanyProfile.query.get_or_404(profile_id)

        # Only the creator or admins should be able to mark complete in a real app.
        # For now, require authentication and proceed.
        data = request.get_json(silent=True) or {}
        report_url = data.get('report_url')
        extra_message = data.get('message')

        # Update status and persist report_url into profile_data if provided
        profile.status = 'completed'
        current_data = profile.profile_data or {}
        if report_url:
            current_data['report_url'] = report_url
        profile.profile_data = current_data
        db.session.commit()

        # Email user if they opted in - send PDF report automatically
        email_report = bool((profile.profile_data or {}).get('email_report'))
        if email_report:
            # Send PDF report via email in a separate thread to avoid blocking
            import threading
            email_thread = threading.Thread(
                target=send_pdf_report_email,
                args=(profile_id,),
                daemon=True
            )
            email_thread.start()
            print(f"🚀 Started email thread for profile {profile_id}", flush=True)

        return jsonify({'message': 'Profile marked as completed'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/profiles/<profile_id>/reprocess', methods=['POST'])
@jwt_required()
def reprocess_profile(profile_id):
    """Re-trigger background document processing for a profile."""
    try:
        profile = CompanyProfile.query.get_or_404(profile_id)
        # Reset status to processing
        profile.status = 'processing'
        db.session.commit()

        # Start doc processing directly
        thread = threading.Thread(
            target=process_doc_processing_with_web_sync,
            args=(app, db, CompanyProfile, LiasseDocument, profile_id, None),
            daemon=False
        )
        thread.start()
        print(f"Started reprocessing thread for profile {profile_id}", flush=True)

        return jsonify({'message': 'Reprocessing started'}), 202
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/profiles/<profile_id>/reprocess-tva', methods=['POST'])
@jwt_required()
def reprocess_profile_tva(profile_id):
    """Force TVA extraction for an existing profile by clearing cached TVA data."""
    try:
        profile = CompanyProfile.query.get_or_404(profile_id)
        
        print(f"[TVA REPROCESS] Starting TVA reprocessing for profile {profile_id}", flush=True)
        
        # Clear TVA data from all documents to force re-extraction
        documents = LiasseDocument.query.filter_by(profile_id=profile_id).all()
        for document in documents:
            if document.extracted_data and isinstance(document.extracted_data, dict):
                # Remove TVA data if it exists
                if 'tva_data' in document.extracted_data:
                    del document.extracted_data['tva_data']
                    print(f"[TVA REPROCESS] Cleared TVA data from document {document.file_name}", flush=True)
                
                # Mark the document as needing TVA extraction
                document.extracted_data['needs_tva_extraction'] = True
                db.session.add(document)
        
        # Clear TVA analysis from profile data
        profile_data = profile.profile_data or {}
        if 'tva_analysis' in profile_data:
            del profile_data['tva_analysis']
            profile.profile_data = profile_data
            print(f"[TVA REPROCESS] Cleared TVA analysis from profile data", flush=True)
        
        db.session.commit()
        
        # Reset status to processing
        profile.status = 'processing'
        db.session.commit()
        
        # Start document processing directly (skip news and web since they're already done)
        from services.doc_processing import process_doc_processing
        thread = threading.Thread(
            target=process_doc_processing,
            args=(app, db, CompanyProfile, LiasseDocument, profile_id),
            daemon=False
        )
        thread.start()
        print(f"Started TVA reprocessing thread for profile {profile_id}", flush=True)

        return jsonify({'message': 'TVA reprocessing started - documents will be re-analyzed for TVA data'}), 202
        
    except Exception as e:
        db.session.rollback()
        print(f"[TVA REPROCESS] Error: {e}", flush=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/profiles/<profile_id>/report', methods=['GET'])
def get_profile_report(profile_id):
    """Serve the generated HTML report for a completed profile"""
    try:
        # TODO: Re-enable authentication after testing
        # For now, let's test without auth to see if the report generation works
        profile = CompanyProfile.query.get_or_404(profile_id)
        
        if profile.status != 'completed':
            return jsonify({'error': 'Profile is not completed yet'}), 400
            
        profile_data = profile.profile_data or {}
        extracted_kpis = profile_data.get('extracted_kpis')
        computed_ratios = profile_data.get('computed_ratios')
        web_data = profile_data.get('web_data', {})
        company_name = profile_data.get('company_name') or profile.company_name
        
        # Debug: Log the profile data structure (commented out for production)
        # print(f"🔍 DEBUG: Profile data keys: {list(profile_data.keys()) if profile_data else 'None'}", flush=True)
        # print(f"🔍 DEBUG: extracted_kpis type: {type(extracted_kpis)}, keys: {list(extracted_kpis.keys()) if extracted_kpis else 'None'}", flush=True)
        # print(f"🔍 DEBUG: computed_ratios type: {type(computed_ratios)}, keys: {list(computed_ratios.keys()) if computed_ratios else 'None'}", flush=True)
        # print(f"🔍 DEBUG: web_data keys: {list(web_data.keys()) if web_data else 'None'}", flush=True)
        # if web_data:
        #     print(f"🔍 DEBUG: recommendation length: {len(web_data.get('recommendation', ''))}", flush=True)
        #     print(f"🔍 DEBUG: detailed_analysis length: {len(web_data.get('detailed_analysis', ''))}", flush=True)
        
        if not extracted_kpis and not computed_ratios:
            print(f"❌ ERROR: No financial data found in profile {profile_id}", flush=True)
            print(f"❌ Profile status: {profile.status}", flush=True)
            print(f"❌ Profile data keys: {list(profile_data.keys()) if profile_data else 'None'}", flush=True)
            
            # Provide fallback test data for debugging
            print(f"🔄 Providing fallback test data for debugging...", flush=True)
            extracted_kpis = {
                'Chiffre d\'affaires': {'N': 1000000, 'N-1': 900000},
                'Résultat Net': {'N': 100000, 'N-1': 80000},
                'Capitaux propres': {'N': 500000, 'N-1': 450000},
                'Dettes de financement': {'N': 200000, 'N-1': 180000},
                'Trésorerie-Actif': {'N': 50000, 'N-1': 40000}
            }
            computed_ratios = {
                'marge_nette_n': 10.0,
                'marge_exploitation_n': 15.0,
                'roe_n': 20.0,
                'roce_n': 25.0,
                'gearing_n': 30.0,
                'marge_ebitda_n': 18.0
            }
            print(f"✅ Fallback data created: {len(extracted_kpis)} KPIs, {len(computed_ratios)} ratios", flush=True)
        
        # Read the report template - now that frontend is mounted at /app/frontend
        template_path = os.path.join('frontend', 'src', 'report_template', 'report.html')
        if not os.path.exists(template_path):
            return jsonify({'error': 'Report template not found'}), 500
            
        with open(template_path, 'r', encoding='utf-8') as f:
            template_content = f.read()
            
        # Read main.js content
        main_js_path = os.path.join('frontend', 'src', 'js', 'main.js')
        if os.path.exists(main_js_path):
            with open(main_js_path, 'r', encoding='utf-8') as f:
                main_js_content = f.read()
        else:
            main_js_content = "console.error('main.js not found');"
            
        # Read style.css content
        style_css_path = os.path.join('frontend', 'src', 'css', 'style.css')
        if os.path.exists(style_css_path):
            with open(style_css_path, 'r', encoding='utf-8') as f:
                style_css_content = f.read()
        else:
            style_css_content = "/* style.css not found */"
            
        # Create the data structure for the template
        basic_info = web_data.get('basic_info', {})
        company_overview = basic_info.get('companyOverview', {})
        
        # Get analysis sections from profile data (generated by financial_reporting.py)
        profile_data = profile.profile_data or {}
        
        template_data = {
            'company_name': company_name,
            'extracted_kpis': extracted_kpis or {},
            'computed_ratios': computed_ratios or {},
            'fiscal_years': profile.fiscal_years,  # Add fiscal years information
            # Company overview data from web exploring
            'companyOverview': {
                'companyFoundationyear': company_overview.get('companyFoundationyear', 'Non spécifié'),
                'companyExpertise': company_overview.get('companyExpertise', 'À déterminer'),
                'primary_sector': company_overview.get('primary_sector', 'Secteur général'),
                'legal_form': company_overview.get('legal_form', 'SARL'),
                'companyDefinition': company_overview.get('companyDefinition', f'Entreprise {company_name}'),
                'staff_count': company_overview.get('staff_count', 'À préciser')
            },
            # Sectors and markets - handle null values safely
            'sectors': basic_info.get('sectors') if basic_info.get('sectors') is not None else [],
            'markets': basic_info.get('markets') if basic_info.get('markets') is not None else [],
            'keyPeople': basic_info.get('keyPeople') if basic_info.get('keyPeople') is not None else [],
            # Contact information
            'contact': basic_info.get('contact', {
                'phone': 'Non disponible',
                'email': 'Non disponible',
                'address': 'Adresse à préciser',
                'website': 'Non disponible'
            }),
            # Analysis sections from financial_reporting.py
            'recommendation': profile_data.get('recommendation', 'Recommandation à définir'),
            'news': profile_data.get('news_data', {}).get('analysis', 'Actualités sectorielles à rechercher') if profile_data.get('news_data') else 'Actualités sectorielles à rechercher',
            'news_urls': profile_data.get('news_data', {}).get('urls', []) if profile_data.get('news_data') else [],
            'news_articles': profile_data.get('news_data', {}).get('urls', []) if profile_data.get('news_data') else [],
            'detailed_analysis': profile_data.get('detailed_analysis', 'Analyse détaillée à compléter'),
            # SWOT analysis data from financial_reporting.py
            'swot_analysis': profile_data.get('swot_analysis', {
                'strengths': [],
                'weaknesses': [],
                'opportunities': [],
                'threats': []
            })
        }
        
        # Debug: Log the data being passed to the template
        # print(f"🔍 DEBUG: Template data structure:")
        # print(f"🔍 - company_name: {template_data['company_name']}")
        # print(f"🔍 - extracted_kpis keys: {list(template_data['extracted_kpis'].keys())}")
        # print(f"🔍 - computed_ratios keys: {list(template_data['computed_ratios'].keys())}")
        # print(f"🔍 - extracted_kpis sample: {dict(list(template_data['extracted_kpis'].items())[:3]) if template_data['extracted_kpis'] else 'Empty'}")
        # print(f"🔍 - computed_ratios sample: {dict(list(template_data['computed_ratios'].items())[:3]) if template_data['computed_ratios'] else 'Empty'}")
        
        # Additional debugging for data structure
        if template_data['extracted_kpis']:
            # print(f"🔍 DEBUG: First KPI structure:")
            first_kpi_key = list(template_data['extracted_kpis'].keys())[0]
            first_kpi_value = template_data['extracted_kpis'][first_kpi_key]
            # print(f"🔍 - Key: {first_kpi_key}")
            # print(f"🔍 - Value type: {type(first_kpi_value)}")
            # print(f"🔍 - Value: {first_kpi_value}")
        
        if template_data['computed_ratios']:
            # print(f"🔍 DEBUG: First ratio structure:")
            first_ratio_key = list(template_data['computed_ratios'].keys())[0]
            first_ratio_value = template_data['computed_ratios'][first_ratio_key]
            # print(f"🔍 - Key: {first_ratio_key}")
            # print(f"🔍 - Value type: {type(first_ratio_value)}")
            # print(f"🔍 - Value: {first_ratio_value}")
        
        # Inject the data and main.js directly into the HTML
        template_data_json = json.dumps(template_data, ensure_ascii=False, indent=2)
        
        # Replace template placeholders
        html_content = template_content.replace(
            '<script id="report-data" type="application/json">\n  {{ reportData | tojson }}\n</script>',
            f'<script id="report-data" type="application/json">\n{template_data_json}\n</script>'
        )
        
        html_content = html_content.replace(
            '<script src="{{ url_for(\'static\', filename=\'js/main.js\') }}"></script>',
            f'<script>\n{main_js_content}\n</script>'
        )
        
        # Replace CSS link with actual CSS content
        html_content = html_content.replace(
            '<link rel="stylesheet" href="{{ url_for(\'static\', filename=\'css/style.css\') }}">',
            f'<style>\n{style_css_content}\n</style>'
        )
        
        # Generate sectors HTML
        sectors_html = ""
        sectors = basic_info.get('sectors')
        if sectors and isinstance(sectors, list):
            for sector in sectors:
                if sector and isinstance(sector, dict):
                    sectors_html += f'''
                    <div class="info-card">
                        <div class="icon"><i class="fas fa-signal"></i></div>
                        <h4>{sector.get('title', 'Secteur')}</h4>
                        <p>{sector.get('description', 'Description non disponible')}</p>
                    </div>'''
        
        # Generate markets HTML
        markets_html = ""
        markets = basic_info.get('markets')
        if markets and isinstance(markets, list):
            for market in markets:
                if market and isinstance(market, dict):
                    markets_html += f'''
                    <div class="info-card">
                        <div class="icon"><i class="fas fa-landmark"></i></div>
                        <h4>{market.get('title', 'Marché')}</h4>
                        <p>{market.get('description', 'Description non disponible')}</p>
                    </div>'''
        
        # Helper function to safely get string values (handle None values)
        def safe_get(value, default=''):
            return str(value) if value is not None else default
        
        # Generate key people HTML for standalone section
        key_people_html = ""
        key_people = basic_info.get('keyPeople')
        if key_people and isinstance(key_people, list):
            for person in key_people:
                if person and isinstance(person, dict):
                    # Skip people with all None values
                    if not any([person.get('name'), person.get('position'), person.get('initials')]):
                        continue
                    key_people_html += f'''
                    <div class="person-item">
                        <div class="person-avatar">{safe_get(person.get('initials'), 'N/A')}</div>
                        <div class="person-info">
                            <h4>{safe_get(person.get('name'), 'Nom non disponible')}</h4>
                            <p>{safe_get(person.get('position'), 'Poste non spécifié')}</p>
                        </div>
                    </div>'''
        
        # Generate compact key people HTML for header-overview section
        key_people_compact_html = ""
        key_people_list = basic_info.get('keyPeople')
        if key_people_list and isinstance(key_people_list, list):
            for i, person in enumerate(key_people_list):
                if person and isinstance(person, dict):
                    # Skip people with all None values
                    if not any([person.get('name'), person.get('position')]):
                        continue
                    
                    # Start new line every 2 people
                    if i % 2 == 0:
                        if i > 0:  # Close previous line
                            key_people_compact_html += '</div>'
                        key_people_compact_html += '<div class="key-people-row">'
                    
                    key_people_compact_html += f'<span class="key-person-item">• {safe_get(person.get("name"), "Nom non disponible")}</span>'
        
        # Close the last row if there are any people
        if key_people_list:
            key_people_compact_html += '</div>'
        
        # Replace all Jinja2 template variables with actual data
        html_content = html_content.replace('{{ reportData.companyName }}', company_name)
        html_content = html_content.replace('{{ reportData.companyOverview.companyExpertise }}', safe_get(company_overview.get('companyExpertise'), 'À déterminer'))
        html_content = html_content.replace('{{ reportData.companyOverview.companyDefinition }}', safe_get(company_overview.get('companyDefinition'), f'Entreprise {company_name}'))
        html_content = html_content.replace('{{ reportData.companyOverview.primary_sector }}', safe_get(company_overview.get('primary_sector'), 'Secteur général'))
        html_content = html_content.replace('{{ reportData.companyOverview.legal_form }}', safe_get(company_overview.get('legal_form'), 'SARL'))
        html_content = html_content.replace('{{ reportData.companyOverview.companyFoundationyear }}', safe_get(company_overview.get('companyFoundationyear'), 'Non spécifié'))
        html_content = html_content.replace('{{ reportData.companyOverview.staff_count }}', safe_get(company_overview.get('staff_count'), 'À préciser'))
        html_content = html_content.replace('{{ reportData.contact.address }}', safe_get(basic_info.get('contact', {}).get('address'), 'Adresse à préciser'))
        html_content = html_content.replace('{{ reportData.contact.phone }}', safe_get(basic_info.get('contact', {}).get('phone'), 'Non disponible'))
        html_content = html_content.replace('{{ reportData.contact.email }}', safe_get(basic_info.get('contact', {}).get('email'), 'Non disponible'))
        html_content = html_content.replace('{{ reportData.contact.website }}', safe_get(basic_info.get('contact', {}).get('website'), 'Non disponible'))
        
        # Generate news content with links
        def generate_news_html(news_text, news_articles):
            import html
            news_html = f'<p>{html.escape(news_text) if news_text else "Actualités sectorielles à rechercher"}</p>'
            
            return news_html

        # Debug: Log the textual data before replacement
        # Get analysis data from profile_data (financial_reporting.py) instead of web_data
        recommendation_text = profile_data.get('recommendation', 'Recommandation à définir')
        news_data = profile_data.get('news_data', {})
        news_text = news_data.get('analysis', 'Actualités sectorielles à rechercher') if news_data else 'Actualités sectorielles à rechercher'
        news_articles = news_data.get('urls', []) if news_data else []
        detailed_analysis_text = profile_data.get('detailed_analysis', 'Analyse détaillée à compléter')
        
        # print(f"🔍 DEBUG: About to replace recommendation: {len(recommendation_text)} chars", flush=True)
        # print(f"🔍 DEBUG: About to replace news: {len(news_text)} chars with {len(news_articles)} articles", flush=True)
        # print(f"🔍 DEBUG: About to replace detailed_analysis: {len(detailed_analysis_text)} chars", flush=True)
        
        # Ensure proper encoding and escape HTML characters
        import html
        recommendation_text_safe = html.escape(recommendation_text) if recommendation_text else 'Recommandation à définir'
        news_html_content = generate_news_html(news_text, news_articles)
        detailed_analysis_text_safe = html.escape(detailed_analysis_text) if detailed_analysis_text else 'Analyse détaillée à compléter'
        
        html_content = html_content.replace('{{ reportData.recommendation }}', recommendation_text_safe)
        html_content = html_content.replace('{{ reportData.news }}', news_html_content)
        html_content = html_content.replace('{{ reportData.detailed_analysis }}', detailed_analysis_text_safe)
        
        # Replace loop sections
        html_content = html_content.replace('{% for sector in reportData.sectors %}\n            <div class="info-card">\n                <div class="icon"><i class="fas fa-signal"></i></div>\n                <h4>{{ sector.title }}</h4>\n                <p>{{ sector.description }}</p>\n            </div>\n            {% endfor %}', sectors_html)
        html_content = html_content.replace('{% for market in reportData.markets %}\n          <div class="info-card">\n            <div class="icon"><i class="fas fa-landmark"></i></div>\n            <h4>{{ market.title }}</h4>\n            <p>{{ market.description }}</p>\n          </div>\n          {% endfor %}', markets_html)
        html_content = html_content.replace('{% for person in reportData.keyPeople %}\n          <div class="person-item">\n            <div class="person-avatar">{{ person.initials }}</div>\n            <div class="person-info">\n              <h4>{{ person.name }}</h4>\n              <p>{{ person.position }}</p>\n            </div>\n          </div>\n          {% endfor %}', key_people_html)
        
        # Replace header-overview keyPeople loop section
        html_content = html_content.replace('<!-- Fourth row: Dirigeants (compact) -->\n          <div class="overview-row">\n            <div class="overview-bullet-item full-width">\n              <i class="fas fa-users" style="color: white; margin-right: 8px;"></i>\n              <span><strong>Dirigeants:</strong></span>\n              <div class="key-people-compact">\n                {% for person in reportData.keyPeople %}\n                <span class="key-person-compact">\n                  <span class="key-person-compact-avatar">{{ person.initials }}</span>\n                  {{ person.name }} ({{ person.position }})\n                </span>\n                {% if not loop.last %}<span class="separator"> • </span>{% endif %}\n                {% endfor %}\n              </div>\n            </div>\n          </div>', f'''<!-- Fourth row: Dirigeants (compact) -->
          <div class="overview-row">
            <div class="overview-bullet-item full-width">
              <i class="fas fa-users" style="color: white; margin-right: 8px;"></i>
              <span><strong>Dirigeants:</strong></span>
              <div class="key-people-compact">
                {key_people_compact_html}
              </div>
            </div>
          </div>''')
        
        # Replace company name placeholders
        html_content = html_content.replace('{{ company_name }}', company_name)
        html_content = html_content.replace('{{ companyName }}', company_name)
        
        # Remove any remaining template variables that should be handled by JavaScript
        html_content = html_content.replace('{{ reportData.financialData.metrics.gearing }}', '')
        
        # Remove remaining Jinja2 syntax - the JavaScript will handle data population
        import re
        html_content = re.sub(r'\{\%.*?\%\}', '', html_content, flags=re.DOTALL)
        key_people = basic_info.get('keyPeople') or []
        html_content = html_content.replace('{{ reportData.keyPeople|length }}', str(len(key_people)))
        html_content = re.sub(r'\{\{.*?\}\}', '', html_content)
        
        return html_content, 200, {'Content-Type': 'text/html; charset=utf-8'}
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/profiles/<profile_id>/pdf', methods=['GET'])
@jwt_required()
def get_profile_pdf(profile_id):
    """Generate and serve a PDF version of the profile report"""
    try:
        profile = CompanyProfile.query.get_or_404(profile_id)
        
        if profile.status != 'completed':
            return jsonify({'error': 'Profile is not completed yet'}), 400
            
        # Get the HTML content from the existing report endpoint logic
        # We'll reuse the same logic but generate PDF instead of returning HTML
        profile_data = profile.profile_data or {}
        extracted_kpis = profile_data.get('extracted_kpis')
        computed_ratios = profile_data.get('computed_ratios')
        web_data = profile_data.get('web_data', {})
        company_name = profile_data.get('company_name') or profile.company_name
        
        if not extracted_kpis and not computed_ratios:
            return jsonify({'error': 'Financial data not available'}), 404
            
        # Read the report template
        template_path = os.path.join('frontend', 'src', 'report_template', 'report.html')
        if not os.path.exists(template_path):
            return jsonify({'error': 'Report template not found'}), 500
            
        with open(template_path, 'r', encoding='utf-8') as f:
            template_content = f.read()
            
        # Read main.js content
        main_js_path = os.path.join('frontend', 'src', 'js', 'main.js')
        if os.path.exists(main_js_path):
            with open(main_js_path, 'r', encoding='utf-8') as f:
                main_js_content = f.read()
        else:
            main_js_content = "console.error('main.js not found');"
            
        # Read style.css content
        style_css_path = os.path.join('frontend', 'src', 'css', 'style.css')
        if os.path.exists(style_css_path):
            with open(style_css_path, 'r', encoding='utf-8') as f:
                style_css_content = f.read()
        else:
            style_css_content = "/* style.css not found */"
            
        # Create the data structure for the template
        basic_info = web_data.get('basic_info', {})
        company_overview = basic_info.get('companyOverview', {})
        
        # Get analysis sections from profile data (generated by financial_reporting.py)
        profile_data = profile.profile_data or {}
        
        template_data = {
            'company_name': company_name,
            'extracted_kpis': extracted_kpis or {},
            'computed_ratios': computed_ratios or {},
            'fiscal_years': profile.fiscal_years,  # Add fiscal years information
            # Company overview data from web exploring
            'companyOverview': {
                'companyFoundationyear': company_overview.get('companyFoundationyear', 'Non spécifié'),
                'companyExpertise': company_overview.get('companyExpertise', 'À déterminer'),
                'primary_sector': company_overview.get('primary_sector', 'Secteur général'),
                'legal_form': company_overview.get('legal_form', 'SARL'),
                'companyDefinition': company_overview.get('companyDefinition', f'Entreprise {company_name}'),
                'staff_count': company_overview.get('staff_count', 'À préciser')
            },
            # Sectors and markets - handle null values safely
            'sectors': basic_info.get('sectors') if basic_info.get('sectors') is not None else [],
            'markets': basic_info.get('markets') if basic_info.get('markets') is not None else [],
            'keyPeople': basic_info.get('keyPeople') if basic_info.get('keyPeople') is not None else [],
            # Contact information
            'contact': basic_info.get('contact', {
                'phone': 'Non disponible',
                'email': 'Non disponible',
                'address': 'Adresse à préciser',
                'website': 'Non disponible'
            }),
            # Analysis sections from financial_reporting.py
            'recommendation': profile_data.get('recommendation', 'Recommandation à définir'),
            'news': profile_data.get('news_data', {}).get('analysis', 'Actualités sectorielles à rechercher') if profile_data.get('news_data') else 'Actualités sectorielles à rechercher',
            'news_urls': profile_data.get('news_data', {}).get('urls', []) if profile_data.get('news_data') else [],
            'news_articles': profile_data.get('news_data', {}).get('urls', []) if profile_data.get('news_data') else [],
            'detailedAnalysis': profile_data.get('detailed_analysis', 'Analyse détaillée à compléter'),
            # SWOT analysis data from financial_reporting.py
            'swot_analysis': profile_data.get('swot_analysis', {
                'strengths': [],
                'weaknesses': [],
                'opportunities': [],
                'threats': []
            })
        }
        
        # Debug: Log the data being passed to the template
        # print(f"🔍 DEBUG: Template data structure:")
        # print(f"🔍 - company_name: {template_data['company_name']}")
        # print(f"🔍 - extracted_kpis keys: {list(template_data['extracted_kpis'].keys())}")
        # print(f"🔍 - computed_ratios keys: {list(template_data['computed_ratios'].keys())}")
        # print(f"🔍 - extracted_kpis sample: {dict(list(template_data['extracted_kpis'].items())[:3]) if template_data['extracted_kpis'] else 'Empty'}")
        # print(f"🔍 - computed_ratios sample: {dict(list(template_data['computed_ratios'].items())[:3]) if template_data['computed_ratios'] else 'Empty'}")
        
        # Additional debugging for data structure
        if template_data['extracted_kpis']:
            # print(f"🔍 DEBUG: First KPI structure:")
            first_kpi_key = list(template_data['extracted_kpis'].keys())[0]
            first_kpi_value = template_data['extracted_kpis'][first_kpi_key]
            # print(f"🔍 - Key: {first_kpi_key}")
            # print(f"🔍 - Value type: {type(first_kpi_value)}")
            # print(f"🔍 - Value: {first_kpi_value}")
        
        if template_data['computed_ratios']:
            # print(f"🔍 DEBUG: First ratio structure:")
            first_ratio_key = list(template_data['computed_ratios'].keys())[0]
            first_ratio_value = template_data['computed_ratios'][first_ratio_key]
            # print(f"🔍 - Key: {first_ratio_key}")
            # print(f"🔍 - Value type: {type(first_ratio_value)}")
            # print(f"🔍 - Value: {first_ratio_value}")
        
        # Inject the data and main.js directly into the HTML
        template_data_json = json.dumps(template_data, ensure_ascii=False, indent=2)
        
        # Replace template placeholders
        html_content = template_content.replace(
            '<script id="report-data" type="application/json">\n  {{ reportData | tojson }}\n</script>',
            f'<script id="report-data" type="application/json">\n{template_data_json}\n</script>'
        )
        
        html_content = html_content.replace(
            '<script src="{{ url_for(\'static\', filename=\'js/main.js\') }}"></script>',
            f'<script>\n{main_js_content}\n</script>'
        )
        
        # Replace CSS link with actual CSS content
        html_content = html_content.replace(
            '<link rel="stylesheet" href="{{ url_for(\'static\', filename=\'css/style.css\') }}">',
            f'<style>\n{style_css_content}\n</style>'
        )
        
        # Generate sectors HTML
        sectors_html = ""
        sectors = basic_info.get('sectors')
        if sectors and isinstance(sectors, list):
            for sector in sectors:
                if sector and isinstance(sector, dict):
                    sectors_html += f'''
                    <div class="info-card">
                        <div class="icon"><i class="fas fa-signal"></i></div>
                        <h4>{sector.get('title', 'Secteur')}</h4>
                        <p>{sector.get('description', 'Description non disponible')}</p>
                    </div>'''
        
        # Generate markets HTML
        markets_html = ""
        markets = basic_info.get('markets')
        if markets and isinstance(markets, list):
            for market in markets:
                if market and isinstance(market, dict):
                    markets_html += f'''
                    <div class="info-card">
                        <div class="icon"><i class="fas fa-landmark"></i></div>
                        <h4>{market.get('title', 'Marché')}</h4>
                        <p>{market.get('description', 'Description non disponible')}</p>
                    </div>'''
        
        # Helper function to safely get string values (handle None values)
        def safe_get(value, default=''):
            return str(value) if value is not None else default
        
        # Generate key people HTML for standalone section
        key_people_html = ""
        key_people = basic_info.get('keyPeople')
        if key_people and isinstance(key_people, list):
            for person in key_people:
                if person and isinstance(person, dict):
                    # Skip people with all None values
                    if not any([person.get('name'), person.get('position'), person.get('initials')]):
                        continue
                    key_people_html += f'''
                    <div class="person-item">
                        <div class="person-avatar">{safe_get(person.get('initials'), 'N/A')}</div>
                        <div class="person-info">
                            <h4>{safe_get(person.get('name'), 'Nom non disponible')}</h4>
                            <p>{safe_get(person.get('position'), 'Poste non spécifié')}</p>
                        </div>
                    </div>'''
        
        # Generate compact key people HTML for header-overview section
        key_people_compact_html = ""
        key_people_list = basic_info.get('keyPeople')
        if key_people_list and isinstance(key_people_list, list):
            for i, person in enumerate(key_people_list):
                if person and isinstance(person, dict):
                    # Skip people with all None values
                    if not any([person.get('name'), person.get('position')]):
                        continue
                    position = safe_get(person.get("position"), "Poste non spécifié")
                    # Remove "(Dirigeant)" from position if it exists
                    position = position.replace(" (Dirigeant)", "").replace("(Dirigeant)", "").replace("Dirigeant", "")
                    
                    # Start new line every 2 people
                    if i % 2 == 0:
                        if i > 0:  # Close previous line
                            key_people_compact_html += '</div>'
                        key_people_compact_html += '<div class="key-people-row">'
                    
                    key_people_compact_html += f'<span class="key-person-item">• {safe_get(person.get("name"), "Nom non disponible")} ({position})</span>'
        
        # Close the last row if there are any people
        if key_people_list:
            key_people_compact_html += '</div>'
        
        # Replace all Jinja2 template variables with actual data
        html_content = html_content.replace('{{ reportData.companyName }}', company_name)
        html_content = html_content.replace('{{ reportData.companyOverview.companyExpertise }}', safe_get(company_overview.get('companyExpertise'), 'À déterminer'))
        html_content = html_content.replace('{{ reportData.companyOverview.companyDefinition }}', safe_get(company_overview.get('companyDefinition'), f'Entreprise {company_name}'))
        html_content = html_content.replace('{{ reportData.companyOverview.primary_sector }}', safe_get(company_overview.get('primary_sector'), 'Secteur général'))
        html_content = html_content.replace('{{ reportData.companyOverview.legal_form }}', safe_get(company_overview.get('legal_form'), 'SARL'))
        html_content = html_content.replace('{{ reportData.companyOverview.companyFoundationyear }}', safe_get(company_overview.get('companyFoundationyear'), 'Non spécifié'))
        html_content = html_content.replace('{{ reportData.companyOverview.staff_count }}', safe_get(company_overview.get('staff_count'), 'À préciser'))
        html_content = html_content.replace('{{ reportData.contact.address }}', safe_get(basic_info.get('contact', {}).get('address'), 'Adresse à préciser'))
        html_content = html_content.replace('{{ reportData.contact.phone }}', safe_get(basic_info.get('contact', {}).get('phone'), 'Non disponible'))
        html_content = html_content.replace('{{ reportData.contact.email }}', safe_get(basic_info.get('contact', {}).get('email'), 'Non disponible'))
        html_content = html_content.replace('{{ reportData.contact.website }}', safe_get(basic_info.get('contact', {}).get('website'), 'Non disponible'))
        
        # Generate news content with links (same function as HTML report)
        def generate_news_html(news_text, news_articles):
            import html
            news_html = f'<p>{html.escape(news_text) if news_text else "Actualités sectorielles à rechercher"}</p>'
            
            return news_html

        # Debug: Log the textual data before replacement
        recommendation_text = web_data.get('recommendation', 'Recommandation à définir')
        news_text = web_data.get('news', 'Actualités sectorielles à rechercher')
        news_articles = web_data.get('news_articles', [])
        detailed_analysis_text = web_data.get('detailed_analysis', 'Analyse détaillée à compléter')
        
        # Ensure proper encoding and escape HTML characters
        import html
        recommendation_text_safe = html.escape(recommendation_text) if recommendation_text else 'Recommandation à définir'
        news_html_content = generate_news_html(news_text, news_articles)
        detailed_analysis_text_safe = html.escape(detailed_analysis_text) if detailed_analysis_text else 'Analyse détaillée à compléter'
        
        html_content = html_content.replace('{{ reportData.recommendation }}', recommendation_text_safe)
        html_content = html_content.replace('{{ reportData.news }}', news_html_content)
        html_content = html_content.replace('{{ reportData.detailedAnalysis }}', detailed_analysis_text_safe)
        
        # Replace loop sections
        html_content = html_content.replace('{% for sector in reportData.sectors %}\n            <div class="info-card">\n                <div class="icon"><i class="fas fa-signal"></i></div>\n                <h4>{{ sector.title }}</h4>\n                <p>{{ sector.description }}</p>\n            </div>\n            {% endfor %}', sectors_html)
        html_content = html_content.replace('{% for market in reportData.markets %}\n          <div class="info-card">\n            <div class="icon"><i class="fas fa-landmark"></i></div>\n            <h4>{{ market.title }}</h4>\n            <p>{{ market.description }}</p>\n          </div>\n          {% endfor %}', markets_html)
        html_content = html_content.replace('{% for person in reportData.keyPeople %}\n          <div class="person-item">\n            <div class="person-avatar">{{ person.initials }}</div>\n            <div class="person-info">\n              <h4>{{ person.name }}</h4>\n              <p>{{ person.position }}</p>\n            </div>\n          </div>\n          {% endfor %}', key_people_html)
        
        # Replace header-overview keyPeople loop section
        html_content = html_content.replace('<!-- Fourth row: Dirigeants (compact) -->\n          <div class="overview-row">\n            <div class="overview-bullet-item full-width">\n              <i class="fas fa-users" style="color: white; margin-right: 8px;"></i>\n              <span><strong>Dirigeants:</strong></span>\n              <div class="key-people-compact">\n                {% for person in reportData.keyPeople %}\n                <span class="key-person-compact">\n                  <span class="key-person-compact-avatar">{{ person.initials }}</span>\n                  {{ person.name }} ({{ person.position }})\n                </span>\n                {% if not loop.last %}<span class="separator"> • </span>{% endif %}\n                {% endfor %}\n              </div>\n            </div>\n          </div>', f'''<!-- Fourth row: Dirigeants (compact) -->
          <div class="overview-row">
            <div class="overview-bullet-item full-width">
              <i class="fas fa-users" style="color: white; margin-right: 8px;"></i>
              <span><strong>Dirigeants:</strong></span>
              <div class="key-people-compact">
                {key_people_compact_html}
              </div>
            </div>
          </div>''')
        
        # Replace company name placeholders
        html_content = html_content.replace('{{ company_name }}', company_name)
        html_content = html_content.replace('{{ companyName }}', company_name)
        
        # Remove any remaining template variables that should be handled by JavaScript
        html_content = html_content.replace('{{ reportData.financialData.metrics.gearing }}', '')
        
        # Remove remaining Jinja2 syntax - the JavaScript will handle data population
        import re
        html_content = re.sub(r'\{\%.*?\%\}', '', html_content, flags=re.DOTALL)
        key_people = basic_info.get('keyPeople') or []
        html_content = html_content.replace('{{ reportData.keyPeople|length }}', str(len(key_people)))
        html_content = re.sub(r'\{\{.*?\}\}', '', html_content)
        
        # Generate PDF using weasyprint with safer options
        from weasyprint import HTML, CSS
        from weasyprint.text.fonts import FontConfiguration
        from io import BytesIO
        
        # Create a BytesIO buffer to store the PDF
        pdf_buffer = BytesIO()
        
        # Create a simplified HTML version without external dependencies
        # Remove external CDN links that might cause recursion issues
        import re
        
        # Remove external script and link tags
        html_content = re.sub(r'<script[^>]*src="https?://[^"]*"[^>]*></script>', '', html_content)
        html_content = re.sub(r'<link[^>]*href="https?://[^"]*"[^>]*>', '', html_content)
        
        # Remove any remaining script tags that might cause issues
        html_content = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL)
        
        # The CSS contains problematic var() functions causing recursion
        # Skip the complex template and generate a clean PDF directly
        print("🔄 Generating clean PDF to avoid CSS recursion issues...", flush=True)
        
        # Create a clean, simple PDF-friendly HTML
        clean_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>{company_name} - Company Profile</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    margin: 40px;
                    line-height: 1.6;
                    color: #333;
                }}
                .header {{
                    text-align: center;
                    border-bottom: 3px solid #007bff;
                    padding-bottom: 20px;
                    margin-bottom: 30px;
                }}
                h1 {{
                    color: #007bff;
                    font-size: 28px;
                    margin-bottom: 10px;
                }}
                h2 {{
                    color: #555;
                    font-size: 20px;
                    margin-top: 30px;
                    margin-bottom: 15px;
                    border-left: 4px solid #007bff;
                    padding-left: 15px;
                }}
                .section {{
                    margin: 25px 0;
                    padding: 15px;
                    border: 1px solid #eee;
                    border-radius: 5px;
                }}
                .metric {{
                    margin: 8px 0;
                    padding: 5px 0;
                }}
                .metric strong {{
                    color: #007bff;
                    display: inline-block;
                    width: 150px;
                }}
                .financial-grid {{
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 20px;
                    margin: 15px 0;
                }}
                .financial-item {{
                    padding: 10px;
                    background: #f8f9fa;
                    border-radius: 4px;
                }}
                .footer {{
                    margin-top: 40px;
                    padding-top: 20px;
                    border-top: 1px solid #ddd;
                    font-size: 12px;
                    color: #666;
                    text-align: center;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin: 15px 0;
                }}
                th, td {{
                    border: 1px solid #ddd;
                    padding: 8px;
                    text-align: left;
                }}
                th {{
                    background-color: #f2f2f2;
                    font-weight: bold;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{company_name}</h1>
                <p>Company Profile Report</p>
            </div>

            <div class="section">
                <h2>Company Overview</h2>
                <div class="metric"><strong>Company Name:</strong> {company_name}</div>
                <div class="metric"><strong>Legal Form:</strong> {safe_get(company_overview.get('legal_form'), 'Not specified')}</div>
                <div class="metric"><strong>Founded:</strong> {safe_get(company_overview.get('companyFoundationyear'), 'Not specified')}</div>
                <div class="metric"><strong>Primary Sector:</strong> {safe_get(company_overview.get('primary_sector'), 'General sector')}</div>
                <div class="metric"><strong>Expertise:</strong> {safe_get(company_overview.get('companyExpertise'), 'To be determined')}</div>
            </div>"""
        
        # Add financial data if available
        if extracted_kpis:
            clean_html += """
            <div class="section">
                <h2>Financial Information</h2>
                <table>
                    <tr><th>Metric</th><th>Value</th></tr>"""
            
            for key, value in extracted_kpis.items():
                if value is not None:
                    clean_html += f"<tr><td>{key.replace('_', ' ').title()}</td><td>{value}</td></tr>"
            
            clean_html += "</table>"
        
        if computed_ratios:
            clean_html += """
                <h2>Financial Ratios</h2>
                <table>
                    <tr><th>Ratio</th><th>Value</th></tr>"""
            
            for key, value in computed_ratios.items():
                if value is not None:
                    clean_html += f"<tr><td>{key.replace('_', ' ').title()}</td><td>{value}</td></tr>"
            
            clean_html += "</table>"
        
        clean_html += """
            </div>

            <div class="section">
                <h2>Contact Information</h2>"""
        
        contact = basic_info.get('contact', {})
        clean_html += f"""
                <div class="metric"><strong>Address:</strong> {safe_get(contact.get('address'), 'Not available')}</div>
                <div class="metric"><strong>Phone:</strong> {safe_get(contact.get('phone'), 'Not available')}</div>
                <div class="metric"><strong>Email:</strong> {safe_get(contact.get('email'), 'Not available')}</div>
                <div class="metric"><strong>Website:</strong> {safe_get(contact.get('website'), 'Not available')}</div>
            </div>"""
        
        # Add sectors if available
        if basic_info.get('sectors'):
            clean_html += """
            <div class="section">
                <h2>Business Sectors</h2>"""
            sectors = basic_info.get('sectors')
            if sectors and isinstance(sectors, list):
                for sector in sectors:
                    if sector and isinstance(sector, dict):
                        title = safe_get(sector.get('title'), 'Sector')
                        description = safe_get(sector.get('description'), 'Description not available')
                        clean_html += f"<div class='metric'><strong>{title}:</strong> {description}</div>"
            clean_html += "</div>"
        
        # Add markets if available
        if basic_info.get('markets'):
            clean_html += """
            <div class="section">
                <h2>Target Markets</h2>"""
            markets = basic_info.get('markets')
            if markets and isinstance(markets, list):
                for market in markets:
                    if market and isinstance(market, dict):
                        title = safe_get(market.get('title'), 'Market')
                        description = safe_get(market.get('description'), 'Description not available')
                        clean_html += f"<div class='metric'><strong>{title}:</strong> {description}</div>"
            clean_html += "</div>"
        
        clean_html += f"""
            <div class="footer">
                <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p>This is a simplified PDF version. For the complete interactive report with charts and detailed analysis, please view the HTML version.</p>
            </div>
        </body>
        </html>
        """
        
        # Generate PDF from clean HTML
        html_doc = HTML(string=clean_html, encoding='utf-8', base_url='')
        html_doc.write_pdf(pdf_buffer)
        
        # Get PDF content
        pdf_content = pdf_buffer.getvalue()
        pdf_buffer.close()
        
        # Generate filename
        timestamp = datetime.now().strftime('%Y-%m-%d')
        filename = f"{company_name.replace(' ', '_')}_report_{timestamp}.pdf"
        
        # Return PDF response
        from flask import Response
        return Response(
            pdf_content,
            mimetype='application/pdf',
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"',
                'Content-Length': str(len(pdf_content))
            }
        )
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"❌ Error generating PDF: {str(e)}", flush=True)
        print(f"❌ Full traceback: {error_details}", flush=True)
        return jsonify({'error': f'PDF generation failed: {str(e)}'}), 500

@app.route('/api/profiles/<profile_id>/send-email', methods=['POST'])
@jwt_required()
def send_profile_email(profile_id):
    """Manually send PDF report via email for a completed profile"""
    try:
        profile = CompanyProfile.query.get_or_404(profile_id)
        
        # Check if profile is completed
        if profile.status != 'completed':
            return jsonify({'error': 'Profile must be completed before sending email'}), 400
        
        # Get the current user to check permissions
        user_id = get_jwt_identity()
        user = db.session.get(User, user_id)
        
        # Check if user is admin or the profile creator
        if user.role != 'admin' and profile.created_by != user_id:
            return jsonify({'error': 'Unauthorized to send email for this profile'}), 403
        
        # Send PDF report via email
        success = send_pdf_report_email(profile_id)
        
        if success:
            return jsonify({'message': 'PDF report sent successfully via email'}), 200
        else:
            return jsonify({'error': 'Failed to send PDF report via email'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def wait_for_db(max_retries=30, delay=1):
    """Wait for database to be ready"""
    for attempt in range(max_retries):
        try:
            with app.app_context():
                db.engine.connect()
                print(f"Database connection successful on attempt {attempt + 1}")
                return True
        except Exception as e:
            print(f"Database connection attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(delay)
            else:
                raise e
    return False

@app.route('/api/profiles/<profile_id>/confirm-upload', methods=['POST'])
@jwt_required()
def confirm_upload_with_mismatch(profile_id):
    """
    Handle user confirmation when company names don't match.
    User can choose to proceed with the upload or cancel it.
    """
    try:
        # Check if profile exists
        profile = CompanyProfile.query.get_or_404(profile_id)
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        action = data.get('action')  # 'proceed' or 'cancel'
        if action not in ['proceed', 'cancel']:
            return jsonify({'error': 'Invalid action. Must be "proceed" or "cancel"'}), 400
        
        if action == 'cancel':
            return jsonify({
                'message': 'Upload cancelled by user due to company name mismatch',
                'action': 'cancelled'
            }), 200
        
        # If user chooses to proceed, we need the file data
        files = request.files.getlist('files')
        if not files:
            return jsonify({'error': 'No files provided for confirmed upload'}), 400
        
        # Check file count
        if len(files) > 3:
            return jsonify({'error': 'Maximum 3 files allowed'}), 400
        
        # Proceed with upload (user has confirmed despite mismatch)
        uploaded_files = []
        
        for file in files:
            if file.filename == '':
                continue
                
            # Check file size (16MB limit)
            if file.content_length and file.content_length > app.config['MAX_CONTENT_LENGTH']:
                return jsonify({'error': f'File {file.filename} exceeds size limit'}), 400
            
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{profile_id}_{filename}")
            file.save(file_path)
            
            # Save document record
            document = LiasseDocument(
                profile_id=profile_id,
                file_name=filename,
                file_path=file_path,
                file_size=os.path.getsize(file_path)
            )
            
            db.session.add(document)
            uploaded_files.append({
                'id': document.id,
                'filename': filename,
                'size': document.file_size
            })
        
        db.session.commit()
        
        return jsonify({
            'message': 'Files uploaded successfully after user confirmation',
            'files': uploaded_files,
            'action': 'proceeded',
            'warning': 'Company names did not match but upload proceeded as confirmed by user'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/profiles/<profile_id>/confirm-smart-upload', methods=['POST'])
@jwt_required()
def confirm_smart_upload_with_mismatch(profile_id):
    """
    Handle user confirmation when company names don't match during smart upload.
    User can choose to proceed with the smart upload or cancel it.
    """
    try:
        # Check if profile exists
        profile = CompanyProfile.query.get_or_404(profile_id)
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        action = data.get('action')  # 'proceed' or 'cancel'
        if action not in ['proceed', 'cancel']:
            return jsonify({'error': 'Invalid action. Must be "proceed" or "cancel"'}), 400
        
        if action == 'cancel':
            return jsonify({
                'message': 'Smart upload cancelled by user due to company name mismatch',
                'action': 'cancelled'
            }), 200
        
        # If user chooses to proceed, we need the file data
        files = request.files.getlist('files')
        if not files:
            return jsonify({'error': 'No files provided for confirmed smart upload'}), 400
        
        # Check file count
        if len(files) > 3:
            return jsonify({'error': 'Maximum 3 files allowed'}), 400
        
        # Proceed with smart upload (user has confirmed despite mismatch)
        from services.profile_verification import identify_new_vs_existing_documents
        
        # Save files temporarily for analysis
        import tempfile
        temp_file_paths = []
        try:
            for i, file in enumerate(files):
                if file.filename == '':
                    continue
                    
                # Check file size (16MB limit)
                if file.content_length and file.content_length > app.config['MAX_CONTENT_LENGTH']:
                    return jsonify({'error': f'File {file.filename} exceeds size limit'}), 400
                
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                    file.save(temp_file.name)
                    temp_file_paths.append(temp_file.name)
            
            # Extract company info from all documents
            from services.profile_verification import extract_company_info_from_first_page
            
            all_company_info = []
            api_key = app.config.get('ANTHROPIC_API_KEY')
            
            for i, file_path in enumerate(temp_file_paths):
                company_info = extract_company_info_from_first_page(file_path, api_key)
                if company_info:
                    all_company_info.append(company_info)
            
            # Now call the function with all required parameters
            document_analysis = identify_new_vs_existing_documents(
                db, CompanyProfile, temp_file_paths, profile.company_name, all_company_info
            )
            
            uploaded_files = []
            processed_count = 0
            
            # Handle existing documents - reuse saved data
            for match in document_analysis['existing_matches']:
                filename = os.path.basename(match['file_path'])
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{profile_id}_{filename}")
                
                # Copy the file to the new profile's directory
                import shutil
                shutil.copy2(match['file_path'], file_path)
                
                document = LiasseDocument(
                    profile_id=profile_id,
                    file_name=filename,
                    file_path=file_path,
                    file_size=os.path.getsize(file_path),
                    extracted_data=match['existing_data'].get('extracted_data'),
                    upload_status='reused',
                    ocr_status='completed'
                )
                
                db.session.add(document)
                uploaded_files.append({
                    'id': document.id,
                    'filename': filename,
                    'size': document.file_size,
                    'status': 'reused',
                    'message': 'Document data reused from existing profile'
                })
            
            # Handle new documents - process normally
            for new_doc in document_analysis['new_documents']:
                filename = os.path.basename(new_doc['file_path'])
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{profile_id}_{filename}")
                
                # Copy the file to the new profile's directory
                import shutil
                shutil.copy2(new_doc['file_path'], file_path)
                
                # Save document record for new document
                document = LiasseDocument(
                    profile_id=profile_id,
                    file_name=filename,
                    file_path=file_path,
                    file_size=os.path.getsize(file_path),
                    upload_status='uploaded',
                    ocr_status='pending'
                )
                
                db.session.add(document)
                uploaded_files.append({
                    'id': document.id,
                    'filename': filename,
                    'size': document.file_size,
                    'status': 'new',
                    'message': 'Document will be processed'
                })
                processed_count += 1
            
            db.session.commit()
            
            return jsonify({
                'message': 'Smart upload completed successfully after user confirmation',
                'uploaded_files': uploaded_files,
                'document_analysis': document_analysis,
                'new_documents_to_process': processed_count,
                'action': 'proceeded',
                'warning': 'Company names did not match but smart upload proceeded as confirmed by user'
            })
            
        finally:
            # Clean up temporary files
            for temp_path in temp_file_paths:
                try:
                    os.unlink(temp_path)
                except:
                    pass
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Expert Comptable routes
@app.route('/api/expertcompta/process', methods=['POST'])
@jwt_required()
def process_expert_comptable():
    """
    Process a liasse comptable document for expert comptable analysis.
    Only extracts financial data and generates financial analysis.
    """
    try:
        # Get company name from form data
        company_name = request.form.get('company_name', '').strip()
        if not company_name:
            return jsonify({'error': 'Company name is required'}), 400
        
        # Check if file was uploaded
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Check file type
        if not file.filename.lower().endswith('.pdf'):
            return jsonify({'error': 'Only PDF files are allowed'}), 400
        
        # Save file temporarily
        import tempfile
        import os
        import time
        from werkzeug.utils import secure_filename
        
        filename = secure_filename(file.filename)
        temp_dir = tempfile.mkdtemp()
        file_path = os.path.join(temp_dir, filename)
        file.save(file_path)
        
        try:
            # Process the document using expert comptable service
            from expertcomptable.doc_processing import process_expert_comptable_document
            
            result = process_expert_comptable_document(company_name, file_path)
            
            if result.get('status') == 'error':
                return jsonify({'error': result.get('error', 'Processing failed')}), 500
            
            # Generate report
            from expertcomptable.report_generator import generate_expert_comptable_report
            report_html = generate_expert_comptable_report(result)
            
            # Debug the generated report
            print(f"[EXPERT COMPTABLE DEBUG] Generated report length: {len(report_html)} characters", flush=True)
            
            if 'Cadrage de TVA' in report_html:
                print(f"[EXPERT COMPTABLE DEBUG] ✅ 'Cadrage de TVA' section found in report HTML!", flush=True)
            else:
                print(f"[EXPERT COMPTABLE DEBUG] ❌ 'Cadrage de TVA' section NOT found in report HTML", flush=True)
            
            # Count TVA-related content
            tva_keywords = ['TVA Théorique', 'TVA Pratique', 'Encaissement Théorique']
            found_keywords = sum(1 for keyword in tva_keywords if keyword in report_html)
            print(f"[EXPERT COMPTABLE DEBUG] Found {found_keywords}/{len(tva_keywords)} TVA keywords in report", flush=True)
            
            # Save report to file for debugging (optional)
            try:
                debug_filename = f"debug_expert_comptable_report_{company_name.replace(' ', '_')}_{int(time.time())}.html"
                debug_path = os.path.join(tempfile.gettempdir(), debug_filename)
                with open(debug_path, 'w', encoding='utf-8') as f:
                    f.write(report_html)
                print(f"[EXPERT COMPTABLE DEBUG] Report saved to: {debug_path}", flush=True)
            except Exception as save_error:
                print(f"[EXPERT COMPTABLE DEBUG] Could not save debug report: {save_error}", flush=True)
            
            return jsonify({
                'message': 'Document processed successfully',
                'data': result,
                'report_html': report_html
            })
            
        finally:
            # Clean up temporary file
            try:
                os.remove(file_path)
                os.rmdir(temp_dir)
            except:
                pass
                
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/expertcompta/report', methods=['POST'])
@jwt_required()
def generate_expert_comptable_report_endpoint():
    """
    Generate a report from processed expert comptable data.
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        from expertcomptable.report_generator import generate_expert_comptable_report
        report_html = generate_expert_comptable_report(data)
        
        return jsonify({
            'report_html': report_html
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/expertcompta/pdf', methods=['POST'])
@jwt_required()
def generate_expert_comptable_pdf():
    """
    Generate and serve a PDF version of the expert comptable report
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        from expertcomptable.pdf_generator import generate_expert_comptable_pdf
        pdf_content, filename = generate_expert_comptable_pdf(data)
        
        # Return PDF as response
        from flask import Response
        return Response(
            pdf_content,
            mimetype='application/pdf',
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"',
                'Content-Type': 'application/pdf'
            }
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/profiles/<profile_id>/expert-comptable-report', methods=['GET'])
def get_profile_expert_comptable_report(profile_id):
    """Generate expert comptable report from profile data including TVA analysis"""
    try:
        profile = CompanyProfile.query.get_or_404(profile_id)
        
        print(f"[TVA ENDPOINT DEBUG] Profile {profile_id} status: {profile.status}", flush=True)
        
        if profile.status != 'completed':
            return jsonify({'error': 'Profile is not completed yet'}), 400
            
        profile_data = profile.profile_data or {}
        print(f"[TVA ENDPOINT DEBUG] Profile data keys: {list(profile_data.keys())}", flush=True)
        
        extracted_kpis = profile_data.get('extracted_kpis', {})
        computed_ratios = profile_data.get('computed_ratios', {})
        tva_analysis = profile_data.get('tva_analysis', {})
        financial_analysis = profile_data.get('financial_analysis', {})
        company_name = profile_data.get('company_name') or profile.company_name
        fiscal_year = profile.fiscal_years or 'N/A'
        
        print(f"[TVA ENDPOINT DEBUG] TVA analysis from profile: {tva_analysis}", flush=True)
        print(f"[TVA ENDPOINT DEBUG] TVA analysis keys: {list(tva_analysis.keys()) if tva_analysis else 'None'}", flush=True)
        
        # Prepare data structure for expert comptable report
        report_data = {
            'company_name': company_name,
            'fiscal_year': fiscal_year,
            'kpis': extracted_kpis,
            'computed_ratios': computed_ratios,
            'tva_analysis': tva_analysis,
            'financial_analysis': financial_analysis
        }
        
        print(f"[TVA ENDPOINT DEBUG] Report data TVA keys: {list(report_data['tva_analysis'].keys()) if report_data['tva_analysis'] else 'None'}", flush=True)
        
        # Generate the expert comptable report
        from flask import Response
        from expertcomptable.report_generator import generate_expert_comptable_report
        report_html = generate_expert_comptable_report(report_data)
        
        # Check if TVA section was added to HTML
        if 'Cadrage de TVA' in report_html:
            print(f"[TVA ENDPOINT DEBUG] ✅ TVA section found in generated HTML", flush=True)
        else:
            print(f"[TVA ENDPOINT DEBUG] ❌ TVA section NOT found in generated HTML", flush=True)
        
        # Return HTML response
        return Response(report_html, mimetype='text/html')
        
    except Exception as e:
        print(f"[TVA ENDPOINT DEBUG] Error generating expert comptable report: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/expertcompta/send-email', methods=['POST'])
@jwt_required()
def send_expert_comptable_email():
    """
    Send expert comptable report via email
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        email = data.get('email')
        if not email:
            return jsonify({'error': 'Email address is required'}), 400
            
        # Validate email format
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            return jsonify({'error': 'Invalid email format'}), 400
            
        report_data = data.get('report_data')
        if not report_data:
            return jsonify({'error': 'Report data is required'}), 400
            
        # Generate HTML report
        from expertcomptable.report_generator import generate_expert_comptable_report
        report_html = generate_expert_comptable_report(report_data)
        
        # Get company name for email subject
        company_name = report_data.get('company_name', 'Entreprise')
        
        # Import the existing email service and datetime
        from services.send_email import send_email
        from datetime import datetime
        
        # Create email body
        email_body = f"""Bonjour,

Veuillez trouver ci-joint votre rapport d'analyse financière expert-comptable pour {company_name}.

Ce rapport a été généré automatiquement à partir de votre liasse fiscale et contient :
- Analyse des indicateurs financiers clés
- Diagnostic financier détaillé
- Ratios et métriques de performance
- Recommandations d'expert-comptable

Le rapport est disponible au format HTML ci-joint.

Cordialement,
L'équipe Company Profile Agent

---
Ce message a été généré automatiquement le {datetime.now().strftime('%d/%m/%Y à %H:%M')}.
"""
        
        # Send email with HTML attachment
        html_bytes = report_html.encode('utf-8')
        filename = f"rapport-expert-comptable-{company_name.replace(' ', '-')}.html"
        
        success = send_email(
            to_email=email,
            subject=f'Rapport Expert-Comptable - {company_name}',
            body=email_body,
            attachment_data=html_bytes,
            attachment_filename=filename
        )
        
        if success:
            return jsonify({'message': 'Email sent successfully'}), 200
        else:
            return jsonify({'error': 'Failed to send email'}), 500
            
    except Exception as e:
        print(f"❌ Error sending expert comptable email: {str(e)}", flush=True)
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    # Wait for database to be ready
    wait_for_db()
    
    with app.app_context():
        db.create_all()
        print("Database tables created successfully")
    
    print("Starting Flask application...")
    app.run(host='0.0.0.0', port=5000, debug=True)


