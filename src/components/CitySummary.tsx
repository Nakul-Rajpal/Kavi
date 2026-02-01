"use client";

import { useState, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { 
  ChevronDown, 
  Activity, 
  AlertTriangle, 
  Lightbulb, 
  MapPin,
  TrendingUp,
  Shield,
  Info,
  Zap
} from "lucide-react";

// =============================================================================
// Types
// =============================================================================

interface CitySummaryData {
  overall_health: "good" | "fair" | "poor" | "critical";
  health_score: number;
  baseline_score: number;
  total_issues: number;
  total_risk_points: number;
  critical_count: number;
  major_count: number;
  minor_count: number;
  high_severity_open_count: number;
  summary: string;
  key_concerns: string[];
  recommendations: string[];
  breakdown: Record<string, number>;
  hotspots: string[];
  confidence: "low" | "medium" | "high";
  score_rationale: string;
}

interface PingData {
  type?: string;
  severity?: string;
  street_name?: string;
  status?: string;
  created_at?: string;
}

interface CitySummaryProps {
  pings: PingData[];
}

interface HotspotInfo {
  street: string;
  totalCount: number;
  riskPoints: number;
  criticalCount: number;
  highSeverityCount: number;
}

// =============================================================================
// Constants (matching Python backend)
// =============================================================================

// Criticality levels
const CRITICALITY_CRITICAL = 3;
const CRITICALITY_MAJOR = 2;
const CRITICALITY_MINOR = 1;

// Criticality multipliers
const CRITICALITY_MULTIPLIERS: Record<number, number> = {
  [CRITICALITY_CRITICAL]: 6.0,
  [CRITICALITY_MAJOR]: 2.0,
  [CRITICALITY_MINOR]: 1.0,
};

// Severity points
const SEVERITY_POINTS: Record<string, number> = {
  low: 1,
  medium: 3,
  high: 8,
};

// Status multipliers
const STATUS_MULTIPLIERS: Record<string, number> = {
  new: 1.0,
  open: 1.0,
  triaged: 0.8,
  assigned: 0.7,
  in_progress: 0.6,
  resolved: 0.0,
  rejected: 0.0,
};

// Recency multipliers
const RECENCY_MULTIPLIERS: [number, number][] = [
  [7, 1.0],
  [30, 0.8],
  [90, 0.5],
  [Infinity, 0.3],
];
const MISSING_TIMESTAMP_MULTIPLIER = 0.6;

// Risk-to-score conversion
const RISK_SATURATION_R = 600.0;
const HIGH_PRIOR_SCORE = 99;
const SCORE_RANGE = 98;
const VOLUME_PENALTY_THRESHOLD = 50;
const MIN_SCORE_FEW_MINOR_ISSUES = 97;
const MAX_SCORE_CRITICAL_HIGH_OPEN = 92;
const ANALYSIS_DAYS = 30;

// Keywords for criticality classification
const CRITICAL_KEYWORDS = [
  "traffic_light", "signal_out", "signal_malfunction", "light_outage",
  "highway_obstruction", "road_blocked", "road_closure",
  "downed_power_line", "power_line", "telephone_pole", "utility_pole",
  "bridge_damage", "bridge", "sinkhole", "collapse",
  "gas_leak", "water_main", "flooding_major", "emergency",
];

const MAJOR_KEYWORDS = [
  "stop_sign", "missing_sign", "damaged_sign", "sign",
  "guardrail", "barrier_damage",
  "pothole",
  "street_light", "streetlight", "light_out", "damaged_light",
  "fallen_tree", "tree_down", "obstruction",
  "construction_hazard", "hazard",
  "flood", "flooding",
];

const MINOR_KEYWORDS = [
  "faded_lines", "faded_markings", "lane_marking", "marking",
  "crack", "minor_crack", "surface_crack",
  "debris", "litter", "graffiti",
  "cosmetic", "aesthetic",
];

// Health color mapping
const healthColors: Record<string, { bg: string; text: string; glow: string; solid: string }> = {
  good: { bg: "bg-green-500/20", text: "text-green-400", glow: "shadow-green-500/30", solid: "bg-green-400" },
  fair: { bg: "bg-yellow-500/20", text: "text-yellow-400", glow: "shadow-yellow-500/30", solid: "bg-yellow-400" },
  poor: { bg: "bg-orange-500/20", text: "text-orange-400", glow: "shadow-orange-500/30", solid: "bg-orange-400" },
  critical: { bg: "bg-red-500/20", text: "text-red-400", glow: "shadow-red-500/30", solid: "bg-red-400" },
};

const confidenceColors: Record<string, string> = {
  low: "text-orange-400",
  medium: "text-yellow-400",
  high: "text-green-400",
};

// =============================================================================
// Risk-Based Scoring Engine (matching Python backend)
// =============================================================================

function classifyCriticality(issue: PingData): number {
  const issueType = (issue.type || "").toLowerCase().replace(/ /g, "_").replace(/-/g, "_");
  const severity = (issue.severity || "medium").toLowerCase();
  
  // Check critical keywords
  for (const keyword of CRITICAL_KEYWORDS) {
    if (issueType.includes(keyword)) return CRITICALITY_CRITICAL;
  }
  
  // Check major keywords
  for (const keyword of MAJOR_KEYWORDS) {
    if (issueType.includes(keyword)) {
      // Potholes: only high-severity are MAJOR, otherwise MINOR
      if (issueType.includes("pothole")) {
        if (severity === "high") return CRITICALITY_MAJOR;
        return CRITICALITY_MINOR;  // medium & low potholes are minor
      }
      return CRITICALITY_MAJOR;
    }
  }
  
  // Check minor keywords
  for (const keyword of MINOR_KEYWORDS) {
    if (issueType.includes(keyword)) return CRITICALITY_MINOR;
  }
  
  // Fallback: use severity
  if (severity === "high") return CRITICALITY_MAJOR;
  if (severity === "low") return CRITICALITY_MINOR;
  return CRITICALITY_MINOR;
}

function getRecencyMultiplier(timestamp?: string): number {
  if (!timestamp) return MISSING_TIMESTAMP_MULTIPLIER;
  
  try {
    const issueTime = new Date(timestamp);
    if (isNaN(issueTime.getTime())) return MISSING_TIMESTAMP_MULTIPLIER;
    
    const now = new Date();
    const daysOld = Math.floor((now.getTime() - issueTime.getTime()) / (1000 * 60 * 60 * 24));
    
    for (const [thresholdDays, multiplier] of RECENCY_MULTIPLIERS) {
      if (daysOld <= thresholdDays) return multiplier;
    }
    return RECENCY_MULTIPLIERS[RECENCY_MULTIPLIERS.length - 1][1];
  } catch {
    return MISSING_TIMESTAMP_MULTIPLIER;
  }
}

function getStatusMultiplier(status?: string): number {
  const s = (status || "new").toLowerCase();
  return STATUS_MULTIPLIERS[s] ?? 1.0;
}

function getSeverityPoints(severity?: string): number {
  const s = (severity || "medium").toLowerCase();
  return SEVERITY_POINTS[s] ?? 3;
}

function isOpen(status?: string): boolean {
  const s = (status || "new").toLowerCase();
  return ["new", "open", "triaged", "assigned", "in_progress"].includes(s);
}

function isRecent(issue: PingData): boolean {
  if (!issue.created_at) return true;
  
  try {
    const issueTime = new Date(issue.created_at);
    if (isNaN(issueTime.getTime())) return true;
    
    const cutoff = new Date();
    cutoff.setDate(cutoff.getDate() - ANALYSIS_DAYS);
    
    return issueTime >= cutoff;
  } catch {
    return true;
  }
}

function computeIssueRiskPoints(issue: PingData): number {
  const severityPts = getSeverityPoints(issue.severity);
  const criticality = classifyCriticality(issue);
  const criticalityMult = CRITICALITY_MULTIPLIERS[criticality];
  const statusMult = getStatusMultiplier(issue.status);
  const recencyMult = getRecencyMultiplier(issue.created_at);
  
  return severityPts * criticalityMult * statusMult * recencyMult;
}

function computeBaselineScore(issues: PingData[]): {
  score: number;
  rationale: string;
  totalRisk: number;
  criticalCount: number;
  majorCount: number;
  minorCount: number;
  highSeverityOpenCount: number;
} {
  if (issues.length === 0) {
    return {
      score: 100,
      rationale: "No issues reported - city infrastructure is in excellent condition.",
      totalRisk: 0,
      criticalCount: 0,
      majorCount: 0,
      minorCount: 0,
      highSeverityOpenCount: 0,
    };
  }
  
  const recentIssues = issues.filter(isRecent);
  const totalRecent = recentIssues.length;
  
  if (totalRecent === 0) {
    return {
      score: 99,
      rationale: "No recent issues in the analysis window.",
      totalRisk: 0,
      criticalCount: 0,
      majorCount: 0,
      minorCount: 0,
      highSeverityOpenCount: 0,
    };
  }
  
  // Compute risk points and categorize
  let totalRisk = 0;
  let criticalCount = 0;
  let majorCount = 0;
  let minorCount = 0;
  let highSeverityOpenCount = 0;
  let criticalHighOpen = false;
  
  for (const issue of recentIssues) {
    totalRisk += computeIssueRiskPoints(issue);
    
    const criticality = classifyCriticality(issue);
    if (criticality === CRITICALITY_CRITICAL) criticalCount++;
    else if (criticality === CRITICALITY_MAJOR) majorCount++;
    else minorCount++;
    
    const severity = (issue.severity || "medium").toLowerCase();
    const issueIsOpen = isOpen(issue.status);
    
    if (severity === "high" && issueIsOpen) {
      highSeverityOpenCount++;
      if (criticality === CRITICALITY_CRITICAL) criticalHighOpen = true;
    }
  }
  
  // Risk-to-score conversion
  const riskFactor = 1 - Math.exp(-totalRisk / RISK_SATURATION_R);
  let baseline = HIGH_PRIOR_SCORE - SCORE_RANGE * riskFactor;
  
  // Volume penalty
  if (totalRecent > VOLUME_PENALTY_THRESHOLD) {
    const volumePenalty = Math.log(totalRecent / VOLUME_PENALTY_THRESHOLD) * 2;
    baseline -= volumePenalty;
  }
  
  // Hard rules
  if (totalRecent <= 15 && criticalCount === 0 && highSeverityOpenCount === 0) {
    baseline = Math.max(baseline, MIN_SCORE_FEW_MINOR_ISSUES);
  }
  
  if (criticalHighOpen) {
    baseline = Math.min(baseline, MAX_SCORE_CRITICAL_HIGH_OPEN);
  }
  
  baseline = Math.max(0, Math.min(100, Math.round(baseline)));
  
  // Build rationale
  const parts = [`${totalRecent} issues analyzed`, `total risk: ${totalRisk.toFixed(1)} pts`];
  if (criticalCount > 0) parts.push(`${criticalCount} critical`);
  if (majorCount > 0) parts.push(`${majorCount} major`);
  if (minorCount > 0) parts.push(`${minorCount} minor`);
  if (highSeverityOpenCount > 0) parts.push(`${highSeverityOpenCount} high-severity open`);
  
  return {
    score: baseline,
    rationale: parts.join("; "),
    totalRisk,
    criticalCount,
    majorCount,
    minorCount,
    highSeverityOpenCount,
  };
}

function getHealthBucket(score: number): "good" | "fair" | "poor" | "critical" {
  if (score >= 90) return "good";
  if (score >= 70) return "fair";
  if (score >= 50) return "poor";
  return "critical";
}

function computeConfidence(issues: PingData[]): "low" | "medium" | "high" {
  const recentIssues = issues.filter(isRecent);
  const total = recentIssues.length;
  
  const withTimestamp = recentIssues.filter(i => i.created_at).length;
  const timestampRatio = total > 0 ? withTimestamp / total : 0;
  
  if (total >= 15 && timestampRatio >= 0.8) return "high";
  if (total >= 5 && timestampRatio >= 0.5) return "medium";
  return "low";
}

function computeHotspots(issues: PingData[], topN: number = 3): HotspotInfo[] {
  const streetData: Record<string, HotspotInfo> = {};
  
  for (const issue of issues) {
    const street = issue.street_name || "Unknown";
    
    if (!streetData[street]) {
      streetData[street] = {
        street,
        totalCount: 0,
        riskPoints: 0,
        criticalCount: 0,
        highSeverityCount: 0,
      };
    }
    
    const info = streetData[street];
    info.totalCount++;
    info.riskPoints += computeIssueRiskPoints(issue);
    
    if (classifyCriticality(issue) === CRITICALITY_CRITICAL) info.criticalCount++;
    if ((issue.severity || "").toLowerCase() === "high") info.highSeverityCount++;
  }
  
  return Object.values(streetData)
    .sort((a, b) => b.riskPoints - a.riskPoints)
    .slice(0, topN);
}

// =============================================================================
// Component
// =============================================================================

export default function CitySummary({ pings }: CitySummaryProps) {
  const [isOpen, setIsOpen] = useState(false);

  const summary = useMemo<CitySummaryData | null>(() => {
    if (pings.length === 0) return null;

    // Compute baseline score using risk-based algorithm
    const {
      score: baselineScore,
      rationale,
      totalRisk,
      criticalCount,
      majorCount,
      minorCount,
      highSeverityOpenCount,
    } = computeBaselineScore(pings);
    
    const overallHealth = getHealthBucket(baselineScore);
    const confidence = computeConfidence(pings);
    const hotspots = computeHotspots(pings);
    
    // Type breakdown
    const typeBreakdown: Record<string, number> = {};
    for (const ping of pings) {
      const type = ping.type || "unknown";
      typeBreakdown[type] = (typeBreakdown[type] || 0) + 1;
    }
    
    // Generate summary text
    let summaryText: string;
    if (pings.length === 0) {
      summaryText = "No infrastructure issues reported. City infrastructure is in excellent condition.";
    } else if (criticalCount > 0) {
      summaryText = `Providence has ${pings.length} issues including ${criticalCount} critical. Immediate attention required for safety-related concerns.`;
    } else if (highSeverityOpenCount > 0) {
      summaryText = `Providence has ${pings.length} infrastructure issues, ${highSeverityOpenCount} high-severity requiring prompt attention.`;
    } else {
      summaryText = `Providence has ${pings.length} minor infrastructure issues. City infrastructure is well-maintained overall.`;
    }
    
    // Key concerns
    const concerns = Object.entries(typeBreakdown)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 3)
      .map(([type, count]) => `${formatIssueType(type)}: ${count} issue${count !== 1 ? "s" : ""}`);
    
    // Recommendations
    const recommendations: string[] = [];
    if (criticalCount > 0) {
      recommendations.push(`Address ${criticalCount} critical safety issues immediately`);
    }
    if (highSeverityOpenCount > 0) {
      recommendations.push(`Prioritize ${highSeverityOpenCount} high-severity open issues`);
    }
    recommendations.push("Continue regular infrastructure monitoring");
    
    return {
      overall_health: overallHealth,
      health_score: baselineScore,
      baseline_score: baselineScore,
      total_issues: pings.length,
      total_risk_points: totalRisk,
      critical_count: criticalCount,
      major_count: majorCount,
      minor_count: minorCount,
      high_severity_open_count: highSeverityOpenCount,
      summary: summaryText,
      key_concerns: concerns,
      recommendations: recommendations.slice(0, 3),
      breakdown: typeBreakdown,
      hotspots: hotspots.filter(h => h.street !== "Unknown").map(h => h.street),
      confidence,
      score_rationale: rationale,
    };
  }, [pings]);

  if (!summary) return null;

  const colors = healthColors[summary.overall_health] || healthColors.fair;

  return (
    <div className="absolute top-20 left-1/2 -translate-x-1/2 z-[700] pointer-events-auto">
      {/* Toggle Button */}
      <motion.button
        onClick={() => setIsOpen(!isOpen)}
        className={`flex items-center gap-3 px-5 py-3 rounded-2xl liquid-glass border border-white/20 
          hover:border-cyan-500/30 transition-all shadow-lg ${isOpen ? 'rounded-b-none border-b-0' : ''}`}
        whileHover={{ scale: 1.02 }}
        whileTap={{ scale: 0.98 }}
      >
        <div className={`w-3 h-3 rounded-full shadow-lg ${colors.glow}`}>
          <div className={`w-full h-full rounded-full ${colors.solid} animate-pulse`} />
        </div>
        <span className="text-sm font-bold text-white/90">City Health</span>
        <div className={`px-2 py-0.5 rounded-full text-[10px] font-black uppercase ${colors.bg} ${colors.text}`}>
          {summary.overall_health}
        </div>
        <div className={`text-xl font-black ${colors.text}`}>{summary.health_score}</div>
        <motion.div
          animate={{ rotate: isOpen ? 180 : 0 }}
          transition={{ duration: 0.2 }}
        >
          <ChevronDown size={18} className="text-white/50" />
        </motion.div>
      </motion.button>

      {/* Dropdown Panel */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: -10, height: 0 }}
            animate={{ opacity: 1, y: 0, height: "auto" }}
            exit={{ opacity: 0, y: -10, height: 0 }}
            transition={{ duration: 0.2 }}
            className="liquid-glass rounded-2xl rounded-t-none border border-white/20 border-t-0 
              shadow-[0_20px_60px_rgba(0,0,0,0.5)] overflow-hidden"
          >
            <div className="p-5 max-w-md">
              {/* Health Score with Risk Points */}
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className={`w-12 h-12 rounded-xl ${colors.bg} flex items-center justify-center`}>
                    <Activity size={24} className={colors.text} />
                  </div>
                  <div>
                    <div className="text-[9px] text-white/40 uppercase tracking-wider">Health Score</div>
                    <div className={`text-2xl font-black ${colors.text}`}>{summary.health_score}</div>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-[9px] text-white/40 uppercase tracking-wider">Risk Points</div>
                  <div className="text-lg font-bold text-white/80">{summary.total_risk_points.toFixed(1)}</div>
                </div>
              </div>

              {/* Risk Breakdown Pills */}
              <div className="flex gap-2 mb-4">
                {summary.critical_count > 0 && (
                  <div className="flex items-center gap-1 px-2 py-1 rounded-full bg-red-500/20 text-red-400">
                    <Zap size={10} />
                    <span className="text-[10px] font-bold">{summary.critical_count} critical</span>
                  </div>
                )}
                {summary.major_count > 0 && (
                  <div className="px-2 py-1 rounded-full bg-orange-500/20 text-orange-400 text-[10px] font-bold">
                    {summary.major_count} major
                  </div>
                )}
                {summary.minor_count > 0 && (
                  <div className="px-2 py-1 rounded-full bg-green-500/20 text-green-400 text-[10px] font-bold">
                    {summary.minor_count} minor
                  </div>
                )}
              </div>

              {/* Confidence Indicator */}
              <div className="flex items-center gap-2 mb-3 p-2 rounded-lg bg-white/5">
                <Shield size={12} className={confidenceColors[summary.confidence]} />
                <span className="text-[9px] text-white/50 uppercase tracking-wider">Confidence:</span>
                <span className={`text-[10px] font-bold ${confidenceColors[summary.confidence]}`}>
                  {summary.confidence.toUpperCase()}
                </span>
                <div className="flex-1" />
                <button 
                  className="group relative"
                  onClick={(e) => e.stopPropagation()}
                >
                  <Info size={11} className="text-white/30 hover:text-white/60 cursor-help" />
                  <div className="absolute bottom-full right-0 mb-2 w-52 p-2 rounded-lg bg-black/95 
                    text-[9px] text-white/70 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10 leading-relaxed">
                    {summary.score_rationale}
                  </div>
                </button>
              </div>

              {/* Summary */}
              <p className="text-xs text-white/70 mb-4 leading-relaxed">
                {summary.summary}
              </p>

              {/* Key Concerns */}
              {summary.key_concerns.length > 0 && (
                <div className="mb-3">
                  <div className="flex items-center gap-2 mb-2">
                    <AlertTriangle size={12} className="text-orange-400" />
                    <span className="text-[9px] font-black text-white/50 uppercase tracking-wider">
                      Key Concerns
                    </span>
                  </div>
                  <div className="space-y-1">
                    {summary.key_concerns.map((concern, i) => (
                      <div 
                        key={i}
                        className="text-[11px] text-white/60 pl-3 border-l-2 border-orange-400/30"
                      >
                        {concern}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Hotspots */}
              {summary.hotspots.length > 0 && (
                <div className="mb-3">
                  <div className="flex items-center gap-2 mb-2">
                    <MapPin size={12} className="text-red-400" />
                    <span className="text-[9px] font-black text-white/50 uppercase tracking-wider">
                      Hotspots
                    </span>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {summary.hotspots.map((spot, i) => (
                      <span 
                        key={i}
                        className="px-2 py-0.5 rounded-full bg-red-500/10 text-red-400 text-[10px] font-semibold"
                      >
                        {spot}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Recommendations */}
              {summary.recommendations.length > 0 && (
                <div className="mb-3">
                  <div className="flex items-center gap-2 mb-2">
                    <Lightbulb size={12} className="text-cyan-400" />
                    <span className="text-[9px] font-black text-white/50 uppercase tracking-wider">
                      Recommendations
                    </span>
                  </div>
                  <div className="space-y-1">
                    {summary.recommendations.map((rec, i) => (
                      <div 
                        key={i}
                        className="text-[11px] text-white/60 pl-3 border-l-2 border-cyan-400/30"
                      >
                        {rec}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Issue Breakdown */}
              <div className="pt-3 border-t border-white/10">
                <div className="flex items-center gap-2 mb-2">
                  <TrendingUp size={12} className="text-purple-400" />
                  <span className="text-[9px] font-black text-white/50 uppercase tracking-wider">
                    Breakdown
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-1.5">
                  {Object.entries(summary.breakdown)
                    .sort((a, b) => b[1] - a[1])
                    .map(([type, count]) => (
                    <div 
                      key={type}
                      className="flex items-center justify-between p-1.5 rounded-lg bg-white/5"
                    >
                      <span className="text-[10px] text-white/60">{formatIssueType(type)}</span>
                      <span className="text-[10px] font-bold text-white">{count}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// =============================================================================
// Helpers
// =============================================================================

function formatIssueType(type: string): string {
  const typeNames: Record<string, string> = {
    pothole: "Potholes",
    damaged_light: "Street Lights",
    fallen_tree: "Obstructions",
    faded_lines: "Faded Markings",
    debris: "Debris",
    flood: "Flooding",
    damaged_sign: "Damaged Signs",
    sign: "Signs",
    traffic_light: "Traffic Lights",
  };
  return typeNames[type] || type.charAt(0).toUpperCase() + type.slice(1).replace(/_/g, " ");
}
