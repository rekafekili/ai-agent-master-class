import dotenv

dotenv.load_dotenv()

from crewai import Crew, Agent, Task
from crewai.project import CrewBase, agent, task, crew


# IMPORTANT : Role, Goal, Backstory
@CrewBase
class TranslatorCrew:
    @agent  # https://docs.crewai.com/en/concepts/agents
    def translator_agent(self):
        return Agent(config=self.agents_config["translator_agent"])

    @task  # https://docs.crewai.com/en/concepts/tasks
    def translate_task(self):
        return Task(config=self.tasks_config["translate_task"])

    @task  # https://docs.crewai.com/en/concepts/tasks
    def retranslate_task(self):
        return Task(config=self.tasks_config["retranslate_task"])

    @crew
    def assemble_crew(self):
        return Crew(
            agents=self.agents,  # @agent 가 붙은 agent 모음
            tasks=self.tasks,  # @task 가 붙은 task 모음
            verbose=True,  # log
        )


TranslatorCrew().assemble_crew().kickoff(
    inputs={
        "sentence": "I'm Nico and I like to ride my bicycle in Napoli",
    }
)
