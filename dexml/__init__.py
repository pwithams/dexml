"""
dexml: A dead-simple Object-XML mapper for Python
"""
import importlib.metadata

from dexml import fields
from dexml.constants import Status
from dexml.exceptions import ParseError, RenderError, XmlError
from dexml.model import Model

try:
    __version__ = importlib.metadata.version("dexml")
except importlib.metadata.PackageNotFoundError:
    __version__ = "dev"


__all__ = [
    "Model",
    "fields",
    "ParseError",
    "RenderError",
    "XmlError",
    "Status",
]
