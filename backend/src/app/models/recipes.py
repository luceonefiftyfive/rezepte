from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


class Unit(StrEnum):
    GRAM = "g"
    KILOGRAM = "kg"
    MILLILITER = "ml"
    LITER = "l"
    TEASPOON = "tsp"
    TABLESPOON = "tbsp"
    PIECE = "piece"
    PINCH = "pinch"
    BUNCH = "bunch"
    CLOVE = "clove"
    SLICE = "slice"
    CUP = "cup"
    AS_NEEDED = "as_needed"
    CUSTOM = "custom"


class ScalingMode(StrEnum):
    LINEAR = "linear"
    MANUAL = "manual"
    NONE = "none"


class RecipeIngredient(BaseModel):
    ingredient_id: str | None = None
    name: str = Field(min_length=1, max_length=200)
    amount: Decimal | None = Field(default=None, ge=0)
    unit: Unit = Unit.PIECE
    custom_unit: str | None = Field(default=None, max_length=50)
    preparation: str | None = Field(default=None, max_length=200)
    remarks: str | None = Field(default=None, max_length=500)
    optional: bool = False
    scaling: ScalingMode = ScalingMode.LINEAR

    @model_validator(mode="after")
    def validate_custom_unit(self) -> "RecipeIngredient":
        if self.unit == Unit.CUSTOM and not self.custom_unit:
            raise ValueError("custom_unit is required when unit is 'custom'")
        if self.unit != Unit.CUSTOM and self.custom_unit:
            raise ValueError("custom_unit is only permitted when unit is 'custom'")
        return self


class IngredientSection(BaseModel):
    id: str = Field(min_length=1, max_length=80)
    name: str | None = Field(default=None, max_length=120)
    ingredients: list[RecipeIngredient] = Field(default_factory=list)


class InstructionStep(BaseModel):
    id: str = Field(min_length=1, max_length=80)
    text: str = Field(min_length=1, max_length=5000)


class RecipeTime(BaseModel):
    preparation_minutes: int | None = Field(default=None, ge=0, le=10080)
    cooking_minutes: int | None = Field(default=None, ge=0, le=10080)
    resting_minutes: int | None = Field(default=None, ge=0, le=10080)


class RecipeYield(BaseModel):
    amount: Decimal = Field(gt=0)
    unit: str = Field(min_length=1, max_length=50)


class RecipeBase(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    group_ids: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    time: RecipeTime = Field(default_factory=RecipeTime)
    yield_: RecipeYield = Field(alias="yield")
    ingredient_sections: list[IngredientSection] = Field(default_factory=list)
    instructions: list[InstructionStep] = Field(default_factory=list)
    remarks: str | None = Field(default=None, max_length=10000)

    model_config = {"populate_by_name": True}

    @model_validator(mode="after")
    def validate_unique_ids(self) -> "RecipeBase":
        section_ids = [section.id for section in self.ingredient_sections]
        if len(section_ids) != len(set(section_ids)):
            raise ValueError("Ingredient section IDs must be unique")
        step_ids = [step.id for step in self.instructions]
        if len(step_ids) != len(set(step_ids)):
            raise ValueError("Instruction step IDs must be unique")
        return self


class RecipeCreate(RecipeBase):
    pass


class RecipeUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    group_ids: list[str] | None = None
    tags: list[str] | None = None
    time: RecipeTime | None = None
    yield_: RecipeYield | None = Field(default=None, alias="yield")
    ingredient_sections: list[IngredientSection] | None = None
    instructions: list[InstructionStep] | None = None
    remarks: str | None = Field(default=None, max_length=10000)
    version: int = Field(ge=1)

    model_config = {"populate_by_name": True}


class RecipeOut(RecipeBase):
    id: str
    created_at: datetime
    updated_at: datetime
    version: int


# Compatibility alias for older imports.
RecipeIn = RecipeCreate
