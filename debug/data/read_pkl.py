import pickle

def load_pkl_data(pkl_file):
    try:
        with open(pkl_file, "rb") as f:
            data = pickle.load(f)
            print(data)  # 打印数据，查看存储内容
        return data
    except Exception as e:
        print(f"Error loading pkl file: {e}")

# 示例调用
data = load_pkl_data("../../user_datas.pkl")
