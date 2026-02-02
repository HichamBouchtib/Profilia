import os
import json
from typing import Dict, Any
from datetime import datetime

def format_financial_number(num, currency="MAD"):
    """Format financial numbers in millions like 2.83 M MAD"""
    if num is None or num == 0:
        return "0"
    
    try:
        number = float(num)
        if abs(number) >= 1000000:
            return f"{number / 1000000:.2f}".replace('.', ',') + " M " + currency
        elif abs(number) >= 1000:
            return f"{number / 1000:.2f}".replace('.', ',') + " K " + currency
        else:
            return f"{number:.2f}".replace('.', ',') + " " + currency
    except (ValueError, TypeError):
        return str(num)

def format_percentage(num):
    """Format percentage numbers"""
    if num is None:
        return "0%"
    try:
        return f"{float(num):.2f}%"
    except (ValueError, TypeError):
        return str(num)

def format_metric_label(label, current_year, previous_year):
    """Format metric labels with actual years instead of N/N-1"""
    if not current_year or current_year == 'N/A':
        return label
    
    # First replace N1 and N-1 with previous year (must be done before replacing N)
    if previous_year:
        formatted_label = label.replace(' N1', f' ({previous_year})')
        formatted_label = formatted_label.replace(' N-1', f' ({previous_year})')
    else:
        formatted_label = label
    
    # Then replace remaining N with current year
    formatted_label = formatted_label.replace(' N', f' ({current_year})')
    
    return formatted_label

def group_metrics_by_base_name(metrics, current_year, previous_year):
    """Group metrics by their base name and organize by year"""
    grouped_metrics = {}
    
    for metric_name, metric_data in metrics.items():
        # Skip metadata
        if metric_name.startswith('_'):
            continue
            
        # Check if this is a nested structure with N and N-1
        if isinstance(metric_data, dict) and ('N' in metric_data or 'N-1' in metric_data):
            # This is the expected structure: {"N": value, "N-1": value}
            base_name = metric_name.replace('_', ' ').title()
            
            if base_name not in grouped_metrics:
                grouped_metrics[base_name] = {}
            
            # Add current year data if available
            if 'N' in metric_data and metric_data['N'] is not None:
                try:
                    value = float(metric_data['N'])
                    if value != 0:
                        grouped_metrics[base_name]['current'] = value
                except (ValueError, TypeError):
                    pass
            
            # Add previous year data if available
            if 'N-1' in metric_data and metric_data['N-1'] is not None:
                try:
                    value = float(metric_data['N-1'])
                    if value != 0:
                        grouped_metrics[base_name]['previous'] = value
                except (ValueError, TypeError):
                    pass
        else:
            # Handle simple values that might have N/N1 suffixes in their names
            try:
                value = float(metric_data)
                if value != 0:
                    # Extract base name by removing N, N1, N-1 suffixes
                    base_name = metric_name
                    year_type = None
                    
                    # Check for N1 or N-1 (previous year) - must check first
                    if (metric_name.endswith(' N1') or metric_name.endswith(' N-1') or 
                        metric_name.endswith('_n1') or metric_name.endswith('_N1')):
                        base_name = (metric_name.replace(' N1', '').replace(' N-1', '')
                                   .replace('_n1', '').replace('_N1', ''))
                        year_type = 'previous'
                    # Check for N (current year)
                    elif (metric_name.endswith(' N') or metric_name.endswith('_n') or 
                          metric_name.endswith('_N')):
                        base_name = (metric_name.replace(' N', '')
                                   .replace('_n', '').replace('_N', ''))
                        year_type = 'current'
                    else:
                        # If no year suffix, assume current year
                        year_type = 'current'
                    
                    # Clean up base name
                    base_name = base_name.replace('_', ' ').title()
                    
                    if base_name not in grouped_metrics:
                        grouped_metrics[base_name] = {}
                    
                    grouped_metrics[base_name][year_type] = value
            except (ValueError, TypeError):
                pass
    
    return grouped_metrics

def generate_expert_comptable_report(data: Dict[str, Any]) -> str:
    """
    Generate a simplified HTML report for expert comptable analysis.
    Only includes financial sections: Diagnostic Financier, Structure Financière, and Analyse de Rentabilité.
    
    Args:
        data (Dict[str, Any]): Processed financial data
        
    Returns:
        str: HTML report content
    """
    
    company_name = data.get('company_name', 'N/A')
    fiscal_year = data.get('fiscal_year', 'N/A')
    kpis = data.get('kpis', {})
    computed_ratios = data.get('computed_ratios', {})
    financial_analysis = data.get('financial_analysis', {})
    tva_analysis = data.get('tva_analysis', {})
    
    # Debug TVA data
    print(f"[TVA REPORT DEBUG] Input data keys: {list(data.keys())}", flush=True)
    print(f"[TVA REPORT DEBUG] TVA analysis keys: {list(tva_analysis.keys()) if tva_analysis else 'None'}", flush=True)
    print(f"[TVA REPORT DEBUG] TVA analysis content: {tva_analysis}", flush=True)
    
    # Extract year from fiscal_year for display
    current_year = fiscal_year
    previous_year = None
    
    if fiscal_year and fiscal_year != 'N/A':
        try:
            # Handle different fiscal year formats
            if '-' in str(fiscal_year):
                # Format like "2023-2024" - take the first year
                current_year = str(fiscal_year).split('-')[0]
            else:
                # Format like "2023" or "2023-2024"
                current_year = str(fiscal_year).split('-')[0]
            
            # Calculate previous year
            previous_year = str(int(current_year) - 1)
        except (ValueError, TypeError):
            current_year = fiscal_year
            previous_year = str(int(current_year) - 1) if current_year.isdigit() else None
    
    # Extract financial sections from the analysis
    swot_analysis = financial_analysis.get('swot_analysis', {})
    recommendation = financial_analysis.get('recommendation', '')
    detailed_analysis = financial_analysis.get('detailed_analysis', '')
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Rapport Expert Comptable - {company_name}</title>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        <style>
            :root {{
                --primary: #f59e0b;
                --primary-rgb: 245, 158, 11;
                --primary-dark: #d97706;
                --success: #10b981;
                --danger: #ef4444;
                --warning: #f59e0b;
                --text-dark: #1f2937;
                --text-light: #6b7280;
                --card-bg: #ffffff;
                --border-radius: 12px;
                --shadow-sm: 0 1px 3px rgba(0, 0, 0, 0.1);
                --shadow-md: 0 4px 6px rgba(0, 0, 0, 0.1);
                --transition: all 0.3s ease;
                --orange-light: #fef3c7;
                --orange-gradient: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
            }}
            
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                line-height: 1.6;
                background: linear-gradient(135deg, #fef3c7 0%, #fed7aa 50%, #f59e0b 100%);
                color: var(--text-dark);
                min-height: 100vh;
            }}
            
            .container {{
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
            }}
            
            .header {{
                text-align: center;
                background: var(--orange-gradient);
                color: white;
                padding: 40px 30px;
                border-radius: var(--border-radius);
                margin-bottom: 30px;
                box-shadow: var(--shadow-md);
            }}
            
            .header h1 {{
                font-size: 2.5rem;
                font-weight: 700;
                margin-bottom: 10px;
                color: white;
                text-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            
            .header .subtitle {{
                font-size: 1.2rem;
                opacity: 0.9;
                color: rgba(255, 255, 255, 0.9);
            }}
            
            .section {{
                background: var(--card-bg);
                border-radius: var(--border-radius);
                padding: 30px;
                margin-bottom: 30px;
                box-shadow: var(--shadow-sm);
                border: 1px solid rgba(0, 0, 0, 0.05);
            }}
            
            .section h2 {{
                color: var(--text-dark);
                font-size: 1.8rem;
                font-weight: 600;
                margin-bottom: 20px;
                padding-bottom: 10px;
                border-bottom: 3px solid var(--primary);
                display: flex;
                align-items: center;
                gap: 10px;
            }}
            
            .section h2 i {{
                color: var(--primary);
                font-size: 1.5rem;
            }}
            
            .metrics-grid {{
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 20px;
                margin-bottom: 24px;
            }}
            
            .metric-card {{
                background: linear-gradient(135deg, #fef3c7 0%, #ffffff 100%);
                color: var(--text-dark);
                padding: 20px;
                border-radius: var(--border-radius);
                text-align: center;
                transition: var(--transition);
                border: 1px solid rgba(245, 158, 11, 0.2);
            }}
            
            .metric-card:hover {{
                transform: translateY(-4px);
                background: linear-gradient(135deg, #fed7aa 0%, #fef3c7 100%);
                box-shadow: 0 8px 25px rgba(245, 158, 11, 0.15);
                border-color: var(--primary);
            }}
            
            .metric-title {{
                font-size: 1.1rem;
                font-weight: 600;
                color: var(--primary-dark);
                margin-bottom: 15px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
            
            .metric-years-container {{
                display: flex;
                gap: 10px;
                justify-content: space-between;
            }}
            
            .metric-years-container:has(.metric-year-box:only-child) .metric-year-box {{
                width: 100%;
            }}
            
            .metric-year-box {{
                flex: 1;
                background: rgba(255, 255, 255, 0.95);
                padding: 12px;
                border-radius: 8px;
                border: 1px solid rgba(245, 158, 11, 0.3);
                min-height: 60px;
                display: flex;
                flex-direction: column;
                justify-content: center;
            }}
            
            .metric-year-value {{
                font-size: 1.4rem;
                font-weight: 700;
                color: var(--primary-dark);
                margin-bottom: 4px;
            }}
            
            .metric-year-label {{
                font-size: 0.8rem;
                font-weight: 500;
                color: var(--text-light);
            }}
            
            .analysis-text {{
                text-align: justify;
                line-height: 1.6;
                color: var(--text-dark);
                margin: 15px 0;
            }}
            
            .analysis-text h4 {{
                color: #374151;
                margin-bottom: 10px;
                text-align: left;
            }}
            
            .analysis-section {{
                background: #f8fafc;
                padding: 20px;
                border-radius: var(--border-radius);
                margin-top: 20px;
                border-left: 4px solid #374151;
                line-height: 1.7;
            }}
            
            /* Financial Diagnostic Table Styles */
            .financial-diagnostic {{
                background: linear-gradient(135deg, #fef3c7 0%, #ffffff 100%);
                border-radius: var(--border-radius);
                padding: 1.5rem;
                box-shadow: var(--shadow-md);
                margin-bottom: 2rem;
                border: 1px solid rgba(245, 158, 11, 0.2);
            }}
            
            .financial-table {{
                width: 100%;
                border-collapse: collapse;
                background: white;
                border-radius: var(--border-radius);
                overflow: hidden;
                box-shadow: var(--shadow-sm);
            }}
            
            .financial-table th,
            .financial-table td {{
                padding: 12px 16px;
                text-align: right;
                border-bottom: 1px solid #e5e7eb;
                color: var(--text-dark);
            }}
            
            .financial-table th:first-child,
            .financial-table td:first-child {{
                text-align: left;
                font-weight: 600;
                color: var(--text-dark);
            }}
            
            .financial-table td:nth-child(2),
            .financial-table td:nth-child(3) {{
                color: var(--text-dark);
                font-weight: 600;
            }}
            
            .financial-table tbody tr:hover {{
                background-color: rgba(55, 65, 81, 0.02);
            }}
            
            .financial-table tbody tr:last-child td {{
                border-bottom: none;
            }}
            
            /* CAGR styling */
            .change {{
                display: inline-flex;
                align-items: center;
                gap: 4px;
                font-weight: 600;
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 0.9em;
            }}
            
            .change.positive {{
                color: var(--success);
                background-color: rgba(16, 185, 129, 0.1);
            }}
            
            .change.negative {{
                color: var(--danger);
                background-color: rgba(239, 68, 68, 0.1);
            }}
            
            .change i {{
                font-size: 0.8em;
            }}
            
            .info-box {{
                background: linear-gradient(135deg, rgba(245, 158, 11, 0.1) 0%, rgba(255, 255, 255, 0.8) 100%);
                padding: 1.5rem;
                border-radius: var(--border-radius);
                border-left: 4px solid var(--primary);
                margin: 1rem 0;
            }}
            
            .info-box h3 {{
                color: var(--primary-dark);
                margin-bottom: 0.5rem;
                font-size: 1.1rem;
            }}
            
            .info-box p {{
                color: var(--text-dark);
                margin: 0;
                line-height: 1.6;
            }}
            
            .footer {{
                text-align: center;
                margin-top: 40px;
                padding: 20px;
                color: white;
                background: var(--orange-gradient);
                border-radius: var(--border-radius);
                box-shadow: var(--shadow-sm);
                text-shadow: 0 1px 3px rgba(0,0,0,0.1);
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1><i class="fas fa-calculator"></i> Revue analytique pour Expert Comptable</h1>
                <div class="subtitle">{company_name} - Exercice {fiscal_year}</div>
            </div>
            
            <!-- Diagnostic Financier -->
            <div class="section">
                <h2><i class="fas fa-chart-bar"></i> Revue Analytique</h2>
                
                <!-- Tableau Diagnostic Financier -->
                <div class="financial-diagnostic" style="margin-bottom: 2rem;">
                    <h3 style="margin-bottom: 1rem; color: var(--primary); font-size: 1.2rem;">
                        <i class="fas fa-chart-line"></i> Diagnostic Financier
                    </h3>
                    <div style="overflow-x: auto;">
                        <table class="financial-table" id="financial-diagnostic-table">
                            <thead>
                                <tr>
                                    <th style="text-align: left; padding: 12px; background-color: var(--primary); color: white; font-weight: 600;">Indicateur Clé</th>
                                    <th style="text-align: right; padding: 12px; background-color: var(--primary); color: white; font-weight: 600;">N (MAD)</th>
                                    <th style="text-align: right; padding: 12px; background-color: var(--primary); color: white; font-weight: 600;">N-1 (MAD)</th>
                                    <th style="text-align: center; padding: 12px; background-color: var(--primary); color: white; font-weight: 600;">CAGR (%)</th>
                                </tr>
                            </thead>
                            <tbody id="financial-diagnostic-tbody">
                                <!-- Table content will be generated dynamically by JavaScript -->
                            </tbody>
                        </table>
                    </div>
                </div>
                
                <!-- Seul le tableau diagnostic financier sera affiché dans cette section -->
                <div class="info-box" style="margin-top: 1rem;">
                    <h3>Analyse des Variations Significatives</h3>
                    <p>Le tableau ci-dessus présente les indicateurs clés de performance avec leurs évolutions entre les exercices N et N-1, ainsi que les taux de croissance (CAGR) correspondants.</p>
                </div>
    """
    
    # Add diagnostic financier analysis
    if detailed_analysis:
        html_content += f'<div class="analysis-text"><p>{detailed_analysis}</p></div>'
    
    html_content += """
            </div>
            
            <!-- Structure Financière -->
            <div class="section">
                <h2><i class="fas fa-building"></i> Structure Financière</h2>
                <div class="metrics-grid">
    """
    
    # Filter ratios for Structure Financière (only specific 3 ratios)
    if computed_ratios:
        structure_ratios = [
            "gearing", "capacité de remboursement", "ratio de liquidité générale"
        ]
        
        filtered_ratios = {}
        for key, value in computed_ratios.items():
            key_lower = key.lower()
            if any(ratio in key_lower for ratio in structure_ratios):
                filtered_ratios[key] = value
        
        grouped_ratios = group_metrics_by_base_name(filtered_ratios, current_year, previous_year)
        
        # Debug output for ratios
        print(f"DEBUG: Filtered ratios for Structure: {list(filtered_ratios.keys())}")
        print(f"DEBUG: Grouped ratios: {grouped_ratios}")
        
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
            
            # Add current year box
            if 'current' in years_data:
                current_value = years_data['current']
                if is_percentage:
                    formatted_value = format_percentage(current_value)
                else:
                    formatted_value = format_financial_number(current_value)
                html_content += f"""
                        <div class="metric-year-box">
                            <div class="metric-year-value">{formatted_value}</div>
                            <div class="metric-year-label">({current_year})</div>
                        </div>
                """
            
            # Add previous year box
            if 'previous' in years_data:
                previous_value = years_data['previous']
                if is_percentage:
                    formatted_value = format_percentage(previous_value)
                else:
                    formatted_value = format_financial_number(previous_value)
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
    
    # Add structure financière analysis
    if detailed_analysis:
        html_content += f'<div class="analysis-text"><p>{detailed_analysis}</p></div>'
    
    html_content += """
            </div>
            
            <!-- Analyse de Rentabilité -->
            <div class="section">
                <h2><i class="fas fa-chart-line"></i> Analyse de Rentabilité</h2>
                <div class="metrics-grid">
    """
    
    # Filter for specific profitability metrics (only 5 indicators)
    profitability_indicators = [
        "marge opérationnelle", "rotation des actifs", "marge nette", "roe", "roce"
    ]
    
    # Combine KPIs and computed ratios for profitability analysis
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
    
    # Group profitability metrics by base name and display with both years
    if profitability_metrics:
        grouped_profitability = group_metrics_by_base_name(profitability_metrics, current_year, previous_year)
        
        # Debug output for profitability
        print(f"DEBUG: Filtered profitability metrics: {list(profitability_metrics.keys())}")
        print(f"DEBUG: Grouped profitability: {grouped_profitability}")
        
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
            
            # Add current year box
            if 'current' in years_data:
                current_value = years_data['current']
                if is_percentage:
                    formatted_value = format_percentage(current_value)
                else:
                    formatted_value = format_financial_number(current_value)
                html_content += f"""
                        <div class="metric-year-box">
                            <div class="metric-year-value">{formatted_value}</div>
                            <div class="metric-year-label">({current_year})</div>
                        </div>
                """
            
            # Add previous year box
            if 'previous' in years_data:
                previous_value = years_data['previous']
                if is_percentage:
                    formatted_value = format_percentage(previous_value)
                else:
                    formatted_value = format_financial_number(previous_value)
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
    
    # Add TVA Analysis section if data is available
    print(f"[TVA REPORT DEBUG] Checking if TVA analysis should be added: {bool(tva_analysis)}", flush=True)
    print(f"[TVA REPORT DEBUG] TVA analysis type: {type(tva_analysis)}", flush=True)
    print(f"[TVA REPORT DEBUG] TVA analysis empty check: {len(tva_analysis) if isinstance(tva_analysis, dict) else 'not dict'}", flush=True)
    
    if tva_analysis and isinstance(tva_analysis, dict) and len(tva_analysis) > 0:
        print(f"[TVA REPORT DEBUG] Adding TVA section to report", flush=True)
        html_content += """
            <!-- Cadrage de TVA -->
            <div class="section">
                <h2><i class="fas fa-receipt"></i> Cadrage de TVA</h2>
        """
        
        # Process TVA analysis data
        for tva_key, tva_data in tva_analysis.items():
            if isinstance(tva_data, dict):
                html_content += f"""
                <div class="tva-analysis-container" style="margin-bottom: 2rem;">
                    <h3 style="margin-bottom: 1rem; color: var(--primary); font-size: 1.2rem;">
                        <i class="fas fa-calculator"></i> Analyse TVA - Exercice {tva_key.replace('tva_analysis_', '')}
                    </h3>
                    
                    <!-- Données extraites -->
                    <div class="tva-data-grid" style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px; margin-bottom: 20px;">
                """
                
                # Display extracted TVA values
                tva_fields = [
                    ('tva_facturee', 'T.V.A. Facturée', True),
                    ('tva_pratique', 'T.V.A. Pratique', True),
                    ('clients_exercice_precedent', 'Clients Exercice Précédent', True),
                    ('clients_exercice_brut', 'Clients Exercice', True)
                ]
                
                for field_key, field_label, is_financial in tva_fields:
                    if field_key in tva_data and tva_data[field_key] is not None:
                        value = tva_data[field_key]
                        if is_financial:
                            formatted_value = format_financial_number(value)
                        else:
                            formatted_value = str(value)
                            
                        html_content += f"""
                        <div class="metric-card" style="text-align: center;">
                            <div class="metric-title" style="font-size: 0.9rem; margin-bottom: 10px;">{field_label}</div>
                            <div class="metric-year-value" style="color: var(--primary-dark);">{formatted_value}</div>
                        </div>
                        """
                
                html_content += """
                    </div>
                    
                    <!-- Calculs théoriques -->
                    <div class="tva-calculations" style="background: linear-gradient(135deg, #fef3c7 0%, #ffffff 100%); padding: 20px; border-radius: var(--border-radius); border: 1px solid rgba(245, 158, 11, 0.2);">
                        <h4 style="color: var(--primary-dark); margin-bottom: 15px; font-size: 1.1rem;">
                            <i class="fas fa-chart-pie"></i> Calculs Théoriques
                        </h4>
                """
                
                # Display calculated values
                if 'encaissement_theorique' in tva_data:
                    html_content += f"""
                        <div style="margin-bottom: 10px;">
                            <strong style="color: #000000;">Encaissement Théorique:</strong> <span style="color: #000000; font-weight: bold;">{format_financial_number(tva_data['encaissement_theorique'])}</span>
                            <br><small style="color: var(--text-light);">Formule: CA + TVA Facturée + Clients N-1 - Clients N</small>
                        </div>
                    """
                
                if 'tva_theorique' in tva_data:
                    html_content += f"""
                        <div style="margin-bottom: 10px;">
                            <strong style="color: #000000;">TVA Théorique:</strong> <span style="color: #000000; font-weight: bold;">{format_financial_number(tva_data['tva_theorique'])}</span>
                            <br><small style="color: var(--text-light);">Formule: Encaissement Théorique ÷ 6</small>
                        </div>
                    """
                
                # Display comparison
                if 'ecart_tva' in tva_data and 'ecart_tva_pourcentage' in tva_data:
                    ecart = tva_data['ecart_tva']
                    ecart_pct = tva_data['ecart_tva_pourcentage']
                    
                    # Determine color based on the difference
                    if ecart > 0:
                        color_class = "positive"
                        icon = "up"
                        interpretation = "TVA théorique supérieure à la TVA pratique"
                    else:
                        color_class = "negative" 
                        icon = "down"
                        interpretation = "TVA théorique inférieure à la TVA pratique"
                    
                    html_content += f"""
                        <div style="margin-top: 15px; padding: 15px; background: rgba(255, 255, 255, 0.8); border-radius: 8px; border-left: 4px solid var(--primary);">
                            <h5 style="color: var(--primary-dark); margin-bottom: 10px;">
                                <i class="fas fa-balance-scale"></i> Comparaison TVA Théorique vs Pratique
                            </h5>
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <div>
                                    <strong>Écart:</strong> {format_financial_number(ecart)}
                                    <br><strong>Pourcentage:</strong> 
                                    <span class="change {color_class}" style="display: inline-flex; align-items: center; gap: 4px;">
                                        {format_percentage(ecart_pct)} <i class="fas fa-arrow-{icon}"></i>
                                    </span>
                                </div>
                                <div style="text-align: right; font-size: 0.9rem; color: var(--text-light);">
                                    {interpretation}
                                </div>
                            </div>
                        </div>
                    """
                
                html_content += """
                    </div>
                </div>
                """
        
        html_content += """
            </div>
        """
    
    html_content += f"""
            
            <div class="footer">
                <p>Rapport généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}</p>
                <p>Expert Comptable - Analyse Financière Simplifiée</p>
            </div>
        </div>
        
        <script id="financial-data" type="application/json">
            {json.dumps({'kpis': kpis, 'computed_ratios': computed_ratios, 'tva_analysis': tva_analysis, 'fiscal_year': fiscal_year}, ensure_ascii=False, indent=2)}
        </script>
        <script>
            // This script will work for downloaded HTML files
            if (typeof window !== 'undefined' && window.document) {{
                document.addEventListener('DOMContentLoaded', function() {{
                    initializeFinancialTable();
                }});
            }}
            
            function initializeFinancialTable() {{
                const dataScript = document.getElementById('financial-data');
                if (!dataScript) return;
                
                const data = JSON.parse(dataScript.textContent);
                window.expertComptableData = data;
                generateFinancialDiagnosticTable();
            }}
            
            // Financial table generation functions
            function formatFinancialNumber(value) {{
                if (value == null || value === '' || isNaN(value)) return '-';
                const num = parseFloat(value);
                if (Math.abs(num) >= 1000000) {{
                    return (num / 1000000).toFixed(1).replace('.', ',') + 'M';
                }} else if (Math.abs(num) >= 1000) {{
                    return (num / 1000).toFixed(0).replace('.', ',') + 'K';
                }} else {{
                    return num.toFixed(0).replace('.', ',');
                }}
            }}
            
            function getKPIValue(kpiName, year = 'n') {{
                if (!window.expertComptableData) return null;
                
                const kpis = window.expertComptableData.kpis || {{}};
                const computedRatios = window.expertComptableData.computed_ratios || {{}};
                
                const yearMappings = {{
                    'n': 'N',
                    'n1': 'N-1', 
                    'n2': 'N-2'
                }};
                
                let normalizedYear = yearMappings[year] || year;
                
                // Try flat structure (computed_ratios)
                const flatKey = `${{kpiName}}_${{year}}`;
                if (computedRatios[flatKey] !== undefined) {{
                    return computedRatios[flatKey];
                }}
                
                // Try nested structure (extracted_kpis) with French mappings
                const kpiNameMappings = {{
                    'chiffre_d_affaires': "Chiffre d'affaires",
                    'resultat_net': 'Résultat Net',
                    'capitaux_propres': 'Capitaux propres',
                    'tresorerie_nette': 'Trésorerie nette',
                    'ebitda': 'EBITDA',
                    'dette_nette': 'Dette nette',
                    'bfr': 'BFR'
                }};
                
                const dbKey = kpiNameMappings[kpiName];
                if (dbKey && kpis[dbKey]) {{
                    return kpis[dbKey][normalizedYear] || null;
                }}
                
                return null;
            }}
            
            function renderCAGRCell(cagr) {{
                if (cagr == null || isNaN(cagr)) {{
                    return `<span class="change" style="font-size: 1.5em; text-align: center; width: 100%;">-</span>`;
                }}

                const isPositive = cagr >= 0;
                const formatted = cagr.toFixed(1).replace('.', ',');

                return `
                <span class="change ${{isPositive ? 'positive' : 'negative'}}">
                    ${{formatted}}% <i class="fas fa-arrow-${{isPositive ? 'up' : 'down'}}"></i>
                </span>`;
            }}
            
            function computeAndDisplayCAGR(kpiName, cellId) {{
                const current = getKPIValue(kpiName, 'n');
                const previous = getKPIValue(kpiName, 'n1');

                if (current != null && previous != null && !isNaN(current) && !isNaN(previous) && previous !== 0) {{
                    const cagr = ((current / previous) - 1) * 100;
                    const cell = document.getElementById(cellId);
                    if (cell) cell.innerHTML = renderCAGRCell(cagr);
                }} else {{
                    const cell = document.getElementById(cellId);
                    if (cell) cell.innerHTML = renderCAGRCell(null);
                }}
            }}
            
            function generateFinancialDiagnosticTable() {{
                const tbody = document.getElementById('financial-diagnostic-tbody');
                if (!tbody) return;
                
                const kpis = [
                    {{
                        name: 'Chiffre d\\'Affaires',
                        key: 'chiffre_d_affaires',
                        cagrId: 'revenue-cagr-cell'
                    }},
                    {{
                        name: 'EBITDA',
                        key: 'ebitda',
                        cagrId: 'ebitda-cagr-cell'
                    }},
                    {{
                        name: 'Résultat Net',
                        key: 'resultat_net',
                        cagrId: 'net_income-cagr-cell'
                    }},
                    {{
                        name: 'Trésorerie Nette',
                        key: 'tresorerie_nette',
                        cagrId: 'tresorerie-nette-cagr-cell'
                    }},
                    {{
                        name: 'Capitaux Propres',
                        key: 'capitaux_propres',
                        cagrId: 'equity-cagr-cell'
                    }},
                    {{
                        name: 'Dette Nette',
                        key: 'dette_nette',
                        cagrId: 'net_debt-cagr-cell'
                    }},
                    {{
                        name: 'BFR',
                        key: 'bfr',
                        cagrId: 'bfr-cagr-cell'
                    }}
                ];
                
                // Clear existing content
                tbody.innerHTML = '';
                
                kpis.forEach(kpi => {{
                    const row = document.createElement('tr');
                    
                    const valueN = getKPIValue(kpi.key, 'n');
                    const valueN1 = getKPIValue(kpi.key, 'n1');
                    
                    row.innerHTML = `
                        <td>${{kpi.name}}</td>
                        <td>${{formatFinancialNumber(valueN)}}</td>
                        <td>${{formatFinancialNumber(valueN1)}}</td>
                        <td id="${{kpi.cagrId}}"></td>
                    `;
                    
                    tbody.appendChild(row);
                }});
                
                // Calculate and display CAGR for each KPI
                kpis.forEach(kpi => {{
                    computeAndDisplayCAGR(kpi.key, kpi.cagrId);
                }});
            }}
        </script>
    </body>
    </html>
    """
    
    return html_content
