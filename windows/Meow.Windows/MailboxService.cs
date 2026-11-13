using System.Collections.Concurrent;
using System.Diagnostics;
using System.IO;
using System.Security.Cryptography;
using System.Text.Json;
using System.Text.Json.Nodes;

namespace Meow.Windows;

public sealed class Letter
{
    public string id { get; set; } = Guid.NewGuid().ToString();
    public string senderID { get; set; } = "";
    public string recipientID { get; set; } = "";
    public string body { get; set; } = "";
    public string createdAt { get; set; } = DateTimeOffset.UtcNow.ToString("yyyy-MM-dd'T'HH:mm:ss'Z'");
}
public sealed class MailEntry
{
    public Letter Letter { get; set; } = new();
    public bool Incoming { get; set; }
    public bool Read { get; set; }
    public bool Delivered { get; set; }
    public bool Cancelled { get; set; }
    public override string ToString() => $"{(Incoming ? (Read ? "已读" : "未读") : Delivered ? "已送达" : Cancelled ? "已取消" : "待寄")} · {Letter.body[..Math.Min(35, Letter.body.Length)]}";
}
public sealed class MailState
{
    public MailDraft? Draft { get; set; }
    public bool Enabled { get; set; }
    public string Secret { get; set; } = "";
    public string DeviceID { get; set; } = "";
    public string Code { get; set; } = "";
    public string PeerCode { get; set; } = "";
    public string PeerID { get; set; } = "";
    public List<MailEntry> Entries { get; set; } = [];
}
public sealed class MailDraft
{
    public string Id { get; set; } = Guid.NewGuid().ToString();
    public string Body { get; set; } = "";
    public string PeerID { get; set; } = "";
}
public sealed class MailboxService(Store store) : IDisposable
{
    private Process? process;
    private int counter;
    private bool busy;
    private readonly ConcurrentDictionary<int, TaskCompletionSource<JsonElement>> pending = new();
    public string Error { get; private set; } = "";
    public int Unread => store.Data.Mail.Entries.Count(x => x.Incoming && !x.Read);
    public async Task<JsonElement> Call(object message)
    {
        if (process is null || process.HasExited) throw new IOException("信箱辅助进程未运行。");
        int id = Interlocked.Increment(ref counter); var node = JsonSerializer.SerializeToNode(message)!.AsObject(); node["id"] = id;
        var completion = new TaskCompletionSource<JsonElement>(TaskCreationOptions.RunContinuationsAsynchronously); pending[id] = completion;
        try { await process.StandardInput.WriteLineAsync(node.ToJsonString()); return await completion.Task.WaitAsync(TimeSpan.FromSeconds(35)); } finally { pending.TryRemove(id, out _); }
    }
    public async Task Start(bool localOnly = false)
    {
        if (process is { HasExited: false }) return;
        string directory = Path.Combine(AppContext.BaseDirectory, "mailbridge");
        if (!File.Exists(Path.Combine(directory, "node.exe")) || !File.Exists(Path.Combine(directory, "bridge.mjs")))
            throw new IOException("尚未安装信箱扩展包。请安装到噜噜所在目录，重启后即可通信；历史信件和草稿会保留。");
        var info = new ProcessStartInfo(Path.Combine(directory, "node.exe")) { UseShellExecute = false, CreateNoWindow = true, RedirectStandardInput = true, RedirectStandardOutput = true, RedirectStandardError = true }; info.ArgumentList.Add(Path.Combine(directory, "bridge.mjs"));
        process = Process.Start(info) ?? throw new IOException("无法启动通信模块。"); var current = process;
        _ = Task.Run(async () => { try { while (await current.StandardOutput.ReadLineAsync() is { } line) { using var doc = JsonDocument.Parse(line); var r = doc.RootElement; if (pending.TryGetValue(r.GetProperty("id").GetInt32(), out var t)) { if (r.TryGetProperty("error", out var e)) t.TrySetException(new IOException(e.GetString())); else t.TrySetResult(r.GetProperty("result").Clone()); } } } finally { foreach (var t in pending.Values) t.TrySetException(new IOException("信箱进程已关闭。")); } });
        _ = Task.Run(async () => { while (await current.StandardError.ReadLineAsync() is not null) { } });
        if (store.Data.Mail.Secret.Length == 0) { store.Data.Mail.Secret = Secret.Protect(Convert.ToBase64String(RandomNumberGenerator.GetBytes(32))); store.Save(); }
        try
        {
            var result = await Call(new { op = "init", key = Secret.Unprotect(store.Data.Mail.Secret), inbox = Path.Combine(store.DirectoryPath, "mail-inbox"), localOnly });
            store.Data.Mail.DeviceID = result.GetProperty("deviceID").GetString()!; store.Data.Mail.Code = result.GetProperty("code").GetString()!; store.Save();
            if (store.Data.Mail.PeerCode.Length > 0) await Bind(store.Data.Mail.PeerCode);
        }
        catch { Dispose(); throw; }
    }
    public async Task Bind(string code)
    {
        var result = await Call(new { op = "peer", code }); string old = store.Data.Mail.PeerID;
        store.Data.Mail.PeerCode = code; store.Data.Mail.PeerID = result.ValueKind == JsonValueKind.Null ? "" : result.GetProperty("deviceID").GetString()!;
        if (old != store.Data.Mail.PeerID) foreach (var e in store.Data.Mail.Entries.Where(x => !x.Incoming && !x.Delivered)) e.Cancelled = true;
        store.Save();
    }
    public MailEntry Queue(string body, string? id = null)
    {
        if (string.IsNullOrWhiteSpace(body) || body.Length > 5000 || System.Text.Encoding.UTF8.GetByteCount(body) > 16384) throw new ArgumentException("信件最多5000字且不能为空。");
        if (store.Data.Mail.PeerID.Length == 0) throw new ArgumentException("请先绑定对方设备。");
        if (id is not null && !Guid.TryParse(id, out _)) throw new ArgumentException("无效的信件编号。");
        if (id is not null && store.Data.Mail.Entries.FirstOrDefault(e => !e.Incoming && e.Letter.id == id) is { } existing) return existing;
        var entry = new MailEntry { Letter = new Letter { id = id ?? Guid.NewGuid().ToString(), senderID = store.Data.Mail.DeviceID, recipientID = store.Data.Mail.PeerID, body = body } };
        store.Data.Mail.Entries.Add(entry); try { store.Save(); } catch { store.Data.Mail.Entries.Remove(entry); throw; }
        return entry;
    }
    public async Task Tick()
    {
        if (!store.Data.Mail.Enabled || busy) return; busy = true;
        try
        {
            await Start();
            string inbox = Path.Combine(store.DirectoryPath, "mail-inbox");
            foreach (var file in Directory.EnumerateFiles(inbox, "*.json"))
            {
                using var doc = JsonDocument.Parse(await File.ReadAllTextAsync(file)); var letter = doc.RootElement.GetProperty("letter").Deserialize<Letter>()!;
                if (!store.Data.Mail.Entries.Any(x => x.Letter.id.Equals(letter.id, StringComparison.OrdinalIgnoreCase))) store.Data.Mail.Entries.Add(new MailEntry { Incoming = true, Delivered = true, Letter = letter });
            }
            store.Save();
            foreach (var entry in store.Data.Mail.Entries.Where(x => !x.Incoming && !x.Delivered && !x.Cancelled && x.Letter.recipientID == store.Data.Mail.PeerID).Take(3).ToArray())
            { await Call(new { op = "send", letter = entry.Letter }); entry.Delivered = true; store.Save(); }
            Error = "";
        }
        catch (Exception e) { Error = e.Message; }
        finally { busy = false; }
    }
    public void Dispose() { if (process is null) return; try { process.StandardInput.Close(); if (!process.WaitForExit(500)) process.Kill(true); } catch { } process.Dispose(); process = null; }
}
