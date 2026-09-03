from typing import Callable, Dict, List, Any
from dataclasses import dataclass

@dataclass
class AgentDefinition:
    name: str
    phase: int
    trigger_condition: Callable[[Dict[str, Any]], bool]

class AgentRegistry:
    def __init__(self):
        self.agents: List[AgentDefinition] = []

    def register(self, name: str, phase: int, trigger_condition: Callable[[Dict[str, Any]], bool]):
        self.agents.append(AgentDefinition(name=name, phase=phase, trigger_condition=trigger_condition))

    def get_agents_for_phase(self, phase: int, input_data: Dict[str, Any]) -> List[str]:
        return [
            agent.name for agent in self.agents
            if agent.phase == phase and agent.trigger_condition(input_data)
        ]

# Global Registry Instance
registry = AgentRegistry()

# Phase 1: Core Analysts
registry.register(
    "properties", 1,
    lambda _: True  # Always runs
)
registry.register(
    "logistics", 1,
    lambda _: True
)
registry.register(
    "costs", 1,
    lambda _: True
)
registry.register(
    "sustainability", 1,
    lambda _: True
)
registry.register(
    "consumer", 1,
    lambda input_data: "b2b" not in input_data.get("target_market", "").lower() 
                       and "industrial" not in input_data.get("target_market", "").lower()
)

# Phase 2: Synthesis / Add-ons
registry.register(
    "carbon_lca", 2,
    lambda input_data: (
        "esg" in input_data.get("sustainability_goals", "").lower() or
        input_data.get("requires_carbon_lca", False)
    )
)
registry.register(
    "compliance_doc", 2,
    lambda input_data: input_data.get("requires_compliance_doc", False)
)
