#!/usr/bin/env python3
"""商品核价统一 CLI：Excel 分析、清洗、批量同步核价与报告（Python 3.11 标准库）。"""

from __future__ import annotations

import json
import math
import os
import posixpath
import re
import subprocess
import sys
import tempfile
import time
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable
from xml.etree import ElementTree as ET


class SkillError(Exception):
    pass


def trim_text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def local_name(name: str) -> str:
    return name.rsplit("}", 1)[-1].rsplit(":", 1)[-1]


def attr_local(element: ET.Element, name: str) -> str | None:
    for key, value in element.attrib.items():
        if local_name(key) == name:
            return value
    return None


def child_text(element: ET.Element, name: str) -> str | None:
    for child in element:
        if local_name(child.tag) == name:
            return child.text or ""
    return None


def col_ref_to_num(ref: str) -> int:
    match = re.match(r"^([A-Za-z]+)", ref or "")
    if not match:
        return 0
    result = 0
    for char in match.group(1).upper():
        result = result * 26 + ord(char) - ord("A") + 1
    return result


def num_to_col_ref(number: int) -> str:
    result = ""
    while number > 0:
        number, remainder = divmod(number - 1, 26)
        result = chr(ord("A") + remainder) + result
    return result


def normalize_relationship_target(target: str) -> str:
    target = target.replace("\\", "/")
    if target.startswith("/xl/"):
        return posixpath.normpath(target[1:])
    if target.startswith("xl/"):
        return posixpath.normpath(target)
    return posixpath.normpath(posixpath.join("xl", target.lstrip("/")))


@dataclass(frozen=True)
class Sheet:
    name: str
    path: str
    state: str


@dataclass(frozen=True)
class RowRecord:
    row_num: int
    cells: list[str]


class XlsxDocument:
    def __init__(self, path: str):
        source = Path(path)
        if not source.is_file():
            raise SkillError(f"文件不存在: {path}")
        try:
            self.archive = zipfile.ZipFile(source, "r")
        except (OSError, zipfile.BadZipFile):
            raise SkillError(f"无法读取 xlsx（可能不是有效的 .xlsx 文件）: {path}") from None

        try:
            workbook = self._read_xml("xl/workbook.xml")
        except KeyError:
            self.archive.close()
            raise SkillError("缺少 xl/workbook.xml，可能是 .xls 旧格式，请另存为 .xlsx") from None
        except ET.ParseError:
            self.archive.close()
            raise SkillError(f"无法读取 xlsx（可能不是有效的 .xlsx 文件）: {path}") from None

        relations: dict[str, str] = {}
        try:
            rel_root = self._read_xml("xl/_rels/workbook.xml.rels")
        except KeyError:
            rel_root = None
        except ET.ParseError:
            self.archive.close()
            raise SkillError(f"无法读取 xlsx（可能不是有效的 .xlsx 文件）: {path}") from None
        if rel_root is not None:
            for relation in rel_root.iter():
                if local_name(relation.tag) != "Relationship":
                    continue
                relation_id = relation.attrib.get("Id")
                target = relation.attrib.get("Target")
                if relation_id and target:
                    relations[relation_id] = normalize_relationship_target(target)

        sheet_defs: list[tuple[str, str, str]] = []
        for element in workbook.iter():
            if local_name(element.tag) != "sheet":
                continue
            name = element.attrib.get("name")
            if name is None:
                continue
            relation_id = attr_local(element, "id") or ""
            state = (element.attrib.get("state") or "visible").lower()
            sheet_defs.append((name, relation_id, state))

        self.sheets: list[Sheet] = []
        for index, (name, relation_id, state) in enumerate(sheet_defs, start=1):
            sheet_path = relations.get(relation_id, f"xl/worksheets/sheet{index}.xml")
            if not sheet_path.startswith("xl/"):
                sheet_path = f"xl/{sheet_path}"
            self.sheets.append(Sheet(name=name, path=sheet_path, state=state))

        self.shared: list[str] = []
        try:
            shared_root = self._read_xml("xl/sharedStrings.xml")
        except KeyError:
            shared_root = None
        except ET.ParseError:
            self.archive.close()
            raise SkillError(f"无法读取 xlsx（可能不是有效的 .xlsx 文件）: {path}") from None
        if shared_root is not None:
            for item in shared_root.iter():
                if local_name(item.tag) != "si":
                    continue
                self.shared.append(
                    "".join(
                        node.text or ""
                        for node in item.iter()
                        if local_name(node.tag) == "t"
                    )
                )

    def _read_xml(self, name: str) -> ET.Element:
        return ET.fromstring(self.archive.read(name))

    def close(self) -> None:
        self.archive.close()

    def __enter__(self) -> "XlsxDocument":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def read_sheet_records(self, sheet_path: str) -> list[RowRecord]:
        try:
            root = self._read_xml(sheet_path)
        except (KeyError, ET.ParseError):
            raise SkillError(f"无法读取工作表: {sheet_path}") from None

        records: list[RowRecord] = []
        sequential_row = 0
        for row in root.iter():
            if local_name(row.tag) != "row":
                continue
            raw_row_num = row.attrib.get("r", "")
            row_num = int(raw_row_num) if raw_row_num.isdigit() else sequential_row + 1
            sequential_row = row_num
            cells: list[str] = []
            expected_col = 1
            for cell in row:
                if local_name(cell.tag) != "c":
                    continue
                ref = cell.attrib.get("r", "")
                cell_type = cell.attrib.get("t", "")
                col_num = col_ref_to_num(ref) if ref else expected_col
                while expected_col < col_num:
                    cells.append("")
                    expected_col += 1

                value = ""
                if cell_type == "s":
                    raw_value = child_text(cell, "v")
                    if raw_value not in (None, ""):
                        try:
                            value = self.shared[int(raw_value)]
                        except (ValueError, IndexError):
                            value = ""
                elif cell_type == "inlineStr":
                    value = "".join(
                        node.text or ""
                        for node in cell.iter()
                        if local_name(node.tag) == "t"
                    )
                else:
                    value = child_text(cell, "v") or ""
                value = re.sub(r"[\t\r\n]", " ", value)
                cells.append(value)
                expected_col = col_num + 1
            records.append(RowRecord(row_num=row_num, cells=cells))
        return records


ITEM_PATTERNS = (
    "商品id", "商品编号", "商品编码", "产品id", "产品编号", "宝贝id", "宝贝编号",
    "itemid", "itemno", "productid", "productno",
)
SKU_PATTERNS = ("skuid", "sku编号", "sku编码", "规格id", "规格编号", "规格编码")
COST_KEYWORDS = ("成本", "进货", "采购", "供货", "结算", "cost", "purchase")
PRICE_POSITIVE = (
    "一口价", "日常价", "活动价", "核验价", "本地价", "售价", "标价", "原价", "现价",
    "券后价", "到手价", "促销价", "价格", "单价", "总价", "price", "amount", "金额",
)
PRICE_NEGATIVE = (
    "库存", "销量", "数量", "件数", "折扣率", "折扣比例", "比例", "比率", "毛利率",
    "利润率", "税率", "评价", "运费", "日期", "时间", "重量", "容量", "id", "sku",
    "编号", "货号", "型号", "规格描述", "颜色", "款式", "类目", "品牌", "链接", "图片", "状态",
)


def normalize_col_name(name: Any) -> str:
    value = trim_text(name).lower()
    value = re.sub(r"[\s_\-]+", "", value)
    return re.sub(r"[（）()\[\]【】]", "", value)


def contains_pattern(name: str, patterns: Iterable[str]) -> bool:
    return any(pattern in name for pattern in patterns)


def is_item_name(name: Any) -> bool:
    normalized = normalize_col_name(name)
    return not contains_pattern(normalized, SKU_PATTERNS) and contains_pattern(normalized, ITEM_PATTERNS)


def is_sku_name(name: Any) -> bool:
    return contains_pattern(normalize_col_name(name), SKU_PATTERNS)


def is_cost_name(name: Any) -> bool:
    return contains_pattern(normalize_col_name(name), COST_KEYWORDS)


def is_price_name(name: Any) -> bool:
    normalized = normalize_col_name(name)
    if is_cost_name(name) or contains_pattern(normalized, PRICE_NEGATIVE):
        return False
    return contains_pattern(normalized, PRICE_POSITIVE) or normalized.endswith("价")


def first_nonempty(values: Iterable[str], limit: int = 20) -> list[str]:
    result: list[str] = []
    for value in values:
        if value != "":
            result.append(value)
            if len(result) == limit:
                break
    return result


def is_numeric_long(values: Iterable[str]) -> bool:
    sample = first_nonempty(values)
    if not sample:
        return False
    count = sum(bool(re.fullmatch(r"\d{6,}", value)) for value in sample)
    return count / len(sample) >= 0.7


def is_price_like_value(value: Any) -> bool:
    normalized = trim_text(value)
    if not normalized or "%" in normalized:
        return False
    normalized = re.sub(r"^[¥￥$]\s*", "", normalized)
    normalized = re.sub(r"\s*(?:元|人民币)$", "", normalized)
    normalized = normalized.replace(",", "")
    match = re.fullmatch(r"\((.+)\)", normalized)
    if match:
        normalized = f"-{match.group(1)}"
    return bool(re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?", normalized))


def is_price_col(name: Any, values: Iterable[str]) -> bool:
    if not is_price_name(name):
        return False
    sample = first_nonempty(values)
    if not sample:
        return True
    return sum(is_price_like_value(value) for value in sample) / len(sample) >= 0.6


def is_sku_price_name(name: Any) -> bool:
    normalized = normalize_col_name(name)
    return "sku" in normalized and (
        contains_pattern(normalized, PRICE_POSITIVE) or "price" in normalized
    )


def is_any_price_col(detail: dict[str, Any], values: Iterable[str]) -> bool:
    name = detail.get("name") or ""
    key = detail.get("technical_key") or ""
    values = list(values)
    if is_price_col(name, values) or (key and is_price_col(key, values)):
        return True
    if is_sku_price_name(name) or is_sku_price_name(key):
        sample = first_nonempty(values)
        if not sample:
            return True
        return sum(is_price_like_value(value) for value in sample) / len(sample) >= 0.6
    return False


def identify_fields(details: list[dict[str, Any]], rows: list[list[str]]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "item_id": None,
        "sku_id": None,
        "price_candidates": [],
        "cost": None,
        "item_price": None,
        "sku_price": None,
        "price_mode": "single",
    }
    column_values = {
        index: [row[index] if index < len(row) else "" for row in rows]
        for index in range(len(details))
    }

    for index, detail in enumerate(details):
        name = detail.get("name") or ""
        key = detail.get("technical_key") or ""
        probe = " ".join(value for value in (name, key) if value)
        normalized_key = normalize_col_name(key)
        if result["item_id"] is None:
            if is_item_name(probe):
                result["item_id"] = detail["selector"]
            elif (
                (normalized_key == "id" or normalize_col_name(name).endswith("id"))
                and not is_sku_name(probe)
                and is_numeric_long(column_values[index])
            ):
                result["item_id"] = detail["selector"]

    for detail in details:
        if detail["selector"] == result["item_id"]:
            continue
        probe = " ".join(
            value for value in (detail.get("name") or "", detail.get("technical_key") or "") if value
        )
        if result["sku_id"] is None and is_sku_name(probe):
            result["sku_id"] = detail["selector"]

    for detail in details:
        probe = " ".join(
            value for value in (detail.get("name") or "", detail.get("technical_key") or "") if value
        )
        if result["cost"] is None and is_cost_name(probe):
            result["cost"] = detail["selector"]

    excluded = {value for value in (result["item_id"], result["sku_id"], result["cost"]) if value}
    for index, detail in enumerate(details):
        selector = detail["selector"]
        if selector in excluded or not is_any_price_col(detail, column_values[index]):
            continue
        result["price_candidates"].append(selector)
        sku_role = is_sku_price_name(detail.get("name") or "") or is_sku_price_name(
            detail.get("technical_key") or ""
        )
        role = "sku_price" if sku_role else "item_price"
        if result[role] is None:
            result[role] = selector
    if result["item_price"] is not None and result["sku_price"] is not None:
        result["price_mode"] = "item_sku"
    return result


def duplicate_headers(header: list[str]) -> list[str]:
    seen: set[str] = set()
    duplicate: set[str] = set()
    for value in header:
        name = trim_text(value)
        if not name:
            continue
        if name in seen:
            duplicate.add(name)
        seen.add(name)
    return sorted(duplicate)


def header_score(cells: list[str]) -> float | None:
    nonempty = [value for value in cells if trim_text(value)]
    if not nonempty:
        return None
    score = min(len(nonempty), 8)
    text_count = sum(bool(re.search(r"[A-Za-z\u4e00-\u9fff]", value)) for value in nonempty)
    score += min(text_count, 6) * 0.5
    for name in nonempty:
        if is_item_name(name):
            score += 8
        if is_sku_name(name):
            score += 8
        if is_price_name(name):
            score += 4
        if is_cost_name(name):
            score += 2
    score -= 10 * len(duplicate_headers(cells))
    return score


def detect_header_record(records: list[RowRecord], override: Any = None) -> RowRecord | None:
    if override not in (None, ""):
        raw = str(override)
        if not re.fullmatch(r"\d+", raw) or int(raw) <= 0:
            raise SkillError("header_row 必须是正整数")
        row_num = int(raw)
        for record in records:
            if record.row_num != row_num:
                continue
            if not any(trim_text(value) for value in record.cells):
                raise SkillError(f"指定的表头行为空: 第 {row_num} 行")
            return record
        raise SkillError(f"指定的表头行不存在: 第 {row_num} 行")

    best: RowRecord | None = None
    best_score: float | None = None
    for record in records:
        if record.row_num > 50:
            continue
        score = header_score(record.cells)
        if score is not None and (best is None or score > best_score):
            best = record
            best_score = score
    return best


def is_visible_business_sheet(sheet: Sheet) -> bool:
    return sheet.state == "visible" and not sheet.name.lower().endswith("_hide")


def visible_sheets(document: XlsxDocument) -> list[Sheet]:
    return [sheet for sheet in document.sheets if is_visible_business_sheet(sheet)]


def find_companion_sheet(document: XlsxDocument, target: Sheet) -> Sheet | None:
    expected = f"{target.name}_hide".lower()
    matches = [
        sheet
        for sheet in document.sheets
        if not is_visible_business_sheet(sheet) and sheet.name.lower() == expected
    ]
    if len(matches) > 1:
        raise SkillError(f"工作表「{target.name}」存在多个同名隐藏字段字典")
    return matches[0] if matches else None


def build_column_details(
    document: XlsxDocument, target: Sheet, header_record: RowRecord
) -> tuple[list[dict[str, Any]], str | None]:
    companion = find_companion_sheet(document, target)
    key_record: RowRecord | None = None
    if companion:
        companion_records = document.read_sheet_records(companion.path)
        key_record = next(
            (record for record in companion_records if record.row_num == header_record.row_num),
            None,
        )
        if key_record and sum(bool(trim_text(value)) for value in key_record.cells) < 2:
            key_record = None
        if key_record is None:
            key_record = detect_header_record(companion_records)
        if key_record and sum(bool(trim_text(value)) for value in key_record.cells) < 2:
            key_record = None

    details: list[dict[str, Any]] = []
    for index, raw_name in enumerate(header_record.cells, start=1):
        ref = num_to_col_ref(index)
        name = trim_text(raw_name)
        key = trim_text(key_record.cells[index - 1]) if key_record and index <= len(key_record.cells) else ""
        label = f"{ref}: {name or '(空表头)'}"
        if key:
            label += f" [{key}]"
        details.append(
            {
                "index": index,
                "ref": ref,
                "selector": f"col:{ref}",
                "name": name,
                "technical_key": key,
                "label": label,
            }
        )
    return details, companion.name if key_record and companion else None


def classify_duplicate_headers(
    header: list[str], details: list[dict[str, Any]]
) -> tuple[list[str], list[str], list[str]]:
    positions: dict[str, list[int]] = {}
    for index, value in enumerate(header):
        name = trim_text(value)
        if name:
            positions.setdefault(name, []).append(index)
    all_duplicates: list[str] = []
    resolved: list[str] = []
    unresolved: list[str] = []
    for name in sorted(positions):
        indexes = positions[name]
        if len(indexes) <= 1:
            continue
        all_duplicates.append(name)
        keys: set[str] = set()
        is_resolved = True
        for index in indexes:
            key = trim_text(details[index].get("technical_key"))
            normalized = key.lower()
            if not key or normalized in keys:
                is_resolved = False
                break
            keys.add(normalized)
        (resolved if is_resolved else unresolved).append(name)
    return all_duplicates, resolved, unresolved


def duplicate_technical_keys(details: list[dict[str, Any]]) -> list[str]:
    first: dict[str, str] = {}
    seen: set[str] = set()
    duplicate: set[str] = set()
    for detail in details:
        key = trim_text(detail.get("technical_key"))
        if not key:
            continue
        normalized = key.lower()
        first.setdefault(normalized, key)
        if normalized in seen:
            duplicate.add(normalized)
        seen.add(normalized)
    return [first[key] for key in sorted(duplicate)]


ROLE_FLAGS = {
    "商品ID": "--item-id",
    "SKU ID": "--sku-id",
    "价格": "--price",
    "商品价格": "--item-price",
    "SKU 价格": "--sku-price",
    "成本价": "--cost",
}


def resolve_column_index(details: list[dict[str, Any]], selector: Any, role: str) -> int:
    query = trim_text(selector)
    if not query:
        flag = ROLE_FLAGS.get(role)
        if flag:
            raise SkillError(
                f"{role} 未指定：请通过 {flag} 传入列选择器（如 {flag} col:A），"
                f"注意参数名是 {flag}，不要写成 {flag}-col 等变体"
            )
        raise SkillError(f"{role} 未指定")
    match = re.fullmatch(r"col:([A-Za-z]+)", query, re.IGNORECASE)
    if match:
        ref = match.group(1).upper()
        matched = [detail for detail in details if detail["ref"] == ref]
        if len(matched) != 1:
            raise SkillError(f"{role} 列不存在: {selector}")
        return matched[0]["index"] - 1

    by_key = [
        detail
        for detail in details
        if trim_text(detail.get("technical_key"))
        and trim_text(detail.get("technical_key")).lower() == query.lower()
    ]
    if len(by_key) > 1:
        raise SkillError(f"{role} 机器字段不唯一: {selector}")
    if len(by_key) == 1:
        return by_key[0]["index"] - 1

    by_name = [detail for detail in details if trim_text(detail.get("name")) == query]
    if len(by_name) > 1:
        refs = "、".join(f"col:{detail['ref']}" for detail in by_name)
        raise SkillError(f"{role} 列名不唯一: {selector}（请使用列选择器 {refs} 中的一个）")
    if len(by_name) == 1:
        return by_name[0]["index"] - 1

    if re.fullmatch(r"[A-Za-z]+", query):
        ref = query.upper()
        matched = [detail for detail in details if detail["ref"] == ref]
        if len(matched) == 1:
            return matched[0]["index"] - 1
    raise SkillError(f"{role} 列不存在: {selector}")


def xml_escape(value: Any) -> str:
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def write_xlsx(out_path: Path, rows: list[list[str]], force_text_cols: set[int]) -> None:
    column_count = max((len(row) for row in rows), default=0)
    sheet_parts = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>',
    ]
    numeric_pattern = re.compile(r"^-?\d+(?:\.\d+)?$")
    for row_num, row in enumerate(rows, start=1):
        sheet_parts.append(f'<row r="{row_num}">')
        for column_index in range(column_count):
            value = row[column_index] if column_index < len(row) and row[column_index] is not None else ""
            value = str(value)
            if value == "":
                continue
            ref = f"{num_to_col_ref(column_index + 1)}{row_num}"
            if column_index not in force_text_cols and numeric_pattern.fullmatch(value):
                sheet_parts.append(f'<c r="{ref}"><v>{value}</v></c>')
            else:
                sheet_parts.append(
                    f'<c r="{ref}" t="inlineStr"><is><t xml:space="preserve">'
                    f"{xml_escape(value)}</t></is></c>"
                )
        sheet_parts.append("</row>")
    sheet_parts.append("</sheetData></worksheet>")

    entries = {
        "[Content_Types].xml": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        "</Types>",
        "_rels/.rels": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
        "</Relationships>",
        "xl/workbook.xml": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets><sheet name="Sheet1" sheetId="1" r:id="rId1"/></sheets></workbook>',
        "xl/_rels/workbook.xml.rels": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
        "</Relationships>",
        "xl/worksheets/sheet1.xml": "".join(sheet_parts),
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    temp_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix=f".{out_path.stem}.", suffix=".tmp", dir=out_path.parent, delete=False
        ) as temp_file:
            temp_name = temp_file.name
        with zipfile.ZipFile(temp_name, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name, content in entries.items():
                archive.writestr(name, content.encode("utf-8"))
        os.replace(temp_name, out_path)
        temp_name = None
    except OSError as exc:
        raise SkillError(f"写出 xlsx 失败: {out_path}") from exc
    finally:
        # 不可逆写操作守卫：下方 os.remove 是不可逆删除。此处仅清理本函数自身通过
        # tempfile 创建、且尚未 os.replace 转为正式产物的临时文件（temp_name），
        # 不触及用户输入文件或最终结果文件。因不是用户发起的不可逆删除，属于内部资源管理，
        # 依据 SKILL.md「全局硬约束」豁免二次确认，无需提示输入 YES / DELETE 再次确认。
        if temp_name:
            try:
                os.remove(temp_name)
            except OSError:
                pass


def analyze(file: str, sheet_name: Any = None, header_row_override: Any = None) -> dict[str, Any]:
    """分析 Excel 工作簿结构。

    入参:
        file: 本地 .xlsx/.xlsm 工作簿路径。
        sheet_name: 可选，指定要分析的 Sheet 名；缺省时返回可见业务 Sheet 列表。
        header_row_override: 可选，用户指定的表头行号覆盖自动探测结果。
    出参:
        dict，包含可见 Sheet 列表、表头行与列选项(selector)等结构信息。
    """
    with XlsxDocument(file) as document:
        if not document.sheets:
            raise SkillError("Excel 中未找到工作表")
        visible = visible_sheets(document)
        if not visible:
            raise SkillError("Excel 中未找到可见业务工作表")

        selected: str | None = None
        if trim_text(sheet_name):
            matched = next((sheet for sheet in document.sheets if sheet.name == sheet_name), None)
            if matched is None:
                raise SkillError(f"工作表不存在: {sheet_name}")
            if not is_visible_business_sheet(matched):
                raise SkillError(f"工作表「{sheet_name}」为隐藏技术 Sheet，禁止作为业务数据处理")
            selected = str(sheet_name)
        elif len(visible) == 1:
            selected = visible[0].name
        if header_row_override not in (None, "") and selected is None:
            raise SkillError("多个可见 Sheet 使用 --header-row 时必须同时指定 --sheet")

        sheets_info: list[dict[str, Any]] = []
        details: dict[str, dict[str, Any]] = {}
        for sheet in visible:
            records = document.read_sheet_records(sheet.path)
            override = header_row_override if selected == sheet.name else None
            header_record = detect_header_record(records, override)
            header = list(header_record.cells) if header_record else []
            data_count = 0
            if header_record:
                data_count = sum(
                    record.row_num > header_record.row_num
                    and any(trim_text(value) for value in record.cells)
                    for record in records
                )
            if header_record:
                column_details, companion_sheet = build_column_details(document, sheet, header_record)
            else:
                column_details = []
                companion_sheet = None
            all_duplicates, resolved, unresolved = classify_duplicate_headers(header, column_details)
            duplicate_keys = duplicate_technical_keys(column_details)
            info = {
                "name": sheet.name,
                "state": sheet.state,
                "selectable": sheet.state == "visible",
                "columns": header,
                "column_options": column_details,
                "header_row": header_record.row_num if header_record else None,
                "row_count": data_count,
                "duplicate_columns": all_duplicates,
                "resolved_duplicate_columns": resolved,
                "unresolved_duplicate_columns": unresolved,
                "duplicate_technical_keys": duplicate_keys,
                "companion_sheet": companion_sheet,
            }
            sheets_info.append(info)
            details[sheet.name] = {
                "records": records,
                "header": header_record,
                "info": info,
                "column_details": column_details,
            }

        identified = None
        detected_header_row = None
        if selected is not None:
            detail = details[selected]
            header_record = detail["header"]
            if header_record is None:
                raise SkillError(f"未能在工作表「{selected}」前 50 行识别表头")
            unresolved = detail["info"]["unresolved_duplicate_columns"]
            if unresolved:
                raise SkillError(
                    f"工作表「{selected}」表头存在无法由隐藏字段字典消歧的重复列名: "
                    + "、".join(unresolved)
                )
            duplicate_keys = detail["info"]["duplicate_technical_keys"]
            if duplicate_keys:
                raise SkillError(
                    f"工作表「{selected}」隐藏字段字典存在重复机器字段: "
                    + "、".join(duplicate_keys)
                )
            detected_header_row = header_record.row_num
            body = [
                record.cells
                for record in detail["records"]
                if record.row_num > detected_header_row
            ]
            identified = identify_fields(detail["column_details"], body)

        return {
            "file_path": file,
            "sheets": sheets_info,
            "visible_sheets": [sheet.name for sheet in visible],
            "selected_sheet": selected,
            "header_row": detected_header_row,
            "column_options": details[selected]["info"]["column_options"] if selected else None,
            "companion_sheet": details[selected]["info"]["companion_sheet"] if selected else None,
            "identified": identified,
        }


def clean(options: dict[str, Any]) -> dict[str, Any]:
    """清洗 Excel 生成固定四列的核价输入文件。

    入参:
        options: dict，含 file 工作簿路径、sheet 名、表头行、column selector 字段映射、
                 单价格或商品/SKU 双层价格模式等。
    出参:
        dict，包含清洗后固定四列文件路径及行数等统计信息。
    """
    file = str(options["file"])
    with XlsxDocument(file) as document:
        if not document.sheets:
            raise SkillError("Excel 中未找到工作表")
        visible = visible_sheets(document)
        if not visible:
            raise SkillError("Excel 中未找到可见业务工作表")

        raw_requested_sheet = options.get("sheet")
        requested_sheet = str(raw_requested_sheet) if trim_text(raw_requested_sheet) else ""
        if requested_sheet:
            target = next((sheet for sheet in document.sheets if sheet.name == requested_sheet), None)
            if target is None:
                raise SkillError(f"工作表不存在: {requested_sheet}")
            if not is_visible_business_sheet(target):
                raise SkillError(f"工作表「{requested_sheet}」为隐藏技术 Sheet，禁止作为业务数据清洗")
        else:
            if len(visible) > 1:
                raise SkillError("文件包含多个可见工作表，必须指定 --sheet")
            target = visible[0]

        records = document.read_sheet_records(target.path)
        if not records:
            raise SkillError("工作表为空")
        header_record = detect_header_record(records, options.get("header_row"))
        if header_record is None:
            raise SkillError(f"未能在工作表「{target.name}」前 50 行识别表头")
        column_details, companion_sheet = build_column_details(document, target, header_record)
        _, _, unresolved = classify_duplicate_headers(header_record.cells, column_details)
        if unresolved:
            raise SkillError(
                f"工作表「{target.name}」表头存在无法由隐藏字段字典消歧的重复列名: "
                + "、".join(unresolved)
            )
        duplicate_keys = duplicate_technical_keys(column_details)
        if duplicate_keys:
            raise SkillError(
                f"工作表「{target.name}」隐藏字段字典存在重复机器字段: "
                + "、".join(duplicate_keys)
            )

        item_index = resolve_column_index(column_details, options.get("item_id"), "商品ID")
        sku_index = resolve_column_index(column_details, options.get("sku_id"), "SKU ID")
        has_single = bool(trim_text(options.get("price")))
        has_item_price = bool(trim_text(options.get("item_price")))
        has_sku_price = bool(trim_text(options.get("sku_price")))
        if has_single and (has_item_price or has_sku_price):
            raise SkillError("价格映射冲突：--price 不能与 --item-price/--sku-price 同时使用")
        if has_single:
            price_mode = "single"
            price_index = resolve_column_index(column_details, options.get("price"), "价格")
            item_price_index = sku_price_index = None
        elif has_item_price and has_sku_price:
            price_mode = "item_sku"
            item_price_index = resolve_column_index(column_details, options.get("item_price"), "商品价格")
            sku_price_index = resolve_column_index(column_details, options.get("sku_price"), "SKU 价格")
            price_index = None
        else:
            raise SkillError("必须指定 --price，或同时指定 --item-price 与 --sku-price")

        cost_index = None
        if trim_text(options.get("cost")):
            cost_index = resolve_column_index(column_details, options.get("cost"), "成本价")

        mappings: list[tuple[str, int]] = [("商品ID", item_index), ("SKU ID", sku_index)]
        if price_mode == "single":
            mappings.append(("本地核验价", price_index))
        else:
            mappings.extend((("商品价格", item_price_index), ("SKU 价格", sku_price_index)))
        if cost_index is not None:
            mappings.append(("成本价", cost_index))
        used: dict[int, str] = {}
        for label, index in mappings:
            if index in used:
                raise SkillError(f"字段映射重复：{label} 与 {used[index]} 指向同一列")
            used[index] = label

        output_rows = [["商品ID", "SKU ID", "成本价", "本地核验价"]]
        item_rows = 0
        sku_rows = 0
        row_errors: list[str] = []
        for record in records:
            if record.row_num <= header_record.row_num or not any(value != "" for value in record.cells):
                continue
            row = record.cells
            cost_value = row[cost_index] if cost_index is not None and cost_index < len(row) else ""
            item_value = row[item_index] if item_index < len(row) else ""
            sku_value = row[sku_index] if sku_index < len(row) else ""
            if price_mode == "single":
                price_value = row[price_index] if price_index < len(row) else ""
                if trim_text(sku_value):
                    sku_rows += 1
                else:
                    item_rows += 1
            elif trim_text(sku_value):
                sku_rows += 1
                price_value = row[sku_price_index] if sku_price_index < len(row) else ""
                if not trim_text(price_value):
                    row_errors.append(f"第 {record.row_num} 行 SKU ID 有值但 SKU 价格为空")
            else:
                item_rows += 1
                sku_price_value = row[sku_price_index] if sku_price_index < len(row) else ""
                price_value = row[item_price_index] if item_price_index < len(row) else ""
                if trim_text(sku_price_value):
                    row_errors.append(f"第 {record.row_num} 行 SKU ID 为空但 SKU 价格有值")
                if not trim_text(price_value):
                    row_errors.append(f"第 {record.row_num} 行无 SKU 且商品价格为空")
            output_rows.append([item_value, sku_value, cost_value, price_value])

        if row_errors:
            raise SkillError("混合价格映射校验失败: " + "；".join(row_errors[:10]))

        out_dir = Path(str(options.get("outdir") or "."))
        output_name = f"清洗_{Path(file).stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        output_path = out_dir / output_name
        write_xlsx(output_path, output_rows, {0, 1})
        return {
            "output_path": str(output_path),
            "output_name": output_name,
            "row_count": len(output_rows) - 1,
            "columns": output_rows[0],
            "header_row": header_record.row_num,
            "price_mode": price_mode,
            "item_row_count": item_rows,
            "sku_row_count": sku_rows,
            "companion_sheet": companion_sheet,
        }


def report(file: str) -> dict[str, Any]:
    """解析核价结果 Excel 并汇总风险统计。

    入参:
        file: 云端返回并已落盘的核价结果 Excel 路径，须含“风险标注”列。
    出参:
        dict，包含 total、evaluated_count、excluded_count、各风险计数与占比、
        low_items/high_items/excluded_items 明细及其截断标记等，字段详见 SKILL.md「输出契约」。
    """
    with XlsxDocument(file) as document:
        if not document.sheets:
            raise SkillError("结果表为空")
        records = document.read_sheet_records(document.sheets[0].path)
        if not records:
            raise SkillError("结果表为空")
        header_record = detect_header_record(records)
        if header_record is None:
            raise SkillError("未能在结果表前 50 行识别表头")
        header = header_record.cells

        risk_index = next(
            (
                index
                for index, value in enumerate(header)
                if "风险" in value and "标注" in value
            ),
            None,
        )
        if risk_index is None:
            raise SkillError("结果表缺少风险标注列，禁止生成风险结论")

        field_patterns = {
            "name": ["商品名称", "商品标题", "宝贝名称", "标题"],
            "item": ["商品ID", "商品id", "ItemId"],
            "sku": ["SKU ID", "SKUID", "skuId", "SKU"],
            "local": ["本地核验价"],
            "cost": ["成本价"],
            "diff": ["差价"],
            "combo": ["优惠组合"],
            "remark": ["备注"],
        }
        labels = {
            "name": "商品名称",
            "item": "商品ID",
            "sku": "SKU ID",
            "local": "本地核验价",
            "cost": "成本价",
            "diff": "差价",
            "combo": "优惠组合",
            "remark": "备注",
        }
        field_indices: dict[str, int] = {}
        for key, patterns in field_patterns.items():
            for pattern in patterns:
                match = next(
                    (index for index, value in enumerate(header) if pattern in value),
                    None,
                )
                if match is not None:
                    field_indices[key] = match
                    break

        online_index = next(
            (
                index
                for index, value in enumerate(header)
                if value != "本地核验价"
                and re.search(r"标价|券后价|预估价|到手价", value)
            ),
            None,
        )

        total = evaluated = excluded = low = high = normal = 0
        low_items: list[dict[str, Any]] = []
        high_items: list[dict[str, Any]] = []
        excluded_items: list[dict[str, Any]] = []
        normal_markers = {"", "正常", "价格正常", "无风险"}
        numeric_pattern = re.compile(r"^-?\d+(?:\.\d+)?$")

        for record in records:
            if record.row_num <= header_record.row_num or not any(
                value != "" for value in record.cells
            ):
                continue
            row = record.cells
            total += 1
            risk_value = trim_text(row[risk_index] if risk_index < len(row) else "")

            info: dict[str, Any] = {}
            for key, label in labels.items():
                index = field_indices.get(key)
                if index is not None and index < len(row) and row[index] != "":
                    info[label] = row[index]
            if online_index is not None and online_index < len(row) and row[online_index] != "":
                info["线上价"] = row[online_index]
            local_value = info.get("本地核验价")
            difference_value = info.get("差价")
            if (
                local_value is not None
                and difference_value is not None
                and numeric_pattern.fullmatch(str(local_value))
                and numeric_pattern.fullmatch(str(difference_value))
                and float(local_value) != 0
            ):
                info["差价率"] = round(
                    float(difference_value) / float(local_value) * 100,
                    1,
                )

            remark_index = field_indices.get("remark")
            remark = trim_text(
                row[remark_index]
                if remark_index is not None and remark_index < len(row)
                else ""
            )
            if remark:
                excluded += 1
                excluded_items.append(info)
                continue

            evaluated += 1
            if risk_value == "价格过低":
                low += 1
                low_items.append(info)
            elif risk_value == "价格过高":
                high += 1
                high_items.append(info)
            elif risk_value in normal_markers:
                normal += 1
            else:
                raise SkillError(
                    f"结果表第 {record.row_num} 行包含未知风险标注「{risk_value}」，禁止生成风险结论"
                )

    def percentage(count: int, denominator: int) -> float | int:
        return round(count / denominator * 100, 1) if denominator else 0

    detail_limit = 50
    returned_low = low_items[:detail_limit]
    returned_high = high_items[:detail_limit]
    returned_excluded = excluded_items[:detail_limit]
    return {
        "total": total,
        "evaluated_count": evaluated,
        "excluded_count": excluded,
        "excluded_pct": percentage(excluded, total),
        "normal_count": normal,
        "normal_pct": percentage(normal, evaluated),
        "low_count": low,
        "low_pct": percentage(low, evaluated),
        "high_count": high,
        "high_pct": percentage(high, evaluated),
        "detail_limit": detail_limit,
        "low_items": returned_low,
        "low_items_returned": len(returned_low),
        "low_items_truncated": len(low_items) > detail_limit,
        "high_items": returned_high,
        "high_items_returned": len(returned_high),
        "high_items_truncated": len(high_items) > detail_limit,
        "excluded_items": returned_excluded,
        "excluded_items_returned": len(returned_excluded),
        "excluded_items_truncated": len(excluded_items) > detail_limit,
    }


SCENE_LABELS = {
    "bid_price": "标价",
    "predict_pmp": "普惠券后价",
    "risk_argus_predict_p": "一件预估价",
    "risk_health_upgrade": "预估最低到手价",
}

ATP_TOOL_CODE = "tool_78717bjpsy"
ATP_TOOL_VERSION = "0.0.2"


def invoke_atp(param0: dict[str, Any]) -> tuple[int, str, str]:
    """调用健康中心核价 ATP 工具，返回 (returncode, stdout, stderr)。

    入参:
        param0: 单批核价参数，含 applyTime/scene/thresholdType/lowThreshold/
                highThreshold 及 itemRequests 数组。
    出参:
        (returncode, stdout, stderr) 三元组，由 atp CLI 原样返回。
    """
    command = [
        "atp",
        "invoke",
        "--code",
        ATP_TOOL_CODE,
        "--version",
        ATP_TOOL_VERSION,
        "--params",
        json.dumps({"param0": param0}, ensure_ascii=False),
    ]
    completed = subprocess.run(command, capture_output=True, text=True)
    return completed.returncode, completed.stdout, completed.stderr


def build_item_request(row: dict[str, Any]) -> dict[str, Any]:
    """由清洗行构造 itemRequests 元素；skuId/costPrice 缺失时省略字段。

    入参:
        row: 含 itemId/skuId/costPrice/localPrice 字段的清洗行字典。
    出参:
        dict，符合 ATP itemRequests 元素结构。
    """
    request: dict[str, Any] = {"itemId": int(row["itemId"]), "localPrice": row["localPrice"]}
    if row["skuId"]:
        try:
            request["skuId"] = int(row["skuId"])
        except ValueError:
            request["skuId"] = row["skuId"]
    if row["costPrice"]:
        request["costPrice"] = row["costPrice"]
    return request


def normalize_risk_tag(raw: Any) -> str:
    """把 ATP 返回的 riskTag 归一到 report() 白名单：价格过低 / 价格过高 / 空（正常）。"""
    text = trim_text(raw)
    if "过低" in text:
        return "价格过低"
    if "过高" in text:
        return "价格过高"
    return ""


def unwrap_biz(response: Any) -> dict[str, Any]:
    """从 atp CLI 响应里剥出业务体。

    atp CLI 信封可能用 `data` 或 `result` 包裹，也可能直接就是业务体；
    这里递归尝试常见落法，避免硬编码某个键名。
    业务体判定：dict 且包含 `model` / `itemResponses` / `success` 中至少一个。
    """
    if not isinstance(response, dict):
        return {}

    def looks_like_biz(value: Any) -> bool:
        return isinstance(value, dict) and any(
            key in value for key in ("model", "itemResponses", "success")
        )

    for key in ("data", "result"):
        candidate = response.get(key)
        if looks_like_biz(candidate):
            return candidate
    if looks_like_biz(response):
        return response
    # 兜底：找不到明显业务体时返回顶层，交给上层判断 success
    return response


def read_cleaned_rows(file: str) -> list[dict[str, Any]]:
    """读取清洗后的四列文件（商品ID / SKU ID / 成本价 / 本地核验价）为行字典列表。

    入参:
        file: clean 子命令产出的 .xlsx 路径。
    出参:
        list[dict]，每项含 _rowIdx / _valid / itemId / skuId / costPrice / localPrice。
    """
    with XlsxDocument(file) as document:
        if not document.sheets:
            raise SkillError("清洗文件为空")
        records = document.read_sheet_records(document.sheets[0].path)
    if not records:
        raise SkillError("清洗文件为空")
    header_record = detect_header_record(records)
    if header_record is None:
        raise SkillError("未能在清洗文件前 50 行识别表头")
    header = header_record.cells

    def locate(target: str) -> int | None:
        for index, value in enumerate(header):
            if trim_text(value) == target:
                return index
        return None

    item_index = locate("商品ID")
    sku_index = locate("SKU ID")
    cost_index = locate("成本价")
    local_index = locate("本地核验价")
    if item_index is None or local_index is None:
        raise SkillError("清洗文件缺少必需列：商品ID 或 本地核验价")

    rows: list[dict[str, Any]] = []
    for record in records:
        if record.row_num <= header_record.row_num or not any(
            value != "" for value in record.cells
        ):
            continue
        cells = record.cells

        def cell(index: int | None) -> str:
            return trim_text(cells[index]) if index is not None and index < len(cells) else ""

        item_id = cell(item_index)
        local_price = cell(local_index)
        valid = bool(item_id) and bool(local_price) and bool(re.fullmatch(r"\d+", item_id))
        rows.append(
            {
                "_rowIdx": len(rows),
                "_valid": valid,
                "itemId": item_id,
                "skuId": cell(sku_index),
                "costPrice": cell(cost_index),
                "localPrice": local_price,
            }
        )
    return rows


def batch_check(options: dict[str, Any]) -> None:
    """读取清洗文件 → 分批同步调用 ATP 核价 → 落盘结果 xlsx → 汇总风险。

    进度以 JSON Lines 事件写入 stdout：parsed / batch / done；不可恢复错误抛
    SkillError（由主入口写 stderr 并以退出码 1 结束）。

    入参:
        options: dict，含 file 清洗文件、apply_time、scene、threshold_type、
                 low、high、outdir、batch_size、sleep。
    """
    file = str(options.get("file") or "")
    if not file:
        raise SkillError("缺少清洗文件路径")
    apply_time = trim_text(options.get("apply_time"))
    scene = trim_text(options.get("scene"))
    threshold_type = trim_text(options.get("threshold_type"))
    low = trim_text(options.get("low"))
    high = trim_text(options.get("high"))

    # apply-time 支持两种格式：yyyy-MM-dd（按天）或 yyyy-MM-dd HH:mm:ss（精确到秒）。
    # 用 strptime 逐一试解析，既校验格式也校验是否为真实日期时间。
    apply_time_ok = False
    for time_format in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            datetime.strptime(apply_time, time_format)
            apply_time_ok = True
            break
        except ValueError:
            continue
    if not apply_time_ok:
        raise SkillError("apply-time 格式应为 yyyy-MM-dd 或 yyyy-MM-dd HH:mm:ss")
    if scene not in SCENE_LABELS:
        raise SkillError("scene 取值非法，应为 " + "/".join(SCENE_LABELS))
    if threshold_type not in {"NUMBER", "PERCENT"}:
        raise SkillError("threshold-type 必须是 NUMBER 或 PERCENT")
    parse_positive_number(low, "low")
    parse_positive_number(high, "high")

    try:
        batch_size = int(options.get("batch_size") or 10)
    except (TypeError, ValueError):
        batch_size = 10
    if batch_size <= 0:
        batch_size = 10
    try:
        sleep_base = float(options.get("sleep") or 0.3)
    except (TypeError, ValueError):
        sleep_base = 0.3
    if sleep_base < 0:
        sleep_base = 0.3

    rows = read_cleaned_rows(file)
    total = len(rows)
    valid_count = sum(1 for row in rows if row["_valid"])
    emit({"event": "parsed", "total": total, "valid": valid_count})
    if total == 0:
        raise SkillError("清洗文件中未解析到任何商品数据")
    if valid_count == 0:
        raise SkillError("清洗文件中无满足必填字段（商品ID 与 本地核验价）的商品")

    scene_label = SCENE_LABELS[scene]
    result_rows: list[list[str]] = [
        ["商品ID", "SKU ID", "成本价", "本地核验价", scene_label, "差价", "风险标注", "优惠组合", "备注"]
    ]

    batches = [rows[i : i + batch_size] for i in range(0, total, batch_size)]
    total_batches = len(batches)
    written = ok = fail = skipped = 0
    consecutive_fail = 0
    consecutive_ok = 0
    sleep_time = sleep_base
    processed = 0
    failed = 0
    aborted = False

    for batch_index, batch in enumerate(batches, 1):
        if aborted:
            for row in batch:
                written += 1
                fail += 1
                result_rows.append(
                    [
                        row["itemId"], row["skuId"], row["costPrice"], row["localPrice"],
                        "", "", "", "", "因批量失败率过高，已提前终止",
                    ]
                )
            emit(
                {
                    "event": "batch", "batchIndex": batch_index, "totalBatches": total_batches,
                    "written": written, "ok": ok, "fail": fail, "skipped": skipped,
                    "status": "aborted",
                }
            )
            continue

        valid_rows = [row for row in batch if row["_valid"]]
        response_map: dict[tuple[str, str], dict[str, Any]] = {}
        status = "success"
        error_note = ""

        if valid_rows:
            param0 = {
                "applyTime": apply_time,
                "scene": scene,
                "thresholdType": threshold_type,
                "lowThreshold": low,
                "highThreshold": high,
                "itemRequests": [build_item_request(row) for row in valid_rows],
            }
            return_code, out, _err = invoke_atp(param0)
            try:
                response = json.loads(out) if out and out.strip() else None
            except json.JSONDecodeError:
                response = None
            if return_code != 0:
                status = "cli_error"
                error_note = "核价接口调用失败"
            elif not isinstance(response, dict):
                status = "biz_fail"
                error_note = "核价接口返回非 JSON 对象"
            else:
                # atp CLI 信封可能是 {data: 业务体} / {result: 业务体} / 直接就是业务体，
                # 用 unwrap_biz 统一剥壳，避免信封键名不同导致整批被识别为空。
                # 业务体标准形态：{success, errorMessage, errorCode,
                #                  model: {itemResponses: [...]}, extModels, totalCount}
                biz = unwrap_biz(response)
                if not biz.get("success", False):
                    status = "biz_fail"
                    message = trim_text(biz.get("errorMessage"))
                    code = trim_text(biz.get("errorCode"))
                    if message and code:
                        error_note = f"{message}（错误码 {code}）"
                    elif code:
                        error_note = f"接口返回失败（错误码 {code}）"
                    else:
                        error_note = message or "接口返回失败"
                else:
                    # itemResponses 通常挂在 biz.model 下；少数场景直接挂在 biz 下，做一次兜底
                    model = biz.get("model") if isinstance(biz.get("model"), dict) else {}
                    item_responses = model.get("itemResponses")
                    if not isinstance(item_responses, list):
                        item_responses = biz.get("itemResponses") if isinstance(
                            biz.get("itemResponses"), list
                        ) else []
                    for item in item_responses:
                        if not isinstance(item, dict):
                            continue
                        key = (str(item.get("itemId", "")), str(item.get("skuId", "") or ""))
                        response_map[key] = item
        else:
            status = "all_invalid"

        for row in batch:
            written += 1
            if not row["_valid"]:
                skipped += 1
                result_rows.append(
                    [
                        row["itemId"], row["skuId"], row["costPrice"], row["localPrice"],
                        "", "", "", "", "必填字段缺失",
                    ]
                )
                continue
            key = (str(row["itemId"]), str(row["skuId"] or ""))
            item = response_map.get(key)
            if item is not None:
                ok += 1
                result_rows.append(
                    [
                        row["itemId"], row["skuId"], row["costPrice"], row["localPrice"],
                        trim_text(item.get("onlineLowestPrice")),
                        trim_text(item.get("diffPrice")),
                        normalize_risk_tag(item.get("riskTag")),
                        trim_text(item.get("promotionCombo")),
                        trim_text(item.get("remark")),
                    ]
                )
            else:
                fail += 1
                result_rows.append(
                    [
                        row["itemId"], row["skuId"], row["costPrice"], row["localPrice"],
                        "", "", "", "", error_note or "接口未返回该商品",
                    ]
                )

        processed += 1
        if status in {"cli_error", "biz_fail"}:
            failed += 1
            consecutive_fail += 1
            consecutive_ok = 0
        else:
            consecutive_ok += 1
            consecutive_fail = 0
            if consecutive_ok >= 2 and sleep_time > sleep_base:
                sleep_time = sleep_base

        emit(
            {
                "event": "batch", "batchIndex": batch_index, "totalBatches": total_batches,
                "written": written, "ok": ok, "fail": fail, "skipped": skipped,
                "status": status,
            }
        )

        if processed >= 3 and failed / processed > 0.5:
            aborted = True
            continue

        if batch_index < total_batches:
            if consecutive_fail >= 2:
                sleep_time = max(sleep_time, 1.5)
            time.sleep(sleep_time)

    out_dir = Path(str(options.get("outdir") or "."))
    output_name = f"核价结果_{Path(file).stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    output_path = out_dir / output_name
    write_xlsx(output_path, result_rows, {0, 1})

    # 关键步骤正确性校验：回读结果文件，确认表头与数据行数与写入前预期一致。
    with XlsxDocument(str(output_path)) as verify_document:
        verify_records = verify_document.read_sheet_records(verify_document.sheets[0].path)
    if not verify_records:
        raise SkillError("结果文件写入失败或为空，无法生成风险报告")
    verify_header = [trim_text(value) for value in verify_records[0].cells[: len(result_rows[0])]]
    if verify_header != result_rows[0]:
        raise SkillError("结果文件回读校验失败：表头与预期不一致")
    verify_data = sum(
        1
        for record in verify_records
        if record.row_num > verify_records[0].row_num
        and any(value != "" for value in record.cells)
    )
    if verify_data != len(result_rows) - 1:
        raise SkillError("结果文件回读校验失败：数据行数与预期不一致")

    summary = report(str(output_path))
    if not isinstance(summary, dict) or "total" not in summary:
        raise SkillError("风险报告解析结果异常，缺少核心统计字段")
    summary["output_path"] = str(output_path)
    summary["output_name"] = output_name
    summary["applyTime"] = apply_time
    summary["scene"] = scene
    summary["scene_label"] = scene_label
    summary["aborted"] = aborted
    summary["ok"] = ok
    summary["fail"] = fail
    summary["skipped"] = skipped
    emit({"event": "done", "summary": summary})


def parse_positive_number(value: Any, option: str) -> int | float:
    raw = trim_text(value)
    try:
        number = float(raw)
    except ValueError:
        raise SkillError(f"{option} 必须是正数") from None
    if not math.isfinite(number) or number <= 0:
        raise SkillError(f"{option} 必须是正数")
    if re.fullmatch(r"\d+", raw):
        return int(raw)
    return number


def parse_options(arguments: list[str]) -> dict[str, Any]:
    options: dict[str, Any] = {}
    positional: list[str] = []
    index = 0
    while index < len(arguments):
        argument = arguments[index]
        if argument.startswith("--") and len(argument) > 2:
            key = argument[2:].replace("-", "_")
            if index + 1 < len(arguments) and not arguments[index + 1].startswith("--"):
                options[key] = arguments[index + 1]
                index += 2
            else:
                options[key] = True
                index += 1
        else:
            positional.append(argument)
            index += 1
    options["_pos"] = positional
    return options


def emit(value: dict[str, Any], stream: Any = sys.stdout) -> None:
    print(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
        file=stream,
        flush=True,
    )


USAGE = {
    "analyze": (
        "analyze <file.xlsx> [--sheet <名称>] [--header-row <1-50>]\n"
        "  说明：文件为位置参数，直接跟路径，不要用 --file。\n"
        "  示例：python -X utf8 price_check.py analyze \"价盘.xlsx\" --sheet Sheet1 --header-row 1"
    ),
    "clean": (
        "clean <file.xlsx> --item-id <col> --sku-id <col> "
        "(--price <col> | --item-price <col> --sku-price <col>) [--cost <col>] [--outdir <dir>]\n"
        "  说明：参数名为 --item-id / --sku-id / --price / --item-price / --sku-price / --cost，"
        "不要写成 --item-id-col 等变体；列选择器形如 col:A。\n"
        "  示例：python -X utf8 price_check.py clean \"价盘.xlsx\" --item-id col:A --sku-id col:B "
        "--item-price col:C --sku-price col:D --cost col:E --outdir ./out"
    ),
    "batch-check": (
        "batch-check <cleaned.xlsx> --apply-time <yyyy-MM-dd[ HH:mm:ss]> --scene <scene> "
        "--threshold-type <PERCENT|NUMBER> --low <正数> --high <正数> [--outdir <dir>] [--batch-size <n>] [--sleep <秒>]\n"
        "  说明：阈值参数名是 --low / --high，不是 --low-threshold / --high-threshold。\n"
        "  示例：python -X utf8 price_check.py batch-check \"清洗.xlsx\" "
        "--apply-time \"2026-07-31 14:00:00\" --scene predict_pmp --threshold-type PERCENT --low 10 --high 10 --outdir ./out"
    ),
    "report": (
        "report <result.xlsx>\n"
        "  说明：结果文件为位置参数，直接跟路径。\n"
        "  示例：python -X utf8 price_check.py report \"核价结果.xlsx\""
    ),
}

HELP_FLAGS = {"help", "-h", "--help"}


def full_usage() -> str:
    lines = ["price_check.py <子命令> [参数]", "支持子命令：analyze / clean / batch-check / report", ""]
    for name in ("analyze", "clean", "batch-check", "report"):
        lines.append(USAGE[name])
        lines.append("")
    return "\n".join(lines).rstrip()


def main(arguments: list[str]) -> int:
    mode = arguments[0] if arguments else ""
    if mode == "" or mode in HELP_FLAGS:
        print(full_usage(), flush=True)
        return 0
    options = parse_options(arguments[1:])
    positional = options.pop("_pos")
    if options.get("help") or options.get("h"):
        usage = USAGE.get(mode)
        if usage:
            print("用法: " + usage, flush=True)
            return 0
    if mode == "analyze":
        if not positional:
            raise SkillError("用法: " + USAGE["analyze"])
        result = analyze(positional[0], options.get("sheet"), options.get("header_row"))
    elif mode == "clean":
        if not positional:
            raise SkillError("用法: " + USAGE["clean"])
        options["file"] = positional[0]
        result = clean(options)
    elif mode == "report":
        if not positional:
            raise SkillError("用法: " + USAGE["report"])
        result = report(positional[0])
    elif mode == "batch-check":
        if not positional:
            raise SkillError("用法: " + USAGE["batch-check"])
        options["file"] = positional[0]
        batch_check(options)
        return 0
    else:
        raise SkillError(
            f"未知子命令: '{mode}'（支持 analyze/clean/batch-check/report；查看用法可运行 price_check.py --help）"
        )
    emit(result)
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="strict")
        sys.stderr.reconfigure(encoding="utf-8", errors="strict")
    try:
        raise SystemExit(main(sys.argv[1:]))
    except SkillError as error:
        emit({"error": str(error)}, sys.stderr)
        raise SystemExit(1) from None
    except Exception as error:
        emit({"error": f"执行异常: {error}"}, sys.stderr)
        raise SystemExit(1) from None
