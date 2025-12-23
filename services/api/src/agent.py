import json
import asyncio
from typing import AsyncGenerator, Union
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage
from .config import settings

class BioBlendAgent:
    def __init__(self):
        # 连接到 vLLM (RTX 6000)
        self.llm = ChatOpenAI(
            model=settings.LLM_MODEL,
            base_url=settings.VLLM_URL,
            api_key="EMPTY",
            temperature=0.1, 
            max_tokens=4096,
            streaming=True
        )

    async def process_query(self, query: str, history: list, uploaded_files: list = None) -> Union[dict, AsyncGenerator]:
        """
        智能处理入口
        """
        query_text = query.lower().strip()
        
        # 1. 显式意图识别
        if any(k in query_text for k in ["规划", "流程", "workflow", "pipeline"]):
            return self._generate_workflow_config(query, uploaded_files)

        # 2. 隐式意图识别 (Context Awareness)
        if uploaded_files and (not query_text or query_text == "发送了文件" or len(query_text) < 5):
            if history and len(history) > 0:
                last_msg = history[-1]
                if last_msg.get('role') == 'assistant' and "未上传数据" in last_msg.get('content', ''):
                    return self._generate_workflow_config("规划流程", uploaded_files)

        # 3. 默认：流式对话 (带深度思考)
        return self._stream_chat(query, uploaded_files)

    def _get_filename(self, f):
        if isinstance(f, dict):
            return f.get('name', 'unknown')
        return getattr(f, 'name', 'unknown')

    def _generate_workflow_config(self, query, uploaded_files=None):
        """
        生成前端可渲染的工作流配置卡片
        """
        if not uploaded_files:
            reply_text = "已为您规划标准分析流程。⚠️ **检测到您尚未上传数据**，请先点击回形针上传 .h5ad 或 .mtx 文件，然后再点击“执行”。"
        else:
            names = [self._get_filename(f) for f in uploaded_files]
            file_names = ", ".join(names)
            reply_text = f"收到文件：**{file_names}**。\n已为您自动匹配 **Standard Scanpy Pipeline (10 Steps)**，涵盖从质控到多维可视化的全流程。请确认参数："

        return {
            "type": "workflow_config",
            "reply": reply_text,
            "workflow_name": "Standard Scanpy Pipeline",
            "steps": [
                {"name": "1. Quality Control", "tool_id": "local_qc", "desc": "Filter cells & genes", "params": [{"name": "min_genes", "label": "Min Genes", "value": "200", "type": "text"}, {"name": "max_mt", "label": "Max MT%", "value": "20", "type": "text"}]},
                {"name": "2. Normalization", "tool_id": "local_normalize", "desc": "Log1p Normalize", "params": []},
                {"name": "3. Find Variable Genes", "tool_id": "local_hvg", "desc": "Select top 2000 genes", "params": []},
                {"name": "4. Scale Data", "tool_id": "local_scale", "desc": "Scale to unit variance", "params": []},
                {"name": "5. PCA", "tool_id": "local_pca", "desc": "Dimensionality Reduction", "params": []},
                {"name": "6. Compute Neighbors", "tool_id": "local_neighbors", "desc": "Build neighborhood graph", "params": []},
                {"name": "7. Clustering", "tool_id": "local_cluster", "desc": "Leiden Clustering", "params": [{"name": "resolution", "label": "Resolution", "value": "0.5", "type": "text"}]},
                {"name": "8. UMAP Visualization", "tool_id": "local_umap", "desc": "Non-linear embedding", "params": []},
                {"name": "9. t-SNE Visualization", "tool_id": "local_tsne", "desc": "t-SNE Visualization", "params": []},
                {"name": "10. Find Markers", "tool_id": "local_markers", "desc": "Identify cluster markers", "params": []}
            ],
            "thought": "识别到用户需要规划分析流程，已加载 Scanpy 完整标准模板。"
        }

    async def _stream_chat(self, query: str, uploaded_files=None) -> AsyncGenerator[str, None]:
        """
        流式对话生成器 (注入思维链指令)
        """
        # 1. 构建上下文
        file_context = ""
        if uploaded_files:
            names = [self._get_filename(f) for f in uploaded_files]
            file_context = f"\n[User Context - Uploaded Files]: {', '.join(names)}"

        # 2. 定义系统人设 (System Prompt) - 🔥 核心修改：强制输出 <think> 标签
        system_template = """你是一个专业的生物信息学专家助手 GIBH-Agent。

请按照以下步骤回答问题：
1. **深度思考 (Thinking Process)**：首先，在 `<think>` 和 `</think>` 标签内，详细规划你的回答逻辑、分析用户意图、检查是否有潜在的坑（如文件格式、参数设置）。这部分内容不要直接展示给用户看。
2. **正式回答 (Response)**：思考结束后，在标签外给出最终的、结构清晰的回答。

请遵循：
- 准确性优先，不要编造。
- 使用 Markdown 格式。
- 拒绝无关问题。

{file_context}
"""
        system_message = SystemMessagePromptTemplate.from_template(system_template)
        human_message = HumanMessagePromptTemplate.from_template("{query}")
        
        chat_prompt = ChatPromptTemplate.from_messages([system_message, human_message])
        
        chain = chat_prompt | self.llm
        
        # 3. 执行流式生成
        async for chunk in chain.astream({"query": query, "file_context": file_context}):
            content = ""
            if hasattr(chunk, 'content') and chunk.content:
                content = chunk.content
            elif isinstance(chunk, str):
                content = chunk
            
            if content:
                yield content
                # 平滑阻尼 (RTX 6000 专用)
                await asyncio.sleep(0.01)
