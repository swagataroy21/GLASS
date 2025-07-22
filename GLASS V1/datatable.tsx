import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { AgGridReact } from 'ag-grid-react';
import 'ag-grid-community/styles/ag-grid.css';
import 'ag-grid-community/styles/ag-theme-alpine.css';

type Props = {
  selectedGL: string;
};

const DataTable: React.FC<Props> = ({ selectedGL }) => {
  const [summary, setSummary] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!selectedGL) return;

    const fetchSummary = async () => {
      setLoading(true);
      try {
        const response = await axios.get(`http://localhost:8000/filtered-summary?gl_account=${selectedGL}`);
        setSummary(response.data);
      } catch (error) {
        console.error('Failed to fetch summary data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchSummary();
  }, [selectedGL]);

  if (loading) return <p>Loading summary tables...</p>;
  if (!summary) return null;

  const commonTableProps = {
    className: 'ag-theme-alpine',
    style: { height: 300, width: '100%', marginBottom: '2rem' },
    rowData: undefined,
    columnDefs: undefined,
    domLayout: 'autoHeight',
  };

  return (
    <div>
      <h4>G/L vs Ageing</h4>
      <div {...commonTableProps}>
        <AgGridReact
          {...commonTableProps}
          rowData={summary.ageing_summary.rows}
          columnDefs={summary.ageing_summary.columns.map((col: string) => ({ field: col }))}
        />
      </div>

      <h4>G/L vs Division</h4>
      <div {...commonTableProps}>
        <AgGridReact
          {...commonTableProps}
          rowData={summary.division_summary.rows}
          columnDefs={summary.division_summary.columns.map((col: string) => ({ field: col }))}
        />
      </div>
    </div>
  );
};

export default DataTable;
