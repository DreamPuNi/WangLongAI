import pilk
import wave

def preprocess_wechat_silk(input_path, output_path):
    """
    预处理微信 Silk 文件，使其符合标准 Silk 格式
    """
    with open(input_path, "rb") as fin, open(output_path, "wb") as fout:
        # 跳过微信 Silk 文件开头的多余字节（0x02）
        fin.seek(1)

        # 读取剩余内容并写入新文件
        data = fin.read()

        # 在文件末尾追加标准 Silk 结束标识（0xFFFF）
        fout.write(data + b'\xFF\xFF')

# 测试用的标准 Silk 文件路径
silk_path = "tmp/voice_86b19948-99d5-4771-9936-aeedcdd51fcf.silk"
formatted_silk_path = "tmp/standard_output.silk"
wav_path = "tmp/standard_output.wav"

# 预处理微信 Silk 文件
preprocess_wechat_silk(silk_path, formatted_silk_path)

# 使用 pilk 解码 Silk 文件
pilk.silk_to_wav(silk_path, wav_path,rate=24000)

# 验证生成的 WAV 文件是否有效
try:
    with wave.open(wav_path, "rb") as fp:
        print("WAV 文件有效，采样率：", fp.getframerate())
except wave.Error as e:
    print(f"WAV 文件无效: {e}")





