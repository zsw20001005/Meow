using System.Runtime.InteropServices;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using OpenCvSharp;

namespace Meow.Windows;

// Register the two poses before interpolating a single opaque silhouette.
// Frames are prepared off the UI thread; the exact displayed pose stays visible
// while preparation runs. This does not fade two unaligned characters together.
internal sealed class LuluPoseTransition
{
    private const int Size = 512;
    private static readonly Lazy<Task> NativeWarmup = new(() => Task.Run(() => { _ = Cv2.GetVersionString(); }));
    internal static void WarmUp() => _ = NativeWarmup.Value;
    internal readonly Task<BitmapSource[]> Preparation;
    internal readonly BitmapSource Source;
    internal double Duration { get; }
    internal double Elapsed { get; private set; }
    internal Exception? Error => Preparation.Exception?.GetBaseException();
    internal BitmapSource Frame => Preparation.IsCompletedSuccessfully
        ? Preparation.Result[Math.Min((int)(Elapsed * 60), Preparation.Result.Length - 1)] : Source;
    internal LuluPoseTransition(BitmapSource source, BitmapSource target, double duration)
    {
        Source = source; Duration = duration;
        Preparation = Task.Run(() => Build(source, target, duration));
    }
    internal bool Advance(double seconds)
    {
        if (!Preparation.IsCompletedSuccessfully) return false;
        Elapsed = Math.Min(Duration, Elapsed + Math.Max(0, seconds));
        return Elapsed >= Duration - 1e-9;
    }
    private static byte[] Pixels(BitmapSource image)
    {
        var p = new byte[Size * Size * 4];
        new FormatConvertedBitmap(image, PixelFormats.Pbgra32, null, 0).CopyPixels(p, Size * 4, 0);
        return p;
    }
    private static Mat Gray(byte[] p)
    {
        var v = new byte[Size * Size];
        for (int i = 0; i < v.Length; i++)
        {
            int n = i * 4;
            v[i] = (byte)Math.Clamp(.114 * p[n] + .587 * p[n + 1] + .299 * p[n + 2] + 255 - p[n + 3], 0, 255);
        }
        var mat = new Mat(Size, Size, MatType.CV_8UC1); Marshal.Copy(v, 0, mat.Data, v.Length); return mat;
    }
    private static float[] Read(Mat mat, int channels = 1)
    {
        var v = new float[Size * Size * channels]; Marshal.Copy(mat.Data, v, 0, v.Length); return v;
    }
    private static float[] Distance(byte[] p)
    {
        var v = new byte[Size * Size];
        for (int i = 0; i < v.Length; i++) v[i] = p[i * 4 + 3] > 127 ? (byte)255 : (byte)0;
        using var mask = new Mat(Size, Size, MatType.CV_8UC1); Marshal.Copy(v, 0, mask.Data, v.Length);
        using var inverse = new Mat(); using var inside = new Mat(); using var outside = new Mat();
        Cv2.BitwiseNot(mask, inverse);
        Cv2.DistanceTransform(mask, inside, DistanceTypes.L2, DistanceTransformMasks.Mask5);
        Cv2.DistanceTransform(inverse, outside, DistanceTypes.L2, DistanceTransformMasks.Mask5);
        var a = Read(inside); var b = Read(outside);
        for (int i = 0; i < a.Length; i++) a[i] -= b[i];
        return a;
    }
    private static float Sample(float[] p, float x, float y, int channels = 1, int channel = 0)
    {
        x = Math.Clamp(x, 0, Size - 1); y = Math.Clamp(y, 0, Size - 1);
        int x0 = (int)x, y0 = (int)y, x1 = Math.Min(x0 + 1, Size - 1), y1 = Math.Min(y0 + 1, Size - 1);
        float fx = x - x0, fy = y - y0;
        return (p[(y0 * Size + x0) * channels + channel] * (1 - fx) + p[(y0 * Size + x1) * channels + channel] * fx) * (1 - fy)
             + (p[(y1 * Size + x0) * channels + channel] * (1 - fx) + p[(y1 * Size + x1) * channels + channel] * fx) * fy;
    }
    private static (float X, float Y) Warp(float[] flow, int x, int y, float t)
    {
        float mx = x, my = y;
        for (int i = 0; i < 4; i++)
        {
            float dx = Sample(flow, mx, my, 2), dy = Sample(flow, mx, my, 2, 1);
            mx = x - t * dx; my = y - t * dy;
        }
        return (mx, my);
    }
    private static BitmapSource[] Build(BitmapSource source, BitmapSource target, double duration)
    {
        NativeWarmup.Value.GetAwaiter().GetResult();
        byte[] a = Pixels(source), b = Pixels(target);
        using var ag = Gray(a); using var bg = Gray(b); using var ab = new Mat(); using var ba = new Mat();
        // A broad smoothing window merges the two glasses rims and leaves a
        // doubled face during the mirrored-front join. Keep small features local.
        Cv2.CalcOpticalFlowFarneback(ag, bg, ab, .5, 5, 9, 10, 5, 1.1, OpticalFlowFlags.None);
        Cv2.CalcOpticalFlowFarneback(bg, ag, ba, .5, 5, 9, 10, 5, 1.1, OpticalFlowFlags.None);
        var forward = Read(ab, 2); var backward = Read(ba, 2);
        var da = Distance(a); var db = Distance(b);
        float[] af = Array.ConvertAll(a, x => (float)x), bf = Array.ConvertAll(b, x => (float)x);
        int count = (int)Math.Round(duration * 60) + 1;
        var frames = new BitmapSource[count]; frames[0] = source; frames[^1] = target;
        Parallel.For(1, count - 1, new ParallelOptions { MaxDegreeOfParallelism = 4 }, n =>
        {
            float t = (float)((1 - Math.Cos(Math.PI * n / (count - 1))) / 2);
            var p = new byte[a.Length];
            for (int y = 0; y < Size; y++) for (int x = 0; x < Size; x++)
            {
                var wa = Warp(forward, x, y, t); var wb = Warp(backward, x, y, 1 - t);
                float alpha = Math.Clamp(Sample(da, wa.X, wa.Y) * (1 - t) + Sample(db, wb.X, wb.Y) * t + .5f, 0, 1) * 255;
                float originalAlpha = Sample(af, wa.X, wa.Y, 4, 3) * (1 - t) + Sample(bf, wb.X, wb.Y, 4, 3) * t;
                int at = (y * Size + x) * 4; p[at + 3] = (byte)Math.Round(alpha);
                for (int c = 0; c < 3; c++)
                {
                    float color = Sample(af, wa.X, wa.Y, 4, c) * (1 - t) + Sample(bf, wb.X, wb.Y, 4, c) * t;
                    p[at + c] = (byte)Math.Clamp(Math.Round(originalAlpha > .01 ? color / originalAlpha * alpha : 0), 0, p[at + 3]);
                }
            }
            var frame = BitmapSource.Create(Size, Size, 96, 96, PixelFormats.Pbgra32, null, p, Size * 4); frame.Freeze(); frames[n] = frame;
        });
        return frames;
    }
}
