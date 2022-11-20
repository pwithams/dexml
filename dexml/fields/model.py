from dexml import constants, exceptions
from dexml.fields import field as dexml_field
from dexml.meta import ModelMetaclass


class Model(dexml_field.Field):
    """Field subclass referencing another Model instance.

    This field sublcass allows Models to contain other Models recursively.
    The first argument to the field constructor must be either a Model
    class, or the name or tagname of a Model class.
    """

    class Arguments(dexml_field.Field.Arguments):
        type = None

    def __init__(self, type=None, **kwds):
        kwds["type"] = type
        self.tagname = kwds.get("tagname", None)
        super().__init__(**kwds)

    def _get_type(self):
        return self.__dict__.get("type")

    def _set_type(self, value):
        if value is not None:
            self.__dict__["type"] = value

    type = property(_get_type, _set_type)

    def __set__(self, instance, value):
        typeclass = self.typeclass
        if value and not isinstance(value, typeclass):
            raise ValueError(
                "Invalid value type %s. Model field requires %s instance"
                % (value.__class__.__name__, typeclass.__name__)
            )
        super().__set__(instance, value)

    @property
    def typeclass(self):
        try:
            return self.__dict__["typeclass"]
        except KeyError:
            self.__dict__["typeclass"] = self._load_typeclass()
            return self.__dict__["typeclass"]

    def _load_typeclass(self):
        typ = self.type
        if isinstance(typ, ModelMetaclass):
            return typ
        if typ is None:
            typ = self.field_name
        typeclass = None
        if isinstance(typ, str):
            if self.model_class.meta.namespace:
                ns = self.model_class.meta.namespace
                typeclass = ModelMetaclass.find_class(typ, ns)
            if typeclass is None:
                typeclass = ModelMetaclass.find_class(typ, None)
            if typeclass is None:
                raise ValueError("Unknown Model class: %s" % (typ,))
        else:
            (ns, typ) = typ
            if isinstance(typ, ModelMetaclass):
                return typ
            typeclass = ModelMetaclass.find_class(typ, ns)
            if typeclass is None:
                raise ValueError("Unknown Model class: (%s,%s)" % (ns, typ))
        return typeclass

    def parse_child_node(self, obj, node):
        typeclass = self.typeclass
        try:
            typeclass.validate_xml_node(node, self.tagname)
        except exceptions.ParseError:
            return constants.Status.PARSE_SKIP
        else:
            inst = typeclass.parse(node, self.tagname)
            self.__set__(obj, inst)
            return constants.Status.PARSE_DONE

    def render_attributes(self, obj, val, nsmap):
        return []

    def render_children(self, obj, val, nsmap):
        if val is not None:
            for data in val._render(nsmap, self.tagname):
                yield data
