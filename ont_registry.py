#!/usr/bin/env python3
"""
ONT Experiment Registry - Permanent Database with Deduplication

Key Identifiers for Deduplication:
1. run_id (8-char hex) - PRIMARY KEY, unique per MinKNOW run
2. flowcell - For merge candidate detection
3. device - Sequencer identity
4. date + time - Chronological ordering
5. fingerprint - Hash of key fields for duplicate detection

Merge Logic:
- Same flowcell + sequential runs = merge candidates
- Select by: most reads > most recent > first canonical
"""

import json
import hashlib
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

class ExperimentRegistry:
    """Permanent experiment database with deduplication"""
    
    VERSION = "2.1"
    
    # Key fields that uniquely identify an experiment
    IDENTITY_FIELDS = ["run_id", "flowcell", "device", "date", "time"]
    
    # Fields for choosing best version
    RANKING_FIELDS = ["total_reads", "total_bases", "has_pod5", "has_summary", "is_canonical"]
    
    def __init__(self, registry_path: str = None):
        """
        Initialize registry
        
        Args:
            registry_path: Path to registry JSON file
                          Default: ~/.ont-registry/experiments.json (local)
                          Or: Y:/sequencing_data/.ont-registry/experiments.json (Great Lakes)
        """
        if registry_path is None:
            # Check for Great Lakes path first
            gl_path = Path("Y:/sequencing_data/.ont-registry/experiments.json")
            local_path = Path.home() / ".ont-registry" / "experiments.json"
            registry_path = gl_path if gl_path.parent.exists() else local_path
        
        self.registry_path = Path(registry_path)
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Main storage
        self.experiments: Dict[str, dict] = {}  # run_id -> record
        
        # Indexes for fast lookup
        self.index_flowcell: Dict[str, List[str]] = {}  # flowcell -> [run_ids]
        self.index_device: Dict[str, List[str]] = {}    # device -> [run_ids]
        self.index_experiment: Dict[str, List[str]] = {} # experiment_name -> [run_ids]
        self.index_fingerprint: Dict[str, str] = {}     # fingerprint -> run_id
        
        self._load()
    
    def _load(self):
        """Load registry from disk"""
        if self.registry_path.exists():
            with open(self.registry_path, 'r') as f:
                data = json.load(f)
            
            self.experiments = data.get("experiments", {})
            
            # Rebuild indexes
            for run_id, record in self.experiments.items():
                self._index_record(run_id, record)
    
    def _save(self):
        """Persist registry to disk"""
        data = {
            "version": self.VERSION,
            "updated": datetime.utcnow().isoformat() + "Z",
            "stats": self.stats(),
            "indexes": {
                "by_flowcell": self.index_flowcell,
                "by_device": self.index_device,
                "by_experiment": self.index_experiment,
            },
            "experiments": self.experiments
        }
        
        with open(self.registry_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)
    
    def _fingerprint(self, record: dict) -> str:
        """Generate unique fingerprint for deduplication"""
        key_parts = [str(record.get(f, "")) for f in self.IDENTITY_FIELDS]
        key = "|".join(key_parts)
        return hashlib.sha256(key.encode()).hexdigest()[:16]
    
    def _index_record(self, run_id: str, record: dict):
        """Add record to all indexes"""
        # Flowcell index
        fc = record.get("flowcell")
        if fc:
            self.index_flowcell.setdefault(fc, [])
            if run_id not in self.index_flowcell[fc]:
                self.index_flowcell[fc].append(run_id)
        
        # Device index
        dev = record.get("device")
        if dev:
            self.index_device.setdefault(dev, [])
            if run_id not in self.index_device[dev]:
                self.index_device[dev].append(run_id)
        
        # Experiment name index
        exp = record.get("experiment") or record.get("harmonized_name")
        if exp:
            self.index_experiment.setdefault(exp, [])
            if run_id not in self.index_experiment[exp]:
                self.index_experiment[exp].append(run_id)
        
        # Fingerprint index
        fp = self._fingerprint(record)
        self.index_fingerprint[fp] = run_id
    
    def exists(self, run_id: str) -> bool:
        """Check if run_id already exists (deduplication check)"""
        return run_id in self.experiments
    
    def exists_by_fingerprint(self, record: dict) -> Optional[str]:
        """Check if equivalent record exists by fingerprint"""
        fp = self._fingerprint(record)
        return self.index_fingerprint.get(fp)
    
    def add(self, record: dict, force: bool = False) -> Tuple[bool, str]:
        """
        Add experiment to registry with deduplication
        
        Returns:
            (added: bool, message: str)
        """
        run_id = record.get("run_id")
        if not run_id:
            return False, "Missing run_id"
        
        # Check for exact duplicate by run_id
        if self.exists(run_id) and not force:
            existing = self.experiments[run_id]
            # Update paths if new path found
            new_path = record.get("canonical_path") or record.get("current_path")
            if new_path:
                existing.setdefault("all_paths", [])
                if new_path not in existing["all_paths"]:
                    existing["all_paths"].append(new_path)
                    existing["updated"] = datetime.utcnow().isoformat() + "Z"
                    self._save()
                    return False, f"Updated paths for existing run_id {run_id}"
            return False, f"Duplicate run_id {run_id}"
        
        # Check for equivalent by fingerprint
        existing_id = self.exists_by_fingerprint(record)
        if existing_id and existing_id != run_id and not force:
            existing = self.experiments[existing_id]
            new_path = record.get("canonical_path") or record.get("current_path")
            if new_path:
                existing.setdefault("all_paths", [])
                if new_path not in existing["all_paths"]:
                    existing["all_paths"].append(new_path)
            return False, f"Equivalent to existing {existing_id} (same fingerprint)"
        
        # Add metadata
        record["registered"] = datetime.utcnow().isoformat() + "Z"
        record["updated"] = record["registered"]
        record.setdefault("all_paths", [])
        for path_field in ["canonical_path", "current_path"]:
            if record.get(path_field) and record[path_field] not in record["all_paths"]:
                record["all_paths"].append(record[path_field])
        
        # Store
        self.experiments[run_id] = record
        self._index_record(run_id, record)
        self._save()
        
        return True, f"Added {run_id}"
    
    def get(self, run_id: str) -> Optional[dict]:
        """Get experiment by run_id"""
        return self.experiments.get(run_id)
    
    def get_merge_candidates(self, flowcell: str) -> List[dict]:
        """Get all runs on same flowcell (potential merge candidates)"""
        run_ids = self.index_flowcell.get(flowcell, [])
        records = [self.experiments[rid] for rid in run_ids if rid in self.experiments]
        return sorted(records, key=lambda r: f"{r.get('date', '')}_{r.get('time', '')}")
    
    def get_best_version(self, flowcell: str) -> Optional[dict]:
        """
        Get the best/longest version for a flowcell
        
        Selection priority:
        1. Already merged runs (num_merged > 1)
        2. Most total_reads
        3. Has POD5 data
        4. Is canonical
        5. Most recent
        """
        candidates = self.get_merge_candidates(flowcell)
        if not candidates:
            return None
        
        # Check for merged
        merged = [r for r in candidates if (r.get("num_merged") or 1) > 1]
        if merged:
            return max(merged, key=lambda r: r.get("num_merged", 1))
        
        # Score each candidate
        def score(r):
            return (
                r.get("total_reads") or 0,
                1 if r.get("has_pod5") else 0,
                1 if r.get("is_canonical") else 0,
                r.get("date", "") + "_" + r.get("time", "")
            )
        
        return max(candidates, key=score)
    
    def search(self, **kwargs) -> List[dict]:
        """Search experiments by any field"""
        results = list(self.experiments.values())
        for key, value in kwargs.items():
            if value is not None:
                results = [r for r in results if r.get(key) == value]
        return results
    
    def find_by_device(self, device: str) -> List[dict]:
        """Get all experiments from a specific device"""
        run_ids = self.index_device.get(device, [])
        return [self.experiments[rid] for rid in run_ids if rid in self.experiments]
    
    def find_by_experiment(self, name: str) -> List[dict]:
        """Get all runs for an experiment name"""
        run_ids = self.index_experiment.get(name, [])
        return [self.experiments[rid] for rid in run_ids if rid in self.experiments]
    
    def stats(self) -> dict:
        """Get registry statistics"""
        records = list(self.experiments.values())
        return {
            "total_experiments": len(records),
            "unique_run_ids": len(self.experiments),
            "unique_flowcells": len(self.index_flowcell),
            "unique_devices": len(self.index_device),
            "unique_experiment_names": len(self.index_experiment),
            "canonical_count": sum(1 for r in records if r.get("is_canonical")),
            "with_qc_data": sum(1 for r in records if r.get("pct_signal_positive")),
            "with_pod5": sum(1 for r in records if r.get("has_pod5")),
            "merge_candidates": sum(1 for ids in self.index_flowcell.values() if len(ids) > 1),
            "total_reads": sum(r.get("total_reads") or 0 for r in records),
        }
    
    def list_devices(self) -> List[str]:
        """List all unique device IDs"""
        return sorted(self.index_device.keys())
    
    def list_flowcells(self) -> List[str]:
        """List all unique flowcell IDs"""
        return sorted(self.index_flowcell.keys())


# CLI interface
if __name__ == "__main__":
    import sys
    
    registry = ExperimentRegistry()
    
    if len(sys.argv) < 2:
        print("Usage: ont_registry.py <command> [args]")
        print("Commands: stats, list, search, get, devices, flowcells, best")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "stats":
        for k, v in registry.stats().items():
            print(f"{k}: {v}")
    
    elif cmd == "list":
        for run_id, rec in list(registry.experiments.items())[:20]:
            print(f"{run_id}: {rec.get('experiment', 'N/A')} | {rec.get('flowcell')} | {rec.get('device')}")
    
    elif cmd == "devices":
        for dev in registry.list_devices():
            count = len(registry.index_device[dev])
            print(f"{dev}: {count} runs")
    
    elif cmd == "flowcells":
        for fc in registry.list_flowcells():
            count = len(registry.index_flowcell[fc])
            if count > 1:
                print(f"{fc}: {count} runs (MERGE CANDIDATE)")
            else:
                print(f"{fc}: {count} run")
    
    elif cmd == "best" and len(sys.argv) > 2:
        fc = sys.argv[2]
        best = registry.get_best_version(fc)
        if best:
            print(json.dumps(best, indent=2, default=str))
        else:
            print(f"No experiments found for flowcell {fc}")
    
    elif cmd == "get" and len(sys.argv) > 2:
        run_id = sys.argv[2]
        rec = registry.get(run_id)
        if rec:
            print(json.dumps(rec, indent=2, default=str))
        else:
            print(f"Not found: {run_id}")
