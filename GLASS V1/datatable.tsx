import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { AgGridReact } from 'ag-grid-react';
import { ColDef } from 'ag-grid-community';
import 'ag-grid-community/styles/ag-grid.css';
import 'ag-grid-community/styles/ag-theme-alpine.css';

type Props = {
  selectedGL: string;
};

const DataTable: React.FC<Props> = ({ selectedGL }) => {
  const [summary, setSummary] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [drillData, setDrillData] = useState<any>(null);
  const [aiSummary, setAiSummary] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedGL) return;
    const fetchSummary = async () => {
      setLoading(true);
      try {
        const response = await axios.get(`http://localhost:8000/filtered-summary?gl_account=${selectedGL}`);
        setSummary(response.data);
      } catch (error) {
        console.error('Failed to fetch summary:', error);
      } finally {
        setLoading(false);
        setDrillData(null); // Reset drilldown if GL changes
        setAiSummary(null);
      }
    };
    fetchSummary();
  }, [selectedGL]);

  const handleCellClick = async (params: any) => {
    const ageing = params.data['Ageing'] || null;
    const division = params.data['Division'] || null;

    try {
      const response = await axios.get('http://localhost:8000/drilldown1', {
        params: {
          gl_account: selectedGL,
          ageing: ageing || '',
          division: division || '',
        },
      });

      setDrillData(response.data.table);
      setAiSummary(response.data.ai_summary);
    } catch (error) {
      console.error('Drilldown failed:', error);
    }
  };

  if (loading) return <p>Loading tables...</p>;
  if (!summary) return null;

  const renderTable = (title: string, data: any, onCellClick?: (params: any) => void) => (
    <div style={{ marginBottom: '2rem' }}>
      <h4>{title}</h4>
      <div className="ag-theme-alpine" style={{ height: 300, width: '100%' }}>
        <AgGridReact
          rowData={data.rows}
          columnDefs={data.columns.map((col: string): ColDef => ({ field: col }))}
          domLayout={'autoHeight' as 'autoHeight'}
          onCellClicked={onCellClick}
        />
      </div>
    </div>
  );

  return (
    <div>
      {renderTable('G/L vs Ageing', summary.ageing_summary, handleCellClick)}
      {renderTable('G/L vs Division', summary.division_summary, handleCellClick)}

      {drillData && (
        <>
          <h4>📊 Drilldown I: G/L + Ageing + Division</h4>
          {renderTable('Drilldown I', drillData)}
        </>
      )}

      {aiSummary && (
        <div style={{ marginTop: '1rem', padding: '1rem', border: '1px solid #ccc', background: '#f5f5f5' }}>
          <h4>🧠 AI Summary (Drilldown I)</h4>
          <p>{aiSummary}</p>
        </div>
      )}
    </div>
  );
};

export default DataTable;



// import React, { useEffect, useState } from 'react';
// import axios from 'axios';
// import { AgGridReact } from 'ag-grid-react';
// import 'ag-grid-community/styles/ag-grid.css';
// import 'ag-grid-community/styles/ag-theme-alpine.css';

// type Props = {
//   selectedGL: string;
// };

// const DataTable: React.FC<Props> = ({ selectedGL }) => {
//   const [summary, setSummary] = useState<any>(null);
//   const [loading, setLoading] = useState(false);

//   useEffect(() => {
//     if (!selectedGL) return;

//     const fetchSummary = async () => {
//       setLoading(true);
//       try {
//         const response = await axios.get(`http://localhost:8000/filtered-summary?gl_account=${selectedGL}`);
//         setSummary(response.data);
//       } catch (error) {
//         console.error('Failed to fetch summary data:', error);
//       } finally {
//         setLoading(false);
//       }
//     };

//     fetchSummary();
//   }, [selectedGL]);

//   if (loading) return <p>Loading summary tables...</p>;
//   if (!summary) return null;

//   const commonTableProps = {
//     className: 'ag-theme-alpine',
//     style: { height: 300, width: '100%', marginBottom: '2rem' },
//     rowData: undefined,
//     columnDefs: undefined,
//     domLayout: 'autoHeight',
//   };

//   return (
//   <div>
//     <h4>G/L vs Ageing</h4>
//     <div className="ag-theme-alpine" style={{ height: 300, width: '100%', marginBottom: '2rem' }}>
//       <AgGridReact
//         rowData={summary.ageing_summary.rows}
//         columnDefs={summary.ageing_summary.columns.map((col: string) => ({ field: col }))}
//         domLayout={'autoHeight' as 'autoHeight'}
//       />
//     </div>

//     <h4>G/L vs Division</h4>
//     <div className="ag-theme-alpine" style={{ height: 300, width: '100%', marginBottom: '2rem' }}>
//       <AgGridReact
//         rowData={summary.division_summary.rows}
//         columnDefs={summary.division_summary.columns.map((col: string) => ({ field: col }))}
//         domLayout={'autoHeight' as 'autoHeight'}
//       />
//     </div>
//   </div>
// );


// export default DataTable;
