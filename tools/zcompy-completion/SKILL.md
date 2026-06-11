---
name: zcompy-completion
description: 使用 zcompy 生成 zsh 补全生成器文件。当被要求为 CLI 命令编写、改进或验证基于 zcompy 的补全时使用，尤其适用于交付物名为 comp_{command}.py、命令补全脚本、zsh 补全生成器，或请求中提到 zcompy、comp.py、_arguments、zsh completions、命令选项或子命令补全 这类示例的情况。
---

# Zcompy 补全

创建一个名为 `comp_{command}.py` 的 Python 生成器文件，用 `zcompy` 对 CLI 建模，并通过 `cmd.complete_source(as_file=True)` 打印 zsh 补全源码。

预期交付物是生成器文件，而不是已生成并提交的 `_command` 文件，除非用户明确要求同时提供生成后的 zsh 输出。

## 工作流

1. 检查 zcompy 是否可用。
   - 尝试运行 `python -c "import zcompy; print(zcompy.__file__)"`。
   - 如果导入失败，在实现或验证补全前先安装它：
     - 推荐方式：`python -m pip install zcompy`
     - 从源码安装：`git clone https://github.com/FateScript/zcompy.git && cd zcompy && python -m pip install -e .`
     - 需要测试或开发工具时使用开发安装：`python -m pip install -e ".[dev]"`
   - 如果网络或权限问题导致无法安装，要明确说明，同时在可能的情况下仍基于本地示例或参考文件起草生成器。

2. 检查命令接口。
   - 优先查看 `command --help`，然后对嵌套命令查看 `command <subcommand> --help`。
   - 如果命令在当前仓库中实现，检查它的 parser/click/fire/absl 源码，并在合适时使用 zcompy 适配器。
   - 如果有本地示例，先阅读附近模式：`lpc_tweak/comp_tweak.py`、`completions/*/*_comp.py`，或已有的 `comp_*.py`。
   - 访问 https://github.com/FateScript/dotfiles/tree/master/py_completions 查看真实命令中使用 zcompy 的示例。

3. 选择 zcompy 构造方式。
   - 对 `argparse` 使用 `ParserCommand`。
   - 对 click 命令使用 `ClickCommand`。
   - 当命令来自外部、实现方式混合，或 help 输出是最可靠的信息来源时，手动构建 `Command`、`Option`、`Completion`、`DependentCompletion`、`Files`、`Default` 等对象。

4. 实现 `comp_{command}.py`。
   - 创建 `make_{command}_command() -> Command`。
   - 添加顶层选项和子命令。
   - 将重复选项提取到 `common_options()` 这类辅助函数中。
   - 将动态补全函数放在命令构造代码之前。
   - 结尾使用：

```python
if __name__ == "__main__":
    cmd = make_{command}_command()
    print(cmd.complete_source(as_file=True, sort_completion=False))
```

5. 验证。
   - 运行 `python -m py_compile comp_{command}.py`。
   - 运行 `python comp_{command}.py >/tmp/_{command}_generated`。
   - 如果 zsh 可用，运行 `zsh -n /tmp/_{command}_generated`。
   - 如果仓库已有 lint 或 format 检查，也运行相应检查。

6. 当用户需要启用补全时，说明 shell 安装方式。
   - 生成的补全文件应放在 zsh `fpath` 中的某个目录里，常见位置是 `~/.zsh/completions`。
   - 用户的 `~/.zshrc` 或当前 zsh 会话需要：

```zsh
fpath=(~/.zsh/completions $fpath)
autoload -U compinit && compinit
compdef _{command} {command}
```

   - 如果使用 `cmd.complete_source(as_file=True)`，将输出写入所选补全目录下名为 `_{command}` 的文件，然后重新加载 zsh 或再次运行 `compinit`。

## 实现规则

- 如果 `zcompy` 源代码存在，把它作为参考基础；检查其中的 README 或包模块，不要猜测 API 细节。
- 优先使用 zcompy 原语：
  - `Command(name, description)`
  - `Option(("--long", "-s"), "description", complete_func=...)`
  - `Completion(("choice1", "choice2"))` 用于固定选项
  - `Completion(func=my_func, ignore_exception=True)` 用于动态值
  - `DependentCompletion(func=..., depends_on=[("--foo", "-f")])` 用于依赖某个选项的值
  - `Files()` 和 `Files(dir_only=True)` 用于路径
  - `Default()` 用于自由形式字符串或命令参数
  - 有用时使用 `OSEnv()`、`URLs()`、`GitBranches()`、`GitCommits()`
- 只有当 zcompy 无法直接表达命令别名时，才把别名保留为独立子命令。
- 对可重复选项使用 `allow_repeat=True`。
- 对 `cmd -- args...` 这类尾随命令参数使用 `repeat_pos_args = Default()`。
- 描述保持简短且单行；过长的 help 文本会让补全菜单变得嘈杂。

## 动态补全函数

zcompy 可能会把 Python 补全函数嵌入生成的 shell 代码中。因此，每个动态补全函数都必须是自包含的：

- 在函数内部导入模块。
- 不要依赖辅助函数、非简单常量的模块全局变量，或外层 import。
- 捕获异常以提供尽力而为的补全，并配合 `ignore_exception=True` 使用。
- 每行打印一个候选项。若要包含描述，打印 `value description`。
- 如果候选项中的冒号会被 zsh `_describe` 解释，需要对冒号进行转义。

示例：

```python
def list_profiles():
    import os
    from pathlib import Path

    try:
        import tomllib
        config = Path(os.environ.get("APP_HOME", "~/.app")).expanduser() / "config.toml"
        with config.open("rb") as f:
            data = tomllib.load(f)
    except Exception:
        return

    for name in data.get("profiles", {}):
        print(name)
```

## 输出形态

一个好的 `comp_{command}.py` 应该可读，并且可以直接运行：

```python
from __future__ import annotations

from zcompy import Command, Completion, Default, Files, Option


def common_options():
    return [
        Option(("-h", "--help"), "Print help"),
        Option("--config", "Config file", complete_func=Files()),
    ]


def make_example_command() -> Command:
    cmd = Command("example", "Example CLI")
    cmd.add_options(common_options())

    run = Command("run", "Run a task")
    run.add_options([
        *common_options(),
        Option("--mode", "Run mode", complete_func=Completion(("fast", "safe"))),
    ])
    run.add_positional_args(Default())

    cmd.add_sub_commands(run)
    return cmd


if __name__ == "__main__":
    cmd = make_example_command()
    print(cmd.complete_source(as_file=True, sort_completion=False))
```

## 质量标准

- 覆盖主命令、常见全局选项、重要子命令，以及枚举、文件、目录、从配置派生的名称等值补全。
- 如果覆盖每个冷门选项会让文件变脆弱，不要过度拟合；对未知的自由形式值使用 `Default()` 建模。
- 避免在补全函数中发起实时网络调用，除非现有本地补全风格已经这样做，并且该命令领域也预期如此。
- 如果 help 输出和源码不一致，对本地仓库命令优先相信源码，对外部二进制优先相信已安装版本的 `--help`。
- 在最终回复中报告文件路径和已运行的验证命令。
