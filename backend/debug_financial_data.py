#!/usr/bin/env python3
"""
Debug script to check financial data structure and identify why KPIs are not showing in the report.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import CompanyProfile
import json

def debug_financial_data_structure():
    """Debug the financial data structure in the database."""
    print("="*60)
    print("DEBUGGING FINANCIAL DATA STRUCTURE")
    print("="*60)
    
    try:
        with app.app_context():
            # Get all profiles
            profiles = CompanyProfile.query.all()
            
            if not profiles:
                print("❌ No profiles found in database")
                return
            
            print(f"🔍 Found {len(profiles)} profiles in database")
            
            for i, profile in enumerate(profiles):
                print(f"\n📋 Profile {i+1}: {profile.company_name} (ID: {profile.id})")
                print(f"   Status: {profile.status}")
                
                if profile.profile_data:
                    print(f"   Profile data keys: {list(profile.profile_data.keys())}")
                    
                    # Check for extracted KPIs
                    extracted_kpis = profile.profile_data.get('extracted_kpis')
                    print(f"   Extracted KPIs type: {type(extracted_kpis)}")
                    if extracted_kpis:
                        print(f"   Extracted KPIs keys: {list(extracted_kpis.keys())}")
                        # Show first few KPIs as example
                        kpi_examples = list(extracted_kpis.keys())[:5]
                        for kpi in kpi_examples:
                            print(f"     {kpi}: {extracted_kpis[kpi]}")
                    else:
                        print("   ❌ No extracted KPIs found")
                    
                    # Check for computed ratios
                    computed_ratios = profile.profile_data.get('computed_ratios')
                    print(f"   Computed ratios type: {type(computed_ratios)}")
                    if computed_ratios:
                        print(f"   Computed ratios keys: {list(computed_ratios.keys())}")
                        # Show first few ratios as example
                        ratio_examples = list(computed_ratios.keys())[:5]
                        for ratio in ratio_examples:
                            print(f"     {ratio}: {computed_ratios[ratio]}")
                    else:
                        print("   ❌ No computed ratios found")
                    
                    # Check for web data
                    web_data = profile.profile_data.get('web_data')
                    print(f"   Web data type: {type(web_data)}")
                    if web_data:
                        print(f"   Web data keys: {list(web_data.keys())}")
                    else:
                        print("   ❌ No web data found")
                        
                else:
                    print("   ❌ No profile data found")
                    
                # Only show first 3 profiles to avoid overwhelming output
                if i >= 2:
                    print("   ... (showing only first 3 profiles)")
                    break
                    
    except Exception as e:
        print(f"❌ Error during debugging: {e}")
        import traceback
        traceback.print_exc()

def debug_specific_profile(profile_id):
    """Debug a specific profile's data structure."""
    print("="*60)
    print(f"DEBUGGING SPECIFIC PROFILE: {profile_id}")
    print("="*60)
    
    try:
        with app.app_context():
            profile = CompanyProfile.query.get(profile_id)
            
            if not profile:
                print(f"❌ Profile {profile_id} not found")
                return
            
            print(f"📋 Profile: {profile.company_name}")
            print(f"   Status: {profile.status}")
            
            if profile.profile_data:
                print(f"   Profile data keys: {list(profile.profile_data.keys())}")
                
                # Detailed analysis of financial data
                extracted_kpis = profile.profile_data.get('extracted_kpis')
                print(f"\n📊 Extracted KPIs Analysis:")
                if extracted_kpis:
                    print(f"   Type: {type(extracted_kpis)}")
                    print(f"   Keys count: {len(extracted_kpis.keys())}")
                    print(f"   All keys: {list(extracted_kpis.keys())}")
                    
                    # Show sample data structure
                    for key, value in extracted_kpis.items():
                        print(f"     {key}: {type(value)} = {value}")
                        # Only show first 5 to avoid overwhelming output
                        if list(extracted_kpis.keys()).index(key) >= 4:
                            print(f"     ... (showing only first 5 KPIs)")
                            break
                else:
                    print("   ❌ No extracted KPIs found")
                
                computed_ratios = profile.profile_data.get('computed_ratios')
                print(f"\n📈 Computed Ratios Analysis:")
                if computed_ratios:
                    print(f"   Type: {type(computed_ratios)}")
                    print(f"   Keys count: {len(computed_ratios.keys())}")
                    print(f"   All keys: {list(computed_ratios.keys())}")
                    
                    # Show sample data structure
                    for key, value in computed_ratios.items():
                        print(f"     {key}: {type(value)} = {value}")
                        # Only show first 5 to avoid overwhelming output
                        if list(computed_ratios.keys()).index(key) >= 4:
                            print(f"     ... (showing only first 5 ratios)")
                            break
                else:
                    print("   ❌ No computed ratios found")
                    
            else:
                print("   ❌ No profile data found")
                
    except Exception as e:
        print(f"❌ Error during debugging: {e}")
        import traceback
        traceback.print_exc()

def debug_template_data_simulation(profile_id):
    """Simulate how the template data would be structured for a specific profile."""
    print("="*60)
    print(f"DEBUGGING TEMPLATE DATA SIMULATION: {profile_id}")
    print("="*60)
    
    try:
        with app.app_context():
            profile = CompanyProfile.query.get(profile_id)
            
            if not profile:
                print(f"❌ Profile {profile_id} not found")
                return
            
            profile_data = profile.profile_data or {}
            extracted_kpis = profile_data.get('extracted_kpis')
            computed_ratios = profile_data.get('computed_ratios')
            web_data = profile_data.get('web_data', {})
            company_name = profile_data.get('company_name') or profile.company_name
            
            print(f"📋 Company: {company_name}")
            
            # Simulate the template data structure (from app.py)
            basic_info = web_data.get('basic_info', {})
            company_overview = basic_info.get('companyOverview', {})
            
            template_data = {
                'company_name': company_name,
                'extracted_kpis': extracted_kpis or {},
                'computed_ratios': computed_ratios or {},
                'companyOverview': {
                    'companyFoundationyear': company_overview.get('companyFoundationyear', 'Non spécifié'),
                    'companyExpertise': company_overview.get('companyExpertise', 'À déterminer'),
                    'primary_sector': company_overview.get('primary_sector', 'Secteur général'),
                    'legal_form': company_overview.get('legal_form', 'SARL'),
                    'companyDefinition': company_overview.get('companyDefinition', f'Entreprise {company_name}'),
                    'staff_count': company_overview.get('staff_count', 'À préciser')
                }
            }
            
            print(f"\n📊 Template Data Structure:")
            print(f"   Template data keys: {list(template_data.keys())}")
            
            print(f"\n📈 Financial Data in Template:")
            print(f"   Extracted KPIs count: {len(template_data.get('extracted_kpis', {}))}")
            print(f"   Computed ratios count: {len(template_data.get('computed_ratios', {}))}")
            
            if template_data.get('extracted_kpis'):
                print(f"   Sample KPIs:")
                kpi_samples = list(template_data['extracted_kpis'].keys())[:3]
                for kpi in kpi_samples:
                    print(f"     {kpi}: {template_data['extracted_kpis'][kpi]}")
            
            if template_data.get('computed_ratios'):
                print(f"   Sample Ratios:")
                ratio_samples = list(template_data['computed_ratios'].keys())[:3]
                for ratio in ratio_samples:
                    print(f"     {ratio}: {template_data['computed_ratios'][ratio]}")
                    
            # Check if data would be available for JavaScript
            print(f"\n🔧 JavaScript Data Availability:")
            print(f"   Data would be passed to JavaScript: {bool(template_data.get('extracted_kpis') or template_data.get('computed_ratios'))}")
            
            if template_data.get('extracted_kpis'):
                print(f"   Sample KPI structure for JS: {type(template_data['extracted_kpis'])}")
                # Show a sample structure
                sample_kpi = list(template_data['extracted_kpis'].keys())[0] if template_data['extracted_kpis'] else None
                if sample_kpi:
                    print(f"   Sample: {sample_kpi} = {template_data['extracted_kpis'][sample_kpi]}")
                    
    except Exception as e:
        print(f"❌ Error during debugging: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Run all financial data debugging."""
    print("🐛 FINANCIAL DATA DEBUGGING")
    print("Identifying why KPIs are not showing in the report")
    
    try:
        # Debug all profiles
        debug_financial_data_structure()
        
        # If you want to debug a specific profile, uncomment and modify the line below
        # debug_specific_profile("your-profile-id-here")
        
        # Simulate template data for the first profile
        with app.app_context():
            profiles = CompanyProfile.query.limit(1).all()
            if profiles:
                debug_template_data_simulation(profiles[0].id)
        
        print("\n" + "="*60)
        print("✅ FINANCIAL DATA DEBUGGING COMPLETED")
        print("="*60)
        print("\n💡 Common issues to check:")
        print("   1. Are extracted_kpis and computed_ratios present in profile_data?")
        print("   2. Are the data structures correct (dict vs list vs string)?")
        print("   3. Is the data being passed correctly to the template?")
        print("   4. Is the JavaScript accessing the data correctly?")
        
    except Exception as e:
        print(f"\n❌ Debug failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
