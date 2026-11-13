using System.Diagnostics;
using System.IO;
using System.Runtime.CompilerServices;
using System.Text.Json;
using System.Windows;
using System.Windows.Media;
using System.Windows.Media.Imaging;

namespace Meow.Windows;

// Isolated animation workload: no Store, API keys, mailbox or local model.
internal static class MemoryChecks
{
    [MethodImpl(MethodImplOptions.NoInlining)]
    private static (WeakReference Scene, WeakReference Buffer) CheckDeparture(Action sample)
    {
        var bed = new LuluBedScene(); var visual = new DrawingVisual();
        using (var dc = visual.RenderOpen()) bed.DrawVideo(dc, "depart", 0);
        var buffer = LuluWalkBuffer.Prepare(Path.Combine(AppContext.BaseDirectory, "Assets", "Lulu", "Bed")).GetAwaiter().GetResult();
        sample();
        GC.KeepAlive(bed);
        return (new(bed), new(buffer));
    }

    [MethodImpl(MethodImplOptions.NoInlining)]
    private static (PetDrawing Drawing, WeakReference Buffer) CheckRoomWalkRelease()
    {
        var drawing = new PetDrawing { BedApproaching = true };
        _ = drawing.PrepareRoomWalk();
        var buffer = LuluWalkBuffer.Prepare(Path.Combine(AppContext.BaseDirectory, "Assets", "Lulu", "Bed")).GetAwaiter().GetResult();
        drawing.BedApproaching = false;
        return (drawing, new(buffer));
    }

    internal static int Run()
    {
        var rows = new List<object>();
        void Sample(string name, double p95 = 0, double maximum = 0)
        {
            GC.Collect(); GC.WaitForPendingFinalizers(); GC.Collect();
            using var process = Process.GetCurrentProcess(); process.Refresh();
            rows.Add(new { name, privateMiB = process.PrivateMemorySize64 / 1048576d,
                workingMiB = process.WorkingSet64 / 1048576d, managedMiB = GC.GetTotalMemory(false) / 1048576d,
                p95FrameMs = p95, maximumFrameMs = maximum });
        }
        void Play(string name, int count, Func<int, BitmapSource> frame)
        {
            var times = new List<double>(); var target = new RenderTargetBitmap(200, 200, 96, 96, PixelFormats.Pbgra32);
            var visual = new DrawingVisual();
            for (int i = 0; i < count; i++)
            {
                long start = Stopwatch.GetTimestamp();
                using (var dc = visual.RenderOpen()) dc.DrawImage(frame(i), new Rect(0, 0, 200, 200));
                target.Clear(); target.Render(visual); times.Add(Stopwatch.GetElapsedTime(start).TotalMilliseconds);
            }
            times.Sort(); Sample(name, times[(int)((times.Count - 1) * .95)], times[^1]);
        }
        try
        {
            Sample("cold"); PetWindow.WarmAnimations();
            _ = LuluVideo.Frame("idle", 0); Thread.Sleep(15000); Sample("startup");
            Play("walking", LuluVideo.Clips["walk"].Frames * 3, i => LuluVideo.Frame("walk", i / 60d));
            Play("edge", LuluEdgeAnimation.Count * 2, i => LuluEdgeAnimation.Frame(i / 24d));
            Play("idle-after-actions", 150, i => LuluVideo.Frame("idle", i / 24d));
            var released = CheckDeparture(() => Sample("bed-departure"));
            Sample("bed-released");
            if (released.Scene.IsAlive || released.Buffer.IsAlive) throw new Exception("Bed scene or departure buffer retained after use.");
            var room = CheckRoomWalkRelease();
            Sample("room-walk-released");
            if (room.Buffer.IsAlive) throw new Exception("Cancelled room walk retains departure buffer.");
            GC.KeepAlive(room.Drawing);
            Play("walking-long-loop", LuluVideo.Clips["walk"].Frames * 40, i => LuluVideo.Frame("walk", i / 60d));
            Play("edge-long-loop", LuluEdgeAnimation.Count * 8, i => LuluEdgeAnimation.Frame(i / 24d));
            File.WriteAllText(Path.Combine(AppContext.BaseDirectory, "memory-check.json"), JsonSerializer.Serialize(rows, new JsonSerializerOptions { WriteIndented = true }));
            return 0;
        }
        catch (Exception error) { File.WriteAllText(Path.Combine(AppContext.BaseDirectory, "memory-check-error.txt"), error.ToString()); return 1; }
    }
}
