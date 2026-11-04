#!/usr/bin/env bash
# ============================================================
# 模版：verify.sh —— 项目可执行校验入口
# 契约：rules/engineering-discipline.md §14（每项目必须有 scripts/verify.sh）
# 用法：
#   ./scripts/verify.sh --fast   # 提交前必跑（lint/类型/单测，目标 ≤2 分钟）
#   ./scripts/verify.sh          # 代码评审前 / 测试版构建前必跑（全量）
# 输出：每步 PASS/FAIL/SKIP + 汇总；任一 FAIL → 退出码非 0。
# 日志：build/verify/<UTC时间>-<commit>.log + latest.log（首行记录 commit）。
# 适配：只需修改下方「适配区」；未适配的占位命令会判 FAIL（fail-closed，
#       不允许未适配的模板伪装通过）。
# ============================================================
set -u
MODE="full"
[ "${1:-}" = "--fast" ] && MODE="fast"

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

COMMIT="$(git rev-parse HEAD 2>/dev/null || echo no-git)"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
LOG_DIR="$ROOT/build/verify"
LOG="$LOG_DIR/$STAMP-$COMMIT.log"
mkdir -p "$LOG_DIR"

# ---------------- 适配区（改这里，别改骨架） ----------------
# 格式："步骤名|fast也跑(1/0)|命令"
# 命令经 bash -c 解释执行，允许 && / || / 管道等复合命令；退出码即该步结果。
STEPS=(
  "lint|1|echo 'TODO_ADAPT: 替换为本项目 lint 命令，例如 npx eslint . || make lint'"
  "typecheck|1|echo 'TODO_ADAPT: 替换为本项目类型检查，例如 npx tsc --noEmit'"
  "unit|1|echo 'TODO_ADAPT: 替换为本项目单元测试，例如 npx vitest run || pytest -q'"
  "build|0|echo 'TODO_ADAPT: 替换为本项目构建命令，例如 npm run build || make build'"
  "integration|0|echo 'TODO_ADAPT: 替换为本项目集成测试命令'"
  "deps-scan|0|echo 'TODO_ADAPT: 替换为本项目依赖/安全扫描，例如 npm audit --production'"
)
# -----------------------------------------------------------

echo "commit $COMMIT" > "$LOG"
echo "verify mode=$MODE commit=$COMMIT" | tee -a "$LOG"

FAIL=0
for entry in "${STEPS[@]}"; do
  name="${entry%%|*}"; rest="${entry#*|}"
  in_fast="${rest%%|*}"; cmd="${rest#*|}"

  # fast 模式只跑 in_fast=1 的步骤
  if [ "$MODE" = "fast" ] && [ "$in_fast" != "1" ]; then
    echo "SKIP: $name — fast 模式不含该步骤" | tee -a "$LOG"
    continue
  fi
  # 工具缺失可 SKIP，但必须打印原因（discipline §14 SKIP 纪律）
  if echo "$cmd" | grep -q "TODO_ADAPT"; then
    echo "FAIL: $name — verify.sh 尚未适配本项目（占位命令）" | tee -a "$LOG"
    FAIL=$((FAIL + 1))
    continue
  fi

  if output=$(bash -c "$cmd" 2>&1); then
    echo "PASS: $name" | tee -a "$LOG"
    printf '%s\n' "$output" | tail -n 20 >> "$LOG"
  else
    code=$?
    echo "FAIL: $name (exit $code)" | tee -a "$LOG"
    printf '%s\n' "$output" | tail -n 50 >> "$LOG"
    FAIL=$((FAIL + 1))
  fi
done

echo "----------------------------------------" | tee -a "$LOG"
if [ "$FAIL" -gt 0 ]; then
  echo "verify: FAIL ($FAIL 步失败) | log $LOG" | tee -a "$LOG"
  cp "$LOG" "$LOG_DIR/latest.log"
  exit 1
fi
echo "verify: PASS (mode=$MODE) | log $LOG" | tee -a "$LOG"
cp "$LOG" "$LOG_DIR/latest.log"
exit 0
