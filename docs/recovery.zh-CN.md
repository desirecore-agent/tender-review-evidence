# 恢复指南 — tender-evidence-review v1.2（草案）

所有恢复保持可审计性：不静默修复，不覆写原件。

## 故障：缺少依赖（jsonschema 未安装）

**症状**：退出码 2；stderr：`{"error": "Cannot import schema_runtime: No module named 'jsonschema'"}`

**恢复**：
```sh
# 确保 EVIDENCE_SKILL_DIR、PRIVATE_RUNTIME_DIR、BOOTSTRAP_PYTHON 已设置且通过守卫。
"$BOOTSTRAP_PYTHON" -m venv "$PRIVATE_RUNTIME_DIR/evidence-validator-env"
case "$(uname -s)" in
  MINGW*|MSYS*|CYGWIN*|Windows_NT) VALIDATOR_PYTHON="$PRIVATE_RUNTIME_DIR/evidence-validator-env/Scripts/python.exe";;
  *)                                 VALIDATOR_PYTHON="$PRIVATE_RUNTIME_DIR/evidence-validator-env/bin/python";;
esac
"$VALIDATOR_PYTHON" -m pip install --require-hashes --only-binary=:all: \
  -r "$EVIDENCE_SKILL_DIR/requirements.lock"
```

无兼容二进制 wheel → **阻塞**。不回退 sdist、不全局 pip、不 sudo。

## 故障：Schema 缺失或损坏

**症状**：退出码 1（`--json` 模式：`{"error":...}` 在 **stdout**）；或退出码 2（目录不存在/导入错误在 stderr）。

**恢复**：
1. 确认 `--schemas` 路径指向 `<TEAM_ROOT>/shared/contracts/schemas/`
2. 确认六份 `.schema.json` 文件均存在且可解析
3. 损坏 → **fail closed**

## 故障：数据包缺少产物

**症状**：退出码 1；`artifact_states` 显示 `absent`。

**恢复**：六件门禁要求全部六件。记录缺失项；不通过。

## 故障：`manifest_id` 不一致（G06）

**症状**：退出码 1。

**恢复**：绑定关系为 `file-manifest.manifest_id` = `requirements.manifest_id` = `coverage.manifest_id` = `findings.manifest_id` = `review-report.inputs_version.manifest_id`；`project-profile` 无 `manifest_id`。不编辑匹配——重新生成过时产物。

## 故障：覆盖闭合不匹配（R3/G02）

**症状**：退出码 1。

**恢复**：从 `items[]` 以 `checked`/`failed`/`unchecked` 终态重新计数（不是 "completed"）。验证 `coverage_file_ids` 覆盖完整 manifest 减去有理由排除的文件。

## 核心原则

1. **Fail closed**：有疑问时拒绝。
2. **不静默修复**：每次修正可追溯。
3. **原件只读**：恢复从不修改源文件或作者包。
4. **诚实部分交付**：`partial_only` 是合法的，不等于"通过"。
5. **仅限二进制**：无 sdist、无全局 pip、无 sudo。
6. **平台提供路径**：如果 `EVIDENCE_SKILL_DIR`、`PRIVATE_RUNTIME_DIR` 或 `BOOTSTRAP_PYTHON` 不可用 → 阻塞。
