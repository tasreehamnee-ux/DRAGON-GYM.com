import os
import datetime
from PyQt6.QtPrintSupport import QPrinter, QPrintDialog
from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtGui import QTextDocument

def print_receipt(parent_widget, receipt_number, member_name, amount, plan_name, date_str):
    try:
        if str(receipt_number).isdigit():
            receipt_number = f"REC-{receipt_number}"
        elif not str(receipt_number).startswith("REC-"):
            receipt_number = f"REC-{receipt_number}"
            
        from business_logic import get_settings
        settings = get_settings()
        gym_name = settings.gym_name if settings.gym_name else "وصل استلام نقدية"
        gym_phone = settings.gym_phone if settings.gym_phone else ""
        gym_address = settings.gym_address if settings.gym_address else ""
        
        contact_info = ""
        if gym_phone or gym_address:
            contact_info += '<div class="footer-line" style="margin-top: 8px; font-size: 11px; color: #475569;">'
            if gym_address:
                contact_info += f'📍 {gym_address}'
            if gym_phone:
                if gym_address:
                    contact_info += ' | '
                contact_info += f'📞 {gym_phone}'
            contact_info += '</div>'
            
        printer = QPrinter(QPrinter.PrinterMode.ScreenResolution)
        
        html = f"""
        <html dir="rtl">
        <head>
        <style>
            body {{ font-family: 'Tahoma', 'Arial', sans-serif; font-size: 14px; color: #1e293b; background-color: #ffffff; margin: 0; padding: 20px; }}
            .receipt-card {{ max-width: 450px; margin: 0 auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 12px; }}
            .header {{ text-align: center; margin-bottom: 15px; }}
            .gym-title {{ font-size: 20px; font-weight: bold; color: #1e3a8a; margin: 0 0 5px 0; }}
            .receipt-subtitle {{ font-size: 13px; color: #64748b; margin: 0; font-weight: bold; text-transform: uppercase; }}
            .divider {{ border-top: 2px solid #3b82f6; margin: 15px 0; }}
            .dashed-divider {{ border-top: 1px dashed #cbd5e1; margin: 15px 0; }}
            
            .info-table {{ width: 100%; border-collapse: collapse; margin-bottom: 15px; }}
            .info-table td {{ padding: 8px 5px; font-size: 13px; border-bottom: 1px solid #f1f5f9; }}
            .info-table td.label {{ font-weight: bold; color: #475569; width: 35%; text-align: right; }}
            .info-table td.value {{ color: #0f172a; text-align: left; }}
            
            .total-box {{ background-color: #eff6ff; border: 1px solid #bfdbfe; border-radius: 8px; padding: 12px; text-align: center; margin: 15px 0; }}
            .total-label {{ font-size: 12px; color: #1e40af; font-weight: bold; margin-bottom: 3px; }}
            .total-amount {{ font-size: 22px; font-weight: bold; color: #1d4ed8; }}
            
            .footer {{ text-align: center; font-size: 12px; color: #64748b; margin-top: 20px; }}
        </style>
        </head>
        <body>
            <div class="receipt-card">
                <div class="header">
                    <h1 class="gym-title">{gym_name}</h1>
                    <div class="receipt-subtitle">وصل استلام نقدية</div>
                </div>
                <div class="divider"></div>
                
                <table class="info-table">
                    <tr>
                        <td class="label">رقم الوصل:</td>
                        <td class="value" style="font-family: monospace; font-weight: bold; font-size: 14px;">{receipt_number}</td>
                    </tr>
                    <tr>
                        <td class="label">التاريخ:</td>
                        <td class="value">{date_str}</td>
                    </tr>
                    <tr>
                        <td class="label">اسم المشترك:</td>
                        <td class="value" style="font-weight: 600;">{member_name}</td>
                    </tr>
                    <tr>
                        <td class="label">نوع الاشتراك:</td>
                        <td class="value">{plan_name}</td>
                    </tr>
                </table>
                
                <div class="total-box">
                    <div class="total-label">المبلغ المدفوع</div>
                    <div class="total-amount">{amount:,.0f} د.ع</div>
                </div>
                
                <div class="dashed-divider"></div>
                
                <div class="footer">
                    <div style="font-weight: bold; font-size: 12px; color: #0f172a;">شكراً لاشتراككم معنا! نتمنى لكم تدريباً ممتعاً.</div>
                    {contact_info}
                </div>
            </div>
        </body>
        </html>
        """
        
        document = QTextDocument()
        document.setHtml(html)
        
        # Save a PDF copy to desktop automatically
        from PyQt6.QtGui import QDesktopServices
        from PyQt6.QtCore import QUrl
        desktop_path = os.path.join(os.path.expanduser("~"), "Desktop", "Gym_Receipts")
        os.makedirs(desktop_path, exist_ok=True)
        pdf_path = os.path.join(desktop_path, f"Receipt_{receipt_number}.pdf")
        
        pdf_printer = QPrinter(QPrinter.PrinterMode.ScreenResolution)
        pdf_printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        pdf_printer.setOutputFileName(pdf_path)
        document.print(pdf_printer)
        
        # Also show standard print dialog for thermal printer
        dialog = QPrintDialog(printer, parent_widget)
        if dialog.exec() == QPrintDialog.DialogCode.Accepted:
            document.print(printer)
            return True, f"تم الطباعة وتم حفظ نسخة (PDF) على سطح المكتب في مجلد Gym_Receipts"
            
        # If they cancel print dialog, we still saved the PDF
        return True, f"لم يتم الطباعة، ولكن تم حفظ الفاتورة (PDF) على سطح المكتب في مجلد Gym_Receipts"
    except Exception as e:
        return False, f"حدث خطأ أثناء الطباعة: {str(e)}"
