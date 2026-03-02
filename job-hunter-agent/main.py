import dotenv

dotenv.load_dotenv()

from crewai import Crew, Agent, Task
from crewai.project import CrewBase, crew, agent, task
from crewai.knowledge.source.text_file_knowledge_source import TextFileKnowledgeSource
from models import JobList, ChosenJob, RankedJobList
from tools import web_search_tool

resume_knowledge = TextFileKnowledgeSource(
    file_paths=[
        "resume.txt",
    ]
)


@CrewBase
class JobHunterCrew:
    @agent
    def job_search_agent(self):
        return Agent(
            config=self.agents_config["job_search_agent"],
            tools=[web_search_tool],
        )

    @agent
    def job_matching_agent(self):
        return Agent(
            config=self.agents_config["job_matching_agent"],
            knowledge_sources=[resume_knowledge],
        )

    @agent
    def resume_optimization_agent(self):
        return Agent(
            config=self.agents_config["resume_optimization_agent"],
            knowledge_sources=[resume_knowledge],
        )

    @agent
    def company_research_agent(self):
        return Agent(
            config=self.agents_config["company_research_agent"],
            knowledge_sources=[resume_knowledge],
            tool=[web_search_tool],
        )

    @agent
    def interview_prep_agent(self):
        return Agent(
            config=self.agents_config["interview_prep_agent"],
            knowledge_sources=[resume_knowledge],
        )

    @task
    def job_extraction_task(self):
        return Task(
            config=self.tasks_config["job_extraction_task"],
            output_pydantic=JobList,
        )

    @task
    def job_matching_task(self):
        return Task(
            config=self.tasks_config["job_matching_task"],
            output_pydantic=RankedJobList,
        )

    @task
    def job_selection_task(self):
        return Task(
            config=self.tasks_config["job_selection_task"],
            output_pydantic=ChosenJob,
        )

    @task
    def resume_rewriting_task(self):
        return Task(
            config=self.tasks_config["resume_rewriting_task"],
            # context=[
            #     self.job_selection_task(),
            # ], # 직전의 task는 자동으로 다음 task로 넘어오기 때문에 꼭 추가할 필요 없음.
        )

    @task
    def company_research_task(self):
        return Task(
            config=self.tasks_config["company_research_task"],
            context=[self.job_selection_task()],
        )

    @task
    def interview_prep_task(self):
        return Task(
            config=self.tasks_config["interview_prep_task"],
            context=[
                self.job_selection_task(),
                self.resume_rewriting_task(),
                self.company_research_task(),
            ],
        )

    @crew
    def crew(self):
        return Crew(agents=self.agents, tasks=self.tasks, verbose=True)


JobHunterCrew().crew().kickoff(
    inputs={
        "level": "Senior",
        "position": "Golang Developer",
        "location": "Netherlands",
    }
)
