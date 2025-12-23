import scanpy as sc
import os
import matplotlib
matplotlib.use('Agg') 
import matplotlib.pyplot as plt
import pandas as pd
import time
import warnings
import io
import base64

warnings.filterwarnings("ignore")

sc.settings.verbosity = 3
sc.settings.set_figure_params(dpi=300, facecolor='white', frameon=True, vector_friendly=True)

class LocalSingleCellPipeline:
    def __init__(self, output_dir="/app/uploads/results"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def _save_plot(self, name_prefix):
        timestamp = int(time.time())
        filename = f"{name_prefix}_{timestamp}.png"
        save_path = os.path.join(self.output_dir, filename)
        plt.savefig(save_path, bbox_inches='tight', dpi=300)
        plt.close()
        return f"/uploads/results/{filename}"

    def run_pipeline(self, data_input, steps_config=None):
        report = {
            "status": "running",
            "steps_details": [],
            "final_plot": None,
            "qc_metrics": {},
            "diagnosis": "",
            "error": None
        }
        adata = None

        try:
            print(f"📂 Loading data from: {data_input}")
            
            # === 🛠️ 核心修复：更健壮的数据读取逻辑 ===
            if os.path.isdir(data_input):
                # 尝试读取 10x 目录
                try:
                    # 优先尝试标准读取 (会自动找 .gz)
                    adata = sc.read_10x_mtx(data_input, var_names='gene_symbols', cache=False)
                except FileNotFoundError:
                    print("⚠️ read_10x_mtx failed, trying manual mtx load...")
                    # 如果失败 (比如文件没压缩)，尝试手动读取
                    # 假设文件名是标准的 matrix.mtx, features.tsv, barcodes.tsv
                    mtx_path = os.path.join(data_input, "matrix.mtx")
                    if not os.path.exists(mtx_path): mtx_path = os.path.join(data_input, "matrix.mtx.gz")
                    
                    adata = sc.read_mtx(mtx_path).T  # 读入后转置 (Cells x Genes)
                    
                    # 读取 features (genes)
                    genes_path = os.path.join(data_input, "features.tsv")
                    if not os.path.exists(genes_path): genes_path = os.path.join(data_input, "genes.tsv")
                    genes = pd.read_csv(genes_path, header=None, sep='\t')
                    adata.var_names = genes[1].values # 假设第二列是基因名
                    adata.var['gene_ids'] = genes[0].values
                    
                    # 读取 barcodes
                    barcodes_path = os.path.join(data_input, "barcodes.tsv")
                    barcodes = pd.read_csv(barcodes_path, header=None, sep='\t')
                    adata.obs_names = barcodes[0].values
                
                adata.var_names_make_unique()
                
            elif data_input.endswith('.h5ad'):
                adata = sc.read_h5ad(data_input)
            else:
                adata = sc.read(data_input)
            # ===========================================
            
            report["qc_metrics"]["raw_cells"] = adata.n_obs
            report["qc_metrics"]["raw_genes"] = adata.n_vars
            
            if not steps_config: steps_config = []

            for step in steps_config:
                tool_id = step['tool_id']
                params = step.get('params', {})
                step_result = {"name": tool_id, "status": "success", "plot": None, "details": ""}

                print(f"▶️ Running step: {tool_id}")

                if tool_id == "local_qc":
                    adata.var['mt'] = adata.var_names.str.startswith(('MT-', 'mt-'))
                    sc.pp.calculate_qc_metrics(adata, qc_vars=['mt'], inplace=True)
                    sc.pl.violin(adata, ['n_genes_by_counts', 'total_counts', 'pct_counts_mt'], jitter=0.4, multi_panel=True, show=False)
                    step_result["plot"] = self._save_plot("qc_violin")
                    
                    min_genes = int(params.get('min_genes', 200))
                    max_mt = float(params.get('max_mt', 20))
                    sc.pp.filter_cells(adata, min_genes=min_genes)
                    adata = adata[adata.obs.pct_counts_mt < max_mt, :]
                    
                    report["qc_metrics"]["filtered_cells"] = adata.n_obs
                    step_result["summary"] = f"剩余 {adata.n_obs} 细胞"

                elif tool_id == "local_normalize":
                    sc.pp.normalize_total(adata, target_sum=1e4)
                    sc.pp.log1p(adata)
                    step_result["summary"] = "LogNormalize 完成"

                elif tool_id == "local_hvg":
                    sc.pp.highly_variable_genes(adata, n_top_genes=2000)
                    sc.pl.highly_variable_genes(adata, show=False)
                    step_result["plot"] = self._save_plot("hvg")
                    adata = adata[:, adata.var.highly_variable]
                    step_result["summary"] = "筛选 2000 高变基因"

                elif tool_id == "local_scale":
                    sc.pp.scale(adata, max_value=10)
                    step_result["summary"] = "数据缩放完成"

                elif tool_id == "local_pca":
                    sc.tl.pca(adata, svd_solver='arpack')
                    sc.pl.pca_variance_ratio(adata, log=True, show=False)
                    step_result["plot"] = self._save_plot("pca_variance")
                    step_result["summary"] = "PCA 降维完成"

                elif tool_id == "local_neighbors":
                    sc.pp.neighbors(adata, n_neighbors=10, n_pcs=40)
                    step_result["summary"] = "邻接图构建完成"

                elif tool_id == "local_cluster":
                    resolution = float(params.get('resolution', 0.5))
                    sc.tl.leiden(adata, resolution=resolution)
                    n_clusters = len(adata.obs['leiden'].unique())
                    step_result["summary"] = f"Leiden 聚类 (Res={resolution}): {n_clusters} 簇"

                elif tool_id == "local_umap":
                    sc.tl.umap(adata)
                    fig, ax = plt.subplots(figsize=(8, 6))
                    sc.pl.umap(adata, color=['leiden'], ax=ax, show=False, title="UMAP", legend_loc='on data', frameon=False)
                    umap_path = self._save_plot("final_umap")
                    step_result["plot"] = umap_path
                    report["final_plot"] = umap_path
                    step_result["summary"] = "UMAP 生成完毕"

                elif tool_id == "local_tsne":
                    if adata.n_obs < 5000: 
                        sc.tl.tsne(adata)
                        fig, ax = plt.subplots(figsize=(8, 6))
                        sc.pl.tsne(adata, color=['leiden'], ax=ax, show=False, title="t-SNE", frameon=False)
                        step_result["plot"] = self._save_plot("final_tsne")
                        step_result["summary"] = "t-SNE 生成完毕"
                    else:
                        step_result["summary"] = "细胞数过多，跳过 t-SNE"

                elif tool_id == "local_markers":
                    sc.tl.rank_genes_groups(adata, 'leiden', method='t-test')
                    result = adata.uns['rank_genes_groups']
                    groups = result['names'].dtype.names
                    markers_df = pd.DataFrame(
                        {group + '_' + key: result[key][group]
                        for group in groups for key in ['names', 'pvals']}
                    ).head(5)
                    step_result["details"] = markers_df.to_html(classes="table table-sm", index=False)
                    step_result["summary"] = "Marker 基因鉴定完成"

                report["steps_details"].append(step_result)

            report["diagnosis"] = f"""
            ### ✅ 分析完成 (10 Steps)
            - **原始细胞**: {report['qc_metrics'].get('raw_cells', 0)}
            - **过滤后**: {report['qc_metrics'].get('filtered_cells', 0)}
            - **聚类结果**: 成功识别出细胞亚群。
            - **可视化**: 已生成 UMAP 和 t-SNE (如适用) 图表。
            """
            
            report["status"] = "success"
            return report

        except Exception as e:
            print(f"❌ Pipeline Error: {e}")
            import traceback
            traceback.print_exc()
            report["status"] = "failed"
            report["error"] = str(e)
            return report
