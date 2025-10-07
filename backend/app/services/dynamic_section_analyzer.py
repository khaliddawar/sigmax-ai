"""
Dynamic Section Analyzer for AI-Driven Section Discovery

This module provides the core AI-driven section discovery engine that replaces
rigid bucketing with sophisticated analysis of content flow and natural discussion
boundaries in financial transcripts.
"""

import os
import logging
import json
import openai
import re
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from .enhanced_prompt_engine import EnhancedPromptEngine

logger = logging.getLogger("dynamic-section-analyzer")


class ContentFlowAnalysis:
    """Analyzes transcript content for natural flow patterns and topic transitions"""
    
    @staticmethod
    def identify_topic_transitions(transcript_text: str) -> List[Dict[str, Any]]:
        """Identify points where the discussion topic changes significantly"""
        transitions = []
        
        # Common transition phrases in financial discussions
        transition_patterns = [
            r"(?i)(moving\s+(?:on\s+)?to|let'?s\s+(?:talk\s+about|look\s+at|move\s+to))",
            r"(?i)(now\s+(?:let'?s|we'?ll)|next\s+(?:up|we'?ll\s+discuss))",
            r"(?i)(another\s+(?:area|opportunity|sector|topic))",
            r"(?i)(shifting\s+(?:focus\s+)?to|turning\s+to)",
        ]
        
        lines = transcript_text.split('\n')
        
        for i, line in enumerate(lines):
            for pattern in transition_patterns:
                matches = re.finditer(pattern, line)
                for match in matches:
                    transitions.append({
                        "line_number": i,
                        "match_text": match.group(),
                        "context": line.strip(),
                        "confidence": 0.7,
                        "transition_type": "phrase_pattern"
                    })
        
        return transitions
    
    @staticmethod
    def detect_temporal_markers(transcript_text: str) -> List[Dict[str, Any]]:
        """Detect time-based markers that indicate progression through content"""
        temporal_markers = []
        
        # Time reference patterns
        time_patterns = [
            r"(?i)(\d{1,2}:\d{2}(?::\d{2})?)",
            r"(?i)(earlier\s+(?:today|this\s+week))",
            r"(?i)(next\s+(?:week|month|quarter))",
            r"(?i)(looking\s+ahead|going\s+forward)",
        ]
        
        lines = transcript_text.split('\n')
        
        for i, line in enumerate(lines):
            for pattern in time_patterns:
                matches = re.finditer(pattern, line)
                for match in matches:
                    temporal_markers.append({
                        "line_number": i,
                        "marker_text": match.group(),
                        "marker_type": "temporal_reference",
                        "context": line.strip(),
                        "confidence": 0.6
                    })
        
        return temporal_markers


class DynamicSectionAnalyzer:
    """AI-driven section discovery engine that identifies natural discussion segments"""
    
    def __init__(self):
        """Initialize the Dynamic Section Analyzer"""
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model = os.getenv("SUMMARY_MODEL", "gpt-4o-mini")
        
        # Initialize the enhanced prompt engine
        self.prompt_engine = EnhancedPromptEngine()
        
        if self.api_key:
            self.client = openai.AsyncClient(api_key=self.api_key)
            self.initialized = True
            logger.info(f"Dynamic Section Analyzer initialized with model: {self.model}")
        else:
            logger.error("OpenAI API key not found - Dynamic Section Analyzer cannot function")
            raise RuntimeError("OpenAI API key required for section discovery - no fallback mode allowed")
    
    async def analyze_transcript_structure(self, transcript_text: str) -> Dict[str, Any]:
        """Analyze transcript structure to understand content flow and natural boundaries"""
        try:
            logger.info(f"Analyzing transcript structure for {len(transcript_text)} characters")
            
            # Step 1: Basic structural analysis
            topic_transitions = ContentFlowAnalysis.identify_topic_transitions(transcript_text)
            temporal_markers = ContentFlowAnalysis.detect_temporal_markers(transcript_text)
            
            # Step 2: AI-powered content flow analysis
            ai_flow_analysis = await self._get_ai_flow_analysis(transcript_text)
            
            # Step 3: Combine analyses
            structure_analysis = {
                "transcript_length": len(transcript_text),
                "estimated_lines": len(transcript_text.split('\n')),
                "topic_transitions": topic_transitions,
                "temporal_markers": temporal_markers,
                "ai_flow_analysis": ai_flow_analysis,
                "natural_boundaries": self._identify_natural_boundaries(topic_transitions, temporal_markers),
                "analysis_timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"Structure analysis complete: {len(topic_transitions)} transitions, "
                       f"{len(temporal_markers)} temporal markers")
            
            return structure_analysis
            
        except Exception as e:
            logger.error(f"Error in transcript structure analysis: {e}")
            raise RuntimeError(f"Transcript structure analysis failed: {e}. No fallback available - fix the underlying issue.")
    
    async def discover_sections(self, transcript_text: str, 
                              structure_analysis: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Discover natural sections within the transcript using AI-driven analysis
        
        HARDENING: Supports multi-window discovery for very long transcripts (>128k tokens)
        """
        try:
            logger.info("Starting AI-driven section discovery")
            
            # Use provided analysis or generate new one
            if structure_analysis is None:
                structure_analysis = await self.analyze_transcript_structure(transcript_text)
            
            # HARDENING: Check if we need multi-window discovery
            estimated_tokens = len(transcript_text) / 3.5  # Rough estimation
            if estimated_tokens > 25600:  # 32K tokens * 0.8 safety margin
                logger.info(f"Large transcript ({estimated_tokens:.0f} tokens), using multi-window discovery")
                return await self._multi_window_section_discovery(transcript_text, structure_analysis)
            
            # Single window discovery (original logic)
            return await self._single_window_section_discovery(transcript_text, structure_analysis)
            
        except Exception as e:
            logger.error(f"Error in section discovery: {e}")
            raise RuntimeError(f"Section discovery failed: {e}. No fallback available - fix the underlying issue.")
    
    async def _single_window_section_discovery(self, transcript_text: str, 
                                             structure_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Original single-window section discovery logic"""
        try:
            # Generate section discovery prompt
            discovery_prompt = self.prompt_engine.get_section_discovery_prompt(transcript_text)
            
            if not self.client:
                raise RuntimeError("Section discovery requires AI client - no mock mode allowed")
            
            # AI-powered section discovery
            chat_params = {
                "model": self.model,
                "messages": [{"role": "system", "content": discovery_prompt}],
                "temperature": 0.3,
                "max_tokens": 3000
            }
            
            # Add JSON response format if supported
            if self.model in ["gpt-4", "gpt-4-turbo", "gpt-4o", "gpt-4o-mini"]:
                chat_params["response_format"] = {"type": "json_object"}
            
            response = await self.client.chat.completions.create(**chat_params)
            
            # Parse AI response
            response_content = response.choices[0].message.content
            
            try:
                ai_sections = json.loads(response_content)
            except json.JSONDecodeError:
                logger.warning("Failed to parse AI response as JSON, using fallback parsing")
                ai_sections = self._parse_non_json_response(response_content)
            
            # Process and validate discovered sections
            discovered_sections = self._process_discovered_sections(
                ai_sections, transcript_text, structure_analysis
            )
            
            logger.info(f"Discovered {len(discovered_sections)} natural sections")
            return discovered_sections
            
        except Exception as e:
            logger.error(f"Single window section discovery failed: {e}")
            raise
    
    async def _multi_window_section_discovery(self, transcript_text: str, 
                                            structure_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        HARDENING: Multi-window section discovery for very long transcripts
        Breaks transcript into windows, discovers sections in each, then merges results
        """
        try:
            logger.info("Starting multi-window section discovery")
            
            # Get first window prompt (this also sets up the multi-window info)
            first_window_prompt = self.prompt_engine.get_section_discovery_prompt(transcript_text)
            
            # Get remaining window prompts
            remaining_prompts = self.prompt_engine.get_remaining_window_prompts()
            
            # Combine all prompts
            all_prompts = [first_window_prompt] + remaining_prompts
            
            if not all_prompts:
                logger.warning("No multi-window prompts generated, falling back to single window")
                return await self._single_window_section_discovery(transcript_text, structure_analysis)
            
            logger.info(f"Processing {len(all_prompts)} windows for section discovery")
            
            # Process each window
            window_results = []
            for i, prompt in enumerate(all_prompts):
                logger.info(f"Processing window {i+1}/{len(all_prompts)}")
                
                chat_params = {
                    "model": self.model,
                    "messages": [{"role": "system", "content": prompt}],
                    "temperature": 0.3,
                    "max_tokens": 3000
                }
                
                if self.model in ["gpt-4", "gpt-4-turbo", "gpt-4o", "gpt-4o-mini"]:
                    chat_params["response_format"] = {"type": "json_object"}
                
                response = await self.client.chat.completions.create(**chat_params)
                response_content = response.choices[0].message.content
                
                try:
                    window_result = json.loads(response_content)
                    window_results.append(window_result)
                    logger.info(f"Window {i+1} processed successfully: {len(window_result.get('sections', []))} sections")
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse window {i+1} response as JSON, using fallback")
                    fallback_result = self._parse_non_json_response(response_content)
                    fallback_result["window_index"] = i
                    window_results.append(fallback_result)
            
            # Merge results from all windows
            if window_results:
                merged_result = self.prompt_engine.merge_multi_window_results(window_results)
                
                # Process the merged sections
                discovered_sections = self._process_discovered_sections(
                    merged_result, transcript_text, structure_analysis
                )
                
                logger.info(f"Multi-window discovery complete: {len(discovered_sections)} total sections from {len(window_results)} windows")
                return discovered_sections
            else:
                logger.error("No valid window results obtained")
                raise RuntimeError("Multi-window discovery failed - no valid results from any window")
                
        except Exception as e:
            logger.error(f"Multi-window section discovery failed: {e}")
            # Attempt fallback to single window with reduced content
            logger.warning("Attempting fallback to single window with truncated content")
            truncated_content = transcript_text[:100000]  # Use first 100K chars as fallback
            return await self._single_window_section_discovery(truncated_content, structure_analysis)
    
    def extract_temporal_markers(self, transcript_text: str) -> List[Dict[str, Any]]:
        """Extract temporal markers to identify time-based discussion progression"""
        try:
            temporal_markers = ContentFlowAnalysis.detect_temporal_markers(transcript_text)
            
            # Enhance markers with additional context
            enhanced_markers = []
            lines = transcript_text.split('\n')
            
            for marker in temporal_markers:
                line_num = marker["line_number"]
                
                enhanced_marker = {
                    **marker,
                    "relative_position": line_num / len(lines),
                    "surrounding_context": lines[max(0, line_num-1):min(len(lines), line_num+2)]
                }
                
                enhanced_markers.append(enhanced_marker)
            
            logger.info(f"Extracted {len(enhanced_markers)} temporal markers")
            return enhanced_markers
            
        except Exception as e:
            logger.error(f"Error extracting temporal markers: {e}")
            return []
    
    async def _get_ai_flow_analysis(self, transcript_text: str) -> Dict[str, Any]:
        """Get AI-powered content flow analysis"""
        try:
            if not self.client:
                raise RuntimeError("Flow analysis requires AI client - no mock mode allowed")
            
            flow_prompt = self.prompt_engine.get_content_flow_analysis_prompt(transcript_text)
            
            chat_params = {
                "model": self.model,
                "messages": [{"role": "system", "content": flow_prompt}],
                "temperature": 0.2,
                "max_tokens": 2000
            }
            
            if self.model in ["gpt-4", "gpt-4-turbo", "gpt-4o", "gpt-4o-mini"]:
                chat_params["response_format"] = {"type": "json_object"}
            
            response = await self.client.chat.completions.create(**chat_params)
            
            try:
                return json.loads(response.choices[0].message.content)
            except json.JSONDecodeError:
                raise RuntimeError("Failed to parse AI flow analysis response - check API response format")
                
        except Exception as e:
            logger.error(f"Error in AI flow analysis: {e}")
            raise RuntimeError(f"AI flow analysis failed: {e}. No fallback available - fix the underlying issue.")
    
    def _identify_natural_boundaries(self, topic_transitions: List[Dict[str, Any]],
                                   temporal_markers: List[Dict[str, Any]]) -> List[str]:
        """Identify natural section boundaries from analysis components"""
        boundaries = set()
        
        # Add boundaries from strong topic transitions
        for transition in topic_transitions:
            if transition.get("confidence", 0) > 0.7:
                boundaries.add(f"line_{transition['line_number']}")
        
        # Add boundaries from temporal markers
        for marker in temporal_markers:
            if marker.get("confidence", 0) > 0.6:
                boundaries.add(f"line_{marker['line_number']}")
        
        return sorted(list(boundaries))
    
    def _process_discovered_sections(self, ai_sections: Dict[str, Any],
                                   transcript_text: str,
                                   structure_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Process and validate AI-discovered sections with robust anti-fabrication measures
        """
        try:
            # Extract sections from AI response
            sections_list = ai_sections.get("sections", [])
            if not sections_list:
                logger.warning("No sections found in AI response")
                return []
            
            # CRITICAL: Validate section count against content length
            transcript_duration = self._estimate_transcript_duration(transcript_text)
            max_reasonable_sections = self._calculate_max_sections(transcript_duration)
            
            if len(sections_list) > max_reasonable_sections:
                logger.warning(f"🚨 AI OVER-SEGMENTATION: Generated {len(sections_list)} sections for {transcript_duration}-minute content")
                logger.warning(f"   Maximum reasonable sections: {max_reasonable_sections}")
                logger.warning("   Truncating to prevent content fabrication...")
                sections_list = sections_list[:max_reasonable_sections]
            
            processed_sections = []
            
            for i, section in enumerate(sections_list):
                # Extract section information
                section_name = section.get("name", f"Section {i+1}")
                start_time = section.get("start_time", "00:00")
                end_time = section.get("end_time", "99:99")
                description = section.get("description", "")
                
                # ANTI-FABRICATION: Validate timestamps against actual content
                if not self._validate_section_timestamps(start_time, end_time, transcript_text):
                    logger.error(f"❌ REJECTING SECTION: '{section_name}' has invalid timestamps {start_time}-{end_time}")
                    continue
                
                # CONTENT VALIDATION: Check if section has enough source material
                content_density = self._check_content_density(start_time, end_time, transcript_text)
                if content_density < 0.1:  # Less than 10% content density indicates potential fabrication
                    logger.warning(f"⚠️ LOW CONTENT DENSITY: '{section_name}' may lead to fabrication (density: {content_density:.2f})")
                
                processed_section = {
                    "name": section_name,
                    "start_time": start_time,
                    "end_time": end_time,
                    "description": description,
                    "content_density": content_density,
                    "validation_status": "validated",
                    "section_index": i
                }
                
                processed_sections.append(processed_section)
                logger.info(f"✅ Section validated: '{section_name}' ({start_time}-{end_time}) density: {content_density:.2f}")
            
            # Final validation: Ensure we have reasonable section distribution
            if processed_sections:
                logger.info(f"Section processing complete: {len(processed_sections)} valid sections from {len(sections_list)} proposed")
                self._log_section_summary(processed_sections, transcript_duration)
            else:
                logger.error("🚨 NO VALID SECTIONS: All proposed sections failed validation")
                # Create minimal fallback section instead of fabricating
                processed_sections = [{
                    "name": "Discussion Summary",
                    "start_time": "00:00",
                    "end_time": self._get_last_timestamp(transcript_text) or "10:00",
                    "description": "Complete discussion content",
                    "content_density": 1.0,
                    "validation_status": "fallback",
                    "section_index": 0
                }]
                logger.info("Created single fallback section to prevent fabrication")
        
            return processed_sections
    
        except Exception as e:
            logger.error(f"Error processing discovered sections: {e}")
            # Create safe fallback that prevents fabrication
            return [{
                "name": "Complete Discussion",
                "start_time": "00:00", 
                "end_time": self._get_last_timestamp(transcript_text) or "10:00",
                "description": "Complete transcript content",
                "content_density": 1.0,
                "validation_status": "error_fallback",
                "section_index": 0
            }]
    
    def _estimate_transcript_duration(self, transcript_text: str) -> int:
        """Estimate transcript duration in minutes"""
        # Method 1: Extract timestamps if available
        timestamps = re.findall(r'(\d{1,2}):(\d{2})(?::(\d{2}))?', transcript_text)
        if timestamps:
            max_time = 0
            for ts in timestamps:
                hours, minutes, seconds = int(ts[0]), int(ts[1]), int(ts[2] or 0)
                total_seconds = hours * 3600 + minutes * 60 + seconds
                max_time = max(max_time, total_seconds)
            return max_time // 60 if max_time > 0 else 5
        
        # Method 2: Estimate from character count (rough: ~1000 chars per minute of speech)
        estimated_minutes = len(transcript_text) // 1000
        return max(1, min(estimated_minutes, 180))  # Clamp between 1-180 minutes
    
    def _calculate_max_sections(self, duration_minutes: int) -> int:
        """Calculate maximum reasonable sections based on duration"""
        if duration_minutes <= 5:
            return 1
        elif duration_minutes <= 10:
            return 2
        elif duration_minutes <= 15:
            return 3
        elif duration_minutes <= 30:
            return 4
        elif duration_minutes <= 45:
            return 5
        else:
            return 6
    
    def _validate_section_timestamps(self, start_time: str, end_time: str, transcript_text: str) -> bool:
        """Validate that section timestamps exist in the actual transcript"""
        # Extract all actual timestamps from transcript
        actual_timestamps = set()
        for line in transcript_text.split('\n'):
            timestamps = re.findall(r'(\d{1,2}:\d{2}(?::\d{2})?)', line)
            actual_timestamps.update(timestamps)
        
        # Convert section times to comparable format
        def normalize_timestamp(ts):
            parts = ts.split(':')
            if len(parts) == 2:
                return f"{parts[0]}:{parts[1]}"
            return ts
        
        norm_start = normalize_timestamp(start_time)
        norm_end = normalize_timestamp(end_time)
        
        # Check if timestamps exist or are reasonable
        if actual_timestamps:
            # Allow some flexibility for AI-generated boundaries
            return any(norm_start <= ts <= norm_end or abs(self._time_to_seconds(norm_start) - self._time_to_seconds(ts)) < 120 
                      for ts in actual_timestamps)
        
        # If no timestamps in transcript, allow reasonable ranges only
        start_seconds = self._time_to_seconds(start_time)
        end_seconds = self._time_to_seconds(end_time)
        return 0 <= start_seconds < end_seconds <= 3600  # Max 1 hour
    
    def _check_content_density(self, start_time: str, end_time: str, transcript_text: str) -> float:
        """Check content density for a time range to detect potential fabrication"""
        start_seconds = self._time_to_seconds(start_time)
        end_seconds = self._time_to_seconds(end_time)
        
        # Extract lines within the time range
        lines_in_range = 0
        total_lines = 0
        
        for line in transcript_text.split('\n'):
            total_lines += 1
            timestamps = re.findall(r'(\d{1,2}):(\d{2})(?::(\d{2}))?', line)
            for ts in timestamps:
                hours, minutes, seconds = int(ts[0]), int(ts[1]), int(ts[2] or 0)
                line_seconds = hours * 3600 + minutes * 60 + seconds
                if start_seconds <= line_seconds <= end_seconds:
                    lines_in_range += 1
                    break
        
        return lines_in_range / max(total_lines, 1)
    
    def _time_to_seconds(self, time_str: str) -> int:
        """Convert time string to seconds"""
        try:
            parts = time_str.split(':')
            if len(parts) == 2:
                return int(parts[0]) * 60 + int(parts[1])
            elif len(parts) == 3:
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            return 0
        except (ValueError, IndexError):
            return 0
    
    def _get_last_timestamp(self, transcript_text: str) -> Optional[str]:
        """Get the last timestamp from the transcript"""
        timestamps = re.findall(r'(\d{1,2}:\d{2}(?::\d{2})?)', transcript_text)
        return timestamps[-1] if timestamps else None
    
    def _log_section_summary(self, sections: List[Dict[str, Any]], duration: int):
        """Log summary of section validation results"""
        logger.info(f"📊 SECTION VALIDATION SUMMARY:")
        logger.info(f"   • Transcript duration: {duration} minutes")
        logger.info(f"   • Valid sections: {len(sections)}")
        logger.info(f"   • Average section length: {duration // len(sections)} minutes")
        
        for section in sections:
            density = section.get('content_density', 0)
            status = '✅' if density > 0.1 else '⚠️'
            logger.info(f"   {status} {section['name']}: {section['start_time']}-{section['end_time']} (density: {density:.2f})")
    
    def _parse_non_json_response(self, response_content: str) -> Dict[str, Any]:
        """Parse non-JSON AI response into structured format"""
        return {
            "sections": [
                {
                    "name": "📋 Parsed Content Section",
                    "content_preview": response_content[:200] + "...",
                    "confidence": 0.3,
                    "parsing_method": "non_json_fallback"
                }
            ],
            "analysis_notes": "Parsed from non-JSON AI response"
        } 