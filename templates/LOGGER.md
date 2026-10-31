# 日志设计：$PROJECT_NAME

> 产出角色：architect ｜ 存放：design/LOGGER.md

## 1. 日志目录与文件

| 日志类型 | 目录 | 文件名规则 | 切分策略 | 保留期 |
|---------|------|-----------|---------|--------|
| 应用日志 | logs/app/ | app-YYYYMMDD.log | 按天 | 30 天 |
| 错误日志 | logs/error/ | error-YYYYMMDD.log | 按天 | 90 天 |
| 审计日志 | logs/audit/ | audit-YYYYMMDD.log | 按天 | 180 天 |

## 2. 日志格式

```
[时间] [级别] [模块] [功能编号] [traceId] [线程] 消息 {结构化字段}
```

| 字段 | 说明 | 示例 |
|------|------|------|
| 时间 | ISO8601 | 2026-01-01T10:00:00.000+08:00 |
| 级别 | DEBUG/INFO/WARN/ERROR | INFO |
| 组件/模块 | 名称 | workbench/task_list |
| 功能编号 | fr-$COMPONENT-$MODULE-NNN | fr-workbench-task_list-001 |
| traceId | 链路追踪 | |
| 消息 | 人类可读 | |

## 3. 记录内容

| 事件类型 | 级别 | 是否记录 | 备注 |
|---------|------|---------|------|
| 请求入口/出口 | INFO | 是 | 含耗时 |
| 业务关键节点 | INFO | 是 | |
| 异常 | ERROR | 是 | 含堆栈 |
| 敏感数据 | - | **禁止** | 脱敏后记录 |

## 4. 脱敏规则

| 字段 | 脱敏方式 |
|------|---------|
| 手机号 | 保留前3后4 |
| 密码/密钥 | 完全不记录 |

## 5. 日志样例

```
[2026-01-01T10:00:00.123+08:00] [INFO] [workbench] [fr-workbench-task_list-001] [t-8f2a] [http-nio-8080-exec-1] 用户注册成功 {"userId":1001}
```
