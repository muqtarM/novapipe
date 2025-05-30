# NovaPipe

> NovaPipe: An advanced, plugin-driven ETL CLI.

## Quickstart

```bash
pip install novapipe
novapipe init
novapipe run pipeline.yaml
```

## Sample Pipeline (pipeline_templates/sample_pipeline.yaml)

```yaml
tasks
  - name: HelloWorld
    task: print_message
    params:
      message: "Hello from NovaPipe!"
```

## Contributing
See [CONTRIBUTING.md](CONTRIBUTING.md) for details
