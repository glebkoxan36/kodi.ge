from flask import render_template, request, flash, redirect, url_for, current_app
from .bp import admin_bp
from .auth_decorators import admin_required
from bson import ObjectId
from db import db, client

@admin_bp.route('/db')
@admin_required
def db_management():
    try:
        collections = db.list_collection_names() if client else []
        collection_counts = {}
        for name in collections:
            collection_counts[name] = db[name].count_documents({}) if client else 0
        
        return render_template(
            'admin/admin.html',
            active_section='db_management',
            collections=collections,
            collection_counts=collection_counts
        )
    except Exception as e:
        current_app.logger.error(f"Database error: {str(e)}")
        flash(f'Database error: {str(e)}', 'danger')
        return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/db/<collection_name>', methods=['GET', 'POST'])
@admin_required
def collection_view(collection_name):
    try:
        if request.method == 'POST':
            doc_id = request.form.get('doc_id')
            if doc_id and client:
                try:
                    db[collection_name].delete_one({'_id': ObjectId(doc_id)})
                    flash('Document deleted successfully', 'success')
                except Exception as e:
                    flash(f'Error deleting document: {str(e)}', 'danger')
            return redirect(url_for('admin.collection_view', collection_name=collection_name))
        
        page = int(request.args.get('page', 1))
        per_page = 20
        skip = (page - 1) * per_page
        
        documents = []
        total = 0
        if client and collection_name in db.list_collection_names():
            total = db[collection_name].count_documents({})
            cursor = db[collection_name].find().skip(skip).limit(per_page)
            for doc in cursor:
                doc['_id'] = str(doc['_id'])
                documents.append(doc)
            
        return render_template(
            'admin/admin.html',
            active_section='db_management',
            collection_name=collection_name,
            documents=documents,
            page=page,
            per_page=per_page,
            total=total
        )
    except Exception as e:
        current_app.logger.error(f"Collection view error: {str(e)}")
        flash(f'Error loading collection: {str(e)}', 'danger')
        return redirect(url_for('admin.db_management'))

@admin_bp.route('/db/<collection_name>/edit/<doc_id>', methods=['GET', 'POST'])
@admin_required
def edit_document(collection_name, doc_id):
    try:
        doc = None
        if client:
            try:
                doc = db[collection_name].find_one({'_id': ObjectId(doc_id)})
            except:
                doc = None
        if not doc:
            flash('Document not found', 'danger')
            return redirect(url_for('admin.collection_view', collection_name=collection_name))
        
        if request.method == 'POST':
            try:
                form_data = {}
                for key, value in request.form.items():
                    if key.startswith('field_'):
                        field_name = key[6:]
                        form_data[field_name] = value
                
                db[collection_name].update_one(
                    {'_id': ObjectId(doc_id)},
                    {'$set': form_data}
                )
                flash('Document updated successfully', 'success')
                return redirect(url_for('admin.collection_view', collection_name=collection_name))
            except Exception as e:
                flash(f'Error updating document: {str(e)}', 'danger')
        
        doc['_id'] = str(doc['_id'])
        
        return render_template(
            'admin/admin.html',
            active_section='db_management',
            collection_name=collection_name,
            doc_id=doc_id,
            document=doc
        )
    except Exception as e:
        current_app.logger.error(f"Edit document error: {str(e)}")
        flash(f'Error loading document: {str(e)}', 'danger')
        return redirect(url_for('admin.collection_view', collection_name=collection_name))

@admin_bp.route('/db/<collection_name>/add', methods=['GET', 'POST'])
@admin_required
def add_document(collection_name):
    try:
        if request.method == 'POST':
            try:
                form_data = {}
                for key, value in request.form.items():
                    if key.startswith('field_'):
                        field_name = key[6:]
                        form_data[field_name] = value
                
                if client:
                    result = db[collection_name].insert_one(form_data)
                    flash(f'Document added successfully with ID: {result.inserted_id}', 'success')
                else:
                    flash('Database connection error', 'danger')
                return redirect(url_for('admin.collection_view', collection_name=collection_name))
            except Exception as e:
                flash(f'Error adding document: {str(e)}', 'danger')
        
        return render_template(
            'admin/admin.html',
            active_section='db_management',
            collection_name=collection_name
        )
    except Exception as e:
        current_app.logger.error(f"Add document error: {str(e)}")
        flash(f'Error loading form: {str(e)}', 'danger')
        return redirect(url_for('admin.collection_view', collection_name=collection_name))
