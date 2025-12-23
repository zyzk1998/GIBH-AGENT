import os
import importlib.util
import glob
import sys

class SkillManager:
    def __init__(self, skills_dir="skills"):
        # 🛡️ 健壮的路径查找逻辑
        # 1. 尝试相对于当前文件的路径
        base_dir = os.path.dirname(os.path.abspath(__file__))
        target_dir = os.path.join(base_dir, skills_dir)
        
        # 2. 如果找不到，尝试相对于工作目录 (Docker 容器内通常是 /app/src/skills)
        if not os.path.exists(target_dir):
            target_dir = os.path.join(os.getcwd(), "src", skills_dir)
        
        # 3. 再次兜底
        if not os.path.exists(target_dir):
             target_dir = "/app/src/skills"

        self.skills_dir = target_dir
        self.skills = {}
        print(f"🔍 SkillManager initialized. Scanning dir: {self.skills_dir}")
        self._load_skills()

    def _load_skills(self):
        """动态加载 skills 目录下的所有 .py 插件"""
        if not os.path.exists(self.skills_dir):
            print(f"⚠️ Skills dir not found: {self.skills_dir}")
            return

        # 将 skills 目录加入 sys.path，防止 import 报错
        if self.skills_dir not in sys.path:
            sys.path.append(self.skills_dir)

        for file_path in glob.glob(os.path.join(self.skills_dir, "*.py")):
            module_name = os.path.basename(file_path)[:-3]
            if module_name == "__init__":
                continue
            
            try:
                spec = importlib.util.spec_from_file_location(module_name, file_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                if hasattr(module, "META"):
                    self.skills[module.META['id']] = module
                    print(f"✅ Loaded Skill: {module.META['name']} ({module.META['id']})")
            except Exception as e:
                print(f"❌ Failed to load skill {module_name}: {e}")

    def get_skill(self, skill_id):
        return self.skills.get(skill_id)

    def match_skill(self, query):
        # 简单的关键词匹配
        for skill in self.skills.values():
            if skill.META['id'] in query or skill.META['name'] in query:
                return skill
        return None
