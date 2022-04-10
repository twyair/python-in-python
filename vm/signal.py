from __future__ import annotations
from collections import OrderedDict
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, TypeAlias

if TYPE_CHECKING:
    from vm.builtins.int import PyInt
    from vm.function_ import FuncArgs
    from vm.vm import VirtualMachine

NSIG = 64
ANY_TRIGGERED = False
TRIGGERS = [False] * NSIG


def check_signals(vm: VirtualMachine) -> None:
    global ANY_TRIGGERED
    if vm.signal_handlers is None:
        return
    if not ANY_TRIGGERED:
        return
    ANY_TRIGGERED = True
    return trigger_signals(vm)


def trigger_signals(vm: VirtualMachine) -> None:
    assert vm.signal_handlers is not None
    for signum, trigger in enumerate(TRIGGERS[1:], 1):
        if trigger:
            if (handler := vm.signal_handlers[signum]) is not None:
                if vm.is_callable(handler):
                    vm.invoke(
                        handler,
                        FuncArgs(
                            [PyInt(signum).into_ref(vm), vm.ctx.get_none()],
                            OrderedDict(),
                        ),
                    )

    if vm.signal_rx is not None:
        for f in vm.signal_rx.rx.try_iter():
            f(vm)


def set_triggered():
    global ANY_TRIGGERED
    ANY_TRIGGERED = True


UserSignal: TypeAlias = Callable[["VirtualMachine"], None]


@dataclass
class UserSignalSender:
    tx: Any  # FIXME


@dataclass
class UserSignalReceiver:
    rx: Any  # FIXME
