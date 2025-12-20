import React, { useState } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell, AreaChart, Area } from 'recharts';

// Real data from Great Lakes turbo storage
const experimentStats = { total: 213, canonical: 118, manuscript: 37, withQC: 37 };

const qcCategories = [
  { name: 'Complete', value: 99, color: '#10b981' },
  { name: 'Non-canonical', value: 51, color: '#6b7280' },
  { name: 'Other', value: 25, color: '#f59e0b' },
  { name: 'Derived', value: 15, color: '#8b5cf6' },
  { name: 'Tiny', value: 6, color: '#3b82f6' },
  { name: 'No Summary', value: 9, color: '#ef4444' },
];

const deviceDistribution = [
  { name: 'MD-101527', runs: 43 },
  { name: 'MD-102066', runs: 42 },
  { name: 'MN47455', runs: 36 },
  { name: 'MD-100098', runs: 31 },
  { name: 'PromethION', runs: 12 },
];

const endReasonData = [
  { exp: 'Eco53KI', signalPositive: 99.56, unblock: 0.11 },
  { exp: 'PvuII_pCYP', signalPositive: 99.08, unblock: 0.47 },
  { exp: 'BciVI_pCYP', signalPositive: 98.44, unblock: 1.32 },
  { exp: 'Cas9_NEB', signalPositive: 98.29, unblock: 1.57 },
  { exp: 'pCYP_rapid', signalPositive: 98.04, unblock: 1.65 },
  { exp: 'pCYP_dA', signalPositive: 85.45, unblock: 10.48 },
];

const recentRuns = [
  { date: '2025-12-08', name: 'IF_NewBCPart4_SMA_seq', device: 'MD-100098', status: 'complete' },
  { date: '2025-11-24', name: 'IF_Part4_CIP_SMA_seq', device: 'MD-102066', status: 'complete' },
  { date: '2025-10-23', name: 'SMS_RC_Eco53KI_PvuII', device: 'MD-101527', status: 'manuscript' },
  { date: '2025-10-16', name: 'Cas9_gRNAs_MT5', device: 'MD-101527', status: 'complete' },
];

const throughput = [
  { hr: 0, gb: 0 }, { hr: 8, gb: 8.5 }, { hr: 16, gb: 22.8 },
  { hr: 24, gb: 42.1 }, { hr: 32, gb: 61.8 }, { hr: 40, gb: 74.2 }, { hr: 48, gb: 80.1 },
];

export default function Dashboard() {
  const [tab, setTab] = useState('overview');

  return (
    <div className="min-h-screen bg-slate-900 text-white p-4">
      <div className="mb-6">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          ðŸ”¬ ONT Ecosystem Dashboard
        </h1>
        <p className="text-slate-400 text-sm">Single Molecule Sequencing Lab â€¢ U-M Great Lakes</p>
      </div>

      <div className="flex gap-2 mb-4">
        {['overview', 'qc', 'workflow'].map(t => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-3 py-1.5 rounded text-sm font-medium ${tab === t ? 'bg-emerald-600' : 'bg-slate-700 hover:bg-slate-600'}`}>
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>

      {tab === 'overview' && (
        <div className="space-y-4">
          <div className="grid grid-cols-4 gap-3">
            <div className="bg-slate-800 rounded-lg p-4">
              <div className="text-slate-400 text-sm">Total Runs</div>
              <div className="text-2xl font-bold">{experimentStats.total}</div>
            </div>
            <div className="bg-slate-800 rounded-lg p-4">
              <div className="text-slate-400 text-sm">Canonical</div>
              <div className="text-2xl font-bold text-emerald-400">{experimentStats.canonical}</div>
            </div>
            <div className="bg-slate-800 rounded-lg p-4">
              <div className="text-slate-400 text-sm">Manuscript</div>
              <div className="text-2xl font-bold text-purple-400">{experimentStats.manuscript}</div>
            </div>
            <div className="bg-slate-800 rounded-lg p-4">
              <div className="text-slate-400 text-sm">With QC</div>
              <div className="text-2xl font-bold text-amber-400">{experimentStats.withQC}</div>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="bg-slate-800 rounded-lg p-4">
              <h3 className="font-semibold mb-3">QC Categories</h3>
              <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                  <Pie data={qcCategories} cx="50%" cy="50%" outerRadius={70} dataKey="value" label={({ name }) => name}>
                    {qcCategories.map((e, i) => <Cell key={i} fill={e.color} />)}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="bg-slate-800 rounded-lg p-4">
              <h3 className="font-semibold mb-3">Sequencer Usage</h3>
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={deviceDistribution}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#475569" />
                  <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 11 }} />
                  <YAxis tick={{ fill: '#94a3b8' }} />
                  <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: 'none' }} />
                  <Bar dataKey="runs" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="bg-slate-800 rounded-lg p-4">
            <h3 className="font-semibold mb-3">Recent Runs</h3>
            <table className="w-full text-sm">
              <thead><tr className="text-slate-400 border-b border-slate-700">
                <th className="text-left pb-2">Date</th><th className="text-left pb-2">Experiment</th>
                <th className="text-left pb-2">Device</th><th className="text-left pb-2">Status</th>
              </tr></thead>
              <tbody>
                {recentRuns.map((r, i) => (
                  <tr key={i} className="border-b border-slate-700/50">
                    <td className="py-2 text-slate-400">{r.date}</td>
                    <td className="py-2">{r.name}</td>
                    <td className="py-2 text-slate-400">{r.device}</td>
                    <td className="py-2"><span className={`px-2 py-0.5 rounded text-xs ${r.status === 'complete' ? 'bg-emerald-900 text-emerald-300' : 'bg-purple-900 text-purple-300'}`}>{r.status}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {tab === 'qc' && (
        <div className="space-y-4">
          <div className="bg-slate-800 rounded-lg p-4">
            <h3 className="font-semibold mb-1">End Reason Analysis</h3>
            <p className="text-slate-400 text-xs mb-3">Signal positive â‰¥80% indicates good quality</p>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={endReasonData} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#475569" />
                <XAxis type="number" domain={[0, 100]} tick={{ fill: '#94a3b8' }} />
                <YAxis dataKey="exp" type="category" width={80} tick={{ fill: '#94a3b8', fontSize: 11 }} />
                <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: 'none' }} />
                <Legend />
                <Bar dataKey="signalPositive" name="Signal Positive %" fill="#10b981" stackId="a" />
                <Bar dataKey="unblock" name="Unblock %" fill="#f59e0b" stackId="a" />
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div className="bg-slate-800 rounded-lg p-4 text-center">
              <div className="text-3xl font-bold text-emerald-400">89.8%</div>
              <div className="text-slate-400 text-sm">Avg Signal Positive</div>
              <div className="text-emerald-500 text-xs">âœ“ Pass</div>
            </div>
            <div className="bg-slate-800 rounded-lg p-4 text-center">
              <div className="text-3xl font-bold text-amber-400">9.3%</div>
              <div className="text-slate-400 text-sm">Avg Unblock</div>
              <div className="text-slate-500 text-xs">Adaptive sampling</div>
            </div>
            <div className="bg-slate-800 rounded-lg p-4 text-center">
              <div className="text-3xl font-bold text-blue-400">0.13%</div>
              <div className="text-slate-400 text-sm">Avg Mux Change</div>
              <div className="text-emerald-500 text-xs">âœ“ Low</div>
            </div>
          </div>

          <div className="bg-slate-800 rounded-lg p-4">
            <h3 className="font-semibold mb-2">Run QC Command</h3>
            <div className="bg-slate-900 rounded p-3 font-mono text-xs">
              <div className="text-slate-500"># Pattern B orchestration with provenance</div>
              <div className="text-emerald-400">$ ont_experiments.py run end_reasons exp-ef0e622b \</div>
              <div className="text-emerald-400 pl-4">--json qc.json --plot qc.png</div>
              <div className="text-slate-300 mt-2">Signal positive: 97.44% âœ“ PASS</div>
            </div>
          </div>
        </div>
      )}

      {tab === 'workflow' && (
        <div className="space-y-4">
          <div className="bg-slate-800 rounded-lg p-4">
            <h3 className="font-semibold mb-4">ONT Workflow Pipeline</h3>
            <div className="flex items-center justify-between text-sm">
              {['ðŸ“‚ Discover', 'ðŸ“ Register', 'ðŸ“Š Monitor', 'ðŸ§¬ Basecall', 'âœ… QC', 'ðŸŽ¯ Align', 'ðŸ“œ History'].map((step, i) => (
                <React.Fragment key={i}>
                  <div className="flex flex-col items-center">
                    <div className={`w-10 h-10 rounded-full flex items-center justify-center text-lg ${i < 3 ? 'bg-emerald-600' : 'bg-slate-700'}`}>
                      {step.split(' ')[0]}
                    </div>
                    <div className="text-xs mt-1 text-slate-400">{step.split(' ')[1]}</div>
                  </div>
                  {i < 6 && <div className="flex-1 h-0.5 bg-slate-700 mx-1" />}
                </React.Fragment>
              ))}
            </div>
          </div>

          <div className="bg-slate-800 rounded-lg p-4">
            <h3 className="font-semibold mb-3">Run Throughput</h3>
            <ResponsiveContainer width="100%" height={180}>
              <AreaChart data={throughput}>
                <CartesianGrid strokeDasharray="3 3" stroke="#475569" />
                <XAxis dataKey="hr" tick={{ fill: '#94a3b8' }} label={{ value: 'Hours', position: 'bottom', fill: '#94a3b8', fontSize: 11 }} />
                <YAxis tick={{ fill: '#94a3b8' }} label={{ value: 'Gb', angle: -90, position: 'left', fill: '#94a3b8', fontSize: 11 }} />
                <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: 'none' }} />
                <Area type="monotone" dataKey="gb" stroke="#10b981" fill="#10b981" fillOpacity={0.3} />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          <div className="bg-slate-800 rounded-lg p-4">
            <h3 className="font-semibold mb-2">Full Workflow Commands</h3>
            <div className="bg-slate-900 rounded p-3 font-mono text-xs space-y-2">
              <div><span className="text-slate-500"># Initialize</span><br/><span className="text-emerald-400">$ ont_experiments.py init --git</span></div>
              <div><span className="text-slate-500"># Discover data</span><br/><span className="text-emerald-400">$ ont_experiments.py discover /nfs/turbo/umms-athey/sequencing_data --register</span></div>
              <div><span className="text-slate-500"># Monitor live run</span><br/><span className="text-emerald-400">$ ont_experiments.py run monitoring exp-2272e10f --live</span></div>
              <div><span className="text-slate-500"># Basecall on GPU (SLURM)</span><br/><span className="text-emerald-400">$ sbatch --partition=spgpu --gres=gpu:1 --wrap="ont_experiments.py run basecalling exp-ef0e622b --model sup@v5.0.0"</span></div>
              <div><span className="text-slate-500"># View history</span><br/><span className="text-emerald-400">$ ont_experiments.py history exp-ef0e622b</span></div>
            </div>
          </div>
        </div>
      )}

      <div className="mt-6 text-center text-slate-500 text-xs">
        ONT Ecosystem v2.1 â€¢ Real data from Great Lakes HPC
      </div>
    </div>
  );
}
