import asyncio
import httpx
import time
import json
import random
import string
import pandas as pd
import numpy as np
from colorama import Fore, Style, init
from datetime import datetime

# 初始化颜色
init(autoreset=True)

# ================= ⚙️ 压测配置区域 (根据需求调整) =================
# 1. 目标地址
AGENT_URL = "http://localhost:8088/api/chat"
JUDGE_URL = "http://localhost:8000/v1/chat/completions"
JUDGE_MODEL = "qwen3-vl"

# 2. 压力参数
TEST_DURATION_SEC = 120   # ⏱️ 测试持续时间 (秒)，建议设为 300 (5分钟)
CONCURRENCY = 30          # 🚀 并发数 (RTX 6000 建议 30-50，太高会增加延迟)
SAMPLE_RATE = 0.1         # 🔍 评分抽样率 (10% 的回答会被 AI Doctor 检查)

# 3. 题库 (基础题 + 随机噪声 = 无限题库)
BASE_QUESTIONS = [
    "解释单细胞测序中 Batch Effect 的原理及去除方法。",
    "如何使用 Scanpy 进行细胞聚类？请给出代码示例。",
    "TP53 基因在肿瘤发生中的作用是什么？",
    "什么是 UMAP？它和 t-SNE 有什么区别？",
    "线粒体基因含量过高说明了什么问题？",
    "请解释 Seurat 流程中的 Normalization 步骤。",
    "什么是高变基因 (HVG)？为什么要筛选它们？",
    "细胞周期评分 (Cell Cycle Scoring) 是如何计算的？",
    "如何通过标记基因 (Marker Genes) 注释细胞类型？",
    "简述 scRNA-seq 数据分析的标准流程。"
]
# ===============================================================

class StressStats:
    def __init__(self):
        self.total_requests = 0
        self.success_count = 0
        self.error_count = 0
        self.latencies = []     # 总耗时
        self.ttfts = []         # 首字延迟
        self.scores = []        # 质量评分
        self.start_time = 0
        self.is_running = True

stats = StressStats()

def generate_random_question():
    """生成带随机噪声的问题，防止缓存作弊"""
    base_q = random.choice(BASE_QUESTIONS)
    # 添加随机后缀，强制 LLM 重新计算 Attention
    salt = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
    return f"{base_q} (Ref: {salt})"

async def ai_doctor_grade(client, question, answer):
    """AI 医生抽检评分"""
    prompt = f"""
    你是一位生信专家。请对以下回答打分（0-10分）。
    问题: {question}
    回答: {answer}
    
    只返回一个 JSON: {{"score": 8.5, "reason": "..."}}
    """
    try:
        resp = await client.post(JUDGE_URL, json={
            "model": JUDGE_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 256
        }, timeout=30)
        res_json = json.loads(resp.json()['choices'][0]['message']['content'].replace("```json", "").replace("```", ""))
        return res_json.get('score', 0)
    except:
        return 0

async def worker(client, sem):
    """模拟一个不断提问的用户"""
    while stats.is_running:
        async with sem:
            question = generate_random_question()
            start = time.perf_counter()
            ttft = 0
            first_chunk = False
            full_response = ""
            
            try:
                # 发起流式请求
                async with client.stream("POST", AGENT_URL, json={"message": question, "history": []}, timeout=60) as response:
                    if response.status_code != 200:
                        stats.error_count += 1
                        print(f"{Fore.RED}x", end="", flush=True)
                        continue

                    async for chunk in response.aiter_text():
                        if not first_chunk:
                            ttft = (time.perf_counter() - start) * 1000
                            first_chunk = True
                        if chunk:
                            full_response += chunk
                
                # 请求完成
                total_time = (time.perf_counter() - start) * 1000
                stats.success_count += 1
                stats.latencies.append(total_time)
                stats.ttfts.append(ttft)
                
                # 🎲 随机抽检评分
                if random.random() < SAMPLE_RATE:
                    score = await ai_doctor_grade(client, question, full_response)
                    if score > 0:
                        stats.scores.append(score)
                        print(f"{Fore.MAGENTA}★", end="", flush=True) # 评分标记
                    else:
                        print(f"{Fore.GREEN}.", end="", flush=True)
                else:
                    print(f"{Fore.GREEN}.", end="", flush=True) # 成功标记

            except Exception as e:
                stats.error_count += 1
                print(f"{Fore.RED}!", end="", flush=True)

async def monitor(duration):
    """监控倒计时"""
    start = time.time()
    while time.time() - start < duration:
        await asyncio.sleep(1)
        elapsed = time.time() - start
        rps = stats.success_count / elapsed if elapsed > 0 else 0
        print(f"\r[{elapsed:.0f}s/{duration}s] RPS: {rps:.2f} | Err: {stats.error_count} | Avg Latency: {np.mean(stats.latencies) if stats.latencies else 0:.0f}ms", end="")
    
    stats.is_running = False

async def run_stress_test():
    print(f"{Fore.CYAN}🚀 GIBH-AGENT 持续压力测试 (Sustained Pressure Test)")
    print(f"硬件环境: RTX 6000 | 并发数: {CONCURRENCY} | 持续时间: {TEST_DURATION_SEC}s")
    print(f"策略: 随机噪声绕过缓存 + AI Doctor 抽检 ({int(SAMPLE_RATE*100)}%)")
    print("-" * 60)
    print("图例: .成功  x失败  !异常  ★抽检评分")
    print("-" * 60)

    stats.start_time = time.perf_counter()
    
    # 限制连接池
    limits = httpx.Limits(max_keepalive_connections=CONCURRENCY, max_connections=CONCURRENCY)
    async with httpx.AsyncClient(limits=limits, timeout=120.0) as client:
        sem = asyncio.Semaphore(CONCURRENCY)
        
        # 启动监控协程
        monitor_task = asyncio.create_task(monitor(TEST_DURATION_SEC))
        
        # 启动并发 Worker
        workers = [asyncio.create_task(worker(client, sem)) for _ in range(CONCURRENCY)]
        
        # 等待时间结束
        await monitor_task
        
        # 等待所有 Worker 收尾
        print(f"\n{Fore.YELLOW}⏳ 时间到，正在等待剩余请求完成...")
        await asyncio.gather(*workers, return_exceptions=True)

    print_report()

def print_report():
    total_time = time.perf_counter() - stats.start_time
    
    print("\n\n" + "=" * 60)
    print(f"{Fore.CYAN}📊 压力测试最终报告 (Pressure Report)")
    print("=" * 60)
    print(f"⏱️  实测时长:      {total_time:.2f} s")
    print(f"📦 总请求数:      {stats.success_count + stats.error_count}")
    print(f"✅ 成功请求:      {Fore.GREEN}{stats.success_count}")
    print(f"❌ 失败请求:      {Fore.RED}{stats.error_count}")
    print(f"🚀 平均 RPS:      {Fore.YELLOW}{stats.success_count / total_time:.2f} req/s")
    
    if stats.latencies:
        print("-" * 60)
        print(f"⚡ 首字延迟 (TTFT):")
        print(f"   Avg: {np.mean(stats.ttfts):.2f} ms")
        print(f"   P99: {np.percentile(stats.ttfts, 99):.2f} ms (99%的用户在此时间内看到第一个字)")
        
        print(f"🐢 完整响应耗时:")
        print(f"   Avg: {np.mean(stats.latencies):.2f} ms")
        print(f"   P99: {np.percentile(stats.latencies, 99):.2f} ms")
    
    if stats.scores:
        print("-" * 60)
        print(f"👨‍⚕️ AI Doctor 质量抽检 ({len(stats.scores)} samples):")
        avg_score = np.mean(stats.scores)
        score_color = Fore.GREEN if avg_score > 8 else Fore.YELLOW
        print(f"   平均分: {score_color}{avg_score:.2f} / 10")
        print(f"   最低分: {min(stats.scores)}")
    
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(run_stress_test())
