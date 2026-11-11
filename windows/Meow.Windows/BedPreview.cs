using System.Diagnostics;
using System.IO;
using System.Text.Json;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;

namespace Meow.Windows;

internal sealed class BedPreview : Window
{
    internal BedPreview(bool walkOnly = false)
    {
        LuluBedScene.WarmUp();
        Title = walkOnly ? "张噜噜 · 回程动画（S14）" : "张噜噜 · 睡觉与唤醒（S14）"; Width = 900; Height = 570;
        WindowStartupLocation = WindowStartupLocation.CenterScreen; Background = PetDrawing.B("#FAF6EF");
        var layout = new DockPanel { Margin = new Thickness(20) }; Content = layout;
        var status = new TextBlock { FontSize = 19, Foreground = PetDrawing.B("#604B3D"), Margin = new Thickness(0, 0, 0, 12) };
        DockPanel.SetDock(status, Dock.Top); layout.Children.Add(status);
        var buttons = new WrapPanel { Margin = new Thickness(0, 12, 0, 0) }; DockPanel.SetDock(buttons, Dock.Bottom); layout.Children.Add(buttons);
        var stage = new Grid { Background = PetDrawing.B("#34475A"), ClipToBounds = true }; layout.Children.Add(stage);
        var drawing = new PetDrawing { Width = 800, Height = 400, HorizontalAlignment = HorizontalAlignment.Left, BedScene = new LuluBedScene() }; stage.Children.Add(drawing);
        bool automatic = false; double age = 0;
        var detail = new List<object>(); var loads = new List<object>();
        var intervals = new List<double>(); bool profileSaved = false;
        void Restart(bool playAll)
        {
            drawing.Width = drawing.Height * 2; drawing.BedScene = new(); age = 0; automatic = playAll; intervals.Clear(); detail.Clear(); loads.Clear(); profileSaved = false;
            if (walkOnly) { var scene = drawing.BedScene; scene.AssetLoadProbe = (name, ms, ready) => loads.Add(new { name, ms, ready, scene.Phase, scene.Elapsed }); }
        }
        void ReplayWalk() { Restart(false); var scene = drawing.BedScene!; scene.Advance(scene.SleepStarts); scene.RequestWake(); scene.Advance(scene.LoopDuration + 2); }
        if (walkOnly) ReplayWalk();
        void Button(string label, Action action) { var b = new Button { Content = label, Padding = new Thickness(12, 8, 12, 8), Margin = new Thickness(0, 0, 8, 0) }; b.Click += (_, _) => action(); buttons.Children.Add(b); }
        if (walkOnly) Button("重播起床回程", ReplayWalk);
        Button("入睡 / 重播", () => Restart(false));
        Button("叫醒", () => drawing.BedScene?.RequestWake());
        Button("整套连播", () => Restart(true));
        Button("桌面实际大小", () => { drawing.Height = 184; drawing.Width = drawing.BedScene is null ? 184 : 368; });
        Button("放大查看", () => { drawing.Height = 400; drawing.Width = drawing.BedScene is null ? 400 : 800; });
        var timer = Stopwatch.StartNew(); double previous = 0; TimeSpan lastRenderingTime = TimeSpan.MinValue;
        void Frame(object? sender, EventArgs e)
        {
            if (e is RenderingEventArgs rendering) { if (lastRenderingTime == rendering.RenderingTime) return; lastRenderingTime = rendering.RenderingTime; }
            double now = timer.Elapsed.TotalSeconds, gap = now - previous, dt = Math.Min(.1, gap); previous = now; age += dt;
            if (drawing.BedScene is { } scene)
            {
                if (walkOnly) detail.Add(new { gapMs = gap * 1000, scene.Phase, scene.Elapsed, previousClip = scene.DisplayedFrame.Clip, previousFrame = scene.DisplayedFrame.Index, drawMs = scene.LastDrawMilliseconds, fullGc = GC.CollectionCount(2) });
                if (age > .5 && scene.Phase is "arrive" or "leave") intervals.Add(gap * 1000);
                if (automatic && age >= scene.SleepStarts + 2) scene.RequestWake();
                scene.Advance(dt);
                status.Text = scene.Phase switch { "arrive" => "向右迈步 · 镜头跟随，床进入视野", "entry" => "走到床边 → 掀被 → 收脚 → 躺下", "loop" => scene.WakeRequested ? "收尾这次呼吸，准备起身…" : "安睡中 · 点击叫醒", "wake" => "醒来 → 起身 → 向左迈步", "leave" => "继续向左走 · 床逐渐退出视野", "settle" => "离开床边 → 收步站稳", _ => "整套完成 · 可以重播" };
                if (scene.Complete && !profileSaved && intervals.Count > 0)
                {
                    profileSaved = true; var ordered = intervals.Order().ToArray();
                    var report = new { samples = ordered.Length, medianFrameMs = ordered[ordered.Length / 2], p95FrameMs = ordered[(int)((ordered.Length - 1) * .95)], maxFrameMs = ordered[^1], over50Ms = ordered.Count(v => v > 50), note = "Observed WPF rendering intervals; leftward walking is resampled from 24 to 60 fps, rightward approach remains 24 fps." };
                    File.WriteAllText(Path.Combine(AppContext.BaseDirectory, "bed-preview-timing.json"), JsonSerializer.Serialize(report, new JsonSerializerOptions { WriteIndented = true }));
                    if (walkOnly) File.WriteAllText(Path.Combine(AppContext.BaseDirectory, "bed-walk-timing.json"), JsonSerializer.Serialize(new { detail, loads }, new JsonSerializerOptions { WriteIndented = true }));
                }
                // Exercise the same real idle handoff as PetWindow, not a frozen terminal frame.
                if (scene.Complete) { drawing.Time = now; drawing.FinishBedScene(); drawing.Width = drawing.Height; drawing.Action = "idle"; drawing.RestartAnimation(); }
            }
            drawing.Time = now; drawing.InvalidateVisual();
        }
        Loaded += (_, _) => { previous = timer.Elapsed.TotalSeconds; CompositionTarget.Rendering += Frame; };
        Closed += (_, _) => CompositionTarget.Rendering -= Frame;
    }
}
