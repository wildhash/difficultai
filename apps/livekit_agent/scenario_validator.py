"""
Scenario validation utilities.

Validates scenario fields according to the scenario contract.
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
    
    # Required fields
    required_fields = ['persona_type', 'company', 'role', 'stakes', 'user_goal', 'difficulty']
    
    for field in required_fields:
        if field not in scenario or not scenario[field]:
            errors.append(f"Missing required field: {field}")
    
    # Validate persona_type is valid
    if 'persona_type' in scenario and scenario['persona_type']:
        valid_personas = [p.value for p in PersonaType]
        if scenario['persona_type'] not in valid_personas:
            errors.append(f"Invalid persona_type: {scenario['persona_type']}. Must be one of: {', '.join(valid_personas)}")
    
    # Validate difficulty is 1-5
    if 'difficulty' in scenario and scenario['difficulty']:
        try:
            diff = int(scenario['difficulty'])
            if diff < 1 or diff > 5:
                errors.append("difficulty must be between 1 and 5")
        except (ValueError, TypeError):
            errors.append("difficulty must be a number between 1 and 5")
    
    return errors


def get_missing_fields(scenario: Dict[str, Any]) -> List[str]:
    """
    Get list of missing required fields from scenario.
    
    Args:
        scenario: Scenario dictionary
        
    Returns:
        List of missing field names
    """
    required_fields = ['persona_type', 'company', 'role', 'stakes', 'user_goal', 'difficulty']
    missing = []
    
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
