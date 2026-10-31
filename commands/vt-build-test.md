---
description: 测试版构建（测试准入）：worktree 从主干构建、打包、产出安装手册、部署冒烟，生成测试环境来源
argument-hint: "构建轮次说明，例如：首轮测试版 或 缺陷修复后重建（列 BUG 编号）"
---

<user_input>
$ARGUMENTS
</user_input>

---

委派 **release-engineer** 执行**测试版构建**（`releasing` 技能阶段一）。

## 前置（缺一 → BLOCKED 报 PM）

- 全部开发任务的代码评审已闭环（无未关闭 P0/P1）。
- 主干含全部通过代码评审的任务 commit（`git log` 可查）。

## 要求

1. 读取 `rules/team-charter.md`、`design/ARCH.md`、`review/code/` 结论。
2. 按 `skills/releasing` 阶段一执行：
   - **全新 worktree** 从主干拉取构建（禁止用工作区脏状态）
   - 编译 → 打包归档 `release/artifact/`（含版本号、commit、依赖清单）
   - 用 `skills/doc-writing` 产出 `release/manual-install.md` / `release/manual-release.md`（**基于真实构建产物**）
   - 目标环境部署 + 冒烟验证（记录命令与结果）
   - 标记**测试版**
3. 产出**构建证据**：build 标识 / commit / 构建命令 / 依赖版本 / 冒烟结果 / 手册路径——交 PM 记入看板，供 `RUN.envs` 引用。
4. 向 PM 报告：`BUILD-DONE | build | commit | 冒烟结果 | 手册路径`；失败报 `BUILD-BLOCKED | 原因 | 已尝试`。

## 禁止

- 禁止跳过冒烟验证。
- 禁止在 P0/P1 未关闭时构建（测试结论会失真）。
- 禁止用工作区而非 worktree 构建。
- 禁止修改 `src/` 代码（构建发现问题 → 报 PM 派发开发者修复）。
