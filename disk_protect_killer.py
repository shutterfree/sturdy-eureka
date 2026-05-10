"""
硬盘还原保护软件 检测 & 安全关闭工具 v4.0
支持: 冰点还原 / 影子系统 / 还原精灵 / 小哨兵 / 噢易 / 联想EDU / 万象 / 网维大师 /
      Power Shadow / RollBack Rx / Reboot Restore Rx / Toolwiz Time Freeze /
      SmartShield / 希沃还原 / 方正还原 / 同方还原 / 网众Netzone / 锐起无盘 /
      信佑还原 / 顺网网维 / 易游网娱 / 海光还原 / 绿坝 / Comodo Time Machine /
      鸿合 HiteVision (鸿合管家/保护/白板/授课/展台/桌面/云/课堂/守护/冻结/还原) 等
安全模式: 不强杀进程、不改驱动文件，通过软件自身机制关闭保护
运行需要: 管理员权限
"""

import subprocess
import os
import sys
import ctypes
import winreg
import time
import shutil
import json
from datetime import datetime

# ============================================================
#  工具函数
# ============================================================

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_cmd(cmd, timeout=15):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                           creationflags=subprocess.CREATE_NO_WINDOW, shell=True)
        return r.stdout + r.stderr
    except subprocess.TimeoutExpired:
        return "[超时]"
    except Exception as e:
        return f"[错误: {e}]"

def pause():
    input("\n按回车键继续...")

def easter_egg():
    """小彩蛋"""
    import time
    frames = [
        r"""
          ___________
         |           |
         |  文 人    |
         |  牛 逼    |
         |___________|
        """,
        r"""
          ★ ★ ★ ★ ★ ★ ★
          ★             ★
          ★  文 人 牛 逼  ★
          ★             ★
          ★ ★ ★ ★ ★ ★ ★
        """,
        r"""
         ╔═══════════════╗
         ║               ║
         ║  文 人 牛 逼   ║
         ║               ║
         ╚═══════════════╝
        """,
    ]
    colors = ["\033[91m", "\033[93m", "\033[92m", "\033[96m", "\033[95m", "\033[94m"]
    reset = "\033[0m"
    print()
    for i in range(12):
        c = colors[i % len(colors)]
        f = frames[i % len(frames)]
        print(f"\r{c}{f}{reset}", end="", flush=True)
        time.sleep(0.3)
        # 清除上一帧（移动光标回去）
        lines = f.count("\n")
        print(f"\033[{lines}A", end="", flush=True)
    # 最终定格
    print(f"\033[93m")
    print(r"""
     ╔═══════════════════════════════╗
     ║                               ║
     ║      ★  文 人 牛 逼  ★        ║
     ║                               ║
     ╚═══════════════════════════════╝
    """)
    print(f"\033[0m")

def print_header(title):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)

# ============================================================
#  安全工具函数
# ============================================================

def safe_sc_stop(service_name):
    """温和停止服务，不强制。返回是否成功。"""
    out = run_cmd(["sc", "stop", service_name], timeout=10)
    if "1060" in out or "不存在" in out:
        return False  # 服务不存在
    if "1052" in out or "拒绝" in out:
        print(f"      [!] 服务 {service_name} 拒绝停止（可能受保护）")
        return False
    if "停止成功" in out or "success" in out.lower():
        print(f"      [OK] 服务 {service_name} 已停止")
        return True
    print(f"      [?] 服务 {service_name}: {out.strip()[:80]}")
    return False

def safe_sc_disable(service_name):
    """将服务设为禁用（不影响当前运行，仅阻止下次启动）。"""
    out = run_cmd(["sc", "config", service_name, "start=", "disabled"], timeout=10)
    if "1060" in out or "不存在" in out:
        return False
    if "成功" in out or "success" in out.lower():
        print(f"      [OK] 服务 {service_name} 已禁用自启")
        return True
    print(f"      [?] 服务 {service_name}: {out.strip()[:80]}")
    return False

def create_restore_point():
    """尝试创建系统还原点。"""
    print("\n  [*] 正在创建系统还原点...")
    # 使用 PowerShell 创建还原点
    ps_cmd = ('powershell -Command "'
              'Checkpoint-Computer -Description \'还原保护工具_操作前备份\' -RestorePointType MODIFY_SETTINGS'
              '"')
    out = run_cmd(ps_cmd, timeout=120)
    if "成功" in out or "success" in out.lower() or out.strip() == "":
        print("  [OK] 系统还原点已创建")
        return True
    else:
        print(f"  [!] 创建还原点失败: {out.strip()[:100]}")
        print("  [?] 建议手动创建: 控制面板 -> 系统 -> 系统保护 -> 创建")
        return False

def find_uninstall_cmd(software_name):
    """从注册表查找卸载命令。"""
    uninstall_keys = [
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
    ]
    keywords = software_name.lower().split()
    found = []
    for uk in uninstall_keys:
        try:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, uk)
            i = 0
            while True:
                try:
                    subkey_name = winreg.EnumKey(key, i)
                    subkey = winreg.OpenKey(key, subkey_name)
                    try:
                        display = winreg.QueryValueEx(subkey, "DisplayName")[0]
                        uninstall_str = None
                        try:
                            uninstall_str = winreg.QueryValueEx(subkey, "UninstallString")[0]
                        except:
                            pass
                        if any(kw in display.lower() for kw in keywords):
                            found.append((display, uninstall_str))
                    except:
                        pass
                    winreg.CloseKey(subkey)
                    i += 1
                except OSError:
                    break
            winreg.CloseKey(key)
        except:
            pass
    return found

def safe_disable_services(service_list):
    """安全停止并禁用一组服务。不强制，失败跳过。"""
    stopped = 0
    disabled = 0
    for svc in service_list:
        if safe_sc_stop(svc):
            stopped += 1
        if safe_sc_disable(svc):
            disabled += 1
    return stopped, disabled

def print_risk_warning(risk_level, description):
    """打印风险提示。"""
    icons = {"安全": "[SAFE]", "低": "[LOW]", "中": "[MID]", "高": "[HIGH]"}
    colors = {"安全": "\033[92m", "低": "\033[93m", "中": "\033[91m", "高": "\033[91;1m"}
    reset = "\033[0m"
    icon = icons.get(risk_level, "[?]")
    color = colors.get(risk_level, "")
    print(f"  {color}{icon}{reset} {description}")

def print_manual_guide(title, steps):
    """打印手动操作指南。"""
    print(f"\n  ┌─ 手动操作指南: {title}")
    for i, step in enumerate(steps, 1):
        print(f"  │  {i}. {step}")
    print(f"  └─")

# ============================================================
#  检测模块
# ============================================================

class DetectedItem:
    def __init__(self, category, name, detail, proc=None, svc=None, reg=None, path=None):
        self.category = category
        self.name = name
        self.detail = detail
        self.proc = proc      # process name
        self.svc = svc        # service name
        self.reg = reg        # registry key
        self.path = path      # file path

# ---- 进程名 -> 软件映射 ----
PROCESS_MAP = {
    "frzstate2k.exe":   ("冰点还原 Deep Freeze", "Faronics Deep Freeze，最常见的还原保护"),
    "frzstate.exe":     ("冰点还原 Deep Freeze", "Faronics Deep Freeze"),
    "dfserv.exe":       ("冰点还原 Deep Freeze", "Deep Freeze 服务进程"),
    "persistray.exe":   ("冰点还原 Deep Freeze", "Deep Freeze 托盘程序"),
    "shadowdefender.exe": ("影子系统 Shadow Defender", "影子系统主程序"),
    "sdservice.exe":    ("影子系统 Shadow Defender", "影子系统服务"),
    "sdtray.exe":       ("影子系统 Shadow Defender", "影子系统托盘"),
    "hshield.exe":      ("小哨兵还原精灵", "小哨兵保护程序"),
    "hshieldagent.exe": ("小哨兵还原精灵", "小哨兵代理"),
    "rvtray.exe":       ("联想EDU保护", "联想教育版保护系统"),
    "rvcontrol.exe":    ("联想EDU保护", "联想EDU控制程序"),
    "ossclient.exe":    ("噢易OSS保护", "噢易OSS客户端"),
    "ossservice.exe":   ("噢易OSS保护", "噢易OSS服务"),
    "osstray.exe":      ("噢易OSS保护", "噢易OSS托盘"),
    "wdpcprot.exe":     ("万象网管还原", "万象网管磁盘保护"),
    "everrestore.exe":  ("易速还原", "易速还原保护程序"),
    "evertray.exe":     ("易速还原", "易速还原托盘"),
    "compustar.exe":    ("联想保护", "联想CompuStar保护"),
    "stup.exe":         ("网吧还原/计费", "网吧还原保护"),
    "diskshield.exe":   ("磁盘保护", "通用磁盘保护"),
    "protdisk.exe":     ("磁盘保护", "通用磁盘保护"),
    "safedog.exe":      ("安全狗", "服务器安全狗"),
    "rtdelay.exe":      ("重启还原", "重启还原程序"),
    "reborn.exe":       ("还原精灵", "还原精灵"),
    "rebornsvc.exe":    ("还原精灵", "还原精灵服务"),
    "sentry.exe":       ("哨兵还原", "哨兵还原系统"),
    "sentrysvc.exe":    ("哨兵还原", "哨兵还原服务"),
    "clsmn.exe":        ("网吧管理", "网吧管理/还原"),
    "nbmsvc.exe":       ("网维大师", "网维大师服务"),
    "clientmain.exe":   ("网维大师", "网维大师客户端"),
    "gamemaster.exe":   ("网维大师", "网维大师游戏管理"),
    "barclient.exe":    ("Pubwin", "Pubwin网吧管理"),
    "vfdrvmon.exe":     ("还原驱动", "还原驱动监控"),
    "atprtmon.exe":     ("还原监控", "还原系统监控"),
    "dskprotect.exe":   ("磁盘保护", "磁盘保护工具"),
    "rvmgr.exe":        ("还原管理", "还原系统管理"),

    # ---- 新增: 更多还原保护软件 ----
    "pwrshadow.exe":    ("Power Shadow", "Power Shadow影子保护"),
    "shadowuser.exe":   ("ShadowUser", "ShadowUser影子用户"),
    "shadowprotect.exe":("ShadowProtect", "ShadowProtect磁盘保护"),
    "ctmexec.exe":      ("Comodo Time Machine", "Comodo时间机器"),
    "rbmanager.exe":    ("RollBack Rx", "RollBack Rx快照管理"),
    "rbtray.exe":       ("RollBack Rx", "RollBack Rx托盘"),
    "shieldtray.exe":   ("Reboot Restore Rx", "Reboot Restore托盘"),
    "shield.exe":       ("Reboot Restore Rx", "Reboot Restore主程序"),
    "drivevaccine.exe": ("Drive Vaccine", "Drive Vaccine还原"),
    "toolwizfreeze.exe":("Toolwiz Time Freeze", "Toolwiz时间冻结"),
    "smartshield.exe":  ("SmartShield", "SmartShield磁盘保护"),
    "ssservice.exe":    ("SmartShield", "SmartShield服务"),

    # 希沃还原
    "seewoservice.exe": ("希沃还原", "希沃还原保护服务"),
    "seewotray.exe":    ("希沃还原", "希沃还原托盘"),
    "seewoprotect.exe": ("希沃还原", "希沃还原保护程序"),

    # 方正还原
    "founderprotect.exe":("方正还原", "方正还原保护程序"),
    "founderservice.exe":("方正还原", "方正还原服务"),

    # 同方还原
    "tongfangprotect.exe":("同方还原", "同方还原保护程序"),
    "tongfangsvc.exe":   ("同方还原", "同方还原服务"),

    # 网众Netzone
    "netzoneservice.exe":("网众Netzone", "网众无盘服务"),
    "netzoneclient.exe": ("网众Netzone", "网众客户端"),
    "netzonedisk.exe":   ("网众Netzone", "网众磁盘保护"),

    # 锐起
    "richguide.exe":    ("锐起无盘", "锐起无盘启动"),
    "richservice.exe":  ("锐起无盘", "锐起服务"),

    # 信佑
    "xinuprotect.exe":  ("信佑还原", "信佑还原保护"),
    "xinuservice.exe":  ("信佑还原", "信佑还原服务"),

    # 顺网
    "swgservice.exe":   ("顺网网维", "顺网网维服务"),
    "swgclient.exe":    ("顺网网维", "顺网客户端"),
    "swprotect.exe":    ("顺网网维", "顺网磁盘保护"),

    # 易游
    "eeyoo.exe":        ("易游网娱", "易游网娱平台"),
    "eeyooservice.exe": ("易游网娱", "易游网娱服务"),
    "eeyootray.exe":    ("易游网娱", "易游网娱托盘"),

    # 海光还原
    "haiguangprotect.exe":("海光还原", "海光还原保护"),
    "haiguangsvc.exe":  ("海光还原", "海光还原服务"),

    # 更多冰点还原进程
    "dfserv64.exe":     ("冰点还原 Deep Freeze", "Deep Freeze 64位服务"),

    # 更多影子系统进程
    "sd64.exe":         ("影子系统 Shadow Defender", "影子系统64位"),

    # 更多噢易OSS进程
    "ossmgr.exe":       ("噢易OSS保护", "噢易OSS管理"),
    "ossupdate.exe":    ("噢易OSS保护", "噢易OSS更新"),

    # 更多网维大师进程
    "nbmupdate.exe":    ("网维大师", "网维大师更新"),
    "nbmprotect.exe":   ("网维大师", "网维大师保护"),

    # 更多万象网管进程
    "wdpcmgr.exe":      ("万象网管还原", "万象网管管理"),
    "wdpcupdate.exe":   ("万象网管还原", "万象网管更新"),

    # 更多小哨兵进程
    "hshield64.exe":    ("小哨兵还原精灵", "小哨兵64位"),
    "hshieldmgr.exe":   ("小哨兵还原精灵", "小哨兵管理"),

    # 更多Pubwin进程
    "barservice.exe":   ("Pubwin", "Pubwin服务"),
    "barupdate.exe":    ("Pubwin", "Pubwin更新"),

    # 绿坝
    "lvbang.exe":       ("绿坝花季护航", "绿坝保护程序"),
    "lvbangservice.exe":("绿坝花季护航", "绿坝服务"),

    # 通用保护进程
    "sysprotect.exe":   ("系统保护", "通用系统保护"),
    "diskguard.exe":    ("磁盘卫士", "磁盘卫士保护"),
    "pcprotect.exe":    ("PC保护", "PC保护程序"),
    "rebootrestore.exe":("重启还原", "重启还原程序"),
    "frozendisk.exe":   ("冻结磁盘", "冻结磁盘保护"),

    # ---- 鸿合 HiteVision 教育一体机 ----
    "hiteprotect.exe":  ("鸿合保护", "鸿合还原保护程序"),
    "hiteservice.exe":  ("鸿合保护", "鸿合保护服务进程"),
    "hitemanage.exe":   ("鸿合管家", "鸿合管家管理程序"),
    "hiteupdater.exe":  ("鸿合管家", "鸿合管家更新程序"),
    "hitetray.exe":     ("鸿合管家", "鸿合管家托盘程序"),
    "hitecloud.exe":    ("鸿合云", "鸿合云服务程序"),
    "hitecloudsvc.exe": ("鸿合云", "鸿合云服务进程"),
    "hiboard.exe":      ("鸿合白板", "鸿合白板程序"),
    "hiboardsvc.exe":   ("鸿合白板", "鸿合白板服务"),
    "hiteach.exe":      ("鸿合授课", "鸿合HiTeach授课"),
    "hiteachsvc.exe":   ("鸿合授课", "鸿合HiTeach服务"),
    "hiview.exe":       ("鸿合展台", "鸿合HiView展台"),
    "hiviewsvc.exe":    ("鸿合展台", "鸿合展台服务"),
    "hitedesktop.exe":  ("鸿合桌面", "鸿合桌面管理程序"),
    "hitedesktopsvc.exe":("鸿合桌面", "鸿合桌面服务"),
    "hiteclass.exe":    ("鸿合课堂", "鸿合课堂管理"),
    "hiteclasssvc.exe": ("鸿合课堂", "鸿合课堂服务"),
    "hiteguard.exe":    ("鸿合守护", "鸿合守护进程"),
    "hiteguardian.exe":  ("鸿合守护", "鸿合守护者"),
    "hitetools.exe":    ("鸿合工具", "鸿合工具箱"),
    "hiteconfig.exe":   ("鸿合配置", "鸿合配置工具"),
    "hitebackup.exe":   ("鸿合备份", "鸿合系统备份"),
    "hiterestore.exe":  ("鸿合还原", "鸿合系统还原"),
    "hitefreeze.exe":   ("鸿合冻结", "鸿合磁盘冻结"),
    "hiteprotect64.exe":("鸿合保护", "鸿合还原保护64位"),
    "hitemsg.exe":      ("鸿合消息", "鸿合消息推送"),
    "hitescreenshot.exe":("鸿合截屏", "鸿合截屏工具"),
    "hiteremote.exe":   ("鸿合远程", "鸿合远程控制"),
    "hitenetwork.exe":  ("鸿合网络", "鸿合网络管理"),
    "hiteboot.exe":     ("鸿合启动", "鸿合启动管理"),
    "hitepolicy.exe":   ("鸿合策略", "鸿合策略管理"),
    "hiteaudit.exe":    ("鸿合审计", "鸿合审计日志"),
    "hitelic.exe":      ("鸿合授权", "鸿合授权管理"),
}

# ---- 服务名 -> 软件映射 ----
SERVICE_MAP = {
    "dfserv":           ("冰点还原 Deep Freeze", "Deep Freeze服务"),
    "deepfrz":          ("冰点还原 Deep Freeze", "Deep Freeze核心"),
    "sdservice":        ("影子系统 Shadow Defender", "影子系统服务"),
    "hshield":          ("小哨兵还原精灵", "小哨兵服务"),
    "rvcontrol":        ("联想EDU保护", "联想EDU服务"),
    "ossservice":       ("噢易OSS保护", "噢易OSS服务"),
    "everrestore":      ("易速还原", "易速还原服务"),
    "rebornsvc":        ("还原精灵", "还原精灵服务"),
    "sentrysvc":        ("哨兵还原", "哨兵还原服务"),
    "nbmsvc":           ("网维大师", "网维大师服务"),
    "diskprotector":    ("磁盘保护", "磁盘保护服务"),
    "rvmgr":            ("还原管理", "还原管理服务"),
    "vfdisk":           ("虚拟磁盘", "虚拟磁盘保护"),
    "rdprotect":        ("重启保护", "重启保护服务"),
    "sfprotect":        ("安全保护", "安全保护服务"),
    "drvshield":        ("驱动保护", "驱动保护服务"),
    "clsmn":            ("网吧管理", "网吧管理服务"),
    "pcsecurity":       ("PC安全", "PC安全服务"),
    "btdownload":       ("BT下载保护", "BT下载保护服务"),
    "atprtmon":         ("还原监控", "还原监控服务"),

    # ---- 新增: 更多还原保护服务 ----
    "pwrshadow":        ("Power Shadow", "Power Shadow服务"),
    "shadowuser":       ("ShadowUser", "ShadowUser服务"),
    "shadowprotect":    ("ShadowProtect", "ShadowProtect服务"),
    "ctmservice":       ("Comodo Time Machine", "Comodo时间机器服务"),
    "rbmanager":        ("RollBack Rx", "RollBack Rx管理服务"),
    "shieldsvc":        ("Reboot Restore Rx", "Reboot Restore服务"),
    "drivevaccine":     ("Drive Vaccine", "Drive Vaccine服务"),
    "toolwizfreeze":    ("Toolwiz Time Freeze", "Toolwiz时间冻结服务"),
    "smartshield":      ("SmartShield", "SmartShield服务"),

    # 希沃
    "seewoservice":     ("希沃还原", "希沃还原保护服务"),
    "seewoprotect":     ("希沃还原", "希沃还原保护"),

    # 方正
    "founderprotect":   ("方正还原", "方正还原服务"),

    # 同方
    "tongfangprotect":  ("同方还原", "同方还原服务"),

    # 网众
    "netzoneservice":   ("网众Netzone", "网众无盘服务"),
    "netzonedisk":      ("网众Netzone", "网众磁盘保护服务"),

    # 锐起
    "richguide":        ("锐起无盘", "锐起无盘服务"),

    # 信佑
    "xinuprotect":      ("信佑还原", "信佑还原服务"),

    # 顺网
    "swgservice":       ("顺网网维", "顺网网维服务"),
    "swprotect":        ("顺网网维", "顺网磁盘保护服务"),

    # 易游
    "eeyooservice":     ("易游网娱", "易游网娱服务"),

    # 海光
    "haiguangprotect":  ("海光还原", "海光还原服务"),

    # 绿坝
    "lvbang":           ("绿坝花季护航", "绿坝服务"),

    # 通用
    "sysprotect":       ("系统保护", "通用系统保护服务"),
    "diskguard":        ("磁盘卫士", "磁盘卫士服务"),
    "pcprotect":        ("PC保护", "PC保护服务"),
    "rebootrestore":    ("重启还原", "重启还原服务"),
    "frozendisk":       ("冻结磁盘", "冻结磁盘服务"),

    # ---- 鸿合 HiteVision ----
    "hiteprotect":      ("鸿合保护", "鸿合还原保护服务"),
    "hiteservice":      ("鸿合保护", "鸿合保护核心服务"),
    "hitemanage":       ("鸿合管家", "鸿合管家服务"),
    "hiteupdater":      ("鸿合管家", "鸿合更新服务"),
    "hitecloud":        ("鸿合云", "鸿合云服务"),
    "hitecloudsvc":     ("鸿合云", "鸿合云后台服务"),
    "hiboard":          ("鸿合白板", "鸿合白板服务"),
    "hiboardsvc":       ("鸿合白板", "鸿合白板后台服务"),
    "hiteach":          ("鸿合授课", "鸿合HiTeach服务"),
    "hiteachsvc":       ("鸿合授课", "鸿合HiTeach后台服务"),
    "hiview":           ("鸿合展台", "鸿合展台服务"),
    "hiviewsvc":        ("鸿合展台", "鸿合展台后台服务"),
    "hitedesktop":      ("鸿合桌面", "鸿合桌面服务"),
    "hitedesktopsvc":   ("鸿合桌面", "鸿合桌面后台服务"),
    "hiteclass":        ("鸿合课堂", "鸿合课堂服务"),
    "hiteclasssvc":     ("鸿合课堂", "鸿合课堂后台服务"),
    "hiteguard":        ("鸿合守护", "鸿合守护服务"),
    "hiteguardian":     ("鸿合守护", "鸿合守护者服务"),
    "hitefreeze":       ("鸿合冻结", "鸿合磁盘冻结服务"),
    "hiterestore":      ("鸿合还原", "鸿合系统还原服务"),
    "hitenetwork":      ("鸿合网络", "鸿合网络管理服务"),
    "hiteboot":         ("鸿合启动", "鸿合启动管理服务"),
    "hitepolicy":       ("鸿合策略", "鸿合策略管理服务"),
    "hiteaudit":        ("鸿合审计", "鸿合审计服务"),
    "hitelic":          ("鸿合授权", "鸿合授权服务"),
}

# ---- 注册表路径 -> 软件映射 ----
REG_MAP = {
    r"SOFTWARE\Faronics":                       ("冰点还原 Deep Freeze", "Faronics注册表项"),
    r"SOFTWARE\WOW6432Node\Faronics":           ("冰点还原 Deep Freeze", "Faronics 64位注册表项"),
    r"SOFTWARE\ShadowDefender":                 ("影子系统", "影子系统注册表项"),
    r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Deep Freeze": ("冰点还原", "冰点卸载项"),
    r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Shadow Defender": ("影子系统", "影子卸载项"),
    r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\HShield": ("小哨兵", "小哨兵卸载项"),
    r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Reborn": ("还原精灵", "还原精灵卸载项"),
    r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\EverRestore": ("易速还原", "易速卸载项"),
    r"SOFTWARE\RvControl":                      ("联想EDU", "联想EDU注册表"),
    r"SOFTWARE\OSS":                            ("噢易OSS", "噢易注册表"),
    r"SOFTWARE\HShield":                        ("小哨兵", "小哨兵注册表"),
    r"SOFTWARE\Reborn":                         ("还原精灵", "还原精灵注册表"),
    r"SOFTWARE\EverRestore":                    ("易速还原", "易速注册表"),
    r"SOFTWARE\Sentry":                         ("哨兵还原", "哨兵注册表"),
    r"SOFTWARE\NetWareMaster":                  ("网维大师", "网维大师注册表"),
    r"SYSTEM\CurrentControlSet\Services\DeepFrz": ("冰点还原", "冰点驱动服务"),
    r"SYSTEM\CurrentControlSet\Services\DFServ":   ("冰点还原", "冰点服务"),

    # ---- 新增: 更多注册表项 ----
    r"SOFTWARE\PowerShadow":                    ("Power Shadow", "Power Shadow注册表"),
    r"SOFTWARE\ShadowUser":                     ("ShadowUser", "ShadowUser注册表"),
    r"SOFTWARE\Comodo\TimeMachine":             ("Comodo Time Machine", "Comodo时间机器注册表"),
    r"SOFTWARE\HorizonDataSys\RollBack":        ("RollBack Rx", "RollBack Rx注册表"),
    r"SOFTWARE\HorizonDataSys\RebootRestore":   ("Reboot Restore Rx", "Reboot Restore注册表"),
    r"SOFTWARE\Toolwiz\TimeFreeze":             ("Toolwiz Time Freeze", "Toolwiz时间冻结注册表"),
    r"SOFTWARE\SmartShield":                    ("SmartShield", "SmartShield注册表"),

    # 希沃
    r"SOFTWARE\Seewo\Protect":                  ("希沃还原", "希沃还原注册表"),
    r"SOFTWARE\Seewo":                          ("希沃还原", "希沃注册表"),

    # 方正
    r"SOFTWARE\Founder\Protect":                ("方正还原", "方正还原注册表"),

    # 同方
    r"SOFTWARE\TongFang\Protect":               ("同方还原", "同方还原注册表"),

    # 网众
    r"SOFTWARE\Netzone":                        ("网众Netzone", "网众注册表"),

    # 锐起
    r"SOFTWARE\RichGuide":                      ("锐起无盘", "锐起注册表"),

    # 信佑
    r"SOFTWARE\Xinu":                           ("信佑还原", "信佑注册表"),

    # 顺网
    r"SOFTWARE\Swg":                            ("顺网网维", "顺网注册表"),

    # 易游
    r"SOFTWARE\Eeyoo":                          ("易游网娱", "易游注册表"),

    # 海光
    r"SOFTWARE\HaiGuang":                       ("海光还原", "海光注册表"),

    # 绿坝
    r"SOFTWARE\LvBang":                         ("绿坝花季护航", "绿坝注册表"),

    # 更多冰点还原
    r"SOFTWARE\Faronics\Deep Freeze":           ("冰点还原 Deep Freeze", "冰点Deep Freeze注册表"),

    # 更多影子系统
    r"SOFTWARE\ShadowDefender\Settings":        ("影子系统", "影子系统设置注册表"),

    # 更多噢易OSS
    r"SOFTWARE\OSS\Settings":                   ("噢易OSS保护", "噢易OSS设置注册表"),

    # 更多联想EDU
    r"SOFTWARE\Lenovo\EDU":                     ("联想EDU保护", "联想EDU注册表"),

    # 通用保护
    r"SOFTWARE\SystemProtect":                  ("系统保护", "通用系统保护注册表"),
    r"SOFTWARE\DiskGuard":                      ("磁盘卫士", "磁盘卫士注册表"),

    # 卸载项补充
    r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\PowerShadow":    ("Power Shadow", "Power Shadow卸载项"),
    r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\RollBackRx":     ("RollBack Rx", "RollBack Rx卸载项"),
    r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\RebootRestore":  ("Reboot Restore Rx", "Reboot Restore卸载项"),
    r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\SmartShield":    ("SmartShield", "SmartShield卸载项"),
    r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\ToolwizFreeze":  ("Toolwiz Time Freeze", "Toolwiz卸载项"),
    r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\SeewoProtect":   ("希沃还原", "希沃卸载项"),
    r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Netzone":        ("网众Netzone", "网众卸载项"),

    # ---- 鸿合 HiteVision ----
    r"SOFTWARE\HiteVision":                    ("鸿合", "鸿合注册表项"),
    r"SOFTWARE\WOW6432Node\HiteVision":        ("鸿合", "鸿合64位注册表项"),
    r"SOFTWARE\HiteVision\Protect":            ("鸿合保护", "鸿合还原保护注册表"),
    r"SOFTWARE\HiteVision\Manager":            ("鸿合管家", "鸿合管家注册表"),
    r"SOFTWARE\HiteVision\Cloud":              ("鸿合云", "鸿合云注册表"),
    r"SOFTWARE\HiteVision\Desktop":            ("鸿合桌面", "鸿合桌面注册表"),
    r"SOFTWARE\HiteVision\HiBoard":            ("鸿合白板", "鸿合白板注册表"),
    r"SOFTWARE\HiteVision\HiTeach":            ("鸿合授课", "鸿合授课注册表"),
    r"SOFTWARE\HiteVision\HiView":             ("鸿合展台", "鸿合展台注册表"),
    r"SOFTWARE\HiteVision\Freeze":             ("鸿合冻结", "鸿合磁盘冻结注册表"),
    r"SOFTWARE\HiteVision\Restore":            ("鸿合还原", "鸿合系统还原注册表"),
    r"SOFTWARE\HiteVision\Policy":             ("鸿合策略", "鸿合策略注册表"),
    r"SOFTWARE\HiteVision\Guard":              ("鸿合守护", "鸿合守护注册表"),
    r"SOFTWARE\HiteVision\Network":            ("鸿合网络", "鸿合网络注册表"),
    r"SOFTWARE\HiteVision\License":            ("鸿合授权", "鸿合授权注册表"),

    # 鸿合驱动服务
    r"SYSTEM\CurrentControlSet\Services\HiteProtect":  ("鸿合保护", "鸿合保护驱动服务"),
    r"SYSTEM\CurrentControlSet\Services\HiteService":  ("鸿合保护", "鸿合核心服务"),
    r"SYSTEM\CurrentControlSet\Services\HiteFreeze":   ("鸿合冻结", "鸿合冻结驱动服务"),
    r"SYSTEM\CurrentControlSet\Services\HiteGuard":    ("鸿合守护", "鸿合守护驱动服务"),

    # 鸿合卸载项
    r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\HiteVision":    ("鸿合", "鸿合卸载项"),
    r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\HiteProtect":   ("鸿合保护", "鸿合保护卸载项"),
    r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\HiteManager":   ("鸿合管家", "鸿合管家卸载项"),
    r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\HiBoard":       ("鸿合白板", "鸿合白板卸载项"),
    r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\HiTeach":       ("鸿合授课", "鸿合授课卸载项"),
    r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\HiView":        ("鸿合展台", "鸿合展台卸载项"),
    r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\HiteCloud":     ("鸿合云", "鸿合云卸载项"),
    r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\HiteDesktop":   ("鸿合桌面", "鸿合桌面卸载项"),
}

# ---- 常见还原软件文件路径 ----
FILE_PATHS = [
    (r"C:\Program Files\Faronics",              "冰点还原"),
    (r"C:\Program Files (x86)\Faronics",        "冰点还原"),
    (r"C:\Program Files\Shadow Defender",       "影子系统"),
    (r"C:\Program Files (x86)\Shadow Defender", "影子系统"),
    (r"C:\Program Files\HShield",               "小哨兵"),
    (r"C:\Program Files (x86)\HShield",         "小哨兵"),
    (r"C:\Program Files\EverRestore",           "易速还原"),
    (r"C:\Program Files (x86)\EverRestore",     "易速还原"),
    (r"C:\Program Files\Reborn",                "还原精灵"),
    (r"C:\Windows\System32\drivers\deepfrz.sys","冰点还原驱动"),
    (r"C:\Windows\System32\drivers\dfdisk.sys", "冰点还原磁盘驱动"),
    (r"C:\Windows\System32\drivers\shadowdrv.sys","影子系统驱动"),
    (r"C:\Windows\System32\drivers\hshield.sys","小哨兵驱动"),
    (r"C:\Windows\System32\drivers\reborn.sys", "还原精灵驱动"),
    (r"C:\Windows\System32\drivers\sentry.sys", "哨兵还原驱动"),
    (r"C:\Windows\System32\drivers\rvprotect.sys","联想EDU驱动"),
    (r"C:\Windows\System32\drivers\ossprot.sys","噢易保护驱动"),
    (r"C:\Windows\System32\drivers\vfdrv.sys",  "虚拟磁盘驱动"),
    (r"C:\Windows\System32\drivers\evrest.sys", "易速还原驱动"),

    # ---- 新增: 更多文件路径 ----
    (r"C:\Program Files\Power Shadow",           "Power Shadow"),
    (r"C:\Program Files (x86)\Power Shadow",     "Power Shadow"),
    (r"C:\Program Files\ShadowUser",             "ShadowUser"),
    (r"C:\Program Files (x86)\ShadowUser",       "ShadowUser"),
    (r"C:\Program Files\Comodo\Time Machine",    "Comodo Time Machine"),
    (r"C:\Program Files (x86)\Comodo\Time Machine","Comodo Time Machine"),
    (r"C:\Program Files\HorizonDataSys",         "RollBack Rx/Reboot Restore"),
    (r"C:\Program Files (x86)\HorizonDataSys",   "RollBack Rx/Reboot Restore"),
    (r"C:\Program Files\Toolwiz\TimeFreeze",     "Toolwiz Time Freeze"),
    (r"C:\Program Files (x86)\Toolwiz\TimeFreeze","Toolwiz Time Freeze"),
    (r"C:\Program Files\SmartShield",            "SmartShield"),
    (r"C:\Program Files (x86)\SmartShield",      "SmartShield"),

    # 希沃
    (r"C:\Program Files\Seewo\Protect",          "希沃还原"),
    (r"C:\Program Files (x86)\Seewo\Protect",    "希沃还原"),
    (r"C:\Program Files\Seewo",                  "希沃"),

    # 方正
    (r"C:\Program Files\Founder\Protect",        "方正还原"),
    (r"C:\Program Files (x86)\Founder\Protect",  "方正还原"),

    # 同方
    (r"C:\Program Files\TongFang\Protect",       "同方还原"),
    (r"C:\Program Files (x86)\TongFang\Protect", "同方还原"),

    # 网众
    (r"C:\Program Files\Netzone",                "网众Netzone"),
    (r"C:\Program Files (x86)\Netzone",          "网众Netzone"),

    # 锐起
    (r"C:\Program Files\RichGuide",              "锐起无盘"),
    (r"C:\Program Files (x86)\RichGuide",        "锐起无盘"),

    # 信佑
    (r"C:\Program Files\Xinu",                   "信佑还原"),
    (r"C:\Program Files (x86)\Xinu",             "信佑还原"),

    # 顺网
    (r"C:\Program Files\Swg",                    "顺网网维"),
    (r"C:\Program Files (x86)\Swg",              "顺网网维"),

    # 易游
    (r"C:\Program Files\Eeyoo",                  "易游网娱"),
    (r"C:\Program Files (x86)\Eeyoo",            "易游网娱"),

    # 海光
    (r"C:\Program Files\HaiGuang",               "海光还原"),
    (r"C:\Program Files (x86)\HaiGuang",         "海光还原"),

    # 绿坝
    (r"C:\Program Files\LvBang",                 "绿坝花季护航"),
    (r"C:\Program Files (x86)\LvBang",           "绿坝花季护航"),

    # 更多驱动文件
    (r"C:\Windows\System32\drivers\pwrshadow.sys","Power Shadow驱动"),
    (r"C:\Windows\System32\drivers\ctm.sys",     "Comodo Time Machine驱动"),
    (r"C:\Windows\System32\drivers\rbmanager.sys","RollBack Rx驱动"),
    (r"C:\Windows\System32\drivers\shield.sys",  "Reboot Restore驱动"),
    (r"C:\Windows\System32\drivers\smartshield.sys","SmartShield驱动"),
    (r"C:\Windows\System32\drivers\seewoprot.sys","希沃还原驱动"),
    (r"C:\Windows\System32\drivers\founderprot.sys","方正还原驱动"),
    (r"C:\Windows\System32\drivers\tongfangprot.sys","同方还原驱动"),
    (r"C:\Windows\System32\drivers\netzonedisk.sys","网众磁盘驱动"),
    (r"C:\Windows\System32\drivers\richguide.sys","锐起无盘驱动"),
    (r"C:\Windows\System32\drivers\xinuprot.sys","信佑还原驱动"),
    (r"C:\Windows\System32\drivers\swprotect.sys","顺网保护驱动"),
    (r"C:\Windows\System32\drivers\eeyooprot.sys","易游保护驱动"),
    (r"C:\Windows\System32\drivers\haiguangprot.sys","海光还原驱动"),
    (r"C:\Windows\System32\drivers\frozendisk.sys","冻结磁盘驱动"),
    (r"C:\Windows\System32\drivers\sysprotect.sys","系统保护驱动"),
    (r"C:\Windows\System32\drivers\diskguard.sys","磁盘卫士驱动"),

    # ---- 鸿合 HiteVision ----
    (r"C:\Program Files\HiteVision",                "鸿合"),
    (r"C:\Program Files (x86)\HiteVision",          "鸿合"),
    (r"C:\Program Files\HiteVision\Protect",        "鸿合保护"),
    (r"C:\Program Files (x86)\HiteVision\Protect",  "鸿合保护"),
    (r"C:\Program Files\HiteVision\Manager",        "鸿合管家"),
    (r"C:\Program Files (x86)\HiteVision\Manager",  "鸿合管家"),
    (r"C:\Program Files\HiteVision\Cloud",          "鸿合云"),
    (r"C:\Program Files (x86)\HiteVision\Cloud",    "鸿合云"),
    (r"C:\Program Files\HiteVision\HiBoard",        "鸿合白板"),
    (r"C:\Program Files (x86)\HiteVision\HiBoard",  "鸿合白板"),
    (r"C:\Program Files\HiteVision\HiTeach",        "鸿合授课"),
    (r"C:\Program Files (x86)\HiteVision\HiTeach",  "鸿合授课"),
    (r"C:\Program Files\HiteVision\HiView",         "鸿合展台"),
    (r"C:\Program Files (x86)\HiteVision\HiView",   "鸿合展台"),
    (r"C:\Program Files\HiteVision\Desktop",        "鸿合桌面"),
    (r"C:\Program Files (x86)\HiteVision\Desktop",  "鸿合桌面"),
    (r"C:\Program Files\HiteVision\Tools",          "鸿合工具"),
    (r"C:\Program Files (x86)\HiteVision\Tools",    "鸿合工具"),
    (r"C:\ProgramData\HiteVision",                  "鸿合数据"),
    (r"C:\HiteVision",                              "鸿合根目录"),
    (r"D:\HiteVision",                              "鸿合根目录D盘"),

    # 鸿合驱动
    (r"C:\Windows\System32\drivers\hiteprotect.sys","鸿合保护驱动"),
    (r"C:\Windows\System32\drivers\hiteservice.sys","鸿合核心驱动"),
    (r"C:\Windows\System32\drivers\hitefreeze.sys", "鸿合冻结驱动"),
    (r"C:\Windows\System32\drivers\hiteguard.sys",  "鸿合守护驱动"),
    (r"C:\Windows\System32\drivers\hiterestore.sys","鸿合还原驱动"),
    (r"C:\Windows\System32\drivers\hitenetwork.sys","鸿合网络驱动"),
]

# ---- 关键驱动文件名 -> 软件映射 ----
DRIVER_MAP = {
    "deepfrz.sys":  "冰点还原 Deep Freeze",
    "dfdisk.sys":   "冰点还原 Deep Freeze",
    "shadowdrv.sys":"影子系统 Shadow Defender",
    "hshield.sys":  "小哨兵还原精灵",
    "reborn.sys":   "还原精灵",
    "sentry.sys":   "哨兵还原",
    "rvprotect.sys":"联想EDU保护",
    "ossprot.sys":  "噢易OSS保护",
    "vfdrv.sys":    "虚拟磁盘保护",
    "evrest.sys":   "易速还原",
    "diskprot.sys": "磁盘保护",
    "protfs.sys":   "保护文件系统",
    "rdprotect.sys":"重启保护",

    # ---- 新增: 更多驱动 ----
    "pwrshadow.sys":    "Power Shadow",
    "ctm.sys":          "Comodo Time Machine",
    "rbmanager.sys":    "RollBack Rx",
    "shield.sys":       "Reboot Restore Rx",
    "drivevaccine.sys": "Drive Vaccine",
    "toolwizfreeze.sys":"Toolwiz Time Freeze",
    "smartshield.sys":  "SmartShield",
    "ssprotect.sys":    "SmartShield",
    "seewoprot.sys":    "希沃还原",
    "founderprot.sys":  "方正还原",
    "tongfangprot.sys": "同方还原",
    "netzonedisk.sys":  "网众Netzone",
    "richguide.sys":    "锐起无盘",
    "xinuprot.sys":     "信佑还原",
    "swprotect.sys":    "顺网网维",
    "eeyooprot.sys":    "易游网娱",
    "haiguangprot.sys": "海光还原",
    "frozendisk.sys":   "冻结磁盘",
    "sysprotect.sys":   "系统保护",
    "diskguard.sys":    "磁盘卫士",
    "lvbang.sys":       "绿坝花季护航",
    "shadowuser.sys":   "ShadowUser",
    "dfserv64.sys":     "冰点还原64位",

    # ---- 鸿合 HiteVision ----
    "hiteprotect.sys":  "鸿合保护",
    "hiteservice.sys":  "鸿合保护",
    "hitefreeze.sys":   "鸿合冻结",
    "hiteguard.sys":    "鸿合守护",
    "hiterestore.sys":  "鸿合还原",
    "hitenetwork.sys":  "鸿合网络",
    "hiboard.sys":      "鸿合白板",
    "hitedesktop.sys":  "鸿合桌面",
}


def detect_all():
    """全面检测，返回所有发现的还原保护项目。"""
    results = []  # list of DetectedItem

    # 1. 进程检测
    print("  [*] 扫描进程...")
    tasklist = run_cmd(["tasklist", "/FO", "CSV", "/V"]).lower()
    for proc_name, (soft, desc) in PROCESS_MAP.items():
        if proc_name.lower() in tasklist:
            results.append(DetectedItem("进程", soft, desc, proc=proc_name))

    # 2. 服务检测 — 精确匹配服务名，避免子串误报
    print("  [*] 扫描服务...")
    sc_out = run_cmd(["sc", "query", "state=", "all", "type=", "service"]).lower()
    # 从 sc query 输出中提取所有服务名（SERVICE_NAME: xxx）
    import re
    svc_names_found = re.findall(r"service_name:\s*(\S+)", sc_out)
    for svc_name, (soft, desc) in SERVICE_MAP.items():
        if svc_name.lower() in [s.lower() for s in svc_names_found]:
            results.append(DetectedItem("服务", soft, desc, svc=svc_name))

    # 3. 注册表检测
    print("  [*] 扫描注册表...")
    for reg_path, (soft, desc) in REG_MAP.items():
        for hive_name, hive in [("HKLM", winreg.HKEY_LOCAL_MACHINE), ("HKCU", winreg.HKEY_CURRENT_USER)]:
            try:
                key = winreg.OpenKey(hive, reg_path)
                winreg.CloseKey(key)
                results.append(DetectedItem("注册表", soft, f"{desc} ({hive_name})", reg=f"{hive_name}\\{reg_path}"))
            except FileNotFoundError:
                pass

    # 4. 文件路径检测
    print("  [*] 扫描文件路径...")
    for fpath, soft in FILE_PATHS:
        if os.path.exists(fpath):
            results.append(DetectedItem("文件", soft, f"安装目录存在: {fpath}", path=fpath))

    # 5. 驱动文件检测
    print("  [*] 扫描系统驱动...")
    driver_dir = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "drivers")
    for drv, soft in DRIVER_MAP.items():
        drv_path = os.path.join(driver_dir, drv)
        if os.path.exists(drv_path):
            results.append(DetectedItem("驱动", soft, f"保护驱动存在: {drv}", path=drv_path))

    # 6. WMI 驱动检测
    print("  [*] 通过WMI扫描驱动...")
    wmi_out = run_cmd(["wmic", "sysdriver", "get", "Name,DisplayName,PathName", "/FORMAT:LIST"])
    for drv, soft in DRIVER_MAP.items():
        if drv.lower() in wmi_out.lower():
            results.append(DetectedItem("WMI驱动", soft, f"WMI中发现驱动: {drv}"))

    # 7. 开机启动项
    print("  [*] 扫描启动项...")
    for reg_run in [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"),
    ]:
        try:
            key = winreg.OpenKey(reg_run[0], reg_run[1])
            i = 0
            while True:
                try:
                    name, value, _ = winreg.EnumValue(key, i)
                    lower_val = value.lower()
                    for proc_name, (soft, _) in PROCESS_MAP.items():
                        if proc_name.replace(".exe", "").lower() in lower_val:
                            results.append(DetectedItem("启动项", soft, f"{name} -> {value}"))
                    i += 1
                except OSError:
                    break
            winreg.CloseKey(key)
        except:
            pass

    # 8. 计划任务 — 仅匹配高置信度关键词，避免泛匹配
    print("  [*] 扫描计划任务...")
    schtasks = run_cmd(["schtasks", "/query", "/FO", "CSV", "/V"]).lower()
    TASK_KEYWORDS = {
        "frzstate2k": "冰点还原", "dfserv": "冰点还原", "deepfrz": "冰点还原",
        "shadowdefender": "影子系统", "sdservice": "影子系统",
        "hshield": "小哨兵", "reborn": "还原精灵", "sentry": "哨兵还原",
        "ossservice": "噢易OSS", "everrestore": "易速还原",
        "rvcontrol": "联想EDU", "diskprotector": "磁盘保护",
        "nbmsvc": "网维大师", "rvmgr": "还原管理",

        # ---- 新增: 更多计划任务关键词 ----
        "pwrshadow": "Power Shadow", "shadowuser": "ShadowUser",
        "shadowprotect": "ShadowProtect", "ctmservice": "Comodo Time Machine",
        "rbmanager": "RollBack Rx", "shieldsvc": "Reboot Restore Rx",
        "drivevaccine": "Drive Vaccine", "toolwizfreeze": "Toolwiz Time Freeze",
        "smartshield": "SmartShield", "ssservice": "SmartShield",
        "seewoservice": "希沃还原", "seewoprotect": "希沃还原",
        "founderprotect": "方正还原", "tongfangprotect": "同方还原",
        "netzoneservice": "网众Netzone", "netzonedisk": "网众Netzone",
        "richguide": "锐起无盘", "xinuprotect": "信佑还原",
        "swgservice": "顺网网维", "swprotect": "顺网网维",
        "eeyoo": "易游网娱", "eeyooservice": "易游网娱",
        "haiguangprotect": "海光还原", "lvbang": "绿坝花季护航",
        "sysprotect": "系统保护", "diskguard": "磁盘卫士",
        "frozendisk": "冻结磁盘", "rebootrestore": "重启还原",

        # ---- 鸿合 HiteVision ----
        "hiteprotect": "鸿合保护", "hiteservice": "鸿合保护",
        "hitemanage": "鸿合管家", "hiteupdater": "鸿合管家",
        "hitecloud": "鸿合云", "hitecloudsvc": "鸿合云",
        "hiboard": "鸿合白板", "hiboardsvc": "鸿合白板",
        "hiteach": "鸿合授课", "hiteachsvc": "鸿合授课",
        "hiview": "鸿合展台", "hiviewsvc": "鸿合展台",
        "hitedesktop": "鸿合桌面", "hitedesktopsvc": "鸿合桌面",
        "hiteclass": "鸿合课堂", "hiteclasssvc": "鸿合课堂",
        "hiteguard": "鸿合守护", "hiteguardian": "鸿合守护",
        "hitefreeze": "鸿合冻结", "hiterestore": "鸿合还原",
        "hitenetwork": "鸿合网络", "hiteboot": "鸿合启动",
        "hitepolicy": "鸿合策略", "hiteaudit": "鸿合审计",
        "hitelic": "鸿合授权",
    }
    for keyword, soft in TASK_KEYWORDS.items():
        if keyword in schtasks:
            results.append(DetectedItem("计划任务", soft, f"计划任务中发现: {keyword}"))

    # 9. 检查磁盘过滤驱动
    print("  [*] 扫描磁盘过滤驱动...")
    filter_out = run_cmd(["reg", "query",
                          r"HKLM\SYSTEM\CurrentControlSet\Control\Class\{4d36e967-e325-11ce-bfc1-08002be10318}",
                          "/v", "UpperFilters"])
    for drv, soft in DRIVER_MAP.items():
        if drv.replace(".sys", "").lower() in filter_out.lower():
            results.append(DetectedItem("磁盘过滤", soft, f"磁盘过滤驱动: {drv}"))

    # 10. 检查卷过滤驱动
    print("  [*] 扫描卷过滤驱动...")
    vol_filter = run_cmd(["reg", "query",
                          r"HKLM\SYSTEM\CurrentControlSet\Control\Class\{71a27cdd-812a-11d0-bec7-08002be2092f}",
                          "/v", "UpperFilters"])
    for drv, soft in DRIVER_MAP.items():
        if drv.replace(".sys", "").lower() in vol_filter.lower():
            results.append(DetectedItem("卷过滤", soft, f"卷过滤驱动: {drv}"))

    # 去重
    seen = set()
    unique = []
    for item in results:
        key = (item.category, item.name, item.detail)
        if key not in seen:
            seen.add(key)
            unique.append(item)

    return unique


def print_results(items):
    """打印检测结果。"""
    if not items:
        print("\n  [-] 未检测到任何已知还原保护软件")
        print("  [?] 可能是未知的保护方案，建议人工排查")
        return

    # 按软件分组
    by_soft = {}
    for item in items:
        by_soft.setdefault(item.name, []).append(item)

    print(f"\n  [!] 共发现 {len(by_soft)} 种还原保护软件，{len(items)} 条证据:\n")

    for i, (soft, evidence) in enumerate(by_soft.items(), 1):
        print(f"  ┌─ [{i}] {soft}")
        for ev in evidence:
            icon = {"进程": ">", "服务": "~", "注册表": "#", "文件": "@", "驱动": "!",
                    "WMI驱动": "!", "启动项": "+", "计划任务": "*", "磁盘过滤": "^", "卷过滤": "^"}
            print(f"  │  [{icon.get(ev.category, '?')}] {ev.category}: {ev.detail}")
        print(f"  └─")
        print()


# ============================================================
#  安全关闭模块 — 不杀进程、不改驱动、不删注册表
# ============================================================

def safe_disable_deep_freeze(detected_items):
    """安全关闭冰点还原：引导用户通过官方方式解冻。"""
    print("\n  ┌─ 冰点还原 Deep Freeze — 安全关闭")
    print("  │")
    print_risk_warning("安全", "以下操作不会破坏系统，仅修改冰点启动模式")

    # 步骤1: 尝试命令行解冻
    print("  │")
    print("  │  [1] 尝试命令行切换到解冻模式...")
    df_path = None
    for item in detected_items:
        if item.path and "faronics" in item.path.lower():
            df_path = item.path
            break

    # 尝试常见安装路径
    possible_paths = [
        r"C:\Program Files\Faronics\Deep Freeze\DFServ.exe",
        r"C:\Program Files (x86)\Faronics\Deep Freeze\DFServ.exe",
    ]
    if df_path:
        possible_paths.insert(0, os.path.join(df_path, "DFServ.exe"))

    thawed = False
    for dfserv in possible_paths:
        if os.path.exists(dfserv):
            # 尝试设置下次启动为解冻
            out = run_cmd([dfserv, "bootthawed"], timeout=10)
            if "成功" in out or "success" in out.lower() or out.strip() == "":
                print(f"  │  [OK] 已设置下次启动为解冻模式")
                thawed = True
                break
            # 也尝试另一个参数
            out = run_cmd([dfserv, "/bootthawed"], timeout=10)
            if "成功" in out or "success" in out.lower() or out.strip() == "":
                print(f"  │  [OK] 已设置下次启动为解冻模式")
                thawed = True
                break

    if not thawed:
        print("  │  [-] 命令行解冻未成功（可能需要密码或路径不同）")

    # 步骤2: 引导手动操作
    print("  │")
    print_manual_guide("冰点还原解冻", [
        "在系统托盘找到冰点图标（熊掌图标）",
        "按住 Ctrl+Alt+Shift+F6 打开冰点控制台",
        "选择 'Boot Thawed'（解冻启动）",
        "点击 OK，然后重启电脑",
        "重启后冰点图标变红 = 已解冻，此时可正常卸载",
        "如需卸载: 控制面板 -> 程序 -> 卸载 Deep Freeze",
    ])

    # 步骤3: 提供卸载信息
    print("  │")
    print("  │  [2] 查找卸载程序...")
    uninst = find_uninstall_cmd("Deep Freeze")
    if uninst:
        for name, cmd in uninst:
            print(f"  │  [OK] 找到: {name}")
            if cmd:
                print(f"  │       卸载命令: {cmd}")
    else:
        print("  │  [-] 未找到卸载程序，请使用控制面板卸载")

    print("  │")
    print("  └─ 操作完成。请先解冻再卸载，不要直接强杀！")


def safe_disable_shadow_defender(detected_items):
    """安全关闭影子系统：引导用户退出影子模式。"""
    print("\n  ┌─ 影子系统 Shadow Defender — 安全关闭")
    print("  │")
    print_risk_warning("安全", "以下操作通过软件自身功能退出影子模式")

    # 步骤1: 检查是否在影子模式
    print("  │")
    print("  │  [1] 检查影子系统状态...")
    sd_path = None
    for item in detected_items:
        if item.path and "shadow defender" in item.path.lower():
            sd_path = item.path
            break

    possible_paths = [
        r"C:\Program Files\Shadow Defender\ShadowDefender.exe",
        r"C:\Program Files (x86)\Shadow Defender\ShadowDefender.exe",
    ]
    if sd_path:
        possible_paths.insert(0, os.path.join(sd_path, "ShadowDefender.exe"))

    exited = False
    for sd_exe in possible_paths:
        if os.path.exists(sd_exe):
            # 尝试退出影子模式
            out = run_cmd([sd_exe, "/exitshadow"], timeout=10)
            if "成功" in out or "success" in out.lower() or out.strip() == "":
                print(f"  │  [OK] 已发送退出影子模式指令")
                exited = True
                break

    if not exited:
        print("  │  [-] 自动退出未成功，请手动操作")

    # 步骤2: 引导手动操作
    print("  │")
    print_manual_guide("影子系统退出", [
        "在系统托盘找到 Shadow Defender 图标",
        "双击打开 Shadow Defender 控制台",
        "点击 'Exit Shadow Mode'（退出影子模式）",
        "确认后重启电脑",
        "重启后系统恢复正常写入模式",
        "如需卸载: 控制面板 -> 程序 -> 卸载 Shadow Defender",
    ])

    # 步骤3: 提供卸载信息
    print("  │")
    print("  │  [2] 查找卸载程序...")
    uninst = find_uninstall_cmd("Shadow Defender")
    if uninst:
        for name, cmd in uninst:
            print(f"  │  [OK] 找到: {name}")
            if cmd:
                print(f"  │       卸载命令: {cmd}")

    print("  │")
    print("  └─ 操作完成。请先退出影子模式再卸载！")


def safe_disable_hitevision(detected_items):
    """安全关闭鸿合保护：通过管理后台或温和方式。"""
    print("\n  ┌─ 鸿合 HiteVision — 安全关闭")
    print("  │")
    print_risk_warning("低", "以下操作温和停止非核心服务，不触及驱动文件")

    # 步骤1: 温和停止非核心服务（不杀进程）
    print("  │")
    print("  │  [1] 温和停止非核心鸿合服务...")
    non_core_services = [
        "HiteUpdater", "HiteCloud", "HiteCloudSvc", "HiteBackup",
        "HiteAudit", "HiteMsg", "HiteLic",
    ]
    stopped, disabled = safe_disable_services(non_core_services)
    print(f"  │      停止: {stopped} 个, 禁用自启: {disabled} 个")

    # 步骤2: 尝试查找鸿合管理工具
    print("  │")
    print("  │  [2] 查找鸿合管理工具...")
    hite_paths = [
        r"C:\Program Files\HiteVision\Manager\HiteManage.exe",
        r"C:\Program Files (x86)\HiteVision\Manager\HiteManage.exe",
        r"C:\Program Files\HiteVision\Tools\HiteConfig.exe",
        r"C:\Program Files (x86)\HiteVision\Tools\HiteConfig.exe",
        r"C:\Program Files\HiteVision\Policy\HitePolicy.exe",
        r"C:\Program Files (x86)\HiteVision\Policy\HitePolicy.exe",
    ]
    found_tools = []
    for p in hite_paths:
        if os.path.exists(p):
            found_tools.append(p)
            print(f"  │  [OK] 找到: {p}")

    # 步骤3: 查找卸载程序
    print("  │")
    print("  │  [3] 查找鸿合卸载程序...")
    uninst = find_uninstall_cmd("HiteVision")
    if not uninst:
        uninst = find_uninstall_cmd("鸿合")
    if uninst:
        for name, cmd in uninst:
            print(f"  │  [OK] 找到: {name}")
            if cmd:
                print(f"  │       卸载命令: {cmd}")
    else:
        print("  │  [-] 未找到卸载程序")

    # 步骤4: 手动操作指南
    print("  │")
    print_manual_guide("鸿合保护关闭", [
        "打开鸿合管家（桌面上通常有快捷方式）",
        "进入 '设置' 或 '保护管理' 页面",
        "找到 '还原保护' 或 '磁盘保护' 选项",
        "将其关闭或设为 '不保护'",
        "保存设置后重启电脑",
        "如需卸载: 使用鸿合管家自带的卸载功能",
        "或: 控制面板 -> 程序 -> 卸载 HiteVision 相关程序",
        "注意: 部分鸿合一体机需要在BIOS中关闭保护",
    ])

    print("  │")
    print("  └─ 温和操作完成。核心保护需通过鸿合管理后台关闭。")


def safe_disable_generic(software_name, detected_items):
    """安全通用关闭：温和停止服务 + 引导用户手动操作。"""
    print(f"\n  ┌─ {software_name} — 安全关闭")
    print("  │")
    print_risk_warning("低", "使用温和方式，不触及驱动和进程")

    action_count = 0

    # 步骤1: 温和停止并禁用相关服务
    print("  │")
    print("  │  [1] 温和停止相关服务...")
    for item in detected_items:
        if item.svc:
            if safe_sc_stop(item.svc):
                action_count += 1
            if safe_sc_disable(item.svc):
                action_count += 1

    # 步骤2: 查找卸载程序
    print("  │")
    print("  │  [2] 查找卸载程序...")
    uninst = find_uninstall_cmd(software_name)
    if uninst:
        for name, cmd in uninst:
            print(f"  │  [OK] 找到: {name}")
            if cmd:
                print(f"  │       卸载命令: {cmd}")
                action_count += 1
    else:
        print(f"  │  [-] 未找到 {software_name} 的卸载程序")

    # 步骤3: 通用手动指南
    print("  │")
    print_manual_guide(f"{software_name} 关闭", [
        "在系统托盘中找到该软件的图标",
        "右键查看是否有 '关闭保护' 或 '退出' 选项",
        "如果没有，打开软件主界面查找设置",
        "查找 '还原保护' / '磁盘保护' / 'Freeze' 相关选项",
        "关闭保护后重启电脑",
        "通过控制面板正常卸载软件",
    ])

    # 步骤4: 检查驱动文件（仅报告，不操作）
    print("  │")
    print("  │  [3] 检查保护驱动状态（仅报告）...")
    driver_dir = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "drivers")
    for item in detected_items:
        if item.category in ("驱动", "WMI驱动", "磁盘过滤", "卷过滤") and item.path:
            drv_name = None
            if ":" in item.detail:
                drv_name = item.detail.split(":")[-1].strip()
            if drv_name:
                drv_path = os.path.join(driver_dir, drv_name)
                if os.path.exists(drv_path):
                    print(f"  │  [!] 驱动存在: {drv_name}")
                    print(f"  │      [?] 请在保护关闭后再卸载，不要直接删除驱动文件")

    if action_count == 0:
        print("  │")
        print("  │  [!] 未能自动执行任何操作。")
        print(f"  │  [?] 建议: 搜索 '{software_name} 卸载方法' 或联系IT部门。")
    else:
        print(f"  │")
        print(f"  │  [*] 已执行 {action_count} 项安全操作")

    print("  │")
    print(f"  └─ {software_name} 安全操作完成。")


def safe_disable_software(software_name, detected_items):
    """安全关闭路由：根据软件名分发到对应的安全关闭函数。"""
    name_lower = software_name.lower()

    if "deep freeze" in name_lower or "冰点" in name_lower:
        safe_disable_deep_freeze(detected_items)
    elif "shadow defender" in name_lower or "影子" in name_lower:
        safe_disable_shadow_defender(detected_items)
    elif "鸿合" in name_lower or "hitevision" in name_lower or "hite" in name_lower or "hiboard" in name_lower or "hiteach" in name_lower or "hiview" in name_lower:
        safe_disable_hitevision(detected_items)
    else:
        safe_disable_generic(software_name, detected_items)


def safe_uninstall_software(software_name, detected_items):
    """安全卸载：查找并引导用户使用正规卸载流程。"""
    print(f"\n  ┌─ 卸载: {software_name}")
    print("  │")
    print_risk_warning("安全", "使用软件自带的卸载程序，最安全的方式")

    # 查找卸载程序
    print("  │")
    print("  │  [1] 查找卸载程序...")
    uninst = find_uninstall_cmd(software_name)

    if uninst:
        print(f"  │  [!] 找到 {len(uninst)} 个卸载程序:")
        for name, cmd in uninst:
            print(f"  │      - {name}")
            if cmd:
                print(f"  │        命令: {cmd}")
                print(f"  │")
                confirm = input(f"  │      是否执行卸载? (y/n): ").strip().lower()
                if confirm == 'y':
                    print(f"  │      执行: {cmd}")
                    out = run_cmd(cmd, timeout=120)
                    print(f"  │      结果: {out.strip()[:200]}")
                else:
                    print(f"  │      已跳过")
    else:
        print(f"  │  [-] 未在注册表中找到 {software_name} 的卸载程序")
        print_manual_guide(f"{software_name} 手动卸载", [
            "打开 控制面板 -> 程序和功能",
            "在列表中找到相关程序",
            "右键选择 '卸载'",
            "按提示完成卸载",
            "如果列表中找不到，尝试在安装目录中找 Uninstall.exe",
        ])

    print("  │")
    print(f"  └─ 卸载流程完成。建议重启电脑。")


def selective_force_kill():
    """选择性强杀：让用户逐个选择要强制终止的进程和服务。"""
    print_header("选择性强制关闭")
    print_risk_warning("高", "强制关闭保护进程可能导致蓝屏(BSOD)或系统不稳定！")
    print("  [?] 请先尝试 [2] 安全关闭保护，仅在安全方式无效时使用此功能")
    print()

    items = detect_all()
    if not items:
        print("  [-] 未检测到任何还原保护软件。")
        return

    # 构建可操作的项目列表（进程 + 服务）
    killable = []  # (类型, 名称, 所属软件, 描述)

    for item in items:
        if item.proc:
            killable.append(("进程", item.proc, item.name, item.detail))
        if item.svc:
            killable.append(("服务", item.svc, item.name, item.detail))

    if not killable:
        print("  [-] 未发现可操作的进程或服务。")
        return

    # 去重
    seen = set()
    unique_killable = []
    for k in killable:
        key = (k[0], k[1])
        if key not in seen:
            seen.add(key)
            unique_killable.append(k)

    killable = unique_killable

    # 显示列表
    print(f"  共发现 {len(killable)} 个可操作的进程/服务:\n")
    for i, (typ, name, soft, desc) in enumerate(killable, 1):
        color = "\033[91m" if typ == "进程" else "\033[93m"
        reset = "\033[0m"
        print(f"    {color}[{i:2d}]{reset} [{typ}] {name}  ({soft})")
        print(f"           {desc}")

    print(f"\n    [A] 全部选择")
    print(f"    [0] 返回")
    print()

    sel = input("  输入要强制关闭的编号（多个用逗号分隔，如 1,3,5）: ").strip()

    if sel == "0" or sel == "":
        return

    # 解析选择
    selected_indices = []
    if sel.lower() == "a":
        selected_indices = list(range(len(killable)))
    else:
        for part in sel.replace("，", ",").split(","):
            part = part.strip()
            if part.isdigit():
                idx = int(part) - 1
                if 0 <= idx < len(killable):
                    selected_indices.append(idx)

    if not selected_indices:
        print("  无效选择")
        return

    # 显示即将操作的项目
    print(f"\n  [!] 你选择了以下 {len(selected_indices)} 个项目进行强制关闭:")
    for idx in selected_indices:
        typ, name, soft, desc = killable[idx]
        icon = "!!" if typ == "进程" else "!"
        print(f"      [{icon}] {typ}: {name} ({soft})")

    print(f"\n  \033[91m[WARNING]\033[0m 强制关闭保护进程/服务可能导致:")
    print(f"      - 蓝屏 (BSOD)")
    print(f"      - 文件系统损坏")
    print(f"      - 系统无法启动")
    print(f"      - 数据丢失")
    print()
    confirm = input("  确认强制关闭? (输入 FORCE 确认): ").strip()

    if confirm != "FORCE":
        print("  已取消。")
        return

    # 执行强制关闭
    print()
    success = 0
    fail = 0
    for idx in selected_indices:
        typ, name, soft, desc = killable[idx]
        if typ == "进程":
            print(f"  [*] 强制终止进程: {name} ...")
            out = run_cmd(["taskkill", "/F", "/IM", name])
            if "成功" in out or "success" in out.lower() or "terminated" in out.lower():
                print(f"       [OK] 已终止")
                success += 1
            elif "not found" in out.lower() or "找不到" in out:
                print(f"       [-] 进程不存在（可能已退出）")
            else:
                print(f"       [!] {out.strip()[:100]}")
                fail += 1
        elif typ == "服务":
            print(f"  [*] 停止并禁用服务: {name} ...")
            out1 = run_cmd(["sc", "stop", name])
            out2 = run_cmd(["sc", "config", name, "start=", "disabled"])
            if "成功" in out1 or "success" in out1.lower():
                print(f"       [OK] 服务已停止")
                success += 1
            elif "1060" in out1 or "不存在" in out1:
                print(f"       [-] 服务不存在")
            else:
                print(f"       [!] 停止: {out1.strip()[:80]}")
                print(f"       [!] 禁用: {out2.strip()[:80]}")
                fail += 1

    print(f"\n  {'='*60}")
    print(f"  完成: 成功 {success} 项, 失败 {fail} 项")
    print(f"  [!] 请立即重启电脑！长时间停留在未保护状态可能导致问题。")
    print(f"  {'='*60}")
    """安全卸载：查找并引导用户使用正规卸载流程。"""
    print(f"\n  ┌─ 卸载: {software_name}")
    print("  │")
    print_risk_warning("安全", "使用软件自带的卸载程序，最安全的方式")

    # 查找卸载程序
    print("  │")
    print("  │  [1] 查找卸载程序...")
    uninst = find_uninstall_cmd(software_name)

    if uninst:
        print(f"  │  [!] 找到 {len(uninst)} 个卸载程序:")
        for name, cmd in uninst:
            print(f"  │      - {name}")
            if cmd:
                print(f"  │        命令: {cmd}")
                print(f"  │")
                confirm = input(f"  │      是否执行卸载? (y/n): ").strip().lower()
                if confirm == 'y':
                    print(f"  │      执行: {cmd}")
                    out = run_cmd(cmd, timeout=120)
                    print(f"  │      结果: {out.strip()[:200]}")
                else:
                    print(f"  │      已跳过")
    else:
        print(f"  │  [-] 未在注册表中找到 {software_name} 的卸载程序")
        print_manual_guide(f"{software_name} 手动卸载", [
            "打开 控制面板 -> 程序和功能",
            "在列表中找到相关程序",
            "右键选择 '卸载'",
            "按提示完成卸载",
            "如果列表中找不到，尝试在安装目录中找 Uninstall.exe",
        ])

    print("  │")
    print(f"  └─ 卸载流程完成。建议重启电脑。")


# ============================================================
#  主程序
# ============================================================

def main():
    if not is_admin():
        print("\n  [!] 警告: 未以管理员权限运行！")
        print("  [?] 请右键程序 -> 以管理员身份运行")
        print("  [?] 继续运行将只进行检测，无法执行关闭操作。\n")
        input("按回车键继续检测...")
        admin_mode = False
    else:
        admin_mode = True

    while True:
        print_header("硬盘还原保护 检测 & 安全关闭工具 v4.0")
        print("  [1] 全面检测还原保护软件")
        print("  [2] 安全关闭保护（推荐）")
        print("  [3] 正规卸载还原软件")
        print("  [4] 导出检测报告")
        print("  \033[91m[5] 强制关闭（选择性，有风险）\033[0m")
        print("  [0] 退出")
        print()
        print("  \033[92m[SAFE]\033[0m v4.0 采用安全模式: 不强杀进程、不改驱动文件")
        print()

        choice = input("  请选择 [0-5]: ").strip()

        if choice == "0":
            break

        elif choice == "1":
            print_header("全面检测")
            items = detect_all()
            print_results(items)
            pause()

        elif choice == "2":
            if not admin_mode:
                print("\n  [!] 需要管理员权限才能执行关闭操作！")
                pause()
                continue

            print_header("安全关闭保护")
            print("  \033[93m[INFO]\033[0m 本功能使用安全方式关闭还原保护:")
            print("        - 通过软件自身机制切换保护状态")
            print("        - 温和停止非核心服务（不强杀进程）")
            print("        - 提供手动操作指南")
            print("        - 不修改驱动文件、不删除系统文件")
            print()

            # 建议创建还原点
            print("  [?] 建议操作前创建系统还原点")
            create_rp = input("  是否创建还原点? (y/n): ").strip().lower()
            if create_rp == 'y':
                create_restore_point()

            items = detect_all()
            print_results(items)

            if not items:
                print("\n  [-] 未检测到还原保护软件，无需操作。")
                pause()
                continue

            # 按软件分组
            by_soft = {}
            for item in items:
                by_soft.setdefault(item.name, []).append(item)

            print("\n  选择要关闭保护的软件:")
            soft_list = list(by_soft.keys())
            for i, s in enumerate(soft_list, 1):
                print(f"    [{i}] {s}")
            print(f"    [A] 全部处理")
            print(f"    [0] 返回")

            sel = input("\n  请选择: ").strip().lower()

            if sel == "0":
                continue
            elif sel == "a":
                targets = soft_list
            else:
                try:
                    idx = int(sel) - 1
                    if 0 <= idx < len(soft_list):
                        targets = [soft_list[idx]]
                    else:
                        print("  无效选择")
                        pause()
                        continue
                except:
                    print("  无效选择")
                    pause()
                    continue

            print("\n  [*] 即将安全处理以下还原保护:")
            for t in targets:
                print(f"      - {t}")
            print()
            confirm = input("  确认执行? (y/n): ").strip().lower()

            if confirm != "y":
                print("  已取消。")
                pause()
                continue

            for soft_name in targets:
                soft_items = by_soft[soft_name]
                safe_disable_software(soft_name, soft_items)

            print("\n" + "=" * 60)
            print("  [*] 所有安全操作已完成！")
            print("  [!] 请按照上述指引操作后重启电脑。")
            print("  [?] 如果保护仍然存在，请尝试选项[3]正规卸载。")
            print("=" * 60)
            pause()

        elif choice == "3":
            if not admin_mode:
                print("\n  [!] 需要管理员权限！")
                pause()
                continue

            print_header("正规卸载还原软件")
            items = detect_all()
            print_results(items)

            if not items:
                print("\n  [-] 未检测到还原保护软件。")
                pause()
                continue

            by_soft = {}
            for item in items:
                by_soft.setdefault(item.name, []).append(item)

            soft_list = list(by_soft.keys())
            for i, s in enumerate(soft_list, 1):
                print(f"    [{i}] {s}")
            print(f"    [0] 返回")

            sel = input("\n  选择要卸载的软件: ").strip()
            try:
                idx = int(sel) - 1
                if 0 <= idx < len(soft_list):
                    safe_uninstall_software(soft_list[idx], by_soft[soft_list[idx]])
            except:
                pass
            pause()

        elif choice == "4":
            print_header("导出检测报告")
            items = detect_all()

            report_path = os.path.join(os.path.expanduser("~"), "Desktop", "还原软件检测报告.txt")
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(f"硬盘还原保护软件检测报告\n")
                f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"计算机名: {os.environ.get('COMPUTERNAME', 'N/A')}\n")
                f.write(f"用户名: {os.environ.get('USERNAME', 'N/A')}\n")
                f.write("=" * 60 + "\n\n")

                if items:
                    by_soft = {}
                    for item in items:
                        by_soft.setdefault(item.name, []).append(item)

                    for soft, evidence in by_soft.items():
                        f.write(f"【{soft}】\n")
                        for ev in evidence:
                            f.write(f"  [{ev.category}] {ev.detail}\n")
                        f.write("\n")

                    f.write(f"\n共发现 {len(by_soft)} 种还原保护软件\n")
                else:
                    f.write("未检测到已知还原保护软件\n")

                # 附录: 所有服务列表
                f.write("\n" + "=" * 60 + "\n")
                f.write("附录: 所有第三方服务\n")
                f.write("=" * 60 + "\n")
                svc_out = run_cmd(["wmic", "service", "get", "Name,DisplayName,State,StartMode,PathName", "/FORMAT:LIST"])
                f.write(svc_out)

                # 附录: 所有驱动
                f.write("\n" + "=" * 60 + "\n")
                f.write("附录: 系统驱动\n")
                f.write("=" * 60 + "\n")
                drv_out = run_cmd(["driverquery", "/FO", "LIST"])
                f.write(drv_out)

            print(f"\n  [OK] 报告已保存到: {report_path}")
            pause()

        elif choice == "5":
            if not admin_mode:
                print("\n  [!] 需要管理员权限！")
                pause()
                continue
            selective_force_kill()
            pause()

        else:
            print("  无效选择")
            pause()

    easter_egg()


if __name__ == "__main__":
    main()
