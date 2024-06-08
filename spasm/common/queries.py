from typing import Any, Optional

import string
from dataclasses import dataclass
from enum import Enum

from wtforms import TextAreaField
from wtforms.validators import ValidationError


class BoundType(Enum):
    EXACTLY, NOT, \
        GREATER_THAN, \
        AT_LEAST, \
        LESS_THAN, \
        AT_MOST = range(6)


BOUND_OPERATOR_TEXTS = ['==', '!=', '>', '>=', '<', '<=']


@dataclass
class Condition:
    bound_type: BoundType
    bound_value: Any

    def to_struct(self):
        return [self.bound_type.value, self.bound_value]

    def from_struct(_dict: dict):
        return Condition(BoundType(_dict[0]), _dict[1])


ConditionsType = dict[str, Condition]


def check_condition(condition: Condition, value):
    try:
        if value is None:
            return False
        match condition.bound_type:
            case BoundType.EXACTLY:
                return value == condition.bound_value
            case BoundType.NOT:
                return value != condition.bound_value
            case BoundType.GREATER_THAN:
                return value > condition.bound_value
            case BoundType.AT_LEAST:
                return value >= condition.bound_value
            case BoundType.LESS_THAN:
                return value < condition.bound_value
            case BoundType.AT_MOST:
                return value < condition.bound_value
    except TypeError:
        return False


def conditional_from_struct(_dict: dict[str, tuple[int, Any]]) -> ConditionsType:
    result = {}
    for key, struct in _dict.items():
        result[key] = Condition.from_struct(struct)
    return result


def conditional_to_struct(conditions: ConditionsType) -> dict[str, tuple[int, Any]]:
    result = {}
    for key, condition in conditions.items():
        result[key] = condition.to_struct()
    return result


def bound_data(info: dict[str], conditions: ConditionsType):
    for key, condition in conditions.items():
        if not check_condition(condition, info.get(key)):
            return False
    return True


def filter_ids(base_data: dict[str, dict[str]], conditions: Optional[ConditionsType] = None):
    if conditions is None:
        return list(base_data.keys())
    result = []
    for id, info in base_data.items():
        if bound_data(info, conditions):
            result.append(id)
    return result


def parse_value(text: str):
    if text.lower() == 'true':
        return True
    if text.lower() == 'false':
        return False
    if any(char not in string.ascii_letters for char in text):
        try:
            return (float if '.' in text else int)(text)
        except ValueError:
            raise ValidationError(f'Invalid value {text}. (parsed as number)')
    return text


def conditions_from_user_text(text: str):
    conditions = {}
    for bound in text.splitlines():
        if not bound:
            continue

        property_name = ''
        oper_name = ''
        value = ''
        state = 0
        for char in bound:
            if char == ' ':
                continue
            match state:
                case 0:
                    if char not in string.ascii_letters:
                        state = 1
                        oper_name += char
                    else:
                        property_name += char
                case 1:
                    if char not in '<>=!':
                        state = 2
                        value += char
                    else:
                        oper_name += char
                case 2:
                    value += char
        if oper_name == '=':
            oper_name = '=='
        if not oper_name:
            raise ValidationError(f'No bound operator found.')
        if oper_name not in BOUND_OPERATOR_TEXTS:
            raise ValidationError(f'Invalid bound type `{oper_name}`.')
        if state == 1:
            raise ValidationError(
                f'Expected value after bound operator `{oper_name}`.')

        cond_type = BoundType(BOUND_OPERATOR_TEXTS.index(oper_name))
        conditions[property_name] = Condition(cond_type, parse_value(value))

    return conditions

