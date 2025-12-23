import os

# ================= 配置区域 =================
# 输出文件名
OUTPUT_FILE = "project_context.txt"

# 需要忽略的目录 (关键：忽略 data 防止读取模型和数据库)
IGNORE_DIRS = {
    "data", "__pycache__", ".git", ".idea", ".vscode", 
    "redis", "postgres", "qdrant", "logs", "uploads"
}

# 需要忽略的文件
IGNORE_FILES = {
    OUTPUT_FILE, "export_code.py", ".DS_Store", 
    "dump.rdb", "gibh_agent_code.tar.gz"
}

# 只读取这些后缀的文件 (白名单模式，防止读取二进制)
ALLOWED_EXTENSIONS = {
    ".py", ".yml", ".yaml", ".conf", ".html", ".css", ".js", 
    ".md", ".txt", ".sh", "Dockerfile", "requirements.txt"
}
# ===========================================

def is_allowed_file(filename):
    # 特殊文件名直接允许
    if filename in ALLOWED_EXTENSIONS:
        return True
    # 检查后缀
    return any(filename.endswith(ext) for ext in ALLOWED_EXTENSIONS)

def export_project():
    root_dir = os.getcwd()
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as out_f:
        # 写入目录结构树
        out_f.write("=== PROJECT STRUCTURE ===\n")
        for root, dirs, files in os.walk(root_dir):
            # 过滤目录
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
            
            level = root.replace(root_dir, '').count(os.sep)
            indent = ' ' * 4 * (level)
            out_f.write(f"{indent}{os.path.basename(root)}/\n")
            subindent = ' ' * 4 * (level + 1)
            for f in files:
                if is_allowed_file(f) and f not in IGNORE_FILES:
                    out_f.write(f"{subindent}{f}\n")
        
        out_f.write("\n\n")

        # 写入文件内容
        for root, dirs, files in os.walk(root_dir):
            # 过滤目录
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
            
            for file in files:
                if file in IGNORE_FILES:
                    continue
                    
                if is_allowed_file(file):
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, root_dir)
                    
                    try:
                        with open(file_path, "r", encoding="utf-8") as in_f:
                            content = in_f.read()
                            out_f.write(f"--- START OF FILE: {rel_path} ---\n")
                            out_f.write(content)
                            out_f.write(f"\n--- END OF FILE: {rel_path} ---\n\n")
                            print(f"✅ Added: {rel_path}")
                    except Exception as e:
                        print(f"⚠️ Skipped {rel_path}: {e}")

    print(f"\n🎉 完成！所有代码已聚合到: {OUTPUT_FILE}")

if __name__ == "__main__":
    export_project()
