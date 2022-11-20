from xml.dom import minidom

from dexml import constants, exceptions
from dexml.meta import ModelMetaclass


class Model(metaclass=ModelMetaclass):
    """Base class for dexml Model objects.

    Subclasses of Model represent a concrete type of object that can parsed
    from or rendered to an XML document.  The mapping to/from XML is controlled
    by two things:

        * attributes declared on an inner class named 'meta'
        * fields declared using instances of fields.Field

    Here's a quick example:

        class Person(dexml.Model):
            # This overrides the default tagname of 'Person'
            class meta
                tagname = "person"
            # This maps to a 'name' attributr on the <person> tag
            name = fields.String()
            # This maps to an <age> tag within the <person> tag
            age = fields.Integer(tagname='age')

    See the 'Meta' class in this module for available meta options, and the
    'fields' submodule for available field types.
    """

    _fields = []
    meta = None

    def __init__(self, **kwds):
        """Default Model constructor.

        Keyword arguments that correspond to declared fields are processed
        and assigned to that field.
        """
        for field in self._fields:
            try:
                setattr(self, field.field_name, kwds[field.field_name])
            except KeyError:
                pass

    @classmethod
    def parse(cls, xml, tagname=None):
        """Produce an instance of this model from some xml.

        The given xml can be a string, a readable file-like object, or
        a DOM node; we might add support for more types in the future.
        """
        self = cls()
        node = self._make_xml_node(xml)
        self.validate_xml_node(node, tagname)
        #  Keep track of fields that have successfully parsed something
        fields_found = []
        #  Try to consume all the node's attributes
        attrs = node.attributes.values()
        for field in self._fields:
            unused_attrs = field.parse_attributes(self, attrs)
            if len(unused_attrs) < len(attrs):
                fields_found.append(field)
            attrs = unused_attrs
        for attr in attrs:
            self._handle_unparsed_node(attr)
        #  Try to consume all child nodes
        if self.meta.order_sensitive:
            self._parse_children_ordered(node, self._fields, fields_found)
        else:
            self._parse_children_unordered(node, self._fields, fields_found)
        #  Check that all required fields have been found
        for field in self._fields:
            if field.required and field not in fields_found:
                err = "required field not found: '%s'" % (field.field_name,)
                raise exceptions.ParseError(err)
            field.parse_done(self)
        #  All done, return the instance so created
        return self

    def _parse_children_ordered(self, node, fields, fields_found):
        """Parse the children of the given node using strict field ordering."""
        cur_field_idx = 0
        for child in node.childNodes:
            idx = cur_field_idx
            #  If we successfully break out of this loop, one of our
            #  fields has consumed the node.
            while idx < len(fields):
                field = fields[idx]
                res = field.parse_child_node(self, child)
                if res is constants.Status.PARSE_DONE:
                    if field not in fields_found:
                        fields_found.append(field)
                    cur_field_idx = idx + 1
                    break
                if res is constants.Status.PARSE_MORE:
                    if field not in fields_found:
                        fields_found.append(field)
                    cur_field_idx = idx
                    break
                if res is constants.Status.PARSE_CHILDREN:
                    if field not in fields_found:
                        fields_found.append(field)
                    self._parse_children_ordered(child, [field], fields_found)
                    cur_field_idx = idx
                    break
                idx += 1
            else:
                self._handle_unparsed_node(child)

    def _parse_children_unordered(self, node, fields, fields_found):
        """Parse the children of the given node using loose field ordering."""
        done_fields = {}
        for child in node.childNodes:
            idx = 0
            #  If we successfully break out of this loop, one of our
            #  fields has consumed the node.
            while idx < len(fields):
                if idx in done_fields:
                    idx += 1
                    continue
                field = fields[idx]
                res = field.parse_child_node(self, child)
                if res is constants.Status.PARSE_DONE:
                    done_fields[idx] = True
                    if field not in fields_found:
                        fields_found.append(field)
                    break
                if res is constants.Status.PARSE_MORE:
                    if field not in fields_found:
                        fields_found.append(field)
                    break
                if res is constants.Status.PARSE_CHILDREN:
                    if field not in fields_found:
                        fields_found.append(field)
                    self._parse_children_unordered(child, [field], fields_found)
                    break
                idx += 1
            else:
                self._handle_unparsed_node(child)

    def _handle_unparsed_node(self, node):
        if not self.meta.ignore_unknown_elements:
            if node.nodeType == node.ELEMENT_NODE:
                err = "unknown element: %s" % (node.nodeName,)
                raise exceptions.ParseError(err)
            if node.nodeType in (node.TEXT_NODE, node.CDATA_SECTION_NODE):
                if node.nodeValue.strip():
                    err = "unparsed text node: %s" % (node.nodeValue,)
                    raise exceptions.ParseError(err)
            if node.nodeType == node.ATTRIBUTE_NODE:
                if not node.nodeName.startswith("xml"):
                    err = "unknown attribute: %s" % (node.name,)
                    raise exceptions.ParseError(err)

    def render(self, encoding=None, fragment=False, pretty=False, nsmap=None):
        """Produce XML from this model's instance data.

        A unicode string will be returned if any of the objects contain
        unicode values; specifying the 'encoding' argument forces generation
        of a bytestring.

        By default a complete XML document is produced, including the
        leading "<?xml>" declaration.  To generate an XML fragment set
        the 'fragment' argument to True.
        """
        if nsmap is None:
            nsmap = {}
        data = []
        header = '<?xml version="1.0" ?>'
        if encoding:
            header = '<?xml version="1.0" encoding="%s" ?>' % (encoding,)
        if not fragment:
            data.append(header)

        data.extend(self._render(nsmap))
        xml = "".join(data)
        if pretty:
            xml = minidom.parseString(xml).toprettyxml()
            # Hack for removing the `<?xml version="1.0"?>` header that
            # minidom adds when pretty printing.
            line_break_position = xml.find("\n") + 1
            headless_xml = xml[line_break_position:]
            if fragment:
                xml = headless_xml
            elif encoding:
                # Minidom also removes the header (or just the `encoding` key)
                # if it is present
                xml = header + "\n" + headless_xml
        if encoding:
            xml = xml.encode(encoding)
        return xml

    def irender(self, encoding=None, fragment=False, nsmap=None):
        """Generator producing XML from this model's instance data.

        If any of the objects contain unicode values, the resulting output
        stream will be a mix of bytestrings and unicode; specify the 'encoding'
        arugment to force generation of bytestrings.

        By default a complete XML document is produced, including the
        leading "<?xml>" declaration.  To generate an XML fragment set
        the 'fragment' argument to True.
        """
        if nsmap is None:
            nsmap = {}
        if not fragment:
            if encoding:
                decl = f'<?xml version="1.0" encoding="{encoding}" ?>'
                yield decl.encode(encoding)
            else:
                yield '<?xml version="1.0" ?>'
        if encoding:
            for data in self._render(nsmap):
                if isinstance(data, str):
                    data = data.encode(encoding)
                yield data
        else:
            for data in self._render(nsmap):
                yield data

    def _render(self, nsmap, tagname=None):
        """Generator rendering this model as an XML fragment."""
        #  Determine opening and closing tags
        pushed_ns = False
        if not tagname:
            tagname = self.meta.tagname
        if self.meta.namespace:
            namespace = self.meta.namespace
            prefix = self.meta.namespace_prefix
            try:
                cur_ns = nsmap[prefix]
            except KeyError:
                cur_ns = []
                nsmap[prefix] = cur_ns
            if prefix:
                tagname = f"{prefix}:{tagname}"
                open_tag_contents = [tagname]
                if not cur_ns or cur_ns[0] != namespace:
                    cur_ns.insert(0, namespace)
                    pushed_ns = True
                    open_tag_contents.append(f'xmlns:{prefix}="{namespace}"')
                close_tag_contents = tagname
            else:
                open_tag_contents = [tagname]
                if not cur_ns or cur_ns[0] != namespace:
                    cur_ns.insert(0, namespace)
                    pushed_ns = True
                    open_tag_contents.append(f'xmlns="{namespace}"')
                close_tag_contents = tagname
        else:
            open_tag_contents = [tagname]
            close_tag_contents = tagname
        used_fields = set()
        open_tag_contents.extend(self._render_attributes(used_fields, nsmap))
        #  Render each child node
        children = self._render_children(used_fields, nsmap)
        try:
            first_child = next(children)
        except StopIteration:
            yield f'<{" ".join(open_tag_contents)} />'
        else:
            yield f'<{" ".join(open_tag_contents)}>'
            yield first_child
            for child in children:
                yield child
            yield f"</{close_tag_contents}>"
        #  Check that all required fields actually rendered something
        for field in self._fields:
            if field.required and field not in used_fields:
                raise exceptions.RenderError(
                    "Field '%s' is missing" % (field.field_name,)
                )
        #  Clean up
        if pushed_ns:
            nsmap[prefix].pop(0)

    def _render_attributes(self, used_fields, nsmap):
        for field in self._fields:
            val = getattr(self, field.field_name)
            datas = iter(field.render_attributes(self, val, nsmap))
            try:
                data = next(datas)
            except StopIteration:
                pass
            else:
                used_fields.add(field)
                yield data
                for data in datas:
                    yield data

    def _render_children(self, used_fields, nsmap):
        for field in self._fields:
            val = getattr(self, field.field_name)
            datas = iter(field.render_children(self, val, nsmap))
            try:
                data = next(datas)
            except StopIteration:
                pass
            else:
                used_fields.add(field)
                yield data
                for data in datas:
                    yield data

    @staticmethod
    def _make_xml_node(xml):
        """Transform a variety of input formats to an XML DOM node."""
        try:
            ntype = xml.nodeType
        except AttributeError as exc:
            if isinstance(xml, bytes):
                try:
                    xml = minidom.parseString(xml)
                except Exception as exception:
                    raise exceptions.XmlError(exception)
            elif isinstance(xml, str):
                try:
                    #  Try to grab the "encoding" attribute from the XML.
                    #  It probably won't exist, so default to utf8.
                    encoding = constants.XML_ENCODING_RE.match(xml)
                    if encoding is None:
                        encoding = "utf8"
                    else:
                        encoding = encoding.group(1)
                    xml = minidom.parseString(xml.encode(encoding))
                except Exception as exception:
                    raise exceptions.XmlError(exception)
            elif hasattr(xml, "read"):
                try:
                    xml = minidom.parse(xml)
                except Exception as exception:
                    raise exceptions.XmlError(exception)
            else:
                raise ValueError("Can't convert that to an XML DOM node") from exc
            node = xml.documentElement
        else:
            if ntype == xml.DOCUMENT_NODE:
                node = xml.documentElement
            else:
                node = xml
        return node

    @classmethod
    def validate_xml_node(cls, node, tagname=None):
        """Check that the given xml node is valid for this object.

        Here 'valid' means that it is the right tag, in the right
        namespace.  We might add more eventually...
        """
        if node.nodeType != node.ELEMENT_NODE:
            err = "Class '%s' got a non-element node"
            err = err % (cls.__name__,)
            raise exceptions.ParseError(err)
        if cls.meta.case_sensitive:
            if not (cls.meta.tagname and node.localName == cls.meta.tagname) and not (
                tagname and tagname == node.localName
            ):
                err = "Class '%s' got tag '%s' (expected '%s')"
                err = err % (cls.__name__, node.localName, cls.meta.tagname)
                raise exceptions.ParseError(err)
        else:
            if not (node.localName.lower() == cls.meta.tagname.lower()) and not (
                tagname and tagname.lower() == node.localName.lower()
            ):
                err = "Class '%s' got tag '%s' (expected '%s')"
                err = err % (cls.__name__, node.localName, cls.meta.tagname)
                raise exceptions.ParseError(err)
        if cls.meta.namespace:
            if node.namespaceURI != cls.meta.namespace:
                err = "Class '%s' got namespace '%s' (expected '%s')"
                err = err % (cls.__name__, node.namespaceURI, cls.meta.namespace)
                raise exceptions.ParseError(err)
        else:
            if node.namespaceURI:
                err = "Class '%s' got namespace '%s' (expected no namespace)"
                err = err % (
                    cls.__name__,
                    node.namespaceURI,
                )
                raise exceptions.ParseError(err)
