"""
PDF Generator for Expert Comptable Reports
Generates PDF versions of expert comptable analysis reports.
"""

import os
import sys
from datetime import datetime
from io import BytesIO
from typing import Dict, Any, Tuple

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from expertcomptable.report_generator import (
    format_financial_number, 
    format_percentage, 
    group_metrics_by_base_name
)

def generate_expert_comptable_pdf(data: Dict[str, Any]) -> Tuple[bytes, str]:
    """
    Generate a PDF version of the expert comptable report.
    
    Args:
        data (Dict[str, Any]): Processed expert comptable data
        
    Returns:
        Tuple[bytes, str]: PDF content and filename
    """
    try:
        # Extract data
        company_name = data.get('company_name', 'Company')
        fiscal_year = data.get('fiscal_year', datetime.now().year)
        kpis = data.get('kpis', {})
        computed_ratios = data.get('computed_ratios', {})
        financial_analysis = data.get('financial_analysis', {})
        
        # Extract years
        if isinstance(fiscal_year, dict):
            current_year = fiscal_year.get('primary_year', datetime.now().year)
            previous_year = current_year - 1
        else:
            current_year = fiscal_year
            previous_year = current_year - 1
        
        # Extract financial sections from the analysis
        detailed_analysis = financial_analysis.get('detailed_analysis', '')
        recommendation = financial_analysis.get('recommendation', '')
        
        # Create clean PDF-friendly HTML
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>{company_name} - Analyse Expert Comptable</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    margin: 30px;
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
                    margin-bottom: 40px;
                    page-break-inside: avoid;
                }}
                .metrics-grid {{
                    display: grid;
                    grid-template-columns: repeat(2, 1fr);
                    gap: 20px;
                    margin-bottom: 24px;
                }}
                .metric-card {{
                    background: #f8fafc;
                    border: 1px solid #e2e8f0;
                    padding: 20px;
                    border-radius: 8px;
                    text-align: center;
                    border-left: 4px solid #007bff;
                }}
                .metric-title {{
                    font-size: 16px;
                    font-weight: 600;
                    color: #2d3748;
                    margin-bottom: 15px;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                }}
                .metric-years-container {{
                    display: flex;
                    gap: 10px;
                    justify-content: space-between;
                }}
                .metric-year-box {{
                    flex: 1;
                    background: white;
                    padding: 12px;
                    border-radius: 6px;
                    border: 1px solid #cbd5e0;
                    min-height: 60px;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                }}
                .metric-year-value {{
                    font-size: 18px;
                    font-weight: 700;
                    color: #007bff;
                    margin-bottom: 4px;
                }}
                .metric-year-label {{
                    font-size: 12px;
                    font-weight: 500;
                    color: #718096;
                }}
                .analysis-text {{
                    text-align: justify;
                    line-height: 1.6;
                    color: #2d3748;
                    margin: 15px 0;
                    background: #f7fafc;
                    padding: 20px;
                    border-radius: 8px;
                    border-left: 4px solid #007bff;
                }}
                .analysis-text h4 {{
                    color: #007bff;
                    margin-bottom: 10px;
                    text-align: left;
                }}
                .footer {{
                    margin-top: 50px;
                    text-align: center;
                    font-size: 12px;
                    color: #718096;
                    border-top: 1px solid #e2e8f0;
                    padding-top: 20px;
                }}
                @page {{
                    margin: 2cm;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{company_name}</h1>
                <p>Analyse Expert Comptable - Année {current_year}</p>
                <p>Rapport généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}</p>
            </div>
        """
        
        # Generate Diagnostic Financier section
        html_content += generate_diagnostic_section(kpis, current_year, previous_year, detailed_analysis)
        
        # Generate Structure Financière section
        html_content += generate_structure_section(computed_ratios, current_year, previous_year, detailed_analysis)
        
        # Generate Analyse de Rentabilité section
        html_content += generate_rentabilite_section(kpis, computed_ratios, current_year, previous_year, recommendation)
        
        # Footer
        html_content += f"""
            <div class="footer">
                <p>Rapport généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}</p>
                <p>Expert Comptable - Analyse Financière Simplifiée</p>
            </div>
        </body>
        </html>
        """
        
        # Generate PDF using weasyprint
        from weasyprint import HTML
        pdf_buffer = BytesIO()
        html_doc = HTML(string=html_content, encoding='utf-8', base_url='')
        html_doc.write_pdf(pdf_buffer)
        
        # Get PDF content
        pdf_content = pdf_buffer.getvalue()
        pdf_buffer.close()
        
        # Generate filename
        timestamp = datetime.now().strftime('%Y-%m-%d')
        filename = f"{company_name.replace(' ', '_')}_analyse_expertcomptable_{timestamp}.pdf"
        
        return pdf_content, filename
        
    except Exception as e:
        raise Exception(f"Error generating PDF: {str(e)}")

def generate_diagnostic_section(kpis: Dict[str, Any], current_year: int, previous_year: int, detailed_analysis: str) -> str:
    """Generate the Diagnostic Financier section HTML"""
    
    # Filter KPIs for Diagnostic Financier
    diagnostic_indicators = [
        "chiffre d'affaires", "ebitda", "résultat net", "trésorerie nette", 
        "capitaux propres", "dette nette", "bfr"
    ]
    
    filtered_kpis = {}
    for key, value in kpis.items():
        key_lower = key.lower()
        if any(indicator in key_lower for indicator in diagnostic_indicators):
            filtered_kpis[key] = value
    
    # Group filtered KPIs
    grouped_kpis = group_metrics_by_base_name(filtered_kpis, current_year, previous_year)
    
    html_content = """
        <div class="section">
            <h2>📊 Diagnostic Financier</h2>
            <div class="metrics-grid">
    """
    
    for base_name, years_data in grouped_kpis.items():
        # Skip metrics that have no data
        if not years_data or (not years_data.get('current') and not years_data.get('previous')):
            continue
            
        # Determine if this is a percentage metric
        is_percentage = any(keyword in base_name.lower() for keyword in ['marge', 'roe', 'roi', 'roce', 'ratio', 'variation'])
        
        html_content += f"""
            <div class="metric-card">
                <div class="metric-title">{base_name}</div>
                <div class="metric-years-container">
        """
        
        # Add current year data if available
        if 'current' in years_data:
            current_value = years_data['current']
            formatted_value = format_percentage(current_value) if is_percentage else format_financial_number(current_value)
            html_content += f"""
                    <div class="metric-year-box">
                        <div class="metric-year-value">{formatted_value}</div>
                        <div class="metric-year-label">({current_year})</div>
                    </div>
            """
        
        # Add previous year data if available
        if 'previous' in years_data:
            previous_value = years_data['previous']
            formatted_value = format_percentage(previous_value) if is_percentage else format_financial_number(previous_value)
            html_content += f"""
                    <div class="metric-year-box">
                        <div class="metric-year-value">{formatted_value}</div>
                        <div class="metric-year-label">({previous_year})</div>
                    </div>
            """
        
        html_content += """
                </div>
            </div>
        """
    
    html_content += """
            </div>
    """
    
    # Add diagnostic analysis
    if detailed_analysis:
        html_content += f'<div class="analysis-text"><p>{detailed_analysis}</p></div>'
    
    html_content += """
        </div>
    """
    
    return html_content

def generate_structure_section(computed_ratios: Dict[str, Any], current_year: int, previous_year: int, detailed_analysis: str) -> str:
    """Generate the Structure Financière section HTML"""
    
    # Filter ratios for Structure Financière
    structure_ratios = [
        "gearing", "capacité de remboursement", "ratio de liquidité générale"
    ]
    
    filtered_ratios = {}
    for key, value in computed_ratios.items():
        key_lower = key.lower()
        if any(ratio in key_lower for ratio in structure_ratios):
            filtered_ratios[key] = value
    
    grouped_ratios = group_metrics_by_base_name(filtered_ratios, current_year, previous_year)
    
    html_content = """
        <div class="section">
            <h2>🏢 Structure Financière</h2>
            <div class="metrics-grid">
    """
    
    for base_name, years_data in grouped_ratios.items():
        # Skip metrics that have no data
        if not years_data or (not years_data.get('current') and not years_data.get('previous')):
            continue
            
        # Determine if this is a percentage metric
        is_percentage = any(keyword in base_name.lower() for keyword in ['marge', 'roe', 'roi', 'roce', 'ratio', 'variation'])
        
        html_content += f"""
            <div class="metric-card">
                <div class="metric-title">{base_name}</div>
                <div class="metric-years-container">
        """
        
        # Add current year data if available
        if 'current' in years_data:
            current_value = years_data['current']
            formatted_value = format_percentage(current_value) if is_percentage else format_financial_number(current_value)
            html_content += f"""
                    <div class="metric-year-box">
                        <div class="metric-year-value">{formatted_value}</div>
                        <div class="metric-year-label">({current_year})</div>
                    </div>
            """
        
        # Add previous year data if available
        if 'previous' in years_data:
            previous_value = years_data['previous']
            formatted_value = format_percentage(previous_value) if is_percentage else format_financial_number(previous_value)
            html_content += f"""
                    <div class="metric-year-box">
                        <div class="metric-year-value">{formatted_value}</div>
                        <div class="metric-year-label">({previous_year})</div>
                    </div>
            """
        
        html_content += """
                </div>
            </div>
        """
    
    html_content += """
            </div>
    """
    
    # Add structure analysis
    if detailed_analysis:
        html_content += f'<div class="analysis-text"><p>{detailed_analysis}</p></div>'
    
    html_content += """
        </div>
    """
    
    return html_content

def generate_rentabilite_section(kpis: Dict[str, Any], computed_ratios: Dict[str, Any], current_year: int, previous_year: int, recommendation: str) -> str:
    """Generate the Analyse de Rentabilité section HTML"""
    
    # Filter for specific profitability metrics
    profitability_indicators = [
        "marge opérationnelle", "rotation des actifs", "marge nette", "roe", "roce"
    ]
    
    # Combine all metrics for profitability analysis
    all_metrics = {}
    if kpis:
        all_metrics.update(kpis)
    if computed_ratios:
        all_metrics.update(computed_ratios)
    
    # Filter for specific profitability metrics only
    profitability_metrics = {}
    for key, value in all_metrics.items():
        key_lower = key.lower()
        if any(indicator in key_lower for indicator in profitability_indicators):
            profitability_metrics[key] = value
    
    grouped_profitability = group_metrics_by_base_name(profitability_metrics, current_year, previous_year)
    
    html_content = """
        <div class="section">
            <h2>📈 Analyse de Rentabilité</h2>
            <div class="metrics-grid">
    """
    
    for base_name, years_data in grouped_profitability.items():
        # Skip metrics that have no data
        if not years_data or (not years_data.get('current') and not years_data.get('previous')):
            continue
            
        # Determine if this is a percentage metric
        is_percentage = any(keyword in base_name.lower() for keyword in ['marge', 'roi', 'roe', 'roce', 'ratio', 'variation'])
        
        html_content += f"""
            <div class="metric-card">
                <div class="metric-title">{base_name}</div>
                <div class="metric-years-container">
        """
        
        # Add current year data if available
        if 'current' in years_data:
            current_value = years_data['current']
            formatted_value = format_percentage(current_value) if is_percentage else format_financial_number(current_value)
            html_content += f"""
                    <div class="metric-year-box">
                        <div class="metric-year-value">{formatted_value}</div>
                        <div class="metric-year-label">({current_year})</div>
                    </div>
            """
        
        # Add previous year data if available
        if 'previous' in years_data:
            previous_value = years_data['previous']
            formatted_value = format_percentage(previous_value) if is_percentage else format_financial_number(previous_value)
            html_content += f"""
                    <div class="metric-year-box">
                        <div class="metric-year-value">{formatted_value}</div>
                        <div class="metric-year-label">({previous_year})</div>
                    </div>
            """
        
        html_content += """
                </div>
            </div>
        """
    
    html_content += """
            </div>
    """
    
    # Add rentabilité analysis
    if recommendation:
        html_content += f'<div class="analysis-text"><h4>Analyse de Rentabilité:</h4><p>{recommendation}</p></div>'
    
    html_content += """
        </div>
    """
    
    return html_content

