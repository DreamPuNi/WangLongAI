from datetime import datetime, timedelta
import json
import sys
import os

class DataMonitoring(dict):
    def __init__(self):
        super().__init__()
        PROJECT_ROOT = sys.path[0]
        self.DATA_FILE_PATH = os.path.join(PROJECT_ROOT, "logs", "data.json")
        self.load_data()

    def load_data(self):
        if os.path.exists(self.DATA_FILE_PATH):
            with open(self.DATA_FILE_PATH, "r", encoding="utf-8") as f:
                self.update(json.load(f))
        else:
            self.clear()
            self._init_today_data()

        today = datetime.now().strftime("%Y-%m-%d")
        if today not in self:
            self._init_today_data()

    def _init_today_data(self):
        today = datetime.now().strftime("%Y-%m-%d")
        self[today] = {
            "reply_count": 0,
            "prompt_usage": {"dify": 0, "coze": 0, "openai": 0},
            "new_friends": 0,
            "ended_conversations": 0
        }

    def update_stat(self, key, value=1 ,sub_key=None):
        today = datetime.now().strftime("%Y-%m-%d")
        if today not in self:
            self._init_today_data()

        if sub_key:
            self[today][key][sub_key] += value
        else:
            self[today][key] += value

        self.save_data()

    def save_data(self):
        with open(self.DATA_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(self, f, ensure_ascii=False, indent=4)

    def read(self):
        return self

data_func = DataMonitoring()

def data():
    return data_func

def get_today_stats():
    data_func.load_data()
    today = datetime.now().strftime("%Y-%m-%d")
    data_json = data_func.read()
    return {
        "reply_count": data_json.get(today, {}).get("reply_count", 0),
        "new_friends": data_json.get(today, {}).get("new_friends", 0),
        "ended_conversations": data_json.get(today, {}).get("ended_conversations", 0),
    }

def get_last_seven_days_prompt_usage():
    data_func.load_data()
    data_json = data_func.read()
    dify_result = []
    for i in range(6, -1, -1):
        day = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        dify_result.append(data_json.get(day, {}).get("prompt_usage", {}).get("dify", 0))

    return dify_result

if __name__ == "__main__":
    # 这里运行不了，因为目录不是项目根目录
    today = datetime.now().strftime("%Y-%m-%d")
    print(data()[today])