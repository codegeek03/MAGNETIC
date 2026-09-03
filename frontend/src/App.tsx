import React, { useState } from 'react';
import axios from 'axios';
import { Package, Upload, ArrowRight, Activity, Beaker, CheckCircle } from 'lucide-react';
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Tooltip, ResponsiveContainer } from 'recharts';
import './index.css';

function App() {
  const [taskStatus, setTaskStatus] = useState<string>('idle'); // idle, processing, completed, failed
  const [taskId, setTaskId] = useState<string | null>(null);
  const [results, setResults] = useState<any>(null);

  const [formData, setFormData] = useState({
    product_name: '',
    location: '',
    units: 100,
    length: 4.0,
    width: 4.0,
    height: 5.0,
    budget: 10.0,
    properties_weight: 0.1,
    logistics_weight: 0.1,
    cost_weight: 0.1,
    sustainability_weight: 0.4,
    consumer_weight: 0.2,
    requires_carbon_lca: false,
    requires_compliance_doc: false
  });

  const [bomFile, setBomFile] = useState<File | null>(null);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : type === 'number' ? Number(value) : value
    }));
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setBomFile(e.target.files[0]);
    }
  };

  const pollStatus = async (id: string) => {
    try {
      const res = await axios.get(`http://localhost:8000/api/analysis/${id}`);
      if (res.data.status === 'completed') {
        setTaskStatus('completed');
        setResults(res.data.result);
      } else if (res.data.status === 'failed') {
        setTaskStatus('failed');
      } else {
        setTimeout(() => pollStatus(id), 2000);
      }
    } catch (err) {
      console.error(err);
      setTaskStatus('failed');
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setTaskStatus('processing');
    
    const data = new FormData();
    Object.entries(formData).forEach(([key, value]) => {
      data.append(key, value.toString());
    });
    if (bomFile) {
      data.append('bom_file', bomFile);
    }

    try {
      const res = await axios.post('http://localhost:8000/api/analysis', data, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setTaskId(res.data.task_id);
      pollStatus(res.data.task_id);
    } catch (err) {
      console.error(err);
      setTaskStatus('failed');
    }
  };

  // Extract top material data for the Radar chart
  const radarData = results?.final_results?.top_materials?.[0] ? [
    { metric: 'Properties', value: results.final_results.top_materials[0].composite_score.components.properties },
    { metric: 'Cost', value: results.final_results.top_materials[0].composite_score.components.cost },
    { metric: 'Logistics', value: results.final_results.top_materials[0].composite_score.components.logistics },
    { metric: 'Sustainability', value: results.final_results.top_materials[0].composite_score.components.sustainability },
    { metric: 'Consumer', value: results.final_results.top_materials[0].composite_score.components.consumer }
  ] : [];

  return (
    <div className="app-container">
      <header className="mb-8 text-center">
        <h1>📦 Packaging Material Analysis</h1>
        <p>Discover the perfect sustainable packaging for your product</p>
      </header>

      {taskStatus === 'idle' && (
        <form onSubmit={handleSubmit} className="glass-card flex-col gap-4">
          <div className="grid grid-cols-2">
            <div className="form-group">
              <label>Product Name</label>
              <input required name="product_name" className="input-field" value={formData.product_name} onChange={handleInputChange} placeholder="e.g. Eggs" />
            </div>
            <div className="form-group">
              <label>Location</label>
              <input required name="location" className="input-field" value={formData.location} onChange={handleInputChange} placeholder="e.g. Kolkata" />
            </div>
            <div className="form-group">
              <label>Units per Shipment</label>
              <input required type="number" name="units" className="input-field" value={formData.units} onChange={handleInputChange} />
            </div>
            <div className="form-group">
              <label>Budget per Unit (USD)</label>
              <input required type="number" step="0.1" name="budget" className="input-field" value={formData.budget} onChange={handleInputChange} />
            </div>
          </div>

          <h3 className="mt-4">Dimensions (cm)</h3>
          <div className="grid grid-cols-3">
            <div className="form-group">
              <label>Length</label>
              <input type="number" step="0.1" name="length" className="input-field" value={formData.length} onChange={handleInputChange} />
            </div>
            <div className="form-group">
              <label>Width</label>
              <input type="number" step="0.1" name="width" className="input-field" value={formData.width} onChange={handleInputChange} />
            </div>
            <div className="form-group">
              <label>Height</label>
              <input type="number" step="0.1" name="height" className="input-field" value={formData.height} onChange={handleInputChange} />
            </div>
          </div>

          <h3 className="mt-4">Advanced & Portfolio</h3>
          <div className="grid grid-cols-2">
            <label className="checkbox-label">
              <input type="checkbox" name="requires_carbon_lca" checked={formData.requires_carbon_lca} onChange={handleInputChange} />
              Generate Carbon LCA (ESG Reporting)
            </label>
            <label className="checkbox-label">
              <input type="checkbox" name="requires_compliance_doc" checked={formData.requires_compliance_doc} onChange={handleInputChange} />
              Draft PPWR Declaration of Conformity
            </label>
            <div className="form-group mt-4">
              <label>Upload BOM (CSV)</label>
              <input type="file" accept=".csv" className="input-field" onChange={handleFileChange} />
            </div>
          </div>

          <div className="mt-4 text-center">
            <button type="submit" className="btn btn-primary">
              <Activity className="mr-2" size={18} /> Analyze Materials
            </button>
          </div>
        </form>
      )}

      {taskStatus === 'processing' && (
        <div className="glass-card text-center flex-col items-center gap-4 py-12">
          <div style={{ display: 'flex', justifyContent: 'center' }} className="mb-4">
            <div className="loader"></div>
          </div>
          <h2>Analyzing Materials...</h2>
          <p>Agents are currently synthesizing constraints, running sustainability metrics, and querying facts.</p>
        </div>
      )}

      {taskStatus === 'completed' && results && (
        <div className="grid gap-4">
          <div className="glass-card flex items-center justify-between mb-4">
            <h2 className="flex items-center gap-2"><CheckCircle color="var(--accent-green)" /> Analysis Complete</h2>
            <button onClick={() => setTaskStatus('idle')} className="btn btn-primary">Run Another</button>
          </div>
          
          {radarData.length > 0 && (
             <div className="glass-card">
               <h3>Top Material Breakdown: {results.final_results.top_materials[0].material_name}</h3>
               <div style={{ width: '100%', height: '300px' }}>
                 <ResponsiveContainer>
                   <RadarChart data={radarData} margin={{ top: 20, right: 30, bottom: 20, left: 30 }}>
                     <PolarGrid stroke="rgba(255,255,255,0.2)" />
                     <PolarAngleAxis dataKey="metric" tick={{ fill: 'var(--text-secondary)' }} />
                     <PolarRadiusAxis angle={30} domain={[0, 'dataMax']} tick={false} axisLine={false} />
                     <Radar name="Score" dataKey="value" stroke="var(--accent-blue)" fill="var(--accent-blue)" fillOpacity={0.5} />
                     <Tooltip contentStyle={{ backgroundColor: 'var(--bg-primary)', border: '1px solid var(--glass-border)' }} />
                   </RadarChart>
                 </ResponsiveContainer>
               </div>
             </div>
          )}

          <div className="glass-card flex-col gap-4">
            <h3>Full Report</h3>
            <pre style={{ background: 'rgba(0,0,0,0.3)', padding: '1rem', borderRadius: '0.5rem', overflowX: 'auto' }}>
              {JSON.stringify(results, null, 2)}
            </pre>
          </div>
        </div>
      )}

      {taskStatus === 'failed' && (
        <div className="glass-card text-center">
          <h2 style={{ color: '#ef4444' }}>Analysis Failed</h2>
          <p>Something went wrong during the analysis workflow.</p>
          <button onClick={() => setTaskStatus('idle')} className="btn btn-primary mt-4">Try Again</button>
        </div>
      )}
    </div>
  );
}

export default App;
