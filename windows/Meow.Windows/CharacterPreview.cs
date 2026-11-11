using System.IO;
using System.Diagnostics;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Threading;

namespace Meow.Windows;

// Isolated, offline preview: no Store, credentials, model calls or mail service.
internal sealed class CharacterPreview : Window
{
    internal CharacterPreview()
    {
        Title = "张噜噜 · 视频动作体验版"; Width = Math.Min(960, SystemParameters.WorkArea.Width - 30); Height = Math.Min(780, SystemParameters.WorkArea.Height - 30); Background = PetDrawing.B("#FAF6EF");
        WindowStartupLocation = WindowStartupLocation.CenterScreen;
        var layout = new DockPanel { Margin = new Thickness(20) }; Content = layout;
        var title = new TextBlock { Text = "张噜噜 · 点下面的按钮试动作", FontFamily = new FontFamily("Microsoft YaHei UI"), FontSize = 26, Foreground = PetDrawing.B("#604B3D"), Margin = new Thickness(0, 0, 0, 12) };
        DockPanel.SetDock(title, Dock.Top); layout.Children.Add(title);
        var actions = new WrapPanel { Margin = new Thickness(0, 16, 0, 0) }; DockPanel.SetDock(actions, Dock.Bottom); layout.Children.Add(actions);
        var bedPreview = new Button { Content = "新睡铺流程…", Padding = new Thickness(12, 7, 12, 7), Margin = new Thickness(0, 0, 6, 6) };
        bedPreview.Click += (_, _) => new BedPreview().Show(); actions.Children.Add(bedPreview);
        var stage = new Grid { Background = PetDrawing.B("#34475A") }; stage.ColumnDefinitions.Add(new()); stage.ColumnDefinitions.Add(new()); layout.Children.Add(stage);
        var reference = new Image { Source = new BitmapImage(new Uri(Path.Combine(AppContext.BaseDirectory, "Assets", "Lulu", "reference-approved-v2.png"))), Stretch = Stretch.Uniform };
        stage.Children.Add(reference);
        var drawing = new PetDrawing { Width = 330, Height = 330, VerticalAlignment = VerticalAlignment.Center };
        Grid.SetColumn(drawing, 1); stage.Children.Add(drawing);
        foreach (var (label, action) in new[] { ("站立", "idle"), ("走路", "walk"), ("挥手", "wave"), ("睡觉", "sleep"), ("思考", "think"), ("吃西瓜", "eat"), ("玩球", "play"), ("抱信", "letter"), ("说话", "talk"), ("转圈", "spin"), ("打滚", "roll"), ("探头", "peek"), ("拖拽", "drag"), ("落地", "land"), ("点头", "nod"), ("摇头", "shakeHead") })
        {
            var button = new Button { Content = label, Padding = new Thickness(12, 7, 12, 7), Margin = new Thickness(0, 0, 6, 6) };
            button.Click += (_, _) => { drawing.KeepStatePose = action == "sleep"; drawing.Emotion = "neutral"; drawing.Action = action is "letter" or "talk" ? "idle" : action; drawing.Unread = action == "letter" ? 2 : 0; drawing.TalkLevel = action == "talk" ? .8 : 0; drawing.RestartAnimation(); };
            actions.Children.Add(button);
        }
        foreach (var (label, emotion) in new[] { ("开心", "happy"), ("喜欢", "love"), ("生气", "angry"), ("委屈", "sad"), ("害羞", "shy"), ("惊讶", "surprised"), ("困倦", "sleepy"), ("饥饿", "hungry"), ("好奇", "curious"), ("晕乎乎", "dizzy"), ("伸懒腰", "stretch"), ("跳舞", "dance") })
        {
            var button = new Button { Content = label, Padding = new Thickness(12, 7, 12, 7), Margin = new Thickness(0, 0, 6, 6) };
            button.Click += (_, _) => { drawing.KeepStatePose = false; drawing.Action = emotion is "stretch" or "dance" ? emotion : "idle"; drawing.Emotion = emotion; drawing.Unread = 0; drawing.TalkLevel = 0; drawing.RestartAnimation(); };
            actions.Children.Add(button);
        }
        var clock = new Stopwatch(); TimeSpan last = TimeSpan.MinValue; double lastFrame = 0;
        var intervals = new List<double>();
        void Frame(object? sender, EventArgs e)
        {
            if (e is RenderingEventArgs rendering) { if (rendering.RenderingTime == last) return; last = rendering.RenderingTime; }
            double now = clock.Elapsed.TotalSeconds;
            if (now > 1 && lastFrame > 0 && now - lastFrame < .5 && intervals.Count < 3600) intervals.Add((now - lastFrame) * 1000);
            lastFrame = now; drawing.Time = now; drawing.WalkPhase = drawing.Time * 6; drawing.InvalidateVisual();
        }
        Loaded += (_, _) => { clock.Start(); CompositionTarget.Rendering += Frame; };
        Closed += (_, _) =>
        {
            CompositionTarget.Rendering -= Frame;
            if (intervals.Count > 0)
            {
                intervals.Sort();
                File.WriteAllText(Path.Combine(AppContext.BaseDirectory, "preview-performance.txt"), $"Unique render callbacks: {intervals.Count}\nMedian interval: {intervals[intervals.Count / 2]:F2} ms\nP95 interval: {intervals[(int)((intervals.Count - 1) * .95)]:F2} ms\nIntervals over 33.4ms: {intervals.Count(x => x > 33.4)}\nThis measures rendering callbacks, not GPU presentation.\n");
            }
        };
    }
}
