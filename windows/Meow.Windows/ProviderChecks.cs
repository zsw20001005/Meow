using System.IO;
using System.Text.Json;

namespace Meow.Windows;

internal static class ProviderChecks
{
    internal static void Run(Action<bool, string> check, Store store)
    {
        Message[] history = [new("system", "你是小喵"), new("user", "你好"), new("assistant", "喵"), new("user", "再说一句")];
        foreach (var provider in ModelProviders.All)
        {
            string url = provider.Id == "custom" ? "https://example.com/v1" : provider.BaseUrl;
            using var request = CloudClient.CreateRequest(url, "test-model", "fake-key", history, thinking: true, provider: provider.Id);
            using var body = JsonDocument.Parse(request.Content!.ReadAsStringAsync().GetAwaiter().GetResult()); var r = body.RootElement;
            bool claude = provider.Id == "anthropic";
            check(request.RequestUri!.AbsolutePath.EndsWith(claude ? "/messages" : "/chat/completions") &&
                (claude ? request.Headers.Authorization is null && request.Headers.GetValues("x-api-key").Single() == "fake-key" && request.Headers.GetValues("anthropic-version").Single() == "2023-06-01"
                    : request.Headers.Authorization?.ToString() == "Bearer fake-key") &&
                r.GetProperty("model").GetString() == "test-model" && r.GetProperty("stream").GetBoolean() &&
                r.TryGetProperty("thinking", out _) == (provider.Id == "ark"), provider.Id + " endpoint, auth and isolated payload");
            if (provider.Id == "openai") check(r.TryGetProperty("max_completion_tokens", out _) && !r.TryGetProperty("max_tokens", out _) && !r.TryGetProperty("reasoning_effort", out _), "GPT token parameter; model-default reasoning");
            if (claude) check(r.GetProperty("system").GetString() == "你是小喵" && r.GetProperty("messages").GetArrayLength() == 3 && r.GetProperty("messages")[0].GetProperty("role").GetString() == "user", "Claude system separated; conversation preserved");
            if (provider.Id == "minimax") check(r.GetProperty("reasoning_split").GetBoolean(), "MiniMax reasoning separated from answer");
            check(CloudClient.Endpoint(request.RequestUri.ToString(), provider.Id) == request.RequestUri, provider.Id + " full endpoint preserved");
        }
        using (var request = CloudClient.CreateRequest("http://127.0.0.1:8080/v1", "local", "never-send", history, local: true, provider: "anthropic"))
        {
            using var body = JsonDocument.Parse(request.Content!.ReadAsStringAsync().GetAwaiter().GetResult());
            check(request.Headers.Authorization is null && !request.Headers.Contains("x-api-key") && !body.RootElement.TryGetProperty("thinking", out _) && request.RequestUri!.AbsolutePath == "/v1/chat/completions", "local mode sends no cloud credentials or vendor parameters");
        }
        foreach (string address in new[] { "http://127.0.0.1:8317/v1", "http://localhost:8317/v1", "http://[::1]:8317/v1" })
        {
            using var request = CloudClient.CreateRequest(address, "test-model", "local-proxy-key", history, provider: "openai");
            using var body = JsonDocument.Parse(request.Content!.ReadAsStringAsync().GetAwaiter().GetResult());
            check(request.RequestUri!.IsLoopback && request.RequestUri.AbsolutePath == "/v1/chat/completions" &&
                request.Headers.Authorization?.ToString() == "Bearer local-proxy-key" && body.RootElement.TryGetProperty("max_completion_tokens", out _),
                "loopback proxy keeps client authentication and OpenAI request format");
        }
        foreach (string address in new[] { "http://example.com/v1", "http://192.168.1.2/v1", "http://localhost.example.com/v1", "http://user:pass@127.0.0.1/v1", "http://127.0.0.1/v1?key=secret", "http://127.0.0.1/v1#secret" })
        {
            bool rejected = false;
            try { CloudClient.Endpoint(address, "openai"); } catch (ArgumentException) { rejected = true; }
            check(rejected, "proxy endpoint rejects remote HTTP, credentials, queries and fragments");
        }
        const string claudeSse = "event: ping\ndata: {\"type\":\"ping\"}\n\nevent: content_block_delta\ndata: {\"type\":\"content_block_delta\",\"delta\":{\"type\":\"thinking_delta\",\"thinking\":\"private\"}}\n\ndata: {\"type\":\"content_block_delta\",\"delta\":{\"type\":\"text_delta\",\"text\":\"你好\"}}\n\ndata: {\"type\":\"content_block_delta\",\"delta\":{\"type\":\"text_delta\",\"text\":\"喵\"}}\n\ndata: {\"type\":\"message_delta\",\"delta\":{\"stop_reason\":\"end_turn\"}}\n\ndata: {\"type\":\"message_stop\"}\n\n";
        var updates = new List<string>();
        check(CloudClient.ReadSse(new StringReader(claudeSse), updates.Add, default, true).GetAwaiter().GetResult() == "你好喵" && updates.SequenceEqual(new[] { "你好", "你好喵" }), "Claude streams text, ignores thinking and ping, waits for message_stop");
        foreach (var sample in new[] {
            (false, "data: {\"error\":{\"message\":\"secret\"}}\n\n"),
            (false, "data: {\"choices\":[{\"delta\":{\"content\":\"partial\"},\"finish_reason\":\"length\"}]}\n\n"),
            (true, "data: {\"type\":\"error\",\"error\":{\"type\":\"overloaded_error\"}}\n\n"),
            (true, claudeSse.Replace("data: {\"type\":\"message_stop\"}\n\n", "")),
            (true, claudeSse.Replace("end_turn", "max_tokens")),
            (true, "data: {\"type\":\"message_stop\"}\n\n") })
        {
            bool rejected = false;
            try { CloudClient.ReadSse(new StringReader(sample.Item2), _ => { }, default, sample.Item1).GetAwaiter().GetResult(); }
            catch (IOException) { rejected = true; }
            check(rejected, "stream rejects errors, truncated or empty answers");
        }
        using (var ct = new CancellationTokenSource())
        {
            ct.Cancel(); bool cancelled = false;
            try { CloudClient.ReadSse(new StringReader(claudeSse), _ => { }, ct.Token, true).GetAwaiter().GetResult(); }
            catch (OperationCanceledException) { cancelled = true; }
            check(cancelled, "stream cancellation");
        }
        var legacy = JsonSerializer.Deserialize<State>("{\"BaseUrl\":\"https://example.com/v3\",\"Model\":\"legacy-model\",\"ProtectedKey\":\"encrypted\"}")!;
        check(legacy.Provider == "ark" && legacy.CloudProfiles.Count == 0 && legacy.Model == "legacy-model", "legacy config defaults to Ark without losing values");
        var original = store.Profile("ark");
        check(store.Profile("openai").ProtectedKey.Length == 0 && store.Profile("openai").Model.Length == 0, "new provider never inherits previous key or model");
        store.SaveProfile("openai", ModelProviders.Get("openai").BaseUrl, "account-model", "fake-openai-secret");
        store = new Store(store.DirectoryPath);
        check(store.Data.Provider == "openai" && store.ReadKey() == "fake-openai-secret" && store.Profile("ark") == original, "provider settings persist independently");
        bool changedHost = false;
        try { store.ProfileKey("openai", "https://different.example/v1"); } catch (ArgumentException) { changedHost = true; }
        check(changedHost, "changing endpoint host requires explicit key");
        store.SaveProfile("ark", original.BaseUrl, original.Model, "");
        check(store.ReadKey() == "test-secret-猫" && store.Data.Provider == "ark" && store.Profile("openai").Model == "account-model", "switch back restores original provider and key");
        bool missingKey = false;
        try { store.SaveProfile("anthropic", ModelProviders.Get("anthropic").BaseUrl, "account-model", ""); } catch (ArgumentException) { missingKey = true; }
        check(missingKey && store.Data.Provider == "ark", "missing provider key leaves active configuration intact");
        check(!File.ReadAllText(Path.Combine(store.DirectoryPath, "state.json")).Contains("fake-openai-secret"), "all saved provider keys encrypted");
    }
}
