
---

# 🧬 GIBH Qwen Agent 前端集成接口文档 (V1.1)

**版本**: 1.1.0 (基于 V1.0 增量修订)
**修订内容**: 补全 `workflow_data` 结构定义、任务失败响应格式、轮询策略建议及流式协议细节。

## 1. 概述
本服务提供单细胞生物信息学分析的智能代理能力。前端通过 RESTful API 与后端交互。

### 1.1 核心机制：混合响应 (Hybrid Response)
同一接口 (`/api/chat`) 根据业务逻辑自动切换响应格式：
1.  **流式文本 (Stream)**: 用于普通对话，响应头 `Content-Type: text/plain`。
2.  **结构化数据 (JSON)**: 用于工具调用/任务启动，响应头 `Content-Type: application/json`。

### 1.2 基础环境
*   **Base URL**: `http://<Server-IP>:8088`
*   **跨域支持**: 服务端已开启 CORS `*`，无需 Nginx 额外配置。
*   **静态资源**: 图片资源无需鉴权，直接访问 `http://<Server-IP>:8088/uploads/results/<filename>`。

---

## 2. 接口详情

### 2.1 文件上传
用于上传生信数据文件。

*   **URL**: `/api/upload`
*   **Method**: `POST`
*   **Content-Type**: `multipart/form-data`

**请求参数**：

| 参数名 | 类型 | 必选 | 说明 |
| :--- | :--- | :--- | :--- |
| `file` | Binary | 是 | 文件二进制流。**单文件最大 10GB**。 |

**建议支持的文件扩展名 (accept)**：
`.h5ad`, `.mtx`, `.tsv`, `.csv`, `.txt`, `.png`, `.jpg`

**响应示例 (JSON)**：
```json
{
  "status": "success",
  "file_id": "matrix.mtx",   // 内部存储ID
  "file_name": "matrix.mtx"  // 原始文件名 (需在 chat 接口回传)
}
```

---

### 2.2 智能对话与任务提交 (核心)
该接口为系统的统一入口。

*   **URL**: `/api/chat`
*   **Method**: `POST`
*   **Content-Type**: `application/json`

**请求参数**：

| 参数名 | 类型 | 必选 | 说明 |
| :--- | :--- | :--- | :--- |
| `message` | String | 否 | 用户文本。若为空且有文件，触发隐式意图。 |
| `history` | Array | 否 | 上下文 `[{role: "user", content: "..."}, ...]` |
| `uploaded_files` | Array | 否 | 文件列表 `[{name: "matrix.mtx", ...}]` |
| `workflow_data` | Object | **否** | **仅在“确认执行”时必填**。定义工作流的具体参数。 |

#### 🔍 补充：`workflow_data` 数据结构定义
当用户在前端修改完参数点击“执行”时，需构造如下 JSON 结构发送给后端：

```json
{
  "workflow_data": {
    "steps": [
      {
        "name": "Quality Control",
        "tool_id": "local_qc",  // 必须与配置卡片中的 tool_id 一致
        "params": {
          "min_genes": "200",   // 用户修改后的值
          "max_mt": "20"
        }
      },
      {
        "name": "Clustering",
        "tool_id": "local_cluster",
        "params": {
          "resolution": "0.5"
        }
      }
      // ... 需包含所有步骤，即使 params 为空
    ]
  },
  "uploaded_files": [...] // 必须带上文件信息
}
```

#### 📡 响应处理规范

**情况 A：流式响应 (普通对话)**
*   **格式**: Raw Text Chunks (纯文本分块)，非 SSE。
*   **结束标志**: HTTP 连接关闭。
*   **前端处理**: 使用 `ReadableStream` + `TextDecoder` 循环读取。

**情况 B：结构化响应 (JSON)**
*   **类型 1: 工作流配置 (type: "workflow_config")**
    *   用于渲染表单。`params` 数组中包含字段定义：
    ```json
    "params": [
      { "name": "min_genes", "label": "Min Genes", "value": "200", "type": "text" }
      // type 可能为: "text", "select", "boolean" (预留)
    ]
    ```
*   **类型 2: 任务已启动 (type: "workflow_started")**
    *   包含 `run_id`，用于启动轮询。

---

### 2.3 任务状态轮询
用于获取异步任务进度。

*   **URL**: `/api/workflow/status/{run_id}`
*   **Method**: `GET`
*   **轮询策略**: 建议间隔 **2s - 3s**。

#### 响应示例 1：执行中 (Running)
```json
{
  "status": "running",
  "completed": false,
  "steps_status": [
    {"name": "local_qc", "status": "success", "summary": "剩余 2500 细胞"},
    {"name": "local_pca", "status": "running", "summary": "计算中..."}
  ]
}
```

#### 响应示例 2：执行成功 (Success)
```json
{
  "status": "success",
  "completed": true,
  "report_data": {
    "final_plot": "/uploads/results/final_umap_123.png", // 结果图相对路径
    "qc_metrics": { "raw_cells": 5000, "filtered_cells": 4800 },
    "steps_details": [...] // 完整日志
  }
}
```

#### 响应示例 3：执行失败 (Failed) ⚠️
若 Worker 发生异常（如内存溢出、文件缺失），将返回如下结构：
```json
{
  "status": "failed",
  "completed": true,
  "error": "❌ 错误：服务器磁盘上找不到文件 matrix.mtx。请重新上传。",
  "steps_status": [...] // 可能包含部分已完成步骤的状态
}
```
> **前端动作**：当 `status === 'failed'` 时，应停止轮询，并用红色 Alert 组件展示 `error` 字段的内容。

---

## 3. 前端 SDK 参考实现

```javascript
class BioAgentClient {
    constructor(baseUrl) {
        this.baseUrl = baseUrl;
    }

    async uploadFile(fileObj) {
        const formData = new FormData();
        formData.append('file', fileObj);
        const res = await fetch(`${this.baseUrl}/api/upload`, { method: 'POST', body: formData });
        if (!res.ok) throw new Error("Upload failed");
        return await res.json();
    }

    async chat(payload) {
        const res = await fetch(`${this.baseUrl}/api/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const contentType = res.headers.get("content-type");
        if (contentType && contentType.includes("application/json")) {
            return await res.json(); // JSON 对象
        } else {
            return res.body; // ReadableStream
        }
    }

    async getStatus(runId) {
        const res = await fetch(`${this.baseUrl}/api/workflow/status/${runId}`);
        return await res.json();
    }
}
```

## 4. 常见问题 (FAQ)

1.  **Q: 为什么流式输出有时候会卡顿？**
    *   A: 后端已优化 Nginx 缓冲配置。如果仍有卡顿，请检查前端 `TextDecoder` 的解码逻辑是否使用了 `stream: true` 选项。

2.  **Q: `workflow_data` 里的 `params` 必须传吗？**
    *   A: 是的。即使用户没有修改默认值，也需要将表单里的当前值回传给后端，否则 Worker 会因缺少参数而报错。

3.  **Q: 图片加载 404？**
    *   A: 请直接将后端返回的 `final_plot` 路径拼接到 Base URL 后。例如：`http://192.168.x.x:8088/uploads/results/xxx.png`。
