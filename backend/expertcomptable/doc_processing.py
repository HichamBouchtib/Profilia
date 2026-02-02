import os
import json
import anthropic
import time
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import sys

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.logger import log_processing, log_success, log_error, log_warning
from services.doc_processing import process_doc_processing

def process_expert_comptable_document(company_name: str, file_path: str) -> Dict[str, Any]:
    """
    Process a liasse comptable document for expert comptable analysis.
    Only extracts financial data and generates financial analysis.
    
    Args:
        company_name (str): Name of the company
        file_path (str): Path to the uploaded PDF file
        
    Returns:
        Dict[str, Any]: Processed financial data and analysis
    """
    try:
        # Use a temporary profile_id for logging
        temp_profile_id = f"expertcompta_{company_name}_{int(time.time())}"
        log_processing(temp_profile_id, f"Starting expert comptable document processing for {company_name}")
        
        # Process the document directly using the existing functions
        from services.doc_processing import _chunk_pdf_files, _convert_chunk_with_claude, _extract_kpis_from_single_document
        import anthropic
        import tempfile
        import os
        
        # Initialize Claude client
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        if not anthropic_key:
            raise Exception("ANTHROPIC_API_KEY not found in environment variables")
        
        client = anthropic.Anthropic(api_key=anthropic_key)
        model_name = "claude-3-5-sonnet-20241022"
        
        # Create temporary directory for processing
        with tempfile.TemporaryDirectory() as temp_dir:
            # Chunk the PDF
            chunk_files = _chunk_pdf_files(file_path, temp_dir, pages_per_chunk=1, max_pages=25)
            
            if not chunk_files:
                raise Exception("Failed to process PDF file")
            
            # Convert chunks to markdown
            markdown_parts = []
            for chunk_file in chunk_files:
                markdown_text = _convert_chunk_with_claude(client, chunk_file, model_name)
                if markdown_text:
                    markdown_parts.append(markdown_text)
            
            if not markdown_parts:
                raise Exception("Failed to convert PDF to markdown")
            
            # Combine all markdown parts
            full_markdown = "\n\n".join(markdown_parts)
            
            # Extract KPIs from the markdown
            kpis_json = _extract_kpis_from_single_document(client, full_markdown, model_name, os.path.basename(file_path))
            
            if not kpis_json:
                raise Exception("Failed to extract KPIs from document")
            
            # Parse the JSON response
            try:
                extracted_data = json.loads(kpis_json)
            except json.JSONDecodeError:
                # Try to extract JSON from the response
                import re
                json_match = re.search(r'\{.*\}', kpis_json, re.DOTALL)
                if json_match:
                    extracted_data = json.loads(json_match.group())
                else:
                    raise Exception("Failed to parse KPIs JSON response")
            
            # Extract TVA data from the markdown
            print(f"[EXPERT COMPTABLE TVA DEBUG] Extracting TVA data from document", flush=True)
            from services.doc_processing import _extract_tva_data_from_single_document, _safe_parse_json
            
            try:
                tva_raw = _extract_tva_data_from_single_document(client, full_markdown, model_name, os.path.basename(file_path))
                print(f"[EXPERT COMPTABLE TVA DEBUG] Raw TVA response: {tva_raw[:500]}...", flush=True)
                
                tva_json = _safe_parse_json(tva_raw)
                print(f"[EXPERT COMPTABLE TVA DEBUG] Parsed TVA JSON: {tva_json}", flush=True)
                
                if tva_json and 'tva_data' in tva_json:
                    # Add TVA data to extracted data
                    extracted_data['tva_data'] = tva_json['tva_data']
                    print(f"[EXPERT COMPTABLE TVA DEBUG] Added TVA data: {tva_json['tva_data']}", flush=True)
                else:
                    print(f"[EXPERT COMPTABLE TVA DEBUG] No TVA data found in response", flush=True)
                    
            except Exception as tva_error:
                print(f"[EXPERT COMPTABLE TVA DEBUG] Error extracting TVA: {tva_error}", flush=True)
                # Continue without TVA data - don't fail the whole process
        
        if not extracted_data:
            raise Exception("Failed to extract data from document")
        
        # Extract only the financial KPIs
        financial_data = {
            'company_name': company_name,
            'fiscal_year': extracted_data.get('fiscal_year'),
            'kpis': extracted_data.get('kpis', {}),
            'processing_timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        # Compute financial ratios from KPIs
        from services.doc_processing import _compute_financial_ratios
        computed_ratios = _compute_financial_ratios(financial_data['kpis'])
        
        # Compute TVA analysis if TVA data is available
        tva_analysis = {}
        if 'tva_data' in extracted_data and extracted_data['tva_data']:
            print(f"[EXPERT COMPTABLE TVA DEBUG] Computing TVA analysis", flush=True)
            from services.doc_processing import _compute_tva_analysis
            
            tva_calc = _compute_tva_analysis(extracted_data['tva_data'])
            if tva_calc:
                fiscal_year = extracted_data.get('fiscal_year', 'unknown')
                tva_analysis[f"tva_analysis_{fiscal_year}"] = tva_calc
                print(f"[EXPERT COMPTABLE TVA DEBUG] Computed TVA analysis: {tva_calc}", flush=True)
            else:
                print(f"[EXPERT COMPTABLE TVA DEBUG] TVA analysis computation failed", flush=True)
        else:
            print(f"[EXPERT COMPTABLE TVA DEBUG] No TVA data available for analysis", flush=True)
        
        # Generate financial analysis using the existing financial reporting service
        from services.financial_reporting import generate_financial_analysis
        
        # Create minimal web_data and news_data for the financial analysis
        web_data = {
            'company_info': {'name': company_name},
            'financial_ratios': computed_ratios
        }
        news_data = ""
        
        # Generate financial analysis
        financial_analysis = generate_financial_analysis(
            company_name=company_name,
            extracted_kpis=financial_data['kpis'],
            computed_ratios=computed_ratios,
            news_data=news_data,
            web_data=web_data,
            fiscal_year=financial_data['fiscal_year']
        )
        
        # Combine the results
        result = {
            'company_name': company_name,
            'fiscal_year': financial_data['fiscal_year'],
            'kpis': financial_data['kpis'],
            'computed_ratios': computed_ratios,
            'tva_analysis': tva_analysis,
            'financial_analysis': financial_analysis,
            'processing_timestamp': financial_data['processing_timestamp'],
            'status': 'completed'
        }
        
        print(f"[EXPERT COMPTABLE TVA DEBUG] Final result includes TVA analysis: {bool(tva_analysis)}", flush=True)
        print(f"[EXPERT COMPTABLE TVA DEBUG] Result keys: {list(result.keys())}", flush=True)
        
        log_success(f"Expert comptable document processing completed for {company_name}")
        return result
        
    except Exception as e:
        log_error(f"Error processing expert comptable document for {company_name}: {str(e)}")
        return {
            'company_name': company_name,
            'error': str(e),
            'status': 'error'
        }
