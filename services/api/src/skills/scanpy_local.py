import sys
import os

# 修复导入路径
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(current_dir)
if src_dir not in sys.path:
    sys.path.append(src_dir)

try:
    from scrna_analysis import LocalSingleCellPipeline
except ImportError:
    # Docker 环境下的备用导入
    from src.scrna_analysis import LocalSingleCellPipeline

META = {
    "id": "scanpy_local",
    "name": "Local Scanpy Engine (Full)",
    "description": "Execute standard 10-step scRNA-seq pipeline",
    "template": {
        "name": "Standard Scanpy Pipeline",
        "steps": [
            {"name": "Quality Control", "tool_id": "local_qc", "params": {"min_genes": "200", "max_mt": "20"}},
            {"name": "Normalization", "tool_id": "local_normalize", "params": {}},
            {"name": "Find Variable Genes", "tool_id": "local_hvg", "params": {}},
            {"name": "Scale Data", "tool_id": "local_scale", "params": {}},
            {"name": "PCA", "tool_id": "local_pca", "params": {}},
            {"name": "Compute Neighbors", "tool_id": "local_neighbors", "params": {}},
            {"name": "Clustering", "tool_id": "local_cluster", "params": {"resolution": "0.5"}},
            {"name": "UMAP Visualization", "tool_id": "local_umap", "params": {}},
            {"name": "t-SNE Visualization", "tool_id": "local_tsne", "params": {}},
            {"name": "Find Markers", "tool_id": "local_markers", "params": {}}
        ]
    }
}

def execute(file_path, params, output_dir):
    print(f"🚀 [Scanpy Skill] Starting analysis on: {file_path}")
    
    # 确保结果目录存在
    results_dir = os.path.join(output_dir, "results")
    os.makedirs(results_dir, exist_ok=True)
    
    pipeline = LocalSingleCellPipeline(output_dir=results_dir)
    
    # 使用 META 中的模板作为基准
    steps_config = META['template']['steps']
    
    # 注入用户参数
    for step in steps_config:
        step_params = step.get('params', {})
        for key in step_params.keys():
            if key in params:
                step['params'][key] = params[key]

    return pipeline.run_pipeline(file_path, steps_config)
