import re

with open('gui_app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# The methods to move start with "    def setup_expenses(self):"
# and end just before "def main():"
methods_pattern = r"(    def setup_expenses\(self\):.*?)def main\(\):"
match = re.search(methods_pattern, content, re.DOTALL)

if match:
    methods_code = match.group(1)
    # Remove them from the end
    content = content.replace(methods_code, "")
    
    # Insert them before class AddExpenseDialog(QDialog):
    target = "class AddExpenseDialog(QDialog):"
    if target in content:
        content = content.replace(target, methods_code + "\n\n" + target)
        with open('gui_app.py', 'w', encoding='utf-8') as f:
            f.write(content)
        print("Methods successfully moved inside MainWindow!")
    else:
        print("Target class not found!")
else:
    print("Methods not found at the end of the file!")
