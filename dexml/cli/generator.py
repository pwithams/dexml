import io
import sys
import xml.etree.ElementTree as xml
from dataclasses import dataclass
from typing import List, Union

TABSIZE = 4
TAB = " " * TABSIZE


def get_type(value: str) -> str:
    if value.isdigit():
        return "Integer"
    if value.replace(".", "").isdigit():
        return "Float"
    if value in ["true", "false"]:
        return "Boolean"
    return "String"


def get_default(value: str) -> Union[int, float, bool, str]:
    value = value.strip()
    if value.isdigit():
        return int(value)
    if value.replace(".", "").isdigit():
        return float(value)
    if value in ["true", "false"]:
        if value == "true":
            return True
        return False
    return f'"{value}"'


def to_snake_case(name: str) -> str:
    new_name = []
    prev_char = None
    for char in name:
        if (
            char.isupper()
            and prev_char
            and prev_char != "_"
            and not prev_char.isupper()
        ):
            new_name.append("_")
        if (
            char.islower()
            and prev_char
            and prev_char.isupper()
            and len(new_name) > 1
            and new_name[-2] != "_"
        ):
            new_name[-1] = "_"
            new_name.append(prev_char.lower())
        if not char.isalpha():
            new_name.append("_")
        else:
            new_name.append(char.lower())
        prev_char = char
    result = "".join(new_name)
    return result.strip("_")


def to_pascal_case(name: str) -> str:
    new_name = []
    cap_next = True
    prev_char_lower = False
    for char in name:
        if char == "_":
            cap_next = True
            continue
        if cap_next or (prev_char_lower and char.isupper()):
            new_name.append(char.upper())
            cap_next = False
        else:
            new_name.append(char.lower())
        prev_char_lower = char.islower()
    return "".join(new_name)


@dataclass
class DexmlAttribute:
    tagname: str
    default: Union[int, str, bool, float]
    type: str

    def __str__(self) -> str:
        name = to_snake_case(self.tagname)
        if name == self.tagname:
            return f"{self.tagname} = fields.{self.type}(default={self.default})"
        return f'{name} = fields.{self.type}(tagname="{self.tagname}", default={self.default})'


@dataclass
class DexmlModel:
    tagname: str
    attributes: List[DexmlAttribute]
    models: List["DexmlModel"]
    level: int

    def get_as_attribute(self) -> str:
        attr_name = to_snake_case(self.tagname)
        cls_name = to_pascal_case(self.tagname)
        return f"{attr_name} = fields.Model({cls_name}, default={cls_name}())"

    def __str__(self) -> str:
        name = to_pascal_case(self.tagname)
        data = [
            f"class {name}(dexml.Model):",
        ]
        if name != self.tagname:
            data.append(f"{TAB}class meta:")
            data.append(f'{TAB}{TAB}tagname = "{self.tagname}"')
        attribute_lines = [TAB + str(attr) for attr in self.attributes]
        model_lines = [TAB + str(model.get_as_attribute()) for model in self.models]
        # model_definitions = [str(model) for model in self.models]
        return "\n".join(data + attribute_lines + model_lines)


def extract_models(
    xml_element: xml.ElementTree, level: int, all_models: List[DexmlModel]
) -> Union[DexmlAttribute, DexmlModel]:
    children_count = 0
    for xml_element_child in xml_element:
        children_count += 1

    if children_count == 0:
        return DexmlAttribute(
            xml_element.tag,
            type=get_type(xml_element.text),
            default=get_default(xml_element.text),
        )

    dexml_model = DexmlModel(xml_element.tag, [], [], level)

    for xml_element_child in xml_element:
        result = extract_models(xml_element_child, level + 1, all_models)
        space = "   " * (level + 1)
        if isinstance(result, DexmlAttribute):
            dexml_model.attributes.append(result)
        else:
            dexml_model.models.append(result)
            all_models.append(result)

    return dexml_model


def parse(xml_string):
    data = xml.parse(io.StringIO(xml_string))
    all_models = []
    top_level_model = extract_models(data.getroot(), 0, all_models)
    models = [top_level_model, *all_models]
    models = sorted(models, key=lambda model: model.level, reverse=True)
    result = []
    result.append("import dexml")
    result.append("from dexml import fields")
    result.append("")
    generated = {}
    for model in models:
        model_str = str(model)
        if model_str in generated:
            continue
        result.append("")
        result.append(model_str)
        result.append("")
        generated[model_str] = True

    return "\n".join(result).rstrip("\n")


def main():
    xml_lines = []
    for line in sys.stdin:
        xml_lines.append(line)

    xml_string = "".join(xml_lines)
    result = parse(xml_string)
    print(result)
