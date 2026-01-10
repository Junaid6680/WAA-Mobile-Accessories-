                # --- خوبصورت پی ڈی ایف بل کی تیاری ---
                pdf = FPDF()
                pdf.add_page()
                
                # لوگو (اگر فائل موجود ہو)
                if os.path.exists("logo.png"):
                    pdf.image("logo.png", 10, 8, 33)
                
                # شاپ کی معلومات
                pdf.set_font("Arial", 'B', 20)
                pdf.cell(0, 10, SHOP_NAME, ln=True, align="C")
                pdf.set_font("Arial", '', 10)
                pdf.cell(0, 5, SHOP_ADDRESS, ln=True, align="C")
                pdf.cell(0, 5, f"Contact: {SHOP_CONTACT}", ln=True, align="C")
                pdf.ln(10)
                
                # کسٹمر اور بل کی معلومات
                pdf.set_fill_color(240, 240, 240)
                pdf.set_font("Arial", 'B', 12)
                pdf.cell(0, 10, f" INVOICE # {bill_no} ", ln=True, align="L", fill=True)
                pdf.set_font("Arial", '', 11)
                pdf.cell(100, 10, f"Customer: {customer}", ln=False)
                pdf.cell(0, 10, f"Date: {datetime.now().strftime('%d-%m-%Y %H:%M')}", ln=True, align="R")
                pdf.ln(5)
                
                # ٹیبل ہیڈر
                pdf.set_font("Arial", 'B', 11)
                pdf.cell(90, 10, "Description", 1)
                pdf.cell(30, 10, "Qty", 1, 0, 'C')
                pdf.cell(30, 10, "Price", 1, 0, 'C')
                pdf.cell(40, 10, "Total", 1, 1, 'C')
                
                # ٹیبل ڈیٹا
                pdf.set_font("Arial", '', 11)
                pdf.cell(90, 10, item, 1)
                pdf.cell(30, 10, str(qty), 1, 0, 'C')
                pdf.cell(30, 10, f"{price}", 1, 0, 'C')
                pdf.cell(40, 10, f"{new_bill_amount}", 1, 1, 'C')
                
                pdf.ln(5)
                
                # مکمل کھاتہ (Ledger Summary)
                pdf.set_font("Arial", 'B', 11)
                pdf.cell(130, 8, "Previous Balance (Purana Baqaya):", 0, 0, 'R')
                pdf.cell(60, 8, f"Rs. {old_balance}", 0, 1, 'R')
                
                pdf.cell(130, 8, "Current Bill Amount:", 0, 0, 'R')
                pdf.cell(60, 8, f"Rs. {new_bill_amount}", 0, 1, 'R')
                
                pdf.set_text_color(0, 0, 255) # نیلا رنگ ادائیگی کے لیے
                pdf.cell(130, 8, "Total Received (Paid Today):", 0, 0, 'R')
                pdf.cell(60, 8, f"Rs. {cash + bank}", 0, 1, 'R')
                
                pdf.set_text_color(255, 0, 0) # لال رنگ باقی رقم کے لیے
                pdf.set_font("Arial", 'B', 13)
                pdf.cell(130, 10, "NET BALANCE (Total Baqaya):", 0, 0, 'R')
                pdf.cell(60, 10, f"Rs. {final_balance}", 1, 1, 'R')
                
                pdf.ln(10)
                pdf.set_text_color(0, 0, 0)
                pdf.set_font("Arial", 'I', 10)
                pdf.cell(0, 10, "Thank you for your business! Software by WAA Mobile", ln=True, align="C")

                # فائل سیو کرنا
                if not os.path.exists("bills"): os.mkdir("bills")
                path = f"bills/Bill_{bill_no}.pdf"
                pdf.output(path)
