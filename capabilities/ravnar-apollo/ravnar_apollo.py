from typing import Literal

import ag_ui.core
import pydantic.alias_generators
import pydantic_ai
import pydantic_ai.models.openai
import pydantic_ai.providers.openai

import ravnar.agents


class RavnarApolloMetadata(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(alias_generator=pydantic.alias_generators.to_camel, populate_by_name=True)

    location: Literal["local", "hub"]


def local_chat_agent(
    *, model_id: str, model_name: str, model_provider: str, model_base_url: str
) -> ravnar.agents.Agent:
    return ravnar.agents.PydanticAiAgentWrapper(
        pydantic_ai.Agent(
            pydantic_ai.models.openai.OpenAIChatModel(
                model_id, provider=pydantic_ai.providers.openai.OpenAIProvider(base_url=model_base_url, api_key="")
            )
        ),
        capabilities=ag_ui.core.AgentCapabilities(
            identity=ag_ui.core.IdentityCapabilities(
                name=model_name,
                provider=model_provider,
                description=f"A local instance of the {model_name} model provided by {model_provider}",
                metadata={
                    "apollo": RavnarApolloMetadata(
                        location="local",
                    )
                },
            )
        ),
    )
