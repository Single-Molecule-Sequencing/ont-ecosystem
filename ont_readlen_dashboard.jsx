import React, { useState, useMemo } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, AreaChart, Area, ComposedChart, Line, Cell, PieChart, Pie } from 'recharts';

// Sample multi-experiment read length data (would come from ont_readlen.py JSON output)
const sampleExperiments = [
  {
    id: 'exp-001',
    name: 'CYP2D6_Batch1_Ligation',
    total_reads: 15234567,
    total_bases: 76172835000,
    mean_length: 5000,
    median_length: 4200,
    n50: 8500,
    n90: 2100,
    max_length: 125000,
    pct_gt_1kb: 90.0,
    pct_gt_5kb: 40.0,
    pct_gt_10kb: 15.0,
    pct_gt_20kb: 3.0,
    pct_gt_50kb: 0.3,
    device: 'MD-101527',
    date: '2025-12-08',
    histogram: [
      { bin: '0-1k', count: 1523456, pct: 10.0 },
      { bin: '1-2k', count: 2285185, pct: 15.0 },
      { bin: '2-3k', count: 2590076, pct: 17.0 },
      { bin: '3-4k', count: 2437530, pct: 16.0 },
      { bin: '4-5k', count: 1980443, pct: 13.0 },
      { bin: '5-7k', count: 1828548, pct: 12.0 },
      { bin: '7-10k', count: 1371411, pct: 9.0 },
      { bin: '10-15k', count: 762283, pct: 5.0 },
      { bin: '15-20k', count: 304913, pct: 2.0 },
      { bin: '>20k', count: 150721, pct: 1.0 },
    ]
  },
  {
    id: 'exp-002', 
    name: 'CYP2D6_Batch2_Rapid',
    total_reads: 12456789,
    total_bases: 49827156000,
    mean_length: 4000,
    median_length: 3500,
    n50: 6200,
    n90: 1800,
    max_length: 85000,
    pct_gt_1kb: 85.0,
    pct_gt_5kb: 32.0,
    pct_gt_10kb: 10.0,
    pct_gt_20kb: 1.5,
    pct_gt_50kb: 0.1,
    device: 'MD-102066',
    date: '2025-11-24',
    histogram: [
      { bin: '0-1k', count: 1868518, pct: 15.0 },
      { bin: '1-2k', count: 2491358, pct: 20.0 },
      { bin: '2-3k', count: 2242221, pct: 18.0 },
      { bin: '3-4k', count: 1868518, pct: 15.0 },
      { bin: '4-5k', count: 1245679, pct: 10.0 },
      { bin: '5-7k', count: 1120111, pct: 9.0 },
      { bin: '7-10k', count: 870975, pct: 7.0 },
      { bin: '10-15k', count: 498272, pct: 4.0 },
      { bin: '15-20k', count: 186852, pct: 1.5 },
      { bin: '>20k', count: 64286, pct: 0.5 },
    ]
  },
  {
    id: 'exp-003',
    name: 'UltraLong_Protocol',
    total_reads: 5678901,
    total_bases: 113578020000,
    mean_length: 20000,
    median_length: 15000,
    n50: 35000,
    n90: 8500,
    max_length: 450000,
    pct_gt_1kb: 98.0,
    pct_gt_5kb: 85.0,
    pct_gt_10kb: 65.0,
    pct_gt_20kb: 40.0,
    pct_gt_50kb: 15.0,
    device: 'MD-101527',
    date: '2025-10-23',
    histogram: [
      { bin: '0-1k', count: 113578, pct: 2.0 },
      { bin: '1-2k', count: 170367, pct: 3.0 },
      { bin: '2-3k', count: 227156, pct: 4.0 },
      { bin: '3-4k', count: 283945, pct: 5.0 },
      { bin: '4-5k', count: 340734, pct: 6.0 },
      { bin: '5-7k', count: 681468, pct: 12.0 },
      { bin: '7-10k', count: 908624, pct: 16.0 },
      { bin: '10-15k', count: 1022202, pct: 18.0 },
      { bin: '15-20k', count: 738656, pct: 13.0 },
      { bin: '>20k', count: 1192171, pct: 21.0 },
    ]
  },
  {
    id: 'exp-004',
    name: 'SMA_seq_Enrichment',
    total_reads: 8901234,
    total_bases: 53407404000,
    mean_length: 6000,
    median_length: 5200,
    n50: 9800,
    n90: 2800,
    max_length: 95000,
    pct_gt_1kb: 92.0,
    pct_gt_5kb: 52.0,
    pct_gt_10kb: 22.0,
    pct_gt_20kb: 5.0,
    pct_gt_50kb: 0.5,
    device: 'MN47455',
    date: '2025-10-16',
    histogram: [
      { bin: '0-1k', count: 712099, pct: 8.0 },
      { bin: '1-2k', count: 1068148, pct: 12.0 },
      { bin: '2-3k', count: 1335185, pct: 15.0 },
      { bin: '3-4k', count: 1424198, pct: 16.0 },
      { bin: '4-5k', count: 1335185, pct: 15.0 },
      { bin: '5-7k', count: 1157160, pct: 13.0 },
      { bin: '7-10k', count: 890123, pct: 10.0 },
      { bin: '10-15k', count: 534074, pct: 6.0 },
      { bin: '15-20k', count: 267037, pct: 3.0 },
      { bin: '>20k', count: 178025, pct: 2.0 },
    ]
  }
];

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16'];

const formatNumber = (num) => {
  if (num >= 1e9) return (num / 1e9).toFixed(2) + ' Gb';
  if (num >= 1e6) return (num / 1e6).toFixed(2) + ' M';
  if (num >= 1e3) return (num / 1e3).toFixed(1) + ' k';
  return num.toString();
};

const StatCard = ({ title, value, subtitle, color = 'text-white' }) => (
  <div className="bg-slate-800 rounded-lg p-4">
    <div className="text-slate-400 text-sm">{title}</div>
    <div className={`text-2xl font-bold ${color}`}>{value}</div>
    {subtitle && <div className="text-slate-500 text-xs mt-1">{subtitle}</div>}
  </div>
);

const QualityBadge = ({ value, thresholds }) => {
  let status = 'good';
  let color = 'bg-emerald-600';
  
  if (value < thresholds.poor) {
    status = 'poor';
    color = 'bg-red-600';
  } else if (value < thresholds.ok) {
    status = 'ok';
    color = 'bg-amber-600';
  }
  
  return (
    <span className={`${color} px-2 py-0.5 rounded text-xs font-medium`}>
      {status.toUpperCase()}
    </span>
  );
};

export default function ReadLengthDashboard() {
  const [selectedExperiments, setSelectedExperiments] = useState(
    sampleExperiments.map(e => e.id)
  );
  const [viewMode, setViewMode] = useState('comparison'); // 'comparison', 'detail', 'table'
  const [selectedDetail, setSelectedDetail] = useState(null);
  const [plotType, setPlotType] = useState('overlay'); // 'overlay', 'bar', 'violin'

  const filteredExperiments = useMemo(() => 
    sampleExperiments.filter(e => selectedExperiments.includes(e.id)),
    [selectedExperiments]
  );

  // Aggregate stats
  const aggregateStats = useMemo(() => {
    if (filteredExperiments.length === 0) return null;
    
    const totalReads = filteredExperiments.reduce((sum, e) => sum + e.total_reads, 0);
    const totalBases = filteredExperiments.reduce((sum, e) => sum + e.total_bases, 0);
    const avgN50 = filteredExperiments.reduce((sum, e) => sum + e.n50, 0) / filteredExperiments.length;
    const avgMean = filteredExperiments.reduce((sum, e) => sum + e.mean_length, 0) / filteredExperiments.length;
    const avgPct10k = filteredExperiments.reduce((sum, e) => sum + e.pct_gt_10kb, 0) / filteredExperiments.length;
    
    return { totalReads, totalBases, avgN50, avgMean, avgPct10k };
  }, [filteredExperiments]);

  // Prepare comparison data
  const comparisonData = useMemo(() => {
    return filteredExperiments.map((exp, idx) => ({
      name: exp.name.length > 20 ? exp.name.slice(0, 18) + '...' : exp.name,
      fullName: exp.name,
      n50: exp.n50,
      mean: exp.mean_length,
      median: exp.median_length,
      max: exp.max_length,
      reads: exp.total_reads,
      bases: exp.total_bases,
      pct_gt_10kb: exp.pct_gt_10kb,
      pct_gt_5kb: exp.pct_gt_5kb,
      color: COLORS[idx % COLORS.length]
    }));
  }, [filteredExperiments]);

  // Prepare histogram overlay data
  const histogramOverlay = useMemo(() => {
    if (filteredExperiments.length === 0) return [];
    
    const bins = filteredExperiments[0].histogram.map(h => h.bin);
    return bins.map((bin, idx) => {
      const point = { bin };
      filteredExperiments.forEach((exp, i) => {
        point[exp.name] = exp.histogram[idx]?.pct || 0;
      });
      return point;
    });
  }, [filteredExperiments]);

  const toggleExperiment = (id) => {
    setSelectedExperiments(prev => 
      prev.includes(id) 
        ? prev.filter(e => e !== id)
        : [...prev, id]
    );
  };

  return (
    <div className="min-h-screen bg-slate-900 text-white p-4">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          ðŸ“ Read Length Distribution Dashboard
        </h1>
        <p className="text-slate-400 text-sm">Multi-experiment comparison â€¢ {filteredExperiments.length} experiments selected</p>
      </div>

      {/* Experiment Selector */}
      <div className="bg-slate-800 rounded-lg p-4 mb-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-semibold text-sm">Select Experiments</h3>
          <div className="flex gap-2">
            <button 
              onClick={() => setSelectedExperiments(sampleExperiments.map(e => e.id))}
              className="text-xs px-2 py-1 bg-slate-700 hover:bg-slate-600 rounded"
            >
              Select All
            </button>
            <button 
              onClick={() => setSelectedExperiments([])}
              className="text-xs px-2 py-1 bg-slate-700 hover:bg-slate-600 rounded"
            >
              Clear
            </button>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          {sampleExperiments.map((exp, idx) => (
            <button
              key={exp.id}
              onClick={() => toggleExperiment(exp.id)}
              className={`px-3 py-1.5 rounded text-sm font-medium transition-colors flex items-center gap-2
                ${selectedExperiments.includes(exp.id) 
                  ? 'bg-opacity-100' 
                  : 'bg-opacity-30 opacity-60'}`}
              style={{ backgroundColor: COLORS[idx % COLORS.length] }}
            >
              <span className="w-2 h-2 rounded-full bg-white"></span>
              {exp.name.length > 25 ? exp.name.slice(0, 23) + '...' : exp.name}
            </button>
          ))}
        </div>
      </div>

      {/* View Mode Tabs */}
      <div className="flex gap-2 mb-4">
        {['comparison', 'detail', 'table'].map(mode => (
          <button
            key={mode}
            onClick={() => setViewMode(mode)}
            className={`px-4 py-2 rounded text-sm font-medium ${
              viewMode === mode ? 'bg-blue-600' : 'bg-slate-700 hover:bg-slate-600'
            }`}
          >
            {mode.charAt(0).toUpperCase() + mode.slice(1)}
          </button>
        ))}
      </div>

      {/* Aggregate Stats */}
      {aggregateStats && (
        <div className="grid grid-cols-5 gap-3 mb-4">
          <StatCard 
            title="Total Reads" 
            value={formatNumber(aggregateStats.totalReads)}
            subtitle="across all selected"
          />
          <StatCard 
            title="Total Bases" 
            value={formatNumber(aggregateStats.totalBases)}
            color="text-emerald-400"
          />
          <StatCard 
            title="Avg N50" 
            value={formatNumber(aggregateStats.avgN50) + ' bp'}
            color="text-amber-400"
          />
          <StatCard 
            title="Avg Mean Length" 
            value={formatNumber(aggregateStats.avgMean) + ' bp'}
            color="text-blue-400"
          />
          <StatCard 
            title="Avg >10kb" 
            value={aggregateStats.avgPct10k.toFixed(1) + '%'}
            color="text-purple-400"
          />
        </div>
      )}

      {/* Comparison View */}
      {viewMode === 'comparison' && (
        <div className="space-y-4">
          {/* Plot Type Selector */}
          <div className="flex gap-2 mb-2">
            {['overlay', 'bar', 'metrics'].map(type => (
              <button
                key={type}
                onClick={() => setPlotType(type)}
                className={`px-3 py-1 rounded text-xs font-medium ${
                  plotType === type ? 'bg-emerald-600' : 'bg-slate-700 hover:bg-slate-600'
                }`}
              >
                {type === 'overlay' ? 'ðŸ“ˆ Overlay' : type === 'bar' ? 'ðŸ“Š Histogram' : 'ðŸ“‹ Metrics'}
              </button>
            ))}
          </div>

          {plotType === 'overlay' && (
            <div className="bg-slate-800 rounded-lg p-4">
              <h3 className="font-semibold mb-3">Read Length Distribution Overlay</h3>
              <ResponsiveContainer width="100%" height={350}>
                <AreaChart data={histogramOverlay}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#475569" />
                  <XAxis dataKey="bin" tick={{ fill: '#94a3b8', fontSize: 11 }} />
                  <YAxis 
                    tick={{ fill: '#94a3b8' }} 
                    label={{ value: '% of Reads', angle: -90, position: 'insideLeft', fill: '#94a3b8' }}
                  />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px' }}
                    formatter={(value) => `${value.toFixed(1)}%`}
                  />
                  <Legend />
                  {filteredExperiments.map((exp, idx) => (
                    <Area 
                      key={exp.id}
                      type="monotone" 
                      dataKey={exp.name} 
                      stroke={COLORS[idx % COLORS.length]}
                      fill={COLORS[idx % COLORS.length]}
                      fillOpacity={0.3}
                      strokeWidth={2}
                    />
                  ))}
                </AreaChart>
              </ResponsiveContainer>
            </div>
          )}

          {plotType === 'bar' && (
            <div className="bg-slate-800 rounded-lg p-4">
              <h3 className="font-semibold mb-3">Read Length Histograms</h3>
              <ResponsiveContainer width="100%" height={350}>
                <BarChart data={histogramOverlay}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#475569" />
                  <XAxis dataKey="bin" tick={{ fill: '#94a3b8', fontSize: 11 }} />
                  <YAxis tick={{ fill: '#94a3b8' }} />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px' }}
                    formatter={(value) => `${value.toFixed(1)}%`}
                  />
                  <Legend />
                  {filteredExperiments.map((exp, idx) => (
                    <Bar 
                      key={exp.id}
                      dataKey={exp.name} 
                      fill={COLORS[idx % COLORS.length]}
                      radius={[2, 2, 0, 0]}
                    />
                  ))}
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

          {plotType === 'metrics' && (
            <div className="grid grid-cols-2 gap-4">
              {/* N50 Comparison */}
              <div className="bg-slate-800 rounded-lg p-4">
                <h3 className="font-semibold mb-3">N50 Comparison</h3>
                <ResponsiveContainer width="100%" height={250}>
                  <BarChart data={comparisonData} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" stroke="#475569" />
                    <XAxis type="number" tick={{ fill: '#94a3b8' }} />
                    <YAxis dataKey="name" type="category" width={100} tick={{ fill: '#94a3b8', fontSize: 10 }} />
                    <Tooltip 
                      contentStyle={{ backgroundColor: '#1e293b', border: 'none' }}
                      formatter={(value) => `${formatNumber(value)} bp`}
                    />
                    <Bar dataKey="n50" fill="#f59e0b" radius={[0, 4, 4, 0]}>
                      {comparisonData.map((entry, idx) => (
                        <Cell key={idx} fill={COLORS[idx % COLORS.length]} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>

              {/* >10kb Percentage */}
              <div className="bg-slate-800 rounded-lg p-4">
                <h3 className="font-semibold mb-3">Reads &gt;10kb (%)</h3>
                <ResponsiveContainer width="100%" height={250}>
                  <BarChart data={comparisonData} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" stroke="#475569" />
                    <XAxis type="number" domain={[0, 100]} tick={{ fill: '#94a3b8' }} />
                    <YAxis dataKey="name" type="category" width={100} tick={{ fill: '#94a3b8', fontSize: 10 }} />
                    <Tooltip 
                      contentStyle={{ backgroundColor: '#1e293b', border: 'none' }}
                      formatter={(value) => `${value.toFixed(1)}%`}
                    />
                    <Bar dataKey="pct_gt_10kb" fill="#10b981" radius={[0, 4, 4, 0]}>
                      {comparisonData.map((entry, idx) => (
                        <Cell key={idx} fill={COLORS[idx % COLORS.length]} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>

              {/* Mean vs Median */}
              <div className="bg-slate-800 rounded-lg p-4">
                <h3 className="font-semibold mb-3">Mean vs Median Length</h3>
                <ResponsiveContainer width="100%" height={250}>
                  <BarChart data={comparisonData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#475569" />
                    <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 9 }} angle={-45} textAnchor="end" height={80} />
                    <YAxis tick={{ fill: '#94a3b8' }} />
                    <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: 'none' }} />
                    <Legend />
                    <Bar dataKey="mean" name="Mean" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="median" name="Median" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>

              {/* Total Yield */}
              <div className="bg-slate-800 rounded-lg p-4">
                <h3 className="font-semibold mb-3">Total Yield (Gb)</h3>
                <ResponsiveContainer width="100%" height={250}>
                  <PieChart>
                    <Pie
                      data={comparisonData.map((d, i) => ({
                        name: d.name,
                        value: d.bases / 1e9,
                        color: COLORS[i % COLORS.length]
                      }))}
                      cx="50%"
                      cy="50%"
                      outerRadius={80}
                      dataKey="value"
                      label={({ name, value }) => `${value.toFixed(1)} Gb`}
                      labelLine={false}
                    >
                      {comparisonData.map((_, idx) => (
                        <Cell key={idx} fill={COLORS[idx % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip 
                      contentStyle={{ backgroundColor: '#1e293b', border: 'none' }}
                      formatter={(value) => `${value.toFixed(2)} Gb`}
                    />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Detail View */}
      {viewMode === 'detail' && (
        <div className="space-y-4">
          <div className="flex gap-2 flex-wrap">
            {filteredExperiments.map((exp, idx) => (
              <button
                key={exp.id}
                onClick={() => setSelectedDetail(exp.id)}
                className={`px-3 py-1.5 rounded text-sm font-medium ${
                  selectedDetail === exp.id ? 'ring-2 ring-white' : ''
                }`}
                style={{ backgroundColor: COLORS[idx % COLORS.length] }}
              >
                {exp.name.length > 20 ? exp.name.slice(0, 18) + '...' : exp.name}
              </button>
            ))}
          </div>

          {selectedDetail && (() => {
            const exp = filteredExperiments.find(e => e.id === selectedDetail);
            if (!exp) return null;
            const idx = filteredExperiments.indexOf(exp);
            
            return (
              <div className="grid grid-cols-3 gap-4">
                <div className="col-span-2 bg-slate-800 rounded-lg p-4">
                  <h3 className="font-semibold mb-3">{exp.name} - Read Length Distribution</h3>
                  <ResponsiveContainer width="100%" height={300}>
                    <ComposedChart data={exp.histogram}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#475569" />
                      <XAxis dataKey="bin" tick={{ fill: '#94a3b8' }} />
                      <YAxis tick={{ fill: '#94a3b8' }} />
                      <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: 'none' }} />
                      <Bar dataKey="pct" fill={COLORS[idx % COLORS.length]} radius={[4, 4, 0, 0]} name="% of Reads" />
                      <Line type="monotone" dataKey="pct" stroke="#fff" strokeWidth={2} dot={false} />
                    </ComposedChart>
                  </ResponsiveContainer>
                </div>
                
                <div className="space-y-3">
                  <div className="bg-slate-800 rounded-lg p-4">
                    <h4 className="text-sm text-slate-400 mb-2">Key Metrics</h4>
                    <div className="space-y-2">
                      <div className="flex justify-between">
                        <span className="text-slate-400">N50</span>
                        <span className="font-mono font-bold text-amber-400">{formatNumber(exp.n50)} bp</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-400">Mean</span>
                        <span className="font-mono">{formatNumber(exp.mean_length)} bp</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-400">Median</span>
                        <span className="font-mono">{formatNumber(exp.median_length)} bp</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-400">Max</span>
                        <span className="font-mono text-emerald-400">{formatNumber(exp.max_length)} bp</span>
                      </div>
                    </div>
                  </div>
                  
                  <div className="bg-slate-800 rounded-lg p-4">
                    <h4 className="text-sm text-slate-400 mb-2">Length Thresholds</h4>
                    <div className="space-y-2">
                      <div className="flex justify-between items-center">
                        <span className="text-slate-400">&gt;1kb</span>
                        <div className="flex items-center gap-2">
                          <span className="font-mono">{exp.pct_gt_1kb}%</span>
                          <QualityBadge value={exp.pct_gt_1kb} thresholds={{ poor: 70, ok: 85 }} />
                        </div>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-slate-400">&gt;5kb</span>
                        <div className="flex items-center gap-2">
                          <span className="font-mono">{exp.pct_gt_5kb}%</span>
                          <QualityBadge value={exp.pct_gt_5kb} thresholds={{ poor: 20, ok: 35 }} />
                        </div>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-slate-400">&gt;10kb</span>
                        <div className="flex items-center gap-2">
                          <span className="font-mono">{exp.pct_gt_10kb}%</span>
                          <QualityBadge value={exp.pct_gt_10kb} thresholds={{ poor: 10, ok: 20 }} />
                        </div>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-slate-400">&gt;20kb</span>
                        <span className="font-mono">{exp.pct_gt_20kb}%</span>
                      </div>
                    </div>
                  </div>

                  <div className="bg-slate-800 rounded-lg p-4">
                    <h4 className="text-sm text-slate-400 mb-2">Run Info</h4>
                    <div className="space-y-1 text-sm">
                      <div className="flex justify-between">
                        <span className="text-slate-400">Device</span>
                        <span>{exp.device}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-400">Date</span>
                        <span>{exp.date}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-400">Reads</span>
                        <span>{formatNumber(exp.total_reads)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-400">Bases</span>
                        <span>{formatNumber(exp.total_bases)}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            );
          })()}
        </div>
      )}

      {/* Table View */}
      {viewMode === 'table' && (
        <div className="bg-slate-800 rounded-lg p-4 overflow-x-auto">
          <h3 className="font-semibold mb-3">Summary Table</h3>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-slate-400 border-b border-slate-700">
                <th className="text-left pb-3 px-2">Experiment</th>
                <th className="text-right pb-3 px-2">Reads</th>
                <th className="text-right pb-3 px-2">Bases</th>
                <th className="text-right pb-3 px-2">Mean</th>
                <th className="text-right pb-3 px-2">Median</th>
                <th className="text-right pb-3 px-2">N50</th>
                <th className="text-right pb-3 px-2">N90</th>
                <th className="text-right pb-3 px-2">Max</th>
                <th className="text-right pb-3 px-2">&gt;10kb</th>
                <th className="text-center pb-3 px-2">Quality</th>
              </tr>
            </thead>
            <tbody>
              {filteredExperiments.map((exp, idx) => (
                <tr key={exp.id} className="border-b border-slate-700/50 hover:bg-slate-700/30">
                  <td className="py-3 px-2">
                    <div className="flex items-center gap-2">
                      <span 
                        className="w-3 h-3 rounded-full" 
                        style={{ backgroundColor: COLORS[idx % COLORS.length] }}
                      />
                      <span className="font-medium">{exp.name}</span>
                    </div>
                  </td>
                  <td className="py-3 px-2 text-right font-mono">{formatNumber(exp.total_reads)}</td>
                  <td className="py-3 px-2 text-right font-mono">{formatNumber(exp.total_bases)}</td>
                  <td className="py-3 px-2 text-right font-mono">{formatNumber(exp.mean_length)}</td>
                  <td className="py-3 px-2 text-right font-mono">{formatNumber(exp.median_length)}</td>
                  <td className="py-3 px-2 text-right font-mono text-amber-400">{formatNumber(exp.n50)}</td>
                  <td className="py-3 px-2 text-right font-mono">{formatNumber(exp.n90)}</td>
                  <td className="py-3 px-2 text-right font-mono text-emerald-400">{formatNumber(exp.max_length)}</td>
                  <td className="py-3 px-2 text-right font-mono">{exp.pct_gt_10kb}%</td>
                  <td className="py-3 px-2 text-center">
                    <QualityBadge 
                      value={exp.n50} 
                      thresholds={{ poor: 3000, ok: 6000 }} 
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* CLI Command Reference */}
      <div className="bg-slate-800 rounded-lg p-4 mt-4">
        <h3 className="font-semibold mb-2">Generate This Analysis</h3>
        <div className="bg-slate-900 rounded p-3 font-mono text-xs space-y-1">
          <div className="text-slate-500"># Pattern B orchestration with provenance</div>
          <div className="text-emerald-400">
            $ ont_experiments.py run readlen {filteredExperiments.map(e => e.id).join(' ')} \
          </div>
          <div className="text-emerald-400 pl-4">--json comparison.json --plot comparison.png --plot-type overlay</div>
          <div className="text-slate-500 mt-2"># Or directly with ont_readlen.py</div>
          <div className="text-blue-400">
            $ ont_readlen.py {filteredExperiments.map(e => `/path/to/${e.name}`).slice(0, 2).join(' ')} ... \
          </div>
          <div className="text-blue-400 pl-4">--json stats.json --plot dist.png --plot-type overlay</div>
        </div>
      </div>

      {/* Footer */}
      <div className="mt-6 text-center text-slate-500 text-xs">
        ONT Read Length Distribution v2.1 â€¢ Part of ONT Ecosystem â€¢ Single Molecule Sequencing Lab
      </div>
    </div>
  );
}
