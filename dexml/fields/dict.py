from dexml import constants, exceptions
from dexml.fields import field as dexml_field
from dexml.fields import model as model_field


class Dict(dexml_field.Field):
    """Field subclass representing a dict of fields keyed by unique attribute value.

    This field corresponds to an indexed dict of other fields.  You would
    declare it like so:

      class MyObject(Model):
          name = fields.String(tagname = 'name')
          attr = fields.String(tagname = 'attr')

      class MyModel(Model):
          items = fields.Dict(fields.Model(MyObject), key = 'name')

    Corresponding to XML such as:

      <MyModel><MyObject><name>obj1</name><attr>val1</attr></MyObject></MyModel>


    The properties 'minlength' and 'maxlength' control the allowable size
    of the dict as in the List class.

    If 'unique' property is set to True, parsing will raise exception on
    non-unique key values.

    The 'dictclass' property controls the internal dict-like class used by
    the fielt.  By default it is the standard dict class.

    The 'tagname' property sets the 'wrapper' tag which acts as container
    for dict items, for example:

      from collections import defaultdict
      class MyObject(Model):
          name = fields.String()
          attr = fields.String()

      class MyDict(defaultdict):
          def __init__(self):
              super().__init__(MyObject)

      class MyModel(Model):
          objects = fields.Dict('MyObject', key = 'name',
                                tagname = 'dict', dictclass = MyDict)

      xml = '<MyModel><dict><MyObject name="obj1">'\
            <attr>val1</attr></MyObject></dict></MyModel>'
      mymodel = MyModel.parse(xml)
      obj2 = mymodel['obj2']
      print(obj2.name)
      print(mymodel.render(fragment = True))

    This wrapper tag is always rendered, even if the dict is empty.  It is
    transparently removed when parsing.
    """

    field: str
    minlength: int
    maxlength: int
    unique: bool
    tagname: str
    dictclass: dict

    class Arguments(dexml_field.Field.Arguments):
        field = None
        minlength = None
        maxlength = None
        unique = False
        tagname = None
        dictclass = dict

    def __init__(self, field, key, **kwds):
        if isinstance(field, dexml_field.Field):
            kwds["field"] = field
        else:
            model_kwds = kwds.copy()
            if "tagname" in model_kwds:
                model_kwds.pop("tagname")
            kwds["field"] = model_field.Model(field, **model_kwds)
        super().__init__(**kwds)
        if not self.minlength and not self.tagname:
            self.required = False
        if self.minlength and not self.required:
            raise ValueError("Dict must be required if it has minlength")
        self.key = key

    def _get_field(self):
        field = self.__dict__["field"]
        if not hasattr(field, "field_name"):
            field.field_name = self.field_name
        if not hasattr(field, "model_class"):
            field.model_class = self.model_class
        return field

    def _set_field(self, field):
        self.__dict__["field"] = field

    field = property(_get_field, _set_field)

    def __get__(self, instance, owner=None):
        val = super().__get__(instance, owner)
        if val is not None:
            return val

        class dictclass(self.dictclass):
            key = self.key

            def __setitem__(self, key, value):
                keyval = getattr(value, self.key)
                if keyval and keyval != key:
                    raise ValueError("Key field value does not match dict key")
                setattr(value, self.key, key)
                super().__setitem__(key, value)

        self.__set__(instance, dictclass())
        return self.__get__(instance, owner)

    def parse_child_node(self, obj, node):
        #  If our children are inside a grouping tag, parse
        #  that first.  The presence of this is indicated by
        #  setting an empty dict on the target object.
        if self.tagname:
            val = super().__get__(obj)
            if val is None:
                if node.nodeType != node.ELEMENT_NODE:
                    return constants.Status.PARSE_SKIP
                if node.tagName == self.tagname:
                    self.__get__(obj)
                    return constants.Status.PARSE_CHILDREN
                return constants.Status.PARSE_SKIP
        #  Now we just parse each child node.
        tmpobj = dexml_field.AttrBucket()
        res = self.field.parse_child_node(tmpobj, node)
        if res is constants.Status.PARSE_MORE:
            raise ValueError("items in a dict cannot return PARSE_MORE")
        if res is constants.Status.PARSE_DONE:
            items = self.__get__(obj)
            val = getattr(tmpobj, self.field_name)
            try:
                key = getattr(val, self.key)
            except AttributeError:
                raise exceptions.ParseError(
                    "Key field '%s' required but not found in dict value" % (self.key,)
                )
            if self.unique and key in items:
                raise exceptions.ParseError("Key '%s' already exists in dict" % (key,))
            items[key] = val
            return constants.Status.PARSE_MORE
        else:
            return constants.Status.PARSE_SKIP

    def parse_done(self, obj):
        items = self.__get__(obj)
        if self.minlength is not None and len(items) < self.minlength:
            raise exceptions.ParseError(f"Field '{self.field_name}': not enough items")
        if self.maxlength is not None and len(items) > self.maxlength:
            raise exceptions.ParseError("Field '{self.field_name}': too many items")

    def render_children(self, obj, items, nsmap):
        if self.minlength is not None and len(items) < self.minlength:
            raise exceptions.RenderError(f"Field '{self.field_name}': not enough items")
        if self.maxlength is not None and len(items) > self.maxlength:
            raise exceptions.RenderError("too many items")
        if self.tagname:
            children = "".join(
                data
                for item in items.values()
                for data in self.field.render_children(obj, item, nsmap)
            )
            if not children:
                if self.required:
                    yield f"<{self.tagname} />"
            else:
                yield children.join((f"<{self.tagname}>", f"</{self.tagname}>"))
        else:
            for item in items.values():
                for data in self.field.render_children(obj, item, nsmap):
                    yield data
