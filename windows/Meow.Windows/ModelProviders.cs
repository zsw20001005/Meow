namespace Meow.Windows;

public sealed record ModelProvider(string Id, string Name, string BaseUrl, string Docs)
{
    public override string ToString() => Name;
}

public static class ModelProviders
{
    // Models are entered from the user's account, rather than hardcoding expiring model IDs.
    public static readonly ModelProvider[] All =
    [
        new("ark", "豆包 · 火山方舟", "https://ark.cn-beijing.volces.com/api/plan/v3", "https://www.volcengine.com/docs/82379"),
        new("openai", "OpenAI · GPT", "https://api.openai.com/v1", "https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create"),
        new("anthropic", "Anthropic · Claude", "https://api.anthropic.com/v1", "https://platform.claude.com/docs/en/api/messages/create"),
        new("gemini", "Google · Gemini", "https://generativelanguage.googleapis.com/v1beta/openai", "https://ai.google.dev/gemini-api/docs/openai"),
        new("deepseek", "DeepSeek", "https://api.deepseek.com/v1", "https://api-docs.deepseek.com/"),
        new("qwen", "通义千问 · 百炼", "https://dashscope.aliyuncs.com/compatible-mode/v1", "https://help.aliyun.com/en/model-studio/base-url"),
        new("kimi", "月之暗面 · Kimi", "https://api.moonshot.cn/v1", "https://platform.kimi.com/blog/posts/kimi-api-quick-start-guide"),
        new("glm", "智谱 · GLM", "https://open.bigmodel.cn/api/paas/v4", "https://docs.bigmodel.cn/api-reference/模型-api/对话补全"),
        new("grok", "xAI · Grok", "https://api.x.ai/v1", "https://docs.x.ai/developers/rest-api-reference/inference/chat-completions"),
        new("minimax", "MiniMax", "https://api.minimax.io/v1", "https://platform.minimax.io/docs/api-reference/text-openai-api"),
        new("siliconflow", "硅基流动", "https://api.siliconflow.cn/v1", "https://docs.siliconflow.cn/docs/api/chat-completions-post"),
        new("openrouter", "OpenRouter", "https://openrouter.ai/api/v1", "https://openrouter.ai/docs/api/api-reference/chat/send-chat-completion-request"),
        new("custom", "自定义 · OpenAI 兼容", "", "https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create")
    ];
    public static ModelProvider Get(string id) => All.FirstOrDefault(p => p.Id == id) ?? throw new ArgumentException("未知模型服务商，请在设置中重新选择。");
}

public sealed record CloudProfile(string BaseUrl, string Model, string ProtectedKey);
