__all__ = ["LocalChatAgent"]

import base64
from typing import Literal, AsyncIterator

import ag_ui.core
import pydantic.alias_generators
import pydantic_ai
import pydantic_ai.models.openai
import pydantic_ai.providers.openai

import ravnar.agents


class AgentMetadata(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(alias_generator=pydantic.alias_generators.to_camel, populate_by_name=True)

    apollo_location: Literal["local", "hub"]


class LocalChatAgent(ravnar.agents.Agent):
    def __init__(self, *, model_id: str, model_name: str, model_provider: str, model_base_url: str):
        self._agent = ravnar.agents.PydanticAiAgentWrapper(
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
                metadata=AgentMetadata(apollo_location="local").model_dump(mode="json"),
            )
        ),
    )

    async def run(self, input: ag_ui.core.RunAgentInput) -> AsyncIterator[ag_ui.core.Event]:
        for m in input.messages:
            if isinstance(m, ag_ui.core.UserMessage) and not isinstance(m.content, str):
                m.content = self._inline_documents(m.content)

        async for event in self._agent.run(input):
            yield event


    def _inline_documents(self, input_contents: list[ag_ui.core.InputContent]) -> list[ag_ui.core.InputContent]:
        ics: list[ag_ui.core.InputContent] = []
        for ic in input_contents:
            if isinstance(ic, ag_ui.core.DocumentInputContent):
                ic = ag_ui.core.TextInputContent(text=self._parse_document(ic))

            ics.append(ic)
        return ics

    def _parse_document(self, document_input_content: ag_ui.core.DocumentInputContent) -> str:
        assert isinstance(document_input_content.source, ag_ui.core.InputContentDataSource)

        return base64.b64decode(document_input_content.source.value).decode()
