import random
from typing import Any, Optional
from xml.sax.saxutils import escape, quoteattr

from dexml import constants, exceptions
from dexml.fields import field


class Value(field.Field):
    """Field subclass that holds a simple scalar value.

    This field.Field subclass contains the common logic to parse/render simple
    scalar value fields - fields that don't required any recursive parsing.
    Individual subclasses should provide the parse_value() and render_value()
    methods to do type coercion of the value.

    Value fields can also have a default value, specified by the 'default'
    keyword argument.

    By default, the field maps to an attribute of the model's XML node with
    the same name as the field declaration.  Consider:

        class MyModel(Model):
            my_field = fields.Value(default="test")


    This corresponds to the XML fragment "<MyModel my_field='test' />".
    To use a different name specify the 'attrname' kwd argument.  To use
    a subtag instead of an attribute specify the 'tagname' kwd argument.

    Namespaced attributes or subtags are also supported, by specifying a
    (namespace,tagname) pair for 'attrname' or 'tagname' respectively.
    """

    class Arguments(field.Field.Arguments):
        tagname = None
        attrname = None

    def __init__(self, **kwds: Any) -> None:
        super().__init__(**kwds)

    def _get_attrname(self) -> Optional[str]:
        if self.__dict__["tagname"]:
            return None
        attrname = self.__dict__["attrname"]
        if not attrname:
            attrname = self.field_name
        return attrname

    def _set_attrname(self, attrname) -> None:
        self.__dict__["attrname"] = attrname

    attrname = property(_get_attrname, _set_attrname)

    def _get_tagname(self):
        if self.__dict__["attrname"]:
            return None
        tagname = self.__dict__["tagname"]
        if tagname and not isinstance(tagname, (str, tuple)):
            tagname = self.field_name
        return tagname

    def _set_tagname(self, tagname: str) -> None:
        self.__dict__["tagname"] = tagname

    tagname = property(_get_tagname, _set_tagname)

    def parse_attributes(self, obj, attrs):
        #  Bail out if we're attached to a subtag rather than an attr.
        if self.tagname:
            return attrs
        unused = []
        attrname = self.attrname
        if isinstance(attrname, str):
            ns = None
        else:
            (ns, attrname) = attrname
        for attr in attrs:
            if attr.localName == attrname:
                if attr.namespaceURI == ns:
                    self.__set__(obj, self.parse_value(attr.nodeValue))
                else:
                    unused.append(attr)
            else:
                unused.append(attr)
        return unused

    def parse_child_node(self, obj, node):
        if not self.tagname:
            return constants.Status.PARSE_SKIP
        if self.tagname == ".":
            node = node.parentNode
        else:
            if not self._check_tagname(node, self.tagname):
                return constants.Status.PARSE_SKIP
        vals = []
        #  Merge all text nodes into a single value
        for child in node.childNodes:
            if child.nodeType not in (child.TEXT_NODE, child.CDATA_SECTION_NODE):
                raise exceptions.ParseError("non-text value node")
            vals.append(child.nodeValue)
        self.__set__(obj, self.parse_value("".join(vals)))
        return constants.Status.PARSE_DONE

    def render_attributes(self, obj, val, nsmap):
        if val is not None and self.attrname:
            qaval = quoteattr(self.render_value(val))
            if isinstance(self.attrname, str):
                yield f"{self.attrname}={qaval}"
            else:
                m_meta = self.model_class.meta
                (ns, nm) = self.attrname
                if ns == m_meta.namespace and m_meta.namespace_prefix:
                    prefix = m_meta.namespace_prefix
                    yield f"{prefix}:{nm}={qaval}"
                elif ns is None:
                    yield f"{nm}={qaval}"
                else:
                    for (p, n) in iter(nsmap.items()):
                        if ns == n[0]:
                            prefix = p
                            break
                    else:
                        prefix = "p" + str(random.randint(0, 10000))
                        while prefix in nsmap:
                            prefix = "p" + str(random.randint(0, 10000))
                        yield f'xmlns:{prefix}="{ns}"'
                    yield f"{prefix}:{nm}={qaval}"

    def render_children(self, obj, val, nsmap, use_field_names=False):
        tagname = self.tagname
        if val is not None and tagname:
            val = self._esc_render_value(val)
            if tagname == ".":
                yield val
            else:
                if use_field_names:
                    tagname = self.field_name
                attrs = ""
                #  By default, tag values inherit the namespace of their
                #  containing model class.
                if isinstance(tagname, str):
                    prefix = self.model_class.meta.namespace_prefix
                    localName = tagname
                else:
                    m_meta = self.model_class.meta
                    (ns, localName) = tagname
                    if not ns:
                        #  If we have an explicitly un-namespaced tag,
                        #  we need to be careful.  The model tag might have
                        #  set the default namespace, which we need to undo.
                        prefix = None
                        if m_meta.namespace and not m_meta.namespace_prefix:
                            attrs = ' xmlns=""'
                    elif ns == m_meta.namespace:
                        prefix = m_meta.namespace_prefix
                    else:
                        for (p, n) in iter(nsmap.items()):
                            if ns == n[0]:
                                prefix = p
                                break
                        else:
                            prefix = "p" + str(random.randint(0, 10000))
                            while prefix in nsmap:
                                prefix = "p" + str(random.randint(0, 10000))
                            attrs = ' xmlns:%s="%s"' % (prefix, ns)
                yield self._render_tag(val, prefix, localName, attrs)

    def _render_tag(self, val, prefix, localName, attrs):
        if val:
            if prefix:
                return f"<{prefix}:{localName}{attrs}>{val}</{prefix}:{localName}>"
            return f"<{localName}{attrs}>{val}</{localName}>"
        if prefix:
            return f"<{prefix}:{localName}{attrs} />"
        return f"<{localName}{attrs} />"

    def parse_value(self, val):
        return val

    def render_value(self, val):
        if not isinstance(val, str):
            val = str(val)
        return val

    def _esc_render_value(self, val):
        return escape(self.render_value(val))


class String(Value):
    """Field representing a simple string value."""

    # actually, the base Value() class will do this automatically.


class CDATA(Value):
    """String field rendered as CDATA."""

    def __init__(self, **kwds):
        super().__init__(**kwds)
        if self.__dict__.get("tagname", None) is None:
            raise ValueError("CDATA fields must have a tagname")

    def _esc_render_value(self, val):
        val = self.render_value(val)
        val = val.replace("]]>", "]]]]><![CDATA[>")
        return "<![CDATA[" + val + "]]>"


class Integer(Value):
    """Field representing a simple integer value."""

    def parse_value(self, val):
        return int(val)


class Float(Value):
    """Field representing a simple float value."""

    def parse_value(self, val):
        return float(val)


class Boolean(Value):
    """Field representing a simple boolean value.

    The strings corresponding to false are 'no', 'off', 'false' and '0',
    compared case-insensitively.  Note that this means an empty tag or
    attribute is considered True - this is usually what you want, since
    a completely missing attribute or tag can be interpreted as False.

    To enforce that the presence of a tag indicates True and the absence of
    a tag indicates False, pass the keyword argument "empty_only".
    """

    empty_only: bool

    class Arguments(Value.Arguments):
        empty_only = False

    def __init__(self, **kwds):
        super().__init__(**kwds)
        if self.empty_only:
            self.required = False

    def __set__(self, instance, value):
        instance.__dict__[self.field_name] = bool(value)

    def parse_value(self, val):
        if self.empty_only and val != "":
            raise ValueError("non-empty value in empty_only Boolean")
        if val.lower() in ("no", "off", "false", "0"):
            return False
        return True

    def render_children(self, obj, val, nsmap, use_field_names=False):
        if not val and self.empty_only:
            return []
        return super().render_children(obj, val, nsmap, use_field_names=use_field_names)

    def render_attributes(self, obj, val, nsmap):
        if not val and self.empty_only:
            return []
        return super().render_attributes(obj, val, nsmap)

    def render_value(self, val):
        if not val:
            return "false"
        if self.empty_only:
            return ""
        return "true"
