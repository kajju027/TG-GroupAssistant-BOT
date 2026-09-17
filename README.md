# 🤖 Telegram Group Moderation Bot

একটা full-featured Telegram গ্রুপ moderation বট — antispam, antilink, antiword, warn, mute, kick, ban, welcome message, custom filters, এবং আরও অনেক কিছু।

এই বটের architecture **Levanter** / **Raganork** স্টাইলে বানানো: এই repo-তে বটের সব কোড থাকে, আর হোস্টিং প্যানেলে শুধু একটা ছোট `index.py` লোডার ফাইল রাখা হয় যেটা প্রতিবার বট চালু হওয়ার সময় এই repo থেকে সবশেষ কোড টেনে এনে চালায়। তাই কোড আপডেট করতে প্যানেলে হাত দেওয়ার দরকার নেই — শুধু GitHub-এ push করে বট restart করলেই হয়।

## 🚀 নিজের বট বানাতে চান? (Fork করে ব্যবহার করুন)

এই repo যে কেউ fork করে নিজের bot বানাতে পারবেন। লাগবে:

1. **এই repo fork করুন** (উপরে ডানদিকে "Fork" বাটনে চাপুন) — এটা আপনার নিজের GitHub অ্যাকাউন্টে একটা কপি বানাবে।
2. একটা **হোস্টিং প্যানেল** (যেকোনো Python-সাপোর্টেড প্যানেল/VPS)।
3. [`@BotFather`](https://t.me/BotFather) থেকে একটা **Bot Token**।
4. [`@userinfobot`](https://t.me/userinfobot) থেকে আপনার **Telegram User ID**।

তারপর প্যানেলে শুধু `index.py` ফাইলটা বসাতে হবে এবং Environment Variables-এ আপনার নিজের `GITHUB_REPO` (আপনার forked repo, যেমন `yourname/yourrepo`) বসাতে হবে। ব্যাস, আপনার নিজস্ব বট চালু হয়ে যাবে — মূল repo-র কোনো কিছু বদলাতে হবে না।

## 📁 Folder Structure

```
bot/
├── core/
│   ├── config.py      # env variable পড়া ও validate করা
│   └── logger.py       # রঙিন কনসোল লগার
├── handlers/            # প্রতিটা কমান্ড/ফিচার আলাদা ফাইলে
│   ├── start.py
│   ├── settings.py
│   ├── warn.py
│   ├── mute.py
│   ├── tag.py
│   ├── welcome.py
│   ├── antifake.py
│   ├── antilink.py
│   ├── antiword.py
│   ├── antispam.py
│   └── filters.py
├── middlewares/
│   └── admin_check.py   # admin কিনা চেক করার middleware
├── utils/
│   └── helpers.py       # সাধারণ helper ফাংশন
├── database.py          # SQLite ডাটাবেস লজিক
└── main.py              # সব router জোড়া দিয়ে বট চালায়

requirements.txt
```

## ✨ ফিচারসমূহ

| কমান্ড | কাজ |
|---|---|
| `/start` | বট চালু আছে কিনা যাচাই, DM-এ সেটিংস প্যানেল |
| `/settings` | গ্রুপের সব সেটিংস ইনলাইন বাটনে দেখা ও বদলানো |
| `/warn`, `/mute`, `/kick`, `/ban` | মডারেশন কমান্ড |
| `/antispam`, `/antilink`, `/antiword` | অটো-মডারেশন টগল ও কনফিগার |
| `/filter` | নিজের কাস্টম কীওয়ার্ড-রিপ্লাই বানানো |
| Welcome message | নতুন মেম্বার জয়েন করলে স্বয়ংক্রিয় শুভেচ্ছা |
| Antifake | ফেক/সন্দেহজনক অ্যাকাউন্ট শনাক্তকরণ |

## 🔧 Environment Variables (প্যানেলে সেট করতে হবে, এই repo-তে না)

| Variable | কী জন্য | বাধ্যতামূলক |
|---|---|---|
| `BOT_TOKEN` | @BotFather থেকে পাওয়া টোকেন | ✅ |
| `OWNER_ID` | আপনার টেলিগ্রাম ইউজার আইডি (সংখ্যা) | ✅ |
| `GITHUB_REPO` | আপনার forked repo, `username/repo-name` ফরম্যাটে | ✅ |
| `GITHUB_BRANCH` | ব্রাঞ্চের নাম | ঐচ্ছিক, ডিফল্ট `main` |
| `DB_PATH` | ডাটাবেস ফাইলের নাম/পাথ | ঐচ্ছিক, ডিফল্ট `bot.db` |

এই repo নিজে কোনো `.env` বা টোকেন বহন করে না — সব environment variable প্যানেলের `index.py` লোডারের মাধ্যমে আসে, এবং ডাটাবেস ফাইল সবসময় আপনার **প্যানেলে** থাকে (এই repo-তে বা GitHub-এ কখনো যায় না)।

## ➕ নতুন ফিচার যোগ করবেন কীভাবে

1. `bot/handlers/` এ একটা নতুন `.py` ফাইল বানান, `router = Router()` দিয়ে শুরু করুন।
2. `bot/main.py`-তে সেটাকে import করে `dp.include_router(...)` দিয়ে যোগ করুন।
3. **গুরুত্বপূর্ণ:** হ্যান্ডলার যদি সব মেসেজ/টেক্সট ধরে ("catch-all" ধরনের), সেটাকে কমান্ড-ভিত্তিক রাউটারগুলোর **পরে** রেজিস্টার করুন এবং `~F.text.startswith("/")` ফিল্টার দিন — নাহলে সেটা অন্য সব কমান্ড আটকে দেবে।
4. GitHub এ push করুন — প্যানেলে বট restart করলেই নতুন কোড চলে আসবে, `index.py`-তে হাত দেওয়ার দরকার নেই।

## 🧪 লোকালি টেস্ট করতে চাইলে

```bash
pip install -r requirements.txt
export BOT_TOKEN="your_token"
export OWNER_ID="your_id"
python -m bot.main
```

## 📜 License

স্বাধীনভাবে ব্যবহার, পরিবর্তন ও fork করার জন্য উন্মুক্ত। কৃতিত্ব দিলে ভালো লাগবে, বাধ্যতামূলক নয়।
