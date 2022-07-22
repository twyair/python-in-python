class TestCase:
    def foo(self) -> int:
        return 5


pdebug(TestCase)
pdebug(TestCase())
pdebug(TestCase().foo())
pdebug([TestCase(), 45343, "abfds", [1212]])
