import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { FileText, Upload, Building2, Calculator, TrendingUp, BarChart3, Download, Mail } from 'lucide-react';
import LoadingSpinner from '../UI/LoadingSpinner';
import axios from 'axios';

const ExpertComptablePage = () => {
  const [formData, setFormData] = useState({
    companyName: '',
    file: null
  });
  const [isProcessing, setIsProcessing] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [emailData, setEmailData] = useState({
    email: '',
    sendEmail: false
  });
  const [isSendingEmail, setIsSendingEmail] = useState(false);
  const [emailSuccess, setEmailSuccess] = useState(false);
  const [reportsHistory, setReportsHistory] = useState([]);
  const [showHistory, setShowHistory] = useState(false);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      if (file.type !== 'application/pdf') {
        setError('Veuillez sélectionner un fichier PDF valide');
        return;
      }
      if (file.size > 10 * 1024 * 1024) { // 10MB limit
        setError('Le fichier est trop volumineux. Taille maximale: 10MB');
        return;
      }
      setFormData(prev => ({
        ...prev,
        file: file
      }));
      setError('');
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!formData.companyName.trim()) {
      setError('Le nom de l\'entreprise est requis');
      return;
    }
    
    if (!formData.file) {
      setError('Veuillez sélectionner un fichier PDF');
      return;
    }

    setIsProcessing(true);
    setError('');
    setResult(null);

    try {
      const formDataToSend = new FormData();
      formDataToSend.append('company_name', formData.companyName);
      formDataToSend.append('file', formData.file);

      console.log('[EXPERT COMPTABLE DEBUG] Sending request to /api/expertcompta/process');

      const response = await axios.post('http://localhost:5000/api/expertcompta/process', formDataToSend, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        timeout: 600000, // 10 minutes timeout
      });

      console.log('[EXPERT COMPTABLE DEBUG] Response received:', {
        status: response.status,
        statusText: response.statusText,
        dataKeys: Object.keys(response.data || {}),
        hasReportHtml: !!response.data?.report_html,
        reportHtmlLength: response.data?.report_html?.length || 0,
        hasTvaAnalysis: !!response.data?.data?.tva_analysis
      });

      if (response.data?.report_html) {
        console.log('[EXPERT COMPTABLE DEBUG] Report HTML contains TVA:', 
          response.data.report_html.includes('Cadrage de TVA'));
      }

      setResult(response.data);
      
      // Sauvegarder le rapport dans l'historique
      if (response.data?.data) {
        saveReportToHistory(response.data.data);
      }
    } catch (err) {
      console.error('[EXPERT COMPTABLE DEBUG] Error occurred:', {
        message: err.message,
        status: err.response?.status,
        statusText: err.response?.statusText,
        data: err.response?.data,
        isTimeout: err.code === 'ECONNABORTED'
      });
      
      setError(err.response?.data?.error || 'Une erreur est survenue lors du traitement');
    } finally {
      setIsProcessing(false);
    }
  };

  const resetForm = () => {
    setFormData({
      companyName: '',
      file: null
    });
    setResult(null);
    setError('');
    setEmailData({
      email: '',
      sendEmail: false
    });
    setEmailSuccess(false);
  };

  const handleEmailInputChange = (e) => {
    const { name, value, type, checked } = e.target;
    setEmailData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };

  const downloadPDF = async () => {
    if (!result?.data) return;
    
    try {
      const token = localStorage.getItem('token');
      const response = await axios.post('/api/expertcompta/pdf', result.data, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        responseType: 'blob'
      });
      
      // Create blob URL and trigger download
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `rapport-expert-comptable-${result.data?.company_name || 'analyse'}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Erreur lors du téléchargement PDF:', error);
      alert('Erreur lors du téléchargement du PDF');
    }
  };

  const downloadHTML = () => {
    if (!result?.report_html) {
      alert('Aucun rapport HTML disponible');
      return;
    }
    
    try {
      console.log('[EXPERT COMPTABLE DEBUG] Downloading HTML report, length:', result.report_html.length);
      
      // Create blob and trigger download
      const blob = new Blob([result.report_html], { type: 'text/html; charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `rapport-expert-comptable-${result.data?.company_name || 'analyse'}.html`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      
      console.log('[EXPERT COMPTABLE DEBUG] HTML report downloaded successfully');
    } catch (error) {
      console.error('[EXPERT COMPTABLE DEBUG] Error downloading HTML:', error);
      alert('Erreur lors du téléchargement du rapport HTML');
    }
  };

  const viewHTMLReport = () => {
    if (!result?.report_html) {
      alert('Aucun rapport HTML disponible');
      return;
    }
    
    try {
      console.log('[EXPERT COMPTABLE DEBUG] Opening HTML report in new window');
      
      // Open in new window
      const newWindow = window.open('', '_blank');
      newWindow.document.write(result.report_html);
      newWindow.document.close();
      
      console.log('[EXPERT COMPTABLE DEBUG] HTML report opened in new window');
    } catch (error) {
      console.error('[EXPERT COMPTABLE DEBUG] Error opening HTML:', error);
      alert('Erreur lors de l\'ouverture du rapport HTML');
    }
  };

  const sendEmail = async () => {
    if (!result?.data || !emailData.email.trim()) {
      setError('Adresse email requise');
      return;
    }

    setIsSendingEmail(true);
    setError('');
    setEmailSuccess(false);

    try {
      const token = localStorage.getItem('token');
      const response = await axios.post('/api/expertcompta/send-email', {
        email: emailData.email,
        report_data: result.data
      }, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      setEmailSuccess(true);
      setEmailData(prev => ({ ...prev, email: '' }));
    } catch (error) {
      console.error('Erreur lors de l\'envoi de l\'email:', error);
      setError(error.response?.data?.error || 'Erreur lors de l\'envoi de l\'email');
    } finally {
      setIsSendingEmail(false);
    }
  };

  const loadReportsHistory = () => {
    const history = JSON.parse(localStorage.getItem('expertComptableHistory') || '[]');
    setReportsHistory(history);
    setShowHistory(true);
  };

  const saveReportToHistory = (reportData) => {
    const history = JSON.parse(localStorage.getItem('expertComptableHistory') || '[]');
    const newReport = {
      id: Date.now(),
      companyName: reportData.company_name,
      fiscalYear: reportData.fiscal_year,
      timestamp: new Date().toLocaleString('fr-FR'),
      data: reportData
    };
    history.unshift(newReport);
    const limitedHistory = history.slice(0, 10);
    localStorage.setItem('expertComptableHistory', JSON.stringify(limitedHistory));
    setReportsHistory(limitedHistory);
  };

  const viewHistoricalReport = (report) => {
    setResult({
      data: report.data,
      report_html: report.data.report_html || 'Rapport non disponible'
    });
    setShowHistory(false);
  };

  const deleteHistoricalReport = (reportId) => {
    const updatedHistory = reportsHistory.filter(report => report.id !== reportId);
    setReportsHistory(updatedHistory);
    localStorage.setItem('expertComptableHistory', JSON.stringify(updatedHistory));
  };

  return (
    <div className="min-h-screen relative overflow-hidden">
      {/* Background */}
      <div 
        className="absolute inset-0 bg-cover bg-center bg-no-repeat"
        style={{
          backgroundImage: `linear-gradient(135deg, rgba(245, 158, 11, 0.9) 0%, rgba(107, 114, 128, 0.8) 100%), 
                           url('data:image/svg+xml,${encodeURIComponent(`
                             <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1000">
                               <defs>
                                 <pattern id="grid" width="50" height="50" patternUnits="userSpaceOnUse">
                                   <path d="M 50 0 L 0 0 0 50" fill="none" stroke="rgba(255,255,255,0.1)" stroke-width="1"/>
                                 </pattern>
                               </defs>
                               <rect width="100%" height="100%" fill="url(#grid)" />
                               <circle cx="200" cy="200" r="100" fill="rgba(255,255,255,0.05)" />
                               <circle cx="800" cy="300" r="150" fill="rgba(255,255,255,0.03)" />
                               <circle cx="300" cy="700" r="80" fill="rgba(255,255,255,0.04)" />
                               <circle cx="700" cy="800" r="120" fill="rgba(255,255,255,0.02)" />
                             </svg>
                           `)}')`
        }}
      />
      
      {/* Floating particles effect */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        {[...Array(20)].map((_, i) => (
          <div
            key={i}
            className="absolute w-2 h-2 bg-white rounded-full opacity-20 animate-pulse"
            style={{
              left: `${Math.random() * 100}%`,
              top: `${Math.random() * 100}%`,
              animationDelay: `${Math.random() * 3}s`,
              animationDuration: `${3 + Math.random() * 4}s`
            }}
          />
        ))}
      </div>

      {/* Main Content */}
      <div className={`relative z-10 min-h-screen ${!result ? 'grid grid-cols-1 lg:grid-cols-2 gap-6 p-4' : 'p-4'}`}>
        {!result ? (
          <>
            {/* Left Side - Upload Form */}
            <motion.div
              initial={{ opacity: 0, x: -50 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.8, ease: "easeOut" }}
              className="flex items-start justify-start max-h-screen p-2"
            >
              <div className="w-full h-[calc(100vh-8rem)] backdrop-blur-xl backdrop-blur-enhanced bg-white/10 border border-white/20 rounded-3xl shadow-2xl overflow-hidden flex flex-col">
                {/* Upload Form Content */}
              {/* Header */}
              <div className="bg-gradient-to-r from-white/20 to-white/10 backdrop-blur-sm border-b border-white/20 p-6 text-center">
                <motion.div
                  initial={{ opacity: 0, y: -20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.3 }}
                  className="flex flex-col items-center space-y-4"
                >
                  <div className="w-16 h-16 bg-gray-300 rounded-2xl flex items-center justify-center shadow-lg float-animation glow-animation">
                    <Calculator className="h-8 w-8 text-gray-700" />
                  </div>
                  <div>
                    <h1 className="text-2xl font-bold text-white mb-2">Agent Comptable</h1>
                    <p className="text-gray-200 text-base">Revue analytique basé sur une liasse fiscale</p>
                  </div>
                </motion.div>
              </div>

              {/* Form Content */}
              <div className="p-6 flex-1 flex flex-col justify-center">
                <motion.form
                  onSubmit={handleSubmit}
                  className="space-y-6"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.5 }}
                >
                  {/* Company Name Input - Top centered */}
                  <motion.div 
                    className="space-y-3"
                    initial={{ opacity: 0, x: -30 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.6 }}
                  >
                    <label className="block text-lg font-semibold text-white text-center">
                      <Building2 className="inline h-6 w-6 mr-3" />
                      Nom de l'entreprise
                    </label>
                    <input
                      type="text"
                      name="companyName"
                      value={formData.companyName}
                      onChange={handleInputChange}
                      className="w-full px-6 py-4 bg-white/20 backdrop-blur-sm border border-white/30 rounded-2xl text-white placeholder-white/70 focus:ring-2 focus:ring-amber-400 focus:border-transparent transition-all duration-300 text-center text-lg font-medium"
                      placeholder="Entrez le nom de l'entreprise"
                      required
                    />
                  </motion.div>

                  {/* Animated divider */}
                  <motion.div 
                    className="flex items-center justify-center py-4"
                    initial={{ opacity: 0, scaleX: 0 }}
                    animate={{ opacity: 1, scaleX: 1 }}
                    transition={{ delay: 0.7 }}
                  >
                    <div className="w-full h-px bg-gradient-to-r from-transparent via-white/30 to-transparent"></div>
                    <div className="mx-4 w-3 h-3 bg-white/40 rounded-full"></div>
                    <div className="w-full h-px bg-gradient-to-r from-transparent via-white/30 to-transparent"></div>
                  </motion.div>

                  {/* File Upload - Below with slide down effect */}
                  <motion.div 
                    className="space-y-4"
                    initial={{ opacity: 0, y: 30 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.8 }}
                  >
                    <label className="block text-lg font-semibold text-white text-center">
                      <FileText className="inline h-6 w-6 mr-3" />
                      Liasse Fiscale (PDF)
                    </label>
                    
                    <div className="relative group">
                      <div className="absolute inset-0 bg-gray-300 rounded-2xl blur opacity-30 group-hover:opacity-50 transition-opacity duration-300"></div>
                      <div className="relative bg-white/20 backdrop-blur-sm border-2 border-dashed border-white/40 rounded-2xl p-8 hover:border-white/60 transition-all duration-300">
                        <input
                          type="file"
                          accept=".pdf"
                          onChange={handleFileChange}
                          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10"
                          required
                        />
                        <div className="text-center">
                          <Upload className="h-12 w-12 text-white/80 mx-auto mb-4" />
                          <p className="text-white text-lg font-medium mb-2">
                            {formData.file ? formData.file.name : "Choisir un fichier ou glisser-déposer"}
                          </p>
                          <p className="text-white/70 text-sm">
                            Taille maximale: 10MB • Format accepté: PDF uniquement
                          </p>
                        </div>
                      </div>
                    </div>
                  </motion.div>

                  {error && (
                    <motion.div
                      initial={{ opacity: 0, y: -10 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="bg-red-500/20 backdrop-blur-sm border border-red-400/30 text-red-100 px-6 py-4 rounded-2xl text-center"
                    >
                      {error}
                    </motion.div>
                  )}

                  <motion.div 
                    className="flex flex-col sm:flex-row justify-center items-center space-y-4 sm:space-y-0 sm:space-x-6 pt-6"
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.9 }}
                  >
                    <button
                      type="button"
                      onClick={resetForm}
                      className="px-8 py-4 bg-white/20 backdrop-blur-sm border border-white/30 text-white rounded-2xl hover:bg-white/30 transition-all duration-300 font-medium"
                    >
                      Réinitialiser
                    </button>
                    <button
                      type="submit"
                      disabled={isProcessing}
                      className="px-10 py-4 bg-gray-300 text-gray-800 rounded-2xl hover:bg-gray-400 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-300 flex items-center space-x-3 font-semibold text-lg shadow-lg hover:shadow-xl transform hover:scale-105"
                    >
                      {isProcessing ? (
                        <>
                          <LoadingSpinner size="sm" />
                          <span>Traitement en cours...</span>
                        </>
                      ) : (
                        <>
                          <Upload className="h-5 w-5" />
                          <span>Analyser le document</span>
                        </>
                      )}
                    </button>
                  </motion.div>
                </motion.form>
              </div>
              </div>
            </motion.div>

            {/* Right Side - Image Section */}
            <motion.div
              initial={{ opacity: 0, x: 50 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.8, ease: "easeOut", delay: 0.2 }}
              className="flex items-start justify-start max-h-screen p-2"
            >
              <div className="w-full h-full flex items-center">
                {/* Decorative Image Container */}
                <div className="relative w-full h-full">
                  {/* Main Image Placeholder */}
                  <div className="backdrop-blur-xl bg-white/10 border border-white/20 rounded-3xl p-6 shadow-2xl h-[calc(100vh-8rem)] flex flex-col">
                    <div className="text-center space-y-4 flex-1 flex flex-col">
                      {/* Financial Analytics Illustration */}
                      {/* Your Image */}
                      <div className="w-full flex-1 rounded-3xl overflow-hidden border border-white/20 shadow-lg" style={{ maxHeight: '576px' }}>
                        <motion.img
                          initial={{ opacity: 0, scale: 0.9 }}
                          animate={{ opacity: 1, scale: 1 }}
                          transition={{ delay: 0.5, duration: 0.8 }}
                          src="/Accountant_innovation.png"
                          // src="/Generated_Image.png"
                          alt="Financial Analytics"
                          className="w-full h-full object-cover rounded-3xl"
                        />
                      </div>
                      
                      {/* Text Content */}
                      <div className="space-y-4 flex-shrink-0">
                        <h2 className="text-xl font-bold text-white">
                          Analyse Financière Intelligente
                        </h2>
                        <p className="text-gray-200 text-sm leading-relaxed">
                          Notre IA analyse vos données financières et génère des rapports détaillés 
                          pour vous aider à prendre des décisions éclairées.
                        </p>
                        
                        {/* Feature Points */}
                        <div className="space-y-2 text-left">
                          {[
                            "Analyse automatique des KPIs",
                            "Rapports personnalisés",
                            "Insights financiers avancés",
                            "Exportation PDF/HTML"
                          ].map((feature, i) => (
                            <motion.div
                              key={i}
                              initial={{ opacity: 0, x: 20 }}
                              animate={{ opacity: 1, x: 0 }}
                              transition={{ delay: 1.5 + i * 0.1 }}
                              className="flex items-center space-x-2 text-gray-200 text-xs"
                            >
                              <div className="w-1.5 h-1.5 bg-amber-400 rounded-full"></div>
                              <span>{feature}</span>
                            </motion.div>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>
                  
                  {/* Floating Elements */}
                  <motion.div
                    animate={{ y: [-5, 5, -5] }}
                    transition={{ duration: 3, repeat: Infinity }}
                    className="absolute -top-4 -right-4 w-12 h-12 bg-gradient-to-br from-amber-400/30 to-gray-600/30 rounded-2xl backdrop-blur-sm border border-white/20 flex items-center justify-center"
                  >
                    <TrendingUp className="h-6 w-6 text-amber-300" />
                  </motion.div>
                  
                  <motion.div
                    animate={{ y: [5, -5, 5] }}
                    transition={{ duration: 4, repeat: Infinity }}
                    className="absolute -bottom-2 -left-4 w-10 h-10 bg-gradient-to-br from-gray-600/30 to-amber-400/30 rounded-xl backdrop-blur-sm border border-white/20 flex items-center justify-center"
                  >
                    <Calculator className="h-5 w-5 text-gray-300" />
                  </motion.div>
                </div>
              </div>
            </motion.div>
          </>
        ) : (
          /* Results Display - Full width when showing results */
          <motion.div
            initial={{ opacity: 0, y: 30, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            transition={{ duration: 0.8, ease: "easeOut" }}
            className="w-full h-full col-span-full"
          >
            {/* Results Display - Full screen layout */}
            <div className="backdrop-blur-xl backdrop-blur-enhanced bg-white/10 border border-white/20 rounded-3xl shadow-2xl overflow-hidden h-full min-h-[calc(100vh-2rem)]">
              {/* Header with Company Info */}
              <motion.div 
                className="bg-gradient-to-r from-amber-400/20 to-gray-600/20 backdrop-blur-sm border-b border-white/20 p-4 flex-shrink-0"
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-4">
                    <div className="w-12 h-12 bg-gradient-to-br from-amber-400 to-gray-600 rounded-xl flex items-center justify-center">
                      <TrendingUp className="h-6 w-6 text-white" />
                    </div>
                    <div>
                      <h3 className="text-xl font-bold text-white">
                        {result.data?.company_name}
                      </h3>
                      <p className="text-gray-200">
                        Exercice: {result.data?.fiscal_year || 'N/A'}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center space-x-2 text-green-100">
                    <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
                    <span className="text-sm font-medium">Analyse terminée</span>
                  </div>
                </div>
              </motion.div>

              <div className="grid grid-cols-1 lg:grid-cols-4 gap-4 p-4 h-full" style={{ height: 'calc(100vh - 10rem)' }}>
                {/* Report Preview - Takes 3/4 of the space */}
                <motion.div 
                  className="lg:col-span-3 bg-white/10 backdrop-blur-sm border border-white/20 rounded-2xl overflow-hidden flex flex-col"
                  initial={{ opacity: 0, x: -30 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.3 }}
                >
                  <div className="bg-gradient-to-r from-amber-400/20 to-gray-600/20 backdrop-blur-sm border-b border-white/20 px-6 py-3 flex-shrink-0">
                    <h3 className="font-semibold text-white text-lg flex items-center">
                      <BarChart3 className="h-6 w-6 mr-3" />
                      Rapport d'analyse financière - Aperçu
                    </h3>
                  </div>
                  <div 
                    ref={(el) => {
                      if (el && result.report_html) {
                        // Inject HTML content
                        const processedHtml = result.report_html?.replace(
                          /style="[^"]*color:\s*#[0-9a-fA-F]{3,6}[^"]*"/g, 
                          'style="color: #F59E0B"'
                        ).replace(
                          /color:\s*#[0-9a-fA-F]{3,6}/g, 
                          'color: #F59E0B'
                        ).replace(
                          /color:\s*rgb\([^)]*\)/g, 
                          'color: #F59E0B'
                        ) || result.report_html;
                        
                        el.innerHTML = processedHtml;
                        
                        // Extract financial data and populate table manually
                        setTimeout(() => {
                          const dataScript = el.querySelector('#financial-data');
                          const tbody = el.querySelector('#financial-diagnostic-tbody');
                          
                          if (dataScript && tbody) {
                            try {
                              const data = JSON.parse(dataScript.textContent);
                              const kpis = data.kpis || {};
                              const computedRatios = data.computed_ratios || {};
                              
                              // Clear existing content
                              tbody.innerHTML = '';
                              
                              // Define KPIs to display
                              const kpiList = [
                                { name: 'Chiffre d\'Affaires', key: 'chiffre_d_affaires', dbKey: "Chiffre d'affaires" },
                                { name: 'EBITDA', key: 'ebitda', dbKey: 'EBITDA' },
                                { name: 'Résultat Net', key: 'resultat_net', dbKey: 'Résultat Net' },
                                { name: 'Trésorerie Nette', key: 'tresorerie_nette', dbKey: 'Trésorerie nette' },
                                { name: 'Capitaux Propres', key: 'capitaux_propres', dbKey: 'Capitaux propres' },
                                { name: 'Dette Nette', key: 'dette_nette', dbKey: 'Dette nette' },
                                { name: 'BFR', key: 'bfr', dbKey: 'BFR' }
                              ];
                              
                              // Helper functions
                              const formatFinancialNumber = (value) => {
                                if (value == null || value === '' || isNaN(value)) return '-';
                                const num = parseFloat(value);
                                if (Math.abs(num) >= 1000000) {
                                  return (num / 1000000).toFixed(1).replace('.', ',') + 'M';
                                } else if (Math.abs(num) >= 1000) {
                                  return (num / 1000).toFixed(0).replace('.', ',') + 'K';
                                } else {
                                  return num.toFixed(0).replace('.', ',');
                                }
                              };
                              
                              const getKPIValue = (kpi, year) => {
                                // Try flat structure first
                                const flatKey = `${kpi.key}_${year}`;
                                if (computedRatios[flatKey] !== undefined) {
                                  return computedRatios[flatKey];
                                }
                                
                                // Try nested structure
                                const yearMapping = { 'n': 'N', 'n1': 'N-1' };
                                const normalizedYear = yearMapping[year] || year;
                                
                                if (kpis[kpi.dbKey] && kpis[kpi.dbKey][normalizedYear] !== undefined) {
                                  return kpis[kpi.dbKey][normalizedYear];
                                }
                                
                                return null;
                              };
                              
                              const renderCAGR = (current, previous) => {
                                if (current != null && previous != null && !isNaN(current) && !isNaN(previous) && previous !== 0) {
                                  const cagr = ((current / previous) - 1) * 100;
                                  const isPositive = cagr >= 0;
                                  const formatted = cagr.toFixed(1).replace('.', ',');
                                  
                                  return `
                                    <span class="change ${isPositive ? 'positive' : 'negative'}">
                                      ${formatted}% <i class="fas fa-arrow-${isPositive ? 'up' : 'down'}"></i>
                                    </span>`;
                                }
                                return '<span class="change" style="font-size: 1.5em; text-align: center;">-</span>';
                              };
                              
                              // Generate table rows
                              kpiList.forEach(kpi => {
                                const valueN = getKPIValue(kpi, 'n');
                                const valueN1 = getKPIValue(kpi, 'n1');
                                
                                const row = document.createElement('tr');
                                row.innerHTML = `
                                  <td>${kpi.name}</td>
                                  <td>${formatFinancialNumber(valueN)}</td>
                                  <td>${formatFinancialNumber(valueN1)}</td>
                                  <td>${renderCAGR(valueN, valueN1)}</td>
                                `;
                                tbody.appendChild(row);
                              });
                              
                              console.log('✅ Financial diagnostic table populated successfully');
                            } catch (e) {
                              console.error('❌ Error populating financial table:', e);
                            }
                          }
                        }, 200);
                      }
                    }}
                    className="p-6 flex-1 overflow-y-auto text-white bg-gradient-to-br from-amber-50/5 to-gray-900/20 report-scrollbar"
                    style={{ minHeight: '0' }}
                  />
                </motion.div>

                {/* Actions Panel - Takes 1/4 of the space */}
                <motion.div 
                  className="space-y-4 flex flex-col"
                  initial={{ opacity: 0, x: 30 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.4 }}
                >
                  {/* Email Section */}
                  <div className="bg-amber-500/20 backdrop-blur-sm border border-amber-400/30 rounded-2xl p-4 flex-shrink-0">
                    <h3 className="text-base font-semibold text-white mb-3 flex items-center">
                      <Mail className="h-4 w-4 mr-2" />
                      Email
                    </h3>
                    
                    {emailSuccess && (
                      <motion.div
                        initial={{ opacity: 0, y: -10 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="bg-green-500/20 backdrop-blur-sm border border-green-400/30 text-green-100 px-3 py-1 rounded-lg mb-2 text-center text-xs"
                      >
                        ✅ Envoyé!
                      </motion.div>
                    )}

                    <div className="space-y-2">
                      <input
                        type="email"
                        name="email"
                        value={emailData.email}
                        onChange={handleEmailInputChange}
                        placeholder="Votre email"
                        className="w-full px-3 py-2 bg-white/20 backdrop-blur-sm border border-white/30 rounded-lg text-white placeholder-white/70 focus:ring-2 focus:ring-amber-400 focus:border-transparent transition-all duration-300 text-xs"
                      />
                      <button
                        onClick={sendEmail}
                        disabled={isSendingEmail || !emailData.email.trim()}
                        className="w-full px-3 py-2 bg-gradient-to-r from-amber-500 to-gray-600 text-white rounded-lg hover:from-amber-600 hover:to-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-300 flex items-center justify-center space-x-2 font-medium text-xs"
                      >
                        {isSendingEmail ? (
                          <>
                            <LoadingSpinner size="sm" />
                            <span>Envoi...</span>
                          </>
                        ) : (
                          <>
                            <Mail className="h-3 w-3" />
                            <span>Envoyer</span>
                          </>
                        )}
                      </button>
                    </div>
                  </div>

                  {/* Download Options */}
                  <div className="bg-gray-500/20 backdrop-blur-sm border border-gray-400/30 rounded-2xl p-4 flex-shrink-0">
                    <h3 className="text-base font-semibold text-white mb-3 flex items-center">
                      <Download className="h-4 w-4 mr-2" />
                      Télécharger
                    </h3>
                    
                    <div className="space-y-2">
                      <button
                        onClick={viewHTMLReport}
                        className="w-full px-3 py-2 bg-gradient-to-r from-blue-500 to-blue-600 text-white rounded-lg hover:from-blue-600 hover:to-blue-700 transition-all duration-300 flex items-center justify-center space-x-2 font-medium text-xs"
                      >
                        <FileText className="h-3 w-3" />
                        <span>Consulter le rapport</span>
                      </button>
                      <button
                        onClick={downloadHTML}
                        className="w-full px-3 py-2 bg-gradient-to-r from-gray-600 to-gray-700 text-white rounded-lg hover:from-gray-700 hover:to-gray-800 transition-all duration-300 flex items-center justify-center space-x-2 font-medium text-xs"
                      >
                        <Download className="h-3 w-3" />
                        <span>Télécharger le rapport</span>
                      </button>
                    </div>
                  </div>

                  {/* New Analysis */}
                  <div className="bg-white/10 backdrop-blur-sm border border-white/20 rounded-2xl p-4 flex-shrink-0">
                    <button
                      onClick={resetForm}
                      className="w-full px-3 py-2 bg-white/20 backdrop-blur-sm border border-white/30 text-white rounded-lg hover:bg-white/30 transition-all duration-300 font-medium text-xs"
                    >
                      Nouvelle analyse
                    </button>
                  </div>
                </motion.div>
              </div>
            </div>
          </motion.div>
        )}

        {/* Section Historique des Rapports */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.2 }}
          className="mt-8"
        >
          <div className="backdrop-blur-xl backdrop-blur-enhanced bg-white/10 border border-white/20 rounded-3xl shadow-2xl overflow-hidden">
            {/* Header de l'historique */}
            <div className="bg-gradient-to-r from-amber-400/20 to-gray-600/20 backdrop-blur-sm border-b border-white/20 px-6 py-4">
              <div className="flex items-center justify-between">
                <h3 className="text-xl font-bold text-white flex items-center">
                  <FileText className="h-6 w-6 mr-3" />
                  Historique des Rapports
                </h3>
                <button
                  onClick={loadReportsHistory}
                  className="px-4 py-2 bg-white/20 backdrop-blur-sm border border-white/30 text-white rounded-lg hover:bg-white/30 transition-all duration-300 font-medium text-sm"
                >
                  {showHistory ? 'Masquer' : 'Afficher'} l'historique
                </button>
              </div>
            </div>

            {/* Contenu de l'historique */}
            {showHistory && (
              <div className="p-6">
                {reportsHistory.length === 0 ? (
                  <div className="text-center py-8">
                    <FileText className="h-12 w-12 text-white/40 mx-auto mb-4" />
                    <p className="text-white/70 text-lg">Aucun rapport généré</p>
                    <p className="text-white/50 text-sm">Les rapports apparaîtront ici après génération</p>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {reportsHistory.map((report) => (
                      <motion.div
                        key={report.id}
                        initial={{ opacity: 0, scale: 0.9 }}
                        animate={{ opacity: 1, scale: 1 }}
                        transition={{ duration: 0.3 }}
                        className="bg-white/10 backdrop-blur-sm border border-white/20 rounded-2xl p-4 hover:bg-white/20 transition-all duration-300"
                      >
                        <div className="flex items-start justify-between mb-3">
                          <div className="flex-1">
                            <h4 className="text-white font-semibold text-lg mb-1">
                              {report.companyName}
                            </h4>
                            <p className="text-white/70 text-sm mb-2">
                              Exercice: {report.fiscalYear || 'N/A'}
                            </p>
                            <p className="text-white/50 text-xs">
                              {report.timestamp}
                            </p>
                          </div>
                          <button
                            onClick={() => deleteHistoricalReport(report.id)}
                            className="text-white/50 hover:text-red-400 transition-colors duration-200 ml-2"
                            title="Supprimer"
                          >
                            <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                          </button>
                        </div>
                        
                        <div className="flex space-x-2">
                          <button
                            onClick={() => viewHistoricalReport(report)}
                            className="flex-1 px-3 py-2 bg-gradient-to-r from-blue-500 to-blue-600 text-white rounded-lg hover:from-blue-600 hover:to-blue-700 transition-all duration-300 flex items-center justify-center space-x-2 font-medium text-xs"
                          >
                            <FileText className="h-3 w-3" />
                            <span>Consulter</span>
                          </button>
                          <button
                            onClick={() => {
                              const blob = new Blob([report.data.report_html || ''], { type: 'text/html; charset=utf-8' });
                              const url = URL.createObjectURL(blob);
                              const a = document.createElement('a');
                              a.href = url;
                              a.download = `rapport-${report.companyName}-${report.fiscalYear || 'analyse'}.html`;
                              document.body.appendChild(a);
                              a.click();
                              document.body.removeChild(a);
                              URL.revokeObjectURL(url);
                            }}
                            className="px-3 py-2 bg-gradient-to-r from-gray-600 to-gray-700 text-white rounded-lg hover:from-gray-700 hover:to-gray-800 transition-all duration-300 flex items-center justify-center"
                            title="Télécharger"
                          >
                            <Download className="h-3 w-3" />
                          </button>
                        </div>
                      </motion.div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </motion.div>
      </div>
    </div>
  );
};

export default ExpertComptablePage;
