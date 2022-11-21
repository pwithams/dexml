"""

dexml.fields:  basic field type definitions for dexml
=====================================================

"""
import xml.dom.minidom
from typing import Any, Dict, Generator, List

from dexml import constants

#  Global counter tracking the order in which fields are declared.
_order_counter = 0


class AttrBucket:
    """A simple class used only to hold attributes."""


class Field(object):
    """Base class for all dexml Field classes.

    Field classes are responsible for parsing and rendering individual
    components to the XML.  They also act as descriptors on dexml Model
    instances, to get/set the corresponding properties.

    Each field instance will magically be given the following properties:

      * model_class:  the Model subclass to which it is attached
      * field_name:   the name under which is appears on that class

    The following methods are required for interaction with the parsing
    and rendering machinery:

      * parse_attributes:    parse info out of XML node attributes
      * parse_child_node:    parse into out of an XML child node
      * render_attributes:   render XML for node attributes
      * render_children:     render XML for child nodes

    """

    required: bool
    field_name: str
    model_class: Any
    default: Any

    class Arguments:
        required = True
        default = None

    def __init__(self, **kwds: Dict[str, Any]) -> None:
        """Default Field constructor.

        This constructor keeps track of the order in which Field instances
        are created, since this information can have semantic meaning in
        XML.  It also merges any keyword arguments with the defaults
        defined on the 'arguments' inner class, and assigned these attributes
        to the Field instance.
        """
        global _order_counter
        self._order_counter = _order_counter = _order_counter + 1
        args = self.__class__.Arguments
        for argnm in dir(args):
            if not argnm.startswith("__"):
                setattr(self, argnm, kwds.get(argnm, getattr(args, argnm)))
        if self.default is not None:
            self.required = False

    def parse_attributes(
        self, obj: object, attrs: List[xml.dom.minidom.Attr]
    ) -> List[xml.dom.minidom.Attr]:
        """Parse any attributes for this field from the given list.

        This method will be called with the Model instance being parsed and
        a list of attribute nodes from its XML tag.  Any attributes of
        interest to this field should be processed, and a list of the unused
        attribute nodes returned.
        """
        return attrs

    def parse_child_node(
        self, obj: object, node: xml.dom.minidom.Element
    ) -> constants.Status:
        """Parse a child node for this field.

        This method will be called with the Model instance being parsed and
        the current child node of that model's XML tag.  There are three
        options for processing this node:

            * return PARSE_DONE, indicating that it was consumed and this
              field now has all the necessary data.
            * return PARSE_MORE, indicating that it was consumed but this
              field will accept more nodes.
            * return PARSE_SKIP, indicating that it was not consumed by
              this field.

        Any other return value will be taken as a parse error.
        """
        return constants.Status.PARSE_SKIP

    def parse_done(self, obj: object) -> None:
        """Finalize parsing for the given object.

        This method is called as a simple indicator that no more data will
        be forthcoming.  No return value is expected.
        """

    def render_attributes(
        self, obj: object, val: Any, nsmap: Dict[str, Any]
    ) -> Generator[str, None, None]:
        """Render any attributes that this field manages."""
        return
        yield

    def render_children(
        self, obj: object, val: Any, nsmap: Dict[str, Any]
    ) -> Generator[str, None, None]:
        """Render any child nodes that this field manages."""
        return
        yield

    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        val = instance.__dict__.get(self.field_name)
        if val is None:
            return self.default
        return val

    def __set__(self, instance, value):
        instance.__dict__[self.field_name] = value

    def _check_tagname(self, node, tagname):
        if node.nodeType != node.ELEMENT_NODE:
            return False
        if isinstance(tagname, str):
            if node.localName != tagname:
                return False
            if node.namespaceURI:
                if node.namespaceURI != self.model_class.meta.namespace:
                    return False
        else:
            (tagns, tagname) = tagname
            if node.localName != tagname:
                return False
            if node.namespaceURI != tagns:
                return False
        return True
