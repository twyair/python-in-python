from __future__ import annotations

import itertools
from dataclasses import dataclass
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Iterable,
    Optional,
    TypeAlias,
    TypeVar,
)
from common.error import unreachable

if TYPE_CHECKING:
    from vm.builtins.pystr import PyStrRef
    from vm.function_ import FuncArgs
    from common.error import PyImplErrorStr
    from vm.pyobjectrc import PyObjectRef, PyRef
    from vm.types.slot import PyTypeSlots
    from vm.vm import VirtualMachine
    from vm.pyobject import PyAttributes

import vm.types.slot as slot
import vm.pyobject as po
import vm.pyobjectrc as prc


def take_next_base(bases: list[list[PyTypeRef]]) -> Optional[PyTypeRef]:
    for base in bases:
        head = base[0]
        if not any(any(y.is_(head) for y in x[1:]) for x in bases):
            for item in bases:
                if item[0].is_(head):
                    item.pop(0)
            return head
    return None


def linearise_mro(bases: list[list[PyTypeRef]]) -> list[PyTypeRef]:
    for i, base_mro in enumerate(bases):
        base = base_mro[0]
        for later_mro in bases[i + 1 :]:
            if any(cls.is_(base) for cls in later_mro[1:]):
                raise PyImplErrorStr(
                    "Unable to find mro order which keeps local precedence ordering"
                )

    result = []
    while bases:
        head = take_next_base(bases)
        if head is None:
            raise PyImplErrorStr(
                "Cannot create a consistent method resolution order (MRO) for bases {}".format(
                    ", ".join(x[0]._.name() for x in bases)
                )
            )
        result.append(head)
        bases = [x for x in bases if x]

    return result


R = TypeVar("R")


@po.tp_flags(basetype=True)
@po.pyimpl(get_attr=True, set_attr=True, callable=True)
@po.pyclass("type")
@dataclass
class PyType(
    po.TryFromObjectMixin,
    po.PyClassImpl,
    po.PyValueMixin,
    slot.CallableMixin,
    slot.SetAttrMixin,
    slot.GetAttrMixin,
):
    base: Optional[PyTypeRef]
    bases: list[PyTypeRef]
    mro_: list[PyTypeRef]
    # subclasses: list[po.PyObjectWeak]
    subclasses: list[PyObjectRef]
    attributes: PyAttributes
    slots: PyTypeSlots

    def into_ref(self: PyType, vm: VirtualMachine) -> PyTypeRef:
        return prc.PyRef.new_ref(self, vm.ctx.types.type_type, None)

    @classmethod
    def class_(cls, vm: VirtualMachine) -> PyTypeRef:
        return vm.ctx.types.type_type

    @staticmethod
    def new_simple_ref(name: str, base: PyTypeRef):
        return PyType.new_ref(
            name,
            [base.clone()],
            po.PyAttributes(),
            PyTypeSlots.default(),
            PyType.static_type().clone(),
        )

    @staticmethod
    def new_ref(
        name: str,
        bases: list[PyTypeRef],
        attrs: PyAttributes,
        slots: PyTypeSlots,
        metaclass: PyTypeRef,
    ) -> PyTypeRef:
        return PyType.new_verbose_ref(
            name, bases[0].clone(), bases, attrs, slots, metaclass
        )

    @staticmethod
    def new_verbose_ref(
        name: str,
        base: PyTypeRef,
        bases: list[PyTypeRef],
        attrs: PyAttributes,
        slots: PyTypeSlots,
        metaclass: PyTypeRef,
    ) -> PyTypeRef:
        unique_bases = set()
        for base in bases:
            if base.get_id() in unique_bases:
                PyImplErrorStr(f"duplicate base class {base._.name()}")
            unique_bases.add(base.get_id())

        mros = [[x] + [c for c in x._.iter_mro_ref()] for x in bases]
        mro = linearise_mro(mros)

        if base._.slots.flags.has_feature(slot.PyTypeFlags.HAS_DICT):
            slots.flags |= slot.PyTypeFlags.HAS_DICT

        slots.name = name

        new_type = prc.PyRef.new_ref(
            PyType(base, bases, mro, [], attrs, slots), metaclass, None
        )

        for attr_name in attrs:
            if attr_name.startswith("__") and attr_name.endswith("__"):
                new_type._.update_slot(attr_name, True)

        # weakref_type = po.PyWeak.static_type()
        for base in bases:
            base._.subclasses.append(new_type)
            # FIXME?
            # new_type.as_object().downgrade_with_weakref_typ_opt(
            #     None, weakref_type.clone()
            # )

        return new_type

    # original name: "__new__"
    @staticmethod
    def s__new__(
        zelf: PyRef[PyType], args: FuncArgs, vm: VirtualMachine
    ) -> PyObjectRef:
        raise NotImplementedError

    def slot_name(self) -> str:
        assert self.slots.name is not None
        return self.slots.name

    def iter_mro(self) -> Iterable[PyType]:
        return itertools.chain([self], (cls._ for cls in self.mro_))

    def iter_mro_ref(self) -> Iterable[PyTypeRef]:
        return (cls for cls in self.mro_)

    def mro_find_map(self, f: Callable[[PyType], Optional[R]]) -> Optional[R]:
        if (r := f(self)) is not None:
            return r
        else:
            return next((f(cls._) for cls in self.mro_), None)

    def set_str_attr(self, attr_name: str, value: PyObjectRef) -> None:
        self.attributes[attr_name] = value

    def get_attr(self, attr_name: str) -> Optional[PyObjectRef]:
        res = self.get_direct_attr(attr_name)
        if res is not None:
            return res
        return self.get_super_attr(attr_name)

    def get_direct_attr(self, attr_name: str) -> Optional[PyObjectRef]:
        return self.attributes.get(attr_name, None)

    def get_super_attr(self, attr_name: str) -> Optional[PyObjectRef]:
        return next(
            (
                v
                for v in (cls._.attributes.get(attr_name, None) for cls in self.mro_)
                if v is not None
            ),
            None,
        )

    def has_attr(self, attr_name: str) -> bool:
        return any(attr_name in c.attributes for c in self.iter_mro())

    def get_attributes(self) -> PyAttributes:
        attributes = po.PyAttributes()
        for bc in reversed(list(self.iter_mro())):
            for name, value in bc.attributes.items():
                attributes[name] = value.clone()
        return attributes

    def get_id(self) -> int:
        return id(self)

    def is_(self, other: Any) -> bool:
        return self.get_id() == other.get_id()

    def issubclass(self, other: PyTypeRef) -> bool:
        return self.is_(other) or any(c.is_(other) for c in self.mro_)

    def name(self) -> str:
        name = self.slots.name
        assert name is not None
        if self.slots.flags.has_feature(slot.PyTypeFlags.HEAPTYPE):
            return name
        else:
            return name.rsplit(".")[0]

    def update_slot(self, name: str, add: bool) -> None:
        assert name.startswith("__") and name.endswith("__"), name

        def foo(func):
            if add:
                return func
            else:
                return None

        if name in ("__len__", "__getitem__", "__setitem__", "__delitem__"):
            self.slots.as_mapping = foo(slot.as_mapping_wrapper)
            self.slots.as_sequence = foo(slot.as_sequence_wrapper)
        elif name == "__hash__":
            self.slots.hash = foo(slot.hash_wrapper)
        elif name == "__call__":
            self.slots.call = foo(slot.call_wrapper)
        elif name == "__getattribute__":
            self.slots.getattro = foo(slot.getattro_wrapper)
        elif name in ("__setattr__", "__delattr__"):
            self.slots.setattro = foo(slot.setattro_wrapper)
        elif name in ("__eq__", "__ne__", "__le__", "__lt__", "__ge__", "__gt__"):
            self.slots.richcompare = foo(slot.richcompare_wrapper)
        elif name == "__iter__":
            self.slots.iter = foo(slot.iter_wrapper)
        elif name == "__next__":
            self.slots.iternext = foo(slot.iternext_wrapper)
        elif name == "__get__":
            self.slots.descr_get = foo(slot.descr_get_wrapper)
        elif name in ("__set__", "__delete__"):
            self.slots.descr_set = foo(slot.descr_set_wrapper)
        elif name == "__new__":
            self.slots.new = foo(slot.new_wrapper)
        elif name == "__del__":
            self.slots.del_ = foo(slot.del_wrapper)
        else:
            pass

    # TODO: impl PyType @ 216

    @classmethod
    def call(
        cls, zelf: PyRef[PyType], args: FuncArgs, vm: VirtualMachine
    ) -> PyObjectRef:
        obj = call_slot_new(zelf, zelf, args, vm)

        if (
            zelf.is_(vm.ctx.types.type_type)
            and not args.kwargs
            or not obj.isinstance(zelf)
        ):
            return obj

        init_method = vm.get_method(obj, "__init__")
        if init_method is not None:
            res = vm.invoke(init_method, args)
            if not vm.is_none(res):
                vm.new_type_error("__init__ must return None")

        return obj

    @classmethod
    def setattro(
        cls,
        zelf: PyRef[PyType],
        name: PyStrRef,
        value: Optional[PyObjectRef],
        vm: VirtualMachine,
    ) -> None:
        attr_name = name._.as_str()
        if (attr := zelf.get_class_attr(name._.as_str())) is not None:
            descr_set = attr.class_()._.mro_find_map(lambda cls: cls.slots.descr_set)
            if descr_set is not None:
                return descr_set(attr, zelf, value, vm)

        assign = value is not None

        attributes = zelf._.attributes
        if value is not None:
            attributes[name._.as_str()] = value
        else:
            prev_value = attributes.remove(attr_name)
            if prev_value is None:
                vm.new_exception(vm.ctx.exceptions.attribute_error, [name])

        if attr_name.startswith("__") and attr_name.endswith("__"):
            zelf._.update_slot(attr_name, assign)

    @classmethod
    def getattro(
        cls, zelf: PyRef[PyType], name: PyStrRef, vm: VirtualMachine
    ) -> PyObjectRef:
        mcl = zelf.class_()._
        mcl_attr = mcl.get_attr(name._.as_str())
        if mcl_attr is not None:
            attr_class = mcl_attr.class_()._
            if attr_class.mro_find_map(lambda cls: cls.slots.descr_set) is not None:
                if (
                    descr_get := attr_class.mro_find_map(
                        lambda cls: cls.slots.descr_get
                    )
                ) is not None:
                    descr_get(mcl_attr, zelf, mcl.into_ref(vm), vm)

        zelf_attr = zelf._.get_attr(name._.as_str())

        if zelf_attr is not None:
            if descr_get := zelf_attr.class_()._.mro_find_map(
                lambda cls: cls.slots.descr_get
            ):
                return descr_get(zelf_attr, None, zelf, vm)

        if zelf_attr is not None:
            return zelf_attr
        elif mcl_attr is not None:
            return vm.call_if_get_descriptor(mcl_attr, zelf)
        else:
            vm.new_attribute_error(
                f"type object '{zelf._.slot_name()}' has no attribute '{name._.as_str()}'"
            )


PyTypeRef: TypeAlias = "PyRef[PyType]"


def call_slot_new(
    typ: PyTypeRef, subtype: PyTypeRef, args: FuncArgs, vm: VirtualMachine
) -> PyObjectRef:
    for cls in typ._.iter_mro():
        if (slot_new := cls.slots.new) is not None:
            return slot_new(subtype, args, vm)
    unreachable("Should be able to find a new slot somewhere in the mro")


SIGNATURE_END_MARKER = ")\n--\n\n"


def get_signature(doc: str) -> Optional[str]:
    i = doc.find(SIGNATURE_END_MARKER)
    if i != -1:
        return doc[: i + 1]
    return None


def find_signature(name: str, doc: str) -> Optional[str]:
    name = name.rsplit(".", 1)[-1]
    doc = doc[len(name) :]
    if not doc.startswith("("):
        return None
    else:
        return doc


def get_text_signature_from_internal_doc(name: str, internal_doc: str) -> Optional[str]:
    r = find_signature(name, internal_doc)
    if r is None:
        return None
    return get_signature(r)


def init(ctx: po.PyContext) -> None:
    PyType.extend_class(ctx, ctx.types.type_type)
