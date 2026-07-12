import pytest
from pydantic import ValidationError

from app.schemas import Dimensions, Shelf
from tests.fixtures import valid_shelf_dict


def test_rejects_non_numeric_length():
    with pytest.raises(ValidationError):
        Dimensions(length="banana", width=12, height=4)


def test_rejects_confidence_over_one():
    shelf = valid_shelf_dict()
    shelf["confidence"] = 91              # must be 0-1, never a percentage
    with pytest.raises(ValidationError):
        Shelf(**shelf)


def test_rejects_unknown_zone_class():
    shelf = valid_shelf_dict()
    shelf["zone_class"] = "banana"        # enum: empty/low/medium/high only
    with pytest.raises(ValidationError):
        Shelf(**shelf)
