from collections import defaultdict
from typing import TYPE_CHECKING, Union

from pydantic import BaseModel, Field
from rich.box import HEAVY_EDGE
from rich.console import Console
from rich.table import Table

try:
    from agentops import track_agent
except ImportError:
    def track_agent():
        def noop(f):
            return f
        return noop

from crewai.agent import Agent
from crewai.llm import LLM
from crewai.task import Task
from crewai.tasks.task_output import TaskOutput
from crewai.telemetry import Telemetry

if TYPE_CHECKING:
    from crewai.crew import Crew


class TaskEvaluationPydanticOutput(BaseModel):
    quality: float = Field(
        description="A score from 1 to 10 evaluating on completion, quality, and overall performance from the task_description and task_expected_output to the actual Task Output."
    )


@track_agent()
class CrewEvaluator:
    """Evaluates the performance of a crew's agents on their tasks.

    Handles evaluation of agent performance using specified LLM model.

    Attributes:
        crew (Crew): The crew of agents to evaluate.
        llm (Union[str, LLM]): The language model to use for evaluation. Can be a string (model name) or LLM instance.
        tasks_scores (defaultdict): A dictionary to store the scores of the agents for each task.
        iteration (int): The current iteration of the evaluation.
    """

    tasks_scores: defaultdict = defaultdict(list)
    run_execution_times: defaultdict = defaultdict(list)
    iteration: int = 0

    def __init__(self, crew: "Crew", llm: Union[str, LLM]) -> None:
        """Initialize CrewEvaluator with crew and language model.
        
        Args:
            crew: The crew to evaluate
            llm: Language model to use for evaluation, can be a string (model name) or LLM instance
        """
        self.crew = crew
        self.llm = llm if isinstance(llm, LLM) else LLM(model=llm)
        self._telemetry = Telemetry()
        self._setup_for_evaluating()

    def _setup_for_evaluating(self) -> None:
        """Sets up the crew for evaluating by assigning evaluation callbacks to tasks."""
        for task in self.crew.tasks:
            task.callback = self.evaluate

    def _evaluator_agent(self) -> Agent:
        """Creates an agent specialized in evaluating task performance.

        Returns:
            Agent: An agent configured to evaluate task execution quality.
        """
        return Agent(
            role="Task Execution Evaluator",
            goal=(
                "Your goal is to evaluate the performance of the agents in the crew based on the tasks they have performed using score from 1 to 10 evaluating on completion, quality, and overall performance."
            ),
            backstory="Evaluator agent for crew evaluation with precise capabilities to evaluate the performance of the agents in the crew based on the tasks they have performed",
            verbose=False,
            llm=self.llm,
        )

    def _evaluation_task(
        self, evaluator_agent: Agent, task_to_evaluate: Task, task_output: str
    ) -> Task:
        """Creates a task for evaluating another task's execution.

        Args:
            evaluator_agent: The agent that will perform the evaluation
            task_to_evaluate: The task whose execution needs to be evaluated
            task_output: The output produced by the task execution

        Returns:
            Task: A task configured to evaluate the execution quality
        """
        return Task(
            description=(
                "Based on the task description and the expected output, compare and evaluate the performance of the agents in the crew based on the Task Output they have performed using score from 1 to 10 evaluating on completion, quality, and overall performance."
                f"task_description: {task_to_evaluate.description} "
                f"task_expected_output: {task_to_evaluate.expected_output} "
                f"agent: {task_to_evaluate.agent.role if task_to_evaluate.agent else None} "
                f"agent_goal: {task_to_evaluate.agent.goal if task_to_evaluate.agent else None} "
                f"Task Output: {task_output}"
            ),
            expected_output="Evaluation Score from 1 to 10 based on the performance of the agents on the tasks",
            agent=evaluator_agent,
            output_pydantic=TaskEvaluationPydanticOutput,
        )

    def set_iteration(self, iteration: int) -> None:
        """Sets the current iteration number for test tracking.

        Args:
            iteration: The iteration number to set
        """
        self.iteration = iteration

    def print_crew_evaluation_result(self) -> None:
        """Prints a formatted table showing evaluation results for all tasks and iterations.

        Displays task scores (1-10), average scores, execution times, and involved agents
        in a rich-formatted table. Each row represents a task or crew-level metric,
        with columns for each test iteration and averages.

        Example output:
                        Tasks Scores
                    (1-10 Higher is better)
        ┏━━━━━━━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
        ┃ Tasks/Crew/Agents  ┃ Run 1 ┃ Run 2 ┃ Run 3 ┃ Avg. Total ┃ Agents                       ┃
        ┡━━━━━━━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
        │ Task 1             │ 9.0   │ 10.0  │ 9.0   │ 9.3        │ - AI LLMs Senior Researcher  │
        │ Task 2             │ 9.0   │ 9.0   │ 9.0   │ 9.0        │ - AI LLMs Senior Researcher  │
        │ Crew               │ 9.0   │ 9.5   │ 9.0   │ 9.2        │                              │
        │ Execution Time (s) │ 42    │ 79    │ 52    │ 57         │                              │
        └────────────────────┴───────┴───────┴───────┴────────────┴──────────────────────────────┘
        """
        task_averages = [
            sum(scores) / len(scores) for scores in zip(*self.tasks_scores.values())
        ]
        crew_average = sum(task_averages) / len(task_averages)

        table = Table(title="Tasks Scores \n (1-10 Higher is better)", box=HEAVY_EDGE)

        table.add_column("Tasks/Crew/Agents", style="cyan")
        for run in range(1, len(self.tasks_scores) + 1):
            table.add_column(f"Run {run}", justify="center")
        table.add_column("Avg. Total", justify="center")
        table.add_column("Agents", style="green")

        for task_index, task in enumerate(self.crew.tasks):
            task_scores = [
                self.tasks_scores[run][task_index]
                for run in range(1, len(self.tasks_scores) + 1)
            ]
            avg_score = task_averages[task_index]
            agents = list(task.processed_by_agents)

            # Add the task row with the first agent
            table.add_row(
                f"Task {task_index + 1}",
                *[f"{score:.1f}" for score in task_scores],
                f"{avg_score:.1f}",
                f"- {agents[0]}" if agents else "",
            )

            # Add rows for additional agents
            for agent in agents[1:]:
                table.add_row("", "", "", "", "", f"- {agent}")

            # Add a blank separator row if it's not the last task
            if task_index < len(self.crew.tasks) - 1:
                table.add_row("", "", "", "", "", "")

        # Add Crew and Execution Time rows
        crew_scores = [
            sum(self.tasks_scores[run]) / len(self.tasks_scores[run])
            for run in range(1, len(self.tasks_scores) + 1)
        ]
        table.add_row(
            "Crew",
            *[f"{score:.2f}" for score in crew_scores],
            f"{crew_average:.1f}",
            "",
        )

        run_exec_times = [
            int(sum(tasks_exec_times))
            for _, tasks_exec_times in self.run_execution_times.items()
        ]
        execution_time_avg = int(sum(run_exec_times) / len(run_exec_times))
        table.add_row(
            "Execution Time (s)", *map(str, run_exec_times), f"{execution_time_avg}", ""
        )

        console = Console()
        console.print(table)

    def evaluate(self, task_output: TaskOutput) -> None:
        """Evaluates the performance of the agents in the crew based on task execution.

        Evaluates task execution quality using a specialized evaluator agent and
        stores the evaluation results for later analysis.

        Args:
            task_output: The output from the task execution to evaluate

        Raises:
            ValueError: If task_output is missing or doesn't match any known task
        """
        current_task = None
        for task in self.crew.tasks:
            if task.description == task_output.description:
                current_task = task
                break

        if not current_task or not task_output:
            raise ValueError(
                "Task to evaluate and task output are required for evaluation"
            )

        evaluator_agent = self._evaluator_agent()
        evaluation_task = self._evaluation_task(
            evaluator_agent, current_task, task_output.raw
        )

        evaluation_result = evaluation_task.execute_sync()

        if isinstance(evaluation_result.pydantic, TaskEvaluationPydanticOutput):
            self._test_result_span = self._telemetry.individual_test_result_span(
                self.crew,
                evaluation_result.pydantic.quality,
                current_task._execution_time,
                str(self.llm),
            )
            self.tasks_scores[self.iteration].append(evaluation_result.pydantic.quality)
            self.run_execution_times[self.iteration].append(
                current_task._execution_time
            )
        else:
            raise ValueError("Evaluation result is not in the expected format")
