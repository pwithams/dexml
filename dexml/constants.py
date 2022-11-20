import enum
import re


class Status(enum.Enum):
    """Constant returned by a Field when it has finished parsing."""

    PARSE_DONE: str = "done"
    PARSE_MORE: str = "more"
    PARSE_SKIP: str = "skip"
    PARSE_CHILDREN: str = "children"


#  You can use this re to extract the encoding declaration from the XML
#  document string.  Hopefully you won't have to, but you might need to...
XML_ENCODING_RE = re.compile(
    "<\\?xml [^>]*encoding=[\"']([a-zA-Z0-9\\.\\-\\_]+)[\"'][^>]*?>"
)
