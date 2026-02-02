import os
import re
import json
import base64
from tempfile import TemporaryDirectory
import anthropic
from typing import Any
from datetime import datetime, timezone
import fitz  # PyMuPDF
import time
import sys

# Import the new logging system
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.logger import log_processing, log_success, log_error, log_warning, log_cleanup, log_database, log_info

def is_document_already_processed(document, required_fields=None) -> bool:
    """Check if a document has already been processed and has valid extracted data.
    
    Args:
        document: LiasseDocument instance
        required_fields: List of required fields in extracted_data. 
                        Defaults to ['fiscal_year', 'kpis']
    
    Returns:
        bool: True if document is already processed with valid data
    """
    if required_fields is None:
        required_fields = ['fiscal_year', 'kpis']
    
    if not document.extracted_data:
        return False
    
    if not isinstance(document.extracted_data, dict):
        return False
    
    # Check if all required fields are present and non-empty
    for field in required_fields:
        if field not in document.extracted_data:
            return False
        
        field_value = document.extracted_data[field]
        if field_value is None:
            return False
        
        # For kpis, check if it's a non-empty dict
        if field == 'kpis' and (not isinstance(field_value, dict) or len(field_value) == 0):
            return False
    
    # Check if processing timestamp exists and is recent (optional validation)
    if 'processing_timestamp' in document.extracted_data:
        try:
            from datetime import datetime, timedelta
            timestamp_str = document.extracted_data['processing_timestamp']
            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            # Consider data valid if processed within last 30 days
            if datetime.utcnow() - timestamp.replace(tzinfo=None) > timedelta(days=30):
                print(f"Document {document.file_name} has old processed data (>30 days), will reprocess", flush=True)
                return False
        except Exception:
            # If timestamp parsing fails, still consider valid if other fields are present
            pass
    
    return True

def cleanup_profile_files(profile_id: str, upload_folder: str, db, LiasseDocument) -> None:
    """Delete all uploaded PDF and markdown files for a profile to save server space.
    
    The important JSON data is preserved in the database.
    """
    try:
        # Get all documents for this profile
        documents = LiasseDocument.query.filter_by(profile_id=profile_id).all()
        deleted_files = []
        
        for document in documents:
            if document.file_path and os.path.exists(document.file_path):
                try:
                    os.remove(document.file_path)
                    deleted_files.append(document.file_path)
                    log_cleanup(f"Deleted PDF file: {document.file_path}")
                except Exception as e:
                    print(f"⚠️ Failed to delete PDF file {document.file_path}: {e}", flush=True)
        
        # Delete markdown file if it exists
        markdown_path = os.path.join(upload_folder, f"{profile_id}_final.md")
        if os.path.exists(markdown_path):
            try:
                os.remove(markdown_path)
                deleted_files.append(markdown_path)
                log_cleanup(f"Deleted markdown file: {markdown_path}")
            except Exception as e:
                print(f"⚠️ Failed to delete markdown file {markdown_path}: {e}", flush=True)
        
        if deleted_files:
            log_success(f"Cleaned up {len(deleted_files)} files for profile {profile_id} - JSON data preserved in database")
        else:
            log_info(f"No files to clean up for profile {profile_id}")
            
    except Exception as e:
        log_error(f"Error during file cleanup for profile {profile_id}: {e}")

def process_doc_processing(flask_app, db, CompanyProfile, LiasseDocument, profile_id: str) -> None:
    """Process all documents for a profile in a background thread.

    Uses the provided Flask app to create an app context, converts PDFs to
    Markdown via Claude, extracts KPIs, and updates the profile.
    Files are automatically deleted after processing to save server space.
    """
    
    def log_progress(message: str, update_db: bool = True):
        """Log progress messages with timestamp"""
        log_processing(profile_id, message)
        
        if update_db:
            try:
                current_data = profile.profile_data or {}
                if 'processing_log' not in current_data:
                    current_data['processing_log'] = []
                current_data['processing_log'].append({
                    'timestamp': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
                    'message': message
                })
                # Keep only last 20 log entries
                current_data['processing_log'] = current_data['processing_log'][-20:]
                profile.profile_data = current_data
                db.session.commit()
            except Exception as e:
                log_error(f"Failed to update log in DB: {e}")
    
    log_info(f"Starting document processing for profile {profile_id}")
    
    with flask_app.app_context():
        profile = CompanyProfile.query.get(profile_id)
        if not profile:
            log_error(f"Profile {profile_id} not found!")
            return

        log_progress("Background processing thread started")
        
        api_key = flask_app.config.get('ANTHROPIC_API_KEY')
        model_name = flask_app.config.get('MODEL')
        pages_per_chunk = flask_app.config.get('PAGES_PER_CHUNK')
        upload_folder = flask_app.config.get('UPLOAD_FOLDER')
        
        log_progress(f"Configuration loaded - Model: {model_name}, Pages per chunk: {pages_per_chunk}")

        # Mark run start in profile_data for observability
        try:
            current_data = profile.profile_data or {}
            current_data['last_run_started_at'] = datetime.utcnow().isoformat()
            current_data.pop('error', None)
            current_data['processing_stage'] = 'initializing'
            profile.profile_data = current_data
            db.session.commit()
            log_progress("Processing initialized", update_db=False)
        except Exception as e:
            db.session.rollback()
            log_progress(f"Failed to initialize processing: {e}")

        if not api_key:
            log_progress("ERROR: Anthropic API key not configured")
            _update_profile_failure(db, profile, 'Anthropic not configured')
            return
        if not fitz:
            log_progress("ERROR: PyMuPDF (fitz) not installed")
            _update_profile_failure(db, profile, 'PyMuPDF (fitz) not installed')
            return

        try:
            # Wait briefly for documents if they are being uploaded right after profile creation
            wait_seconds = flask_app.config.get('WAIT_FOR_DOCS_SECONDS')
            log_progress(f"Waiting up to {wait_seconds} seconds for documents...")
            
            # Update processing stage
            current_data = profile.profile_data or {}
            current_data['processing_stage'] = 'waiting_for_documents'
            profile.profile_data = current_data
            db.session.commit()
            
            documents = []
            start_time = datetime.utcnow()
            while (datetime.utcnow() - start_time).total_seconds() < wait_seconds:
                documents = LiasseDocument.query.filter_by(profile_id=profile_id).all()
                if documents:
                    log_progress(f"Found {len(documents)} documents to process")
                    break
                time.sleep(1)
                
            if not documents:
                log_progress("ERROR: No documents found to process")
                _update_profile_failure(db, profile, 'No documents to process')
                return

            # Update processing stage
            current_data = profile.profile_data or {}
            current_data['processing_stage'] = 'processing_documents'
            current_data['total_documents'] = len(documents)
            profile.profile_data = current_data
            db.session.commit()

            log_progress("Initializing Claude client...")
            try:
                client = anthropic.Anthropic(api_key=api_key)
                log_progress("✅ Claude client initialized successfully")
            except Exception as e:
                log_progress(f"❌ Claude client failed: {str(e)}")
                raise e

            combined_markdown_parts = []

            # Process documents individually to extract KPIs per document
            document_kpis_list = []
            
            # Use a temporary directory for chunk files
            with TemporaryDirectory() as temp_dir:
                for i, document in enumerate(documents):
                    log_progress(f"Processing document {i+1}/{len(documents)}: {document.file_name}")
                    
                    # Check if document is already processed
                    if is_document_already_processed(document):
                        log_progress(f"✅ Document {document.file_name} already processed, using existing data")
                        
                        # Use existing extracted data
                        existing_data = document.extracted_data
                        existing_data['document_name'] = document.file_name
                        document_kpis_list.append(existing_data)
                        
                        # Still add to combined markdown for potential fallback processing
                        combined_markdown_parts.append(f"# Document: {document.file_name}\n\n[Already processed - using cached data]")
                        
                        # Check if TVA data exists in cached data, if not, force re-extraction
                        if 'tva_data' not in existing_data:
                            print(f"[TVA DEBUG] Document {document.file_name} cached but missing TVA data, forcing TVA re-extraction", flush=True)
                            # We'll force TVA extraction for this document even if it's cached
                            force_tva_extraction = True
                        else:
                            print(f"[TVA DEBUG] Document {document.file_name} has cached TVA data: {existing_data.get('tva_data')}", flush=True)
                            force_tva_extraction = False
                        
                        # Mark as processed
                        document.ocr_status = 'done'
                        db.session.add(document)
                        
                        if not force_tva_extraction:
                            continue
                    else:
                        force_tva_extraction = False
                    
                    # Update processing stage
                    current_data = profile.profile_data or {}
                    current_data['processing_stage'] = f'processing_document_{i+1}_of_{len(documents)}'
                    current_data['current_document'] = document.file_name
                    profile.profile_data = current_data
                    db.session.commit()
                    
                    # Only do full document processing if not using cached data
                    if not is_document_already_processed(document) or force_tva_extraction:
                        if force_tva_extraction:
                            log_progress(f"🔄 Re-extracting TVA data from cached document {document.file_name}...")
                        else:
                            log_progress(f"🔄 Processing new/updated document {document.file_name}...")
                        
                        chunk_paths = _chunk_pdf_files(document.file_path, output_dir=temp_dir, pages_per_chunk=pages_per_chunk)
                        log_progress(f"Document split into {len(chunk_paths)} chunks")
                        # print(f"DEBUG: Created {len(chunk_paths)} chunks for {document.file_name}", flush=True)
                        
                        md_parts = []
                        for j, chunk_path in enumerate(chunk_paths):
                            print(f"DEBUG: Processing chunk {j+1}/{len(chunk_paths)}", flush=True)
                            log_progress(f"Converting chunk {j+1}/{len(chunk_paths)} with Claude...")
                            md = _convert_chunk_with_claude(client, chunk_path, model_name)
                            md_parts.append(md)
                            
                        final_md = '\n\n'.join(md_parts)
                        combined_markdown_parts.append(f"# Document: {document.file_name}\n\n{final_md}")
                    else:
                        # Use empty final_md for cached documents that don't need TVA extraction
                        final_md = ""
                    
                    # Extract KPIs from this individual document (only if not cached or forcing TVA extraction)
                    if not is_document_already_processed(document) or force_tva_extraction:
                        if not force_tva_extraction:
                            log_progress(f"Extracting KPIs from document {document.file_name}...")
                            try:
                                document_kpis_raw = _extract_kpis_from_single_document(client, final_md, model_name, document.file_name)
                                document_kpis_json = _safe_parse_json(document_kpis_raw)
                                
                                if document_kpis_json:
                                    # Add document name to the KPIs for later mapping
                                    document_kpis_json['document_name'] = document.file_name
                                    document_kpis_list.append(document_kpis_json)
                                    log_progress(f"Successfully extracted KPIs from {document.file_name} (fiscal year: {document_kpis_json.get('fiscal_year', 'unknown')})")
                                else:
                                    log_progress(f"Failed to parse KPIs from {document.file_name}, storing raw response")
                                    document_kpis_list.append({'document_name': document.file_name, 'raw_response': document_kpis_raw})
                                    
                            except Exception as kpi_error:
                                log_progress(f"Error extracting KPIs from {document.file_name}: {str(kpi_error)}")
                                document_kpis_list.append({'document_name': document.file_name, 'error': str(kpi_error)})
                        
                        # Extract TVA data from this individual document
                        log_progress(f"Extracting TVA data from document {document.file_name}...")
                        try:
                            document_tva_raw = _extract_tva_data_from_single_document(client, final_md, model_name, document.file_name)
                            print(f"[TVA DEBUG] Raw TVA response for {document.file_name}: {document_tva_raw[:500]}...", flush=True)
                            
                            document_tva_json = _safe_parse_json(document_tva_raw)
                            print(f"[TVA DEBUG] Parsed TVA JSON for {document.file_name}: {document_tva_json}", flush=True)
                            
                            if document_tva_json and 'tva_data' in document_tva_json:
                                # Add TVA data to the document KPIs (find existing or create new entry)
                                doc_found = False
                                for doc_kpis in document_kpis_list:
                                    if doc_kpis.get('document_name') == document.file_name:
                                        doc_kpis['tva_data'] = document_tva_json['tva_data']
                                        print(f"[TVA DEBUG] Added TVA data to existing document KPIs: {document_tva_json['tva_data']}", flush=True)
                                        doc_found = True
                                        break
                                
                                # If document not found in document_kpis_list (cached case), create entry
                                if not doc_found:
                                    new_doc_entry = {
                                        'document_name': document.file_name,
                                        'tva_data': document_tva_json['tva_data'],
                                        'fiscal_year': document_tva_json.get('fiscal_year', 'unknown')
                                    }
                                    document_kpis_list.append(new_doc_entry)
                                    print(f"[TVA DEBUG] Created new document entry with TVA data: {new_doc_entry}", flush=True)
                                
                                log_progress(f"Successfully extracted TVA data from {document.file_name}")
                            else:
                                log_progress(f"No TVA data found in {document.file_name}")
                                print(f"[TVA DEBUG] No TVA data structure found. Raw response: {document_tva_raw}", flush=True)
                                
                        except Exception as tva_error:
                            log_progress(f"Error extracting TVA data from {document.file_name}: {str(tva_error)}")
                            print(f"[TVA DEBUG] Exception during TVA extraction: {tva_error}", flush=True)
                    
                    # Mark as processed
                    document.ocr_status = 'done'
                    db.session.add(document)
                    log_progress(f"Document {document.file_name} processed successfully")

            log_progress("Combining all documents into final markdown...")
            combined_markdown = '\n\n---\n\n'.join(combined_markdown_parts)

            # Update processing stage
            current_data = profile.profile_data or {}
            current_data['processing_stage'] = 'saving_markdown'
            profile.profile_data = current_data
            db.session.commit()

            # Ensure upload directory exists
            os.makedirs(upload_folder, exist_ok=True)

            # Optionally save markdown to disk for auditing
            output_md_path = os.path.join(upload_folder, f"{profile_id}_final.md")
            try:
                with open(output_md_path, 'w', encoding='utf-8') as f:
                    f.write(combined_markdown)
                log_progress(f"Markdown saved to {output_md_path}")
            except Exception as e:
                log_progress(f"Failed to save markdown: {e}")
                output_md_path = None

            # Update processing stage
            current_data = profile.profile_data or {}
            current_data['processing_stage'] = 'extracting_kpis'
            profile.profile_data = current_data
            db.session.commit()

            # Use multi-document KPI processing if we have multiple documents, otherwise fallback to combined markdown
            if len(documents) > 1 and document_kpis_list:
                log_progress(f"Using multi-document KPI processing for {len(documents)} documents...")
                kpis_json = _process_multi_document_kpis(client, document_kpis_list, model_name, log_progress)
                
                if kpis_json:
                    if '_metadata' in kpis_json:
                        total_years = len(kpis_json['_metadata'].get('available_years', []))
                        log_progress(f"Successfully processed multi-document KPIs with {total_years} years of data")
                    else:
                        log_progress("Successfully processed KPIs from primary document (fallback mode)")
                else:
                    log_progress("Multi-document KPI processing failed, falling back to combined markdown")
                    kpis_raw = _extract_kpis_from_markdown(client, combined_markdown, model_name)
                    kpis_json = _safe_parse_json(kpis_raw)
            else:
                log_progress("Using single-document processing (combined markdown)...")
                kpis_raw = _extract_kpis_from_markdown(client, combined_markdown, model_name)
                kpis_json = _safe_parse_json(kpis_raw)
                
                if kpis_json:
                    log_progress(f"Successfully extracted {len(kpis_json)} KPIs from combined markdown")
                else:
                    log_progress("Failed to parse KPIs as JSON, storing raw response")

            # Compute financial ratios from extracted KPIs
            log_progress("Computing financial ratios from KPIs...")
            computed_ratios = _compute_financial_ratios(kpis_json)
            log_progress(f"Computed {len(computed_ratios)} financial ratios")
            
            # Compute TVA analysis from document data
            log_progress("Computing TVA analysis from document data...")
            print(f"[TVA DEBUG] Document KPIs list length: {len(document_kpis_list)}", flush=True)
            
            tva_analysis = {}
            if document_kpis_list:
                for i, doc_kpis in enumerate(document_kpis_list):
                    print(f"[TVA DEBUG] Document {i}: {doc_kpis.get('document_name', 'unknown')}", flush=True)
                    print(f"[TVA DEBUG] Document {i} keys: {list(doc_kpis.keys())}", flush=True)
                    
                    if 'tva_data' in doc_kpis and doc_kpis['tva_data']:
                        print(f"[TVA DEBUG] Found TVA data in document {i}: {doc_kpis['tva_data']}", flush=True)
                        
                        doc_tva_analysis = _compute_tva_analysis(doc_kpis['tva_data'])
                        print(f"[TVA DEBUG] Computed TVA analysis for document {i}: {doc_tva_analysis}", flush=True)
                        
                        if doc_tva_analysis:
                            # Use the fiscal year as key or document name if multiple documents
                            fiscal_year = doc_kpis.get('fiscal_year', 'unknown')
                            tva_analysis[f"tva_analysis_{fiscal_year}"] = doc_tva_analysis
                            log_progress(f"Computed TVA analysis for fiscal year {fiscal_year}")
                            print(f"[TVA DEBUG] Added to tva_analysis with key: tva_analysis_{fiscal_year}", flush=True)
                        else:
                            print(f"[TVA DEBUG] TVA analysis computation returned empty result for document {i}", flush=True)
                    else:
                        print(f"[TVA DEBUG] No TVA data found in document {i}", flush=True)
            
            print(f"[TVA DEBUG] Final TVA analysis keys: {list(tva_analysis.keys())}", flush=True)
            print(f"[TVA DEBUG] Final TVA analysis content: {tva_analysis}", flush=True)
            
            if tva_analysis:
                log_progress(f"Computed TVA analysis for {len(tva_analysis)} documents")
            else:
                log_progress("No TVA data found for analysis")
            
            # Update profile - refresh from DB to avoid stale data
            db.session.refresh(profile)
            current_data = profile.profile_data or {}
            
            # Store both extracted KPIs and computed ratios
            # Preserve the original nested structure for extracted_kpis
            if kpis_json is not None:
                # Remove metadata before saving to database to keep it clean
                clean_kpis = {k: v for k, v in kpis_json.items() if k != '_metadata'}
                current_data['extracted_kpis'] = clean_kpis
            else:
                current_data['extracted_kpis'] = {'raw': kpis_raw if 'kpis_raw' in locals() else 'No raw data available'}
            current_data['computed_ratios'] = computed_ratios
            current_data['tva_analysis'] = tva_analysis
            current_data['company_name'] = profile.company_name
            
            print(f"[TVA DEBUG] Saving to profile_data - TVA analysis keys: {list(tva_analysis.keys()) if tva_analysis else 'None'}", flush=True)
            print(f"[TVA DEBUG] TVA analysis being saved: {tva_analysis}", flush=True)
            current_data['processing_stage'] = 'completed'
            if output_md_path:
                current_data['markdown_path'] = output_md_path
            
            # Store individual document KPIs for reference (useful for debugging and frontend display)
            if document_kpis_list:
                current_data['individual_document_kpis'] = document_kpis_list
                log_progress(f"Stored individual KPIs from {len(document_kpis_list)} documents")
            
            # Update the profile's fiscal_years field to include all processed years
            try:
                fiscal_years = []
                
                # Get fiscal years from extracted KPIs metadata
                if kpis_json and '_metadata' in kpis_json:
                    metadata_years = kpis_json['_metadata'].get('fiscal_years', [])
                    fiscal_years.extend(metadata_years)
                
                # Also get from individual document KPIs as backup
                if document_kpis_list:
                    for doc_kpis in document_kpis_list:
                        if isinstance(doc_kpis, dict) and 'fiscal_year' in doc_kpis:
                            year = doc_kpis['fiscal_year']
                            if year and year not in fiscal_years:
                                fiscal_years.append(year)
                
                if fiscal_years:
                    # Sort years and create a range string
                    fiscal_years = sorted(list(set(fiscal_years)))  # Remove duplicates and sort
                    if len(fiscal_years) == 1:
                        profile.fiscal_years = str(fiscal_years[0])
                    else:
                        # Create a range like "2022-2023" for multiple years
                        profile.fiscal_years = f"{min(fiscal_years)}-{max(fiscal_years)}"
                    
                    log_progress(f"Updated profile fiscal_years to: {profile.fiscal_years}")
                
            except Exception as fiscal_year_error:
                log_progress(f"Warning: Could not update fiscal_years field: {fiscal_year_error}")
            
            # Web exploring is handled separately in app.py
                            # Only create minimal web data structure if none exists
                if 'web_data' not in current_data or not current_data['web_data']:
                    log_progress("Creating minimal web data structure (no existing web data found)")
                    current_data['web_data'] = {
                        'basic_info': {
                            'companyOverview': {
                                'companyFoundationyear': 'Non spécifié',
                                'companyExpertise': 'À déterminer',
                                'primary_sector': 'Secteur général',
                                'legal_form': 'SARL',
                                'companyDefinition': f'Entreprise {profile.company_name} - informations à compléter',
                                'staff_count': 'À préciser'
                            },
                            'sectors': [],
                            'markets': [],
                            'keyPeople': [],
                            'contact': {
                                'phone': 'Non disponible',
                                'email': 'Non disponible', 
                                'address': 'Adresse à préciser',
                                'website': 'Non disponible'
                            }
                        },
                        'news': 'Informations sectorielles à rechercher manuellement.'
                    }
                else:
                    log_progress("Preserving existing web data (found existing web exploration results)")
                    # Log what we're preserving
                    existing_web_data = current_data.get('web_data', {})
                    if isinstance(existing_web_data, dict):
                        news_len = len(existing_web_data.get('news', ''))
                        log_progress(f"Preserving web data - news: {news_len} chars")
            
            profile.profile_data = current_data
            # Don't set status to 'completed' here - let the calling function handle it
            # after financial analysis is complete
            profile.status = 'processing'  # Keep as processing until financial analysis is done
            
            log_progress("Saving profile data to database...")
            
            # Save the data directly
            try:
                profile.profile_data = current_data
                db.session.commit()
                db.session.flush()
                
                # Save individual document KPIs and metadata to each liasse document
                log_progress("Saving individual document KPIs and metadata to liasse documents...")
                if document_kpis_list:
                    documents = LiasseDocument.query.filter_by(profile_id=profile_id).all()
                    
                    # Create a mapping of document names to their KPIs
                    doc_name_to_kpis = {}
                    for doc_kpis in document_kpis_list:
                        if isinstance(doc_kpis, dict) and 'document_name' in doc_kpis:
                            doc_name_to_kpis[doc_kpis['document_name']] = doc_kpis
                    
                    # Save individual metadata to each document
                    for document in documents:
                        if document.file_name in doc_name_to_kpis:
                            individual_data = doc_name_to_kpis[document.file_name]
                            
                            # Create individual document metadata
                            individual_metadata = {
                                'fiscal_year': individual_data.get('fiscal_year'),
                                'document_name': document.file_name,
                                'kpis': individual_data.get('kpis', {}),
                                'processing_timestamp': datetime.utcnow().isoformat(),
                                'extracted_from_multi_doc_processing': len(documents) > 1
                            }
                            
                            document.extracted_data = individual_metadata
                            db.session.add(document)
                            log_progress(f"Saved individual metadata for {document.file_name} (fiscal year: {individual_data.get('fiscal_year')})")
                        else:
                            log_progress(f"⚠️ No individual KPIs found for {document.file_name}")
                    
                    db.session.commit()
                    log_progress(f"✅ Individual KPIs and metadata saved to {len(documents)} liasse documents")
                else:
                    log_progress("⚠️ No individual document KPIs to save to liasse documents")
                    
            except Exception as save_error:
                log_progress(f"Error during save: {save_error}")
                db.session.rollback()
                raise save_error
            
            # Verify the data was saved by re-querying
            verification_profile = CompanyProfile.query.get(profile_id)
            verification_data = verification_profile.profile_data or {}
            if not verification_data.get('extracted_kpis') or not verification_data.get('computed_ratios'):
                log_progress("⚠️ Warning: Some data may not have been saved properly")
            
            log_progress("✅ Processing completed successfully!")
            
            # Clean up uploaded files after successful processing to save server space
            log_progress("Cleaning up uploaded files (JSON data preserved in database)...")
            cleanup_profile_files(profile_id, upload_folder, db, LiasseDocument)
            
        except Exception as e:
            log_progress(f"❌ ERROR: {str(e)}")
            _update_profile_failure(db, profile, str(e))
        finally:
            try:
                # Mark run finish time regardless of outcome - refresh profile first to get latest data
                db.session.refresh(profile)
                current_data = profile.profile_data or {}
                current_data['last_run_finished_at'] = datetime.utcnow().isoformat()
                if 'processing_stage' not in current_data or current_data['processing_stage'] != 'completed':
                    current_data['processing_stage'] = 'failed'
                profile.profile_data = current_data
                db.session.commit()
                log_progress("Processing thread finished")
                
                # Final verification - only log if there's an issue
                final_profile = CompanyProfile.query.get(profile_id)
                final_data = final_profile.profile_data or {}
                if not final_data:
                    log_progress("⚠️ Final check - profile_data is empty!")
                elif not final_data.get('extracted_kpis') or not final_data.get('computed_ratios'):
                    log_progress("⚠️ Final check - Some data missing from DB")
            except Exception as e:
                print(f"[PROCESSING {profile_id}] Failed to update finish time: {e}", flush=True)
                db.session.rollback()

def _update_profile_failure(db, profile: Any, reason: str) -> None:
    profile.status = 'failed'
    current_data = profile.profile_data or {}
    current_data['error'] = reason
    current_data['last_error_at'] = datetime.utcnow().isoformat()
    profile.profile_data = current_data
    db.session.commit()

def _chunk_pdf_files(pdf_path: str, output_dir: str, pages_per_chunk: int = 1, max_pages: int = 25) -> list:
    """Split a PDF into temporary chunk files stored in output_dir.
    Only processes the first max_pages pages of the PDF."""
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    pages_to_process = min(total_pages, max_pages)
    
    print(f"PDF has {total_pages} pages, processing first {pages_to_process} pages", flush=True)
    
    chunk_files = []
    for start in range(0, pages_to_process, pages_per_chunk):
        pdf_writer = fitz.open()
        end = min(start + pages_per_chunk - 1, pages_to_process - 1)
        pdf_writer.insert_pdf(doc, from_page=start, to_page=end)
        base_name = os.path.splitext(os.path.basename(pdf_path))[0]
        chunk_path = os.path.join(output_dir, f"{base_name}_chunk_{start // pages_per_chunk + 1}.pdf")
        pdf_writer.save(chunk_path)
        chunk_files.append(chunk_path)
        print(f"DEBUG: Created chunk {len(chunk_files)}: {chunk_path} (pages {start}-{end})", flush=True)
    
    doc.close()
    return chunk_files

def _convert_chunk_with_claude(client: 'anthropic.Anthropic', chunk_path: str, model_name: str) -> str:
    """Send a PDF chunk to Claude and return exhaustive Markdown."""
    try:
        with open(chunk_path, 'rb') as f:
            pdf_base64 = base64.b64encode(f.read()).decode('utf-8')

        prompt = (
            "Tu es un analyste financier expert en liasses fiscales marocaines. "
            "Analyse le PDF fourni et convertis 100 % du contenu en Markdown exhaustif.\n\n"
            "Règles :\n"
            "1. Aucun texte ou tableau ne doit être omis.\n"
            "2. Tous les tableaux doivent être complets.\n"
            "3. Ne pas résumer.\n"
            "4. Conserver la structure originale.\n"
            "5. Retourner uniquement le Markdown.\n"
            "6. Inclure l'intégralité du contenu de ce chunk PDF."
        )

        message = client.messages.create(
            model=model_name,
            max_tokens=8192,
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
                        {'type': 'text', 'text': prompt},
                    ],
                }
            ],
        )
        return (message.content[0].text or '').strip()
        
    except anthropic.APIError as e:
        # Handle specific Anthropic API errors
        error_message = str(e)
        if "529" in error_message and "overloaded" in error_message.lower():
            raise Exception(f"Anthropic API is currently overloaded (Error 529): {error_message}")
        elif "rate_limit" in error_message.lower() or "429" in error_message:
            raise Exception(f"Anthropic API rate limit exceeded: {error_message}")
        elif "invalid_api_key" in error_message.lower() or "401" in error_message:
            raise Exception(f"Anthropic API key is invalid or expired: {error_message}")
        else:
            raise Exception(f"Anthropic API error: {error_message}")
    except Exception as e:
        raise Exception(f"Error converting PDF chunk to markdown: {str(e)}")

def _extract_kpis_from_markdown(client: 'anthropic.Anthropic', markdown_text: str, model_name: str) -> str:
    """Ask Claude to extract KPIs from Markdown and return raw text (ideally JSON)."""
    try:
        kpi_prompt = (
            "Tu es un analyste financier expert en fiscalité marocaine. "
            "À partir du Markdown fourni, identifie et retourne les valeurs suivantes pour l'année N et N-1 :\n\n"
            "- Chiffre d'affaires\n"
            "- Résultat d'exploitation\n"
            "- Résultat Net\n"
            "- Dotations d'exploitation\n"
            "- Reprises d'exploitation; transferts de charges\n"
            "- Redevances de crédit-bail\n"
            "- Trésorerie-Actif\n"
            "- Titres Valeurs de placement\n"
            "- Dettes de financement\n"
            "- Trésorerie-passif\n"
            "- Trésorerie nette\n"
            "- Compte d'associés (Actif)\n"
            "- Compte d'associés (Passif)\n"
            "- Redevanes restant à payer (a plus d'un an)\n"
            "- Redevanes restant à payer (a moins d'un an)\n"
            "- Prix d'achat résiduel en fin du contrat\n"
            "- Capitaux propres\n"
            "- Actif circulant\n"
            "- Passif circulant\n"
            "- Actif circulant total\n\n"
            "Retourne un JSON avec cette structure:\n"
            "{\n"
            "  \"Chiffre d'affaires\": {\"N\": valeur_n, \"N-1\": valeur_n_moins_1},\n"
            "  \"Résultat Net\": {\"N\": valeur_n, \"N-1\": valeur_n_moins_1},\n"
            "  \"Actif circulant\": {\"N\": valeur_n, \"N-1\": valeur_n_moins_1},\n"
            "  \"Passif circulant\": {\"N\": valeur_n, \"N-1\": valeur_n_moins_1},\n"
            "  \"Actif circulant total\": {\"N\": valeur_n, \"N-1\": valeur_n_moins_1}\n"
            "  ...\n"
            "}\n\n"
            "Si une valeur n'est pas trouvée, utilise null."
        )

        message = client.messages.create(
            model=model_name,
            max_tokens=2048,
            messages=[
                {
                    'role': 'user',
                    'content': [
                        {'type': 'text', 'text': kpi_prompt + "\n\n" + markdown_text},
                    ],
                }
            ],
        )
        return (message.content[0].text or '').strip()
        
    except anthropic.APIError as e:
        # Handle specific Anthropic API errors
        error_message = str(e)
        if "529" in error_message and "overloaded" in error_message.lower():
            raise Exception(f"Anthropic API is currently overloaded (Error 529): {error_message}")
        elif "rate_limit" in error_message.lower() or "429" in error_message:
            raise Exception(f"Anthropic API rate limit exceeded: {error_message}")
        elif "invalid_api_key" in error_message.lower() or "401" in error_message:
            raise Exception(f"Anthropic API key is invalid or expired: {error_message}")
        else:
            raise Exception(f"Anthropic API error: {error_message}")
    except Exception as e:
        raise Exception(f"Error extracting KPIs from markdown: {str(e)}")

def _extract_tva_data_from_single_document(client: 'anthropic.Anthropic', markdown_text: str, model_name: str, document_name: str) -> str:
    """Extract TVA-specific data from a single document's markdown."""
    try:
        tva_prompt = (
            "Tu es un analyste financier expert en fiscalité marocaine. "
            f"Analyse ce document fiscal ({document_name}) et extraire spécifiquement les données suivantes du tableau B14 'Détail de La Taxe sur La Valeur Ajoutée':\n\n"
            "1. T.V.A. Facturée (intersection ligne 'T.V.A. Facturée' avec colonne 'Opérations comptables de l'exercice')\n"
            "2. TVA pratique: T.V.A. de l'exercice (intersection ligne 'T.V.A. Facturée' avec colonne 'Déclarations T.V.A de l'exercice')\n"
            "3. Clients et comptes rattachés de l'exercice précédent\n" 
            "4. Clients et comptes rattachés brute de l'exercice\n"
            "5. Chiffre d'affaires (CA) pour le calcul de l'encaissement théorique\n\n"
            "Retourne un JSON avec cette structure:\n"
            "{\n"
            "  \"fiscal_year\": 2023,\n"
            "  \"tva_data\": {\n"
            "    \"tva_facturee\": valeur_tva_facturee,\n"
            "    \"tva_pratique\": valeur_tva_pratique,\n"
            "    \"clients_exercice_precedent\": valeur_clients_n_moins_1,\n"
            "    \"clients_exercice_brut\": valeur_clients_n,\n"
            "    \"chiffre_affaires\": valeur_ca\n"
            "  }\n"
            "}\n\n"
            "Si une valeur n'est pas trouvée, utilise null.\n"
            "Recherche particulièrement dans le tableau B14 'Détail de La Taxe sur La Valeur Ajoutée'."
        )

        message = client.messages.create(
            model=model_name,
            max_tokens=2048,
            messages=[
                {
                    'role': 'user',
                    'content': [
                        {'type': 'text', 'text': tva_prompt + "\n\n" + markdown_text},
                    ],
                }
            ],
        )
        return (message.content[0].text or '').strip()
        
    except anthropic.APIError as e:
        # Handle specific Anthropic API errors
        error_message = str(e)
        if "529" in error_message and "overloaded" in error_message.lower():
            raise Exception(f"Anthropic API is currently overloaded (Error 529): {error_message}")
        elif "rate_limit" in error_message.lower() or "429" in error_message:
            raise Exception(f"Anthropic API rate limit exceeded: {error_message}")
        elif "invalid_api_key" in error_message.lower() or "401" in error_message:
            raise Exception(f"Anthropic API key is invalid or expired: {error_message}")
        else:
            raise Exception(f"Anthropic API error: {error_message}")
    except Exception as e:
        raise Exception(f"Error extracting TVA data from single document {document_name}: {str(e)}")

def _extract_kpis_from_single_document(client: 'anthropic.Anthropic', markdown_text: str, model_name: str, document_name: str) -> str:
    """Extract KPIs from a single document's markdown with fiscal year identification."""
    try:
        kpi_prompt = (
            "Tu es un analyste financier expert en fiscalité marocaine. "
            f"Analyse ce document fiscal ({document_name}) et identifie:\n\n"
            "1. L'année fiscale principale (N) de ce document\n"
            "2. Les valeurs financières pour l'année N et N-1 si disponibles\n\n"
            "Extraire ces KPIs:\n"
            "- Chiffre d'affaires\n"
            "- Résultat d'exploitation\n"
            "- Résultat Net\n"
            "- Dotations d'exploitation\n"
            "- Reprises d'exploitation; transferts de charges\n"
            "- Redevances de crédit-bail\n"
            "- Trésorerie-Actif\n"
            "- Titres Valeurs de placement\n"
            "- Dettes de financement\n"
            "- Trésorerie-passif\n"
            "- Trésorerie nette\n"
            "- Compte d'associés (Actif)\n"
            "- Compte d'associés (Passif)\n"
            "- Redevanes restant à payer (a plus d'un an)\n"
            "- Redevanes restant à payer (a moins d'un an)\n"
            "- Prix d'achat résiduel en fin du contrat\n"
            "- Capitaux propres\n"
            "- Actif circulant\n"
            "- Passif circulant\n"
            "- Actif circulant total\n\n"
            "Retourne un JSON avec cette structure:\n"
            "{\n"
            "  \"fiscal_year\": 2023,\n"
            "  \"kpis\": {\n"
            "    \"Chiffre d'affaires\": {\"N\": valeur_n, \"N-1\": valeur_n_moins_1},\n"
            "    \"Résultat Net\": {\"N\": valeur_n, \"N-1\": valeur_n_moins_1},\n"
            "    \"Actif circulant\": {\"N\": valeur_n, \"N-1\": valeur_n_moins_1},\n"
            "    \"Passif circulant\": {\"N\": valeur_n, \"N-1\": valeur_n_moins_1},\n"
            "    \"Actif circulant total\": {\"N\": valeur_n, \"N-1\": valeur_n_moins_1},\n"
            "    ...\n"
            "  }\n"
            "}\n\n"
            "Si une valeur n'est pas trouvée, utilise null."
        )

        message = client.messages.create(
            model=model_name,
            max_tokens=2048,
            messages=[
                {
                    'role': 'user',
                    'content': [
                        {'type': 'text', 'text': kpi_prompt + "\n\n" + markdown_text},
                    ],
                }
            ],
        )
        return (message.content[0].text or '').strip()
        
    except anthropic.APIError as e:
        # Handle specific Anthropic API errors
        error_message = str(e)
        if "529" in error_message and "overloaded" in error_message.lower():
            raise Exception(f"Anthropic API is currently overloaded (Error 529): {error_message}")
        elif "rate_limit" in error_message.lower() or "429" in error_message:
            raise Exception(f"Anthropic API rate limit exceeded: {error_message}")
        elif "invalid_api_key" in error_message.lower() or "401" in error_message:
            raise Exception(f"Anthropic API key is invalid or expired: {error_message}")
        else:
            raise Exception(f"Anthropic API error: {error_message}")
    except Exception as e:
        raise Exception(f"Error extracting KPIs from single document {document_name}: {str(e)}")

def _process_multi_document_kpis(client: 'anthropic.Anthropic', document_kpis_list: list, model_name: str, log_progress) -> dict:
    """Process multiple documents to extract and validate KPIs with proper multi-year structure."""
    if not document_kpis_list:
        log_progress("No documents to process for multi-document KPI extraction")
        return {}
    
    log_progress(f"Processing {len(document_kpis_list)} documents for multi-document KPI extraction")
    
    # Validate and clean the document KPIs using the same validation logic as the original function
    validated_docs = []
    
    for i, doc_kpis in enumerate(document_kpis_list):
        if isinstance(doc_kpis, dict) and 'kpis' in doc_kpis:
            fiscal_year = doc_kpis.get('fiscal_year')
            if fiscal_year:
                log_progress(f"Validated document {i+1}: fiscal year {fiscal_year}")
                validated_docs.append(doc_kpis)
            else:
                log_progress(f"Warning: Document {i+1} missing fiscal year, skipping")
        else:
            log_progress(f"Warning: Document {i+1} has invalid KPI structure, skipping")
    
    if not validated_docs:
        log_progress("No valid documents found after validation")
        return {}
    
    log_progress(f"Successfully validated {len(validated_docs)} documents")
    
    # Combine the validated KPIs
    combined_kpis = _combine_multi_document_kpis(validated_docs)
    
    # If we have valid combined KPIs, use them; otherwise fall back to single document processing
    if combined_kpis and '_metadata' in combined_kpis:
        log_progress(f"Multi-document KPIs combined successfully with {len(combined_kpis['_metadata']['available_years'])} years of data")
        return combined_kpis
    else:
        log_progress("Multi-document combination failed, falling back to primary document")
        # Use the first (primary) document as fallback
        primary_doc = validated_docs[0] if validated_docs else {}
        if primary_doc and 'kpis' in primary_doc:
            log_progress(f"Using primary document (fiscal year {primary_doc.get('fiscal_year')}) as fallback")
            return primary_doc['kpis']
        else:
            log_progress("No valid primary document found")
            return {}

def _combine_multi_document_kpis(document_kpis_list: list) -> dict:
    """Combine KPIs from multiple documents into a unified multi-year structure."""
    if not document_kpis_list:
        return {}
    
    # Sort documents by fiscal year (newest first)
    sorted_docs = sorted(document_kpis_list, key=lambda x: x.get('fiscal_year', 0), reverse=True)
    
    # Create a unified timeline
    combined_kpis = {}
    year_mapping = {}  # Maps actual fiscal year to timeline position
    
    # Create year labels based on actual fiscal years and their consecutiveness
    all_fiscal_years = sorted([doc.get('fiscal_year') for doc in sorted_docs if doc.get('fiscal_year')], reverse=True)
    
    if not all_fiscal_years:
        return combined_kpis
    
    # Check if years are consecutive
    def are_years_consecutive(years):
        if len(years) <= 1:
            return True
        for i in range(len(years) - 1):
            if years[i] - years[i + 1] != 1:
                return False
        return True
    
    consecutive = are_years_consecutive(all_fiscal_years)
    most_recent_year = all_fiscal_years[0]
    
    print(f"[MULTI-DOC] Fiscal years: {all_fiscal_years}, Consecutive: {consecutive}", flush=True)
    
    if consecutive:
        # Consecutive years: create continuous timeline
        # 1 doc = N, N-1 (2 years)
        # 2 docs = N, N-1, N-2 (3 years) 
        # 3 docs = N, N-1, N-2, N-3 (4 years)
        
        year_mapping[most_recent_year] = 'N'
        
        max_years = len(sorted_docs) + 1  # +1 because each doc has N-1 data
        for i in range(1, max_years + 1):
            target_year = most_recent_year - i
            year_label = f'N-{i}'
            year_mapping[target_year] = year_label
            
    else:
        # Non-consecutive years: each document contributes N and N-1
        # Map each document's years individually
        year_counter = 0
        
        for doc_year in all_fiscal_years:
            if year_counter == 0:
                # Primary document (most recent)
                year_mapping[doc_year] = 'N'
                year_mapping[doc_year - 1] = 'N-1'
                year_counter = 2
            else:
                # Subsequent documents
                year_mapping[doc_year] = f'N-{year_counter}'
                year_mapping[doc_year - 1] = f'N-{year_counter + 1}'
                year_counter += 2
    
    print(f"[MULTI-DOC] Year mapping: {year_mapping}", flush=True)
    
    # Initialize combined structure
    kpi_names = [
        'Chiffre d\'affaires', 'Résultat d\'exploitation', 'Résultat Net',
        'Dotations d\'exploitation', 'Reprises d\'exploitation; transferts de charges',
        'Redevances de crédit-bail', 'Trésorerie-Actif', 'Titres Valeurs de placement',
        'Dettes de financement', 'Trésorerie-passif', 'Compte d\'associés (Actif)',
        'Compte d\'associés (Passif)', 'Redevanes restant à payer (a plus d\'un an)',
        'Redevanes restant à payer (a moins d\'un an)', 'Prix d\'achat résiduel en fin du contrat',
        'Capitaux propres'
    ]
    
    for kpi_name in kpi_names:
        combined_kpis[kpi_name] = {}
    
    # Combine data from all documents
    for doc in sorted_docs:
        fiscal_year = doc.get('fiscal_year')
        kpis = doc.get('kpis', {})
        
        if not fiscal_year or not kpis:
            continue
            
        for kpi_name in kpi_names:
            if kpi_name in kpis:
                kpi_data = kpis[kpi_name]
                
                # Map N and N-1 from this document to the combined timeline
                if isinstance(kpi_data, dict):
                    # Current year (N) from this document
                    if 'N' in kpi_data and fiscal_year in year_mapping:
                        timeline_year = year_mapping[fiscal_year]
                        combined_kpis[kpi_name][timeline_year] = kpi_data['N']
                    
                    # Previous year (N-1) from this document  
                    if 'N-1' in kpi_data and (fiscal_year - 1) in year_mapping:
                        timeline_year = year_mapping[fiscal_year - 1]
                        combined_kpis[kpi_name][timeline_year] = kpi_data['N-1']
    
    # Create available years list based on what we actually have data for
    available_years = []
    fiscal_years_in_docs = [doc.get('fiscal_year') for doc in sorted_docs if doc.get('fiscal_year')]
    
    # Only include years that correspond to actual document years or their N-1 data
    for year_val, year_label in year_mapping.items():
        # Include if it's a document year or if it's N-1 of a document year
        if year_val in fiscal_years_in_docs or (year_val + 1) in fiscal_years_in_docs:
            available_years.append(year_label)
    
    # Sort years logically (N, N-1, N-2, etc.)
    available_years.sort(key=lambda x: 0 if x == 'N' else int(x.split('-')[1]) if '-' in x else 999)
    
    # Add metadata
    combined_kpis['_metadata'] = {
        'total_documents': len(document_kpis_list),
        'fiscal_years': fiscal_years_in_docs,
        'year_mapping': year_mapping,
        'available_years': available_years
    }
    
    print(f"[MULTI-DOC] Combined KPIs created with years: {combined_kpis['_metadata']['available_years']}", flush=True)
    return combined_kpis

def _compute_tva_analysis(tva_data: dict) -> dict:
    """Compute TVA analysis including theoretical encaissement and TVA comparison."""
    if not tva_data or not isinstance(tva_data, dict):
        return {}
    
    def get_numeric_value(value):
        """Extract numeric value from various formats"""
        if value is None:
            return None
        try:
            if isinstance(value, str):
                # Remove common formatting
                cleaned_value = re.sub(r'[^\d.,\-]', '', str(value))
                cleaned_value = cleaned_value.replace(',', '.')
                if cleaned_value and cleaned_value != '.':
                    return float(cleaned_value)
            else:
                return float(value)
        except (ValueError, TypeError):
            pass
        return None
    
    tva_analysis = {}
    
    # Extract values from TVA data
    ca = get_numeric_value(tva_data.get('chiffre_affaires'))
    tva_facturee = get_numeric_value(tva_data.get('tva_facturee'))
    clients_precedent = get_numeric_value(tva_data.get('clients_exercice_precedent'))
    clients_brut = get_numeric_value(tva_data.get('clients_exercice_brut'))
    tva_pratique = get_numeric_value(tva_data.get('tva_pratique'))
    
    # Store extracted values
    tva_analysis['tva_facturee'] = tva_facturee
    tva_analysis['tva_pratique'] = tva_pratique
    tva_analysis['clients_exercice_precedent'] = clients_precedent
    tva_analysis['clients_exercice_brut'] = clients_brut
    tva_analysis['chiffre_affaires'] = ca
    
    # Calculate encaissement théorique
    # Formule: CA + TVA Facturée + Clients exercice précédent - Clients exercice brut
    if all(v is not None for v in [ca, tva_facturee, clients_precedent, clients_brut]):
        encaissement_theorique = ca + tva_facturee + clients_precedent - clients_brut
        tva_analysis['encaissement_theorique'] = encaissement_theorique
        
        # Calculate TVA théorique = encaissement théorique / 6
        tva_theorique = encaissement_theorique / 6
        tva_analysis['tva_theorique'] = tva_theorique
        
        # Compare TVA théorique vs TVA pratique
        if tva_pratique is not None:
            tva_analysis['ecart_tva'] = tva_theorique - tva_pratique
            tva_analysis['ecart_tva_pourcentage'] = ((tva_theorique - tva_pratique) / tva_theorique * 100) if tva_theorique != 0 else 0
    
    return tva_analysis

def _compute_financial_ratios(kpis_data: dict) -> dict:
    """Compute financial ratios from extracted KPIs using French names and multi-year structure"""
    
    if not kpis_data or not isinstance(kpis_data, dict):
        return {}
    
    def get_numeric_value(value):
        """Extract numeric value from various formats"""
        if value is None:
            return None
        try:
            if isinstance(value, str):
                # Remove common formatting
                cleaned_value = re.sub(r'[^\d.,\-]', '', str(value))
                cleaned_value = cleaned_value.replace(',', '.')
                if cleaned_value and cleaned_value != '.':
                    return float(cleaned_value)
            else:
                return float(value)
        except (ValueError, TypeError):
            pass
        return None
    
    def find_kpi_value(kpi_name_patterns, year="N"):
        """Find KPI value by trying different name patterns"""
        for pattern in kpi_name_patterns:
            # First try direct match with the pattern as key
            if pattern in kpis_data:
                if isinstance(kpis_data[pattern], dict) and year in kpis_data[pattern]:
                    value = get_numeric_value(kpis_data[pattern][year])
                    # print(f"[DEBUG] Found {pattern}[{year}] = {value}", flush=True)
                    return value
                elif not isinstance(kpis_data[pattern], dict):
                    value = get_numeric_value(kpis_data[pattern])
                    # print(f"[DEBUG] Found {pattern} = {value}", flush=True)
                    return value
            else:
                print(f"[DEBUG] Pattern '{pattern}' not found in KPIs data", flush=True)
        return None
    
    # Get available years from metadata or default to N, N-1
    available_years = ['N', 'N-1']
    if '_metadata' in kpis_data and 'available_years' in kpis_data['_metadata']:
        available_years = kpis_data['_metadata']['available_years']
        # Sort years in logical order (N, N-1, N-2, etc.)
        available_years = sorted(available_years, key=lambda x: 0 if x == 'N' else int(x.split('-')[1]) if '-' in x else 999)
    
    print(f"[RATIOS] Computing ratios for years: {available_years}", flush=True)
    
    # Log the multi-document structure if available
    if '_metadata' in kpis_data:
        metadata = kpis_data['_metadata']
        total_docs = metadata.get('total_documents', 1)
        fiscal_years = metadata.get('fiscal_years', [])
        print(f"[RATIOS] Multi-document processing: {total_docs} documents, fiscal years: {fiscal_years}", flush=True)
    
    # Extract base KPIs for all available years
    base_kpis = {}

    
    # KPI patterns to search for - using actual database keys
    kpi_patterns = {
        'chiffre_d_affaires': ['Chiffre d\'affaires'],
        'resultat_d_exploitation': ['Résultat d\'exploitation'],
        'resultat_net': ['Résultat Net'],
        'dotations_d_exploitation': ['Dotations d\'exploitation'],
        'reprises_d_exploitation': ['Reprises d\'exploitation; transferts de charges'],
        'redevances_credit_bail': ['Redevances de crédit-bail'],
        'tresorerie_actif': ['Trésorerie-Actif'],
        'titres_valeurs_placement': ['Titres Valeurs de placement'],
        'dettes_financement': ['Dettes de financement'],
        'tresorerie_passif': ['Trésorerie-passif'],
        'tresorerie_nette': ['Trésorerie nette'],
        'comptes_associes_actif': ['Compte d\'associés (Actif)'],
        'comptes_associes_passif': ['Compte d\'associés (Passif)'],
        'redevances_moins_un_an': ['Redevanes restant à payer (a moins d\'un an)'],
        'redevances_plus_un_an': ['Redevanes restant à payer (a plus d\'un an)'],
        'prix_achat_residuel': ['Prix d\'achat résiduel en fin du contrat'],
        'capitaux_propres': ['Capitaux propres'],
        'actif_circulant': ['Actif circulant'],
        'passif_circulant': ['Passif circulant'],
        'actif_circulant_total': ['Actif circulant total']
    }
    
    # Extract values for all available years
    for kpi_name, patterns in kpi_patterns.items():
        for year in available_years:
            year_suffix = year.lower().replace('-', '')
            base_kpis[f"{kpi_name}_{year_suffix}"] = find_kpi_value(patterns, year)
    
    print(f"[PROCESSING] Extracted base KPIs: {len([k for k, v in base_kpis.items() if v is not None])} non-null values", flush=True)
    # print(f"[PROCESSING] Sample base KPIs: {dict(list(base_kpis.items())[:5])}", flush=True)
    
    # Calculate computed ratios using the formulas for all available years
    computed_ratios = {}
    
    # Convert year format for processing (N -> n, N-1 -> n1, etc.)
    year_conversion = {'N': 'n', 'N-1': 'n1', 'N-2': 'n2', 'N-3': 'n3', 'N-4': 'n4', 'N-5': 'n5'}
    processed_years = [year_conversion.get(year, year.lower().replace('-', '')) for year in available_years]
    
    # EBITDA = RESULTAT D'EXPLOITATION + Dotations d'exploitation - Reprises d'exploitation + Redevances de crédit-bail
    for year in processed_years:
        resultat_exploit = base_kpis.get(f'resultat_d_exploitation_{year}', 0) or 0
        dotations = base_kpis.get(f'dotations_d_exploitation_{year}', 0) or 0
        reprises = base_kpis.get(f'reprises_d_exploitation_{year}', 0) or 0
        redevances = base_kpis.get(f'redevances_credit_bail_{year}', 0) or 0
        
        # print(f"[PROCESSING] EBITDA {year}: resultat_exploit={resultat_exploit}, dotations={dotations}, reprises={reprises}, redevances={redevances}", flush=True)
        
        if any([resultat_exploit, dotations, reprises, redevances]):
            ebitda_value = resultat_exploit + dotations - reprises + redevances
            computed_ratios[f'ebitda_{year}'] = ebitda_value
            # print(f"[PROCESSING] Computed EBITDA {year}: {ebitda_value}", flush=True)
    
    # Encours de crédit-bail = Redevances restant à payer (moins + plus d'un an) + Prix d'achat résiduel
    for year in processed_years:
        red_moins = base_kpis.get(f'redevances_moins_un_an_{year}', 0) or 0
        red_plus = base_kpis.get(f'redevances_plus_un_an_{year}', 0) or 0
        prix_residuel = base_kpis.get(f'prix_achat_residuel_{year}', 0) or 0
        
        # Always calculate and save encours_credit_bail, even if the result is 0
        encours_credit_bail = red_moins + red_plus + prix_residuel
        computed_ratios[f'encours_credit_bail_{year}'] = encours_credit_bail
        # print(f"[PROCESSING] Computed Encours crédit-bail {year}: {encours_credit_bail} (red_moins={red_moins}, red_plus={red_plus}, prix_residuel={prix_residuel})", flush=True)
    
    # Dette nette = DETTES DE FINANCEMENT + TRESORERIE-PASSIF + Comptes d'associés (passif) + encours crédit bail - TRESORERIE-ACTIF - TITRES - Comptes d'associés (actif)
    for year in processed_years:
        dettes_fin = base_kpis.get(f'dettes_financement_{year}', 0) or 0
        tres_passif = base_kpis.get(f'tresorerie_passif_{year}', 0) or 0
        comptes_ass_passif = base_kpis.get(f'comptes_associes_passif_{year}', 0) or 0
        encours_cb = computed_ratios.get(f'encours_credit_bail_{year}', 0) or 0
        tres_actif = base_kpis.get(f'tresorerie_actif_{year}', 0) or 0
        titres = base_kpis.get(f'titres_valeurs_placement_{year}', 0) or 0
        comptes_ass_actif = base_kpis.get(f'comptes_associes_actif_{year}', 0) or 0
        
        computed_ratios[f'dette_nette_{year}'] = (dettes_fin + tres_passif + comptes_ass_passif + encours_cb - 
                                                  tres_actif - titres - comptes_ass_actif)
    
    # Variations between consecutive years (N vs N-1, N-1 vs N-2, etc.)
    for i in range(len(processed_years) - 1):
        current_year = processed_years[i]
        previous_year = processed_years[i + 1]
        
        ca_current = base_kpis.get(f'chiffre_d_affaires_{current_year}')
        ca_previous = base_kpis.get(f'chiffre_d_affaires_{previous_year}')
        
        if ca_current and ca_previous and ca_previous != 0:
            computed_ratios[f'variation_chiffre_affaires_{current_year}_vs_{previous_year}'] = ((ca_current / ca_previous) - 1) * 100
    
    # Marge d'EBITDA = EBITDA / Chiffre d'affaires
    for year in processed_years:
        ebitda = computed_ratios.get(f'ebitda_{year}')
        ca = base_kpis.get(f'chiffre_d_affaires_{year}')
        if ebitda and ca and ca != 0:
            computed_ratios[f'marge_ebitda_{year}'] = (ebitda / ca) * 100
    
    # Marge d'exploitation = Résultat d'exploitation / Chiffre d'affaires
    for year in processed_years:
        resultat_exploit = base_kpis.get(f'resultat_d_exploitation_{year}')
        ca = base_kpis.get(f'chiffre_d_affaires_{year}')
        if resultat_exploit and ca and ca != 0:
            computed_ratios[f'marge_exploitation_{year}'] = (resultat_exploit / ca) * 100
    
    # Marge nette = Résultat net / Chiffre d'affaires
    for year in processed_years:
        resultat_net = base_kpis.get(f'resultat_net_{year}')
        ca = base_kpis.get(f'chiffre_d_affaires_{year}')
        if resultat_net and ca and ca != 0:
            computed_ratios[f'marge_nette_{year}'] = (resultat_net / ca) * 100
    
    # ROE = Résultat net / Capitaux Propres
    for year in processed_years:
        resultat_net = base_kpis.get(f'resultat_net_{year}')
        capitaux_propres = base_kpis.get(f'capitaux_propres_{year}')
        if resultat_net and capitaux_propres and capitaux_propres != 0:
            computed_ratios[f'roe_{year}'] = (resultat_net / capitaux_propres) * 100
    
    # ROCE = Résultat d'exploitation / (Capitaux Propres + Dette nette)
    for year in processed_years:
        resultat_exploit = base_kpis.get(f'resultat_d_exploitation_{year}')
        capitaux_propres = base_kpis.get(f'capitaux_propres_{year}')
        dette_nette = computed_ratios.get(f'dette_nette_{year}')
        if resultat_exploit and capitaux_propres and dette_nette is not None:
            denominateur = capitaux_propres + dette_nette
            if denominateur != 0:
                computed_ratios[f'roce_{year}'] = (resultat_exploit / denominateur) * 100
    
    # Gearing = Dette nette / Capitaux propres
    for year in processed_years:
        dette_nette = computed_ratios.get(f'dette_nette_{year}')
        capitaux_propres = base_kpis.get(f'capitaux_propres_{year}')
        if dette_nette is not None and capitaux_propres and capitaux_propres != 0:
            computed_ratios[f'gearing_{year}'] = (dette_nette / capitaux_propres) * 100
    
    # Capacité de remboursements = Dette nette / EBITDA
    for year in processed_years:
        dette_nette = computed_ratios.get(f'dette_nette_{year}')
        ebitda = computed_ratios.get(f'ebitda_{year}')
        if dette_nette is not None and ebitda and ebitda != 0:
            computed_ratios[f'capacite_remboursements_{year}'] = dette_nette / ebitda
    
    # Trésorerie nette = Trésorerie (Actif) - Trésorerie (Passif)
    for year in processed_years:
        # First try to use the extracted value if available
        extracted_tresorerie_nette = base_kpis.get(f'tresorerie_nette_{year}')
        
        if extracted_tresorerie_nette is not None:
            # Use the extracted value directly
            computed_ratios[f'tresorerie_nette_{year}'] = extracted_tresorerie_nette
            # print(f"[PROCESSING] Using extracted Trésorerie nette {year}: {extracted_tresorerie_nette}", flush=True)
        else:
            # Fallback to computation if extracted value not available
            tres_actif = base_kpis.get(f'tresorerie_actif_{year}', 0) or 0
            tres_passif = base_kpis.get(f'tresorerie_passif_{year}', 0) or 0
            
            if tres_actif is not None or tres_passif is not None:
                tresorerie_nette = tres_actif - tres_passif
                computed_ratios[f'tresorerie_nette_{year}'] = tresorerie_nette
                # print(f"[PROCESSING] Computed Trésorerie nette {year}: {tresorerie_nette} (Actif: {tres_actif}, Passif: {tres_passif})", flush=True)
    
    # Add metadata to computed ratios
    computed_ratios['_metadata'] = {
        'available_years': available_years,
        'processed_years': processed_years,
        'total_years': len(available_years)
    }
    
    # Add multi-document metadata if available
    if '_metadata' in kpis_data:
        source_metadata = kpis_data['_metadata']
        computed_ratios['_metadata']['multi_document'] = {
            'total_documents': source_metadata.get('total_documents', 1),
            'fiscal_years': source_metadata.get('fiscal_years', []),
            'year_mapping': source_metadata.get('year_mapping', {}),
            'is_multi_document': source_metadata.get('total_documents', 1) > 1
        }
        print(f"[RATIOS] Added multi-document metadata: {computed_ratios['_metadata']['multi_document']['total_documents']} documents", flush=True)
    
    return computed_ratios

def _safe_parse_json(text: str):
    """Try to robustly parse JSON from a possibly noisy LLM response."""
    if not text:
        return None
    # Try direct parse
    try:
        return json.loads(text)
    except Exception:
        pass
    # Extract fenced or first JSON object/array
    fenced = re.findall(r"```(?:json)?\s*([\s\S]*?)```", text, re.IGNORECASE)
    candidates = fenced + [text]
    for cand in candidates:
        cand = cand.strip()
        # Find first {...} or [...] block
        m = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", cand)
        if m:
            try:
                return json.loads(m.group(1))
            except Exception:
                continue
    return None
