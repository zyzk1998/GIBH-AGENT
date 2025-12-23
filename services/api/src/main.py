import os
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from celery.result import AsyncResult

from .config import settings
from .schemas import ChatRequest
from .agent import BioBlendAgent
from .celery_app import celery_app, run_bioinformatics_task

app = FastAPI(title="GIBH Commercial API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

agent = BioBlendAgent()

@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    """
    处理用户对话或工作流执行请求
    """
    # 🟢 分支 A: 用户点击了“运行工作流”
    if req.workflow_data:
        task = run_bioinformatics_task.delay(
            workflow_data=req.workflow_data,
            files=[f.dict() for f in req.uploaded_files]
        )
        return {
            "type": "workflow_started",
            "run_id": task.id,
            "reply": f"🚀 工作流已启动！任务ID: {task.id}\n正在后台计算，请稍候...",
            "thought": "任务已提交至 Celery 分布式队列。"
        }

    # 🔵 分支 B: 智能对话 / 意图识别
    response = await agent.process_query(
        query=req.message,
        history=req.history,
        uploaded_files=req.uploaded_files
    )
    
    # 判断返回类型
    if hasattr(response, "__aiter__"):
        return StreamingResponse(response, media_type="text/plain")
    
    return response

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        file_path = os.path.join(settings.UPLOAD_DIR, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        return {"status": "success", "file_name": file.filename, "file_id": file.filename}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/workflow/status/{run_id}")
async def get_status(run_id: str):
    task_result = AsyncResult(run_id, app=celery_app)
    
    response = {
        "status": "running",
        "completed": False,
        "steps_status": [], 
        "error": None
    }

    if task_result.state == 'PENDING':
        response["status"] = "running"
        
    elif task_result.state == 'SUCCESS':
        response["status"] = "success"
        response["completed"] = True
        
        result_data = task_result.result 
        if result_data:
            # 🔥🔥🔥 核心修复：将 Worker 的结果（包含图片路径）透传给前端
            response["report_data"] = result_data
            
            # 兼容进度条显示
            if "steps_details" in result_data:
                response["steps_status"] = result_data["steps_details"]
            elif "steps" in result_data:
                response["steps_status"] = result_data["steps"]
                
    elif task_result.state == 'FAILURE':
        response["status"] = "failed"
        response["completed"] = True
        response["error"] = str(task_result.result)
        
    elif task_result.state == 'PROGRESS':
        info = task_result.info
        if isinstance(info, dict):
            response["steps_status"] = info.get("steps", [])
    
    return response

