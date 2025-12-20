import React, { useState, useMemo } from 'react';
import { Database, GitBranch, Dna, Search, Terminal, FileText, ArrowRight, CheckCircle, AlertTriangle, Zap, BarChart3, Copy, Play, Settings, RefreshCw, Layers, Target, Ruler, Edit3, Grid, ArrowLeftRight } from 'lucide-react';

// Edit distance visualization component
const EditDistanceVisualizer = ({ seq1, seq2, result }) => {
  if (!seq1 || !seq2) return null;
  
  const maxLen = Math.max(seq1.length, seq2.length);
  const cellSize = Math.min(24, 400 / maxLen);
  
  // Parse CIGAR to get alignment
  const parseAlignment = (cigar) => {
    if (!cigar) return null;
    const ops = [];
    const regex = /(\d+)([=XIDS])/g;
    let match;
    while ((match = regex.exec(cigar)) !== null) {
      const count = parseInt(match[1]);
      const op = match[2];
      for (let i = 0; i < count; i++) {
        ops.push(op);
      }
    }
    return ops;
  };
  
  const alignment = result?.cigar ? parseAlignment(result.cigar) : null;
  
  return (
    <div className="bg-gray-900 rounded-xl p-4 font-mono text-sm">
      <div className="flex items-center gap-2 text-gray-400 mb-3">
        <Ruler className="w-4 h-4" />
        <span>Sequence Alignment</span>
      </div>
      
      {/* Sequence display */}
      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <span className="text-gray-500 w-16 text-xs">Query:</span>
          <div className="flex gap-0.5 flex-wrap">
            {seq1.split('').map((base, i) => {
              const isMatch = alignment ? alignment[i] === '=' : seq2[i] === base;
              return (
                <span
                  key={i}
                  className={`w-6 h-6 flex items-center justify-center rounded text-xs font-bold ${
                    isMatch ? 'bg-emerald-900/50 text-emerald-400' : 'bg-red-900/50 text-red-400'
                  }`}
                >
                  {base}
                </span>
              );
            })}
          </div>
        </div>
        
        {alignment && (
          <div className="flex items-center gap-2">
            <span className="text-gray-500 w-16 text-xs">Align:</span>
            <div className="flex gap-0.5 flex-wrap">
              {alignment.slice(0, seq1.length).map((op, i) => (
                <span
                  key={i}
                  className={`w-6 h-6 flex items-center justify-center text-xs ${
                    op === '=' ? 'text-emerald-500' : 
                    op === 'X' ? 'text-red-500' : 
                    op === 'I' ? 'text-blue-500' : 
                    op === 'D' ? 'text-orange-500' : 'text-gray-500'
                  }`}
                >
                  {op === '=' ? '|' : op === 'X' ? '×' : op}
                </span>
              ))}
            </div>
          </div>
        )}
        
        <div className="flex items-center gap-2">
          <span className="text-gray-500 w-16 text-xs">Target:</span>
          <div className="flex gap-0.5 flex-wrap">
            {seq2.split('').map((base, i) => {
              const isMatch = alignment ? alignment[i] === '=' : seq1[i] === base;
              return (
                <span
                  key={i}
                  className={`w-6 h-6 flex items-center justify-center rounded text-xs font-bold ${
                    isMatch ? 'bg-emerald-900/50 text-emerald-400' : 'bg-red-900/50 text-red-400'
                  }`}
                >
                  {base}
                </span>
              );
            })}
          </div>
        </div>
      </div>
      
      {/* Legend */}
      <div className="flex items-center gap-4 mt-3 pt-3 border-t border-gray-800 text-xs text-gray-500">
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 bg-emerald-900/50 rounded" /> Match
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 bg-red-900/50 rounded" /> Mismatch
        </span>
        {alignment && (
          <>
            <span className="flex items-center gap-1">
              <span className="text-blue-500">I</span> Insertion
            </span>
            <span className="flex items-center gap-1">
              <span className="text-orange-500">D</span> Deletion
            </span>
          </>
        )}
      </div>
    </div>
  );
};

// Mock reference registry data
const mockReferences = [
  {
    name: 'GRCh38',
    path: '/nfs/turbo/umms-bleu-secure/references/GRCh38.fa',
    description: 'Human reference genome GRCh38 (no alt)',
    species: 'Homo sapiens',
    size_bp: 3088269832,
    contigs: 195,
    indices: { minimap2: 'GRCh38.mmi' },
  },
  {
    name: 'T2T-CHM13',
    path: '/nfs/turbo/umms-bleu-secure/references/chm13v2.0.fa',
    description: 'Telomere-to-Telomere CHM13 v2.0',
    species: 'Homo sapiens',
    size_bp: 3117292070,
    contigs: 24,
    indices: { minimap2: 'chm13v2.0.mmi' },
  },
  {
    name: 'CYP2D6_haplotypes',
    path: '/nfs/turbo/umms-bleu-secure/references/cyp2d6_haplotypes.fa',
    description: 'CYP2D6 star allele reference sequences',
    species: 'Homo sapiens',
    size_bp: 45000,
    contigs: 150,
    indices: {},
  },
];

// Mock alignment stats
const mockAlignmentStats = {
  input_file: 'exp-8a3f2c1b9d4e_basecalled.bam',
  reference: 'GRCh38',
  total_reads: 15420000,
  mapped_reads: 15267800,
  unmapped_reads: 152200,
  mapped_pct: 99.01,
  primary_alignments: 15100000,
  secondary_alignments: 120000,
  supplementary_alignments: 47800,
  mean_mapq: 58.5,
  median_mapq: 60,
  mean_read_length: 12500,
  n50_read_length: 18200,
  total_bases_aligned: 192750000000,
  mean_coverage: 45.3,
  pct_genome_covered_10x: 98.2,
  pct_genome_covered_30x: 95.1,
};

// Edit distance examples for pharmacogenomics
const editDistanceExamples = [
  {
    name: 'CYP2D6*1 vs *4',
    query: 'ATGGGCGCCCCGCTGAGC',
    target: 'ATGGGCACCCCGCTGAGC',
    description: 'Single nucleotide polymorphism (1846G>A)',
    use_case: 'Star allele discrimination',
  },
  {
    name: 'Barcode matching',
    query: 'ACGTACGTACGT',
    target: 'ACGTACGTTCGT',
    description: 'Barcode with 1 error',
    use_case: 'Demultiplexing with error tolerance',
  },
  {
    name: 'Indel detection',
    query: 'ATCGATCGATCG',
    target: 'ATCGAATCGATCG',
    description: 'Single base insertion',
    use_case: 'Variant verification',
  },
];

// Compute simple edit distance (for demo)
const computeEditDistance = (s1, s2) => {
  const m = s1.length;
  const n = s2.length;
  const dp = Array(m + 1).fill(null).map(() => Array(n + 1).fill(0));
  
  for (let i = 0; i <= m; i++) dp[i][0] = i;
  for (let j = 0; j <= n; j++) dp[0][j] = j;
  
  for (let i = 1; i <= m; i++) {
    for (let j = 1; j <= n; j++) {
      if (s1[i-1] === s2[j-1]) {
        dp[i][j] = dp[i-1][j-1];
      } else {
        dp[i][j] = 1 + Math.min(dp[i-1][j], dp[i][j-1], dp[i-1][j-1]);
      }
    }
  }
  
  return dp[m][n];
};

// Generate simple CIGAR for visualization
const generateCigar = (s1, s2) => {
  let cigar = '';
  const len = Math.min(s1.length, s2.length);
  let matchCount = 0;
  let mismatchCount = 0;
  
  for (let i = 0; i < len; i++) {
    if (s1[i] === s2[i]) {
      if (mismatchCount > 0) {
        cigar += `${mismatchCount}X`;
        mismatchCount = 0;
      }
      matchCount++;
    } else {
      if (matchCount > 0) {
        cigar += `${matchCount}=`;
        matchCount = 0;
      }
      mismatchCount++;
    }
  }
  
  if (matchCount > 0) cigar += `${matchCount}=`;
  if (mismatchCount > 0) cigar += `${mismatchCount}X`;
  
  return cigar;
};

// Reference card component
const ReferenceCard = ({ ref }) => (
  <div className="bg-white rounded-xl border border-gray-100 p-3 hover:shadow-md transition-shadow">
    <div className="flex items-start justify-between mb-2">
      <div>
        <div className="font-semibold text-gray-900">{ref.name}</div>
        <div className="text-xs text-gray-500">{ref.description}</div>
      </div>
      {ref.indices.minimap2 && (
        <span className="text-xs bg-emerald-100 text-emerald-700 px-2 py-0.5 rounded-full">indexed</span>
      )}
    </div>
    <div className="grid grid-cols-2 gap-2 text-xs">
      <div className="bg-gray-50 rounded-lg px-2 py-1">
        <span className="text-gray-500">Size:</span>
        <span className="ml-1 font-medium">{(ref.size_bp / 1e9).toFixed(2)} Gb</span>
      </div>
      <div className="bg-gray-50 rounded-lg px-2 py-1">
        <span className="text-gray-500">Contigs:</span>
        <span className="ml-1 font-medium">{ref.contigs}</span>
      </div>
    </div>
  </div>
);

// Main Dashboard
export default function ONTAlignDashboard() {
  const [activeTab, setActiveTab] = useState('editdist');
  const [seq1, setSeq1] = useState('ATGGGCGCCCCGCTGAGC');
  const [seq2, setSeq2] = useState('ATGGGCACCCCGCTGAGC');
  const [editMode, setEditMode] = useState('NW');
  const [showCigar, setShowCigar] = useState(true);
  
  // Compute edit distance result
  const editResult = useMemo(() => {
    if (!seq1 || !seq2) return null;
    const distance = computeEditDistance(seq1.toUpperCase(), seq2.toUpperCase());
    const cigar = generateCigar(seq1.toUpperCase(), seq2.toUpperCase());
    return {
      edit_distance: distance,
      normalized: distance / Math.max(seq1.length, seq2.length),
      cigar: cigar,
      query_length: seq1.length,
      target_length: seq2.length,
    };
  }, [seq1, seq2]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-blue-50 p-4">
      {/* Header */}
      <div className="max-w-6xl mx-auto mb-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-cyan-600 rounded-xl flex items-center justify-center shadow-lg shadow-blue-200">
              <Target className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-lg font-bold text-gray-900">ont-align</h1>
              <p className="text-xs text-gray-500">Alignment, Reference Management & Edit Distance</p>
            </div>
          </div>
          
          {/* Tab navigation */}
          <div className="flex items-center gap-1 bg-gray-100 rounded-lg p-1">
            {[
              { id: 'editdist', label: 'Edit Distance', icon: Edit3 },
              { id: 'align', label: 'Alignment', icon: ArrowLeftRight },
              { id: 'refs', label: 'References', icon: Database },
            ].map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                  activeTab === tab.id
                    ? 'bg-white text-gray-900 shadow-sm'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                <tab.icon className="w-4 h-4" />
                {tab.label}
              </button>
            ))}
          </div>
        </div>
      </div>
      
      {/* Main Content */}
      <div className="max-w-6xl mx-auto">
        {activeTab === 'editdist' && (
          <div className="grid grid-cols-12 gap-4">
            {/* Left: Input */}
            <div className="col-span-5 space-y-4">
              {/* Sequence Input */}
              <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <Ruler className="w-4 h-4 text-blue-600" />
                    <span className="font-semibold text-gray-900">Levenshtein Distance</span>
                  </div>
                  <select
                    value={editMode}
                    onChange={(e) => setEditMode(e.target.value)}
                    className="text-xs border border-gray-200 rounded-lg px-2 py-1"
                  >
                    <option value="NW">Global (NW)</option>
                    <option value="HW">Semi-global (HW)</option>
                    <option value="SHW">Infix (SHW)</option>
                  </select>
                </div>
                
                <div className="space-y-3">
                  <div>
                    <label className="text-xs text-gray-500 mb-1 block">Query Sequence</label>
                    <input
                      type="text"
                      value={seq1}
                      onChange={(e) => setSeq1(e.target.value.toUpperCase())}
                      className="w-full font-mono text-sm px-3 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-200 focus:border-blue-400"
                      placeholder="ACGT..."
                    />
                  </div>
                  <div>
                    <label className="text-xs text-gray-500 mb-1 block">Target Sequence</label>
                    <input
                      type="text"
                      value={seq2}
                      onChange={(e) => setSeq2(e.target.value.toUpperCase())}
                      className="w-full font-mono text-sm px-3 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-200 focus:border-blue-400"
                      placeholder="ACGT..."
                    />
                  </div>
                  
                  <div className="flex items-center gap-2">
                    <label className="flex items-center gap-2 text-sm text-gray-600">
                      <input
                        type="checkbox"
                        checked={showCigar}
                        onChange={(e) => setShowCigar(e.target.checked)}
                        className="rounded"
                      />
                      Show CIGAR
                    </label>
                  </div>
                </div>
                
                {/* Result */}
                {editResult && (
                  <div className="mt-4 pt-4 border-t border-gray-100">
                    <div className="grid grid-cols-3 gap-3">
                      <div className="bg-blue-50 rounded-xl p-3 text-center">
                        <div className="text-2xl font-bold text-blue-700">{editResult.edit_distance}</div>
                        <div className="text-xs text-blue-600">Edit Distance</div>
                      </div>
                      <div className="bg-emerald-50 rounded-xl p-3 text-center">
                        <div className="text-2xl font-bold text-emerald-700">{(editResult.normalized * 100).toFixed(1)}%</div>
                        <div className="text-xs text-emerald-600">Normalized</div>
                      </div>
                      <div className="bg-violet-50 rounded-xl p-3 text-center">
                        <div className="text-2xl font-bold text-violet-700">{((1 - editResult.normalized) * 100).toFixed(1)}%</div>
                        <div className="text-xs text-violet-600">Identity</div>
                      </div>
                    </div>
                    
                    {showCigar && editResult.cigar && (
                      <div className="mt-3 bg-gray-50 rounded-lg p-2">
                        <div className="text-xs text-gray-500 mb-1">CIGAR String</div>
                        <div className="font-mono text-sm text-gray-800">{editResult.cigar}</div>
                      </div>
                    )}
                  </div>
                )}
              </div>
              
              {/* Examples */}
              <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
                <div className="flex items-center gap-2 mb-3">
                  <Zap className="w-4 h-4 text-amber-500" />
                  <span className="font-semibold text-gray-900 text-sm">Examples</span>
                </div>
                <div className="space-y-2">
                  {editDistanceExamples.map((ex, i) => (
                    <button
                      key={i}
                      onClick={() => { setSeq1(ex.query); setSeq2(ex.target); }}
                      className="w-full text-left p-2 rounded-lg bg-gray-50 hover:bg-gray-100 transition-colors"
                    >
                      <div className="font-medium text-gray-900 text-sm">{ex.name}</div>
                      <div className="text-xs text-gray-500">{ex.description}</div>
                    </button>
                  ))}
                </div>
              </div>
              
              {/* CLI Preview */}
              <div className="bg-gray-900 rounded-xl p-3 font-mono text-xs">
                <div className="flex items-center gap-2 text-gray-400 mb-2">
                  <Terminal className="w-4 h-4" />
                  <span>CLI Command</span>
                </div>
                <div className="text-emerald-400 break-all">
                  ont_align.py editdist "{seq1}" "{seq2}" --mode {editMode} {showCigar ? '--cigar' : ''} --normalize
                </div>
              </div>
            </div>
            
            {/* Right: Visualization */}
            <div className="col-span-7 space-y-4">
              {/* Alignment Visualization */}
              <EditDistanceVisualizer seq1={seq1} seq2={seq2} result={editResult} />
              
              {/* Algorithm explanation */}
              <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
                <div className="flex items-center gap-2 mb-3">
                  <Grid className="w-4 h-4 text-blue-600" />
                  <span className="font-semibold text-gray-900 text-sm">Edit Distance Modes (edlib)</span>
                </div>
                <div className="grid grid-cols-3 gap-3">
                  <div className={`p-3 rounded-xl border-2 ${editMode === 'NW' ? 'border-blue-500 bg-blue-50' : 'border-gray-100'}`}>
                    <div className="font-semibold text-gray-900 text-sm">NW (Global)</div>
                    <div className="text-xs text-gray-500 mt-1">Needleman-Wunsch. Align entire query to entire target.</div>
                  </div>
                  <div className={`p-3 rounded-xl border-2 ${editMode === 'HW' ? 'border-blue-500 bg-blue-50' : 'border-gray-100'}`}>
                    <div className="font-semibold text-gray-900 text-sm">HW (Semi-global)</div>
                    <div className="text-xs text-gray-500 mt-1">Query aligned fully, target can have free end gaps.</div>
                  </div>
                  <div className={`p-3 rounded-xl border-2 ${editMode === 'SHW' ? 'border-blue-500 bg-blue-50' : 'border-gray-100'}`}>
                    <div className="font-semibold text-gray-900 text-sm">SHW (Infix)</div>
                    <div className="text-xs text-gray-500 mt-1">Find query as substring of target with errors.</div>
                  </div>
                </div>
              </div>
              
              {/* Use cases */}
              <div className="bg-gradient-to-br from-blue-50 to-cyan-50 rounded-xl p-4">
                <div className="font-semibold text-gray-900 text-sm mb-3">Use Cases for Edit Distance</div>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  {[
                    { title: 'Error Rate Estimation', desc: 'Compare basecalled to known reference' },
                    { title: 'Barcode Demultiplexing', desc: 'Match reads to barcodes with tolerance' },
                    { title: 'Variant Verification', desc: 'Check distance between alleles' },
                    { title: 'Haplotype Comparison', desc: 'Compare phased sequences' },
                    { title: 'Star Allele Matching', desc: 'CYP2D6 allele discrimination' },
                    { title: 'Sequence Clustering', desc: 'Build distance matrices' },
                  ].map((item, i) => (
                    <div key={i} className="bg-white/60 backdrop-blur rounded-lg p-2">
                      <div className="font-medium text-gray-900">{item.title}</div>
                      <div className="text-xs text-gray-500">{item.desc}</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}
        
        {activeTab === 'align' && (
          <div className="grid grid-cols-2 gap-4">
            {/* Alignment Stats */}
            <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
              <div className="flex items-center gap-2 mb-4">
                <BarChart3 className="w-4 h-4 text-blue-600" />
                <span className="font-semibold text-gray-900">Alignment Statistics</span>
              </div>
              
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-blue-50 rounded-xl p-3">
                  <div className="text-2xl font-bold text-blue-700">{(mockAlignmentStats.total_reads / 1e6).toFixed(1)}M</div>
                  <div className="text-xs text-blue-600">Total Reads</div>
                </div>
                <div className="bg-emerald-50 rounded-xl p-3">
                  <div className="text-2xl font-bold text-emerald-700">{mockAlignmentStats.mapped_pct}%</div>
                  <div className="text-xs text-emerald-600">Mapped</div>
                </div>
                <div className="bg-violet-50 rounded-xl p-3">
                  <div className="text-2xl font-bold text-violet-700">{mockAlignmentStats.mean_mapq}</div>
                  <div className="text-xs text-violet-600">Mean MAPQ</div>
                </div>
                <div className="bg-amber-50 rounded-xl p-3">
                  <div className="text-2xl font-bold text-amber-700">{(mockAlignmentStats.n50_read_length / 1000).toFixed(1)}kb</div>
                  <div className="text-xs text-amber-600">N50</div>
                </div>
              </div>
              
              <div className="mt-4 pt-4 border-t border-gray-100 space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-500">Mean Coverage</span>
                  <span className="font-medium">{mockAlignmentStats.mean_coverage}×</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">≥10× Coverage</span>
                  <span className="font-medium">{mockAlignmentStats.pct_genome_covered_10x}%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">≥30× Coverage</span>
                  <span className="font-medium">{mockAlignmentStats.pct_genome_covered_30x}%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Secondary Alignments</span>
                  <span className="font-medium">{(mockAlignmentStats.secondary_alignments / 1000).toFixed(0)}k</span>
                </div>
              </div>
            </div>
            
            {/* Alignment Presets */}
            <div className="space-y-4">
              <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
                <div className="flex items-center gap-2 mb-3">
                  <Settings className="w-4 h-4 text-gray-600" />
                  <span className="font-semibold text-gray-900">Minimap2 Presets</span>
                </div>
                <div className="space-y-2">
                  {[
                    { preset: 'map-ont', desc: 'Standard ONT reads', highlight: true },
                    { preset: 'lr:hq', desc: 'High-quality reads (Q20+, SUP)', highlight: false },
                    { preset: 'splice', desc: 'Spliced alignment (direct RNA)', highlight: false },
                    { preset: 'asm5', desc: 'Assembly-to-reference (<5% div)', highlight: false },
                  ].map((p, i) => (
                    <div key={i} className={`flex items-center justify-between p-2 rounded-lg ${p.highlight ? 'bg-blue-50' : 'bg-gray-50'}`}>
                      <div>
                        <span className={`font-mono text-sm ${p.highlight ? 'text-blue-700' : 'text-gray-700'}`}>{p.preset}</span>
                        <span className="text-xs text-gray-500 ml-2">{p.desc}</span>
                      </div>
                      {p.highlight && <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded">default</span>}
                    </div>
                  ))}
                </div>
              </div>
              
              {/* CLI */}
              <div className="bg-gray-900 rounded-xl p-3 font-mono text-xs">
                <div className="flex items-center gap-2 text-gray-400 mb-2">
                  <Terminal className="w-4 h-4" />
                  <span>CLI Commands</span>
                </div>
                <div className="space-y-1 text-emerald-400">
                  <div><span className="text-violet-400">#</span> ont_align.py align reads.bam -r GRCh38 -o aligned.bam</div>
                  <div><span className="text-violet-400">#</span> ont_align.py align reads.bam -r GRCh38 -x lr:hq --threads 16</div>
                  <div><span className="text-violet-400">#</span> ont_align.py qc aligned.bam --json stats.json --plot cov.png</div>
                </div>
              </div>
            </div>
          </div>
        )}
        
        {activeTab === 'refs' && (
          <div className="grid grid-cols-3 gap-4">
            {mockReferences.map((ref, i) => (
              <ReferenceCard key={i} ref={ref} />
            ))}
            
            {/* Add reference card */}
            <div className="bg-gray-50 rounded-xl border-2 border-dashed border-gray-200 p-4 flex flex-col items-center justify-center text-gray-400 hover:border-blue-300 hover:text-blue-500 cursor-pointer transition-colors">
              <Database className="w-8 h-8 mb-2" />
              <span className="text-sm font-medium">Add Reference</span>
            </div>
            
            {/* CLI card */}
            <div className="col-span-3 bg-gray-900 rounded-xl p-4 font-mono text-xs">
              <div className="flex items-center gap-2 text-gray-400 mb-3">
                <Terminal className="w-4 h-4" />
                <span>Reference Management</span>
              </div>
              <div className="grid grid-cols-2 gap-4 text-emerald-400">
                <div className="space-y-1">
                  <div><span className="text-violet-400">#</span> ont_align.py refs init</div>
                  <div><span className="text-violet-400">#</span> ont_align.py refs add GRCh38 /path/to/GRCh38.fa</div>
                  <div><span className="text-violet-400">#</span> ont_align.py refs list</div>
                </div>
                <div className="space-y-1">
                  <div><span className="text-violet-400">#</span> ont_align.py refs info GRCh38</div>
                  <div><span className="text-violet-400">#</span> ont_align.py refs index GRCh38 --aligner minimap2</div>
                  <div><span className="text-violet-400">#</span> ont_align.py refs import t2t</div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
