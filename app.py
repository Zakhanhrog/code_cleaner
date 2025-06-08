from flask import Flask, request, jsonify, render_template
import re
import subprocess
import os
import tempfile
import io
import tokenize

app = Flask(__name__)

def remove_comments_python(code):
    result_tokens = []
    code_io = io.StringIO(code)
    try:
        for token_info in tokenize.generate_tokens(code_io.readline):
            if token_info.type == tokenize.COMMENT:
                continue
            result_tokens.append(token_info)
        return tokenize.untokenize(result_tokens)
    except tokenize.TokenError:
        return code
    except IndentationError:
        return code
    except Exception:
        return code

def _remove_block_comments_str_aware(text_block):
    pattern_block = re.compile(
        r'("(?:\\.|[^"\\])*")|'
        r"('(?:\\.|[^'\\])*')|"
        r'(/\*.*?\*/)',
        re.DOTALL
    )
    def replacer_block(match_obj):
        if match_obj.group(1) or match_obj.group(2):
            return match_obj.group(0)
        return ""
    return pattern_block.sub(replacer_block, text_block)

def _remove_line_comments_str_aware(text_line, comment_marker="//"):
    processed_lines_arr = []
    for single_line in text_line.splitlines():
        idx_comment_marker = -1
        in_single_q = False
        in_double_q = False
        marker_actual_len = len(comment_marker)
        k = 0
        while k < len(single_line):
            current_char = single_line[k]
            if current_char == '\\' and k + 1 < len(single_line):
                k += 2
                continue
            if current_char == "'":
                if not in_double_q:
                    in_single_q = not in_single_q
            elif current_char == '"':
                if not in_single_q:
                    in_double_q = not in_double_q
            elif single_line[k:k+marker_actual_len] == comment_marker and not in_single_q and not in_double_q:
                idx_comment_marker = k
                break
            k += 1
        if idx_comment_marker != -1:
            processed_lines_arr.append(single_line[:idx_comment_marker].rstrip())
        else:
            processed_lines_arr.append(single_line)
    return "\n".join(processed_lines_arr)

def remove_comments_generic(code, lang):
    if lang in ["c_cpp", "java", "csharp", "javascript", "go", "rust", "swift", "kotlin"]:
        code = _remove_block_comments_str_aware(code)
        code = _remove_line_comments_str_aware(code, "//")
    elif lang == "php":
        code = _remove_block_comments_str_aware(code)
        code = _remove_line_comments_str_aware(code, "//")
        code = _remove_line_comments_str_aware(code, "#")
    elif lang == "html": # HTML sẽ chỉ xóa comment HTML
        code = re.sub(r'<!--.*?-->', '', code, flags=re.DOTALL)
    elif lang == "jsp": # JSP xóa comment HTML và JSP
        code = re.sub(r'<!--.*?-->', '', code, flags=re.DOTALL)
        code = re.sub(r'<%--.*?--%>', '', code, flags=re.DOTALL)
    elif lang == "css":
        code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL) # CSS chỉ có block comments
    elif lang in ["ruby", "shell"]:
        code = _remove_line_comments_str_aware(code, "#")
        if lang == "ruby":
            code = re.sub(r'^=begin.*?^=end', '', code, flags=re.DOTALL | re.MULTILINE)
    elif lang == "sql":
        code = _remove_block_comments_str_aware(code)
        code = _remove_line_comments_str_aware(code, "--")
    
    return "\n".join([line for line in code.splitlines() if line.strip()])


def format_python_code(code):
    try:
        formatted_code = subprocess.check_output(
            ['autopep8', '-', '--aggressive', '--aggressive'],
            input=code, text=True, stderr=subprocess.PIPE
        )
        return formatted_code
    except (subprocess.CalledProcessError, FileNotFoundError, Exception):
        return code

def format_go_code(code):
    try:
        process = subprocess.Popen(['gofmt'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        formatted_code, err = process.communicate(input=code)
        return formatted_code if process.returncode == 0 and formatted_code.strip() else code
    except (FileNotFoundError, Exception):
        return code

def format_rust_code(code):
    try:
        process = subprocess.Popen(['rustfmt'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        formatted_code, err = process.communicate(input=code)
        return formatted_code if process.returncode == 0 and formatted_code.strip() else code
    except (FileNotFoundError, Exception):
        return code

def format_shell_code(code):
    try:
        process = subprocess.Popen(['shfmt', '-s'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        formatted_code, err = process.communicate(input=code)
        return formatted_code if process.returncode == 0 and formatted_code.strip() else code
    except (FileNotFoundError, Exception):
        return code

def format_php_code(code):
    try:
        process = subprocess.Popen(
            ['php-cs-fixer', 'fix', '--using-cache=no', '--quiet', '-'], 
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        formatted_code, err = process.communicate(input=code)
        if process.returncode == 0 and formatted_code.strip():
            return formatted_code
        else:
            process_cbf = subprocess.Popen(
                ['phpcbf', '--standard=PSR12', '-q', '-'],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            formatted_code_cbf, err_cbf = process_cbf.communicate(input=code)
            if process_cbf.returncode == 0 and formatted_code_cbf.strip():
                return formatted_code_cbf
            return code
    except (FileNotFoundError, Exception):
        return code

def format_generic_code(code, lang):
    lines = code.splitlines()
    formatted_lines = []
    indent_level = 0
    indent_char = "    "
    html_void_elements = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
    html_inline_like_tags = {"a", "abbr", "b", "bdi", "bdo", "cite", "code", "data", "del", "dfn", "em", "i", "ins", "kbd", "mark", "q", "s", "samp", "small", "span", "strong", "sub", "sup", "time", "u", "var", "script", "style"}
    block_starters = ['{', '(', '[']
    block_enders = ['}', ')', ']']
    python_dedent_keywords = ["return", "break", "continue", "pass", "raise", "elif", "else", "except", "finally"]

    for i, line in enumerate(lines):
        stripped_line = line.strip()
        
        if not stripped_line:
            if formatted_lines and formatted_lines[-1].strip() != "":
                formatted_lines.append("")
            elif not formatted_lines:
                 formatted_lines.append("")
            continue

        is_html_closing_tag = False
        if lang in ["html", "jsp", "markup"]:
            match_html_close = re.match(r"^\s*</([A-Za-z0-9\-_:]+)", stripped_line)
            if match_html_close:
                tag_name_closed = match_html_close.group(1).split(':')[-1].lower()
                if tag_name_closed not in html_inline_like_tags:
                    indent_level = max(0, indent_level - 1)
                is_html_closing_tag = True
        
        if not is_html_closing_tag and (lang not in ["python", "html", "markup"] or (lang == "jsp")):
            if any(stripped_line.startswith(char) for char in block_enders) and \
               not any(stripped_line.endswith(char) for char in block_starters):
                if not (stripped_line.lower().startswith("else") and stripped_line.endswith("{")):
                    indent_level = max(0, indent_level - 1)
        
        elif lang == "python":
            first_word = stripped_line.split(" ", 1)[0] if stripped_line else ""
            if first_word in python_dedent_keywords:
                 pass

        current_indent = indent_char * indent_level
        formatted_lines.append(current_indent + stripped_line)

        is_html_opening_tag_for_indent = False
        if lang in ["html", "jsp", "markup"]:
            match_html_open = re.match(r"^\s*<([A-Za-z0-9\-_:]+)([^>]*)>", stripped_line)
            if match_html_open:
                tag_name_opened = match_html_open.group(1).split(':')[-1].lower()
                tag_attributes = match_html_open.group(2)
                is_self_closing_explicit = tag_attributes.strip().endswith("/")
                is_void = tag_name_opened in html_void_elements
                is_inline_like = tag_name_opened in html_inline_like_tags
                closes_on_same_line = re.search(r"</" + re.escape(tag_name_opened) + r"\s*>$", stripped_line, re.IGNORECASE)
                if not is_self_closing_explicit and not is_void and not is_inline_like and not closes_on_same_line:
                    indent_level += 1
                    is_html_opening_tag_for_indent = True
        
        if not is_html_opening_tag_for_indent and (lang not in ["python", "html", "markup"] or (lang == "jsp")):
            if any(stripped_line.endswith(char) for char in block_starters):
                if not (any(stripped_line.startswith(end_char) for end_char in block_enders) and len(stripped_line) > 2):
                     indent_level += 1
        
        elif lang == "python" and stripped_line.endswith(":"):
            indent_level += 1
            
    final_output_lines = []
    last_line_was_meaningful_or_empty_intent = False
    for i, l_item in enumerate(formatted_lines):
        is_current_line_blank = not l_item.strip()
        if not is_current_line_blank:
            final_output_lines.append(l_item)
            last_line_was_meaningful_or_empty_intent = True
        elif is_current_line_blank and last_line_was_meaningful_or_empty_intent and i < len(formatted_lines) -1 :
            if i + 1 < len(formatted_lines) and formatted_lines[i+1].strip() != "":
                 final_output_lines.append("")
            elif i == len(formatted_lines) -1:
                 final_output_lines.append("")
            last_line_was_meaningful_or_empty_intent = False
            
    if final_output_lines and not final_output_lines[0].strip():
        final_output_lines.pop(0)
    while len(final_output_lines) > 1 and not final_output_lines[-1].strip() and not final_output_lines[-2].strip():
         final_output_lines.pop()
    if len(final_output_lines) == 1 and not final_output_lines[0].strip():
        final_output_lines.pop()

    return "\n".join(final_output_lines)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process_code', methods=['POST'])
def process_code_route():
    data = request.get_json()
    code = data.get('code')
    language = data.get('language')

    if not code:
        return jsonify({'error': 'Không có code nào được cung cấp'}), 400

    processed_code = code

    if language == 'python':
        processed_code = remove_comments_python(processed_code)
        processed_code = format_python_code(processed_code)
    elif language == 'php':
        processed_code = remove_comments_generic(processed_code, language)
        processed_code = format_php_code(processed_code)
    elif language == 'go':
        processed_code = remove_comments_generic(processed_code, language)
        processed_code = format_go_code(processed_code)
    elif language == 'rust':
        processed_code = remove_comments_generic(processed_code, language)
        processed_code = format_rust_code(processed_code)
    elif language == 'shell':
        processed_code = remove_comments_generic(processed_code, language)
        processed_code = format_shell_code(processed_code)
    elif language in ['html', 'jsp', 'css', 'javascript', 'java', 'csharp', 'c_cpp', 'ruby', 'sql', 'swift', 'kotlin']:
        processed_code = remove_comments_generic(processed_code, language)
        processed_code = format_generic_code(processed_code, language)
    else: # Fallback cho các ngôn ngữ không xác định
        processed_code = remove_comments_generic(processed_code, "unknown") # Xóa comment cơ bản nhất
        processed_code = format_generic_code(processed_code, "unknown") # Format cơ bản nhất

    final_lines_list = []
    if processed_code:
        for line_item_content in processed_code.splitlines():
            if line_item_content.strip() or (final_lines_list and final_lines_list[-1].strip()):
                 final_lines_list.append(line_item_content)
        if final_lines_list and not final_lines_list[0].strip() and len(final_lines_list) > 1:
            final_lines_list.pop(0)
        while final_lines_list and not final_lines_list[-1].strip():
            final_lines_list.pop()

    processed_code = "\n".join(final_lines_list)
    return jsonify({'processed_code': processed_code.strip()})

if __name__ == '__main__':
    app.run(debug=True)