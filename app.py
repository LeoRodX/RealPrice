import sqlite3
import os
from datetime import datetime, timedelta
from flask import Flask, render_template_string, request, redirect, url_for, jsonify, send_file

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

DB_PATH = 'prices.db'

# --- Таблица конверсий единиц измерения ---
CONVERSIONS = {
    ('г', 'кг'): 1000,
    ('кг', 'г'): 0.001,
    ('г', '100г'): 100,
    ('100г', 'г'): 0.01,
    ('мл', 'л'): 1000,
    ('л', 'мл'): 0.001,
}

# --- Инициализация базы данных ---
def init_db():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('PRAGMA foreign_keys = ON')
    
    c.execute('''
        CREATE TABLE units (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            name_short TEXT NOT NULL UNIQUE
        )
    ''')
    
    c.execute('''
        CREATE TABLE stores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            color TEXT DEFAULT '#FF6B35'
        )
    ''')
    
    c.execute('''
        CREATE TABLE products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            input_unit_id INTEGER NOT NULL,
            compare_unit_id INTEGER NOT NULL,
            FOREIGN KEY (input_unit_id) REFERENCES units(id) ON DELETE RESTRICT,
            FOREIGN KEY (compare_unit_id) REFERENCES units(id) ON DELETE RESTRICT
        )
    ''')
    
    c.execute('''
        CREATE TABLE price_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            brand TEXT,
            measure_value REAL NOT NULL,
            price REAL NOT NULL,
            price_per_compare REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (store_id) REFERENCES stores(id) ON DELETE CASCADE,
            FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
        )
    ''')
    
    c.execute('CREATE INDEX idx_price_entries_product ON price_entries(product_id)')
    c.execute('CREATE INDEX idx_price_entries_store ON price_entries(store_id)')
    
    default_units = [
        ('грамм', 'г'),
        ('килограмм', 'кг'),
        ('100 грамм', '100г'),
        ('миллилитр', 'мл'),
        ('литр', 'л'),
        ('штука', 'шт')
    ]
    for unit in default_units:
        c.execute('INSERT INTO units (name, name_short) VALUES (?, ?)', unit)
    
    default_stores = [
        ('Дикси/Областная', '#FF6B35'),
        ('Дикси/Каштановая', '#FF6B35'),
        ('Пятерочка/Ленинградская', '#4CAF50'),
        ('Пятерочка/Строителей', '#4CAF50'),
        ('Семишагофф/Дыбенко', '#2196F3'),
        ('Семишагофф/Подвойского', '#2196F3'),
        ('Лента/Строителей', '#9C27B0'),
        ('Магнит/Ленинградская', '#E91E63'),
        ('Магнит/Строителей', '#E91E63')
    ]
    for store in default_stores:
        c.execute('INSERT INTO stores (name, color) VALUES (?, ?)', store)
    
    units_map = {}
    c.execute('SELECT id, name_short FROM units')
    for row in c.fetchall():
        units_map[row[1]] = row[0]
    
    default_products = [
        ('апельсины', units_map['кг'], units_map['кг']),
        ('бананы', units_map['кг'], units_map['кг']),
        ('батон для фарша', units_map['г'], units_map['кг']),
        ('геркулес', units_map['г'], units_map['кг']),
        ('гречка', units_map['г'], units_map['кг']),
        ('дрожжи сухие', units_map['г'], units_map['г']),
        ('зефир', units_map['кг'], units_map['кг']),
        ('зубная паста', units_map['г'], units_map['100г']),
        ('изюм', units_map['г'], units_map['кг']),
        ('йогурт в баночках', units_map['г'], units_map['г']),
        ('йогурт питьевой', units_map['г'], units_map['кг']),
        ('какао', units_map['г'], units_map['100г']),
        ('капуста', units_map['кг'], units_map['кг']),
        ('картофель', units_map['кг'], units_map['кг']),
        ('кетчуп', units_map['г'], units_map['100г']),
        ('кефир', units_map['г'], units_map['кг']),
        ('колбаса варенная', units_map['г'], units_map['кг']),
        ('колбаса копченная', units_map['г'], units_map['кг']),
        ('конфеты', units_map['кг'], units_map['кг']),
        ('кофе растворимый', units_map['г'], units_map['100г']),
        ('крабовое мясо/палочки', units_map['г'], units_map['кг']),
        ('кукуруза сладкая', units_map['г'], units_map['100г']),
        ('кукурузная крупа', units_map['г'], units_map['кг']),
        ('курага', units_map['г'], units_map['кг']),
        ('лук', units_map['кг'], units_map['кг']),
        ('майонез', units_map['мл'], units_map['л']),
        ('макаронные изделия', units_map['г'], units_map['кг']),
        ('масло подсолнечное', units_map['мл'], units_map['л']),
        ('масло сливочное 72%', units_map['г'], units_map['100г']),
        ('масло сливочное 82%', units_map['г'], units_map['100г']),
        ('минтай', units_map['г'], units_map['кг']),
        ('молоко(г) >2,8%', units_map['г'], units_map['кг']),
        ('молоко(г) 1,5%', units_map['г'], units_map['кг']),
        ('молоко(г) 2,5%', units_map['г'], units_map['кг']),
        ('молоко(мл) 1,5%', units_map['мл'], units_map['л']),
        ('морковь', units_map['кг'], units_map['кг']),
        ('мука высший сорт', units_map['кг'], units_map['кг']),
        ('мука хлебопекарская', units_map['кг'], units_map['кг']),
        ('огурцы', units_map['кг'], units_map['кг']),
        ('пена для бритья', units_map['мл'], units_map['л']),
        ('печенье', units_map['кг'], units_map['кг']),
        ('помидоры', units_map['кг'], units_map['кг']),
        ('пшеничная крупа', units_map['г'], units_map['кг']),
        ('пшено', units_map['г'], units_map['кг']),
        ('рис', units_map['г'], units_map['кг']),
        ('сахар', units_map['кг'], units_map['кг']),
        ('свекла', units_map['кг'], units_map['кг']),
        ('свинина', units_map['кг'], units_map['кг']),
        ('семга', units_map['г'], units_map['кг']),
        ('сметана', units_map['г'], units_map['100г']),
        ('соль крупная', units_map['кг'], units_map['кг']),
        ('соль мелкая', units_map['кг'], units_map['кг']),
        ('сосиски', units_map['г'], units_map['кг']),
        ('станки', units_map['шт'], units_map['шт']),
        ('сыр', units_map['г'], units_map['100г']),
        ('творог', units_map['г'], units_map['100г']),
        ('цикорий растворимый', units_map['г'], units_map['100г']),
        ('цыпленок', units_map['кг'], units_map['кг']),
        ('чай', units_map['г'], units_map['100г']),
        ('шампунь', units_map['мл'], units_map['л']),
        ('шоколад растворимый', units_map['г'], units_map['100г']),
        ('яблоки', units_map['кг'], units_map['кг']),
        ('яйца 0,7/С1=0,6кг/0,5/0,4', units_map['кг'], units_map['кг']),
    ]

    for product in default_products:
        c.execute('INSERT INTO products (name, input_unit_id, compare_unit_id) VALUES (?, ?, ?)', product)
    
    conn.commit()
    conn.close()
    print("База данных успешно создана!")

def calculate_price_per_compare(measure_value, price, compare_unit_id, input_unit_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('SELECT name_short FROM units WHERE id = ?', (input_unit_id,))
    input_unit = c.fetchone()
    if not input_unit:
        conn.close()
        return price / measure_value
    
    c.execute('SELECT name_short FROM units WHERE id = ?', (compare_unit_id,))
    compare_unit = c.fetchone()
    conn.close()
    
    if not compare_unit:
        return price / measure_value
    
    input_unit = input_unit[0]
    compare_unit = compare_unit[0]
    
    if input_unit == compare_unit:
        return price / measure_value
    
    conversion_key = (input_unit, compare_unit)
    if conversion_key in CONVERSIONS:
        compare_value = measure_value / CONVERSIONS[conversion_key]
        return price / compare_value if compare_value > 0 else 0
    
    reverse_key = (compare_unit, input_unit)
    if reverse_key in CONVERSIONS:
        compare_value = measure_value * CONVERSIONS[reverse_key]
        return price / compare_value if compare_value > 0 else 0
    
    return price / measure_value

def is_unit_used(unit_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM products WHERE input_unit_id = ? OR compare_unit_id = ?', (unit_id, unit_id))
    count = c.fetchone()[0]
    conn.close()
    return count > 0

def fmt_measure(value, unit):
    """Форматирует вес/объём: целые для г/мл/шт, два знака для кг/л"""
    if unit in ('г', 'мл', 'шт'):
        return f"{value:.0f}"
    else:
        return f"{value:.2f}"

# --- HTML шаблон ---
INDEX_TEMPLATE = '''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>RealPrice — реальная цена</title>
    <link rel="icon" type="image/png" href="favicon.png">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { background: #f5f5f5; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; padding: 0; }
        
        .site-header {
            background: white;
            padding: 10px 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
            display: flex;
            justify-content: center;
            align-items: center;
            position: sticky;
            top: 0;
            z-index: 100;
        }
        .site-header a {
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 8px;
        }
        .site-header img { height: 32px; width: 32px; }
        .site-header .logo-text { font-size: 26px; font-weight: 900; color: #FF6B35; }
        
        .site-footer { text-align: center; padding: 20px; margin-top: 40px; }
        .container { max-width: 1000px; margin: 0 auto; padding: 16px; }
        
        .add-form-card {
            background: white;
            border-radius: 12px;
            padding: 12px 16px;
            margin-bottom: 24px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }
        .form-grid {
            display: flex;
            gap: 8px;
            align-items: center;
            flex-wrap: wrap;
        }
        .form-field { flex: 1; min-width: 100px; }
        .form-field select, .form-field input {
            width: 100%;
            padding: 10px 0;
            border: none;
            border-bottom: 2px solid #e0e0e0;
            font-size: 14px;
            background: transparent;
            outline: none;
            color: #333;
        }
        .form-field select:focus, .form-field input:focus { border-bottom-color: #FF6B35; }
        .form-field select option[value=""] { color: #999; }
        
        .store-option {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .color-dot {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            flex-shrink: 0;
            display: inline-block;
        }
        
        .form-submit { flex-shrink: 0; }
        
        button, .btn-link {
            background: white;
            color: #666;
            border: 2px solid #e0e0e0;
            padding: 10px 20px;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            white-space: nowrap;
            text-decoration: none;
            transition: all 0.2s;
            display: inline-block;
        }
        button:hover, .btn-link:hover { border-color: #FF6B35; color: #FF6B35; }
        .btn-primary { background: #FF6B35; color: white; border-color: #FF6B35; }
        .btn-primary:hover { opacity: 0.9; color: white; }
        .tab-button.active { background: #FF6B35; color: white; border-color: #FF6B35; }
        
        .btn-delete {
            background: none;
            border: none;
            font-size: 18px;
            cursor: pointer;
            color: #ccc;
            padding: 0 4px;
            transition: color 0.2s;
            line-height: 1;
        }
        .btn-delete:hover { color: #e53935; }
        
        .table-container {
            background: white;
            border-radius: 12px;
            overflow-x: auto;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
            margin-bottom: 24px;
        }
        table { width: 100%; border-collapse: collapse; }
        td { padding: 12px; border-bottom: 1px solid #f0f0f0; font-size: 14px; color: #333; }
        .price-line { font-weight: 700; font-size: 16px; color: #333; }
        .best-price { color: #4CAF50; }
        .empty-state { text-align: center; padding: 60px 20px; color: #999; }
        
        .tabs-container { display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap; }
        
        .reference-section {
            background: white;
            border-radius: 12px;
            margin-bottom: 16px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
            overflow: hidden;
            display: none;
        }
        .reference-section.active { display: block; }
        .reference-content { padding: 20px; }
        
        .unit-item, .store-item, .product-item {
            background: #f9f9f9;
            padding: 12px;
            margin-bottom: 8px;
            border-radius: 8px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .store-item {
            border-left: 4px solid;
        }
        .unit-info, .store-info, .product-info { flex: 1; }
        .unit-name, .store-name, .product-name { font-weight: 500; font-size: 14px; }
        .unit-detail, .product-detail { font-size: 12px; color: #666; }
        .edit-btn, .delete-btn { background: none; border: none; font-size: 20px; cursor: pointer; padding: 0 8px; }
        .edit-btn { color: #FF6B35; }
        .delete-btn { color: #999; }
        
        .add-form { margin-top: 16px; display: flex; flex-wrap: wrap; gap: 8px; }
        .add-form input, .add-form select {
            flex: 1;
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 6px;
            font-size: 14px;
        }
        .modal {
            display: none;
            position: fixed;
            top: 0; left: 0;
            width: 100%; height: 100%;
            background: rgba(0,0,0,0.5);
            z-index: 1000;
            justify-content: center;
            align-items: center;
        }
        .modal-content {
            background: white;
            padding: 24px;
            border-radius: 12px;
            max-width: 400px;
            width: 90%;
        }
        .modal-content h4 { margin-bottom: 20px; }
        .modal-content input, .modal-content select {
            width: 100%;
            padding: 10px;
            margin-bottom: 12px;
            border: 1px solid #ddd;
            border-radius: 6px;
        }
        .modal-buttons { display: flex; gap: 12px; margin-top: 20px; }
        .modal-buttons button { flex: 1; }
        
        .error-message {
            background: #ffebee;
            color: #c62828;
            padding: 10px 16px;
            border-radius: 8px;
            font-size: 13px;
            margin-bottom: 16px;
            display: none;
        }
        .product-table-header {
            display: grid;
            grid-template-columns: 2fr 1fr 1fr 80px;
            gap: 8px;
            padding: 8px 12px;
            font-size: 11px;
            text-transform: uppercase;
            color: #999;
            font-weight: 600;
            margin-bottom: 8px;
        }
        .product-item {
            display: grid;
            grid-template-columns: 2fr 1fr 1fr 80px;
            gap: 8px;
            align-items: center;
        }
        .product-item .product-info {
            grid-column: 1 / -1;
            display: grid;
            grid-template-columns: 2fr 1fr 1fr;
            gap: 8px;
            align-items: center;
        }
        .product-item .product-info .product-name { font-weight: 500; font-size: 14px; }
        .product-item .product-info .product-detail { font-size: 12px; color: #666; text-align: center; }
        .product-actions { display: flex; justify-content: flex-end; }
        .comparison-header { font-size: 13px; color: #999; margin-bottom: 8px; padding: 0 12px; }
        
        .entry-row { display: flex; justify-content: space-between; align-items: center; }
        .entry-text { flex: 1; }
        
        @media (max-width: 768px) {
            .form-grid { flex-direction: column; gap: 6px; }
            .form-field { min-width: 100%; }
            .form-submit button { width: 100%; }
            td { font-size: 11px; padding: 8px; }
            .product-table-header, .product-item { grid-template-columns: 1fr 1fr 1fr 60px; }
            .product-item .product-info { grid-template-columns: 1fr 1fr 1fr; }
        }
    </style>
</head>
<body>
    <header class="site-header">
        <a href="/price/">
            <img src="favicon.png" alt="RealPrice" width="32" height="32">
            <span class="logo-text">RealPrice</span>
        </a>
    </header>
    
    <div class="container">
        <div id="errorMessage" class="error-message"></div>
        
        <div class="add-form-card">
            <form method="POST" action="" id="addForm" onsubmit="return validateForm()">
                <div class="form-grid">
                    <div class="form-field">
                        <select name="store_id" id="storeSelect" required>
                            <option value="">🏪 магазин</option>
                            {% for store in stores %}
                            <option value="{{ store[0] }}" data-color="{{ store[2] }}">🏪 {{ store[1] }}</option>
                            {% endfor %}
                        </select>
                    </div>
                    <div class="form-field">
                        <select name="product_id" id="productSelect" required onchange="if(this.value) window.location.href = window.location.pathname + '?p=0000&product_id=' + this.value;">
                            <option value="">🛒 Товар</option>
                            {% for product in all_products %}
                            <option value="{{ product[0] }}" data-input-unit="{{ product[2] }}" {% if selected_product_id == product[0] %}selected{% endif %}>
                                🛒 {{ product[1] }}
                            </option>
                            {% endfor %}
                        </select>
                    </div>
                    <div class="form-field">
                        <input type="text" name="brand" id="brandInput" placeholder="🏷️ Торговая марка/Название">
                    </div>
                    <div class="form-field">
                        <input type="number" step="any" name="measure_value" id="measureValue" placeholder="⚖️ Количество">
                    </div>
                    <div class="form-field">
                        <input type="number" step="any" name="price" id="priceInput" placeholder="💰 Цена за упаковку, р.">
                    </div>
                    <div class="form-submit">
                        <button type="submit" class="btn-primary">➕</button>
                    </div>
                </div>
            </form>
        </div>
        
        <div class="table-container">
            {% if selected_product_id %}
            <div class="comparison-header" style="padding:12px;">
                Товар: <strong>{{ all_products|selectattr("0", "equalto", selected_product_id)|map(attribute="1")|first }}</strong>
                (топ-5 самых дешёвых)
            </div>
            {% endif %}
            <table>
                <tbody>
                    {% if price_entries %}
                        {% for entry in price_entries %}
                        <tr>
                            <td class="price-line {% if loop.first %}best-price{% endif %}">
                                <div class="entry-row">
                                    <span class="entry-text">
                                        {{ "%.0f"|format(entry[6]) }} ₽ за {{ entry[8] }} • 
                                        упаковка {{ fmt_measure(entry[3], entry[2]) }} {{ entry[2] }} ({{ "%.0f"|format(entry[7]) }} ₽) • 
                                        {{ entry[1] }}{% if entry[5] %} {{ entry[5] }}{% endif %} • 
                                        <span style="display:inline-flex;align-items:center;gap:4px;">
                                            <span class="color-dot" style="background:{{ entry[10] }};"></span>
                                            {{ entry[0] }}
                                        </span>
                                    </span>
                                    <button class="btn-delete" onclick="deleteEntry({{ entry[9] }})" title="Удалить запись">✕</button>
                                </div>
                            </td>
                        </tr>
                        {% endfor %}
                    {% else %}
                        <tr>
                            <td class="empty-state">
                                {% if selected_product_id %}
                                    Нет данных для сравнения<br><small>Добавьте первую запись для этого товара</small>
                                {% else %}
                                    Выберите товар для сравнения цен
                                {% endif %}
                            </td>
                        </tr>
                    {% endif %}
                </tbody>
            </table>
        </div>
        
        <div class="tabs-container">
            <button class="tab-button" onclick="switchTab('products')">🛒 Товары</button>
            <button class="tab-button" onclick="switchTab('stores')">🏪 Магазины</button>
            <button class="tab-button" onclick="switchTab('units')">📏 Единицы измерений</button>
            <a href="/price/report?p=0000" class="btn-link">📈 Отчёт за год</a>
        </div>
        
        <div id="productsSection" class="reference-section">
            <div class="reference-content">
                <div class="product-table-header">
                    <div>ТОВАР</div>
                    <div>МЕРА НА УПАКОВКЕ</div>
                    <div>МЕРА СРАВНЕНИЯ</div>
                    <div></div>
                </div>
                <div id="productsList">
                    {% for product in all_products %}
                    <div class="product-item">
                        <div class="product-info">
                            <div class="product-name">{{ product[1] }}</div>
                            <div class="product-detail">{{ product[2] }}</div>
                            <div class="product-detail">{{ product[3] }}</div>
                        </div>
                        <div class="product-actions">
                            <button class="edit-btn" onclick="editProduct({{ product[0] }})">✏️</button>
                            <button class="delete-btn" onclick="deleteProduct({{ product[0] }})">🗑️</button>
                        </div>
                    </div>
                    {% endfor %}
                </div>
                <div class="add-form" style="flex-direction: column;">
                    <div style="display: flex; gap: 8px; flex-wrap: wrap;">
                        <input type="text" id="newProductName" placeholder="Название товара" style="flex: 2;">
                        <select id="newInputUnit" style="flex: 1;">
                            <option value="">Мера на упаковке</option>
                            {% for unit in units %}
                            <option value="{{ unit[0] }}">{{ unit[1] }} ({{ unit[2] }})</option>
                            {% endfor %}
                        </select>
                        <select id="newCompareUnit" style="flex: 1;">
                            <option value="">Мера сравнения</option>
                            {% for unit in units %}
                            <option value="{{ unit[0] }}">{{ unit[1] }} ({{ unit[2] }})</option>
                            {% endfor %}
                        </select>
                        <button onclick="addProduct()">➕ Добавить товар</button>
                    </div>
                </div>
            </div>
        </div>
        
        <div id="storesSection" class="reference-section">
            <div class="reference-content">
                <div id="storesList">
                    {% for store in stores %}
                    <div class="store-item" style="border-left-color: {{ store[2] }};">
                        <div class="store-info">
                            <div class="store-name" style="display:flex;align-items:center;gap:8px;">
                                <span class="color-dot" style="background:{{ store[2] }};"></span>
                                {{ store[1] }}
                            </div>
                        </div>
                        <div>
                            <button class="edit-btn" onclick="editStore({{ store[0] }})">✏️</button>
                            <button class="delete-btn" onclick="deleteStore({{ store[0] }})">🗑️</button>
                        </div>
                    </div>
                    {% endfor %}
                </div>
                <div class="add-form">
                    <input type="text" id="newStoreName" placeholder="Название магазина">
                    <input type="color" id="newStoreColor" value="#FF6B35" style="width:50px;height:40px;padding:2px;">
                    <button onclick="addStore()">➕ Добавить магазин</button>
                </div>
            </div>
        </div>
        
        <div id="unitsSection" class="reference-section">
            <div class="reference-content">
                <div id="unitsList">
                    {% for unit in units %}
                    <div class="unit-item">
                        <div class="unit-info">
                            <div class="unit-name">{{ unit[1] }}</div>
                            <div class="unit-detail">Сокращение: {{ unit[2] }}</div>
                        </div>
                        <div>
                            <button class="edit-btn" onclick="editUnit({{ unit[0] }})">✏️</button>
                            <button class="delete-btn" onclick="deleteUnit({{ unit[0] }})">🗑️</button>
                        </div>
                    </div>
                    {% endfor %}
                </div>
                <div class="add-form">
                    <input type="text" id="newUnitName" placeholder="Название (грамм)">
                    <input type="text" id="newUnitShort" placeholder="Сокращение (г)">
                    <button onclick="addUnit()">➕ Добавить единицу</button>
                </div>
            </div>
        </div>
    </div>
    
    <footer class="site-footer">
        <span style="color: #6c757d; font-size: 14px;">&copy; Terre & Co, {{ current_year }}</span>
    </footer>
    
    <div id="editModal" class="modal">
        <div class="modal-content">
            <h4 id="modalTitle">Редактировать</h4>
            <input type="hidden" id="editType">
            <input type="hidden" id="editId">
            <input type="text" id="editName" placeholder="Название">
            <input type="text" id="editShort" placeholder="Сокращение" style="display:none">
            <input type="color" id="editColor" value="#FF6B35" style="display:none;width:100%;height:40px;padding:4px;">
            <div id="editProductFields" style="display:none;">
                <label style="font-size:12px;color:#666;">Мера на упаковке</label>
                <select id="editInputUnit">
                    {% for unit in units %}
                    <option value="{{ unit[0] }}">{{ unit[1] }} ({{ unit[2] }})</option>
                    {% endfor %}
                </select>
                <label style="font-size:12px;color:#666;">Мера сравнения</label>
                <select id="editCompareUnit">
                    {% for unit in units %}
                    <option value="{{ unit[0] }}">{{ unit[1] }} ({{ unit[2] }})</option>
                    {% endfor %}
                </select>
            </div>
            <div class="modal-buttons">
                <button onclick="saveItem()">Сохранить</button>
                <button onclick="closeModal()" style="background:#999">Отмена</button>
            </div>
        </div>
    </div>
    
    <script>
        (function() {
            const select = document.getElementById('productSelect');
            if (select.value) {
                const option = select.options[select.selectedIndex];
                const unit = option.getAttribute('data-input-unit');
                if (unit) document.getElementById('measureValue').placeholder = '⚖️ Количество, ' + unit;
            }
        })();
        
        document.getElementById('productSelect').addEventListener('change', function() {
            const option = this.options[this.selectedIndex];
            const unit = option.getAttribute('data-input-unit');
            const measureInput = document.getElementById('measureValue');
            measureInput.placeholder = unit ? '⚖️ Количество, ' + unit : '⚖️ Количество';
        });
        
        function switchTab(tab) {
            const section = document.getElementById(tab + 'Section');
            const button = event.target;
            if (section.classList.contains('active')) {
                section.classList.remove('active');
                button.classList.remove('active');
            } else {
                document.getElementById('storesSection').classList.remove('active');
                document.getElementById('unitsSection').classList.remove('active');
                document.getElementById('productsSection').classList.remove('active');
                document.querySelectorAll('.tab-button').forEach(btn => btn.classList.remove('active'));
                section.classList.add('active');
                button.classList.add('active');
            }
        }
        
        function validateForm() {
            if (!document.getElementById('storeSelect').value) { showError('Выберите магазин'); return false; }
            if (!document.getElementById('productSelect').value) { showError('Выберите товар'); return false; }
            const m = document.getElementById('measureValue').value;
            if (!m || parseFloat(m) <= 0) { showError('Введите количество'); return false; }
            const p = document.getElementById('priceInput').value;
            if (!p || parseFloat(p) <= 0) { showError('Введите цену'); return false; }
            return true;
        }
        
        function showError(msg) {
            const err = document.getElementById('errorMessage');
            err.textContent = msg;
            err.style.display = 'block';
            setTimeout(() => err.style.display = 'none', 3000);
        }
        
        function deleteEntry(id) {
            if(confirm('Удалить эту запись?')) {
                fetch('delete_entry', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:id})})
                .then(r=>r.json()).then(d=>{if(d.success)location.reload();else showError('Ошибка удаления')});
            }
        }
        
        const storeSelect = document.getElementById('storeSelect');
        const savedStore = localStorage.getItem('selectedStore');
        if (savedStore) storeSelect.value = savedStore;
        storeSelect.onchange = () => localStorage.setItem('selectedStore', storeSelect.value);
        
        function editStore(id) {
            document.getElementById('editType').value = 'store';
            document.getElementById('editId').value = id;
            document.getElementById('modalTitle').textContent = 'Редактировать магазин';
            document.getElementById('editName').style.display = 'block';
            document.getElementById('editShort').style.display = 'none';
            document.getElementById('editColor').style.display = 'block';
            document.getElementById('editProductFields').style.display = 'none';
            fetch('get_store/' + id).then(r=>r.json()).then(d=>{
                document.getElementById('editName').value = d.name;
                document.getElementById('editColor').value = d.color;
            });
            document.getElementById('editModal').style.display = 'flex';
        }
        
        function deleteStore(id) {
            if(confirm('Удалить магазин? Все цены для него будут удалены.')) {
                fetch('delete_store', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:id})})
                .then(r=>r.json()).then(d=>{if(d.success)location.reload();else showError(d.error)});
            }
        }
        
        function addStore() {
            const name = document.getElementById('newStoreName').value.trim();
            const color = document.getElementById('newStoreColor').value;
            if(!name){showError('Введите название магазина');return;}
            fetch('add_store', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:name, color:color})})
            .then(r=>r.json()).then(d=>{if(d.success)location.reload();else showError(d.error)});
        }
        
        function editUnit(id) {
            document.getElementById('editType').value = 'unit';
            document.getElementById('editId').value = id;
            document.getElementById('modalTitle').textContent = 'Редактировать единицу';
            document.getElementById('editName').style.display = 'block';
            document.getElementById('editShort').style.display = 'block';
            document.getElementById('editColor').style.display = 'none';
            document.getElementById('editProductFields').style.display = 'none';
            fetch('get_unit/' + id).then(r=>r.json()).then(d=>{
                document.getElementById('editName').value = d.name;
                document.getElementById('editShort').value = d.name_short;
            });
            document.getElementById('editModal').style.display = 'flex';
        }
        
        function deleteUnit(id) {
            if(confirm('Удалить единицу?')) {
                fetch('delete_unit', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:id})})
                .then(r=>r.json()).then(d=>{if(d.success)location.reload();else showError(d.error)});
            }
        }
        
        function addUnit() {
            const name = document.getElementById('newUnitName').value.trim();
            const short = document.getElementById('newUnitShort').value.trim();
            if(!name||!short){showError('Заполните поля');return;}
            fetch('add_unit', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:name,name_short:short})})
            .then(r=>r.json()).then(d=>{if(d.success)location.reload();else showError(d.error)});
        }
        
        function editProduct(id) {
            document.getElementById('editType').value = 'product';
            document.getElementById('editId').value = id;
            document.getElementById('modalTitle').textContent = 'Редактировать товар';
            document.getElementById('editName').style.display = 'block';
            document.getElementById('editShort').style.display = 'none';
            document.getElementById('editColor').style.display = 'none';
            document.getElementById('editProductFields').style.display = 'block';
            fetch('get_product/' + id).then(r=>r.json()).then(d=>{
                document.getElementById('editName').value = d.name;
                document.getElementById('editInputUnit').value = d.input_unit_id;
                document.getElementById('editCompareUnit').value = d.compare_unit_id;
            });
            document.getElementById('editModal').style.display = 'flex';
        }
        
        function deleteProduct(id) {
            if(confirm('Удалить товар? Все цены для него будут удалены.')) {
                fetch('delete_product', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:id})})
                .then(r=>r.json()).then(d=>{if(d.success)location.reload();else showError(d.error)});
            }
        }
        
        function addProduct() {
            const name = document.getElementById('newProductName').value.trim();
            const inputUnit = document.getElementById('newInputUnit').value;
            const compareUnit = document.getElementById('newCompareUnit').value;
            if(!name){showError('Введите название товара');return;}
            if(!inputUnit){showError('Выберите меру на упаковке');return;}
            if(!compareUnit){showError('Выберите меру сравнения');return;}
            fetch('add_product', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({
                name:name, input_unit_id: parseInt(inputUnit), compare_unit_id: parseInt(compareUnit)
            })}).then(r=>r.json()).then(d=>{if(d.success)location.reload();else showError(d.error)});
        }
        
        function saveItem() {
            const type = document.getElementById('editType').value;
            const id = parseInt(document.getElementById('editId').value);
            if(type==='store'){
                const name = document.getElementById('editName').value.trim();
                const color = document.getElementById('editColor').value;
                if(!name){showError('Введите название');return;}
                fetch('edit_store', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:id,name:name,color:color})})
                .then(r=>r.json()).then(d=>{if(d.success)location.reload();else showError(d.error)});
            } else if(type==='unit'){
                const name = document.getElementById('editName').value.trim();
                const short = document.getElementById('editShort').value.trim();
                if(!name||!short){showError('Заполните все поля');return;}
                fetch('edit_unit', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:id,name:name,name_short:short})})
                .then(r=>r.json()).then(d=>{if(d.success)location.reload();else showError(d.error)});
            } else {
                const name = document.getElementById('editName').value.trim();
                const inputUnit = document.getElementById('editInputUnit').value;
                const compareUnit = document.getElementById('editCompareUnit').value;
                if(!name){showError('Введите название товара');return;}
                fetch('edit_product', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({
                    id:id, name:name, input_unit_id: parseInt(inputUnit), compare_unit_id: parseInt(compareUnit)
                })}).then(r=>r.json()).then(d=>{if(d.success)location.reload();else showError(d.error)});
            }
        }
        
        function closeModal() { document.getElementById('editModal').style.display = 'none'; }
        window.onclick = function(e) { if(e.target === document.getElementById('editModal')) closeModal(); }
    </script>
</body>
</html>
'''

# --- HTML шаблон отчёта ---
REPORT_TEMPLATE = '''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RealPrice — отчёт за год</title>
    <link rel="icon" type="image/png" href="favicon.png">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { background: #f5f5f5; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; padding: 0; }
        
        .site-header {
            background: white; padding: 10px 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
            display: flex; justify-content: center; align-items: center;
        }
        .site-header a { text-decoration: none; display: inline-flex; align-items: center; gap: 8px; }
        .site-header img { height: 32px; width: 32px; }
        .site-header .logo-text { font-size: 26px; font-weight: 900; color: #FF6B35; }
        
        .site-footer { text-align: center; padding: 20px; margin-top: 40px; }
        .container { max-width: 1200px; margin: 0 auto; padding: 16px; }
        
        .header { background: white; border-radius: 12px; padding: 20px; margin-bottom: 24px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }
        .header h1 { color: #333; font-size: 24px; margin-bottom: 4px; }
        .header p { color: #999; font-size: 14px; }
        
        .nav-links { display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap; }
        .btn-link {
            background: white; color: #666; border: 2px solid #e0e0e0;
            padding: 10px 20px; border-radius: 8px; font-size: 14px; font-weight: 600;
            cursor: pointer; text-decoration: none; transition: all 0.2s; display: inline-block;
        }
        .btn-link:hover { border-color: #FF6B35; color: #FF6B35; }
        
        .chart-container { background: white; border-radius: 12px; padding: 20px; margin-bottom: 24px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }
        .chart-container h3 { margin-bottom: 16px; color: #333; }
        canvas { width: 100%; max-height: 400px; }
        .charts-grid { display: grid; grid-template-columns: 1fr; gap: 24px; }
        
        table { width: 100%; border-collapse: collapse; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #f0f0f0; font-size: 14px; }
        th { background: #f8f9fa; color: #999; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; }
        .price-up { color: #e53935; }
        .price-down { color: #4CAF50; }
        .price-same { color: #999; }
    </style>
</head>
<body>
    <header class="site-header">
        <a href="/price/">
            <img src="favicon.png" alt="RealPrice" width="32" height="32">
            <span class="logo-text">RealPrice</span>
        </a>
    </header>
    
    <div class="container">
        <div class="nav-links">
            <a href="/price/?p=0000" class="btn-link">🛒 Сравнение цен</a>
        </div>
        
        <div class="header">
            <h1>📈 Отчёт об изменении цен за год</h1>
            <p>Средняя цена по всем товарам и детализация по выбранному</p>
        </div>
        
        <div class="charts-grid">
            <div class="chart-container">
                <h3>📊 Средняя цена по всем товарам за год</h3>
                <canvas id="avgChart"></canvas>
            </div>
            
            {% if report_data %}
            <div class="chart-container">
                <h3>📈 Детализация: 
                    <select onchange="if(this.value) window.location.href = window.location.pathname + '?p=0000&product_id=' + this.value;" style="padding:6px 10px;border-radius:6px;border:1px solid #ddd;font-size:14px;">
                        {% for product in all_products %}
                        <option value="{{ product[0] }}" {% if selected_product_id == product[0] %}selected{% endif %}>{{ product[1] }}</option>
                        {% endfor %}
                    </select>
                </h3>
                <canvas id="priceChart"></canvas>
            </div>
            
            <table>
                <thead>
                    <tr><th>Месяц</th><th>Мин. цена за ед.</th><th>Магазин</th><th>Бренд</th><th>Изменение</th></tr>
                </thead>
                <tbody>
                    {% for row in report_data %}
                    <tr>
                        <td>{{ row[0] }}</td>
                        <td><strong>{{ "%.0f"|format(row[1]) }} ₽/{{ row[4] }}</strong></td>
                        <td>{{ row[2] }}</td>
                        <td>{{ row[3] if row[3] else '—' }}</td>
                        <td class="{% if row[5] > 0 %}price-up{% elif row[5] < 0 %}price-down{% else %}price-same{% endif %}">
                            {% if row[5] > 0 %}↑ +{{ "%.0f"|format(row[5]) }} ₽{% elif row[5] < 0 %}↓ {{ "%.0f"|format(row[5]) }} ₽{% else %}—{% endif %}
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
            {% else %}
            <div class="chart-container" style="text-align:center;color:#999;padding:40px;">
                Выберите товар для детального отчёта
            </div>
            {% endif %}
        </div>
    </div>
    
    <footer class="site-footer">
        <span style="color: #6c757d; font-size: 14px;">&copy; Terre & Co, {{ current_year }}</span>
    </footer>
    
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <script>
        const avgCtx = document.getElementById('avgChart').getContext('2d');
        new Chart(avgCtx, {
            type: 'line',
            data: {
                labels: [{% for month in avg_labels %}'{{ month }}',{% endfor %}],
                datasets: [{
                    label: 'Средняя цена',
                    data: [{% for price in avg_prices %}{{ "%.2f"|format(price) }},{% endfor %}],
                    borderColor: '#2196F3', backgroundColor: 'rgba(33,150,243,0.1)',
                    fill: true, tension: 0.3, pointRadius: 5, pointBackgroundColor: '#2196F3'
                }]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: { y: { beginAtZero: false, ticks: { callback: function(v) { return v + ' ₽'; } } } }
            }
        });
        
        {% if report_data %}
        const ctx = document.getElementById('priceChart').getContext('2d');
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: [{% for row in report_data %}'{{ row[0] }}',{% endfor %}],
                datasets: [{
                    label: 'Мин. цена за ед.',
                    data: [{% for row in report_data %}{{ "%.2f"|format(row[1]) }},{% endfor %}],
                    borderColor: '#FF6B35', backgroundColor: 'rgba(255,107,53,0.1)',
                    fill: true, tension: 0.3, pointRadius: 5, pointBackgroundColor: '#FF6B35'
                }]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: { y: { beginAtZero: false, ticks: { callback: function(v) { return v + ' ₽'; } } } }
            }
        });
        {% endif %}
    </script>
</body>
</html>
'''

# --- Маршруты ---
@app.route('/favicon.png')
def favicon():
    return send_file('favicon.png', mimetype='image/png')

@app.route('/', methods=['GET', 'POST'])
def index():
    password = request.args.get('p') or request.form.get('p')
    if password != '0000':
        return '''
        <!DOCTYPE html>
        <html lang="ru">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
            <title>RealPrice — вход</title>
            <link rel="icon" type="image/png" href="favicon.png">
            <style>
                * { margin: 0; padding: 0; box-sizing: border-box; }
                body {
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    background: #f5f5f5;
                    padding: 20px;
                }
                .login-card {
                    background: white;
                    padding: 32px 24px;
                    border-radius: 16px;
                    box-shadow: 0 4px 16px rgba(0,0,0,0.08);
                    text-align: center;
                    width: 100%;
                    max-width: 340px;
                }
                .login-card h2 {
                    margin-bottom: 20px;
                    color: #333;
                    font-size: 20px;
                }
                .login-card input {
                    width: 100%;
                    padding: 14px;
                    border-radius: 10px;
                    border: 2px solid #e0e0e0;
                    font-size: 18px;
                    text-align: center;
                    margin-bottom: 14px;
                    outline: none;
                    -webkit-appearance: none;
                }
                .login-card input:focus {
                    border-color: #FF6B35;
                }
                .login-card button {
                    width: 100%;
                    padding: 14px;
                    background: #FF6B35;
                    color: white;
                    border: none;
                    border-radius: 10px;
                    font-size: 18px;
                    font-weight: 600;
                    cursor: pointer;
                    -webkit-appearance: none;
                }
            </style>
        </head>
        <body>
            <div class="login-card">
                <h2>🔒 RealPrice</h2>
                <form method="GET">
                    <input type="password" name="p" placeholder="Введите пароль" autofocus>
                    <button type="submit">Войти</button>
                </form>
            </div>
        </body>
        </html>'''
    
    selected_product_id = request.args.get('product_id')
    
    if request.method == 'POST' and request.form.get('measure_value') and request.form.get('price'):
        store_id = int(request.form['store_id'])
        product_id = int(request.form['product_id'])
        brand = request.form.get('brand', '').strip()
        measure_value = float(request.form['measure_value'])
        price = float(request.form['price'])
        
        if measure_value > 0 and price > 0:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute('SELECT input_unit_id, compare_unit_id FROM products WHERE id = ?', (product_id,))
            result = c.fetchone()
            if result:
                input_unit_id, compare_unit_id = result
                price_per_compare = calculate_price_per_compare(measure_value, price, compare_unit_id, input_unit_id)
                c.execute('INSERT INTO price_entries (store_id, product_id, brand, measure_value, price, price_per_compare) VALUES (?, ?, ?, ?, ?, ?)',
                         (store_id, product_id, brand if brand else None, measure_value, price, price_per_compare))
                conn.commit()
            conn.close()
            return redirect(f"?p=0000&product_id={product_id}")
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('SELECT id, name, color FROM stores ORDER BY name')
    stores = c.fetchall()
    
    c.execute('''
        SELECT p.id, p.name, u1.name_short, u2.name_short
        FROM products p
        JOIN units u1 ON p.input_unit_id = u1.id
        JOIN units u2 ON p.compare_unit_id = u2.id
        ORDER BY p.name
    ''')
    all_products = c.fetchall()
    
    c.execute('SELECT id, name, name_short FROM units ORDER BY name')
    units = c.fetchall()
    
    price_entries = []
    if selected_product_id:
        prod_id = int(selected_product_id)
        c.execute('''
            SELECT s.name, pr.name, u_input.name_short, pe.measure_value, 
                   u_compare.name_short, pe.brand, pe.price_per_compare, pe.price,
                   u_compare.name, pe.id, s.color
            FROM price_entries pe
            JOIN stores s ON pe.store_id = s.id
            JOIN products pr ON pe.product_id = pr.id
            JOIN units u_input ON pr.input_unit_id = u_input.id
            JOIN units u_compare ON pr.compare_unit_id = u_compare.id
            WHERE pe.product_id = ?
            ORDER BY pe.price_per_compare ASC
            LIMIT 5
        ''', (prod_id,))
        price_entries = c.fetchall()
    
    conn.close()
    
    return render_template_string(INDEX_TEMPLATE, 
                                 stores=stores,
                                 all_products=all_products,
                                 selected_product_id=int(selected_product_id) if selected_product_id else None,
                                 price_entries=price_entries,
                                 units=units,
                                 current_year=datetime.now().year,
                                 fmt_measure=fmt_measure)

@app.route('/delete_entry', methods=['POST'])
def delete_entry():
    data = request.json
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('DELETE FROM price_entries WHERE id = ?', (data['id'],))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/report')
def report():
    password = request.args.get('p')
    if password != '0000':
        return '''<html><body style="display:flex;justify-content:center;align-items:center;height:100vh;font-family:sans-serif;background:#f5f5f5;"><h2 style="color:#999;">Доступ запрещён</h2></body></html>''', 403
    
    selected_product_id = request.args.get('product_id')
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''
        SELECT p.id, p.name, u1.name_short, u2.name_short
        FROM products p
        JOIN units u1 ON p.input_unit_id = u1.id
        JOIN units u2 ON p.compare_unit_id = u2.id
        ORDER BY p.name
    ''')
    all_products = c.fetchall()
    
    c.execute('''
        SELECT 
            strftime('%Y-%m', pe.created_at) as month,
            AVG(pe.price_per_compare) as avg_price
        FROM price_entries pe
        WHERE pe.created_at >= datetime('now', '-12 months')
        GROUP BY strftime('%Y-%m', pe.created_at)
        ORDER BY month ASC
    ''')
    avg_rows = c.fetchall()
    avg_labels = [row[0] for row in avg_rows]
    avg_prices = [row[1] for row in avg_rows]
    
    report_data = []
    if selected_product_id:
        prod_id = int(selected_product_id)
        c.execute('''
            SELECT 
                strftime('%Y-%m', pe.created_at) as month,
                MIN(pe.price_per_compare) as min_price,
                s.name as store_name,
                (SELECT pe2.brand FROM price_entries pe2 
                 WHERE pe2.product_id = pe.product_id 
                 AND strftime('%Y-%m', pe2.created_at) = strftime('%Y-%m', pe.created_at)
                 AND pe2.price_per_compare = MIN(pe.price_per_compare) 
                 LIMIT 1) as brand,
                u_compare.name_short as compare_unit
            FROM price_entries pe
            JOIN stores s ON pe.store_id = s.id
            JOIN products pr ON pe.product_id = pr.id
            JOIN units u_compare ON pr.compare_unit_id = u_compare.id
            WHERE pe.product_id = ?
            AND pe.created_at >= datetime('now', '-12 months')
            GROUP BY strftime('%Y-%m', pe.created_at)
            ORDER BY month ASC
        ''', (prod_id,))
        rows = c.fetchall()
        
        prev_price = None
        for row in rows:
            month, min_price, store_name, brand, compare_unit = row
            change = min_price - prev_price if prev_price is not None else 0
            report_data.append((month, min_price, store_name, brand, compare_unit, change))
            prev_price = min_price
    
    conn.close()
    
    return render_template_string(REPORT_TEMPLATE,
                                 all_products=all_products,
                                 selected_product_id=int(selected_product_id) if selected_product_id else None,
                                 report_data=report_data,
                                 avg_labels=avg_labels,
                                 avg_prices=avg_prices,
                                 current_year=datetime.now().year)

@app.route('/get_store/<int:store_id>')
def get_store(store_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT id, name, color FROM stores WHERE id = ?', (store_id,))
    store = c.fetchone()
    conn.close()
    return jsonify({'id': store[0], 'name': store[1], 'color': store[2]}) if store else jsonify({'error': 'not found'}), 404

@app.route('/add_store', methods=['POST'])
def add_store():
    data = request.json
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        color = data.get('color', '#FF6B35')
        c.execute('INSERT INTO stores (name, color) VALUES (?, ?)', (data['name'].strip(), color))
        conn.commit()
        return jsonify({'success': True})
    except sqlite3.IntegrityError:
        return jsonify({'success': False, 'error': 'Такой магазин уже существует'})
    finally:
        conn.close()

@app.route('/edit_store', methods=['POST'])
def edit_store():
    data = request.json
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        color = data.get('color', '#FF6B35')
        c.execute('UPDATE stores SET name = ?, color = ? WHERE id = ?', (data['name'].strip(), color, data['id']))
        conn.commit()
        return jsonify({'success': True})
    except sqlite3.IntegrityError:
        return jsonify({'success': False, 'error': 'Такой магазин уже существует'})
    finally:
        conn.close()

@app.route('/delete_store', methods=['POST'])
def delete_store():
    data = request.json
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('DELETE FROM stores WHERE id = ?', (data['id'],))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/get_unit/<int:unit_id>')
def get_unit(unit_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT id, name, name_short FROM units WHERE id = ?', (unit_id,))
    unit = c.fetchone()
    conn.close()
    return jsonify({'id': unit[0], 'name': unit[1], 'name_short': unit[2]}) if unit else jsonify({'error': 'not found'}), 404

@app.route('/get_product/<int:product_id>')
def get_product(product_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT id, name, input_unit_id, compare_unit_id FROM products WHERE id = ?', (product_id,))
    product = c.fetchone()
    conn.close()
    if product:
        return jsonify({'id': product[0], 'name': product[1], 'input_unit_id': product[2], 'compare_unit_id': product[3]})
    return jsonify({'error': 'not found'}), 404

@app.route('/add_unit', methods=['POST'])
def add_unit():
    data = request.json
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute('INSERT INTO units (name, name_short) VALUES (?, ?)', (data['name'].strip(), data['name_short'].strip()))
        conn.commit()
        return jsonify({'success': True})
    except sqlite3.IntegrityError:
        return jsonify({'success': False, 'error': 'Такое сокращение уже есть'})
    finally:
        conn.close()

@app.route('/edit_unit', methods=['POST'])
def edit_unit():
    data = request.json
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('UPDATE units SET name = ?, name_short = ? WHERE id = ?', (data['name'].strip(), data['name_short'].strip(), data['id']))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/delete_unit', methods=['POST'])
def delete_unit():
    data = request.json
    if is_unit_used(data['id']):
        return jsonify({'success': False, 'error': 'Единица используется в товарах'})
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('DELETE FROM units WHERE id = ?', (data['id'],))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/add_product', methods=['POST'])
def add_product():
    data = request.json
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute('INSERT INTO products (name, input_unit_id, compare_unit_id) VALUES (?, ?, ?)',
                 (data['name'].strip(), data['input_unit_id'], data['compare_unit_id']))
        conn.commit()
        return jsonify({'success': True})
    except sqlite3.IntegrityError:
        return jsonify({'success': False, 'error': 'Такой товар уже существует'})
    finally:
        conn.close()

@app.route('/edit_product', methods=['POST'])
def edit_product():
    data = request.json
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute('UPDATE products SET name = ?, input_unit_id = ?, compare_unit_id = ? WHERE id = ?',
                 (data['name'].strip(), data['input_unit_id'], data['compare_unit_id'], data['id']))
        conn.commit()
        return jsonify({'success': True})
    except sqlite3.IntegrityError:
        return jsonify({'success': False, 'error': 'Такой товар уже существует'})
    finally:
        conn.close()

@app.route('/delete_product', methods=['POST'])
def delete_product():
    data = request.json
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('DELETE FROM products WHERE id = ?', (data['id'],))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

if __name__ == '__main__':
    # init_db()
    app.run(host='0.0.0.0', port=5010, debug=True)
