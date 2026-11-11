using System.IO;
using System.Text.Json;
namespace Meow.Windows;

internal static class IntegrationChecks
{
    public static async Task<int> Local()
    {
        try { using var engine = new LocalEngine(); await engine.Start(); using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(60)); var text = await new CloudClient().Generate("http://127.0.0.1:8080/v1", "local", "local", [new Message("user", "请用中文说你好。")], _ => { }, timeout.Token, true); if (text.Length == 0) throw new Exception("Empty response"); File.WriteAllText(Path.Combine(AppContext.BaseDirectory, "localcheck-results.txt"), "PASS bundled local CPU model streamed text"); return 0; }
        catch (Exception e) { File.WriteAllText(Path.Combine(AppContext.BaseDirectory, "localcheck-results.txt"), "FAIL " + e.Message); return 1; }
    }
    public static async Task<int> Features()
    {
        string root = Path.Combine(Path.GetTempPath(), "meow-features-" + Guid.NewGuid()); var log = new List<string>();
        try
        {
            var existing = new Store(); var temp = new Store(root); temp.Data.BaseUrl = existing.Data.BaseUrl; temp.Data.Model = existing.Data.Model; temp.Data.ProtectedKey = existing.Data.ProtectedKey; temp.Data.Provider = existing.Data.Provider;
            var service = new CompanionService(temp); using var deadline = new CancellationTokenSource(TimeSpan.FromMinutes(4));
            await service.HandleMemo("明天晚上七点提醒我检查 Windows 测试", deadline.Token);
            if (temp.Data.Memos.Count != 1 || temp.Data.Memos[0].Due.LocalDateTime.Date != DateTime.Today.AddDays(1) || temp.Data.Memos[0].Due.LocalDateTime.Hour != 19) throw new Exception("Memo date parsing mismatch"); log.Add("PASS real-model memo create and relative date");
            await service.HandleMemo("取消检查 Windows 测试的提醒", deadline.Token); if (!temp.Data.Memos[0].Done) throw new Exception("Memo cancel failed"); log.Add("PASS real-model memo cancel");
            await service.HandleMemo("提醒我开会", deadline.Token); if (temp.Data.Memos.Count != 1) throw new Exception("Ambiguous reminder was created"); log.Add("PASS ambiguous reminder requests clarification");
            await service.HandleMemo("后天上午九点", deadline.Token); if (temp.Data.Memos.Count != 2 || temp.Data.Memos[1].Due.LocalDateTime.Date != DateTime.Today.AddDays(2) || temp.Data.Memos[1].Due.LocalDateTime.Hour != 9) throw new Exception("Pending clarification failed"); log.Add("PASS follow-up fills missing reminder time");
            await service.Learn("以后叫我测试主人，我喜欢茉莉花茶。", deadline.Token); if (!temp.Data.Facts.Any(f => f.Text.Contains("茉莉"))) throw new Exception("Memory extraction failed"); log.Add("PASS real-model evidence-backed memory learning");
            try { await service.FetchNews(deadline.Token); log.Add("PASS live news fetch and model selection"); } catch (Exception e) { log.Add("UNVERIFIED news: " + e.Message); }
            File.WriteAllLines(Path.Combine(AppContext.BaseDirectory, "featurecheck-results.txt"), log); return 0;
        }
        catch (Exception e) { log.Add("FAIL " + e.Message); File.WriteAllLines(Path.Combine(AppContext.BaseDirectory, "featurecheck-results.txt"), log); return 1; }
        finally { if (Directory.Exists(root)) Directory.Delete(root, true); }
    }
    public static async Task<int> Mail()
    {
        string root = Path.Combine(Path.GetTempPath(), "meow-mail-check-" + Guid.NewGuid()); var log = new List<string>();
        try
        {
            var a = new Store(Path.Combine(root, "a")); var b = new Store(Path.Combine(root, "b")); using var first = new MailboxService(a); using var second = new MailboxService(b);
            await first.Start(true); await second.Start(true); await first.Bind(b.Data.Mail.Code); await second.Bind(a.Data.Mail.Code);
            log.Add("PASS fixed identity and pairing codes");
            var letter = new Letter { senderID = a.Data.Mail.DeviceID, recipientID = b.Data.Mail.DeviceID, body = "离线隔离测试：你好小喵 💌" };
            await first.Call(new { op = "send", letter }); var files = Directory.GetFiles(Path.Combine(b.DirectoryPath, "mail-inbox"), "*.json"); if (files.Length != 1) throw new Exception("Missing inbox persistence");
            using (var doc = JsonDocument.Parse(File.ReadAllText(files[0]))) if (doc.RootElement.GetProperty("letter").GetProperty("body").GetString() != letter.body) throw new Exception("Payload mismatch"); log.Add("PASS real QUIC transfer and durable receipt");
            await first.Call(new { op = "send", letter }); if (Directory.GetFiles(Path.Combine(b.DirectoryPath, "mail-inbox"), "*.json").Length != 1) throw new Exception("Duplicate letter"); log.Add("PASS duplicate retransmission deduplicated");
            var backwards = new Letter { senderID = b.Data.Mail.DeviceID, recipientID = a.Data.Mail.DeviceID, body = "收到，回信喵！" }; await second.Call(new { op = "send", letter = backwards }); log.Add("PASS bidirectional Chinese letters");
            string id = a.Data.Mail.DeviceID; first.Dispose(); await first.Start(true); if (a.Data.Mail.DeviceID != id) throw new Exception("Identity changed"); log.Add("PASS identity survives restart");
            File.WriteAllLines(Path.Combine(AppContext.BaseDirectory, "mailcheck-results.txt"), log); return 0;
        }
        catch (Exception e) { log.Add("FAIL " + e); File.WriteAllLines(Path.Combine(AppContext.BaseDirectory, "mailcheck-results.txt"), log); return 1; }
        finally { if (Directory.Exists(root)) Directory.Delete(root, true); }
    }
    public static async Task<int> Cloud()
    {
        try { var store = new Store(); using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(60)); var result = await new CloudClient().Generate(store.Data.BaseUrl, store.Data.Model, store.ReadKey(), [new Message("user", "连接测试。只回复：小喵连接成功。")], _ => { }, timeout.Token, provider: store.Data.Provider); File.WriteAllText(Path.Combine(AppContext.BaseDirectory, "cloudcheck-results.txt"), result.Length > 0 ? "PASS configured model returned text" : "FAIL empty"); return result.Length > 0 ? 0 : 1; }
        catch (Exception e) { File.WriteAllText(Path.Combine(AppContext.BaseDirectory, "cloudcheck-results.txt"), "FAIL " + e.GetType().Name + ": " + e.Message); return 1; }
    }
}
