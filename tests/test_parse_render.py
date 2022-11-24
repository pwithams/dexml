import doctest
import os
import os.path
import sys
import unittest
from io import StringIO
from xml.dom import minidom

import dexml
from dexml import fields
from dexml import model as dexml_model
from dexml.fields import list as dexml_list


class TestParseRender(unittest.TestCase):
    def test_default_rendering_nested(self):
        """Allow a render() on instance to pull defaults, not just during parse."""

        class Inner(dexml.Model):
            name = fields.String(default="Inner", tagname="Name")

        class Hello(dexml.Model):
            recipient = fields.String(default="Test", tagname="recipient")
            size = fields.Integer(default=42, tagname="size")
            message = fields.String(default="Hello, world", tagname="message")
            inner = fields.Model(Inner, default=Inner, tagname="Inner")

        expected_render = '<?xml version="1.0" ?><Hello><recipient>Test</recipient><size>42</size><message>Hello, world</message><Inner><Name>Inner</Name></Inner></Hello>'

        result = Hello().render()
        self.assertEqual(result, expected_render)

    def test_default_rendering_nested_no_tags(self):
        class Inner(dexml.Model):
            name = fields.String(default="Inner")

        class Hello(dexml.Model):
            recipient = fields.String(default="Test")
            size = fields.Integer(default=42)
            message = fields.String(default="Hello, world")
            inner = fields.Model(Inner, default=Inner)

        expected_render = '<?xml version="1.0" ?><Hello recipient="Test" size="42" message="Hello, world"><Inner name="Inner" /></Hello>'

        result = Hello().render()
        self.assertEqual(result, expected_render)

    def test_default_rendering_simple(self):
        class SomeModel(dexml.Model):
            name = fields.String(tagname="Name", default="value")

        expected_render = (
            '<?xml version="1.0" ?><SomeModel><Name>value</Name></SomeModel>'
        )

        result = SomeModel().render()
        self.assertEqual(result, expected_render)

    def test_default_rendering_simple_no_tags(self):
        class SomeModel(dexml.Model):
            name = fields.String(default="value")

        expected_render = '<?xml version="1.0" ?><SomeModel name="value" />'

        result = SomeModel().render()
        self.assertEqual(result, expected_render)

    def test_default_rendering_list(self):
        class Inner(dexml.Model):
            name = fields.String(default="Inner", tagname="Name")

        class Hello(dexml.Model):
            inner = fields.List(Inner, default=[Inner])

        expected_render = (
            '<?xml version="1.0" ?><Hello><Inner><Name>Inner</Name></Inner></Hello>'
        )

        result = Hello().render()
        self.assertEqual(result, expected_render)

    def test_list_parse_order(self):
        class Inner(dexml.Model):
            name = fields.String(tagname="Name")

        class Hello(dexml.Model):
            inner = fields.List(Inner)
            val = fields.String(tagname="Val")

        parse_input = '<?xml version="1.0" ?><Hello><Inner><Name>Inner</Name></Inner><Inner><Name>Inner</Name></Inner><Val>Test</Val></Hello>'

        result = Hello.parse(parse_input)
        self.assertEqual(result.render(), parse_input)

    def test_list_parse_out_of_order(self):
        class Inner(dexml.Model):
            name = fields.String(tagname="Name", attribute="Id")

        class Hello(dexml.Model):
            class meta:
                order_sensitive = False

            inner = fields.List(Inner)
            val = fields.String(tagname="Val")

        parse_input = '<?xml version="1.0" ?><Hello><Inner><Name>Inner</Name></Inner><Val>Test</Val><Inner><Name>Inner</Name></Inner></Hello>'
        expected_output = '<?xml version="1.0" ?><Hello><Inner><Name>Inner</Name></Inner><Inner><Name>Inner</Name></Inner><Val>Test</Val></Hello>'

        result = Hello.parse(parse_input)
        self.assertEqual(result.render(), expected_output)

    def test_render_json(self):
        class Inner(dexml.Model):
            name = fields.String(tagname="Name", default="test_name")

        class Hello(dexml.Model):
            inner = fields.List(Inner, default=[Inner, Inner])
            val = fields.String(tagname="Val", default="test_val")

        result = Hello().render_json(use_field_names=True, flatten=True)
        expected_result = '{"Hello": {"inner": [{"name": "test_name"}, {"name": "test_name"}], "val": "test_val"}}'
        self.assertEqual(result, expected_result)

    def test_render_json_with_single_lists(self):
        class Inner(dexml.Model):
            name = fields.String(tagname="Name", default="test_name")

        class Hello(dexml.Model):
            inner = fields.List(Inner, default=[Inner])
            val = fields.String(tagname="Val", default="test_val")

        result = Hello().render_json(use_field_names=True, flatten=True)
        expected_result = (
            '{"Hello": {"inner": [{"name": "test_name"}], "val": "test_val"}}'
        )
        self.assertEqual(result, expected_result)

    def test_flatten_dict(self):
        data_input = {
            "inner": {"inner": [{"name": "test_name"}, {"name": "test_name"}]},
            "val": "test_val",
        }
        expected_result = {
            "inner": [{"name": "test_name"}, {"name": "test_name"}],
            "val": "test_val",
        }
        result = dexml.model.flatten_dict(data_input)
        print(result)
        self.assertEqual(result, expected_result)

    def test_find_list_names(self):
        class InnerTwo(dexml.Model):
            name = fields.String(tagname="Name2", default="test_name")

        class Mod(dexml.Model):
            lst = fields.List(InnerTwo, default=[InnerTwo])
            val = fields.String(tagname="Val", default="test_val")

        class Inner(dexml.Model):
            mod = fields.Model(Mod, default=Mod)

        class Hello(dexml.Model):
            inner = fields.List(Inner, default=[Inner])
            val = fields.String(tagname="Val", default="test_val")

        result = dexml_list.find_list_names(Hello()._fields)
        expected_result = [("inner", "Inner"), ("lst", "InnerTwo")]
        self.assertEqual(result, expected_result)

    def test_key_to_list(self):
        data = {
            "value1": {
                "name": "test",
            },
            "value2": {
                "name2": "test",
                "inner": {
                    "age": 12,
                },
            },
        }
        dexml_model.key_to_list(data, ["value1", "inner"])
        expected_output = {
            "value1": [
                {
                    "name": "test",
                }
            ],
            "value2": {
                "name2": "test",
                "inner": [
                    {
                        "age": 12,
                    },
                ],
            },
        }
        self.assertEqual(data, expected_output)
