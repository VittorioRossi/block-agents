import json

from .blocks.text import TextInputBlock  # noqa: F401 - Import needed to register text blocks
from .core.pipeline import Pipeline

if __name__ == "__main__":
    with open("./frontend_output.json") as f:
        json_pipleine = json.load(f)


    pipeline = Pipeline.from_frontend_dict(json_pipleine)

    print(pipeline.execute({}))