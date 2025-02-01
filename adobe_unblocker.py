import os
import re
import socket
import subprocess
import requests
import winreg
import ctypes
import sys
from datetime import datetime

ADOBE_DOMAINS = [
    "cc-api-data.adobe.io",
    "*.adobe.com",
    "*.adobe.io",
    "photoshop.com"
]

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def check_hosts_file():
    hosts_path = r"C:\Windows\System32\drivers\etc\hosts"
    blocked = []
    try:
        with open(hosts_path, 'r') as f:
            for line in f:
                if line.strip().startswith('#'):
                    continue
                for domain in ADOBE_DOMAINS:
                    if domain in line:
                        blocked.append(line.strip())
    except Exception as e:
        print(f"Ошибка чтения файла hosts: {e}")
    return blocked

def check_firewall_rules():
    blocked_rules = []
    try:
        result = subprocess.check_output(
            'netsh advfirewall firewall show rule name=all dir=out',
            shell=True,
            text=True
        )
        for domain in ADOBE_DOMAINS:
            if domain in result:
                blocked_rules.append(domain)
    except Exception as e:
        print(f"Ошибка проверки брандмауэра: {e}")
    return blocked_rules

def check_proxy_settings():
    proxy_enabled = False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Internet Settings") as key:
            proxy_enable, _ = winreg.QueryValueEx(key, "ProxyEnable")
            if proxy_enable == 1:
                proxy_enabled = True
    except Exception as e:
        print(f"Ошибка проверки прокси: {e}")
    return proxy_enabled

def check_dns():
    dns_servers = []
    try:
        result = subprocess.check_output('ipconfig /all', shell=True, text=True)
        matches = re.findall(r'DNS Servers[\. ]+: ([\d\.]+)', result)
        dns_servers = matches if matches else []
    except Exception as e:
        print(f"Ошибка проверки DNS: {e}")
    return dns_servers

def fix_hosts_file(backup=True):
    hosts_path = r"C:\Windows\System32\drivers\etc\hosts"
    if backup:
        backup_path = f"{hosts_path}.bak_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        os.rename(hosts_path, backup_path)
        os.rename(backup_path, hosts_path)
    with open(hosts_path, 'r') as f:
        lines = f.readlines()
    with open(hosts_path, 'w') as f:
        for line in lines:
            if not any(domain in line for domain in ADOBE_DOMAINS):
                f.write(line)

def remove_firewall_rules():
    try:
        for domain in ADOBE_DOMAINS:
            subprocess.run(
                f'netsh advfirewall firewall delete rule name="{domain}" dir=out',
                shell=True,
                check=True
            )
    except Exception as e:
        print(f"Ошибка удаления правил брандмауэра: {e}")

def disable_proxy():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Internet Settings", 0, winreg.KEY_WRITE) as key:
            winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 0)
    except Exception as e:
        print(f"Ошибка отключения прокси: {e}")

def main():
    if not is_admin():
        print("Запустите программу от имени администратора!")
        input("Нажмите Enter для выхода...")
        sys.exit(1)

    print("Сканирование системы...")
    issues = {}

    # Проверка файла hosts
    hosts_issues = check_hosts_file()
    if hosts_issues:
        issues["hosts"] = hosts_issues

    # Проверка брандмауэра
    firewall_issues = check_firewall_rules()
    if firewall_issues:
        issues["firewall"] = firewall_issues

    # Проверка прокси
    if check_proxy_settings():
        issues["proxy"] = True

    # Проверка DNS
    dns_servers = check_dns()
    if dns_servers and dns_servers not in [["8.8.8.8"], ["1.1.1.1"]]:
        issues["dns"] = dns_servers

    # Вывод результатов
    if not issues:
        print("Блокировок не обнаружено.")
        return

    print("\nОбнаружены проблемы:")
    for key, value in issues.items():
        print(f"- {key}: {value}")

    # Исправление
    choice = input("\nИсправить автоматически? (y/n): ").lower()
    if choice == 'y':
        if "hosts" in issues:
            fix_hosts_file()
            print("Файл hosts очищен.")
        if "firewall" in issues:
            remove_firewall_rules()
            print("Правила брандмауэра удалены.")
        if "proxy" in issues:
            disable_proxy()
            print("Прокси отключен.")
        if "dns" in issues:
            print("Ручная настройка DNS: 8.8.8.8 (Google DNS)")

    input("\nНажмите Enter для выхода...")

if __name__ == "__main__":
    main()
