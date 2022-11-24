from typing import List

from dexml import constants, exceptions
from dexml.fields import field as dexml_field
from dexml.fields import model as model_field


class Choice(dexml_field.Field):
    """Field subclass accepting any one of a given set of model_field.Model fields."""

    fields: List[dexml_field.Field]

    class Arguments(dexml_field.Field.Arguments):
        fields: List[dexml_field.Field] = []

    def __init__(self, *fields, **kwds):
        real_fields = []
        for field in fields:
            if isinstance(field, model_field.Model):
                real_fields.append(field)
            elif isinstance(field, str):
                real_fields.append(model_field.Model(field))
            else:
                raise ValueError("only Model fields are allowed within a Choice field")
        kwds["fields"] = real_fields
        super().__init__(**kwds)

    def parse_child_node(self, obj, node):
        for field in self.fields:
            field.field_name = self.field_name
            field.model_class = self.model_class
            res = field.parse_child_node(obj, node)
            if res is constants.Status.PARSE_MORE:
                raise ValueError("items in a Choice cannot return PARSE_MORE")
            if res is constants.Status.PARSE_DONE:
                return constants.Status.PARSE_DONE
        else:
            return constants.Status.PARSE_SKIP

    def render_children(self, obj, item, nsmap, use_field_names=False):
        if item is None:
            if self.required:
                raise exceptions.RenderError(
                    f"Field '{self.field_name}': required field is missing"
                )
        else:
            for data in item._render(nsmap=nsmap, use_field_names=use_field_names):
                yield data
