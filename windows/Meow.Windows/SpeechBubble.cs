using System.Runtime.InteropServices;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Interop;
using System.Windows.Media;
using System.Windows.Media.Animation;
using System.Windows.Shapes;

namespace Meow.Windows;

internal sealed class SpeechBubble : Window
{
    private readonly TextBlock text;
    private readonly Grid root;
    private bool dismissing;
    public SpeechBubble()
    {
        WindowStyle = WindowStyle.None; AllowsTransparency = true; Background = Brushes.Transparent;
        ResizeMode = ResizeMode.NoResize; ShowActivated = false; ShowInTaskbar = false; Topmost = true;
        Width = 264; SizeToContent = SizeToContent.Height; IsHitTestVisible = false;
        text = MacTheme.Text("", 13.5); text.FontWeight = FontWeights.Medium; text.Foreground = PetDrawing.B("#523D2E"); text.TextAlignment = TextAlignment.Center; text.LineHeight = 18; text.MaxHeight = 144;
        root = new Grid { Margin = new Thickness(6) }; root.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto }); root.RowDefinitions.Add(new RowDefinition { Height = new GridLength(8) });
        var box = new Border { Background = PetDrawing.B("#FFFBF0"), BorderBrush = PetDrawing.B("#E0C9A8"), BorderThickness = new Thickness(1.5), CornerRadius = new CornerRadius(15), Padding = new Thickness(14, 9, 14, 9), Child = text, Effect = new System.Windows.Media.Effects.DropShadowEffect { BlurRadius = 5, Opacity = .14, ShadowDepth = 2 } }; root.Children.Add(box);
        var tail = new Path { Data = Geometry.Parse("M0,0 Q5,4.5 8,9 Q11,4.5 16,0"), Fill = PetDrawing.B("#FFFBF0"), Stroke = PetDrawing.B("#E0C9A8"), StrokeThickness = 1.5, Width = 18, Height = 10, HorizontalAlignment = HorizontalAlignment.Center, Margin = new Thickness(0, -2, 0, 0) }; Grid.SetRow(tail, 1); root.Children.Add(tail); Content = root;
        SourceInitialized += (_, _) => { var hwnd = new WindowInteropHelper(this).Handle; SetWindowLong(hwnd, -20, new IntPtr(GetWindowLong(hwnd, -20).ToInt64() | 0x08000000 | 0x80 | 0x20)); };
    }
    public void Say(string message, Window pet, Rect area)
    {
        dismissing = false;
        text.Text = message.Length > 180 ? message[..180] + "…" : message;
        // Measure short remarks to their natural width, capped at the original 250-point body.
        text.Measure(new Size(220, double.PositiveInfinity)); Width = Math.Clamp(text.DesiredSize.Width + 44, 70, 264);
        if (!IsVisible) Show(); UpdateLayout(); Position(pet, area);
        BeginAnimation(OpacityProperty, new DoubleAnimation(1, TimeSpan.FromSeconds(.18)));
    }
    public void Position(Window pet, Rect area)
    {
        if (!IsVisible) return;
        Left = Math.Clamp(pet.Left + pet.Width / 2 - Width / 2, area.Left + 4, Math.Max(area.Left + 4, area.Right - Width - 4));
        double y = pet.Top + pet.Height * .16 - ActualHeight - 2;
        Top = y < area.Top + 4 ? Math.Min(area.Bottom - ActualHeight - 4, pet.Top + pet.Height * .86) : y;
    }
    public void Dismiss()
    {
        if (!IsVisible || dismissing) return;
        dismissing = true;
        var fade = new DoubleAnimation(0, TimeSpan.FromSeconds(.25)); fade.Completed += (_, _) => { if (Opacity == 0) Hide(); }; BeginAnimation(OpacityProperty, fade);
    }
    [DllImport("user32.dll", EntryPoint = "GetWindowLongPtrW")] private static extern IntPtr GetWindowLong(IntPtr hwnd, int index);
    [DllImport("user32.dll", EntryPoint = "SetWindowLongPtrW")] private static extern IntPtr SetWindowLong(IntPtr hwnd, int index, IntPtr value);
}
