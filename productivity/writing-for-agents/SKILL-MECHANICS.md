# Skill 机制

这是 [`writing-for-agents`](SKILL.md) 中专门讨论 skill 的分支：当文档本身是 skill 时，frontmatter、调用方式和路由型 skill 应如何处理。其他写作规则仍以 `SKILL.md` 中的通用参考为准。

## 调用方式

有两种选择，分别交换两类负载：

- **模型调用（model-invoked）** skill 保留 `description`，代理可以自行触发它，其他 skill 也可以调用它。用户仍然可以直接输入它的名称：模型调用始终包含用户调用；description 只会增加代理发现能力，不会剥夺人的调用权。description 是 skill 的顶层上下文指针，会一直加载，以持续的上下文负载换取可发现性。如果一个模型调用 skill 全部由参考信息组成，它也可以成为共享参考信息的归属地，让其他 skill 统一调用。配置方式：省略 `disable-model-invocation`，并写一条面向模型、包含触发分支的 description（`SKILL.md` 中的指针写作规则全部适用）。
- **用户调用（user-invoked）** skill 会把 description 从代理的触达范围中移除：只有输入名称的人可以调用它，其他 skill 不能调用。它不产生上下文负载，但会增加认知负载——你必须记得它存在。配置方式：设置 `disable-model-invocation: true`；description 只面向人类，写成一句摘要，不要列触发词。

只有在代理必须自行触发 skill，或另一个 skill 必须调用它时，才选择模型调用。如果它只会由人手动触发，就设为用户调用，避免持续的上下文负载。

两个用户调用 skill 共同需要的参考信息不能放在其中任何一个 skill 里，因为没有 description，它们无法互相触发。应将其放到 skill 系统之外的普通文件中，让任意 skill 都能指向它。

## 按调用方式拆分

拆分时，调用方式是一个切分维度（顺序切分见 `SKILL.md`）：当你有一个应独立触发的明确引导词——确实会在提示词中使用的触发词——或另一个 skill 必须访问某段内容时，就把它拆成模型调用 skill。新的 description 会始终占用上下文负载，因此这种独立触达必须值得这项成本。

## 路由型 skill

当用户调用 skill 多到难以记住时，可以用**路由型 skill**消除堆积的认知负载：创建一个用户调用 skill，列出其他 skill 以及各自适用的场景，让人只需记住一个入口。它只能提示，不能自动触发其他 skill；用户调用 skill 没有 description，因此只有人可以调用它们。
