"""
Prompt Builder for AI Copilot Service.

Builds structured prompts for LLM queries based on context and user input.
Assembles system prompts, context, and user questions into optimized prompts.
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Tuple

from ..config.settings import get_settings
from .context_manager import Context

logger = logging.getLogger(__name__)


@dataclass
class Prompt:
    """A structured prompt for LLM inference."""
    system_prompt: str
    user_prompt: str
    context: str
    messages: List[Dict[str, str]]
    model: str
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    
    def to_openrouter_format(self) -> List[Dict[str, Any]]:
        """Convert to OpenRouter chat completion format."""
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": self.user_prompt}
        ]
        
        # Add context as a system message or user message
        if self.context:
            messages.insert(1, {"role": "system", "content": f"Context:\n{self.context}"})
        
        return messages


class PromptBuilder:
    """
    Builds prompts for LLM queries.
    
    Creates optimized prompts that include:
    - System prompt with role and constraints
    - Structured context from various sources
    - User question
    - Formatting instructions
    """
    
    def __init__(self):
        """Initialize prompt builder."""
        self.settings = get_settings()
    
    def build_prompt(
        self,
        user_id: str,
        question: str,
        context: Context,
        task_type: Optional[str] = None
    ) -> Prompt:
        """
        Build a complete prompt for a user query.
        
        Args:
            user_id: ID of the user
            question: The user's question
            context: Structured context for the query
            task_type: Optional task type for model selection
        
        Returns:
            Complete prompt structure
        """
        # Select model based on task type
        model = self._select_model(task_type, question)
        
        # Build system prompt
        system_prompt = self._build_system_prompt(user_id)
        
        # Build user prompt
        user_prompt = self._build_user_prompt(question, context)
        
        # Build context string
        context_str = context.to_prompt_context(self.settings.max_context_length)
        
        # Create messages
        messages = self._build_messages(system_prompt, user_prompt, context_str)
        
        return Prompt(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            context=context_str,
            messages=messages,
            model=model,
            temperature=self._get_temperature(task_type),
            max_tokens=self._get_max_tokens(task_type)
        )
    
    def _select_model(self, task_type: Optional[str], question: str) -> str:
        """Select the appropriate model."""
        guardrail_engine = self._get_guardrail_engine()
        return guardrail_engine.select_model(task_type, None, question)
    
    def _get_temperature(self, task_type: Optional[str]) -> float:
        """Get temperature setting based on task type."""
        if task_type in ["debug", "explain"]:
            return 0.3  # More deterministic for analytical tasks
        elif task_type in ["recommend", "suggest"]:
            return 0.9  # More creative for suggestions
        else:
            return 0.7  # Default
    
    def _get_max_tokens(self, task_type: Optional[str]) -> Optional[int]:
        """Get max tokens setting based on task type."""
        if task_type in ["summarize", "explain"]:
            return 2000  # Longer responses for explanations
        elif task_type in ["query", "general"]:
            return 1000  # Medium responses
        else:
            return None  # Use model default
    
    def _build_system_prompt(self, user_id: str) -> str:
        """Build the system prompt with role and constraints."""
        system_prompt = """You are an AI Copilot Assistant for the NYC Waste Intelligence Platform.

Your role is to provide advisory-only insights, explanations, and recommendations based on the waste management data and intelligence available.

IMPORTANT CONSTRAINTS:
1. You are in an ADVISORY-ONLY role. You cannot and must not:
   - Trigger any routing changes
   - Modify facility operations
   - Change ML models or configurations
   - Write to any database
   - Execute any automated actions
   - Bypass human approval processes

2. All operational changes require explicit human approval.

3. You must always include a disclaimer that recommendations are advisory only.

4. You must not reveal or use:
   - Raw sensor data
   - PII (personally identifiable information)
   - Exact GPS coordinates
   - User identities
   - Sensitive facility details

5. Always cite your sources when providing information.

6. If you cannot answer a question with available data, say so clearly.

7. Be concise, factual, and actionable in your responses.

Context about the Waste Intelligence Platform:
- Provides real-time organic waste intelligence across NYC buildings, blocks, and facilities
- Uses a Hub-and-Spoke model with sensor-enabled bins, mesh clusters, and processing facilities
- Includes ML-based forecasting, anomaly detection, and contamination classification
- Maintains a Waste-to-Resource Knowledge Graph (W2RKG) for pathway analysis
- Integrates with NYC Open Data for weather, air quality, and mobility information

Your responses should help operators:
- Understand anomalies and their causes
- Interpret ML outputs and predictions
- Optimize waste routing and facility load
- Discover waste-to-resource pathways and symbiosis opportunities
- Make data-driven decisions about waste management

Remember: You are an advisor, not a controller. Human approval is always required."""
        
        return system_prompt
    
    def _build_user_prompt(self, question: str, context: Context) -> str:
        """Build the user prompt with question and context references."""
        # Add any specific instructions based on context
        intent = context.metadata.get("intent", "general")
        
        instructions = self._get_intent_instructions(intent)
        
        user_prompt = f"""Question: {question}

{instructions}

Please provide a clear, actionable, and advisory response based on the available context.
Remember to:
1. Explain the situation clearly
2. Provide relevant data and insights
3. Offer recommendations (advisory only)
4. Cite your sources
5. Include the disclaimer about human approval"""
        
        return user_prompt
    
    def _get_intent_instructions(self, intent: str) -> str:
        """Get specific instructions based on intent."""
        instructions = {
            "explain": "Focus on explaining the causes, patterns, and implications of the data.",
            "query": "Provide factual information and data from the available sources.",
            "predict": "Use forecasting models to predict future trends and outcomes.",
            "recommend": "Offer specific, actionable recommendations based on analysis.",
            "summarize": "Provide a concise summary of the key points and insights.",
            "debug": "Help identify and explain potential issues or problems in the data or systems.",
            "help": "Provide guidance on how to use the system or interpret results.",
            "general": "Provide a comprehensive response based on all available context."
        }
        
        return instructions.get(intent, instructions["general"])
    
    def _build_messages(
        self,
        system_prompt: str,
        user_prompt: str,
        context_str: str
    ) -> List[Dict[str, str]]:
        """Build messages list for chat completion."""
        messages = []
        
        # System message with role
        messages.append({
            "role": "system",
            "content": system_prompt
        })
        
        # Context message
        if context_str:
            messages.append({
                "role": "system",
                "content": f"Available Context:\n{context_str}"
            })
        
        # User message
        messages.append({
            "role": "user",
            "content": user_prompt
        })
        
        return messages
    
    def _get_guardrail_engine(self):
        """Get guardrail engine instance."""
        from .guardrail_engine import get_guardrail_engine
        return get_guardrail_engine()
    
    def build_query_prompt(
        self,
        question: str,
        context_summary: Dict[str, Any],
        used_tools: List[str]
    ) -> str:
        """
        Build a prompt for querying specific information.
        
        Args:
            question: The user's question
            context_summary: Summary of context used
            used_tools: List of tools that were used
        
        Returns:
            Formatted prompt string
        """
        tools_str = ", ".join(used_tools) if used_tools else "none"
        context_str = json.dumps(context_summary, indent=2)
        
        return f"""Based on the following context gathered from {tools_str}:

{context_str}

Question: {question}

Please provide a comprehensive answer based on this context."""
    
    def build_explanation_prompt(
        self,
        data: Dict[str, Any],
        question: str
    ) -> str:
        """
        Build a prompt for explaining data or patterns.
        
        Args:
            data: The data to explain
            question: The user's question
        
        Returns:
            Formatted prompt string
        """
        data_str = json.dumps(data, indent=2)
        
        return f"""Please explain the following data in the context of waste management operations:

{data_str}

Question: {question}

Focus on:
1. What the data shows
2. Why it's significant
3. Potential causes
4. Recommended actions (advisory only)
5. Any patterns or trends"""
    
    def build_recommendation_prompt(
        self,
        options: List[Dict[str, Any]],
        criteria: str,
        question: str
    ) -> str:
        """
        Build a prompt for generating recommendations.
        
        Args:
            options: List of options to evaluate
            criteria: Criteria for evaluation
            question: The user's question
        
        Returns:
            Formatted prompt string
        """
        options_str = json.dumps(options, indent=2)
        
        return f"""Evaluate the following options based on the criteria: {criteria}

Options:
{options_str}

Question: {question}

For each option, provide:
1. Pros and cons
2. Feasibility assessment
3. Expected outcomes
4. Recommendation (advisory only)

Rank the options and explain your reasoning."""
    
    def build_summarization_prompt(
        self,
        data: Dict[str, Any],
        focus_areas: List[str],
        question: str
    ) -> str:
        """
        Build a prompt for summarizing data.
        
        Args:
            data: Data to summarize
            focus_areas: Areas to focus on
            question: The user's question
        
        Returns:
            Formatted prompt string
        """
        data_str = json.dumps(data, indent=2)
        focus_str = ", ".join(focus_areas) if focus_areas else "key insights"
        
        return f"""Please summarize the following data with focus on: {focus_str}

{data_str}

Question: {question}

Provide:
1. Executive summary
2. Key findings
3. Important metrics
4. Trends and patterns
5. Recommendations (advisory only)"""


# Global prompt builder instance
_prompt_builder: Optional[PromptBuilder] = None


def get_prompt_builder() -> PromptBuilder:
    """Get or create the global prompt builder."""
    global _prompt_builder
    if _prompt_builder is None:
        _prompt_builder = PromptBuilder()
    return _prompt_builder
