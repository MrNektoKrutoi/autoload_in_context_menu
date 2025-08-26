import os
import sys
import winreg
import pythoncom
from win32com.client import Dispatch
import ctypes
import tempfile
import shutil
import base64

VERSION = "4.0"
REGISTRY_KEY = r"*\shell\AutostartManager"
REGISTRY_VERSION_KEY = r"Software\AutostartManager"

def is_admin():
    """Проверяет, запущен ли скрипт от имени администратора"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def get_installed_version():
    """Получает установленную версию из реестра"""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_VERSION_KEY) as key:
            version, _ = winreg.QueryValueEx(key, "Version")
            return version
    except:
        return None

def set_installed_version(version):
    """Устанавливает версию в реестре"""
    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, REGISTRY_VERSION_KEY) as key:
            winreg.SetValueEx(key, "Version", 0, winreg.REG_SZ, version)
        return True
    except:
        return False

def create_shortcut(target_path, shortcut_path):
    """Создает ярлык"""
    shell = Dispatch('WScript.Shell')
    shortcut = shell.CreateShortCut(shortcut_path)
    shortcut.Targetpath = target_path
    shortcut.WorkingDirectory = os.path.dirname(target_path)
    shortcut.save()

def remove_context_menu():
    """Удаляет пункт из контекстного меню"""
    try:
        # Удаляем основную ветку
        try:
            winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, REGISTRY_KEY + r"\command")
        except:
            pass
        
        try:
            winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, REGISTRY_KEY)
        except:
            pass
        
        # Удаляем информацию о версии
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, REGISTRY_VERSION_KEY)
        except:
            pass
        
        print("✓ Контекстное меню удалено")
        return True
    except Exception as e:
        print(f"✗ Ошибка при удалении: {e}")
        return False

def add_to_context_menu():
    """Добавляет пункт в контекстное меню с функцией добавления/удаления из автозагрузки"""
    try:
        python_code = '''
import os, sys, tempfile, shutil, base64
from win32com.client import Dispatch

def create_shortcut(target_path, shortcut_path):
    shell = Dispatch('WScript.Shell')
    shortcut = shell.CreateShortCut(shortcut_path)
    shortcut.Targetpath = target_path
    shortcut.WorkingDirectory = os.path.dirname(target_path)
    shortcut.save()

def get_startup_path():
    return os.path.join(os.environ["APPDATA"], "Microsoft", "Windows", "Start Menu", "Programs", "Startup")

def is_in_autostart(file_path):
    startup_path = get_startup_path()
    if not os.path.exists(startup_path):
        return False
    
    file_name = os.path.splitext(os.path.basename(file_path))[0]
    shortcut_name = file_name + ".lnk"
    shortcut_path = os.path.join(startup_path, shortcut_name)
    return os.path.exists(shortcut_path)

def add_to_autostart(file_path):
    try:
        startup_path = get_startup_path()
        if not os.path.exists(startup_path):
            os.makedirs(startup_path)
        
        file_name = os.path.splitext(os.path.basename(file_path))[0]
        shortcut_name = file_name + ".lnk"
        shortcut_path = os.path.join(startup_path, shortcut_name)
        create_shortcut(file_path, shortcut_path)
        return True
    except:
        return False

def remove_from_autostart(file_path):
    try:
        startup_path = get_startup_path()
        file_name = os.path.splitext(os.path.basename(file_path))[0]
        shortcut_name = file_name + ".lnk"
        shortcut_path = os.path.join(startup_path, shortcut_name)
        
        if os.path.exists(shortcut_path):
            os.remove(shortcut_path)
            return True
        return False
    except:
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
        file_path = sys.argv[1]
        
        if is_in_autostart(file_path):
            print(f"Файл '{os.path.basename(file_path)}' уже в автозагрузке!")
            choice = input("Удалить из автозагрузки? [y/N]: ").lower().strip()
            if choice == 'y':
                if remove_from_autostart(file_path):
                    print("✓ Удалено из автозагрузки")
                else:
                    print("✗ Ошибка удаления")
            else:
                print("Отменено")
        else:
            # Просто добавляем без сообщения
            add_to_autostart(file_path)
'''

        # Кодируем код в base64
        encoded_code = base64.b64encode(python_code.encode('utf-8')).decode('utf-8')
        
        # Команда которая декодирует и выполняет Python код
        command = (
            f'"{sys.executable}" -c '
            f'"import base64; exec(base64.b64decode(\\"{encoded_code}\\"))" "%1"'
        )

        # Создаем ключи в реестре
        with winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, REGISTRY_KEY) as key:
            winreg.SetValue(key, None, winreg.REG_SZ, "Управление автозагрузкой")
            winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, "shell32.dll,25")
        
        with winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, REGISTRY_KEY + r"\command") as key:
            winreg.SetValue(key, None, winreg.REG_SZ, command)
        
        # Сохраняем информацию о версии
        set_installed_version(VERSION)
        
        print("✓ Пункт меню добавлен в контекстное меню")
        return True
        
    except Exception as e:
        print(f"✗ Ошибка при добавлении в контекстное меню: {e}")
        return False

def restart_explorer():
    """Перезапускает проводник Windows"""
    try:
        os.system('taskkill /f /im explorer.exe')
        os.system('start explorer.exe')
        print("✓ Проводник перезапущен")
    except:
        print("⚠ Не удалось перезапустить проводник")

def check_and_upgrade():
    """Проверяет и обновляет предыдущие версии"""
    installed_version = get_installed_version()
    
    if not installed_version:
        print("✓ Новая установка")
        return True
    
    if installed_version == VERSION:
        print("✓ Уже установлена актуальная версия")
        return False
    
    print(f"⚡ Обновление с версии {installed_version} до {VERSION}")
    
    # Удаляем старую версию и устанавливаем новую
    remove_context_menu()
    return True

def main():
    print(f"=== Установка контекстного меню v{VERSION} ===")
    
    if not is_admin():
        print("⚠ Запустите скрипт от имени администратора!")
        input("Нажмите Enter для выхода...")
        return
    
    # Проверяем текущую установку
    installed_version = get_installed_version()
    
    if installed_version == VERSION:
        print("✓ Версия 4.0 уже установлена")
        choice = input("Удалить контекстное меню? [y/N]: ").lower().strip()
        if choice == 'y':
            if remove_context_menu():
                restart_explorer()
                print("✓ Удаление завершено")
            else:
                print("✗ Ошибка удаления")
        else:
            print("✓ Операция отменена")
        input("Нажмите Enter для выхода...")
        return
    
    # Обновляем или устанавливаем
    needs_install = check_and_upgrade()
    
    if needs_install:
        if add_to_context_menu():
            restart_explorer()
            print("\n✅ Готово! Теперь можно:")
            print("   • Удалить этот скрипт - меню останется")
            print("   • Правый клик на файле → Управление автозагрузкой")
            print("   • Добавлять и удалять файлы из автозагрузки")
            print("   • Функция работает после перезагрузки")
            print(f"\nУстановлена версия {VERSION}")
        else:
            print("\n❌ Не удалось установить контекстное меню")
    else:
        print("\n✓ Система уже обновлена до актуальной версии")
    
    input("Нажмиte Enter для выхода...")

if __name__ == "__main__":
    main()