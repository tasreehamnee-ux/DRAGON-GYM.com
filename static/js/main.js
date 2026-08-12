function showSection(sectionId, btnElement) {
    // إخفاء كل الأقسام
    document.querySelectorAll('.section').forEach(sec => {
        sec.classList.remove('active');
    });
    // إزالة اللون النشط من كل الأزرار
    document.querySelectorAll('.menu-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    
    // إظهار القسم المطلوب وتفعيل الزر
    document.getElementById(sectionId).classList.add('active');
    btnElement.classList.add('active');

    // إذا كان القسم هو المشتركين، نقوم بتحميلهم
    if(sectionId === 'members') {
        loadMembers();
    }
    // إذا كان القسم هو إعدادات الاشتراكات، نقوم بتحميلها
    if(sectionId === 'plans-settings') {
        loadSettings();
        loadPlansTable();
    }
    if(sectionId === 'payments') loadPayments();
    if(sectionId === 'reports') loadReports();
    if(sectionId === 'staff') loadStaff();
}

function loadDashboardStats() {
    fetch('/api/stats')
        .then(response => response.json())
        .then(data => {
            const statsDiv = document.getElementById('dashboard-stats');
            if (data.error) {
                statsDiv.innerHTML = `<p style="color:red;">خطأ: ${data.error}</p>`;
            } else {
                statsDiv.innerHTML = `
                    <div class="stat-box"><h3>إجمالي المشتركين</h3><p>${data.total_members}</p></div>
                    <div class="stat-box"><h3>النشطين</h3><p>${data.active_members}</p></div>
                    <div class="stat-box"><h3>المجمدين</h3><p>${data.frozen_members}</p></div>
                    <div class="stat-box"><h3>المنتهية صلاحيتهم</h3><p>${data.expired_members}</p></div>
                    <div class="stat-box"><h3>المشرفين على الانتهاء</h3><p>${data.expiring_members}</p></div>
                    <div class="stat-box"><h3>أرباح الشهر</h3><p>${data.revenue_this_month}</p></div>
                    <div class="stat-box"><h3>المصروفات</h3><p>${data.expenses_this_month}</p></div>
                    <div class="stat-box"><h3>صافي الربح</h3><p>${data.net_profit}</p></div>
                `;
            }
        })
        .catch(err => {
            document.getElementById('dashboard-stats').innerHTML = "فشل في جلب البيانات.";
        });
}

function loadMembers() {
    const tbody = document.getElementById('members-table-body');
    tbody.innerHTML = '<tr><td colspan="12">جاري التحميل...</td></tr>';
    
    fetch('/api/members')
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                tbody.innerHTML = `<tr><td colspan="12" style="color:red;">خطأ: ${data.error}</td></tr>`;
                return;
            }
            
            tbody.innerHTML = '';
            data.forEach(m => {
                let statusClass = '';
                let statusText = m.status;
                if (m.status === 'active') { statusClass = 'status-active'; statusText = 'نشط'; }
                else if (m.status === 'expired') { statusClass = 'status-expired'; statusText = 'منتهي'; }
                else if (m.status === 'frozen') { statusClass = 'status-frozen'; statusText = 'مجمد'; }
                
                tbody.innerHTML += `
                    <tr>
                        <td>${m.id}</td>
                        <td>${m.name}<br><small style="color:gray;">${m.phone || ''}</small></td>
                        <td>${m.trainer_name}</td>
                        <td>${m.plan}</td>
                        <td style="white-space: nowrap;">${m.start_date}</td>
                        <td style="white-space: nowrap;">${m.end_date}</td>
                        <td style="white-space: nowrap;">${m.frozen_date}</td>
                        <td style="white-space: nowrap;">${m.last_return_date}</td>
                        <td style="font-weight:bold;">${m.remaining_days}</td>
                        <td>${m.notes}</td>
                        <td class="${statusClass}">${statusText}</td>
                        <td style="display:flex; gap:5px; justify-content:center; flex-wrap:wrap;">
                            <button style="background-color: #3b82f6; color: white; border: none; padding: 5px 10px; border-radius: 4px; cursor: pointer; font-weight:bold;" onclick="viewMemberCard(${m.id})">البطاقة 💳</button>
                            <button style="background-color: #ef4444; color: white; border: none; padding: 5px 10px; border-radius: 4px; cursor: pointer; font-weight:bold;" onclick="deleteMember(${m.id})">حذف 🗑️</button>
                            <button style="background-color: #6366f1; color: white; border: none; padding: 5px 10px; border-radius: 4px; cursor: pointer; font-weight:bold;" onclick="enrollFingerprint(${m.id})">بصمة 👆</button>
                            ${m.status === 'expired' 
                                ? `<button style="background-color: #10b981; color: white; border: none; padding: 5px 10px; border-radius: 4px; cursor: pointer; font-weight:bold;" onclick="renewMember(${m.id})">تجديد 🔄</button>` 
                                : `<button style="background-color: #f59e0b; color: white; border: none; padding: 5px 10px; border-radius: 4px; cursor: pointer; font-weight:bold;" onclick="freezeMember(${m.id})">تجميد ⏸️</button>`
                            }
                        </td>
                    </tr>
                `;
            });
        })
        .catch(err => {
            tbody.innerHTML = '<tr><td colspan="12">فشل في جلب البيانات.</td></tr>';
        });
}

function filterMembersTable() {
    const query = document.getElementById('search_member').value.toLowerCase();
    const rows = document.getElementById('members-table-body').getElementsByTagName('tr');
    
    for (let i = 0; i < rows.length; i++) {
        let textContent = rows[i].innerText.toLowerCase();
        if (textContent.includes(query)) {
            rows[i].style.display = '';
        } else {
            rows[i].style.display = 'none';
        }
    }
}

let currentMemberId = null;

function searchMemberCard() {
    const q = document.getElementById('card_search_input').value.toLowerCase();
    if (!q) return;
    
    // Simple frontend search for demo
    fetch('/api/members')
        .then(res => res.json())
        .then(data => {
            if(data.error) return;
            const found = data.find(m => m.name.toLowerCase().includes(q) || (m.phone && m.phone.includes(q)));
            if (found) {
                viewMemberCard(found.id);
            } else {
                alert("لم يتم العثور على المشترك");
            }
        });
}

function viewMemberCard(id, fromSearch = false) {
    fetch('/api/members/' + id)
        .then(res => res.json())
        .then(data => {
            if(data.error) {
                alert("خطأ: " + data.error);
                return;
            }
            currentMemberId = id;
            document.getElementById('mc_id').innerText = data.id;
            document.getElementById('mc_name').innerText = data.name;
            document.getElementById('mc_phone').innerText = data.phone || '-';
            document.getElementById('mc_card').innerText = data.card_id || 'لا يوجد';
            document.getElementById('mc_address').innerText = data.address || '-';
            document.getElementById('mc_trainer').innerText = data.trainer_name || 'بدون مدرب';
            
            document.getElementById('mc_plan').innerText = data.plan_name;
            document.getElementById('mc_start').innerText = data.start_date;
            document.getElementById('mc_end').innerText = data.end_date;
            document.getElementById('mc_notes').innerText = data.notes || '-';
            
            const stObj = document.getElementById('mc_status');
            if (data.status === 'active') { stObj.innerText = 'نشط'; stObj.className = 'status-active'; }
            else if (data.status === 'expired') { stObj.innerText = 'منتهي'; stObj.className = 'status-expired'; }
            else if (data.status === 'frozen') { stObj.innerText = 'مجمد'; stObj.className = 'status-frozen'; }
            
            document.getElementById('card-modal').style.display = 'flex';
        });
}

function deleteMember(id) {
    if(!id) id = currentMemberId;
    if(confirm("هل أنت متأكد من حذف هذا المشترك نهائياً؟")) {
        fetch('/api/members/' + id, { method: 'DELETE' })
            .then(res => res.json())
            .then(data => {
                if(data.error) alert(data.error);
                else {
                    alert("تم الحذف بنجاح");
                    document.getElementById('member-card-content').style.display = 'none';
                    document.getElementById('card-placeholder').style.display = 'block';
                    loadMembers();
                }
            });
    }
}

function freezeMember(id) {
    if(!id) id = currentMemberId;
    if(confirm("هل أنت متأكد من تجميد هذا الاشتراك بدءاً من اليوم؟")) {
        fetch('/api/members/' + id + '/freeze', { method: 'POST' })
            .then(res => res.json())
            .then(data => {
                if(data.error) alert(data.error);
                else {
                    alert(data.message || "تم التجميد بنجاح");
                    viewMemberCard(id, true);
                    loadMembers();
                }
            });
    }
}

function enrollFingerprint(id) {
    if(confirm("يرجى التأكد من تشغيل الكاميرا من (بوابة الدخول) والوقوف أمامها.\nهل تريد بدء التقاط بصمة الوجه الآن؟")) {
        fetch('/api/enroll_face/' + id, { method: 'POST' })
        .then(res => res.json())
        .then(data => {
            if(data.error) alert("خطأ: " + data.error);
            else {
                alert(data.message);
                loadMembers();
            }
        }).catch(e => {
            alert("حدث خطأ في الاتصال بالخادم. تأكد من تشغيل الكاميرا.");
        });
    }
}

function renewMember() { 
    alert("تجديد الاشتراك قيد التطوير، الرجاء إضافة المشترك كجديد مؤقتاً."); 
}

function exportExcel() {
    window.location.href = '/api/export_excel';
}

function uploadExcelFile(input) {
    if (!input.files || input.files.length === 0) return;
    const file = input.files[0];
    const formData = new FormData();
    formData.append('file', file);
    
    fetch('/api/import_excel', {
        method: 'POST',
        body: formData
    })
    .then(res => res.json())
    .then(data => {
        if(data.error) alert("خطأ: " + data.error);
        else {
            alert(data.message || "تم الاستيراد بنجاح");
            loadMembers();
            loadReports();
        }
        input.value = ''; // reset
    });
}

document.addEventListener("DOMContentLoaded", () => {
    loadDashboardStats();
    loadPlansIntoDropdown();

    // Set today's date as default
    document.getElementById('mem_start').valueAsDate = new Date();

    document.getElementById('add-member-form').addEventListener('submit', function(e) {
        e.preventDefault();
        const msgDiv = document.getElementById('add-msg');
        msgDiv.innerHTML = "جاري الحفظ...";
        msgDiv.style.color = "blue";

        const payload = {
            name: document.getElementById('mem_name').value,
            trainer_name: document.getElementById('mem_trainer').value,
            phone: document.getElementById('mem_phone').value,
            card_id: document.getElementById('mem_card').value,
            address: document.getElementById('mem_address').value,
            landmark: document.getElementById('mem_landmark').value,
            plan_name: document.getElementById('mem_plan').value,
            payment_method: document.getElementById('mem_payment').value,
            receipt_number: document.getElementById('mem_receipt').value,
            notes: document.getElementById('mem_notes').value,
            is_pending: document.getElementById('mem_pending').checked,
            start_date: document.getElementById('mem_start').value
        };

        fetch('/api/members', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        })
        .then(res => res.json().then(data => ({status: res.status, body: data})))
        .then(obj => {
            if (obj.status === 201) {
                msgDiv.innerHTML = obj.body.message;
                msgDiv.style.color = "green";
                this.reset();
                document.getElementById('mem_start').valueAsDate = new Date();
                loadDashboardStats();
                loadMembers();
            } else {
                msgDiv.innerHTML = "خطأ: " + obj.body.error;
                msgDiv.style.color = "red";
            }
        })
        .catch(err => {
            msgDiv.innerHTML = "فشل الاتصال بالخادم";
            msgDiv.style.color = "red";
        });
    });

    // Plans settings logic
    document.getElementById('plan-form').addEventListener('submit', function(e) {
        e.preventDefault();
        const msgDiv = document.getElementById('plan-msg');
        msgDiv.innerHTML = "جاري الحفظ...";
        msgDiv.style.color = "blue";
        
        const payload = {
            name: document.getElementById('plan_name').value,
            price: document.getElementById('plan_price').value,
            duration: document.getElementById('plan_duration').value
        };
        
        fetch('/api/plans', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        })
        .then(res => res.json().then(data => ({status: res.status, body: data})))
        .then(obj => {
            if (obj.status === 200 || obj.status === 201) {
                msgDiv.innerHTML = obj.body.message || "تم الحفظ بنجاح";
                msgDiv.style.color = "green";
                this.reset();
                loadPlansTable();
                loadPlansIntoDropdown();
            } else {
                msgDiv.innerHTML = "خطأ: " + obj.body.error;
                msgDiv.style.color = "red";
            }
        })
        .catch(err => {
            msgDiv.innerHTML = "فشل الاتصال بالخادم";
            msgDiv.style.color = "red";
        });
    });

    // System Settings logic
    document.getElementById('settings-form').addEventListener('submit', function(e) {
        e.preventDefault();
        const msgDiv = document.getElementById('settings-msg');
        msgDiv.innerHTML = "جاري الحفظ...";
        msgDiv.style.color = "blue";
        
        const payload = {
            gym_name: document.getElementById('set_gym_name').value,
            gym_phone: document.getElementById('set_gym_phone').value,
            gym_address: document.getElementById('set_gym_address').value,
            door_com_port: document.getElementById('set_door_com_port').value
        };
        
        fetch('/api/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        })
        .then(res => res.json().then(data => ({status: res.status, body: data})))
        .then(obj => {
            if (obj.status === 200 || obj.status === 201) {
                msgDiv.innerHTML = "تم حفظ الإعدادات بنجاح";
                msgDiv.style.color = "green";
                const sidebarName = document.getElementById('sidebar_gym_name');
                if (sidebarName) sidebarName.innerText = payload.gym_name || 'DRAGON GYM';
            } else {
                msgDiv.innerHTML = "خطأ: " + obj.body.error;
                msgDiv.style.color = "red";
            }
        })
        .catch(err => {
            msgDiv.innerHTML = "فشل الاتصال بالخادم";
            msgDiv.style.color = "red";
        });
    });
    // Staff Form submission logic
    document.getElementById('staff-form').addEventListener('submit', function(e) {
        e.preventDefault();
        const payload = {
            name: document.getElementById('staff_name').value,
            role: document.getElementById('staff_role').value,
            salary: document.getElementById('staff_salary').value,
            salary_type: document.getElementById('staff_type').value,
            phone: document.getElementById('staff_phone').value
        };
        fetch('/api/staff', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        }).then(() => {
            this.reset();
            document.getElementById('staff-form-container').style.display = 'none';
            loadStaff();
        });
    });
    // Payment Form submission logic
    document.getElementById('payment-form').addEventListener('submit', function(e) {
        e.preventDefault();
        const payload = {
            description: document.getElementById('pay_desc').value,
            amount: document.getElementById('pay_amount').value,
            method: document.getElementById('pay_method').value,
            receipt: document.getElementById('pay_receipt').value
        };
        fetch('/api/payments', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        }).then(res => res.json()).then(data => {
            if(data.error) alert(data.error);
            else {
                alert("تم الحفظ بنجاح");
                this.reset();
                document.getElementById('payment-modal').style.display = 'none';
                loadPayments();
            }
        });
    });
});

function loadPayments() {
    fetch('/api/payments')
        .then(res => res.json())
        .then(data => {
            const tbody = document.getElementById('payments-table-body');
            tbody.innerHTML = '';
            data.forEach(p => {
                tbody.innerHTML += `
                    <tr>
                        <td>${p.receipt}</td>
                        <td>${p.member_name}</td>
                        <td>${p.amount} د.ع</td>
                        <td>${p.method}</td>
                        <td>${p.date}</td>
                        <td><span style="color: #10b981; font-weight: bold;">🟢 مسدد</span></td>
                    </tr>
                `;
            });
        });
}

function loadReports() {
    fetch('/api/stats')
        .then(res => res.json())
        .then(data => {
            document.getElementById('rep_active').innerText = data.active_members;
            document.getElementById('rep_total').innerText = data.total_members;
            document.getElementById('rep_revenue').innerText = data.revenue_this_month.toLocaleString() + ' د.ع';
        });
        
    fetch('/api/payments')
        .then(res => res.json())
        .then(data => {
            const tbody = document.getElementById('reports-payments-body');
            tbody.innerHTML = '';
            data.slice(0, 10).forEach(p => { // show only latest 10
                tbody.innerHTML += `
                    <tr>
                        <td>${p.member_name}</td>
                        <td>${p.amount} د.ع</td>
                        <td>${p.method}</td>
                        <td>${p.date}</td>
                    </tr>
                `;
            });
        });
}

function loadStaff() {
    fetch('/api/staff')
        .then(res => res.json())
        .then(data => {
            const tbody = document.getElementById('staff-table-body');
            tbody.innerHTML = '';
            data.forEach(s => {
                tbody.innerHTML += `
                    <tr>
                        <td>${s.name}</td>
                        <td>${s.role}</td>
                        <td>${s.salary} د.ع</td>
                        <td>${s.salary_type}</td>
                        <td>${s.phone || '-'}</td>
                        <td>
                            <button class="btn-primary" style="padding:4px 10px; font-size:12px; background-color:#3b82f6;">تعديل ✏️</button>
                            <button class="btn-danger" style="padding:4px 10px; font-size:12px;" onclick="deleteStaff(${s.id})">حذف 🗑️</button>
                        </td>
                    </tr>
                `;
            });
        });
}

function deleteStaff(id) {
    if(confirm("تأكيد حذف الموظف؟")) {
        fetch('/api/staff/' + id, { method: 'DELETE' }).then(() => loadStaff());
    }
}

function loadSettings() {
    fetch('/api/settings')
        .then(res => res.json())
        .then(data => {
            if(!data.error) {
                document.getElementById('set_gym_name').value = data.gym_name || '';
                document.getElementById('set_gym_phone').value = data.gym_phone || '';
                document.getElementById('set_gym_address').value = data.gym_address || '';
                document.getElementById('set_door_com_port').value = data.door_com_port || '';
                
                const sidebarName = document.getElementById('sidebar_gym_name');
                if (sidebarName) sidebarName.innerText = data.gym_name || 'DRAGON GYM';
            }
        });
}

function loadPlansIntoDropdown() {
    fetch('/api/plans')
        .then(res => res.json())
        .then(data => {
            const select = document.getElementById('mem_plan');
            select.innerHTML = '';
            if(!data.error) {
                data.forEach(p => {
                    select.innerHTML += `<option value="${p.name}">${p.name} - ${p.price}</option>`;
                });
            }
        });
}

function loadPlansTable() {
    const tbody = document.getElementById('plans-table-body');
    tbody.innerHTML = '<tr><td colspan="4">جاري التحميل...</td></tr>';
    
    fetch('/api/plans')
        .then(res => res.json())
        .then(data => {
            tbody.innerHTML = '';
            if(data.error) {
                tbody.innerHTML = `<tr><td colspan="4" style="color:red;">خطأ: ${data.error}</td></tr>`;
                return;
            }
            
            data.forEach(p => {
                tbody.innerHTML += `
                    <tr>
                        <td>${p.name}</td>
                        <td>${p.price}</td>
                        <td>${p.duration}</td>
                        <td><button style="background-color: #ef4444; color: white; border: none; padding: 5px 15px; border-radius: 4px; cursor: pointer; font-weight:bold; width: 100%;" onclick="deletePlan(${p.id})">حذف 🗑️</button></td>
                    </tr>
                `;
            });
        });
}

function deletePlan(id) {
    if(!confirm("هل أنت متأكد من حذف هذا الاشتراك؟")) return;
    fetch('/api/plans/' + id, {
        method: 'DELETE'
    })
    .then(res => res.json())
    .then(data => {
        if(data.error) {
            alert("خطأ: " + data.error);
        } else {
            loadPlansTable();
            loadPlansIntoDropdown();
        }
    })
    .catch(err => alert("فشل الاتصال بالخادم"));
}

let isCameraOn = false;
let cameraStream = null;
let captureInterval = null;

async function toggleCamera() {
    isCameraOn = !isCameraOn;
    const btn = document.getElementById('btn-toggle-camera');
    const feed = document.getElementById('video-feed');
    const statusText = document.getElementById('face-status-text');
    
    if (isCameraOn) {
        try {
            cameraStream = await navigator.mediaDevices.getUserMedia({ video: true });
            feed.srcObject = cameraStream;
            feed.style.display = "block";
            btn.innerText = "????? ????????";
            btn.style.backgroundColor = "#ef4444";
            statusText.innerText = "???????? ????...";
            statusText.style.color = "#10b981";
            
            startFrameCapture();
        } catch (err) {
            console.error("Error accessing camera:", err);
            alert("??? ??? ????? ?????? ????????.");
            isCameraOn = false;
        }
    } else {
        if (cameraStream) {
            cameraStream.getTracks().forEach(track => track.stop());
            cameraStream = null;
        }
        if (captureInterval) {
            clearInterval(captureInterval);
            captureInterval = null;
        }
        feed.srcObject = null;
        feed.style.display = "none";
        btn.innerText = "??? ????????";
        btn.style.backgroundColor = "#10b981";
        statusText.innerText = "???? ???????? ?????";
        statusText.style.color = "#64748b";
    }
}

function startFrameCapture() {
    const video = document.getElementById('video-feed');
    const canvas = document.getElementById('camera-canvas');
    const context = canvas.getContext('2d');
    
    captureInterval = setInterval(() => {
        if (!isCameraOn || video.videoWidth === 0) return;
        
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        context.drawImage(video, 0, 0, canvas.width, canvas.height);
        
        const frameData = canvas.toDataURL('image/jpeg', 0.5);
        
        fetch('/api/process_frame', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image: frameData })
        })
        .then(res => res.json())
        .then(data => {
            if (data.recognized) {
                document.getElementById('face-status-text').innerText = "?? ??????: " + data.member_name;
            }
        })
        .catch(err => console.error("Error sending frame:", err));
        
    }, 1000);
}

