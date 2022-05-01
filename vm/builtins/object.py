from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from vm.builtins.dict import PyDictRef
    from vm.builtins.pystr import PyStrRef
    from vm.builtins.pytype import PyTypeRef
    from vm.pyobject import PyContext
    from vm.pyobjectrc import PyObject, PyObjectRef
    from vm.vm import VirtualMachine

    # from vm.function_ import FuncArgs
    from common.hash import PyHash

import vm.pyobject as po
import vm.pyobjectrc as prc
import vm.types.slot as slot
import vm.builtins.pystr as pystr
import vm.builtins.dict as pydict
import vm.builtins.pytype as pytype
import vm.builtins.int as pyint
import vm.function_ as fn
from common.deco import pyclassmethod, pymethod, pyproperty, pyslot
from common.error import PyImplBase, PyImplError, PyImplException


@po.tp_flags(basetype=True)
@po.pyimpl()
@po.pyclass("object")
@dataclass
class PyBaseObject(po.PyClassImpl):
    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.object_type

    @pyslot
    @staticmethod
    def slot_new(
        class_: PyTypeRef, args: fn.FuncArgs, vm: VirtualMachine
    ) -> PyObjectRef:
        if class_.is_(vm.ctx.types.object_type):
            dict_ = None
        else:
            dict_ = vm.ctx.new_dict()

        if (abs_methods := class_._.get_attr("__abstractmethods__")) is not None:
            if (
                unimplemented_abstract_method_count := abs_methods.length_opt(vm)
            ) is not None:
                if unimplemented_abstract_method_count > 0:
                    vm.new_type_error("You must implement the abstract methods")

        return prc.PyRef.new_ref(PyBaseObject(), class_, dict_)

    @pyslot
    @staticmethod
    def slot_richcompare(
        zelf: PyObject, other: PyObject, op: slot.PyComparisonOp, vm: VirtualMachine
    ) -> PyObjectRef | po.PyComparisonValue:
        return PyBaseObject.cmp(zelf, other, op, vm)

    @staticmethod
    def cmp(
        zelf: PyObject, other: PyObject, op: slot.PyComparisonOp, vm: VirtualMachine
    ) -> po.PyComparisonValue:
        if op == slot.PyComparisonOp.Eq:
            if zelf.is_(other):
                return po.PyComparisonValue(True)
            else:
                return po.PyComparisonValue(None)
        elif op == slot.PyComparisonOp.Ne:
            cmp = zelf.class_()._.mro_find_map(lambda cls: cls.slots.richcompare)
            assert cmp is not None
            obj = cmp(zelf, other, slot.PyComparisonOp.Eq, vm)
            # FIXME? shouldnt the result be negated
            if isinstance(obj, po.PyArithmeticValue):
                return obj
            else:
                v = po.PyArithmeticValue.from_object(vm, obj)
                if v.value is None:
                    return po.PyComparisonValue(None)
                else:
                    return po.PyComparisonValue(v.value.try_to_bool(vm))
        else:
            return po.PyComparisonValue(None)

    @pymethod(True)
    @staticmethod
    def i__eq__(
        zelf: PyObjectRef, value: PyObjectRef, *, vm: VirtualMachine
    ) -> po.PyComparisonValue:
        return PyBaseObject.cmp(zelf, value, slot.PyComparisonOp.Eq, vm)

    @pymethod(True)
    @staticmethod
    def i__ne__(
        zelf: PyObjectRef, value: PyObjectRef, *, vm: VirtualMachine
    ) -> po.PyComparisonValue:
        return PyBaseObject.cmp(zelf, value, slot.PyComparisonOp.Ne, vm)

    @pymethod(True)
    @staticmethod
    def i__lt__(
        zelf: PyObjectRef, value: PyObjectRef, *, vm: VirtualMachine
    ) -> po.PyComparisonValue:
        return PyBaseObject.cmp(zelf, value, slot.PyComparisonOp.Lt, vm)

    @pymethod(True)
    @staticmethod
    def i__le__(
        zelf: PyObjectRef, value: PyObjectRef, *, vm: VirtualMachine
    ) -> po.PyComparisonValue:
        return PyBaseObject.cmp(zelf, value, slot.PyComparisonOp.Le, vm)

    @pymethod(True)
    @staticmethod
    def i__ge__(
        zelf: PyObjectRef, value: PyObjectRef, *, vm: VirtualMachine
    ) -> po.PyComparisonValue:
        return PyBaseObject.cmp(zelf, value, slot.PyComparisonOp.Ge, vm)

    @pymethod(True)
    @staticmethod
    def i__gt__(
        zelf: PyObjectRef, value: PyObjectRef, *, vm: VirtualMachine
    ) -> po.PyComparisonValue:
        return PyBaseObject.cmp(zelf, value, slot.PyComparisonOp.Gt, vm)

    @pymethod(True)
    @staticmethod
    def i__setattr__(
        zelf: PyObjectRef, name: PyStrRef, value: PyObjectRef, *, vm: VirtualMachine
    ) -> None:
        generic_setattr(zelf, name, value, vm)

    @pymethod(True)
    @staticmethod
    def i__delattr__(zelf: PyObjectRef, name: PyStrRef, *, vm: VirtualMachine) -> None:
        generic_setattr(zelf, name, None, vm)

    @pyslot
    @staticmethod
    def slot_setattro(
        obj: PyObject,
        attr_name: PyStrRef,
        value: Optional[PyObjectRef],
        vm: VirtualMachine,
    ) -> None:
        generic_setattr(obj, attr_name, value, vm)

    @pymethod(True)
    @staticmethod
    def i__str__(zelf: PyObjectRef, *, vm: VirtualMachine) -> PyStrRef:
        return zelf.repr(vm)

    @pymethod(True)
    @staticmethod
    def i__repr__(zelf: PyObjectRef, *, vm: VirtualMachine) -> Optional[str]:
        class_ = zelf.class_()

        if (
            qualname := class_._.get___qualname__(vm=vm).downcast_ref(pystr.PyStr)
        ) is not None:
            qualname = qualname._.as_str()
        else:
            return None

        if (
            mod := class_._.get___module__(vm=vm).downcast_ref(pystr.PyStr)
        ) is not None:
            mod = mod._.as_str()
            if mod != "builtins":
                return "<{}.{} object at {:x}>".format(mod, qualname, zelf.get_id())

        return "<{} object at {:x}>".format(class_._.slot_name(), zelf.get_id())

    @pyclassmethod(False)
    @staticmethod
    def i__subclasshook__(args: fn.FuncArgs, *, vm: VirtualMachine) -> PyObjectRef:
        return vm.ctx.get_not_implemented()

    @pyclassmethod(True)
    @staticmethod
    def i__init_subclass__(class_: PyTypeRef, /) -> None:
        return

    @pymethod(True)
    @staticmethod
    def i__dir__(zelf: PyObjectRef, /, *, vm: VirtualMachine) -> PyObjectRef:
        dict_: prc.PyRef[pydict.PyDict] = pydict.PyDict.from_attributes(
            zelf.class_()._.get_attributes(), vm
        ).into_ref(vm)

        if zelf.dict is not None:
            vm.call_method(dict_, "update", fn.FuncArgs([zelf.dict.d]))

        return vm.ctx.new_list(list(dict_._.get_keys()))

    @pymethod(True)
    @staticmethod
    def i__format__(
        zelf: PyObjectRef, format_spec: PyStrRef, *, vm: VirtualMachine
    ) -> PyStrRef:
        if not format_spec._.as_str():
            return zelf.str(vm)
        else:
            vm.new_type_error(
                f"unsupported format string passed to {zelf.class_()._.name()}.__format__"
            )

    @pymethod(False)
    @staticmethod
    def i__init__(zelf: PyObjectRef, args: fn.FuncArgs, *, vm: VirtualMachine) -> None:
        return

    @pyproperty()
    @staticmethod
    def get___class__(zelf: PyObjectRef, *, vm: VirtualMachine) -> PyTypeRef:
        return zelf.clone_class()

    @pyproperty()
    @staticmethod
    def set___class__(
        instance: PyObjectRef, value: PyObjectRef, *, vm: VirtualMachine
    ) -> None:
        if instance.payload_is(PyBaseObject):
            try:
                cls = value.downcast(pytype.PyType)
            except PyImplError as e:
                vm.new_type_error(
                    f"__class__ must be set to a class, not '{e.obj.class_()._.name()}' object"
                )
            else:
                instance.type = cls
                return None
        else:
            vm.new_type_error(
                "__class__ assignment only supported for types without a payload"
            )

    @pyslot
    @staticmethod
    def slot_getattro(
        zelf: PyObjectRef, name: PyStrRef, vm: VirtualMachine
    ) -> PyObjectRef:
        return vm.generic_getattribute(zelf, name)

    @pymethod(True)
    @staticmethod
    def i__getattribute__(
        zelf: PyObjectRef, name: PyStrRef, *, vm: VirtualMachine
    ) -> PyObjectRef:
        return PyBaseObject.slot_getattro(zelf, name, vm=vm)

    @pymethod(True)
    @staticmethod
    def i__reduce__(zelf: PyObjectRef, *, vm: VirtualMachine) -> PyObjectRef:
        return common_reduce(zelf, 0, vm)

    @staticmethod
    def _reduce_ex(zelf: PyObjectRef, proto: int, vm: VirtualMachine) -> PyObjectRef:
        reduce = vm.get_attribute_opt(zelf, vm.ctx.new_str("__reduce__"))
        if reduce is not None:
            object_reduce = vm.ctx.types.object_type._.get_attr("__reduce__")
            assert object_reduce is not None
            typ_obj = zelf.clone_class()
            class_reduce = typ_obj.get_attr(vm.ctx.new_str("__reduce__"), vm)
            if not class_reduce.is_(object_reduce):
                return vm.invoke(reduce, fn.FuncArgs())
        return common_reduce(zelf, proto, vm)

    @pymethod(True)
    @staticmethod
    def i__reduce_ex__(
        zelf: PyObjectRef, proto: pyint.PyIntRef, *, vm: VirtualMachine
    ) -> PyObjectRef:
        return PyBaseObject._reduce_ex(zelf, proto._.as_int(), vm)

    @pyslot
    @staticmethod
    def slot_hash(zelf: PyObject, *, vm: VirtualMachine) -> PyHash:
        return zelf.get_id()

    @pymethod(True)
    @staticmethod
    def i__hash__(zelf: PyObjectRef, *, vm: VirtualMachine) -> PyHash:
        return PyBaseObject.slot_hash(zelf, vm=vm)


def object_get_dict(obj: PyObjectRef, vm: VirtualMachine) -> PyDictRef:
    if obj.dict is not None:
        return obj.dict.d
    else:
        vm.new_attribute_error("This object has no __dict__")


def object_set_dict(obj: PyObjectRef, dict: PyDictRef, vm: VirtualMachine) -> None:
    try:
        obj.set_dict(dict)
    except PyImplBase as _:
        vm.new_attribute_error("This object has no __dict__")


def generic_getattr(
    obj: PyObjectRef, attr_name: PyStrRef, vm: VirtualMachine
) -> PyObjectRef:
    return vm.generic_getattribute(obj, attr_name)


def generic_setattr(
    obj: PyObject, attr_name: PyStrRef, value: Optional[PyObjectRef], vm: VirtualMachine
) -> None:
    if (attr := obj.get_class_attr(attr_name._.as_str())) is not None:
        descr_set = attr.class_()._.mro_find_map(lambda cls: cls.slots.descr_set)
        if descr_set is not None:
            return descr_set(attr, obj, value, vm)

    if (dict := obj.dict) is not None:
        if value is not None:
            dict.set_item(attr_name, value, vm)
        else:
            try:
                dict.del_item(attr_name, vm)
            except PyImplException as e:
                if e.exception.isinstance(vm.ctx.exceptions.key_error):
                    vm.new_attribute_error(
                        f"'{obj.class_()._.name()}' object has no attribute '{attr_name}'"
                    )
                else:
                    raise e
            else:
                return
    else:
        vm.new_attribute_error(
            f"'{obj.class_()._.name()}' object has no attribute '{attr_name._.as_str()}'"
        )


def common_reduce(obj: PyObjectRef, proto: int, vm: VirtualMachine) -> PyObjectRef:
    if proto >= 2:
        reducelib = vm.import_(vm.ctx.new_str("__reducelib"), None, 0)
        reduce_2 = reducelib.get_attr(vm.ctx.new_str("reduce_2"), vm)
        return vm.invoke(reduce_2, fn.FuncArgs([obj]))
    else:
        copyreg = vm.import_(vm.ctx.new_str("copyreg"), None, 0)
        reduce_ex = copyreg.get_attr(vm.ctx.new_str("_reduce_ex"), vm)
        return vm.invoke(reduce_ex, fn.FuncArgs([obj, vm.ctx.new_int(proto)]))


def init(ctx: PyContext) -> None:
    PyBaseObject.extend_class(ctx, ctx.types.object_type)
