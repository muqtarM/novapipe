# tests/test_runner_dot.py

import yaml
from novapipe.runner import PipelineRunner

SAMPLE = """
tasks:
  - name: a
    task: print_message
  - name: b
    task: print_message
    depends_on:
      - a
"""


def test_to_dot_contains_nodes_and_edge(tmp_path):
    data = yaml.safe_load(SAMPLE)
    runner = PipelineRunner(data)
    dot = runner.to_dot()

    # check for node declarations
    assert '"a"' in dot and '"b"' in dot
    # check for edge a -> b
    assert '"a" -> "b"' in dot
    # ensure graph opens and closes
    assert dot.strip().startswith("digraph NovaPipe")
    assert dot.strip().endswith("}")
