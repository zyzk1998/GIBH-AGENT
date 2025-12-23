#!/bin/bash

# ====================================================
# GIBH-AGENT 运维管理脚本 (DevOps Tool)
# ====================================================

# 定义颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 检查是否在项目根目录
if [ ! -f "docker-compose.yml" ]; then
    echo -e "${RED}❌ 错误：请在包含 docker-compose.yml 的项目根目录下运行此脚本！${NC}"
    exit 1
fi

# 打印头部
print_header() {
    clear
    echo -e "${BLUE}================================================${NC}"
    echo -e "${CYAN}   🧬 GIBH-AGENT 智能体管理控制台 (RTX 6000)   ${NC}"
    echo -e "${BLUE}================================================${NC}"
}

# 核心函数
start_all() {
    echo -e "${GREEN}🚀 正在构建并启动所有服务...${NC}"
    sudo docker compose up -d --build
    echo -e "${GREEN}✅ 所有服务已启动！${NC}"
}

stop_all() {
    echo -e "${YELLOW}🛑 正在停止所有服务...${NC}"
    sudo docker compose down
    echo -e "${GREEN}✅ 服务已停止。${NC}"
}

restart_backend() {
    echo -e "${YELLOW}🔄 正在重启业务层 (API + Worker + Nginx)...${NC}"
    echo -e "${CYAN}ℹ️  提示：vLLM (推理引擎) 不会重启，无需重新加载模型。${NC}"
    sudo docker compose restart api-server worker nginx
    echo -e "${GREEN}✅ 业务代码已更新并重启。${NC}"
}

restart_vllm() {
    echo -e "${RED}⚠️  警告：重启 vLLM 需要重新加载 16GB 模型，耗时较长。${NC}"
    read -p "确认重启? (y/n): " confirm
    if [[ $confirm == "y" ]]; then
        sudo docker compose restart inference-engine
        echo -e "${GREEN}✅ vLLM 已重启，请查看日志等待模型加载。${NC}"
        view_logs_vllm
    fi
}

view_logs_vllm() {
    echo -e "${CYAN}📜 正在打开 vLLM 推理引擎日志 (按 Ctrl+C 退出)...${NC}"
    sudo docker compose logs -f inference-engine
}

view_logs_api() {
    echo -e "${CYAN}📜 正在打开 API & Worker 联合日志 (按 Ctrl+C 退出)...${NC}"
    sudo docker compose logs -f api-server worker
}

check_status() {
    echo -e "${BLUE}📊 容器运行状态：${NC}"
    sudo docker compose ps
    echo ""
    echo -e "${BLUE}🎮 显卡状态 (nvidia-smi)：${NC}"
    nvidia-smi
    read -p "按回车键返回菜单..."
}

# 主循环
while true; do
    print_header
    echo -e "1. ${GREEN}🚀 一键启动 (Build & Up)${NC}  - 初次运行或修改配置后用"
    echo -e "2. ${YELLOW}🛑 停止所有服务 (Down)${NC}    - 彻底关闭"
    echo -e "3. ${CYAN}🔄 热重启后端代码${NC}         - 修改 Python/HTML 代码后用 (快!)"
    echo -e "4. ${RED}🔥 重启推理引擎 (vLLM)${NC}    - 显卡报错或模型卡死时用"
    echo -e "------------------------------------------------"
    echo -e "5. ${BLUE}📜 查看 vLLM 日志${NC}           - 看模型加载进度/显存报错"
    echo -e "6. ${BLUE}📜 查看 业务代码 日志${NC}       - 看 API 报错/任务执行情况"
    echo -e "7. ${BLUE}📊 查看系统状态${NC}             - Docker 状态 + 显卡负载"
    echo -e "------------------------------------------------"
    echo -e "0. 🚪 退出脚本"
    echo -e "================================================"
    read -p "请输入选项数字 [0-7]: " choice

    case $choice in
        1) start_all; read -p "按回车继续..." ;;
        2) stop_all; read -p "按回车继续..." ;;
        3) restart_backend; read -p "按回车继续..." ;;
        4) restart_vllm; read -p "按回车继续..." ;;
        5) view_logs_vllm ;;
        6) view_logs_api ;;
        7) check_status ;;
        0) echo "👋 Bye!"; exit 0 ;;
        *) echo -e "${RED}无效选项，请重试。${NC}"; sleep 1 ;;
    esac
done
