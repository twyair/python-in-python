from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from common.error import PyImplError
from vm.builtins.function import PyBoundMethod

if TYPE_CHECKING:
    from vm.builtins.staticmethod import PyStaticMethod
    from vm.function_ import FuncArgs
    from vm.pyobject import PyContext
    from vm.pyobjectrc import PyObjectRef, PyRef
    from vm.builtins.pystr import PyStr, PyStrRef
    from vm.builtins.pytype import PyTypeRef
    from vm.vm import VirtualMachine
    from vm.function_ import PyNativeFunc

from common.deco import pymethod, pyproperty
import vm.pyobject as po
import vm.pyobjectrc as prc
import vm.builtins.pystr as pystr
import vm.builtins.pytype as pytype
import vm.types.slot as slot


@dataclass
class PyNativeFuncDef:
    func: PyNativeFunc
    name: PyStrRef
    doc: Optional[PyStrRef]

    @staticmethod
    def new(func: PyNativeFunc, name: PyStrRef) -> PyNativeFuncDef:
        return PyNativeFuncDef(func, name, None)

    def with_doc(self, doc: str, ctx: PyContext) -> PyNativeFuncDef:
        self.doc = pystr.PyStr.from_str(doc, ctx)
        return self

    def into_function(self) -> PyBuiltinFunction:
        # FIXME?
        return PyBuiltinFunction(self, None)

    def build_function(self, ctx: PyContext) -> PyRef[PyBuiltinFunction]:
        return self.into_function().into_ref(ctx)

    def build_method(self, ctx: PyContext, class_: PyTypeRef) -> PyRef[PyBuiltinMethod]:
        return prc.PyRef.new_ref(
            PyBuiltinMethod(self, class_), ctx.types.method_descriptor_type, None
        )

    def build_class_method(
        self, ctx: PyContext, class_: PyTypeRef
    ) -> PyRef[PyStaticMethod]:
        callable = self.build_method(ctx, class_)
        return prc.PyRef.new_ref(
            PyStaticMethod(callable), ctx.types.staticmethod_type, None
        )


@po.tp_flags(has_dict=True)
@po.pyimpl(callable=True, constructor=False)
@po.pyclass(name="builtin_function_or_method")
@dataclass
class PyBuiltinFunction(po.PyClassImpl, slot.CallableMixin):
    value: PyNativeFuncDef
    module_: Optional[PyObjectRef]

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.builtin_function_or_method_type

    def with_module(self, module: PyObjectRef) -> PyBuiltinFunction:
        self.module_ = module
        return self

    def into_ref(self: PyBuiltinFunction, ctx: PyContext) -> PyRef[PyBuiltinFunction]:
        return prc.PyRef.new_ref(self, ctx.types.builtin_function_or_method_type, None)

    def as_func(self) -> PyNativeFunc:
        return self.value.func

    @pyproperty()
    def get___module__(self, vm: VirtualMachine) -> PyObjectRef:
        return vm.unwrap_or_none(self.module_)

    @pyproperty()
    def get___name__(self) -> PyStrRef:
        return self.value.name

    @pyproperty()
    def get___qualname__(self) -> PyStrRef:
        return self.get___name__()

    @pyproperty()
    def get___doc__(self) -> Optional[PyStrRef]:
        return self.value.doc

    @pyproperty()
    def get___self__(self, vm: VirtualMachine) -> PyObjectRef:
        return vm.ctx.get_none()

    @pymethod(True)
    def i__reduce__(self, vm: VirtualMachine) -> PyStrRef:
        return self.get___name__()

    @pymethod(True)
    def i__reduce_ex__(self, ver: PyObjectRef, vm: VirtualMachine) -> PyStrRef:
        return self.get___name__()

    @pymethod(True)
    def i__repr__(self, vm: VirtualMachine) -> str:
        return f"<built-in function {self.value.name}>"

    @pyproperty()
    def get_text_signature(self, vm: VirtualMachine) -> Optional[str]:
        doc = self.value.doc
        if doc is None:
            return None
        return pytype.get_text_signature_from_internal_doc(
            self.value.name._.as_str(), doc._.as_str()
        )

    @classmethod
    def call(
        cls, zelf: PyRef[PyBuiltinFunction], args: FuncArgs, vm: VirtualMachine
    ) -> PyObjectRef:
        return zelf._.value.func(vm, args)


@po.tp_flags(method_descr=True)
@po.pyimpl(get_descriptor=True, callable=True, constructor=False)
@po.pyclass(name="method_descriptor")
@dataclass
class PyBuiltinMethod(po.PyClassImpl, slot.CallableMixin, slot.GetDescriptorMixin):
    value: PyNativeFuncDef
    klass: PyTypeRef

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.method_descriptor_type

    @classmethod
    def descr_get(
        cls,
        zelf: PyObjectRef,
        obj: Optional[PyObjectRef],
        class_: Optional[PyObjectRef],
        vm: VirtualMachine,
    ) -> PyObjectRef:
        try:
            zelf_, robj = cls._check(zelf, obj, vm)
        except PyImplError as e:
            return e.obj
        if vm.is_none(robj) and not cls._cls_is(class_, robj.class_()):
            return zelf
        else:
            return PyBoundMethod.new_ref(robj, zelf_, vm.ctx)

    @staticmethod
    def new_ref(
        name: PyStr, class_: PyTypeRef, f: PyNativeFunc, ctx: PyContext
    ) -> PyRef[PyBuiltinMethod]:
        return ctx.make_funcdef(name, f).build_method(ctx, class_)

    @pyproperty()
    def get___name__(self) -> PyStrRef:
        return self.value.name

    @pyproperty()
    def get___qualname__(self) -> str:
        return f"{self.klass._.name()}.{self.value.name}"

    @pyproperty()
    def get___doc__(self) -> Optional[PyStrRef]:
        return self.value.doc

    @pyproperty()
    def get_text_signature(self) -> Optional[str]:
        doc = self.value.doc
        if doc is None:
            return None
        return pytype.get_text_signature_from_internal_doc(
            self.value.name._.as_str(), doc._.as_str()
        )

    @pymethod(True)
    def i__repr__(self, vm: VirtualMachine) -> str:
        return f"<method '{self.value.name}' of '{self.klass._.name()}' objects"

    @classmethod
    def call(
        cls, zelf: PyRef[PyBuiltinMethod], args: FuncArgs, vm: VirtualMachine
    ) -> PyObjectRef:
        return zelf._.value.func(vm, args)


def init(context: PyContext) -> None:
    PyBuiltinFunction.extend_class(
        context, context.types.builtin_function_or_method_type
    )
    PyBuiltinMethod.extend_class(context, context.types.method_descriptor_type)
