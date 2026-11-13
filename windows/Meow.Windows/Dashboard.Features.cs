using System.Diagnostics;
using System.Globalization;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;

namespace Meow.Windows;

public sealed partial class Dashboard
{
    private void Toggle(StackPanel p, string title, bool value, Action<bool> change) => p.Children.Add(MacTheme.Toggle(title, value, v => { change(v); Persist(); }));
    private static void Hint(StackPanel p, string text) { var t = MacTheme.Hint(text); t.Margin = new Thickness(0, 5, 0, 8); p.Children.Add(t); }
    private static StackPanel Row(params UIElement[] elements) { var r = new StackPanel { Orientation = Orientation.Horizontal, Margin = new Thickness(0, 5, 0, 5) }; foreach (var e in elements) r.Children.Add(e); return r; }
    private static void PageTitle(StackPanel p, string title) { var t = MacTheme.Text(title, 16, true); t.Margin = new Thickness(0, 0, 0, 14); p.Children.Add(t); }
    private static void HeaderAccessory(StackPanel head, UIElement accessory)
    {
        var title = head.Children[0]; head.Children.RemoveAt(0); var row = new DockPanel();
        DockPanel.SetDock(accessory, Dock.Right); row.Children.Add(accessory); row.Children.Add(title); head.Children.Insert(0, row);
    }
    private static bool Confirm(string message) => MessageBox.Show(message, "张噜噜", MessageBoxButton.OKCancel, MessageBoxImage.Question) == MessageBoxResult.OK;
    private void OpenStorage() => Process.Start(new ProcessStartInfo(store.DirectoryPath) { UseShellExecute = true });
    private UIElement Settings()
    {
        var p = Panel(); PageTitle(p, "设置");
        Label(p, "可选扩展");
        Hint(p, $"动作表情：{(LuluVideo.MissingClips.Count == 0 ? "完整" : $"基础版，另有 {LuluVideo.MissingClips.Count} 种可扩展")}\n上床睡觉：{(LuluBedScene.Available ? "已安装" : "未安装，使用基础睡觉动作")}\n信箱通信：{(System.IO.File.Exists(System.IO.Path.Combine(AppContext.BaseDirectory, "mailbridge", "node.exe")) ? "已安装" : "未安装")}\n本地模型：{(System.IO.File.Exists(System.IO.Path.Combine(AppContext.BaseDirectory, "local-engine", "model.gguf")) ? "已安装" : "未安装，可使用云端聊天")} ");
        Hint(p, "需要更多功能时，运行对应扩展包安装程序，选择与主程序相同的目录。安装前退出噜噜，完成后重新打开。扩展包可在 Windows“已安装的应用”中单独卸载。");
        p.Children.Add(Button("打开程序目录", () => Process.Start(new ProcessStartInfo(AppContext.BaseDirectory) { UseShellExecute = true })));
        p.Children.Add(MacTheme.Divider());
        var provider = new ComboBox { ItemsSource = new[] { "云端模型", "本地模型" }, SelectedIndex = store.Data.LocalModel ? 1 : 0, Width = 215 };
        var row = new DockPanel { MinHeight = 34 }; DockPanel.SetDock(provider, Dock.Right); row.Children.Add(provider); row.Children.Add(MacTheme.Text("对话模型", 12.5)); p.Children.Add(row);
        var cloud = new StackPanel(); p.Children.Add(cloud);
        Label(cloud, "模型服务商");
        var service = new ComboBox { ItemsSource = ModelProviders.All, SelectedItem = ModelProviders.Get(store.Data.Provider), HorizontalAlignment = HorizontalAlignment.Stretch, MaxDropDownHeight = 280 };
        cloud.Children.Add(service);
        string selectedId = store.Data.Provider;
        var drafts = new Dictionary<string, (string Address, string Model, string Key)>();
        Label(cloud, "Base URL"); address = new TextBox { Text = store.Data.BaseUrl }; cloud.Children.Add(address);
        Label(cloud, "模型名称 / 推理接入点 ID"); model = new TextBox { Text = store.Data.Model }; cloud.Children.Add(model);
        Label(cloud, "API Key"); key = new PasswordBox { ToolTip = "留空保留已保存的密钥" }; cloud.Children.Add(key);
        var feedback = MacTheme.Hint(""); feedback.TextWrapping = TextWrapping.Wrap;
        var providerHint = MacTheme.Hint(""); providerHint.TextWrapping = TextWrapping.Wrap;
        void ShowProviderHint()
        {
            providerHint.Text = selectedId == "anthropic" ? "Claude 使用原生 Messages 接口。填写账户可用的文本模型 ID。" : "填写账户可用的文本对话模型 ID；地区或套餐不同可修改 Base URL。";
            providerHint.Text += store.Profile(selectedId).ProtectedKey.Length > 0 ? " 已保存此服务商密钥，留空保留。" : " 此服务商尚未保存密钥。";
        }
        service.SelectionChanged += (_, _) =>
        {
            drafts[selectedId] = (address.Text, model.Text, key.Password);
            selectedId = ((ModelProvider)service.SelectedItem).Id;
            var saved = store.Profile(selectedId);
            var draft = drafts.TryGetValue(selectedId, out var d) ? d : (saved.BaseUrl, saved.Model, "");
            address.Text = draft.Item1; model.Text = draft.Item2; key.Password = draft.Item3;
            feedback.Text = "切换后请保存模型设置。"; ShowProviderHint();
        };
        ShowProviderHint(); cloud.Children.Add(providerHint);
        var test = Button("测试连接", () => { }); test.Click += async (_, _) =>
        {
            test.IsEnabled = false; service.IsEnabled = false; address.IsEnabled = false; model.IsEnabled = false; key.IsEnabled = false;
            try { using var ct = new CancellationTokenSource(TimeSpan.FromSeconds(90)); var secret = key.Password.Length > 0 ? key.Password.Trim() : store.ProfileKey(selectedId, address.Text); if (secret.Length == 0) throw new InvalidOperationException("请填写该服务商的 API Key。"); await new CloudClient().Generate(address.Text.Trim(), model.Text.Trim(), secret, [new("user", "请只回复：你好")], _ => { }, ct.Token, provider: selectedId); feedback.Text = "连接成功。点击保存模型设置后应用。"; }
            catch (Exception e) { feedback.Text = e.Message; }
            finally { test.IsEnabled = true; service.IsEnabled = true; address.IsEnabled = true; model.IsEnabled = true; key.IsEnabled = true; }
        };
        cloud.Children.Add(Row(Button("服务商文档 ↗", () => Process.Start(new ProcessStartInfo(ModelProviders.Get(selectedId).Docs) { UseShellExecute = true })), test));
        Hint(cloud, "云端聊天会把对话与相关记忆发送给所选模型。API Key 加密保存在本机；留空可保留已保存的密钥。");
        var local = new StackPanel(); p.Children.Add(local); Label(local, "本地服务地址"); var localUrl = new TextBox { Text = store.Data.LocalUrl }; local.Children.Add(localUrl); Label(local, "模型名称 / 推理接入点 ID"); var localName = new TextBox { Text = store.Data.LocalModelName }; local.Children.Add(localName);
        var start = Button("启动随附的本地模型", () => { }); local.Children.Add(start); start.Click += async (_, _) => { start.IsEnabled = false; try { await pet.Local.Start(); feedback.Text = "本地模型已就绪。"; } catch (Exception e) { feedback.Text = e.Message; } finally { start.IsEnabled = true; } };
        Hint(local, "本地聊天不发送云端密钥。聊天中的笔记和提醒使用当前对话模型；自动记忆整理、备忘建议和热点仍使用已配置的云端模型。");
        void Provider() { cloud.Visibility = provider.SelectedIndex == 0 ? Visibility.Visible : Visibility.Collapsed; local.Visibility = provider.SelectedIndex == 1 ? Visibility.Visible : Visibility.Collapsed; }
        provider.SelectionChanged += (_, _) => Provider(); Provider();
        p.Children.Add(Button("保存模型设置", () =>
        {
            try
            {
                if (request is not null) throw new InvalidOperationException("请等当前回复结束，或先停止回复再切换模型。");
                if (!test.IsEnabled) throw new InvalidOperationException("请等连接测试结束再保存。");
                bool useLocal = provider.SelectedIndex == 1;
                if (useLocal) { CloudClient.LocalEndpoint(localUrl.Text); if (string.IsNullOrWhiteSpace(localName.Text)) throw new ArgumentException("请填写模型名称。"); store.Data.LocalUrl = localUrl.Text.Trim(); store.Data.LocalModelName = localName.Text.Trim(); }
                else { store.SaveProfile(selectedId, address.Text, model.Text, key.Password); key.Clear(); drafts.Remove(selectedId); ShowProviderHint(); }
                if (useLocal) { store.Data.LocalModel = true; store.Save(); }
                feedback.Text = "设置已应用。";
            }
            catch (Exception e) { feedback.Text = e.Message; }
        })); p.Children.Add(feedback); p.Children.Add(MacTheme.Divider());
        Toggle(p, "记住主人与共同经历", store.Data.MemoryEnabled, v => store.Data.MemoryEnabled = v);
        Toggle(p, "云端整理记忆", store.Data.AutoMemory, v => store.Data.AutoMemory = v);
        Hint(p, "共同经历保存在本机。开启云端整理后，有记忆价值的聊天会在回复后调用一次当前云端模型，发送这轮原话和少量已有记忆。");
        p.Children.Add(Button("打开小本本…", () => OpenFeature("memory"))); p.Children.Add(MacTheme.Divider());
        Toggle(p, "定时分享热点", store.Data.NewsEnabled, v => store.Data.NewsEnabled = v);
        Hint(p, "北京时间每天 11:00、16:00、19:00，按记忆中的偏好挑一条，等空闲时讲给你听。云端选题和写稿会额外消耗模型额度。");
        p.Children.Add(Button("打开热点小报…", () => OpenFeature("news"))); p.Children.Add(MacTheme.Divider());
        var sizeRow = new DockPanel { MinHeight = 34 }; var sizes = (FrameworkElement)MacTheme.Segments(["迷你", "小", "中", "大"], Array.IndexOf(new[] { .5, .8, 1d, 1.3 }, store.Data.Scale), i => { store.Data.Scale = new[] { .5, .8, 1d, 1.3 }[i]; pet.ApplyScale(); Persist(); }); sizes.Width = 230; DockPanel.SetDock(sizes, Dock.Right); sizeRow.Children.Add(sizes); sizeRow.Children.Add(MacTheme.Text("宠物大小", 12.5)); p.Children.Add(sizeRow);
        Hint(p, "拖到屏幕左右边缘后松手，噜噜会贴墙。鼠标靠近时探出身子，移开后缩回。拖回桌面或点“过来这边”即可恢复活动。");
        Toggle(p, "会主动找你说话", store.Data.Proactive, v => store.Data.Proactive = v);
        var frequency = MacTheme.Segments(["文静", "正常", "话痨"], store.Data.ChatterMinutes >= 12 ? 0 : store.Data.ChatterMinutes >= 6 ? 1 : 2, i => { store.Data.ChatterMinutes = new[] { 12d, 6d, 3d }[i]; Persist(); }); p.Children.Add(frequency);
        Toggle(p, "夜间自动睡觉 (23:00–7:00)", store.Data.NightSleep, v => store.Data.NightSleep = v);
        Toggle(p, "会跳上应用窗口", store.Data.WindowJump, v => store.Data.WindowJump = v);
        Toggle(p, "方舟深度思考", store.Data.ThinkingEnabled, v => store.Data.ThinkingEnabled = v);
        Hint(p, "其他服务商采用所选模型的默认思考策略，可通过模型 ID 选择推理模型。");
        p.Children.Add(MacTheme.Divider()); p.Children.Add(Row(Button("打开备忘录…", () => OpenFeature("memos")), Button("打开信箱…", () => OpenFeature("mail"))));
        p.Children.Add(Button("重置宠物状态", () => { if (Confirm("把饱食度、精力和心情恢复到初始值？")) { store.Data.Fullness = 75; store.Data.Energy = 80; store.Data.Happiness = 75; Persist(); } }));
        p.Children.Add(MacTheme.Divider());
        Hint(p, "关闭聊天窗口后，噜噜会继续留在桌面。要完全结束程序，请点击“退出噜噜”。");
        p.Children.Add(Button("退出噜噜", pet.ExitApp));
        Hint(p, "Meow · 住在桌面上的小小陪伴"); return MacTheme.Scroll(p);
    }
    private UIElement Memory()
    {
        var page = MacTheme.Page("张噜噜的小本本", out var head, out var foot);
        var count = MacTheme.Text(""); head.Children.Add(count);
        Hint(head, store.Data.MemoryEnabled ? "一起度过的每一天，噜噜都会记在心里。" : "记忆已暂停：保留小本本，但不继续学习或用于聊天。");
        var search = new TextBox { ToolTip = "搜索小本本", Margin = new Thickness(0, 4, 0, 6) }; head.Children.Add(search);
        int tab = 0; bool old = false; var rows = new StackPanel();
        void Refresh()
        {
            count.Text = $"相伴 {store.Data.Experiences.Select(x => x.Day).Distinct().Count()} 天 · {store.Data.Facts.Count(x => x.Active)} 条当前记忆 · {store.Data.Experiences.Count} 组共同经历 · {store.Data.Notes.Count(x => !x.Archived)} 条笔记";
            rows.Children.Clear(); string query = search.Text.Trim();
            if (tab == 0)
            {
                foreach (var fact in store.Data.Facts.Where(x => (old || x.Active) && (x.Text + x.Evidence).Contains(query, StringComparison.OrdinalIgnoreCase)).OrderByDescending(x => x.At))
                {
                    var card = new StackPanel(); var top = new DockPanel(); var forget = Button("忘掉", () => { store.Data.Facts.Remove(fact); store.Data.History.Clear(); store.Data.PendingReminder = null; conversation.Children.Clear(); Persist(); Refresh(); }); DockPanel.SetDock(forget, Dock.Right); top.Children.Add(forget); top.Children.Add(MacTheme.Text(fact.Text, 13, true)); card.Children.Add(top);
                    Hint(card, $"{fact.At.LocalDateTime:yyyy/M/d HH:mm} · {(fact.Active ? "当前记忆" : "历史版本")}"); card.Children.Add(MacTheme.Hint("主人原话：" + fact.Evidence)); rows.Children.Add(MacTheme.Card(card));
                }
            }
            else if (tab == 2) foreach (var note in store.Data.Notes.Where(n => (old || !n.Archived) && (n.Title + n.Body).Contains(query, StringComparison.OrdinalIgnoreCase)).OrderByDescending(n => n.Updated))
            {
                var card = new StackPanel(); card.Children.Add(MacTheme.Text(note.Title + (note.Archived ? "（已归档）" : ""), 14, true)); Hint(card, note.Body);
                card.Children.Add(Row(Button("编辑", () => EditNote(note)), Button(note.Archived ? "恢复" : "归档", () => { var before = note.Archived; note.Archived = !before; if (!Persist()) note.Archived = before; Refresh(); })));
                rows.Children.Add(MacTheme.Card(card));
            }
            else foreach (var exp in store.Data.Experiences.Where(x => (x.Kind + x.Day).Contains(query, StringComparison.OrdinalIgnoreCase)).OrderByDescending(x => x.Day))
            {
                var card = new DockPanel(); var forget = Button("忘掉", () => { store.Data.Experiences.Remove(exp); Persist(); Refresh(); }); DockPanel.SetDock(forget, Dock.Right); card.Children.Add(forget); var text = new StackPanel(); text.Children.Add(MacTheme.Text(exp.Kind, 13, true)); Hint(text, $"{exp.Day} · 当天 {exp.Count} 次 · 来自实际互动"); card.Children.Add(text); rows.Children.Add(MacTheme.Card(card));
            }
            if (rows.Children.Count == 0) { var empty = MacTheme.Hint(tab == 2 ? "还没有笔记。可以在聊天里说：记下：买牛奶。" : tab == 0 ? "还没有这些记忆。你可以告诉我：‘叫我珺大王’、‘我喜欢茉莉花茶’。" : "还没有这些共同经历。摸摸头、喂食或陪我玩，都会慢慢写进来。"); empty.Margin = new Thickness(0, 24, 0, 24); rows.Children.Add(empty); }
        }
        head.Children.Add(MacTheme.Segments(["主人资料与喜好", "共同经历", "笔记"], 0, i => { tab = i; Refresh(); }));
        head.Children.Add(Button("新增笔记", () => EditNote(null)));
        head.Children.Add(MacTheme.Toggle("显示旧版本、过期记忆和归档笔记", false, v => { old = v; Refresh(); }));
        var manual = new Expander { Header = "主人手写的资料", Margin = new Thickness(0, 4, 0, 8) }; var manualPanel = new StackPanel(); var memory = new TextBox { Text = store.Data.Memory, AcceptsReturn = true, TextWrapping = TextWrapping.Wrap, Height = 80, MaxLength = 8000, VerticalScrollBarVisibility = ScrollBarVisibility.Auto }; manualPanel.Children.Add(memory); manualPanel.Children.Add(Button("保存", () => { store.Data.Memory = memory.Text; Persist(); })); manual.Content = manualPanel; head.Children.Add(manual);
        foot.Children.Add(MacTheme.Divider()); Hint(foot, "记错了？在聊天里重新告诉我。忘掉记忆会同时清空短期聊天，避免从旧对话重新想起。清空聊天本身会保留小本本。");
        HeaderAccessory(head, Button("清空记忆", () => { if (!Confirm("清空主人资料、共同经历和聊天记录？独立保存的笔记会保留。")) return; store.Data.Facts.Clear(); store.Data.Experiences.Clear(); store.Data.Memory = ""; store.Data.History.Clear(); store.Data.PendingReminder = null; memory.Clear(); conversation.Children.Clear(); Persist(); Refresh(); }));
        var storage = new DockPanel(); var open = Button("打开存储位置", OpenStorage); DockPanel.SetDock(open, Dock.Right); storage.Children.Add(open); storage.Children.Add(MacTheme.Hint("记忆保存在这台电脑上")); foot.Children.Add(storage);
        RefreshWithTools(page, Refresh); page.Children.Add(MacTheme.Scroll(rows)); search.TextChanged += (_, _) => Refresh(); page.Loaded += (_, _) => Refresh(); Refresh(); return page;
    }
    private UIElement Memos()
    {
        var page = MacTheme.Page("噜噜备忘录", out var head, out var foot);
        var pending = MacTheme.Hint(""); HeaderAccessory(head, pending);
        Hint(head, "记下时间和要做的事，噜噜到点会提醒，也会每半小时想一想要不要提前叫你准备。");
        Toggle(head, "让噜噜主动提前提醒", store.Data.EarlyReminders, v => store.Data.EarlyReminders = v);
        var editor = new StackPanel(); var editorTitle = MacTheme.Text("新增备忘", 13, true); editor.Children.Add(editorTitle);
        var title = new TextBox { MaxLength = 200, Margin = new Thickness(0, 8, 0, 6), ToolTip = "要做的事，例如：和朋友聚会" }; editor.Children.Add(title);
        var due = new TextBox { Text = DateTime.Now.AddHours(1).ToString("yyyy-MM-dd HH:mm"), Width = 175, ToolTip = "提醒时间：yyyy-MM-dd HH:mm" };
        var saveMemo = Button("添加", () => { }); var cancelEdit = Button("取消编辑", () => { }); cancelEdit.Visibility = Visibility.Collapsed; saveMemo.IsEnabled = false; title.TextChanged += (_, _) => saveMemo.IsEnabled = !string.IsNullOrWhiteSpace(title.Text);
        Memo? editing = null; bool finished = false; var rows = new StackPanel(); var error = MacTheme.Hint("");
        void Reset() { editing = null; title.Clear(); due.Text = DateTime.Now.AddHours(1).ToString("yyyy-MM-dd HH:mm"); editorTitle.Text = "新增备忘"; saveMemo.Content = "添加"; cancelEdit.Visibility = Visibility.Collapsed; }
        void Refresh()
        {
            pending.Text = $"{store.Data.Memos.Count(x => !x.Done && !x.Cancelled)} 条待办";
            rows.Children.Clear();
            foreach (var memo in store.Data.Memos.Where(x => finished || (!x.Done && !x.Cancelled)).OrderBy(x => x.Done || x.Cancelled).ThenBy(x => x.Due))
            {
                var card = new StackPanel(); var heading = new DockPanel(); var state = MacTheme.Hint(memo.Cancelled ? "已取消" : memo.Done ? "已完成" : memo.Notified ? "已到点提醒" : "待提醒"); DockPanel.SetDock(state, Dock.Right); heading.Children.Add(state); heading.Children.Add(MacTheme.Text(memo.Title, 14, true)); card.Children.Add(heading); Hint(card, memo.Due.LocalDateTime.ToString("yyyy年M月d日 HH:mm"));
                void Change(Action change) { change(); Persist(); Refresh(); }
                var buttons = new WrapPanel();
                if (!memo.Done && !memo.Cancelled) { buttons.Children.Add(Button("完成", () => Change(() => memo.Done = true))); buttons.Children.Add(Button("编辑", () => { editing = memo; title.Text = memo.Title; due.Text = memo.Due.LocalDateTime.ToString("yyyy-MM-dd HH:mm"); editorTitle.Text = "编辑备忘"; saveMemo.Content = "保存修改"; cancelEdit.Visibility = Visibility.Visible; })); buttons.Children.Add(Button("稍后十分钟", () => Change(() => { memo.Due = DateTimeOffset.Now.AddMinutes(10); memo.Notified = false; }))); buttons.Children.Add(Button("取消提醒", () => Change(() => memo.Cancelled = true))); }
                else buttons.Children.Add(Button("恢复待办", () => Change(() => { memo.Done = memo.Cancelled = memo.Notified = false; })));
                buttons.Children.Add(Button("删除", () => { if (Confirm("删除这条备忘？\n" + memo.Title)) Change(() => { store.Data.Memos.Remove(memo); if (editing == memo) Reset(); }); })); card.Children.Add(buttons); rows.Children.Add(MacTheme.Card(card));
            }
            if (rows.Children.Count == 0) { var empty = MacTheme.Hint("还没有备忘。也可以在聊天里说：‘明天晚上七点提醒我参加聚会’。"); empty.Margin = new Thickness(0, 28, 0, 28); rows.Children.Add(empty); }
        }
        cancelEdit.Click += (_, _) => Reset(); saveMemo.Click += (_, _) =>
        {
            if (string.IsNullOrWhiteSpace(title.Text) || !DateTime.TryParseExact(due.Text, "yyyy-MM-dd HH:mm", CultureInfo.InvariantCulture, DateTimeStyles.None, out var date) || TimeZoneInfo.Local.IsInvalidTime(date) || TimeZoneInfo.Local.IsAmbiguousTime(date)) { error.Text = "请填写事项和有效且不歧义的本地时间。"; return; }
            var item = editing ?? new Memo(); item.Title = title.Text.Trim(); item.Due = new DateTimeOffset(date, TimeZoneInfo.Local.GetUtcOffset(date)); item.Notified = false; if (editing is null) store.Data.Memos.Add(item); if (Persist()) { Reset(); Refresh(); error.Text = ""; }
        }; editor.Children.Add(Row(MacTheme.Text("提醒时间  ", 12), due, saveMemo, cancelEdit));
        head.Children.Add(MacTheme.Card(editor)); head.Children.Add(error); head.Children.Add(MacTheme.Toggle("显示已完成和已取消", false, v => { finished = v; Refresh(); }));
        foot.Children.Add(MacTheme.Divider()); Hint(foot, "时间按电脑当前时区显示。需要保持噜噜运行；错过的到点提醒会在恢复后补上。不填完整时间时，噜噜会先问清楚。"); foot.Children.Add(Button("打开存储位置", OpenStorage)); page.Children.Add(MacTheme.Scroll(rows)); RefreshWithTools(page, Refresh); page.Loaded += (_, _) => Refresh(); Refresh(); return page;
    }
    private UIElement NewsPanel()
    {
        var page = MacTheme.Page("张噜噜的热点小报", out var head, out var foot); Toggle(head, "定时分享热点", store.Data.NewsEnabled, v => store.Data.NewsEnabled = v); Hint(head, "北京时间 11:00 · 16:00 · 19:00，每次最多一条。");
        var result = MacTheme.Hint(""); var rows = new StackPanel();
        void Refresh()
        {
            rows.Children.Clear(); foreach (var news in store.Data.News.AsEnumerable().Reverse())
            {
                var card = new StackPanel(); var top = new DockPanel(); var source = Button("微博 ↗", () => { if (Uri.TryCreate(news.Url, UriKind.Absolute, out var u) && u.Scheme == "https" && u.Host == "s.weibo.com") Process.Start(new ProcessStartInfo(u.AbsoluteUri) { UseShellExecute = true }); }); DockPanel.SetDock(source, Dock.Right); top.Children.Add(source); top.Children.Add(MacTheme.Text(news.Title, 14, true)); card.Children.Add(top); Hint(card, $"热搜话题 · 抓取于 {news.At.ToOffset(TimeSpan.FromHours(8)):M月d日 HH:mm}（北京时间）"); card.Children.Add(MacTheme.Text(news.Summary)); rows.Children.Add(MacTheme.Card(card));
            }
            if (rows.Children.Count == 0) { var t = MacTheme.Hint("还没有热点小报。你可以先告诉噜噜‘我关注人工智能’、‘我不喜欢娱乐八卦’，再找一条试试。"); t.Margin = new Thickness(0, 28, 0, 28); rows.Children.Add(t); }
        }
        var fetch = Button("现在找一条", () => { }); HeaderAccessory(head, fetch); head.Children.Add(result); head.Children.Add(MacTheme.Divider()); fetch.Click += async (_, _) => { fetch.IsEnabled = false; result.Text = "噜噜正在找热点…"; try { using var ct = new CancellationTokenSource(TimeSpan.FromSeconds(90)); var n = await pet.Features.FetchNews(ct.Token); Refresh(); result.Text = "找到啦。"; pet.Say(n.Summary); } catch (Exception e) { result.Text = e.Message; } finally { fetch.IsEnabled = true; } };
        foot.Children.Add(MacTheme.Divider()); Hint(foot, "需保持噜噜运行和网络连接。云端选题与写稿复用当前模型；来源不可用时会提示错误。小报保存在本机。"); page.Children.Add(MacTheme.Scroll(rows)); page.Loaded += (_, _) => Refresh(); Refresh(); return page;
    }
    private UIElement MailPanel()
    {
        var page = MacTheme.Page("噜噜信箱", out var head, out var foot); var state = MacTheme.Hint("");
        var title = (TextBlock)head.Children[0]; title.Inlines.InsertBefore(title.Inlines.FirstInline, new System.Windows.Documents.InlineUIContainer(ColorEmoji.Icon("💌", 18))); title.Inlines.InsertAfter(title.Inlines.FirstInline, new System.Windows.Documents.Run(" "));
        var unread = MacTheme.Hint(""); HeaderAccessory(head, unread);
        var enable = MacTheme.Toggle("启用通信", store.Data.Mail.Enabled, _ => { }); enable.Width = 115;
        var toolbar = new DockPanel { Margin = new Thickness(0, 0, 0, 4) }; head.Children.Add(toolbar); toolbar.Children.Add(enable);
        enable.Click += async (_, _) => { store.Data.Mail.Enabled = enable.IsChecked == true; Persist(); try { if (store.Data.Mail.Enabled) { await pet.Mailbox.Start(); state.Text = "信箱已启动。"; } else { pet.Mailbox.Dispose(); state.Text = "信箱已关闭。"; } } catch (Exception e) { state.Text = e.Message; } };
        Hint(head, "本机：" + Environment.MachineName); head.Children.Add(state);
        var layout = new Grid(); layout.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(210) }); layout.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(12) }); layout.ColumnDefinitions.Add(new ColumnDefinition());
        var list = new StackPanel(); var read = new DockPanel(); var readCard = MacTheme.Card(read, 16); Grid.SetColumn(readCard, 2); layout.Children.Add(MacTheme.Scroll(list)); layout.Children.Add(readCard);
        int tab = 0; MailEntry? selected = null;
        void Read()
        {
            read.Children.Clear(); if (selected is null) { var empty = new StackPanel { VerticalAlignment = VerticalAlignment.Center }; var icon = ColorEmoji.Icon("💌", 48); icon.HorizontalAlignment = HorizontalAlignment.Center; empty.Children.Add(icon); empty.Children.Add(MacTheme.Hint("点开一封信，就能在这里读到内容。")); read.Children.Add(empty); return; }
            var entry = selected; if (entry.Incoming && !entry.Read) { entry.Read = true; Persist(); }
            var heading = new StackPanel(); DockPanel.SetDock(heading, Dock.Top); read.Children.Add(heading); heading.Children.Add(MacTheme.Text(entry.Incoming ? "寄给主人的一封信 💌" : "寄给另一只噜噜的信", 14, true));
            Hint(heading, MailDate(entry)); var buttons = new WrapPanel { Margin = new Thickness(0, 8, 0, 0) }; DockPanel.SetDock(buttons, Dock.Bottom); read.Children.Add(buttons);
            buttons.Children.Add(Button("删除", () => { if (!Confirm("只删除本机保存的信件，无法从对方信箱撤回。继续？")) return; store.Data.Mail.Entries.Remove(entry); selected = null; Persist(); Refresh(); Read(); }));
            if (!entry.Incoming && !entry.Delivered && !entry.Cancelled) { buttons.Children.Add(Button("停止重试", () => { entry.Cancelled = true; Persist(); Refresh(); Read(); })); }
            var body = MacTheme.Text(entry.Letter.body, 15); body.LineHeight = 24; read.Children.Add(MacTheme.Scroll(body));
        }
        void Refresh()
        {
            unread.Text = $"{pet.Mailbox.Unread} 封未读";
            list.Children.Clear(); state.Text = pet.Mailbox.Error.Length > 0 ? pet.Mailbox.Error : $"{pet.Mailbox.Unread} 封未读 · {(store.Data.Mail.PeerID.Length > 0 ? "已绑定设备" : "尚未绑定设备")}";
            foreach (var entry in store.Data.Mail.Entries.Where(x => x.Incoming == (tab == 0)).Reverse())
            {
                var label = new StackPanel(); var statusLabel = MacTheme.Text(entry.Incoming ? entry.Read ? "已读" : "💌 未读" : entry.Delivered ? "已送达" : entry.Cancelled ? "已停止重试" : "待寄 · 等待回执", 11, true); if (entry.Incoming && !entry.Read) statusLabel.Foreground = MacTheme.Accent; label.Children.Add(statusLabel);
                var preview = MacTheme.Text(entry.Letter.body, 13); preview.MaxHeight = 38; preview.Margin = new Thickness(0, 5, 0, 5); label.Children.Add(preview); label.Children.Add(MacTheme.Hint(MailDate(entry)));
                var button = Button("", () => { selected = entry; Read(); Refresh(); }); button.Content = label; button.HorizontalAlignment = HorizontalAlignment.Stretch; button.HorizontalContentAlignment = HorizontalAlignment.Stretch; button.Padding = new Thickness(10); button.Margin = new Thickness(0, 0, 0, 8); button.BorderThickness = new Thickness(0); button.Background = selected == entry ? PetDrawing.B("#1FFA8CA1") : PetDrawing.B("#CCFFFFFF"); list.Children.Add(button);
            }
            if (list.Children.Count == 0) list.Children.Add(MacTheme.Hint(tab == 0 ? "还没有收到的信。" : "还没有寄出的信。"));
        }
        var retry = Button("刷新 / 重试", () => { }); retry.Click += async (_, _) => { retry.IsEnabled = false; try { await pet.Mailbox.Tick(); Refresh(); } finally { retry.IsEnabled = true; } };
        var bind = Button("设备绑定", () => MailBinding(Refresh)); bind.HorizontalAlignment = HorizontalAlignment.Right; toolbar.Children.Add(bind);
        var selection = new DockPanel(); var compose = Button("写一封信", () => MailCompose(Refresh)); compose.VerticalAlignment = VerticalAlignment.Center; DockPanel.SetDock(compose, Dock.Right); selection.Children.Add(compose); retry.VerticalAlignment = VerticalAlignment.Center; DockPanel.SetDock(retry, Dock.Right); selection.Children.Add(retry); selection.Children.Add(MacTheme.Segments(["收到的信", "寄出的信"], 0, i => { tab = i; selected = null; Refresh(); Read(); })); head.Children.Add(selection);
        foot.Children.Add(MacTheme.Divider()); Hint(foot, "两台电脑都需运行 Meow 并启用信箱。对方离线时，信保留在待寄箱并自动重试；“已送达”表示对方已保存。打开后的信会继续保留在本机信箱里。");
        page.Children.Add(layout); RefreshWithTools(page, Refresh); page.Loaded += (_, _) => Refresh(); Refresh(); Read(); return page;
    }
    private static string MailDate(MailEntry entry) => DateTimeOffset.TryParse(entry.Letter.createdAt, out var d) ? d.LocalDateTime.ToString("M月d日 HH:mm") : "";
    private void MailBinding(Action refresh)
    {
        var p = Panel(); PageTitle(p, "绑定另一台 Meow"); Hint(p, "1. 两台电脑都启用信箱。\n2. 复制各自的设备码，发给对方。\n3. 两边各粘贴一次对方的设备码并绑定。");
        var own = new TextBox { Text = store.Data.Mail.Code, IsReadOnly = true, TextWrapping = TextWrapping.Wrap, Height = 70 }; p.Children.Add(own);
        p.Children.Add(Button("复制本机设备码", () => { if (own.Text.Length > 0) Clipboard.SetText(own.Text); }));
        Label(p, "粘贴对方完整的设备码"); var peer = new TextBox { Text = store.Data.Mail.PeerCode, TextWrapping = TextWrapping.Wrap, AcceptsReturn = true, Height = 80 }; p.Children.Add(peer); var result = MacTheme.Hint("");
        var bind = Button("绑定对方", () => { }); bind.Click += async (_, _) => { bind.IsEnabled = false; try { if (!store.Data.Mail.Enabled) throw new InvalidOperationException("请先启用通信。"); await pet.Mailbox.Start(); await pet.Mailbox.Bind(peer.Text.Trim()); own.Text = store.Data.Mail.Code; result.Text = "绑定成功。对方也需要绑定你的设备码。"; refresh(); } catch (Exception e) { result.Text = e.Message; } finally { bind.IsEnabled = true; } };
        var unbind = Button("解除绑定", () => { }); unbind.Click += async (_, _) => { if (!Confirm("解除绑定并停止重试待寄信件？历史信件会保留。")) return; try { await pet.Mailbox.Bind(""); peer.Clear(); refresh(); result.Text = "已解除绑定。"; } catch (Exception e) { result.Text = e.Message; } };
        p.Children.Add(Row(bind, unbind)); p.Children.Add(result); var window = MacTheme.Window("设备绑定", 460, 430, MacTheme.Scroll(p)); window.Show();
    }
    private void MailCompose(Action refresh)
    {
        var p = Panel(); PageTitle(p, "写一封信 💌"); Hint(p, "信件会寄到另一只噜噜的信箱里。最多 5000 字。");
        var draft = new TextBox { Text = store.Data.Mail.Draft?.Body ?? "", AcceptsReturn = true, TextWrapping = TextWrapping.Wrap, Height = 250, MaxLength = 5000, VerticalScrollBarVisibility = ScrollBarVisibility.Auto }; p.Children.Add(draft); var result = MacTheme.Hint(""); var sendMail = Button("寄出", () => { }); var window = MacTheme.Window("写一封信", 460, 430, p);
        var saveDraft = Button("保存草稿", () => { });
        saveDraft.Click += async (_, _) => { var receipts = await localTools.Execute([ConversationTools.Call("mail.draft", new { body = draft.Text })], "保存草稿", Guid.NewGuid(), default); result.Text = receipts[0].Ok ? "草稿已保存，尚未寄出。" : receipts[0].Text; };
        sendMail.Click += async (_, _) => { sendMail.IsEnabled = false; try { if (!store.Data.Mail.Enabled) throw new InvalidOperationException("请先启用通信。"); var saved = store.Data.Mail.Draft; pet.Mailbox.Queue(draft.Text, saved is not null && saved.Body == draft.Text && saved.PeerID == store.Data.Mail.PeerID ? saved.Id : null); draft.Clear(); refresh(); window.Close(); await pet.Mailbox.Tick(); refresh(); } catch (Exception e) { result.Text = e.Message; } finally { sendMail.IsEnabled = true; } };
        p.Children.Add(Row(sendMail, saveDraft, Button("取消", window.Close))); p.Children.Add(result); window.Show();
    }
    private void EditNote(NotebookEntry? note)
    {
        var panel = Panel(); PageTitle(panel, note is null ? "新增笔记" : "编辑笔记");
        var title = new TextBox { Text = note?.Title ?? "", MaxLength = 120 }; var body = new TextBox { Text = note?.Body ?? "", MaxLength = 8000, Height = 240, AcceptsReturn = true, TextWrapping = TextWrapping.Wrap, VerticalScrollBarVisibility = ScrollBarVisibility.Auto };
        Label(panel, "标题"); panel.Children.Add(title); Label(panel, "内容"); panel.Children.Add(body); var error = MacTheme.Hint(""); panel.Children.Add(error);
        var window = MacTheme.Window("噜噜的笔记", 460, 440, panel); var save = Button("保存", () => { });
        save.Click += async (_, _) => { var results = await localTools.Execute([ConversationTools.Call(note is null ? "note.add" : "note.update", new { query = note?.Id.ToString() ?? "", title = title.Text, body = body.Text })], note is null ? "新增笔记" : "修改笔记", Guid.NewGuid(), default); if (results[0].Ok) { ToolsChanged?.Invoke(); window.Close(); } else error.Text = results[0].Text; };
        panel.Children.Add(Row(save, Button("取消", window.Close))); window.Show();
    }
}
