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

load_dotenv(override=True)

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    number_of_steps: int

def setup_workflow():
    tools = [query_characters_database]

    llm = ChatOpenAI(
        model=os.getenv("OPENAI_MODEL"),
        openai_api_key=os.getenv("OPENAI_API_KEY")
    )

    model = llm.bind_tools(tools)

    tools_by_name = {tool.name: tool for tool in tools}

    def call_tool(state: AgentState):
        """Tool node"""
        outputs = []
        for tool_call in state["messages"][-1].tool_calls:
            tool_result = tools_by_name[tool_call["name"]].invoke(tool_call["args"])
            outputs.append(
                ToolMessage(
                    content=tool_result,
                    name=tool_call["name"],
                    tool_call_id=tool_call["id"],
                )
            )
        return {"messages": outputs}

    def call_model(state: AgentState, config: RunnableConfig):
        """LLM node"""
        response = model.invoke(state["messages"], config)
        return {"messages": [response]}

    def should_continue(state: AgentState):
        messages = state["messages"]
        if not messages[-1].tool_calls:
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
    inputs = {
        "messages": [
            ("user", "Tell me what you know about Wolverine genes and his team members genes")
        ]
    }

    response = graph.invoke(
        inputs, 
        config={
            "callbacks": [langfuse_callback]
        }
    )

    print(response['messages'][-1].content)
