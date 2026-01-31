"""
Researcher Agent

Gathers company and role context to inform scenario design.

Responsibilities:
- Research company background and culture
- Understand role requirements and expectations
- Gather relevant industry context
- Provide context for scenario customization
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass


@dataclass
class CompanyContext:
    """Company research context."""
    name: str
    industry: str
    size: Optional[str] = None
    culture: Optional[str] = None
    recent_news: Optional[List[str]] = None
    key_values: Optional[List[str]] = None


@dataclass
class RoleContext:
    """Role research context."""
    title: str
    level: str  # e.g., "junior", "mid", "senior", "executive"
    key_skills: List[str]
    responsibilities: List[str]
    typical_challenges: Optional[List[str]] = None


class ResearcherAgent:
    """
    Gathers company and role context for scenario customization.
    
    The researcher agent collects information that helps other agents
    create realistic, context-aware scenarios and conversations.
    """
    
    def __init__(self):
        """Initialize the researcher agent."""
        self.research_cache: Dict[str, Any] = {}
    
    def research_company(
        self,
        company_name: str,
        source_docs: Optional[List[str]] = None
    ) -> CompanyContext:
        """
        Research a company to gather context.
        
        Args:
            company_name: Name of the company to research
            source_docs: Optional documents to extract information from
            
        Returns:
            CompanyContext with gathered information
        """
        # Check cache first
        cache_key = f"company:{company_name}"
        if cache_key in self.research_cache:
            return self.research_cache[cache_key]
        
        # In a real implementation, this would:
        # 1. Search company databases
        # 2. Analyze provided documents
        # 3. Gather recent news
        # 4. Extract key information
        
        # For now, create a basic context
        context = CompanyContext(
            name=company_name,
            industry="Technology",  # Placeholder
            size="Unknown",
            culture="Professional and fast-paced",
            recent_news=[],
            key_values=["Innovation", "Customer focus", "Excellence"]
        )
        
        # Cache the result
        self.research_cache[cache_key] = context
        return context
    
    def research_role(
        self,
        role_title: str,
        company_context: Optional[CompanyContext] = None
    ) -> RoleContext:
        """
        Research a role to understand requirements and expectations.
        
        Args:
            role_title: The role title to research
            company_context: Optional company context for customization
            
        Returns:
            RoleContext with gathered information
        """
        # Check cache
        cache_key = f"role:{role_title}"
        if cache_key in self.research_cache:
            return self.research_cache[cache_key]
        
        # In a real implementation, this would:
        # 1. Analyze job descriptions
        # 2. Identify key skills and requirements
        # 3. Understand typical challenges
        # 4. Consider company-specific variations
        
        # For now, create a basic context
        context = RoleContext(
            title=role_title,
            level="mid",  # Placeholder
            key_skills=[
                "Communication",
                "Problem-solving",
                "Technical expertise"
            ],
            responsibilities=[
                "Deliver results",
                "Collaborate with team",
                "Meet deadlines"
            ],
            typical_challenges=[
                "Managing competing priorities",
                "Handling difficult stakeholders",
                "Making decisions under pressure"
            ]
        )
        
        # Cache the result
        self.research_cache[cache_key] = context
        return context
    
    def generate_context_summary(
        self,
        company_context: CompanyContext,
        role_context: RoleContext
    ) -> str:
        """
        Generate a text summary of research context.
        
        Args:
            company_context: Company research results
            role_context: Role research results
            
        Returns:
            Text summary for use by other agents
        """
        summary = f"""
Company: {company_context.name}
Industry: {company_context.industry}
Culture: {company_context.culture}

Role: {role_context.title}
Level: {role_context.level}
Key Skills: {', '.join(role_context.key_skills)}

Typical Challenges: {', '.join(role_context.typical_challenges or [])}
"""
        return summary.strip()
    
    def extract_talking_points(
        self,
        company_context: CompanyContext,
        role_context: RoleContext
    ) -> List[str]:
        """
        Extract key talking points for the scenario.
        
        Args:
            company_context: Company research results
            role_context: Role research results
            
        Returns:
            List of talking points
        """
        talking_points = []
        
        # Add company-related points
        if company_context.key_values:
            talking_points.append(
                f"Alignment with company values: {', '.join(company_context.key_values)}"
            )
        
        # Add role-related points
        talking_points.append(
            f"Key skills required: {', '.join(role_context.key_skills)}"
        )
        
        if role_context.typical_challenges:
            talking_points.append(
                f"Common challenges: {', '.join(role_context.typical_challenges)}"
            )
        
        return talking_points
    
    def clear_cache(self):
        """Clear the research cache."""
        self.research_cache.clear()
