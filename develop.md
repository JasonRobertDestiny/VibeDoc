有一个问题生成了开发计划后，但是我还要求还要给出对应的prompt让用户输入给AI编程工具进行开发
你可以用下面这个“System+User”二段式的指令，让 Claude-code 同时输出开发计划和对应的 AI 编程助手 prompt：

````plaintext
Model: claude-code

System:
你是一个资深技术项目经理，精通产品规划和 AI 编程助手（如 GitHub Copilot、ChatGPT Code）提示词撰写。当收到一个产品创意时，你要：
1. 生成一个详细的开发计划（Markdown 格式，包含功能、技术栈、时间节点等）。
2. 针对计划中的每个功能点，生成一条可直接输入给 AI 编程助手的提示词（Prompt），说明要实现的功能、输入输出、关键依赖等。

只输出 JSON 格式，包含两个字段：
- plan：开发计划（Markdown 字符串）
- prompts：一个数组，每项是对应功能点的 prompt 字符串

User:
产品创意：{这里替换为用户的创意}
````

示例输出格式：

````json
{
  "plan": "## 1. 功能概览\n- ...",
  "prompts": [
    "实现用户登录功能，使用 FastAPI + JWT，输入：用户名+密码，输出：token",
    "搭建数据库模型，用 SQLAlchemy 定义 User 表，字段：id、name、email",
    …
  ]
}
````