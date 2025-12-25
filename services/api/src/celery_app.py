import os
from celery import Celery
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from .config import settings
from .skill_manager import SkillManager 

celery_app = Celery(
    "gibh_worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

skill_mgr = SkillManager()

@celery_app.task(bind=True)
def run_bioinformatics_task(self, workflow_data: dict, files: list):
    """
    统一任务入口
    """
    print(f"🚀 [Worker] 收到任务，文件列表: {[f.get('name') for f in files]}")
    return _run_local_skill(self, workflow_data, files)

def _generate_ai_interpretation(qc_metrics, steps_details):
    """
    🤖 AI Doctor: 根据分析结果生成专业解读报告
    """
    try:
        # 1. 提取关键信息
        raw_cells = qc_metrics.get('raw_cells', 'N/A')
        filtered_cells = qc_metrics.get('filtered_cells', 'N/A')
        
        # 尝试从步骤详情中提取 Marker 基因信息
        markers_info = "未找到 Marker 基因信息"
        n_clusters = "未知"
        
        for step in steps_details:
            if step['name'] == 'local_cluster':
                n_clusters = step.get('summary', '未知')
            if step['name'] == 'local_markers':
                # 这里通常是 HTML 表格，我们简单提取一下或者直接把 HTML 扔给 LLM (如果不太长)
                # 为了节省 token，这里假设 LLM 能看懂简单的 HTML 结构，或者我们只传 summary
                markers_info = step.get('details', '未生成 Marker 表')

        # 2. 连接 vLLM (在 Docker 内部网络中)
        llm = ChatOpenAI(
            model=settings.LLM_MODEL,
            base_url=settings.VLLM_URL, # http://inference-engine:8000/v1
            api_key="EMPTY",
            temperature=0.2,
            max_tokens=2048
        )

        # 3. 构造 Prompt
        prompt_text = f"""
        你是一位资深的单细胞生物信息学专家。请根据以下 Scanpy 分析结果，撰写一份详细的分析报告。

        【数据概况】
        - 原始细胞数: {raw_cells}
        - 质控后细胞数: {filtered_cells}
        - 聚类结果: {n_clusters}

        【差异基因 (Markers) 数据片段】
        {markers_info}

        【任务要求】
        1. **数据质量评估**：根据过滤前后的细胞数量变化，评价数据质量（如：损失率是否过高？）。
        2. **聚类分析**：评价聚类数量是否合理。
        3. **生物学推断**：根据 Marker 基因列表（如果有），尝试推断可能存在的细胞类型（如 T细胞、B细胞等），或者指出最显著的基因。
        4. **下一步建议**：给出后续分析建议（如细胞注释、拟时序分析）。

        请使用 Markdown 格式输出，语气专业、客观。不要输出代码，只输出分析文本。
        """

        prompt = ChatPromptTemplate.from_template(prompt_text)
        chain = prompt | llm
        
        print("🧠 [Worker] 正在请求 AI 生成诊断报告...")
        response = chain.invoke({})
        return response.content

    except Exception as e:
        print(f"⚠️ [Worker] AI 报告生成失败: {e}")
        return f"（AI 解读生成失败，请检查推理引擎连接。错误信息: {str(e)}）\n\n原始数据指标：原始细胞 {raw_cells} -> 过滤后 {filtered_cells}"

def _run_local_skill(task_instance, workflow_data, files):
    """执行本地 Python 插件"""
    
    if not files:
        return {"status": "failed", "error": "❌ 错误：未接收到文件信息。"}
    
    # 智能路径处理
    target_file_name = files[0]['name']
    is_10x = False
    for f in files:
        if 'matrix.mtx' in f['name']:
            is_10x = True
            break
    
    if is_10x:
        data_input_path = settings.UPLOAD_DIR
    else:
        data_input_path = os.path.join(settings.UPLOAD_DIR, target_file_name)

    if not os.path.exists(data_input_path):
        return {"status": "failed", "error": f"❌ 错误：找不到路径 {data_input_path}"}
    
    merged_params = {}
    for step in workflow_data['steps']:
        merged_params.update(step.get('params', {}))
    
    skill = skill_mgr.get_skill("scanpy_local")
    if not skill:
        skill_mgr._load_skills()
        skill = skill_mgr.get_skill("scanpy_local")
        if not skill:
            return {"status": "failed", "error": "❌ 严重错误：无法加载 scanpy_local 插件。"}
    
    try:
        print("▶️ 开始执行 Scanpy Pipeline...")
        task_instance.update_state(state='PROGRESS', meta={'steps': [{"name": "正在初始化 Scanpy...", "status": "running"}]})
        
        # 1. 执行生信分析
        result = skill.execute(data_input_path, merged_params, settings.UPLOAD_DIR)
        
        if result['status'] == 'success':
            # 2. 🔥🔥🔥 核心修复：调用 LLM 生成真正的诊断报告
            # 用 AI 生成的内容覆盖原本 scrna_analysis.py 里硬编码的 diagnosis
            task_instance.update_state(state='PROGRESS', meta={'steps': [{"name": "正在生成 AI 诊断报告...", "status": "running"}]})
            
            ai_diagnosis = _generate_ai_interpretation(result['qc_metrics'], result['steps_details'])
            result['diagnosis'] = ai_diagnosis
            
        print(f"✅ 执行结束，状态: {result.get('status')}")
        return result
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"status": "failed", "error": f"运行异常: {str(e)}"}

def _run_galaxy_task(task_instance, workflow_data, files):
    return {"status": "success", "steps": []}
