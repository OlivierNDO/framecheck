"""
utilities.py

Utility module for registering and instantiating column validation checks.

Defines a CheckFactory class that allows dynamic creation of column check instances
based on a registry of check types.
"""

from inspect import signature

class CheckFactory:
    """
    Factory and registry for dynamically instantiating column validation checks.

    Class Attributes
    ----------------
    registry : dict
        Mapping from check type name (str) to its associated check class.
    """
    registry = {}

    @classmethod
    def register(cls, check_type: str):
        """
        Decorator to register a new check class under a given type name.
    
        Parameters
        ----------
        check_type : str
            The identifier used to associate a string name with the check class.
    
        Returns
        -------
        Callable
            A decorator that registers the class in the factory registry.
        """
        def inner(check_cls):
            cls.registry[check_type] = check_cls
            return check_cls
        return inner

    @classmethod
    def create(cls, check_type: str, column_name: str, raise_on_fail: bool, **kwargs):
        """
        Instantiate one or more check instances based on type and optional flags.
    
        Parameters
        ----------
        check_type : str
            The primary check type to instantiate (e.g., 'int', 'string').
        column_name : str
            Name of the column the check applies to.
        raise_on_fail : bool
            Whether to treat violations as errors.
        **kwargs : dict
            Additional keyword arguments to pass to the check class or flag-based checks.
    
        Returns
        -------
        object or list
            A single check instance or a list of check instances, depending on the kwargs.
    
        Raises
        ------
        ValueError
            If the check type is unknown or if invalid keyword arguments are provided.
        """
        instances = []

        check_cls = cls.registry.get(check_type)
        if not check_cls:
            raise ValueError(f"Unknown column type '{check_type}'")

        # Grab init args for the check class
        init_params = signature(check_cls.__init__).parameters
        valid_keys = set(init_params.keys()) - {'self'}
        invalid_keys = set(kwargs) - valid_keys - set(cls.registry.keys())

        if invalid_keys:
            raise ValueError(
                f"Invalid keyword arguments for '{check_type}' check: {sorted(invalid_keys)}"
            )

        # Separate kwargs for main class and extra flags
        main_kwargs = {k: v for k, v in kwargs.items() if k in valid_keys}
        instances.append(check_cls(column_name=column_name, raise_on_fail=raise_on_fail, **main_kwargs))

        # Handle additional flag-based checks
        remaining_flags = {
            k: v for k, v in kwargs.items()
            if k not in valid_keys and k in cls.registry and v is True
        }

        for flag_name in remaining_flags:
            extra_cls = cls.registry[flag_name]
            instances.append(extra_cls(column_name=column_name, raise_on_fail=raise_on_fail))

        return instances if len(instances) > 1 else instances[0]
