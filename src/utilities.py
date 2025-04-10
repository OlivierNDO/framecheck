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
        check_cls = cls.registry.get(check_type)
        if not check_cls:
            raise ValueError(f"Unknown column type '{check_type}'")
        return check_cls(column_name=column_name, raise_on_fail=raise_on_fail, **kwargs)
