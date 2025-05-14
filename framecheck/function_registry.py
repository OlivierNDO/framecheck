"""
function_registry.py

Registry for serializable validation functions that can be persisted
and reconstructed across sessions.
"""
from typing import Dict, Callable, Any, Optional

# Global registry to store registered functions
_FUNCTION_REGISTRY: Dict[str, Callable] = {}

def register_check_function(name: Optional[str] = None):
    """
    Decorator to register a function as a serializable check function.
    
    Parameters
    ----------
    name : str, optional
        Custom name for the function. If not provided, the function's name will be used.
    
    Returns
    -------
    Callable
        Decorator function that registers the decorated function.
    
    Examples
    --------
    >>> @register_check_function()
    >>> def valid_age(row):
    ...     return 18 <= row['age'] <= 65
    
    >>> @register_check_function(name="custom_price_check")
    >>> def check_price_margin(row):
    ...     return row['price'] >= row['cost'] * 1.2
    """
    def decorator(func: Callable) -> Callable:
        registry_name = name or func.__name__
        _FUNCTION_REGISTRY[registry_name] = func
        # Attach the registry name to the function for later reference
        func._registry_name = registry_name
        return func
    return decorator

def get_registered_function(name: str) -> Optional[Callable]:
    """
    Retrieve a registered function by name.
    
    Parameters
    ----------
    name : str
        The registered name of the function.
    
    Returns
    -------
    Callable or None
        The registered function, or None if not found.
    """
    return _FUNCTION_REGISTRY.get(name)

def is_registered(func: Callable) -> bool:
    """
    Check if a function is registered.
    
    Parameters
    ----------
    func : Callable
        The function to check.
    
    Returns
    -------
    bool
        True if the function is registered, False otherwise.
    """
    return hasattr(func, '_registry_name')

def get_registry_name(func: Callable) -> Optional[str]:
    """
    Get the registry name of a registered function.
    
    Parameters
    ----------
    func : Callable
        The function to get the registry name for.
    
    Returns
    -------
    str or None
        The registry name if registered, None otherwise.
    """
    return getattr(func, '_registry_name', None)

def list_registered_functions() -> Dict[str, Callable]:
    """
    Get a dictionary of all registered functions.
    
    Returns
    -------
    Dict[str, Callable]
        Dictionary of registered function names to functions.
    """
    return _FUNCTION_REGISTRY.copy()