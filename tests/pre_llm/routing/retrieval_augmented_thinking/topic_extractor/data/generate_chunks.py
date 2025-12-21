import json
from pathlib import Path
from altk.pre_llm.routing.retrieval_augmented_thinking.utils import (
    generate_chunks_from_file,
)

if __name__ == "__main__":
    chunks = generate_chunks_from_file(
        str(Path(__file__).parent / "sound.pdf"), 400, 40
    )
    chunks_file = str(Path(__file__).parent / "chunks.json")
    with open(chunks_file, "w") as json_file:
        json.dump(chunks, json_file, indent=4)
    print(f"{len(chunks)} chunks from source file sound.pdf written to {chunks_file}")
