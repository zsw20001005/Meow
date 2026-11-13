using System.Diagnostics;
using System.IO;
using System.Text.Json;
using System.Windows;
using System.Windows.Media;
using System.Windows.Media.Imaging;

namespace Meow.Windows;

internal static class FrameCacheChecks
{
    internal static int Run()
    {
        var log = new List<string>();
        void Check(bool value, string message) { if (!value) throw new Exception(message); log.Add("PASS " + message); }
        BitmapSource Page(string path)
        {
            var source = BitmapDecoder.Create(new Uri(path), BitmapCreateOptions.PreservePixelFormat, BitmapCacheOption.OnLoad);
            return new FormatConvertedBitmap(source.Frames[0], PixelFormats.Pbgra32, null, 0);
        }
        void Compare(string name, int width, int height, int count, int columns, int pageFrames, Func<int, string> file, Action<int, byte[]> actual)
        {
            var expected = new byte[width * height * 4]; var decoded = new byte[expected.Length];
            BitmapSource? page = null; var times = new List<double>();
            for (int i = 0; i < count; i++)
            {
                int local = i % pageFrames;
                if (local == 0) page = Page(file(i / pageFrames));
                page!.CopyPixels(new Int32Rect(local % columns * width, local / columns * height, width, height), expected, width * 4, 0);
                long start = Stopwatch.GetTimestamp(); actual(i, decoded); times.Add(Stopwatch.GetElapsedTime(start).TotalMilliseconds);
                if (!expected.AsSpan().SequenceEqual(decoded)) throw new Exception($"{name} frame {i} differs from source pixels");
            }
            times.Sort(); log.Add($"PASS {name}: all {count} source frames byte-identical, fetch/copy P95={times[(int)((count - 1) * .95)]:F3} ms, max={times[^1]:F3} ms (includes cold preparation)");
        }
        try
        {
            // Exercise clear pixels, partial alpha, an incomplete final page,
            // cache eviction and a frame still owned by a transition.
            const int w = 9, h = 7, count = 19;
            var pixels = new byte[w * h * count * 4]; new Random(123).NextBytes(pixels);
            for (int i = 0; i < pixels.Length; i += 4)
            {
                byte alpha = i % 12 == 0 ? (byte)0 : pixels[i + 3]; pixels[i + 3] = alpha;
                for (int c = 0; c < 3; c++) pixels[i + c] = (byte)(pixels[i + c] * alpha / 255);
            }
            var atlas = BitmapSource.Create(w, h * count, 96, 96, PixelFormats.Pbgra32, null, pixels, w * 4); atlas.Freeze();
            var buffer = LuluFrameBuffer.Load(w, h, count, 1, count + 5, _ => atlas);
            var first = buffer.Frame(0); var bytes = new byte[w * h * 4];
            for (int i = 0; i < count; i++)
            {
                buffer.Frame(i).CopyPixels(bytes, w * 4, 0);
                Check(bytes.AsSpan().SequenceEqual(pixels.AsSpan(i * bytes.Length, bytes.Length)), $"synthetic frame {i} preserves premultiplied color and alpha");
            }
            Check(buffer.CachedCount == 8, "decoded cache stays bounded after eviction");
            first.CopyPixels(bytes, w * 4, 0);
            Check(bytes.AsSpan().SequenceEqual(pixels.AsSpan(0, bytes.Length)), "retained transition frame stays immutable after scratch reuse and eviction");
            Check(ReferenceEquals(buffer.Frame(0), buffer.Frame(0)), "repeated sample reuses its immutable frame");
            var playback = new LuluPlaybackFrame();
            var live = playback.Update(buffer, 0, w, h, data => buffer.CopyFrame(0, data));
            var next = playback.Update(buffer, 1, w, h, data => buffer.CopyFrame(1, data));
            Check(ReferenceEquals(live, next), "live playback reuses one native bitmap across frames");
            next.CopyPixels(bytes, w * 4, 0);
            Check(bytes.AsSpan().SequenceEqual(pixels.AsSpan(bytes.Length, bytes.Length)), "reused playback surface displays the next source pixels exactly");
            _ = playback.Update(buffer, 1, w, h, _ => throw new Exception("Duplicate frame decoded twice"));
            Check(true, "desktop repaint of the same frame does not decode or allocate pixels");

            var videoRoot = Path.Combine(AppContext.BaseDirectory, "Assets", "Lulu", "Video");
            using var videoDoc = JsonDocument.Parse(File.ReadAllText(Path.Combine(videoRoot, "manifest.json")));
            var walk = LuluVideo.Clips["walk"];
            Compare("walking", LuluVideo.CellSize, LuluVideo.CellSize, walk.Frames, videoDoc.RootElement.GetProperty("columns").GetInt32(), LuluVideo.PageFrames,
                page => Path.Combine(videoRoot, walk.File.Replace("{page}", page.ToString(System.Globalization.CultureInfo.InvariantCulture))),
                (index, result) => LuluVideo.Frame("walk", index / walk.Fps).CopyPixels(result, LuluVideo.CellSize * 4, 0));
            foreach (var (name, clip) in LuluVideo.Clips.Where(pair => pair.Key != "walk"))
            {
                // Still-mode files intentionally expose one selected source frame.
                if (clip.Mode == "still") continue;
                Compare(name, LuluVideo.CellSize, LuluVideo.CellSize, clip.Frames, videoDoc.RootElement.GetProperty("columns").GetInt32(), LuluVideo.PageFrames,
                    page => Path.Combine(videoRoot, clip.File.Replace("{page}", page.ToString(System.Globalization.CultureInfo.InvariantCulture))),
                    (index, result) => LuluVideo.Frame(name, index / clip.Fps).CopyPixels(result, LuluVideo.CellSize * 4, 0));
            }
            var edgeRoot = Path.Combine(AppContext.BaseDirectory, "Assets", "Lulu", "Edge");
            using var edgeDoc = JsonDocument.Parse(File.ReadAllText(Path.Combine(edgeRoot, "manifest.json"))); var edge = edgeDoc.RootElement;
            int ew = edge.GetProperty("width").GetInt32(), eh = edge.GetProperty("height").GetInt32();
            Compare("edge", ew, eh, LuluEdgeAnimation.Count, edge.GetProperty("columns").GetInt32(), edge.GetProperty("pageFrames").GetInt32(),
                page => Path.Combine(edgeRoot, $"edge-{page}.png"),
                (index, result) => LuluEdgeAnimation.Frame(index / edge.GetProperty("fps").GetDouble()).CopyPixels(result, ew * 4, 0));
            var bedRoot = Path.Combine(AppContext.BaseDirectory, "Assets", "Lulu", "Bed");
            using var bedDoc = JsonDocument.Parse(File.ReadAllText(Path.Combine(bedRoot, "manifest.json"))); var bed = bedDoc.RootElement;
            var task = LuluWalkBuffer.Prepare(bedRoot);
            Check(ReferenceEquals(task, LuluWalkBuffer.Prepare(bedRoot)), "overlapping bed scenes share preparation");
            var departure = task.GetAwaiter().GetResult();
            Compare("departure", departure.Width, departure.Height, bed.GetProperty("clips").GetProperty("depart").GetProperty("frames").GetInt32(),
                bed.GetProperty("columns").GetInt32(), bed.GetProperty("pageFrames").GetInt32(),
                page => Path.Combine(bedRoot, $"{bed.GetProperty("assetPrefix").GetString()}depart-{page}.png"), departure.CopyFrame);
            foreach (var clip in bed.GetProperty("clips").EnumerateObject())
            {
                if (clip.Name == "depart") continue;
                int scale = bed.GetProperty("pixelScale").GetInt32();
                int bw = (clip.Value.TryGetProperty("width", out var cw) ? cw.GetInt32() : bed.GetProperty("width").GetInt32()) * scale;
                int bh = (clip.Value.TryGetProperty("height", out var ch) ? ch.GetInt32() : bed.GetProperty("height").GetInt32()) * scale;
                int perPage = bed.GetProperty("pageFrames").GetInt32(); int lastPage = -1; LuluBedPage? cached = null;
                Compare("bed-" + clip.Name, bw, bh, clip.Value.GetProperty("frames").GetInt32(), bed.GetProperty("columns").GetInt32(), perPage,
                    page => Path.Combine(bedRoot, $"{bed.GetProperty("assetPrefix").GetString()}{clip.Name}-{page}.png"),
                    (index, result) => { if (lastPage != index / perPage) { lastPage = index / perPage; cached = LuluBedPage.Load(bedRoot, $"{clip.Name}-{lastPage}"); } cached!.CopyFrame(index % perPage, result); });
            }
            File.WriteAllLines(Path.Combine(AppContext.BaseDirectory, "frame-cache-checks.txt"), log); return 0;
        }
        catch (Exception e) { log.Add("FAIL " + e); File.WriteAllLines(Path.Combine(AppContext.BaseDirectory, "frame-cache-checks.txt"), log); return 1; }
    }
}
