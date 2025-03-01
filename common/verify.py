import os
import json
import ctypes
import hashlib
import requests
import platform
import subprocess

from jaraco.functools import retry


class GenerateToken():
    def __init__(self):
        pass

    def get_system_info(self):
        """获取系统特征信息"""
        info = {}

        # 1. 计算机名（非唯一但相对稳定）
        info['computer_name'] = platform.node()

        # 2. 系统安装日期（通过注册表获取）
        try:
            cmd = 'REG QUERY HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows NT\CurrentVersion /v InstallDate'
            result = subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True)
            info['install_date'] = result.decode().split()[-1]
        except:
            info['install_date'] = "unknown"

        # 3. 磁盘卷特征（无需管理员权限）
        info['disk_id'] = self.get_disk_volume_id()

        # 4. 主板特征（WMI查询）
        info['baseboard'] = self.get_wmi_info('Win32_BaseBoard', 'SerialNumber')

        # 5. BIOS特征
        info['bios'] = self.get_wmi_info('Win32_BIOS', 'SerialNumber')

        return info


    def get_disk_volume_id(self):
        """获取系统盘卷序列号（无需管理员权限）"""
        kernel32 = ctypes.windll.kernel32
        volume_name_buffer = ctypes.create_unicode_buffer(1024)
        file_system_name_buffer = ctypes.create_unicode_buffer(1024)
        serial_number = ctypes.c_ulong()

        kernel32.GetVolumeInformationW(
            ctypes.c_wchar_p("C:\\"),
            volume_name_buffer,
            ctypes.sizeof(volume_name_buffer),
            ctypes.byref(serial_number),
            None,
            None,
            file_system_name_buffer,
            ctypes.sizeof(file_system_name_buffer)
        )
        return f"{serial_number.value:X}"


    def get_wmi_info(self,class_name, property_name):
        """通过WMI获取硬件信息（无需管理员权限）"""
        try:
            cmd = f'wmic {class_name} get {property_name} /value'
            result = subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True)
            return result.decode().split('=')[-1].strip()
        except Exception as e:
            return f"error_{str(e)}"


    def generate_device_id(self):
        """生成设备唯一标识"""
        system_info = self.get_system_info()

        # 组合关键特征
        feature_string = (
            f"{system_info['computer_name']}"
            f"|{system_info['install_date']}"
            f"|{system_info['disk_id']}"
            f"|{system_info['baseboard']}"
            f"|{system_info['bios']}"
        )

        # 生成SHA256哈希
        return hashlib.sha256(feature_string.encode()).hexdigest()

class VerifyAccess(GenerateToken):
    def __init__(self):
        super().__init__()
        self.token = self.generate_device_id()
        self.generate_activation_id()

    def verify(self, activtation_code):
        print(activtation_code)
        #self.generate_activation_id(self.token)
        result = self._verify_license(self.token, activtation_code)

        if result and result.get("status") == "success":
            print("验证成功，授权文件已生成！")
            license_data = {
                "device_id": self.token,
                "license_key": result.get("license_key"),
                "expires_at": result.get("expires_at")
            }
            self._create_license_file(license_data)
            return True
        else:
            print("激活失败，请重试。")
            return False

    def generate_activation_id(self):
        url = "http://39.104.61.96:5000/generate"
        payload = {"device_id": self.token}
        headers = {"Content-Type": "application/json"}  # 明确指定内容类型
        gener_status = requests.post(url, json=payload, headers=headers)

    def _verify_license(self, token, activation_code):
        url = "http://39.104.61.96:5000/verify"  # 替换为你的服务器API地址
        payload = {"device_id": token, "activation_code": activation_code}
        try:
            headers = {"Content-Type": "application/json"}
            response = requests.post(url, json=payload, headers=headers)
            if response.status_code == 200:
                print(response.json())
                return response.json()  # 处理服务器返回的数据
            else:
                print("验证失败:", response.text)
                return None
        except Exception as e:
            print("网络错误:", e)
            return None

    def _create_license_file(self, license_data):
        with open("license.lic", "w") as f:
            json.dump(license_data, f)
        print("授权文件已生成！")

    def check_local_license(self):
        if not os.path.exists("license.lic"):
            return False
        with open("license.lic", "r") as f:
            license_data = json.load(f)
            if license_data.get("device_id") == self.token and self.verify_device_online(self.token):
                print("本地授权验证通过！")
                return True
            else:
                print("设备ID不匹配，授权无效！")
                return False

    def verify_device_online(self,token):
        url = "http://39.104.61.96:5000/verifydevices"  # 替换为你的服务器API地址
        payload = {"device_id": self.token}
        try:
            response = requests.post(url, json=payload)
            if response.status_code == 200:
                result = response.json()
                if result and result.get("status") == "success":
                    return True
            else:
                print("验证失败:", response.text)
                return False
        except Exception as e:
            print("网络错误:", e)
            return False


if __name__ == "__main__":
    verify = VerifyAccess()
    i = 0
    if not verify.check_local_license():
        while i < 3:
            print(verify.token)
            key = input("请输入你的Key：")
            verify.verify(key)
            i += 1
    else:
        print("激活成功")
