class Error(Exception):
    """Base exception class for the dexml module."""


class ParseError(Error):
    """Exception raised when XML could not be parsed into objects."""


class RenderError(Error):
    """Exception raised when object could not be rendered into XML."""


class XmlError(Error):
    """Exception raised to encapsulate errors from underlying XML parser."""
