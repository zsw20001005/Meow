using System.Diagnostics;
using System.IO;
using System.Reflection;
using System.Windows;
using System.Windows.Media;
using System.Windows.Media.Imaging;

namespace Meow.Windows;

internal static class BedEntryChecks
{
    internal static int Run()
    {
        string output = Path.Combine(AppContext.BaseDirectory, "bed-entry-checks"); Directory.CreateDirectory(output);
        var log = new List<string>();
        void Check(bool ok, string text) { if (!ok) throw new Exception(text); log.Add("PASS " + text); }
        var petField = typeof(PetWindow).GetField("pet", BindingFlags.NonPublic | BindingFlags.Instance)!;
        var closeField = typeof(PetWindow).GetField("closing", BindingFlags.NonPublic | BindingFlags.Instance)!;
        var areaProperty = typeof(PetWindow).GetProperty("Area", BindingFlags.NonPublic | BindingFlags.Instance)!;
        static BitmapSource Render(PetDrawing drawing, double width)
        {
            drawing.Width = width; drawing.Height = 256; drawing.Measure(new Size(width, 256)); drawing.Arrange(new Rect(0, 0, width, 256)); drawing.InvalidateVisual(); drawing.UpdateLayout();
            var image = new RenderTargetBitmap(512, 256, 96, 96, PixelFormats.Pbgra32); image.Render(drawing); image.Freeze(); return image;
        }
        static double Error(BitmapSource a, BitmapSource b)
        {
            var x = new byte[512 * 256 * 4]; var y = new byte[x.Length]; a.CopyPixels(x, 2048, 0); b.CopyPixels(y, 2048, 0);
            long total = 0; int count = 0;
            for (int p = 0; p < 256 * 256; p++)
            {
                int n = (p / 256 * 512 + p % 256) * 4;
                if (x[n + 3] < 8 && y[n + 3] < 8) continue;
                for (int c = 0; c < 4; c++) { total += Math.Abs(x[n + c] - y[n + c]); count++; }
            }
            return (double)total / Math.Max(1, count);
        }
        static void Save(BitmapSource image, string path)
        { var png = new PngBitmapEncoder(); png.Frames.Add(BitmapFrame.Create(image)); using var file = File.Create(path); png.Save(file); }
        try
        {
            foreach (var (name, emotion, phase, edge, film) in new[] {
                ("idle-open", "neutral", 0d, false, false), ("idle-blink", "neutral", .5, false, true),
                ("idle-late", "neutral", 35d/24, false, false), ("happy", "happy", 1.88, false, false),
                ("love", "love", 1.88, false, false), ("right-blink", "neutral", .5, true, true),
                ("right-happy", "happy", 1.88, true, false) })
            {
                string temp = Path.Combine(Path.GetTempPath(), "meow-entry-" + Guid.NewGuid());
                PetWindow? window = null;
                try
                {
                    var store = new Store(temp); store.Data.Scale = 256d / 230;
                    store.Data.MemoryEnabled = store.Data.Wander = store.Data.NightSleep = store.Data.WindowJump = false;
                    window = new PetWindow(store);
                    var drawing = (PetDrawing)petField.GetValue(window)!;
                    var area = (Rect)areaProperty.GetValue(window)!;
                    double origin = area.Right - 512;
                    window.Left = origin + (edge ? 256 : 0);
                    drawing.Action = "idle"; drawing.Emotion = emotion; drawing.PosePhase = phase;
                    var before = Render(drawing, 256); Save(before, Path.Combine(output, name + "-before.png"));
                    var timer = Stopwatch.StartNew(); window.Animate("sleep"); drawing.PosePhase = null;
                    var first = Render(drawing, window.Width); Save(first, Path.Combine(output, name + "-first.png"));
                    double error = Error(before, first);
                    log.Add($"{name} first-pose error {error:F6}/255"); Check(error < .05, name + " preserves the actually displayed pose at click");
                    var transition = drawing.PoseTransition!;
                    transition.Preparation.GetAwaiter().GetResult();
                    Save(transition.Preparation.Result[transition.Preparation.Result.Length / 2], Path.Combine(output, name + "-middle.png"));
                    log.Add($"{name} preparation {timer.Elapsed.TotalMilliseconds:F1} ms");
                    double initialLeft = window.Left;
                    string frames = Path.Combine(output, name + "-frames"); if (film) Directory.CreateDirectory(frames);
                    int count = film ? 660 : 60;
                    int handoffs = 0;
                    for (int i = 0; i < count; i++)
                    {
                        drawing.Time = i / 60d;
                        if (drawing.PoseTransition is { } pending) pending.Preparation.GetAwaiter().GetResult();
                        var pendingBefore = drawing.PoseTransition;
                        if (i > 0) window.AdvanceBedScene(1d / 60);
                        var current = Render(drawing, window.Width);
                        if (pendingBefore is not null && drawing.PoseTransition is null)
                        {
                            var expected = new RenderTargetBitmap(512, 256, 96, 96, PixelFormats.Pbgra32);
                            var v = new System.Windows.Controls.Image { Width = 256, Height = 256, Source = pendingBefore.Preparation.Result[^1] };
                            RenderOptions.SetBitmapScalingMode(v, BitmapScalingMode.HighQuality);
                            v.Measure(new Size(256, 256)); v.Arrange(new Rect(0, 0, 256, 256)); expected.Render(v);
                            double endError = Error(expected, current); log.Add($"{name} handoff {++handoffs} error {endError:F6}/255");
                            Check(endError < .1, name + " enters the target animation at the exact prepared endpoint");
                        }
                        if (edge && i < 30) Check(Math.Abs(window.Left - initialLeft) < .001, name + " stays grounded until the turn finishes");
                        if (film)
                        {
                            var stage = new DrawingVisual(); using (var dc = stage.RenderOpen())
                            { dc.DrawRectangle(PetDrawing.B("#34475A"), null, new Rect(0, 0, 512, 256)); dc.DrawImage(current, new Rect(window.Left - origin, 0, 512, 256)); }
                            var target = new RenderTargetBitmap(512, 256, 96, 96, PixelFormats.Pbgra32); target.Render(stage);
                            Save(target, Path.Combine(frames, $"{i:D4}.png"));
                        }
                    }
                    if (film)
                    {
                        File.WriteAllText(Path.Combine(frames, "frame-count.txt"), count.ToString()); File.WriteAllText(Path.Combine(frames, "frame-rate.txt"), "60");
                        if (edge) Check(handoffs == 3 && !drawing.BedApproaching && drawing.BedScene is not null, "right edge covers turn-to-walk, walk-to-turn and turn-to-bed handoffs");
                    }
                    // Drag/cancel must not leave a completed worker able to start a scene later.
                    typeof(PetWindow).GetMethod("CancelBedScene", BindingFlags.NonPublic | BindingFlags.Instance)!.Invoke(window, null);
                    Check(drawing.PoseTransition is null && drawing.BedScene is null && !drawing.BedApproaching && window.Width == window.Height, name + " cancels entry cleanly");
                }
                finally { if (window is not null) { closeField.SetValue(window, true); window.Close(); } if (Directory.Exists(temp)) Directory.Delete(temp, true); }
            }
            return 0;
        }
        catch (Exception e) { log.Add("FAIL " + e); return 1; }
        finally { File.WriteAllLines(Path.Combine(output, "results.txt"), log); }
    }
}
