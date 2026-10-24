---
name: implement
description: "根据 spec 或一组 tickets 实现一项工作。"
disable-model-invocation: true
---

实现用户在 spec 或 tickets 中描述的工作。

如果用户给出 ticket 引用，先从 issue tracker 读取 ticket 并说明其标题；引用有歧义时先询问。

尽可能在预先约定的 seam 上调用 `tdd` skill。

定期运行类型检查，定期运行单个测试文件，并在最后运行一次完整测试套件。

完成后，调用 `code-review` skill 审查这项工作。

将你的工作提交到当前分支。
