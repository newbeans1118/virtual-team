-- ============================================================
-- 模版：SQLITE-SCHEMA.sql ｜ 使用：store=sqlite 时由 test-data-gen/
--       case-structure/prd-structure 首次建库执行 ｜ 参照 templates/STORE-CONFIG.json
-- 契约版本: acceptance-v3（acceptance 条列 + GWT{given,when,then,kind} + cases.acceptance_refs；req_* → prd_* 契约重命名；JSON 与 SQL 双轨同序列化）
-- 原则：
--   1. 机制七表字段与 JSON 契约一一对应（templates/ 各模板）
--   2. execs 只追加（触发器禁 UPDATE/DELETE，对应"EXEC 只追加不改写"红线）
--   3. 业务表（td_biz_*）由 test-data-gen 按项目数据域创建，
--      必须含 td_id 列并外键关联 td_registry(id)（用户裁决：业务表与注册表建立关联）
--   4. 加载脚本单独存文件（test/data/scripts/），不入库
-- ============================================================

PRAGMA foreign_keys = ON;

-- ---------- PRD 侧 ----------
-- 来自 docs/prd/$COMPONENT/$MODULE/trace/prd.json 分片；component+module 双列承载分片语义
CREATE TABLE IF NOT EXISTS prd_functions (
  id          TEXT PRIMARY KEY,          -- fr-$COMPONENT-$MODULE-NNN
  component   TEXT NOT NULL,             -- $COMPONENT（一级分片键）
  module      TEXT NOT NULL,             -- $MODULE（二级分片键；组件不细分模块时 = 'all'）
  name        TEXT NOT NULL,
  biz_refs    TEXT,                      -- JSON 数组 ["biz-$COMPONENT-$MODULE-NNN"]
  actor       TEXT,
  acceptance  TEXT,                      -- JSON 数组 [{"key":"c1","given":"…","when":"…","then":"…","kind":"normal"}]（条列+GWT=验证条件/测试点）
                                         -- 旧数据为纯文本时按单条目读取（key=c1，then=原文本）；空数组 = '[]' 而非 NULL
  constraints TEXT,                      -- JSON 数组
  status      TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','deprecated')),
  source_hash TEXT NOT NULL,
  version     INTEGER NOT NULL DEFAULT 1,
  updated_at  TEXT
);
CREATE INDEX IF NOT EXISTS idx_req_component ON prd_functions(component);
CREATE INDEX IF NOT EXISTS idx_req_module ON prd_functions(component, module);

-- ---------- 用例侧 ----------
-- 来自 test/trace/$COMPONENT/case-*.json 分片；用例有主组件（component 列），可跨组件引用功能点
CREATE TABLE IF NOT EXISTS cases (
  case_id           TEXT PRIMARY KEY,    -- CASE-$COMPONENT-NNN
  component         TEXT NOT NULL,       -- 主归属组件
  module            TEXT NOT NULL,       -- 主归属模块（组件不细分模块时 = 'all'）
  title             TEXT NOT NULL,
  function_refs     TEXT NOT NULL,       -- JSON 数组 ["fr-$COMPONENT-$MODULE-NNN"]（可跨组件/跨模块）
  acceptance_refs   TEXT,                -- JSON 数组 ["fr-$COMPONENT-$MODULE-NNN:c1"]（本用例覆盖的验证条件；空 = '[]' 而非 NULL）
                                         -- 引用闭合：每项前缀 fr-id 必须在 function_refs 中
  dataset_refs      TEXT,                -- JSON 数组 ["TD-$COMPONENT-NNN"]（与 td_registry.owner_cases 双向一致）
  type              TEXT CHECK (type IN ('functional','performance','security','compatibility')),
  priority          TEXT CHECK (priority IN ('P0','P1','P2')),
  status            TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','active','deprecated')),
  preconditions     TEXT,                -- JSON 数组
  automation        TEXT,                -- JSON {automatable, script_ref, last_verified_run}
  latest_result_ref TEXT,                -- 指针文本（如 "runs/RUN-007/EXEC-<组件>-<模块>.jsonl#L3"）
  prd_source_hash   TEXT NOT NULL,
  updated_at        TEXT
);
CREATE INDEX IF NOT EXISTS idx_cases_component ON cases(component);
CREATE INDEX IF NOT EXISTS idx_cases_module ON cases(component, module);

-- 旧库升级（v0 → acceptance-v1）：已建库且 cases 无本列时执行
-- ALTER TABLE cases ADD COLUMN acceptance_refs TEXT;

-- ---------- 数据单元注册表 ----------
-- 来自 test/trace/$COMPONENT/TD-REGISTRY-*.json 分片（SQLite 轨为本表）；黑盒：机制层只认这些列
CREATE TABLE IF NOT EXISTS td_registry (
  id            TEXT PRIMARY KEY,        -- TD-$COMPONENT-NNN
  component     TEXT NOT NULL,           -- 主归属组件（一级分片键）
  module        TEXT NOT NULL,           -- 主归属模块（二级分片键；组件不细分模块时 = 'all'）
  purpose       TEXT NOT NULL,
  suitable_for  TEXT NOT NULL,           -- JSON 数组，值域 normal/boundary/negative（与 PRD 侧 acceptance.kind 同枚举；混合底座多值，不设 combination）
  preconditions TEXT,                    -- JSON 数组
  data_scope    TEXT,
  owner_cases   TEXT NOT NULL,           -- JSON 数组 ["CASE-$COMPONENT-NNN"]（与 cases.dataset_refs 双向一致）
  load_entry    TEXT NOT NULL,           -- 加载脚本路径（脚本文件单独存放，不入库）
  verified      TEXT,                    -- JSON {command,result,at}
  updated_at    TEXT
);
CREATE INDEX IF NOT EXISTS idx_td_registry_component ON td_registry(component);
CREATE INDEX IF NOT EXISTS idx_td_registry_module ON td_registry(component, module);

-- ---------- 执行轮（计划态，test-manager 创建） ----------
CREATE TABLE IF NOT EXISTS runs (
  run_id      TEXT PRIMARY KEY,          -- RUN-xxx
  trigger     TEXT NOT NULL CHECK (trigger IN ('full','regression','smoke','defect-verify')),
  defect_refs TEXT,                      -- JSON 数组（defect-verify 时必填）
  scope       TEXT,                      -- JSON {modules,case_ids,tags}
  envs        TEXT,                      -- JSON 数组 [{name,build,commit}]（环境池，执行期独占租用；build/commit 引用测试版构建产物）
  started_at  TEXT                       -- 注意：无 summary/finished_at——轮次汇总由 test-rebuild 从 execs 派生（防回填竞态与双写）
);

-- ---------- 执行计划（实例化产物，审定后生效） ----------
-- plan_id 全局唯一（跨 RUN）：TM 审定时全局查重（含历史 RUN）——保证 exec_id 复合格式 {plan_ref}-{seq} 全局无撞号
CREATE TABLE IF NOT EXISTS exec_plans (
  plan_id    TEXT PRIMARY KEY,           -- P-xxx（全局唯一，跨 RUN 查重）
  component  TEXT NOT NULL,              -- $COMPONENT（分片键，与 prd_functions/cases/td_registry 对齐）
  module     TEXT NOT NULL,              -- $MODULE（分片键；组件不细分模块时 = 'all'）
  run_id     TEXT NOT NULL REFERENCES runs(run_id),
  case_id    TEXT NOT NULL REFERENCES cases(case_id),
  condition  TEXT,                       -- 所验证条件标识 "fr-$COMPONENT-$MODULE-NNN:c1"（kind 从 PRD 侧 acceptance 派生，配对须 ∈ td_registry.suitable_for；功能点级 fallback 时 NULL）
  td_id      TEXT NOT NULL REFERENCES td_registry(id),
  expected   TEXT NOT NULL,              -- 本实例的预期（文本；优先取条件 GWT 的 then）
  source     TEXT CHECK (source IN ('acceptance','case-expected','expected-hints','manual')),
  approved   INTEGER NOT NULL DEFAULT 0, -- test-manager 审定标记
  approved_by TEXT,                      -- 审定人（对应 EXEC-PLAN.json 的 approved_by）
  approved_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_exec_plans_component ON exec_plans(component);
CREATE INDEX IF NOT EXISTS idx_exec_plans_module ON exec_plans(component, module);

-- ---------- 执行明细（INSERT-only） ----------
CREATE TABLE IF NOT EXISTS execs (
  exec_id     TEXT PRIMARY KEY,          -- 复合格式 {plan_ref}-{seq}（如 P-003-1；plan_ref 全局唯一 → exec_id 全局唯一，并行分片零撞号）
  plan_ref    TEXT NOT NULL,
  run_id      TEXT NOT NULL REFERENCES runs(run_id),
  case_id     TEXT NOT NULL REFERENCES cases(case_id),
  condition   TEXT,                      -- 继承自 exec_plans.condition（所验证条件标识；fallback 时 NULL）
  td_id       TEXT NOT NULL REFERENCES td_registry(id),
  env         TEXT,                      -- 本实例执行时租用的环境名（归因依据）
  result      TEXT NOT NULL CHECK (result IN ('pass','fail','blocked')),
  defect_ref  TEXT,                      -- BUG-$COMPONENT-NNN（失败时）
  started_at  TEXT,
  duration_ms INTEGER,
  evidence    TEXT                       -- 证据文件路径（logs/…）
);
CREATE INDEX IF NOT EXISTS idx_execs_run ON execs(run_id);
CREATE INDEX IF NOT EXISTS idx_execs_case ON execs(case_id);
CREATE INDEX IF NOT EXISTS idx_execs_td ON execs(td_id);

-- 红线固化：EXEC 只追加不改写
CREATE TRIGGER IF NOT EXISTS trg_execs_no_update
  BEFORE UPDATE ON execs
BEGIN SELECT RAISE(ABORT, 'EXEC is append-only: UPDATE is forbidden'); END;
CREATE TRIGGER IF NOT EXISTS trg_execs_no_delete
  BEFORE DELETE ON execs
BEGIN SELECT RAISE(ABORT, 'EXEC is append-only: DELETE is forbidden'); END;

-- ---------- 缺陷 ----------
CREATE TABLE IF NOT EXISTS bugs (
  bug_id        TEXT PRIMARY KEY,        -- BUG-$COMPONENT-NNN
  title         TEXT NOT NULL,
  severity      TEXT CHECK (severity IN ('P0','P1','P2')),  -- 唯一分级字段（priority 已移除，语义重复）
  source_exec   TEXT REFERENCES execs(exec_id),
  source_run    TEXT REFERENCES runs(run_id),
  function_refs TEXT,                    -- JSON 数组
  repro_steps   TEXT,                    -- JSON 数组：复现步骤（引用 TD 加载 + 用例步骤）
  expected      TEXT,                    -- 期望（来自执行计划配对行）
  actual        TEXT,                    -- 实际
  evidence      TEXT,                    -- 证据文件路径
  status        TEXT NOT NULL DEFAULT 'open'
    CHECK (status IN ('open','in_fix','fixed','verify_pass','verify_fail','closed','rejected','deferred')),
  assigned_to   TEXT,
  fix           TEXT,                    -- JSON {commit,by,at}
  verification  TEXT,                    -- JSON {run,execs,result}
  reopen_count  INTEGER NOT NULL DEFAULT 0,
  created_at    TEXT,
  updated_at    TEXT
);
CREATE INDEX IF NOT EXISTS idx_bugs_status ON bugs(status);

-- ============================================================
-- 业务表（td_biz_*）：由 test-data-gen 按项目数据域创建。
-- 模板样例（样例本身业务无关，仅示范结构与关联约束）：
--   1. 表名前缀 td_biz_（见 STORE-CONFIG.biz_table_prefix）
--   2. 必含 td_id 列 + 外键关联 td_registry(id)（用户裁决：业务表与注册表建立关联）
--   3. 必含 row_id 列（业务表内唯一，加载脚本按行取数）
--   4. 建议含 tags 列（数据行标签，供配对推荐）
-- ============================================================

-- 样例：删除/重建由 test-data-gen 在生成数据时执行
-- CREATE TABLE IF NOT EXISTS td_biz_<domain> (
--   row_id   TEXT PRIMARY KEY,           -- 业务表内唯一
--   td_id    TEXT NOT NULL REFERENCES td_registry(id),  -- ★ 关联注册表（必须）
--   tags     TEXT,                       -- JSON 数组
--   -- ...以下为项目数据域字段，由 test-data-gen 按需求设计...
--   created_at TEXT
-- );
-- CREATE INDEX IF NOT EXISTS idx_td_biz_<domain>_td ON td_biz_<domain>(td_id);

-- ============================================================
-- 常用查询样例（TEST-METRICS 八项指标）
-- ============================================================
-- 通过率（按轮）：
--   SELECT result, COUNT(*) FROM execs WHERE run_id='RUN-xxx' GROUP BY result;
-- 需求覆盖率：
--   SELECT COUNT(DISTINCT j.value) AS covered,
--          (SELECT COUNT(*) FROM prd_functions WHERE status='active') AS total
--   FROM cases c, json_each(c.function_refs) j WHERE c.status='active';
-- 测试点级覆盖率（度量非门禁：被 ≥1 active 用例引用的验证条件 ÷ 全部 active 功能点的条件总数）：
--   WITH items AS (
--     SELECT rf.id AS fr_id, json_extract(a.value,'$.key') AS ckey
--     FROM prd_functions rf, json_each(rf.acceptance) a WHERE rf.status='active'
--   ), covered AS (
--     SELECT DISTINCT i.fr_id, i.ckey FROM items i
--     WHERE EXISTS (SELECT 1 FROM cases c, json_each(c.acceptance_refs) ar
--                   WHERE c.status='active' AND ar.value = i.fr_id || ':' || i.ckey)
--   )
--   SELECT (SELECT COUNT(*) FROM covered) AS covered, (SELECT COUNT(*) FROM items) AS total;
-- 未覆盖的验证条件清单（缺口报告）：
--   WITH items AS (
--     SELECT rf.id AS fr_id, json_extract(a.value,'$.key') AS ckey, json_extract(a.value,'$.kind') AS kind
--     FROM prd_functions rf, json_each(rf.acceptance) a WHERE rf.status='active'
--   )
--   SELECT fr_id, ckey, kind FROM items i
--   WHERE NOT EXISTS (SELECT 1 FROM cases c, json_each(c.acceptance_refs) ar
--                     WHERE c.status='active' AND ar.value = i.fr_id || ':' || i.ckey);
-- 无数据用例（假覆盖检测）：
--   SELECT case_id FROM cases WHERE status='active'
--     AND (dataset_refs IS NULL OR json_array_length(dataset_refs)=0);
-- 双向一致校验（TD owner_cases ↔ cases.dataset_refs）：
--   SELECT t.id FROM td_registry t WHERE EXISTS (
--     SELECT 1 FROM json_each(t.owner_cases) oc
--     WHERE NOT EXISTS (SELECT 1 FROM cases c
--       WHERE c.case_id=oc.value AND EXISTS (
--         SELECT 1 FROM json_each(c.dataset_refs) d WHERE d.value=t.id)));
-- 修复率：
--   SELECT SUM(CASE WHEN json_extract(verification,'$.result')='pass' THEN 1 ELSE 0 END)*1.0
--        / COUNT(*) FROM bugs WHERE status IN ('closed','verify_pass');
-- 重开率：
--   SELECT SUM(reopen_count)*1.0 / NULLIF(COUNT(*),0) FROM bugs WHERE status='closed';
-- 轮次汇总（原 RUN.summary 的派生替代，test-rebuild 使用）：
--   SELECT COUNT(*) AS total,
--          SUM(CASE WHEN result='pass' THEN 1 ELSE 0 END) AS pass,
--          SUM(CASE WHEN result='fail' THEN 1 ELSE 0 END) AS fail,
--          SUM(CASE WHEN result='blocked' THEN 1 ELSE 0 END) AS blocked
--   FROM execs WHERE run_id='RUN-xxx';
