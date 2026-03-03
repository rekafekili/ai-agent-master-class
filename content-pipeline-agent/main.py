from crewai.flow.flow import Flow, listen, start, router, and_, or_
from pydantic import BaseModel


class ContentPipelineState(BaseModel):
    # inputs
    content_type: str = ""
    topic: str = ""

    # Internal
    max_length: int = 0


class ContentPipelineFlow(Flow[ContentPipelineState]):
    @start()
    def init_content_pipeline(self):
        # print(self.state.content_type)
        # print(self.state.topic)
        if self.state.content_type not in ["tweet", "blog", "linkedin"]:
            raise ValueError("The content type is wrong.")

        if self.state.topic == "":
            raise ValueError("The topic cant't be blank.")

        if self.state.content_type == "tweet":
            self.state.max_length = 150
        elif self.state.content_type == "blog":
            self.state.max_length = 800
        elif self.state.content_type == "linkedin":
            self.state.max_length = 500

    @listen(init_content_pipeline)
    def conduct_research(self):
        print("Researching...")
        return True

    @router(conduct_research)
    def router(self):
        content_type = self.state.content_type

        if self.state.content_type == "tweet":
            return "make_tweet"
        elif self.state.content_type == "blog":
            return "make_blog"
        elif self.state.content_type == "linkedin":
            return "make_linkedin_post"

    @listen("make_blog")
    def handle_make_blog(self):
        print("Making Blog post...")

    @listen("make_tweet")
    def handle_make_tweet(self):
        print("Making Tweet post...")

    @listen("make_linkedin_post")
    def handle_make_linkedin(self):
        print("Making Linkedin post...")

    @listen(handle_make_blog)
    def check_blog_seo(self):
        print("Checking Blog SEO")

    @listen(or_(handle_make_tweet, handle_make_linkedin))
    def check_virality(self):
        print("Checking virality")

    @listen(or_(check_blog_seo, check_virality))
    def finalize_content(self):
        print("Fianlizing content")


flow = ContentPipelineFlow()
flow.plot()
# flow.kickoff(
#     inputs={
#         "content_type": "tweet",
#         "topic": "AI Dog Training",
#     }
# )
