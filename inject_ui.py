import re

with open('gui_app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add Staff and Expense Dialog classes before main()
dialogs_code = """
class AddExpenseDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("إضافة مصروف جديد")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setMinimumWidth(350)
        self.setStyleSheet(parent.styleSheet() if parent else "")
        layout = QFormLayout(self)
        
        self.title_input = QLineEdit()
        self.amount_input = QLineEdit()
        self.category_combo = QComboBox()
        self.category_combo.addItems(["إيجار", "رواتب", "كهرباء", "صيانة", "أخرى"])
        self.notes_input = QLineEdit()
        
        layout.addRow("العنوان (الوصف):", self.title_input)
        layout.addRow("المبلغ (د.ع):", self.amount_input)
        layout.addRow("التصنيف:", self.category_combo)
        layout.addRow("ملاحظات:", self.notes_input)
        
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("حفظ")
        self.save_btn.clicked.connect(self.accept)
        self.cancel_btn = QPushButton("إلغاء")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addRow(btn_layout)

    def get_data(self):
        return {
            'title': self.title_input.text(),
            'amount': self.amount_input.text(),
            'category': self.category_combo.currentText(),
            'notes': self.notes_input.text()
        }

class AddStaffDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("إضافة كادر/مدرب")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setMinimumWidth(350)
        self.setStyleSheet(parent.styleSheet() if parent else "")
        layout = QFormLayout(self)
        
        self.name_input = QLineEdit()
        self.phone_input = QLineEdit()
        self.role_combo = QComboBox()
        self.role_combo.addItems(["مدرب", "موظف استقبال", "عامل نظافة", "مدير"])
        self.salary_type_combo = QComboBox()
        self.salary_type_combo.addItems(["ثابت", "نسبة"])
        self.salary_input = QLineEdit()
        
        layout.addRow("الاسم:", self.name_input)
        layout.addRow("رقم الهاتف:", self.phone_input)
        layout.addRow("المنصب:", self.role_combo)
        layout.addRow("نوع الراتب:", self.salary_type_combo)
        layout.addRow("الراتب / النسبة:", self.salary_input)
        
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("حفظ")
        self.save_btn.clicked.connect(self.accept)
        self.cancel_btn = QPushButton("إلغاء")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addRow(btn_layout)

    def get_data(self):
        return {
            'name': self.name_input.text(),
            'phone': self.phone_input.text(),
            'role': self.role_combo.currentText(),
            'salary_type': self.salary_type_combo.currentText(),
            'salary': self.salary_input.text()
        }

"""

# Add setup methods inside MainWindow class, before "def main():"
methods_code = """
    def setup_expenses(self):
        layout = QVBoxLayout(self.expenses_page)
        layout.setContentsMargins(20, 20, 20, 20)
        
        header = QHBoxLayout()
        add_btn = QPushButton("➕ إضافة مصروف جديد")
        add_btn.setStyleSheet("background-color: #ef4444; color: white; padding: 8px 15px; font-weight: bold;")
        add_btn.clicked.connect(self.show_add_expense_dialog)
        header.addWidget(add_btn, alignment=Qt.AlignmentFlag.AlignRight)
        header.addStretch()
        layout.addLayout(header)
        
        self.expenses_table = QTableWidget()
        self.expenses_table.setColumnCount(5)
        self.expenses_table.setHorizontalHeaderLabels(["التاريخ", "العنوان", "التصنيف", "المبلغ", "ملاحظات"])
        self.expenses_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.expenses_table.verticalHeader().setVisible(False)
        layout.addWidget(self.expenses_table)
        self.refresh_expenses()

    def show_add_expense_dialog(self):
        dialog = AddExpenseDialog(self)
        if dialog.exec():
            data = dialog.get_data()
            if not data['title'] or not data['amount']: return
            from business_logic import add_expense
            success, msg = add_expense(data['title'], data['amount'], data['category'], data['notes'])
            if success:
                self.refresh_expenses()
                self.refresh_dashboard()
                self.show_toast(msg)

    def refresh_expenses(self):
        from business_logic import get_expenses
        expenses = get_expenses()
        self.expenses_table.setRowCount(len(expenses))
        for row, e in enumerate(expenses):
            self.expenses_table.setItem(row, 0, QTableWidgetItem(str(e.expense_date)))
            self.expenses_table.setItem(row, 1, QTableWidgetItem(e.title))
            self.expenses_table.setItem(row, 2, QTableWidgetItem(e.category))
            self.expenses_table.setItem(row, 3, QTableWidgetItem(f"{e.amount:,.0f} د.ع"))
            self.expenses_table.setItem(row, 4, QTableWidgetItem(e.notes))

    def setup_staff(self):
        layout = QVBoxLayout(self.staff_page)
        layout.setContentsMargins(20, 20, 20, 20)
        
        header = QHBoxLayout()
        add_btn = QPushButton("➕ إضافة كادر جديد")
        add_btn.setStyleSheet("background-color: #3b82f6; color: white; padding: 8px 15px; font-weight: bold;")
        add_btn.clicked.connect(self.show_add_staff_dialog)
        header.addWidget(add_btn, alignment=Qt.AlignmentFlag.AlignRight)
        header.addStretch()
        layout.addLayout(header)
        
        self.staff_table = QTableWidget()
        self.staff_table.setColumnCount(5)
        self.staff_table.setHorizontalHeaderLabels(["الاسم", "المنصب", "الراتب", "النوع", "الهاتف"])
        self.staff_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.staff_table.verticalHeader().setVisible(False)
        layout.addWidget(self.staff_table)
        self.refresh_staff()

    def show_add_staff_dialog(self):
        dialog = AddStaffDialog(self)
        if dialog.exec():
            data = dialog.get_data()
            if not data['name']: return
            from business_logic import add_staff
            success, msg = add_staff(data['name'], data['phone'], data['role'], data['salary'] or 0, data['salary_type'])
            if success:
                self.refresh_staff()
                self.show_toast(msg)

    def refresh_staff(self):
        from business_logic import get_all_staff
        staffs = get_all_staff()
        self.staff_table.setRowCount(len(staffs))
        for row, s in enumerate(staffs):
            self.staff_table.setItem(row, 0, QTableWidgetItem(s.name))
            self.staff_table.setItem(row, 1, QTableWidgetItem(s.role))
            self.staff_table.setItem(row, 2, QTableWidgetItem(f"{s.salary:,.0f}"))
            self.staff_table.setItem(row, 3, QTableWidgetItem(s.salary_type))
            self.staff_table.setItem(row, 4, QTableWidgetItem(s.phone or ""))

"""

if "def main():" in content:
    new_content = content.replace("def main():", dialogs_code + methods_code + "\ndef main():")
    with open('gui_app.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("UI classes injected successfully!")
else:
    print("Could not find 'def main():'")
