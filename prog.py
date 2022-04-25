import sys

# import json

# pdebug = pdebug  # type: ignore


# try:
#     pdebug.doesnt_exist
# except AttributeError as e:
#     pdebug(e)


def _wrap(new, old):
    """Simple substitute for functools.update_wrapper."""
    for replace in ["__module__", "__name__", "__qualname__", "__doc__"]:
        if hasattr(old, replace):
            setattr(new, replace, getattr(old, replace))
    new.__dict__.update(old.__dict__)


def nop(f):
    def inner():
        return f()

    _wrap(inner, f)
    return inner


@nop
def bar():
    return 87


# pdebug(bar.__name__)

# # def foo(x: int, /, *, y: float) -> float:
# #     return x / 2.345 * y


# # pdebug(sys.prefix)
# pdebug(3j * 3 + 5j - 3.0)
# # pdebug([3j] + [foo(10, y=3.4)])
# # pdebug(foo)
# # pdebug(isinstance(5, int))
# # pdebug(type(5))
# # pdebug(int)
# # pdebug(int is type(5))
# module_type = type(sys)
# pdebug(sys)
# pdebug(module_type)
# pdebug(isinstance(sys.modules["sys"], module_type))
# for name, module in sys.modules.items():
#     pdebug(name)
#     pdebug(isinstance(module, module_type))

# # import pprint
