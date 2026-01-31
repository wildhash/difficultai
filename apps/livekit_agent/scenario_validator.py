"""
Scenario validation utilities.

Validates scenario fields according to the scenario contract.

Canonical ScenarioConfig fields:
- persona (or persona_type): ANGRY_CUSTOMER | ELITE_INTERVIEWER | etc.
- difficulty: float 0-1 (0 = easy, 1 = maximum pressure)
- company: string
- role: string
- goals (or user_goal): string
"""

from typing import Dict, Any, List, Optional
from agents.architect import PersonaType


def validate_scenario(scenario: Dict[str, Any]) -> List[str]:
    """
    Validate a scenario dictionary against the contract.
    
    Args:
        scenario: Scenario dictionary to validate
        
    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []
    
    # Required fields (support both naming conventions)
    required_fields = ['company', 'role', 'stakes']
    
    # Check persona (support both persona_type and persona)
    if 'persona_type' not in scenario and 'persona' not in scenario:
        errors.append("Missing required field: persona_type (or persona)")
    elif 'persona_type' in scenario or 'persona' in scenario:
        persona_value = scenario.get('persona_type') or scenario.get('persona')
        if not persona_value:
            errors.append("Missing required field: persona_type (or persona)")
    
    # Check goals (support both user_goal and goals)
    if 'user_goal' not in scenario and 'goals' not in scenario:
        errors.append("Missing required field: user_goal (or goals)")
    elif 'user_goal' in scenario or 'goals' in scenario:
        goals_value = scenario.get('user_goal') or scenario.get('goals')
        if not goals_value:
            errors.append("Missing required field: user_goal (or goals)")
    
    # Check difficulty
    if 'difficulty' not in scenario or scenario.get('difficulty') is None:
        errors.append("Missing required field: difficulty")
    
    for field in required_fields:
        if field not in scenario or not scenario[field]:
            errors.append(f"Missing required field: {field}")
    
    # Validate persona_type is valid
    persona_value = scenario.get('persona_type') or scenario.get('persona')
    if persona_value:
        valid_personas = [p.value for p in PersonaType]
        if persona_value not in valid_personas:
            errors.append(f"Invalid persona_type: {persona_value}. Must be one of: {', '.join(valid_personas)}")
    
    # Validate difficulty is 0-1 (float)
    if 'difficulty' in scenario and scenario['difficulty'] is not None:
        try:
            diff = float(scenario['difficulty'])
            if diff < 0 or diff > 1:
                errors.append("difficulty must be between 0 and 1 (0 = easy, 1 = maximum pressure)")
        except (ValueError, TypeError):
            errors.append("difficulty must be a number between 0 and 1")
    
    return errors


def get_missing_fields(scenario: Dict[str, Any]) -> List[str]:
    """
    Get list of missing required fields from scenario.
    
    Args:
        scenario: Scenario dictionary
        
    Returns:
        List of missing field names
    """
    required_fields = ['company', 'role', 'stakes']
    missing = []
    
    # Check persona (support both naming conventions)
    if 'persona_type' not in scenario and 'persona' not in scenario:
        missing.append('persona_type')
    elif not (scenario.get('persona_type') or scenario.get('persona')):
        missing.append('persona_type')
    
    # Check goals (support both naming conventions)
    if 'user_goal' not in scenario and 'goals' not in scenario:
        missing.append('user_goal')
    elif not (scenario.get('user_goal') or scenario.get('goals')):
        missing.append('user_goal')
    
    # Check difficulty
    if 'difficulty' not in scenario or scenario.get('difficulty') is None:
        missing.append('difficulty')
    
    for field in required_fields:
        if field not in scenario or not scenario[field]:
            missing.append(field)
    
    return missing


def is_scenario_complete(scenario: Dict[str, Any]) -> bool:
    """
    Check if scenario has all required fields.
    
    Args:
        scenario: Scenario dictionary
        
    Returns:
        True if scenario is complete, False otherwise
    """
    return len(validate_scenario(scenario)) == 0
