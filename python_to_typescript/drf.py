from __future__ import absolute_import, division, print_function, unicode_literals  # isort:skip # noqa

from typing import Dict, List, Optional, Set

import six
from rest_framework.serializers import (
    Serializer,
    BooleanField,
    CharField,
    ChoiceField,
    DateField,
    DateTimeField,
    DecimalField,
    DictField,
    DurationField,
    FileField,
    FloatField,
    IntegerField,
    ListField,
    MultipleChoiceField,
    NullBooleanField,
    TimeField,
    UUIDField,
)

from .base import generate_interfaces


def _serializer_name(serializer_class):
    return serializer_class.__name__.replace('Serializer', '')


def _python_type_for_field_without_null_check(field):
    # A string comparison is used so we don't require psycopg for people who
    # don't use Postgres.
    if type(field).__name__ == 'CharMappingField':
        return Dict[six.text_type, Optional[six.text_type]]

    if isinstance(field, (BooleanField, NullBooleanField)):
        return bool

    if isinstance(field, MultipleChoiceField):
        return Set[six.text_type]

    if isinstance(field, (
        CharField,
        ChoiceField,
        DateField,
        DateTimeField,
        DecimalField,
        DurationField,
        FileField,
        TimeField,
        UUIDField,
    )):
        return six.text_type

    if isinstance(field, DictField):
        return Dict[six.text_type, object]

    if isinstance(field, FloatField):
        return float

    if isinstance(field, IntegerField):
        return int

    if isinstance(field, ListField):
        return List[_python_type_for_field(field.child)]

    return object


def _python_type_for_field(field):
    field_type = _python_type_for_field_without_null_check(field)

    return (
        Optional[field_type]
        if field.allow_null else
        field_type
    )


def generate_interfaces_from_serializer(serializer_class):
    serializer = serializer_class()

    python_types = []
    attribute_dict = {}
    python_types.append((_serializer_name(serializer_class), attribute_dict))

    for field_name, field in six.iteritems(serializer.fields):
        if not field.write_only:
            attribute_dict[field_name] = _python_type_for_field(field)

    return generate_interfaces(python_types)


def generate_interfaces_from_serializers(serializer_classes, follow_dependencies=True):
    classes_todo = set(serializer_classes)
    classes_done = set()
    python_types = []

    while len(classes_todo) > 0:
        serializer_class = classes_todo.pop()
        serializer = serializer_class()
        attribute_dict = {}

        for field_name, field in six.iteritems(serializer.fields):
            if not field.write_only:
                if isinstance(field, Serializer):
                    field_class = type(field)

                    if field_class in classes_todo or field_class in classes_done or field_class is serializer_class:
                        attribute_dict[field_name] = _serializer_name(field_class) + (' | null' if field.allow_null else '')
                    elif follow_dependencies:
                        classes_todo.add(field_class)
                        attribute_dict[field_name] =  _serializer_name(field_class) + (' | null' if field.allow_null else '')
                    else:
                        attribute_dict[field_name] = _python_type_for_field(field)

                else:
                    attribute_dict[field_name] = _python_type_for_field(field)

        python_types.append((_serializer_name(serializer_class), attribute_dict))
        classes_done.add(serializer_class)

    return generate_interfaces(python_types)