from unittest import mock

from dexml.cli import generator


def test_get_type_int():
    value = "123"
    expected_result = "Integer"
    result = generator.get_type(value)
    assert result == expected_result


def test_get_type_float():
    value = "123.45"
    expected_result = "Float"
    result = generator.get_type(value)
    assert result == expected_result


def test_get_type_string():
    value = "some string"
    expected_result = "String"
    result = generator.get_type(value)
    assert result == expected_result


def test_to_snake_case_pascal():
    value = "SomeValue"
    result = generator.to_snake_case(value)
    expected_result = "some_value"
    assert result == expected_result


def test_to_snake_case_snake():
    value = "some_value"
    result = generator.to_snake_case(value)
    expected_result = "some_value"
    assert result == expected_result


def test_to_snake_case_mix():
    value = "someValue_Example"
    result = generator.to_snake_case(value)
    expected_result = "some_value_example"
    assert result == expected_result


def test_to_snake_case_caps():
    value = "USALtd"
    result = generator.to_snake_case(value)
    expected_result = "usa_ltd"
    assert result == expected_result


def test_to_snake_case_dot():
    value = "com.example"
    result = generator.to_snake_case(value)
    expected_result = "com_example"
    assert result == expected_result


def test_to_snake_case_number():
    value = "SomeValue45"
    result = generator.to_snake_case(value)
    expected_result = "some_value"
    assert result == expected_result


def test_to_pascal_case_snake():
    value = "some_value"
    result = generator.to_pascal_case(value)
    expected_result = "SomeValue"
    assert result == expected_result


def test_to_pascal_case_pascal():
    value = "SomeValue"
    result = generator.to_pascal_case(value)
    expected_result = "SomeValue"
    assert result == expected_result


def test_to_pascal_case_pascal_mix():
    value = "someValue_Example"
    result = generator.to_pascal_case(value)
    expected_result = "SomeValueExample"
    assert result == expected_result


def test_generator_standard():
    input_xml = """<?xml version="1.0" encoding="utf-8"?>
<BLOCK>
    <PersonDetails>
        <PersonName>Jim</PersonName>
        <Address>
            <Street>101 Road</Street>
        </Address>
        <PersonAge>42</PersonAge>
    </PersonDetails>
    <Amount>240.45</Amount>
    <Enabled>true</Enabled>
</BLOCK>
"""
    expected_output = """import dexml
from dexml import fields


class Address(dexml.Model):
    street = fields.String(tagname="Street")


class PersonDetails(dexml.Model):
    person_name = fields.String(tagname="PersonName")
    person_age = fields.Integer(tagname="PersonAge")
    address = fields.Model(Address)


class Block(dexml.Model):
    class meta:
        tagname = "BLOCK"
    amount = fields.Float(tagname="Amount")
    enabled = fields.Boolean(tagname="Enabled")
    person_details = fields.Model(PersonDetails)"""

    result = generator.parse(input_xml)
    assert result == expected_output


def test_generator_custom_name():
    input_xml = """<?xml version="1.0" encoding="utf-8"?>
<BLOCK>
    <person_details>
        <person_name>Jim</person_name>
        <Address>
            <Street>101 Road</Street>
        </Address>
        <PersonAge>42</PersonAge>
    </person_details>
    <Amount>240.45</Amount>
</BLOCK>
"""
    expected_output = """import dexml
from dexml import fields


class Address(dexml.Model):
    street = fields.String(tagname="Street")


class PersonDetails(dexml.Model):
    class meta:
        tagname = "person_details"
    person_name = fields.String()
    person_age = fields.Integer(tagname="PersonAge")
    address = fields.Model(Address)


class Block(dexml.Model):
    class meta:
        tagname = "BLOCK"
    amount = fields.Float(tagname="Amount")
    person_details = fields.Model(PersonDetails)"""

    result = generator.parse(input_xml)
    assert result == expected_output


def test_generator_duplicates():
    input_xml = """<?xml version="1.0" encoding="utf-8"?>
<BLOCK>
    <Details>
        <Name>Jim</Name>
    </Details>
    <Company>
        <Details>
            <Name>Jim</Name>
        </Details>
        <Other>
            <Misc>Unknown</Misc>
        </Other>
    </Company>
</BLOCK>"""

    expected_output = """import dexml
from dexml import fields


class Details(dexml.Model):
    name = fields.String(tagname="Name")


class Other(dexml.Model):
    misc = fields.String(tagname="Misc")


class Company(dexml.Model):
    details = fields.Model(Details)
    other = fields.Model(Other)


class Block(dexml.Model):
    class meta:
        tagname = "BLOCK"
    details = fields.Model(Details)
    company = fields.Model(Company)"""

    result = generator.parse(input_xml)
    assert result == expected_output


@mock.patch("dexml.cli.generator.sys")
def test_main_function(patched_sys):
    input_xml = """<?xml version="1.0" encoding="utf-8"?>
<Data>
    <PersonDetails>
        <PersonName>Jim</PersonName>
    </PersonDetails>
</Data>"""

    patched_sys.stdin = input_xml.split("\n")
    generator.main()
