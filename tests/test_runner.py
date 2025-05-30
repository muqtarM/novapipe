import pytest
import asyncio
from novapipe.runner import PipelineRunner
from novapipe.tasks import task, TASKS


def test_sync_task(capsys):
    @task(name='sync_test')
    def sync_fn(x: int, y: int):
        print(x + y)

    data = {'tasks': [{'name': 'sum', 'task': 'sync_test', 'params': {'x': 2, 'y': 3}}]}
    runner = PipelineRunner(data)
    runner.run()
    captured = capsys.readouterr()
    assert '5' in captured.out


def test_async_test(capsys):
    @task(name='async_test')
    async def async_fn(x: int, y: int):
        await asyncio.sleep(0)
        print(x * y)

    data = {'tasks': [{'name': 'prod', 'task': 'async_test', 'params': {'x': 3, 'y': 4}}]}
    runner = PipelineRunner(data)
    runner.run()
    captured = capsys.readouterr()
    assert '12' in captured.out
