
---

### 第一部分：项目文档 (README.md)

您可以将此内容保存为项目根目录下的 `README.md`。

```markdown
# GIBH-AGENT (Commercial Edition)
**基于多模态大模型与微服务架构的单细胞生信分析智能体平台**

## 📖 项目简介
GIBH-AGENT 是一个企业级生物信息学分析平台，旨在通过自然语言交互（Chat）实现自动化的单细胞数据分析（scRNA-seq）。
系统采用 **微服务架构**，集成了 **Qwen3-VL** 多模态大模型作为大脑，**Scanpy** 作为计算引擎，支持从数据上传、QC、聚类到可视化报告生成的全流程自动化。

## 🏗️ 技术架构
*   **前端/网关**: Nginx (反向代理, 静态托管, 负载均衡)
*   **API 服务**: FastAPI + Gunicorn (高并发异步接口)
*   **任务调度**: Celery + Redis (分布式异步任务队列，解决长耗时分析不阻塞)
*   **推理引擎**: vLLM (部署 Qwen3-VL-8B/32B，OpenAI 兼容接口)
*   **数据存储**: 本地文件系统 (热数据) + ChromaDB (向量知识库)

## 🚀 核心功能
1.  **多模态对话**: 支持图文多模态交互，可识别生信图表并生成解读。
2.  **自动化工作流**: 内置标准单细胞分析流程 (QC -> Normalize -> PCA -> UMAP)。
3.  **本地化部署**: 模型权重、向量库、数据文件全部本地化，数据不出域。
4.  **出版级绘图**: 自动生成高分辨率 (300 DPI) 的分析图表。

## 📂 目录结构
```text
.
├── docker-compose.yml       # 容器编排文件
├── services/
│   ├── api/                 # 后端核心代码 (FastAPI + Celery)
│   │   ├── src/skills/      # 🔌 插件目录 (Scanpy 逻辑在此)
│   │   └── Dockerfile
│   ├── nginx/               # 网关配置
│   └── worker/              # 异步计算节点
└── data/
    ├── models/              # 本地模型权重 (Qwen3-VL)
    ├── uploads/             # 用户上传数据
    └── redis/               # 消息队列持久化
```

## ⚡ 快速开始

### 1. 环境要求
*   Linux 服务器 (推荐 Ubuntu 20.04+)
*   NVIDIA GPU (显存 >= 24GB) + CUDA Drivers
*   Docker & Docker Compose

### 2. 启动服务
```bash
# 1. 确保模型已下载到 ./data/models/Qwen3-VL-8B-Instruct
# 2. 启动所有容器
docker compose up -d --build
```

### 3. 访问系统
*   **Web 界面**: `http://<服务器IP>:8088`
*   **API 文档**: `http://<服务器IP>:8088/api/docs`

## 🛠️ 维护指南
*   **查看日志**: `docker compose logs -f`
*   **重启后端**: `docker compose restart api-server worker`
*   **停止服务**: `docker compose down`
```

---

### 第二部分：如何启动和使用

#### 步骤 1：检查目录结构与模型

请确保您的目录结构如下（特别是模型路径）：

```bash
cd ~/GIBH-AGENT
tree -L 4
```

**必须确认**：
1.  `docker-compose.yml` 在当前目录下。
2.  模型文件在 `data/models/Qwen3-VL-8B-Instruct` 下（包含 `.safetensors` 文件）。
3.  代码文件在 `services/api/src/` 下。

#### 步骤 2：一键启动

在 `~/GIBH-AGENT` 目录下执行：

```bash
# 构建镜像并后台启动
docker compose up -d --build
```

#### 步骤 3：验证启动状态

启动需要几分钟（主要是 vLLM 加载模型比较慢）。请使用以下命令查看日志：

```bash
# 查看 vLLM 是否加载完成
docker compose logs -f inference-engine
```

*   **等待看到**: `Uvicorn running on http://0.0.0.0:8000`
*   **然后按 `Ctrl+C` 退出日志**。

接着检查 API 服务是否正常：
```bash
docker compose logs -f api-server
```
*   **等待看到**: `Application startup complete.`

#### 步骤 4：如何使用 (用户视角)

假设您的服务器 IP 是 `192.168.8.111`（请替换为实际 IP）。

1.  **打开浏览器** (Chrome/Edge)。
2.  **访问地址**: `http://192.168.8.111:8088`
    *   *注意是 8088 端口，不是 80，也不是 8000。*
3.  **开始交互**:
    *   **上传数据**: 点击上传按钮，上传一个 `.h5ad` 或 `.mtx` 格式的单细胞数据文件。
    *   **对话**: 输入 "帮我分析一下这个数据" 或 "Run standard workflow"。
    *   **智能体反应**:
        1.  智能体会识别意图，返回 "Workflow Config" 卡片。
        2.  您确认参数后，点击 "Run"。
        3.  系统会显示 "工作流已启动"，并开始轮询进度。
        4.  几分钟后，您会看到生成的 UMAP 图和 QC 报告。

---

### 常见问题排查

*   **Q: 网页打不开？**
    *   A: 检查服务器防火墙是否放行了 `8088` 端口。
*   **Q: 任务一直显示 Running 不动？**
    *   A: 查看 Worker 日志：`docker compose logs -f worker`。可能是 Scanpy 分析内存不足或报错。
*   **Q: 显存爆了 (OOM)？**
    *   A: 修改 `docker-compose.yml` 中 vLLM 的 `--gpu-memory-utilization 0.9`，改为 `0.8` 或 `0.7`。
