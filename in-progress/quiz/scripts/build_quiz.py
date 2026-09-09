#!/usr/bin/env python3
"""Build a self-contained, automatically scored quiz HTML file from JSON.

The input is deliberately data-only.  Question text is rendered with DOM
textContent in the generated page, and the JSON payload is escaped before it
is placed in an application/json script element.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any


DEFAULT_DESCRIPTION = "独立完成后点击“提交答案”查看得分、正确答案和逐题解释；不确定时请选择每题的“我不知道”选项。"
DEFAULT_UNKNOWN_LABEL = "我不知道"
ALLOWED_TYPES = {"single", "multiple"}


class QuizValidationError(ValueError):
    """Raised when a quiz JSON document cannot be rendered safely."""


def _text(value: Any, path: str, *, required: bool = True) -> str:
    if value is None and not required:
        return ""
    if not isinstance(value, str):
        raise QuizValidationError(f"{path} 必须是字符串")
    result = value.strip()
    if required and not result:
        raise QuizValidationError(f"{path} 不能为空")
    return result


def _points(value: Any, path: str) -> int | float:
    if value is None:
        return 1
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise QuizValidationError(f"{path} 必须是正数")
    try:
        finite = math.isfinite(float(value))
    except (OverflowError, ValueError):
        finite = False
    if not finite or value <= 0:
        raise QuizValidationError(f"{path} 必须是正数")
    return value


def _unknown_details(
    raw_question: dict[str, Any], options: list[str], path: str
) -> tuple[int, str]:
    """Return the uncertainty option and label, filling it in for old data.

    New question banks should provide ``unknown_index`` explicitly.  Inferring
    an existing option with the configured label, or appending it when an old
    bank has no uncertainty option, keeps older data buildable while
    guaranteeing that every rendered question has a sentinel option.
    """

    unknown_label = _text(
        raw_question.get("unknown_label", DEFAULT_UNKNOWN_LABEL),
        f"{path}.unknown_label",
    )
    exact_matches = [
        index for index, option in enumerate(options) if option == unknown_label
    ]
    raw_index = raw_question.get("unknown_index")
    if raw_index is None:
        if len(exact_matches) > 1:
            raise QuizValidationError(
                f"{path}.options 必须恰好包含一个「{unknown_label}」选项"
            )
        if exact_matches:
            return exact_matches[0], unknown_label
        options.append(unknown_label)
        return len(options) - 1, unknown_label

    if isinstance(raw_index, bool) or not isinstance(raw_index, int):
        raise QuizValidationError(f"{path}.unknown_index 必须是非负整数")
    if raw_index < 0 or raw_index >= len(options):
        raise QuizValidationError(
            f"{path}.unknown_index 越界；有效范围是 0–{len(options) - 1}"
        )
    if len(exact_matches) != 1 or exact_matches[0] != raw_index:
        raise QuizValidationError(
            f"{path}.unknown_index 必须唯一指向「{unknown_label}」选项"
        )
    return raw_index, unknown_label


def validate_quiz(document: Any) -> dict[str, Any]:
    """Validate and normalize a quiz document.

    The returned object is safe to serialize as JSON and has defaults filled
    in.  Validation is intentionally strict so a typo cannot silently alter
    scoring.
    """

    if not isinstance(document, dict):
        raise QuizValidationError("题库根对象必须是 JSON 对象")

    version = document.get("version", 1)
    if isinstance(version, bool) or not isinstance(version, int) or version != 1:
        raise QuizValidationError("version 当前必须是整数 1")

    title = _text(document.get("title"), "title")
    source = _text(document.get("source", ""), "source", required=False)
    description = _text(
        document.get("description", DEFAULT_DESCRIPTION),
        "description",
    )

    questions = document.get("questions")
    if not isinstance(questions, list) or not questions:
        raise QuizValidationError("questions 必须是至少包含一道题目的数组")

    metadata = document.get("metadata", {})
    if metadata is None:
        metadata = {}
    if not isinstance(metadata, dict):
        raise QuizValidationError("metadata 必须是 JSON 对象")
    try:
        json.dumps(metadata, ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError) as error:
        raise QuizValidationError("metadata 必须只包含有限的 JSON 值") from error

    normalized_questions: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for number, raw_question in enumerate(questions, start=1):
        path = f"questions[{number}]"
        if not isinstance(raw_question, dict):
            raise QuizValidationError(f"{path} 必须是 JSON 对象")

        question_id = _text(raw_question.get("id"), f"{path}.id")
        if question_id in seen_ids:
            raise QuizValidationError(f"{path}.id 与前面的题目重复：{question_id}")
        seen_ids.add(question_id)

        category = _text(raw_question.get("category"), f"{path}.category")
        objective = _text(
            raw_question.get("objective", ""),
            f"{path}.objective",
            required=False,
        )
        source_anchor = _text(
            raw_question.get("source_anchor", ""),
            f"{path}.source_anchor",
            required=False,
        )
        question_type = _text(raw_question.get("type"), f"{path}.type")
        if question_type not in ALLOWED_TYPES:
            allowed = ", ".join(sorted(ALLOWED_TYPES))
            raise QuizValidationError(
                f"{path}.type 必须是 {allowed}，收到：{question_type}"
            )
        prompt = _text(raw_question.get("prompt"), f"{path}.prompt")
        explanation = _text(
            raw_question.get("explanation"), f"{path}.explanation"
        )

        options = raw_question.get("options")
        if not isinstance(options, list) or len(options) < 2:
            raise QuizValidationError(f"{path}.options 至少需要两个选项")
        normalized_options: list[str] = []
        for option_number, option in enumerate(options, start=1):
            normalized_options.append(
                _text(option, f"{path}.options[{option_number}]")
            )

        # Every rendered question has one explicit uncertainty choice.  The
        # index is persisted so the browser can distinguish it from a normal
        # wrong answer and make it mutually exclusive in multiple-choice UI.
        unknown_index, unknown_label = _unknown_details(
            raw_question, normalized_options, path
        )

        answer = raw_question.get("answer")
        if not isinstance(answer, list) or not answer:
            raise QuizValidationError(f"{path}.answer 必须是非空整数数组")
        if any(isinstance(index, bool) or not isinstance(index, int) for index in answer):
            raise QuizValidationError(f"{path}.answer 中的索引必须是整数")
        if len(set(answer)) != len(answer):
            raise QuizValidationError(f"{path}.answer 不能包含重复索引")
        if any(index < 0 or index >= len(normalized_options) for index in answer):
            raise QuizValidationError(
                f"{path}.answer 含越界索引；有效范围是 0–{len(normalized_options) - 1}"
            )
        if unknown_index in answer:
            raise QuizValidationError(
                f"{path}.answer 不能包含 unknown_index（「{DEFAULT_UNKNOWN_LABEL}」选项）"
            )
        if question_type == "single" and len(answer) != 1:
            raise QuizValidationError(f"{path}.type 为 single 时 answer 必须恰好一个索引")

        normalized_questions.append(
            {
                "id": question_id,
                "category": category,
                "objective": objective,
                "source_anchor": source_anchor,
                "type": question_type,
                "prompt": prompt,
                "options": normalized_options,
                "answer": sorted(answer),
                "unknown_index": unknown_index,
                "unknown_label": unknown_label,
                "explanation": explanation,
                "points": _points(raw_question.get("points"), f"{path}.points"),
            }
        )

    return {
        "version": 1,
        "title": title,
        "source": source,
        "description": description,
        "metadata": metadata,
        "questions": normalized_questions,
    }


def _safe_json_for_script(document: dict[str, Any]) -> str:
    """Serialize JSON without allowing a payload to close the script tag."""

    payload = json.dumps(
        document,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    )
    # A JSON script element is inert, but escaping these characters also makes
    # the boundary safe in browsers and in HTML tooling that treats it as text.
    return (
        payload.replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


HTML_TEMPLATE = r'''<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>知识测验</title>
  <style>
    :root {
      color-scheme: light;
      --ink: #172033;
      --muted: #5f6b7a;
      --line: #dbe2ec;
      --panel: #ffffff;
      --canvas: #f4f7fb;
      --accent: #315efb;
      --accent-soft: #edf1ff;
      --good: #13795b;
      --good-soft: #e8f7f0;
      --bad: #b42318;
      --bad-soft: #fff0ee;
      --uncertain: #8a5a00;
      --uncertain-soft: #fff8df;
      --shadow: 0 12px 32px rgba(28, 46, 82, .08);
    }
    * { box-sizing: border-box; }
    html { scroll-behavior: smooth; }
    body {
      margin: 0;
      color: var(--ink);
      background: var(--canvas);
      font: 16px/1.65 -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
    }
    .shell { width: min(920px, calc(100% - 32px)); margin: 0 auto; padding: 34px 0 64px; }
    .hero, .progress-panel, .question-card, .result-panel {
      background: var(--panel);
      border: 1px solid var(--line);
      box-shadow: var(--shadow);
    }
    .hero { padding: 30px 32px 26px; border-radius: 20px; }
    .eyebrow { margin: 0 0 6px; color: var(--accent); font-size: .82rem; font-weight: 700; letter-spacing: .08em; }
    h1 { margin: 0; font-size: clamp(1.65rem, 4vw, 2.35rem); line-height: 1.25; letter-spacing: -.02em; }
    .source { margin: 10px 0 0; color: var(--muted); font-size: .9rem; overflow-wrap: anywhere; }
    .source a { color: var(--accent); }
    .description { margin: 16px 0 0; color: #354154; }
    .uncertainty-note { margin: 10px 0 0; color: var(--uncertain); font-size: .91rem; }
    .progress-panel { position: sticky; top: 12px; z-index: 2; margin: 18px 0; padding: 15px 18px; border-radius: 14px; }
    .progress-top { display: flex; justify-content: space-between; gap: 12px; color: var(--muted); font-size: .92rem; }
    .progress-top strong { color: var(--ink); }
    .progress-track { height: 9px; margin-top: 9px; overflow: hidden; background: #e9edf4; border-radius: 99px; }
    .progress-bar { width: 0; height: 100%; background: var(--accent); border-radius: inherit; transition: width .2s ease; }
    #questions { display: grid; gap: 16px; }
    .question-card { padding: 24px 26px; border-radius: 16px; transition: border-color .2s, box-shadow .2s; }
    .question-card.is-correct { border-color: #83d5b5; box-shadow: 0 10px 28px rgba(19, 121, 91, .09); }
    .question-card.is-wrong { border-color: #f2aaa3; box-shadow: 0 10px 28px rgba(180, 35, 24, .08); }
    .question-card.is-unknown { border-color: #e6c56c; box-shadow: 0 10px 28px rgba(138, 90, 0, .08); }
    .question-meta { display: flex; flex-wrap: wrap; align-items: center; gap: 8px 12px; margin-bottom: 10px; color: var(--muted); font-size: .84rem; }
    .question-number { color: var(--accent); font-weight: 750; }
    .category { padding: 2px 9px; color: #40516b; background: #eef2f7; border-radius: 99px; }
    .objective { margin: 0 0 13px; color: var(--muted); font-size: .9rem; }
    .prompt { margin: 0 0 17px; font-size: 1.08rem; font-weight: 650; line-height: 1.55; white-space: pre-wrap; overflow-wrap: anywhere; }
    fieldset { min-width: 0; margin: 0; padding: 0; border: 0; }
    .option-list { display: grid; gap: 9px; }
    .option {
      display: flex;
      align-items: flex-start;
      gap: 10px;
      padding: 11px 13px;
      border: 1px solid var(--line);
      border-radius: 11px;
      cursor: pointer;
      transition: background .15s, border-color .15s;
    }
    .option:hover { border-color: #9dafc9; background: #fafcff; }
    .option:has(input:focus-visible) { outline: 3px solid rgba(49, 94, 251, .25); outline-offset: 2px; }
    .option:has(input:checked) { border-color: var(--accent); background: var(--accent-soft); }
    .option input { flex: 0 0 auto; width: 18px; height: 18px; margin: 3px 0 0; accent-color: var(--accent); }
    .option-text { min-width: 0; white-space: pre-wrap; overflow-wrap: anywhere; }
    .feedback { margin-top: 18px; padding: 16px 17px; border-radius: 11px; font-size: .93rem; }
    .feedback.good { color: #0d5b45; background: var(--good-soft); }
    .feedback.bad { color: #7e2018; background: var(--bad-soft); }
    .feedback.unknown { color: #704900; background: var(--uncertain-soft); }
    .feedback-title { margin: 0 0 8px; font-weight: 750; }
    .feedback-row { margin: 5px 0; white-space: pre-wrap; overflow-wrap: anywhere; }
    .feedback-label { font-weight: 700; }
    .feedback-explanation { margin: 11px 0 0; padding-top: 10px; border-top: 1px solid currentColor; opacity: .94; white-space: pre-wrap; overflow-wrap: anywhere; }
    .actions { display: flex; flex-wrap: wrap; gap: 10px; margin: 22px 0 0; }
    button {
      min-height: 44px;
      padding: 9px 17px;
      border: 1px solid transparent;
      border-radius: 10px;
      font: inherit;
      font-weight: 700;
      cursor: pointer;
    }
    button:focus-visible { outline: 3px solid rgba(49, 94, 251, .3); outline-offset: 2px; }
    .primary { color: #fff; background: var(--accent); }
    .primary:hover { background: #254bd7; }
    .secondary { color: #334155; background: #fff; border-color: var(--line); }
    .secondary:hover { background: #f8fafc; border-color: #aab8cc; }
    .result-panel { margin-top: 22px; padding: 25px 26px; border-radius: 16px; }
    .result-panel.hidden, .report-tools.hidden { display: none; }
    .result-kicker { margin: 0; color: var(--accent); font-size: .84rem; font-weight: 750; letter-spacing: .06em; }
    .score { margin: 3px 0 2px; font-size: clamp(1.8rem, 5vw, 2.8rem); font-weight: 800; letter-spacing: -.03em; }
    .result-message { margin: 0; color: var(--muted); }
    .report-tools { margin-top: 19px; padding-top: 17px; border-top: 1px solid var(--line); }
    .report-tools p { margin: 0 0 9px; color: var(--muted); font-size: .9rem; }
    #report-text { display: block; width: 100%; min-height: 145px; padding: 11px; color: #263449; background: #f8fafc; border: 1px solid var(--line); border-radius: 9px; font: .88rem/1.5 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; resize: vertical; }
    .copy-status { display: inline-block; margin-left: 8px; color: var(--good); font-size: .9rem; }
    .footer-note { margin-top: 28px; color: var(--muted); font-size: .82rem; text-align: center; }
    .sr-only { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0, 0, 0, 0); white-space: nowrap; border: 0; }
    @media (max-width: 600px) {
      .shell { width: min(100% - 20px, 920px); padding-top: 14px; }
      .hero { padding: 23px 20px 21px; border-radius: 15px; }
      .question-card, .result-panel { padding: 20px 18px; border-radius: 13px; }
      .progress-panel { top: 7px; }
    }
  </style>
</head>
<body>
  <div class="shell">
    <header class="hero">
      <p class="eyebrow" id="mode-label">知识测验</p>
      <h1 id="quiz-title">知识测验</h1>
      <div class="source" id="quiz-source"></div>
      <p class="description" id="quiz-description"></p>
      <p class="uncertainty-note" id="uncertainty-note">每题都有不确定选项。不确定时请选择它；多选题中该选项与其他选项互斥。</p>
    </header>

    <section class="progress-panel" aria-label="答题进度">
      <div class="progress-top">
        <span id="progress-label">已答 0 / 0 题</span>
        <strong id="progress-percent">0%</strong>
      </div>
      <div class="progress-track" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="0" aria-label="答题进度">
        <div class="progress-bar" id="progress-bar"></div>
      </div>
    </section>

    <main id="questions" aria-label="测验题目"></main>

    <div class="actions">
      <button class="primary" id="submit-button" type="button">提交答案</button>
      <button class="secondary" id="reset-button" type="button">清空重做</button>
    </div>

    <section class="result-panel hidden" id="result-panel" aria-live="polite" aria-labelledby="result-heading">
      <p class="result-kicker" id="result-heading">本轮结果</p>
      <div class="score" id="score"></div>
      <p class="result-message" id="result-message"></p>
      <div class="report-tools hidden" id="report-tools">
        <p>可以复制下面的错题报告发回聊天，让我按知识点帮你复盘。</p>
        <textarea id="report-text" readonly aria-label="错题报告"></textarea>
        <div class="actions">
          <button class="secondary" id="copy-button" type="button">复制错题报告</button>
          <span class="copy-status" id="copy-status" role="status"></span>
        </div>
      </div>
    </section>

    <p class="footer-note">正确答案只在提交后显示在界面中；本页面可离线打开，作答内容不会上传。</p>
  </div>

  <noscript><p>此测验需要启用 JavaScript 才能交互和评分。</p></noscript>
  <script type="application/json" id="quiz-data">__QUIZ_DATA__</script>
  <script>
    (() => {
      "use strict";

      const dataNode = document.getElementById("quiz-data");
      let quiz;
      try {
        quiz = JSON.parse(dataNode.textContent);
      } catch (error) {
        document.getElementById("questions").textContent = "题库数据损坏，无法加载。";
        return;
      }

      const questions = quiz.questions;
      const total = questions.length;
      const cards = [];
      const modeNames = { quick: "快速测试", standard: "标准测试", comprehensive: "全覆盖测试" };
      const $ = (id) => document.getElementById(id);
      const titleNode = $("quiz-title");
      const sourceNode = $("quiz-source");
      const descriptionNode = $("quiz-description");
      const questionsNode = $("questions");
      const progressLabel = $("progress-label");
      const progressPercent = $("progress-percent");
      const progressBar = $("progress-bar");
      const progressTrack = document.querySelector(".progress-track");
      const resultPanel = $("result-panel");
      const scoreNode = $("score");
      const resultMessage = $("result-message");
      const reportTools = $("report-tools");
      const reportText = $("report-text");
      const copyStatus = $("copy-status");
      const unknownLabels = Array.from(new Set(
        questions.map((question) => question.unknown_label || "我不知道")
      ));
      const unknownLabelText = unknownLabels.length === 1
        ? `“${unknownLabels[0]}”`
        : "不确定选项";

      document.title = `${quiz.title} · 知识测验`;
      titleNode.textContent = quiz.title;
      descriptionNode.textContent = quiz.description || "独立完成后点击“提交答案”查看结果。";
      $("uncertainty-note").textContent = `每题都有${unknownLabelText}。不确定时请选择它；多选题中该选项与其他选项互斥。`;
      const mode = quiz.metadata && quiz.metadata.mode;
      $("mode-label").textContent = Object.prototype.hasOwnProperty.call(modeNames, mode) ? modeNames[mode] : "知识测验";

      if (quiz.source) {
        const urlPattern = /^https?:\/\//i;
        if (urlPattern.test(quiz.source)) {
          const link = document.createElement("a");
          link.href = quiz.source;
          link.target = "_blank";
          link.rel = "noopener noreferrer";
          link.textContent = quiz.source;
          sourceNode.append("来源：", link);
        } else {
          sourceNode.textContent = `来源：${quiz.source}`;
        }
      }

      function makeNode(tag, className, text) {
        const node = document.createElement(tag);
        if (className) node.className = className;
        if (text !== undefined) node.textContent = text;
        return node;
      }

      function optionLabel(index) {
        let label = "";
        let value = index + 1;
        while (value > 0) {
          value -= 1;
          label = String.fromCharCode(65 + (value % 26)) + label;
          value = Math.floor(value / 26);
        }
        return label;
      }

      function isUnknownSelection(question, indexes) {
        return Number.isInteger(question.unknown_index)
          && indexes.length === 1
          && indexes[0] === question.unknown_index;
      }

      function handleOptionChange(card, question, input) {
        // A multiple-choice uncertainty choice is an abstention, not another
        // knowledge claim.  Keep it mutually exclusive with all other picks.
        if (question.type === "multiple" && input.checked && Number.isInteger(question.unknown_index)) {
          const selectedIndex = Number(input.value);
          const inputs = Array.from(card.querySelectorAll("input"));
          if (selectedIndex === question.unknown_index) {
            inputs.forEach((other) => { if (other !== input) other.checked = false; });
          } else {
            inputs.forEach((other) => {
              if (Number(other.value) === question.unknown_index) other.checked = false;
            });
          }
        }
        updateProgress();
      }

      function renderQuestions() {
        questions.forEach((question, questionIndex) => {
          const card = makeNode("article", "question-card");
          card.dataset.questionIndex = String(questionIndex);

          const meta = makeNode("div", "question-meta");
          meta.append(
            makeNode("span", "question-number", `第 ${questionIndex + 1} / ${total} 题`),
            makeNode("span", "category", question.category),
            makeNode("span", "", question.type === "multiple" ? "多选" : "单选"),
            makeNode("span", "", `${formatPoints(Number(question.points))} 分`)
          );
          card.append(meta);

          if (question.objective) {
            card.append(makeNode("p", "objective", `考查：${question.objective}`));
          }
          card.append(makeNode("p", "prompt", question.prompt));

          const fieldset = document.createElement("fieldset");
          const legend = makeNode("legend", "sr-only", `第 ${questionIndex + 1} 题选项`);
          fieldset.append(legend);
          const optionList = makeNode("div", "option-list");
          const inputType = question.type === "multiple" ? "checkbox" : "radio";
          question.options.forEach((option, optionIndex) => {
            const label = makeNode("label", "option");
            const input = document.createElement("input");
            input.type = inputType;
            input.name = `question-${questionIndex}`;
            input.value = String(optionIndex);
            input.id = `question-${questionIndex}-option-${optionIndex}`;
            input.setAttribute("aria-label", `${optionLabel(optionIndex)}. ${option}`);
            input.addEventListener("change", () => handleOptionChange(card, question, input));
            const optionText = makeNode("span", "option-text", `${optionLabel(optionIndex)}. ${option}`);
            label.htmlFor = input.id;
            label.append(input, optionText);
            optionList.append(label);
          });
          fieldset.append(optionList);
          card.append(fieldset);
          questionsNode.append(card);
          cards.push(card);
        });
      }

      function selectedFor(card) {
        return Array.from(card.querySelectorAll("input:checked"))
          .map((input) => Number(input.value))
          .sort((a, b) => a - b);
      }

      function sameSet(left, right) {
        if (left.length !== right.length) return false;
        return left.every((value, index) => value === right[index]);
      }

      function updateProgress() {
        const answered = cards.reduce((count, card) => count + (selectedFor(card).length ? 1 : 0), 0);
        const percent = total ? Math.round((answered / total) * 100) : 0;
        progressLabel.textContent = `已答 ${answered} / ${total} 题`;
        progressPercent.textContent = `${percent}%`;
        progressBar.style.width = `${percent}%`;
        progressTrack.setAttribute("aria-valuenow", String(percent));
      }

      function formatAnswer(question, indexes) {
        if (!indexes.length) return "未作答";
        return indexes
          .map((index) => `${optionLabel(index)}. ${question.options[index]}`)
          .join("；");
      }

      function addFeedbackRow(container, label, value) {
        const row = makeNode("p", "feedback-row");
        row.append(makeNode("span", "feedback-label", `${label}：`), document.createTextNode(value));
        container.append(row);
      }

      function showFeedback(card, question, selected, correct) {
        const oldFeedback = card.querySelector(".feedback");
        if (oldFeedback) oldFeedback.remove();
        const uncertain = isUnknownSelection(question, selected);
        card.classList.remove("is-correct", "is-wrong", "is-unknown");
        card.classList.add(correct ? "is-correct" : (uncertain ? "is-unknown" : "is-wrong"));

        const feedback = makeNode("div", `feedback ${correct ? "good" : (uncertain ? "unknown" : "bad")}`);
        feedback.setAttribute("role", "status");
        const status = correct
          ? "✓ 回答正确"
          : (uncertain ? "？ 自报不确定" : (selected.length ? "✕ 需要复习" : "— 未作答"));
        feedback.append(makeNode("p", "feedback-title", status));
        addFeedbackRow(feedback, "你的答案", formatAnswer(question, selected));
        addFeedbackRow(feedback, "正确答案", formatAnswer(question, question.answer));
        if (question.source_anchor) addFeedbackRow(feedback, "证据位置", question.source_anchor);
        const explanation = makeNode("p", "feedback-explanation");
        explanation.append(makeNode("span", "feedback-label", "解释："), document.createTextNode(question.explanation));
        feedback.append(explanation);
        card.append(feedback);
      }

      function formatPoints(value) {
        return Number.isInteger(value) ? String(value) : String(Number(value.toFixed(2)));
      }

      function buildReport(results, score, totalPoints, unanswered) {
        const lines = [];
        lines.push(`测验：${quiz.title}`);
        if (quiz.source) lines.push(`来源：${quiz.source}`);
        lines.push(`得分：${formatPoints(score)} / ${formatPoints(totalPoints)} 分（${totalPoints ? Math.round((score / totalPoints) * 100) : 0}%）`);
        const uncertain = results.filter((result) => isUnknownSelection(result.question, result.selected));
        lines.push(`未作答：${unanswered} 题`);
        lines.push(`自报不确定：${uncertain.length} 题`);
        lines.push("");
        const wrong = results.filter((result) => !result.correct && result.selected.length
          && !isUnknownSelection(result.question, result.selected));
        const blank = results.filter((result) => !result.selected.length);
        if (!wrong.length && !uncertain.length && !blank.length) {
          lines.push("错题：无");
          return lines.join("\n");
        }
        if (wrong.length) lines.push(`已答错：${wrong.length} 题`);
        const appendResult = (result, index, heading) => {
          const question = result.question;
          lines.push("");
          lines.push(`${heading}${index + 1}. [${question.id}] ${question.category}`);
          if (question.objective) lines.push(`考查：${question.objective}`);
          lines.push(`题目：${question.prompt}`);
          lines.push(`你的答案：${formatAnswer(question, result.selected)}`);
          lines.push(`正确答案：${formatAnswer(question, question.answer)}`);
          if (question.source_anchor) lines.push(`证据位置：${question.source_anchor}`);
          lines.push(`解释：${question.explanation}`);
        };
        wrong.forEach((result, index) => appendResult(result, index, ""));
        if (uncertain.length) {
          lines.push("");
          lines.push(`自报不确定题：${uncertain.length} 题（建议优先补学）`);
          uncertain.forEach((result, index) => appendResult(result, index, "不确定 "));
        }
        if (blank.length) {
          lines.push("");
          lines.push(`未作答题：${blank.length} 题（未据此判断知识掌握情况）`);
          blank.forEach((result, index) => appendResult(result, index, "未作答 "));
        }
        return lines.join("\n");
      }

      function submit() {
        let score = 0;
        let totalPoints = 0;
        let unanswered = 0;
        let uncertain = 0;
        const results = [];
        questions.forEach((question, index) => {
          const selected = selectedFor(cards[index]);
          const correct = sameSet(selected, question.answer);
          const points = Number(question.points);
          totalPoints += points;
          if (!selected.length) unanswered += 1;
          if (isUnknownSelection(question, selected)) uncertain += 1;
          if (correct) score += points;
          results.push({ question, selected, correct });
          showFeedback(cards[index], question, selected, correct);
        });

        const percent = totalPoints ? Math.round((score / totalPoints) * 100) : 0;
        scoreNode.textContent = `${formatPoints(score)} / ${formatPoints(totalPoints)} 分（${percent}%）`;
        const unansweredText = unanswered ? `还有 ${unanswered} 题未作答。` : "所有题目都已作答。";
        const uncertainText = uncertain
          ? `有 ${uncertain} 题选择了${unknownLabelText}，已单独列入复盘。`
          : `没有题目标记为${unknownLabelText}。`;
        resultMessage.textContent = `${unansweredText} ${uncertainText} 下方已展开逐题反馈；多选题需要完整匹配正确选项。`;
        reportText.value = buildReport(results, score, totalPoints, unanswered);
        reportTools.classList.remove("hidden");
        resultPanel.classList.remove("hidden");
        copyStatus.textContent = "";
        resultPanel.scrollIntoView({ behavior: "smooth", block: "start" });
      }

      async function copyReport() {
        const report = reportText.value;
        let copied = false;
        try {
          if (navigator.clipboard && window.isSecureContext) {
            await navigator.clipboard.writeText(report);
            copied = true;
          }
        } catch (error) {
          copied = false;
        }
        if (!copied) {
          reportText.focus();
          reportText.select();
          try { copied = document.execCommand("copy"); } catch (error) { copied = false; }
          if (copied) reportText.setSelectionRange(0, 0);
        }
        copyStatus.textContent = copied ? "已复制" : "请手动全选并复制上面的文本";
      }

      function reset() {
        cards.forEach((card) => {
          card.querySelectorAll("input").forEach((input) => { input.checked = false; });
          card.classList.remove("is-correct", "is-wrong", "is-unknown");
          const feedback = card.querySelector(".feedback");
          if (feedback) feedback.remove();
        });
        resultPanel.classList.add("hidden");
        reportTools.classList.add("hidden");
        reportText.value = "";
        copyStatus.textContent = "";
        updateProgress();
        window.scrollTo({ top: 0, behavior: "smooth" });
      }

      renderQuestions();
      updateProgress();
      $("submit-button").addEventListener("click", submit);
      $("reset-button").addEventListener("click", reset);
      $("copy-button").addEventListener("click", copyReport);
    })();
  </script>
</body>
</html>
'''


def build_html(document: dict[str, Any]) -> str:
    payload = _safe_json_for_script(document)
    return HTML_TEMPLATE.replace("__QUIZ_DATA__", payload)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="从题库 JSON 生成可离线打开、自动评分的网页版测验。"
    )
    parser.add_argument("--input", required=True, help="UTF-8 题库 JSON 文件")
    parser.add_argument("--output", required=True, help="输出 HTML 文件")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    input_path = Path(args.input)
    output_path = Path(args.output)
    try:
        document = json.loads(input_path.read_text(encoding="utf-8-sig"))
        normalized = validate_quiz(document)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(build_html(normalized), encoding="utf-8")
    except FileNotFoundError as error:
        print(f"文件不存在：{error.filename}", file=sys.stderr)
        return 2
    except (OSError, UnicodeError, json.JSONDecodeError, QuizValidationError) as error:
        print(f"生成失败：{error}", file=sys.stderr)
        return 2

    print(f"已生成：{output_path}（{len(normalized['questions'])} 题）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
