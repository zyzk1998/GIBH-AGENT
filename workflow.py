# 需要安装: pip install diagrams
from diagrams import Diagram, Cluster, Edge
from diagrams.onprem.compute import Server
from diagrams.onprem.network import Nginx
from diagrams.onprem.inmemory import Redis
from diagrams.onprem.queue import Celery
from diagrams.programming.framework import FastAPI
from diagrams.custom import Custom

# 甚至可以用自定义图片做图标 (比如 vLLM)
with Diagram("GIBH-AGENT Architecture", show=False, direction="TB"):
    user = Server("User")
    
    with Cluster("Docker Host"):
        ingress = Nginx("Gateway :8088")
        
        with Cluster("Application Layer"):
            api = FastAPI("API Server")
            worker = Celery("Async Worker")
            redis = Redis("Broker")
            
        with Cluster("Inference Layer"):
            # 这里可以用 Custom 加载 vLLM 的 logo，或者用通用图标
            vllm = Server("vLLM Engine")
            
    gpu = Server("RTX 6000 Blackwell")

    # 逻辑连线
    user >> Edge(label="HTTP") >> ingress
    ingress >> api
    api >> Edge(label="Task") >> redis >> worker
    api >> Edge(label="Chat") >> vllm
    worker >> Edge(label="Analysis") >> vllm
    vllm >> Edge(label="CUDA 12.8") >> gpu
