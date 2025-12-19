"""
Tests for ONT Ecosystem core library.
"""

import os
import sys
import json
import tempfile
import pytest
from pathlib import Path
from datetime import datetime, timezone

# Add lib to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'lib'))

from ont_core import (
    Registry, Experiment, Event,
    generate_experiment_id, compute_file_checksum,
    format_bytes, format_duration,
    export_experiment_json, export_experiment_commands,
)


class TestEvent:
    """Tests for Event dataclass."""
    
    def test_create_event(self):
        event = Event(
            timestamp=datetime.now(timezone.utc).isoformat(),
            type="analysis",
            analysis="end_reasons",
            command="end_reason.py /data --json results.json",
            exit_code=0,
        )
        assert event.type == "analysis"
        assert event.analysis == "end_reasons"
        assert event.exit_code == 0
    
    def test_event_to_dict(self):
        event = Event(
            timestamp="2024-01-15T12:00:00Z",
            type="discovered",
            agent="manual",
        )
        d = event.to_dict()
        assert d['type'] == "discovered"
        assert 'analysis' not in d  # Empty fields excluded
    
    def test_event_from_dict(self):
        data = {
            'timestamp': "2024-01-15T12:00:00Z",
            'type': "analysis",
            'analysis': "basecalling",
            'results': {'total_reads': 1000},
            'exit_code': 0,
        }
        event = Event.from_dict(data)
        assert event.analysis == "basecalling"
        assert event.results['total_reads'] == 1000


class TestExperiment:
    """Tests for Experiment dataclass."""
    
    def test_create_experiment(self):
        exp = Experiment(
            id="exp-abc123",
            name="Test Run",
            location="/data/test",
            status="discovered",
        )
        assert exp.id == "exp-abc123"
        assert exp.status == "discovered"
        assert exp.events == []
    
    def test_add_event(self):
        exp = Experiment(
            id="exp-abc123",
            name="Test Run",
            location="/data/test",
        )
        event = Event(
            timestamp=datetime.now(timezone.utc).isoformat(),
            type="discovered",
        )
        exp.add_event(event)
        assert len(exp.events) == 1
        assert exp.last_accessed is not None
    
    def test_get_latest_analysis(self):
        exp = Experiment(
            id="exp-abc123",
            name="Test Run",
            location="/data/test",
        )
        # Add events
        exp.events.append(Event(
            timestamp="2024-01-15T10:00:00Z",
            type="analysis",
            analysis="end_reasons",
            exit_code=0,
            results={'quality_status': 'OK'},
        ))
        exp.events.append(Event(
            timestamp="2024-01-15T11:00:00Z",
            type="analysis",
            analysis="basecalling",
            exit_code=1,  # Failed
        ))
        exp.events.append(Event(
            timestamp="2024-01-15T12:00:00Z",
            type="analysis",
            analysis="basecalling",
            exit_code=0,  # Succeeded
            results={'total_reads': 1000},
        ))
        
        latest = exp.get_latest_analysis("basecalling")
        assert latest is not None
        assert latest.results['total_reads'] == 1000
        
        latest_qc = exp.get_latest_analysis("end_reasons")
        assert latest_qc.results['quality_status'] == 'OK'
    
    def test_to_dict_from_dict(self):
        exp = Experiment(
            id="exp-abc123",
            name="Test Run",
            location="/data/test",
            tags=["test", "example"],
            total_reads=1000000,
        )
        exp.add_event(Event(
            timestamp="2024-01-15T10:00:00Z",
            type="discovered",
        ))
        
        d = exp.to_dict()
        assert d['id'] == "exp-abc123"
        assert len(d['events']) == 1
        
        # Reconstruct
        exp2 = Experiment.from_dict(d)
        assert exp2.id == exp.id
        assert exp2.total_reads == exp.total_reads


class TestRegistry:
    """Tests for Registry."""
    
    @pytest.fixture
    def temp_registry(self):
        """Create a temporary registry directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_dir = Path(tmpdir) / '.ont-registry'
            registry_dir.mkdir()
            yield Registry(registry_dir)
    
    def test_add_and_get(self, temp_registry):
        exp = Experiment(
            id="exp-test123",
            name="Test Experiment",
            location="/data/test",
        )
        temp_registry.add(exp)
        
        retrieved = temp_registry.get("exp-test123")
        assert retrieved is not None
        assert retrieved.name == "Test Experiment"
    
    def test_list_with_filters(self, temp_registry):
        # Add experiments
        exp1 = Experiment(id="exp-1", name="E1", location="/d1", 
                         status="complete", tags=["cyp2d6"])
        exp2 = Experiment(id="exp-2", name="E2", location="/d2",
                         status="analyzing", tags=["wgs"])
        exp3 = Experiment(id="exp-3", name="E3", location="/d3",
                         status="complete", tags=["cyp2d6", "clinical"])
        
        temp_registry.add(exp1)
        temp_registry.add(exp2)
        temp_registry.add(exp3)
        
        # Filter by status
        complete = temp_registry.list(status="complete")
        assert len(complete) == 2
        
        # Filter by tags
        cyp2d6 = temp_registry.list(tags=["cyp2d6"])
        assert len(cyp2d6) == 2
        
        # Limit
        limited = temp_registry.list(limit=1)
        assert len(limited) == 1
    
    def test_search(self, temp_registry):
        exp = Experiment(
            id="exp-abc123",
            name="CYP2D6 Patient Cohort",
            location="/data/cyp2d6",
            tags=["cyp2d6", "clinical"],
            notes="First batch of patients",
        )
        temp_registry.add(exp)
        
        # Search by name
        results = temp_registry.search("CYP2D6")
        assert len(results) == 1
        
        # Search by tag
        results = temp_registry.search("clinical")
        assert len(results) == 1
        
        # Search by notes
        results = temp_registry.search("batch")
        assert len(results) == 1
    
    def test_remove(self, temp_registry):
        exp = Experiment(id="exp-del", name="Delete Me", location="/d")
        temp_registry.add(exp)
        
        assert temp_registry.get("exp-del") is not None
        
        temp_registry.remove("exp-del")
        assert temp_registry.get("exp-del") is None
    
    def test_get_stats(self, temp_registry):
        exp1 = Experiment(id="exp-1", name="E1", location="/d1",
                         platform="PromethION", total_reads=1000000)
        exp2 = Experiment(id="exp-2", name="E2", location="/d2",
                         platform="MinION", total_reads=500000)
        
        temp_registry.add(exp1)
        temp_registry.add(exp2)
        
        stats = temp_registry.get_stats()
        assert stats['total_experiments'] == 2
        assert stats['total_reads'] == 1500000
        assert stats['by_platform']['PromethION'] == 1
        assert stats['by_platform']['MinION'] == 1


class TestUtilities:
    """Tests for utility functions."""
    
    def test_generate_experiment_id(self):
        id1 = generate_experiment_id("/data/run1")
        id2 = generate_experiment_id("/data/run2")
        id3 = generate_experiment_id("/data/run1")
        
        assert id1.startswith("exp-")
        assert id1 != id2
        assert id1 == id3  # Same input = same ID
    
    def test_compute_file_checksum(self):
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test content")
            path = Path(f.name)
        
        try:
            checksum = compute_file_checksum(path)
            assert checksum.startswith("sha256:")
            assert len(checksum) > 10
        finally:
            path.unlink()
    
    def test_format_bytes(self):
        assert "0.0 B" in format_bytes(0) or "0" in format_bytes(0)
        assert "KB" in format_bytes(1024)
        assert "MB" in format_bytes(1024 * 1024)
        assert "GB" in format_bytes(1024 * 1024 * 1024)
    
    def test_format_duration(self):
        assert "s" in format_duration(30)
        assert "m" in format_duration(120)
        assert "h" in format_duration(3700)


class TestExport:
    """Tests for export functions."""
    
    def test_export_json(self):
        exp = Experiment(
            id="exp-json",
            name="JSON Export Test",
            location="/data",
            total_reads=1000,
        )
        
        json_str = export_experiment_json(exp)
        data = json.loads(json_str)
        
        assert data['id'] == "exp-json"
        assert data['total_reads'] == 1000
    
    def test_export_commands(self):
        exp = Experiment(
            id="exp-cmd",
            name="Command Export Test",
            location="/data",
        )
        exp.events.append(Event(
            timestamp="2024-01-15T10:00:00Z",
            type="analysis",
            analysis="end_reasons",
            command="end_reason.py /data --json results.json",
        ))
        exp.events.append(Event(
            timestamp="2024-01-15T11:00:00Z",
            type="analysis",
            analysis="basecalling",
            command="dorado basecaller sup /data --output calls.bam",
        ))
        
        script = export_experiment_commands(exp)
        
        assert "#!/bin/bash" in script
        assert "end_reason.py" in script
        assert "dorado basecaller" in script


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
