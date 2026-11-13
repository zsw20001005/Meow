using System.Diagnostics;
using System.IO;
using System.Text.Json;
using System.Windows;
using System.Windows.Media;
using System.Windows.Threading;

namespace Meow.Windows;

// Full visible WPF window, normal timers and renderer. No forced collection,
// real profile, credentials, network traffic, local model or workspace changes.
internal static class RuntimeMemoryChecks
{
    internal static int Run(App app)
    {
        var store = VisualChecks.Sample();
        store.Data.Mail.Enabled = false; store.Data.Proactive = false; store.Data.NewsEnabled = false;
        store.Data.WindowJump = false; store.Data.Scale = .8;
        // Prevent the unconfigured-account dashboard and user clicks from
        // changing the scripted workload. This synthetic value is never used.
        store.Data.ProtectedKey = "offline-performance-test";
        var pet = new PetWindow(store) { IsHitTestVisible = false };
        var drawing = (PetDrawing)pet.Content;
        var samples = new List<object>(); var intervals = new List<double>();
        var clock = new Stopwatch(); var phase = "startup"; int step = 0;
        TimeSpan previousRender = TimeSpan.Zero;
        var actions = new (double At, string Name, Action Play)[]
        {
            (0, "idle", () => pet.Animate("idle")),
            (10, "wave", () => pet.Animate("wave")),
            (20, "play", () => pet.Animate("play")),
            (30, "walk", () => pet.Animate("walk")),
            (50, "idle-after-walk", () => pet.Animate("idle")),
            (60, "sleep", () => pet.Animate("sleep")),
            (85, "wake", () => pet.Animate("idle")),
            (105, "edge", () => store.Data.WallSide = "right"),
            (125, "idle-after-all", () => pet.Animate("idle"))
        };
        void Observe(object? sender, EventArgs e)
        {
            var at = ((RenderingEventArgs)e).RenderingTime;
            if (at == previousRender) return;
            if (previousRender != TimeSpan.Zero) intervals.Add((at - previousRender).TotalMilliseconds);
            previousRender = at;
        }
        var timer = new DispatcherTimer { Interval = TimeSpan.FromSeconds(2) };
        timer.Tick += (_, _) =>
        {
            double seconds = clock.Elapsed.TotalSeconds;
            while (step < actions.Length && seconds >= actions[step].At)
            {
                phase = actions[step].Name; actions[step++].Play();
            }
            using var process = Process.GetCurrentProcess(); process.Refresh();
            var sorted = intervals.Order().ToArray(); intervals.Clear();
            samples.Add(new { seconds, phase, action = drawing.Action, bed = drawing.BedScene?.Phase,
                privateMiB = process.PrivateMemorySize64 / 1048576d, workingMiB = process.WorkingSet64 / 1048576d,
                managedMiB = GC.GetTotalMemory(false) / 1048576d, gen2Collections = GC.CollectionCount(2),
                p95IntervalMs = sorted.Length == 0 ? 0 : sorted[(int)((sorted.Length - 1) * .95)],
                maxIntervalMs = sorted.Length == 0 ? 0 : sorted[^1] });
            File.WriteAllText(Path.Combine(AppContext.BaseDirectory, "runtime-memory-check.json"), JsonSerializer.Serialize(samples, new JsonSerializerOptions { WriteIndented = true }));
            if (seconds >= 145) { timer.Stop(); CompositionTarget.Rendering -= Observe; pet.ExitApp(); }
        };
        pet.Loaded += (_, _) => { clock.Start(); CompositionTarget.Rendering += Observe; timer.Start(); };
        app.Run(pet); return 0;
    }
}
