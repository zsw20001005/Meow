using System.Diagnostics;
using System.IO;
using System.Text.Json;
using System.Windows;
using System.Windows.Media;
using System.Windows.Media.Imaging;

namespace Meow.Windows;

// Real-time offscreen render trace, isolating WPF decoding/render work from
// unrelated user interaction and window minimization. Does not read user state.
internal static class BedRenderProfile
{
    internal static int Run()
    {
        var scene = new LuluBedScene();
        var rows = new List<object>(); var loads = new List<object>();
        scene.AssetLoadProbe = (name, ms, ready) => loads.Add(new { name, ms, ready, scene.Phase, scene.Elapsed });
        var clock = Stopwatch.StartNew(); double previous = 0;
        int lastGc = GC.CollectionCount(2);
        for (int i = 0; i < 2450; i++)
        {
            double now = clock.Elapsed.TotalSeconds, gap = now - previous; previous = now;
            scene.Advance(gap);
            if (now >= scene.SleepStarts + 2) scene.RequestWake();
            var drawStart = Stopwatch.GetTimestamp();
            var visual = new DrawingVisual();
            using (var dc = visual.RenderOpen()) { dc.PushTransform(new ScaleTransform(.92, .92)); scene.Draw(dc); dc.Pop(); }
            var target = new RenderTargetBitmap(368, 184, 96, 96, PixelFormats.Pbgra32); target.Render(visual);
            double drawMs = Stopwatch.GetElapsedTime(drawStart).TotalMilliseconds;
            int gc = GC.CollectionCount(2);
            rows.Add(new { now, gapMs = gap * 1000, drawMs, scene.Phase, scene.Elapsed, clip = scene.DisplayedFrame.Clip, frame = scene.DisplayedFrame.Index, fullGc = gc - lastGc });
            lastGc = gc;
            if (scene.Complete) break;
            int wait = (int)Math.Max(0, 1000d / 60 - Stopwatch.GetElapsedTime(drawStart).TotalMilliseconds);
            if (wait > 0) Thread.Sleep(wait);
        }
        File.WriteAllText(Path.Combine(AppContext.BaseDirectory, "bed-render-profile.json"), JsonSerializer.Serialize(new { rows, loads }, new JsonSerializerOptions { WriteIndented = true }));
        return scene.Complete ? 0 : 1;
    }
}
