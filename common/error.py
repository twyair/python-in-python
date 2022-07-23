from __future__ import annotations
from dataclasses import dataclass
from functools import wraps
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Generic,
    NoReturn,
    Optional,
    ParamSpec,
    TypeAlias,
    TypeVar,
)


import returns.result


if TYPE_CHECKING:
    from vm.pyobjectrc import PyObjectRef
    from vm.exceptions import PyBaseExceptionRef


class PyImplBase(Exception):
    pass


class PyImplError(PyImplBase):
    obj: PyObjectRef

    def __init__(self, obj: PyObjectRef) -> None:
        self.obj = obj
        super().__init__()


class PyImplErrorStr(PyImplBase):
    msg: str

    def __init__(self, msg: str) -> None:
        self.msg = msg
        super().__init__()


class PyImplException(PyImplBase):
    """
    an exception representing an actual python exception
    """

    exception: PyBaseExceptionRef

    def __init__(self, exception: PyBaseExceptionRef) -> None:
        self.exception = exception
        super().__init__()

    # @staticmethod
    # def from_python_exception(exc: OverflowError | ZeroDivisionError, vm: VirtualMachine) -> NoReturn:
    #     if isinstance(exc, OverflowError):
    #         vm.new_overflow_error()

    def __repr__(self) -> str:
        return f"python exception '{self.exception.class_()._.name()}'"


def unreachable(msg: Optional[str] = None) -> NoReturn:
    assert False, f"unreachable: {msg}"


_FuncParams = ParamSpec("_FuncParams")
_ValueType = TypeVar("_ValueType", covariant=True)


# @dataclass
# class RException:
#     exc: PyBaseExceptionRef

#     def unwrap(self) -> NoReturn:
#         raise PyImplException(self.exc)

#     def ok_or(self, f: Callable[[PyBaseExceptionRef], R], /) -> R:
#         return f(self.exc)


# T = TypeVar("T")
# R = TypeVar("R")


# @dataclass
# class ROk(Generic[T]):
#     value: T

#     def unwrap(self) -> T:
#         return self.value

#     def ok_or(self, f: Callable[[PyBaseExceptionRef], Any], /) -> T:
#         return self.value


def safe(
    fn: Callable[_FuncParams, _ValueType]
) -> Callable[_FuncParams, returns.result.Result[_ValueType, PyBaseExceptionRef]]:
    @wraps(fn)
    def decorator(*args: _FuncParams.args, **kwargs: _FuncParams.kwargs):
        try:
            return returns.result.Success(fn(*args, **kwargs))
        except PyImplException as exc:
            return returns.result.Failure(exc.exception)

    return decorator


PE: TypeAlias = "PyBaseExceptionRef"
Result = returns.result.Result
Ok = returns.result.Success

# safe = returns.result.safe(exceptions=(PyImplException,))
