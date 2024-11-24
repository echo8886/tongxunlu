from flask import Flask, jsonify, request, render_template, redirect, url_for, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from models import db, Contact, ContactDetail
import pandas as pd
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///contacts.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your-secret-key'

db.init_app(app)

# Create database tables
with app.app_context():
    db.create_all()

# 首页路由
@app.route('/')
def index():
    search = request.args.get('search', '')
    if search:
        contacts = Contact.query.filter(
            (Contact.name.like(f'%{search}%')) |
            (Contact.contact_details.any(ContactDetail.value.like(f'%{search}%')))
        ).all()
    else:
        contacts = Contact.query.all()
    return render_template('index.html', contacts=contacts, search=search)

# 添加联系人页面
@app.route('/add_contact', methods=['GET', 'POST'])
def add_contact():
    if request.method == 'POST':
        name = request.form['name']
        contact = Contact(name=name)
        
        # 处理电话号码
        phones = request.form.getlist('phone')
        for phone in phones:
            if phone.strip():
                contact_detail = ContactDetail(detail_type='phone', value=phone)
                contact.contact_details.append(contact_detail)
        
        # 处理邮箱
        emails = request.form.getlist('email')
        for email in emails:
            if email.strip():
                contact_detail = ContactDetail(detail_type='email', value=email)
                contact.contact_details.append(contact_detail)
        
        # 处理地址
        addresses = request.form.getlist('address')
        for address in addresses:
            if address.strip():
                contact_detail = ContactDetail(detail_type='address', value=address)
                contact.contact_details.append(contact_detail)
        
        db.session.add(contact)
        db.session.commit()
        flash('联系人添加成功！')
        return redirect(url_for('index'))
    
    return render_template('add_contact.html')

# 更新书签状态
@app.route('/toggle_bookmark/<int:contact_id>')
def toggle_bookmark(contact_id):
    contact = Contact.query.get_or_404(contact_id)
    contact.is_bookmarked = not contact.is_bookmarked
    db.session.commit()
    flash('书签状态已更新！')
    return redirect(url_for('index'))

# 导出联系人
@app.route('/export')
def export_contacts():
    contacts = Contact.query.all()
    data = []
    
    for contact in contacts:
        contact_data = {
            '姓名': contact.name,
            '已收藏': '是' if contact.is_bookmarked else '否'
        }
        
        # 获取所有类型的联系方式
        phones = [d.value for d in contact.contact_details if d.detail_type == 'phone']
        emails = [d.value for d in contact.contact_details if d.detail_type == 'email']
        addresses = [d.value for d in contact.contact_details if d.detail_type == 'address']
        
        contact_data['电话'] = '; '.join(phones)
        contact_data['邮箱'] = '; '.join(emails)
        contact_data['地址'] = '; '.join(addresses)
            
        data.append(contact_data)
    
    df = pd.DataFrame(data)
    export_path = 'contacts_export.xlsx'
    df.to_excel(export_path, index=False)
    return send_file(export_path, as_attachment=True, download_name='通讯录导出.xlsx')

# 导入联系人页面
@app.route('/import', methods=['GET', 'POST'])
def import_contacts():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('没有选择文件')
            return redirect(request.url)
            
        file = request.files['file']
        if file.filename == '':
            flash('没有选择文件')
            return redirect(request.url)
            
        if not file.filename.endswith('.xlsx'):
            flash('请上传Excel文件(.xlsx)')
            return redirect(request.url)
            
        try:
            df = pd.read_excel(file)
            for _, row in df.iterrows():
                contact = Contact(
                    name=row['姓名'],
                    is_bookmarked=True if row.get('已收藏') == '是' else False
                )
                
                # 处理电话
                if pd.notna(row.get('电话')):
                    for phone in str(row['电话']).split(';'):
                        if phone.strip():
                            contact_detail = ContactDetail(detail_type='phone', value=phone.strip())
                            contact.contact_details.append(contact_detail)
                
                # 处理邮箱
                if pd.notna(row.get('邮箱')):
                    for email in str(row['邮箱']).split(';'):
                        if email.strip():
                            contact_detail = ContactDetail(detail_type='email', value=email.strip())
                            contact.contact_details.append(contact_detail)
                
                # 处理地址
                if pd.notna(row.get('地址')):
                    for address in str(row['地址']).split(';'):
                        if address.strip():
                            contact_detail = ContactDetail(detail_type='address', value=address.strip())
                            contact.contact_details.append(contact_detail)
                
                db.session.add(contact)
            
            db.session.commit()
            flash('联系人导入成功！')
            return redirect(url_for('index'))
        except Exception as e:
            flash(f'导入失败：{str(e)}')
            return redirect(request.url)
    
    return render_template('import.html')

# 在现有路由后添加删除联系人路由
@app.route('/delete_contact/<int:contact_id>')
def delete_contact(contact_id):
    contact = Contact.query.get_or_404(contact_id)
    db.session.delete(contact)
    db.session.commit()
    flash('联系人已删除！')
    return redirect(url_for('index'))

# 添加编辑联系人路由
@app.route('/edit_contact/<int:contact_id>', methods=['GET', 'POST'])
def edit_contact(contact_id):
    contact = Contact.query.get_or_404(contact_id)
    
    if request.method == 'POST':
        contact.name = request.form['name']
        
        # 删除现有的联系方式
        for detail in contact.contact_details:
            db.session.delete(detail)
        
        # 添加新的联系方式
        # 处理电话号码
        phones = request.form.getlist('phone')
        for phone in phones:
            if phone.strip():
                contact_detail = ContactDetail(detail_type='phone', value=phone)
                contact.contact_details.append(contact_detail)
        
        # 处理邮箱
        emails = request.form.getlist('email')
        for email in emails:
            if email.strip():
                contact_detail = ContactDetail(detail_type='email', value=email)
                contact.contact_details.append(contact_detail)
        
        # 处理地址
        addresses = request.form.getlist('address')
        for address in addresses:
            if address.strip():
                contact_detail = ContactDetail(detail_type='address', value=address)
                contact.contact_details.append(contact_detail)
        
        db.session.commit()
        flash('联系人更新成功！')
        return redirect(url_for('index'))
    
    # 获取现有联系方式
    phones = [d.value for d in contact.contact_details if d.detail_type == 'phone']
    emails = [d.value for d in contact.contact_details if d.detail_type == 'email']
    addresses = [d.value for d in contact.contact_details if d.detail_type == 'address']
    
    return render_template('edit_contact.html', 
                         contact=contact, 
                         phones=phones, 
                         emails=emails, 
                         addresses=addresses)

if __name__ == '__main__':
    app.run(debug=True)
