using System.IO;
using System.Text.Json;
using System.Windows;
using System.Windows.Media;
using System.Windows.Media.Imaging;

namespace Meow.Windows;

// Offline video frames. Pages are compressed; live playback reuses one surface.
internal sealed class LuluVideo
{
    internal sealed record Clip(string File, int Frames, double Fps, string Mode, int StillFrame);
    private static readonly string Root = Path.Combine(AppContext.BaseDirectory, "Assets", "Lulu", "Video");
    internal static int CellSize { get; private set; } = 256;
    private static int Columns = 8;
    internal static int PageFrames { get; private set; } = int.MaxValue;
    internal static readonly HashSet<string> MissingClips = new();
    internal static readonly Dictionary<string, Clip> Clips = LoadManifest();
    internal static bool Available => Clips.ContainsKey("idle");
    private static readonly Dictionary<string, LuluFrameBuffer> Atlases = new();
    private static readonly Dictionary<string, Task<LuluFrameBuffer>> Pending = new();
    private static readonly LinkedList<string> Recent = new();
    private static readonly Dictionary<(string Key, int Index), BitmapSource> Snapshots = new();
    private static readonly LinkedList<(string Key, int Index)> SnapshotRecent = new();
    private static readonly Lazy<byte[][]> IdlePoses = new(() => Enumerable.Range(0, (Clips["idle"].Frames + 1) / 2)
        .Select(i => PosePixels(Frame("idle", i * 2 / Clips["idle"].Fps))).ToArray());
    private readonly LuluPlaybackFrame playback = new();
    private static readonly Lazy<Task<LuluFrameBuffer>> WalkingFrames = new(() => Task.Run(() =>
    {
        var clip = Clips["walk"];
        return LuluFrameBuffer.Load(CellSize, CellSize, clip.Frames, Columns, PageFrames, page => LoadPage(clip, page * PageFrames),
            Enumerable.Range(0, (clip.Frames + PageFrames - 1) / PageFrames).Select(page => Path.Combine(Root, PageFile(clip, page * PageFrames))).ToArray());
    }));
    internal static void WarmUp()
    {
        if (Clips.ContainsKey("walk")) _ = WalkingFrames.Value;
        if (Clips.TryGetValue("idle", out var idle)) Prefetch(idle, 0);
    }
    private string current = "";
    private double began;
    private double entryOffset;
    private int revision = -1;
    private BitmapSource? lastFrame;

    // Bed exit is authored against idle frame zero, not the stale pre-sleep pose.
    internal void ResumeAfterBed(double time)
    {
        current = "idle"; began = time; entryOffset = 0; revision = -1; lastFrame = null;
    }

    private static Dictionary<string, Clip> LoadManifest()
    {
        var path = Path.Combine(Root, "manifest.json");
        if (!File.Exists(path)) return new();
        using var document = JsonDocument.Parse(File.ReadAllText(path));
        var root = document.RootElement;
        CellSize = root.GetProperty("cellSize").GetInt32(); Columns = root.GetProperty("columns").GetInt32();
        PageFrames = root.TryGetProperty("pageFrames", out var pages) ? pages.GetInt32() : int.MaxValue;
        var clips = new Dictionary<string, Clip>();
        foreach (var item in document.RootElement.GetProperty("clips").EnumerateObject())
        {
            var c = item.Value;
            var clip = new Clip(c.GetProperty("file").GetString()!, c.GetProperty("frames").GetInt32(), c.GetProperty("fps").GetDouble(), c.GetProperty("mode").GetString()!, c.TryGetProperty("stillFrame", out var still) ? still.GetInt32() : 0);
            int pageCount = (int)Math.Ceiling((double)clip.Frames / PageFrames);
            if (Enumerable.Range(0, pageCount).All(page => File.Exists(Path.Combine(Root, PageFile(clip, page * PageFrames))))) clips[item.Name] = clip;
            else MissingClips.Add(item.Name);
        }
        return clips;
    }

    internal static double? Duration(string action) => Clips.TryGetValue(action, out var clip) ? clip.Frames / clip.Fps : null;
    internal static int FrameIndex(Clip clip, double seconds)
    {
        if (clip.Mode == "still") return Math.Clamp(clip.StillFrame, 0, clip.Frames - 1);
        int frame = (int)(Math.Max(0, seconds) * clip.Fps + 1e-7);
        return clip.Mode == "loop" ? frame % clip.Frames : Math.Min(frame, clip.Frames - 1);
    }

    internal static BitmapSource Frame(string key, double seconds)
    {
        var clip = Clips[key];
        // Long clips use indexed frame packets; no PNG atlas I/O during loops.
        if (key == "walk") return WalkingFrames.Value.GetAwaiter().GetResult().Frame(FrameIndex(clip, seconds));
        int index = FrameIndex(clip, seconds);
        var id = (key, index);
        if (!Snapshots.TryGetValue(id, out var frame))
        {
            var pixels = new byte[CellSize * CellSize * 4]; CopyFrame(clip, index, pixels);
            frame = BitmapSource.Create(CellSize, CellSize, 96, 96, PixelFormats.Pbgra32, null, pixels, CellSize * 4);
            frame.Freeze(); Snapshots[id] = frame;
        }
        SnapshotRecent.Remove(id); SnapshotRecent.AddLast(id);
        while (SnapshotRecent.Count > 6) { Snapshots.Remove(SnapshotRecent.First!.Value); SnapshotRecent.RemoveFirst(); }
        return frame;
    }

    private static void CopyFrame(Clip clip, int index, byte[] pixels)
    {
        int local = index % PageFrames;
        string file = PageFile(clip, index);
        if (!Atlases.TryGetValue(file, out var atlas))
        {
            atlas = Pending.Remove(file, out var pending) ? pending.GetAwaiter().GetResult() : LoadFrames(clip, index); Atlases[file] = atlas;
        }
        Recent.Remove(file); Recent.AddLast(file);
        while (Recent.Count > 3) { var oldest = Recent.First!.Value; Recent.RemoveFirst(); Atlases.Remove(oldest); }
        int next = index - local + Math.Min(PageFrames, clip.Frames);
        string? nextFile = next < clip.Frames ? PageFile(clip, next) : clip.Mode == "loop" ? PageFile(clip, 0) : null;
        foreach (string stale in Pending.Keys.Where(k => k != nextFile).ToArray()) Pending.Remove(stale);
        if (nextFile is not null) Prefetch(clip, next < clip.Frames ? next : 0);
        atlas.CopyFrame(local, pixels);
    }

    private static string PageFile(Clip clip, int index) => clip.File.Replace("{page}", (index / PageFrames).ToString(System.Globalization.CultureInfo.InvariantCulture));
    private static void Prefetch(Clip clip, int index)
    {
        string file = PageFile(clip, index);
        if (!Atlases.ContainsKey(file) && !Pending.ContainsKey(file)) Pending[file] = Task.Run(() => LoadFrames(clip, index));
    }
    private static LuluFrameBuffer LoadFrames(Clip clip, int index)
        => LuluFrameBuffer.Load(CellSize, CellSize, Math.Min(PageFrames, clip.Frames - index / PageFrames * PageFrames),
            Columns, PageFrames, _ => LoadPage(clip, index),
            index < PageFrames || clip == Clips["idle"] || clip.Mode == "still" ? [Path.Combine(Root, PageFile(clip, index))] : null);
    private static BitmapSource LoadPage(Clip clip, int index)
    {
        var bitmap = new BitmapImage(); bitmap.BeginInit(); bitmap.CacheOption = BitmapCacheOption.OnLoad;
        bitmap.UriSource = new Uri(Path.Combine(Root, PageFile(clip, index))); bitmap.EndInit(); bitmap.Freeze();
        int count = Math.Min(PageFrames, clip.Frames - index / PageFrames * PageFrames);
        if (bitmap.PixelWidth != Columns * CellSize || bitmap.PixelHeight < ((count + Columns - 1) / Columns) * CellSize)
            throw new InvalidDataException("Incomplete animation atlas: " + PageFile(clip, index));
        // The worker immediately packs individual frames. Never create a second
        // native full-atlas bitmap just to copy it into compressed frame storage.
        return new FormatConvertedBitmap(bitmap, PixelFormats.Pbgra32, null, 0);
    }

    private static byte[] PosePixels(BitmapSource frame)
    {
        var small = new TransformedBitmap(frame, new ScaleTransform(32d / frame.PixelWidth, 32d / frame.PixelHeight));
        var pixels = new byte[32 * 32 * 4];
        new FormatConvertedBitmap(small, PixelFormats.Pbgra32, null, 0).CopyPixels(pixels, 32 * 4, 0);
        return pixels;
    }

    // Pick an existing idle pose, never synthesize or blend two silhouettes.
    // Action entrances always start at frame zero so food/ball entrances are not skipped.
    internal static double ClosestIdleStart(BitmapSource previous)
    {
        var target = PosePixels(previous);
        var idle = Clips["idle"];
        long bestError = long.MaxValue; int bestFrame = 0;
        for (int index = 0; index < idle.Frames; index += 2)
        {
            var candidate = IdlePoses.Value[index / 2];
            long error = 0;
            for (int p = 0; p < target.Length; p++) error += Math.Abs(target[p] - candidate[p]);
            if (error < bestError) { bestError = error; bestFrame = index; }
        }
        return bestFrame / idle.Fps;
    }

    internal const double SleepCycleSeconds = 4.8;
    internal const double SleepLoopEntry = 2.625;
    // Original closed-eye frames only. Ease both turns instead of cutting back to the first frame.
    internal static double SleepBreath(double elapsed) => (1 - Math.Cos(2 * Math.PI * Math.Max(0, elapsed - SleepLoopEntry) / SleepCycleSeconds)) / 2;
    internal static double StatePoseTime(string key, double elapsed)
    {
        if (key == "sleep") return elapsed <= SleepLoopEntry ? elapsed : SleepLoopEntry - .875 * SleepBreath(elapsed);
        return Math.Min(elapsed, key switch
        {
        "happy" => 1.88, "love" => 1.88, "shy" => 1.50, "curious" => 1.83,
        "surprised" => 1.12, "angry" => 2.58, "sad" => 1.42, "sleepy" => 1.12,
            "hungry" => .88, "dizzy" => 1.38, "think" => 1.42, _ => double.PositiveInfinity
        });
    }

    internal bool Draw(DrawingContext context, string action, string emotion, double talk, double time, double? pose, int replay, bool facingRight, bool keepStatePose = false)
    {
        if (!Available) return false;
        string key = action;
        if (action == "idle") key = emotion is not ("neutral" or "") ? (emotion == "sulking" ? "sad" : emotion) : talk > .02 ? "talk" : "idle";
        if (!Clips.ContainsKey(key)) key = "idle";
        if (key != current || replay != revision)
        {
            entryOffset = key == "idle" && current != key && lastFrame is not null && !pose.HasValue ? ClosestIdleStart(lastFrame) : 0;
            began = current.Length == 0 ? 0 : time; current = key; revision = replay;
        }
        double elapsed = pose ?? (Math.Max(0, time - began) + entryOffset);
        bool breathing = keepStatePose && !pose.HasValue && key == "sleep";
        double breath = breathing ? SleepBreath(elapsed) : 0;
        if (keepStatePose && !pose.HasValue) elapsed = StatePoseTime(key, elapsed);
        var clip = Clips[key]; int index = FrameIndex(clip, elapsed);
        var frame = playback.Update(clip, index, CellSize, CellSize, pixels =>
        {
            if (key == "walk") WalkingFrames.Value.GetAwaiter().GetResult().CopyFrame(index, pixels);
            else CopyFrame(clip, index, pixels);
        });
        // Only locomotion follows horizontal facing. Food and ball always face the viewer.
        bool mirror = action == "walk" && !facingRight;
        if (mirror) { context.PushTransform(new ScaleTransform(-1, 1, 100, 100)); }
        // Exhale in the same direction as the original head settling. The old expansion
        // cancelled that motion and was nearly invisible at the desktop's 80% scale.
        if (breathing) context.PushTransform(new ScaleTransform(1 - .008 * breath, 1 - .035 * breath, 100, 170));
        context.DrawImage(frame, new Rect(0, 0, 200, 200));
        if (breathing) context.Pop();
        if (mirror) context.Pop();
        lastFrame = frame;
        return true;
    }
}
