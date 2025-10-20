from altk.core.toolkit import AgentPhase
from altk.pre_llm.core.config import (
    SpotLightConfig,
    SpotLightMetadata,
    SpotLightRunInput,
)
from altk.pre_llm.spotlight.spotlight import SpotLightComponent


class TestSpotLightComponent:
    """Integration test for SpotLight"""

    def test_spotlight_example(self):
        """End-to-end test for SpotLight."""

        model_path = "Qwen/Qwen2.5-1.5B-Instruct"
        config = SpotLightConfig(
            model_path=model_path,
            generation_kwargs={"do_sample": False, "max_new_tokens": 5},
        )
        middleware = SpotLightComponent(config=config)
        prompt = "Write a story about a family that goes camping in the woods.\n\nYour response should follow the instructions below:\n- Your entire response should be in English and in all capital letters."
        emph_span = (
            "- Your entire response should be in English and in all capital letters."
        )

        conversation_context = [{"role": "user", "content": prompt}]

        run_input = SpotLightRunInput(
            messages=conversation_context,
            metadata=SpotLightMetadata(emph_strings=emph_span, alpha=0.1),
        )
        result = middleware.process(run_input, phase=AgentPhase.RUNTIME)
        assert result is not None
        prediction = result.output.prediction
        assert prediction is not None
