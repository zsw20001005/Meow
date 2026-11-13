using System.IO;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

namespace Meow.Windows;

public sealed record Message(string role, string content);
public sealed class ReminderConversation
{
    public string Request { get; set; } = "";
    public string Question { get; set; } = "";
    public DateTimeOffset Expires { get; set; }
}
public sealed class NotebookEntry
{
    public Guid Id { get; set; } = Guid.NewGuid();
    public string Title { get; set; } = "";
    public string Body { get; set; } = "";
    public DateTimeOffset Updated { get; set; } = DateTimeOffset.Now;
    public bool Archived { get; set; }
}
public sealed class Experience
{
    public string Day { get; set; } = "";
    public string Kind { get; set; } = "";
    public int Count { get; set; }
}
public sealed class Memo
{
    public Guid Id { get; set; } = Guid.NewGuid();
    public string Title { get; set; } = "";
    public DateTimeOffset Due { get; set; }
    public bool Done { get; set; }
    public bool Cancelled { get; set; }
    public bool Notified { get; set; }
    public override string ToString() => $"{(Cancelled ? "取消" : Done ? "✓" : "○")} {Due.ToLocalTime():MM-dd HH:mm}  {Title}";
}
public sealed class State
{
    public int Version { get; set; } = 1;
    public string BaseUrl { get; set; } = "https://ark.cn-beijing.volces.com/api/plan/v3";
    public string Model { get; set; } = "ark-code-latest";
    public string ProtectedKey { get; set; } = "";
    public string Provider { get; set; } = "ark";
    public Dictionary<string, CloudProfile> CloudProfiles { get; set; } = [];
    public string Memory { get; set; } = "";
    public double Scale { get; set; } = 1;
    public double? Left { get; set; }
    public double? Top { get; set; }
    public double Fullness { get; set; } = 75;
    public double Energy { get; set; } = 80;
    public double Happiness { get; set; } = 75;
    public bool MemoryEnabled { get; set; } = true;
    public bool ThinkingEnabled { get; set; }
    public double ChatterMinutes { get; set; } = 6;
    public List<Experience> Experiences { get; set; } = [];
    public bool Wander { get; set; } = true;
    public bool AutoMemory { get; set; } = true;
    public bool EarlyReminders { get; set; } = true;
    public bool NewsEnabled { get; set; }
    public bool Proactive { get; set; }
    public bool NightSleep { get; set; } = true;
    public bool WindowJump { get; set; }
    public bool LocalModel { get; set; }
    public string LocalUrl { get; set; } = "http://127.0.0.1:8080/v1";
    public string LocalModelName { get; set; } = "local";
    public string WallSide { get; set; } = "";
    public string LastNewsSlot { get; set; } = "";
    public DateTimeOffset LastEarlyCheck { get; set; }
    public List<MemoryFact> Facts { get; set; } = [];
    public List<NewsItem> News { get; set; } = [];
    public MailState Mail { get; set; } = new();
    public List<Message> History { get; set; } = [];
    public ReminderConversation? PendingReminder { get; set; }
    public List<Memo> Memos { get; set; } = [];
    public List<NotebookEntry> Notes { get; set; } = [];
}
public sealed class Store
{
    private readonly string file;
    public State Data { get; }
    public string DirectoryPath { get; }
    public Store(string? directory = null)
    {
        DirectoryPath = directory ?? Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Meow.Windows");
        Directory.CreateDirectory(DirectoryPath);
        file = Path.Combine(DirectoryPath, "state.json");
        Data = File.Exists(file) ? JsonSerializer.Deserialize<State>(File.ReadAllText(file)) ?? throw new InvalidDataException("存档内容为空。") : new State();
        if (Data.Version != 1 || Data.History is null || Data.Memos is null) throw new InvalidDataException("存档版本或内容不兼容，请保留 state.json 后检查。");
        if (!double.IsFinite(Data.Scale) || Data.Scale < .5 || Data.Scale > 1.5) Data.Scale = 1;
    }
    public void Save()
    {
        var temp = file + ".tmp";
        File.WriteAllText(temp, JsonSerializer.Serialize(Data, new JsonSerializerOptions { WriteIndented = true }));
        File.Move(temp, file, true);
    }
    public string ReadKey() => Data.ProtectedKey.Length == 0 ? "" : Secret.Unprotect(Data.ProtectedKey);
    public CloudProfile Profile(string provider)
    {
        var preset = ModelProviders.Get(provider);
        if (provider == Data.Provider) return new(Data.BaseUrl, Data.Model, Data.ProtectedKey);
        return Data.CloudProfiles.TryGetValue(provider, out var saved) ? saved : new(preset.BaseUrl, "", "");
    }
    internal string ProfileKey(string provider, string address)
    {
        var saved = Profile(provider);
        if (saved.ProtectedKey.Length == 0) return "";
        if (CloudClient.Endpoint(saved.BaseUrl, provider).GetLeftPart(UriPartial.Authority) != CloudClient.Endpoint(address, provider).GetLeftPart(UriPartial.Authority))
            throw new ArgumentException("接口域名已改变，请重新填写该地址对应的 API Key。");
        return Secret.Unprotect(saved.ProtectedKey);
    }
    public void SaveProfile(string provider, string address, string model, string newKey)
    {
        CloudClient.Endpoint(address, provider);
        if (string.IsNullOrWhiteSpace(model)) throw new ArgumentException("请填写模型名称。");
        var previous = Profile(Data.Provider); var previousId = Data.Provider; bool previousLocal = Data.LocalModel;
        var profiles = new Dictionary<string, CloudProfile>(Data.CloudProfiles);
        string secret = string.IsNullOrWhiteSpace(newKey) ? ProfileKey(provider, address) : newKey.Trim();
        if (secret.Length == 0) throw new ArgumentException("请填写该服务商的 API Key。");
        var current = new CloudProfile(address.Trim(), model.Trim(), Secret.Protect(secret));
        Data.CloudProfiles[previousId] = previous; Data.CloudProfiles[provider] = current;
        Data.Provider = provider; Data.BaseUrl = current.BaseUrl; Data.Model = current.Model; Data.ProtectedKey = current.ProtectedKey; Data.LocalModel = false;
        try { Save(); }
        catch { Data.CloudProfiles = profiles; Data.Provider = previousId; Data.BaseUrl = previous.BaseUrl; Data.Model = previous.Model; Data.ProtectedKey = previous.ProtectedKey; Data.LocalModel = previousLocal; throw; }
    }
}
// DPAPI binds the encrypted value to the current Windows account. No key is stored in plaintext.
internal static class Secret
{
    [StructLayout(LayoutKind.Sequential)] private struct Blob { public int Length; public IntPtr Data; }
    [DllImport("crypt32.dll", SetLastError = true, CharSet = CharSet.Unicode)]
    private static extern bool CryptProtectData(ref Blob input, string? description, IntPtr entropy, IntPtr reserved, IntPtr prompt, int flags, out Blob output);
    [DllImport("crypt32.dll", SetLastError = true)]
    private static extern bool CryptUnprotectData(ref Blob input, IntPtr description, IntPtr entropy, IntPtr reserved, IntPtr prompt, int flags, out Blob output);
    [DllImport("kernel32.dll")] private static extern IntPtr LocalFree(IntPtr memory);
    public static string Protect(string value) => Convert.ToBase64String(Transform(Encoding.UTF8.GetBytes(value), true));
    public static string Unprotect(string value) => Encoding.UTF8.GetString(Transform(Convert.FromBase64String(value), false));
    private static byte[] Transform(byte[] bytes, bool protect)
    {
        var input = new Blob { Length = bytes.Length, Data = Marshal.AllocHGlobal(bytes.Length) };
        try
        {
            Marshal.Copy(bytes, 0, input.Data, bytes.Length);
            Blob output;
            bool ok = protect ? CryptProtectData(ref input, null, IntPtr.Zero, IntPtr.Zero, IntPtr.Zero, 1, out output)
                : CryptUnprotectData(ref input, IntPtr.Zero, IntPtr.Zero, IntPtr.Zero, IntPtr.Zero, 1, out output);
            if (!ok) throw new CryptographicException(Marshal.GetLastWin32Error());
            try { var result = new byte[output.Length]; Marshal.Copy(output.Data, result, 0, result.Length); return result; }
            finally { LocalFree(output.Data); }
        }
        finally { Marshal.FreeHGlobal(input.Data); CryptographicOperations.ZeroMemory(bytes); }
    }
}
