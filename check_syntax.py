import ast
import sys

def check_syntax(filename):
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            source = f.read()
        ast.parse(source)
        print(f"Syntax is valid in {filename}")
        return True
    except SyntaxError as e:
        line_num = e.lineno
        col_offset = e.offset
        error_line = source.splitlines()[line_num - 1]
        pointer = ' ' * (col_offset - 1) + '^'
        print(f"Syntax error on line {line_num}:")
        print(error_line)
        print(pointer)
        print(f"Error message: {e}")
        
        # Print context around the error
        start = max(0, line_num - 5)
        end = min(len(source.splitlines()), line_num + 5)
        print("\nContext:")
        for i in range(start, end):
            print(f"{i+1}: {source.splitlines()[i]}")
        
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1:
        check_syntax(sys.argv[1])
    else:
        check_syntax("app.py")
