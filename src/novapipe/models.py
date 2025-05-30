from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Any


class Step(BaseModel):
    name: str
    task: str
    params: Dict[str, Any] = Field(default_factory=dict)


class Pipeline(BaseModel):
    tasks: List[Step]

    @field_validator('tasks', mode='before')
    def check_tasks_not_empty(cls, v):
        if not v:
            raise ValueError("Pipeline must contain at least one task")
        return v
