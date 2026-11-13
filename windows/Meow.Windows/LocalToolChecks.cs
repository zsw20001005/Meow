using System.IO;
using System.Text.Json;

namespace Meow.Windows;

internal static class LocalToolChecks
{
    internal static async Task<int> Run()
    {
        var root = Path.Combine(Path.GetTempPath(), "meow-local-tools-" + Guid.NewGuid()); var lines = new List<string>();
        void Check(bool value, string name) { if (!value) throw new Exception(name); lines.Add("PASS " + name); }
        try
        {
            var store = new Store(root); using var mail = new MailboxService(store); var opened = ""; int transports = 0; bool delivered = false;
            var tools = new ConversationTools(store, mail, p => opened = p, () => { transports++; if (delivered) foreach (var e in store.Data.Mail.Entries) e.Delivered = true; return Task.CompletedTask; });
            async Task<LocalToolResult> Run(string name, object args, string text) => (await tools.Execute([ConversationTools.Call(name, args)], text, Guid.NewGuid(), default))[0];
            var quick = tools.Quick("记下：不要把这封信寄出去");
            var firstTurn = Guid.NewGuid(); await tools.Execute(quick, "记下：不要把这封信寄出去", firstTurn, default);
            Check(store.Data.Notes.Count == 1 && store.Data.Notes[0].Body == "不要把这封信寄出去", "quoted command content is stored as note data, never executed");
            await tools.Execute(quick, "记下：不要把这封信寄出去", firstTurn, default);
            Check(store.Data.Notes.Count == 1, "same turn cannot repeat note mutation");
            Check(new Store(root).Data.Notes.Count == 1, "notes survive reload");
            await Run("note.add", new { title = "购物清单", body = "牛奶" }, "帮我记一条购物笔记");
            var note = store.Data.Notes.Last();
            await Run("note.update", new { query = note.Id.ToString(), body = "牛奶和鸡蛋" }, "把购物清单改成牛奶和鸡蛋");
            Check(store.Data.Notes.Last().Body == "牛奶和鸡蛋", "note updates resolve actual persisted ID");
            await Run("note.append", new { query = note.Id.ToString(), body = "苹果" }, "给购物清单加上苹果");
            Check(store.Data.Notes.Last().Body == "牛奶和鸡蛋\n苹果", "append keeps existing notebook content");
            Check((await Run("note.list", new { query = "购物" }, "看看购物笔记")).Text.Contains("鸡蛋"), "note read returns actual stored content");
            await Run("note.add", new { title = "购物清单周末", body = "苹果" }, "新增笔记");
            Check(!(await Run("note.update", new { query = "购物", body = "覆盖" }, "修改购物笔记")).Ok && store.Data.Notes.Last().Body == "苹果", "ambiguous mutation rejected without changes");
            await Run("note.archive", new { query = note.Id.ToString() }, "删除这条笔记");
            Check(store.Data.Notes.Single(n => n.Id == note.Id).Archived && new Store(root).Data.Notes.Count == 3, "delete archives recoverable note");
            int count = store.Data.Notes.Count;
            Check(!(await Run("note.add", new { title = "坏的", body = "test" }, "如果我让你添加笔记")).Ok && store.Data.Notes.Count == count, "hypothetical request cannot mutate notes");
            Directory.CreateDirectory(Path.Combine(root, "state.json.tmp"));
            Check(!(await Run("note.add", new { title = "不能保存", body = "失败" }, "新增笔记")).Ok && store.Data.Notes.Count == count, "disk save failure rolls back in-memory notes");
            Directory.Delete(Path.Combine(root, "state.json.tmp"));
            store.Data.LocalModel = true;
            await tools.Execute(tools.Quick("打开小本本"), "打开小本本", Guid.NewGuid(), default);
            Check(opened == "memory", "local model mode can still open local tools");
            Check(!(await Run("memo.add", new { title = "开会", due = "" }, "提醒我开会")).Ok && store.Data.Memos.Count == 0, "missing reminder time does not create a fabricated deadline");
            Check(!(await Run("memo.add", new { title = "开会", due = DateTimeOffset.Now.AddDays(1).ToString("O") }, "提醒我开会")).Ok, "model cannot invent an unrequested reminder time");
            tools.FinishTurn("提醒我开会", "请问几点提醒？", []);
            await Run("memo.add", new { title = "开会", due = DateTimeOffset.Now.AddDays(1).ToString("O") }, "明天上午九点");
            Check(store.Data.Memos.Count == 1, "time clarification retains the reminder request");
            store.Data.History.AddRange([new("user", "帮我记录一下，12点要去午睡"), new("assistant", "已保存笔记：12点要去午睡")]);
            Check(tools.EffectiveInput("这个要加到备忘录里").Contains("12点要去午睡"), "exact reported note-to-reminder wording retains previous user content");
            tools.FinishTurn("备忘录里记一下，12点要去污水", "是想记午睡，对吗？污水是不是手滑？", []);
            Check(tools.EffectiveInput("午睡").Contains("12点") && tools.EffectiveInput("不是污水，是午睡").Contains("12点"), "noun-only and explicit corrections keep original reminder time");
            Check(tools.EffectiveInput("不要了") == "不要了" && tools.EffectiveInput("打开信箱") == "打开信箱", "negative and unrelated commands cannot inherit a reminder");
            Check(!(await Run("mail.send", new { id = Guid.NewGuid().ToString() }, "是的")).Ok && transports == 0, "reminder clarification cannot grant permission to send a letter");
            tools.FinishTurn("今天天气不错", "嗯嗯", []);
            Check(tools.EffectiveInput("午睡") == "午睡", "topic change ends the pending clarification");
            tools.FinishTurn("提醒我开会", "请问几点提醒？", []);
            store.Data.PendingReminder!.Expires = DateTimeOffset.Now.AddMinutes(-1);
            Check(tools.EffectiveInput("明天九点") == "明天九点", "expired reminder context is not reused");
            store.Data.PendingReminder = null;
            Check(ConversationTools.Authorized("memo.add", "明天10:00提醒我开会"), "clock colon does not truncate the instruction");
            await Run("memo.update", new { query = "开会", due = DateTimeOffset.Now.AddDays(2).ToString("O") }, "把开会提醒改到后天九点");
            await Run("memo.complete", new { query = "开会" }, "开会完成了");
            Check(new Store(root).Data.Memos[0].Done, "reminder update and completion persist");
            store.Data.Mail.PeerID = "isolated-test-peer"; store.Data.Mail.Enabled = true;
            await Run("mail.draft", new { body = "晚上好" }, "帮我写封信");
            string draft = store.Data.Mail.Draft!.Id;
            Check(store.Data.Mail.Entries.Count == 0 && transports == 0, "draft is persisted without transmitting");
            Check(!(await Run("mail.send", new { id = draft }, "不要寄出这封信")).Ok && transports == 0, "negative send request never transmits");
            Check(!(await Run("mail.send", new { id = draft }, "这封信寄出去了吗？")).Ok && transports == 0, "delivery-status question is not sending consent");
            var sent = await Run("mail.send", new { id = draft }, "寄出这封信");
            Check(sent.Ok && sent.Text.Contains("尚未送达") && store.Data.Mail.Entries.Count == 1, "queued is reported separately from delivered");
            delivered = true;
            await Run("mail.send", new { id = draft }, "寄出这封信");
            Check(store.Data.Mail.Entries.Count == 1 && store.Data.Mail.Entries[0].Delivered, "send retry reuses letter ID instead of duplicating mail");
            var sameTurn = await tools.Execute([ConversationTools.Call("mail.draft", new { body = "新内容" }), ConversationTools.Call("mail.send", new { id = draft })], "写封信并寄出", Guid.NewGuid(), default);
            Check(!sameTurn.Last().Ok && store.Data.Mail.Entries.Count == 1, "cannot compose a new draft and send it before review in one turn");
            draft = store.Data.Mail.Draft!.Id; store.Data.Mail.PeerID = "different-peer";
            Check(!(await Run("mail.send", new { id = draft }, "寄出这封信")).Ok, "changed recipient invalidates draft send");
            bool invalid = false; try { ConversationTools.Parse("{\"tools\":[{\"name\":\"note.add\",\"args\":{}},{\"name\":\"shell.exec\",\"args\":{}}]}"); } catch (InvalidOperationException) { invalid = true; }
            Check(invalid, "unknown tool rejects whole plan before any effects");
            using var canceled = new CancellationTokenSource(); canceled.Cancel();
            bool stopped = false; try { await tools.Execute([ConversationTools.Call("note.add", new { body = "cancel" })], "新增笔记", Guid.NewGuid(), canceled.Token); } catch (OperationCanceledException) { stopped = true; }
            Check(stopped && store.Data.Notes.Count == count, "cancellation before execution leaves notes unchanged");
            Check(ActionLanguage.LocalPlan("不要睡觉，挥挥手")!.Actions.SequenceEqual(new[] { "wave" }), "negative sleep clause does not suppress positive wave");
            Check(ActionLanguage.LocalPlan("别睡了，起来挥挥手")!.Actions.SequenceEqual(new[] { "idle", "wave" }), "wake then wave preserves ordering");
            Check(ActionLanguage.LocalPlan("先挥手，再转圈，最后睡觉")!.Actions.SequenceEqual(new[] { "wave", "spin", "sleep" }), "three action request is recognized locally");
            Check(ActionLanguage.LocalPlan("噜噜，你能不能给我打个滚呀")!.Actions.SequenceEqual(new[] { "roll" }), "natural command prefixes recognized without a model");
            Check(ActionLanguage.LocalPlan("讲个挥手的故事") is null, "story never becomes a local action");
            var parsed = ConversationBehavior.Parse("{\"text\":\"好\",\"emotion\":\"neutral\",\"actions\":[\"idle\",\"wave\"],\"intent\":\"request\"}", "别睡了，起来挥手");
            Check(parsed.Actions.SequenceEqual(new[] { "idle", "wave" }), "model parser also preserves wake and subsequent action");
            lines.Add("No real model requests, accounts or mail transport were used."); return 0;
        }
        catch (Exception e) { lines.Add("FAIL " + e); return 1; }
        finally { File.WriteAllLines(Path.Combine(AppContext.BaseDirectory, "toolcheck-results.txt"), lines); if (Directory.Exists(root)) Directory.Delete(root, true); }
    }
}
