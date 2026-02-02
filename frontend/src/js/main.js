// Load the new data structure
const data = JSON.parse(document.getElementById('report-data').textContent);
const extractedKPIs = data.extracted_kpis || {};
const computedRatios = data.computed_ratios || {};
const companyName = data.company_name || 'Company';
const swotAnalysis = data.swot_analysis || {};
const fiscalYears = data.fiscal_years || null;

console.log('Loaded data:', { extractedKPIs, computedRatios, companyName, swotAnalysis, fiscalYears });

// Debug: Log the actual data structure
console.log('Full data structure:', data);
console.log('Data keys:', Object.keys(data));
console.log('extracted_kpis keys:', Object.keys(extractedKPIs));
console.log('computed_ratios keys:', Object.keys(computedRatios));

// Check if we have the expected data
if (Object.keys(extractedKPIs).length === 0 && Object.keys(computedRatios).length === 0) {
    console.error('❌ No financial data found! This is why the report is empty.');
    console.error('Expected extracted_kpis and computed_ratios to contain data.');
    console.error('Full data object:', data);
} else {
    console.log('✅ Financial data found, proceeding with population...');
    console.log('📊 Data summary:');
    console.log(`   - extractedKPIs: ${Object.keys(extractedKPIs).length} keys`);
    console.log(`   - computedRatios: ${Object.keys(computedRatios).length} keys`);
    
    // Show sample of extracted KPIs
    if (Object.keys(extractedKPIs).length > 0) {
        console.log('📊 Sample extracted KPIs:');
        const sampleKeys = Object.keys(extractedKPIs).slice(0, 3);
        sampleKeys.forEach(key => {
            console.log(`   - ${key}:`, extractedKPIs[key]);
        });
    }
}
// computed data
// const RatioCurrent = financialData.current_assets["2023"] / financialData.current_liabilities["2023"];

// --- UTILITY FUNCTIONS ---
function getKPIValue(kpiName, year = 'n') {
    // Get KPI value from extracted KPIs or computed ratios
    
    // Normalize year parameter to handle multi-year structure
    let normalizedYear = year;
    const yearMappings = {
        'n': 'N',
        'n1': 'N-1', 
        'n2': 'N-2',
        'n3': 'N-3',
        'n4': 'N-4',
        'n5': 'N-5'
    };
    
    if (yearMappings[year]) {
        normalizedYear = yearMappings[year];
    }
    
    // First try the flat structure (computed_ratios)
    const flatKey = `${kpiName}_${year}`;
    if (computedRatios[flatKey] !== undefined) {
        console.log(`✅ Found ${kpiName} in computed_ratios[${flatKey}]:`, computedRatios[flatKey]);
        return computedRatios[flatKey];
    }
    
    // Special handling for EBITDA - calculate it from available data
    if (kpiName === 'ebitda') {
        return calculateEBITDA(normalizedYear);
    }
    
    // Special handling for BFR - calculate it from available data
    if (kpiName === 'bfr') {
        return calculateBFR(normalizedYear);
    }
    
    // Then try the nested structure (extracted_kpis)
    // Map French names to the actual keys in the database
    const kpiNameMappings = {
        'chiffre_d_affaires': "Chiffre d'affaires",
        'resultat_net': 'Résultat Net',
        'capitaux_propres': 'Capitaux propres',
        'resultat_d_exploitation': 'Résultat d\'exploitation',
        'dotations_d_exploitation': 'Dotations d\'exploitation',
        'reprises_d_exploitation': 'Reprises d\'exploitation; transferts de charges',
        'redevances_credit_bail': 'Redevances de crédit-bail',
        'tresorerie_actif': 'Trésorerie-Actif',
        'titres_valeurs_placement': 'Titres Valeurs de placement',
        'dettes_financement': 'Dettes de financement',
        'tresorerie_passif': 'Trésorerie-passif',
        'tresorerie_nette': 'Trésorerie nette',
        'comptes_associes_actif': 'Compte d\'associés (Actif)',
        'comptes_associes_passif': 'Compte d\'associés (Passif)',
        'redevances_moins_un_an': 'Redevances restant à payer (a moins d\'un an)',
        'redevances_plus_un_an': 'Redevances restant à payer (a plus d\'un an)',
        'prix_achat_residuel': 'Prix d\'achat résiduel en fin du contrat',
        'actif_circulant': 'Actif circulant',
        'passif_circulant': 'Passif circulant',
        'actif_circulant_total': 'Actif circulant total'
    };
    
    const dbKey = kpiNameMappings[kpiName];
    if (dbKey && extractedKPIs[dbKey]) {
        const value = extractedKPIs[dbKey][normalizedYear] || null;
        console.log(`✅ Found ${kpiName} in extractedKPIs[${dbKey}][${normalizedYear}]:`, value);
        return value;
    }
    
    // Debug: Log what we're looking for and what we have
    console.log(`🔍 Looking for KPI: ${kpiName}, year: ${year} (normalized: ${normalizedYear})`);
    console.log(`🔍 Flat key tried: ${flatKey}`);
    console.log(`🔍 DB key tried: ${dbKey}`);
    console.log(`🔍 Available computed_ratios keys:`, Object.keys(computedRatios));
    console.log(`🔍 Available extractedKPIs keys:`, Object.keys(extractedKPIs));
    
    // Enhanced debugging: Show exact structure of extractedKPIs
    if (extractedKPIs && Object.keys(extractedKPIs).length > 0) {
        console.log(`🔍 Full extractedKPIs structure:`, extractedKPIs);
        console.log(`🔍 First few extractedKPIs entries:`);
        const firstKeys = Object.keys(extractedKPIs).slice(0, 5);
        firstKeys.forEach(key => {
            console.log(`🔍   ${key}:`, extractedKPIs[key]);
        });
    } else {
        console.log(`🔍 extractedKPIs is empty or null!`);
    }
    
    // Additional debugging: Show the exact structure of extractedKPIs
    if (extractedKPIs && Object.keys(extractedKPIs).length > 0) {
        console.log(`🔍 First few extractedKPIs entries:`);
        const firstKeys = Object.keys(extractedKPIs).slice(0, 5);
        firstKeys.forEach(key => {
            console.log(`🔍   ${key}:`, extractedKPIs[key]);
        });
    }
    
    // Final fallback: Try to find the KPI by searching through all keys
    if (extractedKPIs && Object.keys(extractedKPIs).length > 0) {
        console.log(`🔍 Final fallback: Searching for KPI pattern in all keys...`);
        
        // Try to find a key that contains the KPI name (case-insensitive)
        const searchPattern = kpiName.toLowerCase().replace(/_/g, ' ');
        for (const [key, value] of Object.entries(extractedKPIs)) {
            if (key.toLowerCase().includes(searchPattern) || searchPattern.includes(key.toLowerCase())) {
                console.log(`🔍 Found potential match: ${key} for ${kpiName}`);
                if (typeof value === 'object' && value !== null && normalizedYear in value) {
                    console.log(`✅ Fallback found ${kpiName} in ${key}[${normalizedYear}]:`, value[normalizedYear]);
                    return value[normalizedYear];
                }
            }
        }
    }
    
    return null;
}

// Calculate EBITDA from available data
function calculateEBITDA(year) {
    try {
        // EBITDA = Résultat d'exploitation + Dotations d'exploitation - Reprises d'exploitation
        const resultatExploitation = extractedKPIs[`Résultat d'exploitation`]?.[year] || 0;
        const dotationsExploitation = extractedKPIs[`Dotations d'exploitation`]?.[year] || 0;
        const reprisesExploitation = extractedKPIs[`Reprises d'exploitation; transferts de charges`]?.[year] || 0;
        
        const ebitda = resultatExploitation + dotationsExploitation - reprisesExploitation;
        console.log(`🧮 Calculated EBITDA for ${year}: ${resultatExploitation} + ${dotationsExploitation} - ${reprisesExploitation} = ${ebitda}`);
        
        return ebitda;
    } catch (error) {
        console.error(`❌ Error calculating EBITDA for ${year}:`, error);
        return null;
    }
}

// Calculate BFR from available data
function calculateBFR(year) {
    try {
        // BFR = Actif circulant - Passif circulant
        const actifCirculant = extractedKPIs[`Actif circulant`]?.[year] || 0;
        const passifCirculant = extractedKPIs[`Passif circulant`]?.[year] || 0;
        
        const bfr = actifCirculant - passifCirculant;
        console.log(`🧮 Calculated BFR for ${year}: ${actifCirculant} - ${passifCirculant} = ${bfr}`);
        
        return bfr;
    } catch (error) {
        console.error(`❌ Error calculating BFR for ${year}:`, error);
        return null;
    }
}

// Get current year information for display
function getCurrentYearInfo() {
    // First try to use the fiscal year from the data
    if (fiscalYears) {
        if (fiscalYears.includes('-')) {
            // Range format like "2022-2023" - use the later year as current
            return fiscalYears.split('-')[1] || fiscalYears.split('-')[0];
        } else {
            // Single year format like "2023"
            return fiscalYears;
        }
    }
    
    // Try to get the actual year from the data structure
    if (extractedKPIs && Object.keys(extractedKPIs).length > 0) {
        // Look for any KPI that has year data to determine the current year
        const firstKPI = Object.values(extractedKPIs)[0];
        if (firstKPI && typeof firstKPI === 'object') {
            const years = Object.keys(firstKPI);
            if (years.length > 0) {
                // Return the most recent year (usually 'N' or the actual year)
                return years[0];
            }
        }
    }
    
    // Fallback to generic year reference
    return 'Année N';
}

// Get available years from the data structure
function getAvailableYears() {
    // Check if we have multi-document metadata
    if (computedRatios && computedRatios._metadata && computedRatios._metadata.available_years) {
        return computedRatios._metadata.available_years;
    }
    
    // Check if we have extracted KPIs metadata
    if (extractedKPIs && extractedKPIs._metadata && extractedKPIs._metadata.available_years) {
        return extractedKPIs._metadata.available_years;
    }
    
    // If we have fiscal years, use them to generate actual year labels
    if (fiscalYears) {
        console.log('Using fiscal years to generate year labels:', fiscalYears);
        if (fiscalYears.includes('-')) {
            // Range format like "2022-2023"
            const years = fiscalYears.split('-');
            const result = [years[0], years[1] || years[0]]; // Previous year, Current year
            console.log('Generated year labels from range:', result);
            return result;
        } else {
            // Single year format like "2023"
            const currentYear = fiscalYears;
            const previousYear = String(parseInt(currentYear) - 1);
            const result = [previousYear, currentYear];
            console.log('Generated year labels from single year:', result);
            return result;
        }
    }
    
    // Default to N and N-1 for single document
    return ['N', 'N-1'];
}

// Replace year placeholders (N, N-1, etc.) with actual years based on fiscal year
function replaceYearPlaceholders() {
    if (!fiscalYears) {
        console.log('No fiscal years data available, keeping default placeholders');
        return;
    }
    
    console.log('Replacing year placeholders with fiscal years:', fiscalYears);
    console.log('Fiscal years type:', typeof fiscalYears);
    console.log('Fiscal years value:', fiscalYears);
    
    // Parse fiscal years - could be single year "2023" or range "2022-2023"
    let currentYear, previousYear;
    
    if (fiscalYears.includes('-')) {
        // Range format like "2022-2023"
        const years = fiscalYears.split('-');
        currentYear = years[1] || years[0]; // Use the later year as current
        previousYear = years[0];
    } else {
        // Single year format like "2023"
        currentYear = fiscalYears;
        previousYear = String(parseInt(currentYear) - 1);
    }
    
    console.log(`Mapped years - Current: ${currentYear}, Previous: ${previousYear}`);
    
    // Replace placeholders in the table headers
    const tableHeaders = document.querySelectorAll('.financial-table thead th');
    tableHeaders.forEach(header => {
        if (header.textContent.includes('N (MAD)')) {
            header.textContent = header.textContent.replace('N (MAD)', `${currentYear}`);
        }
        if (header.textContent.includes('N-1 (MAD)')) {
            header.textContent = header.textContent.replace('N-1 (MAD)', `${previousYear}`);
        }
        if (header.textContent.includes('CAGR (N)')) {
            header.textContent = header.textContent.replace('CAGR (N)', `CAGR (${currentYear})`);
        }
    });
    
    // Replace placeholders in chart titles and other text elements
    const chartTitles = document.querySelectorAll('.chart-title');
    chartTitles.forEach(title => {
        if (title.textContent.includes('2023')) {
            title.textContent = title.textContent.replace('2023', currentYear);
        }
        if (title.textContent.includes('(N)')) {
            title.textContent = title.textContent.replace('(N)', `(${currentYear})`);
        }
    });
    
    // Replace placeholders in metric labels
    const metricLabels = document.querySelectorAll('.metric-label');
    metricLabels.forEach(label => {
        if (label.textContent.includes('(N)')) {
            label.textContent = label.textContent.replace('(N)', `(${currentYear})`);
        }
        if (label.textContent.includes('(N-1)')) {
            label.textContent = label.textContent.replace('(N-1)', `(${previousYear})`);
        }
    });
    
    // Replace placeholders in header stat labels
    const headerStatLabels = document.querySelectorAll('.header-stat p');
    headerStatLabels.forEach(label => {
        if (label.textContent.includes('(N)')) {
            label.textContent = label.textContent.replace('(N)', `(${currentYear})`);
        }
    });
    
    console.log('Year placeholders replaced successfully');
}

// Check if this is multi-document data
function isMultiDocument() {
    return (computedRatios && computedRatios._metadata && computedRatios._metadata.multi_document && computedRatios._metadata.multi_document.is_multi_document) ||
           (extractedKPIs && extractedKPIs._metadata && extractedKPIs._metadata.total_documents > 1);
}

function computeAndDisplayCAGR(kpiName, cellId) {
    // Compute and display CAGR between N and N-1
    const current = getKPIValue(kpiName, 'n');
    const previous = getKPIValue(kpiName, 'n1');

    if (current != null && previous != null && !isNaN(current) && !isNaN(previous) && previous !== 0) {
        // CAGR formula: CAGR = (Vf/Vi)^(1/n) - 1
        // For year-over-year: n = 1, so CAGR = (Vf/Vi) - 1
        const cagr = ((current / previous) - 1) * 100;
        document.getElementById(cellId).innerHTML = renderCAGRCell(cagr);
    } else {
        document.getElementById(cellId).innerHTML = renderCAGRCell(null);
    }
}
function renderCAGRCell(cagr) {
    if (cagr == null || isNaN(cagr)) {
        return `<span class="change" style="font-size: 1.5em; text-align: center; width: 100%;">-</span>`;
    }

    const isPositive = cagr >= 0;
    const formatted = cagr.toFixed(1).replace('.', ',');

    return `
    <span class="change ${isPositive ? 'positive' : 'negative'}">
        ${formatted}% <i class="fas fa-arrow-${isPositive ? 'up' : 'down'}"></i>
    </span>`;
}    

// Generate dynamic financial table based on available years
function generateFinancialTable() {
    const availableYears = getAvailableYears();
    const isMultiDoc = isMultiDocument();
    
    console.log('Generating table for years:', availableYears, 'Multi-document:', isMultiDoc);
    
    // Find the financial table
    const financialTable = document.querySelector('.financial-table tbody');
    if (!financialTable) {
        console.error('❌ Financial table not found - cannot populate data');
        return;
    }
    
    console.log('✅ Found financial table, proceeding with population...');
    
    // Clear existing content
    financialTable.innerHTML = '';
    
    // Create table header dynamically
    const thead = document.querySelector('.financial-table thead tr');
    if (thead) {
        thead.innerHTML = '<th>Indicateur Clé</th>';
        
        // Add year columns (reverse order to show newest first)
        const reversedYears = [...availableYears].reverse();
        reversedYears.forEach(year => {
            // Replace generic year labels with actual fiscal years if available
            let displayYear = year;
            if (fiscalYears && year === 'N') {
                if (fiscalYears.includes('-')) {
                    displayYear = fiscalYears.split('-')[1] || fiscalYears.split('-')[0];
                } else {
                    displayYear = fiscalYears;
                }
            } else if (fiscalYears && year === 'N-1') {
                if (fiscalYears.includes('-')) {
                    displayYear = fiscalYears.split('-')[0];
                } else {
                    displayYear = String(parseInt(fiscalYears) - 1);
                }
            }
            thead.innerHTML += `<th>${displayYear} (MAD)</th>`;
        });
        
        // Add CAGR column (only between most recent years)
        let cagrHeader = 'CAGR (%)';
        if (fiscalYears) {
            if (fiscalYears.includes('-')) {
                const currentYear = fiscalYears.split('-')[1] || fiscalYears.split('-')[0];
                cagrHeader = `CAGR (${currentYear})`;
            } else {
                cagrHeader = `CAGR (${fiscalYears})`;
            }
        }
        thead.innerHTML += `<th>${cagrHeader}</th>`;
    }
    
    // Define the KPIs to display
    const kpis = [
        {
            name: 'Chiffre d\'Affaires',
            key: 'chiffre_d_affaires',
            tooltip: 'Revenus totaux générés par les activités ordinaires de l\'entreprise.',
            cagrId: 'revenue-cagr-cell'
        },
        {
            name: 'EBITDA',
            key: 'ebitda',
            tooltip: 'Bénéfice avant intérêts, impôts, dépréciation et amortissement.',
            cagrId: 'ebitda-cagr-cell'
        },
        {
            name: 'Résultat Net',
            key: 'resultat_net',
            tooltip: 'Bénéfice net après impôts.',
            cagrId: 'net_income-cagr-cell'
        },
        {
            name: 'Trésorerie Nette',
            key: 'tresorerie_nette',
            tooltip: 'Trésorerie (Actif) - Trésorerie (Passif).',
            cagrId: 'tresorerie-nette-cagr-cell'
        },
        {
            name: 'Capitaux Propres',
            key: 'capitaux_propres',
            tooltip: 'Valeur nette des actifs de l\'entreprise.',
            cagrId: 'equity-cagr-cell'
        },
        {
            name: 'Dette Nette',
            key: 'dette_nette',
            tooltip: 'Dette financière totale moins la trésorerie.',
            cagrId: 'net_debt-cagr-cell'
        },
        {
            name: 'BFR',
            key: 'bfr',
            tooltip: 'Besoin en Fonds de Roulement = Actif circulant - Passif circulant.',
            cagrId: 'bfr-cagr-cell'
        }
    ];
    
    console.log('📊 Populating table with KPIs:', kpis.map(k => k.key));
    
    // Generate table rows
    kpis.forEach(kpi => {
        const row = document.createElement('tr');
        
        // KPI name column with tooltip
        row.innerHTML = `<td data-tooltip="${kpi.tooltip}">${kpi.name}</td>`;
        
        // Year columns (reverse order to show newest first)
        const reversedYears = [...availableYears].reverse();
        reversedYears.forEach((year, index) => {
            const yearKey = year.toLowerCase().replace('-', '');
            const value = getKPIValue(kpi.key, yearKey);
            const cellId = `${kpi.key}-${yearKey}`;
            
            console.log(`📈 KPI ${kpi.key} for year ${yearKey}:`, value);
            
            row.innerHTML += `<td data-key="${kpi.key}"><span id="${cellId}">${formatFinancialNumber(value)}</span></td>`;
        });
        
        // CAGR column
        row.innerHTML += `<td id="${kpi.cagrId}"></td>`;
        
        financialTable.appendChild(row);
    });
    
    console.log('Financial table generated successfully');
}

// Populate financial data in the report
function populateFinancialData() {
    // Generate dynamic table first
    generateFinancialTable();
    
    // Populate header stats (always use most recent year - N)
    const chiffreAffairesN = getKPIValue('chiffre_d_affaires', 'n');
    const revenueHeaderElement = document.getElementById('revenue-N-cell');
    if (revenueHeaderElement) revenueHeaderElement.textContent = formatFinancialNumber(chiffreAffairesN);
    
    // Generate financial insights paragraph
    generateFinancialInsights();
    

    
    console.log('Financial data populated successfully');
}

// Generate dynamic financial insights paragraph
function generateFinancialInsights() {
    console.log("📊 Generating financial insights...");
    
    try {
        // Get key financial data
        const revenueN = getKPIValue('chiffre_d_affaires', 'n') || 0;
        const revenueN1 = getKPIValue('chiffre_d_affaires', 'n1') || 0;
        const revenueN2 = getKPIValue('chiffre_d_affaires', 'n2') || 0;
        const ebitdaN = getKPIValue('ebitda', 'n') || 0;
        const revenueN_prev = getKPIValue('chiffre_d_affaires', 'n1') || 0;
        
        // Calculate growth rate if we have at least 2 years of data
        let cagrText = "";
        if (revenueN > 0 && revenueN1 > 0) {
            const growthRate = ((revenueN - revenueN1) / revenueN1) * 100;
            if (Math.abs(growthRate) < 1) {
                cagrText = "stabilité";
            } else if (growthRate > 0) {
                cagrText = `croissance de ${Math.abs(growthRate).toFixed(1)}%`;
            } else {
                cagrText = `contraction de ${Math.abs(growthRate).toFixed(1)}%`;
            }
        } else if (revenueN > 0 && revenueN1 === 0) {
            cagrText = "croissance (données N-1 non disponibles)";
        } else if (revenueN === 0 && revenueN1 > 0) {
            cagrText = "contraction (données N non disponibles)";
        } else {
            cagrText = "évolution à analyser (données insuffisantes)";
        }
        
        // Calculate EBITDA margin
        let ebitdaMarginText = "";
        let profitabilityText = "";
        if (ebitdaN > 0 && revenueN > 0) {
            const ebitdaMargin = (ebitdaN / revenueN) * 100;
            ebitdaMarginText = `${ebitdaMargin.toFixed(1)}%`;
            
            // Determine profitability trend
            const ebitdaN1 = getKPIValue('ebitda', 'n1') || 0;
            const revenueN1_prev = getKPIValue('chiffre_d_affaires', 'n1') || 0;
            
            if (ebitdaN1 > 0 && revenueN1_prev > 0) {
                const marginN1 = (ebitdaN1 / revenueN1_prev) * 100;
                const marginChange = ebitdaMargin - marginN1;
                
                if (Math.abs(marginChange) < 0.5) {
                    profitabilityText = "stable";
                } else if (marginChange > 0.5) {
                    profitabilityText = "en progression";
                } else {
                    profitabilityText = "sous pression";
                }
            } else if (ebitdaN > 0 && revenueN > 0) {
                // If we only have current year data, assess based on absolute margin
                if (ebitdaMargin > 15) {
                    profitabilityText = "solide";
                } else if (ebitdaMargin > 8) {
                    profitabilityText = "correcte";
                } else if (ebitdaMargin > 0) {
                    profitabilityText = "modeste";
                } else {
                    profitabilityText = "déficitaire";
                }
            } else {
                profitabilityText = "à évaluer";
            }
        } else {
            ebitdaMarginText = "N/A";
            profitabilityText = "à évaluer";
        }
        
        // Generate the insights text
        let insightsText = `Sur la période traitée, l'entreprise affiche une ${cagrText}. La marge EBITDA s'établit à ${ebitdaMarginText}, traduisant une rentabilité ${profitabilityText}.`;
        
        // Add additional context if available
        if (revenueN > 0) {
            const revenueFormatted = formatFinancialNumber(revenueN, 'MAD');
            insightsText += ` Le chiffre d'affaires s'élève à ${revenueFormatted}.`;
        }
        
        // Update the DOM
        const insightsElement = document.getElementById('financial-insights-text');
        if (insightsElement) {
            insightsElement.textContent = insightsText;
            console.log("✅ Financial insights generated:", insightsText);
        } else {
            console.warn("⚠️ Financial insights element not found");
        }
        
    } catch (error) {
        console.error("❌ Error generating financial insights:", error);
        const insightsElement = document.getElementById('financial-insights-text');
        if (insightsElement) {
            insightsElement.textContent = "Analyse de performance en cours de génération...";
        }
    }
}



function formatFinancialNumber(num, currency = "MAD") {
    if (num === null || num === undefined || isNaN(parseFloat(num))) {
        return "N/A";
    }
    const number = parseFloat(num);
    if (Math.abs(number) >= 1000000) {
        return (number / 1000000).toFixed(1).replace('.', ',') + " M " + currency;
    }
    if (Math.abs(number) >= 1000) {
        return (number / 1000).toFixed(1).replace('.', ',') + " K " + currency;
    }
    return number.toFixed(1).replace('.', ',') + " " + currency;
}
function formatPercentage(num) {
    if (num === null || num === undefined || isNaN(parseFloat(num))) {
        return "N/A";
    }
    return parseFloat(num).toFixed(1).replace('.', ',') + "%";
}

// Populate SWOT Analysis
function populateSWOTAnalysis() {
    // Populate strengths
    const strengthsList = document.getElementById('strength-list');
    if (strengthsList && swotAnalysis.strengths) {
        strengthsList.innerHTML = '';
        swotAnalysis.strengths.forEach(strength => {
            const li = document.createElement('li');
            li.textContent = strength;
            strengthsList.appendChild(li);
        });
    }
    
    // Populate weaknesses (mapped to risk-list in template)
    const risksList = document.getElementById('risk-list');
    if (risksList && swotAnalysis.weaknesses) {
        risksList.innerHTML = '';
        swotAnalysis.weaknesses.forEach(weakness => {
            const li = document.createElement('li');
            li.textContent = weakness;
            risksList.appendChild(li);
        });
    }
    
    // Populate opportunities
    const opportunitiesList = document.getElementById('opportunity-list');
    if (opportunitiesList && swotAnalysis.opportunities) {
        opportunitiesList.innerHTML = '';
        swotAnalysis.opportunities.forEach(opportunity => {
            const li = document.createElement('li');
            li.textContent = opportunity;
            opportunitiesList.appendChild(li);
        });
    }
    
    // Populate threats
    const threatsList = document.getElementById('threat-list');
    if (threatsList && swotAnalysis.threats) {
        threatsList.innerHTML = '';
        swotAnalysis.threats.forEach(threat => {
            const li = document.createElement('li');
            li.textContent = threat;
            threatsList.appendChild(li);
        });
    }
}

// Populate KPI metrics
function populateKPIMetrics() {
    console.log("📊 Populating KPI metrics...");
    
    // Calculate missing ratios from available data
    const ratios = calculateMissingRatios();
    
            // Populate individual metric elements
        const metricMappings = {
            'operatingmargin': 'marge_exploitation', 
            'netmargin': 'marge_nette',
            'roe': 'roe',
            'roce': 'roce',
            'gearing': 'gearing',
            'gearin': 'gearing',
            'rotation_actifs': 'rotation_actifs'
        };
    
    for (const [elementId, ratioKey] of Object.entries(metricMappings)) {
        const element = document.getElementById(elementId);
        if (element) {
            const value = ratios[ratioKey];
            element.textContent = formatPercentage(value);
            console.log(`✅ Populated ${elementId} with ${ratioKey}: ${value}`);
        } else {
            console.warn(`⚠️ Element ${elementId} not found`);
        }
    }
    
    // Populate header net margin
    const netMarginHeaderElement = document.getElementById('netmargin-2023-cell');
    if (netMarginHeaderElement) {
        const netMargin = ratios['marge_nette'];
        netMarginHeaderElement.textContent = formatPercentage(netMargin);
        console.log(`✅ Header net margin populated: ${netMargin}`);
    }
    
            // Populate specific ratio elements (only the ones we want to calculate)
        const ratioDebtEquityElement = document.querySelector('[data-key="ratio_debt_equity"]');
        if (ratioDebtEquityElement) {
            // Use the computed capacite_remboursements ratio instead of calculating manually
            const capaciteRemboursements = getKPIValue('capacite_remboursements', 'n');
            if (capaciteRemboursements !== null) {
                // Take absolute value and round to nearest integer for user-friendly display
                const absoluteValue = Math.abs(capaciteRemboursements);
                const roundedValue = Math.round(absoluteValue);
                ratioDebtEquityElement.textContent = roundedValue + ' années';
                console.log(`✅ Capacité de remboursements populated: ${roundedValue} années`);
            } else {
                ratioDebtEquityElement.textContent = 'N/A';
                console.warn(`⚠️ Cannot find capacite_remboursements ratio`);
            }
        }
        
        // Populate Ratio de liquidité générale
        const ratioLiquiditeGeneraleElement = document.querySelector('[data-key="ratio_liquidite_generale"]');
        if (ratioLiquiditeGeneraleElement) {
            const actifCirculant = getKPIValue('actif_circulant', 'n');
            const passifCirculant = getKPIValue('passif_circulant', 'n');
            
            if (actifCirculant !== null && passifCirculant !== null && passifCirculant !== 0) {
                const ratioLiquidite = (actifCirculant / passifCirculant).toFixed(2);
                ratioLiquiditeGeneraleElement.textContent = ratioLiquidite.replace('.', ',');
                console.log(`✅ Ratio de liquidité générale populated: ${ratioLiquidite}`);
            } else {
                ratioLiquiditeGeneraleElement.textContent = 'N/A';
                console.warn(`⚠️ Cannot calculate ratio de liquidité générale: actif_circulant=${actifCirculant}, passif_circulant=${passifCirculant}`);
            }
        }
    
    // Populate Trésorerie Nette
    const tresorerieNetteElement = document.getElementById('tresorerie-nette');
    if (tresorerieNetteElement) {
        let tresorerieNette = getKPIValue('tresorerie_nette', 'n');
        
        // If direct value not available, calculate from components
        if (tresorerieNette === null) {
            const tresorerieActif = getKPIValue('tresorerie_actif', 'n');
            const tresoreriePassif = getKPIValue('tresorerie_passif', 'n');
            
            if (tresorerieActif !== null && tresoreriePassif !== null) {
                tresorerieNette = tresorerieActif - tresoreriePassif;
                console.log(`🧮 Calculated Trésorerie Nette from components: ${tresorerieActif} - ${tresoreriePassif} = ${tresorerieNette}`);
            }
        }
        
        if (tresorerieNette !== null) {
            // Format the value and add visual indication for negative values
            const formattedValue = formatFinancialNumber(tresorerieNette, 'MAD');
            tresorerieNetteElement.textContent = formattedValue;
            
            // Add visual styling for negative values (treasury deficit)
            const yearInfo = getCurrentYearInfo();
            if (tresorerieNette < 0) {
                tresorerieNetteElement.style.color = 'var(--danger)';
                tresorerieNetteElement.title = `Déficit de trésorerie (${yearInfo})`;
            } else if (tresorerieNette > 0) {
                tresorerieNetteElement.style.color = 'var(--success)';
                tresorerieNetteElement.title = `Excédent de trésorerie (${yearInfo})`;
            } else {
                tresorerieNetteElement.style.color = 'var(--text-light)';
                tresorerieNetteElement.title = `Trésorerie équilibrée (${yearInfo})`;
            }
            
            // Update the label to show the actual year
            const labelElement = tresorerieNetteElement.parentElement.querySelector('.metric-label');
            if (labelElement) {
                labelElement.textContent = `Trésorerie Nette (${yearInfo})`;
            }
            
            console.log(`✅ Trésorerie Nette populated: ${tresorerieNette}`);
        } else {
            tresorerieNetteElement.textContent = 'N/A';
            tresorerieNetteElement.style.color = 'var(--text-light)';
            console.warn(`⚠️ Cannot find Trésorerie Nette data or calculate from components`);
        }
    }
    
    const ratioCurrentElement = document.querySelector('[data-key="ratio_current"]');
    if (ratioCurrentElement) {
        const actifCirculant = getKPIValue('actif_circulant', 'n');
        const passifCirculant = getKPIValue('passif_circulant', 'n');
        if (actifCirculant !== null && passifCirculant !== null && passifCirculant !== 0) {
            const value = (actifCirculant / passifCirculant).toFixed(2);
            ratioCurrentElement.textContent = value.toString().replace('.', ',');
            console.log(`✅ Current ratio populated: ${value}`);
        } else {
            ratioCurrentElement.textContent = 'N/A';
            console.warn(`⚠️ Cannot calculate current ratio: actif_circulant=${actifCirculant}, passif_circulant=${passifCirculant}`);
        }
    }
}

// Calculate missing ratios from available data
function calculateMissingRatios() {
    const ratios = {};
    
    try {
        // Get current year data (N)
        const chiffreAffaires = getKPIValue('chiffre_d_affaires', 'n') || 0;
        const resultatNet = getKPIValue('resultat_net', 'n') || 0;
        const resultatExploitation = getKPIValue('resultat_d_exploitation', 'n') || 0;
        const capitauxPropres = getKPIValue('capitaux_propres', 'n') || 0;
        const detteNette = getKPIValue('dette_nette', 'n') || 0;
        
        // Calculate EBITDA
        const ebitda = calculateEBITDA('N') || 0;
        
        // Calculate ratios
        ratios['marge_ebitda'] = chiffreAffaires > 0 ? (ebitda / chiffreAffaires) * 100 : 0;
        ratios['marge_exploitation'] = chiffreAffaires > 0 ? (resultatExploitation / chiffreAffaires) * 100 : 0;
        ratios['marge_nette'] = chiffreAffaires > 0 ? (resultatNet / chiffreAffaires) * 100 : 0;
        ratios['roe'] = capitauxPropres > 0 ? (resultatNet / capitauxPropres) * 100 : 0;
        ratios['roce'] = capitauxPropres > 0 ? (resultatExploitation / capitauxPropres) * 100 : 0;
        ratios['gearing'] = capitauxPropres > 0 ? (detteNette / capitauxPropres) * 100 : 0;
        
        // Calculate Rotation des actifs = CA année N / [(Actif circulant total N + Actif circulant total N-1) / 2]
        const actifCirculantTotalN = getKPIValue('actif_circulant_total', 'n') || 0;
        const actifCirculantTotalN1 = getKPIValue('actif_circulant_total', 'n1') || 0;
        const actifCirculantTotalMoyen = (actifCirculantTotalN + actifCirculantTotalN1) / 2;
        ratios['rotation_actifs'] = actifCirculantTotalMoyen > 0 ? (chiffreAffaires / actifCirculantTotalMoyen) : 0;
        
        console.log("🧮 Calculated ratios:", ratios);
        
    } catch (error) {
        console.error("❌ Error calculating ratios:", error);
        // Provide fallback values
        ratios['marge_ebitda'] = 0;
        ratios['marge_exploitation'] = 0;
        ratios['marge_nette'] = 0;
        ratios['roe'] = 0;
        ratios['roce'] = 0;
        ratios['gearing'] = 0;
    }
    
    return ratios;
}


// --- INITIALIZATION AND EVENT HANDLERS ---
window.onload = function() {
    // Log library availability for debugging
    console.log("Libraries Loaded:", {
        ChartJS: !!window.Chart,
        gsap: !!window.gsap,
        ScrollTrigger: !!window.ScrollTrigger
    });

    // Initialize animations
    initAnimations();

    // Replace year placeholders with actual fiscal years
    replaceYearPlaceholders();

    // Check if we have data before proceeding
    if (Object.keys(extractedKPIs).length === 0 && Object.keys(computedRatios).length === 0) {
        console.warn("⚠️ No financial data found, attempting fallback population...");
        populateFallbackData();
    } else {
        // Populate financial data using new structure
        populateFinancialData();
        populateKPIMetrics();
        populateSWOTAnalysis();
        populateKeyPeople();
    }

    // Compute and display CAGR using French KPI names
    computeAndDisplayCAGR("chiffre_d_affaires", "revenue-cagr-cell");
    computeAndDisplayCAGR("ebitda", "ebitda-cagr-cell");
    computeAndDisplayCAGR("resultat_net", "net_income-cagr-cell");
    computeAndDisplayCAGR("tresorerie_nette", "tresorerie-nette-cagr-cell");
    computeAndDisplayCAGR("capitaux_propres", "equity-cagr-cell");
    computeAndDisplayCAGR("dette_nette", "net_debt-cagr-cell");
    computeAndDisplayCAGR("bfr", "bfr-cagr-cell");

    // Update financial insights after CAGR calculations
    generateFinancialInsights();
    


    // Initialize buttons
    initButtons();

    // Initialize charts
    if (window.Chart) {
        initCharts();
    } else {
        console.error("Chart.js library not loaded. Charts cannot be initialized.");
        ['revenueChart', 'ebtDebtChart', 'metricsChart', 'gearingChart'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.parentElement.innerHTML = "<p style='text-align:center; color:var(--danger);'>Erreur: Bibliothèque de graphiques non chargée.</p>";
        });
    }
};

// Fallback data population function for testing
function populateFallbackData() {
    console.log("🔄 Attempting fallback data population...");
    
    // Try to populate the financial table with sample data
    const financialTable = document.querySelector('.financial-table tbody');
    if (financialTable) {
        console.log("✅ Found financial table, populating with fallback data...");
        
        // Clear existing content
        financialTable.innerHTML = '';
        
        // Add a test row
        const testRow = document.createElement('tr');
        testRow.innerHTML = `
            <td data-tooltip="Test data">Test KPI</td>
            <td data-key="test">1000 MAD</td>
            <td data-key="test">900 MAD</td>
            <td id="test-cagr">+11.1%</td>
        `;
        financialTable.appendChild(testRow);
        
        console.log("✅ Fallback data populated successfully");
    } else {
        console.error("❌ Financial table not found for fallback population");
    }
    
    // Try to populate header stats
    const revenueHeader = document.getElementById('revenue-N-cell');
    if (revenueHeader) {
        revenueHeader.textContent = "1000 MAD";
        console.log("✅ Header revenue populated with fallback data");
    }
    
    const netMarginHeader = document.getElementById('netmargin-2023-cell');
    if (netMarginHeader) {
        netMarginHeader.textContent = "10.0%";
        console.log("✅ Header net margin populated with fallback data");
    }
}

/*Initializes GSAP animations.*/
function initAnimations() {
    try {
        if (!window.gsap || !window.ScrollTrigger) {
            console.warn("GSAP or ScrollTrigger not loaded. Animations will not run.");
            return;
        }
        gsap.registerPlugin(ScrollTrigger);

        gsap.from('.header-content h1', { duration: 1, opacity: 0, y: 50, ease: 'power3.out', delay: 0.2 });
        gsap.from('.header-content p', { duration: 1, opacity: 0, y: 40, ease: 'power3.out', delay: 0.4 });
        
        gsap.fromTo('.header-stat',
            { opacity: 0, y: 30 }, 
            { opacity: 1, y: 0, duration: 0.8, stagger: 0.2, ease: 'power2.out', delay: 0.7 }
        );
        
        gsap.from('.company-indicator', { duration: 1, opacity: 0, scale:0.5, ease: 'back.out(1.7)', delay: 1 });
        gsap.to(".header-pattern", { yPercent: 20, ease: "none", scrollTrigger: { trigger: "header", start: "top top", end: "bottom top", scrub: true } });

        gsap.utils.toArray('section, .card:not(.strategic-card), .strategic-card, .chart-container, .info-card, .contact-item').forEach(el => {
            gsap.from(el, { opacity: 0, y: 30, duration: 0.6, ease: 'power2.out', scrollTrigger: { trigger: el, start: 'top 85%', toggleActions: 'play none none none', once: true } });
        });
        gsap.utils.toArray('.metric-card').forEach((card, i) => {
            gsap.from(card, { opacity: 0, y: 20, duration: 0.5, delay: i * 0.05, scrollTrigger: { trigger: card, start: 'top 90%', toggleActions: 'play none none none', once: true } });
        });
    } catch (error) {
        console.error("Error initializing animations:", error);
    }
}
/* Initializes all charts*/
function initCharts() {
    // Get dynamic multi-year data
    const availableYears = getAvailableYears();
    const isMultiDoc = isMultiDocument();
    
    console.log('Initializing charts for years:', availableYears, 'Multi-document:', isMultiDoc);
    
    // Create year labels and data arrays (reverse order for oldest to newest display)
    const yearLabels = [...availableYears].reverse().map(year => {
        // Replace generic year labels with actual fiscal years if available
        if (fiscalYears && year === 'N') {
            if (fiscalYears.includes('-')) {
                return fiscalYears.split('-')[1] || fiscalYears.split('-')[0];
            } else {
                return fiscalYears;
            }
        } else if (fiscalYears && year === 'N-1') {
            if (fiscalYears.includes('-')) {
                return fiscalYears.split('-')[0];
            } else {
                return String(parseInt(fiscalYears) - 1);
            }
        }
        return year;
    });
    
    const primaryColor = getComputedStyle(document.documentElement).getPropertyValue('--primary').trim();
    const successColor = getComputedStyle(document.documentElement).getPropertyValue('--success').trim();
    const warningColor = getComputedStyle(document.documentElement).getPropertyValue('--warning').trim();
    const textLightColor = getComputedStyle(document.documentElement).getPropertyValue('--text-light').trim();

    // --- Revenue Chart with EBITDA Margin (Combo Bar/Line) ---
    try {
        const revenueCtx = document.getElementById('revenueChart')?.getContext('2d');
        if (revenueCtx) {
            // Get revenue and EBITDA margin data for all available years
            const revenueData = [];
            const ebitdaMarginData = [];
            const reversedYears = [...availableYears].reverse();
            
            reversedYears.forEach(year => {
                const yearKey = year.toLowerCase().replace('-', '');
                const revenueValue = getKPIValue('chiffre_d_affaires', yearKey);
                const ebitdaMarginValue = getKPIValue('marge_ebitda', yearKey);
                revenueData.push(revenueValue);
                ebitdaMarginData.push(ebitdaMarginValue);
            });
            
            console.log('Chart data - Revenue:', revenueData, 'EBITDA Margin:', ebitdaMarginData, 'Years:', yearLabels);
            
            if (revenueData.some(val => val !== null) || ebitdaMarginData.some(val => val !== null)) {
                new Chart(revenueCtx, {
                    type: 'bar', 
                    data: {
                        labels: yearLabels,
                        datasets: [
                            {
                                label: "Chiffre d'Affaires (MAD)",
                                data: revenueData,
                                backgroundColor: primaryColor,
                                yAxisID: 'y',
                                order: 2
                            },
                            {
                                label: 'Marge EBITDA (%)',
                                data: ebitdaMarginData,
                                borderColor: successColor,
                                backgroundColor: successColor,
                                type: 'line',
                                yAxisID: 'y1',
                                tension: 0.3,
                                pointRadius: 5,
                                pointHoverRadius: 8,
                                pointBackgroundColor: successColor,
                                pointBorderColor: '#fff',
                                pointBorderWidth: 2,
                                order: 1
                            }
                        ]
                    },
                    options: {
                        ...getChartJsOptions('Chiffre d\'Affaires et Marge EBITDA', val => formatFinancialNumber(val, ''), true),
                        barThickness: 100,
                        categoryPercentage: 0.6,
                        barPercentage: 0.8
                    }
                });
                console.log('Revenue chart with EBITDA margin created successfully with', revenueData.length, 'data points');
            } else {
                revenueCtx.canvas.parentElement.innerHTML = "<p style='text-align:center; color:var(--danger);'>Données de chiffre d'affaires et marge EBITDA indisponibles.</p>";
            }
        }
    } catch (error) {
        console.error("Error rendering revenue chart:", error);
        if (document.getElementById('revenueChart')) {
            document.getElementById('revenueChart').parentElement.innerHTML = "<p style='text-align:center; color:var(--danger);'>Graphique indisponible: Erreur.</p>";
        }
    }

    // --- EBITDA & Net Debt Chart (Single Y-Axis) ---
    try {
        const ebtDebtCtx = document.getElementById('ebtDebtChart')?.getContext('2d');
        if (ebtDebtCtx) {
            // Get EBITDA and Dette Nette data for all available years
            const ebitdaData = [];
            const detteNetteData = [];
            const reversedYears = [...availableYears].reverse();
            
            reversedYears.forEach(year => {
                const yearKey = year.toLowerCase().replace('-', '');
                const ebitdaValue = getKPIValue('ebitda', yearKey);
                const detteNetteValue = getKPIValue('dette_nette', yearKey);
                ebitdaData.push(ebitdaValue);
                detteNetteData.push(detteNetteValue);
            });
            
            console.log('Chart data - EBITDA:', ebitdaData, 'Dette Nette:', detteNetteData, 'Years:', yearLabels);
            
            if (ebitdaData.some(val => val !== null) || detteNetteData.some(val => val !== null)) {
                new Chart(ebtDebtCtx, {
                    type: 'bar', 
                    data: {
                        labels: yearLabels,
                        datasets: [
                            {
                                label: 'EBITDA (MAD)',
                                data: ebitdaData,
                                backgroundColor: primaryColor,
                                order: 2 
                            },
                            {
                                label: 'Dette Nette (MAD)',
                                data: detteNetteData,
                                backgroundColor: successColor,
                                order: 1
                            }
                        ]
                    },
                    options: {
                        ...getChartJsOptions('EBITDA et Dette Nette en MAD', val => formatFinancialNumber(val, ''), false),
                        barThickness: 100,
                        categoryPercentage: 0.6,
                        barPercentage: 0.8,
                        scales: {
                            x: {
                                grid: { display: false },
                                ticks: { color: getComputedStyle(document.documentElement).getPropertyValue('--text-light').trim() }
                            },
                            y: {
                                beginAtZero: false,
                                grid: { color: '#e0e0e0', borderDash: [2, 3] },
                                ticks: { 
                                    color: getComputedStyle(document.documentElement).getPropertyValue('--text-light').trim(),
                                    callback: function(value) { return formatFinancialNumber(value, '').replace(' MAD',''); }
                                },
                                title: { 
                                    display: true, 
                                    text: 'Valeur (MAD)', 
                                    color: getComputedStyle(document.documentElement).getPropertyValue('--primary').trim(), 
                                    font: {weight: 'bold'} 
                                }
                            }
                        }
                    }
                });
                console.log('EBITDA/Dette chart created successfully with', ebitdaData.length, 'data points');
            } else {
                ebtDebtCtx.canvas.parentElement.innerHTML = "<p style='text-align:center; color:var(--danger);'>Données EBITDA/Dette Nette indisponibles.</p>";
            }
        }
    } catch (error) {
        console.error("Error rendering EBITDA/Debt chart:", error);
            if (document.getElementById('ebtDebtChart')) document.getElementById('ebtDebtChart').parentElement.innerHTML = "<p style='text-align:center; color:var(--danger);'>Graphique indisponible: Erreur.</p>";
    }

    // --- Metrics Radar Chart ---
    try {
        const metricsCtx = document.getElementById('metricsChart')?.getContext('2d');
        if (metricsCtx) {
            // Get computed ratios from our calculation function
            const ratios = calculateMissingRatios();
            
            console.log('Radar chart data:', ratios);
            
            const radarData = [
                ratios.marge_ebitda || 0,      // Marge EBITDA
                ratios.marge_exploitation || 0, // Marge d'exploitation  
                ratios.rotation_actifs || 0,   // Rotation des actifs (CA/Actif circulant total moyen)
                ratios.marge_nette || 0,       // Marge Nette
                ratios.roe || 0,              // ROE
                ratios.roce || 0              // ROCE
            ];
            
            // Find the actual min and max values for proper scaling (include all values, including 0)
            const validValues = radarData.filter(val => val !== null && val !== undefined);
            const minValue = validValues.length > 0 ? Math.min(...validValues) : 0;
            const maxValue = validValues.length > 0 ? Math.max(...validValues) : 100;
            
            console.log('Radar values - Min:', minValue, 'Max:', maxValue, 'Raw data:', radarData);
            console.log('Individual ratios:', {
                marge_ebitda: ratios.marge_ebitda,
                marge_exploitation: ratios.marge_exploitation,
                rotation_actifs: ratios.rotation_actifs,
                marge_nette: ratios.marge_nette,
                roe: ratios.roe,
                roce: ratios.roce
            });

            if (radarData.some(val => val !== 0)) {
                new Chart(metricsCtx, {
                    type: 'radar',
                    data: {
                        labels: ['Marge EBITDA', 'Marge Exploit.', 'Rotation Actifs', 'Marge Nette', 'ROE', 'ROCE'],
                        datasets: [{
                            label: 'Performance N (%)',
                            data: radarData,
                            fill: true,
                            backgroundColor: `rgba(${getRGB(primaryColor)}, 0.2)`,
                            borderColor: primaryColor,
                            pointBackgroundColor: primaryColor,
                            pointBorderColor: '#fff',
                            pointHoverBackgroundColor: '#fff',
                            pointHoverBorderColor: primaryColor,
                            pointRadius: 4,
                            pointHoverRadius: 6
                        }]
                    },
                    options: getChartJsRadarOptions(minValue, maxValue)
                });
                console.log('Metrics radar chart created successfully');
            } else {
                metricsCtx.canvas.parentElement.innerHTML = "<p style='text-align:center; color:var(--danger);'>Données KPI indisponibles.</p>";
            }
        }
    } catch (error) {
        console.error("Error rendering metrics radar chart:", error);
        if (document.getElementById('metricsChart')) {
            document.getElementById('metricsChart').parentElement.innerHTML = "<p style='text-align:center; color:var(--danger);'>Graphique indisponible: Erreur.</p>";
        }
    }

    // --- Gearing Donut Chart ---
    try {
        const gearingCtx = document.getElementById('gearingChart')?.getContext('2d');
        if (gearingCtx) {
            // Get current year data using our KPI functions
            const netDebtCurrent = getKPIValue('dette_nette', 'n') || 0;
            const equityCurrent = getKPIValue('capitaux_propres', 'n') || 0;
            
            console.log('Gearing chart data - Dette Nette:', netDebtCurrent, 'Capitaux Propres:', equityCurrent);

            if (equityCurrent !== 0 || netDebtCurrent !== 0) {
                let seriesDataGearing = [Math.max(0, netDebtCurrent), Math.max(0, equityCurrent)];
                let labelsGearing = ['Dette Nette', 'Capitaux Propres'];
                let backgroundColors = [warningColor, primaryColor];

                if (netDebtCurrent < 0) {
                    seriesDataGearing = [Math.abs(netDebtCurrent), Math.max(0, equityCurrent)];
                    labelsGearing = ['Trésorerie Nette Excédentaire', 'Capitaux Propres'];
                    backgroundColors = [successColor, primaryColor];
                }
                if (equityCurrent <= 0 && netDebtCurrent > 0) {
                    seriesDataGearing = [netDebtCurrent, 0.0001]; 
                    labelsGearing = ['Dette Nette', 'Capitaux Propres (Négatifs/Nuls)'];
                    backgroundColors = [warningColor, textLightColor];
                }
                if (equityCurrent <= 0 && netDebtCurrent <= 0) {
                    seriesDataGearing = [Math.abs(netDebtCurrent), 0.0001];
                    labelsGearing = ['Trésorerie Nette Excédentaire', 'Capitaux Propres (Négatifs/Nuls)'];
                    backgroundColors = [successColor, textLightColor];
                }

                new Chart(gearingCtx, {
                    type: 'doughnut',
                    data: {
                        labels: labelsGearing,
                        datasets: [{
                            label: 'Structure Financière (MAD)',
                            data: seriesDataGearing,
                            backgroundColor: backgroundColors,
                            hoverOffset: 4,
                            borderWidth: 2,
                            borderColor: '#fff'
                        }]
                    },
                    options: getChartJsDoughnutOptions(netDebtCurrent, equityCurrent)
                });
                console.log('Gearing donut chart created successfully');
            } else {
                gearingCtx.canvas.parentElement.innerHTML = "<p style='text-align:center; color:var(--danger);'>Données de structure financière indisponibles.</p>";
            }
        }
    } catch (error) {
        console.error("Error rendering gearing chart:", error);
        if (document.getElementById('gearingChart')) {
            document.getElementById('gearingChart').parentElement.innerHTML = "<p style='text-align:center; color:var(--danger);'>Graphique indisponible: Erreur.</p>";
        }
    }
}

function getRGB(colorValue) {
    let color = colorValue;
    if (color.startsWith('var(')) {
        color = getComputedStyle(document.documentElement).getPropertyValue(color.slice(4, -1)).trim();
    }
    if (color.startsWith('#')) {
        const r = parseInt(color.slice(1, 3), 16);
        const g = parseInt(color.slice(3, 5), 16);
        const b = parseInt(color.slice(5, 7), 16);
        return `${r}, ${g}, ${b}`;
    }
    const match = color.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);
    if (match) {
        return `${match[1]}, ${match[2]}, ${match[3]}`;
    }
    return '0, 99, 212'; 
}


/*
 * Generates common options for Chart.js line/bar charts.
 */
function getChartJsOptions(titleText, yTooltipCallback, isDualAxis = false) {
    const textLightColor = getComputedStyle(document.documentElement).getPropertyValue('--text-light').trim();
    const gridBorderColor = '#e0e0e0';
    const primaryColor = getComputedStyle(document.documentElement).getPropertyValue('--primary').trim();
    const successColor = getComputedStyle(document.documentElement).getPropertyValue('--success').trim();


    let yAxes = {
        y: {
            beginAtZero: true,
            grid: { color: gridBorderColor, borderDash: [2, 3] },
            ticks: { 
                color: textLightColor,
                callback: function(value) { return formatFinancialNumber(value, '').replace(' MAD',''); }
            },
            title: { display: isDualAxis, text: 'EBITDA (MAD)', color: primaryColor, font: {weight: 'bold'} }
        }
    };

    if (isDualAxis) {
        yAxes.y1 = {
            position: 'right',
            beginAtZero: true,
            grid: { drawOnChartArea: false }, 
            ticks: { 
                color: textLightColor,
                callback: function(value) { return formatFinancialNumber(value, '').replace(' MAD',''); }
            },
            title: { display: true, text: 'Dette Nette (MAD)', color: successColor, font: {weight: 'bold'} }
        };
    }
    
    return {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: { 
                position: 'top',
                labels: { color: textLightColor, boxWidth: 15, padding: 15 }
            },
            tooltip: {
                mode: 'index',
                intersect: false,
                backgroundColor: 'rgba(255,255,255,0.9)',
                titleColor: 'var(--text-dark)',
                bodyColor: 'var(--text-light)',
                borderColor: 'var(--primary)',
                borderWidth: 1,
                padding: 10,
                callbacks: {
                    label: function(context) {
                        let label = context.dataset.label || '';
                        if (label) { label += ': '; }
                        if (context.parsed.y !== null) {
                            label += yTooltipCallback(context.parsed.y);
                        }
                        return label;
                    }
                }
            }
        },
        scales: {
            x: {
                grid: { display: false },
                ticks: { color: textLightColor }
            },
            ...yAxes
        },
        animation: { duration: 800, easing: 'easeInOutQuart' }
    };
}

/**
 * Generates options for Chart.js Radar chart with auto-scaling.
 */
function getChartJsRadarOptions(minValue = 0, maxValue = 100) {
    const textLightColor = getComputedStyle(document.documentElement).getPropertyValue('--text-light').trim();
    const gridBorderColor = '#e0e0e0';

    // Calculate the data range
    const dataRange = maxValue - minValue;
    
    // Auto-scale based on the actual data range to maximize visibility
    let suggestedMin, suggestedMax, stepSize;
    
    // Handle negative values by setting appropriate min
    if (minValue < 0) {
        // When we have negative values, include them in the scale
        suggestedMin = Math.floor(minValue * 1.2); // Add 20% padding below minimum
        suggestedMax = Math.ceil(maxValue * 1.2);  // Add 20% padding above maximum
        stepSize = Math.ceil((suggestedMax - suggestedMin) / 8);
    } else if (dataRange <= 1) {
        // Very small range (0-1%)
        suggestedMin = 0;
        suggestedMax = Math.ceil(maxValue * 1.2 * 10) / 10; // Add 20% padding, round to 1 decimal
        stepSize = suggestedMax / 5;
    } else if (dataRange <= 5) {
        // Small range (0-5%)
        suggestedMin = 0;
        suggestedMax = Math.ceil(maxValue * 1.2);
        stepSize = Math.max(0.5, suggestedMax / 8);
    } else if (dataRange <= 25) {
        // Medium range (0-25%)
        suggestedMin = 0;
        suggestedMax = Math.ceil(maxValue * 1.1);
        stepSize = Math.ceil(suggestedMax / 6);
    } else {
        // Large range (25%+)
        suggestedMin = 0;
        suggestedMax = Math.ceil(maxValue * 1.1 / 10) * 10;
        stepSize = suggestedMax / 5;
    }
    
    console.log('Radar scale - Min:', suggestedMin, 'Max:', suggestedMax, 'Step:', stepSize, 'Data range:', dataRange);

    return {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: { 
                position: 'top',
                labels: { color: textLightColor, boxWidth: 15, padding: 15 }
            },
            tooltip: {
                backgroundColor: 'rgba(255,255,255,0.9)',
                titleColor: 'var(--text-dark)',
                bodyColor: 'var(--text-light)',
                borderColor: 'var(--primary)',
                borderWidth: 1,
                padding: 10,
                callbacks: {
                    label: function(context) {
                        return context.dataset.label + ': ' + context.parsed.r.toFixed(1) + '%';
                    }
                }
            }
        },
        scales: {
            r: {
                angleLines: { color: gridBorderColor },
                grid: { color: gridBorderColor },
                pointLabels: { 
                    font: { size: 12, weight: 'bold' }, 
                    color: textLightColor 
                },
                min: suggestedMin,
                max: suggestedMax,
                ticks: {
                    backdropColor: 'transparent', 
                    color: textLightColor,
                    stepSize: stepSize,
                    callback: function(value) { 
                        return value.toFixed(1) + '%'; 
                    }
                }
            }
        },
        elements: { 
            line: { borderWidth: 3 },
            point: { radius: 5, hoverRadius: 8 }
        }
    };
}

/**
 * Generates options for Chart.js Doughnut chart.
 */
function getChartJsDoughnutOptions(netDebtCurrent, equityCurrent) {
    const textLightColor = getComputedStyle(document.documentElement).getPropertyValue('--text-light').trim();
    let totalLabel = 'Total Structure';
    if (netDebtCurrent < 0 && equityCurrent > 0) totalLabel = 'Excédent Trés. / CP';
    else if (equityCurrent <= 0) totalLabel = 'Structure (CP Négatifs)';


    return {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: { 
                position: 'bottom',
                labels: { color: textLightColor, boxWidth: 15, padding: 20 }
            },
            tooltip: {
                backgroundColor: 'rgba(255,255,255,0.9)',
                titleColor: 'var(--text-dark)',
                bodyColor: 'var(--text-light)',
                borderColor: 'var(--primary)',
                borderWidth: 1,
                padding: 10,
                callbacks: {
                    label: function(context) {
                        let label = context.label || '';
                        if (label) { label += ': '; }
                        if (context.parsed !== null) {
                            label += formatFinancialNumber(context.parsed, 'MAD');
                        }
                        const total = context.chart.data.datasets[0].data.reduce((a, b) => a + b, 0);
                        const percentage = total > 0 ? ((context.parsed / total) * 100).toFixed(1) + '%' : '0.0%';
                        label += ` (${percentage})`;
                        return label;
                    }
                }
            }
        },
        cutout: '60%', 
        animation: { duration: 800, easing: 'easeInOutQuart' }
    };
}

/**
 * Initializes button event listeners.
 */
function initButtons() {
    // Download PDF and Share button functionality has been removed.
    // The "Read More" button for the modal has been removed and replaced with direct display.
    // This function is kept for potential future buttons that might need JS initialization.
    
    // Example: If you had another button:
    // const anotherButton = document.getElementById('another-btn');
    // if (anotherButton) {
    //     anotherButton.addEventListener('click', function() {
    //         console.log('Another button clicked');
    //     });
    // }
}

/**
 * Populates the key people (Dirigeants) section with data from the JSON.
 */
function populateKeyPeople() {
    const keyPeople = data.keyPeople || [];
    console.log('Key People data:', keyPeople);
    
    const keyPeopleContainer = document.getElementById('key-people-container');
    if (keyPeopleContainer && keyPeople.length > 0) {
        // Clear existing content
        keyPeopleContainer.innerHTML = '';
        
        // Create key people elements in a 2x2 grid layout
        keyPeople.forEach((person, index) => {
            const personSpan = document.createElement('span');
            personSpan.className = 'key-person-compact';
            
            // Add hover functionality by setting data-tooltip attribute
            personSpan.setAttribute('data-tooltip', `${person.name} - ${person.position}`);
            
            // Create the person text without initials
            const personText = document.createTextNode(`${person.name} (${person.position})`);
            personSpan.appendChild(personText);
            
            // Add separator between people (but not after the last one)
            if (index < keyPeople.length - 1) {
                const separatorSpan = document.createElement('span');
                separatorSpan.className = 'separator';
                separatorSpan.textContent = ' '; // Empty space instead of bullet point
                personSpan.appendChild(separatorSpan);
            }
            
            keyPeopleContainer.appendChild(personSpan);
        });
        
        console.log('Key People populated successfully');
    } else if (keyPeopleContainer) {
        // If no key people data, show a placeholder
        keyPeopleContainer.innerHTML = '<span class="key-person-compact">Aucun dirigeant spécifié</span>';
        console.log('No key people data, showing placeholder');
    }
}

/**
 * Populates the news URLs section with data from the JSON.
 */
function populateNewsUrls() {
    const newsUrls = data.news_urls || [];
    console.log('News URLs data:', newsUrls);
    
    // Debug: Log each article's title
    newsUrls.forEach((article, index) => {
        console.log(`Article ${index + 1}: title='${article.title || 'NO TITLE'}', url='${article.url || 'NO URL'}', source='${article.source || 'NO SOURCE'}'`);
    });
    
    if (newsUrls.length > 0) {
        const newsSourcesDiv = document.getElementById('news-sources');
        const newsUrlsGrid = document.getElementById('news-urls-grid');
        
        if (newsSourcesDiv && newsUrlsGrid) {
            // Clear existing content
            newsUrlsGrid.innerHTML = '';
            
            // Limit to top 10 articles
            const top10Articles = newsUrls.slice(0, 10);
            
            // Create news article cards - showing only titles with hyperlinks
            top10Articles.forEach((article, index) => {
                const articleCard = document.createElement('div');
                articleCard.className = 'news-url-card';
                
                const titleLink = document.createElement('a');
                titleLink.href = article.url;
                titleLink.target = '_blank';
                titleLink.rel = 'noopener noreferrer';
                titleLink.textContent = article.title || 'Titre non disponible';
                titleLink.style.color = 'var(--primary)';
                titleLink.style.textDecoration = 'none';
                titleLink.style.fontSize = '1rem';
                titleLink.style.fontWeight = '600';
                titleLink.style.lineHeight = '1.4';
                titleLink.style.display = 'block';
                titleLink.style.padding = '12px 16px';
                titleLink.style.borderRadius = '8px';
                titleLink.style.transition = 'all 0.3s ease';
                titleLink.style.border = '1px solid rgba(var(--primary-rgb), 0.1)';
                titleLink.style.backgroundColor = 'rgba(255, 255, 255, 0.8)';
                
                titleLink.addEventListener('mouseover', () => {
                    titleLink.style.textDecoration = 'underline';
                    titleLink.style.color = 'var(--primary-dark)';
                    titleLink.style.backgroundColor = 'rgba(var(--primary-rgb), 0.05)';
                    titleLink.style.borderColor = 'var(--primary)';
                    titleLink.style.transform = 'translateY(-2px)';
                });
                
                titleLink.addEventListener('mouseout', () => {
                    titleLink.style.textDecoration = 'none';
                    titleLink.style.color = 'var(--primary)';
                    titleLink.style.backgroundColor = 'rgba(255, 255, 255, 0.8)';
                    titleLink.style.borderColor = 'rgba(var(--primary-rgb), 0.1)';
                    titleLink.style.transform = 'translateY(0)';
                });
                
                articleCard.appendChild(titleLink);
                newsUrlsGrid.appendChild(articleCard);
            });
            
            // Show the news sources section
            newsSourcesDiv.style.display = 'block';
        }
    } else {
        // Show "no news found" message when no articles are available
        const newsSourcesDiv = document.getElementById('news-sources');
        const newsUrlsGrid = document.getElementById('news-urls-grid');
        
        if (newsSourcesDiv && newsUrlsGrid) {
            // Clear existing content
            newsUrlsGrid.innerHTML = '';
            
            // Create a "no news found" message
            const noNewsMessage = document.createElement('div');
            noNewsMessage.className = 'no-news-message';
            noNewsMessage.style.cssText = `
                text-align: center;
                padding: 40px 20px;
                color: var(--text-light);
                font-style: italic;
                background: rgba(var(--primary-rgb), 0.05);
                border-radius: 12px;
                border: 2px dashed rgba(var(--primary-rgb), 0.2);
                margin: 20px 0;
            `;
            
            const icon = document.createElement('div');
            icon.innerHTML = '📰';
            icon.style.cssText = `
                font-size: 2rem;
                margin-bottom: 12px;
                opacity: 0.6;
            `;
            
            const message = document.createElement('div');
            message.textContent = 'Aucune actualité pertinente trouvée pour cette entreprise';
            message.style.cssText = `
                font-size: 1.1rem;
                font-weight: 500;
            `;
            
            noNewsMessage.appendChild(icon);
            noNewsMessage.appendChild(message);
            newsUrlsGrid.appendChild(noNewsMessage);
            
            // Show the news sources section with the "no news" message
            newsSourcesDiv.style.display = 'block';
        }
    }
}

// Initialize news URLs when the script loads
populateNewsUrls();
  