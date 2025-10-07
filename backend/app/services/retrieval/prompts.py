"""Prompt Engineering Module

Handles prompt generation, templates, and optimization for QA responses.
Extracted from the monolithic retrieval_qa_service.py for better maintainability.

Key responsibilities:
- Prompt template management
- Dynamic prompt generation
- Context-aware prompt optimization
- Domain-specific prompt adaptation
"""
from __future__ import annotations

import logging
import re
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger("retrieval-prompts")


class PromptType(Enum):
    """Types of prompts for different use cases."""
    FACTUAL = "factual"
    COMPARATIVE = "comparative"
    NUMERIC = "numeric"
    ANALYTICAL = "analytical"
    CREATIVE = "creative"


@dataclass
class PromptTemplate:
    """Template for generating prompts."""
    system_prompt: str
    user_prompt: str
    response_format: str
    validation_rules: Dict[str, Any]
    metadata: Dict[str, Any]


@dataclass
class PromptResult:
    """Result of prompt generation."""
    system_prompt: str
    user_prompt: str
    response_format: str
    prompt_type: PromptType
    metadata: Dict[str, Any]


class PromptTemplateManager:
    """Manages prompt templates for different scenarios."""
    
    def __init__(self):
        self.templates: Dict[PromptType, PromptTemplate] = {}
        self._initialize_default_templates()
    
    def _initialize_default_templates(self):
        """Initialize default prompt templates."""
        
        # Base system prompt
        base_system = (
            "You are a helpful AI assistant that answers questions based on provided context. "
            "Always cite your sources using {{source}} notation and be factual. "
            "If you cannot answer based on the context, say so clearly."
        )
        
        # Factual questions template
        self.templates[PromptType.FACTUAL] = PromptTemplate(
            system_prompt=base_system,
            user_prompt=(
                "Context:\n{context}\n\n"
                "Question: {question}\n\n"
                "Please provide a factual answer based only on the information in the context above. "
                "Use {{source}} notation to cite relevant parts of the context."
            ),
            response_format=(
                "Structure your response as follows:\n"
                "- Direct answer to the question\n"
                "- Supporting evidence from context with {{citations}}\n"
                "- Any limitations or uncertainties"
            ),
            validation_rules={"evidence_required": True, "numeric_check": False},
            metadata={"type": "factual", "strict_grounding": True}
        )
        
        # Comparative questions template
        self.templates[PromptType.COMPARATIVE] = PromptTemplate(
            system_prompt=base_system + " Pay special attention to making fair comparisons.",
            user_prompt=(
                "Context:\n{context}\n\n"
                "Question: {question}\n\n"
                "This appears to be a comparative question. Please provide a balanced comparison "
                "based on the information in the context. Use {{source}} notation for citations."
            ),
            response_format=(
                "Structure your comparison as follows:\n"
                "- Overview of what is being compared\n"
                "- Key similarities with {{citations}}\n"
                "- Key differences with {{citations}}\n"
                "- Conclusion based on the evidence"
            ),
            validation_rules={"evidence_required": True, "balance_check": True},
            metadata={"type": "comparative", "requires_balance": True}
        )
        
        # Numeric questions template  
        self.templates[PromptType.NUMERIC] = PromptTemplate(
            system_prompt=base_system + " Be especially careful with numbers and calculations.",
            user_prompt=(
                "Context:\n{context}\n\n"
                "Question: {question}\n\n"
                "This question involves numbers or quantities. Please provide specific numeric "
                "information from the context and cite your sources with {{source}} notation. "
                "Only use numbers that are explicitly mentioned in the context."
            ),
            response_format=(
                "Structure your response as follows:\n"
                "- Direct numeric answer with {{citations}}\n"
                "- Context and explanation of the numbers\n"
                "- Any calculations or relationships\n"
                "- Limitations or caveats about the data"
            ),
            validation_rules={"evidence_required": True, "numeric_check": True},
            metadata={"type": "numeric", "strict_numbers": True}
        )
        
        # Analytical questions template
        self.templates[PromptType.ANALYTICAL] = PromptTemplate(
            system_prompt=base_system + " Provide thoughtful analysis while staying grounded in the context.",
            user_prompt=(
                "Context:\n{context}\n\n"
                "Question: {question}\n\n"
                "This question requires analysis. Please analyze the information in the context "
                "and provide insights while clearly citing your sources with {{source}} notation."
            ),
            response_format=(
                "Structure your analysis as follows:\n"
                "- Key findings from the context with {{citations}}\n"
                "- Analysis and interpretation\n"
                "- Implications or conclusions\n"
                "- Limitations of the analysis"
            ),
            validation_rules={"evidence_required": True, "reasoning_check": True},
            metadata={"type": "analytical", "requires_reasoning": True}
        )
    
    def get_template(self, prompt_type: PromptType) -> PromptTemplate:
        """Get template by type."""
        return self.templates.get(prompt_type, self.templates[PromptType.FACTUAL])
    
    def add_custom_template(self, prompt_type: PromptType, template: PromptTemplate):
        """Add custom template."""
        self.templates[prompt_type] = template
        logger.info(f"Added custom template for {prompt_type.value}")


class PromptClassifier:
    """Classifies questions to determine appropriate prompt type."""
    
    def __init__(self):
        self.classification_patterns = {
            PromptType.COMPARATIVE: [
                r'\b(compare|comparison|versus|vs\.?|difference|similar|different)\b',
                r'\b(better|worse|more|less|higher|lower)\s+than\b',
                r'\b(which\s+is|what\s+are\s+the\s+differences)\b'
            ],
            PromptType.NUMERIC: [
                r'\b(how\s+much|how\s+many|what\s+percentage|what\s+number)\b',
                r'\b(cost|price|amount|quantity|rate|percentage|%)\b',
                r'\b\d+\b',  # Contains numbers
                r'\b(calculate|count|sum|total|average)\b'
            ],
            PromptType.ANALYTICAL: [
                r'\b(why|how|analyze|explain|interpret|understand)\b',
                r'\b(what\s+does\s+this\s+mean|what\s+are\s+the\s+implications)\b',
                r'\b(trend|pattern|relationship|correlation)\b'
            ]
        }
    
    def classify(self, question: str) -> PromptType:
        """Classify question to determine prompt type."""
        question_lower = question.lower()
        
        # Score each type based on pattern matches
        scores = {prompt_type: 0 for prompt_type in PromptType}
        
        for prompt_type, patterns in self.classification_patterns.items():
            for pattern in patterns:
                matches = len(re.findall(pattern, question_lower))
                scores[prompt_type] += matches
        
        # Return type with highest score, default to factual
        best_type = max(scores.items(), key=lambda x: x[1])
        
        if best_type[1] > 0:
            logger.debug(f"Classified question as {best_type[0].value} (score: {best_type[1]})")
            return best_type[0]
        
        logger.debug("Classified question as factual (default)")
        return PromptType.FACTUAL


class PromptGenerator:
    """Generates optimized prompts for QA scenarios."""
    
    def __init__(self):
        self.template_manager = PromptTemplateManager()
        self.classifier = PromptClassifier()
        self.context_optimizer = ContextOptimizer()
    
    async def generate_prompt(
        self,
        question: str,
        context: str,
        prompt_type: Optional[PromptType] = None,
        domain: Optional[str] = None,
        max_context_length: int = 12000
    ) -> PromptResult:
        """Generate optimized prompt for question and context."""
        
        try:
            # Classify question if type not provided
            if prompt_type is None:
                prompt_type = self.classifier.classify(question)
            
            # Get appropriate template
            template = self.template_manager.get_template(prompt_type)
            
            # Optimize context if needed
            optimized_context = await self.context_optimizer.optimize_context(
                context, question, max_context_length
            )
            
            # Apply domain-specific customizations
            if domain:
                template = self._apply_domain_customizations(template, domain)
            
            # Generate prompts
            system_prompt = template.system_prompt
            user_prompt = template.user_prompt.format(
                context=optimized_context,
                question=question
            )
            
            return PromptResult(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_format=template.response_format,
                prompt_type=prompt_type,
                metadata={
                    **template.metadata,
                    "original_context_length": len(context),
                    "optimized_context_length": len(optimized_context),
                    "domain": domain
                }
            )
            
        except Exception as e:
            logger.error(f"Prompt generation failed: {e}")
            # Return fallback prompt
            return self._create_fallback_prompt(question, context)
    
    def _apply_domain_customizations(self, template: PromptTemplate, domain: str) -> PromptTemplate:
        """Apply domain-specific customizations to template."""
        
        domain_customizations = {
            "financial": "Focus on financial terminology and numerical accuracy.",
            "medical": "Use precise medical terminology and emphasize accuracy.",
            "legal": "Pay attention to legal terminology and cite sources carefully.",
            "technical": "Use appropriate technical language and be precise."
        }
        
        customization = domain_customizations.get(domain, "")
        if customization:
            # Create new template with domain customization
            return PromptTemplate(
                system_prompt=template.system_prompt + f" {customization}",
                user_prompt=template.user_prompt,
                response_format=template.response_format,
                validation_rules=template.validation_rules,
                metadata={**template.metadata, "domain_customized": True}
            )
        
        return template
    
    def _create_fallback_prompt(self, question: str, context: str) -> PromptResult:
        """Create fallback prompt if generation fails."""
        return PromptResult(
            system_prompt="You are a helpful assistant that answers questions based on provided context.",
            user_prompt=f"Context: {context}\n\nQuestion: {question}\n\nPlease provide a clear answer.",
            response_format="Provide a clear, factual answer.",
            prompt_type=PromptType.FACTUAL,
            metadata={"fallback": True}
        )


class ContextOptimizer:
    """Optimizes context for better prompt performance."""
    
    def __init__(self):
        self.chars_per_token = 3.5  # Approximate
    
    async def optimize_context(
        self,
        context: str,
        question: str,
        max_length: int = 12000
    ) -> str:
        """Optimize context for prompt generation."""
        
        if len(context) <= max_length:
            return context
        
        logger.debug(f"Optimizing context from {len(context)} to {max_length} chars")
        
        # Strategy 1: Extract most relevant sentences
        relevant_context = self._extract_relevant_sentences(context, question, max_length)
        
        if len(relevant_context) <= max_length:
            return relevant_context
        
        # Strategy 2: Truncate with smart boundaries
        return self._smart_truncate(relevant_context, max_length)
    
    def _extract_relevant_sentences(self, context: str, question: str, max_length: int) -> str:
        """Extract sentences most relevant to the question."""
        
        # Split into sentences
        sentences = re.split(r'[.!?]+', context)
        
        # Score sentences by relevance to question
        question_words = set(question.lower().split())
        scored_sentences = []
        
        for sentence in sentences:
            if len(sentence.strip()) < 10:  # Skip very short sentences
                continue
                
            sentence_words = set(sentence.lower().split())
            overlap = len(question_words.intersection(sentence_words))
            score = overlap / max(len(question_words), 1)
            
            scored_sentences.append((score, sentence.strip()))
        
        # Sort by relevance and select top sentences within length limit
        scored_sentences.sort(key=lambda x: x[0], reverse=True)
        
        selected_sentences = []
        current_length = 0
        
        for score, sentence in scored_sentences:
            if current_length + len(sentence) <= max_length:
                selected_sentences.append(sentence)
                current_length += len(sentence)
            else:
                break
        
        return '. '.join(selected_sentences)
    
    def _smart_truncate(self, text: str, max_length: int) -> str:
        """Truncate text at smart boundaries."""
        
        if len(text) <= max_length:
            return text
        
        # Try to truncate at sentence boundary
        truncated = text[:max_length]
        last_sentence_end = max(
            truncated.rfind('.'),
            truncated.rfind('!'),
            truncated.rfind('?')
        )
        
        if last_sentence_end > max_length * 0.8:  # If we can keep 80% and end at sentence
            return truncated[:last_sentence_end + 1]
        
        # Fallback: truncate at word boundary
        last_space = truncated.rfind(' ')
        if last_space > 0:
            return truncated[:last_space] + "..."
        
        return truncated + "..."


# Factory functions
def create_default_prompt_generator() -> PromptGenerator:
    """Create default prompt generator."""
    return PromptGenerator()


def create_domain_specific_generator(domain: str) -> PromptGenerator:
    """Create domain-specific prompt generator."""
    generator = PromptGenerator()
    
    # Add domain-specific templates if needed
    # This could be expanded based on domain requirements
    
    return generator 