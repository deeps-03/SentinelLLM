from fastapi import FastAPI
from pydantic import BaseModel
import subprocess

app = FastAPI()

class Prompt(BaseModel):
    prompt: str

@app.post("/generate")
async def generate_text(data: Prompt):
    # Run the model using docker model run CLI
    # Note: This assumes docker CLI is available inside the container (see Dockerfile)
    try:
        result = subprocess.run(
            ["docker", "model", "run", "ai/gemma3-qat:latest", data.prompt],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode != 0:
            print(f"Docker model run failed. Stderr: {result.stderr}, Stdout: {result.stdout}")
            return {"error": result.stderr}
        return {
            "choices": [
                {
                    "message": {
                        "content": result.stdout.strip()
                    }
                }
            ]
        }
    except Exception as e:
        return {"error": str(e)}
