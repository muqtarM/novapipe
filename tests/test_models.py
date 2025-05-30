import pytest
from novapipe.models import Pipeline


def test_pipeline_validation_success():
    data = {'tasks': [{'name': 'A', 'task': 'print_message', 'params': {'message': 'hi'}}]}
    pipeline = Pipeline.model_validate(data)
    assert len(pipeline.tasks) == 1


def test_pipeline_validation_empty():
    with pytest.raises(ValueError):
        Pipeline.model_validate({'tasks': []})
