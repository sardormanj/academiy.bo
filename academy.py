import asyncio
import html
import logging

import aiosqlite
from aiogram import Bot, Dispatcher, F, types
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import InlineKeyboardBuilder

# ==========================================
# 1. SOZLAMALAR
# ==========================================
# DIQQAT: Bu token ochiq kodda turibdi. Uni hech kimga ko'rsatmang va
# GitHub kabi ochiq joylarga yuklamang. Agar oshkor bo'lib qolsa,
# @BotFather'da /revoke buyrug'i bilan darhol bekor qiling va yangisini oling.
BOT_TOKEN = "7755178226:AAEarmEOImLIrAlmqOFHF1GKWVj164HpyuU"
DB_PATH = "academy_all_in_one.db"
SEARCH_RESULT_LIMIT = 8

# Admin(lar) Telegram ID raqami shu yerga qo'shiladi — faqat shu ID'lar /add
# buyrug'idan foydalana oladi. O'z ID'ingizni bilish uchun botga /myid yozing.
ADMIN_IDS: set[int] = {
    # 123456789,  # <-- shu yerga o'z ID'ingizni yozing (# belgisini olib tashlang)
}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Kategoriya nomiga mos emoji (ro'yxatda bo'lmasa standart belgi ishlatiladi)
CATEGORY_ICONS = {
    "Python": "🐍",
    "Linux": "🐧",
    "Windows": "🪟",
    "Tarmoq asoslari": "🌐",
    "Kiberxavfsizlik": "🛡️",
    "Git va GitHub": "🔧",
    "Ma'lumotlar bazasi (SQL)": "🗄️",
    "Veb-dasturlash": "🌍",
    "Kompyuter asoslari": "💻",
}
DEFAULT_ICON = "📘"

SEP = "\x1f"  # callback_data ichida maydonlarni ajratish uchun ko'rinmas belgi


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


# ==========================================
# 2. DARSLAR BAZASI (namuna ma'lumotlar)
# ==========================================
SAMPLE_DATA = [
    # ---------------- PYTHON ----------------
    ("Python", "Asoslar", "O'zgaruvchilar va turlar", 'ism = "Umar"\nyosh = 20\nboyi = 1.75',
     "O'zgaruvchi — ma'lumotni xotirada saqlaydigan konteyner. Python turini avtomatik "
     "aniqlaydi: matn (str), butun son (int), kasr son (float), mantiqiy (bool).",
     "ism = 'Umar'\nyosh = 20\nprint(f'{ism} {yosh} yoshda')  # Umar 20 yoshda"),

    ("Python", "Asoslar", "if / else shartli operator", "if shart:\n    ...\nelse:\n    ...",
     "Ma'lum shart to'g'ri (True) yoki noto'g'ri (False) bo'lishiga qarab kodning turli "
     "qismlarini ishga tushiradi.",
     "yosh = 17\nif yosh >= 18:\n    print('Kattasiz')\nelse:\n    print('Kichiksiz')"),

    ("Python", "Asoslar", "for sikli", "for i in range(5):\n    ...",
     "Ro'yxat, satr yoki range() kabi to'plam elementlari bo'ylab kodni qayta-qayta "
     "bajarish uchun ishlatiladi.",
     "for i in range(3):\n    print(i)\n# 0, 1, 2 chiqadi"),

    ("Python", "Asoslar", "while sikli", "while shart:\n    ...",
     "Shart to'g'ri bo'lib turgan ekan kod blokini takrorlab bajaradi. Cheksiz siklga "
     "aylanmasligi uchun shart ichida o'zgaruvchini yangilab turish kerak.",
     "son = 0\nwhile son < 3:\n    print(son)\n    son += 1"),

    ("Python", "Asoslar", "Kiritish va chiqarish (input/print)", "ism = input('Ismingiz: ')",
     "input() foydalanuvchidan matn qabul qiladi (har doim str turida), print() esa "
     "ekranga natija chiqaradi.",
     "ism = input('Ismingiz: ')\nprint(f'Salom, {ism}!')"),

    ("Python", "Ma'lumot turlari", "Ro'yxatlar (list)", "royxat = [1, 2, 3]",
     "Tartiblangan va o'zgartirilishi mumkin bo'lgan elementlar to'plami. Indeks orqali "
     "murojaat qilinadi (0 dan boshlanadi).",
     "mevalar = ['olma', 'nok', 'uzum']\nmevalar.append('anor')\nprint(mevalar[0])  # olma"),

    ("Python", "Ma'lumot turlari", "Kortejlar (tuple)", "kortej = (1, 2, 3)",
     "Ro'yxatga o'xshaydi, lekin yaratilgandan so'ng o'zgartirib bo'lmaydi (immutable). "
     "O'zgarmas ma'lumotlar uchun ishlatiladi.",
     "koordinata = (41.3, 69.2)\nprint(koordinata[0])  # 41.3"),

    ("Python", "Ma'lumot turlari", "Lug'atlar (dictionary)", 'lugat = {"kalit": "qiymat"}',
     "Kalit-qiymat juftliklaridan iborat, tartiblanmagan va o'zgartirilishi mumkin bo'lgan "
     "ma'lumot turi.",
     "talaba = {'ism': 'Ali', 'kurs': 3}\nprint(talaba['ism'])  # Ali"),

    ("Python", "Ma'lumot turlari", "To'plamlar (set)", "toplam = {1, 2, 3}",
     "Faqat takrorlanmaydigan elementlarni saqlaydigan tartiblanmagan to'plam. Dublikatlarni "
     "olib tashlash uchun qulay.",
     "royxat = [1, 2, 2, 3, 3]\nprint(set(royxat))  # {1, 2, 3}"),

    ("Python", "Ma'lumot turlari", "List comprehension", "[ifoda for x in royxat]",
     "Ro'yxatlarni bitta qatorda, qisqa va o'qilishi oson tarzda yaratish usuli.",
     "kvadratlar = [x**2 for x in range(5)]\nprint(kvadratlar)  # [0, 1, 4, 9, 16]"),

    ("Python", "Funksiyalar", "Funksiya yaratish (def)", "def salom(ism):\n    return ...",
     "Qayta-qayta ishlatiladigan kod blokini bitta nom ostida jamlaydi. Kodni takrorlashdan "
     "saqlaydi va o'qishni osonlashtiradi.",
     "def salom(ism):\n    return f'Salom, {ism}!'\nprint(salom('Dilnoza'))"),

    ("Python", "Funksiyalar", "Standart va nomli argumentlar", "def f(x, y=10):",
     "Funksiya parametrlariga standart qiymat berish mumkin; chaqirishda argumentni nom "
     "bilan ham uzatish mumkin.",
     "def daraja(son, ko_paytir=2):\n    return son ** ko_paytir\nprint(daraja(3))  # 9"),

    ("Python", "Funksiyalar", "Lambda funksiyalar", "kvadrat = lambda x: x**2",
     "Bir qatorli, nomsiz kichik funksiyalar. Ko'pincha map(), filter(), sorted() bilan "
     "birga ishlatiladi.",
     "kvadrat = lambda x: x * x\nprint(kvadrat(5))  # 25"),

    ("Python", "Fayllar bilan ishlash", "Faylni o'qish", "with open('f.txt') as f:",
     "'with' operatori bilan faylni ochish uni ishlatib bo'lgach avtomatik yopilishini "
     "kafolatlaydi — bu eng xavfsiz usul.",
     "with open('malumot.txt', 'r') as f:\n    matn = f.read()\nprint(matn)"),

    ("Python", "Fayllar bilan ishlash", "Faylga yozish", "with open('f.txt', 'w') as f:",
     "'w' rejimi faylni yozish uchun ochadi (mavjud bo'lsa tarkibini o'chiradi), 'a' rejimi "
     "esa oxiriga qo'shib yozadi.",
     "with open('log.txt', 'a') as f:\n    f.write('Yangi qator\\n')"),

    ("Python", "Xatoliklar (Exception)", "try / except", "try:\n    ...\nexcept Xato:\n    ...",
     "Kod bajarilishi vaqtida yuzaga kelishi mumkin bo'lgan xatoliklarni ushlab, dastur "
     "to'xtab qolishining oldini oladi.",
     "try:\n    natija = 10 / 0\nexcept ZeroDivisionError:\n    print('Nolga bo'lib bo'lmaydi')"),

    ("Python", "Xatoliklar (Exception)", "O'z xatoligini chaqirish (raise)", "raise ValueError('...')",
     "Muayyan shartda dasturchi o'zi xatolik hosil qilib, uni yuqoriga uzatishi mumkin.",
     "def yosh_tekshir(yosh):\n    if yosh < 0:\n        raise ValueError('Yosh manfiy bo'lolmaydi')"),

    ("Python", "OOP - Klasslar", "Class va Object", "class Odam:\n    ...",
     "Klass — obyektlarni yaratish uchun andoza (shablon). Obyekt esa shu klassdan "
     "yaratilgan aniq nusxa.",
     "class Odam:\n    def salom(self):\n        print('Salom!')\n\no = Odam()\no.salom()"),

    ("Python", "OOP - Klasslar", "__init__ konstruktor", "def __init__(self, ism):",
     "Obyekt yaratilganda avtomatik chaqiriladigan maxsus metod; boshlang'ich "
     "qiymatlarni (atributlarni) belgilash uchun ishlatiladi.",
     "class Odam:\n    def __init__(self, ism):\n        self.ism = ism\n\no = Odam('Ali')\nprint(o.ism)"),

    ("Python", "OOP - Klasslar", "Meros olish (inheritance)", "class Bola(Ota):",
     "Bir klass boshqa klassning xususiyat va metodlarini meros qilib olishi, kodni qayta "
     "ishlatishni osonlashtiradi.",
     "class Hayvon:\n    def ovoz(self):\n        print('...')\n\nclass Mushuk(Hayvon):\n    def ovoz(self):\n        print('Miyov')"),

    ("Python", "Modullar va kutubxonalar", "import va modullar", "import math",
     "Boshqa fayl yoki kutubxonadagi tayyor funksiyalarni joriy faylga ulash imkonini "
     "beradi.",
     "import math\nprint(math.sqrt(16))  # 4.0"),

    ("Python", "Modullar va kutubxonalar", "pip bilan kutubxona o'rnatish", "pip install nomi",
     "PyPI omboridan tashqi kutubxonalarni (masalan, aiogram, requests) o'rnatish uchun "
     "ishlatiladigan buyruq.",
     "pip install requests\n# Endi 'import requests' qilish mumkin"),

    ("Python", "Modullar va kutubxonalar", "Virtual muhit (venv)", "python -m venv venv",
     "Har bir loyiha uchun alohida, izolyatsiya qilingan Python muhiti yaratadi — "
     "kutubxonalar to'qnashuvining oldini oladi.",
     "python -m venv venv\nsource venv/bin/activate  # Linux/macOS\nvenv\\Scripts\\activate  # Windows"),

    # ---------------- LINUX ----------------
    ("Linux", "Fayl tizimi", "Fayllar ro'yxati (ls)", "ls -la",
     "Joriy papkadagi barcha fayllarni (yashirin fayllar bilan birga) ruxsatlar, egasi va "
     "hajmi bilan batafsil ko'rsatadi.",
     "ls -la /home\n# Uy papkadagi barcha fayllar ro'yxati chiqadi"),

    ("Linux", "Fayl tizimi", "Joriy joylashuv (pwd)", "pwd",
     "Terminalda hozir turgan to'liq papka manzilini (path) ko'rsatadi.",
     "pwd\n# /home/sardor kabi natija chiqaradi"),

    ("Linux", "Fayl tizimi", "Papkaga o'tish (cd)", "cd /path/to/dir",
     "Terminal orqali boshqa papkaga o'tish uchun ishlatiladi. 'cd ..' bir papka yuqoriga "
     "chiqaradi.",
     "cd Documents\ncd ..  # bir bosqich orqaga qaytadi"),

    ("Linux", "Fayl tizimi", "Papka yaratish (mkdir)", "mkdir yangi_papka",
     "Joriy joylashuvda yangi katalog (papka) ochadi. '-p' bayrog'i bilan ichma-ich "
     "papkalar ham yaratiladi.",
     "mkdir -p loyiha/src/utils"),

    ("Linux", "Fayl tizimi", "Fayl/papka o'chirish (rm)", "rm -rf papka_nomi",
     "Faylni o'chiradi; '-r' papka ichidagilar bilan, '-f' esa tasdiqlamasdan o'chiradi. "
     "Juda ehtiyot bo'lib ishlatilishi kerak — qaytarib bo'lmaydi.",
     "rm eski.txt\nrm -rf vaqtinchalik_papka"),

    ("Linux", "Fayl tizimi", "Nusxa olish (cp)", "cp manba maqsad",
     "Fayl yoki papkadan nusxa ko'chiradi. Papkani nusxalash uchun '-r' bayrog'i kerak.",
     "cp hisobot.txt zaxira.txt\ncp -r loyiha loyiha_zaxira"),

    ("Linux", "Fayl tizimi", "Ko'chirish/nomlash (mv)", "mv manba maqsad",
     "Fayl yoki papkani boshqa joyga ko'chiradi yoki nomini o'zgartiradi.",
     "mv eski_nom.txt yangi_nom.txt"),

    ("Linux", "Fayl tizimi", "Fayl mazmunini ko'rish (cat)", "cat fayl.txt",
     "Fayl tarkibini to'g'ridan-to'g'ri terminalga chiqaradi. Katta fayllar uchun 'less' "
     "qulayroq.",
     "cat /etc/os-release\n# Tizim versiyasi haqida ma'lumot chiqaradi"),

    ("Linux", "Ruxsatlar", "Ruxsatlarni o'zgartirish (chmod)", "chmod 755 fayl.sh",
     "Fayl yoki papkaga o'qish/yozish/bajarish ruxsatlarini belgilaydi. Raqamlar: "
     "4=o'qish, 2=yozish, 1=bajarish.",
     "chmod +x skript.sh  # skriptni bajariladigan qiladi"),

    ("Linux", "Ruxsatlar", "Egasini o'zgartirish (chown)", "chown user:group fayl",
     "Fayl yoki papkaning egasi va guruhini belgilaydi. Odatda administrator (sudo) "
     "huquqi talab qiladi.",
     "sudo chown sardor:sardor loyiha.txt"),

    ("Linux", "Jarayonlar", "Jarayonlar ro'yxati (ps)", "ps aux",
     "Tizimda hozir ishlayotgan barcha jarayonlarni (process) PID, CPU va xotira "
     "sarfi bilan ko'rsatadi.",
     "ps aux | grep python  # faqat python jarayonlarini ko'rsatadi"),

    ("Linux", "Jarayonlar", "Real vaqt monitoringi (top)", "top",
     "CPU va xotiradan eng ko'p foydalanayotgan jarayonlarni real vaqt rejimida "
     "ko'rsatadi. Chiqish uchun 'q' bosiladi.",
     "top\n# Interaktiv monitoring oynasi ochiladi"),

    ("Linux", "Jarayonlar", "Jarayonni to'xtatish (kill)", "kill -9 PID",
     "Berilgan PID (jarayon raqami) bo'yicha ishlayotgan dasturni majburan yopadi.",
     "kill -9 4521  # 4521 PID raqamli jarayonni to'xtatadi"),

    ("Linux", "Tarmoq", "Ping", "ping -c 4 google.com",
     "Maqsadli host bilan tarmoq aloqasi mavjudligini va javob vaqtini (latency) "
     "tekshiradi.",
     "ping -c 4 8.8.8.8  # Google DNS serveriga 4 ta so'rov yuboradi"),

    ("Linux", "Tarmoq", "IP manzilni ko'rish (ip a)", "ip a",
     "Kompyuterdagi tarmoq interfeyslari va ularga tegishli IP manzillarni ko'rsatadi "
     "(eski buyruq — ifconfig).",
     "ip a\n# eth0, wlan0 kabi interfeyslar va IP manzillari chiqadi"),

    ("Linux", "Tarmoq", "Masofaviy ulanish (ssh)", "ssh user@ip_manzil",
     "Boshqa kompyuter yoki serverga xavfsiz shifrlangan terminal orqali masofadan "
     "ulanish uchun ishlatiladi.",
     "ssh sardor@192.168.1.10\n# Parol so'ralib, ulanish o'rnatiladi"),

    ("Linux", "Tarmoq", "Port skaneri (nmap)", "nmap -sV 192.168.1.1",
     "Maqsadli qurilmadagi ochiq portlarni va ularda ishlayotgan xizmatlar versiyasini "
     "aniqlaydi. Faqat o'zingizga tegishli yoki ruxsat berilgan tarmoqda ishlating.",
     "nmap -sV 192.168.1.1\n# Ochiq portlar va xizmatlar ro'yxati chiqadi"),

    ("Linux", "Paket boshqaruvi", "Paketlarni yangilash (apt)", "sudo apt update && sudo apt upgrade",
     "Debian/Ubuntu/Kali tizimlarida mavjud paketlar ro'yxatini yangilaydi va "
     "o'rnatilganlarini so'nggi versiyaga ko'taradi.",
     "sudo apt update\nsudo apt upgrade -y"),

    ("Linux", "Paket boshqaruvi", "Dastur o'rnatish (apt install)", "sudo apt install nomi",
     "Rasmiy omborlardan yangi dastur yoki paket o'rnatish uchun ishlatiladi.",
     "sudo apt install git\n# Git dasturi o'rnatiladi"),

    ("Linux", "Foydalanuvchilar", "Administrator huquqi (sudo)", "sudo buyruq",
     "Oddiy foydalanuvchi nomidan vaqtincha administrator (root) huquqi bilan buyruq "
     "bajarish imkonini beradi.",
     "sudo apt install htop\n# Parol so'raladi, so'ng buyruq root huquqida bajariladi"),

    ("Linux", "Foydalanuvchilar", "Yangi foydalanuvchi qo'shish (adduser)", "sudo adduser ism",
     "Tizimga yangi foydalanuvchi hisobini interaktiv tarzda qo'shadi (parol, ism kabi "
     "ma'lumotlarni so'raydi).",
     "sudo adduser dilnoza"),

    # ---------------- WINDOWS ----------------
    ("Windows", "CMD buyruqlari", "Papka tarkibi (dir)", "dir",
     "Joriy papkadagi fayl va papkalar ro'yxatini ko'rsatadi (Linuxdagi 'ls' analogi).",
     "dir C:\\Users\n# Users papkasidagi fayllar ro'yxati chiqadi"),

    ("Windows", "CMD buyruqlari", "Papkaga o'tish (cd)", "cd C:\\path",
     "Buyruqlar satrida boshqa papkaga o'tish uchun ishlatiladi.",
     "cd C:\\Users\\Sardor\\Documents"),

    ("Windows", "CMD buyruqlari", "Papka yaratish (mkdir)", "mkdir YangiPapka",
     "Joriy joylashuvda yangi papka yaratadi.",
     "mkdir Loyihalar"),

    ("Windows", "CMD buyruqlari", "Fayl o'chirish (del)", "del fayl.txt",
     "Berilgan faylni o'chiradi. Papkani o'chirish uchun 'rmdir /s' ishlatiladi.",
     "del eski.txt"),

    ("Windows", "CMD buyruqlari", "Nusxa olish (copy)", "copy manba maqsad",
     "Faylning nusxasini boshqa joyga yoki nom bilan ko'chiradi.",
     "copy hisobot.txt zaxira.txt"),

    ("Windows", "CMD buyruqlari", "Tarmoq sozlamalari (ipconfig)", "ipconfig",
     "Kompyuterning IP manzili, tarmoq maskasi va shlyuz kabi tarmoq sozlamalarini "
     "ko'rsatadi.",
     "ipconfig /all\n# Barcha tarmoq adapterlari haqida to'liq ma'lumot chiqadi"),

    ("Windows", "CMD buyruqlari", "Ping", "ping google.com",
     "Maqsadli host bilan tarmoq aloqasini va javob vaqtini tekshiradi.",
     "ping 8.8.8.8"),

    ("Windows", "CMD buyruqlari", "Jarayonlar ro'yxati (tasklist)", "tasklist",
     "Windows tizimida hozir ishlayotgan barcha dasturlar (jarayonlar) ro'yxatini "
     "ko'rsatadi.",
     "tasklist | findstr chrome\n# Faqat chrome jarayonlarini ko'rsatadi"),

    ("Windows", "CMD buyruqlari", "Jarayonni yopish (taskkill)", "taskkill /PID raqam /F",
     "Berilgan PID (yoki nom) bo'yicha ishlayotgan dasturni majburan to'xtatadi.",
     "taskkill /IM notepad.exe /F"),

    ("Windows", "PowerShell", "Jarayonlarni ko'rish (Get-Process)", "Get-Process",
     "PowerShell'da ishlayotgan barcha jarayonlarni CPU va xotira sarfi bilan "
     "ko'rsatadi.",
     "Get-Process | Sort-Object CPU -Descending | Select-Object -First 5"),

    ("Windows", "PowerShell", "Papka tarkibi (Get-ChildItem)", "Get-ChildItem",
     "Joriy papkadagi fayl va papkalarni ko'rsatadi ('ls' yoki 'dir' analogi, "
     "qisqartmasi — 'gci' yoki 'ls').",
     "Get-ChildItem C:\\Projects -Recurse"),

    ("Windows", "PowerShell", "Xizmatlarni ko'rish (Get-Service)", "Get-Service",
     "Windows tizim xizmatlarining (service) holatini — ishlayapti yoki to'xtagan — "
     "ko'rsatadi.",
     "Get-Service | Where-Object {$_.Status -eq 'Running'}"),

    ("Windows", "PowerShell", "Skript ishga tushirish siyosati", "Set-ExecutionPolicy RemoteSigned",
     "PowerShell skriptlarini (.ps1) ishga tushirishga ruxsat siyosatini belgilaydi. "
     "Standart holatda xavfsizlik uchun cheklangan bo'ladi.",
     "Set-ExecutionPolicy RemoteSigned -Scope CurrentUser"),

    # ---------------- TARMOQ ASOSLARI ----------------
    ("Tarmoq asoslari", "Asosiy tushunchalar", "IP manzil nima", "192.168.1.1",
     "Har bir tarmoqdagi qurilmaga beriladigan noyob raqamli manzil. IPv4 (masalan "
     "192.168.1.1) va IPv6 turlari mavjud.",
     "192.168.1.1 — mahalliy tarmoqdagi router manzili bo'lishi mumkin."),

    ("Tarmoq asoslari", "Asosiy tushunchalar", "Subnet mask", "255.255.255.0",
     "Tarmoq va qurilma qismini ajratib beradi; qaysi qurilmalar bir tarmoqda "
     "ekanini aniqlashga yordam beradi.",
     "255.255.255.0 — 256 ta manzilgacha (masalan 192.168.1.0-255) tarmoqni bildiradi."),

    ("Tarmoq asoslari", "Asosiy tushunchalar", "DNS nima", "nslookup google.com",
     "Domen nomlarini (google.com) IP manzilga aylantiruvchi 'internet telefon "
     "kitobi'. Foydalanuvchi uchun raqamlarni eslab qolishni shart qilmaydi.",
     "nslookup google.com\n# Google serverining IP manzilini ko'rsatadi"),

    ("Tarmoq asoslari", "Asosiy tushunchalar", "DHCP nima", "-",
     "Tarmoqqa ulangan qurilmalarga IP manzilni avtomatik tarzda beradigan xizmat — "
     "har bir qurilmaga qo'lda manzil kiritish shart emas.",
     "Uyingizdagi router odatda DHCP orqali telefon va noutbukka avtomatik IP beradi."),

    ("Tarmoq asoslari", "Asosiy tushunchalar", "MAC manzil", "AA:BB:CC:11:22:33",
     "Tarmoq kartasiga ishlab chiqaruvchi tomonidan beriladigan noyob jismoniy "
     "manzil, IP manzildan farqli o'laroq odatda o'zgarmaydi.",
     "getmac (Windows) yoki ip link (Linux) buyrug'i orqali ko'rish mumkin."),

    ("Tarmoq asoslari", "Asosiy tushunchalar", "Port nima", "80, 443, 22",
     "Bitta IP manzilda bir nechta xizmat ishlashi uchun ishlatiladigan raqamli "
     "'eshik'. Masalan 80-port — HTTP, 443 — HTTPS, 22 — SSH.",
     "https://sayt.com odatda 443-portda ishlaydi."),

    ("Tarmoq asoslari", "Asosiy tushunchalar", "TCP va UDP farqi", "-",
     "TCP — ma'lumot yetkazilishini kafolatlaydigan, tartibli protokol (masalan veb "
     "sahifalar). UDP — tezroq, lekin kafolatsiz protokol (masalan video oqim, o'yinlar).",
     "Veb-sayt ochish — TCP; video qo'ng'iroq — ko'pincha UDP ishlatadi."),

    ("Tarmoq asoslari", "Asosiy tushunchalar", "OSI modeli (qisqacha)", "-",
     "Tarmoq aloqasini 7 qatlamga bo'lib tushuntiruvchi nazariy model: Fizik, Kanal, "
     "Tarmoq, Transport, Sessiya, Taqdimot, Ilova. Muammoni topishda yordam beradi.",
     "Internet ishlamasa: kabel (Fizik) → IP sozlamasi (Tarmoq) → dastur (Ilova) tartibida tekshiriladi."),

    ("Tarmoq asoslari", "Diagnostika", "Marshrutni kuzatish (tracert/traceroute)", "tracert google.com",
     "Ma'lumot manba serverga yetguncha qaysi tarmoq nuqtalari (router) orqali "
     "o'tishini ko'rsatadi. Windows'da 'tracert', Linux'da 'traceroute'.",
     "tracert google.com\n# Har bir 'hop' (router) va javob vaqti chiqadi"),

    ("Tarmoq asoslari", "Diagnostika", "Faol ulanishlar (netstat)", "netstat -an",
     "Kompyuterdagi barcha faol tarmoq ulanishlari va tinglayotgan portlarni "
     "ko'rsatadi.",
     "netstat -an | findstr 443  # 443-port orqali ulanishlarni ko'rsatadi"),

    # ---------------- KIBERXAVFSIZLIK ----------------
    ("Kiberxavfsizlik", "Asosiy tushunchalar", "Kuchli parol qanday bo'ladi", "-",
     "Kamida 12 ta belgi, katta-kichik harf, raqam va maxsus belgidan iborat, "
     "boshqa saytlarda takrorlanmaydigan parol eng xavfsiz hisoblanadi.",
     "Yomon: parol123. Yaxshi: T@shk3nt-2026!Bulut"),

    ("Kiberxavfsizlik", "Asosiy tushunchalar", "Ikki bosqichli tasdiqlash (2FA)", "-",
     "Parolga qo'shimcha ravishda telefon kodi yoki autentifikator ilova orqali "
     "tasdiqlash talab qiluvchi qo'shimcha xavfsizlik qatlami.",
     "Google/Telegram akkauntida 2FA yoqilsa, parol o'g'irlansa ham kirib bo'lmaydi."),

    ("Kiberxavfsizlik", "Asosiy tushunchalar", "Fishing (phishing) nima", "-",
     "Firibgarlar haqiqiy tashkilot nomidan soxta xat/sayt orqali parol yoki karta "
     "ma'lumotlarini o'g'irlashga urinishi. Havola manzilini har doim tekshiring.",
     "'Bank-dan' kelgan xat sizni bank-login.ru kabi soxta saytga yo'naltirsa — bu fishing."),

    ("Kiberxavfsizlik", "Asosiy tushunchalar", "Ijtimoiy muhandislik (social engineering)", "-",
     "Texnik emas, balki psixologik aldov orqali (masalan o'zini xodim sifatida "
     "ko'rsatib) maxfiy ma'lumot olishga urinish usuli.",
     "'Men IT bo'limidanman, parolingizni ayting' — bu ijtimoiy muhandislik hujumi."),

    ("Kiberxavfsizlik", "Asosiy tushunchalar", "Zararli dastur (malware) turlari", "-",
     "Virus (o'z-o'zini ko'paytiradi), Troyan (foydali dastur niqobida), Ransomware "
     "(fayllarni shifrlab pul talab qiladi), Spyware (josuslik qiladi).",
     "Ransomware fayllaringizni shifrlab, ochish uchun to'lov talab qilishi mumkin."),

    ("Kiberxavfsizlik", "Asosiy tushunchalar", "Zaxira nusxa (backup)", "-",
     "Ma'lumotlarning muntazam ravishda boshqa joyga (tashqi disk, bulut) "
     "nusxalanishi — hujum yoki uskuna nosozligida ma'lumot yo'qolmasligi uchun.",
     "3-2-1 qoidasi: 3 nusxa, 2 xil turdagi vosita, 1 tasi tashqarida saqlansin."),

    ("Kiberxavfsizlik", "Asosiy tushunchalar", "VPN nima", "-",
     "Internet trafigini shifrlab, boshqa server orqali yo'naltiruvchi xizmat — "
     "maxfiylikni oshiradi va ochiq Wi-Fi'da xavfsizlikni ta'minlaydi.",
     "Kafedagi ochiq Wi-Fi'da bank ilovasidan foydalanishdan oldin VPN yoqish tavsiya etiladi."),

    ("Kiberxavfsizlik", "Asosiy tushunchalar", "Firewall (xavfsizlik devori)", "-",
     "Kiruvchi va chiquvchi tarmoq trafigini qoidalar asosida nazorat qiluvchi "
     "himoya vositasi — ruxsatsiz ulanishlarni bloklaydi.",
     "Windows Defender Firewall — kompyuteringizga o'rnatilgan tayyor firewall."),

    ("Kiberxavfsizlik", "Asosiy tushunchalar", "HTTPS va SSL/TLS", "https://",
     "Sayt bilan brauzer o'rtasidagi ma'lumot almashinuvini shifrlaydigan protokol. "
     "Manzil satrida qulf belgisi bu himoya mavjudligini bildiradi.",
     "https://sayt.com — 's' harfi ma'lumotlar shifrlanganini bildiradi."),

    ("Kiberxavfsizlik", "Asosiy tushunchalar", "Shifrlash: simmetrik vs asimmetrik", "-",
     "Simmetrik shifrlashda bitta kalit ham shifrlash, ham ochish uchun ishlatiladi "
     "(tezroq). Asimmetrikda ochiq va yopiq kalit juftligi ishlatiladi (xavfsizroq).",
     "HTTPS ulanishni o'rnatishda asimmetrik, keyin tezlik uchun simmetrik shifrlash ishlatadi."),

    ("Kiberxavfsizlik", "Asosiy tushunchalar", "Parol menejeri", "-",
     "Har bir sayt uchun murakkab va noyob parollarni xavfsiz saqlab beruvchi "
     "dastur — foydalanuvchi faqat bitta bosh parolni eslab qoladi.",
     "Bitwarden, KeePass — mashhur bepul parol menejerlari."),

    ("Kiberxavfsizlik", "Amaliy xavfsizlik", "Ochiq portlarni tekshirish (nmap)", "nmap -sV localhost",
     "O'z kompyuteringiz yoki serveringizda qanday portlar ochiq ekanini tekshirib, "
     "keraksiz xizmatlarni yopish uchun ishlatiladi.",
     "nmap -sV localhost\n# O'zingizning kompyuteringizdagi ochiq portlarni ko'rsatadi"),

    ("Kiberxavfsizlik", "Amaliy xavfsizlik", "Fayl xesh (hash) tekshirish", "sha256sum fayl.exe",
     "Fayl o'zgartirilmaganini yoki zararli dastur bilan almashtirilmaganini "
     "tekshirish uchun uning raqamli 'barmoq izi' (hash) hisoblanadi.",
     "sha256sum dastur.exe\n# Rasmiy saytdagi hash bilan solishtiriladi"),

    # ---------------- GIT VA GITHUB ----------------
    ("Git va GitHub", "Asoslar", "Repository yaratish (git init)", "git init",
     "Joriy papkani Git tomonidan kuzatiladigan loyihaga (repository) aylantiradi.",
     "cd loyiham\ngit init\n# .git papkasi yaratiladi"),

    ("Git va GitHub", "Asoslar", "O'zgarishlarni belgilash (git add)", "git add .",
     "Fayllardagi o'zgarishlarni keyingi commit uchun tayyorlaydi (staging). "
     "Nuqta (.) barcha o'zgargan fayllarni bildiradi.",
     "git add fayl.py   # faqat bitta faylni qo'shadi\ngit add .          # hammasini qo'shadi"),

    ("Git va GitHub", "Asoslar", "O'zgarishni saqlash (git commit)", 'git commit -m "izoh"',
     "Tayyorlangan o'zgarishlarni izoh bilan birga loyiha tarixiga doimiy saqlaydi.",
     'git commit -m "Login formasi qo\'shildi"'),

    ("Git va GitHub", "Asoslar", "GitHub'ga yuklash (git push)", "git push origin main",
     "Mahalliy kompyuterdagi commit'larni masofaviy GitHub repositoriyga yuboradi.",
     "git push origin main"),

    ("Git va GitHub", "Asoslar", "O'zgarishlarni olish (git pull)", "git pull origin main",
     "GitHub'dagi eng so'nggi o'zgarishlarni mahalliy kompyuterga yuklab oladi.",
     "git pull origin main"),

    ("Git va GitHub", "Asoslar", "Loyihani ko'chirib olish (git clone)", "git clone URL",
     "GitHub'dagi mavjud repositoriyning to'liq nusxasini o'z kompyuteringizga "
     "yuklab oladi.",
     "git clone https://github.com/foydalanuvchi/loyiha.git"),

    ("Git va GitHub", "Tarmoqlar (branch)", "Yangi tarmoq yaratish (branch)", "git branch feature-x",
     "Asosiy koddan mustaqil rivojlanadigan alohida 'tarmoq' yaratish — bu asosiy "
     "kodni buzmasdan yangi funksiya ustida ishlash imkonini beradi.",
     "git branch feature-login\ngit checkout feature-login"),

    ("Git va GitHub", "Tarmoqlar (branch)", "Tarmoqni birlashtirish (merge)", "git merge feature-x",
     "Alohida tarmoqda qilingan o'zgarishlarni asosiy (main) tarmoqqa qo'shib "
     "qo'yadi.",
     "git checkout main\ngit merge feature-login"),

    ("Git va GitHub", "Boshqaruv", "Holatni ko'rish (git status)", "git status",
     "Qaysi fayllar o'zgargani, qaysilari staging'da (add qilingan) yoki hali "
     "kuzatilmayotganini ko'rsatadi.",
     "git status\n# Qizil — o'zgargan, yashil — add qilingan fayllar"),

    ("Git va GitHub", "Boshqaruv", "Tarixni ko'rish (git log)", "git log --oneline",
     "Loyihaning barcha commit tarixini sana, muallif va izoh bilan ko'rsatadi.",
     "git log --oneline\n# Har bir commit bitta qatorda qisqacha chiqadi"),

    ("Git va GitHub", "Boshqaruv", ".gitignore fayli", "node_modules/\n*.log",
     "Git tomonidan e'tiborsiz qoldirilishi kerak bo'lgan fayl/papkalarni "
     "(masalan parollar, vaqtinchalik fayllar) belgilaydi.",
     "# .gitignore ichida:\n__pycache__/\n.env\n*.db"),

    # ---------------- MA'LUMOTLAR BAZASI (SQL) ----------------
    ("Ma'lumotlar bazasi (SQL)", "Asoslar", "Jadval yaratish (CREATE TABLE)",
     "CREATE TABLE users (id INTEGER PRIMARY KEY, ism TEXT)",
     "Ma'lumotlar bazasida yangi jadval va uning ustunlarini (nom va turini) "
     "belgilaydi.",
     "CREATE TABLE users (\n  id INTEGER PRIMARY KEY,\n  ism TEXT,\n  yosh INTEGER\n);"),

    ("Ma'lumotlar bazasi (SQL)", "Asoslar", "Ma'lumot qo'shish (INSERT)",
     "INSERT INTO users (ism) VALUES ('Ali')",
     "Jadvalga yangi qator (yozuv) qo'shish uchun ishlatiladi.",
     "INSERT INTO users (ism, yosh) VALUES ('Ali', 20);"),

    ("Ma'lumotlar bazasi (SQL)", "Asoslar", "Ma'lumot olish (SELECT)", "SELECT * FROM users",
     "Jadvaldan ma'lumot o'qib olish uchun ishlatiladi. '*' barcha ustunlarni "
     "bildiradi.",
     "SELECT ism, yosh FROM users;\n# Faqat ism va yosh ustunlarini qaytaradi"),

    ("Ma'lumotlar bazasi (SQL)", "Asoslar", "Shart bilan tanlash (WHERE)",
     "SELECT * FROM users WHERE yosh > 18",
     "Faqat berilgan shartga mos keladigan qatorlarni qaytaradi.",
     "SELECT * FROM users WHERE yosh > 18;\n# 18 dan katta foydalanuvchilar"),

    ("Ma'lumotlar bazasi (SQL)", "Asoslar", "Ma'lumotni yangilash (UPDATE)",
     "UPDATE users SET yosh = 21 WHERE id = 1",
     "Mavjud yozuvning bir yoki bir nechta ustunini yangi qiymatga o'zgartiradi. "
     "WHERE'siz ishlatilsa BARCHA qatorlar o'zgaradi — ehtiyot bo'ling.",
     "UPDATE users SET yosh = 21 WHERE id = 1;"),

    ("Ma'lumotlar bazasi (SQL)", "Asoslar", "Ma'lumotni o'chirish (DELETE)",
     "DELETE FROM users WHERE id = 1",
     "Jadvaldan qatorni butunlay o'chiradi. WHERE'siz ishlatilsa jadvaldagi "
     "BARCHA ma'lumot o'chib ketadi.",
     "DELETE FROM users WHERE id = 1;"),

    ("Ma'lumotlar bazasi (SQL)", "Asoslar", "Tartiblash (ORDER BY)",
     "SELECT * FROM users ORDER BY yosh DESC",
     "Natijalarni ustun bo'yicha o'sish (ASC, standart) yoki kamayish (DESC) "
     "tartibida joylashtiradi.",
     "SELECT * FROM users ORDER BY yosh DESC;\n# Eng kattadan kichikka"),

    ("Ma'lumotlar bazasi (SQL)", "Kengaytirilgan", "Jadvallarni birlashtirish (JOIN)",
     "SELECT * FROM buyurtmalar JOIN users ON buyurtmalar.user_id = users.id",
     "Ikki bog'liq jadvaldagi ma'lumotlarni bitta natijaga birlashtirib olish "
     "uchun ishlatiladi.",
     "SELECT users.ism, buyurtmalar.mahsulot\nFROM buyurtmalar\nJOIN users ON buyurtmalar.user_id = users.id;"),

    ("Ma'lumotlar bazasi (SQL)", "Kengaytirilgan", "Guruhlash (GROUP BY)",
     "SELECT category, COUNT(*) FROM lessons GROUP BY category",
     "Bir xil qiymatga ega qatorlarni guruhlab, har guruh uchun umumiy hisob "
     "(COUNT, SUM kabi) chiqarish uchun ishlatiladi.",
     "SELECT category, COUNT(*) FROM lessons GROUP BY category;\n# Har kategoriyadagi dars soni"),

    ("Ma'lumotlar bazasi (SQL)", "Kengaytirilgan", "Asosiy kalit (PRIMARY KEY)",
     "id INTEGER PRIMARY KEY",
     "Jadvaldagi har bir qatorni noyob tarzda aniqlovchi ustun — takrorlanmaydi "
     "va bo'sh bo'lolmaydi.",
     "CREATE TABLE users (id INTEGER PRIMARY KEY, ism TEXT);"),

    # ---------------- VEB-DASTURLASH ----------------
    ("Veb-dasturlash", "HTML asoslari", "HTML hujjat tuzilishi",
     "<!DOCTYPE html><html><head></head><body></body></html>",
     "Har bir veb-sahifaning asosiy skeleti: head — sahifa haqidagi ma'lumot "
     "(title, style), body — foydalanuvchi ko'radigan tarkib.",
     "<!DOCTYPE html>\n<html>\n<head><title>Sahifam</title></head>\n<body><h1>Salom!</h1></body>\n</html>"),

    ("Veb-dasturlash", "HTML asoslari", "Havola va rasm (a, img)",
     '<a href="...">matn</a>  <img src="...">',
     "'a' teg havola (link) yaratadi, 'img' teg esa sahifaga rasm joylashtiradi.",
     '<a href="https://google.com">Google</a>\n<img src="rasm.jpg" alt="Rasm">'),

    ("Veb-dasturlash", "HTML asoslari", "Forma (form)",
     '<form><input type="text"><button>Yuborish</button></form>',
     "Foydalanuvchidan ma'lumot (matn, tanlov) qabul qilib, serverga yuborish "
     "uchun ishlatiladigan element.",
     '<form>\n  <input type="text" placeholder="Ismingiz">\n  <button type="submit">Yuborish</button>\n</form>'),

    ("Veb-dasturlash", "CSS asoslari", "Selektor va stil berish",
     "p { color: blue; }",
     "CSS orqali HTML elementlarini tanlab (selektor), ularga rang, o'lcham, "
     "joylashuv kabi ko'rinish xususiyatlarini beriladi.",
     "h1 { color: red; font-size: 32px; }\np { color: gray; }"),

    ("Veb-dasturlash", "CSS asoslari", "Flexbox bilan joylashtirish",
     "display: flex; justify-content: center;",
     "Elementlarni gorizontal yoki vertikal tarzda moslashuvchan joylashtirish "
     "uchun zamonaviy CSS usuli.",
     ".container {\n  display: flex;\n  justify-content: space-between;\n}"),

    ("Veb-dasturlash", "CSS asoslari", "Klass va ID selektorlari",
     ".klass { } #id { }",
     "Klass (.) bir nechta elementga, ID (#) esa sahifada faqat bitta elementga "
     "berilgan noyob nomga tegishli stil qo'llash uchun ishlatiladi.",
     "<p class='matn'>Salom</p>\n<style>.matn { color: green; }</style>"),

    ("Veb-dasturlash", "JavaScript asoslari", "O'zgaruvchi va funksiya",
     "let x = 5;\nfunction salom() { }",
     "JavaScript'da 'let'/'const' bilan o'zgaruvchi e'lon qilinadi, "
     "'function' bilan esa qayta ishlatiladigan kod blogi yaratiladi.",
     "function salom(ism) {\n  return 'Salom, ' + ism;\n}\nconsole.log(salom('Ali'));"),

    ("Veb-dasturlash", "JavaScript asoslari", "DOM bilan ishlash",
     "document.getElementById('id')",
     "JavaScript orqali HTML sahifadagi elementlarni topib, ularning tarkibi "
     "yoki ko'rinishini dinamik o'zgartirish imkonini beradi.",
     "document.getElementById('sarlavha').innerText = 'Yangi matn';"),

    ("Veb-dasturlash", "JavaScript asoslari", "Voqealar (event) bilan ishlash",
     "button.addEventListener('click', ...)",
     "Foydalanuvchi tugma bosishi, forma to'ldirishi kabi harakatlarga javob "
     "beradigan kodni ulash uchun ishlatiladi.",
     "document.querySelector('button').addEventListener('click', () => {\n  alert('Bosildi!');\n});"),

    # ---------------- KOMPYUTER ASOSLARI ----------------
    ("Kompyuter asoslari", "Injener-texnik", "CPU (protsessor) nima", "-",
     "Kompyuterning 'miyasi' — barcha buyruq va hisob-kitoblarni bajaradigan "
     "asosiy qism. Yadrolar soni va chastotasi (GHz) tezlikka ta'sir qiladi.",
     "4-yadroli, 3.5 GHz protsessor — bir vaqtda ko'proq vazifani tezroq bajaradi."),

    ("Kompyuter asoslari", "Injener-texnik", "RAM (operativ xotira) nima", "-",
     "Kompyuter ishlab turgan vaqtda dasturlar va ma'lumotlarni vaqtincha "
     "saqlaydigan tezkor xotira. O'chirilganda ma'lumot yo'qoladi.",
     "8 GB RAM — bir vaqtda bir nechta dastur va brauzer tablarini tez ochib turadi."),

    ("Kompyuter asoslari", "Injener-texnik", "HDD va SSD farqi", "-",
     "HDD — aylanadigan disk asosidagi eski, sekinroq xotira; SSD — mikrosxema "
     "asosidagi, tezroq va chidamliroq zamonaviy xotira turi.",
     "Windows'ni SSD'ga o'rnatish uni HDD'ga qaraganda bir necha barobar tez ishga tushiradi."),

    ("Kompyuter asoslari", "Injener-texnik", "BIOS/UEFI nima", "-",
     "Kompyuter yoqilganda birinchi ishga tushadigan, uskunalarni tekshirib "
     "operatsion tizimni yuklaydigan dastur.",
     "Kompyuter yoqilganda Del yoki F2 tugmasi BIOS/UEFI sozlamalarini ochadi."),

    ("Kompyuter asoslari", "Injener-texnik", "Motherboard (ona plata)", "-",
     "Barcha uskunalarni (protsessor, RAM, disk, video karta) o'zaro "
     "bog'lovchi asosiy elektron plata.",
     "Yangi protsessor sotib olishdan oldin u motherboard'ga mos kelishini tekshirish kerak."),

    ("Kompyuter asoslari", "Dasturiy ta'minot", "Operatsion tizim nima", "-",
     "Kompyuter uskunalari va dasturlar o'rtasida vositachilik qiluvchi asosiy "
     "dastur (Windows, Linux, macOS). Fayllarni boshqarish, dastur ishga tushirish kabi vazifalarni bajaradi.",
     "Windows, Linux va macOS — uchtasi ham operatsion tizim, lekin ichki tuzilishi har xil."),

    ("Kompyuter asoslari", "Dasturiy ta'minot", "Bit va bayt", "1 bayt = 8 bit",
     "Bit — ma'lumotning eng kichik birligi (0 yoki 1). 8 ta bit — 1 baytni "
     "tashkil qiladi. Fayl hajmi shu birliklarda o'lchanadi.",
     "1 KB = 1024 bayt, 1 MB = 1024 KB, 1 GB = 1024 MB"),

    ("Kompyuter asoslari", "Dasturiy ta'minot", "Fayl formatlari", ".txt .jpg .mp4 .pdf",
     "Fayl kengaytmasi (nuqtadan keyingi qism) uning turi va qaysi dastur bilan "
     "ochilishini bildiradi.",
     "hujjat.pdf — PDF o'qigich, rasm.jpg — rasm ko'ruvchi dastur bilan ochiladi."),

    ("Kompyuter asoslari", "Dasturiy ta'minot", "Kompilyator va interpretator", "-",
     "Kompilyator butun kodni oldindan mashina tiliga aylantiradi (C++), "
     "interpretator esa kodni qator-qator, ishga tushirish vaqtida bajaradi (Python).",
     "Python kodi interpretator (python.exe) orqali qator-qator bajariladi."),
]


async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS lessons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                sub_category TEXT,
                topic TEXT NOT NULL,
                command_or_code TEXT,
                description TEXT,
                example TEXT
            )
            """
        )
        async with db.execute("SELECT COUNT(*) FROM lessons") as cur:
            (count,) = await cur.fetchone()
        if count == 0:
            await db.executemany(
                """
                INSERT INTO lessons
                    (category, sub_category, topic, command_or_code, description, example)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                SAMPLE_DATA,
            )
            await db.commit()


async def get_categories() -> list[str]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT DISTINCT category FROM lessons ORDER BY category") as cur:
            rows = await cur.fetchall()
    return [r[0] for r in rows]


async def get_subcategories(category: str) -> list[str]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT sub_category, MIN(id) as first_id FROM lessons WHERE category = ? "
            "GROUP BY sub_category ORDER BY first_id",
            (category,),
        ) as cur:
            rows = await cur.fetchall()
    return [r[0] for r in rows]


async def get_topics(category: str, sub_category: str) -> list[tuple[int, str]]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT id, topic FROM lessons WHERE category = ? AND sub_category = ? ORDER BY id",
            (category, sub_category),
        ) as cur:
            return await cur.fetchall()


async def get_lesson_by_id(lesson_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT category, sub_category, topic, command_or_code, description, example "
            "FROM lessons WHERE id = ?",
            (lesson_id,),
        ) as cur:
            return await cur.fetchone()


async def search_lessons(query: str) -> list[tuple]:
    like = f"%{query}%"
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            """
            SELECT category, topic, command_or_code, description, example
            FROM lessons
            WHERE topic LIKE ? OR description LIKE ? OR category LIKE ?
               OR command_or_code LIKE ? OR sub_category LIKE ?
            LIMIT ?
            """,
            (like, like, like, like, like, SEARCH_RESULT_LIMIT),
        ) as cur:
            return await cur.fetchall()


async def get_category_counts() -> list[tuple[str, int]]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT category, COUNT(*) FROM lessons GROUP BY category ORDER BY category"
        ) as cur:
            return await cur.fetchall()


async def insert_lesson(category, sub_category, topic, code, description, example) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO lessons (category, sub_category, topic, command_or_code, description, example)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (category, sub_category, topic, code, description, example),
        )
        await db.commit()


# ==========================================
# 3. YORDAMCHI FUNKSIYALAR
# ==========================================
def esc(text: str) -> str:
    """HTML uchun xavfsiz matn (parse_mode='HTML' bilan ishlatishga)."""
    return html.escape(str(text)) if text else ""


async def get_main_keyboard() -> types.InlineKeyboardMarkup:
    categories = await get_categories()
    builder = InlineKeyboardBuilder()
    for category in categories:
        icon = CATEGORY_ICONS.get(category, DEFAULT_ICON)
        builder.row(
            types.InlineKeyboardButton(text=f"{icon} {category}", callback_data=f"cat_{category}")
        )
    return builder.as_markup()


def build_lesson_text(category: str, topic: str, code: str, desc: str, ex: str) -> str:
    parts = [f"📌 <b>Sinf:</b> {esc(category)} ➡️ {esc(topic)}\n"]
    if code and code != "-":
        parts.append(f"💻 <b>Kod / Terminal buyrug'i:</b>\n<code>{esc(code)}</code>\n")
    parts.append(f"ℹ️ <b>Izoh:</b>\n{esc(desc)}\n")
    parts.append(f"📝 <b>Amaliy misol:</b>\n<pre>{esc(ex)}</pre>")
    return "\n".join(parts)


async def safe_edit(callback: types.CallbackQuery, text: str, reply_markup=None) -> None:
    """Bir xil xabarni qayta yozishda Telegram xatosini yutib yuborish."""
    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e):
            raise


# ==========================================
# 4. YANGI DARS QO'SHISH (FSM, faqat admin)
# ==========================================
class AddLessonForm(StatesGroup):
    category = State()
    sub_category = State()
    topic = State()
    code = State()
    description = State()
    example = State()


@dp.message(Command("myid"))
async def myid_cmd(message: types.Message):
    await message.answer(
        f"Sizning Telegram ID'ingiz: <code>{message.from_user.id}</code>\n\n"
        f"Admin huquqini olish uchun shu raqamni kod ichidagi ADMIN_IDS "
        f"ro'yxatiga qo'shing.",
        parse_mode="HTML",
    )


@dp.message(Command("stats"))
async def stats_cmd(message: types.Message):
    counts = await get_category_counts()
    total = sum(c for _, c in counts)
    lines = ["📊 <b>Bot statistikasi</b>\n"]
    for category, count in counts:
        icon = CATEGORY_ICONS.get(category, DEFAULT_ICON)
        lines.append(f"{icon} {esc(category)}: <b>{count}</b> ta dars")
    lines.append(f"\n📚 Jami: <b>{total}</b> ta dars")
    await message.answer("\n".join(lines), parse_mode="HTML")


@dp.message(Command("add"))
async def add_start(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer(
            "⛔ Bu buyruq faqat administrator uchun.\n"
            "O'z ID'ingizni bilish uchun /myid yozing."
        )
        return
    await state.set_state(AddLessonForm.category)
    await message.answer(
        "🆕 Yangi dars qo'shish boshlandi.\n"
        "Istalgan vaqtda bekor qilish uchun /cancel yozing.\n\n"
        "1️⃣ Kategoriya nomini kiriting (masalan: Python, Linux, Kiberxavfsizlik):"
    )


@dp.message(Command("cancel"))
async def cancel_form(message: types.Message, state: FSMContext):
    current = await state.get_state()
    if current is None:
        await message.answer("Bekor qilinadigan jarayon yo'q.")
        return
    await state.clear()
    await message.answer("❌ Bekor qilindi.")


@dp.message(AddLessonForm.category)
async def add_category(message: types.Message, state: FSMContext):
    await state.update_data(category=message.text.strip())
    await state.set_state(AddLessonForm.sub_category)
    await message.answer("2️⃣ Kichik mavzu (bo'lim) nomini kiriting (masalan: Asoslar):")


@dp.message(AddLessonForm.sub_category)
async def add_sub_category(message: types.Message, state: FSMContext):
    await state.update_data(sub_category=message.text.strip())
    await state.set_state(AddLessonForm.topic)
    await message.answer("3️⃣ Dars nomini (topic) kiriting (masalan: For sikli):")


@dp.message(AddLessonForm.topic)
async def add_topic(message: types.Message, state: FSMContext):
    await state.update_data(topic=message.text.strip())
    await state.set_state(AddLessonForm.code)
    await message.answer(
        "4️⃣ Kod yoki terminal buyrug'ini kiriting.\n"
        "Agar kod kerak bo'lmasa, faqat '-' deb yozing:"
    )


@dp.message(AddLessonForm.code)
async def add_code(message: types.Message, state: FSMContext):
    await state.update_data(code=message.text.strip())
    await state.set_state(AddLessonForm.description)
    await message.answer("5️⃣ Izoh (bu nima uchun kerakligini) yozing:")


@dp.message(AddLessonForm.description)
async def add_description(message: types.Message, state: FSMContext):
    await state.update_data(description=message.text.strip())
    await state.set_state(AddLessonForm.example)
    await message.answer("6️⃣ Amaliy misol kiriting:")


@dp.message(AddLessonForm.example)
async def add_example(message: types.Message, state: FSMContext):
    data = await state.get_data()
    example = message.text.strip()

    await insert_lesson(
        category=data["category"],
        sub_category=data["sub_category"],
        topic=data["topic"],
        code=data["code"],
        description=data["description"],
        example=example,
    )
    await state.clear()

    icon = CATEGORY_ICONS.get(data["category"], DEFAULT_ICON)
    await message.answer(
        f"✅ Yangi dars qo'shildi!\n\n"
        f"{icon} <b>{esc(data['category'])}</b> → {esc(data['sub_category'])} → "
        f"{esc(data['topic'])}",
        parse_mode="HTML",
    )


# ==========================================
# 5. ASOSIY HANDLERLAR
# ==========================================
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    name = esc(message.from_user.first_name or "do'stim")
    await message.answer(
        f"Salom, {name}!\n\n"
        f"Bu bot kompyuter va dasturlash bo'yicha darslar, izohlar va amaliy "
        f"buyruqlarni bir joyga jamlagan: Python, Linux, Windows, Tarmoq asoslari, "
        f"Kiberxavfsizlik, Git/GitHub, SQL, Veb-dasturlash va Kompyuter asoslari.\n\n"
        f"💡 <b>Imkoniyatlar:</b>\n"
        f"1. Pastdagi tugmalar orqali bo'lim → mavzu → dars tartibida ko'ring.\n"
        f"2. Istalgan vaqtda kalit so'z yozing — masalan <code>nmap</code>, "
        f"<code>fishing</code>, <code>git</code> yoki <code>SQL</code>.\n\n"
        f"/help — barcha buyruqlar",
        parse_mode="HTML",
        reply_markup=await get_main_keyboard(),
    )


@dp.message(Command("help"))
async def help_cmd(message: types.Message):
    text = (
        "/start — bosh menyu\n"
        "/help — shu yordam xabari\n"
        "/stats — bazadagi darslar statistikasi\n"
        "/myid — o'z Telegram ID'ingizni ko'rish\n\n"
        "Har qanday kalit so'zni oddiy xabar sifatida yuboring — bot bazadan qidiradi."
    )
    if is_admin(message.from_user.id):
        text += "\n\n👑 <b>Admin buyruqlari:</b>\n/add — yangi dars qo'shish\n/cancel — jarayonni bekor qilish"
    await message.answer(text, parse_mode="HTML")


@dp.callback_query(F.data.startswith("cat_"))
async def show_subcategories(callback: types.CallbackQuery):
    category = callback.data.removeprefix("cat_")
    subcategories = await get_subcategories(category)

    builder = InlineKeyboardBuilder()
    for sub in subcategories:
        builder.row(
            types.InlineKeyboardButton(
                text=sub, callback_data=f"sub_{category}{SEP}{sub}"
            )
        )
    builder.row(types.InlineKeyboardButton(text="⬅️ Bosh menyu", callback_data="back_to_main"))

    if not subcategories:
        text = f"📚 <b>{esc(category)}</b> bo'limida hozircha darslar yo'q."
    else:
        text = f"📚 <b>{esc(category)}</b> — bo'limni tanlang:"

    await safe_edit(callback, text, builder.as_markup())
    await callback.answer()


@dp.callback_query(F.data.startswith("sub_"))
async def show_topics(callback: types.CallbackQuery):
    category, sub_category = callback.data.removeprefix("sub_").split(SEP, 1)
    topics = await get_topics(category, sub_category)

    builder = InlineKeyboardBuilder()
    for topic_id, topic_name in topics:
        builder.row(
            types.InlineKeyboardButton(text=topic_name, callback_data=f"lesson_{topic_id}")
        )
    builder.row(
        types.InlineKeyboardButton(text="⬅️ Orqaga", callback_data=f"cat_{category}")
    )
    builder.row(types.InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="back_to_main"))

    text = f"📖 <b>{esc(category)} → {esc(sub_category)}</b>\nMavzuni tanlang:"
    await safe_edit(callback, text, builder.as_markup())
    await callback.answer()


@dp.callback_query(F.data.startswith("lesson_"))
async def show_lesson_detail(callback: types.CallbackQuery):
    try:
        lesson_id = int(callback.data.removeprefix("lesson_"))
    except ValueError:
        await callback.answer("Noto'g'ri so'rov.", show_alert=True)
        return

    lesson = await get_lesson_by_id(lesson_id)
    if not lesson:
        await callback.answer("Bu dars topilmadi.", show_alert=True)
        return

    category, sub_category, topic, code, desc, ex = lesson
    text = build_lesson_text(category, topic, code, desc, ex)

    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(
            text="⬅️ Orqaga", callback_data=f"sub_{category}{SEP}{sub_category}"
        )
    )
    builder.row(types.InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="back_to_main"))

    await safe_edit(callback, text, builder.as_markup())
    await callback.answer()


@dp.callback_query(F.data == "back_to_main")
async def back_main(callback: types.CallbackQuery):
    await safe_edit(
        callback,
        "Kerakli bo'limni tanlang yoki kalit so'zni yozib yuboring:",
        await get_main_keyboard(),
    )
    await callback.answer()


@dp.message()
async def smart_search(message: types.Message):
    query = (message.text or "").strip()
    if not query:
        return

    results = await search_lessons(query)

    if not results:
        await message.answer(
            f"⚠️ Xafa bo'lish yo'q-u, lekin bazamizdan <b>'{esc(query)}'</b> bo'yicha "
            f"hech narsa topilmadi.\n"
            f"Boshqa so'z yozib ko'ring (masalan: nmap, for, chmod, class, git, SQL).",
            parse_mode="HTML",
        )
        return

    for category, topic, code, desc, ex in results:
        await message.answer(
            build_lesson_text(category, topic, code, desc, ex), parse_mode="HTML"
        )


# ==========================================
# 6. ISHGA TUSHIRISH
# ==========================================
async def main():
    await init_db()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())