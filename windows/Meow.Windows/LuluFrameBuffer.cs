using System.IO;
using System.IO.Compression;
using System.Windows;
using System.Windows.Media;
using System.Windows.Media.Imaging;

namespace Meow.Windows;

// Lossless frames: long clips stream indexed disk packets; short pages retain
// compressed pixels. Immutable snapshots are bounded and separate from playback.
internal sealed class LuluFrameBuffer
{
    private const int CacheLimit = 8;
    private readonly byte[][]? frames;
    private readonly LuluDiskFrames? disk;
    private readonly Dictionary<int, BitmapSource> cache = new();
    private readonly LinkedList<int> recent = new();
    private readonly byte[] scratch;
    internal int Width { get; }
    internal int Height { get; }
    internal long CompressedBytes => disk?.Bytes ?? frames!.Sum(f => (long)f.Length);
    internal int CachedCount { get { lock (cache) return cache.Count; } }

    private LuluFrameBuffer(byte[][] frames, int width, int height)
    {
        this.frames = frames; Width = width; Height = height;
        scratch = new byte[width * height * 4];
    }
    private LuluFrameBuffer(LuluDiskFrames disk)
    { this.disk = disk; Width = disk.Width; Height = disk.Height; scratch = new byte[Width * Height * 4]; }

    internal static LuluFrameBuffer Load(int width, int height, int count, int columns, int pageFrames, Func<int, BitmapSource> loadPage, string[]? sourceFiles = null)
    {
        IEnumerable<byte[]> Encode()
        {
            var pixels = new byte[width * height * 4]; BitmapSource? page = null;
            for (int i = 0; i < count; i++)
            {
                int local = i % pageFrames;
                if (local == 0) page = loadPage(i / pageFrames);
                page!.CopyPixels(new Int32Rect(local % columns * width, local / columns * height, width, height), pixels, width * 4, 0);
                using var output = new MemoryStream();
                using (var compressor = new DeflateStream(output, CompressionLevel.Fastest, leaveOpen: true)) compressor.Write(pixels);
                yield return output.ToArray();
            }
        }
        if (sourceFiles is not null)
        {
            try { return new(LuluDiskFrames.OpenOrBuild(sourceFiles, width, height, count, Encode)); }
            catch (Exception error) when (error is IOException or UnauthorizedAccessException) { /* Read-only/full disk: retain the in-memory fallback. */ }
        }
        return new(Encode().ToArray(), width, height);
    }

    internal void CopyFrame(int index, byte[] destination)
    {
        if (destination.Length != Width * Height * 4) throw new ArgumentException("Unexpected frame buffer size.", nameof(destination));
        using var input = new MemoryStream(disk?.Get(index) ?? frames![index], writable: false);
        using var decoder = new DeflateStream(input, CompressionMode.Decompress);
        decoder.ReadExactly(destination);
    }

    internal BitmapSource Frame(int index)
    {
        lock (cache)
        {
            if (!cache.TryGetValue(index, out var frame))
            {
                CopyFrame(index, scratch);
                frame = BitmapSource.Create(Width, Height, 96, 96, PixelFormats.Pbgra32, null, scratch, Width * 4);
                frame.Freeze(); cache.Add(index, frame);
            }
            recent.Remove(index); recent.AddLast(index);
            while (recent.Count > CacheLimit) { cache.Remove(recent.First!.Value); recent.RemoveFirst(); }
            return frame;
        }
    }
}
