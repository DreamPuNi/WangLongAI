# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files

datas = [('D:\\\\Program\\\\0-venv\\\\dify-on-wechat-env\\\\Lib\\\\site-packages\\\\flet', 'flet'), ('D:\\\\Program\\\\0-venv\\\\dify-on-wechat-env\\\\Lib\\\\site-packages\\\\wcferry', 'wcferry'), ('D:\\\\Program\\\\0-venv\\\\dify-on-wechat-env\\\\Lib\\\\site-packages\\\\wcferry\\\\sdk.dll', 'wcferry'), ('D:\\\\Program\\\\dify-on-wechat\\\\plugins', 'plugins')]
datas += collect_data_files('ntwork')


a = Analysis(
    ['interface.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='LongShangAI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
