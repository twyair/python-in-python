# from prog2 import B


class TestCase:
    X: int = 2

    def __init__(self) -> None:
        self.bar = 964

    def foo(self) -> int:
        return 5

    @property
    def cached(self):
        return self.bar

    @cached.setter
    def cached(self, value):
        self.bar = value

    @classmethod
    def method(cls, a: int) -> int:
        return a * 2


pdebug(TestCase)
pdebug(TestCase())
pdebug(TestCase().foo())
pdebug([TestCase(), 45343, "abfds", [1212]])

a = TestCase()
pdebug(TestCase.X)
pdebug(TestCase.cached.fset)
a.cached = 1234
pdebug(a.cached)

t = TestCase.method
pdebug(t(222))
pdebug(TestCase.method)
pdebug(TestCase.method(2))

4 + ""
