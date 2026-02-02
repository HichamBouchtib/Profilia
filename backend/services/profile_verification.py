import os
import json
import base64
import fitz  # PyMuPDF
import anthropic
from typing import Optional, Dict, Any
import hashlib
from sqlalchemy import text
import re
import sys

# Import the new logging system
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.logger import log_debug, log_info, log_success, log_warning, log_error

def extract_json_from_response(response_text: str) -> str:
    """
    Extract JSON content from a response that may be wrapped in markdown code blocks.
    
    Args:
        response_text (str): The raw response text from Claude
        
    Returns:
        str: Clean JSON text ready for parsing
    """
    if not response_text:
        return ""
    
    # Remove markdown code block formatting if present
    json_text = response_text.strip()
    
    # Handle ```json ... ``` blocks
    if json_text.startswith('```json') and json_text.endswith('```'):
        json_text = json_text[7:-3].strip()
    # Handle generic ``` ... ``` blocks
    elif json_text.startswith('```') and json_text.endswith('```'):
        json_text = json_text[3:-3].strip()
    
    return json_text

def _extract_first_page_as_pdf(file_path: str) -> Optional[str]:
    """
    Extract the first page of a PDF as a separate PDF file.
    
    Args:
        file_path (str): Path to the original PDF file
        
    Returns:
        str: Path to the temporary first page PDF file, or None if extraction fails
    """
    try:
        # Open the original PDF
        doc = fitz.open(file_path)
        if len(doc) == 0:
            log_error(f"PDF has no pages: {file_path}")
            doc.close()
            return None
        
        # Create a new PDF with only the first page
        first_page_pdf = fitz.open()
        first_page_pdf.insert_pdf(doc, from_page=0, to_page=0)
        
        # Create temporary file for the first page
        import tempfile
        temp_fd, temp_path = tempfile.mkstemp(suffix='_first_page.pdf')
        os.close(temp_fd)  # Close the file descriptor
        
        # Save the first page PDF
        first_page_pdf.save(temp_path)
        first_page_pdf.close()
        doc.close()
        
        # print(f"[VERIFICATION] Extracted first page to: {temp_path}", flush=True)
        return temp_path
        
    except Exception as e:
        log_error(f"Error extracting first page: {str(e)}")
        return None

def extract_company_info_from_first_page(file_path: str, api_key: str) -> Optional[Dict[str, Any]]:
    """
    Extract company name and fiscal year from the first page of a PDF document using Claude.
    
    Args:
        file_path (str): Path to the PDF file
        api_key (str): Anthropic API key
        
    Returns:
        Dict containing company_name and fiscal_year, or None if extraction fails
    """
    temp_first_page_path = None
    try:
        # print(f"[VERIFICATION] Starting extraction from first page: {file_path}", flush=True)
        
        # Initialize Anthropic client
        client = anthropic.Anthropic(api_key=api_key)
        
        # Extract first page as separate PDF
        temp_first_page_path = _extract_first_page_as_pdf(file_path)
        if not temp_first_page_path:
            log_error(f"Failed to extract first page from: {file_path}")
            return None
        
        # Read the first page PDF as base64
        with open(temp_first_page_path, 'rb') as f:
            pdf_base64 = base64.b64encode(f.read()).decode('utf-8')
        
        log_debug(f"First page PDF size: {len(pdf_base64)} chars")
        
        # Create prompt for company info extraction
        extraction_prompt = (
            "Tu es un expert en analyse de documents fiscaux marocains. "
            "À partir de cette première page de document fiscal, identifie et retourne UNIQUEMENT :\n\n"
            "1. Le nom exact de l'entreprise/société\n"
            "2. L'année fiscale ou exercice (par exemple: 2023, 2022, etc.)\n\n"
            "IMPORTANT:\n"
            "- Retourne un JSON strict avec les clés 'company_name' et 'fiscal_year'\n"
            "- Si tu ne trouves pas l'information, mets null pour cette clé\n"
            "- Pour fiscal_year, retourne uniquement l'année en nombre (ex: 2023)\n"
            "- Pour company_name, retourne le nom complet et exact de l'entreprise\n\n"
            "Exemple de format de réponse:\n"
            "{\n"
            "  \"company_name\": \"SOCIÉTÉ EXEMPLE SARL\",\n"
            "  \"fiscal_year\": 2023\n"
            "}"
        )
        
        # Send request to Claude with PDF document format
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            messages=[
                {
                    'role': 'user',
                    'content': [
                        {
                            'type': 'document',
                            'source': {
                                'type': 'base64',
                                'media_type': 'application/pdf',
                                'data': pdf_base64,
                            },
                        },
                        {'type': 'text', 'text': extraction_prompt},
                    ],
                }
            ],
        )
        
        response_text = (message.content[0].text or '').strip()
        print(f"[VERIFICATION] Claude response: {response_text}", flush=True)
        
        # Extract JSON from markdown code blocks if present
        json_text = extract_json_from_response(response_text)
        
        # Parse JSON response
        try:
            company_info = json.loads(json_text)
            
            # Validate required fields
            if not isinstance(company_info, dict):
                print(f"[VERIFICATION] Response is not a dictionary", flush=True)
                return None
                
            # Extract and validate company name
            company_name = company_info.get('company_name')
            if company_name and isinstance(company_name, str):
                company_name = company_name.strip()
                # Normalize company name to remove legal suffixes
                company_name = _normalize_company_name(company_name)
            else:
                company_name = None
                
            # Extract and validate fiscal year
            fiscal_year = company_info.get('fiscal_year')
            if fiscal_year is not None:
                try:
                    fiscal_year = int(fiscal_year)
                    # Validate year range (should be reasonable)
                    if fiscal_year < 2000 or fiscal_year > 2030:
                        print(f"[VERIFICATION] Fiscal year out of range: {fiscal_year}", flush=True)
                        fiscal_year = None
                except (ValueError, TypeError):
                    print(f"[VERIFICATION] Invalid fiscal year format: {fiscal_year}", flush=True)
                    fiscal_year = None
            
            result = {
                'company_name': company_name,
                'fiscal_year': fiscal_year
            }
            
            # print(f"[VERIFICATION] Extracted info: {result}", flush=True)
            return result
            
        except json.JSONDecodeError as e:
            print(f"[VERIFICATION] Failed to parse JSON response: {e}", flush=True)
            print(f"[VERIFICATION] Raw response: {response_text}", flush=True)
            return None
            
    except anthropic.APIError as e:
        # Handle specific Anthropic API errors
        error_message = str(e)
        if "529" in error_message and "overloaded" in error_message.lower():
            print(f"[VERIFICATION] Anthropic API overloaded (Error 529): {error_message}", flush=True)
            # Return a special error indicator for overloaded API
            return {"error": "anthropic_overloaded", "message": "Anthropic API is currently overloaded. Please try again later."}
        elif "rate_limit" in error_message.lower() or "429" in error_message:
            print(f"[VERIFICATION] Anthropic API rate limited: {error_message}", flush=True)
            return {"error": "anthropic_rate_limited", "message": "Anthropic API rate limit exceeded. Please try again later."}
        elif "invalid_api_key" in error_message.lower() or "401" in error_message:
            print(f"[VERIFICATION] Anthropic API key error: {error_message}", flush=True)
            return {"error": "anthropic_auth_error", "message": "Anthropic API key is invalid or expired."}
        else:
            print(f"[VERIFICATION] Anthropic API error: {error_message}", flush=True)
            return {"error": "anthropic_api_error", "message": f"Anthropic API error: {error_message}"}
    except Exception as e:
        print(f"[VERIFICATION] Error extracting company info: {str(e)}", flush=True)
        return None
    finally:
        # Clean up temporary first page PDF file
        if temp_first_page_path and os.path.exists(temp_first_page_path):
            try:
                os.unlink(temp_first_page_path)
                print(f"[VERIFICATION] Cleaned up temporary file: {temp_first_page_path}", flush=True)
            except Exception as e:
                print(f"[VERIFICATION] Warning: Failed to clean up temporary file {temp_first_page_path}: {e}", flush=True)

def check_existing_profile(db, CompanyProfile, company_name: str, fiscal_year_range: Optional[str]) -> Optional[Dict[str, Any]]:
    """
    Check if a profile already exists for the given company name.
    For multi-document scenarios, we check by company name first, then verify if the specific
    fiscal year range already exists in the profile.
    
    Args:
        db: Database session
        CompanyProfile: CompanyProfile model class
        company_name (str): Company name to search for
        fiscal_year_range (str, optional): Fiscal year range to check for (e.g., "2022", "2022-2023")
        
    Returns:
        Dict with existing profile data if found, None otherwise
    """
    try:
        print(f"[VERIFICATION] Checking for existing profile: {company_name}, {fiscal_year_range}", flush=True)
        
        if not company_name or not company_name.strip():
            print(f"[VERIFICATION] Invalid company name provided", flush=True)
            return None
            
        # Try multiple company name variations to catch similar names
        # This handles cases like "G4S MAROC S.A." vs "G4S MAROC"
        company_variations = [
            company_name.strip(),
            company_name.strip().replace('S.A.', '').replace('SA', '').strip(),
            company_name.strip().replace('SARL', '').strip(),
            company_name.strip().split()[0] if company_name.strip().split() else company_name.strip()
        ]
        
        existing_profile = None
        for variation in company_variations:
            if not variation:
                continue
                
            print(f"[VERIFICATION] Trying company name variation: '{variation}'", flush=True)
            
            profiles = CompanyProfile.query.filter(
                CompanyProfile.company_name.ilike(f'%{variation}%')
            ).order_by(CompanyProfile.created_at.desc()).all()
            
            if profiles:
                print(f"[VERIFICATION] Found {len(profiles)} potential matches for '{variation}'", flush=True)
                # Use the most recent profile
                existing_profile = profiles[0]
                break
                
        if not existing_profile:
            # Try a more flexible search with just the first word
            first_word = company_name.strip().split()[0] if company_name.strip().split() else ""
            if len(first_word) > 2:  # Only if first word is meaningful
                print(f"[VERIFICATION] Trying flexible search with first word: '{first_word}'", flush=True)
                profiles = CompanyProfile.query.filter(
                    CompanyProfile.company_name.ilike(f'{first_word}%')
                ).order_by(CompanyProfile.created_at.desc()).all()
                
                if profiles:
                    print(f"[VERIFICATION] Found {len(profiles)} flexible matches for '{first_word}'", flush=True)
                    existing_profile = profiles[0]
        
        if existing_profile:
            print(f"[VERIFICATION] Found existing profile: {existing_profile.id} (fiscal_years: {existing_profile.fiscal_years})", flush=True)
            
            # Check if this profile covers the requested fiscal year range
            if fiscal_year_range and existing_profile.fiscal_years:
                covers_years = _profile_covers_fiscal_year(existing_profile.fiscal_years, fiscal_year_range)
                if covers_years:
                    print(f"[VERIFICATION] Profile already covers fiscal year range {fiscal_year_range}", flush=True)
                else:
                    print(f"[VERIFICATION] Profile found but does not cover fiscal year range {fiscal_year_range} - can be extended", flush=True)
            
            # Safely handle profile_data serialization
            try:
                profile_data = existing_profile.profile_data or {}
            except Exception as e:
                print(f"[VERIFICATION] Error accessing profile_data: {e}", flush=True)
                profile_data = {}
            
            result = {
                'id': str(existing_profile.id),  # Convert UUID to string for JSON serialization
                'company_name': existing_profile.company_name,
                'fiscal_years': getattr(existing_profile, 'fiscal_years', None),  # Fiscal years field
                'fiscal_year': getattr(existing_profile, 'fiscal_years', None),   # Backwards compatibility - use fiscal_years
                'status': existing_profile.status,
                'profile_data': profile_data,
                'created_at': existing_profile.created_at.isoformat()
            }
            
            return result
        else:
            return None
            
    except Exception as e:
        print(f"[VERIFICATION] Error checking existing profile: {str(e)}", flush=True)
        # Re-raise the exception so it can be handled by the calling function
        raise e

def _profile_covers_fiscal_year(profile_fiscal_years: str, target_fiscal_years: str) -> bool:
    """
    Check if a profile's fiscal_years field covers a specific target fiscal year or range.
    
    Args:
        profile_fiscal_years: The fiscal_years field from the profile (e.g., "2023", "2022-2023")
        target_fiscal_years: The target fiscal year or range to check for (e.g., "2023", "2022-2023")
        
    Returns:
        bool: True if the profile covers the target fiscal year(s)
    """
    try:
        if not profile_fiscal_years or not target_fiscal_years:
            return False
        
        profile_fiscal_years = profile_fiscal_years.strip()
        target_fiscal_years = target_fiscal_years.strip()
        
        # Parse target fiscal years
        target_years = set()
        if target_fiscal_years.isdigit():
            # Single year (e.g., "2023")
            target_years.add(int(target_fiscal_years))
        elif '-' in target_fiscal_years:
            # Year range (e.g., "2022-2023")
            parts = target_fiscal_years.split('-')
            if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                start_year = int(parts[0])
                end_year = int(parts[1])
                for year in range(start_year, end_year + 1):
                    target_years.add(year)
        
        if not target_years:
            return False
        
        # Parse profile fiscal years
        profile_years = set()
        if profile_fiscal_years.isdigit():
            # Single year (e.g., "2023")
            profile_years.add(int(profile_fiscal_years))
        elif '-' in profile_fiscal_years:
            # Year range (e.g., "2022-2023")
            parts = profile_fiscal_years.split('-')
            if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                start_year = int(parts[0])
                end_year = int(parts[1])
                for year in range(start_year, end_year + 1):
                    profile_years.add(year)
        
        if not profile_years:
            return False
        
        # Check if profile covers all target years
        return target_years.issubset(profile_years)
        
    except Exception as e:
        print(f"[VERIFICATION] Error checking fiscal year coverage: {e}", flush=True)
        return False

def calculate_document_hash(file_path: str) -> str:
    """
    Calculate a hash of the document content to identify duplicate documents.
    
    Args:
        file_path (str): Path to the document file
        
    Returns:
        str: SHA-256 hash of the document content
    """
    try:
        with open(file_path, 'rb') as f:
            content = f.read()
            return hashlib.sha256(content).hexdigest()
    except Exception as e:
        print(f"[VERIFICATION] Error calculating document hash: {e}", flush=True)
        return None

def check_existing_documents(db, CompanyProfile, company_name: str) -> Dict[str, Any]:
    """
    Check if documents for this company already exist in the database.
    
    Args:
        db: Database session
        CompanyProfile: CompanyProfile model class
        company_name (str): Company name to search for
        
    Returns:
        Dict with existing document information if found
    """
    try:        
        # Try multiple company name variations to catch similar names
        variations = [
            company_name.strip(),
            company_name.strip().replace('S.A.', '').replace('SA', '').strip(),
            company_name.strip().replace('SARL', '').strip(),
            company_name.strip().split()[0] if company_name.strip().split() else company_name.strip()
        ]
        
        # Remove duplicates while preserving order
        company_variations = []
        seen = set()
        for variation in variations:
            if variation and variation not in seen:
                company_variations.append(variation)
                seen.add(variation)
        
        log_debug(f"Generated {len(company_variations)} unique company name variations: {company_variations}")
        
        existing_profile = None
        for variation in company_variations:
            if not variation:
                continue
                
            log_debug(f"Trying company name variation: '{variation}'")
            
            profiles = CompanyProfile.query.filter(
                CompanyProfile.company_name.ilike(f'%{variation}%')
            ).order_by(CompanyProfile.created_at.desc()).all()
            
            if profiles:
                log_info(f"Found {len(profiles)} potential matches for '{variation}'")
                # Use the most recent profile
                existing_profile = profiles[0]
                break
        
        if existing_profile:
            log_success(f"Found existing profile: {existing_profile.id} (fiscal_years: {existing_profile.fiscal_years})")
            
            # Return existing profile info for comparison
            return {
                'id': str(existing_profile.id),
                'company_name': existing_profile.company_name,
                'fiscal_years': getattr(existing_profile, 'fiscal_years', None),
                'status': existing_profile.status,
                'created_at': existing_profile.created_at.isoformat()
            }
        
        return None
        
    except Exception as e:
        print(f"[VERIFICATION] Error checking existing documents: {str(e)}", flush=True)
        return None

def should_create_new_profile(existing_profile: Dict[str, Any], target_fiscal_years: str) -> bool:
    """
    Determine if a new profile should be created based on fiscal year coverage.
    
    Args:
        existing_profile: Existing profile information
        target_fiscal_years: Target fiscal year range (e.g., "2022-2023")
        
    Returns:
        bool: True if a new profile should be created
    """
    try:
        if not existing_profile or not existing_profile.get('fiscal_years'):
            return True
        
        existing_fiscal_years = existing_profile['fiscal_years']
        print(f"[VERIFICATION] Comparing existing fiscal years '{existing_fiscal_years}' with target '{target_fiscal_years}'", flush=True)
        
        # Check if existing profile covers the target fiscal years
        covers_target = _profile_covers_fiscal_year(existing_fiscal_years, target_fiscal_years)
        
        if covers_target:
            print(f"[VERIFICATION] Existing profile already covers target fiscal years - no new profile needed", flush=True)
            return False
        else:
            print(f"[VERIFICATION] Existing profile does not cover target fiscal years - new profile needed", flush=True)
            return True
            
    except Exception as e:
        print(f"[VERIFICATION] Error determining if new profile needed: {e}", flush=True)
        return True

def verify_profile_before_creation(file_paths: list, api_key: str, db, CompanyProfile, fallback_company_name: str = None) -> Dict[str, Any]:
    """
    Main verification function that combines extraction and existence check.
    Implements smart document deduplication to avoid reprocessing existing documents.
    
    Args:
        file_paths (list): List of paths to uploaded files
        api_key (str): Anthropic API key
        db: Database session
        CompanyProfile: CompanyProfile model class
        fallback_company_name (str): Optional fallback company name if extraction fails
        
    Returns:
        Dict with verification results
    """
    try:
        # print(f"[VERIFICATION] Starting profile verification for {len(file_paths)} documents", flush=True)
        
        # Step 1: Extract company info from all documents to determine company name
        all_company_info = []
        company_names = set()
        fiscal_years = set()
        
        for i, file_path in enumerate(file_paths):
            print(f"[VERIFICATION] Processing document {i+1}/{len(file_paths)}: {file_path}", flush=True)
            
            company_info = extract_company_info_from_first_page(file_path, api_key)
            if company_info and not isinstance(company_info, dict):
                # Handle case where extract_company_info_from_first_page returns None
                print(f"[VERIFICATION] Failed to extract info from document {i+1}", flush=True)
            elif company_info and company_info.get('error'):
                # Handle API errors from Anthropic
                error_type = company_info.get('error')
                error_message = company_info.get('message', 'Unknown API error')
                print(f"[VERIFICATION] API error for document {i+1}: {error_type} - {error_message}", flush=True)
                
                # If it's an overloaded error, return it immediately
                if error_type == 'anthropic_overloaded':
                    return {
                        'success': False,
                        'error': 'Anthropic API is currently overloaded. Please try again later.',
                        'error_type': 'anthropic_overloaded',
                        'extracted_info': None,
                        'existing_profile': None
                    }
                elif error_type == 'anthropic_rate_limited':
                    return {
                        'success': False,
                        'error': 'Anthropic API rate limit exceeded. Please try again later.',
                        'error_type': 'anthropic_rate_limited',
                        'extracted_info': None,
                        'existing_profile': None
                    }
                elif error_type == 'anthropic_auth_error':
                    return {
                        'success': False,
                        'error': 'Anthropic API key is invalid or expired. Please check your configuration.',
                        'error_type': 'anthropic_auth_error',
                        'extracted_info': None,
                        'existing_profile': None
                    }
                else:
                    return {
                        'success': False,
                        'error': f'API error: {error_message}',
                        'error_type': error_type,
                        'extracted_info': None,
                        'existing_profile': None
                    }
            elif company_info:
                # Valid company info extracted
                all_company_info.append(company_info)
                
                # Collect company names and fiscal years
                if company_info.get('company_name'):
                    company_names.add(company_info['company_name'].strip())
                if company_info.get('fiscal_year'):
                    fiscal_years.add(company_info['fiscal_year'])
                
                
            else:
                print(f"[VERIFICATION] Failed to extract info from document {i+1}", flush=True)
        
        if not all_company_info:
            # If no company info extracted but we have a fallback, use it
            if fallback_company_name:
                print(f"[VERIFICATION] No company info extracted, using fallback: {fallback_company_name}", flush=True)
                # Create a minimal company info with fallback name
                all_company_info = [{'company_name': fallback_company_name, 'fiscal_year': None}]
                company_names.add(fallback_company_name)
            else:
                return {
                    'success': False,
                    'error': 'Failed to extract company information from any document',
                    'extracted_info': None,
                    'existing_profile': None
                }
        
        # Step 2: Determine the primary company name and fiscal year range
        primary_company_name = None
        if len(company_names) == 1:
            # All documents show the same company name
            primary_company_name = list(company_names)[0]
        elif len(company_names) > 1:
            # Different company names detected - use the most common or first one
            # For now, use the first one and log a warning
            primary_company_name = list(company_names)[0]
            print(f"[VERIFICATION] Warning: Different company names detected: {company_names}. Using: {primary_company_name}", flush=True)
        elif len(company_names) == 0 and fallback_company_name:
            # No company names extracted but we have a fallback
            primary_company_name = fallback_company_name
            print(f"[VERIFICATION] No company names extracted, using fallback: {primary_company_name}", flush=True)
        
        # Create fiscal year range
        fiscal_year_range = None
        if fiscal_years:
            sorted_years = sorted(list(fiscal_years))
            if len(sorted_years) == 1:
                fiscal_year_range = str(sorted_years[0])
            else:
                # Create range like "2022-2023"
                fiscal_year_range = f"{sorted_years[0]}-{sorted_years[-1]}"
        
        
        
        if not primary_company_name:
            return {
                'success': False,
                'error': 'Could not extract company name from any document',
                'extracted_info': None,
                'existing_profile': None
            }
        
        # Step 3: Check if documents for this company already exist
        existing_profile = check_existing_documents(db, CompanyProfile, primary_company_name)
        
        # Step 4: Identify which documents are new vs existing
        # print(f"[VERIFICATION] Starting document analysis for {len(file_paths)} files", flush=True)
        document_analysis = identify_new_vs_existing_documents(db, CompanyProfile, file_paths, primary_company_name, all_company_info)
        
        print(f"[VERIFICATION] Document analysis result: {document_analysis['total_new']} new, {document_analysis['total_existing']} existing", flush=True)
        
        # Step 5: Determine if we should create a new profile or show existing one
        should_create_new = True
        if existing_profile:
            print(f"[VERIFICATION] Found existing profile with fiscal years: {existing_profile.get('fiscal_years')}", flush=True)
            should_create_new = should_create_new_profile(existing_profile, fiscal_year_range)
            
            if should_create_new:
                print(f"[VERIFICATION] Existing profile found but does not cover target fiscal years '{fiscal_year_range}' - will create new profile", flush=True)
                # Don't show existing profile since user wants a more comprehensive one
                existing_profile = None
            else:
                print(f"[VERIFICATION] Existing profile already covers target fiscal years '{fiscal_year_range}' - no new profile needed", flush=True)
        
        # Create combined extracted info
        combined_extracted_info = {
            'company_name': primary_company_name,
            'fiscal_year': fiscal_year_range,
            'document_count': len(file_paths),
            'individual_results': all_company_info,
            'document_analysis': document_analysis
        }
        
        return {
            'success': True,
            'extracted_info': combined_extracted_info,
            'existing_profile': existing_profile,
            'profile_exists': existing_profile is not None,
            'should_create_new': should_create_new,
            'document_analysis': document_analysis
        }
        
    except Exception as e:
        print(f"[VERIFICATION] Error in profile verification: {str(e)}", flush=True)
        return {
            'success': False,
            'error': f'Verification failed: {str(e)}',
            'extracted_info': None,
            'existing_profile': None
        }

def identify_new_vs_existing_documents(db, CompanyProfile, file_paths: list, company_name: str, all_company_info: list) -> Dict[str, Any]:
    """
    Identify which documents are new vs existing to avoid reprocessing.
    
    Args:
        db: Database session
        CompanyProfile: CompanyProfile model class
        file_paths: List of file paths to check
        company_name: Company name to search for
        
    Returns:
        Dict with new and existing document information
    """
    try:
        
        # Find existing profiles for this company
        existing_profiles = CompanyProfile.query.filter(
            CompanyProfile.company_name.ilike(f'%{company_name}%')
        ).all()
        
        existing_documents = []
        for profile in existing_profiles:
            # Get documents associated with this profile
            # Note: LiasseDocument model will be passed from the calling function
            # For now, we'll use a simple approach to avoid import issues
            try:
                # Try to get documents using the profile ID
                profile_docs = db.session.execute(
                    text("SELECT * FROM liasse_documents WHERE profile_id = :profile_id"),
                    {"profile_id": str(profile.id)}
                ).fetchall()
                
                print(f"[VERIFICATION] Found {len(profile_docs)} documents for profile {profile.id}", flush=True)
                
                for doc in profile_docs:
                    # Handle both SQLAlchemy Row objects and dict-like objects
                    if hasattr(doc, '_mapping'):
                        # SQLAlchemy 2.0 Row object
                        doc_dict = dict(doc._mapping)
                    elif hasattr(doc, '__dict__'):
                        # Regular object
                        doc_dict = doc.__dict__
                    else:
                        # Assume it's already a dict
                        doc_dict = doc
                    
                    existing_documents.append({
                        'profile_id': str(profile.id),
                        'fiscal_years': profile.fiscal_years,
                        'file_name': doc_dict.get('file_name'),
                        'file_path': doc_dict.get('file_path'),
                        'extracted_data': doc_dict.get('extracted_data')
                    })
                    
                    print(f"[VERIFICATION] Added document: {doc_dict.get('file_name')} with extracted_data: {doc_dict.get('extracted_data') is not None}", flush=True)
                    
            except Exception as e:
                print(f"[VERIFICATION] Warning: Could not fetch documents for profile {profile.id}: {e}", flush=True)
                # Try alternative approach - direct table access
                try:
                    from sqlalchemy import inspect
                    inspector = inspect(db.engine)
                    if 'liasse_documents' in inspector.get_table_names():
                        print(f"[VERIFICATION] Table 'liasse_documents' exists, trying direct query", flush=True)
                        # Fallback to a simpler query
                        result = db.session.execute(
                            text("SELECT file_name, file_path, extracted_data FROM liasse_documents WHERE profile_id = :profile_id"),
                            {"profile_id": str(profile.id)}
                        )
                        fallback_docs = result.fetchall()
                        print(f"[VERIFICATION] Fallback query found {len(fallback_docs)} documents", flush=True)
                        
                        for doc in fallback_docs:
                            existing_documents.append({
                                'profile_id': str(profile.id),
                                'fiscal_years': profile.fiscal_years,
                                'file_name': doc[0] if len(doc) > 0 else None,
                                'file_path': doc[1] if len(doc) > 1 else None,
                                'extracted_data': doc[2] if len(doc) > 2 else None
                            })
                    else:
                        print(f"[VERIFICATION] Table 'liasse_documents' does not exist", flush=True)
                except Exception as fallback_error:
                    print(f"[VERIFICATION] Fallback approach also failed: {fallback_error}", flush=True)
                continue
        
        print(f"[VERIFICATION] Found {len(existing_documents)} existing documents across {len(existing_profiles)} profiles", flush=True)
        
        # Debug: Log existing documents for troubleshooting
        for i, doc in enumerate(existing_documents):
            print(f"[VERIFICATION] Existing doc {i+1}: profile_id={doc.get('profile_id')}, filename={doc.get('file_name')}, fiscal_years={doc.get('fiscal_years')}", flush=True)
            if doc.get('extracted_data'):
                try:
                    extracted = doc['extracted_data']
                    if isinstance(extracted, str):
                        extracted = json.loads(extract_json_from_response(extracted))
                    print(f"[VERIFICATION]   Extracted data: company={extracted.get('company_name')}, fiscal_year={extracted.get('fiscal_year')}", flush=True)
                except Exception as e:
                    print(f"[VERIFICATION]   Could not parse extracted data: {e}", flush=True)
        
        # Calculate hashes for uploaded files to compare with existing ones
        new_documents = []
        existing_matches = []
        
        for i, file_path in enumerate(file_paths):
            file_hash = calculate_document_hash(file_path)
            if not file_hash:
                print(f"[VERIFICATION] Could not calculate hash for file {i+1}, treating as new", flush=True)
                new_documents.append({
                    'index': i,
                    'file_path': file_path,
                    'reason': 'hash_calculation_failed'
                })
                continue
            
            # Check if this document already exists
            is_existing = False
            for existing_doc in existing_documents:
                # Check multiple criteria for matching:
                # 1. File name match (exact)
                # 2. Company name and fiscal year match (content-based)
                # 3. File hash match (if available)
                
                # File name matching
                if existing_doc.get('file_name') and os.path.basename(file_path) == existing_doc['file_name']:
                    print(f"[VERIFICATION] Document {i+1} matches existing document by filename: {existing_doc['file_name']}", flush=True)
                    existing_matches.append({
                        'index': i,
                        'file_path': file_path,
                        'existing_data': existing_doc,
                        'reason': 'file_name_match'
                    })
                    is_existing = True
                    break
                
                # Content-based matching (company name + fiscal year)
                # This helps catch cases where the same document might have different filenames
                if existing_doc.get('extracted_data'):
                    try:
                        existing_extracted = existing_doc['extracted_data']
                        if isinstance(existing_extracted, str):
                            existing_extracted = json.loads(extract_json_from_response(existing_extracted))
                        
                        # Check if company names are similar
                        existing_company = existing_extracted.get('company_name', '').strip().lower()
                        current_company = company_name.strip().lower()
                        
                        # Simple similarity check (you could make this more sophisticated)
                        if (existing_company in current_company or 
                            current_company in existing_company or
                            existing_company.replace(' ', '') == current_company.replace(' ', '')):
                            
                            # Check if fiscal years match
                            existing_fiscal = existing_extracted.get('fiscal_year')
                            if existing_fiscal:
                                # Get the current document's fiscal year from the already extracted info
                                current_doc_info = all_company_info[i] if i < len(all_company_info) else None
                                if current_doc_info and current_doc_info.get('fiscal_year') == existing_fiscal:
                                    print(f"[VERIFICATION] Document {i+1} matches existing document by content: company={existing_company}, fiscal_year={existing_fiscal}", flush=True)
                                    existing_matches.append({
                                        'index': i,
                                        'file_path': file_path,
                                        'existing_data': existing_doc,
                                        'reason': 'content_match'
                                    })
                                    is_existing = True
                                    break
                    except Exception as e:
                        print(f"[VERIFICATION] Warning: Error checking content match: {e}", flush=True)
                        continue
            
            if not is_existing:
                print(f"[VERIFICATION] Document {i+1} is new: {os.path.basename(file_path)}", flush=True)
                new_documents.append({
                    'index': i,
                    'file_path': file_path,
                    'reason': 'new_document'
                })
        
        result = {
            'new_documents': new_documents,
            'existing_matches': existing_matches,
            'total_new': len(new_documents),
            'total_existing': len(existing_matches)
        }
        
        
        return result
        
    except Exception as e:
        print(f"[VERIFICATION] Error identifying new vs existing documents: {str(e)}", flush=True)
        # Fallback: treat all documents as new
        return {
            'new_documents': [{'index': i, 'file_path': path, 'reason': 'error_fallback'} for i, path in enumerate(file_paths)],
            'existing_matches': [],
            'total_new': len(file_paths),
            'total_existing': 0
        }

def compare_company_names(profile_company_name: str, document_company_names: list) -> Dict[str, Any]:
    """
    Compare company names from uploaded documents with the profile's company name.
    
    Args:
        profile_company_name (str): The company name from the profile
        document_company_names (list): List of company names extracted from documents
        
    Returns:
        Dict containing comparison results and recommendations
    """
    try:
        
        if not profile_company_name or not document_company_names:
            return {
                'match': False,
                'reason': 'Missing company name data',
                'requires_confirmation': False,
                'profile_company': profile_company_name,
                'document_companies': document_company_names,
                'recommendation': 'Cannot compare company names due to missing data'
            }
        
        # Clean and normalize company names for comparison
        profile_clean = _normalize_company_name(profile_company_name)
        document_clean_list = [_normalize_company_name(name) for name in document_company_names if name]
        
        print(f"[VERIFICATION] Normalized names - Profile: '{profile_clean}', Documents: {document_clean_list}", flush=True)
        
        # Check for exact matches
        exact_matches = [name for name in document_clean_list if name == profile_clean]
        
        if exact_matches:
            return {
                'match': True,
                'reason': 'Exact company name match found',
                'requires_confirmation': False,
                'profile_company': profile_company_name,
                'document_companies': document_company_names,
                'recommendation': 'Company names match - safe to proceed'
            }
        
        # Check for partial matches (one company name contains the other)
        partial_matches = []
        for doc_name in document_clean_list:
            if (doc_name in profile_clean or profile_clean in doc_name) and len(doc_name) > 3 and len(profile_clean) > 3:
                partial_matches.append(doc_name)
        
        if partial_matches:
            return {
                'match': True,
                'reason': 'Partial company name match found',
                'requires_confirmation': True,
                'profile_company': profile_company_name,
                'document_companies': document_company_names,
                'partial_matches': partial_matches,
                'recommendation': 'Partial company name match - recommend user confirmation'
            }
        
        # Check for similar names using fuzzy matching
        similar_names = []
        for doc_name in document_clean_list:
            similarity = _calculate_name_similarity(profile_clean, doc_name)
            if similarity > 0.7:  # 70% similarity threshold
                similar_names.append((doc_name, similarity))
        
        if similar_names:
            # Sort by similarity
            similar_names.sort(key=lambda x: x[1], reverse=True)
            return {
                'match': False,
                'reason': 'Similar company names found',
                'requires_confirmation': True,
                'profile_company': profile_company_name,
                'document_companies': document_company_names,
                'similar_names': similar_names,
                'recommendation': f'Similar company names detected (best match: {similar_names[0][0]} with {similar_names[0][1]:.1%} similarity) - requires user confirmation'
            }
        
        # No matches found
        return {
            'match': False,
            'reason': 'No company name matches found',
            'requires_confirmation': True,
            'profile_company': profile_company_name,
            'document_companies': document_company_names,
            'recommendation': 'Different company names detected - requires user confirmation before proceeding'
        }
        
    except Exception as e:
        print(f"[VERIFICATION] Error comparing company names: {str(e)}", flush=True)
        return {
            'match': False,
            'reason': f'Error during comparison: {str(e)}',
            'requires_confirmation': True,
            'profile_company': profile_company_name,
            'document_companies': document_company_names,
            'recommendation': 'Error during company name comparison - recommend user confirmation'
        }

def _normalize_company_name(company_name: str) -> str:
    """
    Normalize company name for comparison by removing common suffixes and formatting.
    
    Args:
        company_name (str): Raw company name
        
    Returns:
        str: Normalized company name
    """
    if not company_name:
        return ""
    
    # Convert to uppercase and remove extra whitespace
    normalized = company_name.strip().upper()
    
    # Remove common legal suffixes including Moroccan company types
    suffixes_to_remove = [
        'S.A.', 'SA', 'SARL', 'SARLAU', 'SAS', 'SASU', 'EURL', 'SNC', 'SCA', 'SCS',
        'SOCIETE ANONYME', 'SOCIETE A RESPONSABILITE LIMITEE',
        'SOCIETE EN NOM COLLECTIF', 'SOCIETE EN COMMANDITE SIMPLE',
        'SOCIETE EN COMMANDITE PAR ACTIONS',
        # Moroccan specific company types
        'SARLAU', 'SARL', 'SA', 'S.A', 'S.A.', 'SOCIETE ANONYME',
        'SOCIETE A RESPONSABILITE LIMITEE', 'SOCIETE A RESPONSABILITE LIMITEE UNIPERSONNELLE',
        'SOCIETE EN NOM COLLECTIF', 'SOCIETE EN COMMANDITE SIMPLE',
        'SOCIETE EN COMMANDITE PAR ACTIONS', 'SOCIETE CIVILE',
        'SOCIETE CIVILE IMMOBILIERE', 'SOCIETE CIVILE PROFESSIONNELLE',
        'GROUPEMENT D INTERET ECONOMIQUE', 'GIE',
        'ETABLISSEMENT PUBLIC', 'EP', 'ETABLISSEMENT PUBLIC A CARACTERE INDUSTRIEL ET COMMERCIAL',
        'EPIC', 'ETABLISSEMENT PUBLIC A CARACTERE ADMINISTRATIF', 'EPA',
        'COOPERATIVE', 'COOP', 'MUTUELLE', 'ASSOCIATION', 'FONDATION'
    ]
    
    for suffix in suffixes_to_remove:
        # Remove suffix at the end of the string (with optional spaces)
        pattern = r'\s*' + re.escape(suffix) + r'\s*$'
        normalized = re.sub(pattern, '', normalized, flags=re.IGNORECASE)
    
    # Remove common punctuation and extra spaces
    normalized = re.sub(r'[^\w\s]', ' ', normalized)
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    
    return normalized

def _calculate_name_similarity(name1: str, name2: str) -> float:
    """
    Calculate similarity between two company names using simple character-based comparison.
    
    Args:
        name1 (str): First company name
        name2 (str): Second company name
        
    Returns:
        float: Similarity score between 0.0 and 1.0
    """
    if not name1 or not name2:
        return 0.0
    
    # Convert to sets of characters for comparison
    chars1 = set(name1.lower())
    chars2 = set(name2.lower())
    
    if not chars1 or not chars2:
        return 0.0
    
    # Calculate Jaccard similarity
    intersection = len(chars1.intersection(chars2))
    union = len(chars1.union(chars2))
    
    if union == 0:
        return 0.0
    
    return intersection / union
