"""Workflow compiler for Orchestra DSL."""

from typing import Any, Dict, List, Optional
from orchestra.core.workflow import Workflow
from orchestra.core.task import Task, TaskStatus
from orchestra.core.context import Context


class WorkflowCompiler:
    """Compiles and validates Orchestra workflows.
    
    The compiler analyzes workflows, validates their structure,
    and prepares them for execution.
    """
    
    def __init__(self):
        """Initialize the workflow compiler."""
        self.compiled_workflows: Dict[str, Workflow] = {}
    
    def compile(self, workflow: Workflow) -> Workflow:
        """Compile a workflow for execution.
        
        Args:
            workflow: Workflow to compile
            
        Returns:
            Compiled workflow
            
        Raises:
            ValueError: If workflow validation fails
        """
        # Validate workflow structure
        workflow.validate()
        
        # Store compiled workflow
        self.compiled_workflows[workflow.name] = workflow
        
        return workflow
    
    def get_execution_plan(self, workflow: Workflow) -> List[List[str]]:
        """Generate an execution plan for the workflow.
        
        Returns tasks grouped by execution level, where tasks in the
        same level can be executed in parallel.
        
        Args:
            workflow: Workflow to analyze
            
        Returns:
            List of task levels, each containing task names that can run in parallel
        """
        execution_order = workflow.get_execution_order()
        levels: List[List[str]] = []
        completed = set()
        
        while len(completed) < len(execution_order):
            # Find tasks that can run in current level
            current_level = []
            for task_name in execution_order:
                if task_name in completed:
                    continue
                
                task = workflow.tasks[task_name]
                if task.is_ready(completed):
                    current_level.append(task_name)
            
            if not current_level:
                # No tasks ready - shouldn't happen with valid workflow
                raise ValueError("Unable to generate execution plan")
            
            levels.append(current_level)
            completed.update(current_level)
        
        return levels
    
    def optimize(self, workflow: Workflow) -> Workflow:
        """Optimize workflow for execution.
        
        Args:
            workflow: Workflow to optimize
            
        Returns:
            Optimized workflow
        """
        # Placeholder for optimization logic
        # Could include: parallel task identification, resource allocation, etc.
        return workflow
    
    def __repr__(self) -> str:
        """String representation of the compiler."""
        return f"WorkflowCompiler(compiled={len(self.compiled_workflows)})"
