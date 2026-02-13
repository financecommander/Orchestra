"""Simple workflow example for Orchestra DSL."""

from orchestra import Agent, Task, Workflow, Context
from orchestra.compilers import WorkflowCompiler, Executor


def main():
    """Run a simple workflow demonstration."""
    print("=" * 60)
    print("Orchestra DSL - Simple Workflow Example")
    print("=" * 60)

    # Create a workflow
    workflow = Workflow(
        name="document_processing",
        description="Process and analyze documents with multiple agents",
    )

    # Define agents
    reader_agent = Agent(
        name="document_reader",
        provider="llm",
        system_prompt="You are a document reader that extracts key information.",
    )

    analyzer_agent = Agent(
        name="content_analyzer",
        provider="llm",
        system_prompt="You are an analyzer that provides insights.",
    )

    summarizer_agent = Agent(
        name="summarizer",
        provider="llm",
        system_prompt="You are a summarizer that creates concise summaries.",
    )

    # Add agents to workflow
    workflow.add_agent(reader_agent)
    workflow.add_agent(analyzer_agent)
    workflow.add_agent(summarizer_agent)

    # Define tasks with dependencies
    read_task = Task(
        name="read_document",
        description="Read and extract text from the document",
        agent="document_reader",
        inputs={"document": "sample_document.pdf"},
    )

    # These two tasks can run in parallel after read_task completes
    analyze_task = Task(
        name="analyze_content",
        description="Analyze the extracted content for insights",
        agent="content_analyzer",
        dependencies=["read_document"],
    )

    summarize_task = Task(
        name="create_summary",
        description="Create a summary of the content",
        agent="summarizer",
        dependencies=["read_document"],
    )

    # Final task depends on both parallel tasks
    final_task = Task(
        name="combine_results",
        description="Combine analysis and summary into final report",
        dependencies=["analyze_content", "create_summary"],
    )

    # Add tasks to workflow
    workflow.add_task(read_task)
    workflow.add_task(analyze_task)
    workflow.add_task(summarize_task)
    workflow.add_task(final_task)

    print("\nWorkflow structure:")
    print(f"  - Agents: {len(workflow.agents)}")
    print(f"  - Tasks: {len(workflow.tasks)}")

    # Compile workflow
    print("\nCompiling workflow...")
    compiler = WorkflowCompiler()
    compiled_workflow = compiler.compile(workflow)

    # Get execution plan
    execution_plan = compiler.get_execution_plan(compiled_workflow)
    print("\nExecution plan (tasks by level):")
    for i, level in enumerate(execution_plan):
        print(f"  Level {i + 1}: {level}")

    # Create context with initial data
    context = Context()
    context.set("environment", "production")
    context.set("config", {"max_tokens": 1000, "temperature": 0.7})

    # Execute workflow
    print("\nExecuting workflow...")
    executor = Executor()
    result = executor.execute(compiled_workflow, context)

    # Display results
    print("\nExecution results:")
    print(f"  Success: {result.success}")
    print(f"  Completed tasks: {len(result.task_results)}")

    if result.success:
        print("\nTask results:")
        for task_name, task_result in result.task_results.items():
            print(f"  - {task_name}: {task_result.get('status', 'unknown')}")

        print("\nContext variables after execution:")
        for key in list(context.variables.keys())[:5]:
            print(f"  - {key}: {type(context.get(key)).__name__}")
    else:
        print("\nErrors occurred:")
        for task_name, error in result.errors.items():
            print(f"  - {task_name}: {error}")

    print("\n" + "=" * 60)
    print("Example completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
