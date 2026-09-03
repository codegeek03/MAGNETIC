import asyncio
import logging
import operator
import os
from datetime import datetime, timezone
from typing import Any, Dict, TypedDict

try:
    from typing import Annotated  # Python 3.9+
except ImportError:
    from typing_extensions import Annotated  # type: ignore[assignment]

# LangGraph imports
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

# Centralised settings + shared service infrastructure
from libs.shared.settings import get_settings
from services.base.prompt_loader import PromptLoader
from services.base.tool_registry import ToolRegistry

# ── Process-scoped singletons (built once, injected everywhere) ────────────────
_settings = get_settings()
_prompt_loader = PromptLoader()
_tool_registry = ToolRegistry()

CURRENT_USER = _settings.current_user
CURRENT_TIME = _settings.now_utc()

# ── Service layer imports (replace old agents/ imports) ────────────────────────
from agents.detail_input import ProductInput  # noqa: E402
from services.consumer_behavior.agent import ConsumerBehaviorService  # noqa: E402
from services.cost.agent import ProductionCostService  # noqa: E402
from services.logistics.agent import LogisticsService  # noqa: E402
from services.material_properties.agent import MaterialPropertiesService  # noqa: E402
from services.materials_db.agent import MaterialsDatabaseService  # noqa: E402
from services.orchestrator.agent import OrchestratorService  # noqa: E402
from services.product_compatibility.agent import ProductCompatibilityService  # noqa: E402
from services.sustainability.agent import SustainabilityService  # noqa: E402

# ── Backward-compat aliases (app.py and tests import these names) ─────────────
ProductCompatibilityAgent = ProductCompatibilityService
PackagingMaterialsAgent   = MaterialsDatabaseService
MaterialPropertiesAgent   = MaterialPropertiesService
LogisticCompatibilityAgent = LogisticsService
ProductionCostAgent       = ProductionCostService
EnvironmentalImpactAgent  = SustainabilityService
ConsumerBehaviorAgent     = ConsumerBehaviorService
OrchestrationAgent        = OrchestratorService

# Set up JSON logging and Sentry
import sentry_sdk
from pythonjsonlogger import jsonlogger

logger = logging.getLogger()
logger.setLevel(logging.INFO)
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter('%(asctime)s %(name)s %(levelname)s %(message)s')
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)

if sentry_dsn := os.getenv("SENTRY_DSN"):
    sentry_sdk.init(
        dsn=sentry_dsn,
        traces_sample_rate=1.0,
    )


# State definition
class AnalysisState(TypedDict):
    input_data: Annotated[Dict[str, Any], "input_data"]
    compatibility_analysis: Annotated[Dict[str, Any], "compatibility_analysis"]
    material_database: Annotated[Dict[str, Any], "material_database"]
    properties_analysis: Annotated[Dict[str, Any], "properties_analysis"]
    logistics_analysis: Annotated[Dict[str, Any], "logistics_analysis"]
    cost_analysis: Annotated[Dict[str, Any], "cost_analysis"]
    sustainability_analysis: Annotated[Dict[str, Any], "sustainability_analysis"]
    consumer_analysis: Annotated[Dict[str, Any], "consumer_analysis"]
    carbon_lca_analysis: Annotated[Dict[str, Any], "carbon_lca_analysis"]
    compliance_doc_analysis: Annotated[Dict[str, Any], "compliance_doc_analysis"]
    final_results: Annotated[Dict[str, Any], "final_results"]
    input_status: Annotated[str, "input_status"]
    compatibility_status: Annotated[str, "compatibility_status"]
    material_db_status: Annotated[str, "material_db_status"]
    properties_status: Annotated[str, "properties_status"]
    logistics_status: Annotated[str, "logistics_status"]
    costs_status: Annotated[str, "costs_status"]
    sustainability_status: Annotated[str, "sustainability_status"]
    consumer_status: Annotated[str, "consumer_status"]
    carbon_lca_status: Annotated[str, "carbon_lca_status"]
    compliance_doc_status: Annotated[str, "compliance_doc_status"]
    consumer_skipped: Annotated[bool, "consumer_skipped"]
    orchestration_status: Annotated[str, "orchestration_status"]
    error: Annotated[str, operator.add] # This is correctly set to append mode
    user_login: Annotated[str, "user_login"]
    current_time: Annotated[str, "current_time"]



# Node definitions
async def process_input(state: AnalysisState) -> Dict:
    logger.info("Starting input processing")
    try:
        if not state.get("input_data"):
            agent = ProductInput(CURRENT_TIME, CURRENT_USER)
            details = await agent.get_product_details()

            return {
                "input_data": details,
                "input_status": "completed",
                "user_login": CURRENT_USER,
                "current_time": CURRENT_TIME
            }
        return {}
    except Exception as e:
        msg = f"Input processing failed: {e}"
        logger.error(msg, exc_info=True)
        return {
            "error": msg,
            "input_status": "failed"
        }

async def analyze_product_compatibility(state: AnalysisState) -> Dict:
    logger.info("Starting product compatibility analysis")
    try:
        if state.get("error"):
            return {}
        agent = ProductCompatibilityAgent()
        result = await agent.analyze_product_compatibility(
            state["input_data"]["product_name"],
            state["input_data"]
        )
        return {
            "compatibility_analysis": result,
            "compatibility_status": "completed"
        }
    except Exception as e:
        msg = f"Product compatibility analysis failed: {e}"
        logger.error(msg, exc_info=True)
        return {
            "error": msg,
            "compatibility_status": "failed"
        }

async def query_material_database(state: AnalysisState) -> Dict:
    logger.info("Starting material database query")
    try:
        if state.get("error"):
            return {}
        agent = PackagingMaterialsAgent(CURRENT_USER, CURRENT_TIME)
        result = await agent.find_materials_by_criteria(state["compatibility_analysis"],state["input_data"])
        if not result.get("materials"):
            raise ValueError("No compatible materials found")
        return {
            "material_database": result,
            "material_db_status": "completed"
        }
    except Exception as e:
        msg = f"Material DB query failed: {e}"
        logger.error(msg, exc_info=True)
        return {
            "error": msg,
            "material_db_status": "failed"
        }

async def analyze_material_properties(state: AnalysisState) -> Dict:
    logger.info("Starting material properties analysis")
    if state.get("error"):
        return {}
    try:
        agent = MaterialPropertiesAgent()
        result = await agent.analyze_material_properties(state["material_database"])
        return {
            "properties_analysis": result,
            "properties_status": "completed"
        }
    except Exception as e:
        msg = f"Material properties analysis failed: {e}"
        logger.error(msg, exc_info=True)
        return {
            "error": msg,
            "properties_status": "failed"
        }

async def analyze_logistics(state: AnalysisState) -> Dict:
    logger.info("Starting logistics analysis")
    if state.get("error"):
        return {}
    try:
        agent = LogisticCompatibilityAgent()
        result = await agent.analyze_top_logistics_materials(state["material_database"],state["input_data"])
        return {
            "logistics_analysis": result,
            "logistics_status": "completed"
        }
    except Exception as e:
        msg = f"Logistics analysis failed: {e}"
        logger.error(msg, exc_info=True)
        return {
            "error": msg,
            "logistics_status": "failed"
        }

async def analyze_costs(state: AnalysisState) -> Dict:
    logger.info("Starting cost analysis")
    if state.get("error"):
        return {}
    try:
        agent = ProductionCostAgent()
        result = await agent.analyze_production_costs(state["material_database"],state["input_data"])
        return {
            "cost_analysis": result,
            "costs_status": "completed"
        }
    except Exception as e:
        msg = f"Cost analysis failed: {e}"
        logger.error(msg, exc_info=True)
        return {
            "error": msg,
            "costs_status": "failed"
        }

async def analyze_sustainability(state: AnalysisState) -> Dict:
    logger.info("Starting sustainability analysis")
    if state.get("error"):
        return {}
    try:
        agent = EnvironmentalImpactAgent()
        result = await agent.analyze_environmental_impact(state["material_database"])
        return {
            "sustainability_analysis": result,
            "sustainability_status": "completed"
        }
    except Exception as e:
        msg = f"Sustainability analysis failed: {e}"
        logger.error(msg, exc_info=True)
        return {
            "error": msg,
            "sustainability_status": "failed"
        }

async def analyze_consumer_behavior(state: AnalysisState) -> Dict:
    logger.info("Starting consumer behavior analysis")
    if state.get("error"):
        return {}

    # Phase 4 Effort Scaling: skip consumer analysis for B2B/Industrial products
    target_market = state.get("input_data", {}).get("target_market", "").lower()
    if "b2b" in target_market or "industrial" in target_market:
        logger.info(f"Skipping consumer behavior analysis for B2B/Industrial market: {target_market}")
        return {
            "consumer_analysis": {},
            "consumer_status": "skipped",
            "consumer_skipped": True
        }

    try:
        agent = ConsumerBehaviorAgent()
        result = await agent.analyze_consumer_behavior(state["material_database"])
        return {
            "consumer_analysis": result,
            "consumer_status": "completed",
            "consumer_skipped": False
        }
    except Exception as e:
        msg = f"Consumer behavior analysis failed: {e}"
        logger.error(msg, exc_info=True)
        return {
            "error": msg,
            "consumer_status": "failed"
        }

def calculate_material_scores(
    material: Dict[str, Any],
    analyses: Dict[str, Dict[str, float]],
    weights: Dict[str, float],
    total_weight: float
) -> Dict[str, Any]:
    """Calculate normalized and weighted scores for a material."""
    try:
        key = material.get("material_name") or material.get("id") or material.get("name")
        if not key:
            raise ValueError("Material missing identifier")

        scores = {}
        total_score = 0

        for dim, analysis_scores in analyses.items():
            if dim not in weights:
                logger.warning(f"Missing weight for dimension: {dim}")
                continue

            raw_score = analysis_scores.get(key, 0)
            if not isinstance(raw_score, (int, float)):
                logger.warning(f"Invalid score type for {key} in {dim}: {type(raw_score)}")
                raw_score = 0

            weight = weights[dim]
            normalized = min(max(raw_score, 0), 100)
            weighted = normalized * weight

            scores[dim] = {
                "raw": raw_score,
                "normalized": round(normalized, 2),
                "weighted": round(weighted, 2),
                "weight": weight
            }
            total_score += weighted

        final_score = round(total_score / total_weight, 2) if total_weight > 0 else 0

        return {
            "total_score": final_score,
            "scores": scores,
            "reasoning": {
                "score_breakdown": scores,
                "strengths": [
                    {
                        "dimension": dim,
                        "score": score["normalized"],
                        "impact": round((score["weight"] / total_weight) * 100, 1)
                    }
                    for dim, score in scores.items()
                    if score["normalized"] >= 70
                ],
                "weaknesses": [
                    {
                        "dimension": dim,
                        "score": score["normalized"],
                        "impact": round((score["weight"] / total_weight) * 100, 1)
                    }
                    for dim, score in scores.items()
                    if score["normalized"] <= 30
                ],
                "contribution_analysis": {
                    dim: round((score["weighted"] / total_score * 100), 1)
                    for dim, score in scores.items()
                } if total_score > 0 else {
                    dim: round((score["weight"] / total_weight * 100), 1)
                    for dim, score in scores.items()
                }
            }
        }

    except Exception as e:
        logger.error(f"Score calculation failed for material {key}: {str(e)}", exc_info=True)
        return {
            "total_score": 0,
            "error": str(e),
            "scores": {},
            "reasoning": {
                "score_breakdown": {},
                "error_details": str(e)
            }
        }

async def orchestrate_results(state: AnalysisState) -> Dict:
    """Orchestrate the analysis results and generate final report."""
    logger.info("Starting results orchestration")
    try:
        orchestrator = OrchestrationAgent(CURRENT_TIME, CURRENT_USER, prop_context=state["properties_analysis"])

        ANALYSIS_WEIGHTS = {
    "properties": state["input_data"].get("properties_weight", 0.1),
    "logistics": state["input_data"].get("logistics_weight", 0.1),
    "cost": state["input_data"].get("cost_weight", 0.1),
    "sustainability": state["input_data"].get("sustainability_weight", 0.4),
    "consumer": state["input_data"].get("consumer_weight", 0.2)
}


        materials = state["material_database"].get("materials", {})
        all_materials = []
        for crit_list in materials.values():
            all_materials.extend(crit_list)

        # Gather analysis scores from agent outputs (structured JSONs)
        # Phase 4: Use new Detail/Summary split schemas
        consumer_scores = {
            m["summary"]["material_name"]: m["summary"]["overall_score"] * 10
            for m in state.get("consumer_analysis", {}).get("top_materials", [])
        } if not state.get("consumer_skipped") else {}

        logistics_scores = {
            m["summary"]["material_name"]: m["summary"]["overall_score"] * 10
            for m in state["logistics_analysis"].get("top_materials", [])
        }
        properties_scores = {
            m["summary"]["material_name"]: m["summary"]["overall_score"] * 10
            for m in state["properties_analysis"].get("top_materials", [])
        }
        cost_scores = {
            m["summary"]["material_name"]: m["summary"]["overall_score"] * 10
            for m in state["cost_analysis"].get("top_materials", [])
        }
        sustainability_scores = {
            m["summary"]["material_name"]: m["summary"]["overall_score"] * 10
            for m in state["sustainability_analysis"].get("top_materials", [])
        }

        # Calculate scores with weights
        scored_materials = []
        for material in all_materials:
            name = material.get("material_name")
            if not name:
                continue

            scores = {
                "consumer": consumer_scores.get(name, 0),
                "logistics": logistics_scores.get(name, 0),
                "properties": properties_scores.get(name, 0),
                "cost": cost_scores.get(name, 0),
                "sustainability": sustainability_scores.get(name, 0),
            }

            total_score = sum(
                (scores[cat] * ANALYSIS_WEIGHTS[cat]) for cat in scores
            ) / sum(ANALYSIS_WEIGHTS.values())

            scored_materials.append({
                **material,
                **scores,
                "total_score": round(total_score, 2)
            })

        # Sort and select top materials
        scored_materials.sort(key=lambda x: x["total_score"], reverse=True)
        seen = set()
        top_materials = []
        for m in scored_materials:
            if m["material_name"] not in seen :
                top_materials.append(m)
                seen.add(m["material_name"])
            if len(top_materials) == 5:
                break

        # just before you call generate_executive_summary:
        product_name = state["input_data"]["product_name"]
        k = len(top_materials)  # number of top materials you're iterating over
        location = state["input_data"]["packaging_location"]

        # Generate material-wise executive summaries
        material_summaries = []
        for material in top_materials:
            mat_name = material["material_name"]
            sub_summaries = {}
            for state_key, agent_name in [
                ("properties_analysis", "properties"),
                ("logistics_analysis", "logistics"),
                ("cost_analysis", "cost"),
                ("sustainability_analysis", "sustainability"),
                ("consumer_analysis", "consumer"),
            ]:
                if state_key == "consumer_analysis" and state.get("consumer_skipped"):
                    continue
                tops = state.get(state_key, {}).get("top_materials", [])
                for t in tops:
                    if t.get("summary", {}).get("material_name") == mat_name:
                        sub_summaries[agent_name] = t.get("summary")
                        break

            material["subagent_summaries"] = sub_summaries

            summary = await orchestrator.generate_executive_summary(
                product_name,
                k,
                location,
                material)
            material_summaries.append({
                "material_name": material["material_name"],
                "summary": summary})


        # Prepare final results
        final_results = {
            "product_name": state["input_data"]["product_name"],
            "timestamp": CURRENT_TIME,
            "user": CURRENT_USER,
            "weights_used": ANALYSIS_WEIGHTS,
            "top_materials": top_materials,
            "all_materials": scored_materials,
            "material_summaries": material_summaries,
        }

        # Save report
        report_path = orchestrator._save_report(final_results, "analysis_report")
        final_results["report_path"] = report_path

        return {
            "final_results": final_results,
            "orchestration_status": "completed"
        }

    except Exception as e:
        msg = f"Results orchestration failed: {str(e)}"
        logger.error(msg, exc_info=True)
        return {
            "error": msg,
            "orchestration_status": "failed"
        }


async def handle_error(state: AnalysisState) -> Dict:
    """Handle errors and generate error reports."""
    logger.error(f"Error handler: {state.get('error', 'Unknown error')}")

    try:
        orchestrator = OrchestrationAgent(CURRENT_TIME, CURRENT_USER)

        status_info = {
            "input": state.get("input_status", "unknown"),
            "compatibility": state.get("compatibility_status", "unknown"),
            "material_db": state.get("material_db_status", "unknown"),
            "properties": state.get("properties_status", "unknown"),
            "logistics": state.get("logistics_status", "unknown"),
            "costs": state.get("costs_status", "unknown"),
            "sustainability": state.get("sustainability_status", "unknown"),
            "consumer": state.get("consumer_status", "unknown"),
            "orchestration": state.get("orchestration_status", "unknown")
        }

        error_analysis = await orchestrator.analyze_error(
            state.get("error", "Unknown error"),
            status_info
        )

        error_report = {
            "error": state.get("error", "Unknown error"),
            "user": CURRENT_USER,
            "timestamp": CURRENT_TIME,
            "status": status_info,
            "error_analysis": error_analysis
        }

        report_path = orchestrator._save_report(error_report, "error_report")
        error_report["report_path"] = report_path

        return {"final_results": error_report}

    except Exception as e:
        logger.critical(f"Error handler failed: {e}", exc_info=True)
        return {
            "final_results": {
                "error": f"Error handling failed: {str(e)}",
                "timestamp": CURRENT_TIME,
                "user": CURRENT_USER,
                "status": "critical_failure"
            }
        }

from langgraph.constants import Send

from libs.shared.registry import registry


def route_phase_1(state: AnalysisState):
    if state.get("error") or not state.get("material_database", {}).get("materials"):
        return ["error_handler"]

    active_agents = registry.get_agents_for_phase(1, state.get("input_data", {}))
    # Create Send commands for each active agent
    return [Send(agent, state) for agent in active_agents]

def check_phase_1_completion(state: AnalysisState):
    if state.get("error"):
        return "error_handler"
    return "route_phase_2"

def route_phase_2(state: AnalysisState):
    if state.get("error"):
        return ["error_handler"]

    active_agents = registry.get_agents_for_phase(2, state.get("input_data", {}))
    if not active_agents:
        return ["orchestrator"]

    return [Send(agent, state) for agent in active_agents]

def check_phase_2_completion(state: AnalysisState):
    if state.get("error"):
        return "error_handler"
    return "orchestrator"

def create_analysis_graph(checkpointer=None):
    """Create and configure the analysis workflow graph."""
    workflow = StateGraph(AnalysisState)

    # Add core nodes
    workflow.add_node("input", process_input)
    workflow.add_node("compatibility", analyze_product_compatibility)
    workflow.add_node("material_db", query_material_database)

    # Add phase 1 nodes dynamically
    workflow.add_node("properties", analyze_material_properties)
    workflow.add_node("logistics", analyze_logistics)
    workflow.add_node("costs", analyze_costs)
    workflow.add_node("sustainability", analyze_sustainability)
    workflow.add_node("consumer", analyze_consumer_behavior)

    # Add phase 2 nodes
    async def _run_carbon_lca(state):
        from services.carbon_lca.agent import CarbonLcaService
        return await CarbonLcaService().run_carbon_lca(state)

    async def _run_compliance_doc(state):
        from services.compliance_doc.agent import ComplianceDocService
        return await ComplianceDocService().run_compliance_doc(state)

    workflow.add_node("carbon_lca", _run_carbon_lca)
    workflow.add_node("compliance_doc", _run_compliance_doc)

    workflow.add_node("route_phase_2", lambda s: {})

    workflow.add_node("orchestrator", orchestrate_results)
    workflow.add_node("error_handler", handle_error)

    # Linear flow up to DB
    workflow.add_edge("input", "compatibility")
    workflow.add_edge("compatibility", "material_db")

    # Phase 1 fan-out
    workflow.add_conditional_edges(
        "material_db",
        route_phase_1,
        ["properties", "logistics", "costs", "sustainability", "consumer", "error_handler"]
    )

    # Phase 1 fan-in to phase 2
    for node in ["properties", "logistics", "costs", "sustainability", "consumer"]:
        workflow.add_edge(node, "route_phase_2")

    workflow.add_conditional_edges(
        "route_phase_2",
        route_phase_2,
        ["carbon_lca", "compliance_doc", "orchestrator", "error_handler"]
    )

    # Phase 2 fan-in to orchestrator
    for node in ["carbon_lca", "compliance_doc"]:
        workflow.add_edge(node, "orchestrator")

    workflow.add_edge("orchestrator", END)
    workflow.add_edge("error_handler", END)

    workflow.set_entry_point("input")
    return workflow.compile(checkpointer=checkpointer or MemorySaver())

def print_results(result: Dict[str, Any], thread_id: str):
    """Print analysis results including performance reviews for multiple materials."""
    if result.get("error") or result.get("final_results", {}).get("error"):
        error_info = result if result.get("error") else result.get("final_results", {})
        print("\nAnalysis Error Report")
        print("===================")
        print(f"Error: {error_info.get('error', 'Unknown error')}")
        print(f"Timestamp: {CURRENT_TIME}")
        print(f"Session ID: {thread_id}")

        if error_analysis := error_info.get("error_analysis", {}):
            print("\nError Analysis:")
            print("--------------")
            if root_cause := error_analysis.get("root_cause_analysis", {}):
                print(f"Likely Cause: {root_cause.get('likely_cause', 'Unknown')}")
                if factors := root_cause.get("contributing_factors", []):
                    print("\nContributing Factors:")
                    for factor in factors:
                        print(f"- {factor.get('factor', 'Unknown factor')} "
                              f"(Impact: {factor.get('impact', 'unknown')})")
        return

    results = result.get("final_results", {})
    print("\n Sustainability Analysis Report")
    print("=======================")
    print(f"Session ID: {thread_id}")
    print(f"Timestamp: {CURRENT_TIME}")

    if materials := results.get("material_summaries", []):
        print("\nSustainability Analysis Report")
        print("========================")
        for i, entry in enumerate(materials, 1):
            name   = entry.get("material_name", f"Material {i}")
            review = entry.get("summary", {})

            snapshot = review.get("executive_snapshot", "N/A")
            comp_obj = review.get("composite_score", {})
            metrics  = comp_obj.get("metrics", {})
            composite = comp_obj.get("composite", "N/A")

            strengths    = review.get("strengths", [])
            trade_offs   = review.get("trade_offs", [])
            sci          = review.get("supply_chain_implications", {})
            rec          = review.get("consulting_recommendation", {})
            reg_context  = review.get("regulatory_context", "No regulatory context available.")
            _provenance   = review.get("fact_provenance", [])

            print(f"\n{i}. Material: {name}")
            print("------------------------")
            print(f"Executive Snapshot: {snapshot}")

            print("\n📊 Composite Score:")
            for dim, data in metrics.items():
                val = data.get("value", "")
                score = data.get("score", "")
                print(f"  • {dim.replace('_', ' ').title()}: {val} ➔ score {score}/100")
            print(f"  → Weighted Composite: {composite}/100")

            # Regulatory Context
            print("\n📝 Regulatory Context:")
            for line in reg_context.split("\n"):
                print(f"  {line}")

            if strengths:
                print("\n✅ Key Strengths:")
                for j, s in enumerate(strengths, 1):
                    print(f"  {j}. {s.get('dimension')}: {s.get('insight')}")

            if trade_offs:
                print("\n⚖️ Trade-off Analysis:")
                for j, t in enumerate(trade_offs, 1):
                    print(f"  {j}. {t.get('dimension')}: {t.get('mitigation')}")

            if sci:
                print("\n📦 Supply-Chain Implications:")
                print(f"  • Costs     : {sci.get('costs','')}")
                print(f"  • Logistics : {sci.get('logistics','')}")
                print(f"  • Regulatory: {sci.get('regulatory','')}")
                print(f"  • Consumer  : {sci.get('consumer','')}")

            if rec:
                _advice = rec.get("advice","")
                #uplift = rec.get("sustainability_uplift_percent","N/A")
                #delta  = rec.get("cost_delta_percent","N/A")

                print("\n📈 Consulting Recommendation:")
                #print(f"  • Advice                   : {advice}")
                #print(f"  • Sustainability Uplift %  : {uplift}")
                #print(f"  • Cost Delta %            : {delta}")




async def main():
    """Main execution function."""
    thread_id = f"{CURRENT_USER}-{int(datetime.now(timezone.utc).timestamp())}"

    # Set up logging
    log_filename = f"analysis_log_{CURRENT_TIME.replace(' ', '_').replace(':', '-')}.log"
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename),
            logging.StreamHandler()
        ]
    )

    logger.info(f"Starting analysis session - Thread: {thread_id}")
    logger.info(f"Analysis timestamp: {CURRENT_TIME}")

    try:
        graph = create_analysis_graph()
        result = await graph.ainvoke(
            {},
            config={
                "configurable": {
                    "thread_id": thread_id,
                    "timestamp": CURRENT_TIME,
                    "user": CURRENT_USER
                }
            }
        )

        # Print results
        print_results(result, thread_id)
        logger.info(f"Analysis completed successfully for {result.get('final_results', {}).get('product_name', 'Unknown product')}")

    except Exception as e:
        logger.critical(f"Fatal error in analysis execution: {e}", exc_info=True)
        print("\nFatal Error Report")
        print("=================")
        print(f"Error: {str(e)}")
        print(f"Timestamp: {CURRENT_TIME}")
        print(f"Session ID: {thread_id}")
        print("Please check the log file for detailed error information.")
        print(f"Log File: {log_filename}")

if __name__ == "__main__":
    # Create necessary directories
    os.makedirs("temp_KB", exist_ok=True)
    os.makedirs("temp_KB/reports", exist_ok=True)
    os.makedirs("logs", exist_ok=True)

    # Update current time and user
    CURRENT_TIME = "2025-05-09 21:04:45"  # Updated with provided time

    # Run analysis
    asyncio.run(main())
