from xml.dom import minidom

from dexml import constants
from dexml.fields import field as dexml_field


class XmlNode(dexml_field.Field):
    tagname = None
    encoding = None

    class Arguments(dexml_field.Field.Arguments):
        tagname = None
        encoding = None

    def __set__(self, instance, value):
        if isinstance(value, str):
            if isinstance(value, str) and self.encoding:
                value = value.encode(self.encoding)
            doc = minidom.parseString(value)
            value = doc.documentElement
        if value is not None and value.namespaceURI is not None:
            nsattr = "xmlns"
            if value.prefix:
                nsattr = ":".join(
                    (
                        nsattr,
                        value.prefix,
                    )
                )
            value.attributes[nsattr] = value.namespaceURI
        return super().__set__(instance, value)

    def parse_child_node(self, obj, node):
        if self.tagname is None or self._check_tagname(node, self.tagname):
            self.__set__(obj, node)
            return constants.Status.PARSE_DONE
        return constants.Status.PARSE_SKIP

    @classmethod
    def render_children(cls, obj, val, nsmap):
        if val is not None:
            yield val.toxml()
