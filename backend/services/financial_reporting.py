import os
import json
import anthropic
import openai
from dotenv import load_dotenv
from typing import Dict, Any, Optional

load_dotenv()

def extract_json_from_response(response_text: str) -> str:
    """
    Extract JSON content from a response that may be wrapped in markdown code blocks.
    
    Args:
        response_text (str): The raw response text from the LLM
        
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

# Initialize OpenAI client
# Initialize Anthropic client
# anthropic_key = os.getenv("ANTHROPIC_API_KEY")
# client = anthropic.Anthropic(api_key=anthropic_key) if anthropic_key else None
openai_key = os.getenv("OPENAI_API_KEY")
client = openai.OpenAI(api_key=openai_key) if openai_key else None

def generate_financial_analysis(
    company_name: str,
    extracted_kpis: Dict[str, Any],
    computed_ratios: Dict[str, Any],
    news_data: str,
    web_data: Dict[str, Any],
    fiscal_year: Optional[str] = None) -> Dict[str, Any]:
    """
    Generate comprehensive financial analysis including SWOT, recommendations, 
    detailed analysis using all previously collected data.
    
    Args:
        company_name: Name of the company
        extracted_kpis: KPIs extracted from financial documents
        computed_ratios: Financial ratios computed from KPIs
        news_data: News analysis from news_retrieving
        web_data: Basic company info from web_exploring (excluding analysis sections)
        fiscal_year: Fiscal year for the analysis (e.g., "2023", "2022-2023")
    
    Returns:
        Dictionary containing SWOT analysis, recommendation, and detailed analysis
    """
    
    # Validate input data
    print(f"🔍 Validating input data for {company_name}")
    print(f"🔍 News data type: {type(news_data)}, length: {len(str(news_data))}")
    
    if not client:
        print("❌ OpenAI API key not available, cannot generate financial analysis")
        return {
            "swot_analysis": {
                "strengths": [],
                "weaknesses": [],
                "opportunities": [],
                "threats": []
            },
            "recommendation": "Analyse financière indisponible - clé API OpenAI manquante",
            "detailed_analysis": "Impossible de générer l'analyse financière sans clé API OpenAI"
        }
    
    try:
        # Prepare the comprehensive prompt for all analysis sections
        system_prompt = """Tu es un analyste financier expert spécialisé dans l'analyse d'entreprises marocaines.

        Ta mission est de générer une analyse financière complète et professionnelle basée sur toutes les données disponibles :
        - KPIs financiers extraits des documents
        - Ratios financiers calculés
        - Actualités et veille sectorielle
        - Informations de base de l'entreprise (secteur, marchés, expertise)

        Tu dois générer 3 sections distinctes en français :

        1. ANALYSE SWOT : Forces, faiblesses, opportunités, menaces
        2. RECOMMANDATION STRATÉGIQUE : Générer une recommandation détaillée et complète qui intègre synthèse, évaluation globale et conseils stratégiques
        3. ANALYSE DÉTAILLÉE : Analyse approfondie de la structure financière, incluant l'équilibre dette/capitaux propres, la santé financière, et la capacité de couverture du coût du capital

        Utilise TOUTES les données disponibles pour une analyse cohérente et factuelle.

        Pour la RECOMMANDATION, génère un paragraphe détaillé de 8-10 lignes qui intègre :
        - Une synthèse de la situation financière
        - L'évaluation globale de la performance
        - Des conseils stratégiques concrets et actionables
        - La justification basée sur les données financières réelles

        IMPORTANT : Retourne UNIQUEMENT un objet JSON valide, sans texte avant ou après."""

        # Prepare the data context for the LLM
        # Safely extract and format data
        try:
            # Ensure web_data is not None and has basic_info
            web_data = web_data or {}
            basic_info = web_data.get('basic_info') or {}
            company_overview = basic_info.get('companyOverview') or {}
            
            primary_sector = company_overview.get('primary_sector', 'Non spécifié')
            company_expertise = company_overview.get('companyExpertise', 'Non spécifié')
            markets = basic_info.get('markets', [])
            sectors = basic_info.get('sectors', [])
            
            markets_text = ', '.join([str(m.get('title', '')) for m in (markets or []) if m and isinstance(m, dict)])
            sectors_text = ', '.join([str(s.get('title', '')) for s in (sectors or []) if s and isinstance(s, dict)])
            
            kpis_text = json.dumps(extracted_kpis, indent=2, ensure_ascii=False) if extracted_kpis and isinstance(extracted_kpis, dict) else 'Aucun KPI disponible'
            ratios_text = json.dumps(computed_ratios, indent=2, ensure_ascii=False) if computed_ratios and isinstance(computed_ratios, dict) else 'Aucun ratio calculé'
            news_text = str(news_data) if news_data else 'Aucune actualité disponible'
            
        except Exception as data_error:
            print(f"⚠️ Error formatting data: {str(data_error)}, using fallback")
            return generate_fallback_analysis(company_name, extracted_kpis, computed_ratios, news_data, web_data, fiscal_year)
        
        # Add fiscal year information to guide the LLM
        fiscal_year_info = ""
        if fiscal_year:
            fiscal_year_info = f"\n        ANNÉE FISCALE : {fiscal_year}\n"
            # Add guidance about using actual years instead of N/N-1
            fiscal_year_info += f"        IMPORTANT : Utilise l'année {fiscal_year} dans tes recommandations et analyses, pas 'N' ou 'N-1'.\n"

        data_context = f"""COMPAGNIE : {company_name}

        INFORMATIONS DE BASE :
        - Secteur principal : {primary_sector}
        - Expertise : {company_expertise}
        - Marchés : {markets_text}
        - Secteurs d'activité : {sectors_text}
        
        ANNÉE FISCALE : {fiscal_year_info}
        KPIs FINANCIERS EXTRACTES :
        {kpis_text}

        RATIOS FINANCIERS CALCULES :
        {ratios_text}

        ACTUALITÉS ET VEILLE SECTORIELLE :
        {news_text}

        GÉNÈRE UNE RÉPONSE JSON AVEC CETTE STRUCTURE EXACTE :
        {{
        "swot_analysis": {{
            "strengths": ["Force 1", "Force 2", "Force 3"],
            "weaknesses": ["Faiblesse 1", "Faiblesse 2", "Faiblesse 3"],
            "opportunities": ["Opportunité 1", "Opportunité 2", "Opportunité 3"],
            "threats": ["Menace 1", "Menace 2", "Menace 3"]
        }},
        "recommendation": "Recommandation stratégique détaillée et complète (8-10 lignes) intégrant synthèse, évaluation globale et conseils stratégiques",
        "detailed_analysis": "Analyse détaillée de la structure financière"
        }}

        Base ton analyse sur les données financières réelles et les indicateurs calculés qui sont toujours en MAD. Sois précis et factuel.
        IMPORTANT : Retourne UNIQUEMENT le JSON, sans texte avant ou après."""

        # Debug: Log what we're sending to the LLM
        print(f"🔍 Sending prompt to LLM - System prompt length: {len(system_prompt)} chars")
        print(f"🔍 Data context length: {len(data_context)} chars")
        print(f"🔍 Total prompt length: {len(system_prompt) + len(data_context)} chars")
        
        # Check if data is too long and truncate if necessary
        max_context_length = 100000  # Claude has a large context window, but let's be safe
        if len(data_context) > max_context_length:
            print(f"⚠️ Data context too long ({len(data_context)} chars), truncating to {max_context_length} chars")
            data_context = data_context[:max_context_length] + "\n\n[DATA TRONQUÉ POUR RESPECTER LES LIMITES]"
        
        # Sanitize the data context to avoid potential issues
        data_context = data_context.replace('\x00', '')  # Remove null bytes
        data_context = data_context.replace('\r', '\n')  # Normalize line endings
        
        # Call the LLM
        # response = client.messages.create(
        #     model="claude-sonnet-4-20250514",
        #     max_tokens=4000,
        #     temperature=0.1,
        #     system=system_prompt,
        #     messages=[{"role": "user", "content": data_context}]
        response = client.chat.completions.create(
            model="gpt-5",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": data_context}
            ]
        )
        
        # Parse the response
        response_text = response.choices[0].message.content.strip()
        
        # Debug: Log the raw response
        print(f"🔍 Raw LLM response length: {len(response_text)} characters")
        print(f"🔍 Raw LLM response preview: {response_text[:200]}...")
        
        try:
            # Try to extract JSON from the response - be more robust
            analysis_data = None
            
            # First try direct parse
            try:
                analysis_data = json.loads(response_text)
                print("✅ Direct JSON parse successful")
            except json.JSONDecodeError:
                print("⚠️ Direct JSON parse failed, trying to extract JSON from markdown...")
                
                # Extract JSON from markdown code blocks if present
                json_text = extract_json_from_response(response_text)
                if json_text != response_text:
                    try:
                        analysis_data = json.loads(json_text)
                        print("✅ JSON extraction from markdown successful")
                    except json.JSONDecodeError:
                        print("⚠️ JSON extraction from markdown failed, trying regex...")
                        
                        # Try to find JSON in the response using regex as fallback
                        import re
                        json_pattern = r'\{[\s\S]*\}'
                        json_matches = re.findall(json_pattern, response_text)
                        
                        if json_matches:
                            print(f"🔍 Found {len(json_matches)} potential JSON blocks")
                            for i, match in enumerate(json_matches):
                                try:
                                    analysis_data = json.loads(match)
                                    print(f"✅ JSON extraction successful from block {i+1}")
                                    break
                                except json.JSONDecodeError:
                                    print(f"⚠️ JSON block {i+1} failed to parse")
                                    continue
                        else:
                            print("⚠️ No JSON pattern found in response")
                else:
                    print("⚠️ No markdown code blocks found, trying regex...")
                    
                    # Try to find JSON in the response using regex as fallback
                    import re
                    json_pattern = r'\{[\s\S]*\}'
                    json_matches = re.findall(json_pattern, response_text)
                    
                    if json_matches:
                        print(f"🔍 Found {len(json_matches)} potential JSON blocks")
                        for i, match in enumerate(json_matches):
                            try:
                                analysis_data = json.loads(match)
                                print(f"✅ JSON extraction successful from block {i+1}")
                                break
                            except json.JSONDecodeError:
                                print(f"⚠️ JSON block {i+1} failed to parse")
                                continue
                    else:
                        print("⚠️ No JSON pattern found in response")
            
            if analysis_data:
                # Validate the structure
                required_keys = ['swot_analysis', 'recommendation', 'detailed_analysis']
                missing_keys = [key for key in required_keys if key not in analysis_data]
                
                if missing_keys:
                    print(f"⚠️ Missing keys in LLM response: {missing_keys}, using fallback")
                    return generate_fallback_analysis(company_name, extracted_kpis, computed_ratios, news_data, web_data, fiscal_year)
                
                print(f"✅ Financial analysis generated successfully for {company_name}")
                return analysis_data
            else:
                print("⚠️ Could not extract valid JSON from LLM response, trying simpler prompt...")
                
                # Try with a simpler prompt
                try:
                    simple_prompt = f"""Analyse la situation financière de {company_name} et génère un JSON avec cette structure exacte:

                    {{
                    "swot_analysis": {{
                        "strengths": ["Force 1", "Force 2", "Force 3"],
                        "weaknesses": ["Faiblesse 1", "Faiblesse 2", "Faiblesse 3"],
                        "opportunities": ["Opportunité 1", "Opportunité 2", "Opportunité 3"],
                        "threats": ["Menace 1", "Menace 2", "Menace 3"]
                    }},
                    "recommendation": "Recommandation stratégique simple et détaillée",
                    "detailed_analysis": "Analyse détaillée de la structure financière simple"
                    }}

                    Retourne uniquement le JSON."""
                    
                    print("🔄 Trying simpler prompt...")
                    simple_response = client.chat.completions.create(
                        model="gpt-5",
                        messages=[{"role": "user", "content": simple_prompt}]
                    )
                    
                    simple_text = simple_response.choices[0].message.content.strip()
                    print(f"🔍 Simple prompt response: {simple_text[:200]}...")
                    
                    # Try to parse the simple response
                    try:
                        # Extract JSON from markdown code blocks if present
                        json_text = extract_json_from_response(simple_text)
                        simple_analysis = json.loads(json_text)
                        required_keys = ['swot_analysis', 'recommendation', 'detailed_analysis']
                        missing_keys = [key for key in required_keys if key not in simple_analysis]
                        
                        if not missing_keys:
                            print("✅ Simple prompt successful!")
                            return simple_analysis
                        else:
                            print(f"⚠️ Simple prompt missing keys: {missing_keys}")
                    except json.JSONDecodeError:
                        print("⚠️ Simple prompt also failed to parse")
                        
                except Exception as simple_error:
                    print(f"❌ Simple prompt also failed: {str(simple_error)}")
                
                print("⚠️ All LLM attempts failed, using fallback analysis")
                return generate_fallback_analysis(company_name, extracted_kpis, computed_ratios, news_data, web_data, fiscal_year)
            
        except Exception as parse_error:
            print(f"❌ Error parsing LLM response: {str(parse_error)}, using fallback")
            return generate_fallback_analysis(company_name, extracted_kpis, computed_ratios, news_data, web_data, fiscal_year)
            
    except Exception as e:
        print(f"❌ Error generating financial analysis: {str(e)}")
        # Only use fallback for specific errors, not all errors
        if "API" in str(e) or "key" in str(e).lower() or "unauthorized" in str(e).lower():
            print("❌ API-related error, returning error response instead of fallback")
            return {
                "swot_analysis": {
                    "strengths": [],
                    "weaknesses": [],
                    "opportunities": [],
                    "threats": []
                },
                "recommendation": f"Erreur API: {str(e)}",
                "detailed_analysis": f"Impossible de générer l'analyse financière: {str(e)}"
            }
        else:
            print("⚠️ Non-API error, using fallback analysis")
            return generate_fallback_analysis(company_name, extracted_kpis, computed_ratios, news_data, web_data, fiscal_year)

def generate_fallback_analysis(
    company_name: str,
    extracted_kpis: Dict[str, Any],
    computed_ratios: Dict[str, Any],
    news_data: str,
    web_data: Dict[str, Any],
    fiscal_year: Optional[str] = None) -> Dict[str, Any]:
    """
    Fallback function that generates basic analysis when LLM is unavailable.
    Handles all 3 elements: SWOT, recommendation, and detailed analysis.
    """
    
    print(f"🔄 Using fallback analysis for {company_name}")
    
    # Extract basic company info with proper None checks
    web_data = web_data or {}
    basic_info = web_data.get('basic_info') or {}
    company_overview = basic_info.get('companyOverview') or {}
    primary_sector = company_overview.get('primary_sector', 'Secteur général')
    company_expertise = company_overview.get('companyExpertise', 'Expertise à déterminer')
    
    # Basic SWOT analysis based on available data
    swot_analysis = {
        'strengths': [
            f'Position établie dans le secteur {primary_sector}',
            f'Expertise reconnue en {company_expertise}',
            'Structure financière documentée'
        ],
        'weaknesses': [
            'Données financières limitées',
            'Analyse approfondie nécessaire',
            'Contexte concurrentiel à évaluer'
        ],
        'opportunities': [
            'Potentiel de croissance identifié',
            'Marchés en développement',
            'Partenariats stratégiques possibles'
        ],
        'threats': [
            'Concurrence sectorielle',
            'Évolution réglementaire',
            'Risques économiques'
        ]
    }
    
    # Enhanced recommendation that includes synthesis and strategic advice
    recommendation = f"""Basé sur l'analyse des données disponibles pour {company_name}, nous recommandons une approche prudente et structurée qui intègre une évaluation globale de la performance financière. La société présente des indicateurs financiers dans le secteur {primary_sector} qui nécessitent une analyse plus approfondie pour identifier précisément les leviers de croissance et les axes d'amélioration prioritaires. 

    L'évaluation globale révèle un potentiel de développement qui mérite une attention particulière, notamment en termes d'optimisation de la structure financière et d'exploitation des opportunités sectorielles. Il est recommandé de compléter cette analyse par une étude de marché détaillée, une évaluation des opportunités de développement, et la mise en place d'un plan d'action stratégique adapté aux spécificités du secteur {primary_sector}. 

    Cette approche permettra de maximiser le potentiel de croissance tout en maintenant une gestion financière rigoureuse et adaptée aux enjeux du marché."""
    
    # Basic detailed analysis
    detailed_analysis = f"""L'analyse détaillée de la structure financière de {company_name} révèle une entreprise positionnée dans le secteur {primary_sector} avec une expertise en {company_expertise}.

    Les données financières disponibles permettent d'identifier les indicateurs clés de performance, mais une analyse plus approfondie est nécessaire pour évaluer l'équilibre dette/capitaux propres, la santé financière, et la capacité de couverture du coût du capital.

    Cette analyse préliminaire constitue une base solide pour des investigations plus approfondies et des recommandations stratégiques ciblées."""
    
    return {
        'swot_analysis': swot_analysis,
        'recommendation': recommendation,
        'detailed_analysis': detailed_analysis
    }
