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

    def __enter__(self):
        pass

    def __exit__(self, *args):
        return True


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


def foo():
    try:
        while True:
            with TestCase():
                pdebug("count")
                if True:
                    pdebug("out")
                    return True
            pdebug("sdsd")
    finally:
        pass


foo()

x = 5
x += 9

pdebug(issubclass(bool, int))

raise ModuleNotFoundError()
