from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class FileInfo(BaseModel):
    id: str
    name: str

class ChatRequest(BaseModel):
    message: str
    history: List[Dict[str, str]] = []
    # 对应前端的 selectedTool
    selected_tool: Optional[Dict[str, Any]] = None
    # 对应前端的 toolParams
    tool_params: Optional[Dict[str, Any]] = None
    # 对应前端的 workflowData
    workflow_data: Optional[Dict[str, Any]] = None
    # 对应前端的 uploadedFiles
    uploaded_files: List[FileInfo] = []
    # 对应前端的 useHistoryFiles
    use_history_files: bool = False
