"""
Enhanced Prompt Engine for Dynamic Section Generation

This module provides sophisticated prompt management for the dynamic AI-driven
section generation system. It loads prompts from YAML configuration files and
generates context-aware prompts for different stages of the processing pipeline.
"""

import os
import logging
import yaml
from typing import Dict, Any, Optional, List
from pathlib import Path

# Import configurable limits to prevent hardcoded truncations
from app.settings import MAX_DISCOVERY_CHARS, MAX_SYNTHESIS_CHARS, MAX_SAFE_TOKENS, CHARS_PER_TOKEN

logger = logging.getLogger("enhanced-prompt-engine")


class EnhancedPromptEngine:
    """
    Sophisticated prompt management for dynamic section generation.
    
    Provides methods to load and generate context-aware prompts for:
    - Section discovery and boundary detection
    - Content synthesis and extraction
    - Quality validation and improvement
    """
    
    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialize the Enhanced Prompt Engine
        
        Args:
            config_dir: Optional path to prompt configuration directory.
                       Defaults to config/prompts in project root.
        """
        self.config_dir = config_dir or self._get_default_config_dir()
        self.prompts = {}
        self._load_prompt_configurations()
        
    def _get_default_config_dir(self) -> str:
        """Get the default prompt configuration directory"""
        # Get project root (where this file is app/services/enhanced_prompt_engine.py)
        current_file = Path(__file__)
        project_root = current_file.parent.parent.parent  # Go up from app/services/
        config_dir = project_root / "config" / "prompts"
        
        # Try multiple paths for different deployment environments
        possible_paths = [
            config_dir,  # Standard: /project_root/config/prompts
            current_file.parent.parent / "config" / "prompts",  # App-relative: /app/config/prompts
            Path("/app/config/prompts"),  # Absolute deployment path
            Path("/config/prompts"),  # Alternative deployment path
            Path.cwd() / "config" / "prompts",  # Current working directory
        ]
        
        for path in possible_paths:
            if path.exists() and (path / "section_discovery.yaml").exists():
                logger.info(f"Found config directory at: {path}")
                return str(path)
        
        logger.warning(f"Config directory not found in any of: {[str(p) for p in possible_paths]}")
        return str(config_dir)
    
    def _load_prompt_configurations(self) -> None:
        """Load all prompt configuration files from the config directory"""
        config_path = Path(self.config_dir)
        
        logger.info(f"Attempting to load prompt configs from: {config_path}")
        logger.info(f"Config directory exists: {config_path.exists()}")
        
        if not config_path.exists():
            logger.warning(f"Prompt config directory not found: {config_path}")
            self._create_default_prompts()
            return
            
        # Load each YAML configuration file
        config_files = [
            "section_discovery.yaml",
            "content_synthesis.yaml", 
            "validation_prompts.yaml"
        ]
        
        for config_file in config_files:
            file_path = config_path / config_file
            if file_path.exists():
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        config_data = yaml.safe_load(f)
                        self.prompts.update(config_data)
                    logger.info(f"Loaded prompt configuration: {config_file}")
                except Exception as e:
                    logger.error(f"Failed to load {config_file}: {e}")
            else:
                logger.warning(f"Prompt config file not found: {file_path}")
        
        logger.info(f"Loaded {len(self.prompts)} prompt configuration sections")
    
    def _create_default_prompts(self) -> None:
        """DISABLED: No fallback prompts - force explicit failure when config missing"""
        logger.error("CRITICAL ERROR: Prompt configuration files not found!")
        logger.error("This system requires proper YAML configuration files to operate safely.")
        logger.error("Fallback prompts are disabled to prevent hallucination and mask real issues.")
        logger.error("Fix the deployment to ensure config files are accessible at the expected path.")
        
        raise FileNotFoundError(
            f"Required prompt configuration files not found in {self.config_dir}. "
            f"Deployment must include config/prompts/*.yaml files. "
            f"Fallback prompts disabled to prevent AI hallucination and system issues."
        )
    
    def _safe_chunk_content(self, content: str, max_chars: int) -> str:
        """
        Safely chunk content without arbitrary truncation.
        
        HARDENING: If max_chars <= 0, treat as unlimited (someone forgot env var)
        
        Args:
            content: Text content to chunk
            max_chars: Maximum characters to include (0 or negative = unlimited)
            
        Returns:
            Chunked content that preserves context boundaries
        """
        # HARDENING: Treat max_chars <= 0 as unlimited
        if max_chars <= 0:
            logger.info(f"max_chars is {max_chars}, treating as unlimited (env var not set?)")
            return content
            
        if len(content) <= max_chars:
            return content
        
        # Use token-aware estimation for very large content
        estimated_tokens = len(content) / CHARS_PER_TOKEN
        if estimated_tokens > MAX_SAFE_TOKENS:
            logger.warning(f"Content too large ({estimated_tokens:.0f} estimated tokens), using intelligent chunking")
            # Use a more conservative limit to stay within context
            max_chars = min(max_chars, int(MAX_SAFE_TOKENS * CHARS_PER_TOKEN * 0.8))
        
        # If still too long, find a natural break point near the limit
        if len(content) > max_chars:
            # Look for natural break points (paragraphs, sections) near the limit
            search_start = int(max_chars * 0.7)  # Start searching at 70% of limit
            search_end = max_chars
            
            # Find the last paragraph break in the search window
            search_window = content[search_start:search_end]
            last_paragraph = search_window.rfind('\n\n')
            
            if last_paragraph != -1:
                # Found a paragraph break - use it
                chunk_end = search_start + last_paragraph
                logger.info(f"Used paragraph break for chunking at position {chunk_end}")
                return content[:chunk_end] + "\n\n[Content continues...]"
            
            # No paragraph break found, look for sentence boundaries
            last_sentence = search_window.rfind('. ')
            if last_sentence != -1:
                chunk_end = search_start + last_sentence + 1
                logger.info(f"Used sentence break for chunking at position {chunk_end}")
                return content[:chunk_end] + " [Content continues...]"
            
            # No natural break found, use the limit with a note
            logger.warning(f"No natural break found, truncating at {max_chars} characters")
            return content[:max_chars] + " [Content truncated - increase MAX_DISCOVERY_CHARS/MAX_SYNTHESIS_CHARS if needed]"
        
        return content
    
    def _multi_window_discovery(self, transcript_text: str, content_type: str = "general_analysis") -> Dict[str, Any]:
        """
        HARDENING: Break very long transcripts into 2-3 windows for discovery and merge results.
        
        This prevents hitting context limits on extremely long transcripts (>128k tokens).
        
        Args:
            transcript_text: Full transcript to analyze
            content_type: Type of content analysis
            
        Returns:
            Merged discovery results from all windows
        """
        estimated_tokens = len(transcript_text) / CHARS_PER_TOKEN
        
        # If under token limit, use single window
        if estimated_tokens <= MAX_SAFE_TOKENS * 0.8:  # 80% safety margin
            return None  # Signal to use single window
        
        logger.info(f"Very long transcript ({estimated_tokens:.0f} tokens), using multi-window discovery")
        
        # Calculate window size (aim for 3 windows max)
        num_windows = min(3, max(2, int(estimated_tokens / (MAX_SAFE_TOKENS * 0.6))))
        window_size = len(transcript_text) // num_windows
        overlap_size = int(window_size * 0.1)  # 10% overlap between windows
        
        windows = []
        merged_sections = []
        
        for i in range(num_windows):
            start_pos = i * window_size - (overlap_size if i > 0 else 0)
            end_pos = (i + 1) * window_size + (overlap_size if i < num_windows - 1 else 0)
            
            window_content = transcript_text[start_pos:min(end_pos, len(transcript_text))]
            windows.append({
                "index": i,
                "start_pos": start_pos,
                "end_pos": min(end_pos, len(transcript_text)),
                "content": window_content
            })
            
            logger.info(f"Window {i+1}/{num_windows}: chars {start_pos}-{min(end_pos, len(transcript_text))} ({len(window_content)} chars)")
        
        return {
            "use_multi_window": True,
            "windows": windows,
            "num_windows": num_windows,
            "overlap_size": overlap_size
        }
    
    def get_section_discovery_prompt(self, 
                                   transcript_text: str,
                                   content_type: str = "general_analysis") -> str:
        """
        Generate a section discovery prompt for AI-driven section identification
        
        HARDENING: Uses multi-window discovery for very long transcripts (>128k tokens)
        
        Args:
            transcript_text: The transcript content to analyze
            content_type: Type of content analysis (default: general_analysis)
            
        Returns:
            Formatted prompt for section discovery (or window-specific prompt for multi-window)
        """
        try:
            # HARDENING: Check if we need multi-window discovery
            multi_window_info = self._multi_window_discovery(transcript_text, content_type)
            
            if multi_window_info:
                # Store multi-window info for later use
                self._current_multi_window = multi_window_info
                # Return prompt for first window - caller will need to handle remaining windows
                window_content = multi_window_info["windows"][0]["content"]
                logger.info(f"Using multi-window discovery: {multi_window_info['num_windows']} windows")
                return self._generate_discovery_prompt_for_content(window_content, content_type, window_index=0, total_windows=multi_window_info['num_windows'])
            else:
                # Single window - normal processing
                self._current_multi_window = None
                return self._generate_discovery_prompt_for_content(transcript_text, content_type)
                
        except Exception as e:
            logger.error(f"Error generating section discovery prompt: {e}")
            raise RuntimeError(f"Section discovery prompt generation failed: {e}. No fallbacks available - fix the configuration issue.")
    
    def _generate_discovery_prompt_for_content(self, content: str, content_type: str, window_index: int = None, total_windows: int = None) -> str:
        """Generate discovery prompt for specific content window"""
        
        # Extract actual timestamps from transcript
        actual_timestamps = self._extract_actual_timestamps(content)
        min_timestamp = min(actual_timestamps) if actual_timestamps else 0
        max_timestamp = max(actual_timestamps) if actual_timestamps else 600  # Default 10 min
        
        # Convert to timestamp format
        min_time_str = self._seconds_to_timestamp(min_timestamp)
        max_time_str = self._seconds_to_timestamp(max_timestamp)
        duration_minutes = max_timestamp // 60
        
        # Get base prompt configuration
        if content_type not in self.prompts.get("section_discovery", {}):
            content_type = "general_analysis"
        
        base_config = self.prompts["section_discovery"][content_type]
        
        # Add timestamp validation context
        timestamp_context = f"""
TRANSCRIPT DURATION ANALYSIS:
- Actual transcript spans: {min_time_str} to {max_time_str} (approximately {duration_minutes} minutes)
- Found timestamps: {len(actual_timestamps)} timestamp markers
- Valid timestamp range: {min_time_str} - {max_time_str}

⚠️ CRITICAL TIMESTAMP CONSTRAINTS:
- You MUST ONLY use timestamps between {min_time_str} and {max_time_str}
- DO NOT create sections outside this range (e.g., don't use 60:00 if transcript ends at {max_time_str})
- Verify each timestamp exists in the content before using it
- If you cannot find specific timestamps, use relative positions within the valid range

ACTUAL TIMESTAMPS FOUND IN TRANSCRIPT:
{self._format_timestamp_list(actual_timestamps[:20])}  # Show first 20 for reference
"""
        
        # Multi-window context
        window_context = ""
        if window_index is not None and total_windows is not None:
            window_context = f"""
MULTI-WINDOW ANALYSIS:
- Processing window {window_index + 1} of {total_windows}
- Focus on content in this window while maintaining awareness of overall structure
- Coordinate with other windows to avoid duplicate sections
"""
        
        # Combine all prompt components
        full_prompt = f"""
{base_config.get('system_prompt', '')}

{timestamp_context}

{window_context}

{base_config.get('content_flow_analysis', '')}

{base_config.get('section_naming_guidelines', '')}

TRANSCRIPT CONTENT TO ANALYZE:
{content}

Remember: Generate sections with timestamps that actually exist in the above content!
"""
        
        return full_prompt
    
    def _extract_actual_timestamps(self, content: str) -> List[int]:
        """Extract all actual timestamps from transcript content and convert to seconds"""
        import re
        timestamps = []
        
        # Find all timestamp patterns (MM:SS or HH:MM:SS)
        timestamp_patterns = [
            r'\b(\d{1,2}:\d{2})\b',  # MM:SS format
            r'\b(\d{1,2}:\d{2}:\d{2})\b'  # HH:MM:SS format
        ]
        
        for pattern in timestamp_patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                seconds = self._timestamp_to_seconds(match)
                if seconds not in timestamps:  # Avoid duplicates
                    timestamps.append(seconds)
        
        return sorted(timestamps)
    
    def _timestamp_to_seconds(self, timestamp_str: str) -> int:
        """Convert timestamp string to seconds"""
        try:
            parts = timestamp_str.split(':')
            if len(parts) == 2:  # MM:SS
                return int(parts[0]) * 60 + int(parts[1])
            elif len(parts) == 3:  # HH:MM:SS
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            return 0
        except (ValueError, IndexError):
            return 0
    
    def _seconds_to_timestamp(self, seconds: int) -> str:
        """Convert seconds to MM:SS timestamp string"""
        if seconds >= 3600:  # More than 1 hour, use HH:MM:SS
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            secs = seconds % 60
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        else:  # Use MM:SS
            minutes = seconds // 60
            secs = seconds % 60
            return f"{minutes:02d}:{secs:02d}"
    
    def _format_timestamp_list(self, timestamps: List[int]) -> str:
        """Format timestamp list for display in prompts"""
        if not timestamps:
            return "No timestamps found in content"
        
        formatted = []
        for ts in timestamps:
            formatted.append(self._seconds_to_timestamp(ts))
        
        if len(formatted) <= 10:
            return ", ".join(formatted)
        else:
            return ", ".join(formatted[:10]) + f" ... (and {len(formatted) - 10} more)"
    
    def get_remaining_window_prompts(self) -> List[str]:
        """
        Get prompts for remaining windows in multi-window discovery
        
        Returns:
            List of prompts for windows 1, 2, etc. (window 0 already handled)
        """
        if not hasattr(self, '_current_multi_window') or not self._current_multi_window:
            return []
        
        remaining_prompts = []
        multi_window_info = self._current_multi_window
        
        for i in range(1, multi_window_info['num_windows']):  # Start from 1, window 0 already done
            window_content = multi_window_info["windows"][i]["content"]
            prompt = self._generate_discovery_prompt_for_content(
                window_content, 
                "general_analysis",  # Default content type
                window_index=i, 
                total_windows=multi_window_info['num_windows']
            )
            remaining_prompts.append(prompt)
        
        return remaining_prompts
    
    def merge_multi_window_results(self, window_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Merge discovery results from multiple windows into a single coherent result
        
        Args:
            window_results: List of JSON results from each window
            
        Returns:
            Merged discovery result
        """
        if not window_results:
            return {"sections": [], "analysis_notes": "No results to merge"}
        
        if len(window_results) == 1:
            return window_results[0]
        
        logger.info(f"Merging results from {len(window_results)} windows")
        
        merged_sections = []
        all_themes = set()
        analysis_notes = []
        
        # Process each window's results
        for window_idx, window_result in enumerate(window_results):
            if not isinstance(window_result, dict) or "sections" not in window_result:
                logger.warning(f"Invalid window result for window {window_idx}")
                continue
                
            window_sections = window_result.get("sections", [])
            window_notes = window_result.get("analysis_notes", "")
            
            # Add window-specific context to sections
            for section in window_sections:
                if isinstance(section, dict):
                    # Add window tracking
                    section["source_window"] = window_idx
                    
                    # Collect themes
                    themes = section.get("primary_themes", [])
                    if isinstance(themes, list):
                        all_themes.update(themes)
                    
                    merged_sections.append(section)
            
            # Collect analysis notes
            if window_notes:
                analysis_notes.append(f"Window {window_idx + 1}: {window_notes}")
        
        # Remove potential duplicates (sections that span windows)
        deduplicated_sections = self._deduplicate_cross_window_sections(merged_sections)
        
        merged_result = {
            "sections": deduplicated_sections,
            "analysis_notes": " | ".join(analysis_notes),
            "multi_window_stats": {
                "total_windows": len(window_results),
                "total_sections": len(deduplicated_sections),
                "unique_themes": list(all_themes),
                "deduplication_applied": len(merged_sections) != len(deduplicated_sections)
            }
        }
        
        logger.info(f"Multi-window merge complete: {len(deduplicated_sections)} sections from {len(window_results)} windows")
        return merged_result
    
    def _deduplicate_cross_window_sections(self, sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Remove duplicate sections that may appear across window boundaries
        
        Args:
            sections: All sections from all windows
            
        Returns:
            Deduplicated sections
        """
        if len(sections) <= 1:
            return sections
        
        deduplicated = []
        seen_content = set()
        
        for section in sections:
            if not isinstance(section, dict):
                continue
                
            # Create a signature for this section
            name = section.get("name", "").lower()
            preview = section.get("content_preview", "").lower()
            themes = str(sorted(section.get("primary_themes", []))).lower()
            
            # Simple similarity check - could be enhanced with more sophisticated matching
            content_signature = f"{name[:50]}|{preview[:100]}|{themes}"
            
            # Check for similar existing sections
            is_duplicate = False
            for seen_sig in seen_content:
                if self._sections_are_similar(content_signature, seen_sig):
                    is_duplicate = True
                    logger.debug(f"Detected duplicate section: {name[:30]}...")
                    break
            
            if not is_duplicate:
                seen_content.add(content_signature)
                deduplicated.append(section)
        
        return deduplicated
    
    def _sections_are_similar(self, sig1: str, sig2: str) -> bool:
        """
        Check if two section signatures are similar enough to be considered duplicates
        
        Args:
            sig1, sig2: Content signatures to compare
            
        Returns:
            True if sections are likely duplicates
        """
        # Split signatures and compare components
        parts1 = sig1.split("|")
        parts2 = sig2.split("|")
        
        if len(parts1) != 3 or len(parts2) != 3:
            return False
        
        # Compare name similarity (simple character overlap)
        name_similarity = len(set(parts1[0]) & set(parts2[0])) / max(len(set(parts1[0])), len(set(parts2[0])), 1)
        
        # Compare theme similarity
        theme_similarity = 1.0 if parts1[2] == parts2[2] else 0.0
        
        # Consider duplicate if high name similarity OR identical themes
        return name_similarity > 0.7 or theme_similarity > 0.8
    
    def get_synthesis_prompt(self, 
                           section_content: str,
                           section_name: str,
                           context: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate a content synthesis prompt for detailed section content creation
        
        Args:
            section_content: The content within the specific section
            section_name: Name/title of the section
            context: Optional additional context (adjacent sections, themes, etc.)
            
        Returns:
            Formatted prompt for content synthesis
        """
        try:
            base_prompt = self.prompts.get("content_synthesis", {}).get("section_content_generation", {}).get("system_prompt", "")
            extraction_guidelines = self.prompts.get("content_synthesis", {}).get("section_content_generation", {}).get("detailed_extraction_guidelines", "")
            
            context_info = ""
            if context:
                context_info = f"""
ADDITIONAL CONTEXT:
- Previous sections: {context.get('previous_sections', [])}
- Discussion themes: {context.get('themes', [])}
- Key participants: {context.get('speakers', [])}
"""
            
            prompt = f"""
{base_prompt}

{extraction_guidelines}

SECTION TO SYNTHESIZE: {section_name}

{context_info}

SECTION CONTENT:
{self._safe_chunk_content(section_content, MAX_SYNTHESIS_CHARS)}  # Configurable limit with intelligent chunking

🚨 CRITICAL ANTI-HALLUCINATION REQUIREMENTS:
1. Extract ONLY numbers, targets, levels, and dates that are EXPLICITLY stated in the section content above
2. If specific financial data is not mentioned in the content, write "information not specified" instead
3. Do NOT fabricate, estimate, or add ANY financial numbers not directly stated in the source
4. Preserve exact asset symbols and references ONLY if mentioned in the content
5. Maintain chronological flow of discussion as presented in the source
6. Include actionable insights ONLY based on what's explicitly discussed
7. Preserve speaker context and reasoning ONLY from the provided content
8. Format for professional readability without adding fabricated details

🚨 ABSOLUTE PROHIBITION: Do not generate specific prices, levels, or targets unless they are explicitly mentioned in the section content above. When financial data is not specified, state that clearly rather than creating placeholder numbers.

Return a comprehensive summary that maintains all critical details from the source while improving readability and flow, but adds NO fabricated financial information.
"""
            
            return prompt.strip()
            
        except Exception as e:
            logger.error(f"Error generating synthesis prompt: {e}")
            raise RuntimeError(f"Synthesis prompt generation failed: {e}. No fallbacks available - fix the configuration issue.")
    
    def get_validation_prompt(self, 
                            generated_sections: List[Dict[str, Any]],
                            original_transcript: str) -> str:
        """
        Generate a validation prompt for quality assurance of generated sections
        
        Args:
            generated_sections: List of generated sections with content
            original_transcript: Original transcript for accuracy verification
            
        Returns:
            Formatted prompt for validation
        """
        try:
            validation_prompt = self.prompts.get("validation_prompts", {}).get("section_validation", {}).get("section_quality_assessment", "")
            
            sections_summary = []
            for i, section in enumerate(generated_sections[:5]):  # Limit for context
                sections_summary.append(f"""
Section {i+1}: {section.get('name', 'Unnamed')}
Content Length: {len(section.get('content', ''))} characters
Key Themes: {section.get('themes', [])}
""")
            
            prompt = f"""
{validation_prompt}

GENERATED SECTIONS TO VALIDATE:
{chr(10).join(sections_summary)}

ORIGINAL TRANSCRIPT SAMPLE (for accuracy verification):
{original_transcript[:4000]}...

VALIDATION TASKS:
1. Verify section names are specific and content-driven
2. Check that all important information is captured
3. Ensure no critical numbers or details are missing
4. Validate temporal boundaries and section flow
5. Assess overall quality vs. baseline bucketing approach

Please return your validation results as a properly formatted JSON object with:
{{
  "overall_quality_score": 8.5,
  "section_evaluations": [
    {{
      "section_name": "...",
      "quality_score": 9.0,
      "strengths": ["specific improvements noted"],
      "issues": ["specific problems if any"],
      "recommendations": ["specific suggestions"]
    }}
  ],
  "improvement_suggestions": "Overall recommendations for enhancement"
}}
"""
            
            return prompt.strip()
            
        except Exception as e:
            logger.error(f"Error generating validation prompt: {e}")
            raise RuntimeError(f"Validation prompt generation failed: {e}. No fallbacks available - fix the configuration issue.")
    
    def get_content_flow_analysis_prompt(self, transcript_text: str) -> str:
        """
        Generate prompt for analyzing content flow and topic transitions
        
        Args:
            transcript_text: Full transcript to analyze
            
        Returns:
            Formatted prompt for content flow analysis
        """
        try:
            flow_analysis = self.prompts.get("section_discovery", {}).get("temporal_boundary_detection", {})
            system_prompt = flow_analysis.get("system_prompt", "")
            boundary_markers = flow_analysis.get("boundary_markers", "")
            
            prompt = f"""
{system_prompt}

{boundary_markers}

TRANSCRIPT FOR FLOW ANALYSIS:
{self._safe_chunk_content(transcript_text, MAX_DISCOVERY_CHARS)}

ANALYSIS OBJECTIVES:
1. Identify natural topic transition points
2. Detect speaker changes or presentation style shifts  
3. Find temporal markers and time-based progression
4. Recognize content density changes
5. Map thematic coherence within segments

Please return your content flow analysis as a properly formatted JSON object with:
{{
  "topic_transitions": [
    {{
      "timestamp": "05:30",
      "from_topic": "market overview",
      "to_topic": "sector analysis", 
      "transition_strength": 0.8,
      "boundary_markers": ["moving on to", "let's look at"]
    }}
  ],
  "content_density_map": [
    {{
      "time_range": "00:00-05:30",
      "density_score": 0.7,
      "primary_themes": ["market analysis", "index levels"]
    }}
  ],
  "natural_boundaries": ["05:30", "12:15", "18:45"]
}}
"""
            
            return prompt.strip()
            
        except Exception as e:
            logger.error(f"Error generating content flow analysis prompt: {e}")
            return "Analyze the transcript content for natural topic transitions and discussion boundaries."
    
    # FALLBACK METHODS REMOVED: No fallbacks allowed - system must fail explicitly when config missing
    
    def reload_configurations(self) -> None:
        """Reload prompt configurations from files (useful for development/testing)"""
        logger.info("Reloading prompt configurations")
        self.prompts.clear()
        self._load_prompt_configurations()
    
    def get_available_prompt_types(self) -> Dict[str, List[str]]:
        """
        Get a summary of available prompt types and configurations
        
        Returns:
            Dictionary mapping category to available prompt types
        """
        available = {}
        for category, category_data in self.prompts.items():
            if isinstance(category_data, dict):
                available[category] = list(category_data.keys())
        return available
    
    def validate_configuration(self) -> Dict[str, Any]:
        """
        Validate that all required prompt configurations are loaded
        
        Returns:
            Validation report with missing configurations and recommendations
        """
        required_configs = [
            "section_discovery.general_analysis.system_prompt",
            "content_synthesis.section_content_generation.system_prompt", 
            "validation_prompts.section_validation.section_quality_assessment"
        ]
        
        validation_report = {
            "is_valid": True,
            "missing_configs": [],
            "loaded_configs": [],
            "recommendations": []
        }
        
        for config_path in required_configs:
            keys = config_path.split('.')
            current = self.prompts
            
            try:
                for key in keys:
                    current = current[key]
                validation_report["loaded_configs"].append(config_path)
            except (KeyError, TypeError):
                validation_report["missing_configs"].append(config_path)
                validation_report["is_valid"] = False
        
        if not validation_report["is_valid"]:
            validation_report["recommendations"].append("Check prompt configuration files in config/prompts/")
            validation_report["recommendations"].append("Ensure YAML files are properly formatted")
            validation_report["recommendations"].append("Verify file permissions and accessibility")
        
        return validation_report 