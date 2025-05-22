from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
import logging

from flask import Flask, jsonify, request, render_template, redirect, url_for, session, g, Response, send_from_directory
from sqlalchemy import or_, and_, func
from sqlalchemy.orm import sessionmaker

from models import BasicInfo, EcologyData, MorphologyData, GenomicsData, PhysiologyData, db
from dbconnector import db_connector
import csv
from io import StringIO
import os

# 配置文件相关的变量
file_name = ["colony_morphology", "microscopic_morphology", "genome_sequence_file", "protein_sequence_file",
             "transcript_sequence_file", "genome_annotation_file_gbk", "genome_annotation_file_gff"]
file_paths = {}
ad = {
    "colony_morphology": "_a.jpg", "microscopic_morphology": "_b.jpg", "genome_sequence_file": ".fna",
    "protein_sequence_file": ".faa", "transcript_sequence_file": ".ffn", "genome_annotation_file_gbk": ".gbk",
    "genome_annotation_file_gff": ".gff"
}

app = Flask(__name__)
app.config.from_object('config.Config')

db.init_app(app)
dbc = db_connector()

logger = logging.getLogger(__name__)

@app.route('/')
def index():
    # 重定向到 results 路由，不带任何查询参数，显示所有结果
    return redirect(url_for('results'))


@app.route('/results')
def results():
    query = request.args.get('q', '')
    page = request.args.get('page', 1, type=int)
    sort = request.args.get('sort', 'relevance')
    per_page = 9  # 每页显示的结果数
    
    # 构建基本查询 - 当没有查询参数时，返回所有结果
    if not query:
        base_query = BasicInfo.query
    else:
        base_query = BasicInfo.query.filter(
            or_(
                BasicInfo.chinese_name.ilike(f'%{query}%'),
                BasicInfo.classification_status.ilike(f'%{query}%'),
                BasicInfo.basic_info_id.ilike(f'%{query}%'),
                BasicInfo.genus.ilike(f'%{query}%'),
                BasicInfo.species.ilike(f'%{query}%'),
                # 添加对genus+species组合的搜索支持
                func.concat(BasicInfo.genus, ' ', BasicInfo.species).ilike(f'%{query}%')
            )
        )
    
    # 应用排序
    if sort == 'name_asc':
        base_query = base_query.order_by(BasicInfo.species.asc())
    elif sort == 'name_desc':
        base_query = base_query.order_by(BasicInfo.species.desc())
    elif sort == 'date_new':
        base_query = base_query.order_by(BasicInfo.preservation_date.desc())
    elif sort == 'date_old':
        base_query = base_query.order_by(BasicInfo.preservation_date.asc())
    else:  # 默认排序 - 按保藏日期降序（最新优先）
        base_query = base_query.order_by(BasicInfo.preservation_date.desc())
    
    # 计算总结果数
    total_results = base_query.count()
    total_pages = (total_results + per_page - 1) // per_page  # 向上取整
    
    # 应用分页
    results = base_query.offset((page - 1) * per_page).limit(per_page).all()
    
    # 创建构建页面URL的函数
    def build_page_url(page_num):
        query_params = request.args.copy()
        query_params['page'] = page_num
        # 使用MultiDict的to_dict(flat=False)保留所有值，然后手动格式化URL参数字符串
        params = []
        for key, values in query_params.lists():
            for value in values:
                params.append(f"{key}={value}")
        return f"{request.path}?{'&'.join(params)}"
    
    return render_template(
        'results.html', 
        query=query,
        results=results, 
        total_results=total_results,
        page=page,
        total_pages=total_pages,
        sort=sort,
        is_advanced_search=False,
        build_page_url=build_page_url
    )


@app.route('/suggestions')
def suggestions():
    query = request.args.get('q', '')
    suggestions = []
    if query and len(query) > 1:
        results = BasicInfo.query.filter(
            or_(
                BasicInfo.chinese_name.ilike(f'%{query}%'),
                BasicInfo.classification_status.ilike(f'%{query}%'),
                BasicInfo.genus.ilike(f'%{query}%'),
                BasicInfo.species.ilike(f'%{query}%'),
                BasicInfo.basic_info_id.ilike(f'%{query}%'),
                # 添加对genus+species组合的搜索支持
                func.concat(BasicInfo.genus, ' ', BasicInfo.species).ilike(f'%{query}%')
            )
        ).limit(5).all()
        
        suggestions = []
        for result in results:
            if result.chinese_name:
                suggestions.append(result.chinese_name)
            else:
                suggestions.append(f"{result.genus} {result.species}")
    
    return jsonify(suggestions)


@app.route('/detail/<basic_info_id>')
def detail(basic_info_id):
    basic_info = BasicInfo.query.get_or_404(basic_info_id)
    ecology_data = EcologyData.query.get(basic_info_id)
    morphology_data = MorphologyData.query.get(basic_info_id)
    genomics_data = GenomicsData.query.get(basic_info_id)
    physiology_data = PhysiologyData.query.get(basic_info_id)
    return render_template('detail.html', basic_info=basic_info, ecology_data=ecology_data,
                           morphology_data=morphology_data, genomics_data=genomics_data,
                           physiology_data=physiology_data)


@dataclass
class User:
    id: int
    username: str
    password: str


file_pass = str(open("password.txt", "r").read())
users = [User(1, "admin", file_pass)]


@app.before_request
def before_request():
    g.user = None
    if 'user_id' in session:
        user = [u for u in users if u.id == session['user_id']][0]
        g.user = user


@app.route('/admin', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        session.pop('user_id', None)
        username = "admin"
        password = request.form.get("password", None)
        user = [u for u in users if u.username == username]
        if len(user) > 0:
            user = user[0]
        if user and user.password == password:
            session['user_id'] = user.id
            return redirect(url_for('profile'))
    return render_template("login.html")


@app.route('/submit', methods=['POST'])
def submit():
    dt = dict(request.form)
    print(dt)
    for fn in file_name:
        if fn not in request.files:
            continue
        file = request.files[fn]
        if file.filename == '':
            continue
        if file:
            filename = dt["basic_info_id"] + ad[fn]
            print(filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            file_paths[fn] = file_path

    try:
        dbc.add_to_db(dt)
        return redirect(url_for('success'))
    except Exception as e:
        print(e)
        return render_template('failure.html', message=str(e))


@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if not g.user:
        return redirect(url_for('login'))
    microbes = dbc.getID()
    stat = dbc.get_statistics()
    return render_template("profile.html", microbes=microbes, stat=stat)


@app.route('/logout')
def logout():
    session.pop("user_id", None)
    return redirect(url_for('login'))


@app.route('/delete', methods=['POST'])
def delete():
    pr_id = dict(request.form)["basic_info_id"]
    try:
        dbc.delete(pr_id)
        return redirect(url_for('success'))
    except Exception as e:
        return render_template('failure.html', message=str(e))


@app.route('/update', methods=['POST'])
def update_microbe():
    data = dict(request.form)
    print(data)
    try:
        dt = dict(request.form)
        print(dt)
        for fn in file_name:
            if fn not in request.files:
                continue
            file = request.files[fn]
            if file.filename == '':
                continue
            if file:
                filename = (dt["basic_info_id"] + ad[fn])
                print(filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                file_paths[fn] = file_path
        dbc.update(data)
        return redirect(url_for('success'))
    except Exception as e:
        print(e)
        return render_template('failure.html', message=str(e))


@app.route('/download_template')
def download_template():
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow([
        'basic_info_id', 'genus', 'species', 'classification_status', 'preservation_date',
        'chinese_name', 'is_type_strain', 'preservation_unit', 'preservation_method',
        'preserver', 'preservation_notes', 'contact_info', 'location_name',
        'habitat', 'coordinates', 'sampling_date',
        'sample_type', 'temperature', 'oxygen_requirement', 'sampler',
        'description', 'colony_color', 'colony_shape', 'colony_edge',
        'colony_surface', 'colony_size', 'colony_texture', 'motility', 'spore_shape',
        'spore_staining_reaction', 'observation_medium', 'observation_conditions',
        'sequencing_method', 'assembly_method', 'annotation_method', 'genome_size', 'gc_content', 'n50',
        'contig_count', 'scaffold_count', 'trna_count', 'rrna_count', 'nicotine_degradation',
        'cellulase', 'acidic_protease', 'lignin_degrading_enzymes'
    ])
    writer.writerows([
        ["13+NA-2-16", "Peribacillus", "frigoritolerans", "Bacteria;Firmicutes;Bacilli;Bacillales;Bacillaceae;Peribacillus", "2023-11-11", "耐寒短芽胞杆菌", "否", "云南省微生物研究所", "甘油保藏",
         "海轩", "无", "1506165827@qq.com", "云南大理", "茶树下土壤", "无坐标数据", "2023-08-21",
         "土壤", "23", "好氧", "海轩", "杆状", "白色", "圆形", "褶皱", "凸起", "大", "粘稠", "强",
         "无数据", "无数据", "NA", "30℃", "Illumina测序", "Spades", "PROKKA", "5.54", "40.60", "107454",
         "314", "", "68", "4", "阳性", "阴性", "阳性", "阴性"]
    ])
    output.seek(0)
    return Response(output, mimetype='text/csv', headers={"Content-Disposition": "attachment;filename=template.csv"})


@app.route('/upload_csv', methods=['POST'])
def upload_csv():
    file = request.files['file']
    if not file:
        return render_template('failure.html', message='No file provided')

    try:
        stream = StringIO(file.stream.read().decode('UTF-8'))
        reader = csv.DictReader(stream)
        rows = list(reader)  # 读取所有行到一个列表中
        print(reader)
        for row in rows:
            dbc.add_to_db(row)
        return redirect(url_for('success'))
    except Exception as e:
        return render_template('failure.html', message=str(e))


@app.route('/success')
def success():
    return render_template('success.html')


@app.route('/microbe/<eid>', methods=['GET'])
def get_microbe(eid):
    microbe = dbc.getdata(eid)
    if microbe:
        for key, value in microbe.items():
            if isinstance(value, (date, Decimal)):
                microbe[key] = str(value)
        return jsonify(microbe)
    else:
        return jsonify({"error": "Microbe not found"}), 404


@app.route('/uploads/<filename>')
def download_file(filename):
    uploads = os.path.join(app.root_path, app.config['UPLOAD_FOLDER'])
    file_path = os.path.join(uploads, filename)
    
    # 检查文件是否存在
    if not os.path.exists(file_path):
        return "文件不存在", 404
    
    try:
        return send_from_directory(uploads, filename)
    except Exception as e:
        logger.error(f"文件下载失败: {str(e)}")
        return "文件下载失败", 500


@app.route('/advanced_search')
def advanced_search():
    """Render the advanced search page"""
    return render_template('advanced_search.html')

@app.route('/advanced_results')
def advanced_results():
    """Process advanced search form and return results"""
    page = request.args.get('page', 1, type=int)
    per_page = 9  # Number of results per page
    
    # Parse search parameters
    search_params = {}
    logic_ops = {}
    freezer_location_params = {}
    
    # Extract all query parameters
    for key, value in request.args.items():
        if key.startswith('logic_'):
            # Store logic operators
            field_name = key[6:]  # Remove 'logic_' prefix
            logic_ops[field_name] = value
        elif key.startswith('BasicInfo.preservation_notes_'):
            # Handle freezer location components
            component = key.split('_')[-1]  # Get component name (freezer, layer, etc)
            if value:  # Only store non-empty values
                freezer_location_params[component] = value
        elif '_min' in key or '_max' in key:
            # Handle range parameters
            base_key = key.rsplit('_', 1)[0]
            range_type = key.rsplit('_', 1)[1]  # 'min' or 'max'
            
            if base_key not in search_params:
                search_params[base_key] = {}
            
            if value:  # Only add non-empty values
                search_params[base_key][range_type] = value
        elif '.' in key and value:
            # Regular field parameters
            search_params[key] = value
    
    # Build query
    query = db.session.query(BasicInfo).distinct()
    
    # Join necessary tables
    table_joins = set()
    for param_key in search_params:
        if param_key.startswith('EcologyData.'):
            if 'EcologyData' not in table_joins:
                query = query.join(EcologyData)
                table_joins.add('EcologyData')
        elif param_key.startswith('MorphologyData.'):
            if 'MorphologyData' not in table_joins:
                query = query.join(MorphologyData)
                table_joins.add('MorphologyData')
        elif param_key.startswith('GenomicsData.'):
            if 'GenomicsData' not in table_joins:
                query = query.join(GenomicsData)
                table_joins.add('GenomicsData')
        elif param_key.startswith('PhysiologyData.'):
            if 'PhysiologyData' not in table_joins:
                query = query.join(PhysiologyData)
                table_joins.add('PhysiologyData')
    
    # Apply filters
    filters = []
    prev_key = None
    
    # Process each search parameter
    for param_key, param_value in search_params.items():
        # Skip empty parameters and processing keys
        if not param_value or param_key == 'sort_by' or param_key == 'sort_order':
            continue
        
        # Split model and field name
        if '.' in param_key:
            model_name, field_name = param_key.split('.')
            model_class = globals()[model_name]
            
            # Handle different parameter types
            if isinstance(param_value, dict):
                # Range parameter
                if 'min' in param_value:
                    filter_condition = getattr(model_class, field_name) >= param_value['min']
                    if prev_key and param_key in logic_ops:
                        if logic_ops[param_key] == 'OR':
                            filters[-1] = or_(filters[-1], filter_condition)
                        else:
                            filters[-1] = and_(filters[-1], filter_condition)
                    else:
                        filters.append(filter_condition)
                    prev_key = param_key
                
                if 'max' in param_value:
                    filter_condition = getattr(model_class, field_name) <= param_value['max']
                    if prev_key and param_key in logic_ops:
                        if logic_ops[param_key] == 'OR':
                            filters[-1] = or_(filters[-1], filter_condition)
                        else:
                            filters[-1] = and_(filters[-1], filter_condition)
                    else:
                        filters.append(filter_condition)
                    prev_key = param_key
            else:
                # Regular string or select parameter
                filter_condition = getattr(model_class, field_name).ilike(f'%{param_value}%')
                if prev_key and param_key in logic_ops:
                    if logic_ops[param_key] == 'OR':
                        filters[-1] = or_(filters[-1], filter_condition)
                    else:
                        filters[-1] = and_(filters[-1], filter_condition)
                else:
                    filters.append(filter_condition)
                prev_key = param_key
    
    # 处理冰箱位置搜索
    if freezer_location_params:
        # 为每个冰箱位置组件构建过滤条件
        freezer_components = []
        
        # 冰箱号
        if 'freezer' in freezer_location_params:
            pattern = f"{freezer_location_params['freezer']}-"
            freezer_components.append(BasicInfo.preservation_notes.like(f'{pattern}%'))
        
        # 层
        if 'layer' in freezer_location_params:
            if 'freezer' in freezer_location_params:
                pattern = f"{freezer_location_params['freezer']}-{freezer_location_params['layer']}-"
            else:
                pattern = f"%-{freezer_location_params['layer']}-"
            freezer_components.append(BasicInfo.preservation_notes.like(f'{pattern}%'))
        
        # 架
        if 'shelf' in freezer_location_params:
            if 'layer' in freezer_location_params:
                if 'freezer' in freezer_location_params:
                    pattern = f"{freezer_location_params['freezer']}-{freezer_location_params['layer']}-{freezer_location_params['shelf']}-"
                else:
                    pattern = f"%-{freezer_location_params['layer']}-{freezer_location_params['shelf']}-"
            else:
                pattern = f"%-%-{freezer_location_params['shelf']}-"
            freezer_components.append(BasicInfo.preservation_notes.like(f'{pattern}%'))
        
        # 盒
        if 'box' in freezer_location_params:
            box = freezer_location_params['box'].zfill(2)  # 确保两位数
            if 'shelf' in freezer_location_params:
                if 'layer' in freezer_location_params:
                    if 'freezer' in freezer_location_params:
                        pattern = f"{freezer_location_params['freezer']}-{freezer_location_params['layer']}-{freezer_location_params['shelf']}-{box}-"
                    else:
                        pattern = f"%-{freezer_location_params['layer']}-{freezer_location_params['shelf']}-{box}-"
                else:
                    pattern = f"%-%-{freezer_location_params['shelf']}-{box}-"
            else:
                pattern = f"%-%-%-{box}-"
            freezer_components.append(BasicInfo.preservation_notes.like(f'{pattern}%'))
        
        # 孔
        if 'hole' in freezer_location_params:
            hole = freezer_location_params['hole'].zfill(2)  # 确保两位数
            if 'box' in freezer_location_params:
                box = freezer_location_params['box'].zfill(2)
                if 'shelf' in freezer_location_params:
                    if 'layer' in freezer_location_params:
                        if 'freezer' in freezer_location_params:
                            pattern = f"{freezer_location_params['freezer']}-{freezer_location_params['layer']}-{freezer_location_params['shelf']}-{box}-{hole}"
                        else:
                            pattern = f"%-{freezer_location_params['layer']}-{freezer_location_params['shelf']}-{box}-{hole}"
                    else:
                        pattern = f"%-%-{freezer_location_params['shelf']}-{box}-{hole}"
                else:
                    pattern = f"%-%-%-{box}-{hole}"
            else:
                pattern = f"%-%-%-%-{hole}"
            freezer_components.append(BasicInfo.preservation_notes.like(f'{pattern}'))
        
        # 将冰箱位置组件与其他过滤条件组合
        if freezer_components:
            freezer_filter = and_(*freezer_components)
            if filters:
                # 如果前面有其他条件，应用逻辑运算符
                if logic_ops.get('BasicInfo.preservation_notes') == 'OR':
                    filters[-1] = or_(filters[-1], freezer_filter)
                else:
                    filters[-1] = and_(filters[-1], freezer_filter)
            else:
                filters.append(freezer_filter)
    
    # Apply all filters
    for f in filters:
        query = query.filter(f)
    
    # Apply sorting
    sort_by = request.args.get('sort_by', 'preservation_date')
    sort_order = request.args.get('sort_order', 'desc')
    
    # Get the correct model class for the sort field
    try:
        if '.' in sort_by:
            sort_model_name, sort_field_name = sort_by.split('.')
            sort_model = globals()[sort_model_name]
            sort_attr = getattr(sort_model, sort_field_name)
        else:
            # Default to BasicInfo model if no model specified
            sort_attr = getattr(BasicInfo, sort_by)
        
        # Apply sort direction
        if sort_order == 'desc':
            query = query.order_by(sort_attr.desc())
        else:
            query = query.order_by(sort_attr.asc())
    except AttributeError:
        # 如果出现属性错误，回退到默认排序
        logger.error(f"排序错误：无法按 {sort_by} 排序，使用默认排序")
        query = query.order_by(BasicInfo.preservation_date.desc())
    
    # Get total count for pagination
    total_results = query.count()
    total_pages = (total_results + per_page - 1) // per_page  # Ceiling division
    
    # Apply pagination
    results_paginated = query.offset((page - 1) * per_page).limit(per_page).all()
    
    # Get search description for display
    search_description = build_search_description(search_params, freezer_location_params)
    
    # 创建构建URL的辅助函数
    def build_page_url(page_num):
        query_params = request.args.copy()
        query_params['page'] = page_num
        # 使用MultiDict的to_dict(flat=False)保留所有值，然后手动格式化URL参数字符串
        params = []
        for key, values in query_params.lists():
            for value in values:
                params.append(f"{key}={value}")
        return f"{request.path}?{'&'.join(params)}"
    
    def build_sort_url(sort_field, sort_dir):
        query_params = request.args.copy()
        query_params['sort_by'] = sort_field
        query_params['sort_order'] = sort_dir
        # 使用MultiDict的lists()方法保留所有值，然后手动格式化URL参数字符串
        params = []
        for key, values in query_params.lists():
            for value in values:
                params.append(f"{key}={value}")
        return f"{request.path}?{'&'.join(params)}"
    
    return render_template(
        'results.html',
        results=results_paginated,
        total_results=total_results,
        page=page,
        total_pages=total_pages,
        sort_by=sort_by,
        sort_order=sort_order,
        search_params=search_params,
        search_description=search_description,
        is_advanced_search=True,
        build_page_url=build_page_url,
        build_sort_url=build_sort_url
    )

def build_search_description(search_params, freezer_location_params=None):
    """Build a human-readable description of the search parameters"""
    if not search_params and not freezer_location_params:
        return "所有微生物"
    
    parts = []
    for key, value in search_params.items():
        if not value:
            continue
            
        if '.' in key:
            model_name, field_name = key.split('.')
            
            # Field name mapping for better readability
            field_labels = {
                'genus': '属名',
                'species': '种名',
                'chinese_name': '中文名',
                'classification_status': '分类地位',
                'is_type_strain': '模式菌株',
                'preservation_date': '保藏日期',
                'preservation_notes': '冰箱位置',  # 修改显示名称
                'cell_shape': '细胞形态',
                'gram_stain': '革兰氏染色',
                'colony_color': '菌落颜色',
                'isolation_source': '分离来源',
                'geographic_location': '地理位置',
                'temperature_range': '温度范围',
                'ph_range': 'pH范围',
                'nicotine_degradation': '尼古丁降解',
                'cellulase': '纤维素酶',
                'acidic_protease': '酸性蛋白酶',
                'lignin_degrading_enzymes': '木质素降解酶'
            }
            
            label = field_labels.get(field_name, field_name)
            
            if isinstance(value, dict):
                # Handle range parameters
                range_str = ""
                if 'min' in value:
                    range_str += f"≥ {value['min']}"
                if 'min' in value and 'max' in value:
                    range_str += " 且 "
                if 'max' in value:
                    range_str += f"≤ {value['max']}"
                parts.append(f"{label}: {range_str}")
            else:
                parts.append(f"{label}: {value}")
    
    # 添加冰箱位置的描述
    if freezer_location_params:
        location_parts = []
        component_labels = {
            'freezer': '冰箱',
            'layer': '层',
            'shelf': '架',
            'box': '盒',
            'hole': '孔'
        }
        
        for component, value in freezer_location_params.items():
            location_parts.append(f"{component_labels.get(component, component)}: {value}")
        
        if location_parts:
            parts.append(f"冰箱位置: {', '.join(location_parts)}")
    
    return " 且 ".join(parts)

@app.route('/get_all_ids', methods=['GET'])
def get_all_ids():
    """获取符合当前搜索/筛选条件的所有IDs"""
    try:
        # 解析搜索参数，与advanced_results函数类似，但不进行分页
        search_params = {}
        logic_ops = {}
        freezer_location_params = {}
        query_term = request.args.get('q', '')
        
        # 处理普通搜索和高级搜索
        if request.args.get('is_advanced', '0') == '1':
            # 高级搜索参数提取
            for key, value in request.args.items():
                if key.startswith('logic_'):
                    field_name = key[6:]
                    logic_ops[field_name] = value
                elif key.startswith('BasicInfo.preservation_notes_'):
                    component = key.split('_')[-1]
                    if value:
                        freezer_location_params[component] = value
                elif '_min' in key or '_max' in key:
                    base_key = key.rsplit('_', 1)[0]
                    range_type = key.rsplit('_', 1)[1]
                    
                    if base_key not in search_params:
                        search_params[base_key] = {}
                    
                    if value:
                        search_params[base_key][range_type] = value
                elif '.' in key and value and key not in ['sort_by', 'sort_order']:
                    search_params[key] = value
            
            # 构建查询
            query = db.session.query(BasicInfo.basic_info_id).distinct()
            
            # 连接必要的表
            table_joins = set()
            for param_key in search_params:
                if param_key.startswith('EcologyData.'):
                    if 'EcologyData' not in table_joins:
                        query = query.join(EcologyData)
                        table_joins.add('EcologyData')
                elif param_key.startswith('MorphologyData.'):
                    if 'MorphologyData' not in table_joins:
                        query = query.join(MorphologyData)
                        table_joins.add('MorphologyData')
                elif param_key.startswith('GenomicsData.'):
                    if 'GenomicsData' not in table_joins:
                        query = query.join(GenomicsData)
                        table_joins.add('GenomicsData')
                elif param_key.startswith('PhysiologyData.'):
                    if 'PhysiologyData' not in table_joins:
                        query = query.join(PhysiologyData)
                        table_joins.add('PhysiologyData')
            
            # 应用过滤器
            filters = []
            prev_key = None
            
            for param_key, param_value in search_params.items():
                if not param_value or param_key == 'sort_by' or param_key == 'sort_order':
                    continue
                
                if '.' in param_key:
                    model_name, field_name = param_key.split('.')
                    model_class = globals()[model_name]
                    
                    if isinstance(param_value, dict):
                        if 'min' in param_value:
                            filter_condition = getattr(model_class, field_name) >= param_value['min']
                            if prev_key and param_key in logic_ops:
                                if logic_ops[param_key] == 'OR':
                                    filters[-1] = or_(filters[-1], filter_condition)
                                else:
                                    filters[-1] = and_(filters[-1], filter_condition)
                            else:
                                filters.append(filter_condition)
                            prev_key = param_key
                        
                        if 'max' in param_value:
                            filter_condition = getattr(model_class, field_name) <= param_value['max']
                            if prev_key and param_key in logic_ops:
                                if logic_ops[param_key] == 'OR':
                                    filters[-1] = or_(filters[-1], filter_condition)
                                else:
                                    filters[-1] = and_(filters[-1], filter_condition)
                            else:
                                filters.append(filter_condition)
                            prev_key = param_key
                    else:
                        filter_condition = getattr(model_class, field_name).ilike(f'%{param_value}%')
                        if prev_key and param_key in logic_ops:
                            if logic_ops[param_key] == 'OR':
                                filters[-1] = or_(filters[-1], filter_condition)
                            else:
                                filters[-1] = and_(filters[-1], filter_condition)
                        else:
                            filters.append(filter_condition)
                        prev_key = param_key
            
            # 处理冰箱位置搜索
            if freezer_location_params:
                freezer_components = []
                
                if 'freezer' in freezer_location_params:
                    pattern = f"{freezer_location_params['freezer']}-"
                    freezer_components.append(BasicInfo.preservation_notes.like(f'{pattern}%'))
                
                if 'layer' in freezer_location_params:
                    if 'freezer' in freezer_location_params:
                        pattern = f"{freezer_location_params['freezer']}-{freezer_location_params['layer']}-"
                    else:
                        pattern = f"%-{freezer_location_params['layer']}-"
                    freezer_components.append(BasicInfo.preservation_notes.like(f'{pattern}%'))
                
                if 'shelf' in freezer_location_params:
                    if 'layer' in freezer_location_params:
                        if 'freezer' in freezer_location_params:
                            pattern = f"{freezer_location_params['freezer']}-{freezer_location_params['layer']}-{freezer_location_params['shelf']}-"
                        else:
                            pattern = f"%-{freezer_location_params['layer']}-{freezer_location_params['shelf']}-"
                    else:
                        pattern = f"%-%-{freezer_location_params['shelf']}-"
                    freezer_components.append(BasicInfo.preservation_notes.like(f'{pattern}%'))
                
                if 'box' in freezer_location_params:
                    box = freezer_location_params['box'].zfill(2)
                    if 'shelf' in freezer_location_params:
                        if 'layer' in freezer_location_params:
                            if 'freezer' in freezer_location_params:
                                pattern = f"{freezer_location_params['freezer']}-{freezer_location_params['layer']}-{freezer_location_params['shelf']}-{box}-"
                            else:
                                pattern = f"%-{freezer_location_params['layer']}-{freezer_location_params['shelf']}-{box}-"
                        else:
                            pattern = f"%-%-{freezer_location_params['shelf']}-{box}-"
                    else:
                        pattern = f"%-%-%-{box}-"
                    freezer_components.append(BasicInfo.preservation_notes.like(f'{pattern}%'))
                
                if 'hole' in freezer_location_params:
                    hole = freezer_location_params['hole'].zfill(2)
                    if 'box' in freezer_location_params:
                        box = freezer_location_params['box'].zfill(2)
                        if 'shelf' in freezer_location_params:
                            if 'layer' in freezer_location_params:
                                if 'freezer' in freezer_location_params:
                                    pattern = f"{freezer_location_params['freezer']}-{freezer_location_params['layer']}-{freezer_location_params['shelf']}-{box}-{hole}"
                                else:
                                    pattern = f"%-{freezer_location_params['layer']}-{freezer_location_params['shelf']}-{box}-{hole}"
                            else:
                                pattern = f"%-%-{freezer_location_params['shelf']}-{box}-{hole}"
                        else:
                            pattern = f"%-%-%-{box}-{hole}"
                    else:
                        pattern = f"%-%-%-%-{hole}"
                    freezer_components.append(BasicInfo.preservation_notes.like(f'{pattern}'))
                
                if freezer_components:
                    freezer_filter = and_(*freezer_components)
                    if filters:
                        if logic_ops.get('BasicInfo.preservation_notes') == 'OR':
                            filters[-1] = or_(filters[-1], freezer_filter)
                        else:
                            filters[-1] = and_(filters[-1], freezer_filter)
                    else:
                        filters.append(freezer_filter)
        else:
            # 普通搜索
            query = db.session.query(BasicInfo.basic_info_id).distinct()
            if query_term:
                filters = [or_(
                    BasicInfo.chinese_name.ilike(f'%{query_term}%'),
                    BasicInfo.classification_status.ilike(f'%{query_term}%'),
                    BasicInfo.basic_info_id.ilike(f'%{query_term}%'),
                    BasicInfo.genus.ilike(f'%{query_term}%'),
                    BasicInfo.species.ilike(f'%{query_term}%'),
                    func.concat(BasicInfo.genus, ' ', BasicInfo.species).ilike(f'%{query_term}%')
                )]
            else:
                filters = []
        
        # 应用过滤器
        for f in filters:
            query = query.filter(f)
        
        # 获取所有ID
        all_ids = [row[0] for row in query.all()]
        
        return jsonify({"ids": all_ids, "count": len(all_ids)})
    
    except Exception as e:
        logger.error(f"获取所有ID时出错: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/download_selected', methods=['POST'])
def download_selected():
    """Download selected items as CSV"""
    try:
        # 获取POST请求中的ID数组
        id_list = request.json.get('ids', [])
        
        if not id_list:
            return jsonify({"error": "No items selected"}), 400
        
        # 查询所选ID的所有数据
        results = []
        for basic_info_id in id_list:
            basic_info = BasicInfo.query.get(basic_info_id)
            if basic_info:
                # 获取关联数据
                ecology_data = EcologyData.query.get(basic_info_id)
                morphology_data = MorphologyData.query.get(basic_info_id)
                genomics_data = GenomicsData.query.get(basic_info_id)
                physiology_data = PhysiologyData.query.get(basic_info_id)
                
                # 合并所有数据为一个字典
                item_data = {
                    'basic_info_id': basic_info.basic_info_id,
                    'genus': basic_info.genus,
                    'species': basic_info.species,
                    'classification_status': basic_info.classification_status,
                    'preservation_date': basic_info.preservation_date,
                    'chinese_name': basic_info.chinese_name,
                    'is_type_strain': basic_info.is_type_strain,
                    'preservation_unit': basic_info.preservation_unit,
                    'preservation_method': basic_info.preservation_method,
                    'preserver': basic_info.preserver,
                    'preservation_notes': basic_info.preservation_notes,
                    'contact_info': basic_info.contact_info
                }
                
                # 添加生态学数据
                if ecology_data:
                    item_data.update({
                        'location_name': ecology_data.location_name,
                        'habitat': ecology_data.habitat,
                        'coordinates': ecology_data.coordinates,
                        'sampling_date': ecology_data.sampling_date,
                        'sample_type': ecology_data.sample_type,
                        'temperature': ecology_data.temperature,
                        'oxygen_requirement': ecology_data.oxygen_requirement,
                        'sampler': ecology_data.sampler
                    })
                
                # 添加形态学数据
                if morphology_data:
                    item_data.update({
                        'description': morphology_data.description,
                        'colony_color': morphology_data.colony_color,
                        'colony_shape': morphology_data.colony_shape,
                        'colony_edge': morphology_data.colony_edge,
                        'colony_surface': morphology_data.colony_surface,
                        'colony_size': morphology_data.colony_size,
                        'colony_texture': morphology_data.colony_texture,
                        'motility': morphology_data.motility,
                        'spore_shape': morphology_data.spore_shape,
                        'spore_staining_reaction': morphology_data.spore_staining_reaction,
                        'observation_medium': morphology_data.observation_medium,
                        'observation_conditions': morphology_data.observation_conditions
                    })
                
                # 添加基因组学数据
                if genomics_data:
                    item_data.update({
                        'sequencing_method': genomics_data.sequencing_method,
                        'assembly_method': genomics_data.assembly_method,
                        'annotation_method': genomics_data.annotation_method,
                        'genome_size': genomics_data.genome_size,
                        'gc_content': genomics_data.gc_content,
                        'n50': genomics_data.n50,
                        'contig_count': genomics_data.contig_count,
                        'scaffold_count': genomics_data.scaffold_count,
                        'trna_count': genomics_data.trna_count,
                        'rrna_count': genomics_data.rrna_count
                    })
                
                # 添加生理学数据
                if physiology_data:
                    item_data.update({
                        'nicotine_degradation': physiology_data.nicotine_degradation,
                        'cellulase': physiology_data.cellulase,
                        'acidic_protease': physiology_data.acidic_protease,
                        'lignin_degrading_enzymes': physiology_data.lignin_degrading_enzymes
                    })
                
                results.append(item_data)
        
        # 生成CSV
        output = StringIO()
        writer = csv.writer(output)
        
        # 写入表头
        header = [
            'basic_info_id', 'genus', 'species', 'classification_status', 'preservation_date',
            'chinese_name', 'is_type_strain', 'preservation_unit', 'preservation_method',
            'preserver', 'preservation_notes', 'contact_info', 'location_name',
            'habitat', 'coordinates', 'sampling_date',
            'sample_type', 'temperature', 'oxygen_requirement', 'sampler',
            'description', 'colony_color', 'colony_shape', 'colony_edge',
            'colony_surface', 'colony_size', 'colony_texture', 'motility', 'spore_shape',
            'spore_staining_reaction', 'observation_medium', 'observation_conditions',
            'sequencing_method', 'assembly_method', 'annotation_method', 'genome_size', 'gc_content', 'n50',
            'contig_count', 'scaffold_count', 'trna_count', 'rrna_count', 'nicotine_degradation',
            'cellulase', 'acidic_protease', 'lignin_degrading_enzymes'
        ]
        writer.writerow(header)
        
        # 写入数据行
        for item in results:
            row = []
            for field in header:
                value = item.get(field, '')
                # 处理日期格式
                if isinstance(value, (date, datetime)):
                    value = value.strftime('%Y-%m-%d')
                # 处理Decimal格式
                elif isinstance(value, Decimal):
                    value = str(value)
                row.append(value)
            writer.writerow(row)
        
        output.seek(0)
        return Response(
            output, 
            mimetype='text/csv', 
            headers={"Content-Disposition": f"attachment;filename=selected_strains_{len(id_list)}.csv"}
        )
    
    except Exception as e:
        logger.error(f"Error downloading selected items: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
