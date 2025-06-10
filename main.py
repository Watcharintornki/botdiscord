import os
import discord
from discord.ext import commands, tasks
import asyncio # ยังคง import ไว้เผื่อใช้งานฟังก์ชัน asynchronous อื่นๆ ในอนาคต
import datetime

# สมมติว่า myserver.py มีฟังก์ชัน server_on() ที่รันเว็บเซิร์ฟเวอร์
# เพื่อให้บอททำงานอยู่ตลอดเวลาบนแพลตฟอร์มเช่น Replit
from myserver import server_on

# กำหนดสิทธิ์ (Intents) ที่บอทต้องการ
# message_content ต้องเปิดใช้งานใน Discord Developer Portal ด้วย
intents = discord.Intents.default()
intents.message_content = True

# สร้างอ็อบเจกต์บอทพร้อมคำนำหน้าคำสั่ง
bot = commands.Bot(command_prefix='!', intents=intents)

# ค่าเริ่มต้นของเวลาคูลดาวน์เป็นนาที
DEFAULT_MINUTES = 15
# Dictionary สำหรับเก็บข้อมูลคูลดาวน์
# key: channel_id (int)
# value: list of dicts: {'name': str, 'end_time': datetime.datetime, 'message': discord.Message}
cooldowns = {}

# Event: เมื่อบอทออนไลน์และพร้อมใช้งาน
@bot.event
async def on_ready():
    print(f'✅ บอทออนไลน์แล้ว: {bot.user}')
    # เริ่มต้นการทำงานของ Task สำหรับอัปเดตสถานะคูลดาวน์
    countdown_updater.start()

# คำสั่ง: !คูลดาวน์ <ชื่อ> [นาที]
# <ชื่อ>: ชื่อของสิ่งที่จะคูลดาวน์ (จำเป็น)
# [นาที]: จำนวนนาทีคูลดาวน์ (ไม่จำเป็น, ใช้ DEFAULT_MINUTES ถ้าไม่ระบุ)
@bot.command()
async def คูลดาวน์(ctx, *, arg: str):
    try:
        # แยกส่วนประกอบของ arguments
        parts = arg.strip().split()

        # ตรวจสอบว่ามี arguments หรือไม่
        if not parts:
            await ctx.send("❗ ใช้คำสั่ง: `!คูลดาวน์ <ชื่อ> [นาที]`")
            return

        minutes = DEFAULT_MINUTES
        name_parts = []

        # ตรวจสอบว่า argument สุดท้ายเป็นตัวเลขนาทีหรือไม่
        if parts[-1].isdigit():
            minutes = int(parts[-1])
            name_parts = parts[:-1] # ชื่อคือส่วนที่เหลือก่อนตัวเลข
        else:
            name_parts = parts # ชื่อคือทั้งหมดถ้าไม่มีตัวเลขนาที

        name = " ".join(name_parts)

        # ตรวจสอบว่าระบุชื่อหรือไม่
        if not name:
            await ctx.send("❗ กรุณาระบุชื่อสิ่งที่ต้องการคูลดาวน์")
            return

        now = datetime.datetime.now() # เวลาปัจจุบัน
        end_time = now + datetime.timedelta(minutes=minutes) # เวลาสิ้นสุดคูลดาวน์

        channel_id = ctx.channel.id # ID ของช่องปัจจุบัน

        # เพิ่ม channel_id ลงใน dictionary ถ้ายังไม่มี
        if channel_id not in cooldowns:
            cooldowns[channel_id] = []

        # ส่งข้อความเริ่มต้นคูลดาวน์และเก็บอ็อบเจกต์ข้อความไว้
        msg = await ctx.send(f'🕒 `{name}` คูลดาวน์ {minutes} นาที (สิ้นสุด {end_time.strftime("%H:%M:%S")})')

        # เพิ่มข้อมูลคูลดาวน์ลงในรายการของช่องนั้น
        cooldowns[channel_id].append({
            'name': name.lower(), # เก็บชื่อเป็นตัวพิมพ์เล็กเพื่อการเปรียบเทียบที่ไม่คำนึงถึงตัวพิมพ์ใหญ่-เล็ก
            'end_time': end_time,
            'message': msg # เก็บอ็อบเจกต์ข้อความเพื่อใช้อัปเดตในภายหลัง
        })

    except Exception as e:
        # ดักจับข้อผิดพลาดและส่งข้อความแจ้งเตือน
        await ctx.send(f'⚠️ เกิดข้อผิดพลาด: {str(e)}')

# คำสั่ง: !ยกเลิก <ชื่อ>
# <ชื่อ>: ชื่อของคูลดาวน์ที่ต้องการยกเลิก
@bot.command()
async def ยกเลิก(ctx, *, name: str):
    channel_id = ctx.channel.id
    name = name.strip().lower() # แปลงชื่อเป็นตัวพิมพ์เล็กเพื่อค้นหา

    # ตรวจสอบว่ามีคูลดาวน์ในช่องนี้หรือไม่
    if channel_id not in cooldowns or not cooldowns[channel_id]:
        await ctx.send("⚠️ ไม่มีคิวคูลดาวน์ในห้องนี้")
        return

    found = False
    # วนลูปผ่านรายการคูลดาวน์และลบรายการที่ตรงกัน
    # ใช้ list(cooldowns[channel_id]) เพื่อสร้างสำเนาของลิสต์ก่อนวนลูปเพื่อป้องกันการเปลี่ยนแปลงลิสต์ขณะวนลูป
    for item in list(cooldowns[channel_id]):
        if item['name'] == name:
            try:
                # พยายามแก้ไขข้อความแจ้งสถานะเดิมเป็นการยกเลิก
                await item['message'].edit(content=f'❌ `{name}` คูลดาวน์ถูกยกเลิกแล้ว')
            except discord.NotFound: # ดักจับกรณีที่ข้อความถูกลบไปแล้ว
                print(f"ข้อความสำหรับคูลดาวน์ `{name}` ไม่พบแล้ว")
            except Exception as e:
                print(f"เกิดข้อผิดพลาดในการแก้ไขข้อความ: {e}")
            finally:
                cooldowns[channel_id].remove(item) # ลบรายการออกจากลิสต์
                found = True
                await ctx.send(f'🛑 ยกเลิกคูลดาวน์ `{name}` เรียบร้อยแล้ว')
                break # หยุดการค้นหาเมื่อพบและลบแล้ว

    if not found:
        await ctx.send(f"⚠️ ไม่พบชื่อ `{name}` ในคิวคูลดาวน์")

# คำสั่ง: !สถานะ
# แสดงรายการคูลดาวน์ที่กำลังทำงานอยู่ในช่องปัจจุบัน
@bot.command()
async def สถานะ(ctx):
    channel_id = ctx.channel.id
    now = datetime.datetime.now()

    # ตรวจสอบว่ามีคูลดาวน์ในช่องนี้หรือไม่
    if channel_id not in cooldowns or not cooldowns[channel_id]:
        await ctx.send("ℹ️ ไม่มีรายการคูลดาวน์ในห้องนี้ตอนนี้")
        return

    lines = []
    # วนลูปผ่านรายการคูลดาวน์และคำนวณเวลาที่เหลือ
    for item in cooldowns[channel_id]:
        remaining = item['end_time'] - now
        if remaining.total_seconds() > 0: # ถ้ายังมีเวลาเหลือ
            mins = int(remaining.total_seconds() // 60)
            secs = int(remaining.total_seconds() % 60)
            lines.append(f"`{item['name']}` เหลือเวลา {mins} นาที {secs} วินาที (สิ้นสุด {item['end_time'].strftime('%H:%M:%S')})")

    # ส่งข้อความแสดงสถานะคูลดาวน์
    if lines:
        await ctx.send("⏳ รายการคูลดาวน์ที่กำลังทำงาน:\n" + "\n".join(lines))
    else:
        await ctx.send("ℹ️ ไม่มีรายการคูลดาวน์ในห้องนี้ตอนนี้")

# Task loop: อัปเดตสถานะคูลดาวน์ทุก 60 วินาที
@tasks.loop(seconds=60)
async def countdown_updater():
    now = datetime.datetime.now()
    # วนลูปผ่าน channel_id และรายการคูลดาวน์
    # ใช้ list(cooldowns.items()) เพื่อสร้างสำเนาของ items ก่อนวนลูป
    for channel_id, items in list(cooldowns.items()):
        channel = bot.get_channel(channel_id)
        if not channel:
            # ถ้าหาช่องไม่พบ (อาจถูกลบไปแล้ว) ให้ข้ามไป
            continue

        # วนลูปผ่านรายการคูลดาวน์ในช่องนั้น
        # ใช้ items[:] เพื่อสร้างสำเนาของลิสต์ก่อนวนลูปเพื่อป้องกันการเปลี่ยนแปลงลิสต์ขณะวนลูป
        for item in items[:]:
            name = item['name']
            end_time = item['end_time']
            msg = item['message']

            remaining = end_time - now
            if remaining.total_seconds() <= 0:
                # ถ้าคูลดาวน์หมดแล้ว
                try:
                    await channel.send(f'✅ `{name}` คูลดาวน์เสร็จแล้ว!')
                except Exception as e:
                    print(f"ไม่สามารถส่งข้อความแจ้งเตือนคูลดาวน์เสร็จสิ้นสำหรับ `{name}` ในช่อง {channel_id}: {e}")
                items.remove(item) # ลบรายการที่หมดเวลาแล้วออก
            else:
                # ถ้ายังมีเวลาเหลือ
                mins_left = int(remaining.total_seconds() // 60)
                try:
                    # อัปเดตข้อความเดิมด้วยเวลาที่เหลือ
                    await msg.edit(content=f'⏳ `{name}` เหลือเวลาอีก {mins_left} นาที (สิ้นสุด {end_time.strftime("%H:%M:%S")})')
                except discord.NotFound:
                    # ถ้าข้อความต้นฉบับถูกลบไปแล้ว ก็ไม่ต้องทำอะไร
                    print(f"ข้อความสำหรับคูลดาวน์ `{name}` ไม่พบแล้ว ไม่สามารถแก้ไขได้")
                    items.remove(item) # ลบรายการออกจากลิสต์เพื่อให้บอทไม่พยายามอัปเดตอีก
                except Exception as e:
                    # ดักจับข้อผิดพลาดอื่น ๆ ในการแก้ไขข้อความ
                    print(f"เกิดข้อผิดพลาดในการแก้ไขข้อความสำหรับ `{name}`: {e}")

        # ถ้าไม่มีคูลดาวน์เหลือในช่องนี้แล้ว ให้ลบ channel_id ออกจาก dictionary
        if not items:
            del cooldowns[channel_id]

# รันเซิร์ฟเวอร์ (จาก myserver.py) เพื่อให้บอททำงานอยู่ตลอดเวลา
server_on()

# รันบอทด้วยโทเค็นที่อยู่ใน Environment Variable
# ต้องตั้งค่า TOKEN ใน Environment Variables ของแพลตฟอร์มที่คุณใช้รันบอท (เช่น Replit)
bot.run(os.getenv('TOKEN'))
