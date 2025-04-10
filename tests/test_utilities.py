from src.utilities import CheckFactory

def test_register_and_create_check():
    @CheckFactory.register('dummy')
    class DummyCheck:
        def __init__(self, column_name, raise_on_fail, custom=None):
            self.column_name = column_name
            self.raise_on_fail = raise_on_fail
            self.custom = custom

    check = CheckFactory.create('dummy', column_name='foo', raise_on_fail=True, custom='bar')

    assert isinstance(check, DummyCheck)
    assert check.column_name == 'foo'
    assert check.raise_on_fail is True
    assert check.custom == 'bar'
