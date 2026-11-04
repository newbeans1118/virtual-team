# 模版：.gitignore ｜ 架构师搭建工程骨架时（discipline §13：`git init` + 初始 commit）
# 复制本文件内容到项目根 `.gitignore`，按项目技术栈增删。

```gitignore
# 构建与临时产物（charter §3：build/、tmp/ 禁止污染交付目录与主干）
build/
tmp/
dist/
out/

# 依赖与虚拟环境
node_modules/
__pycache__/
.venv/
venv/
vendor/

# 环境与密钥（discipline §14：verify 禁止依赖本地密钥，密钥不入主干）
.env
.env.*
*.local
*.pem
*.key

# 运行日志与本地数据
*.log
.DS_Store
Thumbs.db
```
