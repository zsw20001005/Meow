using System.Windows;
using System.Windows.Controls;
using System.Windows.Markup;
using System.Windows.Media;

namespace Meow.Windows;

// Preserve the character's palette while using native Windows window chrome.
internal static class MacTheme
{
    public static readonly Brush Paper = PetDrawing.B("#FFF9F0"), Cocoa = PetDrawing.B("#5C4536"), Accent = PetDrawing.B("#FA8CA1"), Muted = PetDrawing.B("#998579");
    public static readonly FontFamily Font = new("Microsoft YaHei UI");
    public static void Shell(Window window, string title, double width, double height, UIElement content)
    {
        window.Title = title; window.Width = width; window.Height = height;
        window.FontFamily = Font; window.FontSize = 13; window.Foreground = Cocoa;
        window.WindowStyle = WindowStyle.SingleBorderWindow; window.ResizeMode = ResizeMode.CanResize;
        window.MinWidth = width; window.MinHeight = Math.Min(height, 360);
        window.AllowsTransparency = false; window.Background = Paper; window.ShowInTaskbar = true;
        TextOptions.SetTextFormattingMode(window, TextFormattingMode.Display);
        window.UseLayoutRounding = true; window.WindowStartupLocation = WindowStartupLocation.CenterScreen;
        window.Resources.MergedDictionaries.Add((ResourceDictionary)XamlReader.Parse(Resources));
        window.Content = new Border { Background = Paper, Child = content };
    }
    public static Window Window(string title, double width, double height, UIElement content) { var w = new Window(); Shell(w, title, width, height, content); return w; }
    public static TextBlock Text(string text, double size = 13, bool bold = false) => new() { Text = text, FontSize = size, FontWeight = bold ? FontWeights.SemiBold : FontWeights.Normal, Foreground = Cocoa, TextWrapping = TextWrapping.Wrap };
    public static TextBlock Hint(string text) { var t = Text(text, 11); t.Foreground = Muted; return t; }
    public static Border Divider() => new() { Height = 1, Background = PetDrawing.B("#245C4536"), Margin = new Thickness(0, 6, 0, 6) };
    public static Button Button(string text, Action action) { var b = new Button { Content = text, Padding = new Thickness(9, 3, 9, 3), Margin = new Thickness(0, 0, 6, 0), HorizontalAlignment = HorizontalAlignment.Left }; b.Click += (_, _) => action(); return b; }
    public static Border Card(UIElement child, double padding = 12) => new() { Background = PetDrawing.B("#D9FFFFFF"), CornerRadius = new CornerRadius(10), Padding = new Thickness(padding), Child = child, Margin = new Thickness(0, 0, 0, 10) };
    public static ScrollViewer Scroll(UIElement content) { var scroll = new ScrollViewer { Content = content, VerticalScrollBarVisibility = ScrollBarVisibility.Auto, HorizontalScrollBarVisibility = ScrollBarVisibility.Disabled }; scroll.SetResourceReference(FrameworkElement.StyleProperty, "MacScroll"); return scroll; }
    public static StackPanel Stack() => new();
    public static DockPanel Page(string title, out StackPanel head, out StackPanel foot)
    {
        var p = new DockPanel { Margin = new Thickness(20, 18, 20, 20) };
        head = new StackPanel(); DockPanel.SetDock(head, Dock.Top); p.Children.Add(head);
        var t = Text(title, 18, true); t.Margin = new Thickness(0, 0, 0, 12); head.Children.Add(t);
        foot = new StackPanel(); DockPanel.SetDock(foot, Dock.Bottom); p.Children.Add(foot); return p;
    }
    public static CheckBox Toggle(string title, bool value, Action<bool> changed)
    {
        var b = new CheckBox { Content = title, IsChecked = value, Margin = new Thickness(0, 6, 0, 6), VerticalContentAlignment = VerticalAlignment.Center };
        b.Click += (_, _) => changed(b.IsChecked == true); return b;
    }
    public static UIElement Segments(string[] labels, int selected, Action<int> change)
    {
        var p = new System.Windows.Controls.Primitives.UniformGrid { Columns = labels.Length };
        var buttons = new List<Button>();
        void Paint(int index) { for (int j = 0; j < buttons.Count; j++) { buttons[j].Background = j == index ? Brushes.White : Brushes.Transparent; buttons[j].FontWeight = j == index ? FontWeights.SemiBold : FontWeights.Normal; } }
        for (int i = 0; i < labels.Length; i++) { int index = i; var b = Button(labels[i], () => { Paint(index); change(index); }); b.HorizontalAlignment = HorizontalAlignment.Stretch; b.Margin = new Thickness(1); b.BorderThickness = new Thickness(0); buttons.Add(b); p.Children.Add(b); }
        Paint(selected); return new Border { Child = p, Padding = new Thickness(1), CornerRadius = new CornerRadius(6), Background = PetDrawing.B("#145C4536"), Margin = new Thickness(0, 4, 0, 10) };
    }
    private const string Resources = """
    <ResourceDictionary xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation" xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">
      <Style TargetType="Button">
        <Setter Property="Foreground" Value="#5C4536"/><Setter Property="Background" Value="#F5FFFFFF"/><Setter Property="BorderBrush" Value="#305C4536"/><Setter Property="BorderThickness" Value="0.6"/><Setter Property="Cursor" Value="Hand"/>
        <Setter Property="FontSize" Value="12"/><Setter Property="Padding" Value="9,3"/><Setter Property="HorizontalContentAlignment" Value="Center"/>
        <Setter Property="Template"><Setter.Value><ControlTemplate TargetType="Button"><Border x:Name="border" CornerRadius="6" Background="{TemplateBinding Background}" BorderBrush="{TemplateBinding BorderBrush}" BorderThickness="{TemplateBinding BorderThickness}" Padding="{TemplateBinding Padding}"><ContentPresenter HorizontalAlignment="{TemplateBinding HorizontalContentAlignment}" VerticalAlignment="Center"/></Border><ControlTemplate.Triggers><Trigger Property="IsMouseOver" Value="True"><Setter TargetName="border" Property="Opacity" Value="0.72"/></Trigger><Trigger Property="IsEnabled" Value="False"><Setter TargetName="border" Property="Opacity" Value="0.4"/></Trigger><Trigger Property="IsKeyboardFocused" Value="True"><Setter TargetName="border" Property="BorderBrush" Value="#FA8CA1"/></Trigger></ControlTemplate.Triggers></ControlTemplate></Setter.Value></Setter>
      </Style>
      <Style TargetType="TextBox"><Setter Property="Foreground" Value="#5C4536"/><Setter Property="Background" Value="White"/><Setter Property="BorderBrush" Value="#305C4536"/><Setter Property="BorderThickness" Value="1"/><Setter Property="Padding" Value="6,2"/><Setter Property="SelectionBrush" Value="#FA8CA1"/><Setter Property="Template"><Setter.Value><ControlTemplate TargetType="TextBox"><Border CornerRadius="5" Background="{TemplateBinding Background}" BorderBrush="{TemplateBinding BorderBrush}" BorderThickness="{TemplateBinding BorderThickness}" Padding="{TemplateBinding Padding}"><Grid><TextBlock x:Name="placeholder" Text="{TemplateBinding ToolTip}" Foreground="#998579" Visibility="Collapsed" IsHitTestVisible="False"/><ScrollViewer x:Name="PART_ContentHost"/></Grid></Border><ControlTemplate.Triggers><Trigger Property="Text" Value=""><Setter TargetName="placeholder" Property="Visibility" Value="Visible"/></Trigger></ControlTemplate.Triggers></ControlTemplate></Setter.Value></Setter></Style>
            <Style TargetType="ComboBox"><Setter Property="Foreground" Value="#5C4536"/><Setter Property="MinHeight" Value="25"/><Setter Property="Template"><Setter.Value><ControlTemplate TargetType="ComboBox"><Grid><ToggleButton Focusable="False" IsChecked="{Binding IsDropDownOpen, RelativeSource={RelativeSource TemplatedParent}, Mode=TwoWay}"><ToggleButton.Template><ControlTemplate TargetType="ToggleButton"><Border CornerRadius="5" Background="White" BorderBrush="#305C4536" BorderThickness="0.6"><Path Data="M0,0 L3,3 L6,0" Stroke="#5C4536" StrokeThickness="1" HorizontalAlignment="Right" VerticalAlignment="Center" Margin="0,0,7,0"/></Border></ControlTemplate></ToggleButton.Template></ToggleButton><ContentPresenter Content="{TemplateBinding SelectionBoxItem}" ContentTemplate="{TemplateBinding SelectionBoxItemTemplate}" Margin="7,2,22,2" VerticalAlignment="Center" IsHitTestVisible="False"/><Popup x:Name="PART_Popup" IsOpen="{TemplateBinding IsDropDownOpen}" Placement="Bottom" AllowsTransparency="True" Focusable="False"><Border Background="#FFF9F0" CornerRadius="5" BorderBrush="#305C4536" BorderThickness="1" Padding="4" MinWidth="{Binding ActualWidth, RelativeSource={RelativeSource TemplatedParent}}"><ScrollViewer><ItemsPresenter/></ScrollViewer></Border></Popup></Grid></ControlTemplate></Setter.Value></Setter></Style>
      <Style TargetType="PasswordBox"><Setter Property="Foreground" Value="#5C4536"/><Setter Property="BorderBrush" Value="#305C4536"/><Setter Property="Padding" Value="6,2"/></Style>
      <Style TargetType="CheckBox"><Setter Property="Foreground" Value="#5C4536"/><Setter Property="FontSize" Value="12.5"/><Setter Property="Template"><Setter.Value><ControlTemplate TargetType="CheckBox"><DockPanel LastChildFill="True"><Grid DockPanel.Dock="Right" Width="28" Height="16" Margin="10,0,0,0"><Border x:Name="track" CornerRadius="8" Background="#C8C1BA"/><Ellipse x:Name="thumb" Fill="White" Width="12" Height="12" HorizontalAlignment="Left" Margin="2"/></Grid><ContentPresenter VerticalAlignment="Center"/></DockPanel><ControlTemplate.Triggers><Trigger Property="IsChecked" Value="True"><Setter TargetName="track" Property="Background" Value="#FA8CA1"/><Setter TargetName="thumb" Property="HorizontalAlignment" Value="Right"/></Trigger><Trigger Property="IsEnabled" Value="False"><Setter Property="Opacity" Value="0.45"/></Trigger><Trigger Property="IsKeyboardFocused" Value="True"><Setter TargetName="track" Property="Background" Value="#C76479"/></Trigger></ControlTemplate.Triggers></ControlTemplate></Setter.Value></Setter></Style>
      <Style TargetType="TextBlock" x:Key="Status"><Setter Property="Foreground" Value="#998579"/><Setter Property="FontSize" Value="10.5"/><Setter Property="TextWrapping" Value="Wrap"/><Setter Property="MaxHeight" Value="42"/><Style.Triggers><Trigger Property="Text" Value=""><Setter Property="Visibility" Value="Collapsed"/></Trigger></Style.Triggers></Style>
            <Style TargetType="ScrollBar"><Setter Property="MinWidth" Value="0"/><Setter Property="Width" Value="6"/><Setter Property="Template"><Setter.Value><ControlTemplate TargetType="ScrollBar"><Track x:Name="PART_Track" Orientation="Vertical" IsDirectionReversed="True"><Track.DecreaseRepeatButton><RepeatButton Command="ScrollBar.PageUpCommand" Opacity="0" Focusable="False"/></Track.DecreaseRepeatButton><Track.Thumb><Thumb><Thumb.Template><ControlTemplate TargetType="Thumb"><Border Background="#555C4536" CornerRadius="3" Margin="1,2"/></ControlTemplate></Thumb.Template></Thumb></Track.Thumb><Track.IncreaseRepeatButton><RepeatButton Command="ScrollBar.PageDownCommand" Opacity="0" Focusable="False"/></Track.IncreaseRepeatButton></Track></ControlTemplate></Setter.Value></Setter></Style>
      <Style x:Key="MacScroll" TargetType="ScrollViewer"><Setter Property="Template"><Setter.Value><ControlTemplate TargetType="ScrollViewer"><Grid><Grid.ColumnDefinitions><ColumnDefinition Width="*"/><ColumnDefinition Width="Auto"/></Grid.ColumnDefinitions><ScrollContentPresenter x:Name="PART_ScrollContentPresenter" Content="{TemplateBinding Content}" ContentTemplate="{TemplateBinding ContentTemplate}" CanContentScroll="{TemplateBinding CanContentScroll}"/><ScrollBar x:Name="PART_VerticalScrollBar" Grid.Column="1" MinWidth="0" Width="6" Orientation="Vertical" Minimum="0" Maximum="{TemplateBinding ScrollableHeight}" Value="{Binding VerticalOffset, RelativeSource={RelativeSource TemplatedParent}, Mode=OneWay}" ViewportSize="{TemplateBinding ViewportHeight}" Visibility="{TemplateBinding ComputedVerticalScrollBarVisibility}"/></Grid></ControlTemplate></Setter.Value></Setter></Style>
      <Style x:Key="CircleButton" TargetType="Button" BasedOn="{StaticResource {x:Type Button}}"><Setter Property="Template"><Setter.Value><ControlTemplate TargetType="Button"><Border Background="{TemplateBinding Background}" CornerRadius="99"><ContentPresenter HorizontalAlignment="Center" VerticalAlignment="Center"/></Border></ControlTemplate></Setter.Value></Setter></Style>
    </ResourceDictionary>
    """;
}
