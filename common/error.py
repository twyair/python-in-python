from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from vm.pyobjectrc import PyObjectRef


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

    exception: PyObjectRef

    def __init__(self, exception: PyObjectRef) -> None:
        self.exception = exception
        super().__init__()

    # @staticmethod
    # def from_python_exception(exc: OverflowError | ZeroDivisionError, vm: VirtualMachine) -> NoReturn:
    #     if isinstance(exc, OverflowError):
    #         vm.new_overflow_error()
