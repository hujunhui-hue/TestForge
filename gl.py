import json

# 输入与输出路径
INPUT_FILE = "py_functions.jsonl"
OUTPUT_FILE = "py22_functions.jsonl"

def is_testable(f):
    """
    判断一个函数是否适合写测试用例（不考虑行数 loc）
    """

    # ---- 2. 必须有逻辑结构或调用关系 ----
    if len(f.get("control_structures", [])) == 0 and len(f.get("called_functions", [])) < 2:
        return False

    # ---- 3. 行为类型可测试（逻辑 / 序列化类） ----
    if not any(bt in ["logic", "serialization"] for bt in f.get("behavior_type", [])):
        return False

    # ---- 4. 非私有函数（排除 _开头）----
    if f.get("function_name", "").startswith("_"):
        return False



    return True


def main():
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        funcs = [json.loads(line) for line in f]

    testable = [f for f in funcs if is_testable(f)]

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for item in testable:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(f"✅ 已从 {len(funcs)} 个函数中过滤出 {len(testable)} 个适合写测试用例的函数。")
    print(f"结果已保存到: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
