import io
import re
import sys
import xml.etree.ElementTree as xml
from dataclasses import dataclass
from typing import Any, List, Union


@dataclass
class ParserConfig:
    add_defaults: bool
    tab_size: int

    @property
    def tab(self) -> str:
        return self.tab_size * " "


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
    value = value.replace("\n", "")
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
class DexmlBase:
    config: ParserConfig
    level: int


@dataclass
class DexmlAttribute(DexmlBase):
    tagname: str
    default: Union[int, str, bool, float]
    type: str

    def __str__(self) -> str:
        default = ""
        if self.config.add_defaults:
            default = f"default={self.default}"
        name = to_snake_case(self.tagname)
        if name == self.tagname:
            return f"{self.tagname} = fields.{self.type}({default})"
        value = f'{name} = fields.{self.type}(tagname="{self.tagname}", {default})'
        return re.sub(r", \)", ")", value)


@dataclass
class DexmlModel(DexmlBase):
    tagname: str
    attributes: List[DexmlAttribute]
    models: List["DexmlModel"]

    def get_as_attribute(self) -> str:
        attr_name = to_snake_case(self.tagname)
        cls_name = to_pascal_case(self.tagname)
        default = ""
        if self.config.add_defaults:
            default = f"default={cls_name}"
        value = f"{attr_name} = fields.Model({cls_name}, {default})"
        return re.sub(r", \)", ")", value)

    def __str__(self) -> str:
        name = to_pascal_case(self.tagname)
        data = [
            f"class {name}(dexml.Model):",
        ]
        if name != self.tagname:
            data.append(f"{self.config.tab}class meta:")
            data.append(f'{self.config.tab}{self.config.tab}tagname = "{self.tagname}"')
        if "tagname = " not in data[-1]:
            data.append(f"{self.config.tab}class meta:")
        data.append(f"{self.config.tab}{self.config.tab}order_sensitive = False")

        attribute_lines = [self.config.tab + str(attr) for attr in self.attributes]
        sorted_models = self.models
        sorted_models = sorted(
            self.models, key=lambda model: to_snake_case(model.tagname)
        )
        model_lines = [
            self.config.tab + str(model.get_as_attribute()) for model in sorted_models
        ]
        return "\n".join(data + attribute_lines + model_lines)


class Parser:
    def __init__(self, config: ParserConfig) -> None:
        self.config = config

    def extract_models(
        self, xml_element: xml.Element, level: int, all_models: List[DexmlModel]
    ) -> Union[DexmlAttribute, DexmlModel]:
        children_count: int = 0
        for xml_element_child in xml_element:
            children_count += 1

        default: Any
        if children_count == 0:
            if xml_element.text is None:
                attr_type = "String"
                default = '""'
            else:
                attr_type = get_type(xml_element.text)
                default = get_default(xml_element.text)
            return DexmlAttribute(
                self.config,
                level,
                xml_element.tag,
                type=attr_type,
                default=default,
            )

        dexml_model = DexmlModel(self.config, level, xml_element.tag, [], [])

        for xml_element_child in xml_element:
            result = self.extract_models(xml_element_child, level + 1, all_models)
            space = "   " * (level + 1)
            if isinstance(result, DexmlAttribute):
                dexml_model.attributes.append(result)
            else:
                dexml_model.models.append(result)
                all_models.append(result)

        return dexml_model

    def parse(self, xml_string) -> str:
        data = xml.parse(io.StringIO(xml_string))
        all_models: List[DexmlModel] = []
        top_level_model = self.extract_models(data.getroot(), 0, all_models)
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
                for index in range(len(result)):
                    line = result[index]
                    if line == model_str:
                        result[index] = line.replace(
                            " = fields.Model", " = fields.List"
                        )
                continue
            result.append("")
            result.append(model_str)
            result.append("")
            generated[model_str] = True

        return "\n".join(result).rstrip("\n")


def main(add_defaults: bool, tab_size: int) -> None:
    xml_lines = []
    for line in sys.stdin:
        xml_lines.append(line)

    xml_string = "".join(xml_lines)
    config = ParserConfig(add_defaults, tab_size)
    parser = Parser(config)
    result = parser.parse(xml_string)
    print(result)
