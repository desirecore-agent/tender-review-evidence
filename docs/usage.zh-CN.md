# 使用指南 — tender-evidence-review v1.2（草案）

运行时位置先按[正式 Skill 接收入口](../skills/tender-evidence-review/SKILL.zh-CN.md)用当前 ToolCatalog 和只读 ManageWorkDirs(list,current)核本角色登记私有 workspace，再读固定相对初始化回执或本轮已授权的精确回执。PRIVATE_RUNTIME_DIR/BOOTSTRAP_PYTHON/EVIDENCE_SKILL_DIR 是从这些真实事实解析并核验的本地变量，不是自动提供的环境变量；团队 cwd 不能代替私有目录。找不到就 blocked，不搜旧任务或自行替代安装。已有已核环境应复用；下面创建流程只适用于明确授权的初始化，不是每次复核默认重建。

## 前置条件

- Python >= 3.9
- jsonschema 4.25.1 及全部传递依赖（见 `requirements.lock`）
- 团队共享契约 v1.2 Schema 目录 `<TEAM_ROOT>/shared/contracts/schemas/`
- 调用方经当前角色定位后核实的绝对路径（不是平台自动注入变量）：`EVIDENCE_SKILL_DIR`、`PRIVATE_RUNTIME_DIR`、`BOOTSTRAP_PYTHON`

## 搭建校验器环境

```sh
# ─── 0. 调用方依据当前已授权事实解析并核验以下绝对路径 ─────────────────────────────────────
# EVIDENCE_SKILL_DIR：本技能根目录的绝对路径（不在材料/数据包目录内）
# PRIVATE_RUNTIME_DIR：每用户每 Agent 私有目录（绝对、可写、不在技能目录内）
# BOOTSTRAP_PYTHON：Python >=3.9 解释器的绝对路径（仅用于 venv 创建）

# ─── 1. 必需变量守卫 ──────────────────────────────────────────────
[ -n "${EVIDENCE_SKILL_DIR:-}" ] && [ -d "$EVIDENCE_SKILL_DIR" ] || { echo "BLOCKED: EVIDENCE_SKILL_DIR 未设置或不是目录" >&2; exit 2; }
[ -n "${PRIVATE_RUNTIME_DIR:-}" ] && [ -d "$PRIVATE_RUNTIME_DIR" ] || { echo "BLOCKED: PRIVATE_RUNTIME_DIR 未设置或不是目录" >&2; exit 2; }
[ -n "${BOOTSTRAP_PYTHON:-}" ] && [ -x "$BOOTSTRAP_PYTHON" ] || { echo "BLOCKED: BOOTSTRAP_PYTHON 未设置或不可执行" >&2; exit 2; }
case "$PRIVATE_RUNTIME_DIR" in "$EVIDENCE_SKILL_DIR"*|"") echo "BLOCKED: PRIVATE_RUNTIME_DIR 须在技能目录之外" >&2; exit 2; esac

# ─── 2. 创建隔离 venv ────────────────────────────────────────────
VALIDATOR_ENV_DIR="$PRIVATE_RUNTIME_DIR/evidence-validator-env"
"$BOOTSTRAP_PYTHON" -m venv "$VALIDATOR_ENV_DIR"
# 按 OS 解析 venv 解释器
case "$(uname -s)" in
  MINGW*|MSYS*|CYGWIN*|Windows_NT) VALIDATOR_PYTHON="$VALIDATOR_ENV_DIR/Scripts/python.exe";;
  *)                                 VALIDATOR_PYTHON="$VALIDATOR_ENV_DIR/bin/python";;
esac
"$VALIDATOR_PYTHON" -m pip install --require-hashes --only-binary=:all: \
  -r "$EVIDENCE_SKILL_DIR/requirements.lock"
# 平台无兼容二进制 wheel → 安装失败（阻塞）。不回退 sdist。
```

如果调用方无法依据本角色当前已授权的定位事实解析并核验所需变量，**停止**。不要猜测 `cwd`、裸 `python3` 或相对路径。

## 校验报告数据包

### 基本校验（六件门禁）

```sh
"$VALIDATOR_PYTHON" "$EVIDENCE_SKILL_DIR/scripts/validate_report.py" \
  --pack "$PACK_DIR" \
  --schemas "$TEAM_ROOT/shared/contracts/schemas" \
  --json
```

### 校验独立复核员产物

```sh
"$VALIDATOR_PYTHON" "$EVIDENCE_SKILL_DIR/scripts/validate_report.py" \
  --pack "$REVIEW_PACK_DIR" \
  --schemas "$TEAM_ROOT/shared/contracts/schemas" \
  --review-pack --json
```

`--review-pack` 是格式门禁；真正的独立执行需看运行记录和产物回执。

### 退出码

| 退出码 | 含义 |
|--------|------|
| 0 | 当前检查规则全部通过 |
| 1 | 结构违规或业务规则失败；**也**包括 `--json` 模式下 Schema 加载错误（错误写到 stdout） |
| 2 | 调用、文件或依赖导入错误（错误在 stderr） |

`--json` 模式下 Schema 加载错误在 **stdout** 输出 `{"error":...}`，退出码 1。pack/schema 目录不存在或依赖导入错误在 stderr 输出，退出码 2。不要假设所有错误都在 stderr。

### JSON 输出

- `result`："pass" 或 "fail"
- `violation_count`：违规数
- `violations`：`{rule, path, msg}` 对象数组（不是 `message`）
- `identity_ok`：合同名称→布尔值字典（不是单个布尔值）；全部为 true 才算通过
- `artifact_states`：每产物状态
- `artifacts_present`、`artifacts_missing`、`artifacts_invalid`

**不要把空 stdout 当作成功。** 务必检查退出码并解析输出。

## 校验器检查内容

### Schema 校验（jsonschema Draft-07）

- `Draft7Validator.check_schema()` 显式验证每个 Schema
- 本地**空 `Registry`** 禁止远程引用解析；`--schemas` 目录**不会**被预注册为跨资源 Registry
- Schema 中有 `format` 字段不等于已启用格式校验

### 业务规则

机器当前仅对 `severity=potential_rejection` 强制 R2/G05 双边证据。`potential_rejection` 和 `high` 严重性发现均要求**独立人工重读**（不论 `certainty`），但机器当前不对 `high` 强制双边检查。

## 工作流示例

```
1. 总审完成初轮审查 → 产出作者包
2. 独立复核员对作者包运行校验器 → 任何违规在人工复核前记录
3. 独立复核员执行人工重读：
   - 重读所有 potential_rejection 和 high 严重性发现的双边证据
   - 搜索负例 / 复算 / 校验图像 / 重新计数覆盖闭合
4. 复核员产出复核包 → 运行校验器（--review-pack）
5. 复核员逐条记录确认/降级/撤回及完整 issue_id 理由
6. 最终包交团队负责人合并
```

## 重要声明

- **机器通过 ≠ 审查完成**：独立人工重读是独立且必须的步骤。
- **诚实部分交付有效**：`conclusion=partial_only` 配诚实覆盖是有效的，通过结构校验。
- **模型通道处理**：发送到模型的文字和图像由模型提供商处理。用户须拥有材料处理权利。
- **本为草案**：正式校验器已通过 R7/R8，但最终发布需原子晋升完整验证组合，本文档为发布草案，非生产就绪。
