import wcferry
print(wcferry.__file__)

msg = """硝:
宁夏

硝:
吴忠

何颂生:
我在陕西西安

何颂生:
听着不愿

何颂生:
远

硝:
青铜峡

硝:
[不支持类型消息]

何颂生:
okokok
不用那么详细
"""

lines = [line.strip() for line in msg.splitlines() if line.strip()]
print(lines)
# 初始化结果列表和临时变量
result = []
current_speaker = None
current_content = []
user_name = ""

# 遍历每一行
for line in lines:
    # 如果是以 ":" 结尾，表示新的发言者
    if line.endswith(":"):
        # 如果已经有当前发言者，保存其内容到结果中
        if current_speaker and current_speaker != line:
            result.append({current_speaker: "".join(current_content).rstrip("。")})
            current_content = []

        current_speaker = line
        if current_speaker != "何颂生:":
            user_name = current_speaker[:-1]
    else:
        # 否则，将内容添加到当前发言者的内容中
        current_content.append(line + "。")  # 使用句号连接

# 处理最后一个发言者的内容
if current_speaker:
    result.append({current_speaker: "".join(current_content).rstrip("。")})

# 输出结果
print(user_name)
print(result)

# x :['宁夏。']