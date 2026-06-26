[app]
title = Duga
package.name = duga
package.domain = com.yourname.duga
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json,txt,env

version = 1.0.0
requirements = python3,kivy,requests,openai,beautifulsoup4,lxml,trafilatura,duckduckgo-search,platformdirs,python-dotenv,Pillow

# Include our duga core
source.include_patterns = src/duga/*.py,src/duga/templates/*

orientation = portrait
fullscreen = 0

# Android specific
android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE
android.api = 33
android.minapi = 21
android.ndk = 25b
android.arch = arm64-v8a

[buildozer]
log_level = 2
warn_on_root = 1
