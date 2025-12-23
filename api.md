
---

# GIBH-AGENT V1.0 前端集成接口文档

**版本**：1.0.0
**状态**：已发布
**最后更新**：2025-12-23

## 1. 概述
本服务提供单细胞生物信息学分析的智能代理能力。前端通过 RESTful API 与后端交互。
**核心变更**：V1.0 版本引入了 **混合响应机制 (Hybrid Response)**，同一接口根据业务逻辑可能返回 **流式文本 (Stream)** 或 **结构化 JSON**，前端需根据 `Content-Type` 进行动态处理。

### 1.1 基础环境
*   **Base URL**: `http://<Server-IP>:8088`
*   **通信协议**: HTTP/1.1
*   **数据格式**: JSON / Multipart / Text Stream
*   **字符编码**: UTF-8

### 1.2 静态资源映射
后端生成的图片资源（如 UMAP 图）通过 Nginx 直接映射，无需鉴权。
*   **路径规则**: `http://<Server-IP>:8088/uploads/results/<filename>`

---

## 2. 接口详情

### 2.1 文件上传
用于上传生信数据文件（.h5ad, .mtx 等）或图像文件。

*   **URL**: `/api/upload`
*   **Method**: `POST`
*   **Content-Type**: `multipart/form-data`

**请求参数**：

| 参数名 | 类型 | 必选 | 说明 |
| :--- | :--- | :--- | :--- |
| `file` | Binary | 是 | 文件二进制流 |

**响应示例 (JSON)**：
```json
{
  "status": "success",
  "file_id": "matrix.mtx",
  "file_name": "matrix.mtx"
}
```
> **注意**：前端需维护上传成功后的 `file_name`，在后续对话接口中作为上下文回传。

---

### 2.2 智能对话与任务分发 (核心)
该接口为系统的统一入口，支持普通对话、意图识别、工作流规划及任务提交。

*   **URL**: `/api/chat`
*   **Method**: `POST`
*   **Content-Type**: `application/json`

**请求参数**：

| 参数名 | 类型 | 必选 | 说明 |
| :--- | :--- | :--- | :--- |
| `message` | String | 否 | 用户输入的文本。若为空且有文件，将触发隐式意图识别。 |
| `history` | Array | 否 | 对话历史 `[{role: "user", content: "..."}, ...]` |
| `uploaded_files` | Array | 否 | 文件列表 `[{name: "matrix.mtx", ...}]` |
| `workflow_data` | Object | 否 | **仅在确认执行工作流时传递**。包含完整的步骤参数配置。 |

**响应处理规范 (混合响应)**：

前端需读取响应头 `Content-Type` 进行分支处理：

#### 情况 A：流式响应 (普通对话)
*   **Header**: `Content-Type: text/plain; charset=utf-8`
*   **处理方式**: 使用 `ReadableStream` 逐块读取并解码 (UTF-8)，实现打字机效果。

#### 情况 B：结构化响应 (工具/指令)
*   **Header**: `Content-Type: application/json`
*   **处理方式**: 解析 JSON，根据 `type` 字段渲染对应 UI 组件。

**JSON 响应类型定义**：

**1. 工作流配置 (type: "workflow_config")**
用于渲染参数配置表单。
```json
{
  "type": "workflow_config",
  "reply": "已为您规划流程，请确认参数...",
  "workflow_name": "Standard Scanpy Pipeline",
  "steps": [
    {
      "name": "Quality Control",
      "tool_id": "local_qc",
      "desc": "Filter cells",
      "params": [
        {"name": "min_genes", "label": "Min Genes", "value": "200", "type": "text"}
      ]
    }
    // ... 更多步骤
  ]
}
```

**2. 任务已启动 (type: "workflow_started")**
用于通知前端开始轮询。
```json
{
  "type": "workflow_started",
  "run_id": "f3b2c1...",  // 任务唯一ID，用于轮询
  "reply": "任务已启动，正在后台计算..."
}
```

---

### 2.3 任务状态轮询
用于获取异步生信分析任务的执行进度及最终结果。

*   **URL**: `/api/workflow/status/{run_id}`
*   **Method**: `GET`

**响应示例 (进行中)**：
```json
{
  "status": "running",
  "completed": false,
  "steps_status": [
    {"name": "local_qc", "status": "success", "summary": "完成"},
    {"name": "local_pca", "status": "running", "summary": "计算中..."}
  ]
}
```

**响应示例 (已完成)**：
```json
{
  "status": "success",
  "completed": true,
  "report_data": {
    "final_plot": "/uploads/results/final_umap_1734.png", // 结果图路径
    "qc_metrics": { "raw_cells": 5000, "filtered_cells": 4800 },
    "steps_details": [...] // 详细步骤日志
  }
}
```

---

## 3. 业务流程时序

### 3.1 工作流执行闭环
1.  **上传**: 用户上传文件 -> 调用 `/api/upload` -> 前端暂存 `file_name`。
2.  **规划**: 用户发送“规划流程” (带 `uploaded_files`) -> 调用 `/api/chat` -> 后端返回 `type: workflow_config` -> 前端渲染表单。
3.  **提交**: 用户点击执行 -> 调用 `/api/chat` (带 `workflow_data`) -> 后端返回 `type: workflow_started` (含 `run_id`)。
4.  **轮询**: 前端利用 `run_id` 循环调用 `/api/workflow/status/{run_id}`。
5.  **展示**: 当轮询状态为 `success` -> 前端读取 `report_data` -> 渲染图片和报告。

---

## 4. 前端参考实现 (SDK)

以下是封装好的请求类，已处理流式读取与 JSON 解析的兼容性。

```javascript
class BioAgentClient {
    constructor(baseUrl) {
        this.baseUrl = baseUrl;
    }

    async uploadFile(fileObj) {
        const formData = new FormData();
        formData.append('file', fileObj);
        const res = await fetch(`${this.baseUrl}/api/upload`, { method: 'POST', body: formData });
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
            return await res.json(); // 返回对象
        } else {
            return res.body; // 返回 ReadableStream
        }
    }

    async getStatus(runId) {
        const res = await fetch(`${this.baseUrl}/api/workflow/status/${runId}`);
        return await res.json();
    }
}
```

## 5. 错误码规范

*   **200 OK**: 请求成功（业务逻辑可能包含 `status: failed`）。
*   **500 Internal Server Error**: 后端服务异常（如 Python 代码报错）。
*   **413 Payload Too Large**: 上传文件超过 10GB 限制。
