"""
City Analyzer - Risk-based citywide health scoring with Gemini-powered insights.

This module computes a baseline health score using risk-points scoring with a
high healthy prior. Gemini provides qualitative analysis and bounded adjustments.

Scoring Philosophy:
- A city with 5 minor issues should score ~97-99 (nearly perfect)
- Only truly critical problems should significantly impact the score
- The score reflects citywide risk, not raw issue count
"""

import os
import re
import json
import math
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Literal, Tuple
from dataclasses import dataclass, field, asdict
import requests
from supabase import create_client, Client


# =============================================================================
# Configuration - Environment Variables REQUIRED
# =============================================================================

def get_env_required(key: str) -> str:
    """Get required environment variable or raise clear error."""
    value = os.environ.get(key)
    if not value:
        raise EnvironmentError(
            f"\n{'='*60}\n"
            f"MISSING REQUIRED ENVIRONMENT VARIABLE: {key}\n"
            f"{'='*60}\n"
            f"Please set this variable in your environment or .env file.\n"
            f"Example: export {key}='your-value-here'\n"
        )
    return value


def get_config() -> Tuple[str, str, str, str]:
    """Load and validate all required configuration."""
    return (
        get_env_required("SUPABASE_URL"),
        get_env_required("SUPABASE_KEY"),
        get_env_required("GEMINI_API_KEY"),
        os.environ.get(
            "GEMINI_URL",
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
        ),
    )


# =============================================================================
# Scoring Constants
# =============================================================================

# Issue criticality levels
CRITICALITY_CRITICAL = 3  # Life safety / major disruption
CRITICALITY_MAJOR = 2     # Significant infrastructure issue
CRITICALITY_MINOR = 1     # Cosmetic / low impact

# Criticality multipliers (how much each level amplifies risk)
CRITICALITY_MULTIPLIERS = {
    CRITICALITY_CRITICAL: 6.0,
    CRITICALITY_MAJOR: 2.0,
    CRITICALITY_MINOR: 1.0,
}

# Severity points (base risk contribution)
SEVERITY_POINTS = {
    "low": 1,
    "medium": 3,
    "high": 8,
}

# Status multipliers
STATUS_MULTIPLIERS = {
    "new": 1.0,
    "open": 1.0,
    "triaged": 0.8,
    "assigned": 0.7,
    "in_progress": 0.6,
    "resolved": 0.0,  # 0.1 if include_resolved=True
    "rejected": 0.0,
}
RESOLVED_MULTIPLIER_WHEN_INCLUDED = 0.1

# Recency multipliers
RECENCY_MULTIPLIERS = [
    (7, 1.0),      # 0-7 days: full weight
    (30, 0.8),     # 8-30 days: 80%
    (90, 0.5),     # 31-90 days: 50%
    (float('inf'), 0.3),  # >90 days: 30%
]
MISSING_TIMESTAMP_MULTIPLIER = 0.6

# Risk-to-score conversion
RISK_SATURATION_R = 600.0  # Higher = more risk needed to impact score
HIGH_PRIOR_SCORE = 99      # Starting point for healthy city
SCORE_RANGE = 98           # Max penalty (99 - 1 = 98)

# Volume penalty threshold
VOLUME_PENALTY_THRESHOLD = 50

# Hard rule thresholds
MIN_SCORE_FEW_MINOR_ISSUES = 97
MAX_SCORE_CRITICAL_HIGH_OPEN = 92


# =============================================================================
# Issue Type to Criticality Mapping
# =============================================================================

# Keywords for criticality classification
CRITICAL_KEYWORDS = {
    # Traffic/safety critical
    "traffic_light", "signal_out", "signal_malfunction", "light_outage",
    "highway_obstruction", "road_blocked", "road_closure",
    "downed_power_line", "power_line", "telephone_pole", "utility_pole",
    "bridge_damage", "bridge", "sinkhole", "collapse",
    "gas_leak", "water_main", "flooding_major", "emergency",
}

MAJOR_KEYWORDS = {
    # Significant issues
    "stop_sign", "missing_sign", "damaged_sign", "sign",
    "guardrail", "barrier_damage",
    "pothole",  # Default potholes to major
    "street_light", "streetlight", "light_out", "damaged_light",
    "fallen_tree", "tree_down", "obstruction",
    "construction_hazard", "hazard",
    "flood", "flooding",
}

MINOR_KEYWORDS = {
    # Low-impact issues
    "faded_lines", "faded_markings", "lane_marking", "marking",
    "crack", "minor_crack", "surface_crack",
    "debris", "litter", "graffiti",
    "cosmetic", "aesthetic",
}


def classify_criticality(issue: Dict[str, Any]) -> int:
    """
    Classify issue criticality based on type and severity.
    
    Returns:
        CRITICALITY_CRITICAL (3), CRITICALITY_MAJOR (2), or CRITICALITY_MINOR (1)
    """
    issue_type = (issue.get("type") or "").lower().replace(" ", "_").replace("-", "_")
    severity = (issue.get("severity") or "medium").lower()
    
    # Check critical keywords first
    for keyword in CRITICAL_KEYWORDS:
        if keyword in issue_type:
            return CRITICALITY_CRITICAL
    
    # Check major keywords
    for keyword in MAJOR_KEYWORDS:
        if keyword in issue_type:
            # Potholes: only high-severity are MAJOR, otherwise MINOR
            if "pothole" in issue_type:
                if severity == "high":
                    return CRITICALITY_MAJOR
                else:
                    return CRITICALITY_MINOR  # medium & low potholes are minor
            return CRITICALITY_MAJOR
    
    # Check minor keywords
    for keyword in MINOR_KEYWORDS:
        if keyword in issue_type:
            return CRITICALITY_MINOR
    
    # Fallback: use severity to determine criticality
    if severity == "high":
        return CRITICALITY_MAJOR
    elif severity == "low":
        return CRITICALITY_MINOR
    else:
        return CRITICALITY_MINOR  # Default unknown types to minor


def get_criticality_label(criticality: int) -> str:
    """Get human-readable criticality label."""
    return {
        CRITICALITY_CRITICAL: "critical",
        CRITICALITY_MAJOR: "major",
        CRITICALITY_MINOR: "minor",
    }.get(criticality, "unknown")


# =============================================================================
# Data Structures
# =============================================================================

@dataclass
class CitySummary:
    """Complete city health summary with risk-based scoring."""
    
    # Core metrics
    overall_health: Literal["good", "fair", "poor", "critical"]
    health_score: int  # 0-100 (final score after adjustment)
    baseline_score: int  # 0-100 (deterministic baseline)
    total_issues: int
    
    # Risk breakdown
    total_risk_points: float
    critical_count: int
    major_count: int
    minor_count: int
    high_severity_open_count: int
    
    # AI-generated content
    summary: str
    key_concerns: List[str]
    recommendations: List[str]
    hotspots: List[str]
    
    # Metadata
    breakdown: Dict[str, int]
    confidence: Literal["low", "medium", "high"] = "medium"
    score_rationale: str = ""
    score_adjustment: int = 0
    adjustment_rationale: str = ""
    
    # Analysis parameters
    days_analyzed: int = 30
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class HotspotInfo:
    """Hotspot data for ranking."""
    street: str
    total_count: int
    risk_points: float
    critical_count: int
    high_severity_count: int


# =============================================================================
# Risk-Based Scoring Engine
# =============================================================================

class RiskScoringEngine:
    """Risk-based citywide health scoring engine."""
    
    def __init__(self, days: int = 30, include_resolved: bool = False):
        self.days = days
        self.include_resolved = include_resolved
        self.now = datetime.now(timezone.utc)
        self.cutoff = self.now - timedelta(days=days)
    
    def get_recency_multiplier(self, timestamp_str: Optional[str]) -> float:
        """Calculate recency multiplier for an issue."""
        if not timestamp_str:
            return MISSING_TIMESTAMP_MULTIPLIER
        
        try:
            ts = timestamp_str.replace('Z', '+00:00')
            if '.' in ts and '+' in ts:
                ts = re.sub(r'\.(\d+)\+', lambda m: f'.{m.group(1)[:6]}+', ts)
            
            issue_time = datetime.fromisoformat(ts)
            if issue_time.tzinfo is None:
                issue_time = issue_time.replace(tzinfo=timezone.utc)
            
            days_old = (self.now - issue_time).days
            
            for threshold_days, multiplier in RECENCY_MULTIPLIERS:
                if days_old <= threshold_days:
                    return multiplier
            
            return RECENCY_MULTIPLIERS[-1][1]
            
        except (ValueError, TypeError):
            return MISSING_TIMESTAMP_MULTIPLIER
    
    def get_status_multiplier(self, status: Optional[str]) -> float:
        """Get status multiplier."""
        status = (status or "new").lower()
        
        if status in ("resolved", "rejected"):
            if self.include_resolved:
                return RESOLVED_MULTIPLIER_WHEN_INCLUDED
            return 0.0
        
        return STATUS_MULTIPLIERS.get(status, 1.0)
    
    def get_severity_points(self, severity: Optional[str]) -> int:
        """Get severity points."""
        severity = (severity or "medium").lower()
        return SEVERITY_POINTS.get(severity, 3)
    
    def is_open(self, status: Optional[str]) -> bool:
        """Check if issue is considered open."""
        status = (status or "new").lower()
        return status in ("new", "open", "triaged", "assigned", "in_progress")
    
    def is_recent(self, issue: Dict[str, Any]) -> bool:
        """Check if issue is within analysis window."""
        timestamp_str = issue.get("created_at")
        if not timestamp_str:
            return True  # Include issues without timestamps
        
        try:
            ts = timestamp_str.replace('Z', '+00:00')
            if '.' in ts and '+' in ts:
                ts = re.sub(r'\.(\d+)\+', lambda m: f'.{m.group(1)[:6]}+', ts)
            
            issue_time = datetime.fromisoformat(ts)
            if issue_time.tzinfo is None:
                issue_time = issue_time.replace(tzinfo=timezone.utc)
            
            return issue_time >= self.cutoff
            
        except (ValueError, TypeError):
            return True
    
    def compute_issue_risk_points(self, issue: Dict[str, Any]) -> float:
        """
        Compute risk points for a single issue.
        
        risk_points = severity_points * criticality_multiplier * status_multiplier * recency_multiplier
        """
        severity_pts = self.get_severity_points(issue.get("severity"))
        criticality = classify_criticality(issue)
        criticality_mult = CRITICALITY_MULTIPLIERS[criticality]
        status_mult = self.get_status_multiplier(issue.get("status"))
        recency_mult = self.get_recency_multiplier(issue.get("created_at"))
        
        return severity_pts * criticality_mult * status_mult * recency_mult
    
    def compute_baseline_score(
        self, 
        issues: List[Dict[str, Any]]
    ) -> Tuple[int, str, float, int, int, int, int]:
        """
        Compute deterministic baseline health score using risk-points formula.
        
        Returns:
            (score, rationale, total_risk, critical_count, major_count, minor_count, high_severity_open_count)
        """
        if not issues:
            return (100, "No issues reported - city infrastructure is in excellent condition.", 
                    0.0, 0, 0, 0, 0)
        
        # Filter to recent issues
        recent_issues = [i for i in issues if self.is_recent(i)]
        total_recent = len(recent_issues)
        
        if total_recent == 0:
            return (99, "No recent issues in the analysis window.", 0.0, 0, 0, 0, 0)
        
        # Compute risk points and categorize
        total_risk = 0.0
        critical_count = 0
        major_count = 0
        minor_count = 0
        high_severity_open_count = 0
        critical_high_open = False
        
        for issue in recent_issues:
            risk_pts = self.compute_issue_risk_points(issue)
            total_risk += risk_pts
            
            criticality = classify_criticality(issue)
            if criticality == CRITICALITY_CRITICAL:
                critical_count += 1
            elif criticality == CRITICALITY_MAJOR:
                major_count += 1
            else:
                minor_count += 1
            
            severity = (issue.get("severity") or "medium").lower()
            is_open = self.is_open(issue.get("status"))
            
            if severity == "high" and is_open:
                high_severity_open_count += 1
                if criticality == CRITICALITY_CRITICAL:
                    critical_high_open = True
        
        # Risk-to-score conversion with high prior
        # baseline = 99 - 98 * (1 - exp(-total_risk / R))
        risk_factor = 1 - math.exp(-total_risk / RISK_SATURATION_R)
        baseline = HIGH_PRIOR_SCORE - SCORE_RANGE * risk_factor
        
        # Volume penalty only if > threshold
        if total_recent > VOLUME_PENALTY_THRESHOLD:
            volume_penalty = math.log(total_recent / VOLUME_PENALTY_THRESHOLD) * 2
            baseline -= volume_penalty
        
        # Apply hard rules
        has_critical = critical_count > 0
        has_high_severity_open = high_severity_open_count > 0
        
        # Rule 1: Few minor issues should score very high
        if total_recent <= 15 and not has_critical and not has_high_severity_open:
            baseline = max(baseline, MIN_SCORE_FEW_MINOR_ISSUES)
        
        # Rule 2: Critical + high + open must cap score
        if critical_high_open:
            baseline = min(baseline, MAX_SCORE_CRITICAL_HIGH_OPEN)
        
        # Clamp to valid range
        baseline = max(0, min(100, round(baseline)))
        
        # Build rationale
        rationale_parts = []
        rationale_parts.append(f"{total_recent} issues analyzed")
        rationale_parts.append(f"total risk: {total_risk:.1f} pts")
        
        if critical_count > 0:
            rationale_parts.append(f"{critical_count} critical")
        if major_count > 0:
            rationale_parts.append(f"{major_count} major")
        if minor_count > 0:
            rationale_parts.append(f"{minor_count} minor")
        if high_severity_open_count > 0:
            rationale_parts.append(f"{high_severity_open_count} high-severity open")
        
        return (baseline, "; ".join(rationale_parts), total_risk,
                critical_count, major_count, minor_count, high_severity_open_count)
    
    def get_health_bucket(self, score: int) -> Literal["good", "fair", "poor", "critical"]:
        """Convert score to health category."""
        if score >= 90:
            return "good"
        elif score >= 70:
            return "fair"
        elif score >= 50:
            return "poor"
        else:
            return "critical"
    
    def compute_confidence(self, issues: List[Dict[str, Any]]) -> Literal["low", "medium", "high"]:
        """Determine confidence based on data quality."""
        recent_issues = [i for i in issues if self.is_recent(i)]
        total = len(recent_issues)
        
        with_timestamp = sum(1 for i in recent_issues if i.get("created_at"))
        timestamp_ratio = with_timestamp / total if total > 0 else 0
        
        if total >= 15 and timestamp_ratio >= 0.8:
            return "high"
        elif total >= 5 and timestamp_ratio >= 0.5:
            return "medium"
        else:
            return "low"
    
    def compute_hotspots(self, issues: List[Dict[str, Any]], top_n: int = 3) -> List[HotspotInfo]:
        """Rank hotspots by risk concentration."""
        street_data: Dict[str, HotspotInfo] = {}
        
        for issue in issues:
            street = issue.get("street_name") or "Unknown"
            
            if street not in street_data:
                street_data[street] = HotspotInfo(
                    street=street,
                    total_count=0,
                    risk_points=0.0,
                    critical_count=0,
                    high_severity_count=0,
                )
            
            info = street_data[street]
            info.total_count += 1
            info.risk_points += self.compute_issue_risk_points(issue)
            
            if classify_criticality(issue) == CRITICALITY_CRITICAL:
                info.critical_count += 1
            
            if (issue.get("severity") or "").lower() == "high":
                info.high_severity_count += 1
        
        # Rank by risk points (already accounts for criticality and severity)
        ranked = sorted(street_data.values(), key=lambda x: x.risk_points, reverse=True)
        return ranked[:top_n]


# =============================================================================
# Gemini Integration
# =============================================================================

class GeminiAnalyzer:
    """Handles Gemini API calls with tightly bounded adjustments."""
    
    def __init__(self, api_key: str, endpoint: str):
        self.api_key = api_key
        self.endpoint = endpoint
    
    def prepare_context(
        self,
        issues: List[Dict[str, Any]],
        baseline_score: int,
        overall_health: str,
        total_risk: float,
        critical_count: int,
        major_count: int,
        minor_count: int,
        high_severity_open_count: int,
        hotspots: List[HotspotInfo],
        scoring_engine: RiskScoringEngine
    ) -> Dict[str, Any]:
        """Prepare context for Gemini."""
        
        # Type breakdown
        type_counts: Dict[str, int] = {}
        for issue in issues:
            t = issue.get("type") or "unknown"
            type_counts[t] = type_counts.get(t, 0) + 1
        
        # Status breakdown
        status_counts: Dict[str, int] = {}
        open_count = 0
        for issue in issues:
            s = (issue.get("status") or "new").lower()
            status_counts[s] = status_counts.get(s, 0) + 1
            if scoring_engine.is_open(s):
                open_count += 1
        
        # Hotspot summary
        hotspot_summary = [
            {
                "street": h.street,
                "issues": h.total_count,
                "risk_points": round(h.risk_points, 1),
                "critical": h.critical_count,
                "high_severity": h.high_severity_count,
            }
            for h in hotspots if h.street != "Unknown"
        ]
        
        # Compact issue list with criticality
        compact_issues = []
        for i in issues[:30]:
            crit = classify_criticality(i)
            compact_issues.append({
                "type": i.get("type", "unknown"),
                "severity": i.get("severity", "medium"),
                "criticality": get_criticality_label(crit),
                "street": i.get("street_name", "Unknown"),
                "status": i.get("status", "new"),
            })
        
        return {
            "city": "Providence, Rhode Island",
            "baseline_score": baseline_score,
            "overall_health": overall_health,
            "total_issues": len(issues),
            "total_risk_points": round(total_risk, 1),
            "criticality_breakdown": {
                "critical": critical_count,
                "major": major_count,
                "minor": minor_count,
            },
            "high_severity_open_count": high_severity_open_count,
            "type_breakdown": type_counts,
            "status_breakdown": status_counts,
            "open_count": open_count,
            "top_hotspots": hotspot_summary,
            "issues": compact_issues,
            "analysis_window_days": scoring_engine.days,
        }
    
    def build_prompt(self, context: Dict[str, Any]) -> str:
        """Build Gemini prompt with tight adjustment bounds."""
        total_recent = context["total_issues"]
        critical_count = context["criticality_breakdown"]["critical"]
        high_open = context["high_severity_open_count"]
        has_critical_high_open = critical_count > 0 and high_open > 0
        
        # Determine adjustment bounds
        if has_critical_high_open:
            adj_min, adj_max = -5, 1
            adj_note = "Critical high-severity open issues detected. Negative adjustments up to -5 allowed if warranted."
        elif total_recent < 20:
            adj_min, adj_max = -1, 1
            adj_note = f"Small sample ({total_recent} issues). Keep adjustment to ±1 unless critical issues exist."
        else:
            adj_min, adj_max = -2, 2
            adj_note = "Standard adjustment bounds: ±2."
        
        return f"""You are an urban infrastructure analyst reviewing data for {context['city']}.

BASELINE ANALYSIS (computed deterministically):
- Health Score: {context['baseline_score']}/100 ({context['overall_health'].upper()})
- Total Risk Points: {context['total_risk_points']}
- Issues: {context['total_issues']} total, {context['open_count']} open

CRITICALITY BREAKDOWN:
- Critical (life safety): {context['criticality_breakdown']['critical']}
- Major (significant): {context['criticality_breakdown']['major']}
- Minor (low impact): {context['criticality_breakdown']['minor']}
- High-severity open: {context['high_severity_open_count']}

TOP HOTSPOTS:
{json.dumps(context['top_hotspots'], indent=2)}

ISSUE TYPES:
{json.dumps(context['type_breakdown'])}

SAMPLE ISSUES:
{json.dumps(context['issues'][:10], indent=2)}

YOUR TASK:
Provide a JSON response with EXACTLY this structure:
{{
    "summary": "<2-3 sentence overview, under 50 words>",
    "key_concerns": ["<concern 1>", "<concern 2>", "<concern 3>"],
    "recommendations": ["<recommendation 1>", "<recommendation 2>", "<recommendation 3>"],
    "hotspots": ["<street 1>", "<street 2>"],
    "score_adjustment": <integer between {adj_min} and {adj_max}>,
    "adjustment_rationale": "<brief explanation, or empty if 0>"
}}

ADJUSTMENT RULES:
- {adj_note}
- Positive = infrastructure better than score suggests
- Negative = hidden concerns warrant lower score
- Default to 0 unless there's a compelling reason

Respond with ONLY valid JSON, no markdown."""
    
    def parse_response(self, response_text: str, adj_min: int, adj_max: int) -> Dict[str, Any]:
        """Parse and validate Gemini response."""
        text = response_text.strip()
        
        # Extract JSON from markdown if present
        if text.startswith("```"):
            match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
            if match:
                text = match.group(1)
            else:
                text = re.sub(r'^```(?:json)?', '', text)
                text = re.sub(r'```$', '', text)
        
        text = text.strip()
        
        # Find JSON object
        match = re.search(r'\{[\s\S]*\}', text)
        if match:
            text = match.group(0)
        
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return self._default_response()
        
        # Validate with bounds
        adj = data.get("score_adjustment", 0)
        try:
            adj = int(adj)
            adj = max(adj_min, min(adj_max, adj))
        except (TypeError, ValueError):
            adj = 0
        
        return {
            "summary": str(data.get("summary", "Infrastructure analysis complete."))[:200],
            "key_concerns": self._validate_list(data.get("key_concerns"), 3),
            "recommendations": self._validate_list(data.get("recommendations"), 3),
            "hotspots": self._validate_list(data.get("hotspots"), 2),
            "score_adjustment": adj,
            "adjustment_rationale": str(data.get("adjustment_rationale", ""))[:200],
        }
    
    def _validate_list(self, val: Any, max_items: int) -> List[str]:
        if not isinstance(val, list):
            return []
        return [str(item)[:100] for item in val[:max_items] if item]
    
    def _default_response(self) -> Dict[str, Any]:
        return {
            "summary": "Infrastructure analysis complete.",
            "key_concerns": [],
            "recommendations": [],
            "hotspots": [],
            "score_adjustment": 0,
            "adjustment_rationale": "",
        }
    
    def analyze(
        self,
        issues: List[Dict[str, Any]],
        baseline_score: int,
        overall_health: str,
        total_risk: float,
        critical_count: int,
        major_count: int,
        minor_count: int,
        high_severity_open_count: int,
        hotspots: List[HotspotInfo],
        scoring_engine: RiskScoringEngine
    ) -> Dict[str, Any]:
        """Call Gemini API for analysis."""
        context = self.prepare_context(
            issues, baseline_score, overall_health, total_risk,
            critical_count, major_count, minor_count, high_severity_open_count,
            hotspots, scoring_engine
        )
        prompt = self.build_prompt(context)
        
        # Determine adjustment bounds
        has_critical_high_open = critical_count > 0 and high_severity_open_count > 0
        total_recent = len(issues)
        
        if has_critical_high_open:
            adj_min, adj_max = -5, 1
        elif total_recent < 20:
            adj_min, adj_max = -1, 1
        else:
            adj_min, adj_max = -2, 2
        
        try:
            response = requests.post(
                f"{self.endpoint}?key={self.api_key}",
                headers={"Content-Type": "application/json"},
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": 0.3,
                        "maxOutputTokens": 1024,
                    }
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                text = result["candidates"][0]["content"]["parts"][0]["text"]
                return self.parse_response(text, adj_min, adj_max)
            else:
                print(f"[CityAnalyzer] Gemini API error: {response.status_code}")
                return self._generate_fallback(context, hotspots)
                
        except Exception as e:
            print(f"[CityAnalyzer] Gemini call failed: {e}")
            return self._generate_fallback(context, hotspots)
    
    def _generate_fallback(
        self,
        context: Dict[str, Any],
        hotspots: List[HotspotInfo]
    ) -> Dict[str, Any]:
        """Generate fallback analysis without Gemini."""
        total = context["total_issues"]
        crit = context["criticality_breakdown"]
        high_open = context["high_severity_open_count"]
        
        # Build summary
        if total == 0:
            summary = "No infrastructure issues reported. City infrastructure is in excellent condition."
        elif crit["critical"] > 0:
            summary = f"Providence has {total} issues including {crit['critical']} critical. Immediate attention required for safety-related concerns."
        elif high_open > 0:
            summary = f"Providence has {total} infrastructure issues, {high_open} high-severity requiring prompt attention."
        else:
            summary = f"Providence has {total} minor infrastructure issues. City infrastructure is well-maintained overall."
        
        # Concerns from type breakdown
        concerns = [
            f"{t.replace('_', ' ').title()}: {c} issue{'s' if c > 1 else ''}"
            for t, c in sorted(context["type_breakdown"].items(), key=lambda x: -x[1])[:3]
        ]
        
        # Recommendations
        recommendations = []
        if crit["critical"] > 0:
            recommendations.append(f"Address {crit['critical']} critical safety issues immediately")
        if high_open > 0:
            recommendations.append(f"Prioritize {high_open} high-severity open issues")
        recommendations.append("Continue regular infrastructure monitoring")
        
        return {
            "summary": summary[:200],
            "key_concerns": concerns,
            "recommendations": recommendations[:3],
            "hotspots": [h.street for h in hotspots if h.street != "Unknown"][:2],
            "score_adjustment": 0,
            "adjustment_rationale": "",
        }


# =============================================================================
# Main Analyzer
# =============================================================================

class CityAnalyzer:
    """Risk-based city health analyzer."""
    
    def __init__(
        self,
        days: int = 30,
        include_resolved: bool = False,
        supabase_url: str = None,
        supabase_key: str = None,
        gemini_key: str = None,
        gemini_url: str = None
    ):
        # Load config - will raise if env vars missing
        default_url, default_key, default_gemini_key, default_gemini_url = get_config()
        
        self.days = days
        self.include_resolved = include_resolved
        
        self.supabase: Client = create_client(
            supabase_url or default_url,
            supabase_key or default_key
        )
        
        self.gemini = GeminiAnalyzer(
            api_key=gemini_key or default_gemini_key,
            endpoint=gemini_url or default_gemini_url
        )
        
        self.scoring = RiskScoringEngine(days=days, include_resolved=include_resolved)
    
    def fetch_issues(self) -> List[Dict[str, Any]]:
        """Fetch all issues from database."""
        result = self.supabase.table("pings").select("*").execute()
        return result.data if result.data else []
    
    def analyze_city(self) -> CitySummary:
        """Perform complete city health analysis."""
        issues = self.fetch_issues()
        
        if not issues:
            return CitySummary(
                overall_health="good",
                health_score=100,
                baseline_score=100,
                total_issues=0,
                total_risk_points=0.0,
                critical_count=0,
                major_count=0,
                minor_count=0,
                high_severity_open_count=0,
                summary="No infrastructure issues reported. City infrastructure is in excellent condition.",
                key_concerns=[],
                recommendations=["Continue regular infrastructure monitoring."],
                hotspots=[],
                breakdown={},
                confidence="low",
                score_rationale="No issues to analyze.",
                days_analyzed=self.days
            )
        
        # Compute baseline score
        (baseline_score, rationale, total_risk, 
         critical_count, major_count, minor_count, 
         high_severity_open_count) = self.scoring.compute_baseline_score(issues)
        
        overall_health = self.scoring.get_health_bucket(baseline_score)
        confidence = self.scoring.compute_confidence(issues)
        hotspots = self.scoring.compute_hotspots(issues)
        
        # Get AI analysis
        ai_result = self.gemini.analyze(
            issues, baseline_score, overall_health, total_risk,
            critical_count, major_count, minor_count, high_severity_open_count,
            hotspots, self.scoring
        )
        
        # Apply bounded adjustment
        adjustment = ai_result["score_adjustment"]
        final_score = max(0, min(100, baseline_score + adjustment))
        final_health = self.scoring.get_health_bucket(final_score)
        
        # Type breakdown
        type_counts: Dict[str, int] = {}
        for issue in issues:
            t = issue.get("type") or "unknown"
            type_counts[t] = type_counts.get(t, 0) + 1
        
        # Use AI hotspots or computed
        hotspot_names = ai_result["hotspots"] or [h.street for h in hotspots if h.street != "Unknown"]
        
        return CitySummary(
            overall_health=final_health,
            health_score=final_score,
            baseline_score=baseline_score,
            total_issues=len(issues),
            total_risk_points=total_risk,
            critical_count=critical_count,
            major_count=major_count,
            minor_count=minor_count,
            high_severity_open_count=high_severity_open_count,
            summary=ai_result["summary"],
            key_concerns=ai_result["key_concerns"],
            recommendations=ai_result["recommendations"],
            hotspots=hotspot_names[:3],
            breakdown=type_counts,
            confidence=confidence,
            score_rationale=rationale,
            score_adjustment=adjustment,
            adjustment_rationale=ai_result["adjustment_rationale"],
            days_analyzed=self.days
        )
    
    def get_summary_json(self) -> str:
        """Get summary as JSON string."""
        summary = self.analyze_city()
        return json.dumps(asdict(summary), indent=2)


# =============================================================================
# Convenience Functions
# =============================================================================

def generate_city_summary(days: int = 30, include_resolved: bool = False) -> Dict[str, Any]:
    """Generate city summary as dict."""
    analyzer = CityAnalyzer(days=days, include_resolved=include_resolved)
    return asdict(analyzer.analyze_city())


# =============================================================================
# Self-Test
# =============================================================================

def run_self_test():
    """Run self-test with synthetic data to verify scoring."""
    print("\n" + "=" * 60)
    print("SELF-TEST: Verifying risk-based scoring")
    print("=" * 60)
    
    engine = RiskScoringEngine(days=30, include_resolved=False)
    
    # Test 1: 5 minor low open issues => should be >= 97
    test1_issues = [
        {"type": "faded_lines", "severity": "low", "status": "new", "created_at": datetime.now(timezone.utc).isoformat()}
        for _ in range(5)
    ]
    score1, rationale1, risk1, *_ = engine.compute_baseline_score(test1_issues)
    test1_pass = score1 >= 97
    print(f"\nTest 1: 5 minor/low/open issues")
    print(f"  Expected: >= 97")
    print(f"  Actual:   {score1} (risk: {risk1:.1f})")
    print(f"  Result:   {'✓ PASS' if test1_pass else '✗ FAIL'}")
    
    # Test 2: 1 critical high open issue => should be <= 92
    test2_issues = [
        {"type": "traffic_light_out", "severity": "high", "status": "new", "created_at": datetime.now(timezone.utc).isoformat()}
    ]
    score2, rationale2, risk2, *_ = engine.compute_baseline_score(test2_issues)
    test2_pass = score2 <= 92
    print(f"\nTest 2: 1 critical/high/open issue")
    print(f"  Expected: <= 92")
    print(f"  Actual:   {score2} (risk: {risk2:.1f})")
    print(f"  Result:   {'✓ PASS' if test2_pass else '✗ FAIL'}")
    
    # Test 3: 30 mixed issues => should be noticeably lower
    test3_issues = []
    for i in range(30):
        if i < 3:
            test3_issues.append({"type": "pothole", "severity": "high", "status": "new", "created_at": datetime.now(timezone.utc).isoformat()})
        elif i < 10:
            test3_issues.append({"type": "pothole", "severity": "medium", "status": "new", "created_at": datetime.now(timezone.utc).isoformat()})
        else:
            test3_issues.append({"type": "faded_lines", "severity": "low", "status": "new", "created_at": datetime.now(timezone.utc).isoformat()})
    
    score3, rationale3, risk3, *_ = engine.compute_baseline_score(test3_issues)
    test3_pass = score3 < 90  # Should be noticeably lower with volume
    print(f"\nTest 3: 30 mixed issues (3 high, 7 medium, 20 low)")
    print(f"  Expected: < 90 (noticeable impact)")
    print(f"  Actual:   {score3} (risk: {risk3:.1f})")
    print(f"  Result:   {'✓ PASS' if test3_pass else '✗ FAIL'}")
    
    # Test 4: 5 medium potholes (now MINOR), no high severity => should score very high
    test4_issues = [
        {"type": "pothole", "severity": "medium", "status": "new", "created_at": datetime.now(timezone.utc).isoformat()}
        for _ in range(5)
    ]
    score4, rationale4, risk4, *_ = engine.compute_baseline_score(test4_issues)
    test4_pass = score4 >= 95
    print(f"\nTest 4: 5 minor/medium/open issues (medium potholes)")
    print(f"  Expected: >= 95 (small sample, all minor, no critical)")
    print(f"  Actual:   {score4} (risk: {risk4:.1f})")
    print(f"  Result:   {'✓ PASS' if test4_pass else '✗ FAIL'}")
    
    # Summary
    all_pass = test1_pass and test2_pass and test3_pass and test4_pass
    print(f"\n{'=' * 60}")
    print(f"SELF-TEST {'PASSED ✓' if all_pass else 'FAILED ✗'}")
    print(f"{'=' * 60}\n")
    
    return all_pass


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Risk-based city health analyzer")
    parser.add_argument("--days", type=int, default=30, help="Analysis window in days")
    parser.add_argument("--include-resolved", action="store_true", help="Include resolved issues")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--self-test", action="store_true", help="Run self-test with synthetic data")
    args = parser.parse_args()
    
    if args.self_test:
        success = run_self_test()
        exit(0 if success else 1)
    
    print("=" * 60)
    print("KAVI City Health Analyzer (Risk-Based Scoring)")
    print("=" * 60)
    print(f"Analysis window: {args.days} days")
    print(f"Include resolved: {args.include_resolved}")
    print()
    
    analyzer = CityAnalyzer(days=args.days, include_resolved=args.include_resolved)
    summary = analyzer.analyze_city()
    
    if args.json:
        print(json.dumps(asdict(summary), indent=2))
    else:
        health_emoji = {
            "good": "🟢",
            "fair": "🟡",
            "poor": "🟠",
            "critical": "🔴"
        }
        
        print(f"{health_emoji.get(summary.overall_health, '⚪')} CITY HEALTH: {summary.overall_health.upper()}")
        print()
        print(f"📊 SCORES:")
        print(f"   Baseline Score: {summary.baseline_score}/100")
        print(f"   Final Score:    {summary.health_score}/100", end="")
        if summary.score_adjustment != 0:
            sign = "+" if summary.score_adjustment > 0 else ""
            print(f" ({sign}{summary.score_adjustment})")
        else:
            print()
        print(f"   Confidence:     {summary.confidence}")
        print()
        print(f"📈 RISK ANALYSIS:")
        print(f"   Total Risk Points: {summary.total_risk_points:.1f}")
        print(f"   Critical Issues:   {summary.critical_count}")
        print(f"   Major Issues:      {summary.major_count}")
        print(f"   Minor Issues:      {summary.minor_count}")
        print(f"   High-Sev Open:     {summary.high_severity_open_count}")
        print(f"   Rationale:         {summary.score_rationale}")
        if summary.adjustment_rationale:
            print(f"   Adjustment:        {summary.adjustment_rationale}")
        print()
        print(f"📝 SUMMARY:")
        print(f"   {summary.summary}")
        
        if summary.key_concerns:
            print()
            print(f"⚠️  KEY CONCERNS:")
            for concern in summary.key_concerns:
                print(f"   • {concern}")
        
        if summary.hotspots:
            print()
            print(f"📍 HOTSPOTS:")
            for spot in summary.hotspots:
                print(f"   • {spot}")
        
        if summary.recommendations:
            print()
            print(f"💡 RECOMMENDATIONS:")
            for rec in summary.recommendations:
                print(f"   • {rec}")
        
        if summary.breakdown:
            print()
            print(f"📊 BREAKDOWN:")
            for issue_type, count in sorted(summary.breakdown.items(), key=lambda x: -x[1]):
                print(f"   • {issue_type.replace('_', ' ').title()}: {count}")
        
        print()
        print("=" * 60)
