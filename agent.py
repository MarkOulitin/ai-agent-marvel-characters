import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage
from langchain_core.messages import ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, END
from graph_tools import query_characters_database
from typing import Annotated,Sequence, TypedDict
from dotenv import load_dotenv
from langfuse.callback import CallbackHandler
from logger import logger

load_dotenv(override=True)

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]

def setup_workflow():
    tools = [query_characters_database]

    llm = ChatOpenAI(
        model=os.getenv("OPENAI_MODEL"),
        openai_api_key=os.getenv("OPENAI_API_KEY")
    )

    model = llm.bind_tools(tools)

    tools_by_name = {tool.name: tool for tool in tools}

    def call_tool(state: AgentState, config: RunnableConfig):
        """Tool node"""
        outputs = []
        for tool_call in state["messages"][-1].tool_calls:
            tool_name = tool_call["name"]
            logger.info(f"Calling tool {tool_name}, request_id {config['metadata']['request_id']}, langfuse_trace_id {config['callbacks'].handlers[0].trace.id}")
            tool_result = tools_by_name[tool_name].invoke(tool_call["args"])
            outputs.append(
                ToolMessage(
                    content=tool_result,
                    name=tool_name,
                    tool_call_id=tool_call["id"],
                )
            )
        return {"messages": outputs}

    def call_model(state: AgentState, config: RunnableConfig):
        """LLM node"""
        response = model.invoke(state["messages"], config)
        logger.info(f"Calling llm, request_id {config['metadata']['request_id']}, langfuse_trace_id {config['callbacks'].handlers[0].trace.id}")
        return {"messages": [response]}

    def should_continue(state: AgentState, config: RunnableConfig):
        messages = state["messages"]
        if not messages[-1].tool_calls:
            logger.info(f"Finishing agentic workflow, request_id {config['metadata']['request_id']}, langfuse_trace_id {config['callbacks'].handlers[0].trace.id}")
            return "end"
        return "continue"

    workflow = StateGraph(AgentState)

    workflow.add_node("llm", call_model)
    workflow.add_node("tools",  call_tool)
    workflow.set_entry_point("llm")
    workflow.add_conditional_edges(
        "llm",
        should_continue,
        {
            "continue": "tools",
            "end": END,
        },
    )
    workflow.add_edge("tools", "llm")
    graph = workflow.compile()
    graph.get_graph().draw_mermaid_png(output_file_path='workflow.png')
    
    return graph

langfuse_callback = CallbackHandler(
    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    host=os.getenv("LANGFUSE_HOST"),
)

graph = setup_workflow()

if __name__ == '__main__':
    import uuid
    inputs = {
        "messages": [
            ("user", "Return all the names team members of X-men with confidence higer than 0.5")
        ]
    }

    request_id = str(uuid.uuid4())
    response = graph.invoke(
        inputs, 
        config={
            "callbacks": [langfuse_callback],
            "metadata": {
                "request_id": request_id,
            },
        }
    )

    logger.info(f'Answer for request id {request_id}:')
    logger.info(response['messages'][-1].content)
