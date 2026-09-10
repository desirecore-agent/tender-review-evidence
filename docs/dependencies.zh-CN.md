# 依赖说明 — tender-evidence-review v1.2（草案）

运行时位置先按[正式 Skill 接收入口](../skills/tender-evidence-review/SKILL.zh-CN.md)用当前 ToolCatalog 和只读 ManageWorkDirs(list,current)核本角色登记私有 workspace，再读固定相对初始化回执或本轮已授权的精确回执。PRIVATE_RUNTIME_DIR/BOOTSTRAP_PYTHON/EVIDENCE_SKILL_DIR 是从这些真实事实解析并核验的本地变量，不是自动提供的环境变量；团队 cwd 不能代替私有目录。找不到就 blocked，不搜旧任务或自行替代安装。已有已核环境应复用；下面创建流程只适用于明确授权的初始化，不是每次复核默认重建。

## Python 要求

- **Python >= 3.9**
- 调用方须依据本角色当前已授权的定位事实，解析并核验 `BOOTSTRAP_PYTHON` 为可用 Python 解释器的绝对路径。
  此解释器仅用于创建 venv，**不向系统 site-packages 安装**。
- 不要使用裸 `python3` 或相对路径；须对照上述当前事实核验确切解释器。必需事实缺失或无法核验时**阻塞**。

## 直接依赖

| 包名 | 版本 | 用途 | 许可证 |
|------|------|------|--------|
| jsonschema | 4.25.1 | JSON Schema 校验（Draft-07，`Draft7Validator.check_schema()`） | MIT |

## 传递依赖

| 包名 | 版本 | 被谁需要 | 许可证 |
|------|------|----------|--------|
| attrs | 26.1.0 | jsonschema, referencing | MIT |
| jsonschema-specifications | 2025.9.1 | jsonschema | MIT |
| referencing | 0.36.2 | jsonschema, jsonschema-specifications | MIT |
| rpds-py | 0.27.1 | jsonschema, referencing | MIT |
| typing_extensions | 4.16.0 | referencing（条件：`python_version < "3.13"`） | PSF-2.0 |

依赖图（直接 `Requires-Dist` 边）：

```
jsonschema ──→ attrs
            ──→ jsonschema-specifications ──→ referencing ──→ attrs
            ──→ referencing ──→ rpds-py
            ──→ rpds-py                ──→ rpds-py
                           referencing ──→ typing_extensions (python < 3.13)
```

以上是 jsonschema 4.25.1 的验证兼容版本集（2026-08-31），不是最新版本。

`typing_extensions` 是 `referencing` 的条件依赖（仅在 Python < 3.13 时激活）。
统一锁住是兼容超集。

## 为何选择 jsonschema 4.25.1

- 已验证 MIT 许可、Python >= 3.9 兼容
- 显式 `Draft7Validator.check_schema()` 支持
- 空 `Registry` 禁止远程引用
- 成熟、经过充分测试的库

## 安装依赖

```sh
# 调用方须按本角色当前已授权定位事实赋值：EVIDENCE_SKILL_DIR、PRIVATE_RUNTIME_DIR、BOOTSTRAP_PYTHON
"$BOOTSTRAP_PYTHON" -m venv "$PRIVATE_RUNTIME_DIR/evidence-validator-env"
case "$(uname -s)" in
  MINGW*|MSYS*|CYGWIN*|Windows_NT) VALIDATOR_PYTHON="$PRIVATE_RUNTIME_DIR/evidence-validator-env/Scripts/python.exe";;
  *)                                 VALIDATOR_PYTHON="$PRIVATE_RUNTIME_DIR/evidence-validator-env/bin/python";;
esac
"$VALIDATOR_PYTHON" -m pip install --require-hashes --only-binary=:all: \
  -r "$EVIDENCE_SKILL_DIR/requirements.lock"
```

`requirements.lock` 包含**完整官方分发哈希集**（6 个包共 165 个哈希）——
PyPI 为这些精确版本发布的所有 wheel 和 sdist。对任何单一平台是超集；
`--only-binary=:all:` 意味着只安装匹配的 wheel。

### 失败策略

- 平台无兼容二进制 wheel → **阻塞**
- 不回退 sdist（源码构建）、全局 pip 或 sudo
- 不移除 `--only-binary` 允许源码构建
- 如实报告阻塞原因

## 本技能不依赖的

- 无 OCR 引擎、邮件客户端或 URL 抓取
- 运行时无需网络访问（Schema 解析仅限本地）
- 无 Rust 工具链或构建依赖（仅限二进制约束）
- 除 Python 本身外无系统级包

## DesireCore 平台

DesireCore 平台是运行时依赖。每个已安装版本遵从其自身的 LICENSE 和 NOTICE。
根目录 LICENSE 中的 MIT 许可证仅覆盖标书审查团队原创内容。

## 模型通道

用户选择的模型（本地或云端）处理文字和图像。用户须拥有材料处理权利。
这是运行时依赖，不是 Python 包依赖。

## 安全

- 安装在 `PRIVATE_RUNTIME_DIR` 的隔离 venv 中
- `--require-hashes` 确保只安装已验证的包
- `--only-binary=:all:` 防止源码构建
- Schema 解析使用空 `Registry`；无远程引用
