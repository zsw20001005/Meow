using System.IO;
using System.Text.Json;
using System.Windows;
using System.Windows.Media;
using System.Windows.Media.Imaging;

namespace Meow.Windows;

// A stationary world-space bed viewed by a camera following Lulu's walking root.
internal sealed class LuluBedScene
{
    private static readonly string AssetRoot = Path.Combine(AppContext.BaseDirectory, "Assets", "Lulu", "Bed");
    internal static bool Available => File.Exists(Path.Combine(AssetRoot, "manifest.json"));
    private static readonly Lazy<Task<BitmapSource>> InitialCharacter = new(() => Task.Run(() => Decode("approach-0")));
    private static readonly Lazy<Task<BitmapSource>> InitialBed = new(() => Task.Run(() => Decode("arrive-bed")));
    private static readonly Lazy<Task<LuluWalkBuffer>> PreparedDeparture = new(() => Task.Run(() => LuluWalkBuffer.Load(AssetRoot)));
    private static readonly Lazy<Task<BitmapSource>> InitialJoin = new(() => Task.Run(() => Decode("join-start-0")));
    internal static void WarmUp() { if (!Available) return; _ = InitialCharacter.Value; _ = InitialBed.Value; _ = PreparedDeparture.Value; if (File.Exists(AssetPath("join-start-0"))) _ = InitialJoin.Value; }
    private LuluWalkBuffer? departure;
    private WriteableBitmap? departureImage;
    private byte[]? departurePixels;
    private WriteableBitmap? mirroredApproach;
    private byte[]? mirroredPixels;
    private (string Clip, int Index) mirroredFrameId;
    private readonly Dictionary<string, int> frames = new();
    private readonly Dictionary<string, double> rates = new();
    private readonly Dictionary<string, BitmapSource> cache = new();
    private readonly LinkedList<string> recent = new();
    private readonly Dictionary<string, Task<BitmapSource>> pending = new();
    private readonly Dictionary<string, (int Width, int Height)> sizes = new();
    private BitmapSource? lastFrame;
    private (string Clip, int Index) lastFrameId;
    private readonly int width, height, columns, pageFrames, split;
    private readonly double scale, x, y, fps;
    private readonly Dictionary<string, double[]> roots = new();
    private readonly Dictionary<(int Width, int Height), (WriteableBitmap Image, byte[] Pixels)> frameBuffers = new();
    internal bool UseJoins { get; set; } = true;
    private readonly Dictionary<string, double> rootStarts = new();
    internal string Phase { get; private set; } = "arrive";
    internal double Elapsed { get; private set; }
    internal bool WakeRequested { get; private set; }
    internal bool Complete => Phase == "done";
    internal Action<string, double, bool>? AssetLoadProbe { get; set; }
    internal (string Clip, int Index) DisplayedFrame => lastFrameId;
    internal double LastDrawMilliseconds { get; private set; }
    internal double LoopDuration => frames["loop"] / fps;
    // Full uninterrupted takes at original speed. No short-stride modulo/reset.
    internal const double ApproachLead = 34d / 24;
    // End on the matching planted-foot phase, then use the accepted S14 take.
    internal const double DepartureStart = 281d / 60; // last rendered wake pose is original frame 112
    internal const double SettleDuration = 190d / 24 - 3.5; // bed clears before S14 starts turning
    internal double ArrivalDuration => frames["approach"] / rates["approach"];
    internal double DepartureDuration => frames["depart"] / rates["depart"] - SettleDuration;
    internal double SleepStarts => ArrivalDuration + frames["entry"] / fps - ApproachLead;
    internal double BedWorldX => x + split * scale;
    internal double BedScreenX => BedWorldX - CameraX;
    internal double CameraX
    {
        get
        {
            if (Phase == "arrive")
            {
                double start = BedWorldX - 402, end = Root("entry", ApproachLead) - 100;
                double t = Math.Clamp((Elapsed - .6) / (ArrivalDuration - .6), 0, 1);
                return Hermite(start, end, 0, RootVelocity("entry", ApproachLead), t, ArrivalDuration - .6);
            }
            if (Phase == "entry") return Root("entry", Math.Min(Elapsed, 3)) - 100;
            double sleepCamera = Root("entry", 3) - 100;
            if (Phase == "loop") return sleepCamera;
            if (Phase == "wake")
            {
                double t = Math.Clamp((Elapsed - 2.5) / 1, 0, 1);
                return sleepCamera + (Root("wake", Elapsed) - 100 - sleepCamera) * t * t * (3 - 2 * t);
            }
            if (Phase == "leave")
            {
                double start = Root("wake", DepartureStart) - 100, end = BedWorldX - 414;
                double t = Math.Clamp(Elapsed / DepartureDuration, 0, 1);
                return Hermite(start, end, RootVelocity("wake", DepartureStart), 0, t, DepartureDuration);
            }
            return BedWorldX - 414;
        }
    }

    internal LuluBedScene()
    {
        using var doc = JsonDocument.Parse(File.ReadAllText(Path.Combine(AssetRoot, "manifest.json")));
        var root = doc.RootElement;
        width = root.GetProperty("width").GetInt32(); height = root.GetProperty("height").GetInt32();
        columns = root.GetProperty("columns").GetInt32(); pageFrames = root.GetProperty("pageFrames").GetInt32(); fps = root.GetProperty("fps").GetDouble();
        foreach (var clip in root.GetProperty("clips").EnumerateObject())
        {
            frames[clip.Name] = clip.Value.GetProperty("frames").GetInt32();
            rates[clip.Name] = clip.Value.TryGetProperty("fps", out var rate) ? rate.GetDouble() : fps;
            int pixelScale = root.TryGetProperty("pixelScale", out var ps) ? ps.GetInt32() : 1;
            var logicalSize = clip.Value.TryGetProperty("width", out var cw) ? (cw.GetInt32(), clip.Value.GetProperty("height").GetInt32()) : (width, height);
            sizes[clip.Name] = (logicalSize.Item1 * pixelScale, logicalSize.Item2 * pixelScale);
            if (clip.Value.TryGetProperty("rootX", out var track))
            {
                roots[clip.Name] = track.EnumerateArray().Select(v => v.GetDouble()).ToArray();
                rootStarts[clip.Name] = clip.Value.GetProperty("rootStart").GetDouble();
            }
        }
        var render = root.GetProperty("render"); scale = render.GetProperty("scale").GetDouble(); x = render.GetProperty("x").GetDouble(); y = render.GetProperty("y").GetDouble(); split = render.GetProperty("splitX").GetInt32();
        pending["arrive-bed"] = InitialBed.Value; pending["approach-0"] = InitialCharacter.Value;
        if (frames.ContainsKey("join-start")) pending["join-start-0"] = InitialJoin.Value;
        Prefetch($"entry-{(int)(ApproachLead * rates["entry"]) / pageFrames}");
    }

    // Match position and velocity when the tracking camera changes source clips.
    private static double Hermite(double a, double b, double va, double vb, double t, double duration)
        => (2*t*t*t-3*t*t+1)*a + (t*t*t-2*t*t+t)*duration*va + (-2*t*t*t+3*t*t)*b + (t*t*t-t*t)*duration*vb;
    private double RootVelocity(string clip, double time) => (Root(clip, time + 1d/24) - Root(clip, time - 1d/24)) * 12;

    private double Root(string clip, double time)
    {
        var track = roots[clip]; double index = Math.Clamp((time - rootStarts[clip]) * fps, 0, track.Length - 1);
        int low = (int)index, high = Math.Min(low + 1, track.Length - 1);
        return x + (track[low] + (track[high] - track[low]) * (index - low)) * scale;
    }
    internal void RequestWake()
    {
        if (WakeRequested) return;
        WakeRequested = true; Prefetch("wake-0");
        if (frames.ContainsKey("join-wake")) Prefetch("join-wake-0");
        _ = PreparedDeparture.Value;
    }
    internal void KeepSleeping() { if (Phase is "arrive" or "entry" or "loop") WakeRequested = false; }
    internal void Advance(double seconds)
    {
        if (Complete) return;
        Elapsed += Math.Max(0, seconds);
        while (!Complete)
        {
            double duration = Phase switch { "arrive" => ArrivalDuration, "leave" => DepartureDuration, "wake" => DepartureStart, "settle" => SettleDuration, _ => frames[Phase] / fps };
            if (Elapsed + 1e-9 < duration) break;
            Elapsed = Math.Max(0, Elapsed - duration);
            string previous = Phase;
            Phase = Phase switch { "arrive" => "entry", "entry" => WakeRequested ? "wake" : "loop", "loop" => WakeRequested ? "wake" : "loop", "wake" => "leave", "leave" => "settle", _ => "done" };
            if (previous == "arrive") Elapsed += ApproachLead;
            if (Phase == "loop" && !WakeRequested) { Elapsed %= LoopDuration; break; }
        }
    }

    private BitmapSource Load(string name)
    {
        if (cache.TryGetValue(name, out var known)) { recent.Remove(name); recent.AddLast(name); return known; }
        long loadStart = System.Diagnostics.Stopwatch.GetTimestamp();
        bool hadReadyTask = pending.TryGetValue(name, out var existing) && existing.IsCompletedSuccessfully;
        var image = pending.Remove(name, out var task) ? task.GetAwaiter().GetResult() : Decode(name);
        AssetLoadProbe?.Invoke(name, System.Diagnostics.Stopwatch.GetElapsedTime(loadStart).TotalMilliseconds, hadReadyTask);
        cache[name] = image; recent.AddLast(name);
        while (recent.Count > 3) { cache.Remove(recent.First!.Value); recent.RemoveFirst(); }
        return image;
    }
    private static string AssetPath(string name)
    {
        using var manifest = JsonDocument.Parse(File.ReadAllText(Path.Combine(AssetRoot, "manifest.json")));
        string prefix = manifest.RootElement.TryGetProperty("assetPrefix", out var value) ? value.GetString()! : "";
        return Path.Combine(AssetRoot, prefix + name + ".png");
    }
    private static BitmapSource Decode(string name)
    {
        var image = new BitmapImage(); image.BeginInit(); image.CacheOption = BitmapCacheOption.OnLoad; image.UriSource = new Uri(AssetPath(name)); image.EndInit(); image.Freeze();
        // Materialize pixels on this worker: OnLoad alone can leave WIC decoding
        // deferred until the first UI render of a new atlas page.
        var converted = new FormatConvertedBitmap(image, PixelFormats.Pbgra32, null, 0);
        int stride = image.PixelWidth * 4; var pixels = new byte[stride * image.PixelHeight];
        converted.CopyPixels(pixels, stride, 0);
        var decoded = BitmapSource.Create(image.PixelWidth, image.PixelHeight, 96, 96, PixelFormats.Pbgra32, null, pixels, stride);
        decoded.Freeze(); return decoded;
    }
    private void Prefetch(string name)
    {
        if (!cache.ContainsKey(name) && !pending.ContainsKey(name)) pending[name] = Task.Run(() => Decode(name));
    }
    private BitmapSource VideoFrame(string clip, double time)
    {
        int frame = Math.Clamp((int)(time * rates[clip] + 1e-7), 0, frames[clip] - 1), local = frame % pageFrames;
        if (lastFrame is not null && lastFrameId == (clip, frame)) return lastFrame;
        if (clip == "depart")
        {
            if (departure is null)
            {
                var start = System.Diagnostics.Stopwatch.GetTimestamp(); bool ready = PreparedDeparture.Value.IsCompletedSuccessfully;
                departure = PreparedDeparture.Value.GetAwaiter().GetResult();
                AssetLoadProbe?.Invoke("depart-buffer", System.Diagnostics.Stopwatch.GetElapsedTime(start).TotalMilliseconds, ready);
                departurePixels = new byte[departure.Width * departure.Height * 4];
                departureImage = new WriteableBitmap(departure.Width, departure.Height, 96, 96, PixelFormats.Pbgra32, null);
            }
            departure.CopyFrame(frame, departurePixels!);
            departureImage!.WritePixels(new Int32Rect(0, 0, departure.Width, departure.Height), departurePixels!, departure.Width * 4, 0);
            lastFrameId = (clip, frame); return lastFrame = departureImage;
        }
        int page = frame / pageFrames;
        if ((page + 1) * pageFrames < frames[clip]) Prefetch($"{clip}-{page + 1}");
        if (clip == "entry" && time > 8) Prefetch("loop-0");
        if (clip == "loop" && !WakeRequested) Prefetch("loop-0");
        if (clip == "wake" && time > 2) Prefetch("leave-bed");
        var size = sizes[clip];
        if (!frameBuffers.TryGetValue(size, out var buffer))
        {
            buffer = (new WriteableBitmap(size.Width, size.Height, 96, 96, PixelFormats.Pbgra32, null), new byte[size.Width * size.Height * 4]); frameBuffers[size] = buffer;
        }
        Load($"{clip}-{page}").CopyPixels(new Int32Rect(local % columns * size.Width, local / columns * size.Height, size.Width, size.Height), buffer.Pixels, size.Width * 4, 0);
        buffer.Image.WritePixels(new Int32Rect(0, 0, size.Width, size.Height), buffer.Pixels, size.Width * 4, 0);
        var result = buffer.Image;
        lastFrameId = (clip, frame); return lastFrame = result;
    }
    internal void DrawVideo(DrawingContext context, string clip, double time) => context.DrawImage(VideoFrame(clip, time), new Rect(x, y, width * scale, height * scale));
    internal void DrawApproachPose(DrawingContext context, double time, bool mirror)
    {
        var frame = VideoFrame("approach", time);
        if (mirror)
        {
            // Flip native pixels once per source frame. Mirroring during WPF
            // downsampling uses a different sample grid from the captured pose.
            int w = frame.PixelWidth, h = frame.PixelHeight;
            if (mirroredApproach is null)
            {
                mirroredApproach = new WriteableBitmap(w, h, 96, 96, PixelFormats.Pbgra32, null);
                mirroredPixels = new byte[w * h * 4];
            }
            if (mirroredFrameId != lastFrameId)
            {
                frame.CopyPixels(mirroredPixels!, w * 4, 0);
                for (int row = 0; row < h; row++) for (int col = 0; col < w / 2; col++)
                {
                    int left = (row * w + col) * 4, right = (row * w + w - col - 1) * 4;
                    for (int c = 0; c < 4; c++) (mirroredPixels![left + c], mirroredPixels[right + c]) = (mirroredPixels[right + c], mirroredPixels[left + c]);
                }
                mirroredApproach.WritePixels(new Int32Rect(0, 0, w, h), mirroredPixels!, w * 4, 0);
                mirroredFrameId = lastFrameId;
            }
            frame = mirroredApproach;
        }
        context.DrawImage(frame, new Rect(0, 0, 200, 200));
    }
    internal void Draw(DrawingContext context)
    {
        long drawStart = System.Diagnostics.Stopwatch.GetTimestamp();
        if (UseJoins && DrawJoin(context)) { LastDrawMilliseconds = System.Diagnostics.Stopwatch.GetElapsedTime(drawStart).TotalMilliseconds; return; }
        var rect = new Rect(x, y, width * scale, height * scale);
        context.PushClip(new RectangleGeometry(new Rect(0, -20, 400, 240)));
        if (Phase is "arrive" or "leave" or "settle" or "done")
        {
            bool approach = Phase == "arrive";
            string clip = approach ? "approach" : "depart";
            double sourceTime = Phase == "settle" ? DepartureDuration + Elapsed : Complete ? frames["depart"] / rates["depart"] : Elapsed;
            context.PushTransform(new TranslateTransform(-CameraX, 0));
            context.DrawImage(Load(approach ? "arrive-bed" : "leave-bed"), rect);
            context.Pop();
            context.DrawImage(VideoFrame(clip, sourceTime), new Rect(0, 0, 200, 200));
        }
        else
        {
            context.PushTransform(new TranslateTransform(-CameraX, 0));
            DrawVideo(context, Phase, Elapsed);
            context.Pop();
        }
        context.Pop();
        LastDrawMilliseconds = System.Diagnostics.Stopwatch.GetElapsedTime(drawStart).TotalMilliseconds;
    }

    private bool DrawJoin(DrawingContext context)
    {
        string name; double at, duration;
        if (Phase == "arrive" && Elapsed < .25) { name = "start"; at = Elapsed; duration = .25; }
        else if (Phase == "wake" && Elapsed < .2) { name = "wake"; at = Elapsed; duration = .2; }
        else if (Complete) { name = "idle"; at = duration = .25; }
        else
        {
            (name, double end, duration) = Phase switch
            {
                "arrive" => ("approach", ArrivalDuration, .2),
                "entry" => ("sleep", frames["entry"] / fps, .2),
                "loop" => ("breath", LoopDuration, .2),
                "wake" => ("return", DepartureStart, .2),
                "settle" => ("idle", SettleDuration, .25),
                _ => ("", 0d, 0d)
            };
            at = Elapsed - (end - duration);
        }
        string clip = "join-" + name;
        if (name.Length == 0 || !frames.ContainsKey(clip)) return false;
        if (at < 0) { if (at > -.75) Prefetch(clip + "-0"); return false; }
        context.DrawImage(VideoFrame(clip, Math.Min(at, duration)), new Rect(0, 0, 400, 200));
        return true;
    }
}
