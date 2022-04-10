from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar, Optional
from common.deco import pymethod, pyproperty

if TYPE_CHECKING:
    from vm.builtins.staticmethod import PyStaticMethod
    from vm.function_ import FuncArgs
    from vm.pyobject import PyContext
    from vm.pyobjectrc import PyObjectRef, PyRef
    from vm.builtins.pystr import PyStr, PyStrRef
    from vm.builtins.pytype import PyTypeRef, get_text_signature_from_internal_doc
    from vm.vm import VirtualMachine
    from vm.function_ import PyNativeFunc
import vm.pyobject as po
import vm.pyobjectrc as prc
import vm.builtins.pystr as pystr

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
@po.pyimpl()  # TODO
@po.pyclass(name="builtin_function_or_method")
@dataclass
class PyBuiltinFunction(po.PyClassImpl):
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

    @staticmethod
    def call(
        zelf: PyRef[PyBuiltinFunction], args: FuncArgs, vm: VirtualMachine
    ) -> PyObjectRef:
        return zelf.payload.value.func(vm, args)

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
    def i__reduce__(self) -> PyStrRef:
        return self.get___name__()

    @pymethod()
    def i__reduce_ex__(self, ver: PyObjectRef) -> PyStrRef:
        return self.get___name__()

    @pymethod()
    def i__repr__(self) -> str:
        return f"<built-in function {self.value.name}>"

    @pyproperty()
    def get_text_signature(self) -> Optional[str]:
        doc = self.value.doc
        if doc is None:
            return None
        return get_text_signature_from_internal_doc(
            self.value.name.payload.as_str(), doc.payload.as_str()
        )


# TODO: GetDescriptorMixin

@po.pyimpl()  # TODO
@po.pyclass(name="method_descriptor")
@dataclass
class PyBuiltinMethod(po.PyClassImpl):
    value: PyNativeFuncDef
    klass: PyTypeRef

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.method_descriptor_type

    @staticmethod
    def descr_get(
        zelf: PyObjectRef,
        obj: Optional[PyObjectRef],
        cls: Optional[PyObjectRef],
        vm: VirtualMachine,
    ) -> PyObjectRef:
        raise NotImplementedError

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
        return f"{self.klass.payload.name()}.{self.value.name}"

    @pyproperty()
    def get___doc__(self) -> Optional[PyStrRef]:
        return self.value.doc

    @pyproperty()
    def get_text_signature(self) -> Optional[str]:
        doc = self.value.doc
        if doc is None:
            return None
        return get_text_signature_from_internal_doc(
            self.value.name.payload.as_str(), doc.payload.as_str()
        )

    @pymethod(True)
    def i__repr__(self) -> str:
        return f"<method '{self.value.name}' of '{self.klass.payload.name()}' objects"


def init(context: PyContext) -> None:
    PyBuiltinFunction.extend_class(
        context, context.types.builtin_function_or_method_type
    )
    PyBuiltinMethod.extend_class(context, context.types.method_descriptor_type)
