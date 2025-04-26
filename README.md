# 部署说明
此文档提供中烟菌种数据库的部署指导。

## 部署环境
### Python环境的安装
首先部署python环境
下载下面网页的Python环境：
https://www.python.org/downloads/release/python-31210/

特别要注意勾上Add Python 3.x to PATH，然后点“Install Now”即可完成安装。
### 依赖库的安装
打开powershell或者cmd，切换到程序目录下，运行：
```cmd
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn
```

## 运行软件

之后在桌面运行 `run.bat` 即可打开gui环境。