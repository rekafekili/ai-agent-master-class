from crewai.flow.flow import Flow, listen, start, router, and_, or_
from pydantic import BaseModel


class MyFirstFlowState(BaseModel):
    user_id: int = 1
    is_admin: bool = False


# https://docs.crewai.com/en/concepts/flows
class MyFirstFlow(Flow[MyFirstFlowState]):  # Define Flow's State Type
    @start()
    def first(self):
        # self.state["whatever"] = 1  # Unstructured! -> Use pydantic!
        print(self.state.user_id)
        print("Hello")

    @listen(first)
    def second(self):
        # print(self.state["whatever"])
        self.state.user_id = 2
        print("world")

    @listen(first)
    def third(self):
        print("!")

    @listen(and_(second, third))
    def final(self):
        # self.state["whatever"] = 2
        print(":)")

    @router(final)
    def route(self):
        # if self.state["whatever"] == 2:
        if self.state.is_admin:
            return "even"  # emit event
        else:
            return "odd"  # emit event

    @listen("even")
    def handle_even(self):
        print("even")

    @listen("odd")
    def handle_odd(self):
        print("odd")


flow = MyFirstFlow()

flow.plot()  # Visualize Flow
flow.kickoff()  # Start Flow
