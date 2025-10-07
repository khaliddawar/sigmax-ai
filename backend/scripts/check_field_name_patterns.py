#!/usr/bin/env python3
"""
Field Name Pattern Checker

This script scans the codebase for potential field name mismatches that could
cause issues similar to the recent 'transcript_text' vs 'text' bug.

It's a non-destructive diagnostic tool that can be run safely on the codebase
to identify potential issues before they cause problems in production.
"""

import os
import re
import logging
from pathlib import Path
from typing import List, Dict, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("field-checker")


class FieldNameChecker:
    """Checks for potentially problematic field name patterns"""
    
    def __init__(self, project_root: str = "."):
        """Initialize with project root directory"""
        self.project_root = Path(project_root)
        self.issues = []
        
        # Patterns to look for (regex patterns and their descriptions)
        self.problematic_patterns = [
            # Field names that are known to be incorrect
            (r'\.get\(["\']transcript_text["\']', "Uses deprecated 'transcript_text' field (should be 'text')"),
            (r'\.get\(["\']character_count["\']', "Uses non-existent 'character_count' field (should calculate from 'text')"),
            
            # Potential future issues
            (r'\.get\(["\']chunks_count["\']', "Possible typo: 'chunks_count' (should be 'chunk_count')"),
            (r'\.get\(["\']transcripts_text["\']', "Possible typo: 'transcripts_text' (should be 'text')"),
            (r'\.get\(["\']text_content["\']', "Possible confusion: 'text_content' (should be 'text')"),
            (r'\.get\(["\']transcript_content["\']', "Possible confusion: 'transcript_content' (should be 'text')"),
            
            # Hard-coded field access without .get() (more dangerous)
            (r'\[["\']transcript_text["\']\]', "Hard-coded access to deprecated 'transcript_text' field"),
            (r'\[["\']character_count["\']\]', "Hard-coded access to non-existent 'character_count' field"),
        ]
        
        # Files to exclude from checking
        self.exclude_patterns = [
            "test_field_validator.py",  # Our test file intentionally has wrong patterns
            "__pycache__",
            ".git",
            "node_modules",
            ".env",
            "*.pyc",
            "docs/field_name_reference.md",  # Our documentation intentionally shows wrong patterns
        ]
    
    def should_exclude_file(self, file_path: Path) -> bool:
        """Check if a file should be excluded from scanning"""
        str_path = str(file_path)
        
        for pattern in self.exclude_patterns:
            if pattern in str_path:
                return True
        
        return False
    
    def scan_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """Scan a single file for problematic patterns"""
        if self.should_exclude_file(file_path):
            return []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except (UnicodeDecodeError, PermissionError):
            # Skip binary files or files we can't read
            return []
        
        file_issues = []
        lines = content.split('\n')
        
        for line_number, line in enumerate(lines, 1):
            for pattern, description in self.problematic_patterns:
                if re.search(pattern, line):
                    file_issues.append({
                        "file": str(file_path.relative_to(self.project_root)),
                        "line": line_number,
                        "line_content": line.strip(),
                        "pattern": pattern,
                        "description": description,
                        "severity": self._get_severity(pattern)
                    })
        
        return file_issues
    
    def _get_severity(self, pattern: str) -> str:
        """Determine severity level of an issue"""
        if "transcript_text" in pattern or "character_count" in pattern:
            return "HIGH"  # Known issues
        elif "Hard-coded" in pattern:
            return "MEDIUM"  # More dangerous pattern
        else:
            return "LOW"  # Potential future issues
    
    def scan_directory(self, directory: Path) -> None:
        """Recursively scan a directory for Python files"""
        for item in directory.iterdir():
            if item.is_file() and item.suffix == '.py':
                issues = self.scan_file(item)
                self.issues.extend(issues)
            elif item.is_dir() and not self.should_exclude_file(item):
                self.scan_directory(item)
    
    def run_scan(self) -> List[Dict[str, Any]]:
        """Run the complete scan and return results"""
        logger.info(f"🔍 Scanning {self.project_root} for field name issues...")
        
        if (self.project_root / "app").exists():
            logger.info("📁 Scanning app/ directory...")
            self.scan_directory(self.project_root / "app")
        
        if (self.project_root / "scripts").exists():
            logger.info("📁 Scanning scripts/ directory...")
            self.scan_directory(self.project_root / "scripts")
        
        if (self.project_root / "tests").exists():
            logger.info("📁 Scanning tests/ directory...")
            self.scan_directory(self.project_root / "tests")
        
        # Also scan root level Python files
        for py_file in self.project_root.glob("*.py"):
            if not self.should_exclude_file(py_file):
                issues = self.scan_file(py_file)
                self.issues.extend(issues)
        
        return self.issues
    
    def generate_report(self) -> str:
        """Generate a human-readable report"""
        if not self.issues:
            return "✅ No field name issues found!"
        
        # Group by severity
        high_issues = [i for i in self.issues if i["severity"] == "HIGH"]
        medium_issues = [i for i in self.issues if i["severity"] == "MEDIUM"]
        low_issues = [i for i in self.issues if i["severity"] == "LOW"]
        
        report = f"\n🚨 Field Name Issues Found: {len(self.issues)} total\n"
        report += "=" * 60 + "\n"
        
        if high_issues:
            report += f"\n🔴 HIGH SEVERITY ({len(high_issues)} issues):\n"
            report += "-" * 40 + "\n"
            for issue in high_issues:
                report += f"📁 {issue['file']}:{issue['line']}\n"
                report += f"   ⚠️  {issue['description']}\n"
                report += f"   📝 {issue['line_content']}\n\n"
        
        if medium_issues:
            report += f"\n🟡 MEDIUM SEVERITY ({len(medium_issues)} issues):\n"
            report += "-" * 40 + "\n"
            for issue in medium_issues:
                report += f"📁 {issue['file']}:{issue['line']}\n"
                report += f"   ⚠️  {issue['description']}\n"
                report += f"   📝 {issue['line_content']}\n\n"
        
        if low_issues:
            report += f"\n🟢 LOW SEVERITY ({len(low_issues)} issues):\n"
            report += "-" * 40 + "\n"
            for issue in low_issues:
                report += f"📁 {issue['file']}:{issue['line']}\n"
                report += f"   ⚠️  {issue['description']}\n"
                report += f"   📝 {issue['line_content']}\n\n"
        
        report += "\n🛡️ RECOMMENDATIONS:\n"
        report += "-" * 20 + "\n"
        
        if high_issues:
            report += "• HIGH issues should be fixed immediately\n"
            report += "• Replace 'transcript_text' with 'text'\n"
            report += "• Calculate character count from len(text)\n"
        
        if medium_issues:
            report += "• MEDIUM issues use dangerous hard-coded field access\n"
            report += "• Consider using .get() with defaults instead\n"
        
        if low_issues:
            report += "• LOW issues are potential future problems\n"
            report += "• Consider reviewing field names for consistency\n"
        
        report += f"\n📚 See docs/field_name_reference.md for correct patterns\n"
        report += f"🔧 Consider using app.services.field_validator for safe access\n"
        
        return report


def main():
    """Main function to run the field name checker"""
    checker = FieldNameChecker()
    
    logger.info("🔍 Starting field name pattern check...")
    issues = checker.run_scan()
    
    report = checker.generate_report()
    print(report)
    
    # Save report to file
    report_file = Path("field_name_check_report.txt")
    with open(report_file, 'w') as f:
        f.write(report)
    
    logger.info(f"📄 Report saved to {report_file}")
    
    # Exit with error code if high-severity issues found
    high_severity_count = len([i for i in issues if i["severity"] == "HIGH"])
    if high_severity_count > 0:
        logger.error(f"❌ Found {high_severity_count} high-severity issues!")
        return 1
    else:
        logger.info("✅ No high-severity issues found")
        return 0


if __name__ == "__main__":
    import sys
    sys.exit(main()) 