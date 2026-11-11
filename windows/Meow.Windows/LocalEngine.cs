using System.Diagnostics;
using System.IO;
using System.Net.Http;
namespace Meow.Windows;

internal sealed class LocalEngine : IDisposable
{
    private Process? process;
    public async Task Start()
    {
        if (process is { HasExited: false }) return;
        using (var existing = new HttpClient { Timeout = TimeSpan.FromSeconds(1) }) { try { using var response = await existing.GetAsync("http://127.0.0.1:8080/health"); if (response.IsSuccessStatusCode) return; } catch (HttpRequestException) { } catch (TaskCanceledException) { } }
        string root = Path.Combine(AppContext.BaseDirectory, "local-engine");
        string exe = Directory.Exists(root) ? Directory.EnumerateFiles(root, "llama-server.exe", SearchOption.AllDirectories).FirstOrDefault() ?? "" : "";
        string model = Path.Combine(root, "model.gguf");
        if (!File.Exists(exe) || !File.Exists(model)) throw new IOException("请先运行 scripts/prepare_windows_local.ps1，并将 local-engine 目录放在 Meow.exe 旁。");
        var start = new ProcessStartInfo(exe) { UseShellExecute = false, CreateNoWindow = true, WorkingDirectory = Path.GetDirectoryName(exe)!, RedirectStandardError = true, RedirectStandardOutput = true };
        foreach (string arg in new[] { "-m", model, "--host", "127.0.0.1", "--port", "8080", "-c", "4096", "--alias", "local" }) start.ArgumentList.Add(arg);
        process = Process.Start(start) ?? throw new IOException("本地推理服务启动失败。"); var current = process;
        _ = Task.Run(async () => { while (await current.StandardError.ReadLineAsync() is not null) { } }); _ = Task.Run(async () => { while (await current.StandardOutput.ReadLineAsync() is not null) { } });
        using var http = new HttpClient { Timeout = TimeSpan.FromSeconds(2) };
        for (int i = 0; i < 60; i++) { if (current.HasExited) throw new IOException("本地服务退出，请检查端口或 CPU 兼容性。"); try { using var response = await http.GetAsync("http://127.0.0.1:8080/health"); if (response.IsSuccessStatusCode) return; } catch (HttpRequestException) { } catch (TaskCanceledException) { } await Task.Delay(500); }
        Dispose(); throw new TimeoutException("本地模型加载超时。");
    }
    public void Dispose() { if (process is null) return; try { if (!process.HasExited) process.Kill(true); } catch { } process.Dispose(); process = null; }
}
