# 独立复核员清单 — tender-evidence-review v1.2（草案）

机器校验与人工重读缺一不可，互不替代。

## 复核前

- [ ] 数据包含全部六类 JSON 产物
- [ ] `identity_ok`：六个合同名称全部映射 `true`（字典，非单个布尔值）
- [ ] 空输出不算成功——检查退出码

## 双边证据重读（`severity=potential_rejection` 或 `severity=high`，不论 `certainty`）

- [ ] **招标侧**：重读条款矩阵 → 源文件页/段落
  - [ ] `source_file_id` 解析为清单中文件
  - [ ] 比对 `source_quote` 与实际文本
  - [ ] 记录：定位 → 结果 → 一致/不一致 → 理由
- [ ] **投标侧**：重读投标文件位置
  - [ ] `bid_evidence[].file_id` 解析为清单中文件
  - [ ] 比对 `observation` 与实际内容
  - [ ] 记录：定位 → 结果 → 一致/不一致 → 理由
- [ ] 若 `evidence_type=absence`：
  - [ ] `searched_coverage_item_ids` 非空
  - [ ] 每个引用项存在、状态为 `checked`、属于同一 `file_id`
  - [ ] 页码在 `physical_pages` 内

## 负例搜索

- [ ] 检查补遗、例外条款、其他页面
- [ ] 若负例成立 → 记录降级/撤回

## 算式验证

- [ ] 用真实十进制计算工具重算
- [ ] 核对输入、单位、公式、舍入、结果

## 图像观察校验

- [ ] 有实际查看记录（非占位符）
- [ ] `readability` 与实际状态一致
- [ ] `file_id` 指向清单中实际来源文件（PDF、DOCX、图片等任何格式）
- [ ] `location` 在 `physical_pages` 内

## 覆盖闭合重新计数

- [ ] `checked`/`failed`/`unchecked` 与汇总一致
- [ ] 每个 failed/unchecked 有非空 `reason`
- [ ] 每个 checked 有 `method` 或 `location`
- [ ] `coverage_file_ids[]` 覆盖完整 manifest 减去有理由排除的文件

## 版本绑定（G06）

- [ ] `file-manifest.manifest_id` = `requirements.manifest_id` = `coverage.manifest_id` = `findings.manifest_id` = `report.inputs_version.manifest_id`
- [ ] `project-profile` 无 `manifest_id`

## 报告结论（G03）

- [ ] `coverage_closed=false` → `conclusion` 为 `partial_only` 或 `cannot_conclude`
- [ ] `conclusion=pass` 要求全部完成、无失败、无未检

## 复核状态（R5）

- [ ] 作者包无 `reviewed_*`
- [ ] `review_summary.notes` 使用完整 `issue_id`，可引用 `limitations`
- [ ] 不捏造 `review_reason`/`review_note`

## 路径安全（G07）

- [ ] 无 `relative_path` 含反斜杠（任何位置）
- [ ] 无绝对/盘符/UNC/`..`/NUL/空路径

## 机器与人工分工

- [ ] 机器对 `potential_rejection` 强制 R2/G05 双边
- [ ] 人工重读 `potential_rejection` 和 `high`（不论 `certainty`）
- [ ] `observation_method` 非空（机器门禁）
- [ ] 机器当前不对 `high` 强制双边

## 最终记录

- [ ] 完整 `issue_id`（不用子串匹配）
- [ ] 「未读到」绝不写为「未提供」
