"""
Feedback Loop

Implements a learning system that analyzes validation failures and provides
insights for improving prompt templates and validation rules over time.
"""

import logging
import json
import os
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict, Counter

from .validation_rules import ValidationResult

logger = logging.getLogger("bpt-feedback-loop")

class FeedbackAnalyzer:
    """Analyzes validation failures to identify patterns and improvement opportunities"""
    
    def __init__(self, history_days: int = 30):
        self.history_days = history_days
        self.failure_patterns = defaultdict(list)
        self.improvement_suggestions = []
    
    def analyze_validation_failures(self, validation_results: Dict[str, List[ValidationResult]], 
                                   context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Analyze validation failures to identify patterns
        
        Args:
            validation_results: Results from validation engine
            context: Additional context (transcript_id, etc.)
            
        Returns:
            Analysis results with improvement suggestions
        """
        analysis = {
            "timestamp": datetime.now().isoformat(),
            "context": context,
            "failure_summary": {},
            "patterns_detected": [],
            "improvement_suggestions": [],
            "field_analysis": {}
        }
        
        # Collect all failures
        all_failures = []
        field_failures = defaultdict(list)
        
        for field_path, field_results in validation_results.items():
            for result in field_results:
                if not result.is_valid:
                    all_failures.append(result)
                    field_failures[field_path].append(result)
        
        if not all_failures:
            analysis["failure_summary"] = {"total_failures": 0, "message": "No validation failures detected"}
            return analysis
        
        # Analyze failure patterns
        rule_failures = Counter(failure.rule_name for failure in all_failures)
        severity_distribution = Counter(failure.severity for failure in all_failures)
        field_failure_counts = {field: len(failures) for field, failures in field_failures.items()}
        
        analysis["failure_summary"] = {
            "total_failures": len(all_failures),
            "unique_fields_affected": len(field_failures),
            "rule_failures": dict(rule_failures),
            "severity_distribution": dict(severity_distribution),
            "most_problematic_fields": sorted(field_failure_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        }
        
        # Detect patterns
        patterns = self._detect_failure_patterns(all_failures, field_failures)
        analysis["patterns_detected"] = patterns
        
        # Generate improvement suggestions
        suggestions = self._generate_improvement_suggestions(all_failures, field_failures, patterns)
        analysis["improvement_suggestions"] = suggestions
        
        # Field-specific analysis
        field_analysis = {}
        for field_path, failures in field_failures.items():
            field_analysis[field_path] = self._analyze_field_failures(field_path, failures)
        analysis["field_analysis"] = field_analysis
        
        return analysis
    
    def _detect_failure_patterns(self, all_failures: List[ValidationResult], 
                                field_failures: Dict[str, List[ValidationResult]]) -> List[Dict[str, Any]]:
        """Detect common patterns in validation failures"""
        patterns = []
        
        # Pattern 1: High frequency of specific rule failures
        rule_counts = Counter(failure.rule_name for failure in all_failures)
        for rule_name, count in rule_counts.items():
            if count >= 3:  # Threshold for pattern detection
                patterns.append({
                    "pattern_type": "frequent_rule_failure",
                    "rule_name": rule_name,
                    "occurrence_count": count,
                    "description": f"Rule '{rule_name}' is failing frequently ({count} times)",
                    "severity": "high" if count >= 5 else "medium"
                })
        
        # Pattern 2: Consistent field-level issues
        for field_path, failures in field_failures.items():
            if len(failures) >= 2:
                rule_types = set(failure.rule_name for failure in failures)
                patterns.append({
                    "pattern_type": "field_consistency_issue",
                    "field_path": field_path,
                    "failure_count": len(failures),
                    "failing_rules": list(rule_types),
                    "description": f"Field '{field_path}' consistently failing multiple validation rules",
                    "severity": "medium"
                })
        
        # Pattern 3: Template/null value clusters
        template_failures = [f for f in all_failures if f.rule_name in ["not_null", "no_template_values"]]
        if len(template_failures) >= 3:
            affected_fields = set(f.field_name for f in template_failures)
            patterns.append({
                "pattern_type": "template_value_cluster",
                "failure_count": len(template_failures),
                "affected_fields": list(affected_fields),
                "description": f"Multiple template/null value issues detected across {len(affected_fields)} fields",
                "severity": "high"
            })
        
        return patterns
    
    def _generate_improvement_suggestions(self, all_failures: List[ValidationResult],
                                        field_failures: Dict[str, List[ValidationResult]],
                                        patterns: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate specific improvement suggestions based on failure analysis"""
        suggestions = []
        
        # Suggestion 1: Prompt template improvements for null/template values
        template_issues = [f for f in all_failures if f.rule_name in ["not_null", "no_template_values"]]
        if template_issues:
            affected_fields = set(f.field_name for f in template_issues)
            suggestions.append({
                "suggestion_type": "prompt_template_enhancement",
                "priority": "high",
                "description": "Enhance prompt templates to reduce null/template value generation",
                "specific_actions": [
                    f"Add explicit instructions for {field}" for field in affected_fields
                ],
                "affected_fields": list(affected_fields),
                "estimated_impact": "Reduces template value failures by 60-80%"
            })
        
        # Suggestion 2: Content length improvements
        length_issues = [f for f in all_failures if f.rule_name == "min_content_length"]
        if length_issues:
            suggestions.append({
                "suggestion_type": "content_generation_enhancement",
                "priority": "medium", 
                "description": "Improve content generation to meet minimum length requirements",
                "specific_actions": [
                    "Add 'provide detailed explanation' instructions to prompts",
                    "Include examples of appropriate content length in prompts",
                    "Consider using higher temperature for more expansive generation"
                ],
                "estimated_impact": "Improves content quality and completeness"
            })
        
        # Suggestion 3: Structural completeness improvements
        structure_issues = [f for f in all_failures if f.rule_name == "structural_completeness"]
        if structure_issues:
            suggestions.append({
                "suggestion_type": "schema_enforcement",
                "priority": "high",
                "description": "Strengthen schema enforcement in LLM prompts",
                "specific_actions": [
                    "Include complete JSON schema in prompts",
                    "Add examples of properly structured output",
                    "Use response format constraints more strictly"
                ],
                "estimated_impact": "Ensures consistent output structure"
            })
        
        # Suggestion 4: Pattern-specific improvements
        for pattern in patterns:
            if pattern["pattern_type"] == "frequent_rule_failure":
                rule_name = pattern["rule_name"]
                suggestions.append({
                    "suggestion_type": "rule_specific_improvement",
                    "priority": "medium",
                    "description": f"Address frequent failures of rule '{rule_name}'",
                    "specific_actions": [
                        f"Review and refine '{rule_name}' validation logic",
                        f"Add specific prompt instructions to prevent '{rule_name}' failures",
                        f"Consider adjusting '{rule_name}' thresholds or criteria"
                    ],
                    "rule_name": rule_name,
                    "estimated_impact": f"Reduces '{rule_name}' failures"
                })
        
        return suggestions
    
    def _analyze_field_failures(self, field_path: str, failures: List[ValidationResult]) -> Dict[str, Any]:
        """Analyze failures for a specific field"""
        rule_counts = Counter(failure.rule_name for failure in failures)
        severities = Counter(failure.severity for failure in failures)
        
        # Common error messages
        error_messages = [f.error_message for f in failures if f.error_message]
        common_errors = Counter(error_messages).most_common(3)
        
        # Suggested fixes
        suggested_fixes = [f.suggested_fix for f in failures if f.suggested_fix]
        common_fixes = list(set(suggested_fixes))
        
        return {
            "total_failures": len(failures),
            "failing_rules": dict(rule_counts),
            "severity_distribution": dict(severities),
            "common_error_messages": [{"message": msg, "count": count} for msg, count in common_errors],
            "suggested_fixes": common_fixes,
            "needs_attention": len(failures) >= 2 or any(f.severity in ["critical", "high"] for f in failures)
        }

class FeedbackLoop:
    """Main feedback loop coordinator"""
    
    def __init__(self, storage_dir: str = "logs/feedback"):
        self.storage_dir = storage_dir
        self.analyzer = FeedbackAnalyzer()
        
        # Ensure storage directory exists
        os.makedirs(storage_dir, exist_ok=True)
        
        # Load historical data
        self.historical_analyses = self._load_historical_analyses()
    
    def process_validation_feedback(self, validation_results: Dict[str, List[ValidationResult]], 
                                   context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Process validation feedback and generate improvement insights
        
        Args:
            validation_results: Results from validation engine
            context: Additional context
            
        Returns:
            Feedback analysis with improvement suggestions
        """
        # Analyze current failures
        analysis = self.analyzer.analyze_validation_failures(validation_results, context)
        
        # Add historical context
        analysis["historical_context"] = self._get_historical_context(analysis)
        
        # Generate trend analysis
        analysis["trend_analysis"] = self._analyze_trends(analysis)
        
        # Save analysis
        self._save_analysis(analysis)
        
        # Log insights
        self._log_insights(analysis)
        
        return analysis
    
    def generate_improvement_report(self, days_back: int = 7) -> Dict[str, Any]:
        """Generate a comprehensive improvement report based on recent feedback"""
        
        cutoff_date = datetime.now() - timedelta(days=days_back)
        recent_analyses = [
            analysis for analysis in self.historical_analyses
            if datetime.fromisoformat(analysis["timestamp"]) >= cutoff_date
        ]
        
        if not recent_analyses:
            return {
                "report_period": f"Last {days_back} days",
                "total_analyses": 0,
                "message": "No validation analyses found in the specified period"
            }
        
        # Aggregate data across analyses
        all_suggestions = []
        all_patterns = []
        rule_failure_trends = defaultdict(list)
        
        for analysis in recent_analyses:
            all_suggestions.extend(analysis.get("improvement_suggestions", []))
            all_patterns.extend(analysis.get("patterns_detected", []))
            
            rule_failures = analysis.get("failure_summary", {}).get("rule_failures", {})
            for rule, count in rule_failures.items():
                rule_failure_trends[rule].append(count)
        
        # Generate consolidated suggestions
        suggestion_types = Counter(s["suggestion_type"] for s in all_suggestions)
        pattern_types = Counter(p["pattern_type"] for p in all_patterns)
        
        # Calculate trends
        trending_rules = {}
        for rule, counts in rule_failure_trends.items():
            if len(counts) >= 2:
                trending_rules[rule] = {
                    "average_failures": sum(counts) / len(counts),
                    "trend": "increasing" if counts[-1] > counts[0] else "decreasing",
                    "total_occurrences": len(counts)
                }
        
        return {
            "report_period": f"Last {days_back} days",
            "total_analyses": len(recent_analyses),
            "top_suggestion_types": dict(suggestion_types.most_common(5)),
            "top_pattern_types": dict(pattern_types.most_common(5)),
            "rule_failure_trends": trending_rules,
            "priority_actions": self._get_priority_actions(all_suggestions),
            "generated_at": datetime.now().isoformat()
        }
    
    def _load_historical_analyses(self) -> List[Dict[str, Any]]:
        """Load historical feedback analyses"""
        analyses = []
        
        try:
            for filename in os.listdir(self.storage_dir):
                if filename.startswith("feedback_analysis_") and filename.endswith(".json"):
                    filepath = os.path.join(self.storage_dir, filename)
                    with open(filepath, 'r') as f:
                        analysis = json.load(f)
                        analyses.append(analysis)
        except Exception as e:
            logger.warning(f"Could not load historical analyses: {str(e)}")
        
        # Sort by timestamp
        analyses.sort(key=lambda x: x.get("timestamp", ""))
        return analyses
    
    def _save_analysis(self, analysis: Dict[str, Any]):
        """Save feedback analysis to storage"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            context = analysis.get("context") or {}
            transcript_id = context.get("transcript_id", "unknown")
            filename = f"feedback_analysis_{transcript_id}_{timestamp}.json"
            filepath = os.path.join(self.storage_dir, filename)
            
            # Ensure timestamp is set in analysis
            if "timestamp" not in analysis:
                analysis["timestamp"] = datetime.now().isoformat()
            
            with open(filepath, 'w') as f:
                json.dump(analysis, f, indent=2, default=str)
            
            # Add to historical analyses
            self.historical_analyses.append(analysis)
            
            logger.debug(f"Feedback analysis saved to: {filepath}")
            
        except Exception as e:
            logger.error(f"Failed to save feedback analysis: {str(e)}")
    
    def _get_historical_context(self, current_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Get historical context for current analysis"""
        if not self.historical_analyses:
            return {"message": "No historical data available"}
        
        # Compare with recent analyses
        recent_analyses = self.historical_analyses[-5:]  # Last 5 analyses
        
        # Calculate averages
        avg_failures = sum(
            a.get("failure_summary", {}).get("total_failures", 0) 
            for a in recent_analyses
        ) / len(recent_analyses) if recent_analyses else 0
        
        current_failures = current_analysis.get("failure_summary", {}).get("total_failures", 0)
        
        return {
            "recent_average_failures": avg_failures,
            "current_vs_average": "above" if current_failures > avg_failures else "below",
            "historical_analyses_count": len(self.historical_analyses),
            "comparison_base": f"Last {len(recent_analyses)} analyses"
        }
    
    def _analyze_trends(self, current_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze trends in validation failures"""
        if len(self.historical_analyses) < 2:
            return {"message": "Insufficient data for trend analysis"}
        
        # Look at recent trend (last 3 analyses)
        recent = self.historical_analyses[-3:] + [current_analysis]
        
        failure_counts = [a.get("failure_summary", {}).get("total_failures", 0) for a in recent]
        
        if len(failure_counts) >= 2:
            trend = "improving" if failure_counts[-1] < failure_counts[0] else "degrading"
            return {
                "failure_trend": trend,
                "recent_failure_counts": failure_counts,
                "trend_strength": abs(failure_counts[-1] - failure_counts[0])
            }
        
        return {"message": "Unable to determine trend"}
    
    def _get_priority_actions(self, all_suggestions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get prioritized action items from suggestions"""
        high_priority = [s for s in all_suggestions if s.get("priority") == "high"]
        medium_priority = [s for s in all_suggestions if s.get("priority") == "medium"]
        
        # Deduplicate by suggestion type
        seen_types = set()
        priority_actions = []
        
        for suggestion in high_priority + medium_priority:
            suggestion_type = suggestion.get("suggestion_type")
            if suggestion_type not in seen_types:
                priority_actions.append({
                    "action": suggestion.get("description"),
                    "priority": suggestion.get("priority"),
                    "type": suggestion_type,
                    "specific_actions": suggestion.get("specific_actions", [])
                })
                seen_types.add(suggestion_type)
        
        return priority_actions[:10]  # Top 10 actions
    
    def _log_insights(self, analysis: Dict[str, Any]):
        """Log key insights from feedback analysis"""
        failure_summary = analysis.get("failure_summary", {})
        total_failures = failure_summary.get("total_failures", 0)
        
        if total_failures == 0:
            logger.info("Validation feedback: No failures detected - system performing well")
            return
        
        logger.info(f"Validation feedback: {total_failures} failures detected across {failure_summary.get('unique_fields_affected', 0)} fields")
        
        # Log top patterns
        patterns = analysis.get("patterns_detected", [])
        if patterns:
            logger.info(f"Key patterns detected: {', '.join(p['pattern_type'] for p in patterns[:3])}")
        
        # Log top suggestions
        suggestions = analysis.get("improvement_suggestions", [])
        high_priority_suggestions = [s for s in suggestions if s.get("priority") == "high"]
        if high_priority_suggestions:
            logger.warning(f"High priority improvements needed: {len(high_priority_suggestions)} critical suggestions")
        
        # Log trend
        trend_analysis = analysis.get("trend_analysis", {})
        if "failure_trend" in trend_analysis:
            trend = trend_analysis["failure_trend"]
            logger.info(f"Validation trend: {trend}") 