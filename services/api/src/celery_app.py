from celery import Celery
from .config import settings
from .skill_manager import SkillManager 
import os

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
    
    # 🛑 强制走本地分析逻辑 (移除 Galaxy 分支，防止假成功)
    return _run_local_skill(self, workflow_data, files)

def _run_local_skill(task_instance, workflow_data, files):
    """执行本地 Python 插件"""
    
    if not files:
        return {"status": "failed", "error": "❌ 错误：未接收到文件信息。"}
    
    # === 📂 智能路径处理 (关键修复) ===
    # 默认取第一个文件
    target_file_name = files[0]['name']
    
    # 检查是否为 10x Genomics 格式 (通常包含 matrix.mtx)
    is_10x = False
    for f in files:
        if 'matrix.mtx' in f['name']:
            is_10x = True
            break
    
    if is_10x:
        # 如果是 10x 数据，Scanpy 需要读取的是"目录"，而不是文件
        # Docker 里的上传目录是 settings.UPLOAD_DIR
        data_input_path = settings.UPLOAD_DIR
        print(f"📂 检测到 10x 格式，设置输入路径为目录: {data_input_path}")
    else:
        # 如果是 h5ad，直接读取文件
        data_input_path = os.path.join(settings.UPLOAD_DIR, target_file_name)
        print(f"📂 检测到单文件格式，设置输入路径为: {data_input_path}")

    # 再次校验物理路径
    if not os.path.exists(data_input_path):
        return {"status": "failed", "error": f"❌ 错误：找不到路径 {data_input_path}"}
    
    # 提取参数
    merged_params = {}
    for step in workflow_data['steps']:
        merged_params.update(step.get('params', {}))
    
    # 获取插件
    skill = skill_mgr.get_skill("scanpy_local")
    if not skill:
        # 尝试重新加载
        skill_mgr._load_skills()
        skill = skill_mgr.get_skill("scanpy_local")
        if not skill:
            return {"status": "failed", "error": "❌ 严重错误：无法加载 scanpy_local 插件，请检查 skills 目录。"}
    
    # === 执行 ===
    try:
        print("▶️ 开始执行 Scanpy Pipeline...")
        task_instance.update_state(state='PROGRESS', meta={'steps': [{"name": "正在初始化 Scanpy...", "status": "running"}]})
        
        # 执行分析
        result = skill.execute(data_input_path, merged_params, settings.UPLOAD_DIR)
        
        print(f"✅ 执行结束，状态: {result.get('status')}")
        return result
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"status": "failed", "error": f"运行异常: {str(e)}"}
