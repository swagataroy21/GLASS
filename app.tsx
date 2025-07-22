import React, { useState } from 'react';
import FileUpload from './components/FileUpload';
import GLFilter from './components/GLFilter';
import DataTable from './components/DataTable';
import axios from 'axios';

const App: React.FC = () => {
  const [summary, setSummary] = useState<any>(null);
  const [selectedGL, setSelectedGL] = useState('');
  const [drillData, setDrillData] = useState<any>(null);

  const fetchSummary = (glAccount: string) => {
    axios
      .get(`http://localhost:8000/filtered-summary?gl_account=${glAccount}`)
      .then(res => setSummary(res.data));
  };

  const handleGLSelect = (gl: string) => {
    setSelectedGL(gl);
    fetchSummary(gl);
  };

  const handleDrillClick = (params: any) => {
    const ageing = params.data.Ageing;
    const division = params.data.Division;

    axios
      .get(`http://localhost:8000/drilldown1?gl_account=${selectedGL}&ageing=${ageing}&division=${division}`)
      .then(res => setDrillData(res.data));
  };

  return (
    <div style={{ padding: 20 }}>
      <h2>ABAP Data Analyzer</h2>
      <FileUpload />
      <GLFilter onSelect={handleGLSelect} />

      {summary && (
        <>
          <DataTable title="GL vs Ageing" data={summary.ageing_summary} onCellClick={handleDrillClick} />
          <DataTable title="GL vs Division" data={summary.division_summary} onCellClick={handleDrillClick} />
        </>
      )}

      {drillData && (
        <DataTable title="Drilldown I - GL + Ageing + Division" data={drillData} />
      )}
    </div>
  );
};

export default App;
