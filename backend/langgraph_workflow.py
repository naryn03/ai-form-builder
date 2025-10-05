# langgraph_workflow.py
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langchain_core.runnables import RunnableConfig

from agents_impl import (
    schema_agent_impl,
    validation_agent_impl,
    recovery_agent_impl,
    learning_agent_impl,
)

# We'll define nodes that accept payload and update the shared state.
class FormBuilderState(TypedDict, total=False):
    mode: str
    description: str
    schema: dict
    submission: dict
    validation_result: dict
    recovery: dict
    insights: dict

def schema_agent_node(state: FormBuilderState, config: RunnableConfig):
    """Generate schema from user description"""
    user_text = state.get("description")
    schema = schema_agent_impl(user_text)
    print("Schema generated:", schema)
    return {"schema": schema}

def validation_agent_node(state: FormBuilderState, config: RunnableConfig):
    """Validate submission against schema"""
    schema = state.get("schema")
    submission = state.get("submission", {})
    if not schema:
        raise RuntimeError("Schema missing in state")
    result = validation_agent_impl(schema, submission)
    return {"validation_result": result}

def recovery_agent_node(state: FormBuilderState, config: RunnableConfig):
    """Suggest recovery/fixes for invalid submissions"""
    schema = state.get("schema")
    submission = state.get("submission", {})
    errors = state.get("validation_result", {}).get("errors", {})
    suggestions = recovery_agent_impl(schema, submission, errors)
    return {"recovery": suggestions}

def learning_agent_node(state: FormBuilderState, config: RunnableConfig):
    """Learn from historical submissions"""
    schema = state.get("schema")
    submissions = state.get("history", [])
    insights = learning_agent_impl(schema, submissions)
    return {"insights": insights}

def entry_router_node(state: FormBuilderState, config):
    mode = state.get("mode")
    if mode == "schema":
        return schema_agent_node(state, config)
    elif mode == "validate":
        return validation_agent_node(state, config)
    elif mode == "recovery":
        return recovery_agent_node(state, config)
    elif mode == "learning":
        return learning_agent_node(state, config)
    else:
        raise RuntimeError(f"Unknown mode: {mode}")

def build_form_workflow():
    builder = StateGraph(FormBuilderState)

    builder.add_node("entry_router", entry_router_node)
    builder.add_node("schema_agent", schema_agent_node)
    builder.add_node("validation_agent", validation_agent_node)
    builder.add_node("recovery_agent", recovery_agent_node)
    builder.add_node("learning_agent", learning_agent_node)

    # Single entry
    builder.add_edge(START, "entry_router")
    # No other edges required, router decides which node to run
    builder.add_edge("schema_agent", END)
    builder.add_edge("validation_agent", END)
    builder.add_edge("recovery_agent", END)
    builder.add_edge("learning_agent", END)

    graph = builder.compile()
    return graph