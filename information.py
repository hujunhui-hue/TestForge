import os
import ast
import json
import re
import textwrap

# ---------------- 配置区域 ----------------
PROJECT_PATH = r"bU"  # 你的项目路径（文件夹或单文件）
OUTPUT_DIR = "./"  # 输出文件保存路径
MIN_LOC = 5
MAX_LOC = 100
# -----------------------------------------

def read_file(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"[读取错误] {path} - {e}")
        return ""

def get_doc_summary(doc):
    if not doc:
        return ""
    lines = [l.strip() for l in doc.splitlines() if l.strip()]
    for i, l in enumerate(lines):
        if re.match(r"(:param|:return|:raise|Args|Returns|Raises)", l):
            return " ".join(lines[:i])
    return " ".join(lines[:3])

def extract_doc_sections(doc):
    params, returns, raises = {}, "", []
    if not doc:
        return params, returns, raises
    for line in doc.splitlines():
        if m := re.match(r":param\s+(\w+):\s*(.*)", line):
            params[m.group(1)] = m.group(2)
        elif m := re.match(r":return[s]?:\s*(.*)", line):
            returns = m.group(1)
        elif m := re.match(r":raise[s]?\s+(\w+):\s*(.*)", line):
            raises.append({"type": m.group(1), "desc": m.group(2)})
    return params, returns, raises

def find_called_functions(node):
    calls = set()
    for n in ast.walk(node):
        if isinstance(n, ast.Call):
            try:
                if isinstance(n.func, ast.Attribute):
                    calls.add(f"{ast.unparse(n.func.value)}.{n.func.attr}")
                elif isinstance(n.func, ast.Name):
                    calls.add(n.func.id)
            except Exception:
                pass
    return sorted(calls)

def find_control_structures(node):
    ctrls = set()
    for n in ast.walk(node):
        if isinstance(n, (ast.If, ast.For, ast.While, ast.Try)):
            ctrls.add(type(n).__name__)
    return sorted(ctrls)

def detect_behavior(calls):
    joined = " ".join(calls)
    behavior = []
    if re.search(r"(Prompt\.ask|Confirm\.ask|input\()", joined):
        behavior.append("user_input")
    if re.search(r"(open|os\.remove|rmtree|os\.path)", joined):
        behavior.append("file_io")
    if re.search(r"(requests|urllib|http)", joined):
        behavior.append("network_io")
    if re.search(r"(json\.|yaml\.|pickle\.|marshal\.)", joined):
        behavior.append("serialization")
    if re.search(r"(jinja2|\.render\()", joined):
        behavior.append("template_render")
    if not behavior:
        behavior.append("logic")
    return behavior

def extract_functions_from_file(file_path):
    code = read_file(file_path)
    if not code:
        return []

    try:
        tree = ast.parse(code)
    except Exception as e:
        print(f"[解析错误] {file_path} - {e}")
        return []

    functions = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            if hasattr(node, "end_lineno"):
                loc = node.end_lineno - node.lineno + 1
                if not (MIN_LOC <= loc <= MAX_LOC):
                    continue

            # 函数源代码
            try:
                src_lines = code.splitlines()[node.lineno-1:node.end_lineno]
                source = textwrap.dedent("\n".join(src_lines))
            except Exception:
                source = ""

            # 函数所属类
            class_name = None
            for parent in ast.walk(tree):
                if isinstance(parent, ast.ClassDef) and node in parent.body:
                    class_name = parent.name
                    break

            # docstring
            doc = ast.get_docstring(node)
            doc_summary = get_doc_summary(doc)
            param_doc, return_doc, raises_doc = extract_doc_sections(doc)

            params = [a.arg for a in node.args.args]
            param_types = {}
            for a in node.args.args:
                if a.annotation:
                    try:
                        param_types[a.arg] = ast.unparse(a.annotation)
                    except Exception:
                        pass

            return_type = None
            if node.returns:
                try:
                    return_type = ast.unparse(node.returns)
                except Exception:
                    pass

            called_funcs = find_called_functions(node)
            ctrls = find_control_structures(node)
            behaviors = detect_behavior(called_funcs)

            relative_path = os.path.relpath(file_path, start=PROJECT_PATH)
            record = {
                "file": relative_path.replace("/", "\\"),
                "class_name": class_name,
                "function_name": node.name,
                "parameters": params,
                "param_types": param_types,
                "return_type": return_type,
                "param_doc": param_doc,
                "return_doc": return_doc,
                "raises_doc": raises_doc,
                "called_functions": called_funcs,
                "control_structures": ctrls,
                "behavior_type": behaviors,
                "doc_summary": doc_summary,
                "source_code": source,
                "loc": loc
            }
            functions.append(record)
    return functions

def extract_functions_from_project(project_dir):
    all_funcs = []
    for root, dirs, files in os.walk(project_dir):
        dirs[:] = [d for d in dirs if "test" not in d.lower()]
        for f in files:
            if f.endswith(".py") and "test" not in f.lower():
                path = os.path.join(root, f)
                funcs = extract_functions_from_file(path)
                all_funcs.extend(funcs)
                if funcs:
                    print(f"[+] {f}: {len(funcs)} 个函数提取成功")
    return all_funcs

def main():
    path = os.path.abspath(PROJECT_PATH)
    if not os.path.exists(path):
        print(f"❌ 路径不存在: {path}")
        return

    if os.path.isfile(path):
        results = extract_functions_from_file(path)
    else:
        results = extract_functions_from_project(path)

    project_name = os.path.basename(os.path.normpath(path))
    output_path = os.path.join(OUTPUT_DIR, f"{project_name}_functions.jsonl")

    with open(output_path, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print("=" * 70)
    print(f"✅ 完成！共提取 {len(results)} 个函数。结果保存至：{output_path}")
    print("=" * 70)

if __name__ == "__main__":
    main()
