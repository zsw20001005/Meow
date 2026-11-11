using System.Runtime.InteropServices;
using System.Windows;
using System.Windows.Interop;

namespace Meow.Windows;

internal static class Desktop
{
    [StructLayout(LayoutKind.Sequential)] internal struct RECT { public int Left, Top, Right, Bottom; }
    [StructLayout(LayoutKind.Sequential)] private struct MonitorInfo { public int Size; public RECT Monitor, Work; public uint Flags; }
    private delegate bool EnumProc(IntPtr hwnd, IntPtr arg);
    [DllImport("user32.dll")] private static extern IntPtr MonitorFromWindow(IntPtr hwnd, uint flags);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] private static extern bool GetMonitorInfo(IntPtr monitor, ref MonitorInfo info);
    [DllImport("user32.dll")] private static extern bool EnumWindows(EnumProc callback, IntPtr arg);
    [DllImport("user32.dll")] private static extern bool IsWindowVisible(IntPtr hwnd);
    [DllImport("user32.dll")] private static extern bool IsIconic(IntPtr hwnd);
    [DllImport("dwmapi.dll")] private static extern int DwmGetWindowAttribute(IntPtr hwnd, int attr, out RECT rect, int size);
    [DllImport("dwmapi.dll", EntryPoint = "DwmGetWindowAttribute")] private static extern int Cloaked(IntPtr hwnd, int attr, out int value, int size);
    [DllImport("user32.dll")] private static extern uint GetWindowThreadProcessId(IntPtr hwnd, out uint pid);
    public static Rect WorkArea(Window w)
    {
        var info = new MonitorInfo { Size = Marshal.SizeOf<MonitorInfo>() }; var handle = new WindowInteropHelper(w).Handle;
        if (handle == IntPtr.Zero || !GetMonitorInfo(MonitorFromWindow(handle, 2), ref info)) return SystemParameters.WorkArea;
        return Convert(w, info.Work);
    }
    private static Rect Convert(Window w, RECT r)
    {
        var source = PresentationSource.FromVisual(w); var matrix = source?.CompositionTarget?.TransformFromDevice ?? System.Windows.Media.Matrix.Identity;
        return new Rect(matrix.Transform(new Point(r.Left, r.Top)), matrix.Transform(new Point(r.Right, r.Bottom)));
    }
    public static List<(IntPtr Id, Rect Bounds)> Platforms(Window w)
    {
        var result = new List<(IntPtr, Rect)>(); var covered = new List<Rect>();
        EnumWindows((hwnd, _) =>
        {
            GetWindowThreadProcessId(hwnd, out uint pid); if (pid == Environment.ProcessId || !IsWindowVisible(hwnd) || IsIconic(hwnd)) return true;
            if (Cloaked(hwnd, 14, out int cloaked, 4) == 0 && cloaked != 0) return true;
            if (DwmGetWindowAttribute(hwnd, 9, out var rect, Marshal.SizeOf<RECT>()) != 0) return true;
            var b = Convert(w, rect); if (b.Width < 220 || b.Height < 120) return true;
            bool visible = new[] { b.Left + 30, b.Left + b.Width / 2, b.Right - 30 }.Any(x => !covered.Any(c => c.Contains(new Point(x, b.Top + 8)))); covered.Add(b);
            if (visible && b.Top > WorkArea(w).Top + 30) result.Add((hwnd, b)); return true;
        }, IntPtr.Zero); return result;
    }
}
