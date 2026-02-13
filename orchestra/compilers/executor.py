"""Executor for Orchestra workflows."""

from typing import Any, Dict, Optional, Callable
from orchestra.core.workflow import Workflow
from orchestra.core.task import Task, TaskStatus
from orchestra.core.context import Context
from orchestra.core.agent import Agent


class ExecutionResult:
    """Result of workflow execution."""
    
    def __init__(self, workflow_name: str, success: bool):
        """Initialize execution result.
        
        Args:
            workflow_name: Name of executed workflow
            success: Whether execution was successful
        """
        self.workflow_name = workflow_name
        self.success = success
        self.task_results: Dict[str, Any] = {}
        self.errors: Dict[str, str] = {}
    
    def add_task_result(self, task_name: str, result: Any):
        """Add a task result."""
        self.task_results[task_name] = result
    
    def add_error(self, task_name: str, error: str):
        """Add a task error."""
        self.errors[task_name] = error
    
    def __repr__(self) -> str:
        """String representation of the result."""
        status = "success" if self.success else "failed"
        return f"ExecutionResult(workflow='{self.workflow_name}', status='{status}')"


class Executor:
    """Executes compiled Orchestra workflows.
    
    The executor runs workflows, manages task execution,
    and handles agent interactions.
    """
    
    def __init__(self, provider_registry: Optional[Dict[str, Any]] = None):
        """Initialize the executor.
        
        Args:
            provider_registry: Optional registry of provider implementations
        """
        self.provider_registry = provider_registry or {}
        self.execution_history: list = []
    
    def execute(self, workflow: Workflow, context: Optional[Context] = None) -> ExecutionResult:
        """Execute a workflow.
        
        Args:
            workflow: Workflow to execute
            context: Optional execution context
            
        Returns:
            Execution result
        """
        if context is None:
            context = Context()
        
        result = ExecutionResult(workflow.name, True)
        
        try:
            # Get execution order
            execution_order = workflow.get_execution_order()
            completed_tasks = set()
            
            # Execute tasks in order
            for task_name in execution_order:
                task = workflow.tasks[task_name]
                
                try:
                    # Execute task
                    task_result = self._execute_task(task, workflow, context)
                    
                    # Mark task as completed
                    task.mark_completed(task_result)
                    result.add_task_result(task_name, task_result)
                    completed_tasks.add(task_name)
                    
                    # Update context with task result
                    context.set(f"task.{task_name}.result", task_result)
                    
                except Exception as e:
                    # Mark task as failed
                    error_msg = str(e)
                    task.mark_failed(error_msg)
                    result.add_error(task_name, error_msg)
                    result.success = False
                    break
            
            # Store execution in history
            self.execution_history.append({
                'workflow': workflow.name,
                'context': context,
                'result': result
            })
            
        except Exception as e:
            result.success = False
            result.add_error('workflow', str(e))
        
        return result
    
    def _execute_task(self, task: Task, workflow: Workflow, context: Context) -> Any:
        """Execute a single task.
        
        Args:
            task: Task to execute
            workflow: Parent workflow
            context: Execution context
            
        Returns:
            Task execution result
        """
        # Mark task as running
        task.mark_running()
        
        # Get agent for task
        if task.agent:
            agent = workflow.agents.get(task.agent)
            if not agent:
                raise ValueError(f"Agent '{task.agent}' not found")
            
            # Execute with agent
            return self._execute_with_agent(agent, task, context)
        else:
            # Execute as simple task
            return self._execute_simple_task(task, context)
    
    def _execute_with_agent(self, agent: Agent, task: Task, context: Context) -> Any:
        """Execute task with an agent.
        
        Args:
            agent: Agent to use
            task: Task to execute
            context: Execution context
            
        Returns:
            Task result
        """
        # Get provider implementation
        provider = self.provider_registry.get(agent.provider)
        
        if provider:
            # Use registered provider
            return provider.execute(agent, task, context)
        else:
            # Return simulated result for testing
            return {
                'status': 'completed',
                'agent': agent.name,
                'task': task.name,
                'description': task.description
            }
    
    def _execute_simple_task(self, task: Task, context: Context) -> Any:
        """Execute a simple task without an agent.
        
        Args:
            task: Task to execute
            context: Execution context
            
        Returns:
            Task result
        """
        # Simple tasks just return their inputs processed
        return {
            'status': 'completed',
            'task': task.name,
            'inputs': task.inputs
        }
    
    def __repr__(self) -> str:
        """String representation of the executor."""
        return f"Executor(executions={len(self.execution_history)})"
