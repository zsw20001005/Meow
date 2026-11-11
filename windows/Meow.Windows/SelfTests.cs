using System.IO;

namespace Meow.Windows;

internal static class SelfTests
{
    public static int Run()
    {
        string dir = Path.Combine(Path.GetTempPath(), "meow-tests-" + Guid.NewGuid());
        var results = new List<string>();
        void Check(bool ok, string name) { if (!ok) throw new Exception(name); results.Add("PASS " + name); }
        try
        {
            Check(CloudClient.Endpoint("https://example.com/api/v3").AbsolutePath == "/api/v3/chat/completions", "endpoint append");
            Check(CloudClient.Endpoint("https://example.com/chat/completions").AbsolutePath == "/chat/completions", "endpoint preserved");
            foreach (var bad in new[] { "http://example.com", "https://user:pass@example.com", "https://example.com?a=1", "https://example.com/#key" })
            { bool rejected = false; try { CloudClient.Endpoint(bad); } catch (ArgumentException) { rejected = true; } Check(rejected, "reject invalid endpoint"); }
            const string sse = "data: {\"choices\":[{\"delta\":{\"reasoning_content\":\"private\"}}]}\n\ndata: {\"choices\":[{\"delta\":{\"content\":\"你好喵\"}}]}\n\ndata: [DONE]\n\n";
            Check(CloudClient.ReadSse(new StringReader(sse), _ => { }, default).GetAwaiter().GetResult() == "你好喵", "SSE ignores reasoning and reads Chinese");
            bool interrupted = false; try { CloudClient.ReadSse(new StringReader("data: {\"choices\":[{\"delta\":{\"content\":\"半句\"}}]}\n\n"), _ => { }, default).GetAwaiter().GetResult(); } catch (IOException) { interrupted = true; }
            Check(interrupted, "truncated SSE rejected");
            Check(Commands.Action("打个滚给我看") == "roll" && Commands.Action("不要打滚") is null && Commands.Action("讲个小猫跳舞的故事") is null, "explicit commands only");
            Check(Commands.Action("跳上窗口") == "climb" && Commands.Action("如果明天跳上窗口") is null && Commands.Action("伸个懒腰吧") == "stretch", "extended actions stay explicit");
            Check(Commands.Action("张噜噜，笑一个吧") == "emotion:happy" && Commands.Action("噜噜，装生气") == "emotion:angry" && Commands.Action("不要装生气") is null && Commands.Action("讲个害羞的故事") is null, "Lulu expressions honor names and reject negations/stories");
            Check(CloudClient.LocalEndpoint("http://127.0.0.1:8080/v1").AbsolutePath == "/v1/chat/completions", "local endpoint");
            bool remote = false; try { CloudClient.LocalEndpoint("http://example.com/v1"); } catch (ArgumentException) { remote = true; }
            Check(remote, "local mode rejects remote hosts");
            using (var plan = CompanionService.Json("```json\n{\"operation\":\"ask\"}\n```")) Check(plan.RootElement.GetProperty("operation").GetString() == "ask", "structured plan parsing");
            var store = new Store(dir); store.Data.ProtectedKey = Secret.Protect("test-secret-猫"); store.Data.Memory = "喜欢茉莉花茶"; store.Data.Memos.Add(new Memo { Title = "测试", Due = DateTimeOffset.Now.AddMinutes(2) }); store.Save();
            var reopened = new Store(dir); Check(reopened.ReadKey() == "test-secret-猫", "DPAPI roundtrip"); Check(!File.ReadAllText(Path.Combine(dir, "state.json")).Contains("test-secret"), "no plaintext secret"); Check(reopened.Data.Memory == "喜欢茉莉花茶" && reopened.Data.Memos.Count == 1, "persistence roundtrip");
            ProviderChecks.Run(Check, reopened);
            ConversationChecks.Run(Check);
            File.WriteAllText(Path.Combine(dir, "state.json"), "broken"); bool corrupt = false; try { _ = new Store(dir); } catch (System.Text.Json.JsonException) { corrupt = true; }
            Check(corrupt, "corrupt store not overwritten");
            results.Add("All checks passed."); File.WriteAllLines(Path.Combine(AppContext.BaseDirectory, "selftest-results.txt"), results); return 0;
        }
        catch (Exception e) { results.Add("FAIL " + e); File.WriteAllLines(Path.Combine(AppContext.BaseDirectory, "selftest-results.txt"), results); return 1; }
        finally { if (Directory.Exists(dir)) Directory.Delete(dir, true); }
    }
}
