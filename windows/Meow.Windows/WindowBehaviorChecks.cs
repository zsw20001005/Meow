using System.IO;
using System.Windows;
using System.Windows.Controls;

namespace Meow.Windows;

// Exercise close/dispose without opening windows or reading the user's profile.
internal static class WindowBehaviorChecks
{
    internal static int Run()
    {
        var log = new List<string>();
        void Check(bool value, string message) { if (!value) throw new Exception(message); log.Add("PASS " + message); }
        try
        {
            var store = VisualChecks.Sample(); var pet = new PetWindow(store);
            var chat = new Dashboard(store, pet);
            bool chatClosed = false, petClosed = false, settingsClosed = false;
            chat.Closed += (_, _) => chatClosed = true;
            pet.Closed += (_, _) => petClosed = true;
            var settings = chat.CreateFeatureWindow("settings");
            settings.Closed += (_, _) => { settingsClosed = true; pet.FeatureWindows.Remove("settings"); };
            pet.FeatureWindows["settings"] = settings;
            Check(chat.WindowStyle == WindowStyle.SingleBorderWindow && chat.ResizeMode == ResizeMode.CanResize && !chat.AllowsTransparency && chat.ShowInTaskbar,
                "chat uses native Windows caption and taskbar controls");
            Check(settings.WindowStyle == WindowStyle.SingleBorderWindow && settings.ResizeMode == ResizeMode.CanResize,
                "feature windows use the same native caption");
            chat.Close();
            Check(chatClosed && !chat.IsVisible, "close disposes chat instead of cancelling close and hiding it");
            Check(!petClosed && !Application.Current.Dispatcher.HasShutdownStarted, "closing chat keeps desktop pet and application alive");
            Check(!settingsClosed && pet.FeatureWindows["settings"] == settings, "closing chat does not close another window or lose its registration");
            var reopened = new Dashboard(store, pet);
            Check(store.Data.History.Count == 3, "recreating chat preserves conversation history");
            var content = (FrameworkElement)settings.Content;
            content.Measure(new Size(settings.Width, settings.Height)); content.Arrange(new Rect(0, 0, settings.Width, settings.Height)); content.UpdateLayout();
            var exit = VisualChecks.Find<Button>(content).Single(b => Equals(b.Content, "退出噜噜"));
            Check(exit.IsEnabled, "settings provides a separate explicit exit action");
            reopened.Close();
            pet.ExitApp();
            Check(petClosed && settingsClosed, "explicit exit closes pet and independent feature windows");
            Check(File.Exists(Path.Combine(store.DirectoryPath, "state.json")), "explicit exit saves local state");
            File.WriteAllLines(Path.Combine(AppContext.BaseDirectory, "window-behavior-checks.txt"), log); return 0;
        }
        catch (Exception error) { log.Add("FAIL " + error); File.WriteAllLines(Path.Combine(AppContext.BaseDirectory, "window-behavior-checks.txt"), log); return 1; }
    }
}
