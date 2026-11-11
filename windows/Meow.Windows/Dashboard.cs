using System.Globalization;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Text.RegularExpressions;

namespace Meow.Windows;

public sealed partial class Dashboard : Window
{
    private readonly Store store;
    private readonly PetWindow pet;
    private CancellationTokenSource? request;
    private readonly StackPanel conversation = new();
    private readonly ScrollViewer scroll;
    private readonly TextBox input = new() { AcceptsReturn = true, TextWrapping = TextWrapping.Wrap, MinHeight = 18, MaxHeight = 54, VerticalScrollBarVisibility = ScrollBarVisibility.Auto };
    private readonly Button send = new() { Width = 26, Height = 26 };
    private readonly TextBlock status = new();
    private TextBox address = null!, model = null!;
    private PasswordBox key = null!;
    private readonly System.Windows.Shapes.Ellipse brainDot;
    private readonly System.Windows.Threading.DispatcherTimer statsTimer = new() { Interval = TimeSpan.FromSeconds(1) };
    private readonly List<Action> statUpdates = [];
    private readonly Dictionary<string, Window> featureWindows = [];
    public Dashboard(Store store, PetWindow pet)
    {
        this.store = store; this.pet = pet;
        var root = new DockPanel();
        var header = new DockPanel { Margin = new Thickness(14, 24, 14, 8) };
        DockPanel.SetDock(header, Dock.Top); root.Children.Add(header);
        var tools = new StackPanel { Orientation = Orientation.Horizontal, VerticalAlignment = VerticalAlignment.Center };
        DockPanel.SetDock(tools, Dock.Right); header.Children.Add(tools);
        var clear = IconButton("", "清空聊天", () => { if (request is not null) return; store.Data.History.Clear(); Persist(); conversation.Children.Clear(); });
        clear.Content = new System.Windows.Shapes.Path { Data = Geometry.Parse("M2,4 L12,4 M5,4 L5,2 L9,2 L9,4 M3,4 L4,13 L10,13 L11,4 M6,6 L6,11 M8,6 L8,11"), Stroke = MacTheme.Cocoa, StrokeThickness = 1, Width = 14, Height = 15, Opacity = .5 };
        tools.Children.Add(clear); tools.Children.Add(IconButton("⚙", "设置", () => OpenFeature("settings")));
        var title = new StackPanel(); header.Children.Add(title);
        var titleLine = new StackPanel { Orientation = Orientation.Horizontal }; titleLine.Children.Add(MacTheme.Text("张噜噜", 15, true));
        brainDot = new System.Windows.Shapes.Ellipse { Width = 7, Height = 7, Fill = PetDrawing.B("#8CD180"), Margin = new Thickness(6, 0, 0, 0), ToolTip = "模型已就绪" }; titleLine.Children.Add(brainDot); title.Children.Add(titleLine);
        var stats = new StackPanel { Orientation = Orientation.Horizontal, Margin = new Thickness(0, 2, 0, 0) };
        stats.Children.Add(Stat("🍉", () => store.Data.Fullness)); stats.Children.Add(Stat("⚡", () => store.Data.Energy)); stats.Children.Add(Stat("💗", () => store.Data.Happiness)); title.Children.Add(stats);
        var line = MacTheme.Divider(); line.Margin = new Thickness(0); DockPanel.SetDock(line, Dock.Top); root.Children.Add(line);
        var bottom = new StackPanel(); DockPanel.SetDock(bottom, Dock.Bottom); root.Children.Add(bottom);
        var divider = MacTheme.Divider(); divider.Margin = new Thickness(0); bottom.Children.Add(divider);
        var quick = new StackPanel { Orientation = Orientation.Horizontal, Margin = new Thickness(12, 6, 12, 6) };
        foreach (var (label, tip, action) in new (string, string, Action)[] { ("🍉", "喂西瓜", () => pet.Feed("🍉")), ("👋", "挥挥手", () => pet.Animate("wave")), ("⚽", "一起玩", () => pet.Animate("play")), ("💤", "睡觉 / 叫醒", pet.ToggleSleep) })
        { var q = Button(label, action); q.Content = ColorEmoji.Icon(label, 16); q.Width = 30; q.Height = 26; q.Padding = new Thickness(0); q.FontSize = 16; q.BorderThickness = new Thickness(0); q.ToolTip = tip; quick.Children.Add(q); }
        bottom.Children.Add(quick);
        var composer = new DockPanel { Margin = new Thickness(12, 4, 12, 10) };
        send.Padding = new Thickness(0); send.Foreground = Brushes.White; send.Background = MacTheme.Accent; send.BorderThickness = new Thickness(0); send.Margin = new Thickness(8, 0, 0, 0); send.VerticalAlignment = VerticalAlignment.Center;
        send.Content = SendGlyph(); send.ToolTip = "发送 · Enter（Shift+Enter 换行）";
        DockPanel.SetDock(send, Dock.Right); composer.Children.Add(send);
        input.BorderThickness = new Thickness(0); input.Background = Brushes.Transparent; input.Padding = new Thickness(0); input.ToolTip = "对张噜噜说点什么…";
        composer.Children.Add(new Border { Child = input, Padding = new Thickness(12, 8, 12, 8), CornerRadius = new CornerRadius(16), Background = Brushes.White });
        bottom.Children.Add(composer); status.Margin = new Thickness(12, 0, 12, 6); bottom.Children.Add(status);
        scroll = MacTheme.Scroll(conversation); conversation.Margin = new Thickness(12); root.Children.Add(scroll);
        MacTheme.Shell(this, "和张噜噜聊天", 320, 420, root); status.SetResourceReference(StyleProperty, "Status"); send.SetResourceReference(StyleProperty, "CircleButton");
        send.Click += async (_, _) => { if (request is not null) { pet.Animate("idle"); request.Cancel(); } else await Send(); };
        foreach (var m in store.Data.History) AddMessage(m.role == "user" ? "主人" : "噜噜", m.content);
        if (store.Data.History.Count == 0) AddMessage("噜噜", "主人，你来啦～今天想和噜噜聊些什么？");
        input.PreviewKeyDown += async (_, e) => { if (e.Key == System.Windows.Input.Key.Enter && !System.Windows.Input.Keyboard.Modifiers.HasFlag(System.Windows.Input.ModifierKeys.Shift)) { e.Handled = true; if (request is null) await Send(); } };
        input.TextChanged += (_, _) => send.Opacity = request is not null || !string.IsNullOrWhiteSpace(input.Text) ? 1 : .35;
        send.Opacity = .35;
        statsTimer.Tick += (_, _) => { foreach (var update in statUpdates) update(); };
        Loaded += (_, _) => { statsTimer.Start(); input.Focus(); scroll.ScrollToEnd(); };
        IsVisibleChanged += (_, _) => { if (IsVisible) statsTimer.Start(); else statsTimer.Stop(); };
        Closing += (_, e) => { statsTimer.Stop(); if (request is not null) pet.InterruptConversation(preserveState: true); request?.Cancel(); if (!shuttingDown) { e.Cancel = true; Hide(); } };
    }
    private bool shuttingDown;
    public void Shutdown() { shuttingDown = true; foreach (var w in featureWindows.Values.ToArray()) w.Close(); Close(); }
    private static UIElement SendGlyph() => new System.Windows.Shapes.Path { Data = Geometry.Parse("M12,19 L12,5 M6,11 L12,5 L18,11"), Stroke = Brushes.White, StrokeThickness = 2, StrokeStartLineCap = PenLineCap.Round, StrokeEndLineCap = PenLineCap.Round, Width = 24, Height = 24 };
    private static Button IconButton(string glyph, string tip, Action action) { var b = Button(glyph, action); b.ToolTip = tip; b.Background = Brushes.Transparent; b.BorderThickness = new Thickness(0); b.FontSize = 15; b.Padding = new Thickness(2); b.Margin = new Thickness(8, 0, 0, 0); return b; }
    private UIElement Stat(string emoji, Func<double> value)
    {
        var row = new StackPanel { Orientation = Orientation.Horizontal, Margin = new Thickness(0, 0, 8, 0) };
        var icon = ColorEmoji.Icon(emoji, 9); icon.Margin = new Thickness(0, 0, 3, 0); row.Children.Add(icon);
        var fill = new Border { CornerRadius = new CornerRadius(3), HorizontalAlignment = HorizontalAlignment.Left };
        row.Children.Add(new Border { Width = 36, Height = 6, CornerRadius = new CornerRadius(3), Background = PetDrawing.B("#1F5C4536"), Child = fill });
        void Update() { double v = Math.Clamp(value(), 0, 100); fill.Width = Math.Max(3, 36 * v / 100); fill.Background = PetDrawing.B(v < 25 ? "#F27366" : v < 55 ? "#FABF59" : "#8CD180"); row.ToolTip = $"{v:F0}/100"; }
        statUpdates.Add(Update); Update(); return row;
    }
    public void OpenFeature(string kind)
    {
        if (featureWindows.TryGetValue(kind, out var existing)) { existing.Show(); existing.Activate(); return; }
        var window = CreateFeatureWindow(kind); featureWindows[kind] = window;
        window.Closed += (_, _) => featureWindows.Remove(kind); window.Show(); window.Activate();
    }
    internal Window CreateFeatureWindow(string kind)
    {
        var (title, w, h, content) = kind switch
        {
            "memory" => ("张噜噜的小本本", 540d, 660d, Memory()),
            "memos" => ("噜噜备忘录", 600d, 700d, Memos()),
            "news" => ("张噜噜的热点小报", 560d, 700d, NewsPanel()),
            "mail" => ("噜噜信箱", 700d, 680d, MailPanel()),
            _ => ("张噜噜的设置", 410d, 660d, Settings())
        };
        return MacTheme.Window(title, w, h, content);
    }
    private static Button Button(string text, Action click) => MacTheme.Button(text, click);
    private static StackPanel Panel() => new() { Margin = new Thickness(18, 30, 18, 18) };
    private static void Label(Panel p, string text) { var t = MacTheme.Text(text, 11); t.Margin = new Thickness(0, 8, 0, 5); p.Children.Add(t); }
    private TextBlock AddMessage(string who, string text)
    {
        bool mine = who == "主人"; var body = MacTheme.Text(text.Length == 0 ? "…" : text, 13); body.Foreground = mine ? Brushes.White : MacTheme.Cocoa;
        conversation.Children.Add(new Border { Child = body, MaxWidth = 250, HorizontalAlignment = mine ? HorizontalAlignment.Right : HorizontalAlignment.Left, Padding = new Thickness(12, 7, 12, 7), Margin = new Thickness(mine ? 44 : 0, 0, mine ? 0 : 44, 8), CornerRadius = new CornerRadius(14), Background = mine ? MacTheme.Accent : Brushes.White, Effect = new System.Windows.Media.Effects.DropShadowEffect { BlurRadius = 2, ShadowDepth = 1, Opacity = .06 } });
        scroll.ScrollToEnd(); return body;
    }
    private async Task Send()
    {
        string text = input.Text.Trim(); if (text.Length == 0) return;
        if (text.Length > 8000) { status.Text = "一次最多发送 8000 字。"; return; }
        // Explicit short commands execute independently of cloud availability.
        pet.InterruptConversation(preserveState: true);
        var action = Commands.Action(text); if (action is not null) pet.Animate(action);
        int behaviorRevision = pet.ConversationRevision;
        string secret;
        try { secret = store.Data.LocalModel ? "local" : store.ReadKey(); if (store.Data.LocalModel) CloudClient.LocalEndpoint(store.Data.LocalUrl); else CloudClient.Endpoint(store.Data.BaseUrl, store.Data.Provider); if (secret.Length == 0) throw new InvalidOperationException("请先在设置中保存密钥。"); }
        catch (Exception e) { status.Text = e.Message; return; }
        request = new CancellationTokenSource(TimeSpan.FromMinutes(3)); send.Content = "■"; brainDot.Fill = Brushes.Orange; pet.Thinking(true); input.IsEnabled = false; status.Text = "噜噜在想…";
        pet.Features.ChatBusy = true;
        input.Clear(); AddMessage("主人", text); var reply = AddMessage("噜噜", "");
        var messages = new List<Message> { new("system", Character.Prompt(pet.Features.MemoryContext, store.Data.Fullness, store.Data.Energy) + "\n" + ConversationBehavior.Instructions + "\n" + pet.ConversationContext + $"\n本轮已由本地执行的口令：{action ?? "无"}。") };
        messages.AddRange(store.Data.History.TakeLast(30)); messages.Add(new Message("user", text));
        try
        {
            if (store.Data.LocalModel && store.Data.LocalUrl == "http://127.0.0.1:8080/v1") await pet.Local.Start();
            string? tool = store.Data.LocalModel ? null : await pet.Features.HandleMemo(text, request.Token);
            string raw = tool ?? await new CloudClient().Generate(store.Data.LocalModel ? store.Data.LocalUrl : store.Data.BaseUrl, store.Data.LocalModel ? store.Data.LocalModelName : store.Data.Model, secret, messages, t => { reply.Text = ConversationBehavior.DisplayText(t); scroll.ScrollToEnd(); }, request.Token, store.Data.LocalModel, store.Data.ThinkingEnabled, store.Data.Provider);
            request.Token.ThrowIfCancellationRequested();
            var behavior = tool is null ? ConversationBehavior.Parse(raw, text, action is not null) : new BehaviorReply(tool, "neutral", []);
            string result = behavior.Text.Trim();
            if (result.Length == 0) throw new InvalidOperationException("模型没有返回可显示的台词，请重试或更换模型。动作未执行。");
            reply.Text = result;
            store.Data.History.Add(new Message("user", text)); store.Data.History.Add(new Message("assistant", result));
            if (store.Data.History.Count > 200) store.Data.History.RemoveRange(0, store.Data.History.Count - 200);
            Persist(); pet.Thinking(false); pet.ReactToConversation(behavior, behaviorRevision); pet.Say(result);
            status.Text = behavior.Structured ? "" : "本轮正常显示文字；模型未返回有效的动作格式。";
            if (!store.Data.LocalModel) try { await pet.Features.Learn(text, request.Token); } catch (Exception e) { status.Text = "回复完成；记忆整理未完成：" + e.Message; }
            if (text.Contains("不要跳窗")) { store.Data.WindowJump = false; Persist(); }
            if (text.Contains("安静一些")) { store.Data.Proactive = false; store.Data.Wander = false; Persist(); }
        }
        catch (OperationCanceledException) { status.Text = "回复已停止或超时；未完成的这一轮没有写入存档。"; }
        catch (Exception e) { status.Text = "回复失败：" + e.Message; }
        finally { request.Dispose(); request = null; pet.Features.ChatBusy = false; send.Content = SendGlyph(); send.Opacity = .35; brainDot.Fill = PetDrawing.B("#8CD180"); pet.Thinking(false); input.IsEnabled = true; input.Focus(); }
    }
    private bool Persist() { try { store.Save(); return true; } catch (Exception e) { status.Text = "保存失败：" + e.Message; return false; } }
}
internal static class Commands
{
    public static string? Action(string text)
    {
        // Anchor the entire short instruction: stories, quotes and negations never trigger actions.
        text = text.Trim().TrimEnd('。', '！', '!', '～', '~');
        var extra = new Dictionary<string, string> { { "转个圈", "spin" }, { "转圈", "spin" }, { "点点头", "nod" }, { "点头", "nod" }, { "摇摇头", "shakeHead" }, { "摇头", "shakeHead" }, { "伸个懒腰", "stretch" }, { "伸懒腰", "stretch" }, { "跳一下", "jump" }, { "跳上窗口", "climb" }, { "跳到窗口上去", "climb" }, { "下来陪我", "down" }, { "下来", "down" }, { "过来陪我", "come" }, { "过来", "come" }, { "散散步", "walk" }, { "散步", "walk" }, { "吃西瓜", "eat" }, { "陪我玩", "play" } };
        var shortText = Regex.Replace(Regex.Replace(text, @"^(请|张噜噜，|噜噜，|小喵，)", ""), @"(吧|给我看|看看)$", "");
        if (shortText is "保持这个表情" or "保持当前表情" or "保持这个姿势" or "保持当前姿势" or "保持这样" or "保持这个表情直到我叫停") return "hold";
        if (shortText is "恢复自由活动" or "恢复正常" or "自由活动") return "free";
        if (shortText is "站住" or "站着别动" or "待在原地" or "停止" or "停止当前动作" or "停止散步") return "idle";
        if (shortText is "持续散步" or "一直散步" or "继续散步" or "开始散步" or "走走停停") return "walk";
        var expression = shortText switch { "笑一个" or "开心一点" => "happy", "撒个娇" => "love", "害羞一个" => "shy", "装生气" => "angry", "装委屈" => "sad", "惊讶一下" => "surprised", "好奇一下" => "curious", "打个哈欠" => "sleepy", _ => null };
        if (expression is not null) return "emotion:" + expression;
        if (extra.TryGetValue(shortText, out var found)) return found;
        if (Regex.IsMatch(text, @"^(请|张噜噜，|噜噜，|小喵，)?(停|停一下|先停一下|停下来|别动|不要动|别跳了|别转了|醒醒|起床)(吧|啦)?$")) return "idle";
        if (Regex.IsMatch(text, @"^(请|张噜噜，|噜噜，|小喵，)?(跳个舞|跳舞)(给我看|吧)?$")) return "dance";
        if (Regex.IsMatch(text, @"^(请|张噜噜，|噜噜，|小喵，)?(打个滚|打滚)(给我看|吧)?$")) return "roll";
        if (Regex.IsMatch(text, @"^(请|张噜噜，|噜噜，|小喵，)?(挥挥手|挥手|挥挥爪子|挥爪)(吧)?$")) return "wave";
        if (Regex.IsMatch(text, @"^(请|张噜噜，|噜噜，|小喵，)?(去睡觉|睡觉)(吧)?$")) return "sleep";
        return null;
    }
}
