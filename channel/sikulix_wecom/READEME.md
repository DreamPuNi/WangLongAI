# 环境准备
- 前提中的前提！！！启用此项目后，不要在含有中文路径和特殊字符(如空格等)的路径下运行！！！
- 前提中的前提！！！启用此项目后，不要在含有中文路径和特殊字符(如空格等)的路径下运行！！！
- 前提中的前提！！！启用此项目后，不要在含有中文路径和特殊字符(如空格等)的路径下运行！！！
- 前提中的前提！！！启用此项目后，不要在含有中文路径和特殊字符(如空格等)的路径下运行！！！
- 前提中的前提！！！启用此项目后，不要在含有中文路径和特殊字符(如空格等)的路径下运行！！！
- 前提中的前提！！！启用此项目后，不要在含有中文路径和特殊字符(如空格等)的路径下运行！！！
- 前提中的前提！！！启用此项目后，不要在含有中文路径和特殊字符(如空格等)的路径下运行！！！
- 前提中的前提！！！启用此项目后，不要在含有中文路径和特殊字符(如空格等)的路径下运行！！！
- 前提中的前提！！！启用此项目后，不要在含有中文路径和特殊字符(如空格等)的路径下运行！！！
- 首先这个插件需要JAVA环境，所以去`https://www.oracle.com/java/technologies/downloads/?er=221886&spm=5aebb161.2ef5001f.0.0.14b0c921oHq8CW#jdk23-windows` 下载你系统对应的javaJDK
- 安装完 Java 后，你需要设置 JAVA_HOME 环境变量，以便 JPype 能够找到 Java 的安装路径。 
- 这个部分依赖JPype1==1.5.2和pyperclip==1.9.0库
### Windows 系统：
    找到 Java 安装路径 ： 
        默认情况下，Java 通常安装在 C:\Program Files\Java\jdk-<version> 或 C:\Program Files (x86)\Java\jdk-<version>。
        找到你的 Java 安装目录，例如：C:\Program Files\Java\jdk-17。

    设置 JAVA_HOME 环境变量 ： 
        右键点击“此电脑”或“我的电脑”，选择“属性”。
        点击“高级系统设置”，然后点击“环境变量”。
        在“系统变量”部分，点击“新建”按钮。
        输入变量名为 JAVA_HOME，变量值为你的 Java 安装路径（例如：C:\Program Files\Java\jdk-17）。
        点击“确定”保存。

    更新 Path 环境变量 ： 
        在“系统变量”部分，找到 Path 变量，点击“编辑”。
        添加一个新的条目，内容为 %JAVA_HOME%\bin。
        点击“确定”保存。

    验证 Java 安装 ： 
        打开命令提示符（CMD），输入 java -version，你应该能看到 Java 的版本信息。

### macOS/Linux 系统：
    找到 Java 安装路径 ： 
        你可以通过命令 which java 来查看 Java 的路径。
        如果你使用的是 OpenJDK，路径可能是 /usr/lib/jvm/java-<version>-openjdk。

    设置 JAVA_HOME 环境变量 ： 
        打开终端，编辑你的 shell 配置文件（例如 .bashrc, .zshrc）。
        添加以下内容：
    ```
    export JAVA_HOME=/path/to/your/java
    export PATH=$JAVA_HOME/bin:$PATH
    ```
    替换 /path/to/your/java 为你实际的 Java 安装路径。
    保存文件后，运行 source ~/.bashrc 或 source ~/.zshrc 使更改生效。

### 验证 Java 安装 ：
    在终端中输入 java -version，你应该能看到 Java 的版本信息。
     
# 参数设置：
- 当前比较重要的参数一共两个
- jvm_path = r"C:\Program Files\Java\jdk-23\bin\server\jvm.dll"
- sikulix_jar_path = r"D:\Program\dify-on-wechat\lib\sikulix\sikulixide-2.0.5-win.jar"