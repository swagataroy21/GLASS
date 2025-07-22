// src/App.tsx (Phase 1: Upload + GL Dropdown + Tables)
import React, { useEffect, useState } from 'react';
import { FileUpload } from './components/FileUpload';
import { Dropdown } from './components/Dropdown';
import { DataTable } from './components/DataTable';
import { AISummary } from './components/AISummary';
import { fetchGLAccounts, fetchInitialSummary } from './api/api';
import logoLeft from '/logoleft.png';
import logoRight from '/logoright.png';

export default function App() {
  const [glOptions, setGlOptions] = useState<string[]>([]);
  const [selectedGL, setSelectedGL] = useState<string>('');
  const [ageingData, setAgeingData] = useState<any[]>([]);
  const [divisionData, setDivisionData] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchGLAccounts().then(setGlOptions);
  }, []);

  const handleGLChange = async (gl: string) => {
    setSelectedGL(gl);
    setLoading(true);
    const { ageing_table, division_table } = await fetchInitialSummary(gl);
    setAgeingData(ageing_table);
    setDivisionData(division_table);
    setLoading(false);
  };

  return (
    <div className="min-h-screen bg-white text-gray-800 font-sans">
      {/* Nav Bar */}
      <div className="flex items-center justify-between bg-blue-700 text-white p-4">
        <img src={logoLeft} alt="Logo Left" className="h-10" />
        <div className="text-2xl font-semibold">Finance Drilldown Dashboard</div>
        <FileUpload />
      </div>

      {/* Controls */}
      <div className="flex flex-col sm:flex-row items-center gap-4 p-4">
        <Dropdown options={glOptions} onChange={handleGLChange} label="Select G/L Account" />
      </div>

      {/* Tables */}
      {loading ? (
        <div className="text-center py-10 text-blue-600">Loading data...</div>
      ) : (
        <div className="p-4 grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="lg:col-span-2 space-y-6">
            <DataTable title="GL vs Ageing" data={ageingData} />
            <DataTable title="GL vs Division" data={divisionData} />
          </div>
          <AISummary />
        </div>
      )}
    </div>
  );
}
