import React from 'react';

const Filters = ({ glAccounts, selectedGl, setSelectedGl, analysisDate, setAnalysisDate, onAnalyze, isLoading }) => {
    return (
        <div className="filters">
            <select 
                onChange={(e) => setSelectedGl(e.target.value)} 
                value={selectedGl}
                disabled={glAccounts.length === 0}
            >
                <option value="">Select G/L Account</option>
                {glAccounts.map(gl => <option key={gl} value={gl}>{gl}</option>)}
            </select>
            <input 
                type="date" 
                value={analysisDate} 
                onChange={(e) => setAnalysisDate(e.target.value)} 
            />
            <button onClick={onAnalyze} disabled={!selectedGl || isLoading}>
                {isLoading ? 'Analyzing...' : 'Analyze'}
            </button>
        </div>
    );
};

export default Filters;