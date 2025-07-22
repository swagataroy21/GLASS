import React from 'react';

const AISummary = ({ summary, isLoading }) => {
    return (
        <aside className="ai-summary-section">
            <h3>AI Summary</h3>
            {isLoading && !summary && <p>Generating summary...</p>}
            {!isLoading && !summary && <p>The AI-generated summary will appear here after analysis.</p>}
            {summary && <p>{summary}</p>}
        </aside>
    );
};

export default AISummary;