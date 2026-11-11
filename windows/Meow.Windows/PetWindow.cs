using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Interop;
using System.Windows.Media;
using System.Windows.Threading;

namespace Meow.Windows;

public sealed partial class PetWindow : Window
{
    private readonly Store store;
    private readonly PetDrawing pet = new() { KeepStatePose = true };
    private readonly SpeechBubble bubble = new();
    private TimeSpan lastRenderingTime = TimeSpan.MinValue;
    private readonly Stopwatch clock = Stopwatch.StartNew();
    private double lastTick, nextDecision = 4, actionUntil, bubbleUntil, saveAt;
    private double velocityX, velocityY;
    private bool dragging, falling, closing;
    private Point startMouse, startWindow, lastMouse;
    private double lastMove;
    private Dashboard? dashboard;
    public CompanionService Features { get; }
    public MailboxService Mailbox { get; }
    internal LocalEngine Local { get; } = new();
    [StructLayout(LayoutKind.Sequential)] private struct NativePoint { public int X, Y; }
    [DllImport("user32.dll")] private static extern bool GetCursorPos(out NativePoint point);
    [DllImport("user32.dll", EntryPoint = "GetWindowLongPtrW")] private static extern IntPtr GetWindowLong(IntPtr hwnd, int index);
    [DllImport("user32.dll", EntryPoint = "SetWindowLongPtrW")] private static extern IntPtr SetWindowLong(IntPtr hwnd, int index, IntPtr value);
    public PetWindow(Store store)
    {
        this.store = store;
        LuluBedScene.WarmUp();
        LuluVideo.WarmUp();
        LuluEdgeAnimation.WarmUp();
        LuluPoseTransition.WarmUp();
        Features = new CompanionService(store); Mailbox = new MailboxService(store);
        Title = "Meow · 张噜噜"; Width = Height = 230 * store.Data.Scale;
        WindowStyle = WindowStyle.None; ResizeMode = ResizeMode.NoResize; AllowsTransparency = true;
        Background = Brushes.Transparent; Topmost = true; ShowInTaskbar = false; ShowActivated = false;
        Content = pet;
        var area = SystemParameters.WorkArea;
        Left = store.Data.Left ?? area.Right - Width - 60; Top = store.Data.Top ?? area.Bottom - Height * .85;
        Clamp();
        SourceInitialized += (_, _) => { var hwnd = new WindowInteropHelper(this).Handle; SetWindowLong(hwnd, -20, new IntPtr(GetWindowLong(hwnd, -20).ToInt64() | 0x08000000 | 0x80)); };
        pet.MouseLeftButtonDown += OnDown; pet.MouseMove += OnMove; pet.MouseLeftButtonUp += OnUp;
        pet.LostMouseCapture += (_, _) => { dragging = false; };
        var menu = new ContextMenu();
        void Item(string title, Action action) { var i = new MenuItem { Header = title }; i.Click += (_, _) => action(); menu.Items.Add(i); }
        Item("和张噜噜聊天…", OpenDashboard); Item("小本本…", () => OpenFeature("memory")); Item("噜噜备忘录…", () => OpenFeature("memos")); Item("热点小报…", () => OpenFeature("news")); Item("噜噜信箱…", () => OpenFeature("mail")); Item("设置…", () => OpenFeature("settings")); Item("动作预览…", () => new CharacterPreview().Show()); menu.Items.Add(new Separator()); Item("跳上窗口", JumpToWindow); Item("过来这边", () => Animate("come")); Item("喂西瓜", () => Feed("🍉"));
        Item("一起玩", () => { Animate("play"); Say("主人，跟我一起玩小皮球！"); });
        var interactions = new MenuItem { Header = "互动动作" }; menu.Items.Add(interactions);
        foreach (var (label, activity) in new[] { ("挥挥手", "wave"), ("跳个舞", "dance"), ("伸懒腰", "stretch"), ("转圈圈", "spin"), ("打个滚", "roll"), ("点点头", "nod"), ("摇摇头", "shakeHead"), ("探探头", "peek") })
        { var item = new MenuItem { Header = label }; item.Click += (_, _) => Animate(activity); interactions.Items.Add(item); }
        var expressions = new MenuItem { Header = "小表情" }; menu.Items.Add(expressions);
        foreach (var (label, emotion) in new[] { ("开心", "happy"), ("喜欢你", "love"), ("害羞", "shy"), ("好奇", "curious"), ("惊讶", "surprised"), ("生气", "angry"), ("委屈", "sad"), ("困了", "sleepy"), ("饿了", "hungry"), ("晕乎乎", "dizzy") })
        { var item = new MenuItem { Header = label }; item.Click += (_, _) => Express(emotion); expressions.Items.Add(item); }
        Item("睡觉 / 叫醒", ToggleSleep);
        Item("散步（走走停停）", () => Animate("walk"));
        Item("站住 / 停下来", () => Animate("idle"));
        Item("保持当前表情或姿势", HoldCurrentState);
        Item("恢复自由活动", () => { Animate("free"); store.Data.Wander = true; Save(); });
        Item("退出噜噜", () => { closing = true; Close(); Application.Current.Shutdown(); });
        pet.ContextMenu = menu;
        Closing += (_, e) => { if (!closing) { e.Cancel = true; return; } CompositionTarget.Rendering -= Tick; Features.Stop(); Mailbox.Dispose(); Local.Dispose(); bubble.Close(); dashboard?.Shutdown(); Save(); };
        Loaded += (_, _) => { lastTick = clock.Elapsed.TotalSeconds; CompositionTarget.Rendering += Tick; Clamp(); Say("我是张噜噜。慢慢来，我在这里陪你。双击我聊聊天吧。"); if (store.Data.ProtectedKey.Length == 0) OpenDashboard(); };
    }
    private Point CursorPosition()
    {
        GetCursorPos(out var p);
        var source = PresentationSource.FromVisual(this);
        return source?.CompositionTarget?.TransformFromDevice.Transform(new Point(p.X, p.Y)) ?? new Point(p.X, p.Y);
    }
    private void OnDown(object sender, MouseButtonEventArgs e)
    {
        if (e.ClickCount == 2) { if (Mailbox.Unread > 0) OpenFeature("mail"); else OpenDashboard(); return; }
        CancelStroll(); CancelBedScene(); InterruptConversation();
        ReleaseWall(); platform = IntPtr.Zero; jumpTarget = IntPtr.Zero;
        startMouse = lastMouse = CursorPosition(); startWindow = new Point(Left, Top); lastMove = clock.Elapsed.TotalSeconds;
        velocityX = velocityY = 0; pet.Action = "drag"; dragging = true; falling = false; pet.CaptureMouse(); e.Handled = true;
    }
    private void OnMove(object sender, MouseEventArgs e)
    {
        if (!dragging) { if (!Docked && !StateHeld && e.LeftButton == MouseButtonState.Released && clock.Elapsed.TotalSeconds > nextStroke && pet.IsMouseOver) { InterruptConversation(); nextStroke = clock.Elapsed.TotalSeconds + 8; AnimateCore("emotion:love"); store.Data.Happiness = Math.Min(100, store.Data.Happiness + 3); Remember("摸摸头"); Say("蹭蹭主人，好舒服呀～"); } return; }
        var p = CursorPosition(); double now = clock.Elapsed.TotalSeconds, dt = Math.Max(.01, now - lastMove);
        velocityX = Math.Clamp((p.X - lastMouse.X) / dt, -1200, 1200); velocityY = Math.Clamp((p.Y - lastMouse.Y) / dt, -1200, 1200);
        Left = startWindow.X + p.X - startMouse.X; Top = startWindow.Y + p.Y - startMouse.Y;
        lastMouse = p; lastMove = now;
    }
    private void OnUp(object sender, MouseButtonEventArgs e)
    {
        if (!dragging) return;
        dragging = false; pet.ReleaseMouseCapture();
        if ((CursorPosition() - startMouse).Length < 5) { Say("嗯？主人在叫我吗～"); Animate("wave"); falling = Top < Area.Bottom - Height * .85 - 2; return; }
        if (clock.Elapsed.TotalSeconds - lastMove > .15) velocityX = velocityY = 0;
        falling = true; pet.Action = "fall"; DockIfNearEdge(); Save();
    }
    public void Animate(string action)
    {
        if (action == "hold") { HoldCurrentState(); return; }
        // The requested action replaces playback directly; inserting idle here
        // would prepare two competing walk/idle joins for a single click.
        conversationPlayback.Interrupt(); heldState = "";
        AnimateCore(action == "free" ? "idle" : action, hold: action is "idle" or "walk" or "sleep");
    }
    private void AnimateCore(string action, bool speak = true, bool hold = false)
    {
        bool wasStrolling = strollPhase.Length > 0;
        CancelStroll();
        if (TryBedAction(action, speak, hold)) return;
        heldState = "";
        if (action.StartsWith("emotion:", StringComparison.Ordinal))
        {
            AnimateCore("idle", speak); pet.Emotion = action[8..];
            actionUntil = clock.Elapsed.TotalSeconds + Math.Max(ExpressionDuration(pet.Emotion), PetDrawing.Duration(pet.Emotion));
            if (hold) { heldState = action; actionUntil = double.PositiveInfinity; }
            return;
        }
        if (action != "sleep") ReleaseWall(); nightWake = clock.Elapsed.TotalSeconds + 600;
        if (action == "climb") { JumpToWindow(); return; }
        if (action == "come") { var p = CursorPosition(); Left = p.X - Width / 2; Top = p.Y - Height * .6; platform = IntPtr.Zero; falling = true; Clamp(); action = "wave"; }
        if (action == "down") { platform = IntPtr.Zero; falling = true; action = "idle"; }
        if (action == "jump") { platform = IntPtr.Zero; velocityY = -650; falling = true; }
        if (action == "eat") { store.Data.Fullness = Math.Min(100, store.Data.Fullness + 20); store.Data.Happiness = Math.Min(100, store.Data.Happiness + 5); Remember("喂食"); if (speak) Say("啊呜，吃口甜的。今天也慢慢来吧。"); }
        if (action == "play") { store.Data.Happiness = Math.Min(100, store.Data.Happiness + 10); Remember("一起玩"); }
        pet.Emotion = "neutral"; pet.Action = action; pet.RestartAnimation(); actionUntil = clock.Elapsed.TotalSeconds + PetDrawing.Duration(action); velocityX = action == "walk" ? 25 : 0;
        if (hold || action == "sleep") { heldState = action; actionUntil = double.PositiveInfinity; }
        if (action == "walk" && LuluVideo.Available && !dragging && !falling) StartStroll(hold, pet.FacingRight ? 1 : -1);
        else if (action == "idle" && wasStrolling && !dragging && !falling) RestFromStroll(false);
    }
    public void Say(string text) { bubble.Say(text, this, Area); bubbleUntil = clock.Elapsed.TotalSeconds + 10; }
    private void Express(string emotion) => Animate("emotion:" + emotion);
    public void Feed(string food) { pet.Food = food; Animate("eat"); }
    public void ToggleSleep() => Animate(pet.Action == "sleep" ? "idle" : "sleep");
    public void Thinking(bool busy) { if (busy && !StateHeld && !dragging && !falling && pet.Action == "idle" && pet.Emotion == "neutral") pet.Action = "think"; else if (!busy && pet.Action == "think") pet.Action = "idle"; }
    private void Remember(string kind)
    {
        if (!store.Data.MemoryEnabled) return;
        string day = DateTime.Now.ToString("yyyy-MM-dd"); var entry = store.Data.Experiences.FirstOrDefault(x => x.Day == day && x.Kind == kind);
        if (entry is null) store.Data.Experiences.Add(entry = new Experience { Day = day, Kind = kind }); entry.Count++; Save();
    }
    public void OpenFeature(string kind) { if (dashboard is null) { dashboard = new Dashboard(store, this); dashboard.Closed += (_, _) => dashboard = null; } dashboard.OpenFeature(kind); }
    public void OpenDashboard() { if (dashboard is null) { dashboard = new Dashboard(store, this); dashboard.Closed += (_, _) => dashboard = null; } dashboard.Show(); dashboard.Activate(); }
    public void ApplyScale()
    {
        bool bed = pet.BedScene is not null;
        double feet = Top + Height * .85, center = Left + (bed ? Height / 2 : Width / 2);
        Height = 230 * store.Data.Scale; Width = Height * (bed ? 2 : 1);
        Left = center - (bed ? Height / 2 : Width / 2); Top = feet - Height * .85; Clamp();
    }
    private void Clamp()
    {
        // The original feet line is 170 / 200, below the body but above effect margins.
        var a = Area;
        Left = double.IsFinite(Left) ? Math.Clamp(Left, a.Left, Math.Max(a.Left, a.Right - Width)) : a.Left;
        Top = double.IsFinite(Top) ? Math.Clamp(Top, a.Top, Math.Max(a.Top, a.Bottom - Height * .85)) : a.Top;
    }
    private void Tick(object? sender, EventArgs e)
    {
        if (e is RenderingEventArgs rendering) { if (rendering.RenderingTime == lastRenderingTime) return; lastRenderingTime = rendering.RenderingTime; }
        double now = clock.Elapsed.TotalSeconds, dt = Math.Min(.067, now - lastTick); lastTick = now;
        if (falling && StateHeld) { heldState = ""; conversationPlayback.Interrupt(); }
        pet.Time = now; pet.Happiness = store.Data.Happiness;
        if (AdvanceBedScene(dt))
        {
            pet.InvalidateVisual(); bubble.Position(this, Area); if (now > bubbleUntil) bubble.Dismiss();
            store.Data.Energy = Math.Min(100, store.Data.Energy + dt * .08);
            store.Data.Fullness = Math.Max(0, store.Data.Fullness - dt / 120);
            if (now > saveAt) { saveAt = now + 30; _ = Mailbox.Tick(); Save(); }
            return;
        }
        bool strolling = AdvanceStroll(dt);
        if (pet.Action == "walk") pet.WalkPhase += dt * 6;
        pet.Squash *= Math.Exp(-dt * 12);
        pet.EarTwitch = now % 7 < .35 ? 1 : 0;
        var pointer = CursorPosition(); var gaze = new Point((pointer.X - Left - Width / 2) / Math.Max(1, Width) * 5, -(pointer.Y - Top - Height * .48) / Math.Max(1, Height) * 4);
        pet.Gaze = new Point(Math.Clamp(gaze.X, -4.5, 4.5), Math.Clamp(gaze.Y, -3, 3));
        pet.TalkLevel = !strolling && now < bubbleUntil && pet.Action != "sleep" ? .35 + Math.Sin(now * 12) * .3 : 0;
        if (velocityX != 0 && !dragging) pet.FacingRight = velocityX > 0;
        if (!StateHeld && conversationPlayback.Playing && now > actionUntil && !dragging && !falling) AdvanceConversation();
        if (!StateHeld && !strolling && now > actionUntil) pet.Emotion = now % 30 >= 6 ? "neutral" : store.Data.Fullness < 25 ? "hungry" : store.Data.Energy < 25 ? "sleepy" : store.Data.Happiness < 30 ? "sad" : store.Data.Happiness > 85 ? "happy" : "neutral";
        pet.InvalidateVisual(); bubble.Position(this, Area);
        if (now > bubbleUntil) bubble.Dismiss();
        if (!dragging)
        {
            if (falling) { velocityY += 1400 * dt; Left += velocityX * dt; Top += velocityY * dt; if (Top >= Area.Bottom - Height * .85) { falling = false; velocityY = velocityX = 0; pet.Squash = .15; pet.Action = LuluVideo.Available ? "land" : "idle"; actionUntil = now + PetDrawing.Duration(pet.Action); } Clamp(); }
            else if (pet.Action == "walk" && !strolling)
            {
                Left += velocityX * dt; Clamp();
                if (StateHeld && (Left <= Area.Left + .1 || Left >= Area.Right - Width - .1)) velocityX = Left <= Area.Left + .1 ? 25 : -25;
            }
            if (!StateHeld && !strolling && now > actionUntil && pet.Action is not ("sleep" or "think") && !falling)
            {
                string ended = pet.Action; pet.Action = "idle";
                if (ended is "eat" or "play" or "dance") { pet.Emotion = "happy"; actionUntil = now + 3; }
                else if (ended is "spin" or "roll") { pet.Emotion = "dizzy"; actionUntil = now + 3; }
            }
            if (now > nextDecision) { nextDecision = now + 8 + Random.Shared.Next(6); if (!StateHeld && now > actionUntil && store.Data.Wander && !Features.ChatBusy && !conversationPlayback.Playing && !Docked && pet.Action == "idle") { if (LuluVideo.Available) StartStroll(false, Random.Shared.Next(2) == 0 ? -1 : 1); else { pet.Action = "walk"; velocityX = Random.Shared.Next(2) == 0 ? -25 : 25; actionUntil = now + 3; } } }
        }
        FeatureFrame(now, dt);
        store.Data.Fullness = Math.Max(0, store.Data.Fullness - dt / 120);
        store.Data.Energy = Math.Clamp(store.Data.Energy + dt * (pet.Action == "sleep" ? .08 : -.003), 0, 100);
        if (now > saveAt)
        {
            saveAt = now + 30;
            _ = Features.Tick(() => !dragging && !falling && clock.Elapsed.TotalSeconds > bubbleUntil, Say);
            _ = Mailbox.Tick();
            Save();
        }
    }
    private void Save()
    { try { store.Data.Left = Left; store.Data.Top = Top; store.Save(); } catch (Exception e) { Say("存档失败：" + e.Message); } }
}
