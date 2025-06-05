from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from agent import graph, langfuse_callback
from graph_tools import character_neighbors
import uvicorn
from typing import Dict, Any

app = FastAPI()

class QuestionRequest(BaseModel):
    question: str

class QuestionResponse(BaseModel):
    response: str

@app.post("/question", response_model=QuestionResponse)
async def ask_question(request: QuestionRequest):
    """Process a user question using the X-Men agent"""
    input = {
        "messages": [
            ("user", request.question)
        ]
    }
    try:
        response = graph.invoke(
            input, 
            config={
                "callbacks": [langfuse_callback]
            }
        )
        answer = response['messages'][-1].content
        return QuestionResponse(response=answer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing question: {str(e)}")

@app.get("/graph/{character}")
async def get_character_graph(character: str) -> Dict[str, Any]:
    """Get character's immediate neighbors in the graph"""
    try:
        print(f'/graph/{character}: {character}')
        result = character_neighbors(character)
        print(f'/graph/{character}: {result}')
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving character data: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
