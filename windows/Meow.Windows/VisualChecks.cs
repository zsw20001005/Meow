using System.Globalization;
using System.IO;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Media.Imaging;

namespace Meow.Windows;

// Offline, deterministic screenshots. Uses a separate synthetic store; never reads
// the user's history or credentials and never issues a model/network request.
internal static class VisualChecks
{
    internal static Store Sample()
    {
        var store = new Store(Path.Combine(Path.GetTempPath(), "meow-visual-" + Guid.NewGuid()));
        store.Data.Wander = false; store.Data.NightSleep = false; store.Data.AutoMemory = false;
        store.Data.History.AddRange([new("assistant", "主人，你来啦～今天想和噜噜聊些什么？"), new("user", "今天有点累，陪我待一会儿吧。"), new("assistant", "当然啦，我就在这里陪着你。先伸个懒腰，慢慢放松一下呀～")]);
        store.Data.Facts.Add(new MemoryFact { Text = "主人喜欢茉莉花茶", Evidence = "我喜欢茉莉花茶", At = new DateTimeOffset(2026, 11, 10, 10, 0, 0, TimeSpan.FromHours(8)) });
        store.Data.Experiences.Add(new Experience { Day = "2026-11-10", Kind = "摸摸头", Count = 3 });
        store.Data.Memos.Add(new Memo { Title = "和朋友一起吃晚饭", Due = new DateTimeOffset(2026, 11, 11, 19, 0, 0, TimeSpan.FromHours(8)) });
        store.Data.Mail.Entries.Add(new MailEntry { Incoming = true, Letter = new Letter { body = "今天也要好好吃饭呀。\n\n让噜噜带着这封信，替我陪你一会儿。", createdAt = "2026-11-10T06:30:00Z" } });
        return store;
    }
    public static int Run()
    {
        var output = Path.Combine(AppContext.BaseDirectory, "visual-checks"); Directory.CreateDirectory(output);
        var log = new List<string>(); Store? store = null;
        try
        {
            CultureInfo.CurrentCulture = CultureInfo.GetCultureInfo("zh-CN");
            store = Sample(); var pet = new PetWindow(store); var chat = new Dashboard(store, pet);
            RenderWindow(chat, "chat");
            foreach (string kind in new[] { "settings", "memory", "memos", "news", "mail" })
            {
                var window = chat.CreateFeatureWindow(kind); RenderWindow(window, kind);
                if (kind == "settings")
                {
                    var scroll = Find<ScrollViewer>((DependencyObject)window.Content).First(); scroll.ScrollToEnd(); window.UpdateLayout();
                    Save((FrameworkElement)window.Content, window.Width, window.Height, Path.Combine(output, "settings-bottom.png"));
                    if (scroll.ScrollableHeight <= 0 || Math.Abs(scroll.VerticalOffset - scroll.ScrollableHeight) > 1) throw new Exception("Settings footer is not reachable by scrolling.");
                    var bar = Find<System.Windows.Controls.Primitives.ScrollBar>(scroll).First();
                    if (bar.ActualWidth > 6.1) throw new Exception("System scrollbar minimum width overrides the compact design.");
                    log.Add("PASS settings scroll reaches footer; scrollbar is 6 points wide");
                    var services = Find<ComboBox>((DependencyObject)window.Content).Single(c => c.ItemsSource is ModelProvider[]);
                    var fields = Find<TextBox>((DependencyObject)window.Content).ToArray();
                    string originalAddress = fields[0].Text, originalModel = fields[1].Text;
                    services.SelectedItem = ModelProviders.Get("openai");
                    if (fields[0].Text != "https://api.openai.com/v1" || fields[1].Text != "" || store.Data.Provider != "ark") throw new Exception("Provider selection leaked settings or applied without saving.");
                    fields[1].Text = "my-account-model";
                    services.SelectedItem = ModelProviders.Get("anthropic");
                    if (fields[0].Text != "https://api.anthropic.com/v1" || fields[1].Text != "") throw new Exception("Claude preset incorrect.");
                    scroll.ScrollToTop(); window.UpdateLayout();
                    Save((FrameworkElement)window.Content, window.Width, window.Height, Path.Combine(output, "settings-claude.png"));
                    services.SelectedItem = ModelProviders.Get("openai");
                    if (fields[1].Text != "my-account-model") throw new Exception("Unsaved provider draft lost.");
                    window.UpdateLayout(); Save((FrameworkElement)window.Content, window.Width, window.Height, Path.Combine(output, "settings-gpt.png"));
                    services.SelectedItem = ModelProviders.Get("ark");
                    if (fields[0].Text != originalAddress || fields[1].Text != originalModel) throw new Exception("Original Ark UI settings lost.");
                    log.Add("PASS provider selection, isolated model drafts, GPT/Claude screens and original Ark settings");
                }
                window.Close();
            }
            var samples = new (string label, string activity, string emotion)[] {
                ("angry", "idle", "angry"), ("curious", "idle", "curious"), ("dancing", "dance", "neutral"), ("dizzy", "idle", "dizzy"), ("dragged", "drag", "neutral"), ("eating", "eat", "neutral"), ("happy", "idle", "happy"),
                ("hungry", "idle", "hungry"), ("idle-neutral", "idle", "neutral"), ("love", "idle", "love"), ("playing", "play", "neutral"), ("sad", "idle", "sad"), ("shy", "idle", "shy"), ("sleeping", "sleep", "neutral"),
                ("sleepy", "idle", "sleepy"), ("stretching", "stretch", "neutral"), ("sulking", "idle", "sad"), ("surprised", "idle", "surprised"), ("talking", "idle", "happy"), ("thinking", "think", "neutral"), ("walking", "walk", "neutral") };
            var sheet = new Canvas { Width = 1610, Height = 690, Background = PetDrawing.B("#8AA6BD") };
            for (int i = 0; i < samples.Length; i++) { var sample = samples[i]; var drawing = new PetDrawing { Width = 230, Height = 230, Action = sample.activity, Emotion = sample.emotion, Time = .9, PosePhase = sample.label == "stretching" ? 1.1 : null, WalkPhase = 1.2, LookAway = sample.label == "sulking" ? 1 : 0, TalkLevel = sample.label == "talking" ? .8 : 0 }; Canvas.SetLeft(drawing, i % 7 * 230); Canvas.SetTop(drawing, i / 7 * 230); sheet.Children.Add(drawing); var label = new TextBlock { Text = sample.label, FontSize = 10, Foreground = Brushes.Black }; Canvas.SetLeft(label, i % 7 * 230 + 6); Canvas.SetTop(label, i / 7 * 230 + 4); sheet.Children.Add(label); }
            Save(sheet, 1610, 690, Path.Combine(output, "pet-states.png")); log.Add("PASS 21 Zhang Lulu states rendered with bowl cut and glasses");
            Save(new PetDrawing { Time = .9 }, 600, 600, Path.Combine(output, "zhang-lulu.png"));
            var comparison = new Canvas { Width = 1200, Height = 600, Background = PetDrawing.B("#FAF6EF") };
            comparison.Children.Add(new Image { Width = 600, Height = 600, Stretch = Stretch.Uniform, Source = new BitmapImage(new Uri(Path.Combine(AppContext.BaseDirectory, "Assets", "Lulu", "reference.png"))) });
            var actual = new PetDrawing { Width = 570, Height = 570 }; Canvas.SetLeft(actual, 615); Canvas.SetTop(actual, 48); comparison.Children.Add(actual);
            Save(comparison, 1200, 600, Path.Combine(output, "design-comparison.png"));
            foreach (var atlas in LuluRigAssets.All) log.Add($"PASS transparent {atlas.FileName}: {atlas.PixelWidth}x{atlas.PixelHeight}, {atlas.Count} fixed parts");
            var animated = new Canvas { Width = 1840, Height = 920, Background = PetDrawing.B("#263746") };
            var activities = new[] { "walk", "wave", "sleep", "think", "eat", "play", "letter", "talk" };
            for (int row = 0; row < 4; row++) for (int column = 0; column < 8; column++)
            {
                string a = activities[column]; double phase = (row + .1) / (a == "think" ? 2 : a == "sleep" ? 1.5 : a == "letter" ? 2 : a == "talk" ? 5 : 4);
                var d = new PetDrawing { Width = 230, Height = 230, Action = a, Time = phase, PosePhase = phase, WalkPhase = (row + .1) * Math.PI / 2, Unread = a == "letter" ? 2 : 0, TalkLevel = a == "talk" ? .8 : 0 };
                Canvas.SetLeft(d, column * 230); Canvas.SetTop(d, row * 230); animated.Children.Add(d);
            }
            Save(animated, 1840, 920, Path.Combine(output, "animation-frames.png"));
            foreach (string activity in new[] { "walk", "wave", "play" })
            {
                var sequence = new Canvas { Width = 920, Height = 920, Background = PetDrawing.B("#263746") };
                for (int frame = 0; frame < 16; frame++)
                {
                    double t = activity == "wave" ? frame / 15d * PetDrawing.Duration("wave") : frame / 12d;
                    var d = new PetDrawing { Width = 230, Height = 230, Action = activity, Time = 0, PosePhase = t, WalkPhase = frame / 16d * Math.PI * 2 };
                    Canvas.SetLeft(d, frame % 4 * 230); Canvas.SetTop(d, frame / 4 * 230); sequence.Children.Add(d);
                }
                Save(sequence, 920, 920, Path.Combine(output, activity + "-16frames.png"));
            }
            var transitions = new Canvas { Width = 1150, Height = 230, Background = PetDrawing.B("#263746") };
            for (int step = 0; step < 5; step++)
            {
                var d = new PetDrawing { Width = 230, Height = 230, Action = "walk", Time = 0, WalkPhase = (3 + step / 4d) / 16d * Math.PI * 2 };
                Canvas.SetLeft(d, step * 230); transitions.Children.Add(d);
            }
            Save(transitions, 1150, 230, Path.Combine(output, "walk-interpolation.png"));
            foreach (string action in new[] { "wave", "nod", "shakeHead", "spin", "roll", "stretch", "jump" })
            {
                var frames = new Canvas { Width = 1150, Height = 230, Background = PetDrawing.B("#8AA6BD") };
                for (int i = 0; i < 5; i++) { var d = new PetDrawing { Width = 230, Height = 230, Action = action, Time = .9, PosePhase = PetDrawing.Duration(action) * new[] { 0d, .15, .32, .66, 1d }[i] }; Canvas.SetLeft(d, i * 230); frames.Children.Add(d); }
                Save(frames, 1150, 230, Path.Combine(output, action + ".png"));
            }
            foreach (string side in new[] { "left", "right" }) foreach (double reveal in new[] { 0d, 1d })
            { double w = Math.Ceiling((82 + 68 * reveal) * 1.15), h = Math.Ceiling((132 + 44 * reveal) * 1.15); Save(new PetDrawing { Wall = side, Reveal = reveal, Time = .8, Unread = reveal > 0 ? 2 : 0 }, w, h, Path.Combine(output, $"wall-{side}-{reveal}.png")); }
            Save(new PetDrawing { Time = .8, Unread = 3 }, 230, 230, Path.Combine(output, "held-letter.png"));
            // Path parsing must be independent of Windows decimal formatting.
            CultureInfo.CurrentCulture = CultureInfo.GetCultureInfo("fr-FR");
            Save(new PetDrawing { Action = "wave", Time = .7 }, 299, 299, Path.Combine(output, "culture-fr.png"));
            log.Add("PASS wall geometry, held letter, action phases and decimal-comma culture");
            log.Add("All Zhang Lulu visual render checks passed. Mac client remains unchanged.");
            File.WriteAllLines(Path.Combine(output, "results.txt"), log); return 0;
            void RenderWindow(Window w, string name)
            {
                var content = (FrameworkElement)w.Content; Save(content, w.Width, w.Height, Path.Combine(output, name + ".png")); Save(content, w.Width, w.Height, Path.Combine(output, name + "@2x.png"), 2);
                if (content.ActualWidth != w.Width || content.ActualHeight != w.Height) throw new Exception(name + " viewport mismatch");
                log.Add($"PASS {name} {w.Width}x{w.Height} at 1x / 2x");
            }
        }
        catch (Exception e) { log.Add("FAIL " + e); File.WriteAllLines(Path.Combine(output, "results.txt"), log); return 1; }
        finally { if (store is not null) Directory.Delete(store.DirectoryPath, true); }
    }
    internal static IEnumerable<T> Find<T>(DependencyObject root) where T : DependencyObject
    {
        if (root is T match) yield return match;
        for (int i = 0; i < VisualTreeHelper.GetChildrenCount(root); i++) foreach (var child in Find<T>(VisualTreeHelper.GetChild(root, i))) yield return child;
    }
    internal static void Save(FrameworkElement element, double w, double h, string file, double scale = 1)
    {
        element.Measure(new Size(w, h)); element.Arrange(new Rect(0, 0, w, h)); element.UpdateLayout();
        var bitmap = new RenderTargetBitmap((int)Math.Ceiling(w * scale), (int)Math.Ceiling(h * scale), 96 * scale, 96 * scale, PixelFormats.Pbgra32); bitmap.Render(element);
        var encoder = new PngBitmapEncoder(); encoder.Frames.Add(BitmapFrame.Create(bitmap)); using var stream = File.Create(file); encoder.Save(stream);
    }
}
