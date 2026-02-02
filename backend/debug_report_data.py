#!/usr/bin/env python3
"""
Debug script to check the report data structure and identify foundation year issues.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.web_exploring import web_explorer_agent, enhance_with_bizafrix_data
from services.bizafrix_web import get_company_info_from_bizafrix

def debug_report_data_structure():
    """Debug the complete report data structure."""
    print("="*60)
    print("DEBUGGING REPORT DATA STRUCTURE")
    print("="*60)
    
    company_name = "Group 4 Securicor"
    print(f"🔍 Testing complete data flow for: {company_name}")
    
    try:
        # Step 1: Get web exploration data
        print("\n1️⃣ Step 1: Getting web exploration data...")
        web_result = web_explorer_agent(company_name)
        
        if web_result and 'basic_info' in web_result:
            basic_info = web_result['basic_info']
            print("✅ Web exploration completed")
            
            # Check basic info structure
            print(f"   Basic info keys: {list(basic_info.keys())}")
            
            if 'companyOverview' in basic_info:
                overview = basic_info['companyOverview']
                print(f"   Company overview keys: {list(overview.keys())}")
                print(f"   Foundation year (basic): {overview.get('companyFoundationyear', 'NOT FOUND')}")
                print(f"   Legal form (basic): {overview.get('legal_form', 'NOT FOUND')}")
            else:
                print("   ❌ No companyOverview in basic_info")
        else:
            print("❌ Web exploration failed")
            return
        
        # Step 2: Test Bizafrix enhancement separately
        print("\n2️⃣ Step 2: Testing Bizafrix enhancement...")
        
        # Create a minimal basic info to test enhancement
        test_basic_info = {
            'companyOverview': {
                'companyFoundationyear': "Non spécifié",
                'companyExpertise': "Test",
                'primary_sector': "Test",
                'legal_form': "SARL",
                'companyDefinition': "Test company",
                'staff_count': "À préciser"
            },
            'sectors': [],
            'markets': [],
            'keyPeople': [],
            'contact': {
                'phone': "Non disponible",
                'email': "Non disponible",
                'address': "Adresse à préciser",
                'website': "Non disponible"
            }
        }
        
        enhanced_info = enhance_with_bizafrix_data(test_basic_info, company_name)
        
        if 'companyOverview' in enhanced_info:
            enhanced_overview = enhanced_info['companyOverview']
            print(f"   Enhanced foundation year: {enhanced_overview.get('companyFoundationyear', 'NOT FOUND')}")
            print(f"   Enhanced legal form: {enhanced_overview.get('legal_form', 'NOT FOUND')}")
        else:
            print("   ❌ No companyOverview in enhanced_info")
        
        # Step 3: Simulate the template data structure
        print("\n3️⃣ Step 3: Simulating template data structure...")
        
        # This is how the data is structured in app.py
        template_data = {
            'company_name': company_name,
            'companyOverview': {
                'companyFoundationyear': basic_info.get('companyOverview', {}).get('companyFoundationyear', 'Non spécifié'),
                'companyExpertise': basic_info.get('companyOverview', {}).get('companyExpertise', 'À déterminer'),
                'primary_sector': basic_info.get('companyOverview', {}).get('primary_sector', 'Secteur général'),
                'legal_form': basic_info.get('companyOverview', {}).get('legal_form', 'SARL'),
                'companyDefinition': basic_info.get('companyOverview', {}).get('companyDefinition', f'Entreprise {company_name}'),
                'staff_count': basic_info.get('companyOverview', {}).get('staff_count', 'À préciser')
            }
        }
        
        print(f"   Template foundation year: {template_data['companyOverview']['companyFoundationyear']}")
        print(f"   Template legal form: {template_data['companyOverview']['legal_form']}")
        
        # Step 4: Check if the issue is in the template rendering
        print("\n4️⃣ Step 4: Testing template rendering simulation...")
        
        # Simulate what the template would render
        header_foundation_year = template_data['companyOverview']['companyFoundationyear']
        overview_foundation_year = template_data['companyOverview']['companyFoundationyear']
        
        print(f"   Header would render: {header_foundation_year}")
        print(f"   Overview would render: {overview_foundation_year}")
        
        if header_foundation_year == overview_foundation_year:
            print("   ✅ Both locations should render the same value")
        else:
            print("   ❌ Values are different - this shouldn't happen")
            
        # Step 5: Check if the issue is with empty values
        print("\n5️⃣ Step 5: Checking for empty or null values...")
        
        if not header_foundation_year or header_foundation_year.strip() == "":
            print("   ⚠️ Foundation year is empty or null")
        elif header_foundation_year == "Non spécifié":
            print("   ⚠️ Foundation year is default value 'Non spécifié'")
        else:
            print(f"   ✅ Foundation year has a value: '{header_foundation_year}'")
        
        # Step 6: Test Bizafrix data directly
        print("\n6️⃣ Step 6: Testing Bizafrix data directly...")
        
        bizafrix_data = get_company_info_from_bizafrix(company_name)
        
        if bizafrix_data and 'companyOverview' in bizafrix_data:
            bizafrix_overview = bizafrix_data['companyOverview']
            bizafrix_foundation_year = bizafrix_overview.get('companyFoundationyear', 'NOT FOUND')
            print(f"   Bizafrix foundation year: {bizafrix_foundation_year}")
            
            if bizafrix_foundation_year and bizafrix_foundation_year != "Non spécifié":
                print("   ✅ Bizafrix has a valid foundation year")
            else:
                print("   ⚠️ Bizafrix foundation year is missing or default")
        else:
            print("   ❌ No Bizafrix data or company overview")
        
    except Exception as e:
        print(f"❌ Error during debugging: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Run the debug script."""
    print("🐛 REPORT DATA DEBUGGING")
    print("Identifying why foundation year doesn't show in company overview section")
    
    try:
        debug_report_data_structure()
        
        print("\n" + "="*60)
        print("✅ DEBUGGING COMPLETED")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ Debug failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
