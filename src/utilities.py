from inspect import signature

class CheckFactory:
    registry = {}

    @classmethod
    def register(cls, check_type: str):
        def inner(check_cls):
            cls.registry[check_type] = check_cls
            return check_cls
        return inner

    @classmethod
    def create(cls, check_type: str, column_name: str, raise_on_fail: bool, **kwargs):
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
