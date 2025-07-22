import React, { useState } from 'react';
import axios from 'axios';
import FileUpload from './components/FileUpload';
import Filters from './components/Filters';
import DataTable from './components/DataTable';
import AISummary from './components/AISummary';
import './App.css';

function App() {
    const [glAccounts, setGlAccounts] = useState([]);
    const [selectedGl, setSelectedGl] = useState('');
    const [analysisDate, setAnalysisDate] = useState(new Date().toISOString().split('T')[0]);
    const [ageingData, setAgeingData] = useState([]);
    const [divisionData, setDivisionData] = useState([]);
    const [aiSummary, setAiSummary] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState('');

    const handleUploadSuccess = (accounts) => {
        setGlAccounts(accounts);
        // Reset previous analysis
        setAgeingData([]);
        setDivisionData([]);
        setAiSummary('');
        setSelectedGl('');
        setError('');
    };

    const handleAnalysis = async () => {
        setIsLoading(true);
        setError('');
        const formData = new FormData();
        formData.append('gl_account', selectedGl);
        formData.append('analysis_date', analysisDate);

        try {
            const response = await axios.post('http://localhost:8000/analyze/', formData);
            setAgeingData(response.data.gl_vs_ageing);
            setDivisionData(response.data.gl_vs_division);
            setAiSummary(response.data.ai_summary);
        } catch (err) {
            const errorMessage = err.response?.data?.detail || 'Analysis failed. Please try again.';
            setError(errorMessage);
            console.error('Analysis failed:', err);
        } finally {
            setIsLoading(false);
        }
    };

    const ageingColumns = [
        { key: 'Ageing', name: 'Ageing' },
        { key: 'Amount', name: 'Amount' }
    ];

    const divisionColumns = [
        { key: 'Division', name: 'Division' },
        { key: 'Amount', name: 'Amount' }
    ];

    return (
        <div className="App">
            <header className="header">
                <h1 className="title">Financial Analysis Dashboard</h1>
                <FileUpload onUploadSuccess={handleUploadSuccess} onError={setError} />
            </header>

            <main className="main-content">
                <section className="analysis-section">
                    <Filters
                        glAccounts={glAccounts}
                        selectedGl={selectedGl}
                        setSelectedGl={setSelectedGl}
                        analysisDate={analysisDate}
                        setAnalysisDate={setAnalysisDate}
                        onAnalyze={handleAnalysis}
                        isLoading={isLoading}
                    />
                    {error && <p style={{ color: 'red' }}>Error: {error}</p>}
                    <div className="tables-container">
                        <DataTable title="G/L vs Ageing" data={ageingData} columns={ageingColumns} />
                        <DataTable title="G/L vs Division" data={divisionData} columns={divisionColumns} />
                    </div>
                </section>
                <AISummary summary={aiSummary} isLoading={isLoading} />
            </main>
        </div>
    );
}

export default App;