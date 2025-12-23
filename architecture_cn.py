from diagrams import Diagram, Cluster, Edge
from diagrams.programming.framework import FastAPI
from diagrams.onprem.network import Nginx
from diagrams.onprem.inmemory import Redis
from diagrams.onprem.queue import Celery
from diagrams.onprem.compute import Server
from diagrams.onprem.client import User
# ✅ 修复点：使用通用存储图标
from diagrams.generic.storage import Storage

# ================= 全局配置 =================
# 设置中文字体 (WenQuanYi Zen Hei)
graph_attr = {
    "fontsize": "16",
    "fontname": "WenQuanYi Zen Hei",
    "bgcolor": "white",
    "splines": "ortho", 
    "nodesep": "0.6",
    "ranksep": "0.8",
    "pad": "0.5"
}

node_attr = {
    "fontname": "WenQuanYi Zen Hei",
    "fontsize": "14"
}

edge_attr = {
    "fontname": "WenQuanYi Zen Hei",
    "fontsize": "12"
}

with Diagram("GIBH-AGENT 系统架构图 (V1.0)", show=False, direction="TB", 
             graph_attr=graph_attr, node_attr=node_attr, edge_attr=edge_attr):
    
    user = User("用户终端\n(Web/Browser)")

    # === 宿主机容器环境 ===
    with Cluster("Docker 容器化环境 (Ubuntu Host)"):
        
        # 1. 接入层
        with Cluster("接入层 (Ingress)"):
            gateway = Nginx("流量网关\n(Nginx :8088)")
        
        # 2. 业务应用层
        with Cluster("业务应用层 (Application)"):
            api = FastAPI("主控服务\n(API Server)")
            
            with Cluster("异步任务调度"):
                queue = Redis("消息队列\n(Redis Broker)")
                worker = Celery("生信分析引擎\n(Async Worker)")
        
        # 3. 智能推理层
        with Cluster("AI 推理层 (Intelligence)"):
            vllm = Server("大模型服务\n(vLLM Engine)")
            
        # 4. 数据存储层
        with Cluster("数据持久化 (Persistence)"):
            models = Storage("本地模型权重\n(Qwen3-VL)")
            uploads = Storage("用户数据/结果\n(Shared Volume)")

    # === 硬件底座 ===
    gpu = Server("算力底座")

    # ================= 连线逻辑 (带中文说明) =================

    # 1. 访问链路
    user >> Edge(label="HTTP请求") >> gateway
    gateway >> Edge(label="反向代理") >> api
    gateway >> Edge(style="dotted", label="静态资源映射") >> uploads

    # 2. 业务链路
    api >> Edge(label="1. 实时对话") >> vllm
    api >> Edge(label="2. 提交任务") >> queue >> Edge(label="消费") >> worker
    
    # 3. 分析链路
    worker >> Edge(label="视觉理解") >> vllm
    worker >> Edge(label="读写数据") >> uploads

    # 4. 硬件支撑
    vllm >> Edge(label="加载权重", style="dashed") >> models
    vllm >> Edge(label="CUDA 加速", color="firebrick", penwidth="2.0") >> gpu
