
---

## 1. 核心流程图解

前端主要交互逻辑如下：
1. **上传文件** -> 拿到 `file_id`
2. **发送对话** (带上 `file_id`) -> 拿到 `reply` (文本) 或 `action` (建议执行的任务)
3. **确认执行** -> 用户点击“运行” -> 调用 `run_workflow`
4. **轮询状态** -> 每隔 2s 调用 `task_status` -> 更新进度条
5. **展示结果** -> 任务完成 -> 展示图片和报告

---

## 2. 接口详情

### 2.1 文件上传
用于上传 `.h5ad` 或 `.mtx` 格式的单细胞数据文件。

- **URL**: `/upload`
- **Method**: `POST`
- **Content-Type**: `multipart/form-data`

**请求参数 (Form Data):**

| 参数名 | 类型 | 必填 | 说明 |
| :--- | :--- | :--- | :--- |
| `file` | File | ✅ | 原始数据文件 (限制 500MB 以内) |

**返回示例 (Success):**
```json
{
  "code": 200,
  "message": "Upload success",
  "data": {
    "file_id": "f_123456789",  // ⚠️ 存好这个ID，后续对话都要用
    "filename": "pbmc3k.h5ad",
    "size_mb": 45.2
  }
}
```

---

### 2.2 智能对话 (Chat)
发送用户指令，模型会返回文本回复，或者**触发分析任务的建议**。

- **URL**: `/chat/completions`
- **Method**: `POST`

**请求参数 (Body):**

| 参数名 | 类型 | 必填 | 说明 |
| :--- | :--- | :--- | :--- |
| `query` | string | ✅ | 用户输入，例如："帮我分析这个数据" |
| `file_id` | string | ❌ | 当前上下文的文件ID (如果有) |
| `history` | array | ❌ | 历史对话记录 (用于多轮对话上下文) |

**请求示例:**
```json
{
  "query": "这个数据集包含哪些细胞类型？建议怎么分析？",
  "file_id": "f_123456789",
  "history": []
}
```

**返回示例 (场景 A: 普通问答):**
```json
{
  "code": 200,
  "data": {
    "type": "text",
    "content": "这是一个包含 2700 个细胞的 PBMC 数据集。建议先进行质量控制（QC），然后进行降维聚类。"
  }
}
```

**返回示例 (场景 B: 触发工作流建议):**
> ⚠️ **前端注意**：当 `type` 为 `workflow_suggestion` 时，不要直接把 content 显示出来，而是渲染成一个**“配置卡片”**，让用户点击“运行”。

```json
{
  "code": 200,
  "data": {
    "type": "workflow_suggestion",
    "content": "我已为您生成了标准分析流程配置，请确认参数。",
    "workflow_config": {
      "task_type": "standard_analysis",
      "params": {
        "min_genes": 200,
        "min_cells": 3,
        "n_top_genes": 2000,
        "resolution": 0.5
      }
    }
  }
}
```

---

### 2.3 执行工作流
用户在卡片上点击“运行”后调用此接口。

- **URL**: `/workflow/run`
- **Method**: `POST`

**请求参数 (Body):**

| 参数名 | 类型 | 必填 | 说明 |
| :--- | :--- | :--- | :--- |
| `file_id` | string | ✅ | 文件ID |
| `workflow_config` | object | ✅ | 上一步接口返回的 `workflow_config` 对象 |

**请求示例:**
```json
{
  "file_id": "f_123456789",
  "workflow_config": {
    "task_type": "standard_analysis",
    "params": { "min_genes": 200, "resolution": 0.5 }
  }
}
```

**返回示例:**
```json
{
  "code": 200,
  "message": "Workflow started",
  "data": {
    "task_id": "task_abc123" // ⚠️ 拿这个ID去轮询状态
  }
}
```

---

### 2.4 查询任务状态 (轮询)
建议每 2-3 秒调用一次。

- **URL**: `/workflow/status/{task_id}`
- **Method**: `GET`

**返回示例 (进行中):**
```json
{
  "code": 200,
  "data": {
    "status": "running",
    "progress": 45,  // 进度百分比 0-100
    "step": "Running PCA...", // 当前步骤描述
    "logs": ["Load data success", "QC passed", "Running PCA..."] // 实时日志数组
  }
}
```

**返回示例 (已完成):**
```json
{
  "code": 200,
  "data": {
    "status": "success",
    "progress": 100,
    "result": {
      "report_markdown": "## 分析报告\n本次分析共识别出...",
      "images": [
        "http://<IP>:8088/static/results/task_abc123/umap.png",
        "http://<IP>:8088/static/results/task_abc123/violin.png"
      ]
    }
  }
}
```

**返回示例 (失败):**
```json
{
  "code": 200,
  "data": {
    "status": "failed",
    "error": "MemoryError: System out of memory during clustering."
  }
}
```

---

## 3. 常见枚举值 (Enums)

### 任务状态 (`status`)
| 值 | 含义 | 前端动作 |
| :--- | :--- | :--- |
| `pending` | 排队中 | 显示“等待资源...” |
| `running` | 运行中 | 显示进度条和日志 |
| `success` | 成功 | 隐藏进度条，展示结果区域 |
| `failed` | 失败 | 红色高亮显示错误信息 |

---

## 4. 静态资源路径
如果返回的图片路径是相对路径（如 `/static/...`），请务必在前端拼接 Base URL。
- 图片基础路径: `http://<服务器IP>:8088`
```
