from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from agent import graph, langfuse_callback
from graph_tools import character_neighbors
from typing import Dict, Any
from cache_server import set_key_value, get_value
from logger import logger
from dotenv import load_dotenv
import os
import uvicorn
import uuid

load_dotenv(override=True)
app = FastAPI()

class QuestionRequest(BaseModel):
    question: str

class QuestionResponse(BaseModel):
    response: str

@app.post("/question", response_model=QuestionResponse)
async def ask_question(request: QuestionRequest):
    """Process a user question using the X-Men agent"""
    request_id = str(uuid.uuid4())
    logger.info(f'/question request_id {request_id}')
    question = request.question
    cache_result = get_value(question, request_id)
    if cache_result:
        logger.info(f"Cache hit, returning answer from cache, request_id {request_id}")
        return QuestionResponse(response=cache_result)
    else:
        logger.info(f"Cache miss, triggering agentic workflow, request_id {request_id}")
    input = {
        "messages": [
            ("user", question)
        ]
    }
    try:
        response = graph.invoke(
            input, 
            config={
                "callbacks": [langfuse_callback],
                "metadata": {
                    "request_id": request_id,
                },
            }
        )
        answer = response['messages'][-1].content
        set_key_value(question, answer, request_id)
        logger.info(f'returning answer, request_id {request_id}')
        return QuestionResponse(response=answer)
    except Exception as e:
        logger.error(f'Returning 500, got Error: {e}, request_id {request_id}')
        logger.exception(e)
        raise HTTPException(status_code=500, detail=f"Error processing question: {str(e)}")

@app.get("/graph/{character}")
async def get_character_graph(character: str) -> Dict[str, Any]:
    """Get character's immediate neighbors in the graph"""
    request_id = str(uuid.uuid4())
    logger.info(f'/graph/{character}: {request_id}')
    try:
        result = character_neighbors(character, request_id)
        if "error" in result:
            logger.error(f'Returning 404 for error from querying character neighbors: {result["error"]}, request_id {request_id}')
            raise HTTPException(status_code=404, detail=result["error"])
        else:
            logger.info(f'Got result from getting character neighbors: {result}, request_id {request_id}')
        return result
    except Exception as e:
        logger.error(f'Returning 500, got Error: {e}, request_id {request_id}')
        logger.exception(e)
        raise HTTPException(status_code=500, detail=f"Error retrieving character data: {str(e)}")

if __name__ == "__main__":
    server_port = int(os.getenv('SERVER_PORT'))
    logger.info(f'Server is listening at port {server_port}')
    uvicorn.run(app, host="0.0.0.0", port=server_port)
