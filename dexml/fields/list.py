from dexml import constants, exceptions
from dexml.fields import field as dexml_field
from dexml.fields import model as model_field


class List(dexml_field.Field):
    """Field subclass representing a list of fields.

    This field corresponds to a homogeneous list of other fields.  You would
    declare it like so:

      class MyModel(Model):
          items = fields.List(fields.String(tagname="item"))

    Corresponding to XML such as:

      <MyModel><item>one</item><item>two</item></MyModel>


    The properties 'minlength' and 'maxlength' control the allowable length
    of the list.

    The 'tagname' property sets an optional wrapper tag which acts as container
    for list items, for example:

      class MyModel(Model):
          items = fields.List(fields.String(tagname="item"),
                              tagname='list')

    Corresponding to XML such as:

      <MyModel><list><item>one</item><item>two</item></list></MyModel>

    This wrapper tag is always rendered, even if the list is empty.  It is
    transparently removed when parsing.
    """

    minlength: int
    maxlength: int
    tagname: str

    class Arguments(dexml_field.Field.Arguments):
        field = None
        minlength = None
        maxlength = None
        tagname = None

    def __init__(self, field, **kwds):
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
            raise ValueError("List must be required if it has minlength")

    def _get_field(self) -> dexml_field.Field:
        field = self.__dict__["field"]
        if not hasattr(field, "field_name"):
            field.field_name = self.field_name
        if not hasattr(field, "model_class"):
            field.model_class = self.model_class
        return field

    def _set_field(self, field) -> None:
        self.__dict__["field"] = field

    field = property(_get_field, _set_field)

    def __get__(self, instance, owner=None):
        val = super().__get__(instance, owner)
        if val is not None:
            return val
        self.__set__(instance, [])
        return self.__get__(instance, owner)

    def parse_child_node(self, obj, node):
        #  If our children are inside a grouping tag, parse
        #  that first.  The presence of this is indicated by
        #  setting the empty list on the target object.
        if self.tagname:
            val = super().__get__(obj)
            if val is None:
                if node.nodeType != node.ELEMENT_NODE:
                    return constants.Status.PARSE_SKIP
                elif node.tagName == self.tagname:
                    self.__set__(obj, [])
                    return constants.Status.PARSE_CHILDREN
                else:
                    return constants.Status.PARSE_SKIP
        #  Now we just parse each child node.
        tmpobj = dexml_field.AttrBucket()
        res = self.field.parse_child_node(tmpobj, node)
        if res is constants.Status.PARSE_MORE:
            raise ValueError("items in a list cannot return PARSE_MORE")
        if res is constants.Status.PARSE_DONE:
            items = self.__get__(obj)
            val = getattr(tmpobj, self.field_name)
            items.append(val)
            return constants.Status.PARSE_MORE
        else:
            return constants.Status.PARSE_SKIP

    def parse_done(self, obj):
        items = self.__get__(obj)
        if self.minlength is not None and len(items) < self.minlength:
            raise exceptions.ParseError(
                "Field '%s': not enough items" % (self.field_name,)
            )
        if self.maxlength is not None and len(items) > self.maxlength:
            raise exceptions.ParseError(
                "Field '%s': too many items" % (self.field_name,)
            )

    def render_children(self, obj, items, nsmap):
        #  Create a generator that yields child data chunks, and validates
        #  the number of items in the list as it goes.  It allows any
        #  iterable to be passed in, not just a list.
        def child_chunks():
            num_items = 0
            for item in items:
                num_items += 1
                if self.maxlength is not None and num_items > self.maxlength:
                    msg = f"Field '{self.field_name}': too many items"
                    raise exceptions.RenderError(msg)
                for data in self.field.render_children(obj, item, nsmap):
                    yield data
            if self.minlength is not None and num_items < self.minlength:
                msg = f"Field '{self.field_name}': not enough items"
                raise exceptions.RenderError(msg)

        chunks = child_chunks()
        #  Render each chunk, but suppress the wrapper tag if there's no data.
        try:
            data = next(chunks)
        except StopIteration:
            if self.tagname and self.required:
                yield f"<{self.tagname} />"
        else:
            if self.tagname:
                yield f"<{self.tagname}>"
            yield data
            for data in chunks:
                yield data
            if self.tagname:
                yield f"</{self.tagname}>"
