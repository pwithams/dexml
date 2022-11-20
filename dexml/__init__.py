"""
dexml: A dead-simple Object-XML mapper for Python
"""
from dexml import fields
from dexml.constants import Status
from dexml.exceptions import ParseError, RenderError, XmlError
from dexml.model import Model

__version__ = "0.1.0"


__all__ = [
    "Model",
    "fields",
    "ParseError",
    "RenderError",
    "XmlError",
    "Status",
]
