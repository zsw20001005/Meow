using System.Collections.Concurrent;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.Reflection;
using System.Text;
using System.Text.Json;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Threading;

namespace Meow.Windows;

// Runs the actual chat UI handler against an isolated loopback model fixture.
// No configured account, API key, production store or mail transport is used.
internal static class ChatToolChecks
{
    internal static int Run()
    {
        var root = Path.Combine(Path.GetTempPath(), "meow-chat-tools-" + Guid.NewGuid()); var log = new List<string>();
        PetWindow? pet = null; Dashboard? dashboard = null; using var model = new ModelFixture();
        void Check(bool valid, string name) { if (!valid) throw new Exception(name); log.Add("PASS " + name); }
        try
        {
            SynchronizationContext.SetSynchronizationContext(new DispatcherSynchronizationContext(Application.Current.Dispatcher));
            var store = new Store(root); store.Data.LocalModel = true; store.Data.LocalUrl = model.Url;
            store.Data.NightSleep = store.Data.Wander = store.Data.WindowJump = store.Data.AutoMemory = false;
            pet = new PetWindow(store); dashboard = new Dashboard(store, pet);
            var input = (TextBox)typeof(Dashboard).GetField("input", BindingFlags.Instance | BindingFlags.NonPublic)!.GetValue(dashboard)!;
            var send = typeof(Dashboard).GetMethod("Send", BindingFlags.Instance | BindingFlags.NonPublic)!;
            void Turn(string text)
            {
                input.Text = text;
                var task = (Task)send.Invoke(dashboard, null)!;
                var frame = new DispatcherFrame();
                using var deadline = new CancellationTokenSource(TimeSpan.FromSeconds(30));
                using var registration = deadline.Token.Register(() => Application.Current.Dispatcher.BeginInvoke(() => frame.Continue = false));
                _ = task.ContinueWith(_ => Application.Current.Dispatcher.BeginInvoke(() => frame.Continue = false));
                Dispatcher.PushFrame(frame);
                if (!task.IsCompleted) throw new TimeoutException("Chat handler did not finish");
                task.GetAwaiter().GetResult();
            }
            string Plan(string text, params LocalToolCall[] tools) => JsonSerializer.Serialize(new { text, emotion = "neutral", actions = Array.Empty<string>(), intent = "reaction", hold = false, tools = tools.Select(t => new { name = t.Name, args = t.Args }) });
            Turn("记下：买牛奶"); Check(store.Data.Notes.Count == 1 && model.Requests.Count == 0, "chat saves quick note without a model or key");
            Turn("不要睡觉，挥挥手");
            var drawing = (PetDrawing)typeof(PetWindow).GetField("pet", BindingFlags.Instance | BindingFlags.NonPublic)!.GetValue(pet)!;
            Check(drawing.Action == "wave" && model.Requests.Count == 0, "chat executes mixed negative/positive action locally");
            model.Replies.Enqueue(Plan("我来记录", ConversationTools.Call("note.add", new { title = "购物清单", body = "牛奶" })));
            Turn("给我建一条笔记，标题购物清单，内容牛奶");
            Check(store.Data.Notes.Count == 2 && store.Data.History.Last().content.Contains("已保存笔记"), "model tool envelope reaches persistence and real receipt through chat UI");
            model.Replies.Enqueue(Plan("先读取", ConversationTools.Call("note.list", new { query = "购物清单" })));
            model.Replies.Enqueue(Plan("修改", ConversationTools.Call("note.update", new { query = "购物清单", body = "酸奶" })));
            Turn("把购物清单的牛奶改成酸奶");
            Check(store.Data.Notes.Single(n => n.Title == "购物清单").Body == "酸奶", "read-then-modify model loop completes actual note update");
            using (var payload = JsonDocument.Parse(model.Requests.Last()))
                Check(payload.RootElement.GetProperty("messages").EnumerateArray().Any(m => m.GetProperty("content").GetString()!.Contains("本机工具执行结果")), "real tool results are sent back to the planner");
            model.Replies.Enqueue(Plan("请问几点提醒？")); Turn("提醒我开会");
            Check(store.Data.Memos.Count == 0, "chat clarification creates no reminder prematurely");
            var tomorrow = new DateTimeOffset(DateTime.Today.AddDays(1).AddHours(9), TimeZoneInfo.Local.GetUtcOffset(DateTime.Today.AddDays(1)));
            model.Replies.Enqueue(Plan("收到", ConversationTools.Call("memo.add", new { title = "开会", due = tomorrow.ToString("O") })));
            Turn("明天上午九点"); Check(store.Data.Memos.Count == 1, "chat reminder clarification stays connected across turns");
            model.Replies.Enqueue(Plan("已经保存。")); Turn("帮我保存一条笔记");
            Check(store.Data.Notes.Count == 2 && store.Data.History.Last().content.Contains("尚未执行"), "model prose cannot impersonate a successful local write");
            model.Replies.Enqueue(Plan("准备", ConversationTools.Call("shell.exec", new { command = "not-executed" })));
            model.Replies.Enqueue(Plan("更正", ConversationTools.Call("note.add", new { title = "修复格式", body = "完成" })));
            Turn("帮我新增一条笔记：修复格式");
            Check(store.Data.Notes.Count == 3 && store.Data.Notes.Last().Title == "修复格式", "invalid tool plan repairs once before any mutation");
            Check(new Store(root).Data.Notes.Count == 3 && new Store(root).Data.Memos.Count == 1, "end-to-end chat changes survive reload");
            var notebook = dashboard.CreateFeatureWindow("memory");
            var content = (FrameworkElement)notebook.Content;
            VisualChecks.Save(content, notebook.Width, notebook.Height, Path.Combine(AppContext.BaseDirectory, "notebook-check.png"));
            VisualChecks.Find<Button>(content).Single(b => b.Content?.ToString() == "笔记").RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
            VisualChecks.Save(content, notebook.Width, notebook.Height, Path.Combine(AppContext.BaseDirectory, "notebook-check.png"));
            Check(VisualChecks.Find<TextBlock>(content).Any(t => t.Text == "酸奶"), "notebook tab renders the note changed through chat");
            notebook.Close();
            model.Replies.Enqueue(Plan("记住了，你喜欢蓝色。")); Turn("我喜欢蓝色");
            model.Replies.Enqueue(Plan("你刚才说喜欢蓝色。")); Turn("我刚才说喜欢什么颜色？");
            using (var payload = JsonDocument.Parse(model.Requests.Last()))
            {
                var messages = payload.RootElement.GetProperty("messages").EnumerateArray().ToArray();
                Check(messages[^3].GetProperty("content").GetString() == "我喜欢蓝色" && messages[^2].GetProperty("content").GetString() == "记住了，你喜欢蓝色。", "ordinary follow-up sends both sides of the immediately preceding conversation");
            }
            var noon = tomorrow.AddHours(3);
            model.Replies.Enqueue(Plan("记录", ConversationTools.Call("note.add", new { title = "午睡", body = "明天12点要去午睡" })));
            Turn("帮我记录一下，明天12点要去午睡");
            model.Replies.Enqueue(Plan("加入", ConversationTools.Call("memo.add", new { title = "午睡", due = noon.ToString("O") })));
            Turn("这个要加到备忘录里");
            Check(store.Data.Memos.Count == 2 && store.Data.Memos.Last().Title == "午睡", "this goes in reminders inherits the time and task from the preceding note request");
            string clarification = "是想记明天中午12点去午睡，对吗？污水是不是手滑打错啦？";
            model.Replies.Enqueue(Plan(clarification + "\",\"emotion\":\"neutral\",\"actions\":[],\"tools\":[]}"));
            model.Replies.Enqueue(Plan(clarification));
            Turn("备忘录里记一下，明天12点要去污水");
            Check(store.Data.PendingReminder is not null && store.Data.History.Last().content.Contains(clarification) && !store.Data.History.Last().content.Contains("\"emotion\""), "leaked control fields are repaired before display and clarification remains pending");
            Check(new Store(root).Data.PendingReminder?.Request.Contains("12点") == true, "pending reminder context survives a restart");
            model.Replies.Enqueue(Plan("更正", ConversationTools.Call("memo.add", new { title = "午睡", due = noon.ToString("O") })));
            Turn("午睡");
            Check(store.Data.Memos.Count == 3 && store.Data.Memos.Last().Title == "午睡" && store.Data.Memos.Last().Due == noon, "short typo correction completes the original reminder without asking for its time again");
            Check(new Store(root).Data.PendingReminder is null, "successful reminder clears persisted pending context");
            model.Replies.Enqueue(Plan("请问几点提醒？")); Turn("提醒我散步");
            model.Replies.Enqueue(Plan("那我们聊别的。")); Turn("算了，换个话题");
            Check(store.Data.PendingReminder is null, "cancelling or changing topic drops unfinished reminder context");
            log.Add("Only isolated local fixture requests were used; no external provider or real mail."); return 0;
        }
        catch (Exception e) { log.Add("FAIL " + e); return 1; }
        finally
        {
            dashboard?.Shutdown();
            if (pet is not null) { typeof(PetWindow).GetField("closing", BindingFlags.Instance | BindingFlags.NonPublic)!.SetValue(pet, true); pet.Close(); }
            File.WriteAllLines(Path.Combine(AppContext.BaseDirectory, "chattoolcheck-results.txt"), log);
            if (Directory.Exists(root)) Directory.Delete(root, true);
        }
    }
    private sealed class ModelFixture : IDisposable
    {
        private readonly TcpListener listener = new(IPAddress.Loopback, 0);
        private readonly CancellationTokenSource stop = new();
        private readonly Task worker;
        internal readonly ConcurrentQueue<string> Replies = new();
        internal readonly ConcurrentQueue<string> Requests = new();
        internal string Url { get; }
        internal ModelFixture()
        {
            listener.Start(); Url = $"http://127.0.0.1:{((IPEndPoint)listener.LocalEndpoint).Port}/v1";
            worker = Task.Run(async () =>
            {
                try
                {
                    while (!stop.IsCancellationRequested)
                    {
                        using var client = await listener.AcceptTcpClientAsync(stop.Token); using var stream = client.GetStream();
                        var bytes = new List<byte>(); var buffer = new byte[4096]; int split = -1, length = 0;
                        while (split < 0 || bytes.Count < split + 4 + length)
                        {
                            int count = await stream.ReadAsync(buffer, stop.Token); if (count == 0) break; bytes.AddRange(buffer.AsSpan(0, count).ToArray());
                            if (split < 0)
                            {
                                string headers = Encoding.UTF8.GetString(bytes.ToArray()); split = headers.IndexOf("\r\n\r\n", StringComparison.Ordinal);
                                if (split >= 0) length = int.Parse(headers[..split].Split("\r\n").Single(l => l.StartsWith("Content-Length:", StringComparison.OrdinalIgnoreCase)).Split(':')[1]);
                            }
                        }
                        Requests.Enqueue(Encoding.UTF8.GetString(bytes.ToArray(), split+4, length));
                        string body = Replies.TryDequeue(out var reply) ? reply : "unexpected fixture request";
                        byte[] response = Encoding.UTF8.GetBytes("data: " + JsonSerializer.Serialize(new { choices = new[] { new { delta = new { content = body } } } }) + "\n\ndata: [DONE]\n\n");
                        await stream.WriteAsync(Encoding.ASCII.GetBytes($"HTTP/1.1 200 OK\r\nContent-Type: text/event-stream\r\nContent-Length: {response.Length}\r\nConnection: close\r\n\r\n"), stop.Token);
                        await stream.WriteAsync(response, stop.Token);
                    }
                }
                catch (OperationCanceledException) { }
                catch (SocketException) when (stop.IsCancellationRequested) { }
            });
        }
        public void Dispose() { stop.Cancel(); listener.Stop(); worker.GetAwaiter().GetResult(); stop.Dispose(); }
    }
}
