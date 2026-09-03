import logging
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from libs.shared.tasks import celery_app, run_analysis_workflow

# Configure simple logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Sustainable Packaging API")

# Allow CORS for React local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/analysis")
async def start_analysis(
    product_name: str = Form(...),
    units: int = Form(...),
    length: float = Form(...),
    width: float = Form(...),
    height: float = Form(...),
    location: str = Form(...),
    budget: float = Form(...),
    properties_weight: float = Form(...),
    logistics_weight: float = Form(...),
    cost_weight: float = Form(...),
    sustainability_weight: float = Form(...),
    consumer_weight: float = Form(...),
    requires_carbon_lca: bool = Form(False),
    requires_compliance_doc: bool = Form(False),
    bom_file: Optional[UploadFile] = File(None)
):
    try:
        volume = length * width * height

        # Build the input data payload
        input_data = {
            "product_name": product_name,
            "units_per_shipment": units,
            "dimensions": {"length": length, "width": width, "height": height},
            "packaging_location": location,
            "budget_constraint": budget,
            "properties_weight": properties_weight,
            "logistics_weight": logistics_weight,
            "cost_weight": cost_weight,
            "sustainability_weight": sustainability_weight,
            "consumer_weight": consumer_weight,
            "requires_carbon_lca": requires_carbon_lca,
            "requires_compliance_doc": requires_compliance_doc,
            "bom_uploaded": bom_file is not None,
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "user": "system",
                "volume": volume
            }
        }

        # Enqueue the Celery task
        task = run_analysis_workflow.delay(input_data)

        return {"task_id": task.id, "status": "processing"}

    except Exception as e:
        logger.error(f"Error starting analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analysis/{task_id}")
async def get_analysis_status(task_id: str):
    task = celery_app.AsyncResult(task_id)
    if task.state == 'PENDING':
        return {"status": "processing"}
    elif task.state == 'SUCCESS':
        return {"status": "completed", "result": task.result}
    elif task.state == 'FAILURE':
        return {"status": "failed", "error": str(task.info)}
    else:
        return {"status": "processing"}

@app.get("/health")
def health_check():
    return {"status": "ok"}
