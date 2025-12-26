
# GIBH-AGENT (Commercial Edition)

<div align="center">

![GIBH-AGENT Logo](https://via.placeholder.com/150x150.png?text=GIBH-AGENT)

**基于多模态大模型与微服务架构的单细胞生信分析智能体平台**

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![Vue.js](https://img.shields.io/badge/Frontend-Vue.js-4FC08D?logo=vue.js)](https://vuejs.org/)
[![Docker](https://img.shields.io/badge/Deploy-Docker-2496ED?logo=docker)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-Proprietary-red)](LICENSE)

[功能特性](#-功能特性) • [技术架构](#-技术架构) • [快速开始](#-快速开始) • [API文档](#-api-文档) • [联系我们](#-联系我们)

</div>

---

## 📖 项目简介

**GIBH-AGENT** 是一款企业级生物信息学分析平台，旨在通过自然语言交互（Chat）实现单细胞测序数据（scRNA-seq）的全流程自动化分析。

系统摒弃了传统的参数配置界面，采用 **Qwen3-VL** 多模态大模型作为核心大脑，结合 **Scanpy** 强大的计算引擎，让科研人员可以通过对话完成从数据质控（QC）、降维聚类到细胞注释的复杂分析任务。

### ✨ 核心亮点

- **🤖 多模态交互**：支持图文对话，不仅能听懂“帮我分析这个数据”，还能识别并解读生信图表。
- **⚡ 自动化工作流**：内置标准单细胞分析 Pipeline (QC -> Normalize -> PCA -> Neighbors -> UMAP -> Clustering)。
- **🔒 数据隐私安全**：全本地化部署（Local LLM + Local VectorDB），数据不出域，保障科研数据安全。
- **📊 出版级绘图**：自动生成符合 SCI 发表标准的矢量图表（300 DPI+）。

---

## 🏗 技术架构

系统采用前后端分离的微服务架构，各组件通过 Docker Compose 编排：

| 组件 | 技术选型 | 说明 |
| :--- | :--- | :--- |
| **网关层** | Nginx | 反向代理、静态资源托管、负载均衡 |
| **应用层** | FastAPI + Gunicorn | 高并发异步 API 服务，处理业务逻辑 |
| **计算层** | Celery + Redis | 分布式任务队列，处理耗时的生信分析任务 |
| **推理层** | vLLM | 大模型推理加速引擎，部署 Qwen3-VL-8B/32B |
| **存储层** | ChromaDB + FS | 向量知识库（RAG）与本地文件存储 |

> 架构图文件位于：`architecture` (请参考仓库根目录)

---

## ⚡ 快速开始

### 1. 环境准备

- **操作系统**: Linux (Ubuntu 20.04+ 推荐)
- **硬件资源**: 
  - CPU: 16 cores+
  - RAM: 64GB+ (生信分析内存消耗大)
  - GPU: NVIDIA RTX 3090/4090 或 A100 (显存 ≥ 24GB)
- **软件依赖**: Docker, Docker Compose, NVIDIA Container Toolkit

### 2. 部署步骤

```bash
# 1. 克隆仓库
git clone https://github.com/zyzk1998/GIBH-AGENT.git
cd GIBH-AGENT

# 2. 模型准备
# 请确保 Qwen3-VL 模型权重已下载至 data/models 目录
# 目录结构应为: ./data/models/Qwen3-VL-8B-Instruct/model.safetensors ...

# 3. 启动服务
# 首次启动会自动构建镜像，耗时较长请耐心等待
docker compose up -d --build

# 4. 验证状态
docker compose logs -f api-server
# 等待出现 "Application startup complete" 字样
```

### 3. 访问服务

- **Web 界面**: `http://localhost:8088`
- **API 文档**: `http://localhost:8088/api/docs` (Swagger UI)
- **任务监控**: `http://localhost:8088/flower` (如已开启)

---

## 📂 目录结构

```text
GIBH-AGENT/
├── docker-compose.yml      # 容器编排配置
├── services/
│   ├── api/                # 后端核心服务 (FastAPI)
│   │   ├── src/
│   │   │   ├── skills/     # 🧬 生信分析工具集 (Scanpy封装)
│   │   │   ├── routers/    # API 路由定义
│   │   │   └── main.py     # 入口文件
│   │   └── Dockerfile
│   ├── worker/             # 异步计算节点 (Celery)
│   └── nginx/              # 前端网关配置
├── data/
│   ├── models/             # LLM 模型权重
│   ├── uploads/            # 用户上传的原始数据
│   └── results/            # 分析结果产出
└── README.md
```

---

## 🛠 维护与排查

- **服务重启**: `docker compose restart api-server worker`
- **查看推理日志**: `docker compose logs -f inference-engine` (查看 vLLM 加载进度)
- **清理缓存**: `docker compose down -v` (注意：会清空 Redis 队列数据)

---

## 📄 版权说明

Copyright © 2025 GIBH-AGENT Team. All Rights Reserved.
本项目为商业版代码，未经授权禁止商用分发。
```

---

