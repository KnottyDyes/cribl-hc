"""
Utility module for grouping findings by worker group and grouping ID.
Mimics the GUI's grouping logic from ResultsPage.tsx.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass

from cribl_hc.models.finding import Finding


@dataclass
class GroupedFinding:
    """Represents a group of similar findings."""
    findings: List[Finding]
    group_title: str
    worker_group: str
    is_grouped: bool
    severity: str
    finding_count: int


def group_findings(findings: List[Finding]) -> List[GroupedFinding]:
    """
    Group findings by worker group, then by grouping ID.
    
    Mimics the GUI's grouping logic:
    1. Group by worker_group (or '__global__' if None)
    2. Within each worker group, group by grouping_id (or finding id)
    3. Sort by worker group, then severity, then title
    
    Args:
        findings: List of findings from analysis
        
    Returns:
        List of GroupedFinding objects sorted by worker group and severity
    """
    # Build worker group map
    worker_group_map: Dict[str, Dict[str, List[Finding]]] = {}
    
    for finding in findings:
        # Global findings (no worker_group) are separate from default
        worker_group = finding.worker_group or '__global__'
        
        if worker_group not in worker_group_map:
            worker_group_map[worker_group] = {}
        
        # Group by grouping_id or finding id
        group_key = finding.grouping_id or finding.id
        if group_key not in worker_group_map[worker_group]:
            worker_group_map[worker_group][group_key] = []
        
        worker_group_map[worker_group][group_key].append(finding)
    
    # Build result list
    result: List[GroupedFinding] = []
    
    for worker_group in sorted(worker_group_map.keys()):
        for group_key in sorted(worker_group_map[worker_group].keys()):
            group_findings = worker_group_map[worker_group][group_key]
            first = group_findings[0]
            
            # Check if this is a grouped finding (has grouping_id and multiple findings)
            is_grouped = bool(first.grouping_id) and len(group_findings) > 1
            
            # Extract group title (remove " - " prefix if grouped)
            if is_grouped:
                group_title = first.title.split(':')[0] if ':' in first.title else first.title
            else:
                group_title = first.title
            
            result.append(GroupedFinding(
                findings=group_findings,
                group_title=group_title,
                worker_group=worker_group,
                is_grouped=is_grouped,
                severity=first.severity,
                finding_count=len(group_findings)
            ))
    
    # Sort by worker group, then severity, then title
    severity_order = {'critical': 5, 'high': 4, 'medium': 3, 'low': 2, 'info': 1}
    result.sort(
        key=lambda x: (
            x.worker_group,
            -severity_order.get(x.severity, 0),
            x.group_title
        )
    )
    
    return result


def get_severity_counts(findings: List[Finding]) -> Dict[str, int]:
    """
    Get count of findings by severity.
    
    Args:
        findings: List of findings
        
    Returns:
        Dictionary with severity counts
    """
    counts = {
        'critical': 0,
        'high': 0,
        'medium': 0,
        'low': 0,
        'info': 0,
    }
    
    for finding in findings:
        if finding.severity in counts:
            counts[finding.severity] += 1
    
    return counts


def get_worker_group_display_name(worker_group: str) -> str:
    """
    Get a human-readable display name for a worker group.
    
    Args:
        worker_group: The worker group identifier
        
    Returns:
        Formatted display name
    """
    if worker_group == '__global__':
        return 'Global Findings'
    elif worker_group == 'default':
        return 'Default Worker Group'
    else:
        return f'Worker Group: {worker_group}'
