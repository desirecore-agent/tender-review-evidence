#!/usr/bin/env python3
"""validate_report.py — 标书审查报告数据包校验器（契约 v1.2）。

定位：结构校验委托 schema_runtime（Draft-07 完整检查），业务规则由本脚本实现。
不合格立即 JSON fail + 非零退出码。

退出码：0=pass；1=fail；2=调用/文件错误。
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# schema_runtime import（结构层）
# ---------------------------------------------------------------------------
_SCRIPT_DIR = Path(__file__).resolve().parent
_RUNTIME_DIR = None
_candidates = [
    _SCRIPT_DIR,  # 同目录（安装后随包）
    _SCRIPT_DIR.parent.parent.parent.parent.parent / "agents" / "tender-review-evidence" / "skills" / "tender-evidence-review" / "scripts",
]
for _p in _candidates:
    if (_p / "schema_runtime.py").is_file():
        _RUNTIME_DIR = _p
        break
if _RUNTIME_DIR is None:
    print(json.dumps({"error": "schema_runtime.py not found"}), file=sys.stderr)
    sys.exit(2)
if str(_RUNTIME_DIR) not in sys.path:
    sys.path.insert(0, str(_RUNTIME_DIR))

try:
    from schema_runtime import (
        load_contracts,
        check_contract_identity,
        validate_payload,
        CONTRACT_NAMES,
    )
except ImportError as exc:
    print(json.dumps({"error": f"Cannot import schema_runtime: {exc}"}), file=sys.stderr)
    sys.exit(2)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
REVIEWED_STATUSES = ("reviewed_confirmed", "reviewed_downgraded", "reviewed_withdrawn")
PARTIAL_CONCLUSIONS = ("partial_only", "cannot_conclude")
ALLOWED_PATH_RE = re.compile(
    r"^(?!/)(?!\\\\)(?![A-Za-z]:)(?!.*(?:^|/)\.\.(?:/|$))[^\u0000]+$"
)
MANIFEST_FIELDS = ("coverage", "findings", "requirements")


def _nonempty(v):
    return isinstance(v, str) and v.strip() != ""


def _is_list(v):
    return v if isinstance(v, list) else None


def _is_dict(v):
    return v if isinstance(v, dict) else None


def _vloc(base, *parts):
    return ".".join(str(p) for p in (base,) + parts if p is not None)


def _parse_location(value):
    """Parse explicit physical pages; keep other nonempty locators opaque.

    Physical forms: page(s)/p./p N[-M], 第N[-M]页, 第N页至第M页.
    Logical locators (e.g. body:12) match exactly, never as physical pages.
    """
    if not _nonempty(value):
        raise ValueError("缺少可定位位置")
    text = value.strip()
    patterns = (
        r"(?:pages?|p\.?)\s*(\d+)(?:\s*[-–—至到]\s*(\d+))?",
        r"第\s*(\d+)(?:\s*[-–—至到]\s*(\d+))?\s*页",
        r"第\s*(\d+)\s*页\s*[-–—至到]\s*第?\s*(\d+)\s*页",
    )
    for pattern in patterns:
        match = re.fullmatch(pattern, text, re.IGNORECASE)
        if match:
            first = int(match.group(1))
            last = int(match.group(2) or match.group(1))
            if first < 1 or last < first:
                raise ValueError("物理页范围必须从1开始且顺序有效")
            return ("pages", first, last)
    # An unsupported explicit page expression must not silently become a locator.
    if re.match(r"^(?:pages?(?:\b|(?=\d))|p\.?\s*\d)", text, re.IGNORECASE) or re.search(r"第.*页|\d\s*页", text, re.DOTALL):
        raise ValueError("未支持的明确物理页格式，需标未核或改为约定页码形式")
    return ("logical", text)


def _location_contains(outer, inner):
    if outer[0] == inner[0] == "pages":
        return outer[1] <= inner[1] and outer[2] >= inner[2]
    return outer == inner


def _checked_location_covered(file_id, location, items, coverage_id=None):
    """Require same-file checked coverage; an explicit ID restricts the search.

    Without an ID, adjacent checked physical-page intervals may jointly cover
    the evidence range. Opaque logical locators require an exact match.
    """
    intervals = []
    for item in items:
        if item.get("file_id") != file_id or item.get("status") != "checked":
            continue
        if _nonempty(coverage_id) and item.get("item_id") != coverage_id:
            continue
        try:
            checked = _parse_location(item.get("location"))
        except ValueError:
            continue  # A method-only item cannot establish located evidence.
        if _location_contains(checked, location):
            return True
        if location[0] == checked[0] == "pages":
            intervals.append((checked[1], checked[2]))
    next_page = location[1] if location[0] == "pages" else None
    for first, last in sorted(intervals):
        if first > next_page:
            break
        next_page = max(next_page, last + 1)
        if next_page > location[2]:
            return True
    return False


# ---------------------------------------------------------------------------
# Pack loading (四态)
# ---------------------------------------------------------------------------
def load_pack(pack_dir):
    """Return ({name: data_or_None}, {name: state_str})."""
    pack, states = {}, {}
    for name in CONTRACT_NAMES:
        path = Path(pack_dir) / f"{name}.json"
        if not path.is_file():
            pack[name] = None
            states[name] = "absent"
            continue
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError) as exc:
            pack[name] = None
            states[name] = "parse_error"
            continue
        if data is None:
            pack[name] = None
            states[name] = "null"
        elif isinstance(data, dict):
            pack[name] = data
            states[name] = "object"
        else:
            pack[name] = None
            states[name] = "null"
    return pack, states


# ---------------------------------------------------------------------------
# G07: path validation
# ---------------------------------------------------------------------------
def _check_path(value):
    if not isinstance(value, str) or value == "":
        return "空或非字符串"
    if "\u0000" in value:
        return "含 NUL"
    if value.startswith("/"):
        return "POSIX 绝对路径"
    if "\\" in value or value.startswith("//"):
        return "反斜杠/UNC 路径"
    if re.match(r"^[A-Za-z]:", value):
        return "Windows 盘符"
    for seg in value.split("/"):
        if seg == "..":
            return "上级穿越"
    if not ALLOWED_PATH_RE.search(value):
        return "不匹配包内相对路径"
    return None


# ---------------------------------------------------------------------------
# Business rules
# ---------------------------------------------------------------------------
def check_business(pack, states, is_review_pack):
    V = []

    manifest = _is_dict(pack.get("file-manifest"))
    requirements = _is_dict(pack.get("requirements"))
    coverage = _is_dict(pack.get("coverage"))
    findings = _is_dict(pack.get("findings"))
    report = _is_dict(pack.get("review-report"))

    # ======================== G04: build indexes ========================
    file_ids = set()
    file_role = {}
    file_status = {}
    if manifest:
        files = _is_list(manifest.get("files"))
        if files is None and manifest.get("files") is not None:
            V.append({"rule": "G08:shape", "path": "file-manifest.files",
                       "msg": "files 应为数组"})
        for e in (files or []):
            if not isinstance(e, dict):
                continue
            fid = e.get("file_id")
            if _nonempty(fid):
                if fid in file_ids:
                    V.append({"rule": "G04:duplicate_file_id", "path": "file-manifest.files",
                               "msg": f"file_id '{fid}' 重复"})
                file_ids.add(fid)
                file_role[fid] = e.get("role")
                file_status[fid] = e.get("processing_status")

    req_index = {}
    if requirements:
        reqs = _is_list(requirements.get("requirements"))
        if reqs is None and requirements.get("requirements") is not None:
            V.append({"rule": "G08:shape", "path": "requirements.requirements",
                       "msg": "requirements 应为数组"})
        for e in (reqs or []):
            if not isinstance(e, dict):
                continue
            rid = e.get("requirement_id")
            if _nonempty(rid):
                if rid in req_index:
                    V.append({"rule": "G04:duplicate_req_id", "path": "requirements.requirements",
                               "msg": f"requirement_id '{rid}' 重复"})
                req_index[rid] = e
            sfid = e.get("source_file_id")
            if _nonempty(sfid) and sfid not in file_ids:
                V.append({"rule": "G04:source_file_unresolved",
                           "path": f"requirements({rid}).source_file_id",
                           "msg": f"来源文件 '{sfid}' 不在清单中"})

    cov_items = []
    all_item_ids = {}
    checked_item_ids = set()
    recount = {"checked": 0, "failed": 0, "unchecked": 0}
    failed_no_reason = 0
    unchecked_no_reason = 0
    checked_no_method = 0
    if coverage:
        raw = _is_list(coverage.get("items"))
        if raw is None and coverage.get("items") is not None:
            V.append({"rule": "G08:shape", "path": "coverage.items",
                       "msg": "items 应为数组"})
        for item in (raw or []):
            if not isinstance(item, dict):
                continue
            cov_items.append(item)
            iid = item.get("item_id")
            if _nonempty(iid):
                if iid in all_item_ids:
                    V.append({"rule": "G04:duplicate_item_id", "path": "coverage.items",
                               "msg": f"item_id '{iid}' 重复"})
                all_item_ids[iid] = item
            st = item.get("status")
            if st in recount:
                recount[st] += 1
            if st == "checked":
                if _nonempty(iid):
                    checked_item_ids.add(iid)
                if not (_nonempty(item.get("method")) or _nonempty(item.get("location"))):
                    checked_no_method += 1
            if st == "failed" and not _nonempty(item.get("reason")):
                failed_no_reason += 1
            if st == "unchecked" and not _nonempty(item.get("reason")):
                unchecked_no_reason += 1

    findings_list = []
    if findings:
        raw = _is_list(findings.get("findings"))
        if raw is None and findings.get("findings") is not None:
            V.append({"rule": "G08:shape", "path": "findings.findings",
                       "msg": "findings 应为数组"})
        for f in (raw or []):
            if isinstance(f, dict):
                findings_list.append(f)

    # ======================== G02: coverage closure ========================
    coverage_recount = None
    if coverage:
        pi = coverage.get("planned_items")
        ci = coverage.get("completed_items")
        fi = coverage.get("failed_items")
        ui = coverage.get("unchecked_items")
        all_int = all(isinstance(x, int) for x in (pi, ci, fi, ui))
        if all_int:
            total = recount["checked"] + recount["failed"] + recount["unchecked"]
            coverage_recount = {
                "planned_items": total,
                "completed_items": recount["checked"],
                "failed_items": recount["failed"],
                "unchecked_items": recount["unchecked"],
            }
            for key in ("planned_items", "completed_items", "failed_items", "unchecked_items"):
                if coverage.get(key) != coverage_recount[key]:
                    V.append({"rule": "G02:recount_mismatch",
                               "path": f"coverage.{key}",
                               "msg": f"{key}={coverage.get(key)} ≠ 重算={coverage_recount[key]}"})
            if failed_no_reason:
                V.append({"rule": "G02:failed_no_reason",
                           "path": "coverage.items",
                           "msg": f"{failed_no_reason} 个 failed 项缺 reason"})
            if unchecked_no_reason:
                V.append({"rule": "G02:unchecked_no_reason",
                           "path": "coverage.items",
                           "msg": f"{unchecked_no_reason}个 unchecked 项缺 reason"})
            closed_actual = (total == pi and failed_no_reason == 0 and unchecked_no_reason == 0)
            declared = coverage.get("coverage_closed")
            if isinstance(declared, bool) and declared != closed_actual:
                V.append({"rule": "G02:closure_mismatch",
                           "path": "coverage.coverage_closed",
                           "msg": f"declared={declared} ≠ actual={closed_actual}"})

    # ======================== G02: coverage file set completeness ========================
    # B1: coverage scope must cover all manifest files (minus explicit excluded)
    if coverage and manifest:
        manifest_files = {e.get("file_id") for e in (_is_list(manifest.get("files")) or [])
                          if isinstance(e, dict) and _nonempty(e.get("file_id"))}
        cov_file_ids_declared = set(coverage.get("coverage_file_ids") or [])
        # Build excluded set from coverage.excluded (string[]: "file_id: 非空理由")
        excluded_files = set()
        for exc in (_is_list(coverage.get("excluded")) or []):
            if isinstance(exc, str) and _nonempty(exc):
                # Format must be "file_id: non-empty reason"
                if ":" in exc:
                    fid_part = exc.split(":", 1)[0].strip()
                    reason_part = exc.split(":", 1)[1].strip()
                    if _nonempty(fid_part) and _nonempty(reason_part):
                        excluded_files.add(fid_part)
                    # bare "B:" or "B:   " → no valid exclusion
                else:
                    # bare "B" without colon → no valid exclusion
                    pass
        covered_or_excluded = cov_file_ids_declared | excluded_files
        # Any manifest file not in covered or excluded is silently missing
        for fid in manifest_files:
            if fid not in covered_or_excluded:
                V.append({"rule": "G02:silently_shrink_scope",
                           "path": "coverage",
                           "msg": f"manifest 文件 '{fid}' 未在 coverage_file_ids 或 excluded 中声明"})
        # Bidirectional: declared coverage items vs manifest
        cov_file_ids_actual = {it.get("file_id") for it in cov_items
                               if isinstance(it, dict) and _nonempty(it.get("file_id"))}
        for fid in cov_file_ids_declared:
            if _nonempty(fid) and fid not in cov_file_ids_actual:
                V.append({"rule": "G02:file_not_covered",
                           "path": "coverage",
                           "msg": f"coverage_file_ids 声明文件 '{fid}' 无对应覆盖项"})
        for fid in cov_file_ids_actual:
            if _nonempty(fid) and fid not in cov_file_ids_declared:
                V.append({"rule": "G02:unlisted_file_covered",
                           "path": "coverage",
                           "msg": f"文件 '{fid}' 有覆盖项但未在 coverage_file_ids 声明"})

    # ======================== G02: report counts must match recount ========================
    # B1: report.coverage_ref must bind coverage_id + coverage_closed + numbers to same recount
    if report and coverage_recount is not None:
        rc = report.get("coverage_ref")
        if isinstance(rc, dict):
            # coverage_id binding
            report_cid = rc.get("coverage_id")
            cov_cid = coverage.get("coverage_id") if coverage else None
            if _nonempty(report_cid) and _nonempty(cov_cid) and report_cid != cov_cid:
                V.append({"rule": "G02:report_wrong_coverage_id",
                           "path": "review-report.coverage_ref.coverage_id",
                           "msg": f"报告 coverage_id={report_cid} ≠ 合同={cov_cid}"})
            # coverage_closed binding
            report_closed = rc.get("coverage_closed")
            declared_closed = coverage.get("coverage_closed") if coverage else None
            if isinstance(report_closed, bool) and isinstance(declared_closed, bool) \
                    and report_closed != declared_closed:
                V.append({"rule": "G02:report_closed_disagrees",
                           "path": "review-report.coverage_ref.coverage_closed",
                           "msg": f"报告 closed={report_closed} ≠ 合同={declared_closed}"})
            # numeric counts binding
            for key in ("planned_items", "completed_items", "failed_items", "unchecked_items"):
                if rc.get(key) is not None and rc[key] != coverage_recount[key]:
                    V.append({"rule": "G02:report_counts_mismatch",
                               "path": f"review-report.coverage_ref.{key}",
                               "msg": f"报告 {key}={rc[key]} ≠ 重算={coverage_recount[key]}"})

    # ======================== G02: checked must have method+location =================
    if checked_no_method:
        V.append({"rule": "G02:checked_no_method_location",
                   "path": "coverage.items",
                   "msg": f"{checked_no_method} 个 checked 项缺 method 和 location"})

    # ======================== G03: file status vs coverage ========================
    if manifest and coverage:
        for item in cov_items:
            fid = item.get("file_id")
            if item.get("status") == "checked" and _nonempty(fid) \
                    and file_status.get(fid) in ("pending", "partial", "failed"):
                V.append({"rule": "G03:source_status_conflict",
                           "path": f"coverage({item.get('item_id')})",
                           "msg": f"文件 '{fid}' 状态={file_status[fid]} 但覆盖=checked"})

    # G03: conclusion admission
    coverage_closed_actual = None
    if coverage and coverage_recount:
        pi = coverage.get("planned_items")
        total = recount["checked"] + recount["failed"] + recount["unchecked"]
        coverage_closed_actual = (total == pi and failed_no_reason == 0
                                  and unchecked_no_reason == 0)

    if report:
        conclusion = report.get("conclusion")
        # pass / pass_with_cautions require closed + no failures + no unchecked
        clean_conclusions = ("pass", "pass_with_cautions")
        if conclusion in clean_conclusions and coverage_closed_actual is False:
            V.append({"rule": "G03:conclusion_pass_unclosed",
                       "path": "review-report.conclusion",
                       "msg": "coverage_closed=false 时不得 conclusion=pass/pass_with_cautions"})
        if conclusion in clean_conclusions and (recount["failed"] > 0 or recount["unchecked"] > 0):
            V.append({"rule": "G03:conclusion_pass_failures",
                       "path": "review-report.conclusion",
                       "msg": "存在 failed/unchecked 时不得 conclusion=pass/pass_with_cautions"})
        if coverage_closed_actual is False and conclusion not in PARTIAL_CONCLUSIONS:
            V.append({"rule": "G03:conclusion_not_partial",
                       "path": "review-report.conclusion",
                       "msg": "覆盖未闭合时只允许 partial_only/cannot_conclude"})
        # G03 rule: unchecked_items in report blocks pass
        unchecked_report = _is_list(report.get("unchecked_items")) or []
        if unchecked_report and conclusion in clean_conclusions:
            V.append({"rule": "G03:report_unchecked_blocks_pass",
                       "path": "review-report.unchecked_items",
                       "msg": f"报告自述 {len(unchecked_report)} 个未检项，不得 conclusion=pass/pass_with_cautions"})
        # B2 rule: tool_failures without recovery state block pass
        tool_failures_report = _is_list(report.get("tool_failures")) or []
        unresolved_failures = [t for t in tool_failures_report
                               if isinstance(t, dict) and t.get("resolved") is not True]
        if unresolved_failures and conclusion in clean_conclusions:
            V.append({"rule": "G03:unresolved_tool_failure_blocks_pass",
                       "path": "review-report.tool_failures",
                       "msg": f"报告含 {len(unresolved_failures)} 条未恢复工具失败，不得 conclusion=pass/pass_with_cautions"})

    physical_pages = {
        entry.get("file_id"): entry.get("physical_pages")
        for entry in (_is_list(manifest.get("files")) or []) if isinstance(entry, dict)
    } if manifest else {}

    def located(value, file_id, where, require_checked=False, coverage_id=None):
        """One locator/bounds/coverage gate shared by both evidence sides."""
        try:
            location = _parse_location(value)
        except ValueError as exc:
            V.append({"rule": "G05:location_invalid", "path": where, "msg": str(exc)})
            return None
        if file_id not in file_ids:
            V.append({"rule": "G05:location_file_unresolved", "path": where,
                      "msg": "位置引用的文件不在清单中"})
            return None
        pages = physical_pages.get(file_id)
        if location[0] == "pages" and isinstance(pages, int) and location[2] > pages:
            V.append({"rule": "G05:page_exceeds", "path": where,
                      "msg": f"物理页范围 {location[1]}-{location[2]} 超过 physical_pages={pages}"})
        if require_checked and not _checked_location_covered(file_id, location, cov_items, coverage_id):
            V.append({"rule": "G05:evidence_not_covered", "path": where,
                      "msg": "证据位置/范围没有同文件的 checked 覆盖（给定覆盖ID时仅认可该项）"})
        return location

    # ======================== G04: findings issue_id unique + refs ========================
    seen_issues = set()
    for idx, f in enumerate(findings_list):
        iid = f.get("issue_id", "")
        loc = f"findings[{idx}]({iid})"
        if _nonempty(iid):
            if iid in seen_issues:
                V.append({"rule": "G04:duplicate_issue_id", "path": loc,
                           "msg": f"issue_id '{iid}' 重复"})
            seen_issues.add(iid)
        # R2: bilateral evidence for potential_rejection
        if f.get("severity") == "potential_rejection":
            rr = _is_list(f.get("requirement_refs"))
            be = _is_list(f.get("bid_evidence"))
            if not (rr and len(rr) > 0):
                V.append({"rule": "G05:no_req_refs", "path": f"{loc}.requirement_refs",
                           "msg": "potential_rejection 缺 requirement_refs"})
            if not (be and len(be) > 0):
                V.append({"rule": "G05:no_bid_evidence", "path": f"{loc}.bid_evidence",
                           "msg": "potential_rejection 缺 bid_evidence"})
        # ======================== C1: bid_evidence present/absence binding ========================
        for be_idx, be in enumerate(_is_list(f.get("bid_evidence")) or []):
            if not isinstance(be, dict):
                continue
            be_loc = f"{loc}.bid_evidence[{be_idx}]"
            be_fid = be.get("file_id")
            ev_type = be.get("evidence_type", "present")
            # bid side: file must exist and NOT be tender_document
            if _nonempty(be_fid):
                if be_fid not in file_ids:
                    V.append({"rule": "G05:bid_file_not_exist",
                               "path": be_loc, "msg": f"bid file '{be_fid}' 不存在于清单"})
                else:
                    be_role = file_role.get(be_fid)
                    if be_role == "tender_document":
                        V.append({"rule": "G05:bid_uses_tender_role",
                                   "path": be_loc, "msg": f"bid 证据指向 tender_document '{be_fid}'，不能冒充投标侧响应"})
            if ev_type == "present":
                located(be.get("location"), be_fid, be_loc,
                        require_checked=True, coverage_id=be.get("coverage_item_id"))
            elif ev_type == "absence":
                # absence: must have searched_coverage_item_ids
                sci = _is_list(be.get("searched_coverage_item_ids"))
                if not sci or len(sci) == 0:
                    V.append({"rule": "G05:absence_no_searched_ids",
                               "path": be_loc, "msg": "absence 证据缺 searched_coverage_item_ids"})
                else:
                    for sid in sci:
                        if not _nonempty(sid):
                            continue
                        if sid not in all_item_ids:
                            V.append({"rule": "G05:absence_id_not_exist",
                                       "path": be_loc, "msg": f"searched_coverage_item_ids 中 '{sid}' 不存在"})
                        elif all_item_ids[sid].get("status") != "checked":
                            V.append({"rule": "G05:absence_id_not_checked",
                                       "path": be_loc, "msg": f"'{sid}' 未被 checked"})
                        elif _nonempty(be_fid) and all_item_ids[sid].get("file_id") != be_fid:
                            V.append({"rule": "G05:absence_id_file_mismatch",
                                       "path": be_loc, "msg": f"'{sid}' file_id 不属于当前文件"})

        # ======================== C1: requirement_refs source role + location ========================
        for r in (_is_list(f.get("requirement_refs")) or []):
            if not isinstance(r, dict):
                continue
            rid = r.get("requirement_id")
            if _nonempty(rid) and rid not in req_index:
                V.append({"rule": "G04:ref_unresolved",
                           "path": f"{loc}.requirement_refs",
                           "msg": f"requirement_id '{rid}' 不存在"})
            if _nonempty(rid) and rid in req_index:
                req_src = req_index[rid].get("source_file_id")  # always from requirements
                # C1: ALWAYS check source role via req_src, not optional ref.file_id
                if _nonempty(req_src) and req_src in file_ids:
                    src_role = file_role.get(req_src)
                    if src_role == "bid_document":
                        V.append({"rule": "G04:ref_bid_role",
                                   "path": f"{loc}.requirement_refs",
                                   "msg": f"条款 '{rid}' source='{req_src}' 是 bid_document，不能作为招标要求来源"})
                # optional ref.file_id consistency (if provided)
                ref_fid = r.get("file_id")
                if _nonempty(ref_fid) and _nonempty(req_src) and ref_fid != req_src:
                    V.append({"rule": "G04:ref_source_mismatch",
                               "path": f"{loc}.requirement_refs",
                               "msg": f"ref file_id='{ref_fid}' ≠ req source='{req_src}' for '{rid}'"})
                # Resolve canonical clause position; an optional ref may narrow it.
                clause_value = req_index[rid].get("location")
                ref_value = r.get("location")
                clause_location = located(clause_value, req_src, f"requirements({rid}).location") if _nonempty(clause_value) else None
                if _nonempty(ref_value):
                    ref_location = located(ref_value, req_src, f"{loc}.requirement_refs.location", require_checked=True)
                    if clause_location is not None and ref_location is not None and not _location_contains(clause_location, ref_location):
                        V.append({"rule": "G05:requirement_location_mismatch",
                                  "path": f"{loc}.requirement_refs.location",
                                  "msg": "引用位置不在其条款来源位置/范围内"})
                else:
                    located(clause_value, req_src, f"{loc}.requirement_refs.location", require_checked=True)
        # supersede in findings context (image_evidence file refs)
        for img in (_is_list(f.get("image_evidence")) or []):
            if isinstance(img, dict):
                fid = img.get("file_id")
                if _nonempty(fid) and fid not in file_ids:
                    V.append({"rule": "G04:img_file_unresolved",
                               "path": f"{loc}.image_evidence",
                               "msg": f"file_id '{fid}' 不存在"})

    # ======================== G04: coverage item file resolution ========================
    for item in cov_items:
        fid = item.get("file_id")
        if _nonempty(fid) and fid not in file_ids:
            V.append({"rule": "G04:coverage_file_unresolved",
                       "path": f"coverage({item.get('item_id')}).file_id",
                       "msg": f"覆盖项引用文件 '{fid}' 不存在"})

    # ======================== G04: supersede cycle (unified graph) ========================
    if requirements:
        edges = {}
        matrix_edges = set()
        relation_edges = set()
        # Edges from requirements[].superseded_by
        for e in (reqs or []):
            if not isinstance(e, dict):
                continue
            rid = e.get("requirement_id", "")
            sup = e.get("superseded_by")
            if _nonempty(rid) and _nonempty(sup):
                matrix_edges.add((rid, sup))
                edges[rid] = sup
            elif sup is not None:
                V.append({"rule": "G04:supersede_invalid_edge",
                           "path": "requirements.requirements",
                           "msg": "非空替代声明必须提供有效的源和目标条款ID"})
        # Edges from requirements.supersede_relations
        sup_list = _is_list(requirements.get("supersede_relations"))
        if sup_list is not None:
            for rel in sup_list:
                if not isinstance(rel, dict):
                    continue
                o = rel.get("original_requirement_id", "")
                n = rel.get("superseding_requirement_id", "")
                if _nonempty(o) and _nonempty(n):
                    relation_edges.add((o, n))
                    if o in edges and edges[o] != n:
                        V.append({"rule": "G04:supersede_conflict",
                                   "path": "requirements",
                                   "msg": f"'{o}' 的 superseded_by='{edges[o]}' 与 supersede_relations 冲突"})
                    edges[o] = n
                else:
                    V.append({"rule": "G04:supersede_invalid_edge",
                               "path": "requirements.supersede_relations",
                               "msg": "替代关系必须提供非空的源和目标条款ID"})
        # Compare directed endpoint sets before validating the unified graph.
        # Neither representation may silently supply a missing edge for the other.
        if matrix_edges != relation_edges:
            V.append({"rule": "G04:supersede_representation_mismatch",
                       "path": "requirements",
                       "msg": "superseded_by 与 supersede_relations 的有向端点集合必须一致"})
        # C2: every edge endpoint must be a real requirement_id
        for o, n in edges.items():
            if o not in req_index:
                V.append({"rule": "G04:supersede_endpoint_missing",
                           "path": "requirements",
                           "msg": f"supersede 源 '{o}' 不在条款矩阵中"})
            if n not in req_index:
                V.append({"rule": "G04:supersede_endpoint_missing",
                           "path": "requirements",
                           "msg": f"supersede 目标 '{n}' 不在条款矩阵中"})
        # Cycle detection
        for start in edges:
            seen = set()
            cur = start
            while cur in edges:
                if cur in seen:
                    V.append({"rule": "G04:supersede_cycle",
                               "path": "requirements",
                               "msg": f"supersede 循环从 '{start}'"})
                    break
                seen.add(cur)
                cur = edges[cur]

    # Apply the same physical-page parser to the coverage ledger itself.
    # Method-only coverage remains legal; it cannot support located evidence.
    for item in cov_items:
        if _nonempty(item.get("location")):
            located(item["location"], item.get("file_id"), f"coverage({item.get('item_id')}).location")

    # ======================== G06: manifest_id binding ========================
    report_mid = None
    if report:
        iv = _is_dict(report.get("inputs_version"))
        if iv and _nonempty(iv.get("manifest_id")):
            report_mid = iv["manifest_id"]
        elif iv is not None:
            # report present but manifest_id missing/null
            V.append({"rule": "G06:report_manifest_id_missing",
                       "path": "review-report.inputs_version.manifest_id",
                       "msg": "manifest_id 必填且非 null"})
    manifest_mid = None
    if manifest:
        if _nonempty(manifest.get("manifest_id")):
            manifest_mid = manifest["manifest_id"]
        else:
            V.append({"rule": "G06:manifest_id_missing",
                       "path": "file-manifest.manifest_id",
                       "msg": "manifest_id 必填且非 null"})
    if report_mid and manifest_mid and report_mid != manifest_mid:
        V.append({"rule": "G06:manifest_id_mismatch",
                   "path": "inputs_version.manifest_id",
                   "msg": f"report={report_mid} ≠ manifest={manifest_mid}"})
    for art_name in MANIFEST_FIELDS:
        art = pack.get(art_name)
        if art is None:
            continue
        mid = art.get("manifest_id")
        if mid is not None and report_mid is not None and mid != report_mid:
            V.append({"rule": "G06:manifest_binding",
                       "path": f"{art_name}.manifest_id",
                       "msg": f"{art_name}={mid} ≠ report={report_mid}"})

    # ======================== D: R6 observation_method (all findings) ========================
    if findings:
        for f in findings_list:
            om = f.get("observation_method")
            if not _nonempty(om):
                V.append({"rule": "D:R6:observation_method_empty",
                           "path": f"findings({f.get('issue_id')}).observation_method",
                           "msg": "observation_method 缺失或空白"})

    # ======================== D: R5 + R6 review traceability ========================
    if findings:
        for f in findings_list:
            rs = f.get("review_status")
            # R5: without --review-pack, author must not self-claim reviewed
            if not is_review_pack and _nonempty(rs) and rs.startswith("reviewed"):
                V.append({"rule": "D:R5:author_self_review",
                           "path": f"findings({f.get('issue_id')}).review_status",
                           "msg": f"无 --review-pack 时作者不得自标 '{rs}'"})
            # D: reviewed_downgraded/withdrawn must have traceable reason
            if rs in ("reviewed_withdrawn", "reviewed_downgraded"):
                # Check findings[].limitations for reason (legal schema field)
                lims = _is_list(f.get("limitations"))
                if not lims or not any(_nonempty(l) for l in lims):
                    # Also check report.review_summary.notes for exact issue-linked reason
                    has_note = False
                    if report:
                        rs_summary = _is_dict(report.get("review_summary"))
                        if rs_summary:
                            notes_raw = rs_summary.get("notes")
                            if _nonempty(notes_raw):
                                fid = f.get("issue_id", "")
                                # D: exact issue ID match in notes entries
                                # Match patterns like "I1: reason" or "[I1] reason" — NOT "I10" for "I1"
                                if _nonempty(fid):
                                    # Split on common separators and check each entry
                                    import re as _re
                                    for entry in _re.split(r"[;\n]+", str(notes_raw)):
                                        entry = entry.strip()
                                        if not entry:
                                            continue
                                        # Match "ID: ..." or "[ID] ..." at start
                                        m = _re.match(r"^[\[\(]?\s*" + _re.escape(fid) + r"\s*[\]\)]?\s*[:\-]", entry)
                                        if m and _nonempty(entry[m.end():]):
                                            has_note = True
                                            break
                    if not has_note:
                        V.append({"rule": "D:R5:withdraw_no_reason",
                                   "path": f"findings({f.get('issue_id')})",
                                   "msg": "reviewed_downgraded/withdrawn 缺少可追溯理由（findings.limitations 或 report.review_summary.notes）"})

    # ======================== D: SHA256 strict fullmatch ========================
    if manifest:
        for e in (_is_list(manifest.get("files")) or []):
            if not isinstance(e, dict):
                continue
            sha = e.get("sha256")
            if _nonempty(sha) and not re.fullmatch(r"[a-f0-9]{64}", sha):
                V.append({"rule": "D:sha256_not_64hex",
                           "path": f"file-manifest({e.get('file_id')}).sha256",
                           "msg": f"sha256 非严格 64 位 hex (len={len(sha)})"})

    # ======================== G07: path validation ========================
    if manifest:
        for e in (_is_list(manifest.get("files")) or []):
            if not isinstance(e, dict):
                continue
            rp = e.get("relative_path")
            reason = _check_path(rp)
            if reason:
                V.append({"rule": "G07:path_invalid",
                           "path": f"file-manifest({e.get('file_id')}).relative_path",
                           "msg": f"路径不合法：{reason} (值={rp!r})"})

    return V


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main(argv=None):
    parser = argparse.ArgumentParser(description="标书报告数据包校验器（契约 v1.2）")
    parser.add_argument("--pack", required=True, help="数据包目录")
    parser.add_argument("--schemas", required=True, help="契约 Schema 目录")
    parser.add_argument("--review-pack", action="store_true", help="复核产物模式")
    parser.add_argument("--final-admission", action="store_true",
                        help="(deprecated) accepted for CLI compat; does not relax any rules")
    parser.add_argument("--json", action="store_true", help="JSON 输出")
    args = parser.parse_args(argv)

    violations = []

    if not os.path.isdir(args.pack):
        print(json.dumps({"error": f"pack not found: {args.pack}"}), file=sys.stderr)
        return 2
    if not os.path.isdir(args.schemas):
        print(json.dumps({"error": f"schemas not found: {args.schemas}"}), file=sys.stderr)
        return 2

    # --- Structural layer via schema_runtime ---
    try:
        contracts = load_contracts(args.schemas)
    except Exception as exc:
        return _fail({"error": f"schema load failed: {exc}"}, args.json)

    identity_ok = {}
    identity_violations = []
    for name, schema in contracts.items():
        identity_ok[name] = check_contract_identity(name, schema)
        if not identity_ok[name]:
            identity_violations.append({"rule": "G01:identity_failed",
                                        "path": f"schemas/{name}",
                                        "msg": f"产品契约身份/版本校验失败"})
    if identity_violations:
        violations.extend(identity_violations)

    # Load pack
    pack, states = load_pack(args.pack)

    present = [n for n, s in states.items() if s == "object"]
    absent = [n for n, s in states.items() if s == "absent"]
    nonvalid = [n for n, s in states.items() if s in ("parse_error", "null")]

    if not present and not nonvalid:
        violations.append({"rule": "pack:empty", "path": "(pack)",
                           "msg": "数据包无任何已知产物"})

    # G01: null/parse_error artifacts
    for name in nonvalid:
        violations.append({"rule": f"G01:artifact_{states[name]}",
                           "path": f"{name}.json",
                           "msg": f"产物 {name} 状态={states[name]}"})

    # G01: absent artifacts must be violations
    for name in absent:
        violations.append({"rule": "G01:artifact_absent",
                           "path": f"{name}.json",
                           "msg": f"产物 {name} 缺失"})

    # Structural validation via schema_runtime
    schema_errors = {}
    for name in CONTRACT_NAMES:
        if states[name] == "object" and pack[name] is not None:
            res = validate_payload(name, contracts[name], pack[name])
            if not res["valid"]:
                schema_errors[name] = res["errors"]

    if schema_errors:
        for name, errs in schema_errors.items():
            for err in errs:
                violations.append({"rule": f"schema:{name}:draft07",
                                   "path": f"{name}: {err}", "msg": err})
        # 结构层拒绝：不进入check_business
        result = {
            "pack": os.path.basename(os.path.normpath(args.pack)),
            "contract_version": "v1.2",
            "identity_ok": identity_ok,
            "artifact_states": states,
            "artifacts_present": present,
            "artifacts_missing": absent,
            "artifacts_invalid": nonvalid,
            "schema_errors": schema_errors,
            "violation_count": len(violations),
            "violations": violations,
            "result": "fail",
        }
        return _output(result, args.json, True)
    # 仅无schema错误时才进业务
    biz = check_business(pack, states, args.review_pack)
    violations.extend(biz)

    result = {
        "pack": os.path.basename(os.path.normpath(args.pack)),
        "contract_version": "v1.2",
        "identity_ok": identity_ok,
        "artifact_states": states,
        "artifacts_present": present,
        "artifacts_missing": absent,
        "artifacts_invalid": nonvalid,
        "schema_errors": schema_errors,
        "violation_count": len(violations),
        "violations": violations,
        "result": "pass" if not violations else "fail",
    }
    return _output(result, args.json, bool(violations))


def _fail(result, as_json):
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("FAIL: " + result.get("msg", result.get("error", "")), file=sys.stderr)
    return 1


def _output(result, as_json, has_violations):
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        tag = result["result"].upper()
        print(f"=== {tag} === pack={result['pack']} "
              f"violations={result['violation_count']}")
        for v in result["violations"]:
            print(f"  [{v['rule']}] {v['path']}: {v['msg']}")
    return 1 if has_violations else 0


if __name__ == "__main__":
    sys.exit(main())
