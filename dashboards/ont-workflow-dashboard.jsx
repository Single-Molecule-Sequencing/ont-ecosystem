import React, { useState, useMemo } from 'react';
import { Database, Activity, GitBranch, Server, Clock, CheckCircle, XCircle, Tag, BarChart3, Dna, HardDrive, Cloud, Play, Search, Globe, Terminal, FileJson, Workflow, Layers, AlertTriangle, TrendingUp, Zap, ChevronRight, ArrowRight, Settings, RefreshCw, Download, FileText } from 'lucide-react';

// Mock registry data
const mockExperiments = [
  {
    id: 'exp-8a3f2c1b9d4e',
    name: 'CYP2D6_Patient_Cohort_2025Q4',
    location: '/nfs/turbo/umms-bleu-secure/sequencing/promethion/2025-12-15_CYP2D6',
    status: 'pipeline_complete',
    source: 'local',
    platform: 'PromethION',
    flowcell_type: 'FLO-PRO114M',
    kit: 'SQK-LSK114',
    chemistry: 'R10.4.1',
    data_format: 'pod5',
    file_count: 48,
    total_size_gb: 312.7,
    total_reads: 15420000,
    tags: ['cyp2d6', 'pharmacogenomics', 'clinical', 'priority'],
    pipeline: {
      name: 'pharmaco-clinical',
      version: '1.0',
      status: 'completed',
      steps_completed: 6,
      steps_total: 6,
    },
    qc_summary: {
      overall: 'PASS',
      signal_positive_pct: 92.3,
      mean_qscore: 18.7,
      mapped_pct: 98.2,
      cyp2d6_diplotype: '*1/*4',
      cyp2d6_phenotype: 'Intermediate Metabolizer',
      actionable_drugs: 12,
    },
    events: [
      { timestamp: '2025-12-15T08:30:00Z', type: 'discovered', agent: 'claude-web' },
      { timestamp: '2025-12-15T08:35:00Z', type: 'pipeline_start', pipeline: 'pharmaco-clinical' },
      { timestamp: '2025-12-15T08:40:00Z', type: 'analysis', analysis: 'end_reasons', exit_code: 0, duration_seconds: 245,
        results: { quality_status: 'PASS', signal_positive_pct: 92.3 },
        hpc: { job_id: '48392571', partition: 'standard' } },
      { timestamp: '2025-12-15T10:40:00Z', type: 'analysis', analysis: 'basecalling', exit_code: 0, duration_seconds: 7200,
        results: { mean_qscore: 18.7, n50: 12500 },
        hpc: { job_id: '48392892', partition: 'sigbio-a40', gpus: ['A40', 'A40'] } },
      { timestamp: '2025-12-15T12:00:00Z', type: 'analysis', analysis: 'alignment', exit_code: 0, duration_seconds: 1800,
        results: { mapped_pct: 98.2, mean_coverage: 45.3 } },
      { timestamp: '2025-12-15T13:30:00Z', type: 'analysis', analysis: 'variants', exit_code: 0, duration_seconds: 2400,
        results: { total_variants: 4521000, pass_variants: 4320000 } },
      { timestamp: '2025-12-15T14:00:00Z', type: 'analysis', analysis: 'cyp2d6', exit_code: 0, duration_seconds: 300,
        results: { diplotype: '*1/*4', phenotype: 'Intermediate Metabolizer', activity_score: 1.0 } },
      { timestamp: '2025-12-15T14:10:00Z', type: 'analysis', analysis: 'pharmcat', exit_code: 0, duration_seconds: 180,
        results: { drug_count: 42, actionable_count: 12 } },
      { timestamp: '2025-12-15T14:15:00Z', type: 'pipeline_complete', pipeline: 'pharmaco-clinical', duration_seconds: 20700 },
    ]
  },
  {
    id: 'exp-c7b9e4f2a1d8',
    name: 'SMA_Plasmid_Standards_v3',
    location: '/nfs/turbo/umms-bleu-secure/sequencing/promethion/2025-12-10_SMA_Standards',
    status: 'pipeline_running',
    platform: 'PromethION',
    flowcell_type: 'FLO-PRO114M',
    kit: 'SQK-LSK114',
    chemistry: 'R10.4.1',
    data_format: 'pod5',
    file_count: 24,
    total_size_gb: 156.3,
    total_reads: 8240000,
    tags: ['sma-seq', 'standards', 'error-calibration'],
    pipeline: {
      name: 'research-full',
      version: '1.0',
      status: 'running',
      current_step: 'basecalling',
      steps_completed: 1,
      steps_total: 5,
    },
    events: [
      { timestamp: '2025-12-18T14:00:00Z', type: 'discovered', agent: 'claude-code' },
      { timestamp: '2025-12-18T14:30:00Z', type: 'pipeline_start', pipeline: 'research-full' },
      { timestamp: '2025-12-18T14:35:00Z', type: 'analysis', analysis: 'end_reasons', exit_code: 0, duration_seconds: 180,
        results: { quality_status: 'PASS', signal_positive_pct: 94.1 } },
      { timestamp: '2025-12-18T14:40:00Z', type: 'analysis', analysis: 'basecalling', exit_code: null,
        hpc: { job_id: '48401234', partition: 'sigbio-a40', status: 'RUNNING' } },
    ]
  },
  {
    id: 'exp-f1a2b3c4d5e6',
    name: 'GIAB_HG002_Validation',
    location: '/nfs/turbo/umms-bleu-secure/public_data/giab_2025.01',
    status: 'qc_warning',
    source: 'ont-open-data',
    platform: 'PromethION',
    flowcell_type: 'FLO-PRO114M',
    kit: 'SQK-LSK114',
    chemistry: 'R10.4.1',
    data_format: 'pod5',
    file_count: 96,
    total_size_gb: 420.0,
    total_reads: 25000000,
    tags: ['giab', 'validation', 'benchmark'],
    qc_summary: {
      overall: 'WARNING',
      signal_positive_pct: 71.2,
      mean_qscore: 16.1,
    },
    events: [
      { timestamp: '2025-12-01T10:00:00Z', type: 'discovered', agent: 'claude-web' },
      { timestamp: '2025-12-01T10:30:00Z', type: 'analysis', analysis: 'end_reasons', exit_code: 0,
        results: { quality_status: 'WARNING', signal_positive_pct: 71.2 } },
    ]
  },
];

const pipelines = [
  { name: 'pharmaco-clinical', description: 'Clinical pharmacogenomics with PharmCAT', steps: 6, featured: true },
  { name: 'research-full', description: 'Complete research workflow with methylation', steps: 5, featured: true },
  { name: 'qc-fast', description: 'Quick QC assessment', steps: 2, featured: false },
  { name: 'validation', description: 'Validation against truth set', steps: 4, featured: false },
];

// Status badge component
const StatusBadge = ({ status }) => {
  const configs = {
    discovered: { bg: 'bg-slate-100', text: 'text-slate-700', icon: Search },
    pipeline_running: { bg: 'bg-amber-100', text: 'text-amber-700', icon: Activity },
    pipeline_complete: { bg: 'bg-emerald-100', text: 'text-emerald-700', icon: CheckCircle },
    pipeline_failed: { bg: 'bg-red-100', text: 'text-red-700', icon: XCircle },
    qc_warning: { bg: 'bg-orange-100', text: 'text-orange-700', icon: AlertTriangle },
    analyzed: { bg: 'bg-violet-100', text: 'text-violet-700', icon: BarChart3 },
  };
  const config = configs[status] || configs.discovered;
  const Icon = config.icon;
  
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${config.bg} ${config.text}`}>
      <Icon className="w-3 h-3" />
      {status.replace(/_/g, ' ')}
    </span>
  );
};

// Pipeline progress visualization
const PipelineProgress = ({ pipeline, events }) => {
  const steps = ['end_reasons', 'basecalling', 'alignment', 'variants', 'cyp2d6', 'pharmcat'];
  const stepLabels = ['QC', 'Basecall', 'Align', 'Variants', 'CYP2D6', 'PharmCAT'];
  
  const stepStatus = {};
  events?.filter(e => e.type === 'analysis').forEach(e => {
    stepStatus[e.analysis] = e.exit_code === 0 ? 'completed' : e.exit_code === null ? 'running' : 'failed';
  });
  
  return (
    <div className="flex items-center gap-1">
      {steps.slice(0, pipeline?.steps_total || 6).map((step, i) => {
        const status = stepStatus[step] || 'pending';
        const colors = {
          completed: 'bg-emerald-500',
          running: 'bg-amber-500 animate-pulse',
          failed: 'bg-red-500',
          pending: 'bg-gray-200',
        };
        
        return (
          <div key={step} className="flex items-center">
            <div className={`w-6 h-6 rounded-full ${colors[status]} flex items-center justify-center`}>
              {status === 'completed' && <CheckCircle className="w-3 h-3 text-white" />}
              {status === 'running' && <Activity className="w-3 h-3 text-white" />}
              {status === 'failed' && <XCircle className="w-3 h-3 text-white" />}
            </div>
            {i < (pipeline?.steps_total || 6) - 1 && (
              <div className={`w-4 h-0.5 ${status === 'completed' ? 'bg-emerald-500' : 'bg-gray-200'}`} />
            )}
          </div>
        );
      })}
    </div>
  );
};

// QC Summary Card
const QCSummaryCard = ({ qc }) => {
  if (!qc) return null;
  
  const statusColors = {
    PASS: 'from-emerald-500 to-emerald-600',
    WARNING: 'from-amber-500 to-orange-500',
    FAIL: 'from-red-500 to-red-600',
  };
  
  return (
    <div className={`bg-gradient-to-br ${statusColors[qc.overall] || statusColors.PASS} rounded-xl p-4 text-white`}>
      <div className="flex items-center justify-between mb-3">
        <span className="font-semibold">QC Status</span>
        <span className="text-2xl font-bold">{qc.overall}</span>
      </div>
      <div className="grid grid-cols-2 gap-2 text-sm">
        <div className="bg-white/20 rounded-lg px-2 py-1">
          <div className="text-white/80 text-xs">Signal+</div>
          <div className="font-semibold">{qc.signal_positive_pct}%</div>
        </div>
        <div className="bg-white/20 rounded-lg px-2 py-1">
          <div className="text-white/80 text-xs">Q-Score</div>
          <div className="font-semibold">{qc.mean_qscore}</div>
        </div>
        {qc.mapped_pct && (
          <div className="bg-white/20 rounded-lg px-2 py-1">
            <div className="text-white/80 text-xs">Mapped</div>
            <div className="font-semibold">{qc.mapped_pct}%</div>
          </div>
        )}
        {qc.actionable_drugs && (
          <div className="bg-white/20 rounded-lg px-2 py-1">
            <div className="text-white/80 text-xs">Actionable</div>
            <div className="font-semibold">{qc.actionable_drugs} drugs</div>
          </div>
        )}
      </div>
    </div>
  );
};

// Pharmacogenomics Result Card
const PharmacoCard = ({ qc }) => {
  if (!qc?.cyp2d6_diplotype) return null;
  
  const phenotypeColors = {
    'Intermediate Metabolizer': 'bg-amber-100 text-amber-800',
    'Normal Metabolizer': 'bg-emerald-100 text-emerald-800',
    'Poor Metabolizer': 'bg-red-100 text-red-800',
    'Ultrarapid Metabolizer': 'bg-violet-100 text-violet-800',
  };
  
  return (
    <div className="bg-white rounded-xl border border-violet-200 p-4">
      <div className="flex items-center gap-2 mb-3">
        <div className="w-8 h-8 bg-violet-100 rounded-lg flex items-center justify-center">
          <Dna className="w-4 h-4 text-violet-600" />
        </div>
        <div>
          <div className="font-semibold text-gray-900">CYP2D6 Result</div>
          <div className="text-xs text-gray-500">Pharmacogenomics</div>
        </div>
      </div>
      
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-sm text-gray-600">Diplotype</span>
          <span className="font-mono font-bold text-gray-900">{qc.cyp2d6_diplotype}</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-sm text-gray-600">Phenotype</span>
          <span className={`text-xs font-medium px-2 py-1 rounded-full ${phenotypeColors[qc.cyp2d6_phenotype] || 'bg-gray-100'}`}>
            {qc.cyp2d6_phenotype}
          </span>
        </div>
        <div className="pt-2 border-t border-gray-100">
          <div className="text-xs text-gray-500 mb-1">Actionable Drug Interactions</div>
          <div className="text-2xl font-bold text-violet-600">{qc.actionable_drugs}</div>
        </div>
      </div>
    </div>
  );
};

// Pipeline Card
const PipelineCard = ({ pipeline, onRun }) => {
  return (
    <div className="bg-white rounded-xl border border-gray-100 p-4 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between mb-3">
        <div>
          <div className="font-semibold text-gray-900">{pipeline.name}</div>
          <div className="text-xs text-gray-500">{pipeline.description}</div>
        </div>
        {pipeline.featured && (
          <span className="text-xs bg-violet-100 text-violet-700 px-2 py-0.5 rounded-full">Featured</span>
        )}
      </div>
      
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1">
          {Array.from({ length: pipeline.steps }).map((_, i) => (
            <div key={i} className="w-2 h-2 rounded-full bg-gray-200" />
          ))}
          <span className="text-xs text-gray-400 ml-1">{pipeline.steps} steps</span>
        </div>
        <button 
          onClick={() => onRun(pipeline)}
          className="flex items-center gap-1 px-2 py-1 bg-violet-50 text-violet-700 rounded-lg text-xs font-medium hover:bg-violet-100 transition-colors"
        >
          <Play className="w-3 h-3" />
          Run
        </button>
      </div>
    </div>
  );
};

// Event Timeline
const EventTimeline = ({ events }) => {
  const getEventIcon = (event) => {
    if (event.type === 'analysis') {
      if (event.exit_code === 0) return { icon: CheckCircle, color: 'bg-emerald-100 text-emerald-600' };
      if (event.exit_code === null) return { icon: Activity, color: 'bg-amber-100 text-amber-600 animate-pulse' };
      return { icon: XCircle, color: 'bg-red-100 text-red-600' };
    }
    if (event.type === 'pipeline_start') return { icon: Play, color: 'bg-blue-100 text-blue-600' };
    if (event.type === 'pipeline_complete') return { icon: CheckCircle, color: 'bg-emerald-100 text-emerald-600' };
    if (event.type === 'discovered') return { icon: Search, color: 'bg-gray-100 text-gray-600' };
    return { icon: Database, color: 'bg-gray-100 text-gray-600' };
  };
  
  return (
    <div className="space-y-2 max-h-96 overflow-y-auto pr-2">
      {events.slice().reverse().map((event, idx) => {
        const { icon: Icon, color } = getEventIcon(event);
        return (
          <div key={idx} className="flex gap-3 group">
            <div className={`w-7 h-7 rounded-full ${color} flex items-center justify-center shrink-0`}>
              <Icon className="w-3.5 h-3.5" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="font-medium text-gray-900 text-sm truncate">
                  {event.type === 'analysis' ? event.analysis : event.type.replace(/_/g, ' ')}
                </span>
                {event.hpc && (
                  <span className="text-xs bg-violet-50 text-violet-600 px-1.5 py-0.5 rounded shrink-0">
                    #{event.hpc.job_id}
                  </span>
                )}
              </div>
              <div className="text-xs text-gray-400">
                {new Date(event.timestamp).toLocaleString()}
                {event.duration_seconds && ` • ${event.duration_seconds >= 3600 
                  ? `${(event.duration_seconds / 3600).toFixed(1)}h`
                  : `${Math.round(event.duration_seconds)}s`}`}
              </div>
              {event.results && (
                <div className="flex flex-wrap gap-1 mt-1">
                  {Object.entries(event.results).slice(0, 3).map(([k, v]) => (
                    <span key={k} className="text-xs bg-gray-50 text-gray-600 px-1.5 py-0.5 rounded">
                      {k.replace(/_/g, ' ')}: {typeof v === 'number' ? v.toLocaleString() : v}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
};

// Main Dashboard
export default function ONTWorkflowDashboard() {
  const [selectedExp, setSelectedExp] = useState(mockExperiments[0]);
  const [activeTab, setActiveTab] = useState('overview');
  
  const stats = useMemo(() => ({
    total: mockExperiments.length,
    running: mockExperiments.filter(e => e.status === 'pipeline_running').length,
    completed: mockExperiments.filter(e => e.status === 'pipeline_complete').length,
    warnings: mockExperiments.filter(e => e.status === 'qc_warning').length,
  }), []);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-violet-50 p-4">
      {/* Header */}
      <div className="max-w-7xl mx-auto mb-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-violet-500 to-purple-600 rounded-xl flex items-center justify-center shadow-lg shadow-violet-200">
              <Workflow className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-lg font-bold text-gray-900">ONT Experiments + Pipeline</h1>
              <p className="text-xs text-gray-500">Event-sourced registry with workflow orchestration</p>
            </div>
          </div>
          
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-2 text-xs">
              <div className="bg-white rounded-lg px-2.5 py-1.5 shadow-sm border border-gray-100 flex items-center gap-1.5">
                <div className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
                <span className="text-gray-600">{stats.running} running</span>
              </div>
              <div className="bg-white rounded-lg px-2.5 py-1.5 shadow-sm border border-gray-100 flex items-center gap-1.5">
                <div className="w-2 h-2 rounded-full bg-emerald-500" />
                <span className="text-gray-600">{stats.completed} complete</span>
              </div>
              {stats.warnings > 0 && (
                <div className="bg-orange-50 rounded-lg px-2.5 py-1.5 border border-orange-200 flex items-center gap-1.5">
                  <AlertTriangle className="w-3 h-3 text-orange-500" />
                  <span className="text-orange-700">{stats.warnings} warnings</span>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
      
      {/* Main Content */}
      <div className="max-w-7xl mx-auto grid grid-cols-12 gap-4">
        {/* Left: Experiment List */}
        <div className="col-span-4 space-y-3">
          {/* Search */}
          <div className="bg-white rounded-xl p-2 shadow-sm border border-gray-100">
            <div className="flex items-center gap-2">
              <div className="flex-1 relative">
                <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  type="text"
                  placeholder="Search experiments..."
                  className="w-full pl-8 pr-3 py-1.5 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-violet-200"
                />
              </div>
            </div>
          </div>
          
          {/* Experiments */}
          {mockExperiments.map(exp => (
            <div
              key={exp.id}
              onClick={() => setSelectedExp(exp)}
              className={`bg-white rounded-xl border-2 p-3 cursor-pointer transition-all hover:shadow-lg ${
                selectedExp?.id === exp.id ? 'border-violet-500 shadow-lg ring-2 ring-violet-100' : 'border-gray-100'
              }`}
            >
              <div className="flex justify-between items-start mb-2">
                <div className="min-w-0">
                  <div className="text-xs font-mono text-gray-400 truncate">{exp.id}</div>
                  <h3 className="font-semibold text-gray-900 text-sm truncate">{exp.name}</h3>
                </div>
                <StatusBadge status={exp.status} />
              </div>
              
              {exp.pipeline && (
                <div className="mb-2">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs text-gray-500">{exp.pipeline.name}</span>
                    <span className="text-xs text-gray-400">
                      {exp.pipeline.steps_completed}/{exp.pipeline.steps_total}
                    </span>
                  </div>
                  <PipelineProgress pipeline={exp.pipeline} events={exp.events} />
                </div>
              )}
              
              <div className="flex items-center gap-2 text-xs text-gray-400">
                <span>{exp.platform}</span>
                <span>•</span>
                <span>{(exp.total_reads / 1e6).toFixed(1)}M reads</span>
                <span>•</span>
                <span>{exp.total_size_gb.toFixed(0)}GB</span>
              </div>
            </div>
          ))}
          
          {/* Available Pipelines */}
          <div className="bg-gradient-to-br from-violet-50 to-purple-50 rounded-xl p-3">
            <div className="flex items-center gap-2 mb-3">
              <Layers className="w-4 h-4 text-violet-600" />
              <span className="font-semibold text-gray-900 text-sm">Available Pipelines</span>
            </div>
            <div className="space-y-2">
              {pipelines.filter(p => p.featured).map(p => (
                <PipelineCard key={p.name} pipeline={p} onRun={() => {}} />
              ))}
            </div>
          </div>
        </div>
        
        {/* Right: Detail View */}
        <div className="col-span-8 space-y-4">
          {selectedExp && (
            <>
              {/* Header Card */}
              <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
                <div className="flex justify-between items-start mb-3">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs font-mono bg-gray-100 px-2 py-0.5 rounded">{selectedExp.id}</span>
                      <StatusBadge status={selectedExp.status} />
                    </div>
                    <h2 className="text-lg font-bold text-gray-900">{selectedExp.name}</h2>
                  </div>
                  <div className="flex gap-2">
                    <button className="flex items-center gap-1.5 px-3 py-1.5 bg-violet-600 text-white rounded-lg text-sm font-medium hover:bg-violet-700">
                      <Play className="w-4 h-4" />
                      Run Pipeline
                    </button>
                    <button className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-100 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-200">
                      <FileText className="w-4 h-4" />
                      Report
                    </button>
                  </div>
                </div>
                
                {/* Platform info row */}
                <div className="grid grid-cols-5 gap-3 py-3 border-y border-gray-100 text-sm">
                  <div>
                    <div className="text-xs text-gray-400">Platform</div>
                    <div className="font-medium">{selectedExp.platform}</div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-400">Flowcell</div>
                    <div className="font-medium">{selectedExp.flowcell_type}</div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-400">Kit</div>
                    <div className="font-medium">{selectedExp.kit}</div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-400">Chemistry</div>
                    <div className="font-medium">{selectedExp.chemistry}</div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-400">Format</div>
                    <div className="font-medium uppercase">{selectedExp.data_format}</div>
                  </div>
                </div>
                
                {/* Stats row */}
                <div className="grid grid-cols-4 gap-3 mt-3">
                  <div className="bg-blue-50 rounded-xl p-3 text-center">
                    <div className="text-xl font-bold text-blue-700">{(selectedExp.total_reads / 1e6).toFixed(1)}M</div>
                    <div className="text-xs text-blue-600">Reads</div>
                  </div>
                  <div className="bg-emerald-50 rounded-xl p-3 text-center">
                    <div className="text-xl font-bold text-emerald-700">{selectedExp.total_size_gb.toFixed(0)}</div>
                    <div className="text-xs text-emerald-600">GB Data</div>
                  </div>
                  <div className="bg-violet-50 rounded-xl p-3 text-center">
                    <div className="text-xl font-bold text-violet-700">{selectedExp.file_count}</div>
                    <div className="text-xs text-violet-600">POD5 Files</div>
                  </div>
                  <div className="bg-amber-50 rounded-xl p-3 text-center">
                    <div className="text-xl font-bold text-amber-700">{selectedExp.events.length}</div>
                    <div className="text-xs text-amber-600">Events</div>
                  </div>
                </div>
              </div>
              
              {/* Content Grid */}
              <div className="grid grid-cols-2 gap-4">
                {/* Left: QC + Pharmaco */}
                <div className="space-y-4">
                  {selectedExp.qc_summary && (
                    <QCSummaryCard qc={selectedExp.qc_summary} />
                  )}
                  {selectedExp.qc_summary?.cyp2d6_diplotype && (
                    <PharmacoCard qc={selectedExp.qc_summary} />
                  )}
                  
                  {/* CLI Preview */}
                  <div className="bg-gray-900 rounded-xl p-3 font-mono text-xs">
                    <div className="flex items-center gap-2 text-gray-400 mb-2">
                      <Terminal className="w-4 h-4" />
                      <span>CLI Commands</span>
                    </div>
                    <div className="space-y-1 text-emerald-400">
                      <div><span className="text-violet-400">#</span> ont_experiments.py info {selectedExp.id}</div>
                      <div><span className="text-violet-400">#</span> ont_experiments.py pipeline status {selectedExp.id}</div>
                      <div><span className="text-violet-400">#</span> ont_experiments.py qc {selectedExp.id} --format html</div>
                      <div><span className="text-violet-400">#</span> ont_experiments.py history {selectedExp.id} --verbose</div>
                    </div>
                  </div>
                </div>
                
                {/* Right: Timeline */}
                <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <GitBranch className="w-4 h-4 text-violet-600" />
                      <span className="font-semibold text-gray-900 text-sm">Event Timeline</span>
                    </div>
                    <span className="text-xs bg-violet-100 text-violet-700 px-2 py-0.5 rounded-full">
                      {selectedExp.events.length} events
                    </span>
                  </div>
                  <EventTimeline events={selectedExp.events} />
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
