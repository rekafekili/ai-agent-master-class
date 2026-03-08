from typing import List
from crewai.flow.flow import Flow, listen, start, router, and_, or_
from crewai import Agent, LLM
from tools import web_search_tool
from pydantic import BaseModel
from seo_crew import SeoCrew
from virality_crew import ViralityCrew


class BlogPost(BaseModel):
    title: str
    subtitle: str
    sections: List[str]


class TweetPost(BaseModel):
    content: str
    hashtags: str


class LinkedInPost(BaseModel):
    hook: str
    content: str
    call_to_action: str


class Score(BaseModel):
    score: int = 0
    reason: str = ""


class ContentPipelineState(BaseModel):
    # inputs
    content_type: str = ""
    topic: str = ""

    # Internal
    max_length: int = 0
    research: str = ""
    score: Score | None = None

    # Content
    blog: BlogPost | None = None
    tweet: TweetPost | None = None
    linkedin: LinkedInPost | None = None


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
        researcher = Agent(
            role="Head Researcher",
            backstory="You're like a digital detective who loves digging up fascinating facts and insights. You have a knack for finding the good stuff that others miss.",
            goal=f"Find the most interesting and useful info about {self.state.topic}",
            tools=[web_search_tool],
        )

        self.state.research = researcher.kickoff(
            f"Find the most interesting and useful info about {self.state.topic}"
        )

    @router(conduct_research)
    def conduct_research_router(self):
        content_type = self.state.content_type

        if content_type == "tweet":
            return "make_tweet"
        elif content_type == "blog":
            return "make_blog"
        elif content_type == "linkedin":
            return "make_linkedin_post"

    @listen(or_("make_blog", "remake_blog"))
    def handle_make_blog(self):
        # if blog post has been made, show the old one to the ai and ask it to improve,
        # elese just ask to create.
        blog_post = self.state.blog
        llm = LLM(model="openai/o4-mini", response_format=BlogPost)

        if blog_post is None:
            self.state.blog = llm.call(
                f"""
            Make a blog post on the topic {self.state.topic} using the following research:

            <research>
            =======================
            {self.state.research}
            =======================
            </research>
            """
            )
        else:
            self.state.blog = llm.call(
                f"""
            You wrote this blog post with SEO practices on {self.state.topic}, but it does not have a good SEO score
            because of {self.state.score.reason}
            
            Improve it.

            <blog_post>
            {self.state.blog.model_dump_json()}
            </blog_post>

            Use the following research.

            <research>
            =======================
            {self.state.research}
            =======================
            </research>
            """
            )

    @listen(or_("make_tweet", "remake_tweet"))
    def handle_make_tweet(self):
        # if tweet has been made, show the old one to the ai and ask it to improve,
        # elese just ask to create.
        tweet = self.state.tweet
        llm = LLM(model="openai/o4-mini", response_format=TweetPost)

        if tweet is None:
            self.state.tweet = llm.call(
                f"""
            Make a tweet post that can go viral on the topic {self.state.topic} using the following research:

            <research>
            =======================
            {self.state.research}
            =======================
            </research>
            """
            )
        else:
            self.state.tweet = llm.call(
                f"""
            You wrote this tweet post on {self.state.topic}, but it does not have a good virality
            because of {self.state.score.reason}
            
            Improve it.

            <tweet>
            {self.state.tweet.model_dump_json()}
            </tweet>

            Use the following research.

            <research>
            =======================
            {self.state.research}
            =======================
            </research>
            """
            )

    @listen(or_("make_linkedin_post", "remake_linkedin_post"))
    def handle_make_linkedin(self):
        # if linkedin post has been made, show the old one to the ai and ask it to improve,
        # elese just ask to create.
        linkedin_post = self.state.linkedin
        llm = LLM(model="openai/o4-mini", response_format=LinkedInPost)

        if linkedin_post is None:
            self.state.linkedin = llm.call(
                f"""
            Make a linkedin post that can go viral on the topic {self.state.topic} using the following research:

            <research>
            =======================
            {self.state.research}
            =======================
            </research>
            """
            )
        else:
            self.state.linkedin = llm.call(
                f"""
            You wrote this linkedin post on {self.state.topic}, but it does not have a good virality
            because of {self.state.score.reason}
            
            Improve it.

            <blog_post>
            {self.state.linkedin.model_dump_json()}
            </blog_post>

            Use the following research.

            <research>
            =======================
            {self.state.research}
            =======================
            </research>
            """
            )

    @listen(handle_make_blog)
    def check_seo(self):
        result = (
            SeoCrew()
            .crew()
            .kickoff(
                inputs={
                    "topic": self.state.topic,
                    "blog_post": self.state.blog.model_dump_json(),
                }
            )
        )
        self.state.score = result.pydantic

    @listen(or_(handle_make_tweet, handle_make_linkedin))
    def check_virality(self):
        result = (
            ViralityCrew()
            .crew()
            .kickoff(
                inputs={
                    "topic": self.state.topic,
                    "content_type": self.state.content_type,
                    "content": (
                        self.state.tweet.model_dump_json()
                        if self.state.content_type == "tweet"
                        else self.state.linkedin.model_dump_json()
                    ),
                }
            )
        )
        self.state.score = result.pydantic

    @router(or_(check_seo, check_virality))
    def score_router(self):
        content_type = self.state.content_type
        score = self.state.score

        if score.score >= 8:
            return "check_passed"
        else:
            if content_type == "blog":
                return "remake_blog"
            elif content_type == "linkedin":
                return "remake_linkedin_post"
            else:
                return "remake_tweet"

    @listen("check_passed")
    def finalize_content(self):
        """Finalize the content"""
        print("🎉 Finalizing content...")

        if self.state.content_type == "blog":
            print(f"📝 Blog Post: {self.state.blog_post.title}")
            print(f"🔍 SEO Score: {self.state.score.score}/100")
        elif self.state.content_type == "tweet":
            print(f"🐦 Tweet: {self.state.tweet}")
            print(f"🚀 Virality Score: {self.state.score.score}/100")
        elif self.state.content_type == "linkedin":
            print(f"💼 LinkedIn: {self.state.linkedin_post.title}")
            print(f"🚀 Virality Score: {self.state.score.score}/100")

        print("✅ Content ready for publication!")
        return (
            self.state.linkedin_post
            if self.state.content_type == "linkedin"
            else (
                self.state.tweet
                if self.state.content_type == "tweet"
                else self.state.blog_post
            )
        )


flow = ContentPipelineFlow()
# flow.plot()
flow.kickoff(
    inputs={
        "content_type": "blog",
        "topic": "AI Dog Training",
    }
)
