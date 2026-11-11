using System.IO;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Text;
using System.Text.Json;

namespace Meow.Windows;

public sealed class CloudClient
{
    private static readonly HttpClient Client = new(new HttpClientHandler { AllowAutoRedirect = false }) { Timeout = TimeSpan.FromMinutes(3) };
    public static Uri Endpoint(string address, string provider = "ark")
    {
        ModelProviders.Get(provider);
        if (!Uri.TryCreate(address.Trim(), UriKind.Absolute, out var uri) || (uri.Scheme != "https" && !(uri.Scheme == "http" && uri.IsLoopback)) || uri.UserInfo.Length > 0 || uri.Query.Length > 0 || uri.Fragment.Length > 0)
            throw new ArgumentException("接口地址必须使用 HTTPS（本机回环地址可使用 HTTP），且不能包含账号、查询参数或片段。");
        string suffix = provider == "anthropic" ? "/messages" : "/chat/completions";
        return uri.AbsolutePath.TrimEnd('/').EndsWith(suffix, StringComparison.Ordinal)
            ? uri : new Uri(uri.AbsoluteUri.TrimEnd('/') + suffix);
    }
    internal static HttpRequestMessage CreateRequest(string address, string model, string key, IEnumerable<Message> messages, bool local = false, bool thinking = false, string provider = "ark")
    {
        if ((!local && string.IsNullOrWhiteSpace(key)) || string.IsNullOrWhiteSpace(model)) throw new ArgumentException("请先在设置中填写密钥和模型名称。");
        var endpoint = local ? LocalEndpoint(address) : Endpoint(address, provider);
        var request = new HttpRequestMessage(HttpMethod.Post, endpoint);
        bool claude = !local && provider == "anthropic";
        if (claude)
        {
            request.Headers.Add("x-api-key", key.Trim());
            request.Headers.Add("anthropic-version", "2023-06-01");
        }
        else if (!local) request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", key.Trim());
        request.Headers.Accept.Add(new MediaTypeWithQualityHeaderValue("text/event-stream"));
        var history = messages.ToArray();
        var payload = new Dictionary<string, object> { ["model"] = model.Trim(), ["messages"] = history, ["stream"] = true };
        payload[!local && provider == "openai" ? "max_completion_tokens" : "max_tokens"] = local ? 1024 : provider == "ark" ? (thinking ? 4096 : 1024) : 8192;
        if (!local && provider == "ark") payload["thinking"] = new { type = thinking ? "enabled" : "disabled" };
        if (!local && provider == "minimax") payload["reasoning_split"] = true;
        if (claude)
        {
            payload["system"] = string.Join("\n\n", history.Where(m => m.role is "system" or "developer").Select(m => m.content));
            payload["messages"] = history.Where(m => m.role is "user" or "assistant").ToArray();
        }
        request.Content = new StringContent(JsonSerializer.Serialize(payload), Encoding.UTF8, "application/json");
        return request;
    }
    public async Task<string> Generate(string address, string model, string key, IEnumerable<Message> messages, Action<string> update, CancellationToken ct, bool local = false, bool thinking = false, string provider = "ark")
    {
        using var request = CreateRequest(address, model, key, messages, local, thinking, provider);
        using var response = await Client.SendAsync(request, HttpCompletionOption.ResponseHeadersRead, ct);
        if (!response.IsSuccessStatusCode) throw new HttpRequestException($"模型服务返回 HTTP {(int)response.StatusCode}，请检查接口、模型、密钥及额度。");
        using var stream = await response.Content.ReadAsStreamAsync(ct);
        using var reader = new StreamReader(stream);
        return await ReadSse(reader, update, ct, !local && provider == "anthropic");
    }
    internal static Uri LocalEndpoint(string address)
    {
        if (!Uri.TryCreate(address, UriKind.Absolute, out var u) || u.Scheme != "http" || !u.IsLoopback || u.UserInfo.Length > 0 || u.Query.Length > 0 || u.Fragment.Length > 0)
            throw new ArgumentException("本地推理仅允许 http://127.0.0.1 或 localhost 回环地址。");
        return new Uri(u.AbsoluteUri.TrimEnd('/') + (u.AbsolutePath.TrimEnd('/').EndsWith("/chat/completions") ? "" : "/chat/completions"));
    }
    internal static async Task<string> ReadSse(TextReader reader, Action<string> update, CancellationToken ct, bool claude = false)
    {
        var text = new StringBuilder(); var data = new StringBuilder(); bool completed = false;
        void Consume()
        {
            if (data.Length == 0) return;
            string payload = data.ToString(); data.Clear();
            if (!claude && payload.Trim() == "[DONE]") { completed = true; return; }
            using var doc = JsonDocument.Parse(payload);
            if (doc.RootElement.TryGetProperty("error", out _)) throw new IOException("模型服务返回错误，请检查设置或稍后重试。");
            if (claude)
            {
                if (!doc.RootElement.TryGetProperty("type", out var type)) return;
                if (type.GetString() == "message_stop") completed = true;
                if (type.GetString() == "message_delta" && doc.RootElement.TryGetProperty("delta", out var end) && end.TryGetProperty("stop_reason", out var reason) && reason.GetString() == "max_tokens")
                    throw new IOException("回复达到模型输出上限，请缩短问题或换一个模型。");
                if (type.GetString() == "content_block_delta" && doc.RootElement.TryGetProperty("delta", out var part) && part.TryGetProperty("type", out var partType) && partType.GetString() == "text_delta")
                {
                    text.Append(part.GetProperty("text").GetString());
                    if (text.Length > 16000) throw new IOException("回复过长，已停止接收。");
                    update(text.ToString());
                }
                return;
            }
            if (!doc.RootElement.TryGetProperty("choices", out var choices)) return;
            foreach (var choice in choices.EnumerateArray())
            {
                if (choice.TryGetProperty("index", out var index) && index.GetInt32() != 0) continue;
                if (choice.TryGetProperty("delta", out var delta) && delta.TryGetProperty("content", out var content) && content.ValueKind == JsonValueKind.String)
                {
                    text.Append(content.GetString());
                    if (text.Length > 16000) throw new IOException("回复过长，已停止接收。");
                    update(text.ToString());
                }
                if (choice.TryGetProperty("finish_reason", out var finish) && finish.ValueKind == JsonValueKind.String)
                {
                    if (finish.GetString() == "length") throw new IOException("回复达到模型输出上限，请缩短问题或换一个模型。");
                    completed = true;
                }
            }
        }
        while (await reader.ReadLineAsync(ct) is { } line)
        {
            if (line.Length == 0) { Consume(); if (completed) break; }
            else if (line.StartsWith("data:", StringComparison.Ordinal))
            {
                if (data.Length > 0) data.Append('\n');
                data.Append(line[5..].TrimStart(' '));
                if (data.Length > 65536) throw new IOException("模型响应数据过大。");
            }
        }
        Consume();
        if (!completed) throw new IOException("回复中途断开，请重试。");
        if (text.Length == 0) throw new IOException("模型没有返回正文。");
        return text.ToString();
    }
}
