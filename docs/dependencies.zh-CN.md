# 可选结构化导出依赖

业务证据复核不要求 Python 环境。以下依赖仅用于用户明确要求校验保留的 v1.2 六类 JSON 导出。

使用 Python 3.9+ 与技能内 `skills/tender-evidence-review/requirements.lock`（jsonschema 4.25.1 及锁定传递依赖；许可证见 NOTICE）。从当前工作目录解析获准的解释器、已安装技能目录、团队 Schema 目录和可写隔离环境，复用合适环境。需要初始化时，在授权目录创建 venv，使用 `pip install --require-hashes --only-binary=:all: -r <lock-path>` 安装；不全局安装、不改源材料。无兼容 wheel 表示导出校验不可用，自然语言复核仍可继续。

执行：

```sh
"$VALIDATOR_PYTHON" "$EVIDENCE_SKILL_DIR/scripts/validate_report.py" \
  --pack "$PACK_DIR" --schemas "$TEAM_ROOT/shared/contracts/schemas" --json
```

变量代表实际授权路径，不是平台自动提供的环境变量。脚本检查本地 JSON 与内部一致性，不会独立读取业务原件或证明事实。记录实际失败，修正导出时不得编造事实。参见[恢复](recovery.zh-CN.md)。

所选模型按部署方式处理提供的文本图片，安装技能不表示授权额外 OCR 或外部服务。
