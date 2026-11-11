using System.IO;
using System.Text.Json;
using System.Windows.Media;
using System.Windows.Media.Imaging;

namespace Meow.Windows;

// One prepared, immutable pixel buffer shared by bed scenes. Playback copies
// into a single WriteableBitmap instead of allocating a WIC crop every frame.
internal sealed class LuluWalkBuffer
{
    private sealed record FramePixels(byte[] Pixels, int Left, int Top, int Width, int Height);
    private readonly FramePixels[] frames;
    internal int Width { get; }
    internal int Height { get; }
    private LuluWalkBuffer(FramePixels[] frames, int width, int height)
    { this.frames = frames; Width = width; Height = height; }

    internal static LuluWalkBuffer Load(string root)
    {
        using var doc = JsonDocument.Parse(File.ReadAllText(Path.Combine(root, "manifest.json")));
        var manifest = doc.RootElement; var clip = manifest.GetProperty("clips").GetProperty("depart");
        int width = clip.GetProperty("width").GetInt32(), height = clip.GetProperty("height").GetInt32();
        int pixelScale = manifest.TryGetProperty("pixelScale", out var ps) ? ps.GetInt32() : 1;
        width *= pixelScale; height *= pixelScale;
        string prefix = manifest.TryGetProperty("assetPrefix", out var ap) ? ap.GetString()! : "";
        int columns = manifest.GetProperty("columns").GetInt32(), pageFrames = manifest.GetProperty("pageFrames").GetInt32();
        int count = clip.GetProperty("frames").GetInt32(); var frames = new FramePixels[count];
        for (int i = 0; i < (count + pageFrames - 1) / pageFrames; i++)
        {
            var decoder = BitmapDecoder.Create(new Uri(Path.Combine(root, $"{prefix}depart-{i}.png")), BitmapCreateOptions.PreservePixelFormat, BitmapCacheOption.OnLoad);
            var image = new FormatConvertedBitmap(decoder.Frames[0], PixelFormats.Pbgra32, null, 0);
            var pixels = new byte[image.PixelWidth * image.PixelHeight * 4];
            int stride = image.PixelWidth * 4; image.CopyPixels(pixels, stride, 0);
            for (int local = 0; local < pageFrames && i * pageFrames + local < count; local++)
            {
                int offset = local / columns * height * stride + local % columns * width * 4;
                int left = width, top = height, right = -1, bottom = -1;
                for (int y = 0; y < height; y++) for (int x = 0; x < width; x++)
                    if (pixels[offset + y * stride + x * 4 + 3] != 0)
                    { left = Math.Min(left, x); right = Math.Max(right, x); top = Math.Min(top, y); bottom = Math.Max(bottom, y); }
                int fw = Math.Max(0, right - left + 1), fh = Math.Max(0, bottom - top + 1);
                var packed = new byte[fw * fh * 4];
                for (int row = 0; row < fh; row++) Buffer.BlockCopy(pixels, offset + (top + row) * stride + left * 4, packed, row * fw * 4, fw * 4);
                frames[i * pageFrames + local] = new(packed, left, top, fw, fh);
            }
        }
        return new(frames, width, height);
    }

    internal void CopyFrame(int index, byte[] destination)
    {
        var frame = frames[index]; Array.Clear(destination);
        for (int row = 0; row < frame.Height; row++)
            Buffer.BlockCopy(frame.Pixels, row * frame.Width * 4, destination, ((frame.Top + row) * Width + frame.Left) * 4, frame.Width * 4);
    }
}
