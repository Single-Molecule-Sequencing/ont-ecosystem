import React, { useState, useMemo } from 'react';
import { Database, FlaskConical, Activity, GitBranch, Server, Clock, CheckCircle, XCircle, Tag, ChevronRight, BarChart3, Dna, HardDrive, Cloud, Play, Search, Filter, Zap, Layers, Globe, Terminal, FileJson } from 'lucide-react';

// Mock data representing what the registry would look like
const mockExperiments = [
  {
    id: 'exp-8a3f2c1b9d4e',
    name: 'CYP2D6_Patient_Cohort_2025Q4',
    location: '/nfs/turbo/umms-bleu-secure/sequencing/promethion/2025-12-15_CYP2D6',
    status: 'analyzed',
    source: 'local',
    platform: 'PromethION',
    flowcell_type: 'FLO-PRO114M',
    flowcell_id: 'PAW12345',
    kit: 'SQK-LSK114',
    chemistry: 'R10.4.1',
    data_format: 'pod5',
    file_count: 48,
    total_size_gb: 312.7,
    total_reads: 15420000,
    run_started: '2025-12-15T08:30:00Z',
    tags: ['cyp2d6', 'pharmacogenomics', 'clinical', 'priority'],
    events: [
      { timestamp: '2025-12-15T08:30:00Z', type: 'discovered', agent: 'claude-web', machine: 'gl-login1.arc-ts.umich.edu' },
      { timestamp: '2025-12-15T09:00:00Z', type: 'registered', agent: 'claude-web', machine: 'gl-login1.arc-ts.umich.edu' },
      { timestamp: '2025-12-15T10:30:00Z', type: 'analysis', analysis: 'end_reasons', exit_code: 0, duration_seconds: 245, 
        results: { total_reads: 15420000, signal_positive_pct: 92.3, quality_status: 'PASS' },
        hpc: { scheduler: 'slurm', job_id: '48392571', partition: 'standard', gpus: ['NVIDIA A40'] } },
      { timestamp: '2025-12-15T14:00:00Z', type: 'analysis', analysis: 'basecalling', exit_code: 0, duration_seconds: 7200,
        results: { total_reads: 15420000, mean_qscore: 18.7, median_qscore: 19.1, n50: 12500 },
        parameters: { model: 'dna_r10.4.1_e8.2_400bps_sup@v5.0.0', model_tier: 'sup' },
        hpc: { scheduler: 'slurm', job_id: '48392892', partition: 'sigbio-a40', nodes: ['arm003'], gpus: ['NVIDIA A40', 'NVIDIA A40'] } },
    ]
  },
  {
    id: 'exp-c7b9e4f2a1d8',
    name: 'SMA_Plasmid_Standards_v3',
    location: '/nfs/turbo/umms-bleu-secure/sequencing/promethion/2025-12-10_SMA_Standards',
    status: 'qc_complete',
    source: 'local',
    platform: 'PromethION',
    flowcell_type: 'FLO-PRO114M',
    kit: 'SQK-LSK114',
    chemistry: 'R10.4.1',
    data_format: 'pod5',
    file_count: 24,
    total_size_gb: 156.3,
    total_reads: 8240000,
    run_started: '2025-12-10T14:00:00Z',
    tags: ['sma-seq', 'standards', 'error-calibration'],
    events: [
      { timestamp: '2025-12-10T14:00:00Z', type: 'discovered', agent: 'manual', machine: 'armis2.arc-ts.umich.edu' },
      { timestamp: '2025-12-10T14:30:00Z', type: 'registered', agent: 'claude-code', machine: 'armis2.arc-ts.umich.edu' },
      { timestamp: '2025-12-10T15:00:00Z', type: 'analysis', analysis: 'end_reasons', exit_code: 0, duration_seconds: 180,
        results: { total_reads: 8240000, signal_positive_pct: 94.1, quality_status: 'PASS' } },
    ]
  },
  {
    id: 'exp-f1a2b3c4d5e6',
    name: 'GIAB_HG002_Validation',
    location: '/nfs/turbo/umms-bleu-secure/public_data/giab_2025.01',
    status: 'analyzing',
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
    events: [
      { timestamp: '2025-12-01T10:00:00Z', type: 'discovered', agent: 'claude-web', machine: 'gl-login1.arc-ts.umich.edu' },
      { timestamp: '2025-12-01T10:30:00Z', type: 'analysis', analysis: 'basecalling', exit_code: null, duration_seconds: null,
        hpc: { scheduler: 'slurm', job_id: '48391234', partition: 'sigbio-a40', status: 'RUNNING' } },
    ]
  },
];

const publicDatasets = [
  { id: 'giab_2025.01', name: 'GIAB 2025.01 Latest', category: 'GIAB', size: '~400GB', featured: true },
  { id: 'gm24385_2023.12', name: 'GM24385 R10.4.1', category: 'Human Reference', size: '~300GB', featured: true },
  { id: 'hereditary_cancer_2025.09', name: 'Hereditary Cancer Panel', category: 'Cancer', size: '~100GB', featured: true },
  { id: 'colo829_2024.03', name: 'COLO829 Melanoma', category: 'Cancer', size: '~150GB', featured: false },
  { id: 'zymo_16s_2025.09', name: 'ZymoBIOMICS 16S', category: 'Microbial', size: '~20GB', featured: false },
  { id: 'lc2024_t2t', name: 'T2T Reference', category: 'Human Reference', size: '~200GB', featured: true },
];

const StatusBadge = ({ status }) => {
  const configs = {
    discovered: { bg: 'bg-slate-100', text: 'text-slate-700', icon: Search },
    registered: { bg: 'bg-blue-100', text: 'text-blue-700', icon: Database },
    analyzing: { bg: 'bg-amber-100', text: 'text-amber-700', icon: Activity },
    qc_complete: { bg: 'bg-emerald-100', text: 'text-emerald-700', icon: CheckCircle },
    analyzed: { bg: 'bg-violet-100', text: 'text-violet-700', icon: BarChart3 },
    archived: { bg: 'bg-gray-100', text: 'text-gray-600', icon: HardDrive },
  };
  const config = configs[status] || configs.discovered;
  const Icon = config.icon;
  
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${config.bg} ${config.text}`}>
      <Icon className="w-3 h-3" />
      {status.replace('_', ' ')}
    </span>
  );
};

const EventTimeline = ({ events }) => {
  return (
    <div className="space-y-3">
      {events.slice().reverse().map((event, idx) => (
        <div key={idx} className="flex gap-3">
          <div className="flex flex-col items-center">
            <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
              event.type === 'analysis' 
                ? event.exit_code === 0 ? 'bg-emerald-100 text-emerald-600' 
                  : event.exit_code === null ? 'bg-amber-100 text-amber-600' 
                  : 'bg-red-100 text-red-600'
                : 'bg-blue-100 text-blue-600'
            }`}>
              {event.type === 'analysis' ? (
                event.exit_code === 0 ? <CheckCircle className="w-4 h-4" /> 
                : event.exit_code === null ? <Activity className="w-4 h-4 animate-pulse" />
                : <XCircle className="w-4 h-4" />
              ) : event.type === 'discovered' ? <Search className="w-4 h-4" />
                : <Database className="w-4 h-4" />}
            </div>
            {idx < events.length - 1 && <div className="w-0.5 h-full bg-gray-200 mt-1" />}
          </div>
          <div className="flex-1 pb-4">
            <div className="flex items-center gap-2">
              <span className="font-medium text-gray-900 text-sm">
                {event.type === 'analysis' ? event.analysis : event.type}
              </span>
              {event.hpc && (
                <span className="text-xs bg-violet-50 text-violet-700 px-2 py-0.5 rounded-full">
                  SLURM #{event.hpc.job_id}
                </span>
              )}
            </div>
            <div className="text-xs text-gray-500 mt-0.5">
              {new Date(event.timestamp).toLocaleString()} • {event.agent} @ {event.machine?.split('.')[0]}
            </div>
            {event.results && (
              <div className="mt-2 grid grid-cols-2 gap-2 text-xs">
                {Object.entries(event.results).slice(0, 4).map(([k, v]) => (
                  <div key={k} className="bg-gray-50 rounded px-2 py-1">
                    <span className="text-gray-500">{k.replace(/_/g, ' ')}: </span>
                    <span className="font-medium text-gray-700">
                      {typeof v === 'number' ? v.toLocaleString() : v}
                    </span>
                  </div>
                ))}
              </div>
            )}
            {event.duration_seconds && (
              <div className="text-xs text-gray-400 mt-1 flex items-center gap-1">
                <Clock className="w-3 h-3" />
                {event.duration_seconds >= 3600 
                  ? `${(event.duration_seconds / 3600).toFixed(1)}h`
                  : `${Math.round(event.duration_seconds)}s`}
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
};

const ExperimentCard = ({ experiment, onSelect, isSelected }) => {
  return (
    <div 
      onClick={() => onSelect(experiment)}
      className={`bg-white rounded-xl border-2 p-4 cursor-pointer transition-all hover:shadow-lg ${
        isSelected ? 'border-violet-500 shadow-lg ring-2 ring-violet-100' : 'border-gray-100 hover:border-gray-200'
      }`}
    >
      <div className="flex justify-between items-start mb-3">
        <div>
          <div className="text-xs font-mono text-gray-400 mb-1">{experiment.id}</div>
          <h3 className="font-semibold text-gray-900 text-sm leading-tight">{experiment.name}</h3>
        </div>
        <StatusBadge status={experiment.status} />
      </div>
      
      <div className="grid grid-cols-3 gap-3 text-xs mb-3">
        <div className="text-center p-2 bg-gray-50 rounded-lg">
          <div className="text-gray-400 mb-1">Reads</div>
          <div className="font-semibold text-gray-700">{(experiment.total_reads / 1e6).toFixed(1)}M</div>
        </div>
        <div className="text-center p-2 bg-gray-50 rounded-lg">
          <div className="text-gray-400 mb-1">Size</div>
          <div className="font-semibold text-gray-700">{experiment.total_size_gb.toFixed(0)}GB</div>
        </div>
        <div className="text-center p-2 bg-gray-50 rounded-lg">
          <div className="text-gray-400 mb-1">Events</div>
          <div className="font-semibold text-gray-700">{experiment.events.length}</div>
        </div>
      </div>
      
      <div className="flex flex-wrap gap-1.5">
        {experiment.tags.slice(0, 3).map(tag => (
          <span key={tag} className="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded-full">
            {tag}
          </span>
        ))}
        {experiment.tags.length > 3 && (
          <span className="text-xs text-gray-400">+{experiment.tags.length - 3}</span>
        )}
      </div>
      
      <div className="flex items-center gap-2 mt-3 pt-3 border-t border-gray-100 text-xs text-gray-400">
        <Server className="w-3 h-3" />
        {experiment.platform}
        <span className="mx-1">•</span>
        <Dna className="w-3 h-3" />
        {experiment.chemistry}
        <span className="mx-1">•</span>
        {experiment.source === 'ont-open-data' && <Cloud className="w-3 h-3" />}
        {experiment.source}
      </div>
    </div>
  );
};

const CommandPreview = ({ experiment }) => {
  const commands = [
    { label: 'Discover', cmd: `ont_experiments.py discover ${experiment.location.split('/').slice(0, -1).join('/')}` },
    { label: 'Info', cmd: `ont_experiments.py info ${experiment.id}` },
    { label: 'Run QC', cmd: `ont_experiments.py run end_reasons ${experiment.id} --json qc.json` },
    { label: 'Basecall', cmd: `ont_experiments.py run basecalling ${experiment.id} --model sup --output calls.bam` },
    { label: 'History', cmd: `ont_experiments.py history ${experiment.id} --verbose` },
    { label: 'Export', cmd: `ont_experiments.py export ${experiment.id} > replay.sh` },
  ];
  
  return (
    <div className="bg-gray-900 rounded-xl p-4 font-mono text-xs">
      <div className="flex items-center gap-2 text-gray-400 mb-3">
        <Terminal className="w-4 h-4" />
        <span>Pattern B Orchestration</span>
      </div>
      <div className="space-y-2">
        {commands.map((c, i) => (
          <div key={i} className="flex items-start gap-2">
            <span className="text-violet-400 shrink-0">#</span>
            <span className="text-gray-500 shrink-0 w-16">{c.label}:</span>
            <span className="text-emerald-400 break-all">{c.cmd}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

const PublicDataPanel = () => {
  return (
    <div className="bg-gradient-to-br from-slate-50 to-blue-50 rounded-xl p-4">
      <div className="flex items-center gap-2 mb-4">
        <Globe className="w-5 h-5 text-blue-600" />
        <h3 className="font-semibold text-gray-900">ONT Open Data</h3>
        <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full ml-auto">30+ datasets</span>
      </div>
      
      <div className="space-y-2">
        {publicDatasets.filter(d => d.featured).map(dataset => (
          <div key={dataset.id} className="bg-white rounded-lg p-3 flex items-center justify-between hover:shadow-sm transition-shadow">
            <div>
              <div className="font-medium text-sm text-gray-800">{dataset.name}</div>
              <div className="text-xs text-gray-500">{dataset.category} • {dataset.size}</div>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono text-gray-400">{dataset.id}</span>
              <button className="p-1.5 bg-blue-50 text-blue-600 rounded-lg hover:bg-blue-100 transition-colors">
                <Cloud className="w-4 h-4" />
              </button>
            </div>
          </div>
        ))}
      </div>
      
      <div className="mt-3 text-xs text-center text-gray-500">
        <code className="bg-white px-2 py-1 rounded">ont_experiments.py public</code> to list all
      </div>
    </div>
  );
};

export default function ONTExperimentsDashboard() {
  const [selectedExp, setSelectedExp] = useState(mockExperiments[0]);
  const [filterStatus, setFilterStatus] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  
  const filteredExperiments = useMemo(() => {
    return mockExperiments.filter(exp => {
      const matchesStatus = filterStatus === 'all' || exp.status === filterStatus;
      const matchesSearch = searchQuery === '' || 
        exp.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        exp.id.includes(searchQuery) ||
        exp.tags.some(t => t.includes(searchQuery.toLowerCase()));
      return matchesStatus && matchesSearch;
    });
  }, [filterStatus, searchQuery]);

  const stats = useMemo(() => ({
    total: mockExperiments.length,
    totalReads: mockExperiments.reduce((acc, e) => acc + e.total_reads, 0),
    totalSize: mockExperiments.reduce((acc, e) => acc + e.total_size_gb, 0),
    totalEvents: mockExperiments.reduce((acc, e) => acc + e.events.length, 0),
  }), []);
  
  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 via-white to-violet-50 p-6">
      {/* Header */}
      <div className="max-w-7xl mx-auto mb-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 bg-gradient-to-br from-violet-500 to-purple-600 rounded-xl flex items-center justify-center shadow-lg shadow-violet-200">
              <Dna className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-gray-900">ONT Experiments Registry</h1>
              <p className="text-sm text-gray-500">Event-sourced nanopore experiment tracking</p>
            </div>
          </div>
          
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-3 text-sm">
              <div className="bg-white rounded-lg px-3 py-2 shadow-sm border border-gray-100">
                <span className="text-gray-500">Experiments:</span>
                <span className="font-semibold text-gray-800 ml-1">{stats.total}</span>
              </div>
              <div className="bg-white rounded-lg px-3 py-2 shadow-sm border border-gray-100">
                <span className="text-gray-500">Total Reads:</span>
                <span className="font-semibold text-gray-800 ml-1">{(stats.totalReads / 1e6).toFixed(0)}M</span>
              </div>
              <div className="bg-white rounded-lg px-3 py-2 shadow-sm border border-gray-100">
                <span className="text-gray-500">Storage:</span>
                <span className="font-semibold text-gray-800 ml-1">{stats.totalSize.toFixed(0)}GB</span>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      {/* Main Content */}
      <div className="max-w-7xl mx-auto grid grid-cols-12 gap-6">
        {/* Left Panel - Experiment List */}
        <div className="col-span-4 space-y-4">
          {/* Search & Filter */}
          <div className="bg-white rounded-xl p-3 shadow-sm border border-gray-100">
            <div className="flex items-center gap-2 mb-3">
              <div className="flex-1 relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  type="text"
                  placeholder="Search experiments..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-9 pr-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-violet-200 focus:border-violet-400"
                />
              </div>
              <select
                value={filterStatus}
                onChange={(e) => setFilterStatus(e.target.value)}
                className="px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-violet-200"
              >
                <option value="all">All Status</option>
                <option value="discovered">Discovered</option>
                <option value="analyzing">Analyzing</option>
                <option value="qc_complete">QC Complete</option>
                <option value="analyzed">Analyzed</option>
              </select>
            </div>
          </div>
          
          {/* Experiment Cards */}
          <div className="space-y-3">
            {filteredExperiments.map(exp => (
              <ExperimentCard 
                key={exp.id} 
                experiment={exp} 
                onSelect={setSelectedExp}
                isSelected={selectedExp?.id === exp.id}
              />
            ))}
          </div>
          
          {/* Public Data */}
          <PublicDataPanel />
        </div>
        
        {/* Right Panel - Detail View */}
        <div className="col-span-8 space-y-4">
          {selectedExp && (
            <>
              {/* Experiment Header */}
              <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
                <div className="flex justify-between items-start mb-4">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs font-mono bg-gray-100 px-2 py-1 rounded text-gray-600">{selectedExp.id}</span>
                      <StatusBadge status={selectedExp.status} />
                    </div>
                    <h2 className="text-lg font-bold text-gray-900">{selectedExp.name}</h2>
                    <p className="text-sm text-gray-500 font-mono mt-1">{selectedExp.location}</p>
                  </div>
                  <div className="flex gap-2">
                    <button className="flex items-center gap-1.5 px-3 py-2 bg-violet-50 text-violet-700 rounded-lg text-sm font-medium hover:bg-violet-100 transition-colors">
                      <Play className="w-4 h-4" />
                      Run Analysis
                    </button>
                    <button className="flex items-center gap-1.5 px-3 py-2 bg-gray-100 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-200 transition-colors">
                      <FileJson className="w-4 h-4" />
                      Export
                    </button>
                  </div>
                </div>
                
                {/* Platform Info */}
                <div className="grid grid-cols-5 gap-4 py-4 border-y border-gray-100">
                  <div>
                    <div className="text-xs text-gray-400 mb-1">Platform</div>
                    <div className="font-medium text-gray-800">{selectedExp.platform}</div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-400 mb-1">Flowcell</div>
                    <div className="font-medium text-gray-800">{selectedExp.flowcell_type}</div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-400 mb-1">Kit</div>
                    <div className="font-medium text-gray-800">{selectedExp.kit}</div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-400 mb-1">Chemistry</div>
                    <div className="font-medium text-gray-800">{selectedExp.chemistry}</div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-400 mb-1">Format</div>
                    <div className="font-medium text-gray-800 uppercase">{selectedExp.data_format}</div>
                  </div>
                </div>
                
                {/* Stats */}
                <div className="grid grid-cols-4 gap-4 mt-4">
                  <div className="bg-gradient-to-br from-blue-50 to-blue-100 rounded-xl p-4 text-center">
                    <div className="text-2xl font-bold text-blue-700">{(selectedExp.total_reads / 1e6).toFixed(1)}M</div>
                    <div className="text-xs text-blue-600">Total Reads</div>
                  </div>
                  <div className="bg-gradient-to-br from-emerald-50 to-emerald-100 rounded-xl p-4 text-center">
                    <div className="text-2xl font-bold text-emerald-700">{selectedExp.total_size_gb.toFixed(0)}</div>
                    <div className="text-xs text-emerald-600">GB Data</div>
                  </div>
                  <div className="bg-gradient-to-br from-violet-50 to-violet-100 rounded-xl p-4 text-center">
                    <div className="text-2xl font-bold text-violet-700">{selectedExp.file_count}</div>
                    <div className="text-xs text-violet-600">POD5 Files</div>
                  </div>
                  <div className="bg-gradient-to-br from-amber-50 to-amber-100 rounded-xl p-4 text-center">
                    <div className="text-2xl font-bold text-amber-700">{selectedExp.events.length}</div>
                    <div className="text-xs text-amber-600">Events</div>
                  </div>
                </div>
                
                {/* Tags */}
                <div className="flex items-center gap-2 mt-4">
                  <Tag className="w-4 h-4 text-gray-400" />
                  {selectedExp.tags.map(tag => (
                    <span key={tag} className="text-sm bg-slate-100 text-slate-700 px-2.5 py-1 rounded-full hover:bg-slate-200 cursor-pointer transition-colors">
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
              
              {/* Event Timeline & Commands */}
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
                  <div className="flex items-center gap-2 mb-4">
                    <GitBranch className="w-5 h-5 text-violet-600" />
                    <h3 className="font-semibold text-gray-900">Event Timeline</h3>
                    <span className="text-xs bg-violet-100 text-violet-700 px-2 py-0.5 rounded-full ml-auto">
                      {selectedExp.events.length} events
                    </span>
                  </div>
                  <EventTimeline events={selectedExp.events} />
                </div>
                
                <div>
                  <CommandPreview experiment={selectedExp} />
                  
                  {/* HPC Info */}
                  {selectedExp.events.some(e => e.hpc) && (
                    <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100 mt-4">
                      <div className="flex items-center gap-2 mb-3">
                        <Server className="w-5 h-5 text-amber-600" />
                        <h3 className="font-semibold text-gray-900">HPC Provenance</h3>
                      </div>
                      <div className="space-y-2 text-sm">
                        {selectedExp.events.filter(e => e.hpc).slice(-2).map((e, i) => (
                          <div key={i} className="bg-amber-50 rounded-lg p-3">
                            <div className="flex items-center justify-between mb-1">
                              <span className="font-medium text-amber-800">{e.analysis}</span>
                              <span className="font-mono text-xs text-amber-600">Job #{e.hpc.job_id}</span>
                            </div>
                            <div className="text-xs text-amber-700">
                              {e.hpc.partition} • {e.hpc.nodes?.[0]} • {e.hpc.gpus?.join(', ')}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
